let OPTIONS = null;       // cached /api/options
let SCENARIOS = null;     // last built scenarios (A & B)
let DELIVERABLES = [];    // [{deliverable_code, deliverable, category}]
let DELIV_INDEX = {};     // code -> deliverable object lookup for fast rendering
let DELIV_INDEX_LO = {};  // lowercase code lookup for defensive matching

// ================================================================================
// Centralized Step 2 State - Single Source of Truth (selectionStore)
// ================================================================================
window.APB = window.APB || {};

// Unified selection store per requirements
const selectionStore = {
  deliverables: new Set(),                       // deliverable codes (e.g., deck_strategy)
  componentsByDeliv: new Map(),                  // Map<delivCode, Set<componentName>>
  l3ByComponent: new Map(),                      // Map<delivCode::componentKey, Set<l3Name>>
};

window.APB.step2 = {
  rfpText: '',                                   // filled from Step 1 or sessionStorage
  selectedCodes: selectionStore.deliverables,    // alias for compatibility
  selectedComponentsByCode: {},                  // DEPRECATED: use selectionStore.componentsByDeliv
  selectedL3ByKey: {},                           // DEPRECATED: use selectionStore.l3ByComponent
  complexity: 'Advanced',                        // default complexity
  tier: 'T2_MediumVolume',                       // default tier
  activeDeliverableCode: null,                   // currently active deliverable in Components panel
  activeComponentName: null,                     // currently active component in L3 panel
  allDeliverables: [],                           // from /api/options
  aiSuggestedCodes: new Set(),                   // codes that came from AI suggestions
  filters: {                                     // Task 1.3: search filter state
    deliverables: '',
    components: '',
    l3: ''
  },
  els: {                                         // DOM element references
    listRight: null,
    search: null,
    btnApply: null,
    btnSelectAll: null,
    btnClear: null,
    yourSel: null,
    compDrawer: null,
    compList: null,
    compTitle: null,
    compDone: null,
  }
};

// Export selectionStore globally for access
window.selectionStore = selectionStore;

// Aliases for compatibility with existing code
const S2 = window.APB.step2;

// Create dynamic getters that always reference the current object (survives resets to {})
Object.defineProperty(window, 'selectedComponentsMap', {
  get() { return S2.selectedComponentsByCode; },
  configurable: true
});

Object.defineProperty(S2, 'selectedComponentsMap', {
  get() { return S2.selectedComponentsByCode; },
  configurable: true
});

// CRITICAL FIX: Create Proxy-backed object for selectedL3ByKey (Task 6 fix)
// This ensures ALL read/write operations sync with selectionStore.l3ByComponent
const selectedL3Proxy = new Proxy({}, {
  get(target, key) {
    // Let Object.entries(), Object.keys() work via ownKeys/getOwnPropertyDescriptor
    return selectionStore.l3ByComponent.get(String(key));
  },
  set(target, key, value) {
    if (value instanceof Set) {
      selectionStore.l3ByComponent.set(String(key), value);
    } else if (Array.isArray(value)) {
      selectionStore.l3ByComponent.set(String(key), new Set(value));
    } else if (value === undefined || value === null) {
      selectionStore.l3ByComponent.delete(String(key));
    }
    return true;
  },
  deleteProperty(target, key) {
    selectionStore.l3ByComponent.delete(String(key));
    return true;
  },
  has(target, key) {
    return selectionStore.l3ByComponent.has(String(key));
  },
  ownKeys() {
    return Array.from(selectionStore.l3ByComponent.keys());
  },
  getOwnPropertyDescriptor(target, key) {
    if (selectionStore.l3ByComponent.has(String(key))) {
      return {
        enumerable: true,
        configurable: true,
        value: selectionStore.l3ByComponent.get(String(key))
      };
    }
  }
});

// Lock the property to prevent accidental reassignment
Object.defineProperty(S2, 'selectedL3ByKey', {
  get() { return selectedL3Proxy; },
  set(value) {
    // If someone tries to replace the whole object, sync it to the Map instead
    if (value === null || (typeof value === 'object' && Object.keys(value).length === 0)) {
      selectionStore.l3ByComponent.clear();
    } else if (typeof value === 'object') {
      selectionStore.l3ByComponent.clear();
      Object.entries(value).forEach(([k, v]) => {
        if (v instanceof Set) {
          selectionStore.l3ByComponent.set(k, v);
        } else if (Array.isArray(v)) {
          selectionStore.l3ByComponent.set(k, new Set(v));
        }
      });
    }
  },
  configurable: true
});

// Legacy compatibility
let selectedCodes = [];
let removedCodes = [];
let addedCodes = [];

// Cache for component data per deliverable code
const componentDataCache = {};
window.componentDataCache = componentDataCache;

// Concurrency guard for renderYourSelection
let renderYourSelectionToken = 0;

// Debounce utility for search filters (Task 1.3)
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

// Helper to normalize keys for defensive lookup
function key(s) {
  return String(s).trim().toLowerCase();
}

// Defensive lookup that handles case differences
function fromAny(code) {
  return DELIV_INDEX[String(code)] || DELIV_INDEX_LO[key(code)] || null;
}

// Helper functions to get deliverable info from code
function labelFor(code) {
  const row = fromAny(code);
  return row ? row.Deliverable : String(code);
}

function categoryFor(code) {
  const row = fromAny(code);
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

// ================================================================================
// Centralized Step 2 Hydration Functions - wire ALL entry points to selectionStore
// ================================================================================

async function hydrateComponentsFor(delivCode) {
  try {
    const comps = await api(`/api/components?deliverable=${encodeURIComponent(delivCode)}`);
    selectionStore.componentsByDeliv.set(delivCode, new Set(comps));
    
    // Auto-load ALL L3 for ALL components (Task 1.1 requirement)
    if (comps.length > 0) {
      await Promise.all(comps.map(comp => hydrateL3For(delivCode, comp)));
    }
  } catch (error) {
    console.error(`Failed to hydrate components for ${delivCode}:`, error);
  }
}

async function hydrateL3For(delivCode, componentName) {
  try {
    const l3 = await api(`/api/l3?deliverable=${encodeURIComponent(delivCode)}&component=${encodeURIComponent(componentName)}`);
    const key = `${delivCode}::${componentName}`;
    selectionStore.l3ByComponent.set(key, new Set(l3));
  } catch (error) {
    console.error(`Failed to hydrate L3 for ${delivCode}::${componentName}:`, error);
  }
}

async function selectDeliverable(code) {
  selectionStore.deliverables.add(code);
  APB.step2.selectedCodes = selectionStore.deliverables; // sync alias
  
  // Hydrate components for this deliverable
  await hydrateComponentsFor(code);
  
  // Re-render all panels
  if (window.renderDeliverablesPanel) renderDeliverablesPanel();
  if (window.renderComponentsPanel) renderComponentsPanel(code);
  if (window.renderSummary) renderSummary();
}

async function deselectDeliverable(code) {
  selectionStore.deliverables.delete(code);
  selectionStore.componentsByDeliv.delete(code);
  
  // Remove all L3 entries for this deliverable
  Array.from(selectionStore.l3ByComponent.keys())
    .filter(k => k.startsWith(`${code}::`))
    .forEach(k => selectionStore.l3ByComponent.delete(k));
  
  APB.step2.selectedCodes = selectionStore.deliverables; // sync alias
  
  // Re-render panels
  if (window.renderDeliverablesPanel) renderDeliverablesPanel();
  if (window.renderSummary) renderSummary();
  
  // If this was an AI suggestion, show Add button again
  if (APB.step2.aiSuggestedCodes.has(code)) {
    if (window.renderAISuggestions) renderAISuggestions();
  }
}

// Export hydration functions globally
window.selectDeliverable = selectDeliverable;
window.deselectDeliverable = deselectDeliverable;
window.hydrateComponentsFor = hydrateComponentsFor;
window.hydrateL3For = hydrateL3For;

async function boot() {
  await api("/api/load");
  OPTIONS = await api("/api/options");
  
  // Initialize APB.step2 state - load RFP text from sessionStorage or localStorage
  APB.step2.rfpText = sessionStorage.getItem('apb.rfp_text') || localStorage.getItem('apb.rfpText.v1') || '';
  APB.step2.allDeliverables = OPTIONS.deliverables || [];
  
  // Initialize DOM element references for Step 2
  APB.step2.els.listRight = document.querySelector('#s2-deliv-list, #deliverableList');
  APB.step2.els.search = document.querySelector('#s2-deliv-search, #delivSearch');
  APB.step2.els.btnApply = document.querySelector('#s2-apply, #applySelection, #btnApplySelection');
  APB.step2.els.btnSelectAll = document.querySelector('#s2-deliv-selectall, #delivSelectAll');
  APB.step2.els.btnClear = document.querySelector('#s2-deliv-clear, #delivClear');
  APB.step2.els.yourSel = document.querySelector('#s2-your-list, #yourSelection, #yourSelectionList');
  APB.step2.els.compDrawer = document.getElementById('compDrawer');
  APB.step2.els.compList = document.getElementById('compList');
  APB.step2.els.compTitle = document.getElementById('compTitle');
  APB.step2.els.compDone = document.getElementById('compDone');
  
  // Populate dropdowns (with duplicate removal)
  const pricingMode = document.querySelector("#pricingMode");
  if (pricingMode) populateSelect(pricingMode, OPTIONS.pricing_modes);
  const rateBand = document.querySelector("#rateBand");
  if (rateBand) populateSelect(rateBand, OPTIONS.rate_bands);
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
  DELIV_INDEX_LO = {};
  for (const d of (OPTIONS.deliverables || [])) {
    const code = String(d.Deliverable_Code).trim();
    DELIV_INDEX[code] = d;
    DELIV_INDEX_LO[key(code)] = d;
  }
  
  renderDeliverableList(DELIVERABLES);

  // Initialize Step 2 state
  selectedCodes = [];
  removedCodes = [];
  addedCodes = [];
  
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
    reconcileBtn.onclick = async (e) => {
      e.preventDefault();
      
      // Task 1.7: Get RFP text from multiple sources including backend cache
      let rfpText = window.APP?.rfpText || APB.step2.rfpText || sessionStorage.getItem('apb.rfp_text') || localStorage.getItem('apb.rfpText.v1') || '';
      
      // If still no text, check if we have a stored analysis summary
      if (!rfpText && sessionStorage.getItem('apb:rfpSummary')) {
        try {
          const summary = JSON.parse(sessionStorage.getItem('apb:rfpSummary'));
          if (summary && summary.summary_text) {
            rfpText = summary.summary_text; // Use summary as fallback
          }
        } catch (e) {
          console.warn('Could not parse stored summary:', e);
        }
      }
      
      // Task 1.7: If still no text, try backend RFP cache (uses LAST_UPLOAD_FILENAME)
      if (!rfpText) {
        try {
          const cacheRes = await fetch('/api/rfp/cache');
          if (cacheRes.ok) {
            const cacheData = await cacheRes.json();
            if (cacheData.text) {
              rfpText = cacheData.text;
              console.log('Using cached RFP text from backend');
            }
          }
        } catch (e) {
          console.warn('Could not fetch backend RFP cache:', e);
        }
      }
      
      if (!rfpText) {
        // Last resort: show non-blocking message but don't prevent refresh
        console.warn('No RFP text found - refresh may have limited results');
      }
      
      try {
        const res = await fetch('/api/suggest_by_text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rfp_text: rfpText })
        });
        
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        
        const data = await res.json();
        // Update stored summary with new suggestions
        window.APP = window.APP || {};
        window.APP.summary = data;
        sessionStorage.setItem('apb:rfpSummary', JSON.stringify(data));
        
        // Re-render AI summary and suggestions
        initAISummaryAndSuggestions();
      } catch (error) {
        console.error('Refresh error:', error);
        alert(`Failed to refresh suggestions: ${error.message}`);
      }
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
    
    if (compSet instanceof Set) {
      // User has customized component selection (could be all, some, or none)
      if (compSet.size > 0) {
        // User has selected specific components
        const dict = Object.create(null);
        compSet.forEach(label => { dict[label] = null; });
        selectedComponentsPayload[code] = dict;
      } else {
        // Empty Set means user unchecked all - send empty object
        selectedComponentsPayload[code] = {};
      }
    } else if (compSet && typeof compSet === 'object') {
      // Already in object format
      selectedComponentsPayload[code] = compSet;
    } else {
      // No customization - send "__ALL__" sentinel to include all default components
      selectedComponentsPayload[code] = "__ALL__";
    }
  });

  // Include L3 subtasks from APB.step2.selectedL3ByKey
  // Format: { deliverableCode: { component: [l3tasks...] } }
  const l3Payload = {};
  Object.entries(APB.step2.selectedL3ByKey).forEach(([key, l3Set]) => {
    const [code, component] = key.split('::');
    if (codes.includes(code) && l3Set && l3Set.size > 0) {
      if (!l3Payload[code]) l3Payload[code] = {};
      l3Payload[code][component] = Array.from(l3Set);
    }
  });

  // Include retainers if toggle is enabled
  const retainersEnabled = document.querySelector('#retainersToggle')?.checked || false;
  const retainersPayload = retainersEnabled ? (window.APP?.retainers || []) : [];

  const payload = {
    selected_deliverable_codes: codes,
    selected_components_map: selectedComponentsPayload,
    selected_l3_map: l3Payload,
    pricing_mode: window.getPricingModeFromUI?.() || 'Flat_Blended',
    blended_rate: window.getBlendedRateFromUI?.() || 195,
    rate_band: window.getRateBandFromUI?.() || 'Standard_US',
    use_slack: window.getUseSlackFromUI?.() || false,
    slack_after_internal: window.getSlackInternalFromUI?.() || 1,
    slack_after_client: window.getSlackClientFromUI?.() || 2,
    slack_global_pct: window.getSlackPctFromUI?.() || 0.05,
    project_start: window.getProjectStartFromUI?.() || null,
    client_budget_usd: window.getClientBudgetFromUI?.() || null,
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
  const btnAnalyze = document.querySelector('#btnAnalyze');

  let summary;
  try {
    if (fileEl?.files?.length) {
      // Disable button and show loading state
      if (btnAnalyze) {
        btnAnalyze.disabled = true;
        btnAnalyze.textContent = 'Analyzing...';
      }
      
      const form = new FormData();
      form.append('file', fileEl.files[0]);
      const res = await fetch('/api/summarize_by_file', { method: 'POST', body: form });
      if (!res.ok) {
        throw new Error(`Server error: ${res.status} ${res.statusText}`);
      }
      summary = await res.json(); // { summary_text, deliverables: [{label, short_desc, tasks}], word_count }
    } else if (rfpText) {
      // Disable button and show loading state
      if (btnAnalyze) {
        btnAnalyze.disabled = true;
        btnAnalyze.textContent = 'Analyzing...';
      }
      
      const res = await fetch('/api/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rfp_text: rfpText })
      });
      if (!res.ok) {
        throw new Error(`Server error: ${res.status} ${res.statusText}`);
      }
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
    sessionStorage.setItem('apb.rfp_text', rfpText);
    
    // Also persist to localStorage for reliability across refreshes
    localStorage.setItem('apb.rfpText.v1', rfpText);
    
    // Update centralized state
    APB.step2.rfpText = rfpText;

    // Show Step 2
    const step2 = document.getElementById('step2');
    if (step2) {
      step2.style.display = 'block';
      step2.scrollIntoView({ behavior: 'smooth' });
    }

    // Render summary & suggestions on Step 2
    initAISummaryAndSuggestions();
    
    // PATCH: Auto-fill project name from last upload
    try {
      const nameRes = await fetch('/api/last_upload_name');
      if (nameRes.ok) {
        const {project_name_default} = await nameRes.json();
        const projectInput = document.querySelector('#projectName');
        if (projectInput && project_name_default && !projectInput.value) {
          projectInput.value = project_name_default;
        }
      }
    } catch (e) {
      console.warn('Could not fetch project name default:', e);
    }
    
  } catch (error) {
    console.error('Error analyzing RFP:', error);
    alert(`Error getting AI analysis: ${error.message}`);
  } finally {
    // Re-enable button
    if (btnAnalyze) {
      btnAnalyze.disabled = false;
      btnAnalyze.textContent = 'Analyze with AI';
    }
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

// Render AI Suggestions with persistent toggle buttons (rows never disappear)
function renderNewAISuggestions(add = [], del = [], unchanged = []) {
  const root = document.querySelector('#s2-ai-suggest');
  if (!root) return;

  const mkRow = (sug, type) => {
    const row = document.createElement('div');
    row.style = 'display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.06);';
    row.dataset.code = sug.code || '';

    const left = document.createElement('div');
    left.innerHTML = `<strong>${sug.label || sug}</strong> <span style="opacity:.65;">${
      type === 'add' ? '• suggested' : 
      type === 'del' ? '• not in AI' : 
      '• unchanged'
    }</span>`;

    const right = document.createElement('div');
    right.style = 'display:flex;gap:8px;align-items:center;';

    // Create persistent toggle button (never disappears)
    if (sug.code) {
      const isSel = APB.step2.selectedCodes.has(sug.code);
      
      const toggleBtn = document.createElement('button');
      toggleBtn.className = 'btn-sm btn-suggest';
      toggleBtn.dataset.code = sug.code;
      toggleBtn.dataset.mode = isSel ? 'remove' : 'add';
      toggleBtn.textContent = isSel ? 'Added • Remove' : 'Add';
      toggleBtn.style = isSel ? 'background:var(--danger);' : '';
      toggleBtn.onclick = () => toggleSuggestedDeliverable(row, sug.code, !isSel);
      right.appendChild(toggleBtn);
    }

    row.appendChild(left); 
    row.appendChild(right);
    return row;
  };

  root.innerHTML = '';
  
  // Show non-blocking tip if no RFP text
  if (!APB.step2.rfpText) {
    const tip = document.createElement('div');
    tip.style = 'background:rgba(255,193,7,0.1);border-left:3px solid #ffc107;padding:8px 12px;margin-bottom:12px;font-size:0.9em;';
    tip.innerHTML = '<strong>Tip:</strong> No RFP text in memory. Suggestions will be blank until you paste text or re-run Step 1.';
    root.appendChild(tip);
  }
  
  if (!add.length && !del.length && !unchanged.length) {
    root.innerHTML += '<div style="opacity:.7;">Run analysis to see suggestions.</div>';
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
  
  // Sync with new Step 2 UI state
  if (window.step2PickerState) {
    window.step2PickerState.selected.add(code);
  }
  
  // Update new Step 2 UI
  if (window.step2State) {
    window.step2State.currentDeliverable = code;
    if (window.populateComponentsDeliverableDropdown) {
      window.populateComponentsDeliverableDropdown();
    }
    if (window.renderComponentsPanel) {
      window.renderComponentsPanel(code);
    }
    if (window.updateStep2Summary) {
      window.updateStep2Summary();
    }
  }
  
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
  
  // Sync with new Step 2 UI state
  if (window.step2PickerState) {
    window.step2PickerState.selected.delete(code);
  }
  
  // Update new Step 2 UI
  if (window.step2State) {
    // If we're removing the currently active deliverable, clear it and reset panels
    if (window.step2State.currentDeliverable === code) {
      window.step2State.currentDeliverable = null;
      if (window.renderComponentsPanel) {
        window.renderComponentsPanel(null);
      }
    }
    if (window.populateComponentsDeliverableDropdown) {
      window.populateComponentsDeliverableDropdown();
    }
    if (window.updateStep2Summary) {
      window.updateStep2Summary();
    }
  }
  
  // Refresh suggestions to update badges
  initAISummaryAndSuggestions();
}

// ================================================================================
// Centralized Step 2 Functions - Single Source of Truth (APB.step2)
// ================================================================================

// Toggle suggested deliverable (persistent button - never removes row)
// TASK 5: Wire AI Add/Remove buttons to centralized selectionStore with auto-hydration
async function toggleSuggestedDeliverable(rowEl, code, add) {
  const btn = rowEl.querySelector('.btn-suggest');
  if (!btn) return;
  
  if (add) {
    // Use centralized selectDeliverable with auto-hydration
    await selectDeliverable(code);
    APB.step2.aiSuggestedCodes.add(code); // Track as AI-suggested
    APB.step2.activeDeliverableCode = code;
    btn.textContent = 'Added • Remove';
    btn.dataset.mode = 'remove';
    btn.style.background = 'var(--danger)';
  } else {
    // Use centralized deselectDeliverable with cleanup
    await deselectDeliverable(code);
    if (APB.step2.activeDeliverableCode === code) {
      APB.step2.activeDeliverableCode = null;
    }
    btn.textContent = 'Add';
    btn.dataset.mode = 'add';
    btn.style.background = '';
  }
  
  await refreshComponentsPanel();
  updateSummaryCounts();
  
  // Refresh AI suggestions to update other buttons
  initAISummaryAndSuggestions();
}

// Render deliverables panel with Selected on top, then Other (Task 1.5: with search filter)
function renderDeliverablesPanel() {
  const list = APB.step2.allDeliverables;
  const filter = (APB.step2.filters.deliverables || '').toLowerCase();
  const selected = [], other = [];
  
  list.forEach(d => {
    const code = String(d.Deliverable_Code);
    const name = (d.Deliverable || '').toLowerCase();
    const category = (d.Category || '').toLowerCase();
    
    // Apply search filter
    if (filter && !name.includes(filter) && !category.includes(filter) && !code.toLowerCase().includes(filter)) {
      return; // Skip items that don't match filter
    }
    
    if (APB.step2.selectedCodes.has(code)) {
      selected.push(d);
    } else {
      other.push(d);
    }
  });
  
  const host = APB.step2.els.listRight;
  if (!host) return;
  
  let html = '';
  
  // Render Selected group
  if (selected.length > 0) {
    html += '<div style="font-weight:600;padding:8px;color:var(--accent);background:rgba(139,92,246,0.05);border-bottom:1px solid rgba(255,255,255,0.1);">Selected</div>';
    selected.forEach(d => {
      const code = String(d.Deliverable_Code);
      const isActive = APB.step2.activeDeliverableCode === code;
      html += `
        <label class="row deliv-row" data-code="${code}" style="display:flex;gap:8px;align-items:center;padding:6px 8px;cursor:pointer;background:${isActive ? 'rgba(139,92,246,0.15)' : 'rgba(139,92,246,0.03)'};border-left:${isActive ? '3px solid var(--accent)' : '3px solid transparent'};">
          <input type="checkbox" class="deliv-checkbox" data-code="${code}" checked data-visible="1" />
          <span>${d.Deliverable}</span>
          <button onclick="event.stopPropagation(); removeDeliverableX('${code}')" style="margin-left:auto;background:none;border:none;color:var(--danger);cursor:pointer;font-size:1.2em;padding:0 8px;">×</button>
          <small style="opacity:.75">${d.Category || ''}</small>
        </label>
      `;
    });
  }
  
  // Render Other group
  if (other.length > 0) {
    html += '<div style="font-weight:600;padding:8px;color:var(--muted);margin-top:8px;">Other</div>';
    other.forEach(d => {
      const code = String(d.Deliverable_Code);
      html += `
        <label class="row deliv-row" data-code="${code}" style="display:flex;gap:8px;align-items:center;padding:6px 8px;cursor:pointer;">
          <input type="checkbox" class="deliv-checkbox" data-code="${code}" data-visible="1" />
          <span>${d.Deliverable}</span>
          <small style="margin-left:auto;opacity:.75">${d.Category || ''}</small>
        </label>
      `;
    });
  }
  
  if (!html) {
    html = '<div style="opacity:.7;padding:8px;text-align:center;">No deliverables match your search</div>';
  }
  
  host.innerHTML = html;
  
  // Attach checkbox handlers
  host.querySelectorAll('.deliv-checkbox').forEach(cb => {
    cb.addEventListener('change', e => {
      e.stopPropagation(); // Prevent row click from triggering
      onDeliverableToggle(e.target.dataset.code, e.target.checked);
    });
  });
  
  // Attach row click handlers to set active deliverable (preview only)
  host.querySelectorAll('.deliv-row').forEach(row => {
    row.addEventListener('click', async (e) => {
      // Only trigger if clicking the row itself, not the checkbox or button
      if (e.target.classList.contains('deliv-checkbox')) return;
      if (e.target.tagName === 'BUTTON') return;
      
      const code = row.dataset.code;
      const checkbox = row.querySelector('.deliv-checkbox');
      
      // Row click = preview only (do not change selection)
      // Only show components if the deliverable is actually selected
      if (checkbox.checked) {
        APB.step2.activeDeliverableCode = code;
        renderDeliverablesPanel(); // Re-render to update active highlight
        await refreshComponentsPanel();
      }
      // If not selected, row click does nothing (checkbox is the only way to select)
    });
  });
}

// Deliverable checkbox toggle handler
async function onDeliverableToggle(code, checked) {
  if (checked) {
    await selectDeliverable(code);
  } else {
    await deselectDeliverable(code);
  }
  
  renderDeliverablesPanel();
  await refreshComponentsPanel();
  updateSummaryCounts();
  
  // Refresh AI suggestions to update button states
  initAISummaryAndSuggestions();
}

// Task 1.5: Remove deliverable via X button
window.removeDeliverableX = async function(code) {
  await deselectDeliverable(code);
  renderDeliverablesPanel();
  await refreshComponentsPanel();
  updateSummaryCounts();
  initAISummaryAndSuggestions();
}

// Refresh components panel for active deliverable
async function refreshComponentsPanel() {
  const code = APB.step2.activeDeliverableCode || getActiveDeliverableCode();
  if (!code) {
    renderComponentsEmptyState();
    return;
  }
  
  const { complexity, tier } = APB.step2;
  
  try {
    const res = await fetch(`/api/components_for?deliverable_code=${encodeURIComponent(code)}&complexity=${encodeURIComponent(complexity)}&tier=${encodeURIComponent(tier)}`);
    const json = await res.json();
    
    renderComponentsChecklist(code, json.items || []);
  } catch (e) {
    console.error('Error loading components:', e);
    renderComponentsEmptyState('Error loading components');
  }
}

// Get active deliverable code (first selected one if no explicit active)
function getActiveDeliverableCode() {
  if (APB.step2.activeDeliverableCode && APB.step2.selectedCodes.has(APB.step2.activeDeliverableCode)) {
    return APB.step2.activeDeliverableCode;
  }
  const codes = Array.from(APB.step2.selectedCodes);
  return codes.length > 0 ? codes[0] : null;
}

// Render components checklist
function renderComponentsChecklist(code, items) {
  const listEl = document.getElementById('s2-comp-list');
  if (!listEl) return;
  
  if (items.length === 0) {
    listEl.innerHTML = '<p style="color:var(--muted);text-align:center;padding:40px 8px;">No components available</p>';
    return;
  }
  
  // Initialize selection if not exists
  if (!APB.step2.selectedComponentsByCode[code]) {
    APB.step2.selectedComponentsByCode[code] = new Set(items.map(c => c.name));
  }
  
  const selectedSet = APB.step2.selectedComponentsByCode[code];
  
  listEl.innerHTML = items.map(comp => `
    <label style="display:flex;gap:8px;align-items:center;padding:6px 8px;cursor:pointer;">
      <input type="checkbox" class="comp-checkbox" data-comp="${comp.name}" 
             ${selectedSet.has(comp.name) ? 'checked' : ''} />
      <span style="font-size:0.9em;">${comp.name}</span>
    </label>
  `).join('');
  
  // Attach handlers
  listEl.querySelectorAll('.comp-checkbox').forEach(cb => {
    cb.addEventListener('change', async (e) => {
      const compName = e.target.dataset.comp;
      const key = `${code}::${compName}`;
      
      if (e.target.checked) {
        selectedSet.add(compName);
        // Clear and refetch L3 tasks when component is reselected (fixes Task 3)
        selectionStore.l3ByComponent.delete(key);
        await hydrateL3For(code, compName);
      } else {
        selectedSet.delete(compName);
        // Remove L3 tasks when component is deselected
        selectionStore.l3ByComponent.delete(key);
      }
      updateSummaryCounts();
    });
  });
}

// Render empty state for components
function renderComponentsEmptyState(message = 'Select a deliverable to view components') {
  const listEl = document.getElementById('s2-comp-list');
  if (listEl) {
    listEl.innerHTML = `<p style="color:var(--muted);text-align:center;padding:40px 8px;">${message}</p>`;
  }
}

// Update summary counts and render chips with remove buttons
function updateSummaryCounts() {
  const delivCount = APB.step2.selectedCodes.size;
  
  // Count components
  let compCount = 0;
  Object.entries(APB.step2.selectedComponentsByCode).forEach(([code, compSet]) => {
    if (APB.step2.selectedCodes.has(code)) {
      compCount += compSet.size;
    }
  });
  
  // Count L3 - only for selected components (fixes Task 4)
  let l3Count = 0;
  Object.entries(APB.step2.selectedL3ByKey).forEach(([key, l3Set]) => {
    const [code, compName] = key.split('::');
    // Only count if deliverable is selected AND component is selected
    if (APB.step2.selectedCodes.has(code)) {
      const compSet = APB.step2.selectedComponentsByCode[code];
      if (compSet && compSet.has(compName)) {
        l3Count += l3Set.size;
      }
    }
  });
  
  // Update DOM with counts
  const delivEl = document.getElementById('s2-summary-deliverables');
  const compEl = document.getElementById('s2-summary-components');
  const l3El = document.getElementById('s2-summary-l3');
  
  if (delivEl) delivEl.textContent = delivCount;
  if (compEl) compEl.textContent = compCount;
  if (l3El) l3El.textContent = l3Count;
  
  // Render detailed chips below counts
  renderSummaryChips();
  
  // Enable/disable Proceed to Pricing button
  const proceedBtn = document.querySelector('#btnProceedPricing, [data-proceed-pricing]');
  if (proceedBtn) {
    proceedBtn.disabled = delivCount === 0;
  }
}

// Render summary chips with hierarchical L3 display: Deliverable → Component → L3
function renderSummaryChips() {
  const container = document.getElementById('s2-summary-status');
  if (!container) return;
  
  let html = '';
  
  // Group by Deliverable → Component → L3
  APB.step2.selectedCodes.forEach(delivCode => {
    const deliv = APB.step2.allDeliverables.find(d => String(d.Deliverable_Code) === delivCode);
    const delivName = deliv ? (deliv.Deliverable || delivCode) : delivCode;
    
    // Start deliverable group
    html += `<div style="margin-bottom:16px;padding:8px;border-left:3px solid rgba(139,92,246,0.5);background:rgba(139,92,246,0.05);">`;
    
    // Deliverable header with remove button
    html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <strong style="font-size:0.9em;color:var(--accent);">${delivName}</strong>
      <button onclick="removeDeliverableFromSummary('${delivCode}')" 
              style="background:rgba(239,68,68,0.2);border:none;color:var(--danger);cursor:pointer;padding:4px 8px;border-radius:4px;font-size:0.75em;">
        Remove All
      </button>
    </div>`;
    
    // Get components for this deliverable
    const compSelection = APB.step2.selectedComponentsByCode[delivCode];
    let compSet;
    
    // Normalize component selection to Set
    if (compSelection === 'ALL') {
      // Don't show individual components for ALL sentinel
      compSet = new Set();
    } else if (compSelection instanceof Set) {
      compSet = compSelection;
    } else if (typeof compSelection === 'object' && compSelection !== null) {
      compSet = new Set(Object.keys(compSelection));
    } else {
      compSet = new Set();
    }
    
    // Render each component and its L3 items
    compSet.forEach(compName => {
      const key = `${delivCode}::${compName}`;
      const l3Set = APB.step2.selectedL3ByKey[key] || new Set();
      
      if (l3Set.size > 0) {
        // Component label with remove button
        html += `<div style="margin-top:8px;padding-left:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-size:0.8em;color:var(--muted);">${compName}</span>
            <button onclick="removeComponentFromSummary('${delivCode}', '${compName}')" 
                    style="background:none;border:none;color:var(--danger);cursor:pointer;padding:2px 6px;font-size:0.7em;">
              Remove Component
            </button>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:4px;padding-left:8px;">`;
        
        // L3 chips for this component
        l3Set.forEach(l3Name => {
          const escapedKey = key.replace(/'/g, "\\'");
          const escapedL3 = l3Name.replace(/'/g, "\\'");
          html += `<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;background:rgba(16,185,129,0.2);border-radius:12px;font-size:0.7em;">
            ${l3Name}
            <button onclick="removeL3FromSummary('${escapedKey}', '${escapedL3}')" 
                    style="background:none;border:none;color:var(--danger);cursor:pointer;padding:0;font-size:1.2em;line-height:1;">×</button>
          </span>`;
        });
        
        html += `</div></div>`;
      }
    });
    
    html += `</div>`;
  });
  
  if (html === '') {
    html = '<div style="text-align:center;color:var(--muted);font-size:0.85em;padding:20px;">No deliverables selected</div>';
  }
  
  container.innerHTML = html;
}

// Cascading Remove Handlers (Task 2)

// Remove deliverable from summary - cascades to all components and L3
window.removeDeliverableFromSummary = async function(code) {
  await deselectDeliverable(code);
  renderDeliverablesPanel();
  await refreshComponentsPanel();
  updateSummaryCounts();
  initAISummaryAndSuggestions();
}

// Remove component from summary - cascades to its L3 items
window.removeComponentFromSummary = function(delivCode, compName) {
  const key = `${delivCode}::${compName}`;
  
  // Remove L3 for this component
  if (APB.step2.selectedL3ByKey[key]) {
    delete APB.step2.selectedL3ByKey[key];
  }
  
  // Remove component from selection
  const compSet = APB.step2.selectedComponentsByCode[delivCode];
  if (compSet instanceof Set) {
    compSet.delete(compName);
    
    // If no components left, remove deliverable
    if (compSet.size === 0) {
      APB.step2.selectedCodes.delete(delivCode);
      delete APB.step2.selectedComponentsByCode[delivCode];
    }
  }
  
  // Re-render panels
  renderDeliverablesPanel();
  if (APB.step2.activeDeliverableCode === delivCode) {
    refreshComponentsPanel();
  }
  updateSummaryCounts();
}

// Remove single L3 from summary - with cleanup
window.removeL3FromSummary = function(key, l3Name) {
  const l3Set = APB.step2.selectedL3ByKey[key];
  if (!l3Set) return;
  
  // Remove the L3 item
  l3Set.delete(l3Name);
  
  const [delivCode, compName] = key.split('::');
  
  // If no L3 left for this component, remove the component
  if (l3Set.size === 0) {
    delete APB.step2.selectedL3ByKey[key];
    
    const compSet = APB.step2.selectedComponentsByCode[delivCode];
    if (compSet instanceof Set) {
      compSet.delete(compName);
      
      // If no components left, remove deliverable
      if (compSet.size === 0) {
        APB.step2.selectedCodes.delete(delivCode);
        delete APB.step2.selectedComponentsByCode[delivCode];
      }
    }
  }
  
  // Re-render panels
  renderDeliverablesPanel();
  if (APB.step2.activeDeliverableCode === delivCode && APB.step2.activeComponentName === compName) {
    renderL3Panel(delivCode, compName);
  }
  updateSummaryCounts();
}

// Component clicked - load L3 panel
async function onComponentClicked(componentName) {
  const code = APB.step2.activeDeliverableCode || getActiveDeliverableCode();
  if (!code) return;
  
  APB.step2.activeComponentName = componentName;
  
  try {
    const res = await fetch(`/api/l3_for?deliverable_code=${encodeURIComponent(code)}&component_name=${encodeURIComponent(componentName)}`);
    const json = await res.json();
    
    const items = (json.items || json.l3 || []).map(item => 
      typeof item === 'string' ? item : (item.Task_Label || item.name || '')
    );
    
    renderL3Checklist(code, componentName, items);
  } catch (e) {
    console.error('Error loading L3:', e);
    const l3ListEl = document.getElementById('s2-l3-list');
    if (l3ListEl) {
      l3ListEl.innerHTML = '<p style="color:#f88;text-align:center;padding:40px 8px;">Error loading subtasks</p>';
    }
  }
}

// Render L3 checklist
function renderL3Checklist(code, componentName, items) {
  const listEl = document.getElementById('s2-l3-list');
  if (!listEl) return;
  
  if (items.length === 0) {
    listEl.innerHTML = '<p style="color:var(--muted);text-align:center;padding:40px 8px;">No L3 subtasks</p>';
    return;
  }
  
  const key = `${code}::${componentName}`;
  
  // Initialize selection
  if (!APB.step2.selectedL3ByKey[key]) {
    APB.step2.selectedL3ByKey[key] = new Set(items);
  }
  
  const selectedSet = APB.step2.selectedL3ByKey[key];
  
  listEl.innerHTML = items.map(label => `
    <label style="display:flex;gap:8px;align-items:center;padding:6px 8px;cursor:pointer;">
      <input type="checkbox" class="l3-checkbox" data-label="${label}" 
             ${selectedSet.has(label) ? 'checked' : ''} />
      <span style="font-size:0.9em;">${label}</span>
    </label>
  `).join('');
  
  // Attach handlers
  listEl.querySelectorAll('.l3-checkbox').forEach(cb => {
    cb.addEventListener('change', e => {
      const label = e.target.dataset.label;
      if (e.target.checked) {
        selectedSet.add(label);
      } else {
        selectedSet.delete(label);
      }
      updateSummaryCounts();
    });
  });
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
  
  // Create input fields for each retainer using defensive labelFor() lookup
  retainerListControls.innerHTML = retainers.map(r => {
    const delivName = labelFor(r.deliverable_code);
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
// Legacy functions (still used in some templates - bridge to centralized state)
function onRemove(code) {
  selectedCodes = selectedCodes.filter(c => c !== code);
  if (!removedCodes.includes(code)) {
    removedCodes = [...removedCodes, code];
  }
  // Sync to centralized state and re-render
  APB.step2.selectedCodes.delete(code);
  delete APB.step2.selectedComponentsByCode[code];
  if (APB.step2.activeDeliverableCode === code) {
    APB.step2.activeDeliverableCode = null;
  }
  renderDeliverablesPanel();
  refreshComponentsPanel();
  updateSummaryCounts();
  initAISummaryAndSuggestions();
}

function onRestore(code) {
  removedCodes = removedCodes.filter(c => c !== code);
  if (!selectedCodes.includes(code)) {
    selectedCodes = [...selectedCodes, code];
  }
  // Sync to centralized state and re-render
  APB.step2.selectedCodes.add(code);
  APB.step2.activeDeliverableCode = code;
  renderDeliverablesPanel();
  refreshComponentsPanel();
  updateSummaryCounts();
  initAISummaryAndSuggestions();
}

function onAdd(code) {
  removedCodes = removedCodes.filter(c => c !== code); // un-soft-delete if needed
  if (!selectedCodes.includes(code)) {
    selectedCodes = [...selectedCodes, code];
  }
  if (!addedCodes.includes(code)) {
    addedCodes = [...addedCodes, code];
  }
  // Sync to centralized state and re-render
  APB.step2.selectedCodes.add(code);
  APB.step2.activeDeliverableCode = code;
  renderDeliverablesPanel();
  refreshComponentsPanel();
  updateSummaryCounts();
  initAISummaryAndSuggestions();
}

function selectedDeliverables(){
  // Updated to use new state model
  return selectedCodes;
}

// Open components bubble dialog for a deliverable
async function openComponentsBubble(deliv) {
  const dlg = document.getElementById('componentsDialog');
  if (!dlg) return;
  
  document.getElementById('compTitle').textContent = `Components – ${deliv.deliverable}`;
  const box = document.getElementById('componentsContainer');
  box.innerHTML = 'Loading…';
  
  try {
    const r = await fetch(`/api/components_for?deliverable_code=${encodeURIComponent(deliv.code)}`);
    const data = await r.json();
    const comps = data.items || [];
    
    if (comps.length === 0) {
      box.innerHTML = '<p style="color: var(--muted);">No components available.</p>';
      dlg.showModal();
      return;
    }
    
    box.innerHTML = comps.map(c =>
      `<label style="display: block; margin: 8px 0; cursor: pointer;">
        <input class="compChk" type="checkbox" data-name="${c.name}" checked>
        ${c.name} <small style="color: var(--muted);">(${Math.round(c.hours)} h)</small>
      </label>`
    ).join('');
    
    // Default: all selected, so delete key (backend includes all)
    delete S2.selectedComponentsMap[deliv.code];
    
    document.getElementById('selectAllComps').onclick = () => {
      for (const chk of box.querySelectorAll('.compChk')) chk.checked = true;
      // All selected: delete key to signal backend to include all
      delete S2.selectedComponentsMap[deliv.code];
    };
    
    document.getElementById('unselectAllComps').onclick = () => {
      for (const chk of box.querySelectorAll('.compChk')) chk.checked = false;
      // None selected: empty object
      S2.selectedComponentsMap[deliv.code] = {};
    };
    
    box.addEventListener('change', () => {
      const checked = [...box.querySelectorAll('.compChk')].filter(c => c.checked).map(c => c.dataset.name);
      if (checked.length === comps.length) {
        // All selected: delete key to signal backend to include all
        delete S2.selectedComponentsMap[deliv.code];
      } else if (checked.length === 0) {
        // None selected: empty object
        S2.selectedComponentsMap[deliv.code] = {};
      } else {
        // Partial selection: store as object with null values
        S2.selectedComponentsMap[deliv.code] = Object.fromEntries(checked.map(n => [n, null]));
      }
    });
    
    dlg.showModal();
  } catch (e) {
    console.error('Error loading components:', e);
    box.innerHTML = '<p style="color: red;">Error loading components.</p>';
    dlg.showModal();
  }
}

// Populate select element and remove duplicates
function populateSelect(selectEl, items) {
  if (!selectEl) return;
  const unique = [...new Set(items)];
  selectEl.innerHTML = '';
  unique.forEach(v => {
    const opt = document.createElement('option');
    opt.value = opt.textContent = v;
    selectEl.appendChild(opt);
  });
}

// Auto-fill project name from uploaded file
async function defaultProjectName() {
  try {
    const r = await fetch('/api/last_upload_name');
    const data = await r.json();
    const el = document.getElementById('projectName');
    if (data.project_name_default && el && !el.value) {
      el.value = data.project_name_default;
    }
  } catch (e) {
    console.error('Error fetching default project name:', e);
  }
}

// Initialize Step 2 UI when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  // Call boot to initialize everything
  boot();
  
  // Note: renderStep2UI removed - now using centralized renderDeliverablesPanel
});

// ========== NEW STEP 2 UI (4-Column Layout) ==========

// State for new Step 2 UI
const step2State = {
  currentDeliverable: null,     // Currently selected deliverable for viewing components
  currentComponent: null,        // Currently selected component for viewing L3 subtasks
  selectedL3Map: {},             // { deliverableCode: { componentName: Set([l3labels...]) } }
};
window.step2State = step2State;

// Expose functions globally
window.updateStep2Summary = updateStep2Summary;
window.renderComponentsPanel = renderComponentsPanel;
window.renderL3Panel = renderL3Panel;

// Update summary panel with current selection counts
function updateStep2Summary() {
  const delivCount = window.step2PickerState?.selected?.size || 0;
  document.getElementById('s2-summary-deliverables').textContent = delivCount;
  
  // Count total components selected across all deliverables
  let compCount = 0;
  const selectedCodes = Array.from(window.step2PickerState?.selected || []);
  selectedCodes.forEach(code => {
    const rawSel = selectedComponentsMap[code];
    if (!rawSel || rawSel === '__ALL__' || rawSel === 'ALL') {
      // All components selected
      compCount += (componentDataCache[code] || []).length;
    } else if (rawSel instanceof Set) {
      compCount += rawSel.size;
    } else if (Array.isArray(rawSel)) {
      compCount += rawSel.length;
    } else if (typeof rawSel === 'object') {
      compCount += Object.keys(rawSel).length;
    }
  });
  document.getElementById('s2-summary-components').textContent = compCount;
  
  // Count L3 subtasks
  let l3Count = 0;
  Object.values(step2State.selectedL3Map).forEach(compMap => {
    Object.values(compMap).forEach(l3Set => {
      if (l3Set instanceof Set) l3Count += l3Set.size;
      else if (Array.isArray(l3Set)) l3Count += l3Set.length;
    });
  });
  document.getElementById('s2-summary-l3').textContent = l3Count;
  
  // Update status message
  const statusEl = document.getElementById('s2-summary-status');
  if (delivCount === 0) {
    statusEl.textContent = 'No deliverables selected';
    statusEl.style.color = 'var(--muted)';
  } else {
    statusEl.textContent = `${delivCount} deliverable${delivCount > 1 ? 's' : ''} ready`;
    statusEl.style.color = 'var(--accent)';
  }
}


// Render Components panel - aggregates ALL components from ALL selected deliverables
async function renderComponentsPanel() {
  const listEl = document.getElementById('s2-comp-list');
  const btnAll = document.getElementById('s2-comp-selectall');
  const btnClear = document.getElementById('s2-comp-clear');
  
  if (!listEl) return;
  
  const selectedCodes = Array.from(selectionStore.deliverables);
  
  if (selectedCodes.length === 0) {
    listEl.innerHTML = '<p style="color: var(--muted); text-align: center; padding-top: 40px; font-size: 0.9em;">Select deliverables to view components</p>';
    if (btnAll) btnAll.disabled = true;
    if (btnClear) btnClear.disabled = true;
    return;
  }
  
  // Aggregate all components from all selected deliverables
  const allComponents = [];
  for (const delivCode of selectedCodes) {
    // Ensure components are hydrated
    if (!selectionStore.componentsByDeliv.has(delivCode)) {
      await hydrateComponentsFor(delivCode);
    }
    
    const compSet = selectionStore.componentsByDeliv.get(delivCode);
    if (compSet && compSet.size > 0) {
      compSet.forEach(compName => {
        allComponents.push({
          delivCode,
          delivLabel: labelFor(delivCode),
          compName
        });
      });
    }
  }
  
  if (allComponents.length === 0) {
    listEl.innerHTML = '<p style="color: var(--muted); text-align: center; padding-top: 40px; font-size: 0.9em;">No components available</p>';
    if (btnAll) btnAll.disabled = true;
    if (btnClear) btnClear.disabled = true;
    return;
  }
  
  // Apply search filter
  const searchFilter = (APB.step2.filters.components || '').toLowerCase();
  const filteredComponents = searchFilter 
    ? allComponents.filter(c => 
        c.compName.toLowerCase().includes(searchFilter) ||
        c.delivLabel.toLowerCase().includes(searchFilter)
      )
    : allComponents;
  
  if (btnAll) btnAll.disabled = false;
  if (btnClear) btnClear.disabled = false;
  
  // Render checkboxes with deliverable badges
  listEl.innerHTML = filteredComponents.map(comp => {
    const key = `${comp.delivCode}::${comp.compName}`;
    const isSelected = S2.selectedComponentsByCode[comp.delivCode]?.has?.(comp.compName) || false;
    const isVisible = !searchFilter || (
      comp.compName.toLowerCase().includes(searchFilter) ||
      comp.delivLabel.toLowerCase().includes(searchFilter)
    );
    
    return `
      <label style="display:flex; gap:8px; align-items:center; padding:6px 8px; cursor:pointer; border-radius:4px;" 
             class="comp-checkbox-label">
        <input type="checkbox" 
               data-deliv="${comp.delivCode}" 
               data-comp="${comp.compName}"
               data-visible="${isVisible ? '1' : '0'}"
               ${isSelected ? 'checked' : ''}
               style="cursor:pointer;"/>
        <span style="font-size:0.9em;">${comp.compName}</span>
        <span style="margin-left:auto; opacity:.6; font-size:0.75em; padding:2px 6px; background:rgba(255,255,255,.1); border-radius:3px;">${comp.delivLabel}</span>
      </label>
    `;
  }).join('');
  
  // Add change listeners
  listEl.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', e => {
      const delivCode = e.target.getAttribute('data-deliv');
      const compName = e.target.getAttribute('data-comp');
      
      // Ensure the deliverable has a Set in selectedComponentsByCode
      if (!S2.selectedComponentsByCode[delivCode]) {
        S2.selectedComponentsByCode[delivCode] = new Set();
      } else if (!(S2.selectedComponentsByCode[delivCode] instanceof Set)) {
        S2.selectedComponentsByCode[delivCode] = new Set(
          Array.isArray(S2.selectedComponentsByCode[delivCode]) 
            ? S2.selectedComponentsByCode[delivCode]
            : Object.keys(S2.selectedComponentsByCode[delivCode] || {})
        );
      }
      
      if (e.target.checked) {
        S2.selectedComponentsByCode[delivCode].add(compName);
      } else {
        S2.selectedComponentsByCode[delivCode].delete(compName);
      }
      
      if (window.updateStep2Summary) updateStep2Summary();
      if (window.renderL3Panel) renderL3Panel();
    });
  });
  
  if (window.updateStep2Summary) updateStep2Summary();
}


// Render L3 Subtasks panel - aggregates ALL L3 from ALL selected components
async function renderL3Panel() {
  const listEl = document.getElementById('s2-l3-list');
  const btnAll = document.getElementById('s2-l3-selectall');
  const btnClear = document.getElementById('s2-l3-clear');
  
  if (!listEl) return;
  
  const selectedCodes = Array.from(selectionStore.deliverables);
  
  if (selectedCodes.length === 0) {
    listEl.innerHTML = '<p style="color: var(--muted); text-align: center; padding-top: 40px; font-size: 0.9em;">Select deliverables and components to view L3 subtasks</p>';
    if (btnAll) btnAll.disabled = true;
    if (btnClear) btnClear.disabled = true;
    return;
  }
  
  // Aggregate all L3 from all selected components across all deliverables
  const allL3 = [];
  for (const delivCode of selectedCodes) {
    const selectedComponents = S2.selectedComponentsByCode[delivCode];
    
    if (selectedComponents && selectedComponents.size > 0) {
      for (const compName of selectedComponents) {
        const key = `${delivCode}::${compName}`;
        
        // Ensure L3 is hydrated for this component
        if (!selectionStore.l3ByComponent.has(key)) {
          await hydrateL3For(delivCode, compName);
        }
        
        const l3Set = selectionStore.l3ByComponent.get(key);
        if (l3Set && l3Set.size > 0) {
          l3Set.forEach(l3Name => {
            allL3.push({
              delivCode,
              delivLabel: labelFor(delivCode),
              compName,
              l3Name,
              key
            });
          });
        }
      }
    }
  }
  
  if (allL3.length === 0) {
    listEl.innerHTML = '<p style="color: var(--muted); text-align: center; padding-top: 40px; font-size: 0.9em;">No L3 subtasks available for selected components</p>';
    if (btnAll) btnAll.disabled = true;
    if (btnClear) btnClear.disabled = true;
    return;
  }
  
  // Apply search filter
  const searchFilter = (APB.step2.filters.l3 || '').toLowerCase();
  const filteredL3 = searchFilter
    ? allL3.filter(l => 
        l.l3Name.toLowerCase().includes(searchFilter) ||
        l.compName.toLowerCase().includes(searchFilter) ||
        l.delivLabel.toLowerCase().includes(searchFilter)
      )
    : allL3;
  
  if (btnAll) btnAll.disabled = false;
  if (btnClear) btnClear.disabled = false;
  
  // Render checkboxes grouped by component
  listEl.innerHTML = filteredL3.map(item => {
    const isSelected = S2.selectedL3ByKey[item.key]?.has?.(item.l3Name) || false;
    const isVisible = !searchFilter || (
      item.l3Name.toLowerCase().includes(searchFilter) ||
      item.compName.toLowerCase().includes(searchFilter) ||
      item.delivLabel.toLowerCase().includes(searchFilter)
    );
    
    return `
      <label style="display:flex; gap:8px; align-items:center; padding:6px 8px; cursor:pointer; border-radius:4px;" 
             class="l3-checkbox-label">
        <input type="checkbox" 
               data-key="${item.key}" 
               data-l3="${item.l3Name}"
               data-visible="${isVisible ? '1' : '0'}"
               ${isSelected ? 'checked' : ''}
               style="cursor:pointer;"/>
        <span style="font-size:0.9em;">${item.l3Name}</span>
        <span style="margin-left:auto; opacity:.6; font-size:0.75em; padding:2px 6px; background:rgba(255,255,255,.1); border-radius:3px;">${item.compName}</span>
      </label>
    `;
  }).join('');
  
  // Add change listeners
  listEl.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', e => {
      const key = e.target.getAttribute('data-key');
      const l3Name = e.target.getAttribute('data-l3');
      
      // Ensure the key exists in selectedL3ByKey (will use Proxy)
      if (!S2.selectedL3ByKey[key]) {
        S2.selectedL3ByKey[key] = new Set();
      } else if (!(S2.selectedL3ByKey[key] instanceof Set)) {
        S2.selectedL3ByKey[key] = new Set(
          Array.isArray(S2.selectedL3ByKey[key]) 
            ? S2.selectedL3ByKey[key]
            : Object.keys(S2.selectedL3ByKey[key] || {})
        );
      }
      
      if (e.target.checked) {
        S2.selectedL3ByKey[key].add(l3Name);
      } else {
        S2.selectedL3ByKey[key].delete(l3Name);
      }
      
      if (window.updateStep2Summary) updateStep2Summary();
    });
  });
  
  if (window.updateStep2Summary) updateStep2Summary();
}

// Wire up new Step 2 UI controls
document.addEventListener('DOMContentLoaded', function() {
  // Task 1.5: Deliverables search filter
  const delivSearch = document.getElementById('s2-deliv-search');
  if (delivSearch) {
    delivSearch.addEventListener('input', debounce(e => {
      APB.step2.filters.deliverables = e.target.value.toLowerCase();
      renderDeliverablesPanel();
    }, 200));
  }
  
  // Components panel controls
  const compSearch = document.getElementById('s2-comp-search');
  const compBtnAll = document.getElementById('s2-comp-selectall');
  const compBtnClear = document.getElementById('s2-comp-clear');
  
  // Components search filter
  if (compSearch) {
    compSearch.addEventListener('input', debounce(e => {
      APB.step2.filters.components = e.target.value.toLowerCase();
      renderComponentsPanel();
    }, 200));
  }
  
  // Components All button - select only visible checkboxes
  if (compBtnAll) {
    compBtnAll.addEventListener('click', async () => {
      const visibleBoxes = document.querySelectorAll('#s2-comp-list input[type="checkbox"][data-visible="1"]');
      visibleBoxes.forEach(cb => {
        const delivCode = cb.getAttribute('data-deliv');
        const compName = cb.getAttribute('data-comp');
        
        if (!S2.selectedComponentsByCode[delivCode]) {
          S2.selectedComponentsByCode[delivCode] = new Set();
        }
        S2.selectedComponentsByCode[delivCode].add(compName);
        cb.checked = true;
      });
      
      if (window.updateStep2Summary) updateStep2Summary();
      if (window.renderL3Panel) renderL3Panel();
    });
  }
  
  if (compBtnClear) {
    compBtnClear.addEventListener('click', () => {
      const visibleBoxes = document.querySelectorAll('#s2-comp-list input[type="checkbox"][data-visible="1"]');
      visibleBoxes.forEach(cb => {
        const delivCode = cb.getAttribute('data-deliv');
        const compName = cb.getAttribute('data-comp');
        
        if (S2.selectedComponentsByCode[delivCode]) {
          S2.selectedComponentsByCode[delivCode].delete(compName);
        }
        cb.checked = false;
      });
      
      if (window.updateStep2Summary) updateStep2Summary();
      if (window.renderL3Panel) renderL3Panel();
    });
  }
  
  // L3 panel controls
  const l3Search = document.getElementById('s2-l3-search');
  const l3BtnAll = document.getElementById('s2-l3-selectall');
  const l3BtnClear = document.getElementById('s2-l3-clear');
  
  // L3 search filter
  if (l3Search) {
    l3Search.addEventListener('input', debounce(e => {
      APB.step2.filters.l3 = e.target.value.toLowerCase();
      renderL3Panel();
    }, 200));
  }
  
  // L3 All button - select only visible checkboxes
  if (l3BtnAll) {
    l3BtnAll.addEventListener('click', async () => {
      const visibleBoxes = document.querySelectorAll('#s2-l3-list input[type="checkbox"][data-visible="1"]');
      visibleBoxes.forEach(cb => {
        const key = cb.getAttribute('data-key');
        const l3Name = cb.getAttribute('data-l3');
        
        if (!S2.selectedL3ByKey[key]) {
          S2.selectedL3ByKey[key] = new Set();
        }
        S2.selectedL3ByKey[key].add(l3Name);
        cb.checked = true;
      });
      
      if (window.updateStep2Summary) updateStep2Summary();
    });
  }
  
  if (l3BtnClear) {
    l3BtnClear.addEventListener('click', () => {
      const visibleBoxes = document.querySelectorAll('#s2-l3-list input[type="checkbox"][data-visible="1"]');
      visibleBoxes.forEach(cb => {
        const key = cb.getAttribute('data-key');
        const l3Name = cb.getAttribute('data-l3');
        
        if (S2.selectedL3ByKey[key]) {
          S2.selectedL3ByKey[key].delete(l3Name);
        }
        cb.checked = false;
      });
      
      if (window.updateStep2Summary) updateStep2Summary();
    });
  }
});

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
        // Update new UI panels
        if (window.updateStep2Summary) updateStep2Summary();
        if (window.populateComponentsDeliverableDropdown) populateComponentsDeliverableDropdown();
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
    // Update new UI panels
    if (window.updateStep2Summary) updateStep2Summary();
    if (window.populateComponentsDeliverableDropdown) populateComponentsDeliverableDropdown();
  });
  el.btnClear.addEventListener('click', () => { 
    state.selected.clear(); 
    renderList(el.search.value);
    // Sync selection immediately
    window.selectedCodes = Array.from(state.selected);
    if (window.appState) window.appState.selectedCodes = window.selectedCodes;
    // Update new UI panels
    if (window.updateStep2Summary) updateStep2Summary();
    if (window.populateComponentsDeliverableDropdown) populateComponentsDeliverableDropdown();
  });

  // 6) Public init for Step 2; call this right after Step 2 renders scenarios
  window.initStep2DeliverablePicker = async function initStep2DeliverablePicker(scenarios) {
    await ensureOptions();
    seedFromCurrentScenarios(scenarios);
    renderList('');
    // Initialize new UI panels
    if (window.updateStep2Summary) updateStep2Summary();
    if (window.populateComponentsDeliverableDropdown) populateComponentsDeliverableDropdown();
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

// Helper function to render budget pill
function renderBudgetPill(el, scenarioTotalsPrice, clientBudget) {
  const budget = Number(clientBudget || 0);
  el.innerHTML = "";
  el.className = "budget-pill";
  if (!budget || !scenarioTotalsPrice) return;

  const delta = budget - scenarioTotalsPrice;
  const pct = scenarioTotalsPrice / budget;
  const span = document.createElement("span");

  if (delta >= 0) {
    span.textContent = `Under budget by $${delta.toLocaleString()} (${(100*(1-pct)).toFixed(1)}%)`;
    el.classList.add("under");
  } else {
    span.textContent = `Over budget by $${Math.abs(delta).toLocaleString()} (${(100*(pct-1)).toFixed(1)}%)`;
    el.classList.add("over");
  }
  el.appendChild(span);
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
    
    // Check if this deliverable has been customized before
    // If not, initialize with undefined (not an empty Set) to indicate "use all defaults"
    const hasCustomSelection = selectedComponentsMap[code] && selectedComponentsMap[code] instanceof Set;
    
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
            <button onclick="closeComponentPicker()" class="btn-primary">Done</button>
          </div>
        </div>
      </div>
    `);
    
    document.body.appendChild(modal);
    
    // Populate component list with auto-apply on change
    const list = document.getElementById('component-list');
    components.forEach(comp => {
      // Default to checked if no custom selection exists, otherwise check if component is in the Set
      const isSelected = hasCustomSelection ? selectedComponentsMap[code].has(comp.name) : true;
      const item = el(`
        <label style="display: flex; align-items: center; gap: 8px; padding: 8px; border: 1px solid var(--border); margin-bottom: 4px; border-radius: 4px; cursor: pointer;">
          <input type="checkbox" data-component="${comp.name}" ${isSelected ? 'checked' : ''}>
          <div style="flex: 1;">
            <div style="font-weight: 500;">${comp.name}</div>
            <div style="font-size: 12px; color: var(--muted);">${comp.hours} hours</div>
          </div>
        </label>
      `);
      
      // Auto-apply changes when checkbox changes
      const checkbox = item.querySelector('input[type="checkbox"]');
      checkbox.addEventListener('change', (e) => {
        // Initialize Set with ALL components when user makes first change
        if (!selectedComponentsMap[code] || !(selectedComponentsMap[code] instanceof Set)) {
          selectedComponentsMap[code] = new Set(components.map(c => c.name));
        }
        
        if (e.target.checked) {
          selectedComponentsMap[code].add(comp.name);
        } else {
          selectedComponentsMap[code].delete(comp.name);
        }
        
        // IMPORTANT: Keep the empty Set in the map (don't delete the key)
        // This ensures empty Sets are sent as {} in the payload, not "__ALL__"
        
        // Also ensure S2.selectedComponentsMap is updated (should be same reference but being defensive)
        if (S2.selectedComponentsMap) {
          S2.selectedComponentsMap[code] = selectedComponentsMap[code];
        }
        
        // Optionally refresh the display to update component count
        if (window.renderYourSelection) {
          renderYourSelection();
        }
      });
      
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

// ---- Load options and render deliverables panel ----
async function s2LoadDeliverables() {
  const r = await fetch('/api/options');   // server returns deliverables + templates
  const data = await r.json();
  APB.step2.allDeliverables = data.deliverables || [];
  S2.allDeliverables = data.deliverables || [];
  
  // Build code→deliverable index for fast lookups
  DELIV_INDEX = {};
  DELIV_INDEX_LO = {};
  for (const d of (data.deliverables || [])) {
    const code = String(d.Deliverable_Code).trim();
    DELIV_INDEX[code] = d;
    DELIV_INDEX_LO[key(code)] = d;
  }
  
  // Render with centralized state
  renderDeliverablesPanel();
  updateSummaryCounts();
  
  // Wire Select All button
  const btnSelectAll = APB.step2.els.btnSelectAll;
  if (btnSelectAll) {
    btnSelectAll.onclick = () => {
      APB.step2.allDeliverables.forEach(d => {
        APB.step2.selectedCodes.add(String(d.Deliverable_Code));
      });
      renderDeliverablesPanel();
      refreshComponentsPanel();
      updateSummaryCounts();
    };
  }
  
  // Wire Clear button
  const btnClear = APB.step2.els.btnClear;
  if (btnClear) {
    btnClear.onclick = () => {
      APB.step2.selectedCodes.clear();
      APB.step2.selectedComponentsByCode = {};
      APB.step2.selectedL3ByKey = {};
      APB.step2.activeDeliverableCode = null;
      APB.step2.activeComponentName = null;
      renderDeliverablesPanel();
      renderComponentsEmptyState();
      updateSummaryCounts();
    };
  }
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
        
        // Sync with new Step 2 UI state
        if (window.step2PickerState) {
          window.step2PickerState.selected.add(code);
        }
        
        // Update new Step 2 UI - set as current and populate components
        if (window.step2State) {
          window.step2State.currentDeliverable = code;
          if (window.populateComponentsDeliverableDropdown) {
            window.populateComponentsDeliverableDropdown();
          }
          if (window.renderComponentsPanel) {
            window.renderComponentsPanel(code);
          }
          if (window.updateStep2Summary) {
            window.updateStep2Summary();
          }
        }
      } else {
        S2.selectedCodes.delete(code);
        S2.selectedMeta.delete(code);
        
        // Sync with new Step 2 UI state
        if (window.step2PickerState) {
          window.step2PickerState.selected.delete(code);
        }
        
        // Update new Step 2 UI
        if (window.step2State && window.step2State.currentDeliverable === code) {
          window.step2State.currentDeliverable = null;
          if (window.renderComponentsPanel) {
            window.renderComponentsPanel(null);
          }
        }
        
        // Always update dropdown and summary when any deliverable is removed
        if (window.populateComponentsDeliverableDropdown) {
          window.populateComponentsDeliverableDropdown();
        }
        if (window.updateStep2Summary) {
          window.updateStep2Summary();
        }
      }
      s2RenderLeft();
    });
  });
}

S2.els.search?.addEventListener('input', e => s2RenderRight(e.target.value));
S2.els.btnSelectAll?.addEventListener('click', () => {
  S2.allDeliverables.forEach(d => {
    const code = String(d.Deliverable_Code);
    S2.selectedCodes.add(code);
    S2.selectedMeta.set(code, {name: d.Deliverable, category: d.Category});
    // Sync with new Step 2 UI state
    if (window.step2PickerState) {
      window.step2PickerState.selected.add(code);
    }
  });
  s2RenderRight(S2.els.search?.value || '');
  s2RenderLeft();
  
  // Update new Step 2 UI
  if (window.populateComponentsDeliverableDropdown) {
    window.populateComponentsDeliverableDropdown();
  }
  if (window.updateStep2Summary) {
    window.updateStep2Summary();
  }
});
S2.els.btnClear?.addEventListener('click', () => {
  S2.selectedCodes.clear();
  S2.selectedMeta.clear();
  s2RenderRight(S2.els.search?.value || '');
  s2RenderLeft();
  
  // Sync with new Step 2 UI state
  if (window.step2PickerState) {
    window.step2PickerState.selected.clear();
  }
  
  // Update new Step 2 UI
  if (window.step2State) {
    window.step2State.currentDeliverable = null;
  }
  if (window.renderComponentsPanel) {
    window.renderComponentsPanel(null);
  }
  if (window.populateComponentsDeliverableDropdown) {
    window.populateComponentsDeliverableDropdown();
  }
  if (window.updateStep2Summary) {
    window.updateStep2Summary();
  }
});

// ---- Left panel ("Your Selection") with Components… buttons ----
function s2RenderLeft() {
  const host = S2.els.yourSel;
  if (!host) return;
  const rows = Array.from(S2.selectedCodes).map(code => {
    // Use helper functions for consistent lookup with defensive fallback
    const name = labelFor(code);
    const category = categoryFor(code);
    const selectedComps = S2.selectedComponentsMap[code] || new Set();
    const compCountText = selectedComps.size > 0 ? ` (${selectedComps.size})` : ' (all)';
    return `
      <div class="selection-item">
        <div class="selection-item-left">
          <div class="selection-item-name">${name}</div>
          <div class="selection-item-category">${category || ''}</div>
        </div>
        <div class="selection-item-right">
          <button class="btn-component s2-comp" data-code="${code}" data-name="${name.replace(/'/g, "\\'")}">Components...${compCountText}</button>
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
  
  // Handle different types: "__ALL__" sentinel, Set, object/dict, or undefined
  let current;
  const stored = S2.selectedComponentsMap[code];
  if (!stored || stored === "__ALL__") {
    // Default to all components selected
    current = new Set(items.map(c => c.name));
    S2.selectedComponentsMap[code] = current;
  } else if (stored instanceof Set) {
    current = stored;
  } else if (typeof stored === 'object') {
    // Convert object/dict keys to Set
    current = new Set(Object.keys(stored));
    S2.selectedComponentsMap[code] = current;
  } else {
    // Fallback: select all by default
    current = new Set(items.map(c => c.name));
    S2.selectedComponentsMap[code] = current;
  }
  
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

// Select All button handler
document.getElementById('compSelectAll')?.addEventListener('click', () => {
  const checkboxes = S2.els.compList.querySelectorAll('input[type="checkbox"]');
  const delivCode = S2.els.compDrawer.getAttribute('data-active-code');
  if (!S2.selectedComponentsMap[delivCode]) S2.selectedComponentsMap[delivCode] = new Set();
  checkboxes.forEach(chk => {
    chk.checked = true;
    S2.selectedComponentsMap[delivCode].add(chk.dataset.name);
  });
});

// Unselect All button handler
document.getElementById('compUnselectAll')?.addEventListener('click', () => {
  const checkboxes = S2.els.compList.querySelectorAll('input[type="checkbox"]');
  const delivCode = S2.els.compDrawer.getAttribute('data-active-code');
  if (!S2.selectedComponentsMap[delivCode]) S2.selectedComponentsMap[delivCode] = new Set();
  checkboxes.forEach(chk => {
    chk.checked = false;
    S2.selectedComponentsMap[delivCode].delete(chk.dataset.name);
  });
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

  // Convert component selections to proper format (handle "__ALL__" sentinel)
  const compMap = {};
  codes.forEach(code => {
    const compSet = S2.selectedComponentsMap[code];
    
    if (compSet instanceof Set && compSet.size > 0) {
      // User has selected specific components - convert Set to object
      const dict = Object.create(null);
      compSet.forEach(label => { dict[label] = null; });
      compMap[code] = dict;
    } else if (compSet && typeof compSet === 'object' && !(compSet instanceof Set)) {
      // Already in object format
      compMap[code] = compSet;
    } else {
      // No specific components selected - send "__ALL__" sentinel
      compMap[code] = "__ALL__";
    }
  });

  const payload = {
    selected_deliverable_codes: codes,
    selected_components_map: compMap,
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