// Force all steps to be visible - override any other JavaScript
(function() {
  function forceAllStepsVisible() {
    console.log('[FORCE-VISIBLE] Making all steps visible...');
    
    // Get all step elements
    const stepIds = ['step1', 'step2', 'step3', 'step4'];
    
    stepIds.forEach((stepId, index) => {
      const step = document.getElementById(stepId);
      if (step) {
        // Force display with highest priority
        step.style.setProperty('display', 'block', 'important');
        step.style.setProperty('visibility', 'visible', 'important');
        step.style.setProperty('opacity', '1', 'important');
        step.style.setProperty('position', 'relative', 'important');
        step.style.setProperty('left', '0', 'important');
        step.style.setProperty('top', '0', 'important');
        
        // Remove any classes that might hide it
        step.classList.remove('hidden', 'hide', 'invisible', 'd-none');
        
        // Make sure it's not hidden by parent elements
        let parent = step.parentElement;
        while (parent && parent !== document.body) {
          parent.style.setProperty('display', 'block', 'important');
          parent.style.setProperty('visibility', 'visible', 'important');
          parent.style.setProperty('opacity', '1', 'important');
          parent = parent.parentElement;
        }
        
        console.log(`[FORCE-VISIBLE] Step ${index + 1} forced visible`);
      } else {
        console.log(`[FORCE-VISIBLE] Step ${stepId} not found`);
      }
    });
    
    // Also ensure the main element is visible
    const main = document.querySelector('main');
    if (main) {
      main.style.setProperty('display', 'block', 'important');
      main.style.setProperty('min-height', 'auto', 'important');
    }
    
    // Remove any loading overlays
    document.querySelectorAll('.loading-overlay, .loading-spinner').forEach(el => {
      el.style.display = 'none';
    });
    
    console.log('[FORCE-VISIBLE] All steps should now be visible');
  }
  
  // Run immediately
  forceAllStepsVisible();
  
  // Run after DOM is loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', forceAllStepsVisible);
  }
  
  // Run after a delay to override any async JavaScript
  setTimeout(forceAllStepsVisible, 100);
  setTimeout(forceAllStepsVisible, 500);
  setTimeout(forceAllStepsVisible, 1000);
  setTimeout(forceAllStepsVisible, 2000);
  
  // Expose globally for debugging
  window.forceAllStepsVisible = forceAllStepsVisible;
})();