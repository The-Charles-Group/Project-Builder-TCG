// scenario-manager.js
// Unified ScenarioManager that extends ScenarioStore to centralize all scenario operations
// This replaces direct window.currentScenario usage and provides a unified data flow

(function() {
  // Create ScenarioManager as an extension of ScenarioStore
  const ScenarioManager = {
    // Initialize with ScenarioStore methods
    ...window.ScenarioStore,
    
    // Override/extend state to include Step 2 selections
    state: {
      ...window.ScenarioStore.state,
      selectedDeliverables: new Set(),
      selectedComponents: {},
      selectedL3Tasks: {},
      sessionId: null,
      rfpText: '',
      buildPayload: null, // Last payload sent to /api/scenarios
      apiResponse: null   // Last response from /api/scenarios
    },
    
    // Get the current scenario in window.currentScenario format for compatibility
    getCurrentScenario() {
      return {
        items: this.state.deliverables.map(d => ({
          deliverable_code: d.id,
          deliverable_name: d.title,
          deliverable: d.title,
          category: d.dept || 'General',
          hours: d.hours || 0,
          rate: d.rate || this.state.blendedRate || 195,
          blended_rate: d.rate || this.state.blendedRate || 195,
          effective_rate: d.rate || this.state.blendedRate || 195,
          price: d.price || 0,
          is_retainer: d.cadence === 'Monthly' || d.cadence === 'Quarterly',
          retainer_months: d.months || 0,
          cadence: d.cadence || 'One-Time',
          resources: d.resources || [],
          components: (d.components || []).map(c => ({
            name: c.title,
            hours: c.hours || 0,
            rate: c.rate || d.rate || this.state.blendedRate || 195,
            cadence: c.cadence || d.cadence || 'One-Time',
            months: c.months || d.months || 0
          }))
        })),
        totals: this.state.totals,
        metadata: {
          createdAt: this.state.createdAt,
          updatedAt: this.state.updatedAt,
          sessionId: this.state.sessionId
        }
      };
    },
    
    // Set deliverables from Step 2 selections
    setSelectedDeliverables(codes, components = {}, l3Tasks = {}) {
      this.state.selectedDeliverables = new Set(codes);
      this.state.selectedComponents = components;
      this.state.selectedL3Tasks = l3Tasks;
      this.state.updatedAt = new Date().toISOString();
      
      console.log('[ScenarioManager] Updated selections:', {
        deliverables: codes.length,
        components: Object.keys(components).length,
        l3Tasks: Object.keys(l3Tasks).length
      });
      
      this.emit();
    },
    
    // Update deliverables from API response
    updateDeliverablesFromAPI(apiResponse) {
      if (!apiResponse) return;
      
      const scenario = apiResponse.scenarios?.A || apiResponse.scenario || apiResponse;
      if (!scenario || !scenario.items) {
        console.warn('[ScenarioManager] Invalid API response format:', apiResponse);
        return;
      }
      
      // Store the API response for reference
      this.state.apiResponse = apiResponse;
      
      // Clear existing deliverables
      this.state.deliverables = [];
      
      // Transform API items to ScenarioStore format
      scenario.items.forEach(item => {
        const deliverable = {
          id: item.deliverable_code,
          title: item.deliverable_name || item.deliverable || item.deliverable_code,
          dept: item.category || 'General',
          cadence: item.is_retainer ? 'Monthly' : 'One-Time',
          months: item.retainer_months || (item.is_retainer ? 12 : 0),
          hours: item.total_hours || item.hours || 0,
          rate: item.blended_rate || item.rate || item.effective_rate || 195,
          price: item.price || 0,
          resources: item.resources || [],
          components: [],
          resourceConflict: item.resourceConflict || null
        };
        
        // Transform components if they exist
        if (item.components && Array.isArray(item.components)) {
          deliverable.components = item.components.map(comp => ({
            id: this.slugify(comp.name || 'component'),
            title: comp.name || 'Component',
            hours: comp.hours || 0,
            rate: comp.rate || deliverable.rate,
            cadence: comp.cadence || deliverable.cadence,
            months: comp.months || deliverable.months,
            price: (comp.hours || 0) * (comp.rate || deliverable.rate)
          }));
        }
        
        this.state.deliverables.push(deliverable);
      });
      
      // Update totals if provided
      if (scenario.totals) {
        Object.assign(this.state.totals, scenario.totals);
      }
      
      // Recompute and notify
      this.recompute();
      this.emit();
      
      // Also update window.currentScenario for legacy compatibility
      window.currentScenario = this.getCurrentScenario();
      
      console.log('[ScenarioManager] Updated from API:', {
        deliverables: this.state.deliverables.length,
        total: this.state.totals.grandTotal12
      });
    },
    
    // Build scenario payload for API
    buildScenarioPayload() {
      const codes = Array.from(this.state.selectedDeliverables);
      const selectedComponentsPayload = this.state.selectedComponents;
      const l3Payload = this.state.selectedL3Tasks;
      
      // Get retainer configuration from pricingData if available
      const retainersPayload = [];
      if (window.pricingData && window.pricingData.deliverableTypes) {
        window.pricingData.deliverableTypes.forEach((type, code) => {
          if (type === 'RETAINER' && codes.includes(code)) {
            retainersPayload.push({
              deliverable_code: code,
              months: window.pricingData.retainers.get(code) || 12,
              type: 'RETAINER'
            });
          }
        });
      }
      
      const payload = {
        selectedDeliverableCodes: codes,
        selectedComponentsMap: selectedComponentsPayload,
        selectedL2Map: l3Payload,
        pricingMode: window.getPricingModeFromUI?.() || 'Flat_Blended',
        blendedRate: this.state.blendedRate || window.getBlendedRateFromUI?.() || 195,
        rateBand: window.getRateBandFromUI?.() || 'Standard_US',
        projectStart: window.getProjectStartFromUI?.() || null,
        clientBudgetUsd: window.getClientBudgetFromUI?.() || null,
        retainers: retainersPayload,
        sessionId: this.state.sessionId
      };
      
      this.state.buildPayload = payload;
      return payload;
    },
    
    // Call API to build scenario
    async buildScenario() {
      const payload = this.buildScenarioPayload();
      
      console.log('[ScenarioManager] Building scenario with payload:', payload);
      
      try {
        const res = await fetch('/api/scenarios', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        
        if (!res.ok) {
          const msg = await res.text().catch(() => '');
          throw new Error(`Build failed (${res.status}): ${msg}`);
        }
        
        const json = await res.json();
        console.log('[ScenarioManager] Received scenario response:', json);
        
        // Update deliverables from API response
        this.updateDeliverablesFromAPI(json);
        
        // Update global state for compatibility
        window.SCENARIOS = json.scenarios || { A: this.getCurrentScenario() };
        window.APP_STATE = window.APP_STATE || {};
        window.APP_STATE.scenarios = window.SCENARIOS;
        window.APP_STATE.activeScenario = 'A';
        window.APP_STATE.sessionId = this.state.sessionId;
        
        return json;
      } catch (error) {
        console.error('[ScenarioManager] Build scenario failed:', error);
        throw error;
      }
    },
    
    // Update pricing from Step 3 changes (extends base method)
    updatePricing(deliverableId, updates) {
      const deliverable = this.state.deliverables.find(d => d.id === deliverableId);
      if (!deliverable) return;
      
      // Update the deliverable
      this.updateDeliverable(deliverableId, updates);
      
      // Sync to window.currentScenario
      window.currentScenario = this.getCurrentScenario();
      
      // If SCENARIOS exists, update it too
      if (window.SCENARIOS && window.SCENARIOS.A) {
        window.SCENARIOS.A = this.getCurrentScenario();
      }
      
      console.log('[ScenarioManager] Updated pricing for:', deliverableId, updates);
    },
    
    // Update component selection
    updateComponentSelection(deliverableId, componentId, selected) {
      const deliverable = this.state.deliverables.find(d => d.id === deliverableId);
      if (!deliverable) return;
      
      // Update selected components map
      if (!this.state.selectedComponents[deliverableId]) {
        this.state.selectedComponents[deliverableId] = new Set();
      }
      
      if (selected) {
        this.state.selectedComponents[deliverableId].add(componentId);
      } else {
        this.state.selectedComponents[deliverableId].delete(componentId);
      }
      
      // Find and update the component visibility/inclusion
      const component = deliverable.components?.find(c => c.id === componentId);
      if (component) {
        component.included = selected;
        // Recalculate deliverable hours based on included components
        this.recalculateDeliverableHours(deliverableId);
      }
      
      this.emit();
      
      console.log('[ScenarioManager] Updated component selection:', {
        deliverable: deliverableId,
        component: componentId,
        selected
      });
    },
    
    // Recalculate deliverable hours based on components
    recalculateDeliverableHours(deliverableId) {
      const deliverable = this.state.deliverables.find(d => d.id === deliverableId);
      if (!deliverable || !deliverable.components) return;
      
      // Sum hours from included components
      const componentHours = deliverable.components
        .filter(c => c.included !== false)
        .reduce((sum, c) => sum + (c.hours || 0), 0);
      
      // Update deliverable hours if components exist
      if (deliverable.components.length > 0 && componentHours > 0) {
        deliverable.hours = componentHours;
      }
      
      this.recompute();
    },
    
    // Helper to slugify component names
    slugify(text) {
      return text
        .toString()
        .toLowerCase()
        .trim()
        .replace(/\s+/g, '-')
        .replace(/[^\w\-]+/g, '')
        .replace(/\-\-+/g, '-')
        .replace(/^-+/, '')
        .replace(/-+$/, '');
    },
    
    // Sync with backend
    async syncToBackend() {
      try {
        const response = await fetch('/api/scenario/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scenario: this.getCurrentScenario(),
            sessionId: this.state.sessionId,
            timestamp: new Date().toISOString()
          })
        });
        
        if (!response.ok) {
          throw new Error(`Sync failed: ${response.status}`);
        }
        
        console.log('[ScenarioManager] Synced to backend successfully');
        return true;
      } catch (error) {
        console.error('[ScenarioManager] Backend sync failed:', error);
        return false;
      }
    },
    
    // Initialize session
    initSession(sessionId) {
      this.state.sessionId = sessionId || window.generateSessionId?.() || 
                              'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      console.log('[ScenarioManager] Initialized session:', this.state.sessionId);
      return this.state.sessionId;
    },
    
    // Clear all data
    clear() {
      this.state.deliverables = [];
      this.state.selectedDeliverables.clear();
      this.state.selectedComponents = {};
      this.state.selectedL3Tasks = {};
      this.state.totals = { 
        hours: 0, 
        oneTimeCost: 0, 
        monthlyHours: 0, 
        monthlyCost: 0, 
        grandTotal12: 0 
      };
      this.state.buildPayload = null;
      this.state.apiResponse = null;
      this.emit();
      
      console.log('[ScenarioManager] Cleared all data');
    }
  };
  
  // Expose globally
  window.ScenarioManager = ScenarioManager;
  
  // Auto-subscribe to update window.currentScenario for compatibility
  ScenarioManager.subscribe(() => {
    window.currentScenario = ScenarioManager.getCurrentScenario();
  });
  
  // Listen for pricing table changes
  document.addEventListener('pricing:changed', (event) => {
    const { deliverableId, hours, rate, months, cadence } = event.detail || {};
    if (deliverableId) {
      ScenarioManager.updatePricing(deliverableId, { hours, rate, months, cadence });
    }
  });
  
  console.log('[ScenarioManager] Initialized and ready');
})();