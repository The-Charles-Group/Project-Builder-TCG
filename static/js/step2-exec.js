/* global window, document */
(function () {
  // ---- helpers -------------------------------------------------------------
  function fmtDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }
  function el(html) { const div = document.createElement('div'); div.innerHTML = html.trim(); return div.firstChild; }

  // Split a long scopeText into named sections
  function splitScope(scopeText) {
    if (!scopeText) return [];
    const anchors = [
      'Brand Strategy','Brand Identity','Brand Architecture','Experiential Activation',
      'Campaign Creative','Content Production','Marketing Collateral','Program Management'
    ];
    const rx = new RegExp(`(${anchors.map(a => a.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')).join('|')})`, 'i');
    const chunks = scopeText.split(rx).map(s => s && s.trim()).filter(Boolean);

    // chunks like [Title, Body, Title, Body, ...]
    const sections = [];
    for (let i = 0; i < chunks.length; i += 2) {
      const title = chunks[i];
      const body = chunks[i + 1] || '';
      sections.push({ title, summary: body });
    }
    return sections;
  }

  // ---- main render ---------------------------------------------------------
  function renderStep2Exec(data) {
    // Show the executive view container
    const execView = document.getElementById('exec-view');
    if (execView) {
      execView.style.display = 'block';
    }

    // 1) KPI strip
    const kpiStrip = document.getElementById('kpi-strip');
    if (kpiStrip) {
      kpiStrip.innerHTML = '';
      const items = [
        { label: 'Total Price', value: data.priceFormatted || data.price },
        { label: 'Duration', value: data.durationText },
        { label: 'Window', value: `${fmtDate(data.startDate)} → ${fmtDate(data.endDate)}` }
      ];
      items.forEach(k => {
        kpiStrip.appendChild(el(`<div class="kpi"><span class="val">${k.value ?? '—'}</span><span>${k.label}</span></div>`));
      });
    }

    // 2) Overview card
    const ov = document.getElementById('overview-card');
    if (ov) {
      const highlights = (data.highlights || []).slice(0,3).map(h => `<li>${h}</li>`).join('') || '<li>Executive-ready summary</li>';
      const channels = (data.channels || []).join(', ');
      const markets  = (data.markets || []).join(', ');
      ov.innerHTML = `
        <h3 class="card-title">Overview</h3>
        <p><strong>Goal:</strong> ${data.goal || 'Fast analysis'}</p>
        <p><strong>Channels:</strong> ${channels || '—'} &nbsp; • &nbsp; <strong>Markets:</strong> ${markets || '—'}</p>
        <ul class="list">${highlights}</ul>
      `;
    }

    // 3) Scope accordion
    const acc = document.getElementById('scope-accordion');
    if (!acc) return;
    
    acc.innerHTML = '';
    const sections = data.sections?.length ? data.sections : splitScope(data.scopeText || data.summaryText);
    sections.forEach((s, idx) => {
      const node = el(`
        <div class="item">
          <div class="head" data-index="${idx}">
            <h4>${s.title}</h4>
            <button class="button-link" data-action="expand" data-index="${idx}">View details</button>
          </div>
          <div class="preview">${(s.summary || '').replace(/\n/g,'<br>')}</div>
        </div>
      `);
      acc.appendChild(node);
    });

    // Drawer wiring
    const drawer = document.getElementById('details-drawer');
    const backdrop = document.getElementById('drawer-backdrop');
    const summaryPanel = document.getElementById('panel-summary');
    const componentsPanel = document.getElementById('panel-components');
    const risksPanel = document.getElementById('panel-risks');
    const tabButtons = drawer.querySelectorAll('.tab');

    function openDrawer(idx) {
      const s = sections[idx];
      summaryPanel.innerHTML = `<div>${(s.summary || '').replace(/\n/g,'<br>')}</div>`;
      // components tab
      if (Array.isArray(s.components) && s.components.length) {
        document.getElementById('tab-components').hidden = false;
        componentsPanel.innerHTML = `
          <table class="table">
            <thead><tr><th>Component</th><th>Hours</th><th>Owner</th><th>Notes</th></tr></thead>
            <tbody>
              ${s.components.map(r => `<tr><td>${r.name||''}</td><td>${r.hours??''}</td><td>${r.owner||''}</td><td>${r.notes||''}</td></tr>`).join('')}
            </tbody>
          </table>`;
      } else {
        document.getElementById('tab-components').hidden = true;
        componentsPanel.innerHTML = '';
      }
      // risks tab
      const risks = s.risks || data.risks || [];
      risksPanel.innerHTML = risks.length ? `<ul>${risks.map(r=>`<li>${r}</li>`).join('')}</ul>` : '<p>No major risks identified.</p>';

      drawer.classList.add('open');
      backdrop.hidden = false;
      drawer.setAttribute('aria-hidden','false');
      activateTab('summary');
    }
    function closeDrawer() {
      drawer.classList.remove('open');
      backdrop.hidden = true;
      drawer.setAttribute('aria-hidden','true');
    }
    function activateTab(id) {
      tabButtons.forEach(b => {
        const active = b.dataset.tab === id;
        b.classList.toggle('active', active);
        document.getElementById(`panel-${b.dataset.tab}`).hidden = !active;
      });
    }

    acc.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action="expand"]');
      if (btn) openDrawer(Number(btn.dataset.index));
    });
    drawer.querySelector('.drawer-close').addEventListener('click', closeDrawer);
    backdrop.addEventListener('click', closeDrawer);
    drawer.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawer(); });
    drawer.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => activateTab(b.dataset.tab)));
  }

  // ---- init hook -----------------------------------------------------------
  // Call this with your existing Step-2 data object once it's loaded.
  window.renderStep2Exec = renderStep2Exec;
})();
