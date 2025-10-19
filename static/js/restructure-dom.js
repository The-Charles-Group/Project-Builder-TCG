// Restructure DOM to bypass carousel container
(function() {
  console.log('[RESTRUCTURE] Starting DOM restructure');
  
  function restructureSteps() {
    console.log('[RESTRUCTURE] Looking for steps to restructure...');
    
    // Find all steps
    const steps = [];
    for (let i = 1; i <= 5; i++) {
      const step = document.getElementById('step' + i);
      if (step) {
        steps.push(step);
        console.log('[RESTRUCTURE] Found step' + i);
      }
    }
    
    if (steps.length === 0) {
      console.log('[RESTRUCTURE] No steps found yet, will retry...');
      return false;
    }
    
    console.log('[RESTRUCTURE] Found ' + steps.length + ' steps');
    
    // Find or create a container for the steps
    let container = document.querySelector('main');
    if (!container) {
      container = document.body;
    }
    
    // Remove all steps from their current parents and add them directly to container
    steps.forEach(function(step, index) {
      // Clone the step to remove all event listeners and references
      const newStep = step.cloneNode(true);
      
      // Force visible styles
      newStep.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative !important; transform: none !important; left: 0 !important; top: 0 !important; width: 100% !important; margin-bottom: 24px !important; border: 3px solid ' + ['#22c55e', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899'][index] + ' !important;';
      
      // Remove from current parent
      if (step.parentNode) {
        step.parentNode.removeChild(step);
      }
      
      // Add to main container
      container.appendChild(newStep);
      console.log('[RESTRUCTURE] Moved and styled step' + (index + 1));
    });
    
    // Remove any carousel containers that might exist
    const carouselContainers = document.querySelectorAll('.workflow-steps, .steps-container, .carousel, .slider');
    carouselContainers.forEach(function(carousel) {
      if (carousel && carousel.children.length === 0) {
        console.log('[RESTRUCTURE] Removing empty carousel container');
        carousel.remove();
      }
    });
    
    // Ensure main container is visible
    if (container.tagName === 'MAIN') {
      container.style.cssText = 'display: block !important; overflow: visible !important; height: auto !important; min-height: 100vh !important;';
    }
    
    console.log('[RESTRUCTURE] DOM restructure complete!');
    return true;
  }
  
  // Try to restructure immediately
  let success = restructureSteps();
  
  // If not successful, wait for DOM and retry
  if (!success) {
    let retryCount = 0;
    const retryInterval = setInterval(function() {
      retryCount++;
      console.log('[RESTRUCTURE] Retry attempt ' + retryCount);
      
      if (restructureSteps() || retryCount >= 50) {
        clearInterval(retryInterval);
        if (retryCount >= 50) {
          console.log('[RESTRUCTURE] Max retries reached');
        }
      }
    }, 100);
  }
  
  // Also run after various delays to catch dynamic content
  setTimeout(restructureSteps, 500);
  setTimeout(restructureSteps, 1000);
  setTimeout(restructureSteps, 2000);
  setTimeout(restructureSteps, 3000);
  
  console.log('[RESTRUCTURE] DOM restructure script initialized');
})();