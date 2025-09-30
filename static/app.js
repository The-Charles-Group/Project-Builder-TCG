let OPTIONS = null;       // cached /api/options
let SCENARIOS = null;     // last built scenarios (A & B)
let DELIVERABLES = [];    // [{deliverable_code, deliverable, category}]

// ---------- Step 2 state ----------
const S2 = {
  options: null,                  // { deliverables: [...] } from /api/options
  selectedCodes: new Set(),       // deliverable codes
  // componentsByDeliv: { DELIV_CODE: Set([...component names...]) }
  componentsByDeliv: {},
};

// Ensure init only runs once
let s2Inited = false;

// Call this after Step 1's "Analyze with AI" (or when you show Step 2)
async function initStep2() {
  if (s2Inited) return; s2Inited = true;

  // Load options (deliverables) for the picker
  const res = await fetch('/api/options');
  const data = await res.json();
  S2.options = data || { deliverables: [] };

  renderDeliverableList();
  wireStep2Handlers();
  document.querySelector('#step2')?.style && (document.querySelector('#step2').style.display = 'block');
}

function wireStep2Handlers() {
  const search = document.querySelector('#s2-deliv-search');

  search && search.addEventListener('input', () => renderDeliverableList(search.value.trim().toLowerCase()));

  document.addEventListener('click', async (e) => {
    // Deliverable picker buttons
    if (e.target.closest('#s2-select-all')) {
      document.querySelectorAll('#s2-deliv-list input[type=checkbox]').forEach(cb => cb.checked = true);
    }
    if (e.target.closest('#s2-clear')) {
      document.querySelectorAll('#s2-deliv-list input[type=checkbox]').forEach(cb => cb.checked = false);
    }
    if (e.target.closest('#s2-apply')) {
      applySelection();
    }

    // Components… button in "Your Selection"
    const compBtn = e.target.closest('[data-action="components"]');
    if (compBtn) {
      const code = compBtn.getAttribute('data-code');
      openComponentsDialog(code);
    }

    // Remove button in "Your Selection"
    const removeBtn = e.target.closest('[data-action="remove"]');
    if (removeBtn) {
      const code = removeBtn.getAttribute('data-code');
      S2.selectedCodes.delete(code);
      delete S2.componentsByDeliv[code];
      renderSelectionPanel();
    }

    // Component dialog: Select all
    const selectAll = e.target.closest('[data-action="comp-select-all"]');
    if (selectAll) {
      const code = selectAll.getAttribute('data-code');
      document.querySelectorAll(`#comp-dialog .comp-checkbox[data-code="${code}"]`).forEach(cb => {
        cb.checked = true;
        const n = cb.getAttribute('data-name');
        S2.componentsByDeliv[code] = S2.componentsByDeliv[code] || new Set();
        S2.componentsByDeliv[code].add(n);
      });
    }

    // Component dialog: Unselect all
    const unselectAll = e.target.closest('[data-action="comp-unselect-all"]');
    if (unselectAll) {
      const code = unselectAll.getAttribute('data-code');
      document.querySelectorAll(`#comp-dialog .comp-checkbox[data-code="${code}"]`).forEach(cb => {
        cb.checked = false;
      });
      S2.componentsByDeliv[code] = new Set();
    }

    // Component dialog: Close
    const closeBtn = e.target.closest('[data-action="comp-close"]');
    if (closeBtn) {
      document.getElementById('comp-backdrop')?.remove();
      document.getElementById('comp-dialog')?.remove();
      renderSelectionPanel();
    }
  });
}

function renderDeliverableList(filter = '') {
  const box = document.querySelector('#s2-deliv-list');
  if (!box || !S2.options) return;

  const items = (S2.options.deliverables || [])
    .filter(d => {
      if (!filter) return true;
      return (
        String(d.Deliverable).toLowerCase().includes(filter) ||
        String(d.Category).toLowerCase().includes(filter) ||
        String(d.Deliverable_Code).toLowerCase().includes(filter)
      );
    })
    .map(d => `
      <label class="row">
        <input type="checkbox" data-code="${d.Deliverable_Code}" />
        <span class="name">${d.Deliverable}</span>
        <span class="pill">${d.Category}</span>
      </label>
    `)
    .join('');

  box.innerHTML = items || `<div class="muted">No deliverables found.</div>`;
}

function applySelection() {
  const picked = Array.from(document.querySelectorAll('#s2-deliv-list input[type=checkbox]:checked'))
    .map(cb => cb.getAttribute('data-code'))
    .filter(Boolean);

  if (!picked.length) {
    alert('Please select at least one deliverable before proceeding to pricing.');
    return;
  }

  // Merge into selection, maintain insertion order
  picked.forEach(code => S2.selectedCodes.add(code));

  // Default: when a deliverable is added, pre‑select **all** components (can unselect later).
  picked.forEach(code => { if (!S2.componentsByDeliv[code]) S2.componentsByDeliv[code] = 'ALL'; });

  renderSelectionPanel();
}

function renderSelectionPanel() {
  const wrap = document.querySelector('#s2-selected-list');
  if (!wrap) return;
  const byCode = indexDeliverablesByCode();

  const rows = Array.from(S2.selectedCodes).map(code => {
    const d = byCode[code] || { Deliverable: code, Category: '' };
    const compCount = S2.componentsByDeliv[code] === 'ALL' ? 'all' : 
                      (S2.componentsByDeliv[code] instanceof Set ? S2.componentsByDeliv[code].size : 'all');
    return `
      <div class="row">
        <div style="flex:1">
          <div class="name">${d.Deliverable}</div>
          <div class="muted">${d.Category}</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="btn small" data-action="components" data-code="${code}">Components… (${compCount})</button>
          <button class="btn small" data-action="remove" data-code="${code}" style="background:#b00020;border-color:#b00020;padding:4px 8px">✕</button>
        </div>
      </div>`;
  });

  wrap.innerHTML = rows.join('') || `<div class="muted">No deliverables selected yet.</div>`;
}

function indexDeliverablesByCode() {
  const idx = {};
  (S2.options?.deliverables || []).forEach(d => { idx[String(d.Deliverable_Code)] = d; });
  return idx;
}

// Build API payload from S2 state and form inputs
function buildPayloadForApi() {
  const selected_deliverable_codes = Array.from(S2.selectedCodes);
  
  const selected_components_map = {};
  for (const code of selected_deliverable_codes) {
    const pick = S2.componentsByDeliv[code];
    if (!pick || pick === 'ALL') continue; // omit -> backend uses all components
    if (pick instanceof Set) selected_components_map[code] = [...pick]; // list format
    else selected_components_map[code] = pick; // dict {name: hours}
  }
  
  return {
    selected_deliverable_codes,
    selected_components_map,
    scenario_a: { mode: 'template', scenario_key: document.querySelector('#scenarioA')?.value || 'MED_LOW' },
    scenario_b: { mode: 'template', scenario_key: document.querySelector('#scenarioB')?.value || 'MED_HIGH' },
    pricing_mode: document.querySelector('#pricingMode')?.value || 'Flat_Blended',
    blended_rate: Number(document.querySelector('#blendedRate')?.value || 195),
    rate_band: document.querySelector('#rateBand')?.value || 'Standard_US',
    use_slack: (document.querySelector('#useSlack')?.checked ?? true),
    slack_after_internal: Number(document.querySelector('#slackAfterInternal')?.value || 1),
    slack_after_client: Number(document.querySelector('#slackAfterClient')?.value || 2),
    slack_global_pct: Number(document.querySelector('#slackGlobalPct')?.value || 0.05),
    project_start: document.querySelector('#projectStart')?.value || null
  };
}

// Modal/dialog for components (inline simple version)
async function openComponentsDialog(code) {
  // Load components from backend
  const res = await fetch(`/api/components_for?deliverable_code=${encodeURIComponent(code)}`);
  const data = await res.json();
  const items = data.items || [];

  // Default: all checked on first open if we had 'ALL' marker
  let selected = S2.componentsByDeliv[code];
  if (selected === 'ALL') { selected = new Set(items.map(i => i.name)); S2.componentsByDeliv[code] = selected; }
  if (!selected) selected = new Set();

  // Get deliverable name for display
  const byCode = indexDeliverablesByCode();
  const delivName = byCode[code]?.Deliverable || code;

  // Render dialog with backdrop
  const dlgId = 'comp-dialog';
  let backdrop = document.getElementById('comp-backdrop');
  let dlg = document.getElementById(dlgId);
  
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.id = 'comp-backdrop';
    backdrop.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);z-index:999';
    backdrop.onclick = () => { backdrop.remove(); dlg?.remove(); renderSelectionPanel(); };
    document.body.appendChild(backdrop);
  }
  
  if (!dlg) {
    dlg = document.createElement('div');
    dlg.id = dlgId;
    dlg.className = 'dialog';
    document.body.appendChild(dlg);
  }

  dlg.innerHTML = `
    <div class="card">
      <div class="header">
        <div><strong>Components</strong> — ${delivName}</div>
        <div style="display:flex;gap:8px">
          <button class="btn small" data-action="comp-select-all" data-code="${code}">Select all</button>
          <button class="btn small" data-action="comp-unselect-all" data-code="${code}">Unselect all</button>
          <button class="btn small" data-action="comp-close">Close</button>
        </div>
      </div>
      <div class="body">
        ${items.map(i => `
          <label class="row">
            <input type="checkbox" ${selected.has(i.name) ? 'checked' : ''} 
                   data-code="${code}" data-name="${i.name}"
                   class="comp-checkbox" />
            <span class="name">${i.name}</span>
            <span class="muted">${Number(i.hours).toFixed(1)} h</span>
          </label>
        `).join('')}
      </div>
    </div>
  `;
  
  // Wire up checkbox handlers
  dlg.querySelectorAll('.comp-checkbox').forEach(cb => {
    cb.addEventListener('change', function() {
      const c = this.getAttribute('data-code');
      const n = this.getAttribute('data-name');
      S2.componentsByDeliv[c] = S2.componentsByDeliv[c] || new Set();
      if (this.checked) { 
        S2.componentsByDeliv[c].add(n); 
      } else { 
        S2.componentsByDeliv[c].delete(n); 
      }
    });
  });
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

  // Pricing default blended - with null check
  const ps = OPTIONS.pricing_settings.find(x => x.Key==="Default_Blended_Rate");
  const blendedRateEl = document.querySelector("#blendedRate");
  if(ps && blendedRateEl) {
    blendedRateEl.value = ps.Default;
  }

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
  
  // Wire up component drawer Done button
  const compDoneBtn = document.getElementById('compDone');
  if (compDoneBtn) {
    compDoneBtn.addEventListener('click', () => {
      const drawer = document.getElementById('compDrawer');
      if (drawer) drawer.style.display = 'none';
      
      // Save component selections for the current deliverable being edited
      const title = document.getElementById('compTitle');
      if (title && title.textContent) {
        const match = title.textContent.match(/Components — (.+)/);
        if (match) {
          const delivName = match[1];
          const code = DELIVERABLES.find(d => d.Deliverable === delivName)?.Deliverable_Code;
          if (code) {
            saveComponentsFor(code);
          }
        }
      }
    });
  }

  onPricingModeChanged();
}

function onPricingModeChanged(){
  const pricingMode = document.querySelector("#pricingMode");
  if (!pricingMode) return;
  const mode = pricingMode.value;
  
  // Sync to S2 state
  S2.pricingMode = mode;
  
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
  // Use only S2.selectedCodes - no AI merge
  if (S2.selectedCodes.length === 0) {
    alert("Please select at least one deliverable before proceeding to pricing.");
    return;
  }
  
  // Sync legacy state for compatibility
  selectedCodes = [...S2.selectedCodes];
  if (window.appState) window.appState.selectedCodes = [...S2.selectedCodes];
  
  // Build scenarios using buildPayloadForApi
  try {
    const payload = buildPayloadForApi();
    const res = await fetch('/api/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    if (!res.ok) {
      throw new Error(`Build failed: ${await res.text()}`);
    }
    
    const data = await res.json();
    SCENARIOS = data.scenarios || {};
    
    console.log(`Build completed with ${S2.selectedCodes.length} deliverables`);
  } catch (error) {
    console.error("Failed to build scenarios:", error);
    alert("Failed to build scenarios. Please try again.");
    return;
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
  // Initialize and show Step 2
  await initStep2();
  
  // Scroll to Step 2
  const step2 = document.querySelector("#step2");
  if (step2) {
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

