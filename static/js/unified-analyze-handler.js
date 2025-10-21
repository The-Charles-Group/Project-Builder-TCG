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

    // Check if already initialized to avoid duplicate listeners
    if (btnAnalyze.dataset.unifiedAnalyzeInitialized === 'true') {
      console.log('[Unified Analyze] Already initialized, skipping');
      return;
    }

    // Add our handler (don't replace the element as that removes other listeners)
    btnAnalyze.addEventListener('click', async function(e) {
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

            // FIXED: Check for both 'completed' and 'complete' status
            if (status.status === 'completed' || status.status === 'complete') {
              clearInterval(pollInterval);

              console.log('[Unified Analyze] ✅ Job completed, processing results...');
              console.log('[Unified Analyze] Full status object:', status);

              // Extract deliverables from the result structure
              let deliverables = [];
              
              // FIXED: Handle the actual backend response structure
              // Backend returns: { plan: { suggestions_by_department: { "Department": [deliverables] } } }
              if (status.result && status.result.plan && status.result.plan.suggestions_by_department) {
                const deptSuggestions = status.result.plan.suggestions_by_department;
                console.log('[Unified Analyze] Found suggestions_by_department with', Object.keys(deptSuggestions).length, 'departments');
                
                // Flatten all department suggestions into a single array
                Object.entries(deptSuggestions).forEach(([dept, deptDelivs]) => {
                  if (Array.isArray(deptDelivs)) {
                    console.log(`[Unified Analyze] Processing ${deptDelivs.length} deliverables from ${dept}`);
                    deptDelivs.forEach(d => {
                      deliverables.push({
                        deliverable_code: d.code || d.deliverable_code || '',
                        deliverable_name: d.name || d.deliverable_name || d.title || 'Unknown',
                        department: dept,
                        category: dept,
                        confidence: parseFloat(d.confidence || d.confidence_score || 0.5),
                        relevance: parseFloat(d.relevance || d.relevance_score || 50),
                        why: d.why || d.reasoning || '',
                        risks: d.risks || '',
                        components: d.components || [],
                        select: d.select !== false
                      });
                    });
                  }
                });
              } else if (status.result && status.result.deliverables && Array.isArray(status.result.deliverables)) {
                // Handle flat structure (fallback)
                console.log('[Unified Analyze] Found flat deliverables array with', status.result.deliverables.length, 'items');
                deliverables = status.result.deliverables.map(d => ({
                  deliverable_code: d.code || d.deliverable_code || '',
                  deliverable_name: d.name || d.deliverable_name || d.title || 'Unknown',
                  department: d.department || d.category || 'General',
                  category: d.department || d.category || 'General',
                  confidence: parseFloat(d.confidence || d.confidence_score || 0.5),
                  relevance: parseFloat(d.relevance || d.relevance_score || 50),
                  why: d.why || d.reasoning || '',
                  risks: d.risks || '',
                  components: d.components || [],
                  select: d.select !== false
                }));
              }
              
              console.log('[Unified Analyze] ✅ Extracted', deliverables.length, 'deliverables');
              
              // CRITICAL FIX: Update PRIMARY_SCENARIO with deliverables
              if (deliverables.length > 0 && window.PRIMARY_SCENARIO) {
                window.PRIMARY_SCENARIO.deliverables = deliverables;
                window.PRIMARY_SCENARIO.status = 'analyzed';
                console.log('[Unified Analyze] PRIMARY_SCENARIO updated with', deliverables.length, 'deliverables');
              }
              
              if (deliverables.length === 0) {
                console.error('[Unified Analyze] ❌ No deliverables found in result');
                console.error('[Unified Analyze] Full result object:', status.result);
                
                // Try one more time to extract from different path
                if (status.data && status.data.plan && status.data.plan.suggestions_by_department) {
                  console.log('[Unified Analyze] Trying alternate path: status.data.plan...');
                  const altDeptSugg = status.data.plan.suggestions_by_department;
                  Object.entries(altDeptSugg).forEach(([dept, deptDelivs]) => {
                    if (Array.isArray(deptDelivs)) {
                      deptDelivs.forEach(d => {
                        deliverables.push({
                          deliverable_code: d.code || d.deliverable_code || '',
                          deliverable_name: d.name || d.deliverable_name || d.title || 'Unknown',
                          department: dept,
                          category: dept,
                          confidence: parseFloat(d.confidence || d.confidence_score || 0.5),
                          relevance: parseFloat(d.relevance || d.relevance_score || 50),
                          why: d.why || d.reasoning || '',
                          risks: d.risks || '',
                          components: d.components || [],
                          select: d.select !== false
                        });
                      });
                    }
                  });
                }
                
                // FIXED: Extract deliverables from the correct location in job result
                console.log('[Unified Analyze] Job result structure:', JSON.stringify(Object.keys(data.result || {})));
                
                // Check multiple possible locations for deliverables
                let deliverables = [];
                if (data.result && data.result.plan && data.result.plan.suggestions_by_department) {
                  // Extract from suggestions_by_department (standard format)
                  const deptSuggestions = data.result.plan.suggestions_by_department;
                  for (const dept in deptSuggestions) {
                    if (Array.isArray(deptSuggestions[dept])) {
                      deliverables = deliverables.concat(deptSuggestions[dept]);
                    }
                  }
                  console.log('[Unified Analyze] Extracted deliverables from suggestions_by_department:', deliverables.length);
                } else if (data.result && Array.isArray(data.result.deliverables)) {
                  // Fallback: direct deliverables array
                  deliverables = data.result.deliverables;
                  console.log('[Unified Analyze] Extracted deliverables from direct array:', deliverables.length);
                }
                
                if (deliverables.length === 0) {
                  console.error('[Unified Analyze] No deliverables found in job result. Full result:', data.result);
                  alert('Analysis completed but no deliverables were found. The analysis job may have failed. Please try again.');
                  newBtn.disabled = false;
                  newBtn.textContent = 'Analyze with AI';
                  return;
                }
                
                // CRITICAL: Update PRIMARY_SCENARIO with deliverables
                if (window.PRIMARY_SCENARIO) {
                  window.PRIMARY_SCENARIO.deliverables = deliverables.map(d => ({
                    code: d.deliverable_code || d.code,
                    name: d.deliverable_name || d.name || d.deliverable,
                    category: d.category || d.department || 'General',
                    confidence: d.confidence || 0.8,
                    reasoning: d.reasoning || '',
                    selected: true
                  }));
                  window.PRIMARY_SCENARIO.save();
                  console.log('[Unified Analyze] PRIMARY_SCENARIO updated with', deliverables.length, 'deliverables');
                }
                
                // CRITICAL: Update APB.step2.allDeliverables for rendering
                if (window.APB && window.APB.step2) {
                  window.APB.step2.allDeliverables = deliverables;
                  console.log('[Unified Analyze] APB.step2.allDeliverables updated with', deliverables.length, 'deliverables');
                }
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

                // CRITICAL: Wait a tick for state updates to propagate
                setTimeout(() => {
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
                }, 50);
              }

              // Hide progress bar
              if (progressBar) {
                progressBar.style.display = 'none';
              }

              newBtn.disabled = false;
              newBtn.textContent = 'Analyze with AI';

              console.log('[Unified Analyze] Analysis complete! Found', deliverables.length, 'deliverables');
              console.log('[Unified Analyze] Step 2 should now be populated with deliverables');esults');

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

    // Mark as initialized
    btnAnalyze.dataset.unifiedAnalyzeInitialized = 'true';
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