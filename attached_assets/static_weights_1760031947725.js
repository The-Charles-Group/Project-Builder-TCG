
window.TCGWeights = (function () {
  function render(containerSelector, data) {
    const el = document.querySelector(containerSelector);
    if (!el) return;
    const d = data || {};
    const rows = d.deliverables || [];
    const comps = d.components || {};
    const tasks = d.tasks || {};

    const wrap = document.createElement('div');
    wrap.className = 'tcg-weights';

    const h = document.createElement('h3');
    h.textContent = 'AI Match — Deliverables (with Service Department)';
    wrap.appendChild(h);

    const table = document.createElement('table');
    table.className = 'tcg-weights-table';
    const thead = document.createElement('thead');
    thead.innerHTML = `<tr>
      <th>Service Dept</th>
      <th>Deliverable</th>
      <th style="text-align:right">Match %</th>
    </tr>`;
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    rows.forEach(row => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${escapeHtml(row.service_department || '')}</td>
                      <td><strong>${escapeHtml(row.deliverable || '')}</strong></td>
                      <td style="text-align:right"><strong>${Number(row.match_percent||0).toFixed(1)}%</strong></td>`;
      tbody.appendChild(tr);

      const compList = comps[row.deliverable_code] || [];
      if (compList.length) {
        const trc = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 3;
        td.innerHTML = `<div class="tcg-subhead">Top Components (L1)</div>` + compList.slice(0,5).map(c => {
          return `<div class="tcg-chip">${escapeHtml(c.component||'')}: <span class="tcg-chip-pct">${Number(c.percent||0).toFixed(1)}%</span></div>`;
        }).join('');
        trc.appendChild(td);
        tbody.appendChild(trc);
      }

      const taskList = tasks[row.deliverable_code] || [];
      if (taskList.length) {
        const trt = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 3;
        td.innerHTML = `<div class="tcg-subhead">Top Tasks (L2)</div>` + taskList.slice(0,8).map(t => {
          return `<div class="tcg-chip">${escapeHtml(t.component||'')} → ${escapeHtml(t.task||'')}: <span class="tcg-chip-pct">${Number(t.percent||0).toFixed(1)}%</span></div>`;
        }).join('');
        trt.appendChild(td);
        tbody.appendChild(trt);
      }
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    el.innerHTML = '';
    el.appendChild(wrap);
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (m) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]);
    });
  }

  return { render };
})();
