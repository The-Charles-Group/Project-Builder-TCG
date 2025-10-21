// Unified handler for the Analyze with AI button - works with uploaded files
(function() {
  console.log('[Unified Analyze] Loading unified analyze handler...');

  // Wait for DOM and required modules
  function initUnifiedAnalyze() {
    const btnAnalyze = document.getElementById('btnAnalyze');
    if (!btnAnalyze) {
      console.warn('[Unified Analyze] Button not found, retrying...');
      setTimeout(initUnifiedAnalyze, 500);
      return;
    }

    // Remove ALL existing listeners by replacing the element
    const newBtn = btnAnalyze.cloneNode(true);
    btnAnalyze.parentNode.replaceChild(newBtn, btnAnalyze);

    // Add our single, working handler
    newBtn.addEventListener('click', async function(e) {
      e.preventDefault();
      e.stopPropagation();

      console.log('[Unified Analyze] Button clicked!');

      // Disable button and show progress
      newBtn.disabled = true;
      newBtn.textContent = 'Analyzing...';

      try {
        // Get session ID
        const sessionId = window.FileStagingModule?.state?.sessionId || 
                         window.currentSessionId || 
                         localStorage.getItem('apb.currentSession');

        console.log('[Unified Analyze] Session ID:', sessionId);

        // Get RFP text from either uploaded files or textarea
        let rfpText = '';

        // First try to get text from uploaded files
        try {
          const extractRes = await fetch('/api/stage/extract', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `session_id=${encodeURIComponent(sessionId)}`
          });

          if (extractRes.ok) {
            const data = await extractRes.json();
            if (data.success && data.text) {
              rfpText = data.text;
              console.log('[Unified Analyze] Extracted text from files:', rfpText.length, 'characters');
            }
          }
        } catch (err) {
          console.warn('[Unified Analyze] File extraction failed:', err);
        }

        // Fall back to textarea if no file text
        if (!rfpText) {
          const textarea = document.getElementById('rfpText') || document.querySelector('textarea[placeholder*="Paste"]');
          if (textarea) {
            rfpText = textarea.value.trim();
            console.log('[Unified Analyze] Using textarea text:', rfpText.length, 'characters');
          }
        }

        if (!rfpText || rfpText.length < 10) {
          alert('Please upload a file or paste RFP text first.');
          newBtn.disabled = false;
          newBtn.textContent = 'Analyze with AI';
          return;
        }

        console.log('[Unified Analyze] Starting analysis with', rfpText.length, 'characters of text');

        // Get analysis mode
        const modeButtons = document.querySelectorAll('.mode-button');
        let analysisMode = 'fast'; // default
        modeButtons.forEach(btn => {
          if (btn.classList.contains('active')) {
            analysisMode = btn.textContent.toLowerCase().includes('deep') ? 'deep' : 'fast';
          }
        });

        console.log('[Unified Analyze] Starting analysis with mode:', analysisMode);

        // Start AI analysis
        const analyzeRes = await fetch('/api/ai/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            request_text: rfpText,
            strictness: 'balanced',
            tier: analysisMode === 'deep' ? 'thinking' : 'mini',
            mode: analysisMode,
            session_id: sessionId
          })
        });

        if (!analyzeRes.ok) {
          const error = await analyzeRes.text();
          throw new Error(`Analysis failed: ${error}`);
        }

        const jobData = await analyzeRes.json();
        const jobId = jobData.job_id || jobData.id;

        console.log('[Unified Analyze] Job started:', jobId);

        // Show progress bar if available
        const progressBar = document.querySelector('#ai-progress-container');
        if (progressBar) {
          progressBar.style.display = 'block';
        }

        // Poll for results
        let pollCount = 0;
        const maxPolls = 300; // 5 minutes max

        const pollInterval = setInterval(async () => {
          pollCount++;

          if (pollCount > maxPolls) {
            clearInterval(pollInterval);
            alert('Analysis timed out. Please try again.');
            newBtn.disabled = false;
            newBtn.textContent = 'Analyze with AI';
            return;
          }

          try {
            const statusRes = await fetch(`/api/ai/jobs/${jobId}`);
            const status = await statusRes.json();

            console.log('[Unified Analyze] Job status:', status.status);

            if (status.status === 'completed') {
              clearInterval(pollInterval);

              // Store results
              if (window.PRIMARY_SCENARIO) {
                window.PRIMARY_SCENARIO.deliverables = status.deliverables || [];
                window.PRIMARY_SCENARIO.analysisResults = status;
                window.PRIMARY_SCENARIO.rfpText = rfpText;
                window.PRIMARY_SCENARIO.status = 'analyzed';
              }

              // Store in session
              if (window.SessionManager) {
                window.SessionManager.setSessionItem('analysis_results', status);
                window.SessionManager.setSessionItem('rfp_text', rfpText);
              }

              // Move to Step 2
              const step1 = document.getElementById('step1');
              const step2 = document.getElementById('step2');

              if (step1 && step2) {
                step1.style.display = 'none';
                step2.style.display = 'block';

                // Render deliverables if function exists
                if (typeof window.renderDeliverablesPanel === 'function') {
                  window.renderDeliverablesPanel(status.deliverables || []);
                }

                step2.scrollIntoView({ behavior: 'smooth' });
              }

              // Hide progress bar
              if (progressBar) {
                progressBar.style.display = 'none';
              }

              newBtn.disabled = false;
              newBtn.textContent = 'Analyze with AI';

              console.log('[Unified Analyze] Analysis complete! Found', status.deliverables?.length || 0, 'deliverables');

            } else if (status.status === 'failed') {
              clearInterval(pollInterval);
              alert(`Analysis failed: ${status.error || 'Unknown error'}`);
              newBtn.disabled = false;
              newBtn.textContent = 'Analyze with AI';
            }

            // Update progress if available
            if (status.progress && progressBar) {
              const progressText = progressBar.querySelector('.progress-text');
              if (progressText) {
                progressText.textContent = `${Math.round(status.progress)}% - ${status.current_stage || 'Processing...'}`;
              }
              const progressFill = progressBar.querySelector('.progress-fill');
              if (progressFill) {
                progressFill.style.width = `${status.progress}%`;
              }
            }

          } catch (error) {
            console.error('[Unified Analyze] Polling error:', error);
          }
        }, 1000); // Poll every second

      } catch (error) {
        console.error('[Unified Analyze] Error:', error);
        alert(`Analysis failed: ${error.message}`);
        newBtn.disabled = false;
        newBtn.textContent = 'Analyze with AI';
      }
    });

    console.log('[Unified Analyze] ✅ Handler successfully attached to button');
  }

  // Start initialization
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUnifiedAnalyze);
  } else {
    // Short delay to ensure other scripts have loaded
    setTimeout(initUnifiedAnalyze, 100);
  }
})();