// primary-scenario-integration.js
// Integrates existing functions with PRIMARY_SCENARIO

(function() {
  'use strict';

  // Wait for dependencies
  function initIntegration() {
    if (!window.ScenarioDataManager || !window.ButtonManager) {
      setTimeout(initIntegration, 100);
      return;
    }
    
    console.log('[Integration] Initializing PRIMARY_SCENARIO integration...');
    
    // Hook into existing onRunReconcile function
    const originalOnRunReconcile = window.onRunReconcile;
    if (originalOnRunReconcile) {
      window.onRunReconcile = async function() {
        console.log('[Integration] onRunReconcile called, updating PRIMARY_SCENARIO');
        
        // Update PRIMARY_SCENARIO with RFP text
        const rfpText = document.querySelector('#rfpText')?.value || 
                       document.querySelector('#rfp-text')?.value || '';
        
        window.ScenarioDataManager.updateAnalysis({
          rfpText: rfpText,
          analysisMode: window.PRIMARY_SCENARIO?.analysisMode || 'fast'
        });
        
        // Call original function
        const result = await originalOnRunReconcile.apply(this, arguments);
        
        // Update PRIMARY_SCENARIO with results
        if (result) {
          window.ScenarioDataManager.updateAnalysis({
            analysisResults: result,
            deliverables: result.deliverables || []
          });
        }
        
        return result;
      };
    }
    
    // Hook into analyzeProjectRetainer
    const originalAnalyzeProjectRetainer = window.analyzeProjectRetainer;
    if (originalAnalyzeProjectRetainer) {
      window.analyzeProjectRetainer = async function() {
        console.log('[Integration] analyzeProjectRetainer called');
        
        const result = await originalAnalyzeProjectRetainer.apply(this, arguments);
        
        // Update PRIMARY_SCENARIO
        if (result) {
          window.ScenarioDataManager.updatePricing({
            retainerAnalysis: result
          });
        }
        
        return result;
      };
    }
    
    // Hook into optimizeAllPricing
    const originalOptimizeAllPricing = window.optimizeAllPricing;
    if (originalOptimizeAllPricing) {
      window.optimizeAllPricing = async function() {
        console.log('[Integration] optimizeAllPricing called');
        
        const result = await originalOptimizeAllPricing.apply(this, arguments);
        
        // Update PRIMARY_SCENARIO
        if (result) {
          window.ScenarioDataManager.updatePricing({
            pricing: result.pricing,
            totals: result.totals
          });
        }
        
        return result;
      };
    }
    
    // Hook into generateAITimeline
    const originalGenerateAITimeline = window.generateAITimeline;
    if (originalGenerateAITimeline) {
      window.generateAITimeline = async function() {
        console.log('[Integration] generateAITimeline called');
        
        const result = await originalGenerateAITimeline.apply(this, arguments);
        
        // Update PRIMARY_SCENARIO
        if (result) {
          window.ScenarioDataManager.updateTimeline({
            timeline: result.timeline,
            ganttData: result.ganttData,
            timelineReasoning: result.reasoning
          });
        }
        
        return result;
      };
    }
    
    // Hook into applySmartSelection if it exists
    if (typeof window.applySmartSelection === 'function') {
      const originalApplySmartSelection = window.applySmartSelection;
      window.applySmartSelection = function() {
        console.log('[Integration] applySmartSelection called');
        
        const result = originalApplySmartSelection.apply(this, arguments);
        
        // Update PRIMARY_SCENARIO with selections
        const selectedCodes = window.appState?.selectedCodes || [];
        window.ScenarioDataManager.updateSelection({
          selectedDeliverables: selectedCodes
        });
        
        return result;
      };
    } else {
      // Create the function if it doesn't exist
      window.applySmartSelection = function() {
        console.log('[Integration] Creating applySmartSelection function');
        
        // Get selected deliverables from UI
        const selectedDeliverables = [];
        document.querySelectorAll('#step2 input[type="checkbox"]:checked[data-deliverable-code]').forEach(checkbox => {
          selectedDeliverables.push(checkbox.dataset.deliverableCode);
        });
        
        // Update PRIMARY_SCENARIO
        window.ScenarioDataManager.updateSelection({
          selectedDeliverables: selectedDeliverables
        });
        
        // Show notification
        if (window.showNotification) {
          window.showNotification(`Applied ${selectedDeliverables.length} deliverables`, 'success');
        }
        
        console.log('[Integration] Smart selection applied:', selectedDeliverables);
      };
    }
    
    // Hook into askAIForRetainerSuggestions if it exists
    if (typeof window.askAIForRetainerSuggestions === 'function') {
      const originalAskAIForRetainerSuggestions = window.askAIForRetainerSuggestions;
      window.askAIForRetainerSuggestions = async function() {
        console.log('[Integration] askAIForRetainerSuggestions called');
        
        const result = await originalAskAIForRetainerSuggestions.apply(this, arguments);
        
        // Update PRIMARY_SCENARIO
        if (result) {
          window.ScenarioDataManager.updatePricing({
            retainerSuggestions: result
          });
        }
        
        return result;
      };
    } else {
      // Create the function if it doesn't exist
      window.askAIForRetainerSuggestions = async function() {
        console.log('[Integration] Creating askAIForRetainerSuggestions function');
        
        // Call the ButtonHandler directly
        if (window.ButtonHandlers?.suggestRetainerItems) {
          window.ButtonHandlers.suggestRetainerItems();
        }
      };
    }
    
    // Sync SCENARIOS global with PRIMARY_SCENARIO
    Object.defineProperty(window, 'SCENARIOS', {
      get() {
        return {
          a: window.PRIMARY_SCENARIO,
          b: null // No version B anymore
        };
      },
      set(value) {
        if (value && value.a) {
          // Update PRIMARY_SCENARIO from SCENARIOS
          Object.assign(window.PRIMARY_SCENARIO, value.a);
          window.ScenarioDataManager.sync();
        }
      }
    });
    
    console.log('[Integration] PRIMARY_SCENARIO integration complete');
  }
  
  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initIntegration);
  } else {
    initIntegration();
  }
})();