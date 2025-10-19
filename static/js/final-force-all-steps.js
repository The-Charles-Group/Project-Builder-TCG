// Final comprehensive solution to show all steps
(function() {
  console.log('[FINAL] Starting final solution to show all steps');
  
  // Wait for steps to exist in DOM, then force them visible
  function waitForStepsAndShow() {
    console.log('[FINAL] Waiting for steps to exist in DOM...');
    
    const checkInterval = setInterval(function() {
      const step1 = document.getElementById('step1');
      const step2 = document.getElementById('step2');
      const step3 = document.getElementById('step3');
      const step4 = document.getElementById('step4');
      
      if (step1 && step2 && step3 && step4) {
        console.log('[FINAL] All steps found in DOM! Making them visible...');
        clearInterval(checkInterval);
        
        // Force all steps visible
        [step1, step2, step3, step4].forEach(function(step, index) {
          // Clear any inline styles that might hide it
          step.style.removeProperty('display');
          step.style.removeProperty('visibility');
          step.style.removeProperty('opacity');
          
          // Then force it visible with important
          step.style.setProperty('display', 'block', 'important');
          step.style.setProperty('visibility', 'visible', 'important');
          step.style.setProperty('opacity', '1', 'important');
          step.style.setProperty('position', 'relative', 'important');
          step.style.setProperty('left', '0', 'important');
          step.style.setProperty('top', '0', 'important');
          step.style.setProperty('transform', 'none', 'important');
          step.style.setProperty('height', 'auto', 'important');
          step.style.setProperty('width', '100%', 'important');
          step.style.setProperty('overflow', 'visible', 'important');
          
          // Remove any hiding classes
          step.removeAttribute('hidden');
          step.classList.remove('hidden', 'hide', 'd-none', 'invisible');
          
          console.log('[FINAL] Step ' + (index + 1) + ' forced visible');
        });
        
        // Ensure main container can show all content
        const main = document.querySelector('main');
        if (main) {
          main.style.setProperty('display', 'block', 'important');
          main.style.setProperty('height', 'auto', 'important');
          main.style.setProperty('min-height', 'auto', 'important');
          main.style.setProperty('overflow', 'visible', 'important');
        }
        
        // Scroll to top to see all steps
        window.scrollTo(0, 0);
        
        console.log('[FINAL] All steps should now be visible!');
        
        // Monitor for any future attempts to hide steps
        monitorSteps();
      } else {
        console.log('[FINAL] Steps not found yet, still waiting...');
      }
    }, 100); // Check every 100ms
    
    // Timeout after 10 seconds
    setTimeout(function() {
      clearInterval(checkInterval);
      console.log('[FINAL] Timeout waiting for steps');
    }, 10000);
  }
  
  // Monitor steps and re-show them if they get hidden
  function monitorSteps() {
    console.log('[FINAL] Starting monitor to prevent steps from being hidden');
    
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.target && mutation.target.id && mutation.target.id.match(/^step[1-4]$/)) {
          const step = mutation.target;
          
          // Check if step was hidden
          const isHidden = step.style.display === 'none' || 
                          step.hasAttribute('hidden') || 
                          step.classList.contains('hidden');
          
          if (isHidden) {
            console.log('[FINAL] Step ' + step.id + ' was hidden, re-showing it!');
            step.style.setProperty('display', 'block', 'important');
            step.removeAttribute('hidden');
            step.classList.remove('hidden');
          }
        }
      });
    });
    
    // Observe all steps for changes
    ['step1', 'step2', 'step3', 'step4'].forEach(function(stepId) {
      const step = document.getElementById(stepId);
      if (step) {
        observer.observe(step, {
          attributes: true,
          attributeFilter: ['style', 'class', 'hidden']
        });
      }
    });
  }
  
  // Start the process
  waitForStepsAndShow();
  
  // Also run after DOM loads as backup
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', waitForStepsAndShow);
  }
  
  // Expose globally for debugging
  window.forceAllStepsVisible = waitForStepsAndShow;
})();