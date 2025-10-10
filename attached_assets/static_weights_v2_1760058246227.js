
window.TCGWeightsV2 = (function () {
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

    wrap.innerHTML = `<h3>AI Match — Deliverables (sparsity-calibrated)</h3>
      <div class="tcg-note">Top departments: <b>${(meta.top_departments||[]).join(', ')}</b>${meta.budget ? ` • Budget detected: <b>$${Number(meta.budget).toLocaleString()}</b>` : ''}</div>`;

    const table = document.createElement('table');
    table.className = 'tcg-weights-table';
    table.innerHTML = `<thead><tr>
      <th>Service Dept</th><th>Deliverable</th><th style="text-align:right">Match %</th>
    </tr></thead>`;
    const tbody = document.createElement('tbody');

    rows.forEach((row, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${esc(row.service_department||'')}</td>
                      <td><strong>${esc(row.deliverable||'')}</strong></td>
                      <td style="text-align:right"><strong>${Number(row.match_percent||0).toFixed(1)}%</strong></td>`;
      tbody.appendChild(tr);

      if (i < 6) {
        const compList = comps[row.deliverable_code] || [];
        const trc = document.createElement('tr');
        const tdc = document.createElement('td');
        tdc.colSpan = 3;
        tdc.innerHTML = `<div class="tcg-subhead">Top Components (L1)</div>` + compList.slice(0,5).map(c => 
          `<div class="tcg-chip">${esc(c.component||'')}: <span class="tcg-chip-pct">${Number(c.percent||0).toFixed(1)}%</span></div>`
        ).join('');
        trc.appendChild(tdc);
        tbody.appendChild(trc);

        const tList = tasks[row.deliverable_code] || [];
        const trt = document.createElement('tr');
        const tdt = document.createElement('td');
        tdt.colSpan = 3;
        tdt.innerHTML = `<div class="tcg-subhead">Top Tasks (L2)</div>` + tList.slice(0,8).map(t => 
          `<div class="tcg-chip">${esc(t.component||'')} → ${esc(t.task||'')}: <span class="tcg-chip-pct">${Number(t.percent||0).toFixed(1)}%</span></div>`
        ).join('');
        trt.appendChild(tdt);
        tbody.appendChild(trt);
      }
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    el.innerHTML = '';
    el.appendChild(wrap);

    const legend = document.createElement('div');
    legend.className = 'tcg-legend';
    legend.innerHTML = `<div><b>Bands:</b> High (≥85%) — Strong fit • Mid (70–84%) — Consider • Low (&lt;70%) — Usually exclude</div>`;
    wrap.appendChild(legend);
  }

  function esc(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
  return { render };
})();
