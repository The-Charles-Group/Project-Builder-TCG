let OPTIONS = null;       // cached /api/options
let SCENARIOS = null;     // last built scenarios (A & B)
let DELIVERABLES = [];    // [{deliverable_code, deliverable, category}]

// Step 2 component state (from blueprint)
let selectedCodes = [];   // The authoritative list passed to /api/build
let removedCodes = [];    // "soft delete" items (show in "Removed" bucket with Undo)
let addedCodes = [];      // Track what the user explicitly added (optional, for UX badges/telemetry)

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

  // Initialize Step 2 state
  selectedCodes = [];
  removedCodes = [];
  addedCodes = [];
  renderStep2UI();

  // Pricing default blended
  const ps = OPTIONS.pricing_settings.find(x => x.Key==="Default_Blended_Rate");
  if(ps) document.querySelector("#blendedRate").value = ps.Default;

  // Slack defaults
  const ss = Object.fromEntries(OPTIONS.slack_settings.map(x => [x.Key, x.Default]));
  document.querySelector("#useSlack").checked = !!ss["Use_Slack"];
  document.querySelector("#slackInternal").value = ss["Slack_After_Internal_Review_Days"] ?? 1;
  document.querySelector("#slackClient").value   = ss["Slack_After_Client_Review_Days"] ?? 2;
  document.querySelector("#slackGlobal").value   = ss["Slack_Global_Percent"] ?? 0.05;

  // UI wiring (original)
  document.querySelector("#btnSuggest").onclick = onSuggest;
  document.querySelector("#btnBuild").onclick   = onBuild;
  document.querySelector("#pricingMode").onchange = onPricingModeChanged;
  document.querySelector("#useTemplates").onchange = onScenarioTypeChanged;
  document.querySelector("#useBundles").onchange   = onScenarioTypeChanged;
  document.querySelector("#btnExportA").onclick = () => onExport('A');
  document.querySelector("#btnExportB").onclick = () => onExport('B');

  // UI wiring (new Step 2)
  const proceedBtn = document.querySelector("#btnProceedToStep3");
  if (proceedBtn) proceedBtn.onclick = onProceedToStep3;
  
  const reconcileBtn = document.querySelector("#btnRunReconcile");
  if (reconcileBtn) reconcileBtn.onclick = onRunReconcile;

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
  if (!box) return; // Element doesn't exist, skip rendering
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

// Step 2 workflow functions
function onProceedToStep3() {
  if (selectedCodes.length === 0) {
    alert("Please select at least one deliverable before proceeding to pricing.");
    return;
  }
  
  // Hide Step 2 and show Step 3
  const step2 = document.querySelector("#step2");
  const step3 = document.querySelector("#step3");
  
  if (step2) step2.style.display = "none";
  if (step3) {
    step3.style.display = "block";
    step3.scrollIntoView({ behavior: "smooth" });
  }
}

async function onRunReconcile() {
  const txt = document.querySelector("#rfpText").value || "";
  if (!txt.trim()) {
    alert("Please enter RFP text first to get AI suggestions.");
    return;
  }

  try {
    // Get AI suggestions
    const data = await api("/api/suggest_by_text", {method:"POST", body:JSON.stringify({rfp_text:txt})});
    
    // Update AI Suggestions panel
    const suggestions = document.querySelector("#aiSuggestions");
    suggestions.innerHTML = "<h3>AI Suggestions</h3>";
    
    if (data.suggested && data.suggested.length > 0) {
      data.suggested.forEach(s => {
        const isSelected = selectedCodes.includes(s.deliverable_code);
        const item = el(`
          <div class="row ${isSelected ? 'selected' : ''}">
            <div>
              <strong>${s.deliverable}</strong> 
              <small class="badge">${s.category}</small>
              <br><small>Confidence: ${s.confidence}</small>
            </div>
            ${isSelected ? '<span class="already-selected">✓ Selected</span>' : 
              `<button onclick="onAdd('${s.deliverable_code}')" class="add-btn">Add</button>`}
          </div>
        `);
        suggestions.append(item);
      });
      
      // Auto-add highly confident suggestions
      data.suggested.forEach(s => {
        if (s.confidence >= 0.7 && !selectedCodes.includes(s.deliverable_code)) {
          onAdd(s.deliverable_code);
        }
      });
    } else {
      suggestions.append(el(`<p>No AI suggestions found. Try using the search function on the right.</p>`));
    }
    
    // Call reconcile API for additional suggestions  
    const reconData = await api("/api/reconcile", {
      method:"POST", 
      body:JSON.stringify({
        summary_deliverables: data.suggested ? data.suggested.map(s => s.deliverable) : [],
        db_selected_deliverable_codes: selectedCodes
      })
    });
    
    // Add reconcile suggestions to the middle panel
    if (reconData.add && reconData.add.length > 0) {
      const addSection = el(`<div style="margin-top: 16px;"><h4>Additional Suggestions</h4></div>`);
      suggestions.append(addSection);
      
      reconData.add.forEach(item => {
        const isSelected = selectedCodes.includes(item.code);
        const reconItem = el(`
          <div class="row ${isSelected ? 'selected' : ''}">
            <div>
              <strong>${item.label}</strong>
              <br><small>${item.reason}</small>
            </div>
            ${isSelected ? '<span class="already-selected">✓ Selected</span>' : 
              `<button onclick="onAdd('${item.code}')" class="add-btn">Add</button>`}
          </div>
        `);
        suggestions.append(reconItem);
      });
    }
    
    if (reconData.delete && reconData.delete.length > 0) {
      const deleteSection = el(`<div style="margin-top: 16px;"><h4>Consider Removing</h4></div>`);
      suggestions.append(deleteSection);
      
      reconData.delete.forEach(item => {
        const isSelected = selectedCodes.includes(item.code);
        if (isSelected) {
          const deleteItem = el(`
            <div class="row danger">
              <div>
                <strong>${item.label}</strong>
                <br><small>${item.reason}</small>
              </div>
              <button onclick="onRemove('${item.code}')" class="remove-btn">Remove</button>
            </div>
          `);
          suggestions.append(deleteItem);
        }
      });
    }
    
  } catch (error) {
    alert("Error getting AI suggestions: " + error.message);
  }
}

async function onSuggest(){
  // Updated to work with new Step 2 system
  // Show Step 2 first
  const step2 = document.querySelector("#step2");
  if (step2) {
    step2.style.display = "block";
    step2.scrollIntoView({ behavior: "smooth" });
  }
  
  // Then run AI analysis
  await onRunReconcile();
}

// UI behaviors from blueprint
function onRemove(code) {
  selectedCodes = selectedCodes.filter(c => c !== code);
  if (!removedCodes.includes(code)) {
    removedCodes = [...removedCodes, code];
  }
  renderStep2UI();
}

function onRestore(code) {
  removedCodes = removedCodes.filter(c => c !== code);
  if (!selectedCodes.includes(code)) {
    selectedCodes = [...selectedCodes, code];
  }
  renderStep2UI();
}

function onAdd(code) {
  removedCodes = removedCodes.filter(c => c !== code); // un-soft-delete if needed
  if (!selectedCodes.includes(code)) {
    selectedCodes = [...selectedCodes, code];
  }
  if (!addedCodes.includes(code)) {
    addedCodes = [...addedCodes, code];
  }
  renderStep2UI();
}

function selectedDeliverables(){
  // Updated to use new state model
  return selectedCodes;
}

// Initialize Step 2 UI when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  if (document.querySelector('#yourSelection')) {
    renderStep2UI();
  }
});

// New Step 2 UI renderer (blueprint wireframe)
function renderStep2UI() {
  renderYourSelection();
  renderRemovedItems();
  renderSearchAndAdd();
}

function renderYourSelection() {
  const box = document.querySelector("#yourSelection");
  if (!box) return;
  box.innerHTML = "<h3>Your Selection</h3>";
  
  selectedCodes.forEach(code => {
    const deliverable = DELIVERABLES.find(d => d.Deliverable_Code === code);
    if (!deliverable) return;
    
    const item = el(`
      <div class="row">
        <div>
          <strong>${deliverable.Deliverable}</strong> 
          <small class="badge">${deliverable.Category}</small>
        </div>
        <button onclick="onRemove('${code}')" class="remove-btn">×</button>
      </div>
    `);
    box.append(item);
  });
}

function renderRemovedItems() {
  const box = document.querySelector("#removedItems");
  if (!box) return;
  
  if (removedCodes.length === 0) {
    box.innerHTML = "";
    return;
  }
  
  box.innerHTML = "<h3>Removed</h3>";
  removedCodes.forEach(code => {
    const deliverable = DELIVERABLES.find(d => d.Deliverable_Code === code);
    if (!deliverable) return;
    
    const item = el(`
      <div class="row">
        <div>
          <strong>${deliverable.Deliverable}</strong> 
          <small class="badge">${deliverable.Category}</small>
        </div>
        <button onclick="onRestore('${code}')" class="restore-btn">Restore</button>
      </div>
    `);
    box.append(item);
  });
}

function renderSearchAndAdd() {
  const box = document.querySelector("#searchAndAdd");
  if (!box) return;
  
  box.innerHTML = `
    <h3>Search / Add</h3>
    <input type="text" id="searchBox" placeholder="Search deliverables..." />
    <div id="searchResults"></div>
  `;
  
  const searchBox = document.querySelector("#searchBox");
  searchBox.addEventListener('input', debounce(onSearchDeliverables, 300));
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

async function onSearchDeliverables() {
  const query = document.querySelector("#searchBox").value;
  const results = document.querySelector("#searchResults");
  
  if (!query.trim()) {
    results.innerHTML = "";
    return;
  }
  
  try {
    const data = await api(`/api/search_deliverables?q=${encodeURIComponent(query)}`);
    results.innerHTML = "";
    
    (data.items || []).forEach(item => {
      const isSelected = selectedCodes.includes(item.Deliverable_Code);
      const resultItem = el(`
        <div class="row ${isSelected ? 'selected' : ''}">
          <div>
            <strong>${item.Deliverable}</strong> 
            <small class="badge">${item.Category}</small>
          </div>
          ${isSelected ? '<span class="already-selected">✓</span>' : 
            `<button onclick="onAdd('${item.Deliverable_Code}')" class="add-btn">Add</button>`}
        </div>
      `);
      results.append(resultItem);
    });
  } catch (err) {
    results.innerHTML = `<div class="error">Search error: ${err.message}</div>`;
  }
}

// Updated build function to use selectedCodes as specified in blueprint
async function buildScenarios() {
  const payload = {
    selected_deliverable_codes: selectedCodes,
    scenario_a: {/* from UI */},
    scenario_b: {/* from UI */},
    pricing_mode: document.querySelector("#pricingMode").value,
    blended_rate: Number(document.querySelector("#blendedRate").value || 0) || null,
    rate_band: document.querySelector("#rateBand").value,
    use_slack: document.querySelector("#useSlack").checked,
    slack_after_internal: Number(document.querySelector("#slackInternal").value || 0),
    slack_after_client: Number(document.querySelector("#slackClient").value || 0),
    slack_global_pct: Number(document.querySelector("#slackGlobal").value || 0),
    project_start: document.querySelector("#projectStart").value || null,
    retainers: /* if you're using v2.7 retainers */[]
  };
  
  // Get scenario specs from UI
  const useTemplates = document.querySelector("#useTemplates").checked;
  if(useTemplates){
    payload.scenario_a = {mode:"template", scenario_key: document.querySelector("#scenarioA").value};
    payload.scenario_b = {mode:"template", scenario_key: document.querySelector("#scenarioB").value};
  } else {
    payload.scenario_a = {mode:"bundle", bundle: document.querySelector("#bundleA").value};
    payload.scenario_b = {mode:"bundle", bundle: document.querySelector("#bundleB").value};
  }
  
  const res = await fetch("/api/build", { 
    method: "POST", 
    body: JSON.stringify(payload), 
    headers: { "Content-Type": "application/json" }
  });
  const scenarios = await res.json();
  
  // proceed to steps 3/4 with scenarios.A / scenarios.B
  SCENARIOS = scenarios;
  renderScenarios(scenarios);
  
  // Store scenarios globally for timeline and export
  window.appState = window.appState || {};
  window.appState.scenarios = scenarios;
  
  // Show timeline step and render timeline for Scenario A
  document.querySelector("#step4").style.display = "block";
  selectTimeline('A');
}

async function onBuild(){
  if(selectedCodes.length===0){ alert("Select at least one deliverable."); return; }
  await buildScenarios();
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