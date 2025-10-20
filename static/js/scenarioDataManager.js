// scenarioDataManager.js
// Manages the PRIMARY_SCENARIO object as single source of truth
// Integrates with existing ScenarioStore and ScenarioManager

(function() {
  'use strict';

  // Initialize PRIMARY_SCENARIO as the single source of truth
  window.PRIMARY_SCENARIO = {
    // Core identification
    id: null,
    sessionId: null,
    createdAt: null,
    updatedAt: null,
    
    // Step 1 - Analysis
    rfpText: '',
    analysisMode: 'fast', // 'fast' or 'deep'
    analysisResults: null,
    deliverables: [],
    
    // Step 2 - Selection
    selectedDeliverables: [],
    selectedComponents: {},
    selectedL2Tasks: {},
    
    // Step 3 - Pricing
    pricing: {},
    retainerAnalysis: null,
    projectType: 'project', // 'project' or 'retainer'
    blendedRate: 195,
    hoursPerDay: 6,
    totals: {
      hours: 0,
      oneTimeCost: 0,
      monthlyHours: 0,
      monthlyCost: 0,
      grandTotal12: 0
    },
    
    // Step 4 - Timeline
    timeline: null,
    ganttData: null,
    timelineReasoning: null,
    startDate: new Date().toISOString().split('T')[0],
    
    // Step 5 - Export
    exportHistory: [],
    status: 'draft', // 'draft', 'analyzing', 'analyzed', 'pricing', 'timeline', 'shipped'
    
    // Metadata
    projectName: '',
    clientName: '',
    version: '1.0',
    notes: ''
  };

  // ScenarioDataManager - Central management for PRIMARY_SCENARIO
  const ScenarioDataManager = {
    // Get the current scenario
    getScenario() {
      return window.PRIMARY_SCENARIO;
    },
    
    // Initialize scenario
    init(sessionId = null) {
      console.log('[ScenarioDataManager] Initializing PRIMARY_SCENARIO...');
      
      // Generate or use provided session ID
      if (!sessionId) {
        sessionId = this.generateSessionId();
      }
      
      // Initialize PRIMARY_SCENARIO
      window.PRIMARY_SCENARIO = {
        ...window.PRIMARY_SCENARIO,
        id: `scenario_${Date.now()}`,
        sessionId: sessionId,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        status: 'draft'
      };
      
      // Sync with ScenarioStore if it exists
      if (window.ScenarioStore) {
        this.syncWithScenarioStore();
      }
      
      // Sync with ScenarioManager if it exists
      if (window.ScenarioManager) {
        this.syncWithScenarioManager();
      }
      
      // Load from localStorage if available
      this.loadFromStorage();
      
      console.log('[ScenarioDataManager] Initialized:', window.PRIMARY_SCENARIO);
      
      return window.PRIMARY_SCENARIO;
    },
    
    // Update scenario with new data
    update(updates) {
      console.log('[ScenarioDataManager] Updating scenario:', updates);
      
      // Merge updates into PRIMARY_SCENARIO
      window.PRIMARY_SCENARIO = {
        ...window.PRIMARY_SCENARIO,
        ...updates,
        updatedAt: new Date().toISOString()
      };
      
      // Trigger sync
      this.sync();
      
      // Save to storage
      this.saveToStorage();
      
      // Emit update event
      this.emitUpdate();
      
      return window.PRIMARY_SCENARIO;
    },
    
    // Update specific step data
    updateStep(step, data) {
      console.log(`[ScenarioDataManager] Updating step ${step}:`, data);
      
      switch(step) {
        case 1:
          this.updateAnalysis(data);
          break;
        case 2:
          this.updateSelection(data);
          break;
        case 3:
          this.updatePricing(data);
          break;
        case 4:
          this.updateTimeline(data);
          break;
        case 5:
          this.updateExport(data);
          break;
      }
      
      return window.PRIMARY_SCENARIO;
    },
    
    // Step-specific update methods
    updateAnalysis(data) {
      window.PRIMARY_SCENARIO = {
        ...window.PRIMARY_SCENARIO,
        rfpText: data.rfpText || window.PRIMARY_SCENARIO.rfpText,
        analysisMode: data.analysisMode || window.PRIMARY_SCENARIO.analysisMode,
        analysisResults: data.analysisResults || window.PRIMARY_SCENARIO.analysisResults,
        deliverables: data.deliverables || window.PRIMARY_SCENARIO.deliverables,
        status: 'analyzed',
        updatedAt: new Date().toISOString()
      };
      
      this.sync();
      this.saveToStorage();
      this.emitUpdate();
    },
    
    updateSelection(data) {
      window.PRIMARY_SCENARIO = {
        ...window.PRIMARY_SCENARIO,
        selectedDeliverables: data.selectedDeliverables || window.PRIMARY_SCENARIO.selectedDeliverables,
        selectedComponents: data.selectedComponents || window.PRIMARY_SCENARIO.selectedComponents,
        selectedL2Tasks: data.selectedL2Tasks || window.PRIMARY_SCENARIO.selectedL2Tasks,
        status: 'selected',
        updatedAt: new Date().toISOString()
      };
      
      this.sync();
      this.saveToStorage();
      this.emitUpdate();
    },
    
    updatePricing(data) {
      // Calculate totals
      let totals = this.calculateTotals(data.pricing || window.PRIMARY_SCENARIO.pricing);
      
      window.PRIMARY_SCENARIO = {
        ...window.PRIMARY_SCENARIO,
        pricing: data.pricing || window.PRIMARY_SCENARIO.pricing,
        projectType: data.projectType || window.PRIMARY_SCENARIO.projectType,
        blendedRate: data.blendedRate || window.PRIMARY_SCENARIO.blendedRate,
        hoursPerDay: data.hoursPerDay || window.PRIMARY_SCENARIO.hoursPerDay,
        totals: totals,
        status: 'priced',
        updatedAt: new Date().toISOString()
      };
      
      this.sync();
      this.saveToStorage();
      this.emitUpdate();
    },
    
    updateTimeline(data) {
      window.PRIMARY_SCENARIO = {
        ...window.PRIMARY_SCENARIO,
        timeline: data.timeline || window.PRIMARY_SCENARIO.timeline,
        ganttData: data.ganttData || window.PRIMARY_SCENARIO.ganttData,
        timelineReasoning: data.timelineReasoning || window.PRIMARY_SCENARIO.timelineReasoning,
        startDate: data.startDate || window.PRIMARY_SCENARIO.startDate,
        status: 'scheduled',
        updatedAt: new Date().toISOString()
      };
      
      this.sync();
      this.saveToStorage();
      this.emitUpdate();
    },
    
    updateExport(data) {
      // Add to export history
      const exportRecord = {
        timestamp: new Date().toISOString(),
        format: data.format,
        filename: data.filename,
        success: data.success
      };
      
      window.PRIMARY_SCENARIO = {
        ...window.PRIMARY_SCENARIO,
        exportHistory: [...window.PRIMARY_SCENARIO.exportHistory, exportRecord],
        status: data.shipped ? 'shipped' : window.PRIMARY_SCENARIO.status,
        updatedAt: new Date().toISOString()
      };
      
      this.sync();
      this.saveToStorage();
      this.emitUpdate();
    },
    
    // Calculate totals from pricing data
    calculateTotals(pricing) {
      let hours = 0;
      let oneTimeCost = 0;
      let monthlyHours = 0;
      let monthlyCost = 0;
      
      const rate = window.PRIMARY_SCENARIO.blendedRate || 195;
      
      // Calculate from deliverables
      window.PRIMARY_SCENARIO.deliverables.forEach(deliverable => {
        const price = pricing[deliverable.id] || {};
        const deliverableHours = price.hours || 0;
        const deliverableRate = price.rate || rate;
        
        hours += deliverableHours;
        
        if (deliverable.cadence === 'monthly' || deliverable.type === 'retainer') {
          monthlyHours += deliverableHours;
          monthlyCost += deliverableHours * deliverableRate;
        } else {
          oneTimeCost += deliverableHours * deliverableRate;
        }
      });
      
      return {
        hours: Math.round(hours * 10) / 10,
        oneTimeCost: Math.round(oneTimeCost),
        monthlyHours: Math.round(monthlyHours * 10) / 10,
        monthlyCost: Math.round(monthlyCost),
        grandTotal12: Math.round(oneTimeCost + (monthlyCost * 12))
      };
    },
    
    // Sync with existing ScenarioStore
    syncWithScenarioStore() {
      if (!window.ScenarioStore) return;
      
      console.log('[ScenarioDataManager] Syncing with ScenarioStore...');
      
      // Update ScenarioStore state from PRIMARY_SCENARIO
      window.ScenarioStore.state = {
        ...window.ScenarioStore.state,
        id: window.PRIMARY_SCENARIO.id,
        sessionId: window.PRIMARY_SCENARIO.sessionId,
        deliverables: window.PRIMARY_SCENARIO.deliverables,
        totals: window.PRIMARY_SCENARIO.totals,
        blendedRate: window.PRIMARY_SCENARIO.blendedRate,
        hoursPerDay: window.PRIMARY_SCENARIO.hoursPerDay
      };
      
      // Subscribe to ScenarioStore changes
      window.ScenarioStore.subscribe((state) => {
        console.log('[ScenarioDataManager] ScenarioStore changed, updating PRIMARY_SCENARIO');
        
        // Update PRIMARY_SCENARIO from ScenarioStore
        window.PRIMARY_SCENARIO.deliverables = state.deliverables || window.PRIMARY_SCENARIO.deliverables;
        window.PRIMARY_SCENARIO.totals = state.totals || window.PRIMARY_SCENARIO.totals;
        window.PRIMARY_SCENARIO.blendedRate = state.blendedRate || window.PRIMARY_SCENARIO.blendedRate;
        window.PRIMARY_SCENARIO.hoursPerDay = state.hoursPerDay || window.PRIMARY_SCENARIO.hoursPerDay;
        window.PRIMARY_SCENARIO.updatedAt = new Date().toISOString();
        
        this.saveToStorage();
      });
    },
    
    // Sync with existing ScenarioManager
    syncWithScenarioManager() {
      if (!window.ScenarioManager) return;
      
      console.log('[ScenarioDataManager] Syncing with ScenarioManager...');
      
      // Update ScenarioManager state from PRIMARY_SCENARIO
      window.ScenarioManager.state = {
        ...window.ScenarioManager.state,
        id: window.PRIMARY_SCENARIO.id,
        sessionId: window.PRIMARY_SCENARIO.sessionId,
        selectedDeliverables: new Set(window.PRIMARY_SCENARIO.selectedDeliverables),
        selectedComponents: window.PRIMARY_SCENARIO.selectedComponents,
        selectedL2Tasks: window.PRIMARY_SCENARIO.selectedL2Tasks,
        deliverables: window.PRIMARY_SCENARIO.deliverables,
        totals: window.PRIMARY_SCENARIO.totals
      };
      
      // Subscribe to ScenarioManager changes
      window.ScenarioManager.subscribe((state) => {
        console.log('[ScenarioDataManager] ScenarioManager changed, updating PRIMARY_SCENARIO');
        
        // Update PRIMARY_SCENARIO from ScenarioManager
        window.PRIMARY_SCENARIO.selectedDeliverables = Array.from(state.selectedDeliverables || []);
        window.PRIMARY_SCENARIO.selectedComponents = state.selectedComponents || window.PRIMARY_SCENARIO.selectedComponents;
        window.PRIMARY_SCENARIO.selectedL2Tasks = state.selectedL2Tasks || window.PRIMARY_SCENARIO.selectedL2Tasks;
        window.PRIMARY_SCENARIO.deliverables = state.deliverables || window.PRIMARY_SCENARIO.deliverables;
        window.PRIMARY_SCENARIO.totals = state.totals || window.PRIMARY_SCENARIO.totals;
        window.PRIMARY_SCENARIO.updatedAt = new Date().toISOString();
        
        this.saveToStorage();
      });
    },
    
    // Sync all systems
    sync() {
      // Sync with ScenarioStore
      if (window.ScenarioStore) {
        window.ScenarioStore.state = {
          ...window.ScenarioStore.state,
          deliverables: window.PRIMARY_SCENARIO.deliverables,
          totals: window.PRIMARY_SCENARIO.totals,
          blendedRate: window.PRIMARY_SCENARIO.blendedRate,
          hoursPerDay: window.PRIMARY_SCENARIO.hoursPerDay
        };
        window.ScenarioStore.emit();
      }
      
      // Sync with ScenarioManager
      if (window.ScenarioManager) {
        window.ScenarioManager.state = {
          ...window.ScenarioManager.state,
          selectedDeliverables: new Set(window.PRIMARY_SCENARIO.selectedDeliverables),
          selectedComponents: window.PRIMARY_SCENARIO.selectedComponents,
          selectedL2Tasks: window.PRIMARY_SCENARIO.selectedL2Tasks,
          deliverables: window.PRIMARY_SCENARIO.deliverables,
          totals: window.PRIMARY_SCENARIO.totals
        };
        window.ScenarioManager.emit();
      }
    },
    
    // Save to localStorage
    saveToStorage() {
      try {
        const key = `apb.primary_scenario.${window.PRIMARY_SCENARIO.sessionId}`;
        localStorage.setItem(key, JSON.stringify(window.PRIMARY_SCENARIO));
        console.log('[ScenarioDataManager] Saved to localStorage');
      } catch (error) {
        console.error('[ScenarioDataManager] Error saving to localStorage:', error);
      }
    },
    
    // Load from localStorage
    loadFromStorage() {
      try {
        const sessionId = window.PRIMARY_SCENARIO.sessionId;
        if (!sessionId) return;
        
        const key = `apb.primary_scenario.${sessionId}`;
        const stored = localStorage.getItem(key);
        
        if (stored) {
          const data = JSON.parse(stored);
          window.PRIMARY_SCENARIO = {
            ...window.PRIMARY_SCENARIO,
            ...data
          };
          console.log('[ScenarioDataManager] Loaded from localStorage');
        }
      } catch (error) {
        console.error('[ScenarioDataManager] Error loading from localStorage:', error);
      }
    },
    
    // Clear scenario data
    clear() {
      console.log('[ScenarioDataManager] Clearing PRIMARY_SCENARIO...');
      
      // Reset to defaults
      window.PRIMARY_SCENARIO = {
        id: null,
        sessionId: null,
        createdAt: null,
        updatedAt: null,
        rfpText: '',
        analysisMode: 'fast',
        analysisResults: null,
        deliverables: [],
        selectedDeliverables: [],
        selectedComponents: {},
        selectedL2Tasks: {},
        pricing: {},
        retainerAnalysis: null,
        projectType: 'project',
        blendedRate: 195,
        hoursPerDay: 6,
        totals: {
          hours: 0,
          oneTimeCost: 0,
          monthlyHours: 0,
          monthlyCost: 0,
          grandTotal12: 0
        },
        timeline: null,
        ganttData: null,
        timelineReasoning: null,
        startDate: new Date().toISOString().split('T')[0],
        exportHistory: [],
        status: 'draft',
        projectName: '',
        clientName: '',
        version: '1.0',
        notes: ''
      };
      
      // Clear from storage
      if (window.PRIMARY_SCENARIO.sessionId) {
        const key = `apb.primary_scenario.${window.PRIMARY_SCENARIO.sessionId}`;
        localStorage.removeItem(key);
      }
      
      // Clear other stores
      if (window.ScenarioStore) {
        window.ScenarioStore.state.deliverables = [];
        window.ScenarioStore.recompute();
        window.ScenarioStore.emit();
      }
      
      if (window.ScenarioManager) {
        window.ScenarioManager.state.selectedDeliverables = new Set();
        window.ScenarioManager.state.selectedComponents = {};
        window.ScenarioManager.state.selectedL2Tasks = {};
        window.ScenarioManager.emit();
      }
    },
    
    // Emit update event
    emitUpdate() {
      document.dispatchEvent(new CustomEvent('primary-scenario:updated', {
        detail: window.PRIMARY_SCENARIO
      }));
    },
    
    // Generate session ID
    generateSessionId() {
      if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
      }
      return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },
    
    // Export scenario for backend
    exportForBackend() {
      return {
        session_id: window.PRIMARY_SCENARIO.sessionId,
        scenario: window.PRIMARY_SCENARIO,
        timestamp: new Date().toISOString()
      };
    },
    
    // Import scenario from backend
    importFromBackend(data) {
      if (data && data.scenario) {
        window.PRIMARY_SCENARIO = {
          ...window.PRIMARY_SCENARIO,
          ...data.scenario
        };
        
        this.sync();
        this.saveToStorage();
        this.emitUpdate();
      }
    }
  };
  
  // Export to global scope
  window.ScenarioDataManager = ScenarioDataManager;
  
  // Auto-initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      // Check for existing session or create new one
      const sessionId = window.SessionManager?.getCurrentSessionId() || 
                       localStorage.getItem('apb.currentSession');
      ScenarioDataManager.init(sessionId);
    });
  } else {
    const sessionId = window.SessionManager?.getCurrentSessionId() || 
                     localStorage.getItem('apb.currentSession');
    ScenarioDataManager.init(sessionId);
  }
  
  console.log('[ScenarioDataManager] Module loaded');
})();