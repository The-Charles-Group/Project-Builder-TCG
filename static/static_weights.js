
// weights.js — interactive UI for weighted AI deliverable suggestions
window.TCGWeights = (function(){
  let currentData = null;
  let currentSelectionMode = 'confidence_only'; // Default selection mode
  
  function _el(html){
    const t = document.createElement('template');
    t.innerHTML = html.trim();
    return t.content.firstChild;
  }
  
  function render(containerSelector, data, selectionMode = 'confidence_only'){
    currentData = data;
    currentSelectionMode = selectionMode;
    const c = document.querySelector(containerSelector);
    if(!c){ console.warn('weights container not found', containerSelector); return; }
    c.innerHTML = '';
    
    // Add Auto-selection Mode Control
    const modeControl = _el(`
      <div style="margin-bottom: 20px; padding: 16px; background: rgba(139, 92, 246, 0.08); border: 1px solid rgba(139, 92, 246, 0.2); border-radius: 8px;">
        <h3 style="margin: 0 0 12px 0; color: var(--accent); font-size: 1em;">⚙️ Auto-selection Mode</h3>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
            <input type="radio" name="selection-mode" value="confidence_only" ${selectionMode === 'confidence_only' ? 'checked' : ''} />
            <span><strong>AI Confidence Only</strong> (default) — Select deliverables with ≥70% AI confidence</span>
          </label>
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
            <input type="radio" name="selection-mode" value="tfidf_only" ${selectionMode === 'tfidf_only' ? 'checked' : ''} />
            <span><strong>TF-IDF Similarity Only</strong> — Select deliverables with ≥0.70 TF-IDF similarity</span>
          </label>
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
            <input type="radio" name="selection-mode" value="both" ${selectionMode === 'both' ? 'checked' : ''} />
            <span><strong>Both (AI + TF-IDF)</strong> — Select if either method meets threshold</span>
          </label>
        </div>
        <div style="margin-top: 8px; padding: 8px; background: rgba(59, 130, 246, 0.1); border-radius: 4px; font-size: 0.85em; color: var(--muted);">
          <strong>Current mode:</strong> <span id="current-mode-label">${getModeLabel(selectionMode)}</span>
        </div>
      </div>
    `);
    c.appendChild(modeControl);
    
    // Wire up mode change handler
    c.querySelectorAll('input[name="selection-mode"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        const newMode = e.target.value;
        currentSelectionMode = newMode;
        document.getElementById('current-mode-label').textContent = getModeLabel(newMode);
        
        // Re-fetch data from server with new selection mode
        const rfpText = window.APP?.rfpText || '';
        if (rfpText) {
          console.log(`[TCGWeights] Re-fetching with selection_mode: ${newMode}`);
          fetchWeightedScoresWithMode(rfpText, newMode, containerSelector);
        } else {
          // Fallback: just update UI without server call
          console.log('[TCGWeights] No RFP text, updating UI only');
          if (currentData) {
            applySelectionMode(newMode);
          }
        }
      });
    });
    
    // Check which deliverables are already selected
    const alreadySelected = new Set(window.selectionStore?.deliverables.keys() || []);
    
    // Filter to show top matches (>= 50% match OR >= 0.50 TF-IDF)
    const topMatches = (data.deliverables || []).filter(d => 
      d.match_percent >= 50 || (d.tfidf_similarity && d.tfidf_similarity >= 0.50)
    );
    
    if (topMatches.length === 0) {
      c.innerHTML = '<p style="color: var(--muted); padding: 12px;">No strong matches found (threshold: 50%). Try refining your RFP text.</p>';
      return;
    }
    
    // Create table with checkboxes
    const table = _el(`
      <table class="weights-table">
        <thead>
          <tr>
            <th style="width: 40px;">
              <input type="checkbox" id="weights-select-all" title="Select/Deselect All" />
            </th>
            <th>Service Dept</th>
            <th>Deliverable</th>
            <th>Match %</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    `);
    
    const tbody = table.querySelector('tbody');
    
    topMatches.forEach(row => {
      const isSelected = alreadySelected.has(row.deliverable_code);
      const tr = document.createElement('tr');
      tr.className = isSelected ? 'already-selected' : '';
      
      // Determine selection status based on current mode
      const selectionInfo = getSelectionInfo(row, currentSelectionMode);
      
      // Create score display with both TF-IDF and confidence
      let scoreDisplay = `<strong>${row.match_percent.toFixed(1)}%</strong>`;
      
      // Show TF-IDF similarity if available
      if (row.tfidf_similarity !== undefined) {
        scoreDisplay += `<br><small style="color: var(--muted);">TF-IDF: ${row.tfidf_similarity.toFixed(2)}</small>`;
      }
      
      // Show if this was boosted by direct match
      if (row.direct_match) {
        scoreDisplay += `<br><small style="color: #10b981;">✓ Direct Match</small>`;
        if (row.matched_keywords && row.matched_keywords.length > 0) {
          const keywords = row.matched_keywords.slice(0, 3).join(', ');
          scoreDisplay += `<br><small style="color: #6b7280; font-size: 0.75em;">${keywords}</small>`;
        }
      }
      
      // Build badges for selection status
      let badgeHTML = '';
      if (isSelected) {
        badgeHTML = '<span class="badge">Selected</span>';
      } else if (selectionInfo.autoSelected) {
        badgeHTML = `<span class="badge badge-auto" style="background: ${selectionInfo.badgeColor};">${selectionInfo.badgeText}</span>`;
      }
      
      tr.innerHTML = `
        <td>
          <input type="checkbox" 
                 class="weights-checkbox" 
                 data-code="${row.deliverable_code}"
                 ${isSelected ? 'checked disabled' : selectionInfo.autoSelected ? 'checked' : ''} />
        </td>
        <td>${row.service_department||''}</td>
        <td>
          ${row.deliverable||row.deliverable_code}
          ${badgeHTML}
        </td>
        <td>${scoreDisplay}</td>
      `;
      tbody.appendChild(tr);
      
      // Add expandable details for components/tasks
      const comps = (data.components && data.components[row.deliverable_code]) || [];
      const tasks = (data.tasks && data.tasks[row.deliverable_code]) || [];
      if(comps.length || tasks.length){
        const detail = document.createElement('tr');
        detail.className = isSelected ? 'already-selected' : '';
        const td = document.createElement('td');
        td.colSpan = 4;
        let html = '';
        if(comps.length){
          html += '<div class="weights-sub"><div class="weights-sub-h">Top Components</div><ul>';
          comps.slice(0,5).forEach(cmp => {
            html += `<li>${cmp.component} — ${cmp.percent}%</li>`;
          });
          html += '</ul></div>';
        }
        if(tasks.length){
          html += '<div class="weights-sub"><div class="weights-sub-h">Top Tasks</div><ul>';
          tasks.slice(0,6).forEach(tsk => {
            html += `<li>${tsk.component}: ${tsk.task} — ${tsk.percent}%</li>`;
          });
          html += '</ul></div>';
        }
        td.innerHTML = html;
        detail.appendChild(td);
        tbody.appendChild(detail);
      }
    });
    
    c.appendChild(table);
    
    // Add explanatory text
    const explanation = _el(`
      <div style="margin-top: 12px; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; font-size: 0.85em; color: var(--text);">
        <strong>Understanding the Scores:</strong><br>
        <div style="margin-top: 6px; line-height: 1.6;">
          • <strong>Confidence %</strong>: Our overall certainty this deliverable matches your needs (0-100%)<br>
          • <strong>TF-IDF Score</strong>: Content similarity based on keyword frequency analysis (0.00-1.00 scale)<br>
          • <strong style="color: #10b981;">✓ Direct Match</strong>: Deliverable name appears explicitly in your RFP (boosts to 90%+)<br>
          <span style="opacity: 0.8;">Direct matches are prioritized even if TF-IDF is lower, as explicit mentions indicate clear requirements.</span>
        </div>
      </div>
    `);
    c.appendChild(explanation);
    
    // Add action buttons
    const actions = _el(`
      <div style="margin-top: 16px; display: flex; gap: 12px; align-items: center;">
        <button id="btn-apply-weights" class="btn-primary" style="background: var(--accent); padding: 8px 20px;">
          ✓ Apply Selected Deliverables
        </button>
        <button id="btn-select-top3" class="btn-secondary" style="padding: 8px 16px;">
          Select Top 3
        </button>
        <span id="weights-count" style="color: var(--muted); font-size: 0.9em;"></span>
      </div>
    `);
    c.appendChild(actions);
    
    // Wire up event handlers
    wireHandlers();
    updateCount();
  }
  
  function wireHandlers() {
    // Select all checkbox
    const selectAll = document.getElementById('weights-select-all');
    if (selectAll) {
      selectAll.addEventListener('change', (e) => {
        document.querySelectorAll('.weights-checkbox:not(:disabled)').forEach(cb => {
          cb.checked = e.target.checked;
        });
        updateCount();
      });
    }
    
    // Individual checkboxes
    document.querySelectorAll('.weights-checkbox').forEach(cb => {
      cb.addEventListener('change', updateCount);
    });
    
    // Apply button
    const btnApply = document.getElementById('btn-apply-weights');
    if (btnApply) {
      btnApply.addEventListener('click', applySelected);
    }
    
    // Select top 3 button
    const btnTop3 = document.getElementById('btn-select-top3');
    if (btnTop3) {
      btnTop3.addEventListener('click', () => {
        const checkboxes = Array.from(document.querySelectorAll('.weights-checkbox:not(:disabled)'));
        checkboxes.forEach((cb, idx) => {
          cb.checked = idx < 3;
        });
        updateCount();
      });
    }
  }
  
  function updateCount() {
    const checked = document.querySelectorAll('.weights-checkbox:checked:not(:disabled)').length;
    const total = document.querySelectorAll('.weights-checkbox:not(:disabled)').length;
    const countEl = document.getElementById('weights-count');
    if (countEl) {
      countEl.textContent = `${checked} of ${total} selected`;
    }
  }
  
  function applySelected() {
    const selectedCodes = Array.from(document.querySelectorAll('.weights-checkbox:checked:not(:disabled)'))
      .map(cb => cb.dataset.code);
    
    if (selectedCodes.length === 0) {
      alert('Please select at least one deliverable to apply.');
      return;
    }
    
    // Add to selection using the global selection API
    if (window.APB && window.APB.step2 && window.APB.step2.addDeliverables) {
      window.APB.step2.addDeliverables(selectedCodes);
      
      // Show confirmation
      const btnApply = document.getElementById('btn-apply-weights');
      if (btnApply) {
        const orig = btnApply.textContent;
        btnApply.textContent = `✓ Applied ${selectedCodes.length} deliverable(s)`;
        btnApply.disabled = true;
        setTimeout(() => {
          btnApply.textContent = orig;
          btnApply.disabled = false;
          // Hide the panel after applying
          const container = document.getElementById('step2-ai-weights-container');
          if (container) container.style.display = 'none';
        }, 1500);
      }
    } else {
      alert('Selection system not ready. Please refresh and try again.');
    }
  }
  
  function getModeLabel(mode) {
    switch(mode) {
      case 'confidence_only':
        return 'AI Confidence Only';
      case 'tfidf_only':
        return 'TF-IDF Similarity Only';
      case 'both':
        return 'Both (AI + TF-IDF)';
      default:
        return 'AI Confidence Only';
    }
  }
  
  function getSelectionInfo(row, selectionMode) {
    const CONF_THRESHOLD = 70.0;
    const TFIDF_THRESHOLD = 0.70;
    
    const matchPercent = row.match_percent || 0;
    const tfidfSimilarity = row.tfidf_similarity || 0;
    
    // Check if each method would select this
    const confOk = matchPercent >= CONF_THRESHOLD;
    const tfidfOk = tfidfSimilarity >= TFIDF_THRESHOLD;
    
    let autoSelected = false;
    let badgeText = '';
    let badgeColor = '#6366f1';
    
    if (selectionMode === 'confidence_only') {
      autoSelected = confOk;
      badgeText = 'Auto (AI)';
      badgeColor = '#8b5cf6';
    } else if (selectionMode === 'tfidf_only') {
      autoSelected = tfidfOk;
      badgeText = 'Auto (TF-IDF)';
      badgeColor = '#3b82f6';
    } else if (selectionMode === 'both') {
      autoSelected = confOk || tfidfOk;
      if (confOk && tfidfOk) {
        badgeText = 'Auto (AI + TF-IDF)';
        badgeColor = '#10b981';
      } else if (confOk) {
        badgeText = 'Auto (AI)';
        badgeColor = '#8b5cf6';
      } else if (tfidfOk) {
        badgeText = 'Auto (TF-IDF)';
        badgeColor = '#3b82f6';
      }
    }
    
    return {
      autoSelected,
      badgeText,
      badgeColor,
      by_confidence: confOk,
      by_tfidf: tfidfOk
    };
  }
  
  function applySelectionMode(newMode) {
    // Re-render table rows with new selection badges
    if (!currentData) return;
    
    const tbody = document.querySelector('.weights-table tbody');
    if (!tbody) return;
    
    const alreadySelected = new Set(window.selectionStore?.deliverables.keys() || []);
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.forEach((tr, idx) => {
      // Skip detail rows (they don't have checkboxes)
      const checkbox = tr.querySelector('.weights-checkbox');
      if (!checkbox) return;
      
      const code = checkbox.dataset.code;
      const row = currentData.deliverables.find(d => d.deliverable_code === code);
      if (!row) return;
      
      const isSelected = alreadySelected.has(code);
      const selectionInfo = getSelectionInfo(row, newMode);
      
      // Update checkbox state
      if (!isSelected) {
        checkbox.checked = selectionInfo.autoSelected;
      }
      
      // Update badge
      const deliverableCell = tr.cells[2];
      if (deliverableCell) {
        const existingBadge = deliverableCell.querySelector('.badge');
        if (existingBadge && !isSelected) {
          existingBadge.remove();
        }
        
        if (!isSelected && selectionInfo.autoSelected) {
          const badge = document.createElement('span');
          badge.className = 'badge badge-auto';
          badge.style.background = selectionInfo.badgeColor;
          badge.textContent = selectionInfo.badgeText;
          deliverableCell.appendChild(document.createTextNode(' '));
          deliverableCell.appendChild(badge);
        }
      }
    });
    
    updateCount();
  }
  
  async function fetchWeightedScoresWithMode(rfpText, selectionMode, containerSelector) {
    try {
      const response = await fetch('/api/step2/ai/weights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rfp_text: rfpText,
          selection_mode: selectionMode
        })
      });
      
      if (!response.ok) {
        console.error('[TCGWeights] Failed to fetch weighted scores:', response.statusText);
        return;
      }
      
      const data = await response.json();
      console.log(`[TCGWeights] Received data with selection_mode: ${data.selection_mode}`);
      
      // Re-render with new data
      render(containerSelector, data, selectionMode);
    } catch (error) {
      console.error('[TCGWeights] Error fetching weighted scores:', error);
    }
  }
  
  return { render, fetchWeightedScoresWithMode };
})();
