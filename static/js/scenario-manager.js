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
      apiResponse: null,   // Last response from /api/scenarios
      lastSaved: null,
      isDirty: false,
      autoSaveTimer: null,
      saveIndicator: null
    },
    
    // Initialize with persistence support
    init() {
      // Get or create session ID from localStorage
      let sessionId = localStorage.getItem('apb.currentSession');
      if (!sessionId) {
        sessionId = this.generateSessionId();
        localStorage.setItem('apb.currentSession', sessionId);
        console.log('[ScenarioManager] Created new session:', sessionId);
      } else {
        console.log('[ScenarioManager] Restored session:', sessionId);
      }
      
      this.state.sessionId = sessionId;
      
      // Store sessionId globally for compatibility
      if (window.SessionManager) {
        window.SessionManager.currentSessionId = sessionId;
      }
      
      // Load scenario from backend if exists
      this.loadFromBackend().then(loaded => {
        if (loaded) {
          console.log('[ScenarioManager] Loaded scenario from backend');
        } else {
          console.log('[ScenarioManager] No existing scenario, starting fresh');
        }
      });
      
      // Set up auto-save
      this.setupAutoSave();
      
      // Set up beforeunload handler
      window.addEventListener('beforeunload', (e) => {
        if (this.state.isDirty) {
          this.saveToBackend(true); // Synchronous save
          e.preventDefault();
          e.returnValue = 'You have unsaved changes.';
        }
      });
      
      // Create save indicator UI
      this.createSaveIndicator();
      
      return this;
    },
    
    // Generate a new session ID
    generateSessionId() {
      if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
      }
      return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },
    
    // Load scenario from backend
    async loadFromBackend() {
      try {
        const sessionId = this.state.sessionId;
        if (!sessionId) return false;
        
        const response = await fetch(`/api/scenario/${sessionId}`);
        if (!response.ok) return false;
        
        const data = await response.json();
        if (!data.success || !data.scenario) return false;
        
        const scenario = data.scenario;
        
        // Restore state from scenario
        if (scenario.state) {
          // Restore deliverables
          if (scenario.state.deliverables) {
            this.state.deliverables = scenario.state.deliverables;
          }
          
          // Restore selections
          if (scenario.state.selectedDeliverables) {
            this.state.selectedDeliverables = new Set(scenario.state.selectedDeliverables);
          }
          if (scenario.state.selectedComponents) {
            this.state.selectedComponents = scenario.state.selectedComponents;
          }
          if (scenario.state.selectedL3Tasks) {
            this.state.selectedL3Tasks = scenario.state.selectedL3Tasks;
          }
          
          // Restore other state
          if (scenario.state.totals) {
            this.state.totals = scenario.state.totals;
          }
          if (scenario.state.blendedRate) {
            this.state.blendedRate = scenario.state.blendedRate;
          }
          if (scenario.state.rfpText) {
            this.state.rfpText = scenario.state.rfpText;
          }
        }
        
        // Restore scenario-level data
        if (scenario.items) {
          this.updateDeliverablesFromAPI({ scenario });
        }
        
        // Update last saved timestamp
        this.state.lastSaved = scenario.last_saved || null;
        this.state.isDirty = false;
        
        // Emit change event
        this.emit();
        
        return true;
      } catch (error) {
        console.error('[ScenarioManager] Error loading from backend:', error);
        return false;
      }
    },
    
    // Save scenario to backend
    async saveToBackend(synchronous = false) {
      try {
        if (!this.state.isDirty && !synchronous) return;
        
        const sessionId = this.state.sessionId;
        if (!sessionId) return;
        
        // Prepare save payload
        const payload = {
          session_id: sessionId,
          scenario: {
            state: {
              deliverables: this.state.deliverables,
              selectedDeliverables: Array.from(this.state.selectedDeliverables || []),
              selectedComponents: this.state.selectedComponents,
              selectedL3Tasks: this.state.selectedL3Tasks,
              totals: this.state.totals,
              blendedRate: this.state.blendedRate,
              rfpText: this.state.rfpText,
              createdAt: this.state.createdAt,
              updatedAt: this.state.updatedAt
            },
            items: this.getCurrentScenario().items,
            totals: this.state.totals,
            metadata: {
              createdAt: this.state.createdAt,
              updatedAt: new Date().toISOString(),
              sessionId: sessionId
            }
          }
        };
        
        // Include current step and UI state
        if (window.APP_STATE) {
          payload.scenario.currentStep = window.APP_STATE.currentStep;
          payload.scenario.activeScenario = window.APP_STATE.activeScenario;
        }
        
        // Show saving indicator
        this.updateSaveIndicator('saving');
        
        if (synchronous) {
          // Use synchronous XHR for beforeunload
          const xhr = new XMLHttpRequest();
          xhr.open('POST', '/api/scenario/save', false);
          xhr.setRequestHeader('Content-Type', 'application/json');
          xhr.send(JSON.stringify(payload));
        } else {
          const response = await fetch('/api/scenario/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          
          if (response.ok) {
            const result = await response.json();
            this.state.lastSaved = result.saved_at || new Date().toISOString();
            this.state.isDirty = false;
            this.updateSaveIndicator('saved');
            console.log('[ScenarioManager] Saved to backend at', this.state.lastSaved);
          } else {
            this.updateSaveIndicator('error');
            console.error('[ScenarioManager] Save failed:', response.status);
          }
        }
      } catch (error) {
        this.updateSaveIndicator('error');
        console.error('[ScenarioManager] Error saving to backend:', error);
      }
    },
    
    // Set up auto-save with debouncing
    setupAutoSave() {
      const AUTOSAVE_DELAY = 3000; // 3 seconds
      
      // Override emit to track changes
      const originalEmit = this.emit.bind(this);
      this.emit = () => {
        this.state.isDirty = true;
        this.state.updatedAt = new Date().toISOString();
        
        // Clear existing timer
        if (this.state.autoSaveTimer) {
          clearTimeout(this.state.autoSaveTimer);
        }
        
        // Set new timer for auto-save
        this.state.autoSaveTimer = setTimeout(() => {
          this.saveToBackend();
        }, AUTOSAVE_DELAY);
        
        originalEmit();
      };
    },
    
    // Create save indicator UI
    createSaveIndicator() {
      const existing = document.getElementById('save-indicator');
      if (existing) existing.remove();
      
      const indicator = document.createElement('div');
      indicator.id = 'save-indicator';
      indicator.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 10px 20px;
        border-radius: 20px;
        font-size: 14px;
        z-index: 10000;
        display: none;
        align-items: center;
        gap: 10px;
      `;
      
      document.body.appendChild(indicator);
      this.state.saveIndicator = indicator;
    },
    
    // Update save indicator
    updateSaveIndicator(status) {
      const indicator = this.state.saveIndicator;
      if (!indicator) return;
      
      indicator.style.display = 'flex';
      
      switch (status) {
        case 'saving':
          indicator.innerHTML = '<span>💾</span> Saving...';
          indicator.style.background = 'rgba(33, 150, 243, 0.9)';
          break;
        case 'saved':
          indicator.innerHTML = '<span>✓</span> Saved';
          indicator.style.background = 'rgba(76, 175, 80, 0.9)';
          setTimeout(() => {
            indicator.style.display = 'none';
          }, 2000);
          break;
        case 'error':
          indicator.innerHTML = '<span>⚠️</span> Save failed';
          indicator.style.background = 'rgba(244, 67, 54, 0.9)';
          setTimeout(() => {
            indicator.style.display = 'none';
          }, 3000);
          break;
      }
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
      if (!apiResponse) {
        console.warn('[ScenarioManager] No API response provided');
        return;
      }
      
      console.log('[ScenarioManager] Processing API response:', apiResponse);
      
      // Try to extract scenario from response
      const scenario = apiResponse.scenarios?.A || apiResponse.scenario || apiResponse;
      console.log('[ScenarioManager] Extracted scenario:', scenario);
      
      // Validate scenario exists and has items
      if (!scenario) {
        console.error('[ScenarioManager] Could not extract scenario from API response');
        alert('Build failed: Invalid API response structure');
        return;
      }
      
      if (!scenario.items) {
        console.error('[ScenarioManager] Scenario missing items array:', scenario);
        alert('Build failed: Scenario data is incomplete');
        return;
      }
      
      if (!Array.isArray(scenario.items)) {
        console.error('[ScenarioManager] Scenario items is not an array:', typeof scenario.items);
        alert('Build failed: Invalid scenario data format');
        return;
      }
      
      console.log('[ScenarioManager] Valid scenario with', scenario.items.length, 'items');
      
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
  
  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      ScenarioManager.init();
    });
  } else {
    // DOM already loaded
    ScenarioManager.init();
  }
})();