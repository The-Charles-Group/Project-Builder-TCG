let OPTIONS = null;       // cached /api/options
let SCENARIOS = null;     // last built scenarios (A & B)
let DELIVERABLES = [];    // [{deliverable_code, deliverable, category}]
let DELIV_INDEX = {};     // code -> deliverable object lookup for fast rendering
let DELIV_INDEX_LO = {};  // lowercase code lookup for defensive matching

// ================================================================================
// Centralized Step 2 State - Single Source of Truth (selectionStore)
// ================================================================================
window.APB = window.APB || {};

// Enables auto-pick of components when a deliverable is selected
const AUTO_SUGGEST_ON_SELECT = true;
const USE_GPT_FOR_AUTOSUGGEST = true;

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
  },
  // API methods (will be wired after boot)
  addDeliverables: null                          // batch add deliverables (for AI suggestions)
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

// Gantt Chart Instance and Timeline State
let ganttChart = null;
let currentTimelineTasks = [];
let timelineReasoning = null;

// Pricing and Retainer State
let pricingData = {
  deliverables: new Map(),
  retainers: new Map(),
  monthlyHours: new Map(),
  currentRedistribution: null,
  currentMonthlyItem: null
};

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

// ================================================================================
// Gantt Chart and AI Timeline Functions
// ================================================================================
async function initializeGanttChart(tasks = []) {
  const container = document.querySelector('#gantt');
  if (!container || !window.Gantt) {
    console.warn('Gantt library not loaded, falling back to table view');
    showFallbackTable(tasks);
    return;
  }
  
  // Clear any existing chart
  container.innerHTML = '';
  
  if (tasks.length === 0) {
    container.innerHTML = '<div style="padding:40px;text-align:center;color:var(--muted);">No timeline data. Click "Generate AI Timeline" to create one.</div>';
    return;
  }
  
  try {
    // Initialize Frappe Gantt
    ganttChart = new Gantt(container, tasks, {
      view_mode: document.getElementById('gantt-view-mode')?.value || 'Day',
      date_format: 'YYYY-MM-DD',
      popup_trigger: 'click',
      language: 'en',
      custom_popup_html: function(task) {
        const start = new Date(task._start);
        const end = new Date(task._end);
        const duration = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
        
        return `
          <div class="gantt-popup" style="padding:12px;">
            <h5 style="margin:0 0 8px;">${task.name}</h5>
            <p style="margin:4px 0;"><strong>Department:</strong> ${task.department || 'N/A'}</p>
            <p style="margin:4px 0;"><strong>Start:</strong> ${task.start}</p>
            <p style="margin:4px 0;"><strong>End:</strong> ${task.end}</p>
            <p style="margin:4px 0;"><strong>Duration:</strong> ${duration} days</p>
            <p style="margin:4px 0;"><strong>Hours:</strong> ${task.hours || 0}</p>
            ${task.critical_path ? '<p style="margin:4px 0;color:#fbbf24;"><strong>⚡ Critical Path</strong></p>' : ''}
          </div>
        `;
      },
      on_click: function(task) {
        console.log('Task clicked:', task);
      },
      on_date_change: function(task, start, end) {
        console.log('Task date changed:', task.name, start, end);
        // Update the task in our state
        const taskIndex = currentTimelineTasks.findIndex(t => t.id === task.id);
        if (taskIndex >= 0) {
          currentTimelineTasks[taskIndex].start = start.toISOString().split('T')[0];
          currentTimelineTasks[taskIndex].end = end.toISOString().split('T')[0];
        }
        // Show save button
        const saveBtn = document.getElementById('btn-save-timeline');
        if (saveBtn) saveBtn.style.display = '';
      },
      on_progress_change: function(task, progress) {
        console.log('Task progress changed:', task.name, progress);
      },
      on_view_change: function(mode) {
        console.log('View mode changed to:', mode);
      }
    });
    
    // Apply custom classes for department colors and critical path
    setTimeout(() => {
      tasks.forEach(task => {
        const taskElement = container.querySelector(`.bar[data-id="${task.id}"]`);
        if (taskElement) {
          // Add department class
          if (task.custom_class) {
            taskElement.classList.add(task.custom_class);
          }
          // Add critical path class
          if (task.critical_path) {
            taskElement.classList.add('critical-path');
          }
        }
      });
    }, 100);
    
  } catch (error) {
    console.error('Error initializing Gantt chart:', error);
    showFallbackTable(tasks);
  }
}

function showFallbackTable(tasks) {
  // Show the fallback table
  const table = document.getElementById('tl-table');
  const tbody = document.getElementById('tl-body');
  
  if (table) table.style.display = '';
  
  if (!tbody) return;
  
  tbody.innerHTML = tasks.map(task => `
    <tr>
      <td>${task.name}</td>
      <td>${task.start}</td>
      <td>${task.end}</td>
      <td>${calculateDuration(task.start, task.end)} days</td>
    </tr>
  `).join('');
}

function calculateDuration(start, end) {
  const startDate = new Date(start);
  const endDate = new Date(end);
  return Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
}

// ================================================================================
// Pricing and Retainer Management Functions
// ================================================================================

// Hour redistribution function
async function redistributeHours(deliverableCode, newTotalHours, level) {
  try {
    const response = await fetch('/api/pricing/redistribute-hours', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        deliverable_code: deliverableCode,
        new_total_hours: newTotalHours,
        level: level // 'deliverable' or 'component'
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result = await response.json();
    showRedistributionModal(result);
  } catch (error) {
    console.error('Error redistributing hours:', error);
    alert('Error redistributing hours. Please try again.');
  }
}

// Show AI redistribution modal
function showRedistributionModal(data) {
  const modal = document.getElementById('redistribution-modal');
  const content = document.getElementById('redistribution-content');
  
  if (!modal || !content) return;
  
  pricingData.currentRedistribution = data;
  
  let html = `
    <div style="margin-bottom: 16px;">
      <h4 style="color: var(--text); margin-bottom: 8px;">AI Recommendation</h4>
      <p style="color: var(--muted); font-size: 0.9em; line-height: 1.4;">${data.reasoning || 'Based on project requirements and optimal resource allocation.'}</p>
    </div>
    <div style="background: rgba(0,0,0,0.3); border-radius: 8px; padding: 12px;">
      <h5 style="color: var(--text); margin-bottom: 12px;">Suggested Hour Distribution</h5>
  `;
  
  if (data.distribution) {
    html += '<table style="width: 100%; border-collapse: collapse;">';
    html += '<thead><tr><th style="text-align: left; padding: 8px; border-bottom: 1px solid var(--border); color: var(--muted);">Component</th>';
    html += '<th style="text-align: center; padding: 8px; border-bottom: 1px solid var(--border); color: var(--muted);">Current Hours</th>';
    html += '<th style="text-align: center; padding: 8px; border-bottom: 1px solid var(--border); color: var(--muted);">Suggested Hours</th>';
    html += '<th style="text-align: center; padding: 8px; border-bottom: 1px solid var(--border); color: var(--muted);">Change</th></tr></thead>';
    html += '<tbody>';
    
    for (const [component, hours] of Object.entries(data.distribution)) {
      const currentHours = data.currentDistribution?.[component] || 0;
      const change = hours - currentHours;
      const changeClass = change > 0 ? 'color: var(--accent2);' : change < 0 ? 'color: #dc3545;' : 'color: var(--muted);';
      const changePrefix = change > 0 ? '+' : '';
      
      html += `<tr>
        <td style="padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.1);">${component}</td>
        <td style="padding: 8px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1);">${currentHours}</td>
        <td style="padding: 8px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); font-weight: 500;">${hours}</td>
        <td style="padding: 8px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); ${changeClass}">${changePrefix}${change}</td>
      </tr>`;
    }
    
    html += '</tbody></table>';
  }
  
  html += '</div>';
  
  content.innerHTML = html;
  modal.style.display = 'block';
}

// Close redistribution modal
function closeRedistributionModal() {
  const modal = document.getElementById('redistribution-modal');
  if (modal) modal.style.display = 'none';
  pricingData.currentRedistribution = null;
}

// Apply redistribution
function applyRedistribution() {
  if (!pricingData.currentRedistribution) return;
  
  const data = pricingData.currentRedistribution;
  
  // Apply the new hour distribution to the pricing table
  if (data.distribution) {
    for (const [component, hours] of Object.entries(data.distribution)) {
      const input = document.querySelector(`input[data-component="${component}"]`);
      if (input) {
        input.value = hours;
      }
    }
  }
  
  updatePricingCalculations();
  closeRedistributionModal();
}

// Toggle retainer for a deliverable or component
function toggleRetainer(itemId, isRetainer) {
  if (isRetainer) {
    pricingData.retainers.set(itemId, true);
    showMonthlyHoursModal(itemId);
  } else {
    pricingData.retainers.delete(itemId);
    pricingData.monthlyHours.delete(itemId);
  }
  updatePricingCalculations();
}

// Show monthly hours modal
function showMonthlyHoursModal(itemId) {
  const modal = document.getElementById('monthly-hours-modal');
  const content = document.getElementById('monthly-hours-content');
  
  if (!modal || !content) return;
  
  pricingData.currentMonthlyItem = itemId;
  
  const existingHours = pricingData.monthlyHours.get(itemId) || {};
  
  content.innerHTML = createMonthlyHoursGrid(itemId, existingHours);
  modal.style.display = 'block';
}

// Close monthly hours modal
function closeMonthlyHoursModal() {
  const modal = document.getElementById('monthly-hours-modal');
  if (modal) modal.style.display = 'none';
  pricingData.currentMonthlyItem = null;
}

// Create monthly hours grid
function createMonthlyHoursGrid(itemId, existingHours = {}) {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  
  let html = `
    <div style="margin-bottom: 16px;">
      <h4 style="color: var(--text);">Monthly Hour Allocation for: ${itemId}</h4>
      <p style="color: var(--muted); font-size: 0.85em;">Configure hours for each month of the retainer period</p>
    </div>
    <div class="monthly-hours-grid" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
  `;
  
  months.forEach(month => {
    const value = existingHours[month] || 0;
    html += `
      <div class="month-input" style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 6px;">
        <label style="font-size: 0.85em; color: var(--muted); margin-bottom: 4px; display: block;">${month}</label>
        <input type="number" data-month="${month}" value="${value}" placeholder="0" 
               style="width: 100%; padding: 6px; border: 1px solid var(--border); border-radius: 4px; background: var(--card); color: var(--text);" />
      </div>
    `;
  });
  
  html += `
    </div>
    <div style="margin-top: 16px; display: flex; gap: 12px; align-items: center;">
      <button onclick="copyToAllMonths()" class="btn-secondary" style="padding: 6px 12px;">
        Copy First Month to All
      </button>
      <div style="flex: 1; text-align: center;">
        <span style="color: var(--muted);">Total Hours: </span>
        <strong id="monthly-total-hours" style="color: var(--accent); font-size: 1.1em;">0</strong>
      </div>
    </div>
  `;
  
  return html;
}

// Save monthly hours
function saveMonthlyHours() {
  if (!pricingData.currentMonthlyItem) return;
  
  const itemId = pricingData.currentMonthlyItem;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monthlyHours = {};
  
  months.forEach(month => {
    const input = document.querySelector(`input[data-month="${month}"]`);
    if (input) {
      monthlyHours[month] = parseFloat(input.value) || 0;
    }
  });
  
  pricingData.monthlyHours.set(itemId, monthlyHours);
  updatePricingCalculations();
  closeMonthlyHoursModal();
}

// Copy first month hours to all months
function copyToAllMonths() {
  const firstInput = document.querySelector('input[data-month="Jan"]');
  if (!firstInput) return;
  
  const value = firstInput.value;
  const months = ['Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  
  months.forEach(month => {
    const input = document.querySelector(`input[data-month="${month}"]`);
    if (input) input.value = value;
  });
  
  updateMonthlyTotal();
}

// Update monthly total hours display
function updateMonthlyTotal() {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  let total = 0;
  
  months.forEach(month => {
    const input = document.querySelector(`input[data-month="${month}"]`);
    if (input) {
      total += parseFloat(input.value) || 0;
    }
  });
  
  const totalEl = document.getElementById('monthly-total-hours');
  if (totalEl) totalEl.textContent = total.toFixed(1);
}

// AI suggest monthly distribution
async function aiSuggestMonthlyDistribution() {
  if (!pricingData.currentMonthlyItem) return;
  
  try {
    const response = await fetch('/api/pricing/suggest-monthly-distribution', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        item_id: pricingData.currentMonthlyItem,
        total_hours: 100, // Default or calculated from current values
        seasonality: 'balanced' // Could be 'front-loaded', 'back-loaded', 'seasonal'
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result = await response.json();
    
    // Apply suggested distribution
    if (result.distribution) {
      for (const [month, hours] of Object.entries(result.distribution)) {
        const input = document.querySelector(`input[data-month="${month}"]`);
        if (input) input.value = hours;
      }
      updateMonthlyTotal();
    }
    
  } catch (error) {
    console.error('Error getting AI suggestions:', error);
    alert('Error getting AI suggestions. Using balanced distribution.');
    
    // Fallback to balanced distribution
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const hoursPerMonth = 10; // Default hours
    
    months.forEach(month => {
      const input = document.querySelector(`input[data-month="${month}"]`);
      if (input) input.value = hoursPerMonth;
    });
    
    updateMonthlyTotal();
  }
}

// Update pricing calculations
function updatePricingCalculations() {
  updatePricingTable();
  updatePricingSummary();
}

// Update pricing table with current scenario data
function updatePricingTable() {
  const tbody = document.getElementById('pricing-tbody');
  if (!tbody || !SCENARIOS) return;
  
  const scenario = SCENARIOS.A || SCENARIOS[0];
  if (!scenario || !scenario.items) return;
  
  let html = '';
  let oneTimeTotal = 0;
  let retainerMonthlyTotal = 0;
  
  scenario.items.forEach(item => {
    const isRetainer = pricingData.retainers.has(item.deliverable_code);
    const monthlyHours = pricingData.monthlyHours.get(item.deliverable_code) || {};
    const totalMonthlyHours = Object.values(monthlyHours).reduce((sum, h) => sum + h, 0);
    
    // Main deliverable row
    html += `
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
        <td style="padding: 12px; font-weight: 500;">
          ${item.deliverable}
          ${isRetainer ? '<span class="retainer-indicator" style="background: var(--accent2); color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-left: 8px;">RETAINER</span>' : ''}
        </td>
        <td style="padding: 8px; text-align: center;">
          <input type="number" value="${item.hours}" data-deliverable="${item.deliverable_code}" 
                 style="width: 60px; padding: 4px; border: 1px solid var(--border); border-radius: 4px; background: var(--card); color: var(--text); text-align: center;" />
          <button onclick="redistributeHours('${item.deliverable_code}', this.previousElementSibling.value, 'deliverable')" 
                  class="redistribute-btn" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; margin-left: 4px;">
            🤖
          </button>
        </td>
        <td style="padding: 8px; text-align: center;">-</td>
        <td style="padding: 8px; text-align: center;">
          <input type="checkbox" ${isRetainer ? 'checked' : ''} 
                 onchange="toggleRetainer('${item.deliverable_code}', this.checked)" 
                 style="cursor: pointer;" />
        </td>
        <td style="padding: 8px; text-align: center;">
          ${isRetainer ? `<button onclick="showMonthlyHoursModal('${item.deliverable_code}')" class="btn-sm">Configure</button>` : '-'}
        </td>
        <td style="padding: 8px; text-align: right;">$${item.blended_rate || 195}</td>
        <td style="padding: 8px; text-align: right; font-weight: 500; color: var(--accent);">
          $${((isRetainer ? totalMonthlyHours : item.hours) * (item.blended_rate || 195)).toLocaleString()}
        </td>
      </tr>
    `;
    
    // Component rows (if expanded)
    if (item.components) {
      item.components.forEach(comp => {
        const compIsRetainer = pricingData.retainers.has(`${item.deliverable_code}_${comp.name}`);
        html += `
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
            <td style="padding: 8px 8px 8px 32px; color: var(--muted); font-size: 0.9em;">
              ↳ ${comp.name}
            </td>
            <td style="padding: 8px; text-align: center;">
              <input type="number" value="${comp.hours}" data-component="${comp.name}" 
                     style="width: 50px; padding: 2px; border: 1px solid var(--border); border-radius: 4px; background: var(--card); color: var(--text); text-align: center; font-size: 0.9em;" />
            </td>
            <td style="padding: 8px; text-align: center;">-</td>
            <td style="padding: 8px; text-align: center;">
              <input type="checkbox" ${compIsRetainer ? 'checked' : ''} 
                     onchange="toggleRetainer('${item.deliverable_code}_${comp.name}', this.checked)" 
                     style="cursor: pointer; transform: scale(0.9);" />
            </td>
            <td style="padding: 8px; text-align: center;">
              ${compIsRetainer ? `<button onclick="showMonthlyHoursModal('${item.deliverable_code}_${comp.name}')" class="btn-sm" style="font-size: 0.8em;">Config</button>` : '-'}
            </td>
            <td style="padding: 8px; text-align: right; font-size: 0.9em;">$${comp.rate || 195}</td>
            <td style="padding: 8px; text-align: right; font-size: 0.9em;">
              $${(comp.hours * (comp.rate || 195)).toLocaleString()}
            </td>
          </tr>
        `;
      });
    }
    
    // Calculate totals
    if (isRetainer) {
      retainerMonthlyTotal += totalMonthlyHours * (item.blended_rate || 195) / 12;
    } else {
      oneTimeTotal += item.price || (item.hours * (item.blended_rate || 195));
    }
  });
  
  tbody.innerHTML = html;
}

// Update pricing summary panels
function updatePricingSummary() {
  if (!SCENARIOS) return;
  
  const scenario = SCENARIOS.A || SCENARIOS[0];
  if (!scenario || !scenario.items) return;
  
  let oneTimeCount = 0;
  let oneTimeHours = 0;
  let oneTimeCost = 0;
  
  let retainerCount = 0;
  let retainerMonthlyHours = 0;
  let retainerMonthlyCost = 0;
  
  const retainerItemsList = [];
  
  scenario.items.forEach(item => {
    const isRetainer = pricingData.retainers.has(item.deliverable_code);
    
    if (isRetainer) {
      retainerCount++;
      const monthlyHours = pricingData.monthlyHours.get(item.deliverable_code) || {};
      const avgMonthlyHours = Object.values(monthlyHours).reduce((sum, h) => sum + h, 0) / 12;
      retainerMonthlyHours += avgMonthlyHours;
      retainerMonthlyCost += avgMonthlyHours * (item.blended_rate || 195);
      retainerItemsList.push(item.deliverable);
    } else {
      oneTimeCount++;
      oneTimeHours += item.hours || 0;
      oneTimeCost += item.price || (item.hours * (item.blended_rate || 195));
    }
  });
  
  // Update One-Time Summary
  document.getElementById('one-time-count').textContent = oneTimeCount;
  document.getElementById('one-time-hours').textContent = oneTimeHours.toFixed(1);
  document.getElementById('one-time-cost').textContent = `$${oneTimeCost.toLocaleString()}`;
  
  // Update Retainer Summary
  document.getElementById('retainer-count').textContent = retainerCount;
  document.getElementById('retainer-monthly-hours').textContent = retainerMonthlyHours.toFixed(1);
  document.getElementById('retainer-monthly-cost').textContent = `$${retainerMonthlyCost.toLocaleString()}`;
  document.getElementById('retainer-annual-cost').textContent = `$${(retainerMonthlyCost * 12).toLocaleString()}`;
  
  // Update Retainer Items List
  const retainerListEl = document.getElementById('retainer-items-list');
  if (retainerListEl) {
    if (retainerItemsList.length > 0) {
      retainerListEl.innerHTML = retainerItemsList.map(item => 
        `<div style="padding: 4px 0; color: var(--muted); font-size: 0.85em;">• ${item}</div>`
      ).join('');
    } else {
      retainerListEl.innerHTML = '<div style="color: var(--muted); font-size: 0.85em; font-style: italic;">No retainer services configured</div>';
    }
  }
  
  // Update Grand Total
  const grandTotal = oneTimeCost + (retainerMonthlyCost * 12);
  document.getElementById('grand-total-cost').textContent = `$${grandTotal.toLocaleString()}`;
  document.getElementById('grand-total-breakdown').textContent = retainerCount > 0 
    ? `One-time ($${oneTimeCost.toLocaleString()}) + 12 months retainer ($${(retainerMonthlyCost * 12).toLocaleString()})`
    : 'One-time project cost';
}

// Export pricing details
async function exportPricingDetails() {
  // Implementation for exporting pricing details to Excel/CSV
  console.log('Exporting pricing details...');
  
  // Prepare data for export
  const exportData = {
    project_name: document.getElementById('projectName')?.value || 'Project',
    one_time_deliverables: [],
    retainer_services: [],
    monthly_breakdown: []
  };
  
  // Call export endpoint
  try {
    const response = await fetch('/api/export/pricing-details', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(exportData)
    });
    
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${exportData.project_name}_pricing_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }
  } catch (error) {
    console.error('Error exporting pricing details:', error);
    alert('Error exporting pricing details. Please try again.');
  }
}

// AI Optimize All Pricing Function
async function optimizeAllPricing() {
  const btn = document.getElementById('btn-ai-optimize-pricing');
  if (!btn) return;
  
  // Show loading state
  btn.disabled = true;
  btn.textContent = 'Optimizing...';
  
  try {
    // Get current scenario data
    const scenario = SCENARIOS?.A || SCENARIOS?.[0];
    if (!scenario || !scenario.items) {
      alert('Please build a scenario first');
      return;
    }
    
    // Get client budget and project details
    const clientBudget = Number(document.getElementById('clientBudget')?.value || 0);
    const projectName = document.getElementById('projectName')?.value || '';
    const rfpText = APB.step2?.rfpText || document.getElementById('rfpText')?.value || '';
    
    // Call AI optimization endpoint
    const response = await fetch('/api/pricing/optimize-all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario_data: scenario,
        client_budget: clientBudget,
        project_name: projectName,
        rfp_context: rfpText,
        optimization_goals: ['budget_fit', 'resource_balance', 'timeline_efficiency']
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result = await response.json();
    
    // Show results in a modal or apply directly
    if (result.optimized_hours) {
      showOptimizationResults(result);
    }
    
  } catch (error) {
    console.error('Error optimizing pricing:', error);
    alert('Error optimizing pricing. Using fallback optimization.');
    
    // Fallback: Simple budget-based optimization
    optimizePricingFallback();
  } finally {
    // Reset button state
    btn.disabled = false;
    btn.textContent = 'Optimize All Pricing';
  }
}

// Show optimization results modal
function showOptimizationResults(data) {
  const modal = document.getElementById('redistribution-modal');
  const content = document.getElementById('redistribution-content');
  
  if (!modal || !content) return;
  
  let html = `
    <div style="margin-bottom: 16px;">
      <h4 style="color: var(--text); margin-bottom: 8px;">AI Pricing Optimization Complete</h4>
      <p style="color: var(--muted); font-size: 0.9em; line-height: 1.4;">${data.summary || 'Optimized for budget, resources, and timeline efficiency.'}</p>
    </div>
  `;
  
  if (data.savings) {
    html += `
      <div style="background: rgba(61, 220, 151, 0.1); border: 1px solid rgba(61, 220, 151, 0.3); border-radius: 8px; padding: 12px; margin-bottom: 16px;">
        <div style="font-size: 0.9em; color: var(--accent2);">
          <strong>Potential Savings:</strong> $${data.savings.toLocaleString()}
        </div>
        <div style="font-size: 0.85em; color: var(--muted); margin-top: 4px;">
          ${data.efficiency_gain ? `Efficiency Gain: ${data.efficiency_gain}%` : ''}
        </div>
      </div>
    `;
  }
  
  if (data.recommendations) {
    html += '<div style="margin-top: 16px;"><h5 style="color: var(--text);">Recommendations:</h5><ul style="padding-left: 20px;">';
    data.recommendations.forEach(rec => {
      html += `<li style="color: var(--muted); margin: 8px 0; font-size: 0.9em;">${rec}</li>`;
    });
    html += '</ul></div>';
  }
  
  content.innerHTML = html;
  modal.style.display = 'block';
}

// Fallback optimization (client-side)
function optimizePricingFallback() {
  const clientBudget = Number(document.getElementById('clientBudget')?.value || 0);
  if (!clientBudget) {
    alert('Please enter a client budget for optimization');
    return;
  }
  
  // Simple optimization: scale hours to fit budget
  const scenario = SCENARIOS?.A || SCENARIOS?.[0];
  if (scenario && scenario.totals) {
    const currentTotal = scenario.totals.price;
    const scaleFactor = clientBudget / currentTotal;
    
    if (scaleFactor < 1) {
      // Need to reduce hours
      const reduction = ((1 - scaleFactor) * 100).toFixed(1);
      alert(`Recommendation: Reduce all hours by ${reduction}% to fit budget`);
    } else if (scaleFactor > 1.2) {
      // Have room to add more
      const increase = ((scaleFactor - 1) * 100).toFixed(1);
      alert(`Opportunity: Budget allows for ${increase}% more hours if needed`);
    } else {
      alert('Current pricing is well-aligned with budget');
    }
  }
}

// Export pricing functions to global scope
window.redistributeHours = redistributeHours;
window.showRedistributionModal = showRedistributionModal;
window.closeRedistributionModal = closeRedistributionModal;
window.applyRedistribution = applyRedistribution;
window.toggleRetainer = toggleRetainer;
window.showMonthlyHoursModal = showMonthlyHoursModal;
window.closeMonthlyHoursModal = closeMonthlyHoursModal;
window.createMonthlyHoursGrid = createMonthlyHoursGrid;
window.saveMonthlyHours = saveMonthlyHours;
window.copyToAllMonths = copyToAllMonths;
window.updateMonthlyTotal = updateMonthlyTotal;
window.aiSuggestMonthlyDistribution = aiSuggestMonthlyDistribution;
window.updatePricingCalculations = updatePricingCalculations;
window.updatePricingTable = updatePricingTable;
window.updatePricingSummary = updatePricingSummary;
window.exportPricingDetails = exportPricingDetails;
window.optimizeAllPricing = optimizeAllPricing;
window.showOptimizationResults = showOptimizationResults;
window.optimizePricingFallback = optimizePricingFallback;

async function generateAITimeline() {
  const btn = document.getElementById('btn-generate-timeline');
  const loading = document.getElementById('timeline-loading');
  const container = document.getElementById('gantt-container');
  
  if (!btn || !loading || !container) return;
  
  // Get selected deliverables from Step 2
  const selectedCodes = readSelectedCodesFromUI();
  if (selectedCodes.length === 0) {
    alert('Please select deliverables in Step 2 first');
    return;
  }
  
  // Show loading state
  btn.disabled = true;
  btn.textContent = 'Generating...';
  loading.style.display = 'block';
  container.style.display = 'none';
  
  try {
    // Get optimization mode
    const optimizationMode = document.getElementById('timeline-optimization')?.value || 'balanced';
    
    // Get project start date from Step 3
    const projectStart = document.getElementById('projectStart')?.value || null;
    
    // Get RFP text for context
    const rfpText = APB.step2?.rfpText || document.getElementById('rfpText')?.value || '';
    
    // Prepare retainer information
    const retainerData = {};
    pricingData.retainers.forEach((value, key) => {
      retainerData[key] = {
        is_retainer: true,
        monthly_hours: pricingData.monthlyHours.get(key) || {}
      };
    });
    
    // Call AI timeline endpoint
    const response = await fetch('/api/timeline/suggest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        selected_deliverable_codes: selectedCodes,
        rfp_text: rfpText,
        project_start: projectStart,
        optimization_mode: optimizationMode,
        retainer_services: retainerData  // Include retainer information
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to generate timeline');
    }
    
    const result = await response.json();
    
    // Store the timeline data
    currentTimelineTasks = result.tasks || [];
    timelineReasoning = result.reasoning || {};
    
    // Update reasoning panel
    updateReasoningPanel(result.reasoning);
    
    // Update metadata
    updateTimelineMetadata(result.metadata);
    
    // Initialize Gantt chart with AI-generated timeline
    await initializeGanttChart(currentTimelineTasks);
    
    // Show the container
    container.style.display = '';
    
    // Show metadata
    const metadataDiv = document.getElementById('timeline-metadata');
    if (metadataDiv) metadataDiv.style.display = '';
    
  } catch (error) {
    console.error('Error generating AI timeline:', error);
    alert('Failed to generate timeline: ' + error.message);
  } finally {
    // Hide loading state
    btn.disabled = false;
    btn.textContent = '🤖 Generate AI Timeline';
    loading.style.display = 'none';
  }
}

function updateReasoningPanel(reasoning) {
  if (!reasoning) return;
  
  // Update strategy
  const strategyEl = document.getElementById('ai-strategy');
  if (strategyEl) {
    strategyEl.textContent = reasoning.overall_strategy || 'Timeline optimized for balanced delivery';
  }
  
  // Update confidence
  const confidenceBar = document.getElementById('ai-confidence-bar');
  const confidenceText = document.getElementById('ai-confidence-text');
  if (confidenceBar && confidenceText) {
    const confidence = Math.round((reasoning.confidence_score || 0.75) * 100);
    confidenceBar.style.width = confidence + '%';
    confidenceText.textContent = confidence + '%';
  }
  
  // Update critical path
  const criticalPathEl = document.getElementById('ai-critical-path');
  if (criticalPathEl) {
    criticalPathEl.textContent = reasoning.critical_path_explanation || 'All sequential tasks form the critical path';
  }
  
  // Update dependencies
  const depsEl = document.getElementById('ai-dependencies');
  if (depsEl && reasoning.dependency_rationale) {
    const deps = Object.entries(reasoning.dependency_rationale)
      .filter(([k, v]) => v)
      .map(([k, v]) => `<li style="font-size:0.85em; color:var(--muted); padding:6px 0;">• ${v}</li>`)
      .join('');
    depsEl.innerHTML = deps || '<li style="font-size:0.85em; color:var(--muted); padding:6px 0;">No specific dependencies noted</li>';
  }
  
  // Update optimization notes
  const optEl = document.getElementById('ai-optimization');
  if (optEl && reasoning.optimization_notes) {
    const notes = reasoning.optimization_notes
      .map(note => `<li style="font-size:0.85em; color:var(--muted); padding:6px 0;">• ${note}</li>`)
      .join('');
    optEl.innerHTML = notes || '<li style="font-size:0.85em; color:var(--muted); padding:6px 0;">Using standard scheduling</li>';
  }
  
  // Update parallel opportunities
  const parallelEl = document.getElementById('ai-parallel');
  if (parallelEl && reasoning.parallel_opportunities) {
    const parallel = reasoning.parallel_opportunities
      .map(opp => `<li style="font-size:0.85em; color:var(--muted); padding:6px 0;">• ${opp}</li>`)
      .join('');
    parallelEl.innerHTML = parallel || '<li style="font-size:0.85em; color:var(--muted); padding:6px 0;">No parallel work opportunities identified</li>';
  }
  
  // Update risks
  const risksEl = document.getElementById('ai-risks');
  if (risksEl && reasoning.risk_factors) {
    const risks = reasoning.risk_factors
      .map(risk => `<li style="font-size:0.85em; color:var(--muted); padding:6px 0;">⚠️ ${risk}</li>`)
      .join('');
    risksEl.innerHTML = risks || '<li style="font-size:0.85em; color:var(--muted); padding:6px 0;">No significant risks identified</li>';
  }
}

function updateTimelineMetadata(metadata) {
  if (!metadata) return;
  
  const elements = {
    'meta-duration': metadata.total_duration_days ? `${metadata.total_duration_days} days` : '-',
    'meta-tasks': metadata.total_tasks || '-',
    'meta-critical': metadata.critical_tasks || '-',
    'meta-departments': metadata.departments_involved ? metadata.departments_involved.join(', ') : '-'
  };
  
  for (const [id, value] of Object.entries(elements)) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }
}

// Initialize Gantt event handlers when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Generate AI Timeline button
  const btnGenerate = document.getElementById('btn-generate-timeline');
  if (btnGenerate) {
    btnGenerate.addEventListener('click', generateAITimeline);
  }
  
  // Toggle AI Reasoning Panel
  const btnToggleReasoning = document.getElementById('btn-toggle-reasoning');
  if (btnToggleReasoning) {
    btnToggleReasoning.addEventListener('click', () => {
      const panel = document.getElementById('ai-reasoning-panel');
      if (panel) {
        panel.style.display = panel.style.display === 'none' ? '' : 'none';
      }
    });
  }
  
  // View mode change
  const viewModeSelect = document.getElementById('gantt-view-mode');
  if (viewModeSelect) {
    viewModeSelect.addEventListener('change', (e) => {
      if (ganttChart) {
        ganttChart.change_view_mode(e.target.value);
      }
    });
  }
  
  // Save timeline changes
  const btnSave = document.getElementById('btn-save-timeline');
  if (btnSave) {
    btnSave.addEventListener('click', async () => {
      // TODO: Implement save functionality to persist timeline changes
      console.log('Saving timeline changes:', currentTimelineTasks);
      alert('Timeline changes saved (in browser state)');
      btnSave.style.display = 'none';
    });
  }
});

// Export timeline data for use in exports
window.getTimelineData = function() {
  return {
    tasks: currentTimelineTasks,
    reasoning: timelineReasoning
  };
};

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
  
  // Update AI checkbox if present (bi-directional sync)
  const aiCheckbox = document.querySelector(`.ai-deliv-checkbox[data-code="${code}"]`);
  if (aiCheckbox) {
    aiCheckbox.checked = true;
  }
  
  // Update AI "Add to Selection" button if present
  const aiDiv = document.querySelector(`.ai-deliverable[data-deliv-code="${code}"]`);
  if (aiDiv) {
    const btn = aiDiv.querySelector('button[onclick*="addAIDeliverableToSelection"]');
    if (btn) {
      btn.textContent = 'Added';
      btn.style.background = '#10b981';
      btn.disabled = true;
    }
  }
  
  // Re-render all panels
  if (window.renderDeliverablesPanel) renderDeliverablesPanel();
  if (window.renderComponentsPanel) renderComponentsPanel(code);
  if (window.renderSummary) renderSummary();
}

// Batch add multiple deliverables (used by AI suggestions)
async function addDeliverables(codes) {
  if (!codes || codes.length === 0) return;
  
  // Add all codes to selection
  for (const code of codes) {
    selectionStore.deliverables.add(code);
  }
  APB.step2.selectedCodes = selectionStore.deliverables; // sync alias
  
  // Hydrate components for all new deliverables
  for (const code of codes) {
    await hydrateComponentsFor(code);
  }
  
  // Re-render all panels once
  if (window.renderDeliverablesPanel) renderDeliverablesPanel();
  if (window.renderSummary) renderSummary();
  if (window.updateSummaryCounts) updateSummaryCounts();
}

// Wire addDeliverables to APB.step2 API
APB.step2.addDeliverables = addDeliverables;

async function deselectDeliverable(code) {
  selectionStore.deliverables.delete(code);
  selectionStore.componentsByDeliv.delete(code);
  
  // Remove all L3 entries for this deliverable
  Array.from(selectionStore.l3ByComponent.keys())
    .filter(k => k.startsWith(`${code}::`))
    .forEach(k => selectionStore.l3ByComponent.delete(k));
  
  // Also clean up S2 state for compatibility
  delete S2.selectedComponentsByCode[code];
  
  APB.step2.selectedCodes = selectionStore.deliverables; // sync alias
  
  // Update AI checkbox if present (bi-directional sync)
  const aiCheckbox = document.querySelector(`.ai-deliv-checkbox[data-code="${code}"]`);
  if (aiCheckbox) {
    aiCheckbox.checked = false;
  }
  
  // Update AI "Add to Selection" button if present
  const aiDiv = document.querySelector(`.ai-deliverable[data-deliv-code="${code}"]`);
  if (aiDiv) {
    const btn = aiDiv.querySelector('button[onclick*="addAIDeliverableToSelection"]');
    if (btn) {
      btn.textContent = 'Add to Selection';
      btn.style.background = '#3b82f6';
      btn.disabled = false;
    }
  }
  
  // Uncheck all components and tasks for this deliverable in AI suggestions
  document.querySelectorAll(`.ai-comp-checkbox[data-deliv="${code}"]`).forEach(cb => cb.checked = false);
  document.querySelectorAll(`.ai-task-checkbox[data-deliv="${code}"]`).forEach(cb => cb.checked = false);
  
  // Re-render panels
  if (window.renderDeliverablesPanel) renderDeliverablesPanel();
  if (window.renderSummary) renderSummary();
  
  // If this was an AI suggestion, show Add button again
  if (APB.step2.aiSuggestedCodes.has(code)) {
    APB.step2.aiSuggestedCodes.delete(code);
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
  // Scenario templates (Scenario B/C removed - only populate A if it exists)
  const sA = document.querySelector("#scenarioA");
  if (sA) {
    OPTIONS.scenario_templates.forEach(s => {
      sA.append(el(`<option value="${s.Scenario_Key}">${s.Scenario_Key} (${s.Complexity}×${s.Tier})</option>`));
    });
    // Default: MED_LOW
    if(OPTIONS.scenario_templates.find(x => x.Scenario_Key==="MED_LOW")) sA.value="MED_LOW";
  }

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
    retainers: retainersPayload
  };

  const res = await fetch('/api/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  
  if (!res.ok) {
    const msg = await res.text().catch(() => '');
    alert(`Build failed (${res.status}): ${msg}`);
    return;
  }
  
  const json = await res.json();
  
  // Extract scenarios (now only contains A)
  const scenarios = json.scenarios || {};

  if (!scenarios || !scenarios.A) {
    console.warn('Build response', json);
    alert('Malformed build response: missing scenario A');
    return;
  }

  // Save to client state
  window.APP_STATE = window.APP_STATE || {};
  window.APP_STATE.scenarios = scenarios;
  window.APP_STATE.activeScenario = 'A';
  
  // Legacy aliases for backward compatibility
  window.BUILD = json;
  window.appState = window.appState || {};
  window.appState.scenarios = scenarios;
  window.latestScenarios = scenarios;
  window.SCENARIOS = scenarios;

  // Show Step 3 and scroll
  const step3 = document.querySelector("#step3");
  if (step3) {
    step3.style.display = "block";
    step3.scrollIntoView({ behavior: "smooth" });
  }

  // Render Scenario A only
  if (window.renderScenario) {
    window.renderScenario('scenarioA', scenarios.A);
  }

  // Show Step 4 (Timeline) and Step 5 (Export)
  const step4 = document.querySelector("#step4");
  const step5 = document.querySelector("#step5");
  if (step5) step5.style.display = 'block';
  if (step4 && window.showStep4) {
    window.showStep4('A');  // Show timeline for Scenario A
  }
}

// Alias for backward compatibility
const onProceedToStep3 = buildFromCurrentSelection;

// Image Progress Tracking
let currentJobId = null;
let progressInterval = null;

function showProgressUI() {
  const container = document.getElementById('image-progress-container');
  if (container) container.style.display = 'block';
}

function hideProgressUI() {
  const container = document.getElementById('image-progress-container');
  if (container) container.style.display = 'none';
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
}

function updateProgressUI(progress) {
  const bar = document.getElementById('image-progress-bar');
  const percentage = document.getElementById('image-progress-percentage');
  const status = document.getElementById('image-progress-status');
  const eta = document.getElementById('image-progress-eta');
  const errors = document.getElementById('image-progress-errors');
  
  if (bar) bar.style.width = `${progress.percentage || 0}%`;
  if (percentage) percentage.textContent = `${Math.round(progress.percentage || 0)}%`;
  
  // Update status message with two-phase support
  if (status) {
    if (progress.status === 'processing') {
      if (progress.phase === 'quick_scan') {
        let msg = `🔍 Quick scan: ${progress.processed_images} of ${progress.total_images} images`;
        if (progress.skipped_images > 0) {
          msg += ` (${progress.skipped_images} filtered)`;
        }
        status.textContent = msg;
      } else if (progress.phase === 'deep_analysis') {
        status.textContent = `🧠 Deep analysis: ${progress.processed_images} of ${progress.total_images} relevant images`;
      } else {
        status.textContent = `Processing ${progress.processed_images} of ${progress.total_images} images...`;
      }
    } else if (progress.status === 'completed') {
      if (progress.relevant_images !== undefined && progress.skipped_images !== undefined) {
        status.textContent = `✓ Complete: ${progress.relevant_images} relevant, ${progress.skipped_images} filtered`;
      } else {
        status.textContent = `✓ Complete! Analyzed ${progress.total_images} images`;
      }
    } else if (progress.status === 'failed') {
      status.textContent = `✗ Analysis failed`;
    } else if (progress.status === 'cancelled') {
      status.textContent = `✗ Analysis cancelled`;
    } else {
      status.textContent = 'Preparing...';
    }
  }
  
  // Update ETA
  if (eta && progress.eta_seconds != null && progress.eta_seconds > 0) {
    const seconds = Math.ceil(progress.eta_seconds);
    if (seconds < 60) {
      eta.textContent = `~${seconds}s remaining`;
    } else {
      const minutes = Math.ceil(seconds / 60);
      eta.textContent = `~${minutes}m remaining`;
    }
  } else {
    if (eta) eta.textContent = '';
  }
  
  // Show errors if any
  if (errors && progress.errors && progress.errors.length > 0) {
    errors.textContent = `⚠️ Errors: ${progress.errors.join(', ')}`;
    errors.style.display = 'block';
  } else {
    if (errors) errors.style.display = 'none';
  }
}

async function pollProgress(jobId) {
  if (!jobId) return;
  
  try {
    const res = await fetch(`/api/upload/progress/${jobId}`);
    if (!res.ok) {
      console.warn('Progress fetch failed:', res.status);
      hideProgressUI();
      return;
    }
    
    const progress = await res.json();
    updateProgressUI(progress);
    
    // Stop polling if complete, failed, or cancelled
    if (['completed', 'failed', 'cancelled'].includes(progress.status)) {
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      
      // Hide UI after a short delay
      setTimeout(() => {
        hideProgressUI();
        
        // If completed successfully, update RFP text cache with image results
        if (progress.status === 'completed' && progress.result_text) {
          APB.step2.rfpText = progress.result_text;
          sessionStorage.setItem('apb.rfp_text', progress.result_text);
          localStorage.setItem('apb.rfpText.v1', progress.result_text);
          console.log('[Image Analysis] Results merged into RFP text cache');
        }
      }, 2000);
    }
  } catch (error) {
    console.error('Error polling progress:', error);
    hideProgressUI();
  }
}

function startProgressPolling(jobId) {
  if (!jobId) return;
  
  currentJobId = jobId;
  showProgressUI();
  updateProgressUI({ status: 'pending', percentage: 0, processed_images: 0, total_images: 0 });
  
  // Poll every 500ms
  progressInterval = setInterval(() => pollProgress(jobId), 500);
  
  // Initial fetch
  pollProgress(jobId);
}

// AI Analysis Progress Tracking
let aiAnalysisJobId = null;
let aiAnalysisInterval = null;

function showAIProgressBar() {
  let progressBar = document.getElementById('ai-progress-bar');
  if (!progressBar) {
    // Create progress bar if it doesn't exist
    const step1 = document.getElementById('step1');
    if (step1) {
      progressBar = document.createElement('div');
      progressBar.id = 'ai-progress-bar';
      progressBar.style.cssText = 'margin: 20px 0; padding: 20px; background: #f3f4f6; border-radius: 8px; display: none;';
      progressBar.innerHTML = `
        <div style="margin-bottom: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong id="ai-progress-stage" style="color: #000000;">Initializing AI Analysis...</strong>
            <span id="ai-progress-percent" style="color: #2563eb; font-weight: bold;">0%</span>
          </div>
          <div style="background: #e5e7eb; height: 24px; border-radius: 12px; overflow: hidden;">
            <div id="ai-progress-fill" style="background: linear-gradient(90deg, #3b82f6, #2563eb); height: 100%; width: 0%; transition: width 0.3s ease;"></div>
          </div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 14px; color: #6b7280;">
          <span id="ai-progress-elapsed">Elapsed: 0s</span>
          <span id="ai-progress-eta">Estimating...</span>
        </div>
      `;
      step1.appendChild(progressBar);
    }
  }
  if (progressBar) {
    progressBar.style.display = 'block';
  }
}

function hideAIProgressBar() {
  const progressBar = document.getElementById('ai-progress-bar');
  if (progressBar) {
    progressBar.style.display = 'none';
  }
}

function updateAIProgress(status) {
  const fillEl = document.getElementById('ai-progress-fill');
  const percentEl = document.getElementById('ai-progress-percent');
  const stageEl = document.getElementById('ai-progress-stage');
  const elapsedEl = document.getElementById('ai-progress-elapsed');
  const etaEl = document.getElementById('ai-progress-eta');
  
  if (fillEl) fillEl.style.width = `${status.progress || 0}%`;
  if (percentEl) percentEl.textContent = `${status.progress || 0}%`;
  if (stageEl) stageEl.textContent = status.current_stage || 'Processing...';
  if (elapsedEl) elapsedEl.textContent = `Elapsed: ${Math.round(status.elapsed_seconds || 0)}s`;
  if (etaEl) {
    if (status.eta_seconds !== null && status.eta_seconds !== undefined) {
      etaEl.textContent = `ETA: ${Math.round(status.eta_seconds)}s`;
    } else {
      etaEl.textContent = 'Estimating...';
    }
  }
}

async function pollAIAnalysis(jobId) {
  try {
    const res = await fetch(`/api/ai/status/${jobId}`);
    if (!res.ok) return;
    
    const status = await res.json();
    updateAIProgress(status);
    
    if (status.status === 'completed' && status.result) {
      clearInterval(aiAnalysisInterval);
      hideAIProgressBar();
      
      // Handle completed analysis
      const aiPlanResponse = status.result;
      window.APP = window.APP || {};
      window.APP.aiPlan = aiPlanResponse;
      sessionStorage.setItem('apb:aiPlan', JSON.stringify(aiPlanResponse));
      
      const step2 = document.getElementById('step2');
      if (step2) {
        step2.style.display = 'block';
        step2.scrollIntoView({ behavior: 'smooth' });
      }
      
      renderAIPlan(aiPlanResponse);
      
      const btnAnalyze = document.querySelector('#btnAnalyze');
      if (btnAnalyze) {
        btnAnalyze.disabled = false;
        btnAnalyze.textContent = 'Analyze with AI';
      }
    } else if (status.status === 'failed') {
      clearInterval(aiAnalysisInterval);
      hideAIProgressBar();
      alert(`AI analysis failed: ${status.error || 'Unknown error'}`);
      
      const btnAnalyze = document.querySelector('#btnAnalyze');
      if (btnAnalyze) {
        btnAnalyze.disabled = false;
        btnAnalyze.textContent = 'Analyze with AI';
      }
    }
  } catch (error) {
    console.error('Error polling AI analysis:', error);
  }
}

// Helper function for fetch with retry logic for 502 errors
async function fetchWithRetry(url, options = {}, maxRetries = 3, baseDelay = 2000) {
  let lastError = null;
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(url, options);
      
      // If we get a 502 error, retry with exponential backoff
      if (response.status === 502) {
        if (attempt < maxRetries - 1) {
          const delay = baseDelay * Math.pow(2, attempt); // 2s, 4s, 8s
          console.log(`Got 502 error, retrying in ${delay/1000}s (attempt ${attempt + 1}/${maxRetries})`);
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }
        throw new Error(`Gateway timeout (502). The server may be processing your request. Please wait and try again.`);
      }
      
      return response;
    } catch (error) {
      lastError = error;
      
      // Network errors - retry
      if (attempt < maxRetries - 1) {
        const delay = baseDelay * Math.pow(2, attempt);
        console.log(`Network error, retrying in ${delay/1000}s:`, error);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
    }
  }
  
  throw lastError || new Error('Request failed after multiple retries');
}

// Handle Fast/Deep mode selection
function setAnalysisMode(mode) {
  const fastBtn = document.getElementById('mode-fast');
  const deepBtn = document.getElementById('mode-deep');
  const modeInput = document.getElementById('analysis-mode');
  
  // Set global variable for analysis
  window.selectedAnalysisMode = mode;
  
  if (mode === 'fast') {
    fastBtn.style.background = '#10b981';
    fastBtn.style.color = 'white';
    deepBtn.style.background = 'white';
    deepBtn.style.color = '#6366f1';
    modeInput.value = 'fast';
  } else {
    deepBtn.style.background = '#6366f1';
    deepBtn.style.color = 'white';
    fastBtn.style.background = 'white';
    fastBtn.style.color = '#10b981';
    modeInput.value = 'deep';
  }
  
  console.log('Analysis mode set to:', mode);
}

// Step 1: Analyze with AI (NEW: uses GPT-5 Pro AI planner for Summary + Suggestions in one call)
async function onRunReconcile() {
  const fileEl = document.querySelector('#rfpFile');
  const textEl = document.querySelector('#rfpText');
  let rfpText = (textEl?.value || '').trim();
  const btnAnalyze = document.querySelector('#btnAnalyze');
  const analysisMode = document.getElementById('analysis-mode')?.value || 'fast';

  // Show progress bar IMMEDIATELY when button is clicked
  showAIProgressBar();
  updateAIProgress({ progress: 0, current_stage: 'Preparing analysis...', elapsed_seconds: 0, eta_seconds: null });

  let aiPlanResponse;
  try {
    // First, extract text from file if provided
    if (fileEl?.files?.length) {
      if (btnAnalyze) {
        btnAnalyze.disabled = true;
        btnAnalyze.textContent = 'Extracting text...';
      }
      
      updateAIProgress({ progress: 5, current_stage: 'Extracting text from file...', elapsed_seconds: 0, eta_seconds: null });
      
      const form = new FormData();
      for (let i = 0; i < fileEl.files.length; i++) {
        form.append('files', fileEl.files[i]);
      }
      
      const analyzeToggle = document.querySelector('#analyzeImagesToggle');
      const analyzeImages = analyzeToggle ? analyzeToggle.checked : true;
      form.append('analyze_images', analyzeImages);
      
      const res = await fetchWithRetry('/api/summarize_by_file', { method: 'POST', body: form });
      if (!res.ok) {
        throw new Error(`Server error: ${res.status} ${res.statusText}`);
      }
      const summary = await res.json();
      
      // Update rfpText from file extraction
      rfpText = summary.summary_text || '';
      
      // Start progress polling if image processing jobs were started
      if (summary.job_ids && summary.job_ids.length > 0 && summary.processing_images) {
        startProgressPolling(summary.job_ids[0]);
      }
    }
    
    if (!rfpText) {
      hideAIProgressBar();
      alert('Please enter RFP text or upload a file first.');
      return;
    }

    // Start AI analysis as background job
    if (btnAnalyze) {
      btnAnalyze.disabled = true;
      btnAnalyze.textContent = 'Starting AI Analysis...';
    }
    
    updateAIProgress({ progress: 10, current_stage: 'Sending request to AI...', elapsed_seconds: 0, eta_seconds: null });
    
    // Map mode to tier
    const tierMap = {
      'fast': 'mini',
      'deep': 'thinking'
    };
    const tier = tierMap[analysisMode] || 'thinking';
    
    // Get selected mode (Fast or Deep) - default to Deep
    const selectedMode = window.selectedAnalysisMode || 'deep';
    
    const aiRes = await fetchWithRetry('/api/ai/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        request_text: rfpText,
        strictness: 'balanced',
        tier: tier,
        mode: selectedMode  // Add mode parameter
      })
    }, 3, 2000);
    
    if (!aiRes.ok) {
      throw new Error(`AI analysis error: ${aiRes.status} ${aiRes.statusText}`);
    }
    
    const jobInfo = await aiRes.json();
    
    // Persist RFP text for Step 2
    window.APP = window.APP || {};
    window.APP.rfpText = rfpText;
    sessionStorage.setItem('apb.rfp_text', rfpText);
    localStorage.setItem('apb.rfpText.v1', rfpText);
    APB.step2.rfpText = rfpText;
    
    // Start polling for AI analysis progress
    if (jobInfo.job_id) {
      aiAnalysisJobId = jobInfo.job_id;
      showAIProgressBar();
      updateAIProgress({ progress: 0, current_stage: 'Starting AI analysis...', elapsed_seconds: 0, eta_seconds: null });
      
      // Poll every 2 seconds
      aiAnalysisInterval = setInterval(() => pollAIAnalysis(aiAnalysisJobId), 2000);
      pollAIAnalysis(aiAnalysisJobId); // Initial fetch
      
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
      
      return; // Exit early - polling will handle completion
    }
    
  } catch (error) {
    console.error('Error analyzing RFP:', error);
    hideAIProgressBar();
    
    // Provide more user-friendly error messages
    let errorMessage = 'Error getting AI analysis: ';
    if (error.message.includes('502') || error.message.includes('Gateway timeout')) {
      errorMessage = 'The AI analysis is taking longer than expected. This usually happens with complex documents. Please try again in a moment.';
    } else if (error.message.includes('Network')) {
      errorMessage = 'Network connection issue. Please check your internet connection and try again.';
    } else {
      errorMessage += error.message;
    }
    
    alert(errorMessage);
    
    // Re-enable button only on error (not during normal operation - polling handles it)
    if (btnAnalyze) {
      btnAnalyze.disabled = false;
      btnAnalyze.textContent = 'Analyze with AI';
    }
  }
}

// Render NEW AI Plan (GPT-5 Pro: Summary + Evidence-backed Suggestions)
function renderAIPlan(aiPlan) {
  if (!aiPlan || !aiPlan.plan) {
    console.warn('No AI plan to render');
    return;
  }

  const plan = aiPlan.plan;
  const summary = plan.summary || {};
  const suggestionsByDept = plan.suggestions_by_department || {};
  
  // Render summary panel
  const summaryPanel = document.getElementById('ai-summary-panel');
  if (summaryPanel) {
    const goals = (summary.goals || []).map(g => `<li>${g}</li>`).join('');
    const channels = (summary.channels || []).join(', ') || 'Not specified';
    const markets = (summary.markets || []).join(', ') || 'Not specified';
    
    summaryPanel.innerHTML = `
      <div style="background: rgba(59, 130, 246, 0.1); padding: 16px; border-radius: 8px; margin-bottom: 16px;">
        <h3 style="margin: 0 0 12px 0; color: #2563eb;">📋 RFP Summary</h3>
        <p style="margin: 0 0 12px 0; line-height: 1.6;">${summary.summary || 'No summary available'}</p>
        
        ${goals ? `
          <div style="margin-bottom: 12px;">
            <strong>Goals:</strong>
            <ul style="margin: 4px 0 0 20px; line-height: 1.6;">${goals}</ul>
          </div>
        ` : ''}
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-top: 12px;">
          <div>
            <strong>Channels:</strong> <span style="color: #6b7280;">${channels}</span>
          </div>
          <div>
            <strong>Markets:</strong> <span style="color: #6b7280;">${markets}</span>
          </div>
          <div>
            <strong>Complexity:</strong> <span style="color: #6b7280; text-transform: capitalize;">${summary.complexity || 'medium'}</span>
          </div>
        </div>
        
        <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(0,0,0,0.1);">
          <strong>Total Planned Hours:</strong> <span style="font-size: 1.2em; color: #2563eb;">${plan.totals?.planned_hours_total || 0}</span>
        </div>
      </div>
    `;
  }
  
  // Render suggestions by department
  const suggestionsPanel = document.getElementById('ai-suggestions-panel');
  if (suggestionsPanel) {
    // Start with the main container and button section
    let html = `
    <div style="margin-top: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h3 style="margin: 0;">🤖 AI-Suggested Deliverables</h3>
        <div style="display: flex; gap: 8px;">
          <button onclick="selectAllAIDeliverables(true)" 
                  style="padding: 8px 16px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.2s;"
                  onmouseover="this.style.opacity='0.9'" 
                  onmouseout="this.style.opacity='1'">
            ✅ Select All
          </button>
          <button onclick="selectAllAIDeliverables(false)" 
                  style="padding: 8px 16px; background: #6b7280; color: white; border: none; border-radius: 6px; cursor: pointer; transition: all 0.2s;"
                  onmouseover="this.style.opacity='0.9'" 
                  onmouseout="this.style.opacity='1'">
            ❌ Deselect All
          </button>
        </div>
      </div>
      
      <!-- Smart Select by Relevancy -->
      <div id="smart-select-container" style="background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 8px; padding: 12px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px;">
          <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
            <label style="margin: 0; font-weight: 600; color: var(--accent);">🎯 Smart Select by Relevancy:</label>
            <input type="number" 
                   id="smart-select-threshold" 
                   min="0" 
                   max="100" 
                   value="60"
                   placeholder="Min relevancy %" 
                   style="width: 100px; padding: 6px 10px; background: #0b0e13; border: 1px solid var(--border); border-radius: 4px; color: var(--text);">
            <span style="color: var(--muted); font-size: 0.9em;">%</span>
          </div>
          <button onclick="applySmartSelection()" 
                  id="btn-smart-select"
                  style="padding: 8px 20px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.2s;"
                  onmouseover="this.style.opacity='0.9'" 
                  onmouseout="this.style.opacity='1'">
            🎯 Apply Smart Selection
          </button>
        </div>
        <div style="margin-top: 8px; font-size: 0.85em; color: var(--muted);">
          Automatically select deliverables, components, and tasks with confidence ≥ threshold
        </div>
      </div>
      
      <div style="background: #f0f9ff; padding: 12px; border-radius: 8px; margin-bottom: 16px; border-left: 4px solid #3b82f6;">
        <h4 style="margin: 0 0 8px 0; color: #1e40af;">📊 Project Flow & Department Sequencing</h4>
        <p style="margin: 0; font-size: 0.9em; line-height: 1.6; color: #1e3a8a;">
          <strong>From a PM perspective, here's how these departments flow together:</strong><br>
          <strong>1. Strategy</strong> → Sets foundation & direction<br>
          <strong>2. Creative</strong> → Develops visual identity & concepts<br>
          <strong>3. Content</strong> → Creates messaging & narratives<br>
          <strong>4. Paid Media</strong> → Plans distribution & reach<br>
          <strong>5. Technology</strong> → Builds digital infrastructure<br>
          <strong>6. Integrated Marketing</strong> → Orchestrates & optimizes all channels
        </p>
      </div>
    `;
    
    const deptOrder = ['Strategy', 'Creative', 'Content', 'Paid Media', 'Technology', 'Integrated Marketing Management'];
    
    for (const dept of deptOrder) {
      const deliverables = suggestionsByDept[dept] || [];
      if (deliverables.length === 0) continue;
      
      // Department colors for visual distinction
      const deptColors = {
        'Strategy': '#8b5cf6',
        'Creative': '#f59e0b', 
        'Content': '#10b981',
        'Paid Media': '#3b82f6',
        'Technology': '#6366f1',
        'Integrated Marketing Management': '#ec4899'
      };
      
      html += `
        <details class="ai-dept-group" open style="margin-bottom: 16px; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; background: linear-gradient(to right, ${deptColors[dept]}15 0%, transparent 100%);">
          <summary style="cursor: pointer; font-weight: 600; font-size: 1.1em; color: #1f2937; margin-bottom: 12px;">
            <span style="color: ${deptColors[dept]}; margin-right: 8px;">●</span>
            ${dept} <span style="color: #6b7280; font-weight: normal; font-size: 0.9em;">(${deliverables.length} deliverable${deliverables.length > 1 ? 's' : ''})</span>
          </summary>
      `;
      
      for (const deliv of deliverables) {
        const confidence = Math.round((deliv.calibrated_confidence || 0) * 100);
        const confidenceColor = confidence >= 75 ? '#10b981' : confidence >= 50 ? '#f59e0b' : '#ef4444';
        const delivCode = deliv.deliverable_code || deliv.code;
        
        html += `
          <div class="ai-deliverable" data-deliv-code="${delivCode}" data-department="${dept}" style="background: #f9fafb; padding: 12px; border-radius: 6px; margin-bottom: 12px; border-left: 3px solid ${confidenceColor};">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
              <div style="display: flex; align-items: center; gap: 8px; flex: 1;">
                <input type="checkbox" 
                       class="ai-deliv-checkbox" 
                       data-code="${delivCode}" 
                       data-title="${deliv.title}"
                       data-dept="${dept}"
                       style="cursor: pointer;">
                <div style="flex: 1;">
                  <h4 style="margin: 0; color: #111827;">
                    <span style="color: ${deptColors[dept]}; font-weight: 500; font-size: 0.85em;">[${dept}]</span>
                    ${deliv.title}
                  </h4>
                </div>
              </div>
              <div style="display: flex; gap: 8px; align-items: center;">
                <span style="font-size: 0.85em; color: ${confidenceColor}; font-weight: 600;">${confidence}% confidence</span>
                <span style="font-size: 0.85em; color: #6b7280;">${deliv.planned_hours || 0}h</span>
                <button class="btn-small" 
                        onclick="addAIDeliverableToSelection('${delivCode}', this)"
                        style="padding: 4px 12px; font-size: 0.85em; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">
                  Add to Selection
                </button>
              </div>
            </div>
            
            ${deliv.why ? `
              <p style="margin: 8px 0; font-size: 0.9em; color: #4b5563; line-height: 1.5;">${deliv.why}</p>
            ` : ''}
            
            ${deliv.risks ? `
              <div style="background: rgba(239, 68, 68, 0.1); padding: 8px; border-radius: 4px; margin: 8px 0; font-size: 0.85em; color: #991b1b;">
                <strong>⚠️ Risks:</strong> ${deliv.risks}
              </div>
            ` : ''}
            
            ${(deliv.components || []).length > 0 ? `
              <details style="margin-top: 8px;">
                <summary style="cursor: pointer; font-size: 0.9em; color: #4b5563; font-weight: 500;">
                  Components (${deliv.components.length})
                  <button onclick="event.stopPropagation(); selectAllComponents('${delivCode}', true)" 
                          style="margin-left: 8px; padding: 2px 8px; font-size: 0.8em; background: #e5e7eb; border: none; border-radius: 3px;">
                    Select All
                  </button>
                  <button onclick="event.stopPropagation(); selectAllComponents('${delivCode}', false)" 
                          style="margin-left: 4px; padding: 2px 8px; font-size: 0.8em; background: #e5e7eb; border: none; border-radius: 3px;">
                    Deselect All
                  </button>
                </summary>
                <div style="margin-top: 8px; margin-left: 16px;">
                  ${deliv.components.map((comp, idx) => `
                    <div style="margin-bottom: 8px; padding: 8px; background: white; border-radius: 4px;">
                      <div style="display: flex; align-items: start; gap: 8px;">
                        <input type="checkbox" 
                               class="ai-comp-checkbox" 
                               data-deliv="${delivCode}" 
                               data-comp="${comp.title}"
                               data-comp-id="${comp.id || comp.title}"
                               style="cursor: pointer; margin-top: 2px;">
                        <div style="flex: 1;">
                          <div style="font-weight: 500; color: #374151;">${comp.title}</div>
                          <div style="font-size: 0.85em; color: #6b7280; margin-top: 4px;">${comp.why || ''}</div>
                          <div style="font-size: 0.85em; color: #9ca3af; margin-top: 2px;">${comp.planned_hours || 0}h</div>
                        </div>
                      </div>
                      
                      ${(comp.tasks || []).length > 0 ? `
                        <details style="margin-top: 8px; margin-left: 24px;">
                          <summary style="cursor: pointer; font-size: 0.85em; color: #6b7280;">
                            ✓ AI-Selected Tasks (${comp.tasks.length})
                            <button onclick="event.stopPropagation(); selectAllTasks('${delivCode}', '${comp.title}', true)" 
                                    style="margin-left: 8px; padding: 2px 6px; font-size: 0.75em; background: #e5e7eb; border: none; border-radius: 3px;">
                              Select All
                            </button>
                            <button onclick="event.stopPropagation(); selectAllTasks('${delivCode}', '${comp.title}', false)" 
                                    style="margin-left: 4px; padding: 2px 6px; font-size: 0.75em; background: #e5e7eb; border: none; border-radius: 3px;">
                              Deselect All
                            </button>
                          </summary>
                          <div style="margin-top: 6px; margin-left: 12px;">
                            ${comp.tasks.map((task, tIdx) => `
                              <div style="margin-bottom: 4px; padding: 6px; background: rgba(16, 185, 129, 0.05); border-left: 2px solid #10b981; border-radius: 3px;">
                                <div style="display: flex; align-items: start; gap: 8px;">
                                  <input type="checkbox" 
                                         class="ai-task-checkbox" 
                                         data-deliv="${delivCode}" 
                                         data-comp="${comp.title}"
                                         data-task="${task.title}"
                                         data-task-id="${task.id || task.title}"
                                         ${task.ai_selected ? 'checked' : ''}
                                         style="cursor: pointer; margin-top: 2px;">
                                  <div style="flex: 1;">
                                    <div style="font-size: 0.85em; color: #065f46; font-weight: 500;">${task.title}</div>
                                    ${task.why ? `<div style="font-size: 0.8em; color: #6b7280; margin-top: 2px;">${task.why}</div>` : ''}
                                    <div style="font-size: 0.8em; color: #9ca3af; margin-top: 2px;">${task.planned_hours || 0}h</div>
                                  </div>
                                </div>
                              </div>
                            `).join('')}
                          </div>
                        </details>
                      ` : '<div style="font-size: 0.85em; color: #9ca3af; margin-top: 6px; font-style: italic; margin-left: 24px;">No specific tasks selected by AI</div>'}
                    </div>
                  `).join('')}
                </div>
              </details>
            ` : ''}
          </div>
        `;
      }
      
      html += '</details>';
    }
    
    // Add button to apply all selected items
    html += `
      <div style="margin-top: 20px; padding-top: 20px; border-top: 2px solid #e5e7eb; display: flex; gap: 12px;">
        <button onclick="applyAllSelectedFromAI()" 
                style="padding: 10px 24px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
          Apply Selected to Manual Selection
        </button>
        <button onclick="clearAllAISelections()" 
                style="padding: 10px 24px; background: #ef4444; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
          Clear All Selections
        </button>
      </div>
    `;
    
    html += '</div>';
    suggestionsPanel.innerHTML = html;
    
    // Store AI plan for later use
    window.lastAIPlan = plan;
  }
}

// Smart Selection Function - Select based on confidence threshold
function applySmartSelection() {
  const thresholdInput = document.getElementById('smart-select-threshold');
  if (!thresholdInput) {
    console.warn('Smart select threshold input not found');
    return;
  }
  
  const threshold = parseFloat(thresholdInput.value) || 60;
  console.log(`Applying smart selection with threshold: ${threshold}%`);
  
  // Check if AI data is available
  if (!window.lastAIPlan || !window.lastAIPlan.suggestions_by_department) {
    console.warn('No AI suggestions available. Please run AI analysis first.');
    alert('No AI suggestions available. Please run AI analysis first.');
    return;
  }
  
  // Clear all current selections first
  clearAllAISelections();
  
  let selectedDelivCount = 0;
  let selectedCompCount = 0;
  let selectedTaskCount = 0;
  
  // Iterate through AI suggestions data directly
  const suggestionsByDept = window.lastAIPlan.suggestions_by_department || {};
  
  for (const dept in suggestionsByDept) {
    const deliverables = suggestionsByDept[dept] || [];
    
    for (const deliv of deliverables) {
      // Get confidence score from the AI data (0-1 scale, convert to percentage)
      const confidence = Math.round((deliv.calibrated_confidence || deliv.confidence || 0) * 100);
      const delivCode = deliv.deliverable_code || deliv.code;
      
      console.log(`Deliverable ${delivCode}: ${confidence}% confidence vs threshold ${threshold}%`);
      
      // Get the checkbox for this deliverable
      const delivCheckbox = document.querySelector(`.ai-deliv-checkbox[data-code="${delivCode}"]`);
      if (!delivCheckbox) {
        console.warn(`Checkbox not found for deliverable ${delivCode}`);
        continue;
      }
      
      // Check if deliverable meets threshold
      if (confidence >= threshold) {
        delivCheckbox.checked = true;
        selectedDelivCount++;
        
        // For components within this deliverable
        const components = deliv.components || [];
        for (const comp of components) {
          // Components inherit deliverable confidence (since they don't have their own)
          const compCheckbox = document.querySelector(`.ai-comp-checkbox[data-deliv="${delivCode}"][data-comp="${comp.title}"]`);
          if (compCheckbox) {
            compCheckbox.checked = true;
            selectedCompCount++;
            
            // For tasks within this component
            const tasks = comp.tasks || [];
            for (const task of tasks) {
              // Check if task was AI-selected
              const taskCheckbox = document.querySelector(`.ai-task-checkbox[data-deliv="${delivCode}"][data-comp="${comp.title}"][data-task="${task.title}"]`);
              if (taskCheckbox) {
                // Only select AI-recommended tasks when deliverable meets threshold
                if (task.ai_selected) {
                  taskCheckbox.checked = true;
                  selectedTaskCount++;
                } else {
                  taskCheckbox.checked = false;
                }
              }
            }
          }
        }
      } else {
        // Uncheck this deliverable and all its components/tasks
        delivCheckbox.checked = false;
        
        // Uncheck all components for this deliverable
        const compCheckboxes = document.querySelectorAll(`.ai-comp-checkbox[data-deliv="${delivCode}"]`);
        compCheckboxes.forEach(compCheckbox => {
          compCheckbox.checked = false;
        });
        
        // Uncheck all tasks for this deliverable
        const taskCheckboxes = document.querySelectorAll(`.ai-task-checkbox[data-deliv="${delivCode}"]`);
        taskCheckboxes.forEach(taskCheckbox => {
          taskCheckbox.checked = false;
        });
      }
    }
  }
  
  // Show feedback
  const feedbackMessage = `Smart Selection Applied: ${selectedDelivCount} deliverables, ${selectedCompCount} components, ${selectedTaskCount} tasks selected (threshold: ${threshold}%)`;
  console.log(feedbackMessage);
  
  // Show visual feedback (optional - add a temporary notification)
  const smartSelectContainer = document.getElementById('smart-select-container');
  if (smartSelectContainer) {
    const existingFeedback = smartSelectContainer.querySelector('.smart-select-feedback');
    if (existingFeedback) {
      existingFeedback.remove();
    }
    
    const feedbackDiv = document.createElement('div');
    feedbackDiv.className = 'smart-select-feedback';
    feedbackDiv.style = 'margin-top: 8px; padding: 8px; background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; border-radius: 4px; color: #10b981; font-size: 0.9em;';
    feedbackDiv.textContent = feedbackMessage;
    smartSelectContainer.appendChild(feedbackDiv);
    
    // Remove feedback after 5 seconds
    setTimeout(() => {
      feedbackDiv.remove();
    }, 5000);
  }
}

// Make function available globally
window.applySmartSelection = applySmartSelection;

// Helper functions for AI selection checkboxes
function addAIDeliverableToSelection(delivCode, button) {
  // Add deliverable to selection
  if (!selectionStore.deliverables.has(delivCode)) {
    selectDeliverable(delivCode).then(() => {
      // Mark as AI-suggested for tracking
      APB.step2.aiSuggestedCodes.add(delivCode);
      
      // Update button state
      button.textContent = 'Added';
      button.style.background = '#10b981';
      button.disabled = true;
      
      // Update AI checkbox state
      const aiCheckbox = document.querySelector(`.ai-deliv-checkbox[data-code="${delivCode}"]`);
      if (aiCheckbox) {
        aiCheckbox.checked = true;
      }
      
      // Update task panel if visible
      if (window.renderTasksPanel && APB.step2.activeComponentName && APB.step2.activeDeliverableCode === delivCode) {
        renderTasksPanel();
      }
    });
  } else {
    button.textContent = 'Already Added';
    button.disabled = true;
  }
}

// Select/Deselect all AI-suggested deliverables
function selectAllAIDeliverables(select) {
  const checkboxes = document.querySelectorAll('.ai-deliv-checkbox');
  checkboxes.forEach(checkbox => {
    checkbox.checked = select;
    
    // Also trigger component checkboxes if selecting
    if (select) {
      const delivCode = checkbox.dataset.code;
      const compCheckboxes = document.querySelectorAll(`.ai-comp-checkbox[data-deliv="${delivCode}"]`);
      compCheckboxes.forEach(cb => cb.checked = true);
    }
  });
  
  // Also update component and task checkboxes
  if (!select) {
    // If deselecting all, also deselect all components and tasks
    document.querySelectorAll('.ai-comp-checkbox').forEach(cb => cb.checked = false);
    document.querySelectorAll('.ai-task-checkbox').forEach(cb => cb.checked = false);
  }
  
  // Update button visual feedback
  const selectAllBtn = event?.target;
  if (selectAllBtn) {
    selectAllBtn.style.transform = 'scale(0.95)';
    setTimeout(() => {
      selectAllBtn.style.transform = 'scale(1)';
    }, 100);
  }
  
  // Update UI to show selection state
  const count = checkboxes.length;
  if (select) {
    console.log(`Selected all ${count} AI deliverables`);
  } else {
    console.log(`Deselected all ${count} AI deliverables`);
  }
}

function selectAllComponents(delivCode, select) {
  const checkboxes = document.querySelectorAll(`.ai-comp-checkbox[data-deliv="${delivCode}"]`);
  checkboxes.forEach(cb => cb.checked = select);
}

function selectAllTasks(delivCode, compTitle, select) {
  const checkboxes = document.querySelectorAll(`.ai-task-checkbox[data-deliv="${delivCode}"][data-comp="${compTitle}"]`);
  checkboxes.forEach(cb => cb.checked = select);
}

// Clear all AI selections
function clearAllAISelections() {
  // Clear all checkboxes
  document.querySelectorAll('.ai-deliv-checkbox').forEach(cb => cb.checked = false);
  document.querySelectorAll('.ai-comp-checkbox').forEach(cb => cb.checked = false);
  document.querySelectorAll('.ai-task-checkbox').forEach(cb => cb.checked = false);
  
  console.log('Cleared all AI selections');
}

async function applyAllSelectedFromAI() {
  // Collect selected deliverables
  const delivCheckboxes = document.querySelectorAll('.ai-deliv-checkbox:checked');
  
  for (const delivCb of delivCheckboxes) {
    const delivCode = delivCb.dataset.code;
    
    // Add deliverable to selection if not already there
    if (!selectionStore.deliverables.has(delivCode)) {
      await selectDeliverable(delivCode);
    }
    
    // Mark as AI-suggested for tracking
    APB.step2.aiSuggestedCodes.add(delivCode);
    
    // Collect selected components for this deliverable
    const compCheckboxes = document.querySelectorAll(`.ai-comp-checkbox[data-deliv="${delivCode}"]:checked`);
    const selectedComps = new Set();
    
    for (const compCb of compCheckboxes) {
      const compTitle = compCb.dataset.comp;
      selectedComps.add(compTitle);
      
      // Ensure component is hydrated
      if (!selectionStore.componentsByDeliv.get(delivCode)?.has(compTitle)) {
        await hydrateComponentsFor(delivCode);
      }
      
      // Collect selected tasks for this component
      const taskCheckboxes = document.querySelectorAll(`.ai-task-checkbox[data-deliv="${delivCode}"][data-comp="${compTitle}"]:checked`);
      const selectedTasks = new Set();
      
      for (const taskCb of taskCheckboxes) {
        selectedTasks.add(taskCb.dataset.task);
      }
      
      // Store selected tasks
      if (selectedTasks.size > 0) {
        const key = `${delivCode}::${compTitle}`;
        selectionStore.l3ByComponent.set(key, selectedTasks);
      }
    }
    
    // Store selected components in both selectionStore and S2 (for compatibility)
    if (selectedComps.size > 0) {
      selectionStore.componentsByDeliv.set(delivCode, selectedComps);
      S2.selectedComponentsByCode[delivCode] = selectedComps;
    }
  }
  
  // Update all panels properly
  if (window.renderDeliverablesPanel) renderDeliverablesPanel();
  if (window.renderComponentsPanel) {
    const activeCode = APB.step2.activeDeliverableCode || Array.from(selectionStore.deliverables)[0];
    if (activeCode) {
      await refreshComponentsPanel();
    }
  }
  // Call renderTasksPanel with the active component key
  if (window.renderTasksPanel && APB.step2.activeComponentName && APB.step2.activeDeliverableCode) {
    const componentKey = `${APB.step2.activeDeliverableCode}::${APB.step2.activeComponentName}`;
    renderTasksPanel(componentKey);
  }
  
  // Update summary and counts
  updateSummaryCounts();
  if (window.renderSummary) renderSummary();
  
  // Update all "Add to Selection" buttons to show they've been added
  document.querySelectorAll('.ai-deliverable').forEach(div => {
    const code = div.dataset.delivCode;
    if (selectionStore.deliverables.has(code)) {
      const btn = div.querySelector('button[onclick*="addAIDeliverableToSelection"]');
      if (btn) {
        btn.textContent = 'Added';
        btn.style.background = '#10b981';
        btn.disabled = true;
      }
    }
  });
  
  alert('Selected items have been added to your manual selection!');
}

// Tasks Panel rendering function
async function renderTasksPanel(componentKey) {
  const taskList = document.getElementById('s2-task-list');
  if (!taskList) return;
  
  if (!componentKey && APB.step2.activeComponentName && APB.step2.activeDeliverableCode) {
    componentKey = `${APB.step2.activeDeliverableCode}::${APB.step2.activeComponentName}`;
  }
  
  if (!componentKey) {
    taskList.innerHTML = '<p style="color: var(--muted); text-align: center; padding-top: 40px; font-size: 0.9em;">Select a component to view its tasks</p>';
    document.getElementById('s2-tasks-active-component').textContent = 'Select a component';
    return;
  }
  
  // Parse component key
  const [delivCode, compName] = componentKey.split('::');
  
  // Update active component display
  document.getElementById('s2-tasks-active-component').textContent = `${compName}`;
  
  // Get available tasks for this component
  const availableTasks = selectionStore.l3ByComponent.get(componentKey) || new Set();
  const selectedTasks = selectionStore.l3ByComponent.get(componentKey) || new Set();
  
  if (availableTasks.size === 0) {
    // Fetch tasks if not loaded
    try {
      const tasks = await api(`/api/l3?deliverable=${encodeURIComponent(delivCode)}&component=${encodeURIComponent(compName)}`);
      tasks.forEach(task => availableTasks.add(task));
      selectionStore.l3ByComponent.set(componentKey, availableTasks);
    } catch (e) {
      console.error('Error fetching tasks:', e);
      taskList.innerHTML = '<p style="color: #ef4444; text-align: center; padding: 20px;">Error loading tasks</p>';
      return;
    }
  }
  
  // Render task checkboxes
  if (availableTasks.size === 0) {
    taskList.innerHTML = '<p style="color: var(--muted); text-align: center; padding: 20px;">No tasks available for this component</p>';
    return;
  }
  
  const tasksHtml = Array.from(availableTasks).map(task => {
    const isAiRecommended = window.lastAIPlan && isTaskAIRecommended(delivCode, compName, task);
    const isChecked = selectedTasks.has(task);
    const taskColor = isAiRecommended ? '#10b981' : '#6b7280';
    
    return `
      <label style="display: flex; align-items: start; gap: 8px; padding: 8px; border-radius: 4px; cursor: pointer; hover:background: rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.05);">
        <input type="checkbox" 
               class="task-checkbox" 
               data-task="${task}" 
               data-component="${componentKey}"
               ${isChecked ? 'checked' : ''}
               style="margin-top: 2px; cursor: pointer;">
        <div style="flex: 1;">
          <span style="color: ${taskColor}; font-size: 0.9em;">${task}</span>
          ${isAiRecommended ? '<span style="margin-left: 8px; font-size: 0.75em; color: #10b981; background: rgba(16,185,129,0.1); padding: 2px 6px; border-radius: 3px;">AI ✓</span>' : ''}
        </div>
      </label>
    `;
  }).join('');
  
  taskList.innerHTML = tasksHtml;
  
  // Add event listeners to checkboxes
  taskList.querySelectorAll('.task-checkbox').forEach(cb => {
    cb.addEventListener('change', (e) => {
      const task = e.target.dataset.task;
      const compKey = e.target.dataset.component;
      
      if (!selectionStore.l3ByComponent.has(compKey)) {
        selectionStore.l3ByComponent.set(compKey, new Set());
      }
      
      if (e.target.checked) {
        selectionStore.l3ByComponent.get(compKey).add(task);
      } else {
        selectionStore.l3ByComponent.get(compKey).delete(task);
      }
      
      updateTasksSummary();
    });
  });
  
  updateTasksSummary();
}

// Helper to check if a task was AI-recommended
function isTaskAIRecommended(delivCode, compName, taskName) {
  if (!window.lastAIPlan) return false;
  
  const depts = window.lastAIPlan.suggestions_by_department || {};
  for (const dept of Object.values(depts)) {
    for (const deliv of dept) {
      if (deliv.deliverable_code === delivCode) {
        for (const comp of (deliv.components || [])) {
          if (comp.title === compName) {
            return (comp.tasks || []).some(t => t.title === taskName && t.ai_selected);
          }
        }
      }
    }
  }
  return false;
}

// Update tasks summary panel
function updateTasksSummary() {
  let totalTasks = 0;
  let aiTasks = 0;
  let manualTasks = 0;
  
  // Count all selected tasks
  for (const [compKey, tasks] of selectionStore.l3ByComponent.entries()) {
    const [delivCode, compName] = compKey.split('::');
    for (const task of tasks) {
      totalTasks++;
      if (isTaskAIRecommended(delivCode, compName, task)) {
        aiTasks++;
      } else {
        manualTasks++;
      }
    }
  }
  
  // Update counts
  const summaryTasks = document.getElementById('s2-summary-tasks');
  const summaryAiTasks = document.getElementById('s2-summary-ai-tasks');
  const summaryManualTasks = document.getElementById('s2-summary-manual-tasks');
  
  if (summaryTasks) summaryTasks.textContent = totalTasks;
  if (summaryAiTasks) summaryAiTasks.textContent = aiTasks;
  if (summaryManualTasks) summaryManualTasks.textContent = manualTasks;
  
  // Update details list
  const detailsDiv = document.getElementById('s2-selected-tasks-details');
  if (detailsDiv) {
    if (totalTasks === 0) {
      detailsDiv.innerHTML = '<div style="color: var(--muted); text-align: center; padding: 20px; font-size: 0.85em;">No tasks selected yet</div>';
    } else {
      const detailsHtml = Array.from(selectionStore.l3ByComponent.entries())
        .filter(([_, tasks]) => tasks.size > 0)
        .map(([compKey, tasks]) => {
          const [delivCode, compName] = compKey.split('::');
          return `
            <div style="margin-bottom: 12px; padding: 8px; background: rgba(255,255,255,0.03); border-radius: 4px;">
              <div style="font-size: 0.85em; color: var(--accent); margin-bottom: 4px;">${compName}</div>
              <div style="margin-left: 12px; font-size: 0.8em;">
                ${Array.from(tasks).map(task => {
                  const isAI = isTaskAIRecommended(delivCode, compName, task);
                  return `<div style="color: ${isAI ? '#10b981' : '#9ca3af'};">• ${task}</div>`;
                }).join('')}
              </div>
            </div>
          `;
        }).join('');
      detailsDiv.innerHTML = detailsHtml;
    }
  }
}

// Wire up tasks panel buttons
window.addEventListener('DOMContentLoaded', () => {
  // Task panel buttons
  const taskSelectAll = document.getElementById('s2-task-selectall');
  const taskClear = document.getElementById('s2-task-clear');
  const taskAiFilter = document.getElementById('s2-task-ai-filter');
  
  if (taskSelectAll) {
    taskSelectAll.addEventListener('click', () => {
      document.querySelectorAll('.task-checkbox').forEach(cb => {
        cb.checked = true;
        cb.dispatchEvent(new Event('change'));
      });
    });
  }
  
  if (taskClear) {
    taskClear.addEventListener('click', () => {
      document.querySelectorAll('.task-checkbox').forEach(cb => {
        cb.checked = false;
        cb.dispatchEvent(new Event('change'));
      });
    });
  }
  
  if (taskAiFilter) {
    taskAiFilter.addEventListener('click', () => {
      document.querySelectorAll('.task-checkbox').forEach(cb => {
        const task = cb.dataset.task;
        const [delivCode, compName] = cb.dataset.component.split('::');
        const isAI = isTaskAIRecommended(delivCode, compName, task);
        cb.checked = isAI;
        cb.dispatchEvent(new Event('change'));
      });
    });
  }
});

// Export all AI-related functions globally for HTML access
window.addAIDeliverableToSelection = addAIDeliverableToSelection;
window.selectAllComponents = selectAllComponents;
window.selectAllTasks = selectAllTasks;
window.clearAllAISelections = clearAllAISelections;
window.applyAllSelectedFromAI = applyAllSelectedFromAI;
window.renderTasksPanel = renderTasksPanel;
window.updateTasksSummary = updateTasksSummary;

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

// Render GPT-5 AI Suggestions Panel
function renderAISuggestionsPanel(dCode, ai) {
  const host = document.getElementById("ai-suggest-panel");
  if (!host) return;

  const comps = (ai.components || []).map(c => `
    <div class="ai-chip">
      <strong>${c.name}</strong>
      ${c.why ? `<div class="muted" style="font-size:0.85em;margin-top:4px;">${c.why}</div>` : ""}
    </div>
  `).join("");

  const l3html = Object.entries(ai.l3_by_component || {}).map(([comp, tasks]) => `
    <details class="ai-group" style="margin:8px 0;">
      <summary style="cursor:pointer;font-weight:600;padding:4px 0;">${comp}</summary>
      <ul class="ai-l3" style="margin:4px 0 0 20px;list-style:disc;">
        ${tasks.map(t => `<li style="padding:2px 0;">${t.label}${t.why ? ` — <span class="muted" style="font-size:0.85em;">${t.why}</span>` : ""}</li>`).join("")}
      </ul>
    </details>
  `).join("");

  host.innerHTML = `
    <div class="panel-head row-between" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
      <h3 style="margin:0;">AI Analysis & Suggestions</h3>
      <div class="muted" style="font-size:0.85em;">Source: ${ai.source === "gpt" ? `GPT‑5 (${ai.model_used})` : "Rules"}</div>
    </div>

    ${ai.rationale_summary ? `<div class="ai-note" style="background:rgba(100,100,255,0.1);padding:12px;border-radius:6px;margin-bottom:12px;font-size:0.9em;">${ai.rationale_summary}</div>` : ""}

    <div class="ai-section" style="margin-bottom:16px;">
      <h4 style="margin:8px 0;">GPT‑5 Suggested Components</h4>
      <div class="ai-list" style="display:flex;flex-direction:column;gap:8px;margin:8px 0;">${comps || "<div class='muted'>No suggestions.</div>"}</div>
      <div class="row" style="gap:8px;margin-top:8px;display:flex;">
        <button class="btn" data-ai-act="apply-all" data-d="${dCode}">Apply All</button>
        <button class="btn-ghost" data-ai-act="replace" data-d="${dCode}">Replace Current</button>
      </div>
    </div>

    <div class="ai-section">
      <h4 style="margin:8px 0;">GPT‑5 Suggested L3 (per component)</h4>
      ${l3html || "<div class='muted'>No task suggestions.</div>"}
    </div>
  `;

  host.onclick = async (e) => {
    const btn = e.target.closest("[data-ai-act]");
    if (!btn) return;
    const act = btn.getAttribute("data-ai-act");
    const d = btn.getAttribute("data-d");
    const compsPicked = (ai.components || []).map(x => x.name);

    if (act === "replace") {
      S2.selectedComponentsByCode[d] = new Set();
      selectionStore.componentsByDeliv.set(d, new Set());
      for (const key of Array.from(selectionStore.l3ByComponent.keys())) {
        if (key.startsWith(d + "::")) {
          selectionStore.l3ByComponent.delete(key);
        }
      }
    }
    
    for (const c of compsPicked) {
      if (!S2.selectedComponentsByCode[d]) {
        S2.selectedComponentsByCode[d] = new Set();
      }
      S2.selectedComponentsByCode[d].add(c);
      await hydrateL3For(d, c);
    }
    
    if (ai.l3_by_component) {
      for (const [comp, items] of Object.entries(ai.l3_by_component)) {
        const key = `${d}::${comp}`;
        if (!selectionStore.l3ByComponent.has(key)) {
          selectionStore.l3ByComponent.set(key, new Set());
        }
        items.forEach(t => selectionStore.l3ByComponent.get(key).add(t.label));
      }
    }
    
    await refreshComponentsPanel();
    updateSummaryCounts();
  };
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
    
    const hasComponents = S2.selectedComponentsByCode[code] && S2.selectedComponentsByCode[code].size > 0;
    
    if (AUTO_SUGGEST_ON_SELECT && !hasComponents) {
      if (USE_GPT_FOR_AUTOSUGGEST) {
        try {
          // STEP 1: Get weighted rule matches as pre-filter context
          const rfpText = APB.step2.rfpText || document.getElementById('rfpText')?.value || '';
          let weightedContext = null;
          
          if (rfpText) {
            try {
              const weightsRes = await fetch('/api/step2/ai/weights', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rfp_text: rfpText })
              });
              if (weightsRes.ok) {
                weightedContext = await weightsRes.json();
              }
            } catch (err) {
              console.warn('Weighted pre-filter unavailable, proceeding without:', err);
            }
          }
          
          // STEP 2: Call GPT-5 with weighted context for smarter suggestions
          const exclude = [];
          const requestBody = {
            deliverable_code: code,
            include_l3: true,
            top_components: 6,
            top_l3_per_component: 20,
            exclude_labels: exclude
          };
          
          // Include weighted matches as context for GPT-5
          if (weightedContext && weightedContext.deliverables) {
            requestBody.weighted_context = weightedContext.deliverables
              .filter(d => d.deliverable_code === code)
              .map(d => ({
                match_percent: d.match_percent,
                top_components: (weightedContext.components && weightedContext.components[code]) || [],
                top_tasks: (weightedContext.tasks && weightedContext.tasks[code]) || []
              }))[0] || null;
          }
          
          const res = await fetch("/api/step2/ai/suggest", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify(requestBody)
          });
          const ai = await res.json();

          renderAISuggestionsPanel(code, ai);

          if (!S2.selectedComponentsByCode[code]) {
            S2.selectedComponentsByCode[code] = new Set();
          }
          
          for (const c of (ai.components || []).map(x => x.name)) {
            S2.selectedComponentsByCode[code].add(c);
            await hydrateL3For(code, c);
          }
          
          if (ai.l3_by_component) {
            for (const [comp, items] of Object.entries(ai.l3_by_component)) {
              const key = `${code}::${comp}`;
              if (!selectionStore.l3ByComponent.has(key)) {
                selectionStore.l3ByComponent.set(key, new Set());
              }
              items.forEach(t => selectionStore.l3ByComponent.get(key).add(t.label));
            }
          }
        } catch (error) {
          console.error('GPT auto-suggest error:', error);
        }
      } else {
        try {
          const response = await fetch('/api/step2/suggest/components', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ deliverable_code: code, limit: 6 })
          });
          
          const suggested = await response.json();
          
          if (suggested && suggested.length > 0) {
            if (!S2.selectedComponentsByCode[code]) {
              S2.selectedComponentsByCode[code] = new Set();
            }
            
            suggested.forEach(comp => {
              S2.selectedComponentsByCode[code].add(comp);
            });
            
            await Promise.all(suggested.map(comp => hydrateL3For(code, comp)));
          }
        } catch (error) {
          console.error('Auto-suggest components error:', error);
        }
      }
    }
  } else {
    await deselectDeliverable(code);
  }
  
  renderDeliverablesPanel();
  await refreshComponentsPanel();
  updateSummaryCounts();
  
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
        // Component label with reset and remove buttons
        html += `<div style="margin-top:8px;padding-left:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-size:0.8em;color:var(--muted);">${compName}</span>
            <div style="display:flex;gap:6px;">
              <button onclick="resetL3ForComponent('${delivCode}', '${compName}')" 
                      style="background:rgba(139,92,246,0.15);border:none;color:var(--accent);cursor:pointer;padding:2px 8px;border-radius:4px;font-size:0.7em;"
                      title="Restore all L3 subtasks for this component">
                ↻ Reset
              </button>
              <button onclick="removeComponentFromSummary('${delivCode}', '${compName}')" 
                      style="background:none;border:none;color:var(--danger);cursor:pointer;padding:2px 6px;font-size:0.7em;">
                Remove
              </button>
            </div>
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

// Reset L3 subtasks for a component - refetches all from server
window.resetL3ForComponent = async function(delivCode, compName) {
  const key = `${delivCode}::${compName}`;
  
  // Clear the cached L3 for this component
  selectionStore.l3ByComponent.delete(key);
  
  // Refetch L3 from server
  await hydrateL3For(delivCode, compName);
  
  // Update the summary display
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
  const activeKey = `${S2.activeDeliverableCode}::${S2.activeComponentName}`;
  
  listEl.innerHTML = filteredComponents.map(comp => {
    const key = `${comp.delivCode}::${comp.compName}`;
    const isSelected = S2.selectedComponentsByCode[comp.delivCode]?.has?.(comp.compName) || false;
    const isActive = key === activeKey;
    const isVisible = !searchFilter || (
      comp.compName.toLowerCase().includes(searchFilter) ||
      comp.delivLabel.toLowerCase().includes(searchFilter)
    );
    
    return `
      <label style="display:flex; gap:8px; align-items:center; padding:6px 8px; cursor:pointer; border-radius:4px; ${isActive ? 'background:rgba(139,92,246,0.2); border:1px solid var(--accent);' : ''}" 
             class="comp-checkbox-label"
             data-deliv="${comp.delivCode}" 
             data-comp="${comp.compName}">
        <input type="checkbox" 
               data-deliv="${comp.delivCode}" 
               data-comp="${comp.compName}"
               data-visible="${isVisible ? '1' : '0'}"
               ${isSelected ? 'checked' : ''}
               style="cursor:pointer;"/>
        <span style="font-size:0.9em; ${isActive ? 'color:var(--accent);' : ''}">${comp.compName}</span>
        <span style="margin-left:auto; opacity:.6; font-size:0.75em; padding:2px 6px; background:rgba(255,255,255,.1); border-radius:3px;">${comp.delivLabel}</span>
      </label>
    `;
  }).join('');
  
  // Add click listeners for component selection (sets active component)
  listEl.querySelectorAll('.comp-checkbox-label').forEach(label => {
    label.addEventListener('click', async e => {
      if (e.target.type === 'checkbox') return; // Let checkbox handle its own click
      
      const delivCode = label.getAttribute('data-deliv');
      const compName = label.getAttribute('data-comp');
      
      // Set as active component
      S2.activeDeliverableCode = delivCode;
      S2.activeComponentName = compName;
      
      // Re-render components to show active state
      renderComponentsPanel();
      
      // Update L2 tasks panel
      if (window.renderL3Panel) await renderL3Panel();
    });
  });
  
  // Add change listeners for checkboxes
  listEl.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', e => {
      e.stopPropagation(); // Don't trigger the label click
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
        
        // Also set as active component when checked
        S2.activeDeliverableCode = delivCode;
        S2.activeComponentName = compName;
        renderComponentsPanel(); // Re-render to show active state
        if (window.renderL3Panel) renderL3Panel(); // Update L2 tasks
      } else {
        S2.selectedComponentsByCode[delivCode].delete(compName);
      }
      
      if (window.updateStep2Summary) updateStep2Summary();
    });
  });
  
  if (window.updateStep2Summary) updateStep2Summary();
}


// Render L2 Tasks panel - shows tasks for the active component
async function renderL3Panel() {
  const listEl = document.getElementById('s2-l3-list');
  const btnAll = document.getElementById('s2-l3-selectall');
  const btnClear = document.getElementById('s2-l3-clear');
  
  if (!listEl) return;
  
  // Check if we have an active component selected
  const activeDeliv = S2.activeDeliverableCode;
  const activeComp = S2.activeComponentName;
  
  if (!activeDeliv || !activeComp) {
    listEl.innerHTML = '<p style="color: var(--muted); text-align: center; padding-top: 40px; font-size: 0.9em;">Select a component to view its L2 tasks</p>';
    if (btnAll) btnAll.disabled = true;
    if (btnClear) btnClear.disabled = true;
    return;
  }
  
  const key = `${activeDeliv}::${activeComp}`;
  
  // Ensure L3 is hydrated for this component
  if (!selectionStore.l3ByComponent.has(key)) {
    await hydrateL3For(activeDeliv, activeComp);
  }
  
  const l3Set = selectionStore.l3ByComponent.get(key);
  const allL3 = [];
  
  if (l3Set && l3Set.size > 0) {
    l3Set.forEach(l3Name => {
      allL3.push({
        delivCode: activeDeliv,
        delivLabel: labelFor(activeDeliv),
        compName: activeComp,
        l3Name,
        key
      });
    });
  }
  
  if (allL3.length === 0) {
    listEl.innerHTML = '<p style="color: var(--muted); text-align: center; padding-top: 40px; font-size: 0.9em;">No L2 tasks available for this component</p>';
    if (btnAll) btnAll.disabled = true;
    if (btnClear) btnClear.disabled = true;
    return;
  }
  
  // Apply search filter
  const searchFilter = (APB.step2.filters.l3 || '').toLowerCase();
  const filteredL3 = searchFilter
    ? allL3.filter(l => 
        l.l3Name.toLowerCase().includes(searchFilter)
      )
    : allL3;
  
  if (btnAll) btnAll.disabled = filteredL3.length > 0;
  if (btnClear) btnClear.disabled = filteredL3.length === 0;
  
  // Render checkboxes for L2 tasks
  listEl.innerHTML = filteredL3.map(item => {
    const isSelected = S2.selectedL3ByKey[item.key]?.has?.(item.l3Name) || false;
    const isVisible = !searchFilter || item.l3Name.toLowerCase().includes(searchFilter);
    
    return `
      <label style="display:flex; gap:8px; align-items:center; padding:6px 8px; cursor:pointer; border-radius:4px; ${isSelected ? 'background:rgba(139,92,246,0.1);' : ''}" 
             class="l3-checkbox-label">
        <input type="checkbox" 
               data-key="${item.key}" 
               data-l3="${item.l3Name}"
               data-visible="${isVisible ? '1' : '0'}"
               ${isSelected ? 'checked' : ''}
               style="cursor:pointer;"/>
        <span style="font-size:0.9em; ${isSelected ? 'color:var(--accent);' : ''}">${item.l3Name}</span>
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
        e.target.parentElement.style.background = 'rgba(139,92,246,0.1)';
      } else {
        S2.selectedL3ByKey[key].delete(l3Name);
        e.target.parentElement.style.background = '';
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
  
  // Components Suggest button - AI suggests relevant components
  const compBtnSuggest = document.getElementById('s2-comp-suggest');
  if (compBtnSuggest) {
    compBtnSuggest.addEventListener('click', async () => {
      const activeDeliv = APB.step2.activeDeliverableCode || Array.from(selectionStore.deliverables)[0];
      if (!activeDeliv) {
        alert('Please select a deliverable first');
        return;
      }
      
      try {
        compBtnSuggest.disabled = true;
        compBtnSuggest.textContent = 'Suggesting...';
        
        const response = await fetch('/api/step2/suggest/components', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ deliverable_code: activeDeliv, limit: 6 })
        });
        
        const suggested = await response.json();
        
        if (suggested && suggested.length > 0) {
          if (!S2.selectedComponentsByCode[activeDeliv]) {
            S2.selectedComponentsByCode[activeDeliv] = new Set();
          }
          
          // Add suggested components to selection
          suggested.forEach(comp => {
            S2.selectedComponentsByCode[activeDeliv].add(comp);
          });
          
          // Hydrate L3 for each suggested component
          await Promise.all(suggested.map(comp => hydrateL3For(activeDeliv, comp)));
          
          await renderComponentsPanel();
          updateSummaryCounts();
        } else {
          alert('No component suggestions available for this deliverable');
        }
      } catch (error) {
        console.error('Suggest components error:', error);
        alert('Failed to get suggestions. Please try again.');
      } finally {
        compBtnSuggest.disabled = false;
        compBtnSuggest.textContent = 'Suggest';
      }
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
    ['A'].forEach(letter => {
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

// ========== XML Export Functions ==========
async function exportXMLScenario(letter) {
  // Check if anchors should be included
  const addAnchors = document.getElementById('toggle-anchors')?.checked || false;
  
  // Build endpoint with query parameter
  const endpoint = `/api/export/xml/${letter.toLowerCase()}?add_anchors=${addAnchors}`;
  
  try {
    const response = await fetch(endpoint);
    if (!response.ok) throw new Error(`Export failed: ${response.statusText}`);
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Project_Scenario_${letter}.xml`;
    a.click();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert(`XML export failed: ${err.message}`);
  }
}

// Wire up XML export button (Scenario A only)
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-export-xml-a')?.addEventListener('click', () => exportXMLScenario('A'));
  
  // Initialize image analysis toggle from localStorage
  const analyzeToggle = document.getElementById('analyzeImagesToggle');
  if (analyzeToggle) {
    // Load saved preference (default true)
    const savedPreference = localStorage.getItem('apb.analyzeImages');
    if (savedPreference !== null) {
      analyzeToggle.checked = savedPreference === 'true';
    }
    
    // Save preference when changed
    analyzeToggle.addEventListener('change', (e) => {
      localStorage.setItem('apb.analyzeImages', e.target.checked);
      console.log('[Image Analysis] Preference saved:', e.target.checked);
    });
  }
  
  // Display selected file names when files are chosen
  const fileInput = document.getElementById('rfpFile');
  const filesList = document.getElementById('selected-files-list');
  if (fileInput && filesList) {
    fileInput.addEventListener('change', (e) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        const names = Array.from(files).map(f => f.name).join(', ');
        filesList.textContent = `Selected: ${names}`;
        filesList.style.color = 'var(--accent)';
      } else {
        filesList.textContent = '';
      }
    });
  }
});

window.addEventListener("load", boot);

// LEARN button functionality (Learning Brain integration)
(function attachLearn(){
  const btn = document.getElementById('learnBtn');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const rfpText = (window.APB?.step2?.rfpText) || "";
    const selected = Array.from(window.APB?.step2?.selectedCodes || []);
    const components = (window.APB?.selectionStore?.componentsByDeliv)
      ? Object.fromEntries(window.APB.selectionStore.componentsByDeliv) : {};
    try {
      const res = await fetch("/api/brain/learn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rfp_text: rfpText,
          selected_deliverables: selected,
          components_by_deliv: components,
          outcome: "accepted",
          notes: "learn-from-ui"
        })
      });
      const data = await res.json();
      alert("Learning event: " + (data?.message || res.status));
    } catch (e) {
      alert("Learn call failed: " + e);
    }
  });
})();