// ================================================================================
// Toast Notification Utility
// ================================================================================
function showToast(message, type = 'info') {
  // Create toast container if it doesn't exist
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = `
      position: fixed; bottom: 20px; right: 20px; z-index: 10000;
      display: flex; flex-direction: column; gap: 10px;
    `;
    document.body.appendChild(container);
  }
  
  // Create toast element
  const toast = document.createElement('div');
  const bgColor = type === 'success' ? 'rgba(16, 185, 129, 0.95)' : 
                  type === 'error' ? 'rgba(220, 38, 38, 0.95)' : 
                  'rgba(139, 92, 246, 0.95)';
  
  toast.style.cssText = `
    padding: 12px 20px; background: ${bgColor}; color: white;
    border-radius: 8px; font-weight: 500; font-size: 0.9em;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 350px;
    animation: slideIn 0.3s ease-out;
  `;
  toast.textContent = message;
  
  container.appendChild(toast);
  
  // Auto-remove after 3 seconds
  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease-in';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Add toast animations to head
if (!document.getElementById('toast-styles')) {
  const style = document.createElement('style');
  style.id = 'toast-styles';
  style.textContent = `
    @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
    @keyframes slideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(100%); opacity: 0; } }
  `;
  document.head.appendChild(style);
}

// ================================================================================
// Theme Management - Dark/Light Mode Toggle
// ================================================================================
function toggleTheme() {
  const html = document.documentElement;
  const currentTheme = html.getAttribute('data-theme');
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  
  html.setAttribute('data-theme', newTheme);
  localStorage.setItem('apb.theme', newTheme);
  
  // Update toggle button icon
  const toggleBtn = document.getElementById('theme-toggle');
  if (toggleBtn) {
    toggleBtn.textContent = newTheme === 'light' ? '🌙' : '☀️';
  }
  
  // Apply theme to Gantt chart if it exists
  applyGanttTheme();
}

// FEATURE: Apply dark/light theme to Gantt chart (override Frappe's inline styles)
function applyGanttTheme() {
  const container = document.getElementById('gantt-chart');
  if (!container) return;
  
  const currentTheme = document.documentElement.getAttribute('data-theme');
  const isDark = currentTheme !== 'light';
  
  // Override SVG background colors
  const svg = container.querySelector('svg');
  if (svg) {
    // Set main SVG background
    svg.style.backgroundColor = isDark ? '#151a22' : '#ffffff';
    
    // Update grid background
    const gridBackground = svg.querySelector('.grid-background');
    if (gridBackground) {
      gridBackground.setAttribute('fill', isDark ? '#151a22' : '#ffffff');
    }
    
    // Update grid header
    const gridHeader = svg.querySelector('.grid-header');
    if (gridHeader) {
      gridHeader.setAttribute('fill', isDark ? '#151a22' : '#f7fafc');
      gridHeader.setAttribute('stroke', isDark ? '#232a35' : '#e2e8f0');
    }
    
    // Update grid rows
    const gridRows = svg.querySelectorAll('.grid-row');
    gridRows.forEach((row, index) => {
      if (index % 2 === 1) {
        row.setAttribute('fill', isDark ? 'rgba(255, 255, 255, 0.02)' : '#f7fafc');
      } else {
        row.setAttribute('fill', isDark ? '#151a22' : '#ffffff');
      }
    });
    
    // Update all text elements
    const textElements = svg.querySelectorAll('text');
    textElements.forEach(text => {
      text.setAttribute('fill', isDark ? '#e6eaf2' : '#1a202c');
    });
    
    // Update today highlight
    const todayHighlight = svg.querySelector('.today-highlight');
    if (todayHighlight) {
      todayHighlight.setAttribute('fill', isDark ? 'rgba(106, 163, 255, 0.1)' : 'rgba(49, 130, 206, 0.1)');
    }
    
    // Update arrows if any
    const arrows = svg.querySelectorAll('.arrow');
    arrows.forEach(arrow => {
      arrow.setAttribute('stroke', isDark ? '#232a35' : '#e2e8f0');
    });
  }
}

// Initialize theme on page load
(function initTheme() {
  const savedTheme = localStorage.getItem('apb.theme') || 'dark';
  const html = document.documentElement;
  
  if (savedTheme === 'light') {
    html.setAttribute('data-theme', 'light');
    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
      toggleBtn.textContent = '🌙';
    }
  }
})();

// ================================================================================
// Global Variables and State
// ================================================================================
let OPTIONS = null;       // cached /api/options
let SCENARIOS = null;     // last built scenarios (A & B)
let DELIVERABLES = [];    // [{deliverable_code, deliverable, category}]

// Centralized scenario accessors to sync local variable with window.SCENARIOS
// This prevents the "build a scenario first" bug where Step-2 sets window.SCENARIOS
// but Step-3 functions check the local SCENARIOS variable which stays null
const getScenarioState = () => window.SCENARIOS ?? SCENARIOS;
const setScenarioState = (value) => { 
  SCENARIOS = value; 
  window.SCENARIOS = value; 
};
window.getScenarioState = getScenarioState;
window.setScenarioState = setScenarioState;
let DELIV_INDEX = {};     // code -> deliverable object lookup for fast rendering
let DELIV_INDEX_LO = {};  // lowercase code lookup for defensive matching

// ================================================================================
// Session Management - Data Isolation Between RFPs
// ================================================================================
const SessionManager = {
  generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  },
  
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
      window.pricingData.customHours.clear();
      window.pricingData.customRates.clear();
      window.pricingData.retainerMonths.clear();
      window.pricingData.originalScenario = null;
      window.pricingData.rebuildVersion = 0;
    }
    if (window.pricingDataEnhanced) {
      window.pricingDataEnhanced.cadenceTypes.clear();
      window.pricingDataEnhanced.periodsCount.clear();
      window.pricingDataEnhanced.editMode.clear();
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
        analysisMode: 'fast',
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
  
  // Initialize PDF download button event listeners
  initializePDFDownloadButton();
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
    await applyIndustryTemplate();
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
      body: JSON.stringify({
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
      sessionStorage.setItem('industry_deliverables', JSON.stringify(industryDeliverables));
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
    
    // Hide all steps except Step 1
    document.getElementById('step1').style.display = 'block';
    document.getElementById('step2').style.display = 'none';
    const step3 = document.getElementById('step3');
    if (step3) step3.style.display = 'none';
    const step4 = document.getElementById('step4');
    if (step4) step4.style.display = 'none';
    
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

// ISSUE 3: Retainer Options Functions

// ISSUE FIX 3: Add global retainer suggestions function
async function askAIForRetainerSuggestions() {
  const codes = Array.from(selectionStore.deliverables);
  
  if (codes.length === 0) {
    alert('Please select deliverables first');
    return;
  }
  
  const rfpText = APB.step2?.rfpText || 
                 sessionStorage.getItem('rfpContent') || 
                 sessionStorage.getItem('apb.rfp_text') ||
                 document.getElementById('rfpText')?.value || '';
  
  if (!rfpText) {
    alert('Please provide RFP text before using AI suggestions');
    return;
  }
  
  // Build deliverables array with proper format
  const deliverables = codes.map(code => ({
    code: code,
    name: labelFor(code), // Get the label/name
    type: "DELIVERABLE"
  }));
  
  // Show loading on button
  const btn = document.getElementById('btn-global-retainer-suggest');
  if (btn) {
    btn.disabled = true;
    btn.textContent = '🔄 Analyzing...';
  }
  
  try {
    const res = await fetch('/api/pricing/retainer_suggest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        deliverable_codes: codes,  // Backend expects just the codes array
        rfp_text: rfpText
      })
    });
    
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({error: 'Unknown error'}));
      throw new Error(errorData.error || `Server error: ${res.status}`);
    }
    
    const data = await res.json();
    const suggestions = data.suggestions || [];
    
    // Backend only returns items that SHOULD be retainers
    // First, mark all selected codes as PROJECT (default)
    codes.forEach(code => {
      pricingData.deliverableTypes.set(code, 'PROJECT');
      pricingData.retainers.delete(code);
    });
    
    // Then apply retainer suggestions
    let retainerCount = 0;
    suggestions.forEach(suggestion => {
      // Defensive: support both suggested_months and recommended_months field names
      const months = suggestion.suggested_months || suggestion.recommended_months || 12;
      pricingData.deliverableTypes.set(suggestion.deliverable_code, 'RETAINER');
      pricingData.retainers.set(suggestion.deliverable_code, months);
      retainerCount++;
    });
    
    // Update UI to show retainer indicators
    if (window.renderDeliverablesPanel) {
      renderDeliverablesPanel();
    }
    
    // Show success message with details
    if (retainerCount > 0) {
      const retainerNames = suggestions.map(s => {
        const months = s.suggested_months || s.recommended_months || 12;
        return `  • ${s.deliverable_name} (${months} months)`;
      }).join('\n');
      alert(`✅ AI Retainer Analysis Complete!\n\n${retainerCount} of ${codes.length} deliverables suggested as retainers:\n\n${retainerNames}\n\nRetainer items will be marked in the deliverables list.`);
    } else {
      alert(`✅ Analysis complete!\n\nAll ${codes.length} items are best suited as one-time projects.`);
    }
  } catch (error) {
    console.error('[RETAINER] Failed to get suggestions:', error);
    
    // Show user-friendly error message
    let errorMsg = 'Failed to get AI suggestions.';
    if (error.message) {
      errorMsg += `\n\nDetails: ${error.message}`;
    }
    errorMsg += '\n\nPlease ensure you have:';
    errorMsg += '\n• Selected deliverables in Step 2';
    errorMsg += '\n• Provided RFP text in Step 1';
    errorMsg += '\n\nCheck the console (F12) for technical details.';
    
    alert(`❌ ${errorMsg}`);
  } finally {
    // Reset button
    if (btn) {
      btn.disabled = false;
      btn.textContent = '🤖 AI Suggest Retainer Items';
    }
  }
}

// Export the function globally
window.askAIForRetainerSuggestions = askAIForRetainerSuggestions;

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
  
  // FIX: Update pricing displays immediately after toggle
  updatePricingTable();
  updatePricingSummary();
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
      body: JSON.stringify({
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
            body: JSON.stringify({
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
      body: JSON.stringify({
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
// ISSUE FIX 3: Make currentTimelineTasks accessible globally for PDF export
window.currentTimelineTasks = [];
let currentTimelineTasks = window.currentTimelineTasks;
let timelineReasoning = null;
// CRITICAL FIX: Prevent reentrancy freeze when dragging tasks
let isSyncing = false;

// GPT-5.1 Pro: Timeline metrics state for real-time updates
let timelineMetrics = null;
let resourceRisk = null;

// GPT-5.1 Pro: Debounced timeline save function for real-time metrics updates
const saveTimelineWithMetrics = debounce(async function(tasks) {
  const session_id = window.SessionManager ? window.SessionManager.getCurrentSessionId() : null;
  if (!session_id || !tasks || tasks.length === 0) {
    console.log('[Timeline Metrics] Skipping save - no session or tasks');
    return;
  }
  
  try {
    console.log('[Timeline Metrics] Saving timeline with', tasks.length, 'tasks');
    
    const existingMetadata = window.ScenarioStore?.state?.timelineMetadata || {};
    const mergedMetadata = {
      ...existingMetadata,
      hours_per_day: window.ScenarioStore?.state?.hoursPerDay || existingMetadata.hours_per_day || 6
    };
    
    const response = await fetch('/api/timeline/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: session_id,
        tasks: tasks,
        metadata: mergedMetadata,
        reasoning: timelineReasoning || {}
      })
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log('[Timeline Metrics] Save response:', result.metrics);
      
      timelineMetrics = result.metrics || null;
      resourceRisk = result.metrics?.resource_risk || null;
      
      updateTimelineHeaderChips();
      renderResourceRiskPanel();
    } else {
      console.warn('[Timeline Metrics] Save failed:', await response.text());
    }
  } catch (error) {
    console.error('[Timeline Metrics] Error saving timeline:', error);
  }
}, 400);

// GPT-5.1 Pro: Update header chips with timeline metrics
function updateTimelineHeaderChips() {
  const durationEl = document.getElementById('meta-duration');
  const tasksEl = document.getElementById('meta-tasks');
  const criticalEl = document.getElementById('meta-critical');
  const departmentsEl = document.getElementById('meta-departments');
  const metadataContainer = document.getElementById('timeline-metadata');
  
  if (timelineMetrics) {
    if (metadataContainer) metadataContainer.style.display = 'block';
    if (durationEl) durationEl.textContent = `${timelineMetrics.total_duration_days || 0} days`;
    if (tasksEl) tasksEl.textContent = timelineMetrics.total_tasks || 0;
    if (criticalEl) criticalEl.textContent = timelineMetrics.critical_path_count || 0;
    if (departmentsEl) departmentsEl.textContent = timelineMetrics.departments_count || '-';
  }
}

// GPT-5.1 Pro: Render Resource Risk Management panel
function renderResourceRiskPanel() {
  const section = document.getElementById('resource-risk-section');
  const summary = document.getElementById('resource-risk-summary');
  const tbody = document.getElementById('resource-risk-tbody');
  
  if (!section) return;
  
  section.style.display = 'block';
  
  if (!resourceRisk || !resourceRisk.items || resourceRisk.items.length === 0) {
    if (summary) {
      summary.innerHTML = `<span style="color: var(--muted);">No resource idle-time risks detected. Resources are efficiently allocated across the timeline.</span>`;
      summary.style.background = 'rgba(16, 185, 129, 0.1)';
      summary.style.borderColor = 'rgba(16, 185, 129, 0.2)';
    }
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="5" style="padding: 20px; text-align: center; color: var(--muted);">All resources are optimally scheduled with no idle gaps.</td></tr>`;
    }
    return;
  }
  
  const highRiskCount = resourceRisk.summary?.high_risk_count || 0;
  const totalIdleCost = resourceRisk.summary?.total_idle_cost || 0;
  const totalRiskCount = resourceRisk.items.length;
  
  if (summary) {
    if (highRiskCount > 0) {
      summary.innerHTML = `<strong>${highRiskCount} high-risk resource conflicts detected.</strong> Total potential idle cost: <strong>$${totalIdleCost.toLocaleString()}</strong>`;
      summary.style.background = 'rgba(239, 68, 68, 0.15)';
      summary.style.borderColor = 'rgba(239, 68, 68, 0.3)';
    } else {
      summary.innerHTML = `<span style="color: #10b981;">No high-risk resource conflicts.</span> ${totalRiskCount} resource(s) with idle time identified. Review below.`;
      summary.style.background = 'rgba(16, 185, 129, 0.1)';
      summary.style.borderColor = 'rgba(16, 185, 129, 0.2)';
    }
  }
  
  if (tbody) {
    const sortedItems = [...resourceRisk.items].sort((a, b) => b.idle_cost - a.idle_cost);
    
    tbody.innerHTML = sortedItems.map(item => {
      const riskColor = item.risk_level === 'High' ? '#ef4444' : 
                        item.risk_level === 'Medium' ? '#f59e0b' : '#10b981';
      const riskBg = item.risk_level === 'High' ? 'rgba(239, 68, 68, 0.2)' : 
                     item.risk_level === 'Medium' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)';
      
      return `<tr>
        <td style="padding: 10px; border-bottom: 1px solid var(--border);">${item.resource}</td>
        <td style="padding: 10px; border-bottom: 1px solid var(--border);">${item.waiting_days} days</td>
        <td style="padding: 10px; border-bottom: 1px solid var(--border);">$${item.idle_cost.toLocaleString()}</td>
        <td style="padding: 10px; border-bottom: 1px solid var(--border);">
          <span style="background: ${riskBg}; color: ${riskColor}; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: 600;">${item.risk_level}</span>
        </td>
        <td style="padding: 10px; border-bottom: 1px solid var(--border); font-size: 0.9em; color: var(--text-muted);">${item.recommendation}</td>
      </tr>`;
    }).join('');
  }
}

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
    // Initialize Frappe Gantt with drag-enabled configuration
    const ganttOptions = {
      view_mode: document.getElementById('gantt-view-mode')?.value || 'Day',
      date_format: 'YYYY-MM-DD',
      popup_trigger: 'click',
      language: 'en',
      readonly: false,           // Enable editing
      readonly_dates: false,     // Enable date dragging/resizing
      readonly_progress: false,  // Enable progress bar adjustment
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
      on_date_change: async function(task, start, end) {
        // CRITICAL FIX: Prevent reentrancy freeze - exit if already syncing
        if (isSyncing) {
          console.log('[Gantt] Skipping date change (already syncing)');
          return;
        }
        
        isSyncing = true;
        try {
          console.log('Task date changed:', task.name, start, end);
          
          // Update the task in our local state
          const taskIndex = currentTimelineTasks.findIndex(t => t.id === task.id);
          if (taskIndex >= 0) {
            currentTimelineTasks[taskIndex].start = start.toISOString().split('T')[0];
            currentTimelineTasks[taskIndex].end = end.toISOString().split('T')[0];
          }
          
          // Sync to backend SCENARIO_STORE (GPT-5's plan: call /api/timeline/update_task)
          try {
            const duration_days = window.businessDaysInclusive ? window.businessDaysInclusive(start, end) : Math.ceil((end - start) / (1000 * 60 * 60 * 24));
            // Get fresh session_id directly from SessionManager (no caching)
            const session_id = window.SessionManager ? window.SessionManager.getCurrentSessionId() : null;
            
            if (session_id && task.id) {
              const response = await fetch('/api/timeline/update_task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  session_id: session_id,
                  wbs_id: task.id,
                  start_date: start.toISOString().split('T')[0],
                  end_date: end.toISOString().split('T')[0],
                  duration_days: duration_days,
                  hours_per_day: window.ScenarioStore?.state?.hoursPerDay || 8
                })
              });
              
              if (response.ok) {
                const result = await response.json();
                console.log('[Gantt] Task updated in backend SCENARIO_STORE:', result);
                // TODO: Refresh pricing table with result.totals if needed
              } else {
                console.warn('[Gantt] Failed to sync task to backend:', await response.text());
              }
            }
          } catch (error) {
            console.error('[Gantt] Error syncing task to backend:', error);
          }
          
          // Show save button
          const saveBtn = document.getElementById('btn-save-timeline');
          if (saveBtn) saveBtn.style.display = '';
          
          // GPT-5.1 Pro: Trigger debounced full timeline save for metrics updates
          saveTimelineWithMetrics(currentTimelineTasks);
        } finally {
          // CRITICAL FIX: Always release lock, even if error occurs
          isSyncing = false;
        }
      },
      on_progress_change: function(task, progress) {
        console.log('Task progress changed:', task.name, progress);
      },
      on_view_change: function(mode) {
        console.log('View mode changed to:', mode);
      }
    };
    
    // Debug: Log options to verify callback exists
    console.log('[Gantt Init] Creating Gantt with options. on_date_change exists?', typeof ganttOptions.on_date_change === 'function');
    
    // Create Gantt instance
    ganttChart = new Gantt(container, tasks, ganttOptions);
    
    // Apply custom classes for department colors and critical path, and add hover tooltips
    setTimeout(() => {
      console.log('[Gantt Tooltips] Starting tooltip application for', tasks.length, 'tasks');
      console.log('[Gantt Tooltips] Container:', container);
      console.log('[Gantt Tooltips] All .bar elements:', container.querySelectorAll('.bar').length);
      console.log('[Gantt Tooltips] All .bar-wrapper elements:', container.querySelectorAll('.bar-wrapper').length);
      
      let tooltipsAdded = 0;
      tasks.forEach((task, index) => {
        // Try multiple selectors to find the bar element (Frappe Gantt structure varies)
        let taskElement = container.querySelector(`.bar[data-id="${task.id}"]`);
        if (!taskElement) {
          taskElement = container.querySelector(`[data-id="${task.id}"]`);
        }
        if (!taskElement) {
          // Try finding by text content
          const allBars = container.querySelectorAll('.bar');
          taskElement = Array.from(allBars).find(bar => {
            const barWrapper = bar.closest('.bar-wrapper');
            const label = barWrapper?.querySelector('.bar-label');
            return label?.textContent?.trim() === task.name;
          });
        }
        
        if (taskElement) {
          // Add department class
          if (task.custom_class) {
            taskElement.classList.add(task.custom_class);
          }
          // Add critical path class
          if (task.critical_path) {
            taskElement.classList.add('critical-path');
          }
          
          // FEATURE: Add hover tooltip showing start/end dates and duration
          const taskData = tasks.find(t => t.id === task.id);
          if (taskData) {
            const duration = calculateDuration(taskData.start, taskData.end);
            const tooltipText = `${taskData.name} | Start: ${taskData.start} | End: ${taskData.end} | Duration: ${duration} days`;
            
            // Try to add tooltip to both the bar and its wrapper
            taskElement.setAttribute('title', tooltipText);
            taskElement.style.cursor = 'pointer';
            
            const barWrapper = taskElement.closest('.bar-wrapper');
            if (barWrapper) {
              barWrapper.setAttribute('title', tooltipText);
              barWrapper.style.cursor = 'pointer';
            }
            
            tooltipsAdded++;
            if (index < 3) {
              console.log('[Gantt Tooltips] Added tooltip to task:', task.name, '| Element:', taskElement);
            }
          }
        } else {
          if (index < 3) {
            console.log('[Gantt Tooltips] Could not find element for task:', task.name, '| ID:', task.id);
          }
        }
      });
      
      console.log('[Gantt Tooltips] ✅ Added tooltips to', tooltipsAdded, 'out of', tasks.length, 'tasks');
      
      // Apply Gantt dark mode if theme is dark
      applyGanttTheme();
      
      // Show PDF download button after Gantt is successfully rendered
      showPDFDownloadButton();
    }, 500);
    
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
  if (window.businessDaysInclusive) {
    return window.businessDaysInclusive(startDate, endDate);
  }
  return Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
}

// ================================================================================
// Gantt Chart PDF Export Functions
// ================================================================================

// Show PDF button after Gantt chart is successfully rendered
function showPDFDownloadButton() {
  console.log('[PDF] showPDFDownloadButton() called');
  const pdfButton = document.getElementById('gantt-pdf-button');
  console.log('[PDF] Button element found:', !!pdfButton);
  
  if (pdfButton) {
    pdfButton.style.display = 'block';
    console.log('[PDF] ✅ PDF download button now visible (fixed position, z-index: 10000)');
  } else {
    console.error('[PDF] ❌ PDF button element not found in DOM');
  }
}

// Initialize PDF download button event listeners
function initializePDFDownloadButton() {
  const downloadBtn = document.getElementById('pdf-download-btn');
  const dropdown = document.getElementById('pdf-dropdown');
  const pdfOptions = document.querySelectorAll('.pdf-option');
  
  if (!downloadBtn || !dropdown) return;
  
  // Toggle dropdown on button click
  downloadBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
  });
  
  // Close dropdown when clicking outside
  document.addEventListener('click', function() {
    dropdown.style.display = 'none';
  });
  
  // Prevent dropdown from closing when clicking inside it
  dropdown.addEventListener('click', function(e) {
    e.stopPropagation();
  });
  
  // Handle PDF option selection
  pdfOptions.forEach(option => {
    option.addEventListener('click', function() {
      const view = this.getAttribute('data-view');
      dropdown.style.display = 'none';
      
      // Generate PDF based on selected view
      if (view === 'daily') {
        generateDailyPDF();
      } else if (view === 'weekly') {
        generateWeeklyPDF();
      } else if (view === 'monthly') {
        generateMonthlyPDF();
      }
    });
    
    // Add hover effect
    option.addEventListener('mouseenter', function() {
      this.style.background = 'rgba(139, 92, 246, 0.2)';
    });
    option.addEventListener('mouseleave', function() {
      this.style.background = 'transparent';
    });
  });
}

// Helper function to get project info
function getProjectInfo() {
  const projectNameInput = document.getElementById('projectName');
  const projectName = projectNameInput ? projectNameInput.value || 'Untitled Project' : 'Untitled Project';
  
  // Get date range from tasks
  if (!window.currentTimelineTasks || window.currentTimelineTasks.length === 0) {
    return {
      name: projectName,
      startDate: new Date().toISOString().split('T')[0],
      endDate: new Date().toISOString().split('T')[0]
    };
  }
  
  const tasks = window.currentTimelineTasks;
  const dates = tasks.map(t => new Date(t.start)).concat(tasks.map(t => new Date(t.end)));
  const minDate = new Date(Math.min(...dates));
  const maxDate = new Date(Math.max(...dates));
  
  return {
    name: projectName,
    startDate: minDate.toISOString().split('T')[0],
    endDate: maxDate.toISOString().split('T')[0]
  };
}

// Helper function to format date for display
function formatDate(dateStr) {
  const date = new Date(dateStr);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
}

// Helper function to generate date columns for timeline
function generateDateColumns(startDate, endDate, groupBy) {
  const columns = [];
  const start = new Date(startDate);
  const end = new Date(endDate);
  
  if (groupBy === 'day') {
    let current = new Date(start);
    while (current <= end) {
      columns.push({
        date: new Date(current),
        label: `${current.getMonth() + 1}/${current.getDate()}`
      });
      current.setDate(current.getDate() + 1);
    }
  } else if (groupBy === 'week') {
    let current = new Date(start);
    let weekNum = 1;
    while (current <= end) {
      columns.push({
        date: new Date(current),
        label: `W${weekNum}`
      });
      current.setDate(current.getDate() + 7);
      weekNum++;
    }
  } else if (groupBy === 'month') {
    let current = new Date(start.getFullYear(), start.getMonth(), 1);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    while (current <= end) {
      columns.push({
        date: new Date(current),
        label: `${months[current.getMonth()]} ${current.getFullYear()}`
      });
      current.setMonth(current.getMonth() + 1);
    }
  }
  
  return columns;
}

// Generate Daily PDF
function generateDailyPDF() {
  // ISSUE FIX 3: Comprehensive data check with fallback to local currentTimelineTasks
  console.log('[PDF] generateDailyPDF called');
  console.log('[PDF] window.currentTimelineTasks:', window.currentTimelineTasks);
  console.log('[PDF] local currentTimelineTasks:', typeof currentTimelineTasks !== 'undefined' ? currentTimelineTasks : 'undefined');
  
  if (!window.jspdf || !window.jspdf.jsPDF) {
    alert('PDF library not loaded. Please refresh the page and try again.');
    return;
  }
  
  // ISSUE FIX 3: Check both window.currentTimelineTasks and local currentTimelineTasks variable
  const tasks = window.currentTimelineTasks || (typeof currentTimelineTasks !== 'undefined' ? currentTimelineTasks : null) || [];
  
  console.log('[PDF] Resolved tasks array:', tasks);
  console.log('[PDF] Tasks length:', tasks.length);
  
  if (!tasks || tasks.length === 0) {
    console.error('[PDF] No timeline data available after checking all sources');
    console.error('[PDF] - window.currentTimelineTasks:', window.currentTimelineTasks);
    console.error('[PDF] - local currentTimelineTasks:', typeof currentTimelineTasks !== 'undefined' ? currentTimelineTasks : 'undefined');
    alert('No timeline data available. Please generate a timeline first.');
    return;
  }
  
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF('l', 'mm', 'a4'); // Landscape orientation
  const projectInfo = getProjectInfo();
  
  // Title
  doc.setFontSize(16);
  doc.text(projectInfo.name, 15, 15);
  
  // Date range
  doc.setFontSize(10);
  doc.text(`Timeline: ${formatDate(projectInfo.startDate)} - ${formatDate(projectInfo.endDate)}`, 15, 22);
  doc.text('View: Daily', 15, 28);
  
  // Generate date columns
  const dateColumns = generateDateColumns(projectInfo.startDate, projectInfo.endDate, 'day');
  
  // Prepare table data - use resolved tasks array
  const tableData = tasks.map(task => {
    const row = [task.name];
    const taskStart = new Date(task.start);
    const taskEnd = new Date(task.end);
    
    // Add timeline bars for each date column
    dateColumns.forEach(col => {
      const colDate = col.date;
      if (colDate >= taskStart && colDate <= taskEnd) {
        row.push('■'); // Task bar indicator
      } else {
        row.push('');
      }
    });
    
    return row;
  });
  
  // Table headers
  const headers = [['Deliverable', ...dateColumns.map(c => c.label)]];
  
  // Generate table
  doc.autoTable({
    head: headers,
    body: tableData,
    startY: 35,
    theme: 'grid',
    styles: { fontSize: 7, cellPadding: 1.5 },
    headStyles: { fillColor: [102, 126, 234], fontSize: 7 },
    columnStyles: {
      0: { cellWidth: 50, fontStyle: 'bold' }
    },
    margin: { left: 15, right: 15 }
  });
  
  // Save PDF
  doc.save(`${projectInfo.name}_Daily_Timeline.pdf`);
}

// Generate Weekly PDF
function generateWeeklyPDF() {
  // ISSUE FIX 3: Comprehensive data check with fallback to local currentTimelineTasks
  console.log('[PDF] generateWeeklyPDF called');
  console.log('[PDF] window.currentTimelineTasks:', window.currentTimelineTasks);
  console.log('[PDF] local currentTimelineTasks:', typeof currentTimelineTasks !== 'undefined' ? currentTimelineTasks : 'undefined');
  
  if (!window.jspdf || !window.jspdf.jsPDF) {
    alert('PDF library not loaded. Please refresh the page and try again.');
    return;
  }
  
  // ISSUE FIX 3: Check both window.currentTimelineTasks and local currentTimelineTasks variable
  const tasks = window.currentTimelineTasks || (typeof currentTimelineTasks !== 'undefined' ? currentTimelineTasks : null) || [];
  
  console.log('[PDF] Resolved tasks array:', tasks);
  console.log('[PDF] Tasks length:', tasks.length);
  
  if (!tasks || tasks.length === 0) {
    console.error('[PDF] No timeline data available after checking all sources');
    console.error('[PDF] - window.currentTimelineTasks:', window.currentTimelineTasks);
    console.error('[PDF] - local currentTimelineTasks:', typeof currentTimelineTasks !== 'undefined' ? currentTimelineTasks : 'undefined');
    alert('No timeline data available. Please generate a timeline first.');
    return;
  }
  
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF('l', 'mm', 'a4');
  const projectInfo = getProjectInfo();
  
  // Title
  doc.setFontSize(16);
  doc.text(projectInfo.name, 15, 15);
  
  // Date range
  doc.setFontSize(10);
  doc.text(`Timeline: ${formatDate(projectInfo.startDate)} - ${formatDate(projectInfo.endDate)}`, 15, 22);
  doc.text('View: Weekly', 15, 28);
  
  // Generate week columns
  const weekColumns = generateDateColumns(projectInfo.startDate, projectInfo.endDate, 'week');
  
  // Prepare table data - use resolved tasks array
  const tableData = tasks.map(task => {
    const row = [task.name, formatDate(task.start), formatDate(task.end)];
    const taskStart = new Date(task.start);
    const taskEnd = new Date(task.end);
    
    // Add timeline bars for each week
    weekColumns.forEach(col => {
      const weekStart = new Date(col.date);
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekEnd.getDate() + 6);
      
      // Check if task overlaps with this week
      if (taskStart <= weekEnd && taskEnd >= weekStart) {
        row.push('■■'); // Task bar indicator
      } else {
        row.push('');
      }
    });
    
    return row;
  });
  
  // Table headers
  const headers = [['Deliverable', 'Start', 'End', ...weekColumns.map(c => c.label)]];
  
  // Generate table
  doc.autoTable({
    head: headers,
    body: tableData,
    startY: 35,
    theme: 'grid',
    styles: { fontSize: 8, cellPadding: 2 },
    headStyles: { fillColor: [102, 126, 234], fontSize: 8 },
    columnStyles: {
      0: { cellWidth: 45, fontStyle: 'bold' },
      1: { cellWidth: 25 },
      2: { cellWidth: 25 }
    },
    margin: { left: 15, right: 15 }
  });
  
  // Save PDF
  doc.save(`${projectInfo.name}_Weekly_Timeline.pdf`);
}

// Generate Monthly PDF
function generateMonthlyPDF() {
  // ISSUE FIX 3: Comprehensive data check with fallback to local currentTimelineTasks
  console.log('[PDF] generateMonthlyPDF called');
  console.log('[PDF] window.currentTimelineTasks:', window.currentTimelineTasks);
  console.log('[PDF] local currentTimelineTasks:', typeof currentTimelineTasks !== 'undefined' ? currentTimelineTasks : 'undefined');
  
  if (!window.jspdf || !window.jspdf.jsPDF) {
    alert('PDF library not loaded. Please refresh the page and try again.');
    return;
  }
  
  // ISSUE FIX 3: Check both window.currentTimelineTasks and local currentTimelineTasks variable
  const tasks = window.currentTimelineTasks || (typeof currentTimelineTasks !== 'undefined' ? currentTimelineTasks : null) || [];
  
  console.log('[PDF] Resolved tasks array:', tasks);
  console.log('[PDF] Tasks length:', tasks.length);
  
  if (!tasks || tasks.length === 0) {
    console.error('[PDF] No timeline data available after checking all sources');
    console.error('[PDF] - window.currentTimelineTasks:', window.currentTimelineTasks);
    console.error('[PDF] - local currentTimelineTasks:', typeof currentTimelineTasks !== 'undefined' ? currentTimelineTasks : 'undefined');
    alert('No timeline data available. Please generate a timeline first.');
    return;
  }
  
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF('l', 'mm', 'a4');
  const projectInfo = getProjectInfo();
  
  // Title
  doc.setFontSize(16);
  doc.text(projectInfo.name, 15, 15);
  
  // Date range
  doc.setFontSize(10);
  doc.text(`Timeline: ${formatDate(projectInfo.startDate)} - ${formatDate(projectInfo.endDate)}`, 15, 22);
  doc.text('View: Monthly', 15, 28);
  
  // Generate month columns
  const monthColumns = generateDateColumns(projectInfo.startDate, projectInfo.endDate, 'month');
  
  // Prepare table data - use resolved tasks array
  const tableData = tasks.map(task => {
    const row = [task.name, formatDate(task.start), formatDate(task.end), `${task.hours || 0}h`];
    const taskStart = new Date(task.start);
    const taskEnd = new Date(task.end);
    
    // Add timeline bars for each month
    monthColumns.forEach(col => {
      const monthStart = new Date(col.date);
      const monthEnd = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0);
      
      // Check if task overlaps with this month
      if (taskStart <= monthEnd && taskEnd >= monthStart) {
        row.push('■■■'); // Task bar indicator
      } else {
        row.push('');
      }
    });
    
    return row;
  });
  
  // Table headers
  const headers = [['Deliverable', 'Start', 'End', 'Hours', ...monthColumns.map(c => c.label)]];
  
  // Generate table
  doc.autoTable({
    head: headers,
    body: tableData,
    startY: 35,
    theme: 'grid',
    styles: { fontSize: 8, cellPadding: 2 },
    headStyles: { fillColor: [102, 126, 234], fontSize: 8 },
    columnStyles: {
      0: { cellWidth: 50, fontStyle: 'bold' },
      1: { cellWidth: 25 },
      2: { cellWidth: 25 },
      3: { cellWidth: 18 }
    },
    margin: { left: 15, right: 15 }
  });
  
  // Save PDF
  doc.save(`${projectInfo.name}_Monthly_Timeline.pdf`);
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

// Enhanced pricing data store with cadence support
const pricingDataEnhanced = {
  ...pricingData,
  cadenceTypes: new Map(),      // deliverable_code -> 'ONE_TIME' | 'MONTHLY' | 'QUARTERLY' | 'SEMI_ANNUAL'
  periodsCount: new Map(),      // deliverable_code -> number of periods
  editMode: new Map(),          // deliverable_code -> boolean (editing state)
  componentTasks: new Map(),    // deliverable_code -> array of tasks
};

// UNIFIED PRICING TABLE - Fully editable inline version
function updatePricingTable() {
  const container = document.getElementById('pricing-container') || document.getElementById('pricing-tbody')?.parentElement?.parentElement;
  if (!container || !SCENARIOS) return;
  
  const scenario = SCENARIOS.A || SCENARIOS[0];
  if (!scenario || !scenario.items) return;
  
  // Store original scenario on first load
  if (!pricingData.originalScenario) {
    pricingData.originalScenario = JSON.parse(JSON.stringify(scenario));
  }
  
  // Create comprehensive table HTML structure with ALWAYS EDITABLE inputs
  let tableHTML = `
    <div class="unified-pricing-table" style="margin: 20px 0;">
      <h3 style="color: var(--accent); margin-bottom: 16px; font-size: 1.3em;">
        📊 Unified Pricing Details (Direct Edit)
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
          </tr>
        </thead>
        <tbody>
  `;
  
  let grandTotal = 0;
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
    const customRate = pricingData.customRates.get(item.deliverable_code) || item.blended_rate || 210;
    const pricePerPeriod = customHours * customRate;
    const totalPrice = pricePerPeriod * periods;
    
    // Get resource breakdown
    const resources = pricingData.resourceBreakdown.get(item.deliverable_code) || 
                     extractResourceAllocation(item);
    
    // Get tasks list
    const tasks = extractDeliverableTasks(item);
    
    // Update grand total
    grandTotal += totalPrice;
    
    // Determine row background (alternating + highlight for recurring)
    const isRecurring = cadenceType !== 'ONE_TIME';
    const rowBg = isRecurring ? 
      'background: linear-gradient(90deg, rgba(139,92,246,0.05), rgba(139,92,246,0.02));' : 
      (rowIndex % 2 === 0 ? 'background: rgba(255,255,255,0.01);' : 'background: transparent;');
    
    // Main deliverable row - ALWAYS EDITABLE, no edit mode
    tableHTML += `
      <tr data-deliverable="${item.deliverable_code}" data-row-type="deliverable" 
          style="${rowBg} border-bottom: 1px solid rgba(255,255,255,0.1); transition: all 0.2s ease;">
        <td style="padding: 12px; font-weight: 700; color: var(--text);">
          <button onclick="toggleDeliverableExpand('${item.deliverable_code}')" 
                  style="background: transparent; border: none; color: var(--accent); cursor: pointer; padding: 0 8px 0 0; font-size: 0.9em; transition: transform 0.2s;"
                  title="Expand/collapse components">
            <span id="expand-${item.deliverable_code}" style="display: inline-block; transition: transform 0.2s;">▶</span>
          </button>
          <span style="color: ${isRecurring ? 'var(--accent2)' : 'var(--accent)'};">
            ${item.deliverable}
          </span>
        </td>
        <td style="padding: 8px; text-align: center;">
          <select id="cadence-${item.deliverable_code}" 
                  onchange="updateCadenceType('${item.deliverable_code}', this.value)"
                  style="padding: 6px 10px; border: 1px solid rgba(139,92,246,0.5); border-radius: 6px; 
                         background: rgba(139,92,246,0.1); color: var(--text); cursor: pointer; 
                         font-size: 0.85em; width: 100%;">
            <option value="ONE_TIME" ${cadenceType === 'ONE_TIME' ? 'selected' : ''}>One-Time</option>
            <option value="MONTHLY" ${cadenceType === 'MONTHLY' ? 'selected' : ''}>Monthly</option>
            <option value="QUARTERLY" ${cadenceType === 'QUARTERLY' ? 'selected' : ''}>Quarterly</option>
            <option value="SEMI_ANNUAL" ${cadenceType === 'SEMI_ANNUAL' ? 'selected' : ''}>Semi-Annual</option>
          </select>
        </td>
        <td style="padding: 8px; text-align: center;">
          ${cadenceType !== 'ONE_TIME' ? 
            `<input type="number" id="periods-${item.deliverable_code}" value="${periods}" 
                    min="1" max="36" step="1"
                    onchange="updatePeriods('${item.deliverable_code}', this.value)"
                    style="width: 70px; padding: 6px; border: 1px solid rgba(139,92,246,0.3); 
                           border-radius: 4px; background: rgba(139,92,246,0.05); 
                           color: var(--text); text-align: center; font-weight: 500;" />` :
            '<span style="color: var(--muted);">-</span>'}
        </td>
        <td style="padding: 8px; text-align: center;">
          <input type="number" id="hours-${item.deliverable_code}" value="${customHours}" 
                  min="0" step="0.5"
                  onchange="updateCustomHours('${item.deliverable_code}', this.value)"
                  style="width: 80px; padding: 6px; border: 1px solid rgba(106,163,255,0.3); 
                         border-radius: 4px; background: rgba(106,163,255,0.05); 
                         color: var(--text); text-align: center; font-weight: 500;" />
        </td>
        <td style="padding: 8px; text-align: center;">
          <div style="display: flex; align-items: center; gap: 2px; justify-content: center;">
            <span style="color: var(--muted);">$</span>
            <input type="number" id="rate-${item.deliverable_code}" value="${customRate}" 
                   min="0" step="5"
                   onchange="updateCustomRate('${item.deliverable_code}', this.value)"
                   style="width: 70px; padding: 6px; border: 1px solid rgba(106,163,255,0.3); 
                          border-radius: 4px; background: rgba(106,163,255,0.05); 
                          color: var(--text); text-align: center; font-weight: 500;" />
          </div>
        </td>
        <td id="price-period-${item.deliverable_code}" style="padding: 8px; text-align: right; font-weight: 600; color: var(--accent);">
          $${pricePerPeriod.toLocaleString()}
        </td>
        <td id="total-price-${item.deliverable_code}" style="padding: 8px; text-align: right; font-weight: 700; font-size: 1.05em; 
                   color: ${isRecurring ? 'var(--accent2)' : 'var(--accent)'};">
          $${totalPrice.toLocaleString()}
        </td>
        <td style="padding: 8px; font-size: 0.85em; color: var(--muted);">
          ${formatResourceDisplay(resources)}
        </td>
        <td style="padding: 8px; font-size: 0.85em; color: var(--muted);">
          ${formatTasksList(tasks)}
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
        
        grandTotal += compTotalPrice;
        
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
              $${grandTotal.toLocaleString()}
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
    const rate = pricingData.customRates.get(item.deliverable_code) || item.blended_rate || 210;
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
  
  // FIX: Update Grand Total - ALWAYS use original unscaled prices
  // Calculate the original total from items' original prices
  let originalOneTimeCost = 0;
  let originalRetainerMonthlyCost = 0;
  
  scenario.items.forEach(item => {
    const isRetainer = item.is_retainer || item.retainer || 
                      (item.cadence && item.cadence !== 'ONE_TIME');
    
    if (isRetainer) {
      // Use original monthly price if available
      originalRetainerMonthlyCost += item.original_monthly_price || item.monthly_price || 0;
    } else {
      // Use original price if available
      originalOneTimeCost += item.original_price || item.price || 0;
    }
  });
  
  // Use original costs for Grand Total
  const scenarioTotal = originalOneTimeCost;
  const grandTotal = originalOneTimeCost + (originalRetainerMonthlyCost * 12);
  const grandTotalEl = document.getElementById('grand-total-cost');
  const grandBreakdownEl = document.getElementById('grand-total-breakdown');
  
  if (grandTotalEl) grandTotalEl.textContent = `$${Math.round(grandTotal).toLocaleString()}`;
  if (grandBreakdownEl) {
    // Always show scenario total even when retainer is $0
    if (originalRetainerMonthlyCost > 0) {
      grandBreakdownEl.textContent = `One-time ($${Math.round(originalOneTimeCost).toLocaleString()}) + 12 months retainer ($${Math.round(originalRetainerMonthlyCost * 12).toLocaleString()})`;
    } else {
      grandBreakdownEl.textContent = `One-time total: $${Math.round(originalOneTimeCost).toLocaleString()}`;
    }
  }
  
  // Render executive summary view
  if (typeof renderExecSimple === 'function') {
    renderExecSimple(scenario);
  }
}

// Render Executive Summary (Simple View - No Overlays)
function renderExecSimple(scenario) {
  function setText(id, v){ const el=document.getElementById(id); if(el) el.textContent = v || '—'; }
  function injectScope(scopeText){
    const host = document.getElementById('scope-sections'); if(!host) return;
    const anchors = [
      'Brand Strategy','Brand Identity','Brand Architecture','Experiential Activation',
      'Campaign Creative','Content Production','Marketing Collateral','Program Management'
    ];
    const rx = new RegExp(`(${anchors.map(a=>a.replace(/[-/\\^$*+?.()|[\]{}]/g,'\\$&')).join('|')})`,'i');
    const chunks = (scopeText||'').split(rx).map(s=>s&&s.trim()).filter(Boolean);
    host.innerHTML = '';
    for(let i=0;i<chunks.length;i+=2){
      const title = chunks[i]; const body = chunks[i+1] || '';
      const details = document.createElement('details');
      const summary = document.createElement('summary'); summary.textContent = title;
      const content = document.createElement('div'); content.innerHTML = body.replace(/\n/g,'<br>');
      details.appendChild(summary); details.appendChild(content); host.appendChild(details);
    }
  }

  setText('ov-goal', scenario?.meta?.goal || window.RFP?.goal || 'Fast analysis');
  setText('ov-channels', (scenario?.meta?.channels||window.RFP?.channels||[]).join(', ') || '—');
  setText('ov-markets', (scenario?.meta?.markets||window.RFP?.markets||[]).join(', ') || '—');

  const hi = (scenario?.highlights||[]).slice(0,3);
  const ul = document.getElementById('ov-highlights');
  if (ul) ul.innerHTML = hi.length ? hi.map(h=>`<li>${h}</li>`).join('') : '<li>Executive-ready summary</li>';

  const scopeText = scenario?.summary?.bulletsText || window.Step2?.summaryText || '';
  injectScope(scopeText);
  
  // Show executive summary panel
  const execSummary = document.getElementById('executive-summary');
  if (execSummary) execSummary.style.display = 'block';
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
    taskRows.forEach(row => row.style.display = 'none');
    // Reset all component expand icons
    componentRows.forEach(row => {
      const compButton = row.querySelector('span[id^="expand-comp-"]');
      if (compButton) compButton.textContent = '▶';
    });
  }
}

// Toggle component expansion to show/hide tasks
function toggleComponentExpand(deliverableCode, componentName) {
  const safeCompName = componentName.replace(/\s+/g, '_');
  const expandIcon = document.getElementById(`expand-comp-${deliverableCode}-${safeCompName}`);
  const taskRows = document.querySelectorAll(`.task-row-comp-${deliverableCode}-${safeCompName}`);
  
  if (expandIcon.textContent === '▶') {
    expandIcon.textContent = '▼';
    taskRows.forEach(row => row.style.display = '');
  } else {
    expandIcon.textContent = '▶';
    taskRows.forEach(row => row.style.display = 'none');
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

// Update custom hours - immediate recalculation
function updateCustomHours(deliverableCode, hours) {
  const numHours = parseFloat(hours) || 0;
  pricingData.customHours.set(deliverableCode, numHours);
  
  // Get current rate for complete patch
  const currentRate = parseFloat(document.getElementById(`rate-${deliverableCode}`)?.value) || 
                      pricingData.customRates.get(deliverableCode) || 210;
  
  // Sync to ScenarioStore for backend persistence
  if (window.ScenarioStore) {
    window.ScenarioStore.updateDeliverable(deliverableCode, {
      hours: numHours,
      rate: currentRate,
      rate_usd: currentRate
    });
  }
  
  // Immediate update without full re-render
  updateRowTotals(deliverableCode);
  updatePricingSummary();
}

// Update custom rate - immediate recalculation
function updateCustomRate(deliverableCode, rate) {
  const numRate = parseFloat(rate) || 210;
  pricingData.customRates.set(deliverableCode, numRate);
  
  // Get current hours for complete patch
  const currentHours = parseFloat(document.getElementById(`hours-${deliverableCode}`)?.value) || 
                       pricingData.customHours.get(deliverableCode) || 0;
  
  // Sync to ScenarioStore for backend persistence - use rate_usd canonical key
  if (window.ScenarioStore) {
    window.ScenarioStore.updateDeliverable(deliverableCode, {
      rate: numRate,
      rate_usd: numRate,
      hours: currentHours
    });
  }
  
  // Immediate update without full re-render
  updateRowTotals(deliverableCode);
  updatePricingSummary();
}

// Analyze PROJECT vs RETAINER with AI - ENHANCED VERSION
async function analyzeProjectRetainer() {
  // Try multiple sources for RFP text
  let rfpText = '';
  
  // First try from textarea if still visible
  const rfpTextarea = document.getElementById('rfpText');
  if (rfpTextarea) rfpText = rfpTextarea.value;
  
  // If empty, try from sessionStorage (using correct key)
  if (!rfpText) rfpText = sessionStorage.getItem('apb.rfp_text') || sessionStorage.getItem('rfp_text') || '';
  
  // If empty, try from APB.step2
  if (!rfpText && window.APB && window.APB.step2) {
    rfpText = window.APB.step2.rfpText || '';
  }
  
  // If empty, try from app.state (if stored during analysis)
  if (!rfpText && window.appState && window.appState.rfpText) {
    rfpText = window.appState.rfpText || '';
  }
  
  if (!rfpText) {
    console.warn('No RFP text found in any storage location');
    // Instead of failing, use a generic analysis based on deliverable names
    const useGenericAnalysis = confirm('No RFP text found. Would you like to analyze based on deliverable names only?');
    if (!useGenericAnalysis) return;
    rfpText = 'Analyze based on deliverable names only';
  }
  
  const scenarios = getScenarioState();
  if (!scenarios || !scenarios.A) {
    alert('Please build a scenario first (click Build Scenario button).');
    return;
  }
  
  const btn = document.getElementById('btn-ai-suggest-type');
  if (btn) {
    btn.disabled = true;
    btn.textContent = '🔄 Analyzing...';
  }
  
  try {
    // Get deliverables from current scenario
    const deliverables = (scenarios.A.items || []).map(item => ({
      code: item.deliverable_code,
      name: item.deliverable
    }));
    
    const response = await fetch('/api/ai/analyze_project_retainer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rfp_text: rfpText,
        deliverables: deliverables
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    
    const result = await response.json();
    
    if (result.suggestions) {
      // Apply suggestions to BOTH pricing data AND scenario
      Object.entries(result.suggestions).forEach(([code, suggestion]) => {
        // Update pricingData for future calculations
        pricingData.deliverableTypes.set(code, suggestion.type);
        
        // Update the actual scenario items
        const scenarioItem = scenarios.A.items.find(i => i.deliverable_code === code);
        if (scenarioItem) {
          // Set retainer_months based on type
          if (suggestion.type === 'RETAINER') {
            // Default to 12 months for retainers unless already set
            scenarioItem.retainer_months = scenarioItem.retainer_months || 12;
            pricingData.retainers.set(code, scenarioItem.retainer_months);
          } else {
            // PROJECT type - clear retainer months
            scenarioItem.retainer_months = 0;
            pricingData.retainers.delete(code);
          }
        }
        
        // Also apply to components (inherit from parent)
        const item = scenarios.A.items.find(i => i.deliverable_code === code);
        if (item && item.components) {
          item.components.forEach(comp => {
            const compKey = `${code}::${comp.name}`;
            if (!pricingData.deliverableTypes.has(compKey)) {
              pricingData.deliverableTypes.set(compKey, suggestion.type);
            }
          });
        }
      });
      
      // Re-render the scenario table to show updated types and cadence
      if (window.renderScenario) {
        window.renderScenario('scenarioA', scenarios.A);
      }
      
      // Update pricing calculations if the function exists
      if (typeof updatePricingCalculations === 'function') {
        updatePricingCalculations();
      }
      
      // Show summary of suggestions with reasoning
      const projectCount = Object.values(result.suggestions).filter(s => s.type === 'PROJECT').length;
      const retainerCount = Object.values(result.suggestions).filter(s => s.type === 'RETAINER').length;
      
      let summaryMessage = `✨ AI Analysis Complete!\n\n` +
                          `📦 ${projectCount} deliverables marked as PROJECT (one-time)\n` +
                          `🔄 ${retainerCount} deliverables marked as RETAINER (recurring)\n\n`;
      
      // Add method info
      if (result.method === 'gpt5') {
        summaryMessage += `🧠 Analysis by: GPT-5 Intelligence\n`;
      } else if (result.method === 'ai') {
        summaryMessage += `🤖 Analysis by: AI Assistant\n`;
      } else {
        summaryMessage += `⚡ Analysis by: Smart Heuristics\n`;
      }
      
      // Add confidence if available
      if (result.confidence) {
        summaryMessage += `📊 Confidence: ${(result.confidence * 100).toFixed(0)}%\n`;
      }
      
      alert(summaryMessage);
      
      console.log('AI Suggestions applied:', result);
    }
  } catch (error) {
    console.error('Error analyzing project/retainer types:', error);
    alert('Error analyzing deliverable types: ' + error.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = '🤖 AI Suggest Type';
    }
  }
}

// Update Pricing Function - saves all changes and recalculates
async function updatePricing() {
  const scenarios = getScenarioState();
  if (!scenarios || !scenarios.A) {
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
    const scenario = scenarios.A;
    scenario.items.forEach(item => {
      const delivType = pricingData.deliverableTypes.get(item.deliverable_code) || 'PROJECT';
      const customHours = pricingData.customHours.get(item.deliverable_code);
      const customRate = pricingData.customRates.get(item.deliverable_code);
      
      if (customHours !== undefined) item.hours = customHours;
      if (customRate !== undefined) item.blended_rate = customRate;
      item.price = (item.hours || 0) * (item.blended_rate || 210);
      item.is_retainer = (delivType === 'RETAINER');
      
      // Update components
      if (item.components) {
        item.components.forEach(comp => {
          const compKey = `${item.deliverable_code}::${comp.name}`;
          const compHours = pricingData.customHours.get(compKey);
          const compRate = pricingData.customRates.get(compKey);
          
          if (compHours !== undefined) comp.hours = compHours;
          if (compRate !== undefined) comp.rate = compRate;
          comp.price = (comp.hours || 0) * (comp.rate || item.blended_rate || 210);
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
  // Try to load from memory using centralized accessor
  let scenariosToUse = getScenarioState();
  
  if (!scenariosToUse || !scenariosToUse.A) {
    console.log('[REBUILD] SCENARIOS not in memory, checking localStorage...');
    
    // Try to load from localStorage
    try {
      const sessionId = window.APB?.sessionId || 
                       sessionStorage.getItem('apb.session_id') || 
                       'default';
      const storageKey = `scenarios_${sessionId}`;
      const saved = localStorage.getItem(storageKey) || localStorage.getItem('latest_scenarios');
      
      if (saved) {
        scenariosToUse = JSON.parse(saved);
        setScenarioState(scenariosToUse);  // Sync both local and window variables
        console.log('[REBUILD] Restored scenarios from localStorage');
      }
    } catch (err) {
      console.error('[REBUILD] Failed to load from localStorage:', err);
    }
  }
  
  if (!scenariosToUse || !scenariosToUse.A) {
    console.error('[REBUILD] No scenario found in memory or localStorage');
    alert('No scenario to rebuild. Please build a scenario first.');
    return;
  }
  
  // scenariosToUse is now the reference to use (no shadowing const SCENARIOS)
  
  const btn = document.getElementById('btn-rebuild-scenario') || 
            document.querySelector('button[onclick*="rebuildScenario"]');
  
  if (btn) {
    btn.disabled = true;
    btn.textContent = '🔄 Rebuilding...';
  }
  
  try {
    // Store current version if not already stored
    if (!pricingData.originalScenario) {
      pricingData.originalScenario = JSON.parse(JSON.stringify(scenariosToUse.A));
    }
    
    // Increment rebuild version
    if (!pricingData.rebuildVersion) pricingData.rebuildVersion = 0;
    pricingData.rebuildVersion++;
    
    // Create rebuilt scenario with custom values
    const rebuiltScenario = JSON.parse(JSON.stringify(scenariosToUse.A));
    
    rebuiltScenario.items.forEach(item => {
      // Get cadence and periods for this deliverable
      const cadenceType = pricingDataEnhanced.cadenceTypes.get(item.deliverable_code) || 
                         (pricingData.deliverableTypes.get(item.deliverable_code) === 'RETAINER' ? 'MONTHLY' : 'ONE_TIME');
      const periods = pricingDataEnhanced.periodsCount.get(item.deliverable_code) || 
                     (cadenceType === 'MONTHLY' ? 12 : cadenceType === 'QUARTERLY' ? 4 : cadenceType === 'SEMI_ANNUAL' ? 2 : 1);
      
      // Get custom values or keep originals
      const customHours = pricingData.customHours.get(item.deliverable_code);
      const customRate = pricingData.customRates.get(item.deliverable_code);
      
      if (customHours !== undefined) item.hours = customHours;
      if (customRate !== undefined) item.blended_rate = customRate;
      
      // Update price calculation (price per period)
      item.price = (item.hours || 0) * (item.blended_rate || 210);
      
      // Mark as retainer if not one-time
      item.is_retainer = (cadenceType !== 'ONE_TIME');
      if (item.is_retainer) {
        item.retainer_months = periods;
      }
      
      // Update components
      if (item.components) {
        item.components.forEach(comp => {
          const compKey = `${item.deliverable_code}::${comp.name}`; // Fixed to use :: separator
          const compCadence = pricingDataEnhanced.cadenceTypes.get(compKey) || cadenceType;
          const compPeriods = pricingDataEnhanced.periodsCount.get(compKey) || periods;
          const compHours = pricingData.customHours.get(compKey);
          const compRate = pricingData.customRates.get(compKey);
          
          if (compHours !== undefined) comp.hours = compHours;
          if (compRate !== undefined) comp.rate = compRate;
          
          comp.price = (comp.hours || 0) * (comp.rate || item.blended_rate || 210);
          comp.is_retainer = (compCadence !== 'ONE_TIME');
          if (comp.is_retainer) {
            comp.retainer_months = compPeriods;
          }
        });
      }
    });
    
    // Show comparison modal
    showScenarioComparison(pricingData.originalScenario, rebuiltScenario);
    
    // Update current scenario and sync to both local and window variables
    scenariosToUse.A = rebuiltScenario;
    setScenarioState(scenariosToUse);
    updatePricingCalculations();
    
    console.log('Scenario rebuilt successfully', rebuiltScenario);
    
  } catch (error) {
    console.error('Error rebuilding scenario:', error);
    alert('Error rebuilding scenario. Please try again.');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = '🔨 Re-build Scenario';
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
    const price = item.price || (item.hours * (item.blended_rate || 210));
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
        const compPrice = comp.price || (comp.hours * (comp.rate || item.blended_rate || 210));
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
      <h3 style="margin: 0 0 12px; color: var(--accent);">📊 Scenario Comparison</h3>
      <p style="margin: 0 0 20px; font-size: 0.85em; color: var(--muted);">Click a version to select it</p>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
        <div id="version-original-box" style="padding: 16px; background: rgba(255,255,255,0.05); border-radius: 8px; 
                    cursor: pointer; border: 2px solid transparent; transition: all 0.2s ease;"
             onmouseover="this.style.background='rgba(255,255,255,0.1)'; this.style.borderColor='var(--muted)';"
             onmouseout="this.style.background='rgba(255,255,255,0.05)'; this.style.borderColor='transparent';">
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
          <div style="margin-top: 10px; font-size: 0.8em; color: var(--muted); text-align: center;">
            🔄 Click to rollback
          </div>
        </div>
        
        <div id="version-rebuilt-box" style="padding: 16px; background: rgba(139, 92, 246, 0.1); border-radius: 8px;
                    cursor: pointer; border: 2px solid var(--accent); transition: all 0.2s ease;"
             onmouseover="this.style.background='rgba(139, 92, 246, 0.2)';"
             onmouseout="this.style.background='rgba(139, 92, 246, 0.1)';">
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
          <div style="margin-top: 10px; font-size: 0.8em; color: var(--accent); text-align: center;">
            ✓ Currently selected
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
      
      <button id="comparison-close-btn"
              style="width: 100%; padding: 10px; background: var(--accent); color: white; 
                     border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
        Close
      </button>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Add click handlers for version selection
  const originalBox = modal.querySelector('#version-original-box');
  const rebuiltBox = modal.querySelector('#version-rebuilt-box');
  const closeBtn = modal.querySelector('#comparison-close-btn');
  
  // Click Version 1 (Original) - Rollback to baseline
  originalBox.addEventListener('click', async () => {
    try {
      originalBox.style.opacity = '0.6';
      originalBox.innerHTML = '<div style="text-align: center; padding: 20px;"><div class="spinner"></div><div style="margin-top: 10px;">Rolling back...</div></div>';
      
      const response = await fetch('/api/pricing/reset_from_step2', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: SessionManager?.currentSessionId || 'A' })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('[ROLLBACK] Reset to baseline successful:', result);
        
        // Refresh the pricing display
        if (typeof refreshPricingData === 'function') {
          await refreshPricingData();
        }
        if (typeof updatePricingTable === 'function') {
          updatePricingTable();
        }
        
        // Close modal and show success message
        modal.remove();
        showToast('✅ Rolled back to original pricing', 'success');
      } else {
        throw new Error('Reset failed');
      }
    } catch (err) {
      console.error('[ROLLBACK] Error:', err);
      showToast('❌ Rollback failed: ' + err.message, 'error');
      modal.remove();
    }
  });
  
  // Click Version 2 (Rebuilt) - Keep current and close
  rebuiltBox.addEventListener('click', () => {
    console.log('[COMPARISON] Keeping rebuilt version');
    modal.remove();
    showToast('✓ Keeping rebuilt pricing', 'success');
  });
  
  // Close button
  closeBtn.addEventListener('click', () => {
    modal.remove();
  });
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
    const rate = parseFloat(rateInput.value) || 210;
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
    pricingDataEnhanced.periodsCount.set(code, periods);
    
    // Store retainer months if it's a retainer
    if (pricingData.deliverableTypes.get(code) === 'RETAINER') {
      pricingData.retainers.set(code, periods);
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
        item.price = (item.hours || 0) * (item.blended_rate || 210);
        
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
            comp.price = (comp.hours || 0) * (comp.rate || item.blended_rate || 210);
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
  
  // Map UI cadence values to backend billing_cadence format
  const cadenceMap = {
    'ONE_TIME': 'one_time',
    'MONTHLY': 'monthly',
    'QUARTERLY': 'quarterly',
    'SEMI_ANNUAL': 'semi_annual',
    'ANNUAL': 'annual'
  };
  const billingCadence = cadenceMap[cadence] || 'one_time';
  
  // Set default cadence_units based on cadence type
  let defaultUnits = 1;
  if (cadence === 'MONTHLY') defaultUnits = 12;
  else if (cadence === 'QUARTERLY') defaultUnits = 4;
  else if (cadence === 'SEMI_ANNUAL') defaultUnits = 2;
  else if (cadence === 'ANNUAL') defaultUnits = 1;
  
  pricingDataEnhanced.periodsCount.set(code, defaultUnits);
  
  // Update periods input immediately
  const periodsInput = document.getElementById(`periods-${code}`);
  if (periodsInput) {
    periodsInput.value = defaultUnits;
  }
  
  // Get current hours and rate for ScenarioStore update
  const hours = parseFloat(document.getElementById(`hours-${code}`)?.value) || 0;
  const rate = parseFloat(document.getElementById(`rate-${code}`)?.value) || 210;
  
  // Calculate retainer_months from cadence structure (null for one_time to avoid stale values)
  const monthsPerPeriod = { 'one_time': null, 'monthly': 1, 'quarterly': 3, 'semi_annual': 6, 'annual': 12 };
  const monthMultiplier = monthsPerPeriod[billingCadence];
  const retainerMonths = monthMultiplier !== null ? monthMultiplier * defaultUnits : null;
  
  // Sync to ScenarioStore (which PATCHes to backend) - use rate_usd for canonical key
  if (window.ScenarioStore) {
    window.ScenarioStore.updateDeliverable(code, {
      billing_cadence: billingCadence,
      cadence_units: defaultUnits,
      hours: hours,
      rate: rate,
      rate_usd: rate,
      months: retainerMonths
    });
  }
  
  // Recalculate totals immediately
  updateRowTotals(code);
  updatePricingSummary();
}

function updatePeriods(code, periods) {
  const periodsNum = parseInt(periods) || 1;
  const clampedPeriods = Math.max(1, Math.min(36, periodsNum));
  pricingDataEnhanced.periodsCount.set(code, clampedPeriods);
  
  // Get current cadence for retainer_months calculation
  const cadence = pricingDataEnhanced.cadenceTypes.get(code) || 'ONE_TIME';
  const cadenceMap = {
    'ONE_TIME': 'one_time',
    'MONTHLY': 'monthly',
    'QUARTERLY': 'quarterly',
    'SEMI_ANNUAL': 'semi_annual',
    'ANNUAL': 'annual'
  };
  const billingCadence = cadenceMap[cadence] || 'one_time';
  const monthsPerPeriod = { 'one_time': null, 'monthly': 1, 'quarterly': 3, 'semi_annual': 6, 'annual': 12 };
  const monthMultiplier = monthsPerPeriod[billingCadence];
  const retainerMonths = monthMultiplier !== null ? monthMultiplier * clampedPeriods : null;
  
  // Sync to ScenarioStore
  if (window.ScenarioStore) {
    window.ScenarioStore.updateDeliverable(code, {
      cadence_units: clampedPeriods,
      months: retainerMonths
    });
  }
  
  // Recalculate totals immediately
  updateRowTotals(code);
  updatePricingSummary();
}

// Update monthly price (for retainers - derives total from monthly price)
function updateMonthlyPrice(code, monthlyPrice) {
  const monthlyPriceNum = parseFloat(monthlyPrice) || 0;
  
  // Sync to ScenarioStore - backend will apply priority rules
  if (window.ScenarioStore) {
    window.ScenarioStore.updateDeliverable(code, {
      monthly_price: monthlyPriceNum
    });
  }
  
  // Recalculate totals
  updateRowTotals(code);
  updatePricingSummary();
}

// Update cadence price (price per period)
function updateCadencePrice(code, cadencePrice) {
  const cadencePriceNum = parseFloat(cadencePrice) || 0;
  
  // Sync to ScenarioStore - backend will apply priority rules
  if (window.ScenarioStore) {
    window.ScenarioStore.updateDeliverable(code, {
      cadence_price: cadencePriceNum
    });
  }
  
  // Recalculate totals
  updateRowTotals(code);
  updatePricingSummary();
}

// New helper: Update row totals without full table re-render
function updateRowTotals(code) {
  const hours = parseFloat(document.getElementById(`hours-${code}`)?.value) || 0;
  const rate = parseFloat(document.getElementById(`rate-${code}`)?.value) || 210;
  const periods = pricingDataEnhanced.periodsCount.get(code) || 1;
  
  const pricePerPeriod = hours * rate;
  const totalPrice = pricePerPeriod * periods;
  
  // Update display cells
  const pricePeriodCell = document.getElementById(`price-period-${code}`);
  const totalPriceCell = document.getElementById(`total-price-${code}`);
  
  if (pricePeriodCell) {
    pricePeriodCell.textContent = `$${pricePerPeriod.toLocaleString()}`;
  }
  
  if (totalPriceCell) {
    totalPriceCell.textContent = `$${totalPrice.toLocaleString()}`;
  }
  
  // Update scenario data
  if (SCENARIOS && SCENARIOS.A) {
    const item = SCENARIOS.A.items.find(i => i.deliverable_code === code);
    if (item) {
      item.total_hours = hours;
      item.effective_rate = rate;
      item.price = pricePerPeriod;
      item.cadence_price = pricePerPeriod;
      
      if (periods > 1) {
        item.retainer_months = periods;
        item.cadence_units = periods;
      }
    }
  }
}

// Export pricing details
async function exportPricingDetails() {
  console.log('[EXPORT] Starting pricing export...');
  
  // Get button reference for UI feedback
  const btn = document.getElementById('btn-export-pricing');
  const originalText = btn?.textContent || 'Export Pricing Details';
  
  // Get the scenario (try memory first, then localStorage)
  let scenario = window.SCENARIOS?.A;
  
  if (!scenario) {
    console.log('[EXPORT] Trying to load scenario from localStorage...');
    try {
      const saved = localStorage.getItem('latest_scenarios');
      if (saved) {
        const scenarios = JSON.parse(saved);
        scenario = scenarios.A;
        window.SCENARIOS = scenarios;  // Restore to memory
      }
    } catch (err) {
      console.error('[EXPORT] Failed to load from localStorage:', err);
    }
  }
  
  if (!scenario) {
    alert('❌ No scenario available to export.\n\nPlease build a scenario first in Step 3.');
    return;
  }
  
  // Show loading state
  if (btn) {
    btn.disabled = true;
    btn.textContent = '⏳ Exporting...';
  }
  
  try {
    const projectName = document.getElementById('projectName')?.value || 'Project';
    const formatSelect = document.getElementById('export-format');
    const fileFormat = formatSelect?.value || 'xlsx';
    
    console.log('[EXPORT] Calling /api/export with format:', fileFormat);
    
    // Get session_id from ScenarioManager (preferred) or SessionManager
    const sessionId = window.ScenarioManager?.state?.sessionId || 
                      window.SessionManager?.currentSessionId ||
                      localStorage.getItem('apb.currentSession');
    console.log('[EXPORT] Using session_id:', sessionId);
    
    const response = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,  // NEW: Prefer SCENARIO_STORE working scenario
        scenario: scenario,
        file_format: fileFormat
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('[EXPORT] Server error:', errorText);
      throw new Error(`Export failed (${response.status}): ${errorText}`);
    }
    
    // Download the file
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const ext = fileFormat === 'xlsx' ? 'xlsx' : 'csv';
    const filename = `${projectName}_pricing_${new Date().toISOString().split('T')[0]}.${ext}`;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    // Show success message
    console.log('[EXPORT] Successfully exported:', filename);
    alert(`✅ Pricing exported successfully!\n\nFile: ${filename}\n\nCheck your downloads folder.`);
    
  } catch (error) {
    console.error('[EXPORT] Error:', error);
    alert(`❌ Export failed.\n\nError: ${error.message}\n\nPlease try again or check the console for details.`);
  } finally {
    // Reset button state
    if (btn) {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }
}

// Generic export function for Step 5 exports
async function exportScenario(fileFormat, buttonId) {
  console.log(`[EXPORT] Starting ${fileFormat} export...`);
  
  // Get button reference for UI feedback
  const btn = document.getElementById(buttonId);
  const originalText = btn?.textContent || `Export ${fileFormat.toUpperCase()}`;
  
  // Get the scenario (try memory first, then localStorage)
  let scenario = window.SCENARIOS?.A;
  
  if (!scenario) {
    console.log('[EXPORT] Trying to load scenario from localStorage...');
    try {
      const saved = localStorage.getItem('latest_scenarios');
      if (saved) {
        const scenarios = JSON.parse(saved);
        scenario = scenarios.A;
        window.SCENARIOS = scenarios;  // Restore to memory
      }
    } catch (err) {
      console.error('[EXPORT] Failed to load from localStorage:', err);
    }
  }
  
  if (!scenario) {
    alert('❌ No scenario available to export.\n\nPlease build a scenario first in Step 3.');
    return;
  }
  
  // Show loading state
  if (btn) {
    btn.disabled = true;
    btn.textContent = '⏳ Exporting...';
  }
  
  try {
    const projectName = document.getElementById('projectName')?.value || 'Project';
    
    console.log('[EXPORT] Calling /api/export with format:', fileFormat);
    
    // Get session_id from ScenarioManager (preferred) or SessionManager
    const sessionId = window.ScenarioManager?.state?.sessionId || 
                      window.SessionManager?.currentSessionId ||
                      localStorage.getItem('apb.currentSession');
    console.log('[EXPORT] Using session_id:', sessionId);
    
    const response = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,  // NEW: Prefer SCENARIO_STORE working scenario
        scenario: scenario,
        file_format: fileFormat
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('[EXPORT] Server error:', errorText);
      throw new Error(`Export failed (${response.status}): ${errorText}`);
    }
    
    // Download the file
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const ext = fileFormat === 'xlsx' ? 'xlsx' : 'csv';
    const filename = `${projectName}_export_${new Date().toISOString().split('T')[0]}.${ext}`;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    // Show success message
    console.log('[EXPORT] Successfully exported:', filename);
    alert(`✅ Export successful!\n\nFile: ${filename}\n\nCheck your downloads folder.`);
    
  } catch (error) {
    console.error('[EXPORT] Error:', error);
    alert(`❌ Export failed.\n\nError: ${error.message}\n\nPlease try again or check the console for details.`);
  } finally {
    // Reset button state
    if (btn) {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }
}

// Export as Excel (.xlsx)
async function exportExcel() {
  await exportScenario('xlsx', 'btn-export-excel');
}

// Export as CSV (.csv)
async function exportCSV() {
  await exportScenario('csv', 'btn-export-csv');
}

// AI Optimize All Pricing Function - ENHANCED VERSION
async function optimizeAllPricing() {
  const btn = document.getElementById('btn-ai-optimize-pricing');
  if (!btn) return;
  
  // Check for scenario using centralized accessor
  const scenarios = getScenarioState();
  if (!scenarios || !scenarios.A) {
    alert('Please build a scenario first before optimizing pricing.');
    return;
  }
  
  // Show loading state
  btn.disabled = true;
  btn.textContent = '🔄 Optimizing...';
  
  try {
    // Get current scenario data
    const scenario = scenarios.A;
    if (!scenario || !scenario.items || scenario.items.length === 0) {
      alert('No scenario items to optimize. Please build a scenario first.');
      return;
    }
    
    // Get client budget and project details
    const clientBudget = Number(document.getElementById('clientBudget')?.value || 0);
    const projectName = document.getElementById('projectName')?.value || 'Project';
    
    // Get RFP text for context
    let rfpText = '';
    const rfpTextarea = document.getElementById('rfpText');
    if (rfpTextarea) rfpText = rfpTextarea.value;
    if (!rfpText) rfpText = sessionStorage.getItem('apb.rfp_text') || '';
    if (!rfpText && window.APB && window.APB.step2) {
      rfpText = window.APB.step2.rfpText || '';
    }
    
    // Try to call AI optimization endpoint first
    try {
      const response = await fetch('/api/ai/optimize_pricing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario: scenario,
          client_budget: clientBudget,
          project_name: projectName,
          rfp_context: rfpText,
          deliverables: scenario.items.map(item => ({
            code: item.deliverable_code,
            name: item.deliverable,
            hours: item.total_hours,
            price: item.price,
            is_retainer: item.retainer_months > 0
          }))
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        
        // Apply optimizations to scenario
        if (result.optimized_items) {
          result.optimized_items.forEach((opt, idx) => {
            if (scenario.items[idx]) {
              scenario.items[idx].total_hours = opt.hours;
              scenario.items[idx].price = opt.price;
              scenario.items[idx].effective_rate = opt.hours > 0 ? opt.price / opt.hours : 210;
            }
          });
          
          // Update totals - but preserve original totals for Grand Total calculation
          if (!scenario.totals.original_price) {
            scenario.totals.original_price = scenario.totals.price;
          }
          scenario.totals.hours = scenario.items.reduce((sum, item) => sum + item.total_hours, 0);
          scenario.totals.price = scenario.items.reduce((sum, item) => sum + item.price, 0);
          
          // Re-render scenario
          if (window.renderScenario) {
            window.renderScenario('scenarioA', scenario);
          }
          
          // Show success message
          showOptimizationSuccess(result, clientBudget);
        }
        
        return; // Exit if AI optimization succeeded
      }
    } catch (apiError) {
      console.log('AI optimization not available, using smart fallback');
    }
    
    // Fallback: Smart budget-based optimization
    performSmartOptimization(scenario, clientBudget);
    
  } catch (error) {
    console.error('Error optimizing pricing:', error);
    alert('Error occurred during optimization. Please try again.');
  } finally {
    // Reset button state
    btn.disabled = false;
    btn.textContent = 'Optimize All Pricing';
  }
}

// Smart optimization fallback
function performSmartOptimization(scenario, clientBudget) {
  if (!clientBudget || clientBudget <= 0) {
    alert('Please enter a client budget to optimize pricing.');
    return;
  }
  
  const currentTotal = scenario.totals.price;
  const scaleFactor = clientBudget / currentTotal;
  
  // Apply scaling to all items - PRESERVE ORIGINAL PRICES
  scenario.items.forEach(item => {
    // Preserve original prices before scaling for Grand Total calculation
    if (!item.original_price) {
      item.original_price = item.price;
    }
    if (!item.original_hours) {
      item.original_hours = item.total_hours;
    }
    if (item.monthly_price && !item.original_monthly_price) {
      item.original_monthly_price = item.monthly_price;
    }
    
    // Scale hours and price proportionally
    const originalHours = item.original_hours || item.total_hours;
    const originalPrice = item.original_price || item.price;
    
    item.total_hours = Math.round(originalHours * scaleFactor);
    item.price = Math.round(originalPrice * scaleFactor);
    
    // Scale monthly prices for retainers
    if (item.monthly_price) {
      const originalMonthlyPrice = item.original_monthly_price || item.monthly_price;
      item.monthly_price = Math.round(originalMonthlyPrice * scaleFactor);
    }
    
    // Maintain effective rate
    if (item.total_hours > 0) {
      item.effective_rate = item.price / item.total_hours;
    }
  });
  
  // Update totals - but preserve original totals for Grand Total calculation
  if (!scenario.totals.original_price) {
    scenario.totals.original_price = scenario.totals.price;
  }
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
  } else if (scaleFactor > 1) {
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
window.updateMonthlyPrice = updateMonthlyPrice;
window.updateCadencePrice = updateCadencePrice;
window.extractDeliverableTasks = extractDeliverableTasks;
window.formatTasksList = formatTasksList;

// Export timeline error handling functions
window.generateAITimeline = generateAITimeline;
window.showUserFriendlyError = showUserFriendlyError;
window.cancelTimelineGeneration = cancelTimelineGeneration;

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
  
  // Connection health tracking
  let lastHeartbeatTime = Date.now();
  let lastDataTime = Date.now();
  const HEARTBEAT_TIMEOUT_MS = 30000; // 30 seconds without any data = real issue
  const POLLING_INTERVAL_MS = 2000; // Poll every 2 seconds if SSE fails
  
  // Polling fallback state
  let isPolling = false;
  let pollingIntervalId = null;
  
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
      <div id="timeline-connection-status" style="display: none; background: rgba(251, 146, 60, 0.1); border: 1px solid rgba(251, 146, 60, 0.2); padding: 8px; border-radius: 4px; margin-bottom: 12px;">
        <p style="margin: 0; color: #ea580c; font-size: 0.85em;">
          🔄 Connection switched to polling mode. Timeline generation continues...
        </p>
      </div>
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
  
  let eventSource = null;
  let jobId = null;
  let heartbeatCheckInterval = null;
  
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
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    if (heartbeatCheckInterval) {
      clearInterval(heartbeatCheckInterval);
      heartbeatCheckInterval = null;
    }
    if (pollingIntervalId) {
      clearInterval(pollingIntervalId);
      pollingIntervalId = null;
    }
  };
  
  // Start heartbeat monitoring
  const startHeartbeatMonitor = () => {
    heartbeatCheckInterval = setInterval(() => {
      const timeSinceLastData = Date.now() - lastDataTime;
      
      if (timeSinceLastData > HEARTBEAT_TIMEOUT_MS && !isPolling) {
        console.log('[TIMELINE] No data for 30s, switching to polling fallback');
        
        // Switch to polling mode
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        
        // Show polling mode message
        const connectionStatus = document.getElementById('timeline-connection-status');
        if (connectionStatus) {
          connectionStatus.style.display = 'block';
        }
        
        // Start polling
        startPollingFallback();
      }
    }, 5000); // Check every 5 seconds
  };
  
  // Polling fallback function
  const startPollingFallback = async () => {
    isPolling = true;
    
    const pollJobStatus = async () => {
      if (!jobId) return;
      
      try {
        const response = await fetch(`/api/ai/jobs/${jobId}`);
        if (!response.ok) throw new Error('Failed to get job status');
        
        const data = await response.json();
        
        // Update UI with polling data
        updateProgressUI(data);
        
        // Check if job is complete
        if (data.status === 'completed' && data.result) {
          cleanup();
          handleTimelineCompletion(data.result);
        } else if (data.status === 'failed') {
          cleanup();
          handleTimelineError(data.error || 'Timeline generation failed');
        }
      } catch (error) {
        console.error('[TIMELINE] Polling error:', error);
        // Continue polling despite errors
      }
    };
    
    // Start polling immediately
    await pollJobStatus();
    
    // Continue polling at intervals
    pollingIntervalId = setInterval(pollJobStatus, POLLING_INTERVAL_MS);
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
    // ISSUE FIX 3: Update window.currentTimelineTasks so PDF export can access it
    window.currentTimelineTasks = result.tasks || [];
    currentTimelineTasks = window.currentTimelineTasks;
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
      
      // GPT-5.1 Pro: Trigger initial timeline save to populate metrics and resource risk
      saveTimelineWithMetrics(currentTimelineTasks);
      
      // ISSUE FIX 2: Show PDF Download and Save Changes buttons after successful timeline generation
      // These should stay visible permanently once timeline is generated
      const pdfButton = document.getElementById('gantt-pdf-button');
      if (pdfButton) {
        pdfButton.style.display = '';
        console.log('[Timeline] PDF download button shown');
      }
      
      const saveButton = document.getElementById('btn-save-timeline');
      if (saveButton) {
        saveButton.style.display = '';
        console.log('[Timeline] Save Changes button shown and will stay visible');
      }
      
      // ISSUE FIX 2: Defensive - ensure button stays visible even after other operations
      // Set a flag to prevent it from being hidden
      if (saveButton) {
        saveButton.setAttribute('data-timeline-generated', 'true');
      }
      
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
    
    // ISSUE FIX 4: Ensure timeline gets proper scenario items with actual count
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
      alert('Error: Scenario has no deliverables list. Please rebuild in Step 3.');
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
        body: JSON.stringify({
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
    
    // Store job ID for potential polling fallback
    jobId = jobData.job_id;
    
    // Connect to SSE stream for progress updates
    eventSource = new EventSource(`/api/stream/${jobData.job_id}`);
    
    // Start heartbeat monitoring
    startHeartbeatMonitor();
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Update last data time for heartbeat tracking
        lastDataTime = Date.now();
        
        // Handle heartbeat messages
        if (data.type === 'heartbeat') {
          lastHeartbeatTime = Date.now();
          console.log('[TIMELINE] Heartbeat received:', new Date(data.timestamp * 1000).toLocaleTimeString());
          return; // Don't process heartbeat as regular update
        }
        
        // Update progress UI using the helper function
        updateProgressUI(data);
        
        // Handle completion
        if (data.status === 'completed' && data.result) {
          cleanup();
          handleTimelineCompletion(data.result);
        }
        
        // Handle errors
        if (data.status === 'failed') {
          cleanup();
          handleTimelineError(data.error);
        }
        
      } catch (parseError) {
        console.error('Error parsing SSE data:', parseError);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      
      // Try polling fallback instead of immediately showing error
      if (!isPolling) {
        console.log('[TIMELINE] SSE connection failed, switching to polling fallback');
        
        // Show polling mode message
        const connectionStatus = document.getElementById('timeline-connection-status');
        if (connectionStatus) {
          connectionStatus.style.display = 'block';
        }
        
        // Close the SSE connection
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        
        // Start polling
        startPollingFallback();
      }
    };
    
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
                     border-radius: 4px; cursor: pointer;">
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

// Function to cancel timeline generation and clean up
function cancelTimelineGeneration() {
  const loading = document.getElementById('timeline-loading');
  const btn = document.getElementById('btn-generate-timeline');
  
  if (loading) {
    loading.style.display = 'none';
  }
  
  if (btn) {
    btn.disabled = false;
    btn.textContent = '🤖 Generate AI Timeline';
  }
  
  console.log('[TIMELINE] Generation cancelled by user');
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

// Update Resource Risk Management table
function updateResourceRiskTable(tasks, reasoning) {
  const tbody = document.getElementById('resource-risk-tbody');
  const section = document.getElementById('resource-risk-section');
  const summaryText = document.getElementById('risk-summary-text');
  
  if (!tbody || !section) return;
  
  // Analyze resource conflicts
  const resourceRisks = analyzeResourceRisks(tasks);
  
  if (resourceRisks.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--muted);">No resource conflicts or risks detected</td></tr>';
    summaryText.textContent = 'No resource conflicts detected';
    section.style.display = 'none';
    return;
  }
  
  // Show the section
  section.style.display = 'block';
  
  // Populate the table
  let totalIdleCost = 0;
  let highRiskCount = 0;
  
  const rows = resourceRisks.map(risk => {
    totalIdleCost += risk.idleCost;
    if (risk.riskLevel === 'High') highRiskCount++;
    
    const riskBadge = risk.riskLevel === 'High' 
      ? '<span style="background:#ef4444; color:white; padding:2px 8px; border-radius:4px;">High</span>'
      : risk.riskLevel === 'Medium'
      ? '<span style="background:#f59e0b; color:white; padding:2px 8px; border-radius:4px;">Medium</span>'
      : '<span style="background:#10b981; color:white; padding:2px 8px; border-radius:4px;">Low</span>';
    
    return `<tr>
      <td style="padding:12px; border-bottom:1px solid var(--border);">${risk.resource}</td>
      <td style="padding:12px; border-bottom:1px solid var(--border);">${risk.waitingPeriod} days</td>
      <td style="padding:12px; text-align:right; border-bottom:1px solid var(--border);">$${risk.idleCost.toLocaleString()}</td>
      <td style="padding:12px; text-align:center; border-bottom:1px solid var(--border);">${riskBadge}</td>
      <td style="padding:12px; border-bottom:1px solid var(--border); font-size:0.9em; color:var(--muted);">${risk.recommendation}</td>
    </tr>`;
  }).join('');
  
  tbody.innerHTML = rows;
  
  // Update summary
  if (highRiskCount > 0) {
    summaryText.innerHTML = `<span style="color:#ef4444;">⚠️ ${highRiskCount} high-risk resource conflicts detected. Total potential idle cost: $${totalIdleCost.toLocaleString()}</span>`;
  } else {
    summaryText.textContent = `${resourceRisks.length} resource risks identified. Total potential idle cost: $${totalIdleCost.toLocaleString()}`;
  }
}

// Analyze tasks for resource risks and conflicts
function analyzeResourceRisks(tasks) {
  if (!tasks || tasks.length === 0) return [];
  
  const risks = [];
  const resourceSchedule = {};
  
  // Build resource schedule
  tasks.forEach(task => {
    // Use proper department name, defaulting to 'Strategy' if not specified
    const resource = task.department || task.custom_class?.replace('dept-', '').replace(/-/g, ' ') || 'Strategy';
    if (!resourceSchedule[resource]) {
      resourceSchedule[resource] = [];
    }
    resourceSchedule[resource].push({
      taskId: task.id,
      taskName: task.name,
      start: new Date(task.start),
      end: new Date(task.end)
    });
  });
  
  // Analyze each resource for conflicts and idle time
  Object.entries(resourceSchedule).forEach(([resource, schedule]) => {
    if (schedule.length < 2) return;
    
    // Sort by start date
    schedule.sort((a, b) => a.start - b.start);
    
    // Look for gaps and overlaps
    for (let i = 0; i < schedule.length - 1; i++) {
      const current = schedule[i];
      const next = schedule[i + 1];
      
      const gapDays = Math.floor((next.start - current.end) / (1000 * 60 * 60 * 24));
      
      if (gapDays > 3) { // More than 3 days gap
        const idleCost = gapDays * 800; // Assume $800/day cost
        const riskLevel = gapDays > 10 ? 'High' : gapDays > 5 ? 'Medium' : 'Low';
        
        risks.push({
          resource: resource,
          waitingPeriod: gapDays,
          idleCost: idleCost,
          riskLevel: riskLevel,
          recommendation: gapDays > 10 
            ? 'Consider reassigning tasks or adjusting timeline to reduce idle time'
            : 'Minor gap - may be acceptable for resource availability'
        });
      }
    }
  });
  
  return risks;
}

// Function to manage AI button states based on scenario existence
function updateAIButtonStates() {
  const hasScenario = !!(window.SCENARIOS && window.SCENARIOS.A);
  
  // AI Suggest Type button
  const btnAISuggest = document.getElementById('btn-ai-suggest-type');
  if (btnAISuggest) {
    btnAISuggest.disabled = !hasScenario;
    if (!hasScenario) {
      btnAISuggest.title = 'Build a scenario first before using AI suggestions';
      btnAISuggest.style.opacity = '0.5';
      btnAISuggest.style.cursor = 'not-allowed';
    } else {
      btnAISuggest.title = 'Analyze deliverable types using AI';
      btnAISuggest.style.opacity = '1';
      btnAISuggest.style.cursor = 'pointer';
    }
  }
  
  // Optimize Pricing button
  const btnOptimize = document.getElementById('btn-ai-optimize-pricing');
  if (btnOptimize) {
    btnOptimize.disabled = !hasScenario;
    if (!hasScenario) {
      btnOptimize.title = 'Build a scenario first before optimizing pricing';
      btnOptimize.style.opacity = '0.5';
      btnOptimize.style.cursor = 'not-allowed';
    } else {
      btnOptimize.title = 'Optimize pricing using AI';
      btnOptimize.style.opacity = '1';
      btnOptimize.style.cursor = 'pointer';
    }
  }
  
  // Update AI panel visibility
  const aiPanel = document.querySelector('.ai-pricing-panel');
  if (aiPanel) {
    if (!hasScenario) {
      aiPanel.style.display = 'none';
    } else {
      aiPanel.style.display = 'block';
    }
  }
}

// Initialize Gantt event handlers when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Initialize button states
  updateAIButtonStates();
  
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
      // Save timeline changes to backend
      if (!currentTimelineTasks || currentTimelineTasks.length === 0) {
        alert('No timeline data to save');
        return;
      }
      
      try {
        // Get session_id for SCENARIO_STORE integration
        const sessionId = window.SessionManager ? window.SessionManager.getCurrentSessionId() : null;
        
        // Step 1: Save timeline edits (dates, durations, etc.)
        const response = await fetch('/api/timeline/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tasks: currentTimelineTasks,
            reasoning: timelineReasoning,
            session_id: sessionId,  // Include session_id so backend saves to SCENARIO_STORE
            metadata: {
              saved_at: new Date().toISOString(),
              project_name: document.getElementById('projectName')?.value || 'Project'
            }
          })
        });
        
        if (sessionId) {
          console.log('[Timeline Save] Including session_id:', sessionId);
        }
        
        if (response.ok) {
          // Step 2: Save timeline order (drag-and-drop reordering)
          // Determine which scenario we're saving (A, B, or C)
          const scenarioLetter = window.APP_STATE?.activeScenario || 'A';
          
          // Get the current scenario data
          const scenario = (window.appState?.scenarios || window.SCENARIOS)?.[scenarioLetter];
          
          if (scenario) {
            // Extract deliverable codes in current order from tasks
            const deliverableCodes = currentTimelineTasks
              .map(task => task.deliverable_code || (task.id ? task.id.split('-')[0] : null))
              .filter((code, index, self) => code && self.indexOf(code) === index); // Remove nulls and duplicates
            
            if (deliverableCodes.length > 0) {
              // Build included_map from scenario items
              const includedMap = {};
              if (scenario.items) {
                scenario.items.forEach(item => {
                  const code = item.deliverable_code;
                  includedMap[code] = item.included_task_groups || [];
                });
              }
              
              // Build payload for reorder_timeline endpoint
              const reorderPayload = {
                scenario_letter: scenarioLetter,
                deliverable_codes: deliverableCodes,
                included_map: includedMap,
                project_start: scenario.project_start,
                complexity: scenario.items?.[0]?.complexity || 'Advanced',
                tier: scenario.items?.[0]?.tier || 'T2_MediumVolume',
                use_slack: scenario.use_slack !== false, // Default to true
                slack_after_internal: scenario.slack_after_internal || 1,
                slack_after_client: scenario.slack_after_client || 2,
                slack_global_pct: scenario.slack_global_pct || 0.0
              };
              
              console.log('[Timeline Save] Saving timeline order:', deliverableCodes);
              
              // Call reorder_timeline to persist the order
              const reorderResponse = await fetch('/api/reorder_timeline', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(reorderPayload)
              });
              
              if (reorderResponse.ok) {
                const reorderResult = await reorderResponse.json();
                
                // Update local scenario with reordered items
                if (reorderResult.items && window.appState?.scenarios) {
                  window.appState.scenarios[scenarioLetter] = {
                    ...window.appState.scenarios[scenarioLetter],
                    items: reorderResult.items,
                    user_order: deliverableCodes,
                    manual_order_locked: true
                  };
                }
                if (reorderResult.items && window.SCENARIOS) {
                  window.SCENARIOS[scenarioLetter] = {
                    ...window.SCENARIOS[scenarioLetter],
                    items: reorderResult.items,
                    user_order: deliverableCodes,
                    manual_order_locked: true
                  };
                }
                
                console.log('[Timeline Save] ✅ Timeline order saved successfully');
              } else {
                console.warn('[Timeline Save] Failed to save timeline order:', await reorderResponse.text());
              }
            }
          }
          
          alert('✅ Timeline changes and order saved successfully');
          // ISSUE FIX 2: Keep Save Changes button visible after saving
          // btnSave.style.display = 'none';  // REMOVED - button should stay visible
          
          // Mark timeline as synced
          localStorage.setItem('timeline_synced', 'true');
          localStorage.setItem('timeline_data', JSON.stringify(currentTimelineTasks));
        } else {
          // Fallback to local storage
          localStorage.setItem('timeline_data', JSON.stringify(currentTimelineTasks));
          localStorage.setItem('timeline_reasoning', JSON.stringify(timelineReasoning));
          alert('Timeline saved locally (will sync when server is available)');
        }
      } catch (error) {
        console.error('Error saving timeline:', error);
        // Save to local storage as fallback
        localStorage.setItem('timeline_data', JSON.stringify(currentTimelineTasks));
        localStorage.setItem('timeline_reasoning', JSON.stringify(timelineReasoning));
        alert('Timeline saved locally');
      }
      
      // ISSUE FIX 2: Keep Save Changes button visible after saving
      // btnSave.style.display = 'none';  // REMOVED - button should stay visible
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
    // FIX: Extract task names from objects if needed
    const taskNames = l3.map(task => {
      if (typeof task === 'string') return task;
      if (task && typeof task === 'object') {
        const name = task.Task_Label || task.task_label || task.name || task.title || task.label || '';
        if (name && typeof name === 'string') return name;
      }
      return null; // Filter out invalid entries
    }).filter(name => name && name !== '[object Object]'); // Remove nulls and object strings
    selectionStore.l3ByComponent.set(key, new Set(taskNames));
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
  // CRITICAL FIX: Check if data was recently cleared (don't auto-restore)
  const dataClearedFlag = localStorage.getItem('apb.data_cleared');
  const clearTimestamp = localStorage.getItem('apb.clear_timestamp');
  const timeSinceClear = clearTimestamp ? Date.now() - parseInt(clearTimestamp) : Infinity;
  
  // Don't auto-restore if cleared within last hour (3600000 ms)
  if (dataClearedFlag === 'true' && timeSinceClear < 3600000) {
    console.log('[RESTORE] Data was cleared recently, not auto-restoring');
    APB.step2.rfpText = '';
  } else {
    // Only restore if not recently cleared
    console.log('[RESTORE] Checking for stored data...');
    const restoredText = sessionStorage.getItem('apb.rfp_text') || localStorage.getItem('apb.rfpText.v1') || '';
    if (restoredText) {
      console.log('[RESTORE] Found and restored RFP text, length:', restoredText.length);
    }
    APB.step2.rfpText = restoredText;
  }
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
  
  // Wire up Step 5 export buttons
  const btnExportExcel = document.querySelector("#btn-export-excel");
  if (btnExportExcel) btnExportExcel.onclick = exportExcel;
  
  const btnExportCSV = document.querySelector("#btn-export-csv");
  if (btnExportCSV) btnExportCSV.onclick = exportCSV;

  // UI wiring (new Step 2)
  const proceedBtn = document.querySelector("#btnProceedToStep3");
  if (proceedBtn) proceedBtn.onclick = onProceedToStep3;
  
  const reconcileBtn = document.querySelector("#btnRunReconcile");
  if (reconcileBtn) {
    reconcileBtn.onclick = async (e) => {
      e.preventDefault();
      
      // Task 1.7: Get RFP text from multiple sources including backend cache
      // CRITICAL FIX: Check if data was recently cleared
      const dataClearedFlag = localStorage.getItem('apb.data_cleared');
      const clearTimestamp = localStorage.getItem('apb.clear_timestamp');
      const timeSinceClear = clearTimestamp ? Date.now() - parseInt(clearTimestamp) : Infinity;
      
      let rfpText = '';
      // Only restore if not recently cleared (within last hour)
      if (dataClearedFlag !== 'true' || timeSinceClear > 3600000) {
        rfpText = window.APP?.rfpText || APB.step2.rfpText || sessionStorage.getItem('apb.rfp_text') || '';
        // IMPORTANT: Do NOT restore from localStorage.getItem('apb.rfpText.v1') anymore
        console.log('[ANALYZE] Attempting to use existing RFP text, length:', rfpText?.length || 0);
      } else {
        console.log('[ANALYZE] Data was cleared recently, not using stored RFP text');
      }
      
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
  
  // ISSUE 2 FIX: Auto-clear on first keystroke in RFP text area
  const rfpTextEl = document.querySelector("#rfpText");
  if (rfpTextEl && !rfpTextEl.dataset.clearOnKeystrokeWired) {
    rfpTextEl.dataset.clearOnKeystrokeWired = 'true';
    let hasTyped = false;
    rfpTextEl.addEventListener('keydown', async (e) => {
      // Skip modifier keys and navigation keys
      if (e.ctrlKey || e.metaKey || e.altKey || ['Tab', 'Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) {
        return;
      }
      
      // Only clear on first real character typed in a new session
      if (!hasTyped && rfpTextEl.value.trim().length === 0 && !['Backspace', 'Delete', 'Enter'].includes(e.key)) {
        hasTyped = true;
        console.log('[SESSION] Auto-clearing on first keystroke');
        
        // Clear server cache but don't reset the entire UI
        const sessionId = SessionManager.getCurrentSessionId();
        try {
          await fetch('/api/clear_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
          });
          
          // Start fresh session
          SessionManager.startNewSession();
          console.log('[SESSION] Session cleared on first keystroke');
        } catch (err) {
          console.warn('[SESSION] Failed to clear on keystroke:', err);
        }
      }
    });
  }
  
  // ISSUE 2 FIX: Auto-clear on new file upload
  const rfpFileEl = document.querySelector("#rfpFile");
  if (rfpFileEl && !rfpFileEl.dataset.clearOnUploadWired) {
    rfpFileEl.dataset.clearOnUploadWired = 'true';
    rfpFileEl.addEventListener('change', async (e) => {
      if (e.target.files && e.target.files.length > 0) {
        console.log('[SESSION] Auto-clearing on file upload');
        
        // Clear server cache
        const sessionId = SessionManager.getCurrentSessionId();
        try {
          await fetch('/api/clear_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
          });
          
          // Start fresh session
          SessionManager.startNewSession();
          console.log('[SESSION] Session cleared on file upload');
        } catch (err) {
          console.warn('[SESSION] Failed to clear on file upload:', err);
        }
      }
    });
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
  // FIX: Ensure we only send strings, not objects
  // GPT-5.1 Pro: Also include SmartSelectionState.selectedL3Map as fallback
  const l3Payload = {};
  
  // First, populate from SmartSelectionState if available (curated AI selections)
  if (window.SmartSelectionState && Object.keys(window.SmartSelectionState.selectedL3Map).length > 0) {
    console.log('[Build] Using SmartSelectionState.selectedL3Map for L3 payload');
    for (const [delivCode, compMap] of Object.entries(window.SmartSelectionState.selectedL3Map)) {
      if (codes.includes(delivCode)) {
        if (!l3Payload[delivCode]) l3Payload[delivCode] = {};
        for (const [compName, taskLabels] of Object.entries(compMap)) {
          l3Payload[delivCode][compName] = Array.isArray(taskLabels) ? taskLabels : [];
        }
      }
    }
  }
  
  // Also include from APB.step2.selectedL3ByKey (may have additional manual selections)
  Object.entries(APB.step2.selectedL3ByKey).forEach(([key, l3Set]) => {
    const [code, component] = key.split('::');
    if (codes.includes(code) && l3Set && l3Set.size > 0) {
      if (!l3Payload[code]) l3Payload[code] = {};
      // Only add if not already set by SmartSelectionState
      if (!l3Payload[code][component]) {
        // Convert Set to Array and ensure all items are strings
        l3Payload[code][component] = Array.from(l3Set).map(item => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object') {
            const name = item.Task_Label || item.task_label || item.name || item.title || item.label || '';
            if (name && typeof name === 'string') return name;
          }
          return null;
        }).filter(name => name && name !== '[object Object]' && name !== '');
      }
    }
  });
  
  console.log('[Build] L3 payload:', l3Payload);

  // ISSUE 3 FIX: Build retainers payload from pricingData
  const retainersPayload = [];
  pricingData.deliverableTypes.forEach((type, code) => {
    if (type === 'RETAINER' && codes.includes(code)) {
      retainersPayload.push({
        deliverable_code: code,
        months: pricingData.retainers.get(code) || 12,
        type: 'RETAINER'
      });
    }
  });

  // ISSUE FIX 1: Include both snake_case and camelCase formats for compatibility
  const payload = {
    // Snake_case versions
    selected_deliverable_codes: codes,
    selected_components_map: selectedComponentsPayload,
    selected_l3_map: l3Payload,
    // CamelCase versions for compatibility
    selectedDeliverableCodes: codes,
    selectedComponentsMap: selectedComponentsPayload,
    selectedL3Map: l3Payload,
    // Pricing and configuration
    pricing_mode: window.getPricingModeFromUI?.() || 'Flat_Blended',
    blended_rate: window.getBlendedRateFromUI?.() || 210,
    rate_band: window.getRateBandFromUI?.() || 'Standard_US',
    use_slack: window.getUseSlackFromUI?.() || false,
    slack_after_internal: window.getSlackInternalFromUI?.() || 1,
    slack_after_client: window.getSlackClientFromUI?.() || 2,
    slack_global_pct: window.getSlackPctFromUI?.() || 0.05,
    project_start: window.getProjectStartFromUI?.() || null,
    client_budget_usd: window.getClientBudgetFromUI?.() || null,
    project_name: document.getElementById('projectName')?.value || null,
    session_id: window.SessionManager ? window.SessionManager.getCurrentSessionId() : null,
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
  
  // Persist SCENARIOS to localStorage for rebuild and other operations
  try {
    const sessionId = window.APB?.sessionId || 
                     sessionStorage.getItem('apb.session_id') || 
                     Date.now().toString();
    const storageKey = `scenarios_${sessionId}`;
    localStorage.setItem(storageKey, JSON.stringify(scenarios));
    localStorage.setItem('latest_scenarios', JSON.stringify(scenarios));
    console.log('[BUILD] Saved scenarios to localStorage:', storageKey);
    console.log('[BUILD] window.SCENARIOS.A is now available with', scenarios.A.items?.length || 0, 'items');
  } catch (err) {
    console.error('[BUILD] Failed to save scenarios to localStorage:', err);
  }

  // Update AI button states now that scenario exists
  updateAIButtonStates();

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

  // FIX: Show Step 4 and Step 5 WITHOUT scrolling to them
  // This allows the user to review pricing in Step 3 first
  // They can scroll down to Step 4 when ready to generate timeline
  const step4 = document.querySelector("#step4");
  const step5 = document.querySelector("#step5");
  if (step5) step5.style.display = 'block';
  if (step4) step4.style.display = 'block';
  
  // NOTE: We do NOT call step4.scrollIntoView() or window.showStep4()
  // The page stays focused on Step 3 so user reviews pricing first
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
        current_stage: data.current_stage || '',
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

// Removed duplicate - see proper implementation below

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
  let rfpText = (textEl?.value || '').trim();
  const btnAnalyze = document.querySelector('#btnAnalyze');
  const analysisMode = document.getElementById('analysis-mode')?.value || 'fast';

  // ============================================================================
  // SESSION ISOLATION: Start fresh session for each new analysis
  // ============================================================================
  const sessionId = SessionManager.startNewSession();
  console.log('[SESSION] New analysis session:', sessionId);
  
  // Reset global state for fresh analysis
  SCENARIOS = null;
  DELIVERABLES = [];
  DELIV_INDEX = {};
  DELIV_INDEX_LO = {};
  
  // Reset Step 2 state
  selectionStore.deliverables.clear();
  selectionStore.componentsByDeliv.clear();
  selectionStore.l3ByComponent.clear();
  S2.selectedComponentsByCode = {};
  S2.aiSuggestedCodes = new Set();
  S2.activeDeliverableCode = null;
  S2.activeComponentName = null;
  
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
      
      // Store summary globally for unified card rendering
      window.currentRfpSummary = summary;
      
      // Render summary card immediately with default planner label
      renderRfpSummaryCard(summary, {
        plannerLabel: analysisMode === 'deep' ? 'GPT-5 Pro AI Planner' : 'Fast AI Planner'
      });
      console.log('[RFP Summary] Card rendered from /api/summarize_by_file');
      
      // Update rfpText from file extraction
      rfpText = summary.summary_text || '';
      
      // Start progress polling if image processing jobs were started
      if (summary.job_ids && summary.job_ids.length > 0 && summary.processing_images) {
        startProgressPolling(summary.job_ids[0]);
      }
    }
    
    // If using textarea-only (no file), call /api/summarize to get summary object
    if (rfpText && !fileEl?.files?.length) {
      try {
        updateAIProgress({ progress: 8, current_stage: 'Generating RFP summary...', elapsed_seconds: 0, eta_seconds: null });
        const summaryRes = await fetchWithRetry('/api/summarize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rfp_text: rfpText })
        });
        
        if (summaryRes.ok) {
          const summary = await summaryRes.json();
          window.currentRfpSummary = summary;
          renderRfpSummaryCard(summary, {
            plannerLabel: analysisMode === 'deep' ? 'GPT-5 Pro AI Planner' : 'Fast AI Planner'
          });
          console.log('[RFP Summary] Card rendered from /api/summarize');
        }
      } catch (err) {
        console.warn('[RFP Summary] Failed to generate summary from textarea:', err);
        // Continue with analysis even if summary fails
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
    
    // Get selected mode (Fast or Deep) - use analysisMode variable
    const selectedMode = analysisMode || 'deep';
    
    const aiRes = await fetchWithRetry('/api/ai/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        request_text: rfpText,
        strictness: 'balanced',
        tier: tier,
        mode: selectedMode,
        session_id: sessionId
      })
    }, 3, 2000);
    
    if (!aiRes.ok) {
      throw new Error(`AI analysis error: ${aiRes.status} ${aiRes.statusText}`);
    }
    
    const jobInfo = await aiRes.json();
    
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
      
      // Start polling for job status (SSE not implemented for AI jobs yet)
      // Poll the correct endpoint for job status
      aiAnalysisInterval = setInterval(() => pollAIAnalysis(jobInfo.job_id), 2000);
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
          }
          
          // Handle errors
          if (data.status === 'failed') {
            eventSource.close();
            hideAIProgressBar();
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
          aiAnalysisInterval = setInterval(() => pollAIAnalysis(aiAnalysisJobId), 2000);
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

// Poll AI Analysis job status and handle completion
async function pollAIAnalysis(jobId) {
  if (!jobId) return;
  
  try {
    const response = await fetch(`/api/agencydb/status/${jobId}`);
    if (!response.ok) {
      console.error('Failed to get job status:', response.status);
      return;
    }
    
    const data = await response.json();
    console.log(`[AI Analysis] Job ${jobId} status: ${data.status}`);
    
    // Update progress UI
    if (data.progress !== undefined || data.current_stage) {
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
    }
    
    // Handle completion
    if (data.status === 'completed') {
      console.log('[AI Analysis] Job completed, checking for result data...', data);
      
      // Stop polling first
      if (aiAnalysisInterval) {
        clearInterval(aiAnalysisInterval);
        aiAnalysisInterval = null;
        console.log('[AI Analysis] Stopped polling interval');
      }
      
      hideAIProgressBar();
      
      // Check if we have result data
      if (data.result) {
        console.log('[AI Analysis] Found result data with deliverables');
        
        // Store the AI plan results
        const aiPlanResponse = data.result;
        window.APP = window.APP || {};
        window.APP.aiPlan = aiPlanResponse;
        
        // Store with session isolation
        const sessionId = SessionManager.getCurrentSessionId();
        if (sessionId) {
          SessionManager.setSessionItem('ai_plan', aiPlanResponse);
        }
        sessionStorage.setItem('apb:aiPlan', JSON.stringify(aiPlanResponse));
        
        // Show Step 2
        const step2 = document.getElementById('step2');
        if (step2) {
          step2.style.display = 'block';
          step2.scrollIntoView({ behavior: 'smooth' });
          console.log('[AI Analysis] Step 2 is now visible');
        }
        
        // Render the AI plan with deliverables
        renderAIPlan(aiPlanResponse);
        
        // Re-enable the analyze button
        const btnAnalyze = document.querySelector('#btnAnalyze');
        if (btnAnalyze) {
          btnAnalyze.disabled = false;
          btnAnalyze.textContent = 'Analyze with AI';
        }
        
        console.log('[AI Analysis] Successfully completed and displayed deliverables');
      } else {
        console.error('[AI Analysis] Job completed but no result data found!', data);
        alert('Analysis completed but no deliverables were returned. Please try again.');
        
        // Re-enable button
        const btnAnalyze = document.querySelector('#btnAnalyze');
        if (btnAnalyze) {
          btnAnalyze.disabled = false;
          btnAnalyze.textContent = 'Analyze with AI';
        }
      }
      
      return; // Exit early after handling completion
    }
    
    // Handle failure
    if (data.status === 'failed') {
      // Stop polling
      if (aiAnalysisInterval) {
        clearInterval(aiAnalysisInterval);
        aiAnalysisInterval = null;
      }
      
      hideAIProgressBar();
      
      const errorMessage = data.error || 'Unknown error occurred during AI analysis';
      console.error('[AI Analysis] Job failed:', errorMessage);
      alert(`AI analysis failed: ${errorMessage}`);
      
      // Re-enable the analyze button
      const btnAnalyze = document.querySelector('#btnAnalyze');
      if (btnAnalyze) {
        btnAnalyze.disabled = false;
        btnAnalyze.textContent = 'Analyze with AI';
      }
    }
    
  } catch (error) {
    console.error('[AI Analysis] Error polling job status:', error);
    // Don't stop polling on network errors - they might be temporary
  }
}

// Centralized RFP Summary Card Renderer (for both Fast and Deep modes)
// Data source: /api/summarize or /api/summarize_by_file only (stored in window.currentRfpSummary)
// Bradley Spec: Summary bullets MUST render as discrete <li> elements, NOT as paragraph with inline bullets
function renderRfpSummaryCard(summary, options = {}) {
  const {
    plannerLabel = "Fast AI Planner",   // Default label before mode selection
    complexity = "Medium"               // Default complexity
  } = options;

  const summaryPanel = document.getElementById('ai-summary-panel');
  if (!summaryPanel) {
    console.warn('[RFP Summary] No summary panel element found');
    return;
  }
  
  if (!summary) {
    console.warn('[RFP Summary] No summary data provided');
    summaryPanel.innerHTML = '<p style="color: #6b7280; padding: 16px;">No RFP summary available</p>';
    return;
  }

  // =========================================================================
  // BUILD SUMMARY BULLETS HTML (Bradley Spec: 3-6 discrete bullets with bold labels)
  // MUST always render as <ul><li> bullets, NEVER as paragraph
  // =========================================================================
  
  // Helper to build a single bullet <li> element with inline styles
  function buildBulletLi(label, desc) {
    const safeLabel = label || 'Item';
    const safeDesc = desc || '';
    return `<li style="display: list-item !important; list-style: disc outside !important; margin-left: 20px !important; margin-bottom: 8px !important; padding-left: 4px !important;"><strong>${safeLabel}</strong> — ${safeDesc}</li>`;
  }
  
  // Helper to wrap bullets in <ul> with inline styles
  function wrapInUl(bulletItems) {
    return `<ul style="list-style-type: disc !important; padding-left: 20px !important; margin: 0 0 12px 0 !important;">${bulletItems}</ul>`;
  }
  
  // Default fallback bullets (Bradley spec: minimum 3 bullets required)
  const fallbackBullets = [
    { label: 'Strategy', short_desc: 'Project strategy and planning requirements' },
    { label: 'Creative', short_desc: 'Creative and design deliverables' },
    { label: 'Execution', short_desc: 'Implementation and delivery scope' }
  ];
  
  let summaryBulletsHtml = '';
  let bullets = summary.summary_bullets || [];
  
  console.log('[RFP Summary] Building bullets from summary_bullets array:', bullets.length, 'items');
  
  // If no structured bullets, try to parse from summary_text
  if (bullets.length === 0) {
    const summaryText = summary.summary_text || summary.summary || '';
    console.log('[RFP Summary] No summary_bullets, attempting text parsing. Text length:', summaryText.length);
    
    if (summaryText && summaryText.length > 0) {
      // AGGRESSIVE BULLET PARSING: Split on • character anywhere in text
      // This handles "• Label: desc • Label2: desc2" format
      const bulletPattern = /•\s*/;
      const rawBullets = summaryText.split(bulletPattern).filter(s => s.trim().length > 0);
      
      console.log('[RFP Summary] Text split produced', rawBullets.length, 'segments');
      
      if (rawBullets.length >= 2) {
        // Parse each segment into {label, short_desc}
        bullets = rawBullets.map(segment => {
          const trimmed = segment.trim();
          // Try to extract "Label: description" pattern
          const colonMatch = trimmed.match(/^([^:]+):\s*(.+)$/s);
          if (colonMatch) {
            return { label: colonMatch[1].trim(), short_desc: colonMatch[2].trim() };
          }
          // Try to extract first sentence as label
          const periodMatch = trimmed.match(/^([^.]+)\.\s*(.*)$/s);
          if (periodMatch && periodMatch[1].length < 50) {
            return { label: periodMatch[1].trim(), short_desc: periodMatch[2].trim() };
          }
          // Use first 40 chars as label, rest as desc
          if (trimmed.length > 40) {
            return { label: trimmed.substring(0, 40).trim() + '...', short_desc: trimmed.substring(40).trim() };
          }
          return { label: trimmed, short_desc: '' };
        });
        console.log('[RFP Summary] Parsed', bullets.length, 'bullets from text');
      }
    }
  }
  
  // GUARANTEE: Always have at least 3 bullets (Bradley spec)
  if (bullets.length < 3) {
    console.log('[RFP Summary] Only', bullets.length, 'bullets found, padding with fallbacks');
    const needed = 3 - bullets.length;
    for (let i = 0; i < needed && i < fallbackBullets.length; i++) {
      bullets.push(fallbackBullets[i]);
    }
  }
  
  // Cap at 6 bullets max (Bradley spec: 3-6 bullets)
  if (bullets.length > 6) {
    bullets = bullets.slice(0, 6);
    console.log('[RFP Summary] Capped bullets at 6');
  }
  
  // Build the HTML
  const bulletItems = bullets.map(b => buildBulletLi(b.label, b.short_desc)).join('');
  summaryBulletsHtml = wrapInUl(bulletItems);
  
  // ASSERTION: Verify we always produce 3-6 bullets
  const bulletCount = bullets.length;
  console.assert(bulletCount >= 3 && bulletCount <= 6, 
    `[RFP Summary] VIOLATION: Expected 3-6 bullets, got ${bulletCount}`);
  console.log('[RFP Summary] Final bullet count:', bulletCount, '(min: 3, max: 6)');
  
  // Extract goals from deliverables array (RfpSummary format)
  const deliverables = summary.deliverables || [];
  const goals = deliverables.map(d => d.label || d.title).filter(Boolean);
  const goalsHtml = goals.length > 0 ? goals.map(g => `<li style="display: list-item !important; list-style: disc outside !important;">${g}</li>`).join('') : '';
  
  const channels = (summary.channels || []).join(', ') || 'Not specified';
  const markets = (summary.markets || []).join(', ') || 'Not specified';
  const displayComplexity = summary.complexity || complexity;

  summaryPanel.innerHTML = `
    <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.1)); padding: 16px; border-radius: 8px; margin-bottom: 16px; border: 1px solid rgba(139, 92, 246, 0.2);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <span style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 6px 12px; border-radius: 6px; font-size: 0.85em; font-weight: 600;">
          🧠 ${plannerLabel}
        </span>
        <span style="color: #6b7280; font-size: 0.85em; font-style: italic;">
          Evidence-backed • Reasoning-powered
        </span>
      </div>
      
      <h3 style="margin: 0 0 12px 0; color: #6366f1;">📋 RFP Summary</h3>
      ${summaryBulletsHtml}
      
      ${goalsHtml ? `
        <div style="margin-bottom: 12px;">
          <strong style="color: var(--text);">Key Deliverables:</strong>
          <ul style="margin: 4px 0 0 20px; line-height: 1.6; color: var(--text); list-style-type: disc !important; padding-left: 20px !important;">${goalsHtml}</ul>
        </div>
      ` : ''}
      
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-top: 12px;">
        <div>
          <strong style="color: var(--text);">Channels:</strong> 
          <span id="rfp-channels" style="color: #6b7280;">${channels}</span>
        </div>
        <div>
          <strong style="color: var(--text);">Markets:</strong> 
          <span id="rfp-markets" style="color: #6b7280;">${markets}</span>
        </div>
        <div>
          <strong style="color: var(--text);">Complexity:</strong> 
          <span style="color: #6b7280; text-transform: capitalize;">${displayComplexity}</span>
        </div>
      </div>
    </div>
  `;
  
  console.log(`[RFP Summary] Rendered with planner: ${plannerLabel}`);
}

// Update summary card badge when analysis mode changes (Fast ↔ Deep)
function updateSummaryCardMode() {
  if (!window.currentRfpSummary) {
    console.log('[RFP Summary] No summary available to update');
    return;
  }
  
  const analysisMode = document.getElementById('analysis-mode')?.value || 'fast';
  const plannerLabel = analysisMode === 'deep' ? 'GPT-5 Pro AI Planner' : 'Fast AI Planner';
  
  // Re-render card with new badge
  renderRfpSummaryCard(window.currentRfpSummary, {
    plannerLabel: plannerLabel
  });
  console.log(`[RFP Summary] Updated badge to: ${plannerLabel}`);
}

// Set analysis mode (called from HTML buttons) and update summary card badge
function setAnalysisMode(mode) {
  // Update hidden input
  const modeInput = document.getElementById('analysis-mode');
  if (modeInput) {
    modeInput.value = mode;
  }
  
  // Update button styles
  const fastBtn = document.getElementById('mode-fast');
  const deepBtn = document.getElementById('mode-deep');
  
  if (mode === 'fast') {
    if (fastBtn) {
      fastBtn.classList.add('mode-active');
      fastBtn.style.background = '#10b981';
      fastBtn.style.color = 'white';
      fastBtn.style.borderColor = '#10b981';
    }
    if (deepBtn) {
      deepBtn.classList.remove('mode-active');
      deepBtn.style.background = 'white';
      deepBtn.style.color = '#6366f1';
      deepBtn.style.borderColor = '#6366f1';
    }
  } else {
    if (deepBtn) {
      deepBtn.classList.add('mode-active');
      deepBtn.style.background = '#6366f1';
      deepBtn.style.color = 'white';
      deepBtn.style.borderColor = '#6366f1';
    }
    if (fastBtn) {
      fastBtn.classList.remove('mode-active');
      fastBtn.style.background = 'white';
      fastBtn.style.color = '#10b981';
      fastBtn.style.borderColor = '#10b981';
    }
  }
  
  // Update summary card badge if summary already exists
  updateSummaryCardMode();
  
  console.log(`[Analysis Mode] Set to: ${mode}`);
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
  
  // Check if we have weighted deliverables to display
  const hasWeightedData = aiPlan.weighted_deliverables || plan.weighted_deliverables || 
                          (plan.deliverables && plan.deliverables.length > 0);
  
  // If we have weighted deliverables, render them using the TCGWeights system
  if (hasWeightedData && window.TCGWeights) {
    console.log('[AI Analysis] Checking for weighted deliverables to display');
    
    // Prepare weighted data format for TCGWeights
    let weightedData = aiPlan.weighted_deliverables || plan.weighted_deliverables;
    
    // Convert suggestions_by_department to weighted format if needed
    if (!weightedData && plan.deliverables) {
      console.log('[AI Analysis] Converting deliverables to weighted format');
      const deliverables = [];
      
      // Flatten all department suggestions into weighted format
      if (suggestionsByDept) {
        for (const [dept, deptDelivs] of Object.entries(suggestionsByDept)) {
          for (const deliv of (deptDelivs || [])) {
            deliverables.push({
              deliverable_code: deliv.deliverable_code || deliv.code,
              title: deliv.title,
              department: dept,
              match_percent: Math.round((deliv.calibrated_confidence || 0) * 100),
              tfidf_similarity: deliv.tfidf_similarity || deliv.calibrated_confidence,
              direct_match: deliv.direct_match || false,
              matched_keywords: deliv.matched_keywords || []
            });
          }
        }
      }
      
      weightedData = { deliverables };
    }
    
    // Show the weighted suggestions container
    const weightsContainer = document.getElementById('step2-ai-weights-container');
    if (weightsContainer && weightedData && weightedData.deliverables && weightedData.deliverables.length > 0) {
      weightsContainer.style.display = 'block';
      window.TCGWeights.render('#step2-ai-weights', weightedData, 'confidence_only');
      console.log(`[AI Analysis] Rendered ${weightedData.deliverables.length} weighted deliverables`);
    }
  }
  
  // Summary card is now rendered from window.currentRfpSummary only (not planner response)
  // The card is populated by /api/summarize before analysis runs
  
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
      
      <!-- Smart Select Cards (AI + TF-IDF) -->
      <div id="smart-select-container" style="background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 8px; padding: 16px; margin-bottom: 16px;">
        
        <!-- Row 1: AI Smart Select -->
        <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 16px;">
          <div>
            <h4 style="margin: 0 0 4px 0; font-size: 0.95em; font-weight: 600; color: var(--text);">🎯 AI Smart Select by Relevancy</h4>
            <p style="margin: 0; font-size: 0.8em; color: var(--muted);">
              Automatically select deliverables, components, and tasks with <span style="font-weight: 500;">AI confidence ≥ threshold.</span>
            </p>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <input type="number" 
                   id="ai-smart-threshold" 
                   min="0" 
                   max="100" 
                   value="70"
                   style="width: 60px; padding: 6px 10px; background: var(--card); border: 1px solid var(--border); border-radius: 4px; color: var(--text); text-align: right;">
            <span style="color: var(--muted); font-size: 0.9em;">%</span>
            <button onclick="applySmartSelection('ai')" 
                    id="btn-ai-smart-select"
                    style="padding: 8px 16px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 0.9em; transition: all 0.2s;"
                    onmouseover="this.style.opacity='0.9'" 
                    onmouseout="this.style.opacity='1'">
              Apply AI Smart Selection
            </button>
          </div>
        </div>

        <!-- Divider -->
        <div style="margin: 16px 0; border-top: 1px solid rgba(139, 92, 246, 0.2);"></div>

        <!-- Row 2: TF-IDF Smart Select -->
        <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 16px;">
          <div>
            <h4 style="margin: 0 0 4px 0; font-size: 0.95em; font-weight: 600; color: var(--text);">📊 TF-IDF Smart Select by Relevancy</h4>
            <p style="margin: 0; font-size: 0.8em; color: var(--muted);">
              Automatically select deliverables, components, and tasks with <span style="font-weight: 500;">TF-IDF similarity ≥ threshold.</span>
            </p>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <input type="number" 
                   id="tfidf-smart-threshold" 
                   min="0" 
                   max="100" 
                   value="70"
                   style="width: 60px; padding: 6px 10px; background: var(--card); border: 1px solid var(--border); border-radius: 4px; color: var(--text); text-align: right;">
            <span style="color: var(--muted); font-size: 0.9em;">%</span>
            <button onclick="applySmartSelection('tfidf')" 
                    id="btn-tfidf-smart-select"
                    style="padding: 8px 16px; background: #4b5563; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 0.9em; transition: all 0.2s;"
                    onmouseover="this.style.background='#6b7280'" 
                    onmouseout="this.style.background='#4b5563'">
              Apply TF-IDF Smart Selection
            </button>
          </div>
        </div>
      </div>
      
      <div style="background: var(--card); padding: 12px; border-radius: 8px; margin-bottom: 16px; border-left: 4px solid var(--accent);">
        <h4 style="margin: 0 0 8px 0; color: var(--text);">📊 Project Flow & Department Sequencing</h4>
        <p style="margin: 0; font-size: 0.9em; line-height: 1.6; color: var(--text);">
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
        <details class="ai-dept-group" style="margin-bottom: 16px; border: 1px solid var(--border); border-radius: 8px; padding: 12px; background: linear-gradient(to right, ${deptColors[dept]}15 0%, transparent 100%);">
          <summary style="cursor: pointer; font-weight: 600; font-size: 1.1em; color: var(--text); margin-bottom: 12px;">
            <span style="color: ${deptColors[dept]}; margin-right: 8px;">●</span>
            ${dept} <span style="color: var(--muted); font-weight: normal; font-size: 0.9em;">(${deliverables.length} deliverable${deliverables.length > 1 ? 's' : ''})</span>
          </summary>
      `;
      
      for (const deliv of deliverables) {
        const confidence = Math.round((deliv.calibrated_confidence || 0) * 100);
        const tfidfSimilarity = Math.round((deliv.tfidf_similarity || 0) * 100);
        const confidenceColor = confidence >= 75 ? '#10b981' : confidence >= 50 ? '#f59e0b' : '#ef4444';
        const tfidfColor = tfidfSimilarity >= 75 ? '#10b981' : tfidfSimilarity >= 50 ? '#f59e0b' : '#ef4444';
        const delivCode = deliv.deliverable_code || deliv.code;
        
        html += `
          <div class="ai-deliverable" data-deliv-code="${delivCode}" data-department="${dept}" style="background: var(--card); padding: 12px; border-radius: 6px; margin-bottom: 12px; border-left: 3px solid ${confidenceColor};">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
              <div style="display: flex; align-items: center; gap: 8px; flex: 1;">
                <input type="checkbox" 
                       class="ai-deliv-checkbox" 
                       data-code="${delivCode}" 
                       data-title="${deliv.title}"
                       data-dept="${dept}"
                       style="cursor: pointer;">
                <div style="flex: 1;">
                  <h4 style="margin: 0; color: var(--text);">
                    <span style="color: ${deptColors[dept]}; font-weight: 500; font-size: 0.85em;">[${dept}]</span>
                    ${deliv.title}
                  </h4>
                </div>
              </div>
              <div style="display: flex; gap: 8px; align-items: center;">
                <span style="font-size: 0.85em; color: ${confidenceColor}; font-weight: 600;" title="AI Confidence Score">${confidence}% AI</span>
                <span style="font-size: 0.85em; color: ${tfidfColor}; font-weight: 600;" title="TF-IDF Keyword Similarity">${tfidfSimilarity}% TF-IDF</span>
                <span style="font-size: 0.85em; color: var(--muted);">${deliv.planned_hours || 0}h</span>
                <button class="btn-small" 
                        onclick="addAIDeliverableToSelection('${delivCode}', this)"
                        style="padding: 4px 12px; font-size: 0.85em; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">
                  Add to Selection
                </button>
              </div>
            </div>
            
            ${deliv.why ? `
              <p style="margin: 8px 0; font-size: 0.9em; color: var(--text); line-height: 1.5;">${deliv.why}</p>
            ` : ''}
            
            ${deliv.risks ? `
              <div style="background: rgba(239, 68, 68, 0.1); padding: 8px; border-radius: 4px; margin: 8px 0; font-size: 0.85em; color: var(--text);">
                <strong>⚠️ Risks:</strong> ${deliv.risks}
              </div>
            ` : ''}
            
            ${(deliv.components || []).length > 0 ? `
              <details style="margin-top: 8px;">
                <summary style="cursor: pointer; font-size: 0.9em; color: var(--text); font-weight: 500;">
                  Components (${deliv.components.length})
                  <button onclick="event.stopPropagation(); selectAllComponents('${delivCode}', true)" 
                          style="margin-left: 8px; padding: 2px 8px; font-size: 0.8em; background: var(--border); color: var(--text); border: none; border-radius: 3px;">
                    Select All
                  </button>
                  <button onclick="event.stopPropagation(); selectAllComponents('${delivCode}', false)" 
                          style="margin-left: 4px; padding: 2px 8px; font-size: 0.8em; background: var(--border); color: var(--text); border: none; border-radius: 3px;">
                    Deselect All
                  </button>
                </summary>
                <div style="margin-top: 8px; margin-left: 16px;">
                  ${deliv.components.map((comp, idx) => `
                    <div style="margin-bottom: 8px; padding: 8px; background: var(--card); border-radius: 4px;">
                      <div style="display: flex; align-items: start; gap: 8px;">
                        <input type="checkbox" 
                               class="ai-comp-checkbox" 
                               data-deliv="${delivCode}" 
                               data-comp="${comp.title}"
                               data-comp-id="${comp.id || comp.title}"
                               style="cursor: pointer; margin-top: 2px;">
                        <div style="flex: 1;">
                          <div style="font-weight: 500; color: var(--text);">${comp.title}</div>
                          <div style="font-size: 0.85em; color: var(--muted); margin-top: 4px;">${comp.why || ''}</div>
                          <div style="font-size: 0.85em; color: var(--muted); margin-top: 2px;">${comp.planned_hours || 0}h</div>
                        </div>
                      </div>
                      
                      ${(comp.tasks || []).length > 0 ? `
                        <details style="margin-top: 8px; margin-left: 24px;">
                          <summary style="cursor: pointer; font-size: 0.85em; color: var(--muted);">
                            ✓ AI-Selected Tasks (${comp.tasks.length})
                            <button onclick="event.stopPropagation(); selectAllTasks('${delivCode}', '${comp.title}', true)" 
                                    style="margin-left: 8px; padding: 2px 6px; font-size: 0.75em; background: var(--border); color: var(--text); border: none; border-radius: 3px;">
                              Select All
                            </button>
                            <button onclick="event.stopPropagation(); selectAllTasks('${delivCode}', '${comp.title}', false)" 
                                    style="margin-left: 4px; padding: 2px 6px; font-size: 0.75em; background: var(--border); color: var(--text); border: none; border-radius: 3px;">
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
                                    <div style="font-size: 0.85em; color: var(--text); font-weight: 500;">${task.title}</div>
                                    ${task.why ? `<div style="font-size: 0.8em; color: var(--muted); margin-top: 2px;">${task.why}</div>` : ''}
                                    <div style="font-size: 0.8em; color: var(--muted); margin-top: 2px;">${task.planned_hours || 0}h</div>
                                  </div>
                                </div>
                              </div>
                            `).join('')}
                          </div>
                        </details>
                      ` : '<div style="font-size: 0.85em; color: var(--muted); margin-top: 6px; font-style: italic; margin-left: 24px;">No specific tasks selected by AI</div>'}
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
      <div style="margin-top: 20px; padding-top: 20px; border-top: 2px solid var(--border); display: flex; gap: 12px;">
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
    
    // Initialize Step 2 selection mode controls
    initializeStep2SelectionMode();
  }
}

// Initialize Step 2 Selection Mode Controls (no-op - radio buttons removed)
function initializeStep2SelectionMode() {
  // Radio buttons removed from UI - now using Smart Select cards with AI/TF-IDF thresholds
  console.log('[Step2 SelectionMode] Initialization skipped - using Smart Select cards');
}

// Apply Step 2 Selection Mode (deprecated - kept for backward compatibility)
function applyStep2SelectionMode(selectionMode) {
  console.log(`[Step2 SelectionMode] Deprecated - use applySmartSelection('ai') or applySmartSelection('tfidf') instead`);
}

// Expose functions globally (for backward compatibility)
window.initializeStep2SelectionMode = initializeStep2SelectionMode;
window.applyStep2SelectionMode = applyStep2SelectionMode;

// ========== SMART SELECTION STATE (GPT-5.1 Pro L3 Task Filtering) ==========
// This structure tracks the curated selections from AI/TF-IDF Smart Selection
// to ensure only AI-vetted L3 tasks flow through to Step 3, not all database tasks
const SmartSelectionState = {
  selectedDeliverableCodes: [],           // Array of deliverable codes
  selectedComponentsMap: {},               // { deliverableCode: [componentNames...] }
  selectedL3Map: {},                        // { deliverableCode: { componentName: [taskLabels...] } }
  mode: null,                               // 'ai' or 'tfidf'
  threshold: 70,                            // Current threshold percentage
  lastApplied: null                         // Timestamp of last application
};
window.SmartSelectionState = SmartSelectionState;

// Helper to clear SmartSelectionState
function clearSmartSelectionState() {
  SmartSelectionState.selectedDeliverableCodes = [];
  SmartSelectionState.selectedComponentsMap = {};
  SmartSelectionState.selectedL3Map = {};
  SmartSelectionState.mode = null;
  SmartSelectionState.lastApplied = null;
  console.log('[SmartSelection] State cleared');
}
window.clearSmartSelectionState = clearSmartSelectionState;

// Helper to get total L3 task count from SmartSelectionState
function getSmartSelectionL3Count() {
  let count = 0;
  Object.values(SmartSelectionState.selectedL3Map).forEach(compMap => {
    Object.values(compMap).forEach(taskList => {
      count += Array.isArray(taskList) ? taskList.length : 0;
    });
  });
  return count;
}
window.getSmartSelectionL3Count = getSmartSelectionL3Count;

// Smart Selection Function - Select based on AI confidence or TF-IDF similarity threshold
// GPT-5.1 Pro: Now populates SmartSelectionState with L3 tasks from l3_by_component
function applySmartSelection(mode = 'ai') {
  // Get the appropriate threshold based on mode
  const thresholdInputId = mode === 'ai' ? 'ai-smart-threshold' : 'tfidf-smart-threshold';
  const thresholdInput = document.getElementById(thresholdInputId);
  if (!thresholdInput) {
    console.warn(`Smart select threshold input not found: ${thresholdInputId}`);
    return;
  }
  
  const threshold = Math.max(0, Math.min(100, parseFloat(thresholdInput.value) || 70));
  const modeLabel = mode === 'ai' ? 'AI Confidence' : 'TF-IDF Similarity';
  console.log(`[SmartSelection] Applying ${modeLabel} with threshold: ${threshold}%`);
  
  // Check if AI data is available
  if (!window.lastAIPlan || !window.lastAIPlan.suggestions_by_department) {
    console.warn('No AI suggestions available. Please run AI analysis first.');
    alert('No AI suggestions available. Please run AI analysis first.');
    return;
  }
  
  // Clear all current selections first
  clearAllAISelections();
  
  // GPT-5.1 Pro: Clear and rebuild SmartSelectionState
  clearSmartSelectionState();
  SmartSelectionState.mode = mode;
  SmartSelectionState.threshold = threshold;
  SmartSelectionState.lastApplied = new Date().toISOString();
  
  let selectedDelivCount = 0;
  let selectedCompCount = 0;
  let selectedTaskCount = 0;
  
  // Iterate through AI suggestions data directly
  const suggestionsByDept = window.lastAIPlan.suggestions_by_department || {};
  
  for (const dept in suggestionsByDept) {
    const deliverables = suggestionsByDept[dept] || [];
    
    for (const deliv of deliverables) {
      // Get the metric based on mode
      let metricValue;
      if (mode === 'ai') {
        // AI confidence: 0-1 scale, convert to percentage
        metricValue = Math.round((deliv.calibrated_confidence || deliv.confidence || 0) * 100);
      } else {
        // TF-IDF similarity: 0-1 scale, convert to percentage
        metricValue = Math.round((deliv.tfidf_similarity || 0) * 100);
      }
      const delivCode = deliv.deliverable_code || deliv.code;
      
      console.log(`[SmartSelection] ${delivCode}: ${modeLabel}=${metricValue}% vs threshold ${threshold}%`);
      
      // Get the checkbox for this deliverable
      const delivCheckbox = document.querySelector(`.ai-deliv-checkbox[data-code="${delivCode}"]`);
      if (!delivCheckbox) {
        console.warn(`Checkbox not found for deliverable ${delivCode}`);
        continue;
      }
      
      // Check if deliverable meets threshold
      if (metricValue >= threshold) {
        delivCheckbox.checked = true;
        selectedDelivCount++;
        
        // GPT-5.1 Pro: Add to SmartSelectionState
        SmartSelectionState.selectedDeliverableCodes.push(delivCode);
        SmartSelectionState.selectedComponentsMap[delivCode] = [];
        SmartSelectionState.selectedL3Map[delivCode] = {};
        
        // For components within this deliverable
        const components = deliv.components || [];
        for (const comp of components) {
          const compName = comp.title || comp.name;
          
          // Components inherit deliverable metric (since they don't have their own)
          const compCheckbox = document.querySelector(`.ai-comp-checkbox[data-deliv="${delivCode}"][data-comp="${compName}"]`);
          if (compCheckbox) {
            compCheckbox.checked = true;
            selectedCompCount++;
            
            // GPT-5.1 Pro: Add component to SmartSelectionState
            SmartSelectionState.selectedComponentsMap[delivCode].push(compName);
            
            // GPT-5.1 Pro: Extract L3 tasks from l3_by_component (the key insight!)
            // This is the curated task list from AI, not all database tasks
            const l3ByComponent = deliv.l3_by_component || {};
            const l3Tasks = l3ByComponent[compName] || [];
            
            // Extract just the task labels (not the full objects with why/confidence)
            const taskLabels = l3Tasks.map(t => {
              if (typeof t === 'string') return t;
              return t.label || t.name || t.Task_Label || t.title || '';
            }).filter(label => label);
            
            if (taskLabels.length > 0) {
              SmartSelectionState.selectedL3Map[delivCode][compName] = taskLabels;
              selectedTaskCount += taskLabels.length;
              console.log(`[SmartSelection] ${delivCode}/${compName}: ${taskLabels.length} L3 tasks from l3_by_component`);
            } else {
              // Fallback: use tasks from comp.tasks if l3_by_component is missing
              const fallbackTasks = (comp.tasks || [])
                .filter(t => t.ai_selected)
                .map(t => t.title || t.name || t.label || '')
                .filter(label => label);
              
              if (fallbackTasks.length > 0) {
                SmartSelectionState.selectedL3Map[delivCode][compName] = fallbackTasks;
                selectedTaskCount += fallbackTasks.length;
                console.log(`[SmartSelection] ${delivCode}/${compName}: ${fallbackTasks.length} L3 tasks from fallback`);
              }
            }
            
            // Update task checkboxes in UI (for visual feedback)
            const allTaskLabelsForComp = SmartSelectionState.selectedL3Map[delivCode]?.[compName] || [];
            const taskCheckboxes = document.querySelectorAll(`.ai-task-checkbox[data-deliv="${delivCode}"][data-comp="${compName}"]`);
            taskCheckboxes.forEach(taskCb => {
              const taskTitle = taskCb.dataset.task;
              taskCb.checked = allTaskLabelsForComp.includes(taskTitle);
            });
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
  
  // Log SmartSelectionState for debugging
  console.log('[SmartSelection] State populated:', {
    deliverables: SmartSelectionState.selectedDeliverableCodes.length,
    components: Object.values(SmartSelectionState.selectedComponentsMap).flat().length,
    tasks: getSmartSelectionL3Count(),
    state: SmartSelectionState
  });
  
  // Show feedback with accurate task count from SmartSelectionState
  const actualTaskCount = getSmartSelectionL3Count();
  const feedbackMessage = `${modeLabel} Selection Applied: ${selectedDelivCount} deliverables, ${selectedCompCount} components, ${actualTaskCount} tasks selected (threshold: ${threshold}%)`;
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
    feedbackDiv.style = 'margin-top: 12px; padding: 10px; background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; border-radius: 4px; color: #10b981; font-size: 0.9em;';
    feedbackDiv.textContent = feedbackMessage;
    smartSelectContainer.appendChild(feedbackDiv);
    
    // Remove feedback after 5 seconds
    setTimeout(() => {
      feedbackDiv.remove();
    }, 5000);
  }
  
  // GPT-5.1 Pro: Update Selection Summary to reflect SmartSelectionState counts
  updateSummaryCounts();
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
  
  // GPT-5.1 Pro: Also clear SmartSelectionState
  clearSmartSelectionState();
  
  console.log('Cleared all AI selections');
}

async function applyAllSelectedFromAI() {
  // GPT-5.1 Pro: Use SmartSelectionState for curated L3 task filtering
  // This ensures only AI-vetted tasks flow through, not all database tasks
  
  console.log('[ApplySelectedFromAI] Starting with SmartSelectionState:', SmartSelectionState);
  
  let firstDelivCode = null;
  let firstCompName = null;
  
  // GPT-5.1 Pro: If SmartSelectionState has curated selections, use those
  // Otherwise fall back to reading from DOM checkboxes
  const useSmartState = SmartSelectionState.selectedDeliverableCodes.length > 0;
  
  if (useSmartState) {
    console.log('[ApplySelectedFromAI] Using SmartSelectionState for curated L3 tasks');
    
    // Process deliverables from SmartSelectionState
    for (const delivCode of SmartSelectionState.selectedDeliverableCodes) {
      if (!firstDelivCode) {
        firstDelivCode = delivCode;
      }
      
      // Add deliverable to selection if not already there
      if (!selectionStore.deliverables.has(delivCode)) {
        await selectDeliverable(delivCode);
      }
      
      // Mark as AI-suggested for tracking
      APB.step2.aiSuggestedCodes.add(delivCode);
      
      // Get components from SmartSelectionState
      const selectedComps = new Set(SmartSelectionState.selectedComponentsMap[delivCode] || []);
      
      for (const compTitle of selectedComps) {
        if (!firstCompName && delivCode === firstDelivCode) {
          firstCompName = compTitle;
        }
        
        // Ensure component is hydrated
        if (!selectionStore.componentsByDeliv.get(delivCode)?.has(compTitle)) {
          await hydrateComponentsFor(delivCode);
        }
        
        // GPT-5.1 Pro: Use curated L3 tasks from SmartSelectionState
        const curatedTasks = SmartSelectionState.selectedL3Map[delivCode]?.[compTitle] || [];
        
        if (curatedTasks.length > 0) {
          const key = `${delivCode}::${compTitle}`;
          selectionStore.l3ByComponent.set(key, new Set(curatedTasks));
          console.log(`[ApplySelectedFromAI] Set ${curatedTasks.length} curated L3 tasks for ${key}`);
        }
      }
      
      // Store selected components
      if (selectedComps.size > 0) {
        selectionStore.componentsByDeliv.set(delivCode, selectedComps);
        S2.selectedComponentsByCode[delivCode] = selectedComps;
      }
    }
    
    // Also sync to APB.step2.selectedL3ByKey for payload building
    for (const delivCode of SmartSelectionState.selectedDeliverableCodes) {
      const compMap = SmartSelectionState.selectedL3Map[delivCode] || {};
      for (const [compName, taskLabels] of Object.entries(compMap)) {
        const key = `${delivCode}::${compName}`;
        APB.step2.selectedL3ByKey[key] = new Set(taskLabels);
      }
    }
    
    console.log('[ApplySelectedFromAI] SmartSelectionState applied to selectionStore');
    
  } else {
    // Fallback: Read from DOM checkboxes (original behavior)
    console.log('[ApplySelectedFromAI] Falling back to DOM checkbox reading');
    
    const delivCheckboxes = document.querySelectorAll('.ai-deliv-checkbox:checked');
    
    for (const delivCb of delivCheckboxes) {
      const delivCode = delivCb.dataset.code;
      
      if (!firstDelivCode) {
        firstDelivCode = delivCode;
      }
      
      if (!selectionStore.deliverables.has(delivCode)) {
        await selectDeliverable(delivCode);
      }
      
      APB.step2.aiSuggestedCodes.add(delivCode);
      
      const compCheckboxes = document.querySelectorAll(`.ai-comp-checkbox[data-deliv="${delivCode}"]:checked`);
      const selectedComps = new Set();
      
      for (const compCb of compCheckboxes) {
        const compTitle = compCb.dataset.comp;
        selectedComps.add(compTitle);
        
        if (!firstCompName && delivCode === firstDelivCode) {
          firstCompName = compTitle;
        }
        
        if (!selectionStore.componentsByDeliv.get(delivCode)?.has(compTitle)) {
          await hydrateComponentsFor(delivCode);
        }
        
        const taskCheckboxes = document.querySelectorAll(`.ai-task-checkbox[data-deliv="${delivCode}"][data-comp="${compTitle}"]:checked`);
        const selectedTasks = new Set();
        
        for (const taskCb of taskCheckboxes) {
          selectedTasks.add(taskCb.dataset.task);
        }
        
        if (selectedTasks.size > 0) {
          const key = `${delivCode}::${compTitle}`;
          selectionStore.l3ByComponent.set(key, selectedTasks);
        }
      }
      
      if (selectedComps.size > 0) {
        selectionStore.componentsByDeliv.set(delivCode, selectedComps);
        S2.selectedComponentsByCode[delivCode] = selectedComps;
      }
    }
  }
  
  // GPT-5.1 Pro: Only fetch from database if SmartSelectionState wasn't used
  // This prevents overwriting curated L3 tasks with all database tasks
  if (!useSmartState) {
    const allSelectedDelivs = Array.from(selectionStore.deliverables);
    
    for (const delivCode of allSelectedDelivs) {
      const components = selectionStore.componentsByDeliv.get(delivCode);
      
      if (components && components.size > 0) {
        const componentArray = Array.from(components);
        
        try {
          const res = await fetch('/api/step2/l3/bulk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              deliverable: delivCode,
              components: componentArray
            })
          });
          
          if (res.ok) {
            const l3Data = await res.json();
            const tasksData = l3Data.l3_by_component || l3Data;
            
            for (const [compName, tasks] of Object.entries(tasksData)) {
              const key = `${delivCode}::${compName}`;
              if (!selectionStore.l3ByComponent.has(key)) {
                selectionStore.l3ByComponent.set(key, new Set());
              }
              const existingTasks = selectionStore.l3ByComponent.get(key);
              
              if (Array.isArray(tasks)) {
                tasks.forEach(task => {
                  let taskName;
                  if (typeof task === 'string') {
                    taskName = task;
                  } else if (task && typeof task === 'object') {
                    taskName = task.Task_Label || task.task_label || task.name || task.title || task.label || '';
                    if (!taskName && task.toString && task.toString() !== '[object Object]') {
                      taskName = task.toString();
                    }
                  }
                  if (taskName && typeof taskName === 'string' && taskName !== '[object Object]') {
                    existingTasks.add(taskName);
                  }
                });
              }
            }
            
            if (firstDelivCode && firstCompName) {
              S2.activeComponentName = firstCompName;
              await refreshL3Panel();
            }
            
            console.log(`Fetched L2 tasks for ${delivCode} components:`, Object.keys(tasksData));
          }
        } catch (error) {
          console.error(`Failed to fetch L2 tasks for ${delivCode}:`, error);
        }
      } else {
        try {
          const generalTasks = await api(`/api/l3?deliverable=${encodeURIComponent(delivCode)}&component=general`);
          if (generalTasks && generalTasks.length > 0) {
            const key = `${delivCode}::general`;
            selectionStore.l3ByComponent.set(key, new Set(generalTasks));
            selectionStore.componentsByDeliv.set(delivCode, new Set(['general']));
            S2.selectedComponentsByCode[delivCode] = new Set(['general']);
            console.log(`Fetched L2 tasks for ${delivCode} (general fallback):`, generalTasks.length);
          }
        } catch (error) {
          console.warn(`No components or general tasks found for ${delivCode}:`, error);
        }
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
  
  // FIX: Render L3 panel to display the first component's L2 tasks
  if (firstDelivCode && firstCompName) {
    // Use renderL3Panel which displays L2 tasks in the third column
    if (window.renderL3Panel) {
      await renderL3Panel();
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
    // FIX: Extract task name if it's an object
    let taskName = task;
    if (typeof task === 'object' && task) {
      taskName = task.Task_Label || task.task_label || task.name || task.title || task.label || String(task);
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
    html += '<div style="font-weight:600;padding:8px;color:#ffffff;background:rgba(139,92,246,0.15);border-bottom:1px solid rgba(255,255,255,0.1);">Selected</div>';
    selected.forEach(d => {
      const code = String(d.Deliverable_Code);
      const isActive = APB.step2.activeDeliverableCode === code;
      const isRetainer = pricingData.deliverableTypes.get(code) === 'RETAINER';
      const retainerMonths = pricingData.retainers.get(code) || 12;
      
      html += `
        <div class="deliv-row" data-code="${code}" style="background:${isActive ? 'rgba(139,92,246,0.15)' : 'rgba(139,92,246,0.03)'};border-left:${isActive ? '3px solid var(--accent)' : '3px solid transparent'};">
          <label style="display:flex;gap:8px;align-items:center;padding:6px 8px;cursor:pointer;">
            <input type="checkbox" class="deliv-checkbox" data-code="${code}" checked data-visible="1" />
            <span>${d.Deliverable}</span>
            ${isRetainer ? '<span style="background:#10b981;color:white;padding:2px 6px;border-radius:3px;font-size:0.75em;font-weight:600;">RETAINER</span>' : ''}
            <button onclick="event.stopPropagation(); removeDeliverableX('${code}')" style="margin-left:auto;background:none;border:none;color:var(--danger);cursor:pointer;font-size:1.2em;padding:0 8px;">×</button>
            <small style="opacity:.75">${d.Category || ''}</small>
          </label>
          
          <!-- ISSUE 3 FIX: Retainer Options -->
          <div style="display:flex;gap:12px;align-items:center;padding:4px 8px 8px 32px;background:rgba(0,0,0,0.1);border-top:1px solid rgba(255,255,255,0.05);">
            <label style="display:flex;align-items:center;gap:4px;font-size:0.85em;cursor:pointer;">
              <input type="checkbox" 
                     class="retainer-toggle" 
                     data-code="${code}" 
                     ${isRetainer ? 'checked' : ''}
                     onchange="toggleRetainerType('${code}', this.checked)"
                     style="cursor:pointer;">
              <span style="color:${isRetainer ? '#10b981' : 'var(--muted)'};">Retainer</span>
            </label>
            
            <div class="retainer-months-wrap" data-code="${code}" style="display:${isRetainer ? 'flex' : 'none'};align-items:center;gap:4px;">
              <span style="font-size:0.85em;color:var(--muted);">Months:</span>
              <input type="number" 
                     class="retainer-months" 
                     data-code="${code}"
                     value="${retainerMonths}"
                     min="1" 
                     max="24"
                     onchange="updateRetainerMonths('${code}', this.value)"
                     style="width:50px;padding:2px 4px;border:1px solid rgba(255,255,255,0.2);border-radius:3px;background:rgba(0,0,0,0.2);">
            </div>
            
            <button onclick="event.stopPropagation(); suggestRetainerConfig('${code}')" 
                    style="margin-left:auto;background:#3b82f6;color:white;border:none;padding:3px 8px;border-radius:3px;cursor:pointer;font-size:0.8em;">
              AI Suggest
            </button>
          </div>
        </div>
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
  // GPT-5.1 Pro: Check if SmartSelectionState is populated (Smart Selection was applied)
  // If so, use SmartSelectionState for accurate counts; otherwise fall back to APB.step2
  const useSmartState = SmartSelectionState.selectedDeliverableCodes.length > 0;
  
  let delivCount, compCount, l3Count;
  
  if (useSmartState) {
    // Use SmartSelectionState for accurate counts
    delivCount = SmartSelectionState.selectedDeliverableCodes.length;
    
    // Count components from SmartSelectionState
    compCount = 0;
    Object.values(SmartSelectionState.selectedComponentsMap).forEach(compArray => {
      compCount += Array.isArray(compArray) ? compArray.length : 0;
    });
    
    // Count L3 from SmartSelectionState (curated tasks)
    l3Count = getSmartSelectionL3Count();
    
    console.log(`[UpdateSummaryCounts] Using SmartSelectionState: ${delivCount} delivs, ${compCount} comps, ${l3Count} tasks`);
  } else {
    // Fall back to APB.step2 for manual selections
    delivCount = APB.step2.selectedCodes.size;
    
    // Count components
    compCount = 0;
    Object.entries(APB.step2.selectedComponentsByCode).forEach(([code, compSet]) => {
      if (APB.step2.selectedCodes.has(code)) {
        compCount += compSet.size;
      }
    });
    
    // Count L3 - only for selected components (fixes Task 4)
    l3Count = 0;
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
  }
  
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
window.onComponentClicked = async function onComponentClicked(componentName) {
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
  const delivEl = document.getElementById('s2-summary-deliverables');
  if (delivEl) delivEl.textContent = delivCount;
  
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
  const compEl = document.getElementById('s2-summary-components');
  if (compEl) compEl.textContent = compCount;
  
  // Count L3 subtasks
  let l3Count = 0;
  Object.values(step2State.selectedL3Map).forEach(compMap => {
    Object.values(compMap).forEach(l3Set => {
      if (l3Set instanceof Set) l3Count += l3Set.size;
      else if (Array.isArray(l3Set)) l3Count += l3Set.length;
    });
  });
  const l3El = document.getElementById('s2-summary-l3');
  if (l3El) l3El.textContent = l3Count;
  
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
      
      // Update L2 tasks panel - use onComponentClicked to fetch and display L3 tasks
      if (window.onComponentClicked) {
        await onComponentClicked(compName);
      } else if (window.renderL3Panel) {
        await renderL3Panel();
      }
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
        // Update L2 tasks - use onComponentClicked to fetch and display L3 tasks
        if (window.onComponentClicked) {
          onComponentClicked(compName);
        } else if (window.renderL3Panel) {
          renderL3Panel(); // Fallback to old method
        }
      } else {
        S2.selectedComponentsByCode[delivCode].delete(compName);
      }
      
      if (window.updateStep2Summary) updateStep2Summary();
    });
  });
  
  if (window.updateStep2Summary) updateStep2Summary();
}


// ISSUE FIX 5: Add hydrateL3For function to fetch L3 tasks for a specific component
async function hydrateL3For(delivCode, compName) {
  const key = `${delivCode}::${compName}`;
  
  // Skip if already hydrated
  if (selectionStore.l3ByComponent.has(key)) {
    return;
  }
  
  try {
    // Fetch L3 tasks for this specific component
    const res = await fetch(`/api/l3_for?deliverable_code=${encodeURIComponent(delivCode)}&component_name=${encodeURIComponent(compName)}`);
    
    if (!res.ok) {
      console.warn(`Failed to fetch L3 for ${key}`);
      return;
    }
    
    const data = await res.json();
    const l3Items = data.items || [];
    
    // Store L3 tasks in selectionStore - ensure strings only
    if (l3Items.length > 0) {
      const l3Set = new Set(l3Items.map(item => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object') {
          const name = item.name || item.Task_Label || item.task_label || item.title || item.label || '';
          if (name && typeof name === 'string') return name;
        }
        return null;
      }).filter(name => name && name !== '[object Object]'));
      selectionStore.l3ByComponent.set(key, l3Set);
      
      // Also update S2 selectedL3ByKey for compatibility
      if (S2.selectedL3ByKey) {
        S2.selectedL3ByKey[key] = l3Set;
      }
    }
  } catch (err) {
    console.error(`Error hydrating L3 for ${key}:`, err);
  }
}

// Export the function globally
window.hydrateL3For = hydrateL3For;

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
    l3Set.forEach(l3Item => {
      // FIX: Extract task name if it's an object
      let l3Name = l3Item;
      if (typeof l3Item === 'object' && l3Item) {
        l3Name = l3Item.Task_Label || l3Item.task_label || l3Item.name || l3Item.title || l3Item.label || '';
      }
      // Only add valid string names
      if (l3Name && typeof l3Name === 'string' && l3Name !== '[object Object]') {
        allL3.push({
          delivCode: activeDeliv,
          delivLabel: labelFor(activeDeliv),
          compName: activeComp,
          l3Name,
          key
        });
      }
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
      
      // ISSUE FIX 5: Ensure L3 tasks are fetched and displayed after Smart Apply
      // Hydrate L3 tasks for all selected components
      const hydratePromises = [];
      for (const [delivCode, compSet] of Object.entries(S2.selectedComponentsByCode)) {
        if (compSet instanceof Set && compSet.size > 0) {
          for (const compName of compSet) {
            if (window.hydrateL3For) {
              hydratePromises.push(hydrateL3For(delivCode, compName));
            }
          }
        }
      }
      
      // Wait for all L3 hydrations to complete
      if (hydratePromises.length > 0) {
        await Promise.all(hydratePromises);
      }
      
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
        blended_rate: 210,
        rate_band: 'Standard_US',
        scenario_a: {mode:'template', complexity:'Advanced', tier:'T2_MediumVolume'},
        scenario_b: {mode:'template', complexity:'Advanced', tier:'T2_MediumVolume'},
        use_slack: true,
        slack_after_internal: 1,
        slack_after_client: 2,
        slack_global_pct: 0.05,
        project_start: null,
        project_name: document.getElementById('projectName')?.value || null
      };
    }
    
    const payload = { 
      ...window.__lastBuildPayload, 
      selected_deliverable_codes: selectedCodes,
      project_name: document.getElementById('projectName')?.value || window.__lastBuildPayload.project_name || null,
      session_id: window.SessionManager ? window.SessionManager.getCurrentSessionId() : null
    };
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
  // Clear button handler removed - using centralized handler in initStep2UI()

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
  
  // Get session_id from ScenarioManager (preferred) or SessionManager
  const sessionId = window.ScenarioManager?.state?.sessionId || 
                    window.SessionManager?.currentSessionId ||
                    localStorage.getItem('apb.currentSession');
  console.log('[EXPORT] onExport using session_id:', sessionId);
  
  const res = await fetch("/api/export", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({
      session_id: sessionId,  // NEW: Prefer SCENARIO_STORE working scenario
      scenario: SCENARIOS[which]
    })
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
  
  // Wire Clear button - clears ALL 3 panels at once
  const btnClear = APB.step2.els.btnClear;
  if (btnClear) {
    btnClear.onclick = () => {
      console.log('[CLEAR ALL] Clearing all 3 panels...');
      
      // Clear all selections from selectionStore
      selectionStore.deliverables.clear();
      selectionStore.componentsByDeliv.clear();
      selectionStore.l3ByComponent.clear();
      
      // Clear deprecated properties for compatibility
      APB.step2.selectedComponentsByCode = {};
      APB.step2.selectedL3ByKey = {};
      
      // Clear active state
      APB.step2.activeDeliverableCode = null;
      APB.step2.activeComponentName = null;
      
      // Sync with global state
      window.selectedCodes = [];
      if (window.appState) window.appState.selectedCodes = [];
      if (window.step2PickerState) window.step2PickerState.selected.clear();
      
      // PANEL 1: Clear Deliverables panel checkboxes
      const delivCheckboxes = document.querySelectorAll('#s2-deliv-list input[type="checkbox"]');
      delivCheckboxes.forEach(cb => cb.checked = false);
      
      // PANEL 2: Clear Components panel checkboxes
      const compCheckboxes = document.querySelectorAll('#s2-comp-list input[type="checkbox"]');
      compCheckboxes.forEach(cb => cb.checked = false);
      
      // PANEL 3: Clear L3 panel checkboxes
      const l3Checkboxes = document.querySelectorAll('#s2-l3-list input[type="checkbox"]');
      l3Checkboxes.forEach(cb => cb.checked = false);
      
      // Re-render all panels to show empty states
      renderDeliverablesPanel();
      
      // Clear components panel with empty state
      if (window.renderComponentsPanel) {
        renderComponentsPanel();
      } else {
        renderComponentsEmptyState();
      }
      
      // Clear L3 panel with empty state
      if (window.renderL3Panel) {
        renderL3Panel();
      } else {
        const l3ListEl = document.getElementById('s2-l3-list');
        if (l3ListEl) {
          l3ListEl.innerHTML = '<p style="color: var(--muted); text-align: center; padding-top: 40px; font-size: 0.9em;">Select a component to view its L2 tasks</p>';
        }
      }
      
      // Update summary counts to 0
      updateSummaryCounts();
      
      console.log('[CLEAR ALL] All 3 panels cleared successfully');
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
  
  // Render grouped deliverables with collapsible sections (FEATURE: collapsed by default)
  const html = sortedDepts.map(dept => {
    const deptItems = grouped[dept].sort((a, b) => {
      const sortA = a.Sort_Order ?? 999;
      const sortB = b.Sort_Order ?? 999;
      if (sortA !== sortB) return sortA - sortB;
      return (a.Deliverable || '').localeCompare(b.Deliverable || '');
    });
    
    const deptId = `dept-${dept.replace(/\s+/g, '-')}`;
    const deptHeader = `<div class="dept-header" data-dept="${deptId}" style="font-weight:600; padding:8px 8px 4px; color:#ffffff; border-top:1px solid rgba(255,255,255,0.1); margin-top:4px; background:rgba(139,92,246,0.15); cursor:pointer; display:flex; justify-content:space-between; align-items:center;">
      <span>${dept} (${deptItems.length})</span>
      <span class="collapse-icon">▶</span>
    </div>`;
    const deptRows = `<div id="${deptId}" style="display:none;">${deptItems.map(d => `
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
    `).join('')}</div>`;
    return deptHeader + deptRows;
  }).join('');
  
  host.innerHTML = html || '<div style="opacity:.7;padding:8px">No deliverables</div>';

  // FEATURE: Add collapse/expand functionality for department headers
  host.querySelectorAll('.dept-header').forEach(header => {
    header.addEventListener('click', () => {
      const deptId = header.getAttribute('data-dept');
      const deptContent = document.getElementById(deptId);
      const icon = header.querySelector('.collapse-icon');
      
      if (deptContent && icon) {
        const isCollapsed = deptContent.style.display === 'none';
        deptContent.style.display = isCollapsed ? 'block' : 'none';
        icon.textContent = isCollapsed ? '▼' : '▶';
      }
    });
  });

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
// Clear button handler removed - using centralized handler in initStep2UI()

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
  const blendedRate  = Number(document.querySelector('#blendedRate')?.value || 210);
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
    project_start: projectStart,
    project_name: document.getElementById('projectName')?.value || null,
    session_id: window.SessionManager ? window.SessionManager.getCurrentSessionId() : null
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
  // WORKFRONT COMPATIBILITY: Anchors disabled (alphanumeric WBS breaks Workfront import)
  const addAnchors = false;
  
  // Get fresh session_id directly from SessionManager (no caching)
  // This ensures we use the canonical ID that matches backend SCENARIO_STORE keys
  const sessionId = window.SessionManager ? window.SessionManager.getCurrentSessionId() : null;
  
  // Build endpoint with query parameters
  // If session_id exists, backend will use SCENARIO_STORE (with Gantt changes)
  // Otherwise, backend falls back to _CURRENT_SCENARIOS (pricing-only data)
  let endpoint = `/api/export/xml/${letter.toLowerCase()}?add_anchors=${addAnchors}`;
  if (sessionId) {
    endpoint += `&session_id=${encodeURIComponent(sessionId)}`;
    console.log('[Export] Including session_id for Gantt-synced export:', sessionId);
  }
  
  try {
    const response = await fetch(endpoint, {
      method: 'GET'
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Export failed: ${response.statusText}`);
    }
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    // Let browser use backend's Content-Disposition filename - don't override
    a.click();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert(`XML export failed: ${err.message}`);
  }
}

// Wire up XML export button (Scenario A only)
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-export-xml-a')?.addEventListener('click', () => exportXMLScenario('A'));
  
  // Auto-clear when RFP textarea content is typed
  const rfpTextarea = document.getElementById('rfpText');
  if (rfpTextarea) {
    let hasCleared = false; // Track if we've already cleared for this typing session
    
    rfpTextarea.addEventListener('input', async (e) => {
      // Only clear once when user starts typing, not on every keystroke
      if (!hasCleared && e.target.value.length > 0) {
        hasCleared = true;
        console.log('[AUTO-CLEAR] New RFP text entered, clearing old session data...');
        
        // Clear all localStorage and sessionStorage
        for (const key of Object.keys(localStorage)) {
          if (key.startsWith('apb.') || key.startsWith('apb:') || key === 'rfp_text') {
            localStorage.removeItem(key);
          }
        }
        for (const key of Object.keys(sessionStorage)) {
          if (key.startsWith('apb.') || key.startsWith('apb:') || key === 'rfp_text') {
            sessionStorage.removeItem(key);
          }
        }
        
        // Clear in-memory state
        if (window.APP) {
          window.APP.summary = null;
          window.APP.rfpText = null;
        }
        if (window.APB && window.APB.step2) {
          window.APB.step2.rfpText = null;
        }
        
        // Start fresh session
        const newSessionId = SessionManager.startNewSession();
        
        // Clear server-side cache
        try {
          await fetch('/api/clear_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: newSessionId })
          });
        } catch (err) {
          console.warn('[AUTO-CLEAR] Failed to clear server cache:', err);
        }
      }
      
      // Reset the flag when textarea is cleared
      if (e.target.value.length === 0) {
        hasCleared = false;
      }
    });
  }
  
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
  
  // Display selected file names when files are chosen AND auto-clear old data
  const fileInput = document.getElementById('rfpFile');
  const filesList = document.getElementById('selected-files-list');
  if (fileInput && filesList) {
    fileInput.addEventListener('change', async (e) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        const names = Array.from(files).map(f => f.name).join(', ');
        filesList.textContent = `Selected: ${names}`;
        filesList.style.color = 'var(--accent)';
        
        // AUTO-CLEAR: Automatically clear old data when new file is selected
        console.log('[AUTO-CLEAR] New file selected, clearing old session data...');
        
        // Clear all localStorage and sessionStorage
        for (const key of Object.keys(localStorage)) {
          if (key.startsWith('apb.') || key.startsWith('apb:') || key === 'rfp_text') {
            localStorage.removeItem(key);
          }
        }
        for (const key of Object.keys(sessionStorage)) {
          if (key.startsWith('apb.') || key.startsWith('apb:') || key === 'rfp_text') {
            sessionStorage.removeItem(key);
          }
        }
        
        // Clear in-memory state
        if (window.APP) {
          window.APP.summary = null;
          window.APP.rfpText = null;
        }
        if (window.APB && window.APB.step2) {
          window.APB.step2.rfpText = null;
        }
        
        // Start fresh session
        const newSessionId = SessionManager.startNewSession();
        
        // Clear server-side cache
        try {
          await fetch('/api/clear_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: newSessionId })
          });
        } catch (err) {
          console.warn('[AUTO-CLEAR] Failed to clear server cache:', err);
        }
        
        console.log('[AUTO-CLEAR] Session cleared, ready for new RFP analysis');
      } else {
        filesList.textContent = '';
      }
    });
  }
});

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
        alert('Please build Scenario A first before creating a second version.');
        return;
      }
      
      try {
        buildSecondBtn.textContent = 'Creating Version 2...';
        buildSecondBtn.disabled = true;
        
        const response = await fetch('/api/scenario/duplicate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scenario_id: 'scenario_a',
            scenario_data: window.SCENARIOS.A,
            version_name: 'Version 2 - Alternative'
          })
        });
        
        const result = await response.json();
        
        if (result.success) {
          alert(`✅ Version 2 created successfully!\n\nVersion ID: ${result.version_id}\nYou can now modify this version independently.`);
          
          // Store the new version
          window.SCENARIOS[`A_${result.version_id}`] = window.SCENARIOS.A;
          
          // Update version list display
          if (versionList && versionItems) {
            versionList.style.display = 'block';
            versionItems.innerHTML += `
              <div style="padding: 8px; margin: 4px 0; background: rgba(255,255,255,0.05); border-radius: 4px;">
                <strong>${result.version_name}</strong> - Created ${new Date(result.created_date).toLocaleDateString()}
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
          body: JSON.stringify(payload)
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
                Shipped on ${new Date(result.shipped_date).toLocaleString()}
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

window.addEventListener("load", boot);

// Admin Authentication System for Learning Brain
const AdminAuth = {
  getToken() {
    return localStorage.getItem('apb.adminToken');
  },
  
  setToken(token) {
    localStorage.setItem('apb.adminToken', token);
    this.updateAdminIndicator();
  },
  
  clearToken() {
    localStorage.removeItem('apb.adminToken');
    this.updateAdminIndicator();
  },
  
  isAuthenticated() {
    return !!this.getToken();
  },
  
  async promptForToken(message = "Enter admin token to access learning features:") {
    const token = prompt(message);
    if (!token) return false;
    
    // Test the token with a simple status call
    try {
      const res = await fetch('/api/brain/status', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        this.setToken(token);
        alert("✅ Admin authentication successful!");
        return true;
      } else if (res.status === 401 || res.status === 403) {
        alert("❌ Invalid admin token. Please try again.");
        return false;
      }
    } catch (e) {
      alert("❌ Authentication failed: " + e.message);
      return false;
    }
  },
  
  updateAdminIndicator() {
    // Remove existing indicator if any
    const existingIndicator = document.getElementById('adminModeIndicator');
    if (existingIndicator) {
      existingIndicator.remove();
    }
    
    // Add indicator if authenticated
    if (this.isAuthenticated()) {
      const indicator = document.createElement('div');
      indicator.id = 'adminModeIndicator';
      indicator.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: bold;
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        cursor: pointer;
        transition: transform 0.2s;
      `;
      indicator.innerHTML = `
        <span>🔐 Admin Mode</span>
        <span style="font-size: 10px; opacity: 0.9;">(click to logout)</span>
      `;
      indicator.onmouseover = () => indicator.style.transform = 'scale(1.05)';
      indicator.onmouseout = () => indicator.style.transform = 'scale(1)';
      indicator.onclick = () => {
        if (confirm("Logout from admin mode?")) {
          this.clearToken();
          alert("Logged out from admin mode");
        }
      };
      document.body.appendChild(indicator);
    }
  },
  
  async makeAuthenticatedRequest(url, options = {}) {
    const token = this.getToken();
    if (!token) {
      throw new Error("Not authenticated");
    }
    
    options.headers = options.headers || {};
    options.headers['Authorization'] = `Bearer ${token}`;
    
    const response = await fetch(url, options);
    
    // If unauthorized, clear token and prompt again
    if (response.status === 401 || response.status === 403) {
      this.clearToken();
      throw new Error("Authentication expired or invalid");
    }
    
    return response;
  }
};

// Initialize admin indicator on page load
document.addEventListener('DOMContentLoaded', () => {
  AdminAuth.updateAdminIndicator();
});

// LEARN button functionality (Learning Brain integration with authentication)
(function attachLearn(){
  const btn = document.getElementById('learnBtn');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    // Check authentication first
    if (!AdminAuth.isAuthenticated()) {
      const authenticated = await AdminAuth.promptForToken(
        "🔐 Admin authentication required\n\n" +
        "Enter the admin token to access learning features.\n" +
        "(Check server logs for the default token if not configured)"
      );
      if (!authenticated) {
        return;
      }
    }
    
    const rfpText = (window.APB?.step2?.rfpText) || "";
    const selected = Array.from(window.APB?.step2?.selectedCodes || []);
    const components = (window.APB?.selectionStore?.componentsByDeliv)
      ? Object.fromEntries(window.APB.selectionStore.componentsByDeliv) : {};
    
    try {
      const res = await AdminAuth.makeAuthenticatedRequest("/api/brain/learn", {
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
      
      if (res.ok) {
        const data = await res.json();
        alert("✅ Learning successful!\n\n" + (data?.message || "Data recorded for future improvements"));
      } else {
        const error = await res.json();
        alert("❌ Learning failed: " + (error?.detail || res.statusText));
      }
    } catch (e) {
      if (e.message.includes("Authentication")) {
        alert("❌ " + e.message + "\n\nPlease click the Learn button again to re-authenticate.");
      } else {
        alert("❌ Learn call failed: " + e.message);
      }
    }
  });

  // Safety net: Kill any overlay/backdrop elements that might block clicks
  const killOverlays = () => {
    document.querySelectorAll('#drawer-backdrop,.backdrop,.drawer.open').forEach(n=>{
      if (n.id === 'drawer-backdrop') n.setAttribute('hidden','');
      if (n.classList.contains('open')) n.classList.remove('open');
    });
  };
  // Run once on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', killOverlays);
  } else {
    killOverlays();
  }
})();