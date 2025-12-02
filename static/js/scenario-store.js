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
        for (const c of d.components || []) if (!c._customCadence) {
          c.cadence = d.cadence; c.months = d.months;
        }
      }
      this.recompute(); 
      this.emit();
      
      if ((patch.hours !== undefined && patch.hours !== oldHours) || 
          (patch.months !== undefined && patch.months !== oldMonths)) {
        this.emitPricingChange(did, d);
      }
      
      if (patch && (patch.hours !== undefined || patch.rate !== undefined || patch.cadence !== undefined || patch.months !== undefined)) {
        this.patchScenarioItem(did, {
          hours: d.hours,
          rate: d.rate,
          cadence: d.cadence,
          months: d.months
        });
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
      
      if (patch.hours !== undefined && patch.hours !== oldHours) {
        this.emitPricingChange(did, d);
      }
      
      if (patch && (patch.hours !== undefined || patch.rate !== undefined || patch.cadence !== undefined || patch.months !== undefined)) {
        this.patchScenarioItem(`${did}::${cid}`, {
          hours: c.hours,
          rate: c.rate,
          cadence: c.cadence,
          months: c.months,
          _isComponent: true,
          _deliverableId: did
        });
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
      // GPT 5.1 Pro spec: Do NOT recalc prices client-side - let Python apply_cadence_to_item do it.
      // This function now only aggregates read-only totals from backend-computed values.
      let hours = 0, oneTimeCost = 0, monthlyHours = 0, monthlyCost = 0;
      const rate = Number(this.state.blendedRate || DEFAULTS.blendedRate);
      for (const d of this.state.deliverables) {
        // Sum component hours if deliverable hours not set
        const dh = (typeof d.hours === "number" && d.hours > 0) ? d.hours
                   : (d.components || []).reduce((s,c)=> s + (Number(c.hours||0)||0), 0);
        d.hours = Math.round(dh*10)/10;
        d.rate   = d.rate || rate;
        
        // Use backend-computed price if available, else estimate for display only
        const backendPrice = d.price_usd || d.Price_USD || d.total_price || d.price;
        if (backendPrice && backendPrice > 0) {
          d.price = backendPrice;
        }
        
        // Cadence classification for totals aggregation
        const cad = d.billing_cadence || d.cadence || "one_time";
        const isRetainer = d.is_retainer || (cad !== "one_time" && cad !== "One-Time");
        
        if (isRetainer) {
          monthlyHours += d.monthly_hours || d.hours || 0;
          monthlyCost += d.monthly_price || (d.price / (d.retainer_months || 1)) || 0;
        } else {
          oneTimeCost += d.price || 0;
        }
        hours += d.hours || 0;
        
        // Component aggregation (read-only)
        for (const c of d.components || []) {
          c.rate = c.rate || rate;
          c.hours = Number(c.hours || 0);
          const cPrice = c.price_usd || c.Price_USD || c.price;
          if (cPrice && cPrice > 0) c.price = cPrice;
        }
      }
      this.state.totals.hours = Math.round(hours*10)/10;
      this.state.totals.oneTimeCost = Math.round(oneTimeCost);
      this.state.totals.monthlyHours = Math.round(monthlyHours*10)/10;
      this.state.totals.monthlyCost = Math.round(monthlyCost);
      this.state.totals.grandTotal12 = Math.round(oneTimeCost + (monthlyCost * 12));
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
    
    _patchDebounce: null,
    _pendingPatches: {},
    
    async patchScenarioItem(deliverableId, updates) {
      const sessionId = this.sessionId;
      if (!sessionId) {
        console.warn("[ScenarioStore] No session_id, cannot PATCH to backend");
        return;
      }
      
      this._pendingPatches[deliverableId] = Object.assign(
        this._pendingPatches[deliverableId] || {},
        updates
      );
      
      if (this._patchDebounce) clearTimeout(this._patchDebounce);
      this._patchDebounce = setTimeout(() => this._flushPatches(), 300);
    },
    
    async flushPatchesNow() {
      if (this._patchDebounce) {
        clearTimeout(this._patchDebounce);
        this._patchDebounce = null;
      }
      await this._flushPatches();
    },
    
    async _flushPatches() {
      // GPT 5.1 Pro spec: Use /api/scenario/sync instead of /api/pricing/scenario/item
      // This ensures cadence edits are processed by apply_cadence_to_item on the backend
      const sessionId = this.sessionId;
      if (!sessionId) return;
      
      const patches = Object.entries(this._pendingPatches);
      if (patches.length === 0) return;
      
      this._pendingPatches = {};
      
      // Apply patches to local deliverables first
      for (const [patchId, updates] of patches) {
        let delivId = patchId;
        let componentId = null;
        
        if (patchId.includes("::")) {
          const parts = patchId.split("::");
          delivId = parts[0];
          componentId = parts[1];
        }
        
        const d = this.state.deliverables.find(x => x.id === delivId);
        if (!d) continue;
        
        if (componentId) {
          const c = (d.components || []).find(x => x.id === componentId);
          if (c) Object.assign(c, updates);
        } else {
          Object.assign(d, updates);
        }
      }
      
      // Now sync entire scenario to backend
      await this.syncToBackend();
    },
    
    // Scenario sync versioning for conflict detection
    _clientVersion: 1,
    _lastServerVersion: 0,
    
    async syncToBackend() {
      // GPT 5.1 Pro spec: POST to /api/scenario/sync with full scenario
      // Backend runs apply_cadence_to_item on each item and returns normalized data
      const sessionId = this.sessionId;
      if (!sessionId) {
        console.warn("[ScenarioStore] No session_id, cannot sync to backend");
        return null;
      }
      
      try {
        // Build scenario items array with correct field names for backend
        const items = this.state.deliverables.map(d => ({
          id: d.id,
          deliverable_code: d.deliverable_code || d.id,
          Row_ID: d.Row_ID,
          title: d.title || d.name,
          billing_cadence: d.billing_cadence || d.cadence || "one_time",
          cadence_units: d.cadence_units || 1,
          cadence_price: d.cadence_price,
          monthly_price: d.monthly_price,
          retainer_months: d.retainer_months || d.months,
          is_retainer: d.is_retainer,
          hours: d.hours,
          Planned_Hours: d.Planned_Hours || d.hours,
          Rate_USD: d.Rate_USD || d.rate,
          price_usd: d.price_usd || d.Price_USD || d.price,
          Price_USD: d.Price_USD || d.price_usd || d.price,
          components: (d.components || []).map(c => ({
            id: c.id,
            title: c.title || c.name,
            hours: c.hours,
            Rate_USD: c.Rate_USD || c.rate,
            price_usd: c.price_usd || c.Price_USD || c.price
          }))
        }));
        
        const payload = {
          session_id: sessionId,
          client_version: this._clientVersion++,
          last_server_version: this._lastServerVersion,
          scenario: {
            items: items,
            totals: this.state.totals
          },
          timestamp: Date.now()
        };
        
        const r = await fetch("/api/scenario/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        
        if (!r.ok) throw new Error(await r.text());
        const data = await r.json();
        
        console.log("[ScenarioStore] Synced to backend:", data);
        
        // Update version tracking
        this._lastServerVersion = data.serverVersion || this._lastServerVersion;
        
        // If server has changes, update local state from server response
        if (data.hasChanges && data.scenario) {
          this._applyServerScenario(data.scenario);
        }
        
        // Update totals if available
        if (data.scenario && data.scenario.totals) {
          this._updateTotalsFromBackend(data.scenario.totals);
        }
        
        this.emit();
        return data;
        
      } catch (e) {
        console.warn("[ScenarioStore] Sync failed:", e.message);
        return null;
      }
    },
    
    _applyServerScenario(serverScenario) {
      // Apply server-computed values back to local deliverables
      if (!serverScenario || !serverScenario.items) return;
      
      const serverItemsById = {};
      for (const item of serverScenario.items) {
        const id = item.id || item.deliverable_code || item.Row_ID;
        if (id) serverItemsById[id] = item;
      }
      
      for (const d of this.state.deliverables) {
        const servItem = serverItemsById[d.id] || serverItemsById[d.deliverable_code];
        if (!servItem) continue;
        
        // Apply backend-computed cadence fields
        d.billing_cadence = servItem.billing_cadence || d.billing_cadence;
        d.cadence_units = servItem.cadence_units || d.cadence_units;
        d.cadence_price = servItem.cadence_price;
        d.monthly_price = servItem.monthly_price;
        d.retainer_months = servItem.retainer_months;
        d.is_retainer = servItem.is_retainer;
        d.monthly_hours = servItem.monthly_hours;
        
        // Apply backend-computed pricing
        d.price_usd = servItem.price_usd || servItem.Price_USD;
        d.Price_USD = servItem.Price_USD || servItem.price_usd;
        d.price = d.price_usd || d.Price_USD;
        
        // Apply backend-computed hours
        d.hours = servItem.hours || servItem.Planned_Hours || d.hours;
        d.Planned_Hours = servItem.Planned_Hours || d.hours;
      }
      
      console.log("[ScenarioStore] Applied server scenario to local state");
    },
    
    _updateTotalsFromBackend(totals) {
      if (!totals) return;
      this.state.totals.hours = totals.hours || totals.total_hours || 0;
      this.state.totals.oneTimeCost = totals.one_time_cost || totals.one_time?.price || totals.price || 0;
      this.state.totals.monthlyCost = totals.retainer_cost || totals.retainer?.price || 0;
      this.state.totals.monthlyHours = totals.retainer_hours || totals.retainer?.hours || 0;
      const grandTotal = (this.state.totals.oneTimeCost || 0) + ((this.state.totals.monthlyCost || 0) * 12);
      this.state.totals.grandTotal12 = grandTotal;
    },
    
    async rebuildBreakdown() {
      const sessionId = this.sessionId;
      if (!sessionId) {
        console.warn("[ScenarioStore] No session_id, cannot rebuild breakdown");
        return null;
      }
      
      try {
        const r = await fetch("/api/pricing/rebuild_breakdown", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId })
        });
        if (!r.ok) throw new Error(await r.text());
        const data = await r.json();
        
        console.log("[ScenarioStore] Rebuilt breakdown:", data);
        
        this._updateTotalsFromBackend(data.totals);
        if (data.summary) {
          this.state.totals.oneTimeCost = data.summary.one_time?.price || 0;
          this.state.totals.monthlyCost = data.summary.retainer?.price || 0;
          this.state.totals.hours = data.summary.grand_total?.hours || 0;
        }
        this.emit();
        
        document.dispatchEvent(new CustomEvent("pricing:breakdown-rebuilt", { detail: data }));
        
        return data;
      } catch (e) {
        console.warn("[ScenarioStore] Rebuild breakdown failed:", e.message);
        return null;
      }
    },
    
    async resetFromStep2() {
      const sessionId = this.sessionId;
      if (!sessionId) {
        console.warn("[ScenarioStore] No session_id, cannot reset from Step 2");
        return null;
      }
      
      try {
        const r = await fetch("/api/pricing/reset_from_step2", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId })
        });
        if (!r.ok) throw new Error(await r.text());
        const data = await r.json();
        
        console.log("[ScenarioStore] Reset from Step 2:", data);
        
        if (data.scenario) {
          this.load(data.scenario);
        }
        
        return data;
      } catch (e) {
        console.warn("[ScenarioStore] Reset from Step 2 failed:", e.message);
        return null;
      }
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
