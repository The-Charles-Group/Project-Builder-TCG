// Hook up the analyze button with proper file detection
(function () {
  // Wait for DOM ready
  function init() {
    const BTN = document.querySelector('#btnAnalyze') || 
                document.querySelector('#analyzeButton') || 
                document.querySelector('[data-action="analyze"]');
    
    const INPUT = document.querySelector('#rfp-text') || 
                  document.querySelector('#rfpText') || 
                  document.querySelector('textarea[name="rfp"]');
    
    if (BTN && window.Analysis) {
      window.Analysis.bindAnalyzeButton(
        BTN.id ? `#${BTN.id}` : '[data-action="analyze"]', 
        INPUT?.id ? `#${INPUT.id}` : 'textarea', 
        {
          mode: window.PRIMARY_SCENARIO?.analysisMode || 'fast',
          strictness: 'balanced',
          tier: 'mini'
        }
      );
      console.log('[AI Buttons Fix] Analyze button wired successfully');
    } else {
      console.warn('[AI Buttons Fix] Waiting for button or Analysis module...');
      setTimeout(init, 500);
    }
  }
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();