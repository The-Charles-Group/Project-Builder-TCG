
// weights.js — interactive UI for weighted AI deliverable suggestions
window.TCGWeights = (function(){
  let currentData = null;
  
  function _el(html){
    const t = document.createElement('template');
    t.innerHTML = html.trim();
    return t.content.firstChild;
  }
  
  function render(containerSelector, data){
    currentData = data;
    const c = document.querySelector(containerSelector);
    if(!c){ console.warn('weights container not found', containerSelector); return; }
    c.innerHTML = '';
    
    // Check which deliverables are already selected
    const alreadySelected = new Set(window.selectionStore?.deliverables.keys() || []);
    
    // Filter to show top matches (>= 50% match)
    const topMatches = (data.deliverables || []).filter(d => d.match_percent >= 50);
    
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
      
      tr.innerHTML = `
        <td>
          <input type="checkbox" 
                 class="weights-checkbox" 
                 data-code="${row.deliverable_code}"
                 ${isSelected ? 'checked disabled' : ''} />
        </td>
        <td>${row.service_department||''}</td>
        <td>
          ${row.deliverable||row.deliverable_code}
          ${isSelected ? '<span class="badge">Selected</span>' : ''}
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
  
  return { render };
})();
