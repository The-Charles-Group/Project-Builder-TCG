// ================================================================================
// DEBUG MODE - Set to true to enable verbose logging (reduces browser CPU usage)
// ================================================================================
const DEBUG_MODE = false;  // Change to true for detailed debugging logs
const log = (...args) => DEBUG_MODE && console.log(...args);
const logGroup = (title) => DEBUG_MODE && console.group(title);
const logGroupEnd = () => DEBUG_MODE && console.groupEnd();

let OPTIONS = null;       // cached /api/options
let SCENARIOS = null;     // last built scenarios (A & B)
let DELIVERABLES = [];    // [{deliverable_code, deliverable, category}]
let DELIV_INDEX = {};     // code -> deliverable object lookup for fast rendering
let DELIV_INDEX_LO = {};  // lowercase code lookup for defensive matching

// ================================================================================
// CRITICAL: Global Error Handlers to Prevent App Freezing
// ================================================================================
window.addEventListener('error', function(event) {
  console.error('[GLOBAL ERROR]', event.message, event.filename, event.lineno, event.colno);
  console.error('[GLOBAL ERROR] Stack:', event.error?.stack);

  // Show user-friendly message
  if (!window._errorShown) {
    window._errorShown = true;
    setTimeout(() => {
      alert('An error occurred. Please check the console and try refreshing the page.');
      window._errorShown = false;
    }, 100);
  }

  // Don't prevent default - let console show the error too
  return false;
});

window.addEventListener('unhandledrejection', function(event) {
  console.error('[UNHANDLED PROMISE REJECTION]', event.reason);

  // Show user-friendly message
  if (!window._promiseErrorShown) {
    window._promiseErrorShown = true;
    setTimeout(() => {
      alert('A background operation failed. Please check the console and try again.');
      window._promiseErrorShown = false;
    }, 100);
  }
});

// ================================================================================
// Session ID Helper - Uses crypto.randomUUID() with fallback
// ================================================================================
function generateSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

window.generateSessionId = generateSessionId;

// ================================================================================
// Session ID Helper - Get current session or throw error
// ================================================================================
function getCurrentSessionId() {
  if (!window.APP_STATE?.sessionId) {
    alert('Please complete Step 2 (Apply Smart Selection) first');
    throw new Error('No active session ID - Step 2 must be completed first');
  }
  return window.APP_STATE.sessionId;
}

window.getCurrentSessionId = getCurrentSessionId;

// ================================================================================
// Session Management - Data Isolation Between RFPs
// ================================================================================
const SessionManager = {
  generateSessionId,

  getCurrentSessionId() {
    let sessionId = localStorage.getItem('apb.currentSession');
    if (!sessionId) {
      sessionId = this.generateSessionId();
      localStorage.setItem('apb.currentSession', sessionId);
    }
    return sessionId;
  },

  startNewSession() {
    const newSessionId = this.generateSessionId();

    // Clear ALL apb localStorage data from previous sessions (both 'apb.' and 'apb:' patterns)
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith('apb.') || key.startsWith('apb:')) {
        localStorage.removeItem(key);
      }
    });

    // Clear sessionStorage (all patterns)
    Object.keys(sessionStorage).forEach(key => {
      if (key.startsWith('apb.') || key.startsWith('apb:') || key === 'rfp_text') {
        sessionStorage.removeItem(key);
      }
    });

    // Clear in-memory summary to prevent persistence
    if (window.APP) {
      window.APP.summary = null;
      window.APP.rfpText = '';
    }

    // Set new session ID
    localStorage.setItem('apb.currentSession', newSessionId);

    console.log('[SESSION] Started new session:', newSessionId);
    return newSessionId;
  },

  async clearAllData() {
    const sessionId = this.getCurrentSessionId();

    console.log('[CLEAR] Starting complete data clear at', new Date().toISOString());

    // Track what we're clearing for logging
    const clearingLog = {
      localStorage: [],
      sessionStorage: [],
      inMemory: [],
      timestamp: Date.now()
    };

    // Clear localStorage (ALL patterns - be aggressive)
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith('apb.') || key.startsWith('apb:') || 
          key.includes('rfp') || key.includes('RFP') ||
          key.includes('scenario') || key.includes('deliverable') ||
          key.includes('timeline') || key.includes('pricing') ||
          key.includes('charles') || key.includes('session')) {
        clearingLog.localStorage.push(key);
        localStorage.removeItem(key);
      }
    });

    // Explicitly clear ALL known problematic keys
    const explicitKeys = [
      'apb.rfpText.v1', 'charles_agent_state', 'latest_scenarios',
      'current_session_id', 'timeline_synced', 'timeline_data',
      'timeline_reasoning', 'apb.analyzeImages', 'charles_width'
    ];
    explicitKeys.forEach(key => {
      if (localStorage.getItem(key)) {
        clearingLog.localStorage.push(key + ' (explicit)');
      }
      localStorage.removeItem(key);
    });

    // Clear ALL sessionStorage
    Object.keys(sessionStorage).forEach(key => {
      clearingLog.sessionStorage.push(key);
      sessionStorage.removeItem(key);
    });

    // Clear ALL in-memory data comprehensively
    if (window.APP) {
      clearingLog.inMemory.push('APP object');
      window.APP.summary = null;
      window.APP.rfpText = '';
      window.APP.suggestions = null;
      window.APP.deliverables = [];
    }

    if (window.APB) {
      clearingLog.inMemory.push('APB object');
      if (window.APB.step2) {
        window.APB.step2.rfpText = '';
        window.APB.step2.deliverables = [];
        window.APB.step2.components = {};
      }
    }

    // Clear global variables
    if (window.SCENARIOS) {
      clearingLog.inMemory.push('SCENARIOS');
      window.SCENARIOS = null;
    }
    if (window.DELIVERABLES) {
      clearingLog.inMemory.push('DELIVERABLES');
      window.DELIVERABLES = [];
    }
    if (window.OPTIONS) {
      clearingLog.inMemory.push('OPTIONS');
      window.OPTIONS = null;
    }
    if (window.DELIV_INDEX) {
      clearingLog.inMemory.push('DELIV_INDEX');
      window.DELIV_INDEX = {};
      window.DELIV_INDEX_LO = {};
    }
    if (window.selectionStore) {
      clearingLog.inMemory.push('selectionStore');
      window.selectionStore.deliverables.clear();
      window.selectionStore.components.clear();
      window.selectionStore.manualDeliverables.clear();
      window.selectionStore.manualComponents.clear();
    }
    if (window.pricingData) {
      clearingLog.inMemory.push('pricingData');
      window.pricingData.deliverableTypes.clear();
      window.pricingData.retainers.clear();
      window.pricingData.complexity.clear();
      window.pricingData.urgency.clear();
      window.pricingData.resourceTypes.clear();
      window.pricingData.discounts.clear();
    }
    if (window.componentDataCache) {
      clearingLog.inMemory.push('componentDataCache');
      window.componentDataCache.clear();
    }

    // Clear AI Assistant state
    if (window.aiAssistant) {
      clearingLog.inMemory.push('AI Assistant');
      window.aiAssistant.agentState = {
        uploadedFiles: [],
        selectedDeliverables: [],
        currentStep: 'step1',
        formValues: {},
        analysisMode: 'deep',
        jobId: null,
        lastError: null,
        stateHistory: []
      };
    }

    // Set PERMANENT flag to prevent auto-restore
    localStorage.setItem('apb.data_cleared', 'true');
    localStorage.setItem('apb.clear_timestamp', Date.now().toString());

    // Log what we cleared
    console.log('[CLEAR] Cleared localStorage keys:', clearingLog.localStorage);
    console.log('[CLEAR] Cleared sessionStorage keys:', clearingLog.sessionStorage);
    console.log('[CLEAR] Cleared in-memory data:', clearingLog.inMemory);

    // Clear server-side cache
    try {
      await fetch('/api/clear_session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });
      console.log('[CLEAR] Server cache cleared for session:', sessionId);
    } catch (err) {
      console.warn('[CLEAR] Failed to clear server cache:', err);
    }

    // Start fresh session
    this.startNewSession();

    console.log('[CLEAR] ✅ All data cleared completely at', new Date().toISOString());
    return clearingLog;
  },

  getSessionKey(key) {
    const sessionId = this.getCurrentSessionId();
    return `apb.${sessionId}.${key}`;
  },

  setSessionItem(key, value) {
    const sessionKey = this.getSessionKey(key);
    localStorage.setItem(sessionKey, value);
  },

  getSessionItem(key) {
    const sessionKey = this.getSessionKey(key);
    return localStorage.getItem(sessionKey);
  },

  removeSessionItem(key) {
    const sessionKey = this.getSessionKey(key);
    localStorage.removeItem(sessionKey);
  }
};

window.SessionManager = SessionManager;

// ================================================================================
// Data Transformation Utilities
// ================================================================================

/**
 * Transform SCENARIOS.A backend format to unified pricing table patch format
 * @param {Object} scenario - Scenario object with items array
 * @returns {Object} - {deliverables: [...]} format for APBOneTable.hydrateFrom()
 */
function transformScenarioToPatchFormat(scenario) {
  if (!scenario || !scenario.items) {
    return { deliverables: [] };
  }

  // Helper to slugify component names for IDs
  function slugify(text) {
    return text
      .toString()
      .toLowerCase()
      .trim()
      .replace(/\s+/g, '-')           // Replace spaces with -
      .replace(/[^\w\-]+/g, '')       // Remove all non-word chars
      .replace(/\-\-+/g, '-')         // Replace multiple - with single -
      .replace(/^-+/, '')              // Trim - from start
      .replace(/-+$/, '');             // Trim - from end
  }

  const deliverables = scenario.items.map(item => {
    // Determine cadence based on is_retainer flag
    const isRetainer = item.is_retainer || item.retainer_months > 0;
    const cadence = isRetainer ? 'Monthly' : 'One-Time';
    const months = isRetainer ? (item.retainer_months || 12) : 0;

    const deliverable = {
      id: item.deliverable_code,
      title: item.deliverable_name || item.deliverable || item.deliverable_code,
      dept: item.category || 'General',
      cadence: cadence,
      months: months,
      hours: item.total_hours || item.hours || 0,
      rate: item.blended_rate || item.rate || item.effective_rate || 195,
      price: item.price || 0,
      resources: item.resources || [],
      components: []
    };

    // Transform components if they exist
    if (item.components && Array.isArray(item.components)) {
      deliverable.components = item.components.map(comp => ({
        id: slugify(comp.name || 'component'),
        title: comp.name || 'Component',
        hours: comp.hours || 0,
        rate: comp.rate || deliverable.rate,
        cadence: comp.cadence || deliverable.cadence,
        months: comp.months || deliverable.months
      }));
    }

    return deliverable;
  });

  return { deliverables };
}

// ================================================================================
// Industry Template System
// ================================================================================
let selectedIndustry = null;
let industryDeliverables = [];

// Initialize industry selector
document.addEventListener('DOMContentLoaded', function() {
  const selector = document.getElementById('industry-selector');
  if (selector) {
    selector.addEventListener('change', handleIndustrySelection);
  }
});

async function handleIndustrySelection() {
  const selector = document.getElementById('industry-selector');
  const applyBtn = document.getElementById('btn-apply-template');
  const infoDiv = document.getElementById('industry-info');
  const descDiv = document.getElementById('industry-description');

  selectedIndustry = selector.value;

  if (!selectedIndustry) {
    applyBtn.style.display = 'none';
    infoDiv.style.display = 'none';
    industryDeliverables = [];
    return;
  }

  // Show apply button
  applyBtn.style.display = 'block';

  // Show industry-specific information
  infoDiv.style.display = 'block';

  if (selectedIndustry === 'luxury_fashion') {
    descDiv.innerHTML = `
      <strong>Luxury & Fashion Template:</strong><br>
      • Seasonal campaign planning (SS/FW collections)<br>
      • Fashion week activations & runway shows<br>
      • Influencer partnerships & celebrity ambassadors<br>
      • Heritage storytelling & craftsmanship content<br>
      • Exclusive events & VIP experiences<br>
      • Editorial shoots & lookbook production<br>
      <span style="color: #d946ef;">✨ Includes 1.5x-2x luxury pricing multipliers</span>
    `;
  }

  // Fetch industry-specific deliverables when button clicked
  applyBtn.onclick = async () => {
    try {
      await applyIndustryTemplate();
    } catch (error) {
      console.error('[INDUSTRY] Error applying industry template:', error);
      alert(`An error occurred while applying the industry template. Please try again.`);
    }
  };
}

async function applyIndustryTemplate() {
  if (!selectedIndustry) return;

  const applyBtn = document.getElementById('btn-apply-template');
  applyBtn.disabled = true;
  applyBtn.textContent = 'Applying...';

  try {
    // Get RFP text if available
    const rfpText = document.getElementById('rfpText').value || '';

    // Fetch industry-specific suggestions
    const response = await fetch('/api/industry/suggest-deliverables', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.JSON.stringify({
        industry: selectedIndustry,
        rfp_text: rfpText
      })
    });

    if (!response.ok) throw new Error('Failed to fetch industry deliverables');

    const data = await response.json();
    industryDeliverables = data.deliverables || [];

    // Show a notification
    if (industryDeliverables.length > 0) {
      alert(`✅ Applied ${data.industry} template!\n\n${industryDeliverables.length} fashion-specific deliverables loaded.\n\nClick "Analyze with AI" to incorporate these into your project.`);

      // Store for use during analysis
      sessionStorage.setItem('industry_template', selectedIndustry);
      sessionStorage.setItem('industry_deliverables', JSON.JSON.stringify(industryDeliverables));
    } else {
      alert('No specific deliverables found for this industry template.');
    }
  } catch (err) {
    console.error('Error applying industry template:', err);
    alert('Failed to apply industry template. Please try again.');
  } finally {
    applyBtn.disabled = false;
    applyBtn.textContent = 'Apply Template';
  }
}

// Manual AI Polling Recovery - Can be called from console if polling gets stuck
window.resumeAIPolling = function(jobId) {
  if (!jobId && window.aiAnalysisJobId) {
    jobId = window.aiAnalysisJobId;
  }

  if (!jobId) {
    console.error('[MANUAL RECOVERY] No job ID available. Cannot resume polling.');
    return false;
  }

  console.log('[MANUAL RECOVERY] 🚨 Manually resuming AI polling for job:', jobId);

  // Clear any existing intervals first
  if (window.aiAnalysisInterval) {
    clearInterval(window.aiAnalysisInterval);
    window.aiAnalysisInterval = null;
  }
  if (window.PROTECTED_AI_INTERVAL) {
    clearInterval(window.PROTECTED_AI_INTERVAL);
    window.PROTECTED_AI_INTERVAL = null;
  }

  // Set protection flags
  window.PROTECTED_AI_POLLING = true;

  // Create new protected interval
  window.aiAnalysisInterval = setInterval(() => {
    console.log('[MANUAL RECOVERY] ⚡ Polling tick at', new Date().toLocaleTimeString());
    pollAIAnalysis(jobId);
  }, 2000);

  window.PROTECTED_AI_INTERVAL = window.aiAnalysisInterval;

  // Start polling immediately
  pollAIAnalysis(jobId);

  console.log('[MANUAL RECOVERY] ✅ Polling resumed. Use window.stopAIPolling() to stop.');
  return true;
};

// Stop AI Polling manually
window.stopAIPolling = function() {
  console.log('[MANUAL] 🛑 Manually stopping AI polling');
  window.PROTECTED_AI_POLLING = false;

  if (window.aiAnalysisInterval) {
    clearInterval(window.aiAnalysisInterval);
    window.aiAnalysisInterval = null;
  }
  if (window.PROTECTED_AI_INTERVAL) {
    clearInterval(window.PROTECTED_AI_INTERVAL);
    window.PROTECTED_AI_INTERVAL = null;
  }

  console.log('[MANUAL] ✅ AI polling stopped');
  return true;
};

// Emergency polling override for AI analysis
window.forceAllowPolling = function() {
  if (window.GlobalPollingManager) {
    window.GlobalPollingManager.isShuttingDown = false;
    console.log('[POLLING] Force allowed all polling');
  }
};

// Clear All Data with Confirmation Dialog
async function clearAllDataWithConfirmation() {
  const confirmed = confirm(
    '⚠️ Clear All Data?\n\n' +
    'This will:\n' +
    '• Delete all stored RFP data\n' +
    '• Clear all analysis results\n' +
    '• Clear AI Assistant history\n' +
    '• Reset the application to fresh state\n' +
    '• Clear server-side cache\n\n' +
    'This action cannot be undone. Continue?'
  );

  if (!confirmed) return;

  try {
    console.log('[CLEAR] User confirmed data clear at', new Date().toISOString());

    // Show loading state
    const btn = document.getElementById('btnClearAllData');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '⏳ Clearing...';
    }

    // Clear all data - this now returns detailed log
    const clearLog = await SessionManager.clearAllData();

    // Clear AI Assistant data
    if (window.aiAssistant) {
      window.aiAssistant.clearAllData();
    }

    // Reset UI completely
    document.getElementById('rfpText').value = '';
    document.getElementById('rfpFile').value = '';

    // Clear any file previews
    const filePreview = document.getElementById('file-preview');
    if (filePreview) filePreview.innerHTML = '';

    // All steps remain visible - open dashboard layout
    // No need to hide steps as users can see entire workflow

    // Clear any visible deliverables or components panels
    const delivPanel = document.getElementById('deliverableList');
    if (delivPanel) delivPanel.innerHTML = '';
    const compPanel = document.getElementById('componentsList');
    if (compPanel) compPanel.innerHTML = '';

    // Log what was cleared
    console.log('[CLEAR] Clear operation completed:', clearLog);

    // Reset button state
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '🗑️ Clear All Data';
    }

    alert(
      '✅ All data cleared successfully!\n\n' +
      'The application has been reset to a fresh state.\n\n' +
      'The page will reload to ensure complete cleanup.'
    );

    // Reload page for complete reset
    setTimeout(() => window.location.reload(), 500);
  } catch (err) {
    console.error('[CLEAR] Error clearing data:', err);
    alert('❌ Error clearing data. Please try again or refresh the page.');

    // Reset button state
    const btn = document.getElementById('btnClearAllData');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '🗑️ Clear All Data';
    }
  }
}

window.clearAllDataWithConfirmation = clearAllDataWithConfirmation;

// ================================================================================
// Resource Leveling Event Listeners
// ================================================================================
// Listen for pricing leveling applied events to refresh the pricing display
document.addEventListener('pricing:leveling-applied', (event) => {
  console.log('[Resource Leveling] Pricing updated with leveling costs:', event.detail);

  // Refresh pricing table to show conflict indicators
  if (typeof updatePricingTable === 'function') {
    updatePricingTable();
  }

  // Refresh pricing summary to show leveling costs
  if (typeof updatePricingSummary === 'function') {
    updatePricingSummary();
  }

  // Notify user of the resource conflicts detected
  const levelingData = event.detail;
  if (levelingData && levelingData.totalCost > 0) {
    const conflictCount = Object.keys(levelingData.deliverableConflicts || {}).length;
    console.log(`[Resource Leveling] ${conflictCount} deliverables affected by resource conflicts. Total leveling cost: $${Math.round(levelingData.totalCost).toLocaleString()}`);
  }
});

// Listen for gantt:changed events to re-analyze resource conflicts
document.addEventListener('gantt:changed', (event) => {
  console.log('[Resource Leveling] Gantt changed, re-analyzing resource conflicts');

  // Get all tasks from the Gantt if available
  if (window.gantt && typeof window.gantt.getTaskByTime === 'function') {
    const tasks = window.gantt.getTaskByTime();
    if (tasks && tasks.length > 0) {
      // Re-analyze resource risks which will emit resource:conflicts event
      analyzeResourceRisks(tasks);
    }
  }
});

// Listen for timeline task drag events to provide real-time feedback
document.addEventListener('task:dragging', (event) => {
  const { taskId, newStart, newEnd } = event.detail || {};
  if (!taskId) return;

  // Get current tasks and create a temporary updated list
  if (window.gantt && typeof window.gantt.getTaskByTime === 'function') {
    const tasks = window.gantt.getTaskByTime();
    const tempTasks = tasks.map(task => {
      if (task.id === taskId) {
        return { ...task, start: newStart, end: newEnd };
      }
      return task;
    });

    // Analyze temporary state for preview
    const tempRisks = analyzeResourceRisks(tempTasks);

    // Show preview of cost impact (could be displayed in a tooltip or status bar)
    if (tempRisks.length > 0) {
      const totalCost = tempRisks.reduce((sum, risk) => sum + risk.idleCost, 0);
      console.log(`[Resource Leveling Preview] Potential leveling cost: $${Math.round(totalCost).toLocaleString()}`);
    }
  }
});

// NEW: Gantt task updates sync with SCENARIO_STORE
document.addEventListener('gantt:task_updated', async (event) => {
  const {task, wbs_id, start_date, duration_days } = event.detail || {};
  if (!wbs_id) return;

  console.log('[GANTT SYNC] Task updated:', { wbs_id, start_date, duration_days });

  // Get session ID from APP_STATE (must exist from build_scenario)
  const sessionId = getCurrentSessionId();

  try {
    // Call new SCENARIO_STORE timeline update endpoint
    const response = await fetch('/api/timeline/update_task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.JSON.stringify({
        session_id: sessionId,
        wbs_id: wbs_id,
        start_date: start_date,
        duration_days: duration_days
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[GANTT SYNC] Update failed:', errorText);
      return;
    }

    const result = await response.json();

    // Update the scenario with timeline changes
    const updatedScenario = result.scenario || result;

    if (updatedScenario && updatedScenario.items) {
      // Store updated scenario
      window.currentScenario = updatedScenario;
      window.SCENARIOS = { A: updatedScenario };

      // Update pricing table display to reflect timeline changes
      if (typeof updatePricingTable === 'function') {
        updatePricingTable();
      }

      console.log('[GANTT SYNC] Pricing table updated with timeline changes');
    }
  } catch (error) {
    console.error('[GANTT SYNC] Error updating task:', error);
  }
});

// Hook into existing Gantt library's drag end event if available
if (typeof window.Gantt !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    // Listen for Gantt bar drag end events
    const ganttContainer = document.querySelector('#gantt');
    if (ganttContainer) {
      ganttContainer.addEventListener('date_change', (event) => {
        const task = event.detail?.task;
        if (task) {
          // Calculate duration in days
          const start = new Date(task.start);
          const end = new Date(task.end);
          const durationDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24));

          // Dispatch our custom event for SCENARIO_STORE sync
          document.dispatchEvent(new CustomEvent('gantt:task_updated', {
            detail: {
              task: task,
              wbs_id: task.id || task.wbs_id,
              start_date: task.start,
              duration_days: durationDays
            }
          }));
        }
      });
    }
  });
}

// ISSUE 3: Retainer Options Functions

// NEW: Global retainer suggestions using ScenarioManager and updated backend
async function askAIForRetainerSuggestions(monthlyBudget = null) {
  // Check if ScenarioManager is available
  if (!window.ScenarioManager) {
    alert('ScenarioManager not available. Please reload the page.');
    return;
  }

  // Get current scenario from ScenarioManager
  const currentScenario = window.ScenarioManager.getCurrentScenario();

  // Check for scenario
  if (!currentScenario || !currentScenario.items || currentScenario.items.length === 0) {
    alert('Please build a scenario first before analyzing retainers.');
    return;
  }

  // Get session ID - prioritize ScenarioManager's session ID
  let sessionId;
  try {
    sessionId = window.ScenarioManager.state.sessionId || window.APP_STATE?.sessionId || getCurrentSessionId();
  } catch (e) {
    // If getCurrentSessionId throws, generate a new one
    sessionId = window.generateSessionId ? window.generateSessionId() : 'session_' + Date.now();
    if (window.ScenarioManager) {
      window.ScenarioManager.state.sessionId = sessionId;
    }
  }

  // Show loading on button
  const btn = event?.target;
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Analyzing...';
  }

  try {
    // Call updated retainer_suggestions endpoint with full scenario
    const res = await fetch('/api/pricing/retainer_suggestions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.JSON.stringify({
        session_id: sessionId,
        monthly_budget: monthlyBudget,
        scenario: currentScenario  // Send the full scenario for analysis
      })
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Retainer suggestions failed: ${errorText}`);
    }

    const result = await res.json();

    // Update the scenario with retainer suggestions
    const updatedScenario = result.scenario;

    if (updatedScenario && updatedScenario.items) {
      // Update ScenarioManager with new data
      window.ScenarioManager.updateDeliverablesFromAPI({ 
        scenarios: { A: updatedScenario },
        scenario: updatedScenario 
      });

      // Also update global references for compatibility
      window.currentScenario = updatedScenario;
      window.SCENARIOS = { A: updatedScenario };

      // Update pricing table display
      if (typeof updatePricingTable === 'function') {
        updatePricingTable();
      }

      // Re-render scenario if function exists
      if (window.renderScenario) {
        window.renderScenario('scenarioA', updatedScenario);
      }

      // Display retainer plan in UI panel
      if (result.retainer_plan) {
        displayRetainerPlan(result.retainer_plan);
      }

      // Display individual suggestions in AI Assistant panel if available
      if (result.suggestions && result.suggestions.length > 0) {
        displayRetainerSuggestions(result.suggestions);
      }

      // Show success message with details
      const message = result.message || 'Retainer suggestions applied successfully.';
      const details = result.converted_count > 0 
        ? `\n\n✓ ${result.converted_count} deliverables converted to retainers\n✓ ${result.retainer_plan?.monthly_hours || 0} total monthly hours\n✓ $${result.retainer_plan?.monthly_budget || 0} monthly budget`
        : '';

      alert(`✅ AI Retainer Suggestions Complete!\n\n${message}${details}`);

      console.log('[Retainer Suggestions] Applied:', result);
    } else {
      throw new Error('Invalid retainer suggestions response');
    }
  } catch (error) {
    console.error('[Retainer Suggestions] Failed:', error);
    alert(`❌ Retainer Suggestions Error:\n\n${error.message || 'Failed to get retainer suggestions. Please try again.'}`);
  } finally {
    // Reset button
    if (btn) {
      btn.disabled = false;
      btn.textContent = '🤖 Ask AI for Retainer Suggestions';
    }
  }
}

// Display retainer plan in a nice UI panel
function displayRetainerPlan(retainerPlan) {
  const container = document.getElementById('retainer-plan-container');
  if (!container) {
    // Create container if it doesn't exist
    const newContainer = document.createElement('div');
    newContainer.id = 'retainer-plan-container';
    newContainer.style.cssText = 'margin: 20px 0; padding: 20px; background: var(--card); border-radius: 12px; border: 2px solid var(--accent2);';

    // Insert after pricing table or in Step 3
    const step3 = document.getElementById('step3');
    if (step3) {
      step3.appendChild(newContainer);
    }
  }

  const displayContainer = container || document.getElementById('retainer-plan-container');

  if (displayContainer && retainerPlan) {
    let html = `
      <h3 style="color: var(--accent2); margin-bottom: 16px;">
        🔄 Suggested Retainer Plan
      </h3>
      <div style="background: rgba(139,92,246,0.1); padding: 16px; border-radius: 8px;">
        <p style="color: var(--text); font-size: 0.95em; line-height: 1.6;">
          ${retainerPlan.description || 'Recommended retainer configuration based on your project requirements.'}
        </p>
    `;

    if (retainerPlan.items && retainerPlan.items.length > 0) {
      html += `
        <div style="margin-top: 16px;">
          <h4 style="color: var(--accent); margin-bottom: 8px;">Retainer Items:</h4>
          <ul style="list-style: none; padding: 0;">
      `;

      retainerPlan.items.forEach(item => {
        html += `
          <li style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
            <strong style="color: var(--text);">${item.name || item.deliverable}</strong>
            <span style="color: var(--muted); margin-left: 8px;">${item.months || 12} months</span>
          </li>
        `;
      });

      html += `
          </ul>
        </div>
      `;
    }

    html += `
      </div>
    `;

    displayContainer.innerHTML = html;
    displayContainer.style.display = 'block';
  }
}

// Display individual retainer suggestions in the AI Assistant panel
function displayRetainerSuggestions(suggestions) {
  // Find or create container for suggestions in the AI Assistant panel
  let suggestionsContainer = document.getElementById('retainer-suggestions-list');

  if (!suggestionsContainer) {
    // Try to find AI Assistant panel or create in Step 3
    const aiAssistantPanel = document.querySelector('.ai-assistant-panel') || 
                            document.querySelector('#ai-assistant-content');

    if (aiAssistantPanel) {
      suggestionsContainer = document.createElement('div');
      suggestionsContainer.id = 'retainer-suggestions-list';
      suggestionsContainer.className = 'retainer-suggestions-list';
      aiAssistantPanel.appendChild(suggestionsContainer);
    } else {
      // Create in Step 3 as fallback
      const step3 = document.getElementById('step3');
      if (step3) {
        suggestionsContainer = document.createElement('div');
        suggestionsContainer.id = 'retainer-suggestions-list';
        suggestionsContainer.style.cssText = 'margin: 20px 0; padding: 20px; background: var(--card); border-radius: 12px; border: 2px solid var(--accent2);';
        step3.appendChild(suggestionsContainer);
      }
    }
  }

  if (!suggestionsContainer) return;

  // Build HTML for suggestions
  let html = `
    <h4 style="color: var(--accent2); margin-bottom: 16px;">
      🤖 AI Retainer Analysis
    </h4>
    <div class="suggestions-grid" style="display: grid; gap: 12px;">
  `;

  suggestions.forEach(suggestion => {
    const confidence = Math.round((suggestion.confidence || 0.85) * 100);
    const confidenceColor = confidence >= 80 ? '#10b981' : confidence >= 60 ? '#f59e0b' : '#ef4444';

    html += `
      <div class="suggestion-card" style="padding: 16px; background: rgba(139,92,246,0.05); border: 1px solid rgba(139,92,246,0.2); border-radius: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
          <h5 style="color: var(--text); margin: 0; font-size: 0.95em;">
            ${suggestion.deliverable_name}
          </h5>
          <span style="padding: 2px 8px; background: ${confidenceColor}20; color: ${confidenceColor}; border-radius: 4px; font-size: 0.8em;">
            ${confidence}% confidence
          </span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 12px 0;">
          <div style="text-align: center;">
            <div style="color: var(--muted); font-size: 0.8em;">Monthly Hours</div>
            <div style="color: var(--accent); font-weight: bold;">${suggestion.monthly_hours}</div>
          </div>
          <div style="text-align: center;">
            <div style="color: var(--muted); font-size: 0.8em;">Duration</div>
            <div style="color: var(--accent); font-weight: bold;">${suggestion.suggested_months} mo</div>
          </div>
          <div style="text-align: center;">
            <div style="color: var(--muted); font-size: 0.8em;">Total Hours</div>
            <div style="color: var(--accent); font-weight: bold;">${suggestion.total_hours}</div>
          </div>
        </div>

        <p style="color: var(--muted); font-size: 0.85em; margin: 8px 0; font-style: italic;">
          ${suggestion.reasoning}
        </p>

        <button 
          onclick="applyRetainerSuggestion('${suggestion.deliverable_code}', ${suggestion.suggested_months}, ${suggestion.monthly_hours})"
          style="width: 100%; padding: 8px; background: var(--accent2); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9em;"
          onmouseover="this.style.opacity='0.9'" 
          onmouseout="this.style.opacity='1'"
        >
          Apply This Retainer
        </button>
      </div>
    `;
  });

  html += `
    </div>
  `;

  suggestionsContainer.innerHTML = html;
  suggestionsContainer.style.display = 'block';
}

// Apply individual retainer suggestion
function applyRetainerSuggestion(deliverableCode, months, monthlyHours) {
  // Update in ScenarioManager
  if (window.ScenarioManager) {
    const deliverable = window.ScenarioManager.state.deliverables.find(
      d => d.id === deliverableCode || d.deliverable_code === deliverableCode
    );

    if (deliverable) {
      // Update deliverable to retainer
      deliverable.cadence = 'Monthly';
      deliverable.months = months;
      deliverable.monthly_hours = monthlyHours;
      deliverable.is_retainer = true;

      // Recalculate price
      deliverable.price = monthlyHours * months * (deliverable.rate || 195);

      // Trigger updates
      window.ScenarioManager.recompute();
      window.ScenarioManager.emit();

      // Update pricing table
      if (typeof updatePricingTable === 'function') {
        updatePricingTable();
      }

      // Show confirmation
      alert(`✅ Applied retainer configuration:\n\n${deliverable.title}\n${monthlyHours} hours/month for ${months} months`);
    }
  }
}

// Export the functions globally
window.askAIForRetainerSuggestions = askAIForRetainerSuggestions;
window.displayRetainerSuggestions = displayRetainerSuggestions;
window.applyRetainerSuggestion = applyRetainerSuggestion;

function toggleRetainerType(code, isRetainer) {
  if (isRetainer) {
    pricingData.deliverableTypes.set(code, 'RETAINER');
    pricingData.retainers.set(code, 12); // Default 12 months
    // Show months input
    const monthsWrap = document.querySelector(`.retainer-months-wrap[data-code="${code}"]`);
    if (monthsWrap) monthsWrap.style.display = 'flex';
  } else {
    pricingData.deliverableTypes.set(code, 'PROJECT');
    pricingData.retainers.delete(code);
    // Hide months input
    const monthsWrap = document.querySelector(`.retainer-months-wrap[data-code="${code}"]`);
    if (monthsWrap) monthsWrap.style.display = 'none';
  }

  console.log(`[RETAINER] ${code} set to ${isRetainer ? 'RETAINER' : 'PROJECT'}`);
}

function updateRetainerMonths(code, months) {
  const monthsNum = parseInt(months) || 12;
  const clampedMonths = Math.min(Math.max(monthsNum, 1), 36); // Allow up to 36 months
  pricingData.retainerMonths.set(code, clampedMonths);

  // Update the pricing display immediately
  updatePricingTable();
  updatePricingSummary();

  console.log(`[RETAINER] ${code} set to ${clampedMonths} months`);
}

async function suggestRetainerConfig(code) {
  const btn = event.target;
  btn.disabled = true;
  btn.textContent = 'Analyzing...';

  try {
    // Get RFP text
    const rfpText = window.APP?.rfpText || APB.step2.rfpText || 
                   sessionStorage.getItem('apb.rfp_text') || 
                   document.getElementById('rfpText')?.value || '';

    if (!rfpText) {
      alert('Please provide RFP text before using AI suggestions');
      return;
    }

    // Call AI to analyze if this should be a retainer
    const analyzeRes = await fetch('/api/ai/analyze_project_retainer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.JSON.stringify({
        rfp_text: rfpText,
        deliverables: [{ code, name: labelFor(code) || code }]
      })
    });

    if (analyzeRes.ok) {
      const analysis = await analyzeRes.json();
      const suggestion = analysis.suggestions?.[0];

      if (suggestion) {
        // Update retainer type
        const isRetainer = suggestion.type === 'RETAINER';
        const retainerToggle = document.querySelector(`.retainer-toggle[data-code="${code}"]`);
        if (retainerToggle) {
          retainerToggle.checked = isRetainer;
          toggleRetainerType(code, isRetainer);
        }

        // If retainer, get month suggestion
        if (isRetainer) {
          const monthsRes = await fetch('/api/pricing/retainer_suggest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.JSON.stringify({
              deliverables: [{ 
                code, 
                name: labelFor(code) || code,
                type: 'RETAINER'
              }],
              rfp_text: rfpText
            })
          });

          if (monthsRes.ok) {
            const monthsData = await monthsRes.json();
            const monthsSuggestion = monthsData.suggestions?.[0];

            if (monthsSuggestion && monthsSuggestion.recommended_months) {
              const monthsInput = document.querySelector(`.retainer-months[data-code="${code}"]`);
              if (monthsInput) {
                monthsInput.value = monthsSuggestion.recommended_months;
                updateRetainerMonths(code, monthsSuggestion.recommended_months);
              }
            }
          }
        }

        // Show feedback
        alert(`Suggested: ${isRetainer ? 'RETAINER' : 'PROJECT'}${isRetainer && suggestion.recommended_months ? ' for ' + suggestion.recommended_months + ' months' : ''}\n\nReason: ${suggestion.reason || 'Based on RFP analysis'}`);
      }
    }
  } catch (error) {
    console.error('Failed to get AI suggestion:', error);
    alert('Failed to get AI suggestion. Please try again.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'AI Suggest';
  }
}

// Auto-detect retainer items after smart selection
async function autoDetectRetainers() {
  const rfpText = window.APP?.rfpText || APB.step2.rfpText || 
                 sessionStorage.getItem('apb.rfp_text') || 
                 document.getElementById('rfpText')?.value || '';

  if (!rfpText || APB.step2.selectedCodes.size === 0) return;

  const deliverables = Array.from(APB.step2.selectedCodes).map(code => ({
    code,
    name: labelFor(code) || code
  }));

  try {
    const res = await fetch('/api/ai/analyze_project_retainer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.JSON.stringify({
        rfp_text: rfpText,
        deliverables
      })
    });

    if (res.ok) {
      const data = await res.json();
      data.suggestions?.forEach(suggestion => {
        if (suggestion.type === 'RETAINER') {
          pricingData.deliverableTypes.set(suggestion.deliverable_code, 'RETAINER');
          pricingData.retainers.set(suggestion.deliverable_code, suggestion.recommended_months || 12);
        }
      });

      // Re-render to show retainer badges
      renderDeliverablesPanel();
    }
  } catch (error) {
    console.warn('Failed to auto-detect retainers:', error);
  }
}

window.toggleRetainerType = toggleRetainerType;
window.updateRetainerMonths = updateRetainerMonths;
window.suggestRetainerConfig = suggestRetainerConfig;

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
  l2ByComponent: new Map(),                      // Map<delivCode::componentKey, Set<l2Name>>
};

window.APB.step2 = {
  rfpText: '',                                   // filled from Step 1 or sessionStorage
  selectedCodes: selectionStore.deliverables,    // alias for compatibility
  selectedComponentsByCode: {},                  // DEPRECATED: use selectionStore.componentsByDeliv
  selectedL2ByKey: {},                           // DEPRECATED: use selectionStore.l2ByComponent
  complexity: 'Advanced',                        // default complexity
  tier: 'T2_MediumVolume',                       // default tier
  activeDeliverableCode: null,                   // currently active deliverable in Components panel
  activeComponentName: null,                     // currently active component in L2 panel
  allDeliverables: [],                           // from /api/options
  aiSuggestedCodes: new Set(),                   // codes that came from AI suggestions
  filters: {                                     // Task 1.3: search filter state
    deliverables: '',
    components: '',
    l2: ''
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

// CRITICAL FIX: Create Proxy-backed object for selectedL2ByKey (Task 6 fix)
// This ensures ALL read/write operations sync with selectionStore.l2ByComponent
const selectedL2Proxy = new Proxy({}, {
  get(target, key) {
    // Let Object.entries(), Object.keys() work via ownKeys/getOwnPropertyDescriptor
    return selectionStore.l2ByComponent.get(String(key));
  },
  set(target, key, value) {
    if (value instanceof Set) {
      selectionStore.l2ByComponent.set(String(key), value);
    } else if (Array.isArray(value)) {
      selectionStore.l2ByComponent.set(String(key), new Set(value));
    } else if (value === undefined || value === null) {
      selectionStore.l2ByComponent.delete(String(key));
    }
    return true;
  },
  deleteProperty(target, key) {
    selectionStore.l2ByComponent.delete(String(key));
    return true;
  },
  has(target, key) {
    return selectionStore.l2ByComponent.has(String(key));
  },
  ownKeys() {
    return Array.from(selectionStore.l2ByComponent.keys());
  },
  getOwnPropertyDescriptor(target, key) {
    if (selectionStore.l2ByComponent.has(String(key))) {
      return {
        enumerable: true,
        configurable: true,
        value: selectionStore.l2ByComponent.get(String(key))
      };
    }
  }
});

// Lock the property to prevent accidental reassignment
Object.defineProperty(S2, 'selectedL2ByKey', {
  get() { return selectedL2Proxy; },
  set(value) {
    // If someone tries to replace the whole object, sync it to the Map instead
    if (value === null || (typeof value === 'object' && Object.keys(value).length === 0)) {
      selectionStore.l2ByComponent.clear();
    } else if (typeof value === 'object') {
      selectionStore.l2ByComponent.clear();
      Object.entries(value).forEach(([k, v]) => {
        if (v instanceof Set) {
          selectionStore.l2ByComponent.set(k, v);
        } else if (Array.isArray(v)) {
          selectionStore.l2ByComponent.set(k, new Set(v));
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
  currentMonthlyItem: null,
  deliverableTypes: new Map(), // Maps deliverable_code -> 'PROJECT' or 'RETAINER'
  customHours: new Map(),      // Maps deliverable_code -> custom hours
  customRates: new Map(),       // Maps deliverable_code -> custom rate
  retainerMonths: new Map(),   // Maps deliverable_code -> number of months for retainers
  originalScenario: null,       // Store original scenario for comparison
  rebuildVersion: 0,            // Track rebuild versions
  resourceBreakdown: new Map()  // Maps deliverable_code -> resource allocation
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
  // Check both old and new state systems for compatibility
  // New UI uses APB.step2.selectedCodes, old UI uses S2.selectedCodes
  const newSystemCodes = (window.APB?.step2?.selectedCodes) ? Array.from(APB.step2.selectedCodes) : [];
  const oldSystemCodes = Array.from(S2.selectedCodes);

  // Get whichever has data (prefer new system if both have data)
  const codes = newSystemCodes.length > 0 ? newSystemCodes : oldSystemCodes;

  // Filter out null, undefined, empty strings, and invalid values
  const validCodes = codes.filter(code => {
    if (code == null || code === undefined) return false;
    if (typeof code !== 'string') return false;
    if (code.trim() === '') return false;
    return true;
  });

  console.log(`[readSelectedCodesFromUI] Total: ${codes.length}, Valid: ${validCodes.length}`);
  if (codes.length !== validCodes.length) {
    console.warn('[readSelectedCodesFromUI] Filtered out invalid codes:', codes.filter(c => !validCodes.includes(c)));
  }

  return validCodes;
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

        // Emit change to ScenarioStore via GanttBridge
        if (window.GanttBridge && window.GanttBridge.emitChange) {
          GanttBridge.emitChange({
            deliverableId: task.id,
            start: start.toISOString().split('T')[0],
            end: end.toISOString().split('T')[0],
            durationDays: Math.ceil((end - start) / (1000*60*60*24)),
            resources: task.resources || []
          });
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
      body: JSON.JSON.stringify({
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
      body: JSON.JSON.stringify({
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

// Enhanced pricing data store with cadence support
const pricingDataEnhanced = {
  ...pricingData,
  cadenceTypes: new Map(),      // deliverable_code -> 'ONE_TIME' | 'MONTHLY' | 'QUARTERLY' | 'SEMI_ANNUAL'
  periodsCount: new Map(),      // deliverable_code -> number of periods
  editMode: new Map(),          // deliverable_code -> boolean (editing state)
  componentTasks: new Map(),    // deliverable_code -> array of tasks
};

// UNIFIED PRICING TABLE - Comprehensive implementation
function updatePricingTable() {
  const container = document.getElementById('pricing-container') || document.getElementById('pricing-tbody')?.parentElement?.parentElement;
  if (!container || !SCENARIOS) return;

  const scenario = SCENARIOS.A || SCENARIOS[0];
  if (!scenario || !scenario.items) return;

  // Store original scenario on first load
  if (!pricingData.originalScenario) {
    pricingData.originalScenario = JSON.parse(JSON.JSON.stringify(scenario));
  }

  // Create comprehensive table HTML structure
  let tableHTML = `
    <div class="unified-pricing-table" style="margin: 20px 0;">
      <h3 style="color: var(--accent); margin-bottom: 16px; font-size: 1.3em;">
        📊 Unified Pricing Details
      </h3>

      <table id="pricing-details-table" style="width: 100%; border-collapse: separate; border-spacing: 0; background: var(--card); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <thead style="background: linear-gradient(135deg, rgba(106,163,255,0.1), rgba(139,92,246,0.1));">
          <tr>
            <th style="padding: 14px 12px; text-align: left; color: var(--accent); font-weight: 600; border-bottom: 2px solid rgba(106,163,255,0.2);">
              Deliverable/Component
            </th>
            <th style="padding: 14px 12px; text-align: center; color: var(--accent); font-weight: 600; border-bottom: 2px solid rgba(106,163,255,0.2); width: 140px;">
              Type/Cadence
            </th>
            <th style="padding: 14px 12px; text-align: center; color: var(--accent); font-weight: 600; border-bottom: 2px solid rgba(106,163,255,0.2); width: 100px;">
              # Periods
            </th>
            <th style="padding: 14px 12px; text-align: center; color: var(--accent); font-weight: 600; border-bottom: 2px solid rgba(106,163,255,0.2); width: 90px;">
              Hours
            </th>
            <th style="padding: 14px 12px; text-align: center; color: var(--accent); font-weight: 600; border-bottom: 2px solid rgba(106,163,255,0.2); width: 100px;">
              Rate (USD)
            </th>
            <th style="padding: 14px 12px; text-align: right; color: var(--accent); font-weight: 600; border-bottom: 2px solid rgba(106,163,255,0.2); width: 120px;">
              Price/Period
            </th>
            <th style="padding: 14px 12px; text-align: right; color: var(--accent); font-weight: 600; border-bottom: 2px solid rgba(106,163,255,0.2); width: 130px;">
              Total Price
            </th>
            <th style="padding: 14px 12px; text-align: left; color: var(--accent); font-weight: 600; border-bottom: 2px solid rgba(106,163,255,0.2); min-width: 150px;">
              Resources/Roles
            </th>
            <th style="padding: 14px 12px; text-align: left; color: var(--accent); font-weight: 600; border-bottom: 2px solid rgba(106,163,255,0.2); min-width: 150px;">
              Tasks
            </th>
            <th style="padding: 14px 12px; text-align: center; color: var(--accent); font-weight: 600; border-bottom: 2px solid rgba(106,163,255,0.2); width: 100px;">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
  `;

  // NEW: Calculate grand total from scenario.totals.price instead of manual calculation
  let grandTotal = 0;
  if (scenario.totals && typeof scenario.totals.price === 'number' && !isNaN(scenario.totals.price) && scenario.totals.price > 0) {
    grandTotal = scenario.totals.price;
  }

  let rowIndex = 0;

  scenario.items.forEach((item, itemIndex) => {
    // Get cadence and periods
    const cadenceType = pricingDataEnhanced.cadenceTypes.get(item.deliverable_code) || 
                       (pricingData.deliverableTypes.get(item.deliverable_code) === 'RETAINER' ? 'MONTHLY' : 'ONE_TIME');
    const periods = pricingDataEnhanced.periodsCount.get(item.deliverable_code) || 
                   (cadenceType === 'MONTHLY' ? 12 : cadenceType === 'QUARTERLY' ? 4 : cadenceType === 'SEMI_ANNUAL' ? 2 : 1);
    const isEditing = pricingDataEnhanced.editMode.get(item.deliverable_code) || false;

    // Get custom values or defaults
    const customHours = pricingData.customHours.get(item.deliverable_code) || item.hours || 0;
    const customRate = pricingData.customRates.get(item.deliverable_code) || item.blended_rate || 195;
    const pricePerPeriod = customHours * customRate;
    const totalPrice = pricePerPeriod * periods;

    // Get resource breakdown
    const resources = pricingData.resourceBreakdown.get(item.deliverable_code) || 
                     extractResourceAllocation(item);

    // Get tasks list
    const tasks = extractDeliverableTasks(item);

    // Check for resource conflicts from ScenarioStore
    let hasResourceConflict = false;
    let conflictCost = 0;
    let conflictTooltip = '';

    if (window.ScenarioStore && window.ScenarioStore.state.resourceLeveling) {
      const conflicts = window.ScenarioStore.state.resourceLeveling.deliverableConflicts[item.deliverable_code];
      if (conflicts) {
        hasResourceConflict = true;
        conflictCost = conflicts.totalCost || 0;
        const conflictTypes = [...new Set(conflicts.conflicts.map(c => c.type))];
        const resources = [...new Set(conflicts.conflicts.map(c => c.resource))];
        conflictTooltip = `Resource conflicts detected:\n- ${resources.join(', ')}\n- Type: ${conflictTypes.join(', ')}\n- Leveling Cost: $${conflictCost.toLocaleString()}`;
      }
    }

    // Note: Grand total is now calculated from scenario.totals.price, not accumulated here

    // Determine row background (alternating + highlight for recurring)
    const isRecurring = cadenceType !== 'ONE_TIME';
    const rowBg = isRecurring ? 
      'background: linear-gradient(90deg, rgba(139,92,246,0.05), rgba(139,92,246,0.02));' : 
      (rowIndex % 2 === 0 ? 'background: rgba(255,255,255,0.01);' : 'background: transparent;');

    // Main deliverable row
    tableHTML += `
      <tr data-deliverable="${item.deliverable_code}" data=row-type="deliverable" 
          style="${rowBg} ${hasResourceConflict ? 'border-left: 4px solid #ef4444;' : ''} border-bottom: 1px solid rgba(255,255,255,0.1); transition: all 0.2s ease;">
        <td style="padding: 12px; font-weight: 700; color: var(--text);">
          <button onclick="toggleDeliverableExpand('${item.deliverable_code}')" 
                  style="background: transparent; border: none; color: var(--accent); cursor: pointer; padding: 0 8px 0 0; font-size: 0.9em; transition: transform 0.2s;"
                  title="Expand/collapse components">
            <span id="expand-${item.deliverable_code}" style="display: inline-block; transition: transform 0.2s;">▶</span>
          </button>
          <span style="color: ${isRecurring ? 'var(--accent2)' : 'var(--accent)'};">
            ${item.deliverable}
          </span>
          ${hasResourceConflict ? `
            <span class="resource-conflict-badge" 
                  style="background: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; 
                         margin-left: 8px; font-size: 0.75em; font-weight: 600; cursor: help;"
                  title="${conflictTooltip}">
              ⚠️ Resource Conflict
            </span>` : ''}
        </td>
        <td style="padding: 8px; text-align: center;">
          ${isEditing ? 
            `<select id="cadence-${item.deliverable_code}" 
                    onchange="updateCadenceType('${item.deliverable_code}', this.value)"
                    style="padding: 6px 10px; border: 1px solid rgba(139,92,246,0.5); border-radius: 6px; 
                           background: rgba(139,92,246,0.1); color: var(--text); cursor: pointer; 
                           font-size: 0.85em; width: 100%;">
              <option value="ONE_TIME" ${cadenceType === 'ONE_TIME' ? 'selected' : ''}>One-Time</option>
              <option value="MONTHLY" ${cadenceType === 'MONTHLY' ? 'selected' : ''}>Monthly</option>
              <option value="QUARTERLY" ${cadenceType === 'QUARTERLY' ? 'selected' : ''}>Quarterly</option>
              <option value="SEMI_ANNUAL" ${cadenceType === 'SEMI_ANNUAL' ? 'selected' : ''}>Semi-Annual</option>
            </select>` :
            `<span class="cadence-badge" style="padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 500;
                   background: ${cadenceType === 'ONE_TIME' ? 'rgba(106,163,255,0.1)' : 'rgba(139,92,246,0.1)'};
                   color: ${cadenceType === 'ONE_TIME' ? 'var(--accent)' : 'var(--accent2)'};">
              ${cadenceType.replace('_', '-')}
            </span>`}
        </td>
        <td style="padding: 8px; text-align: center;">
          ${cadenceType !== 'ONE_TIME' ? 
            (isEditing ?
              `<input type="number" id="periods-${item.deliverable_code}" value="${periods}" 
                      min="1" max="36" step="1"
                      onchange="updatePeriods('${item.deliverable_code}', this.value)"
                      style="width: 70px; padding: 6px; border: 1px solid rgba(139,92,246,0.3); 
                             border-radius: 4px; font-size: 0.85em;" />` :
              `<span style="font-weight: 500; color: var(--accent2);">${periods}</span>`) :
            '<span style="color: var(--muted);">-</span>'}
        </td>
        <td style="padding: 8px; text-align: center;">
          ${isEditing ?
            `<input type="number" id="hours-${item.deliverable_code}" value="${customHours}" 
                    min="0" step="0.5"
                    onchange="updateCustomHours('${item.deliverable_code}', this.value)"
                    style="width: 80px; padding: 6px; border: 1px solid rgba(106,163,255,0.3); 
                           border-radius: 4px; background: rgba(106,163,255,0.05); 
                           color: var(--text); text-align: center; font-weight: 500;" />` :
            `<span style="font-weight: 500;">${customHours}</span>`}
        </td>
        <td style="padding: 8px; text-align: center;">
          ${isEditing ?
            `<div style="display: flex; align-items: center; gap: 2px; justify-content: center;">
              <span style="color: var(--muted);">$</span>
              <input type="number" id="rate-${item.deliverable_code}" value="${customRate}" 
                     min="0" step="5"
                     onchange="updateCustomRate('${item.deliverable_code}', this.value)"
                     style="width: 70px; padding: 6px; border: 1px solid rgba(106,163,255,0.3); 
                            border-radius: 4px; background: rgba(106,163,255,0.05); 
                            color: var(--text); text-align: center; font-weight: 500;" />
            </div>` :
            `<span style="font-weight: 500;">$${customRate}</span>`}
        </td>
        <td style="padding: 8px; text-align: right; font-weight: 600; color: var(--accent);">
          $${pricePerPeriod.toLocaleString()}
        </td>
        <td style="padding: 8px; text-align: right; font-weight: 700; font-size: 1.05em;
                   color: ${isRecurring ? 'var(--accent2)' : 'var(--accent)'};">
          $${totalPrice.toLocaleString()}
        </td>
        <td style="padding: 8px; font-size: 0.85em; color: var(--muted);">
          ${formatResourceDisplay(resources)}
        </td>
        <td style="padding: 8px; font-size: 0.85em; color: var(--muted);">
          ${formatTasksList(tasks)}
        </td>
        <td style="padding: 8px; text-align: center;">
          ${isEditing ?
            `<div style="display: flex; gap: 4px; justify-content: center;">
              <button onclick="saveRowEdit('${item.deliverable_code}')"
                      style="padding: 4px 12px; background: var(--accent2); border: none; 
                             border-radius: 4px; color: #08121e; font-size: 0.8em; font-weight: 600;">
                Save
              </button>
              <button onclick="cancelRowEdit('${item.deliverable_code}')"
                      style="padding: 4px 12px; background: transparent; 
                             border: 1px solid var(--border); border-radius: 4px; 
                             color: var(--text); cursor: pointer; font-size: 0.8em;">
                Cancel
              </button>
            </div>` :
            `<button onclick="enableRowEdit('${item.deliverable_code}')"
                    style="padding: 6px 16px; background: transparent; 
                           border: 1px solid var(--accent); border-radius: 6px; 
                           color: var(--accent); cursor: pointer; font-size: 0.85em; 
                           font-weight: 500; transition: all 0.2s;">
              Edit
            </button>`}
        </td>
      </tr>
    `;

    rowIndex++;

    // Component rows (initially hidden)
    if (item.components && item.components.length > 0) {
      item.components.forEach(comp => {
        const compKey = `${item.deliverable_code}::${comp.name}`;
        const compCadence = pricingDataEnhanced.cadenceTypes.get(compKey) || cadenceType;
        const compPeriods = pricingDataEnhanced.periodsCount.get(compKey) || periods;
        const compIsEditing = pricingDataEnhanced.editMode.get(compKey) || false;
        const compHours = pricingData.customHours.get(compKey) || comp.hours || 0;
        const compRate = pricingData.customRates.get(compKey) || comp.rate || customRate;
        const compPricePerPeriod = compHours * compRate;
        const compTotalPrice = compPricePerPeriod * compPeriods;
        const compResources = extractComponentResources(comp);
        const compTasks = comp.tasks || [];

        // Note: Grand total is now calculated from scenario.totals.price, not accumulated here

        const compRowBg = compCadence !== 'ONE_TIME' ? 
          'background: linear-gradient(90deg, rgba(139,92,246,0.03), rgba(139,92,246,0.01));' :
          'background: rgba(255,255,255,0.005);';

        tableHTML += `
          <tr data-component="${compKey}" data-parent="${item.deliverable_code}" 
              class="component-row-${item.deliverable_code}"
              style="${compRowBg} display: none; border-bottom: 1px solid rgba(255,255,255,0.05);">
            <td style="padding: 10px 12px 10px 48px; color: var(--text); font-size: 0.9em;">
              ↳ ${comp.name}
            </td>
            <td style="padding: 8px; text-align: center;">
              ${compIsEditing ?
                `<select onchange="updateCadenceType('${compKey}', this.value)"
                        style="padding: 4px 8px; border: 1px solid rgba(139,92,246,0.4); 
                               border-radius: 4px; background: rgba(139,92,246,0.08); 
                               color: var(--text); font-size: 0.8em; width: 100%;">
                  <option value="ONE_TIME" ${compCadence === 'ONE_TIME' ? 'selected' : ''}>One-Time</option>
                  <option value="MONTHLY" ${compCadence === 'MONTHLY' ? 'selected' : ''}>Monthly</option>
                  <option value="QUARTERLY" ${compCadence === 'QUARTERLY' ? 'selected' : ''}>Quarterly</option>
                  <option value="SEMI_ANNUAL" ${compCadence === 'SEMI_ANNUAL' ? 'selected' : ''}>Semi-Annual</option>
                </select>` :
                `<span style="font-size: 0.8em; padding: 2px 8px; border-radius: 12px;
                       background: ${compCadence === 'ONE_TIME' ? 'rgba(106,163,255,0.08)' : 'rgba(139,92,246,0.08)'};">
                  ${compCadence.replace('_', '-')}
                </span>`}
            </td>
            <td style="padding: 8px; text-align: center;">
              ${compCadence !== 'ONE_TIME' ?
                (compIsEditing ?
                  `<input type="number" value="${compPeriods}" min="1" max="36"
                          onchange="updatePeriods('${compKey}', this.value)"
                          style="width: 60px; padding: 4px; border: 1px solid rgba(139,92,246,0.3); 
                                 border-radius: 4px; font-size: 0.85em;" />` :
                  `<span style="font-size: 0.85em;">${compPeriods}</span>`) :
                '<span style="color: var(--muted); font-size: 0.85em;">-</span>'}
            </td>
            <td style="padding: 8px; text-align: center;">
              ${compIsEditing ?
                `<input type="number" value="${compHours}" min="0" step="0.5"
                        onchange="updateCustomHours('${compKey}', this.value)"
                        style="width: 70px; padding: 4px; border: 1px solid rgba(106,163,255,0.3); 
                               border-radius: 4px; font-size: 0.85em;" />` :
                `<span style="font-size: 0.85em;">${compHours}</span>`}
            </td>
            <td style="padding: 8px; text-align: center;">
              ${compIsEditing ?
                `<div style="display: flex; align-items: center; gap: 2px; justify-content: center;">
                  <span style="color: var(--muted); font-size: 0.85em;">$</span>
                  <input type="number" value="${compRate}" min="0" step="5"
                         onchange="updateCustomRate('${compKey}', this.value)"
                         style="width: 60px; padding: 4px; border: 1px solid rgba(106,163,255,0.3); 
                                border-radius: 4px; font-size: 0.85em;" />
                </div>` :
                `<span style="font-size: 0.85em;">$${compRate}</span>`}
            </td>
            <td style="padding: 8px; text-align: right; font-size: 0.9em; color: var(--accent);">
              $${compPricePerPeriod.toLocaleString()}
            </td>
            <td style="padding: 8px; text-align: right; font-weight: 600; font-size: 0.95em;
                       color: ${compCadence !== 'ONE_TIME' ? 'var(--accent2)' : 'var(--accent)'};">
              $${compTotalPrice.toLocaleString()}
            </td>
            <td style="padding: 8px; font-size: 0.75em; color: var(--muted);">
              ${formatResourceDisplay(compResources)}
            </td>
            <td style="padding: 8px; font-size: 0.75em; color: var(--muted);">
              ${formatTasksList(compTasks)}
            </td>
            <td style="padding: 8px; text-align: center;">
              ${compIsEditing ?
                `<div style="display: flex; gap: 2px; justify-content: center;">
                  <button onclick="saveRowEdit('${compKey}')"
                          style="padding: 2px 8px; background: var(--accent2); border: none; 
                                 border-radius: 3px; color: #08121e; font-size: 0.75em;">
                    ✓
                  </button>
                  <button onclick="cancelRowEdit('${compKey}')"
                          style="padding: 2px 8px; background: transparent; 
                                 border: 1px solid var(--border); border-radius: 3px; 
                                 color: var(--text); font-size: 0.75em;">
                    ✗
                  </button>
                </div>` :
                `<button onclick="enableRowEdit('${compKey}')"
                        style="padding: 4px 12px; background: transparent; 
                               border: 1px solid rgba(106,163,255,0.5); border-radius: 4px; 
                               color: var(--accent); font-size: 0.8em;">
                  Edit
                </button>`}
            </td>
          </tr>
        `;
      });
    }
  });

  tableHTML += `
        </tbody>
      </table>

      <!-- Unified Grand Total Section -->
      <div class="grand-total-section" style="margin-top: 24px; padding: 20px; 
                background: linear-gradient(135deg, rgba(139,92,246,0.1), rgba(106,163,255,0.1)); 
                border-radius: 12px; border: 2px solid rgba(139,92,246,0.3);">
        <h4 style="margin: 0 0 12px 0; color: var(--accent); font-size: 1.2em;">
          💰 Grand Total
        </h4>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="font-size: 0.9em; color: var(--muted); margin-bottom: 4px;">
              Total Investment
            </div>
            <div id="grand-total-cost" style="font-size: 2.5em; font-weight: 700; 
                        background: linear-gradient(135deg, var(--accent), var(--accent2)); 
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              ${grandTotal > 0 ? '$' + grandTotal.toLocaleString() : '—'}
            </div>
            <div id="grand-total-breakdown" style="font-size: 0.85em; color: var(--muted); margin-top: 4px;">
              <!-- Breakdown will be updated by updatePricingSummary -->
            </div>
          </div>
          <div style="text-align: right;">
            <button onclick="optimizeAllPricing()" 
                    style="padding: 10px 20px; background: var(--accent2); border: none; 
                           border-radius: 8px; color: #08121e; font-weight: 600; 
                           cursor: pointer; margin-bottom: 8px;">
              🤖 AI Optimize Pricing
            </button>
            <div style="font-size: 0.85em; color: var(--muted);">
              Optimize based on budget & scope
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  // Replace the container content
  if (container.id === 'pricing-tbody') {
    // Replace entire table structure
    container.parentElement.parentElement.outerHTML = tableHTML;
  } else {
    container.innerHTML = tableHTML;
  }

  // Update any other summary sections that might exist
  updatePricingSummary();
}

// Update pricing summary panels - FIXED CALCULATION VERSION
function updatePricingSummary() {
  if (!SCENARIOS) return;

  const scenario = SCENARIOS.A || SCENARIOS[0];
  if (!scenario || !scenario.items) return;

  let oneTimeCount = 0;
  let oneTimeHours = 0;
  let oneTimeCost = 0;
  const projectItemsList = [];

  let retainerCount = 0;
  let retainerMonthlyHours = 0;
  let retainerMonthlyCost = 0;
  const retainerItemsList = [];

  scenario.items.forEach(item => {
    const delivType = pricingData.deliverableTypes.get(item.deliverable_code) || 'PROJECT';
    const isRetainer = (delivType === 'RETAINER');

    // Get custom values or defaults
    const hours = pricingData.customHours.get(item.deliverable_code) || item.hours || 0;
    const rate = pricingData.customRates.get(item.deliverable_code) || item.blended_rate || 195;
    const cost = hours * rate;

    if (isRetainer) {
      retainerCount++;
      retainerMonthlyHours += hours;
      retainerMonthlyCost += cost;
      retainerItemsList.push(item.deliverable);
    } else {
      oneTimeCount++;
      oneTimeHours += hours;
      oneTimeCost += cost;
      projectItemsList.push(item.deliverable);
    }

    // Also count components (FIXED KEY FORMAT)
    if (item.components && item.components.length > 0) {
      item.components.forEach(comp => {
        const compKey = `${item.deliverable_code}::${comp.name}`;  // Fixed to use :: separator
        const compType = pricingData.deliverableTypes.get(compKey) || delivType;
        const compIsRetainer = (compType === 'RETAINER');
        const compHours = pricingData.customHours.get(compKey) || comp.hours || 0;
        const compRate = pricingData.customRates.get(compKey) || comp.rate || rate;
        const compCost = compHours * compRate;

        if (compIsRetainer) {
          retainerMonthlyHours += compHours;
          retainerMonthlyCost += compCost;
        } else {
          oneTimeHours += compHours;
          oneTimeCost += compCost;
        }
      });
    }
  });

  // Update One-Time Summary
  const oneTimeCountEl = document.getElementById('one-time-count');
  const oneTimeHoursEl = document.getElementById('one-time-hours');
  const oneTimeCostEl = document.getElementById('one-time-cost');

  if (oneTimeCountEl) oneTimeCountEl.textContent = oneTimeCount;
  if (oneTimeHoursEl) oneTimeHoursEl.textContent = oneTimeHours.toFixed(1);
  if (oneTimeCostEl) oneTimeCostEl.textContent = `$${Math.round(oneTimeCost).toLocaleString()}`;

  // Update Retainer Summary
  const retainerCountEl = document.getElementById('retainer-count');
  const retainerHoursEl = document.getElementById('retainer-monthly-hours');
  const retainerCostEl = document.getElementById('retainer-monthly-cost');
  const retainerAnnualEl = document.getElementById('retainer-annual-cost');

  if (retainerCountEl) retainerCountEl.textContent = retainerCount;
  if (retainerHoursEl) retainerHoursEl.textContent = retainerMonthlyHours.toFixed(1);
  if (retainerCostEl) retainerCostEl.textContent = `$${Math.round(retainerMonthlyCost).toLocaleString()}`;
  if (retainerAnnualEl) retainerAnnualEl.textContent = `$${Math.round(retainerMonthlyCost * 12).toLocaleString()}`;

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

  // FIX: Update Grand Total - read from scenarios.A.totals.price
  const scenarioTotal = (scenario.totals && scenario.totals.price) ? scenario.totals.price : oneTimeCost;

  // Get resource leveling costs from ScenarioStore if available
  let resourceLevelingCost = 0;
  if (window.ScenarioStore && window.ScenarioStore.state.resourceLeveling) {
    resourceLevelingCost = window.ScenarioStore.state.resourceLeveling.totalCost || 0;
  }

  const grandTotal = scenarioTotal + (retainerMonthlyCost * 12) + resourceLevelingCost;
  const grandTotalEl = document.getElementById('grand-total-cost');
  const grandBreakdownEl = document.getElementById('grand-total-breakdown');

  if (grandTotalEl) grandTotalEl.textContent = `$${Math.round(grandTotal).toLocaleString()}`;
  if (grandBreakdownEl) {
    // Build breakdown text including resource leveling if applicable
    let breakdownParts = [`Scenario total ($${Math.round(scenarioTotal).toLocaleString()})`];

    if (retainerMonthlyCost > 0) {
      breakdownParts.push(`12 months retainer ($${Math.round(retainerMonthlyCost * 12).toLocaleString()})`);
    }

    if (resourceLevelingCost > 0) {
      breakdownParts.push(`<span style="color: #ef4444;">Resource leveling ($${Math.round(resourceLevelingCost).toLocaleString()})</span>`);
    }

    grandBreakdownEl.innerHTML = breakdownParts.join(' + ');
  }
}

// Helper function to extract resource allocation from item
function extractResourceAllocation(item) {
  const resources = {};

  // First, try to get from hours_by_role (from backend API)
  if (item.hours_by_role && Array.isArray(item.hours_by_role)) {
    item.hours_by_role.forEach(roleData => {
      // Backend uses Resource_Title as the role field
      const role = roleData.Resource_Title || roleData.role || 'General';
      const seniority = roleData.Seniority || roleData.seniority || '';
      const hours = parseFloat(roleData.Hours || roleData.hours || 0);
      if (hours > 0) {
        // Format as "Role (Seniority)" if seniority exists
        const roleKey = seniority ? `${role} (${seniority})` : role;
        resources[roleKey] = (resources[roleKey] || 0) + hours;
      }
    });
    if (Object.keys(resources).length > 0) {
      return resources;
    }
  }

  // Try to get from existing resources data structure
  if (item.resources) {
    return item.resources;
  }

  // Try to parse from tasks if available
  if (item.tasks && Array.isArray(item.tasks)) {
    item.tasks.forEach(task => {
      const role = task.role || task.Resource_Title || 'General';
      const hours = task.hours || 0;
      if (hours > 0) {
        resources[role] = (resources[role] || 0) + hours;
      }
    });
  }

  // Fallback to basic allocation
  if (Object.keys(resources).length === 0 && item.hours > 0) {
    resources['Team'] = item.hours;
  }

  return resources;
}

// Helper function to extract component resources
function extractComponentResources(comp) {
  const resources = {};

  // First, try to get from hours_by_role (from backend API)
  if (comp.hours_by_role && Array.isArray(comp.hours_by_role)) {
    comp.hours_by_role.forEach(roleData => {
      // Backend uses Resource_Title as the role field
      const role = roleData.Resource_Title || roleData.role || 'General';
      const seniority = roleData.Seniority || roleData.seniority || '';
      const hours = parseFloat(roleData.Hours || roleData.hours || 0);
      if (hours > 0) {
        // Format as "Role (Seniority)" if seniority exists
        const roleKey = seniority ? `${role} (${seniority})` : role;
        resources[roleKey] = (resources[roleKey] || 0) + hours;
      }
    });
    if (Object.keys(resources).length > 0) {
      return resources;
    }
  }

  // Try to get from existing resources data
  if (comp.resources) return comp.resources;

  // Try to parse from tasks if available
  if (comp.tasks && Array.isArray(comp.tasks)) {
    comp.tasks.forEach(task => {
      const role = task.role || task.Resource_Title || 'General';
      const hours = task.hours || 0;
      if (hours > 0) {
        resources[role] = (resources[role] || 0) + hours;
      }
    });
  }

  // Fallback to basic allocation
  if (Object.keys(resources).length === 0 && comp.hours > 0) {
    resources['Team'] = comp.hours;
  }

  return resources;
}

// Format resource display for the table
function formatResourceDisplay(resources) {
  if (!resources || Object.keys(resources).length === 0) {
    return '-';
  }

  const entries = Object.entries(resources)
    .sort((a, b) => b[1] - a[1]) // Sort by hours descending
    .slice(0, 3) // Show top 3
    .map(([role, hours]) => `${role}: ${hours}h`);

  return entries.join(' • ');
}

// Toggle deliverable expansion
function toggleDeliverableExpand(deliverableCode) {
  const expandIcon = document.getElementById(`expand-${deliverableCode}`);
  const componentRows = document.querySelectorAll(`.component-row-${deliverableCode}`);
  const taskRows = document.querySelectorAll(`.task-row-${deliverableCode}`);

  if (expandIcon.textContent === '▶') {
    expandIcon.textContent = '▼';
    componentRows.forEach(row => row.style.display = '');
    // Tasks remain hidden until component is expanded
  } else {
    expandIcon.textContent = '▶';
    componentRows.forEach(row => row.style.display = 'none');
    // Reset all component expand icons
    componentRows.forEach(row => {
      const compButton = row.querySelector('span[id^="expand-comp-"]');
      if (compButton) compButton.textContent = '▶';
    });
  }
}

// Update deliverable type (PROJECT/RETAINER)
function updateDeliverableType(deliverableCode, type) {
  pricingData.deliverableTypes.set(deliverableCode, type);

  // If switching to retainer, set default months
  if (type === 'RETAINER') {
    if (!pricingData.retainerMonths.has(deliverableCode)) {
      pricingData.retainerMonths.set(deliverableCode, 12); // Default 12 months
    }
  }

  updatePricingTable();
  updatePricingSummary();
}

// Update custom hours
function updateCustomHours(deliverableCode, hours) {
  const numHours = parseFloat(hours) || 0;
  pricingData.customHours.set(deliverableCode, numHours);
  updatePricingCalculations();
}

// Update custom rate
function updateCustomRate(deliverableCode, rate) {
  const numRate = parseFloat(rate) || 195;
  pricingData.customRates.set(deliverableCode, numRate);
  updatePricingCalculations();
}

// AI analyze PROJECT vs RETAINER with AI - BATCH ENDPOINT (Brad build format)
async function analyzeProjectRetainer() {
  // Check for scenario first
  if (!window.currentScenario && (!SCENARIOS || !SCENARIOS.A)) {
    alert('Please build a scenario first (click Build Scenario button).');
    return;
  }

  const btn = document.getElementById('btn-ai-suggest-type');
  if (btn) {
    btn.disabled = true;
    btn.textContent = '🔄 Analyzing...';
  }

  try {
    // Get scenario and RFP text
    const scenario = window.currentScenario || SCENARIOS.A;
    const rfpText = window.APB?.step2?.rfpText || sessionStorage.getItem('rfpText') || '';

    // Build deliverables array from scenario items
    const deliverables = scenario.items.map(item => ({
      code: item.deliverable_code,
      name: item.deliverable_name || item.deliverable || item.deliverable_code
    }));

    console.log('[AI RETAINER] Calling batch endpoint with', deliverables.length, 'deliverables');

    // Call Brad build batch endpoint
    const response = await fetch('/api/ai/analyze_project_retainer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.JSON.stringify({
        rfp_text: rfpText,
        deliverables: deliverables
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Analysis failed: ${errorText}`);
    }

    const result = await response.json();
    console.log('[AI RETAINER] Received suggestions:', result);

    // Apply suggestions to scenario items
    if (result.suggestions) {
      let updatedCount = 0;
      scenario.items.forEach(item => {
        const suggestion = result.suggestions[item.deliverable_code];
        if (suggestion) {
          // Update item based on suggestion
          item.is_retainer = (suggestion.type === 'RETAINER');
          item.retainer_months = (suggestion.type === 'RETAINER') ? 12 : 0;
          item.pricing_type = suggestion.type;
          item.ai_confidence = suggestion.confidence;
          item.ai_reasoning = suggestion.reasoning;
          updatedCount++;
        }
      });

      // Store updated scenario
      window.currentScenario = scenario;
      window.SCENARIOS = { A: scenario };

      // Update pricing table display
      if (typeof updatePricingTable === 'function') {
        updatePricingTable();
      }

      // Re-render scenario
      if (window.renderScenario) {
        window.renderScenario('scenarioA', scenario);
      }

      alert(`✅ AI Retainer Analysis Complete!\n\n${updatedCount} deliverables classified as PROJECT or RETAINER.`);
    } else {
      throw new Error('No suggestions returned from API');
    }
  } catch (error) {
    console.error('[AI RETAINER] Error:', error);
    alert(`❌ Retainer Analysis Error:\n\n${error.message || 'Failed to analyze deliverables. Please try again.'}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = '🤖 AI Suggest Type';
    }
  }
}

// Update Pricing Function - saves all changes and recalculates
async function updatePricing() {
  if (!SCENARIOS || !SCENARIOS.A) {
    alert('No scenario to update. Please build a scenario first.');
    return;
  }

  const btn = document.getElementById('btn-update-pricing');
  if (btn) {
    btn.disabled = true;
    btn.textContent = '🔄 Updating...';
  }

  try {
    // Recalculate all totals
    updatePricingCalculations();

    // Save to scenario
    const scenario = SCENARIOS.A;
    scenario.items.forEach(item => {
      const delivType = pricingData.deliverableTypes.get(item.deliverable_code) || 'PROJECT';
      const customHours = pricingData.customHours.get(item.deliverable_code);
      const customRate = pricingData.customRates.get(item.deliverable_code);

      if (customHours !== undefined) item.hours = customHours;
      if (customRate !== undefined) item.blended_rate = customRate;
      item.price = (item.hours || 0) * (item.blended_rate || 195);
      item.is_retainer = (delivType === 'RETAINER');

      // Update components
      if (item.components) {
        item.components.forEach(comp => {
          const compKey = `${item.deliverable_code}::${comp.name}`;
          const compHours = pricingData.customHours.get(compKey);
          const compRate = pricingData.customRates.get(compKey);
          if (compHours !== undefined) comp.hours = compHours;
          if (compRate !== undefined) comp.rate = compRate;
          comp.price = (comp.hours || 0) * (comp.rate || item.blended_rate || 195);
        });
      }
    });

    // Update displays
    updatePricingTable();
    updatePricingSummary();

    // Show success message
    const oneTimeCount = document.getElementById('one-time-count')?.textContent || '0';
    const retainerCount = document.getElementById('retainer-count')?.textContent || '0';
    const grandTotal = document.getElementById('grand-total-cost')?.textContent || '$0';

    alert(`✅ Pricing Updated Successfully!\n\n` +
          `📦 One-Time Items: ${oneTimeCount}\n` +
          `🔄 Retainer Items: ${retainerCount}\n` +
          `💰 Grand Total: ${grandTotal}`);

  } catch (error) {
    console.error('Error updating pricing:', error);
    alert('Error updating pricing. Please try again.');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = '💾 Update Pricing';
    }
  }
}

// Re-build scenario with current pricing settings
async function rebuildScenario() {
  if (!window.ScenarioManager) {
    alert('ScenarioManager not available. Please ensure the unified pricing system is loaded.');
    return;
  }

  const btn = document.getElementById('btn-rebuild-scenario') || 
            document.querySelector('button[onclick*="rebuildScenario"]');

  if (btn) {
    btn.disabled = true;
    btn.textContent = '🔄 Saving...';
  }

  try {
    // Simply save the current scenario state via ScenarioManager
    await ScenarioManager.save();
    console.log('[REBUILD] Scenario saved successfully via ScenarioManager');

    // Trigger scenarios:updated event to refresh UI
    window.dispatchEvent(new Event('scenarios:updated'));

  } catch (error) {
    console.error('Error saving scenario:', error);
    alert('Error saving scenario. Please try again.');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = '🔄 Re-build Scenario';
    }
  }
}

// Show scenario comparison modal
function showScenarioComparison(original, rebuilt) {
  // Calculate totals for each version
  let originalGrandTotal = 0;
  let rebuiltGrandTotal = 0;
  let originalBreakdown = {
    oneTime: 0,
    monthly: 0,
    quarterly: 0,
    semiAnnual: 0
  };
  let rebuiltBreakdown = {
    oneTime: 0,
    monthly: 0,
    quarterly: 0,
    semiAnnual: 0
  };

  // Calculate original totals
  original.items.forEach(item => {
    const cadenceType = pricingDataEnhanced.cadenceTypes.get(item.deliverable_code) || 
                       (pricingData.deliverableTypes.get(item.deliverable_code) === 'RETAINER' ? 'MONTHLY' : 'ONE_TIME');
    const periods = pricingDataEnhanced.periodsCount.get(item.deliverable_code) || 
                   (cadenceType === 'MONTHLY' ? 12 : cadenceType === 'QUARTERLY' ? 4 : cadenceType === 'SEMI_ANNUAL' ? 2 : 1);
    const price = item.price || (item.hours * (item.blended_rate || 195));
    const totalPrice = price * periods;

    originalGrandTotal += totalPrice;

    if (cadenceType === 'ONE_TIME') originalBreakdown.oneTime += totalPrice;
    else if (cadenceType === 'MONTHLY') originalBreakdown.monthly += price;
    else if (cadenceType === 'QUARTERLY') originalBreakdown.quarterly += price;
    else if (cadenceType === 'SEMI_ANNUAL') originalBreakdown.semiAnnual += price;

    // Add components
    if (item.components) {
      item.components.forEach(comp => {
        const compKey = `${item.deliverable_code}::${comp.name}`;
        const compCadence = pricingDataEnhanced.cadenceTypes.get(compKey) || cadenceType;
        const compPeriods = pricingDataEnhanced.periodsCount.get(compKey) || periods;
        const compPrice = comp.price || (comp.hours * (comp.rate || item.blended_rate || 195));
        const compTotalPrice = compPrice * compPeriods;

        originalGrandTotal += compTotalPrice;

        if (compCadence === 'ONE_TIME') originalBreakdown.oneTime += compTotalPrice;
        else if (compCadence === 'MONTHLY') originalBreakdown.monthly += compPrice;
        else if (compCadence === 'QUARTERLY') originalBreakdown.quarterly += compPrice;
        else if (compCadence === 'SEMI_ANNUAL') originalBreakdown.semiAnnual += compPrice;
      });
    }
  });

  // Calculate rebuilt totals
  rebuilt.items.forEach(item => {
    const cadenceType = pricingDataEnhanced.cadenceTypes.get(item.deliverable_code) || 
                       (item.is_retainer ? 'MONTHLY' : 'ONE_TIME');
    const periods = pricingDataEnhanced.periodsCount.get(item.deliverable_code) || 
                   item.retainer_months || 
                   (cadenceType === 'MONTHLY' ? 12 : cadenceType === 'QUARTERLY' ? 4 : cadenceType === 'SEMI_ANNUAL' ? 2 : 1);
    const price = item.price;
    const totalPrice = price * periods;

    rebuiltGrandTotal += totalPrice;

    if (cadenceType === 'ONE_TIME') rebuiltBreakdown.oneTime += totalPrice;
    else if (cadenceType === 'MONTHLY') rebuiltBreakdown.monthly += price;
    else if (cadenceType === 'QUARTERLY') rebuiltBreakdown.quarterly += price;
    else if (cadenceType === 'SEMI_ANNUAL') rebuiltBreakdown.semiAnnual += price;

    // Add components
    if (item.components) {
      item.components.forEach(comp => {
        const compKey = `${item.deliverable_code}::${comp.name}`;
        const compCadence = pricingDataEnhanced.cadenceTypes.get(compKey) || cadenceType;
        const compPeriods = pricingDataEnhanced.periodsCount.get(compKey) || 
                          comp.retainer_months || periods;
        const compPrice = comp.price;
        const compTotalPrice = compPrice * compPeriods;

        rebuiltGrandTotal += compTotalPrice;

        if (compCadence === 'ONE_TIME') rebuiltBreakdown.oneTime += compTotalPrice;
        else if (compCadence === 'MONTHLY') rebuiltBreakdown.monthly += compPrice;
        else if (compCadence === 'QUARTERLY') rebuiltBreakdown.quarterly += compPrice;
        else if (compCadence === 'SEMI_ANNUAL') rebuiltBreakdown.semiAnnual += compPrice;
      });
    }
  });

  const difference = rebuiltGrandTotal - originalGrandTotal;
  const percentChange = originalGrandTotal > 0 ? ((difference / originalGrandTotal) * 100).toFixed(1) : '0.0';

  // Create comparison modal
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
    background: rgba(0,0,0,0.8); z-index: 1000;
    display: flex; align-items: center; justify-content: center;
  `;

  modal.innerHTML = `
    <div style="background: var(--card); border: 1px solid var(--accent); border-radius: 12px; 
                padding: 24px; width: 90%; max-width: 700px; max-height: 80vh; overflow-y: auto;">
      <h3 style="margin: 0 0 20px; color: var(--accent);">📊 Scenario Comparison</h3>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
        <div style="padding: 16px; background: rgba(255,255,255,0.05); border-radius: 8px;">
          <h4 style="margin: 0 0 12px; color: var(--muted);">Version 1 (Original)</h4>
          <div style="font-size: 0.9em;">
            ${originalBreakdown.oneTime > 0 ? `<div>One-Time: <strong>$${originalBreakdown.oneTime.toLocaleString()}</strong></div>` : ''}
            ${originalBreakdown.monthly > 0 ? `<div>Monthly (×12): <strong>$${(originalBreakdown.monthly * 12).toLocaleString()}</strong></div>` : ''}
            ${originalBreakdown.quarterly > 0 ? `<div>Quarterly (×4): <strong>$${(originalBreakdown.quarterly * 4).toLocaleString()}</strong></div>` : ''}
            ${originalBreakdown.semiAnnual > 0 ? `<div>Semi-Annual (×2): <strong>$${(originalBreakdown.semiAnnual * 2).toLocaleString()}</strong></div>` : ''}
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border);">
              <strong>Total: $${originalGrandTotal.toLocaleString()}</strong>
            </div>
          </div>
        </div>

        <div style="padding: 16px; background: rgba(139, 92, 246, 0.1); border-radius: 8px;">
          <h4 style="margin: 0 0 12px; color: var(--accent);">Version ${pricingData.rebuildVersion || 2} (Rebuilt)</h4>
          <div style="font-size: 0.9em;">
            ${rebuiltBreakdown.oneTime > 0 ? `<div>One-Time: <strong>$${rebuiltBreakdown.oneTime.toLocaleString()}</strong></div>` : ''}
            ${rebuiltBreakdown.monthly > 0 ? `<div>Monthly (×12): <strong>$${(rebuiltBreakdown.monthly * 12).toLocaleString()}</strong></div>` : ''}
            ${rebuiltBreakdown.quarterly > 0 ? `<div>Quarterly (×4): <strong>$${(rebuiltBreakdown.quarterly * 4).toLocaleString()}</strong></div>` : ''}
            ${rebuiltBreakdown.semiAnnual > 0 ? `<div>Semi-Annual (×2): <strong>$${(rebuiltBreakdown.semiAnnual * 2).toLocaleString()}</strong></div>` : ''}
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border);">
              <strong>Total: $${rebuiltGrandTotal.toLocaleString()}</strong>
            </div>
          </div>
        </div>
      </div>

      <div style="padding: 12px; background: ${difference > 0 ? 'rgba(220, 38, 38, 0.1)' : 'rgba(16, 185, 129, 0.1)'}; 
                  border-radius: 8px; text-align: center; margin-bottom: 20px;">
        <div style="font-size: 1.2em; font-weight: bold; color: ${difference > 0 ? '#fca5a5' : '#6ee7b7'};">
          ${difference > 0 ? '↑' : '↓'} ${Math.abs(difference).toLocaleString()} (${percentChange}%)
        </div>
        <div style="font-size: 0.9em; color: var(--muted); margin-top: 4px;">
          ${difference > 0 ? 'Increase from original' : 'Decrease from original'}
        </div>
      </div>

      <button onclick="this.parentElement.parentElement.remove()" 
              style="width: 100%; padding: 10px; background: var(--accent); color: white; 
                     border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
        Close
      </button>
    </div>
  `;

  document.body.appendChild(modal);
}

// Helper function to extract deliverable tasks
function extractDeliverableTasks(item) {
  const tasks = [];

  // Extract from components
  if (item.components && Array.isArray(item.components)) {
    item.components.forEach(comp => {
      if (comp.tasks && Array.isArray(comp.tasks)) {
        comp.tasks.forEach(task => {
          if (task.name && !tasks.includes(task.name)) {
            tasks.push(task.name);
          }
        });
      }
    });
  }

  // Extract from included_task_groups
  if (item.included_task_groups && Array.isArray(item.included_task_groups)) {
    item.included_task_groups.forEach(tg => {
      if (!tasks.includes(tg)) {
        tasks.push(tg);
      }
    });
  }

  return tasks.slice(0, 5); // Limit to 5 for display
}

// Helper function to format tasks list
function formatTasksList(tasks) {
  if (!tasks || tasks.length === 0) {
    return '<span style="color: var(--muted); font-style: italic;">No tasks</span>';
  }

  return tasks.map(task => 
    `<div style="padding: 1px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
      • ${task}
    </div>`
  ).join('');
}

// Functions for inline editing
function enableRowEdit(code) {
  pricingDataEnhanced.editMode.set(code, true);
  updatePricingTable();
}

function cancelRowEdit(code) {
  pricingDataEnhanced.editMode.set(code, false);
  updatePricingTable();
}

function saveRowEdit(code) {
  // Get the edited values
  const hoursInput = document.getElementById(`hours-${code}`);
  const rateInput = document.getElementById(`rate-${code}`);
  const cadenceSelect = document.getElementById(`cadence-${code}`);
  const periodsInput = document.getElementById(`periods-${code}`);

  if (hoursInput) {
    const hours = parseFloat(hoursInput.value) || 0;
    pricingData.customHours.set(code, hours);
  }

  if (rateInput) {
    const rate = parseFloat(rateInput.value) || 195;
    pricingData.customRates.set(code, rate);
  }

  if (cadenceSelect) {
    const cadence = cadenceSelect.value;
    pricingDataEnhanced.cadenceTypes.set(code, cadence);

    // Update deliverable type based on cadence
    if (cadence === 'ONE_TIME') {
      pricingData.deliverableTypes.set(code, 'PROJECT');
    } else {
      pricingData.deliverableTypes.set(code, 'RETAINER');
    }
  }

  if (periodsInput) {
    const periods = parseInt(periodsInput.value) || 1;
    pricingDataEnhanced.periodsCount.set(code, Math.max(1, Math.min(36, periods)));

    // Store retainer months if it's a retainer
    if (pricingData.deliverableTypes.get(code) === 'RETAINER') {
      pricingData.retainers.set(code, pricingDataEnhanced.periodsCount.get(code));
    }
  }

  // Update scenario items with new values
  if (SCENARIOS && SCENARIOS.A) {
    SCENARIOS.A.items.forEach(item => {
      if (item.deliverable_code === code) {
        const hours = pricingData.customHours.get(code);
        const rate = pricingData.customRates.get(code);
        if (hours !== undefined) item.hours = hours;
        if (rate !== undefined) item.blended_rate = rate;
        item.price = (item.hours || 0) * (item.blended_rate || 195);

        // Update retainer status
        const cadence = pricingDataEnhanced.cadenceTypes.get(code);
        item.is_retainer = (cadence !== 'ONE_TIME');
        if (item.is_retainer) {
          item.retainer_months = pricingDataEnhanced.periodsCount.get(code) || 12;
        }
      }

      // Update components
      if (item.components) {
        item.components.forEach(comp => {
          const compKey = `${item.deliverable_code}::${comp.name}`;
          if (compKey === code) {
            const compHours = pricingData.customHours.get(compKey);
            const compRate = pricingData.customRates.get(compKey);
            if (compHours !== undefined) comp.hours = compHours;
            if (compRate !== undefined) comp.rate = compRate;
            comp.price = (comp.hours || 0) * (comp.rate || item.blended_rate || 195);
          }
        });
      }
    });
  }

  // Exit edit mode
  pricingDataEnhanced.editMode.set(code, false);

  // Update the table
  updatePricingTable();
}

// Toggle expand/collapse for deliverable components
function toggleDeliverableExpand(deliverableCode) {
  const expandIcon = document.getElementById(`expand-${deliverableCode}`);
  const componentRows = document.querySelectorAll(`.component-row-${deliverableCode}`);

  if (expandIcon && componentRows.length > 0) {
    const isExpanded = expandIcon.style.transform === 'rotate(90deg)';

    if (isExpanded) {
      // Collapse
      expandIcon.style.transform = 'rotate(0deg)';
      componentRows.forEach(row => {
        row.style.display = 'none';
      });
    } else {
      // Expand
      expandIcon.style.transform = 'rotate(90deg)';
      componentRows.forEach(row => {
        row.style.display = 'table-row';
      });
    }
  }
}

function updateCadenceType(code, cadence) {
  pricingDataEnhanced.cadenceTypes.set(code, cadence);

  // Set default periods based on cadence
  if (cadence === 'MONTHLY') {
    pricingDataEnhanced.periodsCount.set(code, 12);
  } else if (cadence === 'QUARTERLY') {
    pricingDataEnhanced.periodsCount.set(code, 4);
  } else if (cadence === 'SEMI_ANNUAL') {
    pricingDataEnhanced.periodsCount.set(code, 2);
  } else {
    pricingDataEnhanced.periodsCount.set(code, 1);
  }

  // If in edit mode, update the display
  if (pricingDataEnhanced.editMode.get(code)) {
    const periodsInput = document.getElementById(`periods-${code}`);
    if (periodsInput) {
      periodsInput.value = pricingDataEnhanced.periodsCount.get(code);
    }
  }
}

function updatePeriods(code, periods) {
  const periodsNum = parseInt(periods) || 1;
  pricingDataEnhanced.periodsCount.set(code, Math.max(1, Math.min(36, periodsNum)));
}

// AI Optimize All Pricing Function - Calls Brad build redistribute-hours per deliverable
async function optimizeAllPricing() {
  const btn = document.getElementById('btn-ai-optimize-pricing');
  if (!btn) return;

  // Check for scenario
  if (!window.currentScenario && (!SCENARIOS || !SCENARIOS.A)) {
    alert('Please build a scenario first before optimizing pricing.');
    return;
  }

  // Show loading state
  btn.disabled = true;
  btn.textContent = '🔄 Optimizing...';

  try {
    const scenario = window.currentScenario || SCENARIOS.A;

    // Group items by deliverable code
    const deliverableMap = new Map();
    scenario.items.forEach(item => {
      const code = item.deliverable_code;
      if (!deliverableMap.has(code)) {
        deliverableMap.set(code, {
          code: code,
          name: item.deliverable_name || item.deliverable || code,
          total_hours: 0,
          components: []
        });
      }
      const deliv = deliverableMap.get(code);
      deliv.total_hours += (item.total_hours || item.hours || 0);

      // Track components
      const compName = item.component_name || item.component || '';
      if (compName) {
        const existing = deliv.components.find(c => c.name === compName);
        if (existing) {
          existing.hours += (item.total_hours || item.hours || 0);
        } else {
          deliv.components.push({
            name: compName,
            hours: (item.total_hours || item.hours || 0)
          });
        }
      }
    });

    console.log(`[OPTIMIZE] Processing ${deliverableMap.size} deliverables`);

    // Call redistribute-hours for each deliverable
    const optimizationResults = [];
    for (const [code, deliv] of deliverableMap.entries()) {
      try {
        const response = await fetch('/api/pricing/redistribute-hours', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.JSON.stringify({
            deliverable_code: code,
            deliverable_name: deliv.name,
            new_total_hours: deliv.total_hours,
            components: deliv.components
          })
        });

        if (response.ok) {
          const result = await response.json();
          optimizationResults.push({ code, result });
        } else {
          console.warn(`[OPTIMIZE] Failed for ${code}:`, await response.text());
        }
      } catch (err) {
        console.error(`[OPTIMIZE] Error for ${code}:`, err);
      }
    }

    // Apply optimization results back to scenario
    if (optimizationResults.length > 0) {
      optimizationResults.forEach(({ code, result }) => {
        if (result.suggested_distribution) {
          result.suggested_distribution.forEach(compSuggestion => {
            // Update items matching this deliverable + component
            scenario.items.forEach(item => {
              if (item.deliverable_code === code && 
                  (item.component_name || item.component) === compSuggestion.component) {
                item.total_hours = compSuggestion.hours;
                item.hours = compSuggestion.hours;
                // Recalculate price if needed
                const rate = item.rate || 195;
                item.price = Math.round(compSuggestion.hours * rate);
              }
            });
          });
        }
      });

      // Recompute totals
      let totalHours = 0;
      let totalPrice = 0;
      scenario.items.forEach(item => {
        totalHours += (item.total_hours || item.hours || 0);
        totalPrice += (item.price || 0);
      });

      if (!scenario.totals) scenario.totals = {};
      scenario.totals.hours = totalHours;
      scenario.totals.price = totalPrice;

      // Store updated scenario
      window.currentScenario = scenario;
      window.SCENARIOS = { A: scenario };

      // Update UI
      if (typeof updatePricingTable === 'function') {
        updatePricingTable();
      }
      if (window.renderScenario) {
        window.renderScenario('scenarioA', scenario);
      }

      alert(`✅ Pricing Optimized!\n\n${optimizationResults.length} deliverables redistributed using AI.`);
    } else {
      alert('⚠️ No optimization results. Please try again.');
    }

  } catch (error) {
    console.error('[OPTIMIZE] Error:', error);
    alert(`❌ Optimization Error:\n\n${error.message || 'Failed to optimize pricing. Please try again.'}`);
  } finally {
    // Reset button state
    btn.disabled = false;
    btn.textContent = 'Optimize All Pricing';
  }
}

// Smart optimization fallback
function performSmartOptimization(scenario, clientBudget) {
  if (!clientBudget || clientBudget <= 0) {
    alert('Please enter a client budget for optimization');
    return;
  }

  const currentTotal = scenario.totals.price;
  const scaleFactor = clientBudget / currentTotal;

  // Apply scaling to all items
  scenario.items.forEach(item => {
    // Scale hours and price proportionally
    const originalHours = item.total_hours;
    const originalPrice = item.price;

    item.total_hours = Math.round(originalHours * scaleFactor);
    item.price = Math.round(originalPrice * scaleFactor);

    // Maintain effective rate
    if (item.total_hours > 0) {
      item.effective_rate = item.price / item.total_hours;
    }
  });

  // Update totals
  scenario.totals.hours = scenario.items.reduce((sum, item) => sum + item.total_hours, 0);
  scenario.totals.price = scenario.items.reduce((sum, item) => sum + item.price, 0);

  // Re-render scenario
  if (window.renderScenario) {
    window.renderScenario('scenarioA', scenario);
  }

  // Show results
  let message = '✅ Pricing Optimized!\n\n';
  if (scaleFactor < 1) {
    const reduction = ((1 - scaleFactor) * 100).toFixed(1);
    message += `📉 Reduced all deliverables by ${reduction}% to fit within budget\n`;
    message += `💰 New Total: ${window.fmtUSD0 ? window.fmtUSD0(scenario.totals.price) : '$' + scenario.totals.price.toLocaleString()}`;
  } else if (scaleFactor > 1.2) {
    const increase = ((scaleFactor - 1) * 100).toFixed(1);
    message += `📈 Increased all deliverables by ${increase}% to maximize budget utilization\n`;
    message += `💰 New Total: ${window.fmtUSD0 ? window.fmtUSD0(scenario.totals.price) : '$' + scenario.totals.price.toLocaleString()}`;
  } else {
    message += `✨ Pricing is already optimized for the budget`;
  }

  alert(message);
}

// Show optimization success message
function showOptimizationSuccess(result, clientBudget) {
  let message = '🎯 AI Pricing Optimization Complete!\n\n';

  if (result.method === 'gpt5') {
    message += '🧠 Powered by GPT-5 Intelligence\n';
  }

  if (result.summary) {
    message += `📊 ${result.summary}\n`;
  }

  if (result.total_hours && result.total_price) {
    message += `\n💼 Optimized Totals:\n`;
    message += `• Hours: ${result.total_hours}\n`;
    message += `• Price: $${result.total_price.toLocaleString()}\n`;
  }

  if (clientBudget && result.total_price) {
    const variance = ((result.total_price - clientBudget) / clientBudget * 100).toFixed(1);
    if (Math.abs(variance) < 5) {
      message += `✅ Within 5% of budget target\n`;
    } else if (variance < 0) {
      message += `📉 ${Math.abs(variance)}% under budget\n`;
    } else {
      message += `📈 ${variance}% over budget\n`;
    }
  }

  if (result.adjustments && result.adjustments.length > 0) {
    message += `\n🔧 Key Adjustments:\n`;
    result.adjustments.slice(0, 3).forEach(adj => {
      message += `• ${adj}\n`;
    });
  }

  alert(message);
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

  // FIX: Wire Excel/CSV export button - Call POST /api/export with scenario + file_format
  try {
    // Get the scenario (default to A)
    const scenario = SCENARIOS?.A;
    if (!scenario) {
      alert('Please build a scenario first before exporting');
      return;
    }

    // Get export format from dropdown
    const formatSelect = document.getElementById('export-format');
    const fileFormat = formatSelect?.value || 'xlsx';

    // Call export endpoint with scenario and format
    const response = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.JSON.stringify({
        scenario: scenario,
        file_format: fileFormat
      })
    });

    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = fileFormat === 'xlsx' ? 'xlsx' : 'csv';
      a.download = `${exportData.project_name}_pricing_${new Date().toISOString().split('T')[0]}.${ext}`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } else {
      const errorText = await response.text();
      console.error('Export failed:', errorText);
      alert('Failed to export pricing details. Please try again.');
    }
  } catch (error) {
    console.error('Error exporting pricing details:', error);
    alert('Error exporting pricing details. Please try again.');
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
window.toggleDeliverableExpand = toggleDeliverableExpand;
window.updateDeliverableType = updateDeliverableType;
window.updateCustomHours = updateCustomHours;
window.updateCustomRate = updateCustomRate;
window.analyzeProjectRetainer = analyzeProjectRetainer;
window.rebuildScenario = rebuildScenario;
window.enableRowEdit = enableRowEdit;
window.cancelRowEdit = cancelRowEdit;
window.saveRowEdit = saveRowEdit;
window.updateCadenceType = updateCadenceType;
window.updatePeriods = updatePeriods;
window.extractDeliverableTasks = extractDeliverableTasks;
window.formatTasksList = formatTasksList;

// Global timeline polling state for cancellation
let timelinePollingIntervalId = null;

// Export timeline error handling functions
window.generateAITimeline = generateAITimeline;
window.showUserFriendlyError = showUserFriendlyError;
window.cancelTimelineGeneration = cancelTimelineGeneration;

function cancelTimelineGeneration() {
  log('[TIMELINE] Cancelling timeline generation');

  // Clear polling interval if active
  if (timelinePollingIntervalId) {
    clearInterval(timelinePollingIntervalId);
    timelinePollingIntervalId = null;
  }

  // Hide progress UI
  const loading = document.getElementById('timeline-loading');
  if (loading) {
    loading.style.display = 'none';
  }

  // Reset button state
  const btn = document.getElementById('btn-generate-timeline');
  if (btn) {
    btn.disabled = false;
    btn.textContent = '🤖 Generate AI Timeline';
  }

  console.log('[TIMELINE] Timeline generation cancelled');
}

async function generateAITimeline(retryAttempt = 0) {
  const btn = document.getElementById('btn-generate-timeline');
  const loading = document.getElementById('timeline-loading');
  const container = document.getElementById('gantt-container');

  if (!btn || !loading || !container) return;

  // Get selected deliverables from Step 2
  const selectedCodes = readSelectedCodesFromUI();
  if (selectedCodes.length === 0) {
    showUserFriendlyError('No deliverables selected', 'Please select at least one deliverable in Step 2 before generating a timeline.');
    return;
  }

  const deliverableCount = selectedCodes.length;

  // Polling configuration
  const POLLING_INTERVAL_MS = 2500; // Poll every 2.5 seconds
  const MAX_POLLING_TIME_MS = 600000; // 10 minutes timeout

  // Polling state (using global variable for cancellation support)
  let pollingStartTime = Date.now();

  // Show loading state with progress UI
  btn.disabled = true;
  btn.textContent = retryAttempt > 0 ? `Retrying... (Attempt ${retryAttempt + 1}/3)` : 'Starting...';

  // Create comprehensive progress UI with error display area
  const progressHTML = `
    <div id="timeline-progress-container" style="padding: 20px; background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.1)); border: 1px solid rgba(139, 92, 246, 0.2); border-radius: 8px; margin-bottom: 20px;">
      <h3 style="margin: 0 0 12px 0; color: #6366f1;">🚀 Generating AI Timeline</h3>
      ${deliverableCount > 20 ? `<div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.2); padding: 10px; border-radius: 4px; margin-bottom: 12px;">
        <p style="margin: 0; color: #16a34a; font-size: 0.9em;">
          📋 Large project detected (${deliverableCount} deliverables). This may take several minutes. You can continue working while we generate your timeline.
        </p>
      </div>` : deliverableCount > 10 ? `<div style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2); padding: 10px; border-radius: 4px; margin-bottom: 12px;">
        <p style="margin: 0; color: #2563eb; font-size: 0.9em;">
          ℹ️ Processing ${deliverableCount} deliverables. We're optimizing your timeline with AI.
        </p>
      </div>` : ''}
      <div id="timeline-progress-content">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <strong id="timeline-progress-stage" style="color: #6366f1;">Initializing...</strong>
          <span id="timeline-progress-percentage" style="font-weight: 600; color: #6366f1;">0%</span>
        </div>
        <div style="width: 100%; height: 8px; background: rgba(0,0,0,0.1); border-radius: 4px; overflow: hidden;">
          <div id="timeline-progress-bar" style="height: 100%; width: 0%; background: linear-gradient(90deg, #667eea, #764ba2); transition: width 0.3s ease;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 8px;">
          <small id="timeline-progress-message" style="color: var(--muted);">Preparing timeline generation...</small>
          <small id="timeline-progress-deliverables" style="color: var(--muted); display: none;"></small>
        </div>
        <div id="timeline-progress-details" style="margin-top: 12px; padding: 12px; background: rgba(0,0,0,0.05); border-radius: 6px; display: none;">
          <div style="font-size: 0.85em; color: var(--muted);">
            <span id="timeline-progress-items"></span>
          </div>
        </div>
      </div>
      <div id="timeline-error-container" style="display: none; margin-top: 16px;">
        <div style="background: #fee2e2; border: 1px solid #fecaca; border-radius: 6px; padding: 16px;">
          <div style="display: flex; align-items: start; gap: 12px;">
            <span style="color: #dc2626; font-size: 1.5em;">⚠️</span>
            <div style="flex: 1;">
              <h4 id="timeline-error-title" style="margin: 0 0 8px 0; color: #dc2626;">Timeline Generation Failed</h4>
              <p id="timeline-error-message" style="margin: 0 0 12px 0; color: #7f1d1d;">Something went wrong while generating the timeline.</p>
              <div style="display: flex; gap: 10px;">
                <button id="btn-retry-timeline" onclick="generateAITimeline(${retryAttempt + 1})" style="padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">
                  🔄 Try Again
                </button>
                <button id="btn-cancel-timeline" onclick="cancelTimelineGeneration()" style="padding: 8px 16px; background: #6b7280; color: white; border: none; border-radius: 4px; cursor: pointer;">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  loading.innerHTML = progressHTML;
  loading.style.display = 'block';
  container.style.display = 'none';

  // Helper function to show error in the UI
  const showTimelineError = (title, message, canRetry = true) => {
    const errorContainer = document.getElementById('timeline-error-container');
    const errorTitle = document.getElementById('timeline-error-title');
    const errorMessage = document.getElementById('timeline-error-message');
    const progressContent = document.getElementById('timeline-progress-content');

    if (errorContainer && errorTitle && errorMessage) {
      errorTitle.textContent = title;
      errorMessage.textContent = message;
      errorContainer.style.display = 'block';

      // Hide progress UI when showing error
      if (progressContent) {
        progressContent.style.display = 'none';
      }

      // Update retry button visibility and attempts left
      const retryBtn = document.getElementById('btn-retry-timeline');
      if (retryBtn) {
        const attemptsLeft = 3 - retryAttempt;
        retryBtn.style.display = (canRetry && attemptsLeft > 0) ? 'inline-block' : 'none';
        if (canRetry && attemptsLeft > 0) {
          retryBtn.textContent = `🔄 Try Again (${attemptsLeft} attempts left)`;
        }
      }
    }

    // Re-enable main button
    btn.disabled = false;
    btn.textContent = '🤖 Generate AI Timeline';
  };

  // Clean up function
  const cleanup = () => {
    if (timelinePollingIntervalId) {
      clearInterval(timelinePollingIntervalId);
      timelinePollingIntervalId = null;
    }
  };

  // Polling function for job status
  const startPolling = async () => {
    if (!jobId) {
      console.error('[TIMELINE] Cannot start polling: no job ID');
      return;
    }

    console.log('[TIMELINE] Starting polling for job:', jobId);

    const pollJobStatus = async () => {
      if (!jobId) return;

      // Check for timeout
      const elapsed = Date.now() - pollingStartTime;
      if (elapsed > MAX_POLLING_TIME_MS) {
        cleanup();
        showTimelineError(
          'Timeline Generation Timeout',
          'Timeline generation took longer than expected (10 minutes). This usually happens with very large projects. Please try with fewer deliverables or contact support.',
          true
        );
        return;
      }

      try {
        const response = await fetch(`/api/agencydb/status/${jobId}`);

        if (!response.ok) {
          if (response.status === 404) {
            // Job not found - might have been cleaned up
            console.error('[TIMELINE] Job not found:', jobId);
            cleanup();
            showTimelineError(
              'Job Not Found',
              'The timeline generation job could not be found. It may have been cancelled or expired. Please try again.',
              true
            );
            return;
          }
          throw new Error(`Status check failed: ${response.status}`);
        }

        const data = await response.json();

        console.log('[TIMELINE] Poll update:', {
          status: data.status,
          progress: data.progress,
          stage: data.current_stage
        });

        // Update UI with polling data
        updateProgressUI(data);

        // Check if job is complete
        if (data.status === 'completed') {
          cleanup();

          // Extract result from either 'data' or 'result' field
          const result = data.data || data.result;
          if (result) {
            handleTimelineCompletion(result);
          } else {
            showTimelineError(
              'Invalid Response',
              'Timeline generation completed but no data was returned. Please try again.',
              true
            );
          }
        } else if (data.status === 'failed') {
          cleanup();
          handleTimelineError(data.error || 'Timeline generation failed');
        }
        // Otherwise continue polling (status is still "pending" or "processing")

      } catch (error) {
        console.error('[TIMELINE] Polling error:', error);

        // For network errors, continue polling but log the issue
        // Only stop if we've been trying for too long
        const elapsedMinutes = Math.floor(elapsed / 60000);
        if (elapsedMinutes >= 10) {
          cleanup();
          showTimelineError(
            'Network Error',
            'Unable to check timeline status due to network issues. Please check your connection and try again.',
            true
          );
        }
        // Otherwise, continue polling - transient network issues should resolve
      }
    };

    // Start polling immediately
    await pollJobStatus();

    // Continue polling at intervals
    timelinePollingIntervalId = setInterval(pollJobStatus, POLLING_INTERVAL_MS);
  };

  // Helper function to update progress UI
  const updateProgressUI = (data) => {
    const progressBar = document.getElementById('timeline-progress-bar');
    const progressPercentage = document.getElementById('timeline-progress-percentage');
    const progressStage = document.getElementById('timeline-progress-stage');
    const progressMessage = document.getElementById('timeline-progress-message');
    const progressDeliverables = document.getElementById('timeline-progress-deliverables');
    const progressDetails = document.getElementById('timeline-progress-details');
    const progressItems = document.getElementById('timeline-progress-items');

    if (progressBar && data.progress !== undefined) {
      progressBar.style.width = `${data.progress}%`;
    }

    if (progressPercentage) {
      progressPercentage.textContent = `${Math.round(data.progress || 0)}%`;
    }

    // Map stage names to user-friendly messages
    const stageMessages = {
      'initialization': '⚙️ Initializing timeline generation...',
      'analyzing_deliverables': '📊 Analyzing deliverables...',
      'creating_dependencies': '🔗 Creating dependencies and workstreams...',
      'optimizing_schedule': '⚡ Optimizing schedule with AI...',
      'ai_reasoning': '🧠 Enhancing with AI reasoning...',
      'generating_timeline': '📅 Generating timeline...',
      'finalizing': '✨ Finalizing timeline...',
      'completed': '✅ Timeline generation complete!'
    };

    if (progressStage && data.current_stage) {
      progressStage.textContent = stageMessages[data.current_stage] || data.current_stage;
    }

    if (progressMessage && data.message) {
      progressMessage.textContent = data.message;
    }

    // Show deliverable progress for large sets
    if (data.processed_items !== undefined && data.total_items !== undefined) {
      if (progressDeliverables) {
        progressDeliverables.style.display = 'inline';
        progressDeliverables.textContent = `Processing deliverable ${data.processed_items} of ${data.total_items}`;
      }

      if (progressDetails && progressItems && data.total_items > 10) {
        progressDetails.style.display = 'block';
        const percentage = Math.round((data.processed_items / data.total_items) * 100);
        progressItems.textContent = `📊 Progress: ${data.processed_items}/${data.total_items} deliverables (${percentage}%)`;
      }
    }
  };

  // Helper function to handle timeline completion
  const handleTimelineCompletion = (result) => {
    currentTimelineTasks = result.tasks || [];
    timelineReasoning = result.reasoning || {};

    // Update reasoning panel
    updateReasoningPanel(result.reasoning);

    // Auto-show the reasoning panel when timeline is generated
    const panel = document.getElementById('ai-reasoning-panel');
    if (panel) {
      panel.style.display = 'block';
    }

    // Update metadata
    updateTimelineMetadata(result.metadata);

    // Update resource risk table
    updateResourceRiskTable(currentTimelineTasks, result.reasoning);

    // Initialize Gantt chart with AI-generated timeline
    initializeGanttChart(currentTimelineTasks).then(() => {
      // Show the container
      container.style.display = '';

      // Show metadata
      const metadataDiv = document.getElementById('timeline-metadata');
      if (metadataDiv) metadataDiv.style.display = '';

      // Hide loading
      loading.style.display = 'none';
      btn.disabled = false;
      btn.textContent = '🤖 Generate AI Timeline';
    }).catch(chartError => {
      console.error('Failed to initialize Gantt chart:', chartError);
      showTimelineError(
        'Display Error',
        'Timeline generated successfully but could not be displayed. Please refresh the page and try again.',
        true
      );
    });
  };

  // Helper function to handle timeline errors
  const handleTimelineError = (error) => {
    let errorMessage = 'Timeline generation failed. Please try again.';

    if (error) {
      const errorLower = error.toLowerCase();

      if (errorLower.includes('timeout')) {
        errorMessage = 'The request took too long. Please try with fewer deliverables.';
      } else if (errorLower.includes('memory') || errorLower.includes('resource')) {
        errorMessage = 'Too many deliverables selected. Please reduce your selection and try again.';
      } else if (errorLower.includes('invalid') || errorLower.includes('missing')) {
        errorMessage = 'Some selected deliverables have invalid data. Please review your selection.';
      } else if (errorLower.includes('api') || errorLower.includes('gpt') || errorLower.includes('openai')) {
        errorMessage = 'The AI service is temporarily unavailable. Please try again in a moment.';
      } else if (errorLower.includes('gateway timeout') || errorLower.includes('504')) {
        errorMessage = 'The request took too long. Try selecting fewer deliverables.';
      } else {
        // Use a simplified version of the error if it's not too technical
        errorMessage = error.length < 100 ? error : 'An unexpected error occurred. Please try again.';
      }
    }

    showTimelineError('Timeline Generation Failed', errorMessage, true);
  };

  try {
    // Get optimization mode
    const optimizationMode = document.getElementById('timeline-optimization')?.value || 'balanced';

    // Get project start date from Step 3
    const projectStart = document.getElementById('projectStart')?.value || null;

    // Get RFP text for context
    const rfpText = APB.step2?.rfpText || document.getElementById('rfpText')?.value || '';

    // ISSUE 3: Ensure timeline gets proper scenario items with actual count
    // First check if SCENARIOS exists in memory, if not, try to load from localStorage
    let SCENARIOS = window.SCENARIOS;

    if (!SCENARIOS) {
      console.log('[TIMELINE] No SCENARIOS in memory, checking localStorage...');

      // Try to load from localStorage with session ID
      const sessionId = window.APB?.sessionId || 
                       localStorage.getItem('current_session_id') || 
                       'default_session';
      const storageKey = `scenarios_${sessionId}`;

      try {
        const savedScenarios = localStorage.getItem(storageKey);
        if (savedScenarios) {
          SCENARIOS = JSON.parse(savedScenarios);
          window.SCENARIOS = SCENARIOS; // Restore to memory
          console.log('[TIMELINE] Loaded scenarios from localStorage with key:', storageKey);
        } else {
          // Try fallback key
          const fallbackScenarios = localStorage.getItem('latest_scenarios');
          if (fallbackScenarios) {
            SCENARIOS = JSON.parse(fallbackScenarios);
            window.SCENARIOS = SCENARIOS; // Restore to memory
            console.log('[TIMELINE] Loaded scenarios from localStorage fallback');
          }
        }
      } catch (err) {
        console.error('[TIMELINE] Failed to load scenarios from localStorage:', err);
      }
    }

    const scenario = SCENARIOS?.A;

    // Enhanced error diagnostics
    if (!SCENARIOS) {
      console.error('[TIMELINE] No SCENARIOS object found in memory or localStorage');
      alert('Error: No scenarios found. Please click "Build Scenario" in Step 3 first.');
      btn.disabled = false;
      btn.textContent = '🤖 Generate AI Timeline';
      loading.style.display = 'none';
      return;
    }

    if (!scenario) {
      console.error('[TIMELINE] SCENARIOS exists but no A scenario:', SCENARIOS);
      alert('Error: Scenario A not found. Please rebuild your scenario in Step 3.');
      btn.disabled = false;
      btn.textContent = '🤖 Generate AI Timeline';
      loading.style.display = 'none';
      return;
    }

    if (!scenario.items) {
      console.error('[TIMELINE] Scenario A exists but has no items:', scenario);
      alert('Error: Scenario has no deliverables list. Please select deliverables in Step 2 and rebuild.');
      btn.disabled = false;
      btn.textContent = '🤖 Generate AI Timeline';
      loading.style.display = 'none';
      return;
    }

    if (scenario.items.length === 0) {
      console.error('[TIMELINE] Scenario has empty items array:', scenario);
      alert('Error: No deliverables in scenario. Please select deliverables in Step 2 and rebuild.');
      btn.disabled = false;
      btn.textContent = '🤖 Generate AI Timeline';
      loading.style.display = 'none';
      return;
    }

    console.log('[TIMELINE] Scenario validation passed:', {
      scenarioExists: true,
      itemsCount: scenario.items.length,
      sampleItem: scenario.items[0]
    });

    // Use actual scenario items for timeline generation
    const deliverables = scenario.items.map(item => {
      return {
        deliverable_code: item.deliverable_code,
        name: item.deliverable || labelFor(item.deliverable_code),
        department: item.department || 'Strategy',
        hours: item.total_hours || 0,
        components: item.components || [],
        is_retainer: pricingData.retainers.has(item.deliverable_code),
        retainer_months: pricingData.retainers.get(item.deliverable_code) || 0
      };
    });

    console.log(`[TIMELINE] Generating timeline for ${deliverables.length} deliverables from Scenario A`);

    // Exponential backoff delay for retries
    if (retryAttempt > 0) {
      const delayMs = Math.min(1000 * Math.pow(2, retryAttempt - 1), 8000); // 1s, 2s, 4s, max 8s
      console.log(`[TIMELINE] Retry attempt ${retryAttempt + 1}/3 with ${delayMs}ms delay`);
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }

    // Call NEW SSE-enabled timeline endpoint with better error handling
    let response;
    try {
      response = await fetch('/api/ai/generate_timeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.JSON.stringify({
          deliverables: deliverables,
          rfp_text: rfpText,
          project_start: projectStart,
          optimization_mode: optimizationMode,
          use_intelligent_scheduler: true,
          retry_attempt: retryAttempt
        })
      });
    } catch (fetchError) {
      // Network error - couldn't reach the server
      cleanup();

      // Auto-retry for network errors with exponential backoff
      if (retryAttempt < 2) {
        console.log('[TIMELINE] Network error, auto-retrying...');
        setTimeout(() => generateAITimeline(retryAttempt + 1), 1000 * Math.pow(2, retryAttempt));
        return;
      }

      showTimelineError(
        'Connection Failed',
        `Unable to connect to the server after ${retryAttempt + 1} attempts. Please check your internet connection and try again.`,
        false // No more retries after 3 attempts
      );
      return;
    }

    if (!response.ok) {
      cleanup();

      // Handle specific HTTP errors with user-friendly messages
      let errorTitle = 'Timeline Generation Failed';
      let errorMessage = 'Something went wrong. Please try again.';
      let shouldRetry = true;

      if (response.status === 400) {
        // User error - don't auto-retry
        errorMessage = 'Invalid request. Please ensure you have selected valid deliverables and try again.';
        shouldRetry = false;
      } else if (response.status === 404) {
        errorMessage = 'The timeline generation service is currently unavailable. Please try again later.';
      } else if (response.status === 429) {
        errorMessage = `Too many requests. ${retryAttempt < 2 ? 'Retrying automatically...' : 'Please wait a moment before trying again.'}`;
        // Auto-retry for rate limiting
        if (retryAttempt < 2) {
          setTimeout(() => generateAITimeline(retryAttempt + 1), 2000 * Math.pow(2, retryAttempt));
          return;
        }
      } else if (response.status === 500 || response.status === 502 || response.status === 503) {
        errorMessage = `The server is experiencing issues. ${retryAttempt < 2 ? 'Retrying automatically...' : 'Please try again in a few moments.'}`;
        // Auto-retry for server errors
        if (retryAttempt < 2) {
          setTimeout(() => generateAITimeline(retryAttempt + 1), 1000 * Math.pow(2, retryAttempt));
          return;
        }
      } else if (response.status === 504) {
        errorMessage = 'The request took too long. Try selecting fewer deliverables.';
      }

      showTimelineError(errorTitle, errorMessage, shouldRetry && retryAttempt < 2);
      return;
    }

    let jobData;
    try {
      jobData = await response.json();
    } catch (parseError) {
      cleanup();
      showTimelineError(
        'Invalid Response',
        'Received an invalid response from the server. Please try again.',
        true
      );
      return;
    }

    if (!jobData.job_id) {
      cleanup();
      showTimelineError(
        'Generation Failed',
        'Could not start timeline generation. Please try again.',
        true
      );
      return;
    }

    // Store job ID and start polling
    jobId = jobData.job_id;
    console.log('[TIMELINE] Timeline generation started, job ID:', jobId);

    // Start polling for status updates
    await startPolling();

  } catch (error) {
    console.error('Error generating AI timeline:', error);
    cleanup();

    // Determine the error type and show appropriate message
    let errorTitle = 'Timeline Generation Failed';
    let errorMessage = 'Something went wrong. Please try again.';

    if (error.message) {
      const errorLower = error.message.toLowerCase();

      if (errorLower.includes('scenario')) {
        errorMessage = 'No pricing scenario found. Please complete Step 3 (Build Scenario) first.';
      } else if (errorLower.includes('deliverable')) {
        errorMessage = 'No deliverables selected. Please select at least one deliverable in Step 2.';
      } else if (errorLower.includes('network') || errorLower.includes('fetch')) {
        errorMessage = 'Network error. Please check your internet connection and try again.';
      } else {
        // Use a simplified version of the error if it's not too technical
        errorMessage = error.message.length < 100 ? error.message : 'An unexpected error occurred. Please try again.';
      }
    }

    showTimelineError(errorTitle, errorMessage, true);
  }
}

// Helper function to show user-friendly error messages
function showUserFriendlyError(title, message) {
  // Create a nice modal or alert with the error
  const modalHTML = `
    <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                background: white; padding: 24px; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); 
                z-index: 10000; max-width: 400px;">
      <h3 style="margin: 0 0 12px 0; color: #dc2626;">⚠️ ${title}</h3>
      <p style="margin: 0 0 16px 0; color: #4b5563;">${message}</p>
      <button onclick="this.parentElement.remove()" 
              style="padding: 8px 16px; background: #3b82f6; color: white; border: none; 
                     border-radius: 4px; cursor: pointer; font-weight: 600;">
        OK
      </button>
    </div>
    <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
                background: rgba(0,0,0,0.5); z-index: 9999;"
         onclick="this.remove(); this.previousElementSibling.remove()">
    </div>
  `;

  // Add to body
  document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// Helper: Show recoverable warning
function showRecoverableWarning(message) {
  console.warn('[BUILD] Showing warning:', message);

  let warningBanner = document.getElementById('transition-warning-banner');
  if (!warningBanner) {
    warningBanner = document.createElement('div');
    warningBanner.id = 'transition-warning-banner';
    warningBanner.style.cssText = `
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: linear-gradient(135deg, #ffc107, #ff9800);
      color: #000;
      padding: 12px 20px;
      border-radius: 6px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2);
      z-index: 9999;
      max-width: 400px;
      text-align: center;
      animation: slideUp 0.3s ease;
    `;
    document.body.appendChild(warningBanner);
  }

  warningBanner.innerHTML = `
    <div>ℹ️ ${message}</div>
  `;

  warningBanner.style.display = 'block';

  // Auto-hide after 5 seconds
  setTimeout(() => {
    if (warningBanner) warningBanner.style.display = 'none';
  }, 5000);
}

// Helper: Retry transition
window.retryTransition = function() {
  console.log('[BUILD] Retrying transition...');
  clearErrorState();
  buildFromCurrentSelection();
};

// ================================================================================
// Global Error Handler for Transition Issues
// ================================================================================
let transitionInProgress = false;
let lastTransitionError = null;

// Track when transition is happening
window.addEventListener('error', function(event) {
  if (transitionInProgress) {
    console.error('[GLOBAL ERROR] Error during transition:', event);
    lastTransitionError = event.error || event.message;

    // Log the error details
    console.error('[GLOBAL ERROR] Message:', event.message);
    console.error('[GLOBAL ERROR] File:', event.filename);
    console.error('[GLOBAL ERROR] Line:', event.lineno);
    console.error('[GLOBAL ERROR] Column:', event.colno);
    console.error('[GLOBAL ERROR] Stack:', event.error?.stack);

    // Try to recover and show Step 3 anyway
    const step3 = document.querySelector("#step3");
    if (step3 && step3.style.display === 'none') {
      console.warn('[GLOBAL ERROR] Attempting recovery - forcing Step 3 to show');
      step3.style.display = 'block';
      step3.style.visibility = 'visible';
      step3.style.opacity = '1';
      // No scrollIntoView here, let the user decide where to look

      // Show error message
      showUserFriendlyError('An error occurred during the transition. Some features may be limited.', true);
    }

    // Don't prevent default - let console show the error too
    return false;
  }
});

// Track unhandled promise rejections during transition
window.addEventListener('unhandledrejection', function(event) {
  if (transitionInProgress) {
    console.error('[GLOBAL PROMISE] Unhandled rejection during transition:', event);
    lastTransitionError = event.reason;

    // Try to recover and show Step 3 anyway
    const step3 = document.querySelector("#step3");
    if (step3 && step3.style.display === 'none') {
      console.warn('[GLOBAL PROMISE] Attempting recovery - forcing Step 3 to show');
      step3.style.display = 'block';
      step3.style.visibility = 'visible';
      step3.style.opacity = '1';
      step3.scrollIntoView({ behavior: 'smooth' });

      // Show error message
      showUserFriendlyError('An async error occurred. Some features may be limited.', true);
    }
  }
});

// Placeholder for buildFromCurrentSelection (referenced by retryTransition)
// TODO: Implement proper scenario rebuild logic
window.buildFromCurrentSelection = function() {
  console.warn('[BUILD] buildFromCurrentSelection not yet implemented - using fallback');
  // Fallback: just show Step 3
  const step3 = document.querySelector("#step3");
  if (step3) {
    step3.style.display = 'block';
    step3.scrollIntoView({ behavior: 'smooth' });
  }
};

// Debug helper: Get transition state
window.getTransitionDebugInfo = function() {
  const info = {
    transitionInProgress,
    lastTransitionError,
    step3Visible: document.querySelector("#step3")?.style.display !== 'none',
    scenariosLoaded: !!window.SCENARIOS,
    scenarioManagerLoaded: !!window.ScenarioManager,
    selectedCodes: window.selectedCodes || [],
    appState: window.APP_STATE,
    timestamp: new Date().toISOString()
  };

  console.table(info);
  return info;
};

// Debug helper: Force show Step 3
window.forceShowStep3 = function() {
  console.log('[DEBUG] Force showing Step 3...');
  const step3 = document.querySelector("#step3");
  if (step3) {
    step3.style.display = 'block';
    step3.style.visibility = 'visible';
    step3.style.opacity = '1';
    step3.scrollIntoView({ behavior: 'smooth' });
    console.log('[DEBUG] Step 3 forced to display');
  } else {
    console.error('[DEBUG] Step 3 element not found');
    createStep3Fallback();
  }
};

// Debug helper: Test transition with mock data
window.testTransition = function() {
  console.log('[DEBUG] Testing transition with mock data...');

  // Create mock selection
  window.selectedCodes = ['TEST_001', 'TEST_002'];

  // Create mock scenario
  window.SCENARIOS = {
    A: {
      items: [
        {
          deliverable_code: 'TEST_001',
          deliverable_name: 'Test Deliverable 1',
          category: 'Test',
          hours: 40,
          rate: 195,
          price: 7800
        },
        {
          deliverable_code: 'TEST_002',
          deliverable_name: 'Test Deliverable 2',
          category: 'Test',
          hours: 60,
          rate: 195,
          price: 11700
        }
      ],
      total: 19500
    }
  };

  // Force show Step 3
  window.forceShowStep3();

  console.log('[DEBUG] Test transition complete');
};

console.log('[GLOBAL] Error handlers and debug helpers installed');
console.log('[GLOBAL] Debug commands available:');
console.log('  - getTransitionDebugInfo() : Get current transition state');
console.log('  - forceShowStep3() : Force Step 3 to display');
console.log('  - testTransition() : Test transition with mock data');

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
          // REMOVED: localStorage.setItem('apb.rfpText.v1', progress.result_text);
          // Don't persist to localStorage to prevent data restoration issues
          console.log('[Image Analysis] Results stored in session only (not persisted)');
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

  // Use SSE instead of polling for real-time updates
  const eventSource = new EventSource(`/api/stream/${jobId}`);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      // Update progress UI with SSE data
      updateProgressUI({
        status: data.status || 'processing',
        percentage: Math.round(data.progress || 0),
        processed_images: data.processed_items || 0,
        total_images: data.total_items || 0,
        current_stage: data.current_stage,
        message: data.message || '',
        eta_seconds: data.eta_seconds
      });

      // Handle completion
      if (data.status === 'completed') {
        eventSource.close();
        hideProgressUI();
        currentJobId = null;
      }

      // Handle errors
      if (data.status === 'failed') {
        eventSource.close();
        console.error('Image processing failed:', data.error);
        hideProgressUI();
        currentJobId = null;
      }
    } catch (error) {
      console.error('Error parsing SSE data:', error);
    }
  };

  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    eventSource.close();

    // Fallback to polling if SSE fails
    if (!progressInterval) {
      progressInterval = setInterval(() => pollProgress(jobId), 500);
    }
  };

  // Store event source for cleanup
  window.currentEventSource = eventSource;
}

// AI Analysis Progress Tracking
let aiAnalysisJobId = null;
let aiAnalysisInterval = null;

// Clean up polling on page unload or visibility change
function cleanupPolling() {
  if (aiAnalysisInterval) {
    console.log('[POLLING] Cleaning up AI analysis polling interval');
    clearInterval(aiAnalysisInterval);
    aiAnalysisInterval = null;
  }
  if (progressInterval) {
    console.log('[POLLING] Cleaning up progress polling interval');
    clearInterval(progressInterval);
    progressInterval = null;
  }
  // Note: timelinePollingIntervalId is managed within generateAITimeline function scope
}

// Expose cleanup function globally
window.cleanupPolling = cleanupPolling;

// Stop polling when user leaves the page
window.addEventListener('beforeunload', cleanupPolling);

// Stop polling when page becomes hidden
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    cleanupPolling();
  }
});

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
            <strong id="ai-progress-stage" style="color: #6366f1;">Initializing AI Analysis...</strong>
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
  if (percentEl) percentEl.textContent = `${Math.round(status.progress || 0)}%`;
  if (stageEl) stageEl.textContent = status.current_stage || 'Processing...';
  if (elapsedEl) elapsedEl.textContent = `Elapsed: ${Math.round(status.elapsed_seconds || 0)}s`;
  if (etaEl) {
    if (status.eta_seconds != null && status.eta_seconds > 0) {
      etaEl.textContent = `ETA: ${Math.round(status.eta_seconds)}s`;
    } else {
      etaEl.textContent = 'Estimating...';
    }
  }
}

async function pollAIAnalysis(jobId) {
  log(`[POLLING] pollAIAnalysis called for job ${jobId}`);

  // Force allow polling every time
  if (window.GlobalPollingManager && window.GlobalPollingManager.isShuttingDown) {
    log('[POLLING] Overriding shutdown mode to allow critical polling');
    window.GlobalPollingManager.isShuttingDown = false;
  }

  log(`[POLLING] ⏰ pollAIAnalysis STARTED for job ${jobId} at ${new Date().toISOString()}`);

  try {
    log(`[POLLING] Checking status for job ${jobId}...`);
    const res = await fetch(`/api/ai/jobs/${jobId}`);

    // Handle 410 Gone (zombie job blocked) or 404 - STOP IMMEDIATELY
    if (res.status === 410 || res.status === 404) {
      const statusText = res.status === 410 ? 'expired and blocked' : 'not found';
      log(`[POLLING] Job ${jobId} ${statusText} (${res.status}), stopping polling permanently`);

      // Clear the interval immediately
      if (aiAnalysisInterval) {
        clearInterval(aiAnalysisInterval);
        aiAnalysisInterval = null;
      }

      // Clear the job ID from memory
      aiAnalysisJobId = null;

      // Hide progress bar
      hideAIProgressBar();

      // Clear job ID from specific localStorage keys only (avoid scanning all storage)
      try {
        const savedState = localStorage.getItem('charles_agent_state');
        if (savedState) {
          const state = JSON.parse(savedState);
          if (state && state.jobId === jobId) {
            state.jobId = null;
            state.jobIdTimestamp = null;
            // Also clear from stateHistory
            if (state.stateHistory && Array.isArray(state.stateHistory)) {
              state.stateHistory.forEach(historyState => {
                if (historyState.jobId === jobId) {
                  historyState.jobId = null;
                  historyState.jobIdTimestamp = null;
                }
              });
            }
            localStorage.setItem('charles_agent_state', JSON.JSON.stringify(state));
            log('[POLLING] Cleared job ID from charles_agent_state');
          }
        }
      } catch (e) {
        console.error('[POLLING] Failed to clear job from localStorage:', e);
      }

      // Show error message to user
      const errorMsg = res.status === 410 
        ? `Analysis job ${jobId} has expired. Please start a new analysis.`
        : `Analysis job ${jobId} not found. It may have expired or been deleted.`;
      console.error('[POLLING]', errorMsg);

      // Don't continue polling
      return;
    }

    if (!res.ok) {
      console.error(`[POLLING] Error fetching job status: ${res.status}`);
      return;
    }

    // Reset counter on successful response
    consecutive404Count = 0;

    const status = await res.json();
    log(`[POLLING] Job ${jobId} status:`, status);
    updateAIProgress(status);

    // Check for completion states (completed, complete, done, etc.)
    const isCompleted = status.status === 'completed' || 
                        status.status === 'complete' || 
                        status.status === 'done';

    const isFailed = status.status === 'failed' || 
                     status.status === 'error' || 
                     status.status === 'cancelled';

    // Handle completion - check for result OR if status is complete with 100% progress
    if (isCompleted) {
      console.log('[ANALYSIS] ✅ Job complete, advancing to Step 2', status);
      log('[POLLING] 🛑 Stopping AI analysis polling - job completed');

      // Clear all polling protection and intervals
      window.PROTECTED_AI_POLLING = false;

      if (aiAnalysisInterval) {
        clearInterval(aiAnalysisInterval);
        aiAnalysisInterval = null;
      }
      if (window.PROTECTED_AI_INTERVAL) {
        clearInterval(window.PROTECTED_AI_INTERVAL);
        window.PROTECTED_AI_INTERVAL = null;
      }

      hideAIProgressBar();

      // Handle completed analysis - result might be in status.result or status.data
      const aiPlanResponse = status.result || status.data || status;
      window.APP = window.APP || {};
      window.APP.aiPlan = aiPlanResponse;
      sessionStorage.setItem('apb:aiPlan', JSON.JSON.stringify(aiPlanResponse));

      // CRITICAL: Update PRIMARY_SCENARIO with deliverables from AI analysis
      log('[ANALYSIS DEBUG] AI Plan Response structure:', {
        hasDeliverables: !!aiPlanResponse.deliverables,
        hasPlan: !!aiPlanResponse.plan,
        hasSuggestionsByDept: !!(aiPlanResponse.plan && aiPlanResponse.plan.suggestions_by_department),
        responseKeys: Object.keys(aiPlanResponse),
        planKeys: aiPlanResponse.plan ? Object.keys(aiPlanResponse.plan) : []
      });

      if (window.PRIMARY_SCENARIO) {
        // Extract deliverables from response (may be nested in .plan or .deliverables or directly in response)
        let deliverables = [];

        // Try direct deliverables first
        if (aiPlanResponse.deliverables && Array.isArray(aiPlanResponse.deliverables)) {
          deliverables = aiPlanResponse.deliverables;
          log('[ANALYSIS DEBUG] Found deliverables directly in response:', deliverables.length);
        } 
        // Try plan.deliverables
        else if (aiPlanResponse.plan && aiPlanResponse.plan.deliverables && Array.isArray(aiPlanResponse.plan.deliverables)) {
          deliverables = aiPlanResponse.plan.deliverables;
          log('[ANALYSIS DEBUG] Found deliverables in plan.deliverables:', deliverables.length);
        } 
        // Try plan.suggestions_by_department
        else if (aiPlanResponse.plan && aiPlanResponse.plan.suggestions_by_department) {
          const suggestionsByDept = aiPlanResponse.plan.suggestions_by_department;
          log('[ANALYSIS DEBUG] Extracting from suggestions_by_department. Departments:', Object.keys(suggestionsByDept));

          Object.entries(suggestionsByDept).forEach(([dept, deptDeliverables]) => {
            log(`[ANALYSIS DEBUG] Department "${dept}" has ${Array.isArray(deptDeliverables) ? deptDeliverables.length : 0} deliverables`);
            if (Array.isArray(deptDeliverables)) {
              // Map the backend format to our expected format
              const mappedDeliverables = deptDeliverables.map(d => ({
                deliverable_code: d.code || d.deliverable_code || d.deliverable_code,
                deliverable_name: d.name || d.deliverable_name || d.deliverable || d.title,
                department: dept,
                category: dept,
                confidence: d.confidence_score || d.confidence || 0,
                selected: d.selected || false,
                // Preserve additional fields for AI suggestions
                confidence_score: d.confidence_score,
                relevancy_tags: d.relevancy_tags,
                evidence: d.evidence
              }));
              deliverables = deliverables.concat(mappedDeliverables);
            }
          });
          log('[ANALYSIS DEBUG] Total deliverables extracted from departments:', deliverables.length);
        }

        // Log sample deliverable structure if we have any
        if (deliverables.length > 0) {
          log('[ANALYSIS DEBUG] Sample deliverable structure:', JSON.JSON.stringify(deliverables[0], null, 2));
          log('[ANALYSIS DEBUG] All deliverable codes:', deliverables.map(d => d.deliverable_code || d.code || 'NO_CODE'));
        }

        console.log('[ANALYSIS] Found deliverables to load into PRIMARY_SCENARIO:', deliverables.length);

        // Update PRIMARY_SCENARIO with deliverables and analysis results
        window.PRIMARY_SCENARIO.deliverables = deliverables;
        window.PRIMARY_SCENARIO.status = 'analyzed';
        window.PRIMARY_SCENARIO.updatedAt = new Date().toISOString();

        // Also update DELIVERABLES global for backward compatibility
        window.DELIVERABLES = deliverables;

        // If ScenarioManager exists, update it too
        if (window.ScenarioManager && window.ScenarioManager.setState) {
          window.ScenarioManager.setState({
            deliverables: deliverables
          });
        }

        log('[ANALYSIS] Updated PRIMARY_SCENARIO with', deliverables.length, 'deliverables');
      } else {
        console.warn('[ANALYSIS] PRIMARY_SCENARIO not available, creating it now');
        window.PRIMARY_SCENARIO = {
          deliverables: aiPlanResponse.deliverables || [],
          analysisResults: aiPlanResponse,
          status: 'analyzed',
          updatedAt: new Date().toISOString()
        };
      }

      // Show Step 2
      const step2 = document.getElementById('step2');
      if (step2) {
        console.log('[ANALYSIS] Showing Step 2');
        step2.style.display = 'block';
        step2.scrollIntoView({ behavior: 'smooth' });
      }

      // CRITICAL: Ensure APB.step2.allDeliverables is populated from PRIMARY_SCENARIO
      // This is needed for renderDeliverablesPanel to work correctly
      if (window.PRIMARY_SCENARIO.deliverables && window.PRIMARY_SCENARIO.deliverables.length > 0) {
        log('[ANALYSIS] Populating APB.step2.allDeliverables from PRIMARY_SCENARIO');

        // Ensure APB.step2 exists
        if (!window.APB) {
          window.APB = {};
        }
        if (!window.APB.step2) {
          window.APB.step2 = {
            selectedCodes: new Set(),
            selectedComponentsByCode: {},
            selectedL2ByKey: {},
            allDeliverables: [],
            aiSuggestedCodes: new Set(),
            filters: { deliverables: '', components: '', l2: '' },
            els: {}
          };
        }

        APB.step2.allDeliverables = window.PRIMARY_SCENARIO.deliverables.map(d => {
          // Handle both formats: new AI format and old OPTIONS format
          if (d.deliverable_code || d.Deliverable_Code) {
            return {
              Deliverable_Code: d.deliverable_code || d.Deliverable_Code || d.code || d.id,
              Deliverable: d.deliverable_name || d.Deliverable || d.name || d.title,
              Category: d.department || d.Category || d.category || '',
              Service_Dept_for_PM: d.service_dept || d.Service_Dept_for_PM || '',
              confidence: d.confidence || d.score || 0,
              selected: d.selected || false,
              // Preserve additional fields for AI suggestions
              confidence_score: d.confidence_score,
              relevancy_tags: d.relevancy_tags,
              evidence: d.evidence
            };
          }
          return d; // Return as-is if format is unknown
        });

        // Also populate DELIVERABLES for backward compatibility
        window.DELIVERABLES = APB.step2.allDeliverables;

        // Build the indexes for fast lookup
        window.DELIV_INDEX = {};
        window.DELIV_INDEX_LO = {};
        APB.step2.allDeliverables.forEach(d =>{
          const code = String(d.Deliverable_Code);
          window.DELIV_INDEX[code] = d;
          window.DELIV_INDEX_LO[code.toLowerCase()] = d;
        });

        log('[ANALYSIS] Built deliverable indexes with', Object.keys(window.DELIV_INDEX).length, 'items');
      }

      // Only call renderAIPlan if we have a valid plan structure
      if (aiPlanResponse && (aiPlanResponse.plan || aiPlanResponse.deliverables)) {
        renderAIPlan(aiPlanResponse);
      } else {
        console.warn('[ANALYSIS] No valid plan structure found in response:', aiPlanResponse);
      }

      // CRITICAL: Call renderDeliverablesPanel to populate Step 2 UI
      if (typeof window.renderDeliverablesPanel === 'function') {
        log('[ANALYSIS] Calling renderDeliverablesPanel to populate Step 2');
        window.renderDeliverablesPanel();

        // Verify rendering worked
        setTimeout(() => {
          const delivRows = document.querySelectorAll('.deliv-row');
          console.log('[ANALYSIS] Verification: Found', delivRows.length, 'deliverable rows in DOM');
          if (delivRows.length === 0) {
            console.error('[ANALYSIS] ❌ Deliverables did not render! Force re-render...');
            window.renderDeliverablesPanel();
          } else {
            console.log('[ANALYSIS] ✅ Deliverables rendered successfully');
          }
        }, 100);
      } else {
        console.warn('[ANALYSIS] renderDeliverablesPanel function not found!');
      }

      const btnAnalyze = document.querySelector('#btnAnalyze');
      if (btnAnalyze) {
        btnAnalyze.disabled = false;
        btnAnalyze.textContent = 'Analyze with AI';
      }
    } else if (isFailed) {
      log(`[POLLING] ❌ Job ${jobId} failed, stopping polling`);
      log(`[POLLING] 🛑 Stopping AI analysis polling - job failed`);

      // Clear all polling protection and intervals
      window.PROTECTED_AI_POLLING = false;

      if (aiAnalysisInterval) {
        clearInterval(aiAnalysisInterval);
        aiAnalysisInterval = null;
      }
      if (window.PROTECTED_AI_INTERVAL) {
        clearInterval(window.PROTECTED_AI_INTERVAL);
        window.PROTECTED_AI_INTERVAL = null;
      }

      hideAIProgressBar();
      alert(`AI analysis failed: ${status.error || status.message || 'Unknown error'}`);

      const btnAnalyze = document.querySelector('#btnAnalyze');
      if (btnAnalyze) {
        btnAnalyze.disabled = false;
        btnAnalyze.textContent = 'Analyze with AI';
      }
    }
  } catch (error) {
    console.error('[POLLING] Error polling AI analysis:', error);
    // Don't stop polling on transient errors - retry
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
window.setAnalysisMode = function(mode) {
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

  // Check for uploaded session ID (for GPT-5 Vision PDF processing) or text
  let rfpText = '';
  let uploadSessionId = null;
  let hasStagedFiles = false;
  let extractionErrors = [];

  // PRIORITY 1: Check for staged files FIRST (using SessionManager for consistency)
  const stagedSessionId = SessionManager.getCurrentSessionId();
  log('[ANALYSIS DEBUG] Current session ID:', stagedSessionId);

  if (stagedSessionId) {
    try {
      log('[ANALYSIS] Checking for staged files in session:', stagedSessionId);

      // Call the extract endpoint to get text from staged files
      const extractFormData = new FormData();
      extractFormData.append('session_id', stagedSessionId);

      log('[ANALYSIS DEBUG] Calling /api/stage/extract with session:', stagedSessionId);
      const extractRes = await fetch('/api/stage/extract', {
        method: 'POST',
        body: extractFormData
      });

      log('[ANALYSIS DEBUG] Extract response status:', extractRes.status);

      if (extractRes.ok) {
        const extractData = await extractRes.json();
        log('[ANALYSIS DEBUG] Extract response data:', extractData);

        // Track if we have staged files (even if extraction fails for some)
        if (extractData.files_count > 0 || extractData.total_files > 0) {
          hasStagedFiles = true;
          log('[ANALYSIS DEBUG] Staged files detected:', extractData.files_count || extractData.total_files);
        }

        // Track any extraction errors (even if success is false)
        if (extractData.errors && extractData.errors.length > 0) {
          extractionErrors = extractData.errors;
          console.warn('[ANALYSIS] File extraction errors:', extractData.errors);
        }

        if (extractData.success && extractData.text) {
          // Start with textarea text first (if present)
          const textareaText = (textEl?.value || '').trim();
          if (textareaText) {
            rfpText = textareaText + '\n\n=== UPLOADED FILES ===\n\n';
            log('[ANALYSIS] Starting with textarea text:', textareaText.length, 'chars');
          }

          // Add staged files text
          rfpText += extractData.text;
          log('[ANALYSIS] Added staged files text:', extractData.files_count, 'files,', extractData.text.length, 'chars');
          log('[ANALYSIS] Total combined text:', rfpText.length, 'chars');
        } else {
          log('[ANALYSIS DEBUG] No text extracted. Success:', extractData.success, 'Text length:', extractData.text?.length);
        }
      } else {
        console.warn('[ANALYSIS] Extract endpoint returned error:', extractRes.status);
        const errorText = await extractRes.text();
        log('[ANALYSIS DEBUG] Error response:', errorText);
      }
    } catch (e) {
      console.error('[ANALYSIS] Error extracting staged files:', e);
      log('[ANALYSIS DEBUG] Full error:', e.stack);
      // Show user-friendly error
      extractionErrors.push('Network error while extracting files: ' + e.message);
    }
  } else {
    log('[ANALYSIS DEBUG] No session ID available for staged files');
  }

  // PRIORITY 2: Check for old-style uploaded files (GPT-5 Vision PDF processing)
  if (!rfpText && window.APP?.uploadSessionId) {
    log('[ANALYSIS] Using uploaded PDF session:', window.APP.uploadSessionId);
    uploadSessionId = window.APP.uploadSessionId;
    rfpText = window.APP.uploadedFileText || "PDF files uploaded";
  } else if (!rfpText && window.uploadedFileText) {
    log('[ANALYSIS] Using uploaded file text:', window.uploadedFileText.length, 'chars');
    rfpText = window.uploadedFileText;
  } else if (!rfpText && window.APP?.uploadedFileText) {
    log('[ANALYSIS] Using APP.uploadedFileText:', window.APP.uploadedFileText.length, 'chars');
    rfpText = window.APP.uploadedFileText;
  } else if (!rfpText) {
    // PRIORITY 3: Fall back to textarea only
    rfpText = (textEl?.value || '').trim();
    if (rfpText) {
      log('[ANALYSIS] Using textarea text only:', rfpText.length, 'chars');
    }
  }

  const btnAnalyze = document.querySelector('#btnAnalyze');
  const analysisMode = document.getElementById('analysis-mode')?.value || 'deep';
  log('[ANALYSIS] Starting analysis with mode:', analysisMode);

  // ============================================================================
  // SESSION ISOLATION: Use existing session if we have uploaded/staged files, otherwise start fresh
  // ============================================================================
  let sessionId;
  if (uploadSessionId || hasStagedFiles) {
    // Keep existing session if we have uploaded files or staged files
    sessionId = SessionManager.getCurrentSessionId();
    log('[SESSION] Using existing session with files:', sessionId);
  } else {
    // Start fresh session only if no files were uploaded
    sessionId = SessionManager.startNewSession();
    log('[SESSION] New analysis session:', sessionId);
  }

  // Reset global state for fresh analysis
  SCENARIOS = null;
  DELIVERABLES = [];
  DELIV_INDEX = {};
  DELIV_INDEX_LO = {};

  // Reset Step 2 state
  selectionStore.deliverables.clear();
  selectionStore.componentsByDeliv.clear();
  selectionStore.l2ByComponent.clear();
  S2.selectedComponentsByCode = {};
  S2.aiSuggestedCodes = new Set();
  S2.activeDeliverableCode = null;
  S2.activeComponentName = null;

  // Show progress bar IMMEDIATELY when button is clicked
  showAIProgressBar();
  updateAIProgress({ progress: 10, current_stage: 'Preparing analysis...', elapsed_seconds: 0, eta_seconds: null });

  let aiPlanResponse;
  try {
    // Check for RFP text from multiple sources
    const hasText = rfpText.trim().length > 0 || 
                    window.PRIMARY_SCENARIO?.rfpText?.trim().length > 0;
    const hasStagedFilesCheck = window.FileStagingModule?.state?.files?.length > 0;

    if (!hasText && !hasStagedFilesCheck) {
      hideAIProgressBar();

      // Show extraction errors if any
      if (extractionErrors.length > 0) {
        alert('File extraction errors:\n\n' + extractionErrors.join('\n') + '\n\nPlease check your files and try again.');
      } else {
        alert('Please enter RFP text or upload a document first.');
      }
      return;
    }

    // Debug logging to help diagnose validation issues
    log('[VALIDATION] RFP text length:', rfpText.trim().length);
    log('[VALIDATION] Staged files:', hasStagedFilesCheck);
    log('[VALIDATION] PRIMARY_SCENARIO.rfpText length:', window.PRIMARY_SCENARIO?.rfpText?.length || 0);
    log('[VALIDATION] ✅ Validation passed, starting analysis');

    // If we have staged files but no text yet, use placeholder
    if (!rfpText && (hasStagedFilesCheck || uploadSessionId)) {
      log('[ANALYSIS] Using placeholder for staged files');
      rfpText = "Analyzing uploaded files...";
    }

    // Warn about extraction errors but proceed with analysis
    if (extractionErrors.length > 0) {
      console.warn('[ANALYSIS] Proceeding with partial extraction. Errors:', extractionErrors);
      // Optional: Show a non-blocking warning to the user
      const warningMsg = `Note: Some files had extraction errors:\n${extractionErrors.join('\n')}\n\nProceeding with available text...`;
      if (confirm(warningMsg + '\n\nContinue with analysis?')) {
        log('[ANALYSIS] User chose to continue despite extraction errors');
      } else {
        hideAIProgressBar();
        if (btnAnalyze) {
          btnAnalyze.disabled = false;
          btnAnalyze.textContent = 'Analyze with AI';
        }
        return;
      }
    }

    log('[ANALYSIS] Proceeding with text analysis:', rfpText.length, 'characters');

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

    // Get selected mode (Fast or Deep) - use analysisMode variable
    const selectedMode = analysisMode || 'deep';

    log('[ANALYSIS] Sending API request with:', {
      mode: selectedMode,
      tier: tier,
      textLength: rfpText.length,
      sessionId: sessionId
    });

    const aiRes = await fetchWithRetry('/api/ai/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.JSON.stringify({ 
        request_text: rfpText,
        strictness: 'balanced',
        tier: tier,
        mode: selectedMode,  // Add mode parameter
        session_id: sessionId,  // Add session_id for cache isolation
        upload_session_id: uploadSessionId  // NEW: Pass upload session for PDF processing
      })
    }, 3, 2000);

    if (!aiRes.ok) {
      throw new Error(`AI analysis error: ${aiRes.status} ${aiRes.statusText}`);
    }

    const jobInfo = await aiRes.json();
    console.log('[ANALYSIS] Job created with ID:', jobInfo.job_id);

    // Persist RFP text for Step 2
    window.APP = window.APP || {};
    window.APP.rfpText = rfpText;

    // Store RFP text with session isolation
    SessionManager.setSessionItem('rfp_text', rfpText);
    sessionStorage.setItem('apb.rfp_text', rfpText);  // Keep for backward compatibility

    APB.step2.rfpText = rfpText;

    // Start SSE streaming for AI analysis progress
    if (jobInfo.job_id) {
      aiAnalysisJobId = jobInfo.job_id;
      showAIProgressBar();
      updateAIProgress({ progress: 0, current_stage: 'Starting AI analysis...', elapsed_seconds: 0, eta_seconds: null });

      // Clear any existing polling interval before starting a new one
      if (aiAnalysisInterval) {
        console.log('[POLLING] Clearing existing interval before starting new polling');
        clearInterval(aiAnalysisInterval);
        aiAnalysisInterval = null;
      }

      // Start polling for job status (SSE not implemented for AI jobs yet)
      // Poll the correct endpoint for job status

      // CRITICAL: Force GlobalPollingManager to allow polling BEFORE starting
      if (window.GlobalPollingManager) {
        console.log('[POLLING FIX] Forcing GlobalPollingManager to allow polling...');
        window.GlobalPollingManager.isShuttingDown = false;
        if (window.GlobalPollingManager.resumePolling) {
          window.GlobalPollingManager.resumePolling();
        }
      }

      // Set protection flag for AI polling
      window.PROTECTED_AI_POLLING = true;
      console.log('[POLLING] 🚀 Starting PROTECTED AI Analysis polling for job:', jobInfo.job_id);

      // Use both a protected interval and store it globally
      aiAnalysisInterval = setInterval(() => {
        console.log('[POLLING] Executing poll for job:', jobInfo.job_id);
        pollAIAnalysis(jobInfo.job_id);
      }, 2000);

      // Also store as protected interval in case the global manager tries to clear it
      window.PROTECTED_AI_INTERVAL = aiAnalysisInterval;

      // Start the first poll immediately
      console.log('[POLLING] 🎯 Triggering first poll immediately');
      pollAIAnalysis(jobInfo.job_id);

      // Old SSE code commented out for now
      // const eventSource = new EventSource(`/api/stream/${jobInfo.job_id}`);

      /* SSE event handler disabled for now - using polling instead
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Update progress UI with detailed status
          const progressUpdate = {
            progress: Math.round(data.progress || 0),
            current_stage: data.current_stage || data.message || 'Processing...',
            elapsed_seconds: data.elapsed_seconds || 0,
            eta_seconds: data.eta_seconds
          };

          // Map stages to user-friendly messages
          const stageMap = {
            'extracting_text': '📄 Extracting text from document...',
            'analyzing_content': '🧠 Analyzing content with AI...',
            'processing_deliverables': '📋 Processing deliverables...',
            'generating_suggestions': '💡 Generating AI suggestions...',
            'finalizing': '✨ Finalizing analysis...'
          };

          if (data.current_stage && stageMap[data.current_stage]) {
            progressUpdate.current_stage = stageMap[data.current_stage];
          }

          updateAIProgress(progressUpdate);

          // Handle completion
          if (data.status === 'completed' && data.result) {
            eventSource.close();
            hideAIProgressBar();

            // Handle completed analysis
            const aiPlanResponse = data.result;
            window.APP = window.APP || {};
            window.APP.aiPlan = aiPlanResponse;
            sessionStorage.setItem('apb:aiPlan', JSON.JSON.stringify(aiPlanResponse));

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
          }

          // Handle errors
          if (data.status === 'failed') {
            eventSource.close();
            alert(`AI analysis failed: ${data.error || 'Unknown error'}`);

            const btnAnalyze = document.querySelector('#btnAnalyze');
            if (btnAnalyze) {
              btnAnalyze.disabled = false;
              btnAnalyze.textContent = 'Analyze with AI';
            }
          }
        } catch (error) {
          console.error('Error parsing SSE data:', error);
        }
      };

      */
      // SSE error handler also disabled
      /*
      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        eventSource.close();

        // Fallback to polling if SSE fails
        if (!aiAnalysisInterval) {
          window.PROTECTED_AI_POLLING = true;
          console.log('[POLLING] 🚀 Starting PROTECTED fallback AI polling');
          aiAnalysisInterval = setInterval(() => pollAIAnalysis(aiAnalysisJobId), 2000);
          window.PROTECTED_AI_INTERVAL = aiAnalysisInterval;
          pollAIAnalysis(aiAnalysisJobId);
        }
      };

      // Store event source for cleanup
      window.aiAnalysisEventSource = eventSource;
      */

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
  console.log('[renderAIPlan DEBUG] Called with:', {
    hasAIPlan: !!aiPlan,
    hasPlan: !!(aiPlan?.plan),
    planKeys: aiPlan ? Object.keys(aiPlan) : [],
    planPlanKeys: aiPlan?.plan ? Object.keys(aiPlan.plan) : []
  });

  if (!aiPlan || !aiPlan.plan) {
    console.warn('[renderAIPlan] No AI plan to render, received:', aiPlan);
    return;
  }

  const plan = aiPlan.plan;
  const summary = plan.summary || {};
  const suggestionsByDept = plan.suggestions_by_department || {};

  console.log('[renderAIPlan DEBUG] Departments found:', Object.keys(suggestionsByDept));
  console.log('[renderAIPlan DEBUG] Total deliverables by dept:', 
    Object.entries(suggestionsByDept).map(([dept, items]) => 
      `${dept}: ${Array.isArray(items) ? items.length : 0}`
    ).join(', ')
  );

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
                        style="padding: 4px 12px; font-size: 0.85em; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer;">
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
                          style="margin-left: 8px; padding: 2px 8px; font-size: 0.75em; background: #e5e7eb; border: none; border-radius: 3px;">
                    Select All
                  </button>
                  <button onclick="event.stopPropagation(); selectAllComponents('${delivCode}', false)" 
                          style="margin-left: 4px; padding: 2px 8px; font-size: 0.75em; background: #e5e7eb; border: none; border-radius: 3px;">
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
      const confidence = Math.round((deliv.calibrated_confidence || 0) * 100);
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
  // CRITICAL: Stop all polling before applying selections to prevent 404 flood
  console.log('[APPLY-AI] ========= STOPPING ALL POLLING BEFORE APPLYING =========');

  // 1. Use GlobalPollingManager master kill switch
  if (window.GlobalPollingManager && window.GlobalPollingManager.stopAllPolling) {
    console.log('[APPLY-AI] Calling GlobalPollingManager.stopAllPolling()...');
    const result = window.GlobalPollingManager.stopAllPolling();
    console.log('[APPLY-AI] GlobalPollingManager stopped:', result);
  }

  // 2. Stop AI Assistant polling specifically
  if (window.aiAssistant) {
    console.log('[APPLY-AI] Stopping AI Assistant polling...');
    if (window.aiAssistant.currentPollInterval) {
      clearInterval(window.aiAssistant.currentPollInterval);
      window.aiAssistant.currentPollInterval = null;
    }
    if (window.aiAssistant.stopJobPolling) {
      window.aiAssistant.stopJobPolling();
    }
    // Clear the job ID from assistant state
    if (window.aiAssistant.agentState) {
      window.aiAssistant.agentState.jobId = null;
    }
  }

  // 3. Clear any lingering job IDs from localStorage
  try {
    const charlesState = JSON.parse(localStorage.getItem('charles_agent_state') || '{}');
    if (charlesState.jobId) {
      console.log('[APPLY-AI] Clearing CHARLES jobId:', charlesState.jobId);
      charlesState.jobId = null;
      charlesState.jobIdTimestamp = null;
      localStorage.setItem('charles_agent_state', JSON.JSON.stringify(charlesState));
    }
  } catch (e) {
    console.error('[APPLY-AI] Error clearing localStorage:', e);
  }

  console.log('[APPLY-AI] Polling cleanup complete, now applying selections...');

  // Collect selected deliverables
  const delivCheckboxes = document.querySelectorAll('.ai-deliv-checkbox:checked');
  let firstDelivCode = null;
  let firstCompName = null;

  for (const delivCb of delivCheckboxes) {
    const delivCode = delivCb.dataset.code;

    // Track first selected deliverable
    if (!firstDelivCode) {
      firstDelivCode = delivCode;
    }

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

      // Track first component
      if (!firstCompName && delivCode === firstDelivCode) {
        firstCompName = compTitle;
      }

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
        selectionStore.l2ByComponent.set(key, selectedTasks);
      }
    }

    // Store selected components in both selectionStore and S2 (for compatibility)
    if (selectedComps.size > 0) {
      selectionStore.componentsByDeliv.set(delivCode, selectedComps);
      S2.selectedComponentsByCode[delivCode] = selectedComps;
    }
  }

  // FIX: Fetch L2 tasks for ALL selected deliverables (not just the first one)
  const allSelectedDelivs = Array.from(selectionStore.deliverables);

  for (const delivCode of allSelectedDelivs) {
    // Get components for this deliverable
    const components = selectionStore.componentsByDeliv.get(delivCode);

    if (components && components.size > 0) {
      const componentArray = Array.from(components);

      try {
        // Fetch L2 tasks in bulk for all selected components of this deliverable
        const res = await fetch('/api/l2/bulk', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.JSON.stringify({
            deliverable: delivCode,
            components: componentArray
          })
        });

        if (res.ok) {
          const l2Data = await res.json();

          // FIX: Handle l2_by_component structure from API
          const tasksData = l2Data.l2_by_component || l2Data;

          // Store L2 tasks for each component
          for (const [compName, tasks] of Object.entries(tasksData)) {
            const key = `${delivCode}::${compName}`;
            if (!selectionStore.l2ByComponent.has(key)) {
              selectionStore.l2ByComponent.set(key, new Set());
            }
            const existingTasks = selectionStore.l2ByComponent.get(key);

            // Handle array of tasks properly
            if (Array.isArray(tasks)) {
              tasks.forEach(task => {
                // Ensure we always get a string value, not an object
                let taskName;
                if (typeof task === 'string') {
                  taskName = task;
                } else if (task && typeof task === 'object') {
                  // Extract string from object - check all possible property names
                  taskName = task.Task_Label || task.task_label || task.name || task.title || task.label || '';
                  // If still no valid string, try converting to string
                  if (!taskName && task.toString && task.toString() !== '[object Object]') {
                    taskName = task.toString();
                  }
                }
                // Only add if we have a valid string
                if (taskName && typeof taskName === 'string' && taskName !== '[object Object]') {
                  existingTasks.add(taskName);
                }
              });
            }
          }

          // Auto-activate first component if available
          if (firstDelivCode && firstCompName) {
            S2.activeComponentName = firstCompName;
            // Trigger component panel refresh to show L2 tasks immediately
            await refreshL2Panel();
          }

          console.log(`Fetched L2 tasks for ${delivCode} components:`, Object.keys(tasksData));
        }
      } catch (error) {
        console.error(`Failed to fetch L2 tasks for ${delivCode}:`, error);
      }
    } else {
      // Edge case: deliverable has no components, use "general" fallback
      try {
        const generalTasks = await api(`/api/l2?deliverable=${encodeURIComponent(delivCode)}&component=general`);
        if (generalTasks && generalTasks.length > 0) {
          // Store as "general" component
          const key = `${delivCode}::general`;
          selectionStore.l2ByComponent.set(key, new Set(generalTasks));

          // Also update the component map to have "general"
          selectionStore.componentsByDeliv.set(delivCode, new Set(['general']));
          S2.selectedComponentsByCode[delivCode] = new Set(['general']);

          console.log(`Fetched L2 tasks for ${delivCode} (general fallback):`, generalTasks.length);
        }
      } catch (error) {
        console.warn(`No components or general tasks found for ${delivCode}:`, error);
      }
    }
  }

  // Set the active deliverable and component for UI (first selected)
  if (firstDelivCode) {
    // Set in both APB.step2 and S2 to ensure consistency
    APB.step2.activeDeliverableCode = firstDelivCode;
    S2.activeDeliverableCode = firstDelivCode;

    const components = selectionStore.componentsByDeliv.get(firstDelivCode);
    if (components && components.size > 0) {
      firstCompName = firstCompName || Array.from(components)[0];
      APB.step2.activeComponentName = firstCompName;
      S2.activeComponentName = firstCompName;
    }
  }

  // Update all panels properly
  if (window.renderDeliverablesPanel) renderDeliverablesPanel();
  if (window.renderComponentsPanel) {
    if (firstDelivCode) {
      await renderComponentsPanel();
    }
  }

  // FIX: Render L2 panel to display the first component's L2 tasks
  if (firstDelivCode && firstCompName) {
    // Use renderL2Panel which displays L2 tasks in the third column
    if (window.renderL2Panel) {
      await renderL2Panel();
    } else if (window.renderTasksPanel) {
      // Fallback to renderTasksPanel if available
      const componentKey = `${firstDelivCode}::${firstCompName}`;
      await renderTasksPanel(componentKey);
    }
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
    taskList.innerHTML = '<p style="color: var(--muted); text-align: center; padding-top: 40px; font-size: 0.9em;">Select a component to view tasks</p>';
    document.getElementById('s2-tasks-active-component').textContent = 'Select a component';
    return;
  }

  // Parse component key
  const [delivCode, compName] = componentKey.split('::');

  // Update active component display
  document.getElementById('s2-tasks-active-component').textContent = `${compName}`;

  // Get available tasks for this component
  const availableTasks = selectionStore.l2ByComponent.get(componentKey) || new Set();
  const selectedTasks = selectionStore.l2ByComponent.get(componentKey) || new Set();

  if (availableTasks.size === 0) {
    // Fetch tasks if not loaded
    try {
      const tasks = await api(`/api/l2?deliverable=${encodeURIComponent(delivCode)}&component=${encodeURIComponent(compName)}`);
      tasks.forEach(task => availableTasks.add(task));
      selectionStore.l2ByComponent.set(key, availableTasks);
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
    // FIX: Extract task name if it's an object
    let taskName = task;
    if (typeof task === 'object' && task) {
      taskName = task.Task_Label || task.task_label || task.name || task.title || task.label || '';
    }
    if (!taskName || taskName === '[object Object]') return ''; // Skip invalid entries

    const isAiRecommended = window.lastAIPlan && isTaskAIRecommended(delivCode, compName, taskName);
    const isChecked = selectedTasks.has(taskName);
    const taskColor = isAiRecommended ? '#10b981' : '#6b7280';

    return `
      <label style="display: flex; align-items: start; gap: 8px; padding: 8px; border-radius: 4px; cursor: pointer; hover:background: rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.05);">
        <input type="checkbox" 
               class="task-checkbox" 
               data-task="${taskName}" 
               data-component="${componentKey}"
               ${isChecked ? 'checked' : ''}
               style="margin-top: 2px; cursor: pointer;">
        <div style="flex: 1;">
          <span style="color: ${taskColor}; font-size: 0.9em;">${taskName}</span>
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

      if (!selectionStore.l2ByComponent.has(compKey)) {
        selectionStore.l2ByComponent.set(compKey, new Set());
      }

      if (e.target.checked) {
        selectionStore.l2ByComponent.get(compKey).add(task);
      } else {
        selectionStore.l2ByComponent.get(compKey).delete(task);
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
  for (const [compKey, tasks] of selectionStore.l2ByComponent.entries()) {
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
      const detailsHtml = Array.from(selectionStore.l2ByComponent.entries())
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
document.addEventListener('DOMContentLoaded', () => {
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

  const l2html = Object.entries(ai.l2_by_component || {}).map(([comp, tasks]) => `
    <details class="ai-group" style="margin:8px 0;">
      <summary style="cursor:pointer;font-weight:600;padding:4px 0;">${comp}</summary>
      <ul class="ai-l2" style="margin:4px 0 0 20px;list-style:disc;">
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
      <h4 style="margin:8px 0;">GPT‑5 Suggested L2 (per component)</h4>
      ${l2html || "<div class='muted'>No task suggestions.</div>"}
    </div>
  `;

  host.onclick = async (e) => {
    try {
      const btn = e.target.closest("[data-ai-act]");
      if (!btn) return;
      const act = btn.getAttribute("data-ai-act");
      const d = btn.getAttribute("data-d");
      const compsPicked = (ai.components || []).map(x => x.name);

      if (act === "replace") {
        S2.selectedComponentsByCode[d] = new Set();
        selectionStore.componentsByDeliv.set(d, new Set());
        for (const key of Array.from(selectionStore.l2ByComponent.keys())) {
          if (key.startsWith(d + "::")) {
            selectionStore.l2ByComponent.delete(key);
          }
        }
      }

      for (const c of compsPicked) {
        if (!S2.selectedComponentsByCode[d]) {
          S2.selectedComponentsByCode[d] = new Set();
        }
        S2.selectedComponentsByCode[d].add(c);
        await hydrateL2For(d, c);
      }

      if (ai.l2_by_component) {
        for (const [comp, items] of Object.entries(ai.l2_by_component)) {
          const key = `${d}::${comp}`;
          if (!selectionStore.l2ByComponent.has(key)) {
            selectionStore.l2ByComponent.set(key, new Set());
          }
          const existingTasks = selectionStore.l2ByComponent.get(key);
          items.forEach(t => existingTasks.add(t.label));
        }
      }

      await refreshComponentsPanel();
      updateSummaryCounts();
    } catch (error) {
      console.error('[AI SUGGESTIONS] Error applying AI suggestions:', error);
      alert(`An error occurred while applying AI suggestions. Please try again.`);
    }
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
      body: JSON.JSON.stringify({
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
      toggleBtn.className = 'btn-suggest';
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
  if (!S2.selectedComponentsByCode[code]) {
    S2.selectedComponentsByCode[code] = 'ALL';
  }
  s2RenderLeft();
  s2RenderRight(S2.els.search?.value || '');

  // Sync with new Step 2 UI state
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
  S2.selectedComponentsByCode[code] = undefined; // Remove custom component selection
  s2RenderLeft();
  s2RenderRight(S2.els.search?.value || '');

  // Sync with new Step 2 UI state
  if (window.step2State) {
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
      body: JSON.JSON.stringify(payload)
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
      const row = el(`
        <div class="row">
          <div>
            <strong>${item.Deliverable}</strong> 
            <small class="badge">${item.Category}</small>
          </div>
          ${isSelected ? '<span class="already-selected">✓</span>' : 
            `<button onclick="onAdd('${item.Deliverable_Code}')" class="add-btn">Add</button>`}
        </div>
      `);
      results.append(row);
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
          <div class="inline">${currency(d.total_hours)} hrs &nbsp; <strong>Price:</strong> ${currency(d.price)}</div>
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
    body: JSON.JSON.stringify({scenario: SCENARIOS[which]})
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

    const response = await fetch(`/api/components_for?deliverable_code=${encodeURIComponent(code)}&complexity=${encodeURIComponent(complexity)}&tier=${encodeURIComponent(tier)}`);
    const data = await response.json();
    const components = data.items || [];

    if (components.length === 0) {
      alert(`No components found for ${name}`);
      return;
    }

    // Check if this deliverable has been customized before
    // If not, initialize with undefined (not an empty Set) to indicate "use all defaults"
    let current = APB.step2.selectedComponentsByCode[code];
    if (!current || current === '__ALL__' || current === 'ALL') {
      // Default to all selected if no custom selection exists
      current = new Set(components.map(c => c.name));
    } else if (current instanceof Set) {
      // Already a Set
    } else if (Array.isArray(current)) {
      // Convert array to Set
      current = new Set(current);
    } else if (typeof current === 'object' && current !== null) {
      // Convert object keys to Set
      current = new Set(Object.keys(current));
    } else {
      // Fallback if state is corrupted - default to all selected
      current = new Set(components.map(c => c.name));
    }

    // Ensure the current selection is stored back in the correct format
    APB.step2.selectedComponentsByCode[code] = current;

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
            <button onclick="saveComponentSelection('${code}')" class="btn-primary">Done</button>
          </div>
        </div>
      </div>
    `);

    document.body.appendChild(modal);

    // Populate component list with auto-apply on change
    const list = document.getElementById('component-list');
    components.forEach(comp => {
      const item = el(`
        <label style="display: block; margin: 8px 0; cursor: pointer;">
          <input type="checkbox" data-component="${comp.name}" ${current.has(comp.name) ? 'checked' : ''}>
          ${comp.name} <small style="color: var(--muted);">(${Math.round(comp.hours)} h)</small>
        </label>
      `);

      // Auto-apply changes when checkbox changes
      const checkbox = item.querySelector('input[type="checkbox"]');
      checkbox.addEventListener('change', (e) => {
        // Ensure we are working with a Set
        if (!(current instanceof Set)) {
          current = new Set(Array.from(current || []));
          APB.step2.selectedComponentsByCode[code] = current;
        }

        if (e.target.checked) {
          current.add(comp.name);
        } else {
          current.delete(comp.name);
        }

        // Update the global S2 state as well for consistency
        S2.selectedComponentsByCode[code] = current;
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
    const compSet = S2.selectedComponentsByCode[code];

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
    scenario_b: { mode: 'template', complexity:'Advanced', tier:'T2_MediumVolume'}, // Default for B
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
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.JSON.stringify(payload)
  });
  const scenarios = await res.json();
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

// ========== New Step 2 UI (4-Column Layout) ==========

// State for new Step 2 UI
const step2State = {
  currentDeliverable: null,     // Currently selected deliverable for viewing components
  currentComponent: null,        // Currently selected component for viewing L2 subtasks
  selectedL2Map: {},             // { deliverableCode: { componentName: Set([l2labels...]) } }
};
window.step2State = step2State;

// Expose functions globally
window.updateStep2Summary = updateStep2Summary;
window.renderComponentsPanel = renderComponentsPanel;
window.renderL2Panel = renderL2Panel;

// Update summary panel with current selection counts
function updateStep2Summary() {
  const delivCount = window.step2PickerState?.selected?.size || 0;
  const delivEl = document.getElementById('s2-summary-deliverables');
  if (delivEl) delivEl.textContent = delivCount;

  // Count components
  let compCount = 0;
  Object.entries(APB.step2.selectedComponentsByCode).forEach(([code, compSet]) => {
    if (APB.step2.selectedCodes.has(code)) {
      // Handle '__ALL__' sentinel
      if (compSet === '__ALL__' || compSet === 'ALL') {
        // Count all available components for this deliverable
        const comps = APB.step2.allDeliverables.find(d => String(d.Deliverable_Code) === code)?.components || [];
        compCount += comps.length;
      } else if (compSet instanceof Set) {
        compCount += compSet.size;
      } else if (Array.isArray(compSet)) {
        compCount += compSet.length;
      } else if (typeof compSet === 'object') {
        compCount += Object.keys(compSet).length;
      }
    }
  });
  const compEl = document.getElementById('s2-summary-components');
  if (compEl) compEl.textContent = compCount;

  // Count L2 - only for selected components (fixes Task 4)
  let l2Count = 0;
  Object.entries(APB.step2.selectedL2ByKey).forEach(([key, l2Set]) => {
    const [code, compName] = key.split('::');
    // Only count if deliverable is selected AND component is selected
    if (APB.step2.selectedCodes.has(code)) {
      const compSet = APB.step2.selectedComponentsByCode[code];
      // Check if selectedComponentsByCode[code] is NOT '__ALL__' or 'ALL'
      // And if the component set actually contains the component for this key
      if (compSet && compSet !== '__ALL__' && compSet !== 'ALL' && compSet instanceof Set && compSet.has(compName)) {
        if (l2Set instanceof Set) l2Count += l2Set.size;
        else if (Array.isArray(l2Set)) l2Count += l2Set.length;
      } else if (compSet === '__ALL__' || compSet === 'ALL') {
        // If all components are selected, count all L2 tasks for this component
        // This requires fetching L2 tasks again or assuming they are available
        // For simplicity, we assume they are counted if the deliverable is selected and component is implicitly selected
        // A more robust solution would require fetching/storing all L2s initially
        // For now, we'll skip counting L2 if compSet is '__ALL__' and rely on explicit selections.
      }
    }
  });
  const l2El = document.getElementById('s2-summary-l2');
  if (l2El) l2El.textContent = l2Count;

  // Update status message
  const statusEl = document.getElementById('s2-summary-status');
  if (statusEl) {
    if (delivCount === 0) {
      statusEl.textContent = 'No deliverables selected';
      statusEl.style.color = 'var(--muted)';
    } else {
      statusEl.textContent = `${delivCount} deliverable${delivCount > 1 ? 's' : ''} ready`;
      statusEl.style.color = 'var(--accent)';
    }
  }
}

// Render summary chips with hierarchical display: Deliverable → Component → L2
function renderSummaryChips() {
  const container = document.getElementById('s2-summary-status');
  if (!container) return;

  let html = '';

  // Group by Deliverable → Component → L2
  Array.from(APB.step2.selectedCodes).forEach(delivCode => {
    const deliv = APB.step2.allDeliverables.find(d => String(d.Deliverable_Code) === delivCode);
    const delivName = deliv ? (deliv.Deliverable || delivCode) : delivCode;
    const deptColor = getDepartmentColor(deliv?.Category); // Use helper for color

    // Start deliverable group
    html += `<div style="margin-bottom:16px;padding:8px;border-left:3px solid ${deptColor};background:rgba(139,92,246,0.05);border-radius:4px;">`;

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
    if (compSelection === '__ALL__' || compSelection === 'ALL') {
      // If all components are selected, render a single chip for the deliverable
      compSet = new Set(['All Components']); // Sentinel value
    } else if (compSelection instanceof Set) {
      compSet = compSelection;
    } else if (Array.isArray(compSelection)) {
      compSet = new Set(compSelection);
    } else if (typeof compSelection === 'object' && compSelection !== null) {
      compSet = new Set(Object.keys(compSelection));
    } else {
      compSet = new Set(); // Default to empty if undefined or null
    }

    // Render each component and its L2 items
    if (compSet.size > 0) {
      compSet.forEach(compName => {
        const key = `${delivCode}::${compName}`;
        const l2Set = APB.step2.selectedL2ByKey[key] || new Set();

        // Render component chips
        html += `<div style="margin-top:8px;padding-left:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-size:0.8em;color:var(--muted);">${compName}</span>
            <div style="display:flex;gap:6px;">
              <button onclick="resetL2ForComponent('${delivCode}', '${compName}')" 
                      style="background:rgba(139,92,246,0.15);border:none;color:var(--accent);cursor:pointer;padding:2px 8px;border-radius:4px;font-size:0.7em;"
                      title="Restore all L2 subtasks for this component">
                ↻ Reset
              </button>
              <button onclick="removeComponentFromSummary('${delivCode}', '${compName}')" 
                      style="background:none;border:none;color:var(--danger);cursor:pointer;padding:2px 6px;font-size:0.7em;">
                Remove
              </button>
            </div>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:4px;padding-left:8px;">`;

          // L2 chips for this component
          if (l2Set.size > 0) {
            l2Set.forEach(l2Name => {
              const escapedKey = key.replace(/'/g, "\\'"); // Escape single quotes for inline JS
              const escapedL2 = l2Name.replace(/'/g, "\\'");
              html += `<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;background:rgba(16,185,129,0.2);border-radius:12px;font-size:0.7em;">
                ${l2Name}
                <button onclick="removeL2FromSummary('${escapedKey}', '${escapedL2}')" 
                        style="background:none;border:none;color:var(--danger);cursor:pointer;padding:0;font-size:1.2em;line-height:1;">×</button>
              </span>`;
            });
          } else {
            html += `<span style="font-size:0.7em;color:var(--muted);font-style:italic;">No L2 tasks selected</span>`;
          }

          html += `</div></div>`;
      });
    } else {
      // Case where "__ALL__" or "ALL" was selected for components
      html += `<div style="margin-top:8px;padding-left:8px;">
        <span style="font-size:0.8em;color:var(--accent);font-style:italic;">All components included</span>
      </div>`;
    }

    html += `</div>`;
  });

  if (html === '') {
    html = '<div style="text-align:center;color:var(--muted);font-size:0.85em;padding:20px;">No deliverables selected</div>';
  }

  container.innerHTML = html;
}

// Remove deliverable from summary - cascades to all components and L2
window.removeDeliverableFromSummary = async function(code) {
  await deselectDeliverable(code);
  renderDeliverablesPanel();
  await refreshComponentsPanel();
  updateSummaryCounts();
  initAISummaryAndSuggestions();
}

// Remove component from summary - cascades to its L2 items
window.removeComponentFromSummary = function(delivCode, compName) {
  const key = `${delivCode}::${compName}`;

  // Remove L2 for this component
  if (APB.step2.selectedL2ByKey[key]) {
    delete APB.step2.selectedL2ByKey[key];
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

// Reset L2 subtasks for a component - refetches all from server
window.resetL2ForComponent = async function(delivCode, compName) {
  const key = `${delivCode}::${compName}`;

  // Clear the cached L2 for this component
  selectionStore.l2ByComponent.delete(key);
  // Clear from proxy as well
  delete APB.step2.selectedL2ByKey[key];

  // Refetch L2 from server
  await hydrateL2For(delivCode, compName);

  // Update the summary display
  updateSummaryCounts();

  // If this component is the active one, re-render L2 panel
  if (APB.step2.activeDeliverableCode === delivCode && APB.step2.activeComponentName === compName) {
    if (window.renderL2Panel) {
      renderL2Panel();
    } else if (window.renderTasksPanel) {
      await renderTasksPanel(key); // Fallback
    }
  }
}

// Component clicked - load L2 panel
window.onComponentClicked = async function onComponentClicked(componentName) {
  const code = APB.step2.activeDeliverableCode || getActiveDeliverableCode();
  if (!code) return;

  APB.step2.activeComponentName = componentName;

  try {
    const res = await fetch(`/api/l3_for?deliverable_code=${encodeURIComponent(code)}&component_name=${encodeURIComponent(componentName)}`);
    const json = await res.json();
    const items = (json.items || json.l2 || []).map(item => 
      typeof item === 'string' ? item : (item.Task_Label || item.name || '')
    ).filter(Boolean); // Filter out empty strings or nulls

    renderL2Checklist(code, componentName, items);
  } catch (e) {
    console.error('Error loading L2:', e);
    const l2ListEl = document.getElementById('s2-l2-list');
    if (l2ListEl) {
      l2ListEl.innerHTML = '<p style="color: red;">Error loading subtasks</p>';
    }
  }
}

// Render L2 checklist
function renderL2Checklist(code, componentName, items) {
  const listEl = document.getElementById('s2-l2-list');
  if (!listEl) return;

  if (items.length === 0) {
    listEl.innerHTML = '<p style="color: var(--muted); text-align: center; padding-top: 40px; font-size: 0.9em;">No L2 subtasks</p>';
    return;
  }

  const key = `${code}::${componentName}`;

  // Initialize selection for this key if it doesn't exist
  if (!S2.selectedL2ByKey[key] || !(S2.selectedL2ByKey[key] instanceof Set)) {
    S2.selectedL2ByKey[key] = new Set(items);
  }
  const selectedSet = S2.selectedL2ByKey[key];

  // Render checkboxes
  listEl.innerHTML = items.map(label => `
    <label style="display: flex; align-items: start; gap: 8px; padding: 6px 8px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,.05);">
      <input type="checkbox" class="l2-checkbox" data-key="${key}" data-label="${label}"
             ${selectedSet.has(label) ? 'checked' : ''} style="margin-top: 3px; cursor: pointer;">
      <div style="flex: 1;">
        <span style="font-size: 0.9em;">${label}</span>
      </div>
    </label>
  `).join('');

  // Attach handlers
  listEl.querySelectorAll('.l2-checkbox').forEach(cb => {
    cb.addEventListener('change', e => {
      const label = e.target.dataset.label;
      const key = e.target.dataset.key;

      // Ensure Set exists for the key
      if (!S2.selectedL2ByKey[key]) {
        S2.selectedL2ByKey[key] = new Set();
      }

      if (e.target.checked) {
        S2.selectedL2ByKey[key].add(label);
      } else {
        S2.selectedL2ByKey[key].delete(label);
      }

      updateSummaryCounts();
    });
  });

  updateSummaryCounts();
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
      body: JSON.JSON.stringify(payload)
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

// ========== New Features: Import, Second Scenario, Final Ship ==========

// Import Previous Project functionality
document.addEventListener('DOMContentLoaded', () => {
  const importBtn = document.getElementById('btnImportProject');
  const importFile = document.getElementById('importFile');

  if (importBtn && importFile) {
    importBtn.addEventListener('click', () => {
      importFile.click();
    });

    importFile.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);

      try {
        importBtn.textContent = 'Importing...';
        importBtn.disabled = true;

        const response = await fetch('/api/project/import', {
          method: 'POST',
          body: formData
        });

        const result = await response.json();

        if (result.success) {
          alert(`✅ Project imported successfully!\n\nProject: ${result.project_name}\nDeliverables: ${result.deliverables_count}\nTotal Hours: ${result.total_hours}\nTotal Price: $${result.total_price}`);

          // Store imported scenario and refresh UI
          if (result.import_id && result.scenario) {
            window.SCENARIOS = window.SCENARIOS || {};
            window.SCENARIOS.imported = result.scenario;

            // Populate Step 2 with imported deliverables
            if (result.scenario.items) {
              const codes = result.scenario.items.map(item => item.deliverable_code);
              codes.forEach(code => {
                if (S2.selectedCodes) S2.selectedCodes.add(code);
              });

              // Refresh Step 2 display
              if (typeof s2RenderDelivs === 'function') {
                s2RenderDelivs();
              }
            }

            // Show Step 2
            document.getElementById('step2').style.display = 'block';
          }
        } else {
          alert('❌ Import failed: ' + (result.detail || result.message || 'Unknown error'));
        }
      } catch (err) {
        alert(`❌ Import error: ${err.message}`);
      } finally {
        importBtn.textContent = 'Import XML/Excel';
        importBtn.disabled = false;
        importFile.value = ''; // Reset file input
      }
    });
  }

  // Build Second Scenario functionality
  const buildSecondBtn = document.getElementById('btn-build-second-scenario');
  const compareBtn = document.getElementById('btn-compare-versions');
  const versionList = document.getElementById('version-list');
  const versionItems = document.getElementById('version-items');

  if (buildSecondBtn) {
    buildSecondBtn.addEventListener('click', async () => {
      if (!window.SCENARIOS || !window.SCENARIOS.A) {
        alert('Please build a scenario first before creating a second version.');
        return;
      }

      try {
        buildSecondBtn.textContent = 'Creating Version 2...';
        buildSecondBtn.disabled = true;

        const response = await fetch('/api/scenario/duplicate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.JSON.stringify({
            scenario_id: 'scenario_a',
            scenario_data: window.SCENARIOS.A,
            version_name: 'Version 2 - Alternative'
          })
        });

        const result = await response.json();

        if (result.success) {
          alert(`✅ Version 2 created successfully!\n\nVersion ID: ${result.version_id}\nYou can now modify this version independently.`);

          // Store the new version
          window.SCENARIOS.A_version2 = window.SCENARIOS.A; // Store as a copy, modifications will be separate

          // Update version list display
          if (versionList && versionItems) {
            versionList.style.display = 'block';
            versionItems.innerHTML += `
              <div style="padding: 8px; margin: 4px 0; background: rgba(255,255,255,0.05); border-radius: 4px;">
                <strong>Version 2 - Alternative</strong> - Created ${new Date().toLocaleDateString()}
              </div>
            `;
          }
        }
      } catch (err) {
        alert(`❌ Error creating second scenario: ${err.message}`);
      } finally {
        buildSecondBtn.textContent = 'Create Version 2';
        buildSecondBtn.disabled = false;
      }
    });
  }

  if (compareBtn) {
    compareBtn.addEventListener('click', async () => {
      try {
        const response = await fetch('/api/scenario/versions/scenario_a');
        const result = await response.json();

        if (result.versions && result.versions.length > 0) {
          let versionInfo = 'Available Versions:\n\n';
          versionInfo += 'Version 1 (Original)\n';
          result.versions.forEach(v => {
            versionInfo += `${v.version_name} - Created ${new Date(v.created_date).toLocaleDateString()}\n`;
          });
          alert(versionInfo);
        } else {
          alert('No alternative versions found. Create a second scenario first.');
        }
      } catch (err) {
        alert(`❌ Error fetching versions: ${err.message}`);
      }
    });
  }

  // Final Ship functionality
  const finalShipBtn = document.getElementById('btn-final-ship');
  const finalShipStatus = document.getElementById('final-ship-status');
  const finalShipDownloads = document.getElementById('final-ship-downloads');

  if (finalShipBtn) {
    finalShipBtn.addEventListener('click', async () => {
      if (!window.SCENARIOS || !window.SCENARIOS.A) {
        alert('Please build at least Scenario A before final shipping.');
        return;
      }

      const projectName = document.getElementById('projectName')?.value || 
                          sessionStorage.getItem('apb.uploadTitle') || 
                          'Project Export';

      const confirmShip = confirm(`🚢 FINAL SHIP CONFIRMATION\n\nThis will:\n• Lock all scenario data\n• Generate comprehensive exports\n• Prevent further edits\n\nProject: ${projectName}\n\nProceed with final ship?`);

      if (!confirmShip) return;

      try {
        finalShipBtn.textContent = 'Processing Final Ship...';
        finalShipBtn.disabled = true;

        const payload = {
          scenario_a: window.SCENARIOS.A,
          scenario_b: window.SCENARIOS.B || null,
          scenario_c: window.SCENARIOS.C || null,
          project_name: projectName,
          notes: 'Final ship from UI'
        };

        const response = await fetch('/api/project/final_ship', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.JSON.stringify(payload)
        });

        const result = await response.json();

        if (result.success) {
          // Show success status
          if (finalShipStatus) {
            finalShipStatus.style.display = 'block';
          }

          // Add download links
          if (finalShipDownloads) {
            finalShipDownloads.innerHTML = `
              <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                ${result.exports.excel ? `<a href="${result.download_url}" class="btn-primary" style="text-decoration: none;">📥 Download Complete Package</a>` : ''}
                <span style="color: var(--muted);">Ship ID: ${result.ship_id}</span>
              </div>
              <div style="margin-top: 8px; font-size: 0.85em; color: var(--muted);">
                Shipped on ${new Date(result.shipped_date).toLocaleDateString()}
              </div>
            `;
          }

          // Disable editing controls
          finalShipBtn.style.display = 'none';
          document.querySelectorAll('#step3 button, #step4 button').forEach(btn => {
            if (!btn.id.includes('export')) {
              btn.disabled = true;
            }
          });

          alert(`✅ PROJECT SHIPPED SUCCESSFULLY!\n\nShip ID: ${result.ship_id}\nAll data has been locked and exported.\n\nYou can download the complete package using the link provided.`);
        } else {
          alert('❌ Final ship failed: ' + (result.detail || result.message || 'Unknown error'));
        }
      } catch (err) {
        alert(`❌ Final ship error: ${err.message}`);
      } finally {
        if (!finalShipStatus || finalShipStatus.style.display === 'none') {
          finalShipBtn.textContent = '🔒 Final Ship Project';
          finalShipBtn.disabled = false;
        }
      }
    });
  }
});

// Session management UI functions
function toggleSessionInfo() {
  const sessionInfo = document.getElementById('session-info');
  if (sessionInfo) {
    sessionInfo.style.display = sessionInfo.style.display === 'none' ? 'block' : 'none';

    // Update session display
    if (sessionInfo.style.display === 'block' && window.ScenarioManager) {
      const sessionIdDisplay = document.getElementById('session-id-display');
      const lastSavedDisplay = document.getElementById('last-saved-display');

      if (sessionIdDisplay) {
        sessionIdDisplay.textContent = window.ScenarioManager.state.sessionId || 'None';
      }

      if (lastSavedDisplay) {
        if (window.ScenarioManager.state.lastSaved) {
          const date = new Date(window.ScenarioManager.state.lastSaved);
          lastSavedDisplay.textContent = 'Last saved: ' + date.toLocaleTimeString();
        } else {
          lastSavedDisplay.textContent = 'Not saved yet';
        }
      }
    }
  }
}

function startNewSession() {
  if (confirm('Start a new session? This will clear all current data.')) {
    // Clear current data and start fresh
    SessionManager.startNewSession();

    // Clear ScenarioManager state
    if (window.ScenarioManager) {
      window.ScenarioManager.clear();
      window.ScenarioManager.state.sessionId = SessionManager.getCurrentSessionId();
      window.ScenarioManager.saveToBackend();
    }

    // Reload the page to start fresh
    window.location.reload();
  }
}

function clearAllData() {
  if (confirm('Clear all data? This cannot be undone.')) {
    clearAllDataWithConfirmation();
  }
}

// Update session info periodically
setInterval(() => {
  const sessionInfo = document.getElementById('session-info');
  if (sessionInfo && sessionInfo.style.display === 'block') {
    toggleSessionInfo(); // Refresh display
    toggleSessionInfo(); // Show again
  }
}, 30000); // Every 30 seconds

window.toggleSessionInfo = toggleSessionInfo;
window.startNewSession = startNewSession;
window.clearAllData = clearAllData;

window.addEventListener("load", boot);

// LEARN button functionality (Learning Brain integration)
(function attachLearn(){
  const btn = document.getElementById('learnBtn');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const rfpText = (window.APP?.rfpText) || "";
    const selected = Array.from(window.APB?.step2?.selectedCodes || []);
    const components = (window.APB?.selectionStore?.componentsByDeliv)
      ? Object.fromEntries(window.APB.selectionStore.componentsByDeliv) : {};
    try {
      const res = await fetch("/api/brain/learn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.JSON.stringify({
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