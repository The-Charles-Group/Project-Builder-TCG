// step2-sync.js
// Real-time sync integration for Step 2 (Deliverable Selection)

(function() {
  // Wait for DOM and dependencies
  function initStep2Sync() {
    if (!window.ScenarioManager || !window.APB?.step2) {
      setTimeout(initStep2Sync, 100);
      return;
    }
    
    console.log('[Step2 Sync] Initializing real-time sync');
    
    // Subscribe to ScenarioManager changes
    const unsubscribe = window.ScenarioManager.subscribe((state) => {
      console.log('[Step2 Sync] Received state update');
      
      // Check if we're on Step 2
      const step2Element = document.getElementById('step2');
      if (!step2Element || step2Element.style.display === 'none') {
        return; // Step 2 not visible
      }
      
      // Update deliverable selections
      updateDeliverableSelections(state);
      
      // Update component selections
      updateComponentSelections(state);
      
      // Update counts and summaries
      updateStep2Summary(state);
      
      // Show sync notification
      showSyncNotification();
    });
    
    // Store unsubscribe for cleanup
    window.APB.step2.syncUnsubscribe = unsubscribe;
    
    // Listen for external change events
    document.addEventListener('scenario:external-change', (event) => {
      console.log('[Step2 Sync] External change detected:', event.detail);
      
      // Refresh Step 2 UI
      if (typeof refreshStep2UI === 'function') {
        refreshStep2UI();
      }
      
      // Flash updated deliverables
      flashUpdatedDeliverables(event.detail.changedElements);
    });
    
    // Listen for Step 2 being shown
    document.addEventListener('step2:shown', () => {
      console.log('[Step2 Sync] Step 2 shown, syncing with ScenarioManager');
      
      // Get current state and update UI
      const currentState = window.ScenarioManager.state;
      if (currentState) {
        updateDeliverableSelections(currentState);
        updateComponentSelections(currentState);
        updateStep2Summary(currentState);
      }
    });
    
    console.log('[Step2 Sync] Sync initialized successfully');
  }
  
  // Update deliverable checkbox selections
  function updateDeliverableSelections(state) {
    if (!state.selectedDeliverables || !window.APB.step2) return;
    
    const selectedCodes = state.selectedDeliverables;
    const checkboxes = document.querySelectorAll('#step2 input[type="checkbox"][data-deliverable-code]');
    
    checkboxes.forEach(checkbox => {
      const code = checkbox.dataset.deliverableCode;
      const shouldBeChecked = selectedCodes.has(code);
      
      if (checkbox.checked !== shouldBeChecked) {
        checkbox.checked = shouldBeChecked;
        
        // Update visual state
        const parent = checkbox.closest('.deliverable-item');
        if (parent) {
          parent.classList.toggle('selected', shouldBeChecked);
          
          // Flash to indicate external update
          parent.classList.add('sync-flash');
          setTimeout(() => parent.classList.remove('sync-flash'), 500);
        }
      }
    });
    
    // Update APB.step2 state
    window.APB.step2.selectedCodes = selectedCodes;
  }
  
  // Update component selections
  function updateComponentSelections(state) {
    if (!state.selectedComponents) return;
    
    // Update component checkboxes if component panel is open
    const componentPanel = document.querySelector('.components-panel');
    if (componentPanel && componentPanel.style.display !== 'none') {
      const activeDeliverable = window.APB.step2.activeDeliverableCode;
      
      if (activeDeliverable && state.selectedComponents[activeDeliverable]) {
        const selectedComponents = state.selectedComponents[activeDeliverable];
        const componentCheckboxes = componentPanel.querySelectorAll('input[type="checkbox"][data-component]');
        
        componentCheckboxes.forEach(checkbox => {
          const componentName = checkbox.dataset.component;
          const shouldBeChecked = selectedComponents.has(componentName);
          
          if (checkbox.checked !== shouldBeChecked) {
            checkbox.checked = shouldBeChecked;
            
            // Flash to indicate update
            const parent = checkbox.closest('.component-item');
            if (parent) {
              parent.classList.add('sync-flash');
              setTimeout(() => parent.classList.remove('sync-flash'), 500);
            }
          }
        });
      }
    }
    
    // Update APB.step2 component state
    window.APB.step2.selectedComponentsByCode = state.selectedComponents;
  }
  
  // Update Step 2 summary
  function updateStep2Summary(state) {
    // Update deliverable count
    const countElement = document.querySelector('#step2-deliverable-count');
    if (countElement) {
      const count = state.selectedDeliverables ? state.selectedDeliverables.size : 0;
      countElement.textContent = `${count} deliverables selected`;
    }
    
    // Update total hours if available
    const hoursElement = document.querySelector('#step2-total-hours');
    if (hoursElement && state.totals) {
      hoursElement.textContent = `${state.totals.hours || 0} hours`;
    }
    
    // Update total price if available
    const priceElement = document.querySelector('#step2-total-price');
    if (priceElement && state.totals) {
      const price = state.totals.grandTotal12 || 0;
      priceElement.textContent = `$${price.toLocaleString()}`;
    }
  }
  
  // Flash updated deliverables
  function flashUpdatedDeliverables(changedElements) {
    if (!changedElements || !Array.isArray(changedElements)) return;
    
    changedElements.forEach(element => {
      if (element.type === 'deliverable' && element.id) {
        const checkbox = document.querySelector(`input[data-deliverable-code="${element.id}"]`);
        if (checkbox) {
          const parent = checkbox.closest('.deliverable-item');
          if (parent) {
            parent.classList.add('sync-flash');
            setTimeout(() => parent.classList.remove('sync-flash'), 500);
          }
        }
      }
    });
  }
  
  // Show sync notification
  function showSyncNotification() {
    // Check if notification already exists
    let notification = document.getElementById('step2-sync-notification');
    if (!notification) {
      notification = document.createElement('div');
      notification.id = 'step2-sync-notification';
      notification.style.cssText = `
        position: fixed;
        top: 60px;
        right: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 10px 16px;
        border-radius: 6px;
        font-size: 14px;
        z-index: 1000;
        display: none;
        animation: slideIn 0.3s ease;
      `;
      document.body.appendChild(notification);
    }
    
    notification.textContent = '✓ Selections synced';
    notification.style.display = 'block';
    
    // Hide after 2 seconds
    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => {
        notification.style.display = 'none';
        notification.style.animation = 'slideIn 0.3s ease';
      }, 300);
    }, 2000);
  }
  
  // Refresh Step 2 UI (called from external)
  window.refreshStep2UI = function() {
    // Re-render deliverable panel if function exists
    if (typeof window.renderDeliverablesPanel === 'function') {
      window.renderDeliverablesPanel();
    }
    
    // Update summary
    const state = window.ScenarioManager?.state;
    if (state) {
      updateStep2Summary(state);
    }
  };
  
  // Initialize when ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initStep2Sync);
  } else {
    initStep2Sync();
  }
  
  console.log('[Step2 Sync] Module loaded');
})();