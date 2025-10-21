// buttonManager.js
// Centralized button event listener management with error boundaries
// Ensures all buttons are properly wired and functional

(function() {
  'use strict';

  // Button Manager handles all button event listeners
  const ButtonManager = {
    // Map of button selectors to their handlers
    buttons: {
      // Step 1 - Upload & Analysis
      '#mode-fast': {
        event: 'click',
        handler: () => ButtonHandlers.setAnalysisMode('fast'),
        description: 'Fast Mode Analysis'
      },
      '#mode-deep': {
        event: 'click', 
        handler: () => ButtonHandlers.setAnalysisMode('deep'),
        description: 'Deep Mode Analysis'
      },
      '#btnAnalyze': {
        event: 'click',
        handler: () => ButtonHandlers.runAnalysis(),
        description: 'Analyze with AI'
      },
      
      // Step 2 - Deliverable Selection
      '#btn-proceed-pricing': {
        event: 'click',
        handler: () => ButtonHandlers.proceedToPricing(),
        description: 'Proceed to Pricing'
      },
      '#btn-learn': {
        event: 'click',
        handler: () => ButtonHandlers.openDocumentation(),
        description: 'LEARN Documentation'
      },
      '#btn-apply-smart-selection': {
        event: 'click',
        handler: () => ButtonHandlers.applySmartSelection(),
        description: 'Apply Smart Selection'
      },
      
      // Step 3 - Pricing Configuration
      '#btn-ai-suggest-type': {
        event: 'click',
        handler: () => ButtonHandlers.analyzeProjectRetainer(),
        description: 'AI Suggest Type'
      },
      '#btn-global-retainer-suggest': {
        event: 'click',
        handler: () => ButtonHandlers.suggestRetainerItems(),
        description: 'AI Suggest Retainer Items'
      },
      '#btn-ai-optimize-pricing': {
        event: 'click',
        handler: () => ButtonHandlers.optimizeAllPricing(),
        description: 'Optimize All Pricing'
      },
      '#btn-update-pricing': {
        event: 'click',
        handler: () => ButtonHandlers.updatePricing(),
        description: 'Update Pricing'
      },
      
      // Step 4 - Timeline Generation
      '#btn-generate-timeline': {
        event: 'click',
        handler: () => ButtonHandlers.generateAITimeline(),
        description: 'Generate AI Timeline'
      },
      '#btn-toggle-reasoning': {
        event: 'click',
        handler: () => ButtonHandlers.toggleReasoning(),
        description: 'Toggle AI Reasoning'
      },
      '#btn-optimize-timeline': {
        event: 'click',
        handler: () => ButtonHandlers.optimizeTimeline(),
        description: 'Optimize Timeline'
      },
      
      // Step 5 - Export
      '#btnExportA': {
        event: 'click',
        handler: () => ButtonHandlers.exportExcel(),
        description: 'Export to Excel'
      },
      '#btn-export-xml': {
        event: 'click',
        handler: () => ButtonHandlers.exportXML(),
        description: 'Export to XML'
      },
      '#btn-final-ship-project': {
        event: 'click',
        handler: () => ButtonHandlers.finalShipProject(),
        description: 'Final Ship Project'
      }
    },
    
    // Initialize all button event listeners
    init() {
      console.log('[ButtonManager] Initializing button event listeners...');
      
      // Wait for DOM to be ready
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.attachListeners());
      } else {
        this.attachListeners();
      }
      
      // Re-attach listeners when steps are shown
      document.addEventListener('step:shown', (event) => {
        console.log(`[ButtonManager] Step shown: ${event.detail?.step}`);
        setTimeout(() => this.attachListeners(), 100);
      });
    },
    
    // Attach event listeners to all buttons
    attachListeners() {
      let attached = 0;
      let missing = 0;
      
      for (const [selector, config] of Object.entries(this.buttons)) {
        const element = document.querySelector(selector);
        
        if (element) {
          // Remove any existing listener first
          element.replaceWith(element.cloneNode(true));
          const newElement = document.querySelector(selector);
          
          // Add new listener with error boundary
          newElement.addEventListener(config.event, (event) => {
            event.preventDefault();
            event.stopPropagation();
            
            console.log(`[ButtonManager] ${config.description} clicked`);
            
            try {
              config.handler(event);
            } catch (error) {
              console.error(`[ButtonManager] Error in ${config.description}:`, error);
              this.showError(config.description, error);
            }
          });
          
          // Mark button as wired
          newElement.classList.add('button-wired');
          newElement.dataset.buttonDescription = config.description;
          attached++;
        } else {
          missing++;
          console.debug(`[ButtonManager] Button not found: ${selector} (${config.description})`);
        }
      }
      
      console.log(`[ButtonManager] Attached ${attached} listeners, ${missing} buttons not yet in DOM`);
    },
    
    // Show error message to user
    showError(action, error) {
      const message = `Error in ${action}: ${error.message || 'Unknown error'}`;
      
      // Show in UI if available
      if (window.showNotification) {
        window.showNotification(message, 'error');
      } else {
        alert(message);
      }
      
      // Log to console
      console.error(`[ButtonManager] ${message}`, error);
    }
  };
  
  // Button Handlers - Actual functionality for each button
  const ButtonHandlers = {
    // Step 1 Handlers
    setAnalysisMode(mode) {
      console.log(`[ButtonHandlers] Setting analysis mode to: ${mode}`);
      
      // Update PRIMARY_SCENARIO
      window.PRIMARY_SCENARIO = window.PRIMARY_SCENARIO || {};
      window.PRIMARY_SCENARIO.analysisMode = mode;
      
      // Update other state variables for backward compatibility
      window.selectedAnalysisMode = mode;
      
      // Update hidden input
      const modeInput = document.getElementById('analysis-mode');
      if (modeInput) modeInput.value = mode;
      
      // Update AI Assistant state if it exists
      if (window.aiAssistant && window.aiAssistant.agentState) {
        window.aiAssistant.agentState.analysisMode = mode;
      }
      
      // Update UI with proper visual feedback
      const fastBtn = document.getElementById('mode-fast');
      const deepBtn = document.getElementById('mode-deep');
      
      if (mode === 'fast') {
        // Fast mode active
        if (fastBtn) {
          fastBtn.style.background = '#10b981';
          fastBtn.style.color = 'white';
          fastBtn.style.borderColor = '#10b981';
        }
        if (deepBtn) {
          deepBtn.style.background = 'white';
          deepBtn.style.color = '#6366f1';
          deepBtn.style.borderColor = '#6366f1';
        }
      } else {
        // Deep mode active
        if (deepBtn) {
          deepBtn.style.background = '#6366f1';
          deepBtn.style.color = 'white';
          deepBtn.style.borderColor = '#6366f1';
        }
        if (fastBtn) {
          fastBtn.style.background = 'white';
          fastBtn.style.color = '#10b981';
          fastBtn.style.borderColor = '#10b981';
        }
      }
      
      // Store in localStorage
      localStorage.setItem('apb.analysisMode', mode);
      
      console.log('[ButtonHandlers] Analysis mode set successfully');
    },
    
    async runAnalysis() {
      console.log('[ButtonHandlers] Running RFP analysis...');
      
      // Get RFP text from multiple sources
      const rfpText = document.querySelector('#rfpText')?.value || 
                     document.querySelector('#rfp-text')?.value || 
                     window.PRIMARY_SCENARIO?.rfpText || '';
      
      // Check if we have staged files
      const hasStagedFiles = window.FileStagingModule?.state?.files?.length > 0;
      
      // Only show error if we have neither text nor files
      if (!rfpText.trim() && !hasStagedFiles) {
        alert('Please enter RFP text or upload a document first');
        return;
      }
      
      // Debug logging to help diagnose validation issues
      console.log('[VALIDATION] RFP text length:', rfpText.trim().length);
      console.log('[VALIDATION] Staged files:', hasStagedFiles);
      console.log('[VALIDATION] PRIMARY_SCENARIO.rfpText length:', window.PRIMARY_SCENARIO?.rfpText?.length || 0);
      console.log('[VALIDATION] ✅ Validation passed, starting analysis');
      
      // Defer heavy operations to next tick to avoid blocking
      setTimeout(() => {
        try {
          // Initialize PRIMARY_SCENARIO safely without spreading huge objects
          if (!window.PRIMARY_SCENARIO) {
            window.PRIMARY_SCENARIO = {};
          }
          window.PRIMARY_SCENARIO.rfpText = rfpText;
          window.PRIMARY_SCENARIO.analysisMode = window.PRIMARY_SCENARIO?.analysisMode || 'fast';
          window.PRIMARY_SCENARIO.sessionId = window.SessionManager?.getCurrentSessionId() || generateSessionId();
          window.PRIMARY_SCENARIO.createdAt = new Date().toISOString();
          window.PRIMARY_SCENARIO.status = 'analyzing';
          
          // Call the analysis function
          if (typeof window.onRunReconcile === 'function') {
            window.onRunReconcile();
          } else {
            console.error('[ButtonHandlers] onRunReconcile function not found');
            // Fallback: trigger analysis directly
            this.triggerAnalysis();
          }
        } catch (error) {
          console.error('[ButtonHandlers] Error during analysis:', error);
          alert('Error starting analysis. Please refresh and try again.');
          
          // Reset button state
          const button = document.querySelector('#btnAnalyze');
          if (button) {
            button.disabled = false;
            button.textContent = 'Analyze with AI';
          }
        }
      }, 10);
    },
    
    triggerAnalysis() {
      const mode = window.PRIMARY_SCENARIO?.analysisMode || 'fast';
      const rfpText = window.PRIMARY_SCENARIO?.rfpText || '';
      
      // Show loading state
      const button = document.querySelector('#btnAnalyze');
      const originalText = button?.textContent;
      if (button) {
        button.disabled = true;
        button.textContent = 'Analyzing...';
      }
      
      // Make API call
      fetch('/api/ai/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rfp_text: rfpText,
          analysis_mode: mode,
          session_id: window.PRIMARY_SCENARIO.sessionId
        })
      })
      .then(response => response.json())
      .then(data => {
        console.log('[ButtonHandlers] Analysis complete:', data);
        
        // Update PRIMARY_SCENARIO
        window.PRIMARY_SCENARIO = {
          ...window.PRIMARY_SCENARIO,
          analysisResults: data,
          deliverables: data.deliverables || [],
          status: 'analyzed',
          updatedAt: new Date().toISOString()
        };
        
        // Move to Step 2
        if (typeof window.showStep === 'function') {
          window.showStep(2);
        }
      })
      .catch(error => {
        console.error('[ButtonHandlers] Analysis error:', error);
        alert('Analysis failed. Please try again.');
      })
      .finally(() => {
        if (button) {
          button.disabled = false;
          button.textContent = originalText;
        }
      });
    },
    
    // Step 2 Handlers
    async proceedToPricing() {
      console.log('[ButtonHandlers] Proceeding to pricing...');
      
      try {
        // Use the proper buildFromCurrentSelection function which has all the logic
        if (typeof window.buildFromCurrentSelection === 'function') {
          await window.buildFromCurrentSelection();
        } else {
          // Fallback: ensure we have selections
          const selectedDeliverables = window.PRIMARY_SCENARIO?.selectedDeliverables || [];
          if (selectedDeliverables.length === 0) {
            alert('Please select at least one deliverable before proceeding');
            return;
          }
          
          // Update PRIMARY_SCENARIO status
          if (window.PRIMARY_SCENARIO) {
            window.PRIMARY_SCENARIO.status = 'pricing';
            window.PRIMARY_SCENARIO.step2CompletedAt = new Date().toISOString();
          }
          
          // Move to Step 3 with proper null checks
          const step2 = document.querySelector('#step2');
          const step3 = document.querySelector('#step3');
          
          if (step2 && step3) {
            step2.style.display = 'none';
            step3.style.display = 'block';
          } else {
            console.error('[ButtonHandlers] Step elements not found');
            alert('Unable to navigate to pricing. Please refresh the page.');
          }
        }
      } catch (error) {
        console.error('[ButtonHandlers] Error in proceedToPricing:', error);
        alert('An error occurred while proceeding to pricing. Please try again.');
      }
    },
    
    openDocumentation() {
      console.log('[ButtonHandlers] Opening documentation...');
      window.open('/docs/user-guide.html', '_blank');
    },
    
    async applySmartSelection() {
      console.log('[ButtonHandlers] Applying smart selection...');
      
      try {
        if (typeof window.applySmartSelection === 'function') {
          await window.applySmartSelection();
        } else {
          console.error('[ButtonHandlers] applySmartSelection function not found');
          alert('Smart selection feature is not available. Please try refreshing the page.');
        }
      } catch (error) {
        console.error('[ButtonHandlers] Error in applySmartSelection:', error);
        alert('An error occurred while applying smart selection. Please try again.');
      }
    },
    
    // Step 3 Handlers
    analyzeProjectRetainer() {
      console.log('[ButtonHandlers] Analyzing project vs retainer...');
      
      if (typeof window.analyzeProjectRetainer === 'function') {
        window.analyzeProjectRetainer();
      } else {
        // Make API call directly
        fetch('/api/analyze-retainer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scenario: window.PRIMARY_SCENARIO
          })
        })
        .then(response => response.json())
        .then(data => {
          console.log('[ButtonHandlers] Retainer analysis complete:', data);
          window.PRIMARY_SCENARIO.retainerAnalysis = data;
          // Update UI with recommendations
          this.applyRetainerRecommendations(data);
        });
      }
    },
    
    suggestRetainerItems() {
      console.log('[ButtonHandlers] Suggesting retainer items...');
      
      const deliverables = window.PRIMARY_SCENARIO?.deliverables || [];
      const retainerCandidates = deliverables.filter(d => 
        d.frequency === 'recurring' || 
        d.type === 'ongoing' ||
        d.name?.toLowerCase().includes('monthly') ||
        d.name?.toLowerCase().includes('ongoing')
      );
      
      console.log('[ButtonHandlers] Found retainer candidates:', retainerCandidates);
      
      // Update UI to show suggestions
      retainerCandidates.forEach(d => {
        const row = document.querySelector(`[data-deliverable-id="${d.id}"]`);
        if (row) {
          row.classList.add('retainer-suggested');
        }
      });
    },
    
    optimizeAllPricing() {
      console.log('[ButtonHandlers] Optimizing all pricing...');
      
      if (typeof window.optimizeAllPricing === 'function') {
        window.optimizeAllPricing();
      } else {
        // Make API call directly
        fetch('/api/optimize-pricing', {
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scenario: window.PRIMARY_SCENARIO
          })
        })
        .then(response => response.json())
        .then(data => {
          console.log('[ButtonHandlers] Pricing optimized:', data);
          window.PRIMARY_SCENARIO.pricing = data.pricing;
          window.PRIMARY_SCENARIO.totals = data.totals;
          // Update UI
          this.refreshPricingTable();
        });
      }
    },
    
    updatePricing() {
      console.log('[ButtonHandlers] Updating pricing...');
      
      // Collect pricing data from UI
      const pricingData = this.collectPricingData();
      
      // Update PRIMARY_SCENARIO
      window.PRIMARY_SCENARIO.pricing = pricingData;
      window.PRIMARY_SCENARIO.pricingUpdatedAt = new Date().toISOString();
      
      // Save to backend
      if (window.ScenarioManager?.saveToBackend) {
        window.ScenarioManager.saveToBackend();
      }
      
      console.log('[ButtonHandlers] Pricing updated successfully');
    },
    
    // Step 4 Handlers
    generateAITimeline() {
      console.log('[ButtonHandlers] Generating AI timeline...');
      
      if (typeof window.generateAITimeline === 'function') {
        window.generateAITimeline();
      } else {
        // Make API call directly
        const button = document.querySelector('#btn-generate-timeline');
        const originalText = button?.textContent;
        
        if (button) {
          button.disabled = true;
          button.textContent = 'Generating...';
        }
        
        fetch('/api/generate-timeline', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scenario: window.PRIMARY_SCENARIO
          })
        })
        .then(response => response.json())
        .then(data => {
          console.log('[ButtonHandlers] Timeline generated:', data);
          window.PRIMARY_SCENARIO.timeline = data.timeline;
          window.PRIMARY_SCENARIO.ganttData = data.ganttData;
          // Render timeline
          if (typeof window.renderGanttChart === 'function') {
            window.renderGanttChart(data.ganttData);
          }
        })
        .finally(() => {
          if (button) {
            button.disabled = false;
            button.textContent = originalText;
          }
        });
      }
    },
    
    toggleReasoning() {
      console.log('[ButtonHandlers] Toggling AI reasoning panel...');
      
      const reasoningPanel = document.querySelector('#reasoning-panel, .reasoning-sidebar');
      if (reasoningPanel) {
        reasoningPanel.classList.toggle('visible');
      } else {
        console.warn('[ButtonHandlers] Reasoning panel not found');
      }
    },
    
    optimizeTimeline() {
      console.log('[ButtonHandlers] Optimizing timeline...');
      
      if (typeof window.optimizeTimeline === 'function') {
        window.optimizeTimeline();
      }
    },
    
    // Step 5 Handlers
    exportExcel() {
      console.log('[ButtonHandlers] Exporting to Excel...');
      
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `export_${timestamp}.xlsx`;
      
      fetch('/api/export/excel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario: window.PRIMARY_SCENARIO
        })
      })
      .then(response => response.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
        console.log('[ButtonHandlers] Excel export complete');
      })
      .catch(error => {
        console.error('[ButtonHandlers] Excel export error:', error);
        alert('Export failed. Please try again.');
      });
    },
    
    exportXML() {
      console.log('[ButtonHandlers] Exporting to XML...');
      
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `export_${timestamp}.xml`;
      
      fetch('/api/export/xml', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario: window.PRIMARY_SCENARIO
        })
      })
      .then(response => response.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
        console.log('[ButtonHandlers] XML export complete');
      })
      .catch(error => {
        console.error('[ButtonHandlers] XML export error:', error);
        alert('Export failed. Please try again.');
      });
    },
    
    finalShipProject() {
      console.log('[ButtonHandlers] Final ship project...');
      
      // Confirm with user
      if (!confirm('This will lock the project and export all data. Continue?')) {
        return;
      }
      
      // Update status
      window.PRIMARY_SCENARIO.status = 'shipped';
      window.PRIMARY_SCENARIO.shippedAt = new Date().toISOString();
      
      // Export all formats
      Promise.all([
        this.exportExcel(),
        this.exportXML()
      ]).then(() => {
        console.log('[ButtonHandlers] Project shipped successfully');
        alert('Project has been shipped successfully!');
        
        // Lock UI
        document.querySelectorAll('input, button, select, textarea').forEach(el => {
          el.disabled = true;
        });
      });
    },
    
    // Helper methods
    collectPricingData() {
      const pricingData = {};
      
      document.querySelectorAll('[data-deliverable-id]').forEach(row => {
        const id = row.dataset.deliverableId;
        const hours = parseFloat(row.querySelector('[data-field="hours"]')?.value) || 0;
        const rate = parseFloat(row.querySelector('[data-field="rate"]')?.value) || 195;
        
        pricingData[id] = {
          hours,
          rate,
          price: hours * rate
        };
      });
      
      return pricingData;
    },
    
    refreshPricingTable() {
      if (typeof window.refreshPricingTable === 'function') {
        window.refreshPricingTable();
      }
    },
    
    applyRetainerRecommendations(data) {
      // Apply recommendations to UI
      if (data.recommendations) {
        data.recommendations.forEach(rec => {
          const row = document.querySelector(`[data-deliverable-id="${rec.deliverableId}"]`);
          if (row) {
            const typeSelect = row.querySelector('[data-field="type"]');
            if (typeSelect) {
              typeSelect.value = rec.suggestedType;
            }
          }
        });
      }
    }
  };
  
  // Helper function for session ID generation
  function generateSessionId() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }
  
  // Export to global scope
  window.ButtonManager = ButtonManager;
  window.ButtonHandlers = ButtonHandlers;
  
  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => ButtonManager.init());
  } else {
    ButtonManager.init();
  }
  
  console.log('[ButtonManager] Module loaded');
})();