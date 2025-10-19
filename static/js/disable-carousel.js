// Disable all carousel/transform-based step management
(function() {
  console.log('[DISABLE-CAROUSEL] Starting carousel disable script');
  
  // Override any function that might use transforms
  const originalTransform = CSSStyleDeclaration.prototype.setProperty;
  CSSStyleDeclaration.prototype.setProperty = function(property, value, priority) {
    // Block any transform that moves elements off-screen
    if (property === 'transform' && value && value.includes('translateX')) {
      // Check if this is trying to move a step off-screen
      const element = this.parentElement || this;
      if (element && element.id && element.id.match(/step[1-5]/)) {
        console.log('[DISABLE-CAROUSEL] Blocked transform on', element.id, '- was trying to set:', value);
        return; // Don't apply the transform
      }
      
      // Also block transforms on container elements
      if (element && (element.classList.contains('workflow-steps') || 
                      element.classList.contains('steps-container') ||
                      element.querySelector('#step1'))) {
        console.log('[DISABLE-CAROUSEL] Blocked transform on container - was trying to set:', value);
        return; // Don't apply the transform
      }
    }
    
    // Block overflow hidden on main containers
    if (property === 'overflow' && (value === 'hidden' || value === 'clip')) {
      const element = this.parentElement || this;
      if (element && (element.tagName === 'MAIN' || 
                      element.classList.contains('workflow-steps') ||
                      element.querySelector('#step1'))) {
        console.log('[DISABLE-CAROUSEL] Blocked overflow:hidden on container');
        return; // Don't apply overflow hidden
      }
    }
    
    // Allow other properties
    return originalTransform.call(this, property, value, priority);
  };
  
  // Also override direct style.transform assignments
  Object.defineProperty(CSSStyleDeclaration.prototype, 'transform', {
    get: function() {
      return this.getPropertyValue('transform');
    },
    set: function(value) {
      const element = this.parentElement || this;
      
      // Block transforms on steps and containers
      if (element && element.id && element.id.match(/step[1-5]/)) {
        console.log('[DISABLE-CAROUSEL] Blocked direct transform on', element.id);
        return;
      }
      
      if (element && (element.classList.contains('workflow-steps') || 
                      element.classList.contains('steps-container') ||
                      element.querySelector('#step1'))) {
        console.log('[DISABLE-CAROUSEL] Blocked direct transform on container');
        return;
      }
      
      this.setProperty('transform', value);
    }
  });
  
  // Override any showStep or goToStep functions
  const blockStepFunctions = function() {
    const functionNames = ['showStep', 'hideStep', 'goToStep', 'showStep1', 'showStep2', 'showStep3', 'showStep4', 'showStep5'];
    
    functionNames.forEach(function(funcName) {
      if (window[funcName]) {
        console.log('[DISABLE-CAROUSEL] Overriding', funcName);
        window[funcName] = function() {
          console.log('[DISABLE-CAROUSEL] Blocked', funcName, 'call');
          // Do nothing - don't hide or transform steps
        };
      }
    });
    
    // Also check for TransitionManager
    if (window.TransitionManager) {
      console.log('[DISABLE-CAROUSEL] Neutralizing TransitionManager');
      window.TransitionManager = {
        showStep: function() { console.log('[DISABLE-CAROUSEL] TransitionManager.showStep blocked'); },
        hideStep: function() { console.log('[DISABLE-CAROUSEL] TransitionManager.hideStep blocked'); },
        init: function() { console.log('[DISABLE-CAROUSEL] TransitionManager.init blocked'); }
      };
    }
  };
  
  // Run immediately and after DOM loads
  blockStepFunctions();
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', blockStepFunctions);
  }
  
  // Run periodically to catch late-loaded functions
  setTimeout(blockStepFunctions, 100);
  setTimeout(blockStepFunctions, 500);
  setTimeout(blockStepFunctions, 1000);
  setTimeout(blockStepFunctions, 2000);
  
  console.log('[DISABLE-CAROUSEL] Carousel disable script initialized');
})();