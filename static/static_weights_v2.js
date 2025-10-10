/**
 * TCG Weights V2 UI Renderer
 * Displays AI relevance results with department context, budget awareness, and band indicators
 */

window.TCGWeightsV2 = (function () {
  
  /**
   * Render AI weights v2 results into container
   * @param {string} containerSelector - CSS selector for container element
   * @param {object} data - Results from /api/step2/ai/weights_v2
   */
  function render(containerSelector, data) {
    const el = document.querySelector(containerSelector);
    if (!el) return;
    
    const d = data || {};
    const rows = d.deliverables || [];
    const comps = d.components || {};
    const tasks = d.tasks || {};
    const meta = d.meta || {};
    
    const wrap = document.createElement('div');
    wrap.className = 'tcg-weights';
    
    // Header with metadata
    const deptList = (meta.top_departments || []).join(', ') || 'None detected';
    const budgetText = meta.budget ? ` • Budget detected: <b>$${Number(meta.budget).toLocaleString()}</b>` : '';
    
    wrap.innerHTML = `<h3>🤖 AI Match V2 — Deliverables (Sparse, Calibrated)</h3>
      <div class="tcg-note">Top departments: <b>${esc(deptList)}</b>${budgetText}</div>`;
    
    // Results table
    const table = document.createElement('table');
    table.className = 'tcg-weights-table';
    table.innerHTML = `<thead><tr>
      <th>Service Dept</th>
      <th>Deliverable</th>
      <th style="text-align:right">Match %</th>
    </tr></thead>`;
    
    const tbody = document.createElement('tbody');
    
    rows.forEach((row, i) => {
      // Deliverable row
      const tr = document.createElement('tr');
      const matchPct = Number(row.match_percent || 0).toFixed(1);
      const bandClass = matchPct >= 85 ? 'high' : matchPct >= 70 ? 'mid' : 'low';
      
      tr.innerHTML = `
        <td>${esc(row.service_department || '')}</td>
        <td><strong>${esc(row.deliverable || '')}</strong></td>
        <td style="text-align:right">
          <strong style="color: ${getBandColor(matchPct)}">${matchPct}%</strong>
        </td>`;
      tbody.appendChild(tr);
      
      // Show components and tasks for top 6 deliverables
      if (i < 6) {
        const compList = comps[row.deliverable_code] || [];
        if (compList.length > 0) {
          const trc = document.createElement('tr');
          const tdc = document.createElement('td');
          tdc.colSpan = 3;
          tdc.innerHTML = `<div class="tcg-subhead">Top Components (L1)</div>` + 
            compList.slice(0, 5).map(c => 
              `<div class="tcg-chip">${esc(c.component || '')}: <span class="tcg-chip-pct">${Number(c.percent || 0).toFixed(1)}%</span></div>`
            ).join('');
          trc.appendChild(tdc);
          tbody.appendChild(trc);
        }
        
        const tList = tasks[row.deliverable_code] || [];
        if (tList.length > 0) {
          const trt = document.createElement('tr');
          const tdt = document.createElement('td');
          tdt.colSpan = 3;
          tdt.innerHTML = `<div class="tcg-subhead">Top Tasks (L2)</div>` + 
            tList.slice(0, 8).map(t => 
              `<div class="tcg-chip">${esc(t.component || '')} → ${esc(t.task || '')}: <span class="tcg-chip-pct">${Number(t.percent || 0).toFixed(1)}%</span></div>`
            ).join('');
          trt.appendChild(tdt);
          tbody.appendChild(trt);
        }
      }
    });
    
    table.appendChild(tbody);
    wrap.appendChild(table);
    
    // Legend
    const legend = document.createElement('div');
    legend.className = 'tcg-legend';
    legend.innerHTML = `<div><b>Bands:</b> 
      <span style="color: #10b981">High (≥85%)</span> — Strong fit • 
      <span style="color: #f59e0b">Mid (70–84%)</span> — Consider • 
      <span style="color: #6b7280">Low (&lt;70%)</span> — Usually exclude
    </div>`;
    wrap.appendChild(legend);
    
    // Replace container content
    el.innerHTML = '';
    el.appendChild(wrap);
  }
  
  /**
   * Get color for match percentage band
   */
  function getBandColor(pct) {
    if (pct >= 85) return '#10b981'; // Green - High
    if (pct >= 70) return '#f59e0b'; // Amber - Mid
    return '#6b7280'; // Gray - Low
  }
  
  /**
   * Escape HTML entities
   */
  function esc(s) {
    return String(s).replace(/[&<>"']/g, m => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[m]));
  }
  
  return { render };
})();
