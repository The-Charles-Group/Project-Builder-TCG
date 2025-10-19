// Complete override to show all steps - nuclear option
(function() {
  console.log('[OVERRIDE] Starting complete override to show all steps');
  
  // Function to force all steps visible and remove any hiding mechanisms
  function nukeHidingMechanisms() {
    console.log('[OVERRIDE] Removing all step hiding mechanisms...');
    
    // Override any functions that might hide steps
    window.showStep = function() { console.log('[OVERRIDE] showStep blocked'); };
    window.hideStep = function() { console.log('[OVERRIDE] hideStep blocked'); };
    window.showStep1 = function() { console.log('[OVERRIDE] showStep1 blocked'); };
    window.showStep2 = function() { console.log('[OVERRIDE] showStep2 blocked'); };
    window.showStep3 = function() { console.log('[OVERRIDE] showStep3 blocked'); };
    window.showStep4 = function() { console.log('[OVERRIDE] showStep4 blocked'); };
    
    // Override TransitionManager if it exists
    if (window.TransitionManager) {
      window.TransitionManager.showStep = function() { 
        console.log('[OVERRIDE] TransitionManager.showStep blocked'); 
      };
    }
    
    // Force all steps to be visible
    const steps = document.querySelectorAll('[id^="step"]');
    steps.forEach(function(step) {
      if (step.id.match(/^step\d+$/)) {
        // Remove all hiding mechanisms
        step.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative !important;';
        step.removeAttribute('hidden');
        step.classList.remove('hidden', 'hide', 'd-none', 'invisible');
        console.log('[OVERRIDE] Forced ' + step.id + ' visible with cssText override');
      }
    });
    
    // Ensure the main container can show all content
    const main = document.querySelector('main');
    if (main) {
      main.style.cssText = 'display: block !important; min-height: auto !important; height: auto !important; overflow: visible !important;';
    }
    
    // Override any MutationObserver that might be hiding steps
    const originalMO = window.MutationObserver;
    window.MutationObserver = function(callback) {
      return new originalMO(function(mutations, observer) {
        // Block any mutations that try to hide steps
        mutations = mutations.filter(function(m) {
          if (m.target && m.target.id && m.target.id.match(/^step\d+$/)) {
            console.log('[OVERRIDE] Blocked mutation on ' + m.target.id);
            return false;
          }
          return true;
        });
        if (mutations.length > 0) {
          callback(mutations, observer);
        }
      });
    };
    
    console.log('[OVERRIDE] All hiding mechanisms neutralized');
  }
  
  // Run immediately
  nukeHidingMechanisms();
  
  // Run when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', nukeHidingMechanisms);
  }
  
  // Run after a delay
  setTimeout(nukeHidingMechanisms, 100);
  setTimeout(nukeHidingMechanisms, 500);
  setTimeout(nukeHidingMechanisms, 1000);
  setTimeout(nukeHidingMechanisms, 2000);
  
  // Run on every animation frame for 5 seconds to combat any async hiding
  let frameCount = 0;
  function forceVisible() {
    if (frameCount++ < 300) { // ~5 seconds at 60fps
      const steps = document.querySelectorAll('[id^="step"]');
      steps.forEach(function(step) {
        if (step.id.match(/^step\d+$/) && step.style.display === 'none') {
          step.style.display = 'block';
          console.log('[OVERRIDE] Re-showing hidden step: ' + step.id);
        }
      });
      requestAnimationFrame(forceVisible);
    }
  }
  requestAnimationFrame(forceVisible);
  
  // Expose globally
  window.nukeHidingMechanisms = nukeHidingMechanisms;
})();