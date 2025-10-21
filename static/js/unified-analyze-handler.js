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

            console.log('[Unified Analyze] Poll #' + pollCount + ' - Status:', status.status, 'Progress:', status.progress + '%');
            
            // Debug log full status on first and completion polls
            if (pollCount === 1 || status.status === 'completed') {
              console.log('[Unified Analyze] Full status object:', JSON.stringify(status, null, 2));
            }

            if (status.status === 'completed') {
              clearInterval(pollInterval);

              console.log('[Unified Analyze] Job completed, processing results...', status);

              // Extract deliverables from the result structure
              let deliverables = [];
              
              // Handle both nested (result.plan.suggestions_by_department) and flat (result.deliverables) structures
              if (status.result) {
                if (status.result.plan && status.result.plan.suggestions_by_department) {
                  const deptSuggestions = status.result.plan.suggestions_by_department;
                  console.log('[Unified Analyze] Found suggestions_by_department:', Object.keys(deptSuggestions));
                  
                  // Flatten all department suggestions into a single array
                  Object.entries(deptSuggestions).forEach(([dept, deptDelivs]) => {
                    if (Array.isArray(deptDelivs)) {
                      deptDelivs.forEach(d => {
                        deliverables.push({
                          deliverable_code: d.code || d.deliverable_code,
                          deliverable_name: d.name || d.deliverable_name || d.title,
                          department: dept,
                          category: dept,
                          confidence: d.confidence_score || d.confidence || 0,
                          relevance: d.relevance_score || d.relevance || 0,
                          why: d.why || d.reasoning || '',
                          risks: d.risks || '',
                          components: d.components || [],
                          select: d.select !== false
                        });
                      });
                    }
                  });
                } else if (status.result.deliverables && Array.isArray(status.result.deliverables)) {
                  // Handle flat structure
                  deliverables = status.result.deliverables.map(d => ({
                    deliverable_code: d.code || d.deliverable_code,
                    deliverable_name: d.name || d.deliverable_name || d.title,
                    department: d.department || d.category || 'General',
                    category: d.department || d.category || 'General',
                    confidence: d.confidence_score || d.confidence || 0,
                    relevance: d.relevance_score || d.relevance || 0,
                    why: d.why || d.reasoning || '',
                    risks: d.risks || '',
                    components: d.components || [],
                    select: d.select !== false
                  }));
                }
                
                console.log('[Unified Analyze] Extracted', deliverables.length, 'deliverables');
              }
              
              if (deliverables.length === 0) {
                console.error('[Unified Analyze] No deliverables found in result:', status.result);
                alert('Analysis completed but no deliverables were found. Please try again.');
                newBtn.disabled = false;
                newBtn.textContent = 'Analyze with AI';
                return;
              }

              // Store results in PRIMARY_SCENARIO
              if (window.PRIMARY_SCENARIO) {
                window.PRIMARY_SCENARIO.deliverables = deliverables;
                window.PRIMARY_SCENARIO.analysisResults = status.result;
                window.PRIMARY_SCENARIO.rfpText = rfpText;
                window.PRIMARY_SCENARIO.status = 'analyzed';
              }

              // Store in APB.step2 for the UI to access
              if (!window.APB) window.APB = {};
              if (!window.APB.step2) {
                window.APB.step2 = {
                  selectedCodes: new Set(),
                  selectedComponentsByCode: {},
                  selectedL2ByKey: {},
                  allDeliverables: [],
                  aiSuggestedCodes: new Set(),
                  filters: { deliverables: '', components: '', l2: '' },
                  els: {}
                };
              }

              // Convert to APB format
              window.APB.step2.allDeliverables = deliverables.map(d => ({
                Deliverable_Code: d.deliverable_code,
                Deliverable: d.deliverable_name,
                Category: d.department,
                Service_Dept_for_PM: d.department,
                confidence: d.confidence,
                relevance: d.relevance,
                why: d.why,
                risks: d.risks,
                components: d.components,
                select: d.select
              }));

              // Mark AI suggested codes
              deliverables.forEach(d => {
                if (d.select && d.deliverable_code) {
                  window.APB.step2.aiSuggestedCodes.add(d.deliverable_code);
                }
              });

              console.log('[Unified Analyze] Populated APB.step2.allDeliverables with', window.APB.step2.allDeliverables.length, 'items');

              // Store in session
              if (window.SessionManager) {
                window.SessionManager.setSessionItem('analysis_results', status.result);
                window.SessionManager.setSessionItem('rfp_text', rfpText);
              }

              // Populate the AI summary panel
              if (status.result && status.result.summary) {
                const summaryPanel = document.getElementById('ai-summary-panel');
                if (summaryPanel) {
                  summaryPanel.innerHTML = `
                    <div style="background: rgba(139, 92, 246, 0.1); padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                      <h4 style="margin: 0 0 8px 0; color: var(--accent);">📊 RFP Summary</h4>
                      <p style="margin: 0; font-size: 0.9em; line-height: 1.5;">${status.result.summary.summary || 'Analysis complete'}</p>
                    </div>
                  `;
                }
              }

              // Move to Step 2
              const step1 = document.getElementById('step1');
              const step2 = document.getElementById('step2');

              if (step1 && step2) {
                step1.style.display = 'none';
                step2.style.display = 'block';

                // Render deliverables - call the function that exists
                if (typeof window.renderDeliverablesPanel === 'function') {
                  console.log('[Unified Analyze] Calling renderDeliverablesPanel...');
                  window.renderDeliverablesPanel();
                } else {
                  console.warn('[Unified Analyze] renderDeliverablesPanel function not found');
                }

                // Initialize AI suggestions display
                if (typeof window.initAISummaryAndSuggestions === 'function') {
                  console.log('[Unified Analyze] Calling initAISummaryAndSuggestions...');
                  window.initAISummaryAndSuggestions();
                }

                step2.scrollIntoView({ behavior: 'smooth' });
              }

              // Hide progress bar
              if (progressBar) {
                progressBar.style.display = 'none';
              }

              newBtn.disabled = false;
              newBtn.textContent = 'Analyze with AI';

              console.log('[Unified Analyze] Analysis complete! Found', deliverables.length, 'deliverables');
              console.log('[Unified Analyze] Step 2 should now be populated with results');

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