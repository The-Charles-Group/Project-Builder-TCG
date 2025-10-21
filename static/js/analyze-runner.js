// Starts the analysis job safely, handles uploaded files, dedupes concurrent runs, and renders results progressively.

(function () {
  let currentRun = null;

  // Extract text from staged files
  async function extractStagedFilesText() {
    const sessionId = window.FileStagingModule?.state?.sessionId || 
                     window.currentSessionId || 
                     localStorage.getItem('apb.currentSession');
    
    if (!sessionId) return '';
    
    try {
      const response = await fetch('/api/stage/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });
      
      if (response.ok) {
        const data = await response.json();
        return data.text || '';
      }
    } catch (error) {
      console.error('[AnalyzeRunner] Failed to extract text from files:', error);
    }
    
    return '';
  }

  async function startAnalyze(rfpText, opts = {}) {
    const controller = new AbortController();
    const payload = {
      request_text: rfpText,  // Changed from 'text' to 'request_text' to match API
      mode: opts.mode || 'fast',
      strictness: opts.strictness || 'balanced',
      gpt5_tier: opts.tier || 'mini',
      session_id: window.currentSessionId || window.FileStagingModule?.state?.sessionId || generateSessionId()
    };

    const res = await fetch('/api/ai/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    if (!res.ok) {
      const t = await res.text();
      throw new Error(`Analyze failed ${res.status}: ${t.slice(0, 200)}`);
    }

    const data = await res.json();
    const jobId = data.job_id || data.id || data.jobId;
    if (!jobId) throw new Error('Analyze did not return a job_id');

    return { jobId, controller };
  }

  function defaultRenderIntoStep2(data) {
    const container = document.querySelector('#step2Results');
    if (!container) return;
    
    const items = (data.deliverables || []).map(d => ({
      code: d.code || d.deliverable_code || '',
      name: d.name || d.title || '',
      dept: d.department || d.dept || '',
      hours: d.total_hours || d.hours || 0,
      confidence: d.confidence || d.score || 0,
      components: d.components || []
    }));

    const renderItem = (it, idx) => {
      const div = document.createElement('div');
      div.className = 'deliverable-card';
      div.innerHTML = `
        <div class="card-hd">
          <span class="dept">${it.dept || '-'}</span>
          <span class="code">${it.code}</span>
          <span class="conf">${Math.round((it.confidence || 0) * 100)}</span>
        </div>
        <div class="name">${it.name}</div>
        <div class="meta">${(it.hours || 0)}h • ${it.components.length} components</div>
      `;
      return div;
    };

    // Use progressive rendering if available
    if (window.progressiveListRender) {
      window.progressiveListRender(items, renderItem, container, { chunkSize: 16 });
    } else {
      // Fallback to simple rendering
      container.innerHTML = items.map((it, idx) => {
        const html = renderItem(it, idx).outerHTML;
        return html;
      }).join('');
    }
  }

  async function bindAnalyzeButton(btnSelector, inputSelector, opts = {}) {
    const btn = document.querySelector(btnSelector);
    const input = document.querySelector(inputSelector);
    if (!btn) return;

    // Reentrancy guard
    let busy = false;

    async function clickHandler(ev) {
      ev.preventDefault();
      ev.stopPropagation();
      if (busy) return;

      // First check for uploaded files
      const hasStagedFiles = window.FileStagingModule?.state?.stagedFiles?.length > 0;
      let rfpText = '';
      
      if (hasStagedFiles) {
        // Extract text from uploaded files
        console.log('[AnalyzeRunner] Extracting text from uploaded files...');
        rfpText = await extractStagedFilesText();
      }
      
      // Fall back to textarea if no file text
      if (!rfpText && input) {
        rfpText = (input.value || '').trim();
      }
      
      // Also check PRIMARY_SCENARIO
      if (!rfpText && window.PRIMARY_SCENARIO?.rfpText) {
        rfpText = window.PRIMARY_SCENARIO.rfpText;
      }

      if (!rfpText) {
        alert('Please paste RFP text or upload a document first.');
        return;
      }

      busy = true;
      btn.classList.add('is-busy');
      btn.setAttribute('aria-busy', 'true');
      btn.disabled = true;

      // cancel any previous run
      if (currentRun?.cancel) currentRun.cancel();
      
      try {
        // Get analysis mode
        const mode = opts.mode || 
                    window.PRIMARY_SCENARIO?.analysisMode || 
                    document.querySelector('#analysis-mode')?.value || 
                    'fast';
        
        const { jobId, controller } = await startAnalyze(rfpText, { ...opts, mode });
        
        // watcher: dedupe and cancel others automatically
        const watcher = window.JobPoller?.watch(jobId, (data, done) => {
          // Write into step 2 progressively to avoid jank
          if (Array.isArray(data?.deliverables)) {
            (opts.renderIntoStep2 || defaultRenderIntoStep2)(data);
            
            // Update PRIMARY_SCENARIO
            if (window.PRIMARY_SCENARIO) {
              window.PRIMARY_SCENARIO.deliverables = data.deliverables;
              window.PRIMARY_SCENARIO.analysisResults = data;
              window.PRIMARY_SCENARIO.status = done ? 'analyzed' : 'analyzing';
            }
          }
          
          if (done) {
            btn.classList.remove('is-busy');
            btn.removeAttribute('aria-busy');
            btn.disabled = false;
            busy = false;
            
            // Move to Step 2 if available
            if (typeof window.showStep === 'function') {
              window.showStep(2);
            } else {
              // Simple show/hide
              const step1 = document.querySelector('#step1');
              const step2 = document.querySelector('#step2');
              if (step1 && step2) {
                step1.style.display = 'none';
                step2.style.display = 'block';
              }
            }
          }
        }, { intervalMs: 600, maxIntervalMs: 2000 });

        currentRun = {
          cancel: () => {
            try { controller.abort(); } catch {}
            try { watcher.cancel(); } catch {}
          }
        };
      } catch (err) {
        console.error('Analyze failed', err);
        alert(`Analyze failed: ${err.message}`);
        btn.classList.remove('is-busy');
        btn.removeAttribute('aria-busy');
        btn.disabled = false;
        busy = false;
      }
    }

    // Remove existing listeners that might double-trigger
    const freshBtn = btn.cloneNode(true);
    btn.replaceWith(freshBtn);
    freshBtn.addEventListener('click', clickHandler, { passive: false });

    // stop accidental form submit from re-triggering
    const form = freshBtn.closest('form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        e.stopPropagation();
      });
    }
  }

  // Helper to generate session ID
  function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  window.Analysis = { bindAnalyzeButton };
})();