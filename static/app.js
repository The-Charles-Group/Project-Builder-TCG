let OPTIONS = null;       // cached /api/options
let SCENARIOS = null;     // last built scenarios (A & B)
let DELIVERABLES = [];    // [{deliverable_code, deliverable, category}]

// Legacy compatibility
let selectedCodes = [];
let removedCodes = [];
let addedCodes = [];

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
  
  // Initialize S2 system
  s2LoadDeliverables();

  // Pricing default blended - with null check
  const ps = OPTIONS.pricing_settings.find(x => x.Key==="Default_Blended_Rate");
  const blendedRateEl = document.querySelector("#blendedRate");
  if(ps && blendedRateEl) blendedRateEl.value = ps.Default;

  // Slack defaults - with null checks
  const ss = Object.fromEntries(OPTIONS.slack_settings.map(x => [x.Key, x.Default]));
  const useSlackEl = document.querySelector("#useSlack");
  if (useSlackEl) useSlackEl.checked = !!ss["Use_Slack"];
  
  const slackInternalEl = document.querySelector("#slackInternal");
  if (slackInternalEl) slackInternalEl.value = ss["Slack_After_Internal_Review_Days"] ?? 1;
  
  const slackClientEl = document.querySelector("#slackClient");
  if (slackClientEl) slackClientEl.value = ss["Slack_After_Client_Review_Days"] ?? 2;
  
  const slackGlobalEl = document.querySelector("#slackGlobal");
  if (slackGlobalEl) slackGlobalEl.value = ss["Slack_Global_Percent"] ?? 0.05;

  // UI wiring (original) - with null checks
  const btnSuggest = document.querySelector("#btnSuggest");
  if (btnSuggest) btnSuggest.onclick = onSuggest;
  
  // Remove double binding - Step 3 uses buildScenariosAB from index.html
  // const btnBuild = document.querySelector("#btnBuild");
  // if (btnBuild) btnBuild.onclick = onBuild;
  
  const pricingModeEl = document.querySelector("#pricingMode");
  if (pricingModeEl) pricingModeEl.onchange = onPricingModeChanged;
  
  const useTemplates = document.querySelector("#useTemplates");
  if (useTemplates) useTemplates.onchange = onScenarioTypeChanged;
  
  const useBundles = document.querySelector("#useBundles");
  if (useBundles) useBundles.onchange = onScenarioTypeChanged;
  
  const btnExportA = document.querySelector("#btnExportA");
  if (btnExportA) btnExportA.onclick = () => onExport('A');
  
  const btnExportB = document.querySelector("#btnExportB");
  if (btnExportB) btnExportB.onclick = () => onExport('B');

  // UI wiring (new Step 2)
  const proceedBtn = document.querySelector("#btnProceedToStep3");
  if (proceedBtn) proceedBtn.onclick = onProceedToStep3;
  
  const reconcileBtn = document.querySelector("#btnRunReconcile");
  if (reconcileBtn) reconcileBtn.onclick = onRunReconcile;

  onPricingModeChanged();
}

function onPricingModeChanged(){
  const pricingMode = document.querySelector("#pricingMode");
  if (!pricingMode) return;
  const mode = pricingMode.value;
  
  const blendedWrap = document.querySelector("#blendedWrap");
  if (blendedWrap) blendedWrap.classList.toggle("hidden", mode!=="Flat_Blended");
  
  const bandWrap = document.querySelector("#bandWrap");
  if (bandWrap) bandWrap.classList.toggle("hidden", mode!=="Per_Resource");
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
async function onProceedToStep3() {
  // Check both old and new selection systems and sync them
  const step2Selected = window.appState?.selectedCodes || [];
  const pickerSelected = window.selectedCodes || [];
  const allSelected = [...new Set([...step2Selected, ...pickerSelected])];
  
  if (allSelected.length === 0) {
    alert("Please select at least one deliverable before proceeding to pricing.");
    return;
  }
  
  // Sync the selection state
  selectedCodes = allSelected;
  if (window.appState) window.appState.selectedCodes = allSelected;
  
  // Build scenarios for Step 3 if we don't have them already
  if (!SCENARIOS || Object.keys(SCENARIOS).length === 0) {
    try {
      // Use the working buildScenariosAB function from index.html
      if (window.buildScenariosAB) {
        await window.buildScenariosAB();
      } else {
        console.log("buildScenariosAB not available, scenarios will be built when user clicks Build button in Step 3");
      }
    } catch (error) {
      console.error("Failed to build scenarios:", error);
      alert("Failed to build scenarios. Please try again.");
      return;
    }
  }
  
  // Show Step 3 while keeping Step 2 visible
  const step3 = document.querySelector("#step3");
  
  if (step3) {
    step3.style.display = "block";
    step3.scrollIntoView({ behavior: "smooth" });
  }
}

async function onRunReconcile() {
  // Check if we're in Step 2 with existing analysis or Step 1 needing text input
  const step2Visible = document.getElementById('step2')?.style.display !== 'none';
  const txt = document.querySelector("#rfpText")?.value || "";
  const hasAnalysis = window.appState && window.appState.aiSummary;
  
  console.log("onRunReconcile debug:", { step2Visible, hasText: !!txt.trim(), hasAnalysis, appState: window.appState });
  
  // If Step 2 is visible, we already have analysis - just show Stage 2
  if (step2Visible) {
    document.getElementById('stage2').style.display = 'block';
    document.getElementById('stage2').scrollIntoView({ behavior: 'smooth' });
    return;
  }
  
  // Otherwise we need RFP text first  
  if (!txt.trim() && !hasAnalysis) {
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
    
    const selectedComps = selectedComponentsMap[code] || new Set();
    const compCountText = selectedComps.size > 0 ? ` (${selectedComps.size} components)` : '';
    
    const item = el(`
      <div class="row">
        <div>
          <strong>${deliverable.Deliverable}</strong>${compCountText}
          <small class="badge">${deliverable.Category}</small>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <button onclick="openComponentPicker('${code}', '${deliverable.Deliverable}')" class="btn-small" style="padding: 4px 8px; font-size: 12px;">Components...</button>
          <button onclick="onRemove('${code}')" class="remove-btn">×</button>
        </div>
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
  // This will be handled by the Step 2 Deliverables Picker
}

// ---- Step 2 Deliverables Picker (search + select/clear + apply) ----
(function(){
  // cache from Step 1 build; make sure you store payload when you build (see note below)
  window.__lastBuildPayload = window.__lastBuildPayload || null;

  const el = {
    card: document.getElementById('s2-deliv-card'),
    search: document.getElementById('s2-deliv-search'),
    list: document.getElementById('s2-deliv-list'),
    btnAll: document.getElementById('s2-deliv-selectall'),
    btnClear: document.getElementById('s2-deliv-clear'),
    btnApply: document.getElementById('s2-apply'),
  };
  if (!el.card) return; // card not present on this page

  const state = {
    options: null,                 // { deliverables, scenario_templates, bundles, ... }
    selected: new Set(),           // selected deliverable codes
  };
  
  // Expose state globally for reconciliation sync
  window.step2PickerState = state;

  // 1) Load options if needed
  async function ensureOptions() {
    if (state.options) return;
    const r = await fetch('/api/options'); // v2.8 route
    state.options = await r.json();
  }

  // 2) Seed selection from the most recent scenarios (A/B)
  function seedFromCurrentScenarios(scenarios) {
    const set = new Set();
    ['A','B'].forEach(letter => {
      (scenarios?.[letter]?.items || []).forEach(it => set.add(String(it.deliverable_code)));
    });
    if (set.size) state.selected = set;
  }

  // 3) Render list
  function renderList(filter = '') {
    const q = (filter || '').toLowerCase().trim();
    const items = (state.options?.deliverables || []).filter(d =>
      !q ||
      String(d.Deliverable).toLowerCase().includes(q) ||
      String(d.Category).toLowerCase().includes(q) ||
      String(d.Deliverable_Code).toLowerCase().includes(q)
    );
    el.list.innerHTML = items.map(d => `
      <label style="display:flex; gap:8px; align-items:center; padding:8px;">
        <input type="checkbox" data-code="${d.Deliverable_Code}"
               ${state.selected.has(String(d.Deliverable_Code)) ? 'checked' : ''}/>
        <span>${d.Deliverable}</span>
        <span style="margin-left:auto; opacity:.75; font-size:12px;">${d.Category}</span>
      </label>
    `).join('') || '<div style="opacity:.7; padding:8px;">No deliverables</div>';
    el.list.querySelectorAll('input[type="checkbox"]').forEach(cb => {
      cb.addEventListener('change', e => {
        const code = e.target.getAttribute('data-code');
        if (e.target.checked) state.selected.add(code); else state.selected.delete(code);
        // Sync selection immediately
        window.selectedCodes = Array.from(state.selected);
        if (window.appState) window.appState.selectedCodes = window.selectedCodes;
      });
    });
  }

  // 4) Apply → rebuild scenarios keeping the same scenario settings / pricing / timeline
  async function applySelection() {
    const selectedCodes = Array.from(state.selected);
    if (selectedCodes.length === 0) {
      alert('Pick at least one deliverable.');
      return;
    }
    
    // If no build context, create a basic payload
    if (!window.__lastBuildPayload) {
      window.__lastBuildPayload = {
        pricing_mode: 'Flat_Blended',
        blended_rate: 195,
        rate_band: 'Standard_US',
        scenario_a: {mode:'template', complexity:'Advanced', tier:'T2_MediumVolume'},
        scenario_b: {mode:'template', complexity:'Advanced', tier:'T2_MediumVolume'},
        use_slack: true,
        slack_after_internal: 1,
        slack_after_client: 2,
        slack_global_pct: 0.05,
        project_start: null
      };
    }
    
    const payload = { ...window.__lastBuildPayload, selected_deliverable_codes: selectedCodes };
    const r = await fetch('/api/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const scenarios = await r.json();
    // keep for future edits
    window.__lastBuildPayload = payload;

    // if you already have a Step 2 render method, call it here:
    if (window.renderStep2) {
      window.renderStep2(scenarios);
    } else {
      // minimal fallback
      console.log('Scenarios rebuilt:', scenarios);
    }

    // reseed selection from newly built scenarios
    seedFromCurrentScenarios(scenarios);
    renderList(el.search.value);
    
    // Sync with global state for other workflows
    window.selectedCodes = Array.from(state.selected);
    if (window.appState) window.appState.selectedCodes = window.selectedCodes;
  }

  // 5) Hook up UI
  el.search.addEventListener('input', () => renderList(el.search.value));
  el.btnAll.addEventListener('click', () => {
    (state.options?.deliverables || []).forEach(d => state.selected.add(String(d.Deliverable_Code)));
    renderList(el.search.value);
    // Sync selection immediately
    window.selectedCodes = Array.from(state.selected);
    if (window.appState) window.appState.selectedCodes = window.selectedCodes;
  });
  el.btnClear.addEventListener('click', () => { 
    state.selected.clear(); 
    renderList(el.search.value);
    // Sync selection immediately
    window.selectedCodes = Array.from(state.selected);
    if (window.appState) window.appState.selectedCodes = window.selectedCodes;
  });
  el.btnApply.addEventListener('click', applySelection);

  // 6) Public init for Step 2; call this right after Step 2 renders scenarios
  window.initStep2DeliverablePicker = async function initStep2DeliverablePicker(scenarios) {
    await ensureOptions();
    seedFromCurrentScenarios(scenarios);
    renderList('');
  };
  
  // 7) Public function to update Step 2 picker from external selection (e.g., reconciliation)
  window.updateStep2PickerSelection = function updateStep2PickerSelection(selectedCodes) {
    state.selected.clear();
    selectedCodes.forEach(code => state.selected.add(String(code)));
    renderList(el.search.value);
    console.log("Step 2 picker updated with selection:", selectedCodes);
  };
})();

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

// Removed broken buildScenarios function - using buildScenariosAB from index.html instead

// onBuild function removed - using buildScenariosAB from index.html instead

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

// Component Selection Functionality
async function openComponentPicker(code, name) {
  try {
    const complexity = document.querySelector('#complexity')?.value || 'Advanced';
    const tier = document.querySelector('#tier')?.value || 'T2_MediumVolume';
    
    const response = await fetch(`/api/components_for?deliverable_code=${encodeURIComponent(code)}&complexity=${complexity}&tier=${tier}`);
    const data = await response.json();
    const components = data.items || [];
    
    if (components.length === 0) {
      alert(`No components found for ${name}`);
      return;
    }
    
    // Initialize selection for this deliverable if not exists
    if (!selectedComponentsMap[code]) selectedComponentsMap[code] = new Set();
    
    // Create modal
    const modal = el(`
      <div id="component-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;">
        <div style="background: var(--card); padding: 24px; border-radius: 8px; max-width: 500px; width: 90%; max-height: 80%; overflow-y: auto;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h3 style="margin: 0;">Components for ${name}</h3>
            <button onclick="closeComponentPicker()" style="background: none; border: none; font-size: 20px; cursor: pointer;">&times;</button>
          </div>
          <p style="font-size: 14px; color: var(--muted); margin-bottom: 16px;">Select which components to include in your estimate:</p>
          <div id="component-list"></div>
          <div style="margin-top: 16px; display: flex; gap: 8px; justify-content: flex-end;">
            <button onclick="closeComponentPicker()" class="btn-secondary">Cancel</button>
            <button onclick="saveComponentSelection('${code}')" class="btn-primary">Save Selection</button>
          </div>
        </div>
      </div>
    `);
    
    document.body.appendChild(modal);
    
    // Populate component list
    const list = document.getElementById('component-list');
    components.forEach(comp => {
      const isSelected = selectedComponentsMap[code].has(comp.name);
      const item = el(`
        <label style="display: flex; align-items: center; gap: 8px; padding: 8px; border: 1px solid var(--border); margin-bottom: 4px; border-radius: 4px; cursor: pointer;">
          <input type="checkbox" data-component="${comp.name}" ${isSelected ? 'checked' : ''}>
          <div style="flex: 1;">
            <div style="font-weight: 500;">${comp.name}</div>
            <div style="font-size: 12px; color: var(--muted);">${comp.hours} hours</div>
          </div>
        </label>
      `);
      list.appendChild(item);
    });
    
  } catch (error) {
    console.error('Error loading components:', error);
    alert('Error loading components. Please try again.');
  }
}

function closeComponentPicker() {
  const modal = document.getElementById('component-modal');
  if (modal) modal.remove();
}

function saveComponentSelection(code) {
  const modal = document.getElementById('component-modal');
  const checkboxes = modal.querySelectorAll('input[type="checkbox"]');
  
  selectedComponentsMap[code] = new Set();
  checkboxes.forEach(cb => {
    if (cb.checked) {
      selectedComponentsMap[code].add(cb.dataset.component);
    }
  });
  
  closeComponentPicker();
  renderYourSelection(); // Refresh the display to show component count
}

// Timeline functionality
function getScenario(letter) {
  return window.appState?.scenarios?.[letter];
}

// Timeline rendering function removed - using the one in index.html to avoid conflicts

function enableTimelineDnD(letter) {
  const body = document.getElementById('tl-body');
  if (!body) {
    console.log("Timeline body not available for DnD setup");
    return;
  }
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
  if (!box) {
    console.log("Timeline status element not available");
    return;
  }
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
  // Call the timeline rendering function from index.html
  if (window.renderTimeline) {
    window.renderTimeline(letter);
  }
  document.querySelectorAll('[data-timeline-sel]')
    .forEach(btn => btn.classList.toggle('active', btn.dataset.timelineSel === letter));
}

// Event delegation for timeline controls
document.addEventListener('click', e => {
  const btn = e.target.closest('[data-timeline-sel]');
  if (!btn) return;
  selectTimeline(btn.dataset.timelineSel);  // 'A' or 'B'
});

// ---- S2 Functions (GPT 5 Pro Implementation) ----

// ---- Initialize S2 elements and load deliverables ----
async function s2LoadDeliverables() {
  // First, populate the elements object now that DOM is ready
  S2.els = {
    listRight: document.querySelector('#s2-deliv-list') || document.querySelector('#deliverableList'),
    search: document.querySelector('#s2-deliv-search') || document.querySelector('#delivSearch'),
    btnApply: document.querySelector('#s2-apply') || document.querySelector('#applySelection, #btnApplySelection'),
    btnSelectAll: document.querySelector('#s2-deliv-selectall') || document.querySelector('#delivSelectAll'),
    btnClear: document.querySelector('#s2-deliv-clear') || document.querySelector('#delivClear'),
    yourSel: document.querySelector('#yourSelection') || document.querySelector('#s2-your-list, #yourSelectionList'),
    compDrawer: document.getElementById('compDrawer'),
    compList: document.getElementById('compList'),
    compTitle: document.getElementById('compTitle'),
    compDone: document.getElementById('compDone'),
  };
  
  console.log('S2 Elements found:', {
    listRight: !!S2.els.listRight,
    search: !!S2.els.search,
    btnApply: !!S2.els.btnApply,
    btnSelectAll: !!S2.els.btnSelectAll,
    btnClear: !!S2.els.btnClear,
    yourSel: !!S2.els.yourSel
  });
  
  const r = await fetch('/api/options');   // server returns deliverables + templates
  const data = await r.json();
  S2.allDeliverables = data.deliverables || [];
  s2RenderRight('');
  s2SetupEventListeners();
}

function s2RenderRight(filter) {
  const host = S2.els.listRight;
  if (!host) return;
  const q = (filter || '').toLowerCase();
  const items = S2.allDeliverables.filter(d =>
    !q ||
    String(d.Deliverable).toLowerCase().includes(q) ||
    String(d.Category || '').toLowerCase().includes(q) ||
    String(d.Deliverable_Code).toLowerCase().includes(q)
  );
  host.innerHTML = items.map(d => `
    <label class="row" style="display:flex;gap:8px;align-items:center;padding:6px 8px;">
      <input type="checkbox" class="s2chk"
        data-code="${d.Deliverable_Code}"
        data-name="${d.Deliverable}"
        data-cat="${d.Category}"
        ${S2.selectedCodes.has(String(d.Deliverable_Code)) ? 'checked' : ''}/>
      <span>${d.Deliverable}</span>
      <small style="margin-left:auto;opacity:.75">${d.Category || ''}</small>
    </label>
  `).join('') || '<div style="opacity:.7;padding:8px">No deliverables</div>';

  host.querySelectorAll('.s2chk').forEach(cb => {
    cb.addEventListener('change', e => {
      const code = e.target.dataset.code, name = e.target.dataset.name, cat = e.target.dataset.cat;
      if (e.target.checked) {
        S2.selectedCodes.add(code);
        S2.selectedMeta.set(code, {name, category: cat});
      } else {
        S2.selectedCodes.delete(code);
        S2.selectedMeta.delete(code);
      }
      s2RenderLeft();
    });
  });
}

// Setup event listeners (called after elements are found)
function s2SetupEventListeners() {
  if (S2.els.search) {
    S2.els.search.addEventListener('input', e => s2RenderRight(e.target.value));
  }
  
  if (S2.els.btnSelectAll) {
    S2.els.btnSelectAll.addEventListener('click', () => {
      S2.allDeliverables.forEach(d => {
        S2.selectedCodes.add(String(d.Deliverable_Code));
        S2.selectedMeta.set(String(d.Deliverable_Code), {name: d.Deliverable, category: d.Category});
      });
      s2RenderRight(S2.els.search?.value || '');
      s2RenderLeft();
    });
  }
  
  if (S2.els.btnClear) {
    S2.els.btnClear.addEventListener('click', () => {
      S2.selectedCodes.clear();
      S2.selectedMeta.clear();
      s2RenderRight(S2.els.search?.value || '');
      s2RenderLeft();
    });
  }
  
  if (S2.els.btnApply) {
    S2.els.btnApply.addEventListener('click', s2ApplyAndBuild);
  }
  
  if (S2.els.compDone) {
    S2.els.compDone.addEventListener('click', () => S2.els.compDrawer.classList.add('hidden'));
  }
}

// ---- Left panel ("Your Selection") with Components… buttons ----
function s2RenderLeft() {
  const host = S2.els.yourSel;
  if (!host) return;
  const rows = Array.from(S2.selectedCodes).map(code => {
    const meta = S2.selectedMeta.get(code) || {name: code, category: ''};
    return `
      <div class="row" style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-bottom:1px solid rgba(255,255,255,.06)">
        <strong>${meta.name}</strong>
        <small style="opacity:.75">${meta.category || ''}</small>
        <button class="btn small s2-comp" data-code="${code}" data-name="${meta.name}" style="margin-left:auto">Components…</button>
        <button class="btn small s2-remove" data-code="${code}">✕</button>
      </div>`;
  });
  host.innerHTML = rows.join('') || '<div style="opacity:.7;padding:8px">No deliverables selected yet.</div>';

  host.querySelectorAll('.s2-remove').forEach(btn => btn.addEventListener('click', e => {
    const code = e.target.dataset.code;
    S2.selectedCodes.delete(code);
    S2.selectedMeta.delete(code);
    s2RenderRight(S2.els.search?.value || '');
    s2RenderLeft();
  }));

  host.querySelectorAll('.s2-comp').forEach(btn => btn.addEventListener('click', e => {
    s2OpenComponents(e.target.dataset.code, e.target.dataset.name);
  }));
}

// ---- Components drawer ----
async function s2OpenComponents(code, name) {
  const compUrl = `/api/components_for?deliverable_code=${encodeURIComponent(code)}`;
  const res = await fetch(compUrl);
  const data = await res.json();
  const items = data.items || [];
  const current = S2.selectedComponentsMap[code] || new Set();
  if (!S2.els.compDrawer) {
    alert('Component picker UI not mounted (add #compDrawer).');
    return;
  }
  S2.els.compTitle.textContent = `Components — ${name}`;
  S2.els.compList.innerHTML = items.map(c => `
    <label class="row" style="display:flex;gap:8px;align-items:center;padding:6px 8px;">
      <input type="checkbox" class="s2compchk" data-code="${code}" data-name="${c.name}"
        ${current.has(c.name) ? 'checked' : ''}/>
      <span>${c.name}</span>
      <small style="margin-left:auto;opacity:.75">${Math.round(c.hours)}h</small>
    </label>`).join('') || '<div style="opacity:.7;padding:8px">No components for this deliverable.</div>';
  S2.els.compDrawer.classList.remove('hidden');

  S2.els.compList.querySelectorAll('.s2compchk').forEach(chk => {
    chk.addEventListener('change', e => {
      const c = e.target.dataset.code, n = e.target.dataset.name;
      if (!S2.selectedComponentsMap[c]) S2.selectedComponentsMap[c] = new Set();
      e.target.checked ? S2.selectedComponentsMap[c].add(n) : S2.selectedComponentsMap[c].delete(n);
    });
  });
}
// Component Done event listener moved to s2SetupEventListeners()

// ---- Build Scenarios directly from Step 2 ----
async function s2ApplyAndBuild() {
  const codes = Array.from(S2.selectedCodes);
  if (!codes.length) { alert('Please select at least one deliverable.'); return; }

  // gather knobs (fallbacks keep it working even if Step 1 controls are untouched)
  const pricingMode  = document.querySelector('#pricingMode')?.value || 'Flat_Blended';
  const blendedRate  = Number(document.querySelector('#blendedRate')?.value || 195);
  const rateBand     = document.querySelector('#rateBand')?.value || 'Standard_US';
  const useSlack     = (document.querySelector('#useSlack')?.checked ?? true);
  const slackI       = Number(document.querySelector('#slackAfterInternal')?.value || 1);
  const slackC       = Number(document.querySelector('#slackAfterClient')?.value   || 2);
  const slackPct     = Number(document.querySelector('#slackGlobalPct')?.value     || 0.05);
  const projectStart = document.querySelector('#projectStart')?.value || null;
  const scenA        = document.querySelector('#scenarioA')?.value || 'MED_LOW';
  const scenB        = document.querySelector('#scenarioB')?.value || 'MED_HIGH';

  const compMap = Object.fromEntries(Object.entries(S2.selectedComponentsMap)
                      .map(([k, set]) => [k, Array.from(set || [])]));

  const payload = {
    selected_deliverable_codes: codes,
    selected_components_map: compMap,                        // <-- NEW
    scenario_a: { mode: 'template', scenario_key: scenA },
    scenario_b: { mode: 'template', scenario_key: scenB },
    pricing_mode: pricingMode,
    blended_rate: pricingMode === 'Flat_Blended' ? blendedRate : undefined,
    rate_band: rateBand,
    use_slack: useSlack,
    slack_after_internal: slackI,
    slack_after_client: slackC,
    slack_global_pct: slackPct,
    project_start: projectStart
  };

  const res = await fetch('/api/build', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).then(r => r.json());

  window.__lastBuild = res; // enable downstream pricing/export
  // Optional: update any pricing/summary widgets here
  // s2RenderTotals(res); // if you have one
}

// Event listeners are now set up in s2SetupEventListeners()

// Complete Step 2 Implementation (v2.8 Fix)
document.addEventListener('DOMContentLoaded', () => {
  initStep2();
});

function initStep2() {
  const S2 = window.S2 = {
    allDeliverables: [],
    selectedCodes: new Set(),
    selectedMeta: new Map(),       // code -> {name, category}
    selectedComponentsMap: {},     // code -> Set(component names)
    els: {
      listRight: document.querySelector('#deliverableList'),
      search: document.querySelector('#delivSearch'),
      btnApply: document.querySelector('#applySelection'),
      btnSelectAll: document.querySelector('#delivSelectAll'),
      btnClear: document.querySelector('#delivClear'),
      yourSel: document.querySelector('#yourSelection'),
      compDrawer: document.getElementById('compDrawer'),
      compList: document.getElementById('compList'),
      compTitle: document.getElementById('compTitle'),
      compDone: document.getElementById('compDone'),
    }
  };

  // Load deliverables for the picker
  fetch('/api/options').then(r=>r.json()).then(data => {
    S2.allDeliverables = data.deliverables || [];
    renderRight('');
  });

  // ---------- Right panel ----------
  function renderRight(filter) {
    const host = S2.els.listRight; if (!host) return;
    const q = (filter || '').toLowerCase();
    const items = S2.allDeliverables.filter(d =>
      !q ||
      String(d.Deliverable).toLowerCase().includes(q) ||
      String(d.Category||'').toLowerCase().includes(q) ||
      String(d.Deliverable_Code).toLowerCase().includes(q)
    );
    host.innerHTML = items.map(d => `
      <label class="row" style="display:flex;gap:8px;align-items:center;padding:6px 8px;">
        <input type="checkbox" class="s2chk"
          data-code="${d.Deliverable_Code}"
          data-name="${d.Deliverable}"
          data-cat="${d.Category}"
          ${S2.selectedCodes.has(String(d.Deliverable_Code)) ? 'checked' : ''}/>
        <span>${d.Deliverable}</span>
        <small style="margin-left:auto;opacity:.75">${d.Category||''}</small>
      </label>
    `).join('') || '<div style="opacity:.7;padding:8px">No deliverables</div>';
    host.querySelectorAll('.s2chk').forEach(cb => {
      cb.addEventListener('change', e => {
        const code = e.target.dataset.code, name = e.target.dataset.name, cat = e.target.dataset.cat;
        if (e.target.checked) {
          S2.selectedCodes.add(code);
          S2.selectedMeta.set(code, {name, category: cat});
        } else {
          S2.selectedCodes.delete(code);
          S2.selectedMeta.delete(code);
        }
        renderLeft();
      });
    });
  }
  S2.els.search?.addEventListener('input', e => renderRight(e.target.value));
  S2.els.btnSelectAll?.addEventListener('click', () => {
    S2.allDeliverables.forEach(d => {
      const code = String(d.Deliverable_Code);
      S2.selectedCodes.add(code);
      S2.selectedMeta.set(code, {name:d.Deliverable, category:d.Category});
    });
    renderRight(S2.els.search?.value || ''); renderLeft();
  });
  S2.els.btnClear?.addEventListener('click', () => {
    S2.selectedCodes.clear(); S2.selectedMeta.clear();
    renderRight(S2.els.search?.value || ''); renderLeft();
  });

  // ---------- Left panel ("Your Selection") ----------
  function renderLeft() {
    const host = S2.els.yourSel; if (!host) return;
    const rows = Array.from(S2.selectedCodes).map(code => {
      const meta = S2.selectedMeta.get(code) || {name: code, category: ''};
      return `<div class="row" style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-bottom:1px solid rgba(255,255,255,.06)">
        <strong>${meta.name}</strong>
        <small style="opacity:.75">${meta.category||''}</small>
        <button class="btn small s2-comp" data-code="${code}" data-name="${meta.name}" style="margin-left:auto">Components…</button>
        <button class="btn small s2-remove" data-code="${code}">✕</button>
      </div>`;
    });
    host.innerHTML = rows.join('') || '<div style="opacity:.7;padding:8px">No deliverables selected yet.</div>';
    host.querySelectorAll('.s2-remove').forEach(btn => btn.addEventListener('click', e => {
      const code = e.target.dataset.code;
      S2.selectedCodes.delete(code); S2.selectedMeta.delete(code);
      renderRight(S2.els.search?.value || ''); renderLeft();
    }));
    host.querySelectorAll('.s2-comp').forEach(btn => btn.addEventListener('click', e => {
      openComponents(e.target.dataset.code, e.target.dataset.name);
    }));
  }

  // ---------- Components drawer ----------
  async function openComponents(code, name) {
    try {
      const r = await fetch(`/api/components_for?deliverable_code=${encodeURIComponent(code)}`);
      const data = await r.json();
      const items = data.items || [];
      const current = S2.selectedComponentsMap[code] || new Set();
      S2.els.compTitle.textContent = `Components — ${name}`;
      S2.els.compList.innerHTML = items.map(c => `
        <label class="row" style="display:flex;gap:8px;align-items:center;padding:6px 8px;">
          <input type="checkbox" class="s2compchk" data-code="${code}" data-name="${c.name}" ${current.has(c.name)?'checked':''}/>
          <span>${c.name}</span>
          <small style="margin-left:auto;opacity:.75">${Math.round(c.hours)}h</small>
        </label>`).join('') || '<div style="opacity:.7;padding:8px">No components for this deliverable.</div>';
      S2.els.compDrawer.style.display = 'block';
      S2.els.compList.querySelectorAll('.s2compchk').forEach(chk => {
        chk.addEventListener('change', e => {
          const k = e.target.dataset.code, n = e.target.dataset.name;
          if (!S2.selectedComponentsMap[k]) S2.selectedComponentsMap[k] = new Set();
          e.target.checked ? S2.selectedComponentsMap[k].add(n) : S2.selectedComponentsMap[k].delete(n);
        });
      });
    } catch (err) {
      console.error(err); alert('Could not load components.');
    }
  }
  S2.els.compDone?.addEventListener('click', () => S2.els.compDrawer.style.display = 'none');

  // ---------- Apply selection: BUILD ----------
  S2.els.btnApply?.addEventListener('click', async () => {
    const codes = Array.from(S2.selectedCodes);
    if (!codes.length) { alert('Please select at least one deliverable.'); return; }
    const compMap = Object.fromEntries(Object.entries(S2.selectedComponentsMap)
                      .map(([k,set]) => [k, Array.from(set || [])]));
    // knobs from Step 1 (safe defaults)
    const pricingMode  = document.querySelector('#pricingMode')?.value || 'Flat_Blended';
    const blendedRate  = Number(document.querySelector('#blendedRate')?.value || 195);
    const rateBand     = document.querySelector('#rateBand')?.value || 'Standard_US';
    const useSlack     = (document.querySelector('#useSlack')?.checked ?? true);
    const slackI       = Number(document.querySelector('#slackAfterInternal')?.value || 1);
    const slackC       = Number(document.querySelector('#slackAfterClient')?.value   || 2);
    const slackPct     = Number(document.querySelector('#slackGlobalPct')?.value     || 0.05);
    const projectStart = document.querySelector('#projectStart')?.value || null;
    const scenA        = document.querySelector('#scenarioA')?.value || 'MED_LOW';
    const scenB        = document.querySelector('#scenarioB')?.value || 'MED_HIGH';

    const payload = {
      selected_deliverable_codes: codes,
      selected_components_map: compMap,
      scenario_a: { mode:'template', scenario_key: scenA },
      scenario_b: { mode:'template', scenario_key: scenB },
      pricing_mode: pricingMode,
      blended_rate: pricingMode==='Flat_Blended' ? blendedRate : undefined,
      rate_band: rateBand,
      use_slack: useSlack,
      slack_after_internal: slackI,
      slack_after_client: slackC,
      slack_global_pct: slackPct,
      project_start: projectStart
    };
    const res = await fetch('/api/build', {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)
    }).then(r=>r.json());
    window.__lastBuild = res; // used by pricing/export
    console.log('Build completed:', res);
    // Optional: enable Proceed button now that we have a build
    document.querySelector('#btnProceed, #proceedPricing')?.removeAttribute('disabled');
    alert('Build completed! You can now proceed to pricing.');
  });
}

window.addEventListener("load", boot);