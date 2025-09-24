let OPTIONS = null;       // cached /api/options
let SCENARIOS = null;     // last built scenarios (A & B)
let DELIVERABLES = [];    // [{deliverable_code, deliverable, category}]

async function api(path, opts={}) {
  const res = await fetch(path, {headers:{"Content-Type":"application/json"}, ...opts});
  if(!res.ok){ throw new Error(await res.text()); }
  const ct = res.headers.get("content-type") || "";
  if(ct.includes("application/json")) return res.json();
  return res.text();
}

function el(html){ const t=document.createElement('template'); t.innerHTML=html.trim(); return t.content.firstChild; }

function currency(n){ return `$${Number(n||0).toLocaleString()}`; }

async function boot() {
  await api("/api/load");
  OPTIONS = await api("/api/options");
  // Populate dropdowns
  const pricingMode = document.querySelector("#pricingMode");
  OPTIONS.pricing_modes.forEach(m => pricingMode.append(el(`<option>${m}</option>`)));
  const rateBand = document.querySelector("#rateBand");
  OPTIONS.rate_bands.forEach(b => rateBand.append(el(`<option>${b}</option>`)));
  // Scenario templates
  const sA = document.querySelector("#scenarioA");
  const sB = document.querySelector("#scenarioB");
  OPTIONS.scenario_templates.forEach(s => {
    sA.append(el(`<option value="${s.Scenario_Key}">${s.Scenario_Key} (${s.Complexity}×${s.Tier})</option>`));
    sB.append(el(`<option value="${s.Scenario_Key}">${s.Scenario_Key} (${s.Complexity}×${s.Tier})</option>`));
  });
  // Defaults: MED_LOW / MED_HIGH
  if(OPTIONS.scenario_templates.find(x => x.Scenario_Key==="MED_LOW")) sA.value="MED_LOW";
  if(OPTIONS.scenario_templates.find(x => x.Scenario_Key==="MED_HIGH")) sB.value="MED_HIGH";

  // Deliverables list
  DELIVERABLES = OPTIONS.deliverables;
  renderDeliverableList(DELIVERABLES);

  // Pricing default blended
  const ps = OPTIONS.pricing_settings.find(x => x.Key==="Default_Blended_Rate");
  if(ps) document.querySelector("#blendedRate").value = ps.Default;

  // Slack defaults
  const ss = Object.fromEntries(OPTIONS.slack_settings.map(x => [x.Key, x.Default]));
  document.querySelector("#useSlack").checked = !!ss["Use_Slack"];
  document.querySelector("#slackInternal").value = ss["Slack_After_Internal_Review_Days"] ?? 1;
  document.querySelector("#slackClient").value   = ss["Slack_After_Client_Review_Days"] ?? 2;
  document.querySelector("#slackGlobal").value   = ss["Slack_Global_Percent"] ?? 0.05;

  // UI wiring
  document.querySelector("#btnSuggest").onclick = onSuggest;
  document.querySelector("#btnBuild").onclick   = onBuild;
  document.querySelector("#pricingMode").onchange = onPricingModeChanged;
  document.querySelector("#useTemplates").onchange = onScenarioTypeChanged;
  document.querySelector("#useBundles").onchange   = onScenarioTypeChanged;
  document.querySelector("#btnExportA").onclick = () => onExport('A');
  document.querySelector("#btnExportB").onclick = () => onExport('B');
  onPricingModeChanged();
}

function onPricingModeChanged(){
  const mode = document.querySelector("#pricingMode").value;
  document.querySelector("#blendedWrap").classList.toggle("hidden", mode!=="Flat_Blended");
  document.querySelector("#bandWrap").classList.toggle("hidden", mode!=="Per_Resource");
}

function onScenarioTypeChanged(){
  const useTemplates = document.querySelector("#useTemplates").checked;
  document.querySelector("#templateRow").classList.toggle("hidden", !useTemplates);
  document.querySelector("#bundleRow").classList.toggle("hidden", useTemplates);
}

function renderDeliverableList(items){
  const box = document.querySelector("#deliverableList");
  box.innerHTML = "";
  items.forEach(d => {
    const id = `deliv_${d.Deliverable_Code}`;
    box.append(el(`
      <div class="row">
        <input type="checkbox" id="${id}" data-code="${d.Deliverable_Code}"/>
        <label for="${id}"><strong>${d.Deliverable}</strong> <small class="badge">${d.Category}</small></label>
      </div>
    `));
  });
}

async function onSuggest(){
  const txt = document.querySelector("#rfpText").value || "";
  const data = await api("/api/suggest_by_text", {method:"POST", body:JSON.stringify({rfp_text:txt})});
  const sugg = document.querySelector("#suggestions");
  sugg.innerHTML = "";
  (data.suggested || []).forEach(s => {
    sugg.append(el(`<span class="pill">${s.deliverable}<span class="hit">+${s.confidence}</span></span>`));
    // pre-check matching deliverables
    const elx = document.querySelector(`#deliv_${s.deliverable_code}`);
    if(elx) elx.checked = true;
  });
}

function selectedDeliverables(){
  return Array.from(document.querySelectorAll("#deliverableList input[type=checkbox]:checked"))
    .map(x => x.dataset.code);
}

async function onBuild(){
  const codes = selectedDeliverables();
  if(codes.length===0){ alert("Select at least one deliverable."); return; }

  const pricingMode = document.querySelector("#pricingMode").value;
  const blendedRate = Number(document.querySelector("#blendedRate").value || 0) || null;
  const rateBand    = document.querySelector("#rateBand").value;

  const useSlack    = document.querySelector("#useSlack").checked;
  const slackInternal = Number(document.querySelector("#slackInternal").value || 0);
  const slackClient   = Number(document.querySelector("#slackClient").value || 0);
  const slackGlobal   = Number(document.querySelector("#slackGlobal").value || 0);
  const projectStart  = document.querySelector("#projectStart").value || null;

  // Scenario specs
  const useTemplates = document.querySelector("#useTemplates").checked;
  let specA, specB;
  if(useTemplates){
    specA = {mode:"template", scenario_key: document.querySelector("#scenarioA").value};
    specB = {mode:"template", scenario_key: document.querySelector("#scenarioB").value};
  } else {
    specA = {mode:"bundle", bundle: document.querySelector("#bundleA").value};
    specB = {mode:"bundle", bundle: document.querySelector("#bundleB").value};
  }

  const payload = {
    selected_deliverable_codes: codes,
    scenario_a: specA,
    scenario_b: specB,
    pricing_mode: pricingMode,
    blended_rate: blendedRate,
    rate_band: rateBand,
    use_slack: useSlack,
    slack_after_internal: slackInternal,
    slack_after_client: slackClient,
    slack_global_pct: slackGlobal,
    project_start: projectStart
  };

  const res = await api("/api/build", {method:"POST", body:JSON.stringify(payload)});
  SCENARIOS = res;
  renderScenarios(res);
  
  // Store scenarios globally for timeline and export
  window.appState = window.appState || {};
  window.appState.scenarios = res;
  
  // Show timeline step and render timeline for Scenario A
  document.querySelector("#step4").style.display = "block";
  selectTimeline('A');
}

function renderScenarios(data){
  const box = document.querySelector("#scenarios");
  box.innerHTML = "";
  ["A","B"].forEach(key => {
    const scn = data[key];
    const head = `
      <h3>Scenario ${key} <span class="badge">${scn.pricing_mode}${scn.pricing_mode==='Per_Resource' ? ' · ' + scn.rate_band : ''}</span>
        ${scn.pricing_mode==='Flat_Blended' ? `<span class="badge">${Number(scn.blended_rate||0).toFixed(0)}/hr</span>`:''}
      </h3>
      <div><strong>Total Hours:</strong> ${Number(scn.totals.hours).toFixed(2)} &nbsp; <strong>Total Price:</strong> ${currency(scn.totals.price)}</div>
    `;
    const wrap = el(`<div class="scenario">${head}<div></div></div>`);

    scn.items.forEach(d => {
      const tgPills = d.included_task_groups.map(tg => `<span class="pill">${tg}</span>`).join(" ");
      const rows = (d.hours_by_role||[]).map(r => `
        <tr><td>${r.Resource_Title} <small class="badge">${r.Seniority}</small></td><td>${Number(r.Hours).toFixed(2)}</td></tr>
      `).join("");
      const sched = (d.schedule||[]).map(s => `
        <tr><td>${s.task_group}</td><td>${s.start_date}</td><td>${s.end_date}</td><td>${s.duration_days}</td></tr>
      `).join("");
      const card = el(`
        <div class="card" style="background:#0f141d;">
          <h4>${d.deliverable} <span class="badge">${d.category}</span> <span class="badge">${d.complexity}×${d.tier}</span></h4>
          <div class="inline">${tgPills}</div>
          <table class="tbl"><thead><tr><th>Role</th><th>Hours</th></tr></thead><tbody>${rows || '<tr><td colspan="2">No hours</td></tr>'}</tbody></table>
          <div class="inline"><strong>Deliverable Total Hours:</strong> ${Number(d.total_hours).toFixed(2)} &nbsp; <strong>Price:</strong> ${currency(d.price)}</div>
          <details>
            <summary>Timeline (auto)</summary>
            <table class="tbl"><thead><tr><th>Task Group</th><th>Start</th><th>End</th><th>Days</th></tr></thead><tbody>${sched || '<tr><td colspan="4">No schedule</td></tr>'}</tbody></table>
          </details>
        </div>
      `);
      wrap.append(card);
    });

    box.append(wrap);
  });

  document.querySelector("#totA").innerText = currency(data.A.totals.price);
  document.querySelector("#totB").innerText = currency(data.B.totals.price);
}

async function onExport(which){
  if(!SCENARIOS){ alert("Build scenarios first."); return; }
  const res = await fetch("/api/export", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({scenario: SCENARIOS[which]})
  });
  if(!res.ok){ alert("Export failed"); return; }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `workfront_export_${which}.csv`;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

// Timeline functionality
function getScenario(letter) {
  return window.appState?.scenarios?.[letter];
}

function renderTimeline(letter) {
  const scen = getScenario(letter);
  const box = document.getElementById('timeline');
  
  if (!scen) {
    box.innerHTML = '<em>Build scenarios in Step 3 to see a timeline.</em>';
    return;
  }

  const header = `<div class="timeline-head">
    <strong>Scenario ${letter}</strong> · Deliverables: ${(scen.items || []).length}
  </div>`;

  // Build draggable rows, one per deliverable
  const table = `<table id="tl-table" class="table-compact">
    <thead>
      <tr><th>Deliverable</th><th>Start Date</th><th>End Date</th><th>Total Days</th></tr>
    </thead>
    <tbody id="tl-body"></tbody>
  </table>`;

  box.innerHTML = header + table;

  const body = document.getElementById('tl-body');
  body.innerHTML = (scen.items || []).map(d => {
    const sch = d.schedule || [];
    const start = sch[0]?.start_date ?? '';
    const end   = sch[sch.length - 1]?.end_date ?? '';
    const days  = sch.reduce((n,s)=>n+(s.duration_days||0),0);
    return `<tr class="tl-row" draggable="true" data-dcode="${d.deliverable_code}">
      <td>${d.deliverable}</td><td>${start}</td><td>${end}</td><td>${days}</td>
    </tr>`;
  }).join('');

  enableTimelineDnD(letter);
  renderTimelineStatus(letter);
}

function enableTimelineDnD(letter) {
  const body = document.getElementById('tl-body');
  let dragEl = null;

  body.querySelectorAll('.tl-row').forEach(row => {
    row.addEventListener('dragstart', e => {
      dragEl = row;
      e.dataTransfer.effectAllowed = 'move';
      row.classList.add('dragging');
    });
    row.addEventListener('dragend', () => row.classList.remove('dragging'));
    row.addEventListener('dragover', e => {
      e.preventDefault();
      const after = getDragAfterElement(body, e.clientY);
      if (!after) body.appendChild(dragEl);
      else body.insertBefore(dragEl, after);
    });
  });

  function getDragAfterElement(container, y) {
    const els = [...container.querySelectorAll('.tl-row:not(.dragging)')];
    return els.reduce((closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      return (offset < 0 && offset > closest.offset) ? { offset, element: child } : closest;
    }, { offset: Number.NEGATIVE_INFINITY }).element;
  }

  // Save + recompute schedule
  document.getElementById('timeline-controls')?.querySelector('#tl-save')?.remove();
  const btn = document.createElement('button');
  btn.id = 'tl-save'; btn.textContent = 'Save Order';
  btn.onclick = async () => {
    const scenario = getScenario(letter);
    if (!scenario) return;

    // Get ordered deliverable codes from UI
    const rows = [...body.querySelectorAll('.tl-row')];
    const codes = rows.map(tr => tr.dataset.dcode);
    
    // Build included_map from current scenario items
    const includedMap = Object.fromEntries(
      scenario.items.map(item => [item.deliverable_code, item.included_task_groups ?? []])
    );

    // Get knobs from current scenario (these are the authoritative values)
    const knobs = {
      project_start: scenario.project_start,
      complexity: scenario.items[0]?.complexity,  // Use first item's complexity as default
      tier: scenario.items[0]?.tier,  // Use first item's tier as default
      use_slack: scenario.use_slack,
      slack_after_internal: scenario.slack_after_internal,
      slack_after_client: scenario.slack_after_client,
      slack_global_pct: scenario.slack_global_pct
    };

    const payload = {
      scenario_letter: letter,
      deliverable_codes: codes,
      included_map: includedMap,
      project_start: knobs.project_start,
      complexity: knobs.complexity,
      tier: knobs.tier,
      use_slack: knobs.use_slack,
      slack_after_internal: knobs.slack_after_internal,
      slack_after_client: knobs.slack_after_client,
      slack_global_pct: knobs.slack_global_pct
    };

    const res = await fetch('/api/reorder_timeline', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    }).then(r => r.json());

    // Replace local items with server-persisted order + dates
    if (res.items && window.appState.scenarios[letter]) {
      window.appState.scenarios[letter] = {
        ...window.appState.scenarios[letter],
        items: res.items,
        user_order: codes,
        manual_order_locked: true
      };
    }
    renderTimeline(letter);
  };
  document.getElementById('timeline-controls')?.appendChild(btn);
}

function renderTimelineStatus(letter) {
  const scen = getScenario(letter);
  const box = document.getElementById('timeline-status');
  if (!scen) { box.innerHTML = ''; return; }

  // Sum days by deliverable
  const stats = (scen.items || []).map(d => {
    const days = (d.schedule || []).reduce((n,s)=>n+(s.duration_days||0),0);
    return { label: d.deliverable, days };
  });
  const total = stats.reduce((n,s)=>n+s.days,0) || 1;
  const rows = stats
    .sort((a,b)=>b.days-a.days)
    .map(s => {
      const pct = Math.round((100*s.days)/total);
      return `<div class="stat">
        <div class="label">${s.label}</div>
        <div class="bar"><span style="width:${pct}%"></span></div>
        <div class="pct">${pct}%</div>
      </div>`;
    }).join('');
  box.innerHTML = `<h4>Time Allocation (Scenario ${letter})</h4>${rows}`;
}

function selectTimeline(letter) {
  renderTimeline(letter);
  document.querySelectorAll('[data-timeline-sel]')
    .forEach(btn => btn.classList.toggle('active', btn.dataset.timelineSel === letter));
}

// Event delegation for timeline controls
document.addEventListener('click', e => {
  const btn = e.target.closest('[data-timeline-sel]');
  if (!btn) return;
  selectTimeline(btn.dataset.timelineSel);  // 'A' or 'B'
});

window.addEventListener("load", boot);