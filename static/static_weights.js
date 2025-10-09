
// weights.js — tiny UI helper to show match percentages in Step 2
// Usage example:
//   fetch('/api/step2/ai/weights', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({rfp_text})})
//     .then(r=>r.json()).then(data => TCGWeights.render('#step2A-weights', data));

window.TCGWeights = (function(){
  function _el(html){
    const t = document.createElement('template');
    t.innerHTML = html.trim();
    return t.content.firstChild;
  }
  function render(containerSelector, data){
    const c = document.querySelector(containerSelector);
    if(!c){ console.warn('weights container not found', containerSelector); return; }
    c.innerHTML = '';
    const table = _el('<table class="weights-table"><thead><tr><th>Service Dept</th><th>Deliverable</th><th>Match %</th></tr></thead><tbody></tbody></table>');
    const tbody = table.querySelector('tbody');
    (data.deliverables || []).forEach(row => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${row.service_department||''}</td>
                      <td>${row.deliverable||row.deliverable_code}</td>
                      <td><strong>${row.match_percent.toFixed(1)}%</strong></td>`;
      tbody.appendChild(tr);
      // Add expandable top components and tasks for context
      const comps = (data.components && data.components[row.deliverable_code]) || [];
      const tasks = (data.tasks && data.tasks[row.deliverable_code]) || [];
      if(comps.length || tasks.length){
        const detail = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 3;
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
  }
  return { render };
})();
