// scenario-store.js
// Central store: carries the "Working Scenario" across steps and keeps
// Step‑3 Pricing and Step‑4 Gantt in sync via pub/sub.

(function () {
  const _listeners = new Set();
  const DEFAULTS = { hoursPerDay: 6, currency: "USD", blendedRate: 210 };

  const ScenarioStore = {
    // Use SessionManager's canonical session_id (matches backend SCENARIO_STORE keys)
    get sessionId() {
      return window.SessionManager ? window.SessionManager.getCurrentSessionId() : null;
    },
    state: {
      id: "working",
      // session_id getter for backend sync
      get session_id() {
        return window.SessionManager ? window.SessionManager.getCurrentSessionId() : null;
      },
      name: "Working Scenario",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      currency: DEFAULTS.currency,
      blendedRate: DEFAULTS.blendedRate,
      hoursPerDay: DEFAULTS.hoursPerDay,
      deliverables: [],
      totals: { hours: 0, oneTimeCost: 0, monthlyHours: 0, monthlyCost: 0, grandTotal12: 0 }
    },
    subscribe(fn) { _listeners.add(fn); return () => _listeners.delete(fn); },
    emit() { for (const fn of Array.from(_listeners)) try { fn(this.state); } catch(_){} },
    setState(patch) {
      Object.assign(this.state, patch || {});
      this.recompute();
      this.state.updatedAt = new Date().toISOString();
      this.emit();
    },
    load(scenario) {
      if (!scenario) return;
      this.state = Object.assign({}, this.state, scenario);
      this.recompute();
      this.emit();
    },
    upsertDeliverable(d) {
      const idx = this.state.deliverables.findIndex(x => x.id === d.id);
      if (idx >= 0) this.state.deliverables[idx] = Object.assign({}, this.state.deliverables[idx], d);
      else this.state.deliverables.push(Object.assign({components:[], tasks:[], resources:[]}, d));
      this.recompute(); this.emit();
    },
    updateDeliverable(did, patch) {
      const d = this.state.deliverables.find(x => x.id === did);
      if (!d) return;
      const oldHours = d.hours;
      const oldMonths = d.months;
      Object.assign(d, patch || {});
      if (patch && patch.cadence) {
        // propagate unless component has an explicit override
        for (const c of d.components || []) if (!c._customCadence) {
          c.cadence = d.cadence; c.months = d.months;
        }
      }
      this.recompute(); 
      this.emit();
      
      // Emit pricing:changed event when hours or months change
      if ((patch.hours !== undefined && patch.hours !== oldHours) || 
          (patch.months !== undefined && patch.months !== oldMonths)) {
        this.emitPricingChange(did, d);
      }
    },
    updateComponent(did, cid, patch) {
      const d = this.state.deliverables.find(x => x.id === did);
      if (!d) return;
      const c = (d.components || []).find(x => x.id === cid);
      if (!c) return;
      const oldHours = c.hours;
      Object.assign(c, patch || {});
      if (patch && (patch.cadence || patch.months != null)) c._customCadence = true;
      this.recompute(); 
      this.emit();
      
      // Emit pricing:changed event when component hours change
      if (patch.hours !== undefined && patch.hours !== oldHours) {
        this.emitPricingChange(did, d);
      }
    },
    emitPricingChange(deliverableId, deliverable) {
      // Emit event for Gantt to update
      const detail = {
        deliverableId,
        hours: deliverable.hours,
        months: deliverable.months || 1,
        cadence: deliverable.cadence || "One-Time",
        hoursPerDay: this.state.hoursPerDay || DEFAULTS.hoursPerDay,
        resources: deliverable.resources || []
      };
      
      // Calculate duration in days from hours
      const hoursPerDay = detail.hoursPerDay;
      const resourceCount = Math.max(1, detail.resources.length);
      const durationDays = Math.ceil(detail.hours / (hoursPerDay * resourceCount));
      detail.durationDays = durationDays;
      
      console.log('[ScenarioStore] Emitting pricing:changed event:', detail);
      document.dispatchEvent(new CustomEvent("pricing:changed", { detail }));
    },
    upsertMany(deliverables) {
      for (const d of deliverables || []) this.upsertDeliverable(d);
      this.recompute(); this.emit();
    },
    recompute() {
      let hours = 0, oneTimeCost = 0, monthlyHours = 0, monthlyCost = 0;
      const rate = Number(this.state.blendedRate || DEFAULTS.blendedRate);
      for (const d of this.state.deliverables) {
        const dh = (typeof d.hours === "number") ? d.hours
                   : (d.components || []).reduce((s,c)=> s + (Number(c.hours||0)||0), 0);
        d.hours = Math.round(dh*10)/10;
        d.rate   = d.rate || rate;
        const cad = d.cadence || "One-Time";
        if (cad === "One-Time") {
          d.price = Math.round(d.hours * d.rate);
          oneTimeCost += d.price;
        } else {
          const months = Number(d.months || 1);
          d.price = Math.round(d.hours * d.rate * months);
          monthlyHours += d.hours;
          monthlyCost   += Math.round(d.hours * d.rate);
        }
        hours += d.hours;
        for (const c of d.components || []) {
          c.rate   = c.rate || rate;
          c.hours = Number(c.hours || 0);
          const ccad = c.cadence || d.cadence || "One-Time";
          if (ccad === "One-Time") c.price = Math.round(c.hours * c.rate);
          else {
            const months = Number(c.months || d.months || 1);
            c.price = Math.round(c.hours * c.rate * months);
          }
        }
      }
      this.state.totals.hours              = Math.round(hours*10)/10;
      this.state.totals.oneTimeCost        = oneTimeCost;
      this.state.totals.monthlyHours = Math.round(monthlyHours*10)/10;
      this.state.totals.monthlyCost        = monthlyCost;
      this.state.totals.grandTotal12 = oneTimeCost + (monthlyCost * 12);
    },
    async save() {
      try { localStorage.setItem("working_scenario", JSON.stringify(this.state)); } catch(_){}
      try {
        const r = await fetch("/api/scenario/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.state)
        });
        if (!r.ok) throw new Error(await r.text());
      } catch (e) { console.warn("Scenario save failed (local copy saved):", e.message); }
      this.emit();
    },
    updateFromGantt(payload) {
      const { deliverableId, durationDays, resources } = payload || {};
      const d = this.state.deliverables.find(x => x.id === deliverableId);
      if (!d) return;
      const hrsPerDay = Number(this.state.hoursPerDay || DEFAULTS.hoursPerDay);
      const resCount    = Number((Array.isArray(resources) ? resources.length : (resources||1)) || 1);
      d.hours = Math.round(Math.max(1, Number(durationDays||0)) * hrsPerDay * resCount * 10) / 10;

      if (d.cadence && d.cadence !== "One-Time" && payload.start && payload.end) {
        const s = new Date(payload.start), e = new Date(payload.end);
        const months = Math.max(1, (e.getFullYear() - s.getFullYear()) * 12 + (e.getMonth() - s.getMonth()) + 1);
        d.months = months;
        for (const c of d.components || []) if (!c._customCadence) c.months = months;
      }
      this.recompute(); this.emit();
    },
    applyResourceLeveling(levelingData) {
      if (!levelingData) return;
      
      const { totalCost, deliverableConflicts } = levelingData;
      
      // Store resource leveling data in state
      this.state.resourceLeveling = {
        totalCost: totalCost || 0,
        deliverableConflicts: deliverableConflicts || {},
        lastUpdated: new Date().toISOString()
      };
      
      // Apply leveling costs to affected deliverables
      for (const delivId in deliverableConflicts) {
        const d = this.state.deliverables.find(x => x.id === delivId);
        if (!d) continue;
        
        const conflict = deliverableConflicts[delivId];
        
        // Store conflict information on the deliverable
        d.resourceConflict = {
          hasConflict: true,
          cost: conflict.totalCost,
          conflicts: conflict.conflicts,
          riskLevel: Math.max(...conflict.conflicts.map(c => c.riskLevel === 'High' ? 3 : c.riskLevel === 'Medium' ? 2 : 1))
        };
      }
      
      // Clear conflicts from deliverables not in the conflict list
      this.state.deliverables.forEach(d => {
        if (!deliverableConflicts[d.id] && d.resourceConflict) {
          delete d.resourceConflict;
        }
      });
      
      // Recompute totals including leveling costs
      this.recomputeWithLeveling();
      this.emit();
      
      // Emit event for UI updates
      document.dispatchEvent(new CustomEvent('pricing:leveling-applied', { 
        detail: this.state.resourceLeveling 
      }));
    },
    recomputeWithLeveling() {
      // First do regular recompute
      this.recompute();
      
      // Then add resource leveling costs
      if (this.state.resourceLeveling && this.state.resourceLeveling.totalCost > 0) {
        // Add leveling cost to the grand total
        const levelingCost = this.state.resourceLeveling.totalCost;
        this.state.totals.resourceLevelingCost = levelingCost;
        this.state.totals.grandTotalWithLeveling = this.state.totals.grandTotal12 + levelingCost;
      } else {
        this.state.totals.resourceLevelingCost = 0;
        this.state.totals.grandTotalWithLeveling = this.state.totals.grandTotal12;
      }
    }
  };

  window.ScenarioStore = ScenarioStore;
  document.addEventListener("gantt:changed", (ev) => ScenarioStore.updateFromGantt(ev.detail || {}));
  document.addEventListener("resource:conflicts", (ev) => ScenarioStore.applyResourceLeveling(ev.detail || {}));

  // bootstrap from localStorage if available
  try {
    const saved = localStorage.getItem("working_scenario");
    if (saved) ScenarioStore.load(JSON.parse(saved));
  } catch(_) {}
})();
