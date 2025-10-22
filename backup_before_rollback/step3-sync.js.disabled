// step3-sync.js
// Real-time sync integration for Step 3 (Pricing)

(function() {
  // Wait for dependencies
  function initStep3Sync() {
    if (!window.ScenarioManager || !window.ScenarioStore) {
      setTimeout(initStep3Sync, 100);
      return;
    }
    
    console.log('[Step3 Sync] Initializing real-time sync for pricing');
    
    // Store original render functions
    const originalRenderScenario = window.renderScenario;
    const originalUpdatePricingTable = window.updatePricingTable;
    
    // Track if we're currently rendering to prevent loops
    let isRendering = false;
    
    // Subscribe to ScenarioManager changes
    const unsubscribe = window.ScenarioManager.subscribe((state) => {
      console.log('[Step3 Sync] Received state update');
      
      // Check if we're on Step 3
      const step3Element = document.getElementById('step3');
      if (!step3Element || step3Element.style.display === 'none') {
        return; // Step 3 not visible
      }
      
      // Skip if we're already rendering
      if (isRendering) return;
      
      // Update pricing table
      updatePricingFromSync(state);
    });
    
    // Store unsubscribe for cleanup
    window.step3SyncUnsubscribe = unsubscribe;
    
    // Also subscribe to ScenarioStore for immediate updates
    window.ScenarioStore.subscribe((state) => {
      if (isRendering) return;
      
      const step3Element = document.getElementById('step3');
      if (!step3Element || step3Element.style.display === 'none') {
        return;
      }
      
      // Update the pricing display
      if (typeof window.APBOneTable !== 'undefined' && window.APBOneTable.hydrateFrom) {
        window.APBOneTable.hydrateFrom(state);
      }
    });
    
    // Listen for external change events
    document.addEventListener('scenario:external-change', (event) => {
      console.log('[Step3 Sync] External change detected:', event.detail);
      
      if (isRendering) return;
      
      // Refresh pricing table
      refreshPricingTable(event.detail.changedElements);
    });
    
    // Listen for pricing changes to sync back
    document.addEventListener('pricing:changed', (event) => {
      console.log('[Step3 Sync] Pricing changed locally:', event.detail);
      
      // Update ScenarioManager with new pricing
      if (window.ScenarioManager && event.detail.deliverableId) {
        window.ScenarioManager.updatePricing(event.detail.deliverableId, {
          hours: event.detail.hours,
          rate: event.detail.rate,
          months: event.detail.months,
          cadence: event.detail.cadence
        });
      }
    });
    
    // Override renderScenario to add sync
    window.renderScenario = function(scenario) {
      console.log('[Step3 Sync] Rendering scenario with sync');
      isRendering = true;
      
      try {
        // Call original render
        if (originalRenderScenario) {
          originalRenderScenario.call(this, scenario);
        }
        
        // Sync with ScenarioManager
        if (window.ScenarioManager && scenario) {
          window.ScenarioManager.updateDeliverablesFromAPI({ scenario });
        }
      } finally {
        isRendering = false;
      }
    };
    
    console.log('[Step3 Sync] Initialized successfully');
  }
  
  // Update pricing from sync state
  function updatePricingFromSync(state) {
    console.log('[Step3 Sync] Updating pricing from sync');
    
    if (!state.deliverables || state.deliverables.length === 0) return;
    
    // Get the pricing table container
    const pricingContainer = document.querySelector('#pricing-table-container, .pricing-container, #step3 .content');
    if (!pricingContainer) return;
    
    // Flash the container to indicate update
    pricingContainer.classList.add('sync-flash');
    setTimeout(() => pricingContainer.classList.remove('sync-flash'), 500);
    
    // Update each deliverable row
    state.deliverables.forEach(deliverable => {
      updateDeliverableRow(deliverable);
    });
    
    // Update totals
    updatePricingTotals(state.totals);
    
    // Show sync notification
    showPricingSyncNotification();
  }
  
  // Update individual deliverable row
  function updateDeliverableRow(deliverable) {
    const rowId = `pricing-row-${deliverable.id}`;
    const row = document.getElementById(rowId) || 
                document.querySelector(`[data-deliverable-id="${deliverable.id}"]`);
    
    if (!row) return;
    
    // Update hours
    const hoursInput = row.querySelector('input[data-field="hours"]');
    if (hoursInput && hoursInput.value != deliverable.hours) {
      hoursInput.value = deliverable.hours || 0;
      hoursInput.classList.add('sync-flash');
      setTimeout(() => hoursInput.classList.remove('sync-flash'), 500);
    }
    
    // Update rate
    const rateInput = row.querySelector('input[data-field="rate"]');
    if (rateInput && rateInput.value != deliverable.rate) {
      rateInput.value = deliverable.rate || 195;
      rateInput.classList.add('sync-flash');
      setTimeout(() => rateInput.classList.remove('sync-flash'), 500);
    }
    
    // Update price display
    const priceElement = row.querySelector('.price-display, [data-field="price"]');
    if (priceElement) {
      const price = deliverable.price || 0;
      priceElement.textContent = `$${price.toLocaleString()}`;
    }
    
    // Update cadence if retainer
    if (deliverable.cadence && deliverable.cadence !== 'One-Time') {
      const cadenceElement = row.querySelector('.cadence-display');
      if (cadenceElement) {
        cadenceElement.textContent = `${deliverable.cadence} (${deliverable.months}m)`;
      }
    }
  }
  
  // Update pricing totals
  function updatePricingTotals(totals) {
    if (!totals) return;
    
    // Update total hours
    const hoursElement = document.querySelector('#pricing-total-hours, .total-hours');
    if (hoursElement) {
      hoursElement.textContent = `${totals.hours || 0} hours`;
    }
    
    // Update one-time cost
    const oneTimeElement = document.querySelector('#pricing-onetime-cost, .onetime-cost');
    if (oneTimeElement) {
      oneTimeElement.textContent = `$${(totals.oneTimeCost || 0).toLocaleString()}`;
    }
    
    // Update monthly cost
    const monthlyElement = document.querySelector('#pricing-monthly-cost, .monthly-cost');
    if (monthlyElement) {
      monthlyElement.textContent = `$${(totals.monthlyCost || 0).toLocaleString()}`;
    }
    
    // Update grand total
    const grandTotalElement = document.querySelector('#pricing-grand-total, .grand-total');
    if (grandTotalElement) {
      grandTotalElement.textContent = `$${(totals.grandTotal12 || 0).toLocaleString()}`;
      grandTotalElement.classList.add('sync-flash');
      setTimeout(() => grandTotalElement.classList.remove('sync-flash'), 500);
    }
  }
  
  // Refresh pricing table for specific elements
  function refreshPricingTable(changedElements) {
    if (!changedElements || !Array.isArray(changedElements)) return;
    
    changedElements.forEach(element => {
      if (element.type === 'deliverable' && element.id) {
        // Find and update the specific deliverable
        const deliverable = window.ScenarioManager?.state?.deliverables?.find(d => d.id === element.id);
        if (deliverable) {
          updateDeliverableRow(deliverable);
        }
      }
    });
    
    // Recalculate totals
    if (window.ScenarioStore && typeof window.ScenarioStore.recompute === 'function') {
      window.ScenarioStore.recompute();
    }
  }
  
  // Show pricing sync notification
  function showPricingSyncNotification() {
    let notification = document.getElementById('pricing-sync-notification');
    if (!notification) {
      notification = document.createElement('div');
      notification.id = 'pricing-sync-notification';
      notification.style.cssText = `
        position: fixed;
        top: 60px;
        right: 20px;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
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
    
    notification.textContent = '✓ Pricing synced';
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
  
  // Initialize when ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initStep3Sync);
  } else {
    initStep3Sync();
  }
  
  console.log('[Step3 Sync] Module loaded');
})();