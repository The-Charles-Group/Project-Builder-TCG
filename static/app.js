let OPTIONS = null;       // cached /api/options
let SCENARIOS = null;     // last built scenarios (A & B)
let DELIVERABLES = [];    // [{deliverable_code, deliverable, category}]
let DELIV_INDEX = {};     // code -> deliverable object lookup for fast rendering

// ---- Step 2 state ---- (GPT 5 Pro Implementation)
const S2 = {
  allDeliverables: [],                // from /api/options
  selectedCodes: new Set(),           // codes the user checked
  selectedMeta: new Map(),            // code -> {name, category}
  selectedComponentsMap: {},          // code -> Set(component names)
  els: {
    listRight: document.querySelector('#s2-deliv-list, #deliverableList'),
    search: document.querySelector('#s2-deliv-search, #delivSearch'),
    btnApply: document.querySelector('#s2-apply, #applySelection, #btnApplySelection'),
    btnSelectAll: document.querySelector('#s2-deliv-selectall, #delivSelectAll'),
    btnClear: document.querySelector('#s2-deliv-clear, #delivClear'),
    yourSel: document.querySelector('#s2-your-list, #yourSelection, #yourSelectionList'),
    compDrawer: document.getElementById('compDrawer'),
    compList: document.getElementById('compList'),
    compTitle: document.getElementById('compTitle'),
    compDone: document.getElementById('compDone'),
  }
};

// Legacy compatibility
let selectedCodes = [];
let removedCodes = [];
let addedCodes = [];
const selectedComponentsMap = S2.selectedComponentsMap;
window.selectedComponentsMap = selectedComponentsMap;

// Helper functions to get deliverable info from code
function labelFor(code) {
  const row = DELIV_INDEX[String(code).trim()];
  return row ? row.Deliverable : String(code);
}

function categoryFor(code) {
  const row = DELIV_INDEX[String(code).trim()];
  return row ? row.Category : "";
}

// Read currently chosen deliverables from the Your Selection column
function readSelectedCodesFromUI() {
  return Array.from(S2.selectedCodes);
}

// Save component choices for a deliverable
// If "all" are selected or empty, remove the key so server includes all by default
function setComponentsFor(delivCode, labelsArray) {
  if (!labelsArray || !labelsArray.length) {
    delete S2.selectedComponentsMap[delivCode];
    return;
  }
  const dict = Object.create(null);
  labelsArray.forEach(label => { dict[label] = null; });
  S2.selectedComponentsMap[delivCode] = dict;
}

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
  
  // Build code→deliverable index for fast lookups
  DELIV_INDEX = {};
  for (const d of (OPTIONS.deliverables || [])) {
    DELIV_INDEX[String(d.Deliverable_Code).trim()] = d;
  }
  
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
  const btnAnalyze = document.querySelector("#btnAnalyze");
  if (btnAnalyze) btnAnalyze.onclick = onRunReconcile;
  
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
  if (reconcileBtn) {
    reconcileBtn.onclick = (e) => {
      e.preventDefault();
      // Refresh suggestions with current selection
      initAISummaryAndSuggestions();
    };
  }

  onPricingModeChanged();
  
  // Wire up retainer toggle
  const retainersToggle = document.querySelector("#retainersToggle");
  if (retainersToggle) {
    retainersToggle.addEventListener('change', onToggleRetainers);
  }
  
  // Export functions globally for index.html
  window.onRunReconcile = onRunReconcile;
  window.buildFromCurrentSelection = buildFromCurrentSelection;
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

// Build from current S2 selection (surgical patch implementation)
async function buildFromCurrentSelection() {
  const codes = readSelectedCodesFromUI();
  if (!codes.length) {
    alert("Pick at least one deliverable before proceeding to pricing.");
    return;
  }

  // Sync legacy state for compatibility
  selectedCodes = codes;
  if (window.appState) window.appState.selectedCodes = codes;
  window.selectedCodes = codes;

  // Convert S2.selectedComponentsMap (which uses Sets) to API format (plain objects)
  const selectedComponentsPayload = {};
  
  // For all selected deliverables, ensure we have component info
  codes.forEach(code => {
    const compSet = S2.selectedComponentsMap[code];
    
    if (compSet instanceof Set && compSet.size > 0) {
      // User has selected specific components
      const dict = Object.create(null);
      compSet.forEach(label => { dict[label] = null; });
      selectedComponentsPayload[code] = dict;
    } else if (compSet && typeof compSet === 'object' && !(compSet instanceof Set)) {
      // Already in object format (fix: proper parentheses for instanceof)
      selectedComponentsPayload[code] = compSet;
    } else {
      // No specific components selected - send "__ALL__" sentinel to include all
      selectedComponentsPayload[code] = "__ALL__";
    }
  });

  // Include retainers if toggle is enabled
  const retainersEnabled = document.querySelector('#retainersToggle')?.checked || false;
  const retainersPayload = retainersEnabled ? (window.APP?.retainers || []) : [];

  const payload = {
    selected_deliverable_codes: codes,
    selected_components_map: selectedComponentsPayload,
    pricing_mode: window.getPricingModeFromUI?.() || 'Flat_Blended',
    blended_rate: window.getBlendedRateFromUI?.() || 195,
    rate_band: window.getRateBandFromUI?.() || 'Standard_US',
    use_slack: window.getUseSlackFromUI?.() || false,
    slack_after_internal: window.getSlackInternalFromUI?.() || 1,
    slack_after_client: window.getSlackClientFromUI?.() || 2,
    slack_global_pct: window.getSlackPctFromUI?.() || 0.05,
    project_start: window.getProjectStartFromUI?.() || null,
    scenario_a: window.getScenarioSpecAFromUI?.() || { mode: 'template', scenario_key: 'MED_LOW' },
    scenario_b: window.getScenarioSpecBFromUI?.() || { mode: 'template', scenario_key: 'MED_HIGH' },
    retainers: retainersPayload
  };

  const res = await fetch('/api/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  
  if (!res.ok) {
    const txt = await res.text();
    alert(`Build failed: ${txt}`);
    return;
  }
  
  const data = await res.json();
  
  // Store globally for Step 3 and exports
  window.BUILD = data;
  window.appState = window.appState || {};
  window.appState.scenarios = data;
  window.latestScenarios = data;
  SCENARIOS = data;

  // Show Step 3 and scroll
  const step3 = document.querySelector("#step3");
  if (step3) {
    step3.style.display = "block";
    step3.scrollIntoView({ behavior: "smooth" });
  }

  // Render scenarios if function exists
  if (window.renderScenario) {
    window.renderScenario('scenarioA', data.A);
    window.renderScenario('scenarioB', data.B);
  }
}

// Alias for backward compatibility
const onProceedToStep3 = buildFromCurrentSelection;

// Step 1: Analyze with AI (updated to use summarize endpoints and show Step 2)
async function onRunReconcile() {
  const fileEl = document.querySelector('#rfpFile');
  const textEl = document.querySelector('#rfpText');
  const rfpText = (textEl?.value || '').trim();

  let summary;
  try {
    if (fileEl?.files?.length) {
      const form = new FormData();
      form.append('file', fileEl.files[0]);
      const res = await fetch('/api/summarize_by_file', { method: 'POST', body: form });
      summary = await res.json(); // { summary_text, deliverables: [{label, short_desc, tasks}], word_count }
    } else if (rfpText) {
      const res = await fetch('/api/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rfp_text: rfpText })
      });
      summary = await res.json();
    } else {
      alert('Please enter RFP text or upload a file first.');
      return;
    }

    // Persist for Step 2
    window.APP = window.APP || {};
    window.APP.rfpText = rfpText;
    window.APP.summary = summary;
    sessionStorage.setItem('apb:rfpSummary', JSON.stringify(summary));

    // Show Step 2
    const step2 = document.getElementById('step2');
    if (step2) {
      step2.style.display = 'block';
      step2.scrollIntoView({ behavior: 'smooth' });
    }

    // Render summary & suggestions on Step 2
    initAISummaryAndSuggestions();
    
  } catch (error) {
    console.error('Error analyzing RFP:', error);
    alert(`Error getting AI analysis: ${error.message}`);
  }
}

// Initialize AI Summary and Suggestions on Step 2
function initAISummaryAndSuggestions() {
  // Hydrate from memory or session
  const sum = window.APP?.summary || JSON.parse(sessionStorage.getItem('apb:rfpSummary') || 'null');
  if (!sum) {
    // No analysis yet – keep UI available but empty
    renderAISummary(null);
    renderNewAISuggestions([]);
    return;
  }
  renderAISummary(sum);
  // Build suggestions from AI deliverable labels vs current selection
  const labels = (sum.deliverables || []).map(d => d.label).filter(Boolean);
  const selCodes = Array.from(S2.selectedCodes || []);
  reconcileAndRender(labels, selCodes);
}

// Render AI Summary panel
function renderAISummary(sum) {
  const body  = document.querySelector('#s2-ai-summary-body');
  const count = document.querySelector('#s2-ai-summary-count');
  const copy  = document.querySelector('#s2-ai-summary-copy');
  const tog   = document.querySelector('#s2-ai-summary-toggle');

  if (!body) return;
  if (!sum) {
    body.textContent = 'Run analysis to see summary.';
    if (count) count.textContent = '';
    if (copy) copy.onclick = null;
    if (tog) tog.onclick = null;
    return;
  }

  body.textContent = sum.summary_text || '';
  if (count) count.textContent = sum.word_count ? `${sum.word_count}/500 words` : '';
  if (copy) copy.onclick = () => navigator.clipboard.writeText(sum.summary_text || '');
  let hidden = false;
  if (tog) {
    tog.onclick = () => {
      hidden = !hidden;
      body.style.display = hidden ? 'none' : 'block';
      tog.textContent = hidden ? 'Show' : 'Hide';
    };
  }
}

// Call reconcile API and render suggestions
async function reconcileAndRender(aiLabels, selectedCodes) {
  try {
    const res = await fetch('/api/reconcile', {
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        summary_deliverables: aiLabels,
        db_selected_deliverable_codes: selectedCodes,
        rfp_text: window.APP?.rfpText || ''
      })
    });
    const data = await res.json(); // { add, delete, unchanged, db_used_codes, db_used_labels }
    renderNewAISuggestions(data.add || [], data.delete || [], data.unchanged || []);
  } catch (e) {
    console.error('Reconcile error:', e);
    renderNewAISuggestions([]);
  }
}

// Render AI Suggestions with Accept/Remove buttons
function renderNewAISuggestions(add = [], del = [], unchanged = []) {
  const root = document.querySelector('#s2-ai-suggest');
  if (!root) return;

  const mkRow = (sug, type) => {
    const row = document.createElement('div');
    row.style = 'display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.06);';

    const left = document.createElement('div');
    left.innerHTML = `<strong>${sug.label || sug}</strong> <span style="opacity:.65;">${
      type === 'add' ? '• suggested' : 
      type === 'del' ? '• not in AI' : 
      '• unchanged'
    }</span>`;

    const right = document.createElement('div');
    right.style = 'display:flex;gap:8px;align-items:center;';

    // Only add action buttons if we have a code
    if (sug.code) {
      // Check if already selected
      const isSel = (S2.selectedCodes || new Set()).has(sug.code);
      if (isSel) {
        const badge = document.createElement('span');
        badge.style = 'background:var(--accent);color:#fff;padding:2px 8px;border-radius:4px;font-size:0.75em;';
        badge.textContent = 'Selected ✓';
        right.appendChild(badge);

        const rm = document.createElement('button');
        rm.className = 'btn-sm';
        rm.textContent = 'Remove';
        rm.style = 'background:var(--danger);';
        rm.onclick = () => s2onRemove(sug.code);
        right.appendChild(rm);
      } else {
        const addBtn = document.createElement('button');
        addBtn.className = 'btn-sm';
        addBtn.textContent = 'Add';
        addBtn.onclick = () => s2onAdd(sug.code);
        right.appendChild(addBtn);
      }
    }

    row.appendChild(left); 
    row.appendChild(right);
    return row;
  };

  root.innerHTML = '';
  if (!add.length && !del.length && !unchanged.length) {
    root.innerHTML = '<div style="opacity:.7;">Run analysis to see suggestions.</div>';
    return;
  }

  if (add.length) {
    const h = document.createElement('div'); 
    h.style = 'font-weight:600;margin-top:8px;margin-bottom:4px;';
    h.textContent = 'AI-Suggested Deliverables';
    root.appendChild(h);
    add.forEach(s => root.appendChild(mkRow(s, 'add')));
  }
  if (del.length) {
    const h = document.createElement('div'); 
    h.style = 'font-weight:600;margin-top:12px;margin-bottom:4px;';
    h.textContent = 'Consider Removing';
    root.appendChild(h);
    del.forEach(s => root.appendChild(mkRow(s, 'del')));
  }
  if (unchanged.length) {
    const h = document.createElement('div'); 
    h.style = 'font-weight:600;margin-top:12px;margin-bottom:4px;';
    h.textContent = 'Unchanged';
    root.appendChild(h);
    unchanged.forEach(lbl => {
      root.appendChild(mkRow({ code: '', label: lbl }, 'unchanged'));
    });
  }
}

// Add deliverable from AI suggestions
function s2onAdd(code) {
  if (!code) return;
  S2.selectedCodes.add(code);
  // AI-suggested deliverables default to ALL components unless user manually edits
  if (!S2.selectedComponentsMap[code]) {
    S2.selectedComponentsMap[code] = 'ALL';
  }
  s2RenderLeft();
  s2RenderRight(S2.els.search?.value || '');
  // Refresh suggestions to update badges
  initAISummaryAndSuggestions();
}

// Remove deliverable from AI suggestions
function s2onRemove(code) {
  if (!code) return;
  S2.selectedCodes.delete(code);
  S2.selectedComponentsMap[code] = undefined;
  s2RenderLeft();
  s2RenderRight(S2.els.search?.value || '');
  // Refresh suggestions to update badges
  initAISummaryAndSuggestions();
}

// Retainer toggle handler
async function onToggleRetainers(e) {
  const enabled = e.target.checked;
  window.APP = window.APP || {};
  
  if (!enabled) {
    window.APP.retainers = [];
    renderRetainerPanel([]);
    return;
  }

  // Get current selection from S2
  const selectedCodes = Array.from(S2.selectedCodes);
  
  if (selectedCodes.length === 0) {
    alert('Please select deliverables first before enabling retainers.');
    e.target.checked = false;
    return;
  }

  const payload = {
    rfp_text: window.APP.rfpText || '',
    deliverable_codes: selectedCodes
  };

  try {
    const res = await fetch('/api/retainer_detect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    const rec = await res.json(); // { retainers: [{deliverable_code, suggested_months, ...}] }

    // Persist and render
    window.APP.retainers = (rec.retainers || []).map(r => ({
      deliverable_code: r.deliverable_code,
      months: r.suggested_months || 12
    }));
    
    renderRetainerPanel(window.APP.retainers);
  } catch (error) {
    console.error('Error detecting retainers:', error);
    alert(`Failed to detect retainers: ${error.message}`);
    e.target.checked = false;
  }
}

// Render the retainer configuration panel
function renderRetainerPanel(retainers) {
  const retainerConfig = document.getElementById('retainer-config');
  const retainerListControls = document.getElementById('retainer-list-controls');
  
  if (!retainerConfig || !retainerListControls) {
    console.warn('Retainer config elements not found');
    return;
  }

  if (!retainers || retainers.length === 0) {
    retainerConfig.style.display = 'none';
    retainerListControls.innerHTML = '';
    return;
  }

  retainerConfig.style.display = 'block';
  
  // Create input fields for each retainer
  retainerListControls.innerHTML = retainers.map(r => {
    const delivName = S2.selectedMeta.get(r.deliverable_code)?.name || r.deliverable_code;
    return `
      <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 12px;">
        <label style="flex: 1; font-weight: 500;">${delivName}</label>
        <input 
          type="number" 
          min="1" 
          max="60" 
          value="${r.months}" 
          data-code="${r.deliverable_code}"
          class="retainer-months-input"
          style="width: 80px; padding: 6px; border: 1px solid var(--muted); border-radius: 4px; background: var(--bg); color: var(--fg);"
        />
        <span style="color: var(--muted); font-size: 0.9em;">months</span>
      </div>
    `;
  }).join('');

  // Update retainer months when inputs change
  retainerListControls.querySelectorAll('.retainer-months-input').forEach(input => {
    input.addEventListener('change', e => {
      const code = e.target.dataset.code;
      const months = parseInt(e.target.value) || 12;
      const retainerIdx = window.APP.retainers.findIndex(r => r.deliverable_code === code);
      if (retainerIdx >= 0) {
        window.APP.retainers[retainerIdx].months = months;
      }
    });
  });
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
  // Call boot to initialize everything
  boot();
  
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
  
  // Sync legacy selectedCodes array with S2.selectedCodes Set
  const codes = S2.selectedCodes.size > 0 ? Array.from(S2.selectedCodes) : selectedCodes || [];
  
  if (codes.length === 0) {
    box.innerHTML = '<p style="color: var(--muted);">No deliverables selected yet.</p>';
    return;
  }
  
  box.innerHTML = "";
  
  codes.forEach(code => {
    // Use helper functions for lookups - works with both AI-suggested and manually selected deliverables
    const name = labelFor(code);
    const category = categoryFor(code);
    
    const selectedComps = selectedComponentsMap[code] || new Set();
    const compCountText = selectedComps.size > 0 ? ` (${selectedComps.size})` : ' (all)';
    
    const item = el(`
      <div class="selection-item">
        <div class="selection-item-left">
          <div class="selection-item-name">${name}</div>
          <div class="selection-item-category">${category}</div>
        </div>
        <div class="selection-item-right">
          <button onclick="openComponentPicker('${code}', '${name.replace(/'/g, "\\'")}')" class="btn-component">Components...${compCountText}</button>
          <button onclick="onRemove('${code}')" class="btn-remove">×</button>
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
    // Use helper functions for lookups
    const name = labelFor(code);
    const category = categoryFor(code);
    
    const item = el(`
      <div class="row">
        <div>
          <strong>${name}</strong> 
          <small class="badge">${category}</small>
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

// ---- Load options and render right-hand list ----
async function s2LoadDeliverables() {
  const r = await fetch('/api/options');   // server returns deliverables + templates
  const data = await r.json();
  S2.allDeliverables = data.deliverables || [];
  
  // Build code→deliverable index for fast lookups
  DELIV_INDEX = {};
  for (const d of (data.deliverables || [])) {
    DELIV_INDEX[String(d.Deliverable_Code).trim()] = d;
  }
  
  s2RenderRight('');
}

function s2RenderRight(filter) {
  const host = S2.els.listRight;
  if (!host) return;
  const q = (filter || '').toLowerCase();
  const items = S2.allDeliverables.filter(d =>
    !q ||
    String(d.Deliverable).toLowerCase().includes(q) ||
    String(d.Category || '').toLowerCase().includes(q) ||
    String(d['Service Department'] || '').toLowerCase().includes(q) ||
    String(d.Deliverable_Code).toLowerCase().includes(q)
  );
  
  // Group by Service Department
  const DEPT_ORDER = ['Strategy', 'Creative', 'Content', 'Production', 'Technology', 'PM', 'Other'];
  const grouped = {};
  items.forEach(d => {
    const dept = d['Service Department'] || 'Other';
    if (!grouped[dept]) grouped[dept] = [];
    grouped[dept].push(d);
  });
  
  // Sort departments by defined order
  const sortedDepts = Object.keys(grouped).sort((a, b) => {
    const aIdx = DEPT_ORDER.indexOf(a);
    const bIdx = DEPT_ORDER.indexOf(b);
    return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx);
  });
  
  // Render grouped deliverables
  const html = sortedDepts.map(dept => {
    const deptItems = grouped[dept].sort((a, b) => {
      const sortA = a.Sort_Order ?? 999;
      const sortB = b.Sort_Order ?? 999;
      if (sortA !== sortB) return sortA - sortB;
      return (a.Deliverable || '').localeCompare(b.Deliverable || '');
    });
    
    const deptHeader = `<div style="font-weight:600; padding:8px 8px 4px; color:var(--accent); border-top:1px solid rgba(255,255,255,0.1); margin-top:4px; background:rgba(139,92,246,0.05);">${dept}</div>`;
    const deptRows = deptItems.map(d => `
      <label class="row" data-deliv-row="1" data-search="${(d.Deliverable + ' ' + (d.Category || '') + ' ' + (d['Service Department'] || '')).toLowerCase()}" 
             style="display:flex;gap:8px;align-items:center;padding:6px 8px;">
        <input type="checkbox" class="s2chk"
          data-code="${d.Deliverable_Code}"
          data-name="${d.Deliverable}"
          data-cat="${d.Category}"
          ${S2.selectedCodes.has(String(d.Deliverable_Code)) ? 'checked' : ''}/>
        <span>${d.Deliverable}</span>
        <small style="margin-left:auto;opacity:.75">${d.Category || ''}</small>
      </label>
    `).join('');
    return deptHeader + deptRows;
  }).join('');
  
  host.innerHTML = html || '<div style="opacity:.7;padding:8px">No deliverables</div>';

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

S2.els.search?.addEventListener('input', e => s2RenderRight(e.target.value));
S2.els.btnSelectAll?.addEventListener('click', () => {
  S2.allDeliverables.forEach(d => {
    S2.selectedCodes.add(String(d.Deliverable_Code));
    S2.selectedMeta.set(String(d.Deliverable_Code), {name: d.Deliverable, category: d.Category});
  });
  s2RenderRight(S2.els.search?.value || '');
  s2RenderLeft();
});
S2.els.btnClear?.addEventListener('click', () => {
  S2.selectedCodes.clear();
  S2.selectedMeta.clear();
  s2RenderRight(S2.els.search?.value || '');
  s2RenderLeft();
});

// ---- Left panel ("Your Selection") with Components… buttons ----
function s2RenderLeft() {
  const host = S2.els.yourSel;
  if (!host) return;
  const rows = Array.from(S2.selectedCodes).map(code => {
    const meta = S2.selectedMeta.get(code) || {name: code, category: ''};
    const selectedComps = S2.selectedComponentsMap[code] || new Set();
    const compCountText = selectedComps.size > 0 ? ` (${selectedComps.size})` : ' (all)';
    return `
      <div class="selection-item">
        <div class="selection-item-left">
          <div class="selection-item-name">${meta.name}</div>
          <div class="selection-item-category">${meta.category || ''}</div>
        </div>
        <div class="selection-item-right">
          <button class="btn-component s2-comp" data-code="${code}" data-name="${meta.name}">Components...${compCountText}</button>
          <button class="btn-remove s2-remove" data-code="${code}">×</button>
        </div>
      </div>`;
  });
  host.innerHTML = rows.join('') || '<p style="color: var(--muted);">No deliverables selected yet.</p>';

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
  
  // Store the deliverable code on the drawer for the close handler
  S2.els.compDrawer.setAttribute('data-active-code', code);
}

// Component drawer close handler - saves selection and updates UI
S2.els.compDone?.addEventListener('click', () => {
  const delivCode = S2.els.compDrawer.getAttribute('data-active-code');
  if (delivCode) {
    const checked = Array.from(S2.els.compList.querySelectorAll('input[type="checkbox"]:checked'))
      .map(x => x.dataset.name)
      .filter(Boolean);
    
    // Save using setComponentsFor (removes key if empty = "all")
    setComponentsFor(delivCode, checked);
    
    // Re-render the left panel to update the component count button
    s2RenderLeft();
  }
  S2.els.compDrawer.classList.add('hidden');
});

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

// Bind buttons
S2.els.btnApply?.addEventListener('click', s2ApplyAndBuild);

window.addEventListener("load", boot);