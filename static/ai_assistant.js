/**
 * CHARLES AGENT - ProBuFo (Progressive Business Forecasting Oracle)
 * Advanced AI Assistant with Autonomous Self-Healing Capabilities
 * Version: 3.0.0 - Full Autonomy & State Preservation
 */

class AIAssistant {
    constructor() {
        this.isOpen = false;
        this.isMinimized = false;
        this.sessionId = this.generateSessionId();
        this.isProcessing = false;
        this.currentActions = [];
        this.actionQueue = [];
        this.executionDelay = 500; // ms between actions
        this.stagedFiles = []; // Multi-file staging area
        this.currentTypingIndicators = new Set(); // Track all active typing indicators
        this.apiTimeout = 10000; // 10 seconds timeout for API calls
        
        // Enhanced State Management
        this.agentState = {
            uploadedFiles: [],
            selectedDeliverables: [],
            currentStep: 'step1',
            formValues: {},
            analysisMode: 'fast',
            jobId: null,
            lastError: null,
            stateHistory: []
        };
        
        // Self-Healing & Error Recovery
        this.errorRecoveryQueue = [];
        this.retryAttempts = {};
        this.maxRetries = 3;
        this.errorPatterns = [];
        
        // Visual Feedback
        this.activeHighlights = new Set();
        this.progressIndicators = new Map();
        
        // Batch Processing
        this.batchProcessingStatus = {
            total: 0,
            completed: 0,
            failed: 0,
            inProgress: false,
            fileStatuses: new Map()
        };
        
        // Stuck State Detection & Operation Tracking
        this.operationTracker = {
            currentOperations: new Map(), // Map of operation ID to operation info
            operationTimeouts: {
                file_upload: 60000,    // 60 seconds for file uploads
                analysis: 30000,       // 30 seconds for analysis
                ui_action: 15000,      // 15 seconds for UI actions
                network: 10000,        // 10 seconds for network requests
                default: 30000         // 30 seconds default
            },
            stuckOperations: new Set()
        };
        
        // Auto-Fix State
        this.autoFixEnabled = false;
        this.healthCheckInterval = null;
        this.healthCheckFrequency = 5000; // Check every 5 seconds
        this.lastHealthCheck = Date.now();
        
        this.init();
    }
    
    generateSessionId() {
        return 'agent_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    init() {
        this.createSidebar();
        this.addEnhancedStyles();
        this.attachEventListeners();
        this.initializeAutoRecovery();
        this.restoreState();
        this.checkAgentStatus();
        this.initProgressIndicators();
    }
    
    // ====================
    // STATE PRESERVATION SYSTEM
    // ====================
    
    saveState() {
        const currentState = {
            timestamp: Date.now(),
            uploadedFiles: this.agentState.uploadedFiles,
            selectedDeliverables: this.getSelectedDeliverables(),
            currentStep: this.detectCurrentStep(),
            formValues: this.captureFormValues(),
            analysisMode: document.getElementById('analysis-mode')?.value || 'fast',
            jobId: this.agentState.jobId,
            rfpText: document.getElementById('rfpText')?.value || '',
            scenarios: window.SCENARIOS || null
        };
        
        // Add to history
        this.agentState.stateHistory.push(currentState);
        
        // Keep only last 10 states
        if (this.agentState.stateHistory.length > 10) {
            this.agentState.stateHistory.shift();
        }
        
        // Save to localStorage
        localStorage.setItem('charles_agent_state', JSON.stringify(this.agentState));
        
        console.log('[CHARLES] State saved:', currentState);
        return currentState;
    }
    
    restoreState(stateToRestore = null) {
        try {
            // Use provided state or load from localStorage
            const savedState = stateToRestore || JSON.parse(localStorage.getItem('charles_agent_state') || '{}');
            
            if (!savedState || Object.keys(savedState).length === 0) {
                console.log('[CHARLES] No state to restore');
                return false;
            }
            
            // Get the most recent state
            const latestState = savedState.stateHistory?.[savedState.stateHistory.length - 1] || savedState;
            
            // Restore uploaded files
            if (latestState.uploadedFiles) {
                this.agentState.uploadedFiles = latestState.uploadedFiles;
            }
            
            // Restore RFP text
            if (latestState.rfpText) {
                const rfpTextEl = document.getElementById('rfpText');
                if (rfpTextEl) {
                    rfpTextEl.value = latestState.rfpText;
                }
            }
            
            // Restore form values
            if (latestState.formValues) {
                this.restoreFormValues(latestState.formValues);
            }
            
            // Restore analysis mode
            if (latestState.analysisMode) {
                const modeEl = document.getElementById('analysis-mode');
                if (modeEl) {
                    modeEl.value = latestState.analysisMode;
                }
                // Update UI buttons
                this.setAnalysisMode(latestState.analysisMode);
            }
            
            // Restore selected deliverables
            if (latestState.selectedDeliverables && latestState.selectedDeliverables.length > 0) {
                this.restoreSelectedDeliverables(latestState.selectedDeliverables);
            }
            
            // Navigate to the correct step
            if (latestState.currentStep && latestState.currentStep !== 'step1') {
                this.navigateToStep(latestState.currentStep);
            }
            
            // Restore job ID if analysis was in progress
            if (latestState.jobId) {
                this.agentState.jobId = latestState.jobId;
                // Resume tracking
                this.trackAnalysisJob(latestState.jobId, true);
            }
            
            this.addMessage('✅ Previous state restored successfully', 'assistant');
            
            return true;
        } catch (error) {
            console.error('[CHARLES] Failed to restore state:', error);
            return false;
        }
    }
    
    captureFormValues() {
        const formValues = {};
        
        // Capture all input values
        document.querySelectorAll('input[type="text"], input[type="number"], textarea, select').forEach(el => {
            if (el.id) {
                formValues[el.id] = el.value;
            }
        });
        
        // Capture checkbox states
        document.querySelectorAll('input[type="checkbox"]').forEach(el => {
            if (el.id || el.name) {
                const key = el.id || el.name;
                formValues[key] = el.checked;
            }
        });
        
        return formValues;
    }
    
    restoreFormValues(formValues) {
        Object.entries(formValues).forEach(([key, value]) => {
            const el = document.getElementById(key) || document.querySelector(`[name="${key}"]`);
            if (el) {
                if (el.type === 'checkbox') {
                    el.checked = value;
                } else {
                    el.value = value;
                }
                // Trigger change events
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    }
    
    restoreSelectedDeliverables(deliverables) {
        // Clear current selections
        document.querySelectorAll('input[type="checkbox"][data-deliverable]').forEach(cb => {
            cb.checked = false;
        });
        
        // Restore selections
        deliverables.forEach(code => {
            const checkbox = document.querySelector(`input[type="checkbox"][data-deliverable="${code}"]`);
            if (checkbox) {
                checkbox.checked = true;
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    }
    
    // ====================
    // REAL-TIME PROGRESS DISPLAY
    // ====================
    
    initProgressIndicators() {
        // Add floating progress indicator to main UI
        const floatingProgress = document.createElement('div');
        floatingProgress.id = 'charles-floating-progress';
        floatingProgress.className = 'charles-floating-progress';
        floatingProgress.style.display = 'none';
        floatingProgress.innerHTML = `
            <div class="charles-progress-header">
                <span class="charles-progress-title">🔮 CHARLES Processing</span>
                <span class="charles-progress-close" onclick="this.parentElement.parentElement.style.display='none'">×</span>
            </div>
            <div class="charles-progress-content">
                <div class="charles-progress-bar-container">
                    <div class="charles-progress-bar" id="charles-main-progress-bar"></div>
                </div>
                <div class="charles-progress-text" id="charles-progress-text">Initializing...</div>
                <div class="charles-progress-details" id="charles-progress-details"></div>
            </div>
        `;
        document.body.appendChild(floatingProgress);
        
        // Add progress to Step 1
        const step1 = document.getElementById('step1');
        if (step1) {
            const step1Progress = document.createElement('div');
            step1Progress.id = 'step1-progress';
            step1Progress.className = 'charles-step-progress';
            step1Progress.style.display = 'none';
            step1Progress.innerHTML = `
                <div class="progress-bar-container">
                    <div class="progress-bar" id="step1-progress-bar"></div>
                </div>
                <div class="progress-text" id="step1-progress-text"></div>
            `;
            step1.insertBefore(step1Progress, step1.querySelector('.card-content') || step1.firstChild);
        }
    }
    
    updateProgress(percentage, message, details = null) {
        // Update floating progress
        const floatingProgress = document.getElementById('charles-floating-progress');
        const mainBar = document.getElementById('charles-main-progress-bar');
        const progressText = document.getElementById('charles-progress-text');
        const progressDetails = document.getElementById('charles-progress-details');
        
        if (floatingProgress && percentage >= 0) {
            floatingProgress.style.display = 'block';
            if (mainBar) mainBar.style.width = `${percentage}%`;
            if (progressText) progressText.textContent = message || `Processing... ${percentage}%`;
            if (progressDetails && details) {
                progressDetails.innerHTML = details;
            }
        }
        
        // Update Step 1 progress
        const step1Progress = document.getElementById('step1-progress');
        const step1Bar = document.getElementById('step1-progress-bar');
        const step1Text = document.getElementById('step1-progress-text');
        
        if (step1Progress && percentage >= 0) {
            step1Progress.style.display = 'block';
            if (step1Bar) step1Bar.style.width = `${percentage}%`;
            if (step1Text) step1Text.textContent = message || `${percentage}%`;
        }
        
        // Update chat progress
        this.addProgressMessage(percentage, message, details);
        
        // Hide on completion
        if (percentage >= 100) {
            setTimeout(() => {
                if (floatingProgress) floatingProgress.style.display = 'none';
                if (step1Progress) step1Progress.style.display = 'none';
            }, 2000);
        }
    }
    
    addProgressMessage(percentage, message, details) {
        const messagesContainer = document.getElementById('ai-chat-messages');
        let progressMsg = document.getElementById('charles-progress-message');
        
        if (!progressMsg) {
            progressMsg = document.createElement('div');
            progressMsg.id = 'charles-progress-message';
            progressMsg.className = 'ai-message assistant';
            messagesContainer.appendChild(progressMsg);
        }
        
        progressMsg.innerHTML = `
            <div class="ai-message-avatar">🤖</div>
            <div class="ai-message-content">
                <div class="progress-indicator">
                    <div class="progress-bar-mini">
                        <div class="progress-fill" style="width: ${percentage}%"></div>
                    </div>
                    <div class="progress-status">
                        <strong>${message}</strong>
                        ${details ? `<div class="progress-details">${details}</div>` : ''}
                        <div class="progress-percentage">${percentage}%</div>
                    </div>
                </div>
            </div>
        `;
        
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    createTaskMonitor() {
        const monitor = {
            container: null,
            tasks: [],
            
            init() {
                // Create or find container
                let container = document.getElementById('charles-task-monitor');
                if (!container) {
                    container = document.createElement('div');
                    container.id = 'charles-task-monitor';
                    container.className = 'charles-task-monitor';
                    container.innerHTML = `
                        <div class="task-monitor-header">
                            <span>📋 Current Tasks</span>
                            <span class="task-monitor-close" onclick="this.parentElement.parentElement.style.display='none'">×</span>
                        </div>
                        <div class="task-monitor-list"></div>
                    `;
                    
                    // Add styles if not already present
                    if (!document.getElementById('task-monitor-styles')) {
                        const styles = document.createElement('style');
                        styles.id = 'task-monitor-styles';
                        styles.textContent = `
                            .charles-task-monitor {
                                position: fixed;
                                top: 20px;
                                right: 460px;
                                width: 300px;
                                background: rgba(30, 30, 40, 0.98);
                                border: 1px solid rgba(100, 100, 255, 0.3);
                                border-radius: 12px;
                                padding: 15px;
                                z-index: 9998;
                                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
                                backdrop-filter: blur(10px);
                            }
                            
                            .task-monitor-header {
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                margin-bottom: 15px;
                                color: #fff;
                                font-weight: 600;
                            }
                            
                            .task-monitor-close {
                                cursor: pointer;
                                opacity: 0.6;
                                transition: opacity 0.2s;
                            }
                            
                            .task-monitor-close:hover {
                                opacity: 1;
                            }
                            
                            .task-monitor-list {
                                display: flex;
                                flex-direction: column;
                                gap: 8px;
                            }
                            
                            .task-monitor-item {
                                display: flex;
                                align-items: center;
                                gap: 10px;
                                padding: 8px;
                                background: rgba(255, 255, 255, 0.05);
                                border-radius: 8px;
                                color: #fff;
                                font-size: 13px;
                            }
                            
                            .task-monitor-item.in-progress {
                                background: rgba(100, 100, 255, 0.1);
                                border: 1px solid rgba(100, 100, 255, 0.3);
                            }
                            
                            .task-monitor-item.completed {
                                opacity: 0.7;
                            }
                            
                            .task-monitor-item.failed {
                                background: rgba(255, 50, 50, 0.1);
                                border: 1px solid rgba(255, 50, 50, 0.3);
                            }
                            
                            .task-status {
                                width: 20px;
                                height: 20px;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                            }
                            
                            .task-status.pending::before {
                                content: '⏳';
                            }
                            
                            .task-status.in-progress::before {
                                content: '🔄';
                                animation: spin 2s linear infinite;
                            }
                            
                            .task-status.completed::before {
                                content: '✅';
                            }
                            
                            .task-status.failed::before {
                                content: '❌';
                            }
                            
                            @keyframes spin {
                                from { transform: rotate(0deg); }
                                to { transform: rotate(360deg); }
                            }
                            
                            .task-name {
                                flex: 1;
                            }
                            
                            .task-progress {
                                font-size: 11px;
                                color: rgba(255, 255, 255, 0.6);
                            }
                        `;
                        document.head.appendChild(styles);
                    }
                    
                    document.body.appendChild(container);
                }
                
                this.container = container;
                container.style.display = 'block';
                return this;
            },
            
            addTask(name, status = 'pending', progress = null) {
                this.tasks.push({ name, status, progress });
                this.render();
                return this;
            },
            
            updateTask(index, status, progress = null) {
                if (this.tasks[index]) {
                    this.tasks[index].status = status;
                    if (progress !== null) {
                        this.tasks[index].progress = progress;
                    }
                    this.render();
                }
                return this;
            },
            
            updateAllPending(status) {
                this.tasks.forEach(task => {
                    if (task.status === 'pending') {
                        task.status = status;
                    }
                });
                this.render();
                return this;
            },
            
            render() {
                if (!this.container) return;
                
                const list = this.container.querySelector('.task-monitor-list');
                list.innerHTML = this.tasks.map((task, index) => `
                    <div class="task-monitor-item ${task.status}">
                        <div class="task-status ${task.status}"></div>
                        <div class="task-name">${index + 1}. ${task.name}</div>
                        ${task.progress ? `<div class="task-progress">${task.progress}%</div>` : ''}
                    </div>
                `).join('');
            },
            
            close() {
                if (this.container) {
                    setTimeout(() => {
                        this.container.style.display = 'none';
                    }, 5000);
                }
            }
        };
        
        return monitor.init();
    }
    
    async trackAnalysisJob(jobId, taskMonitor = null, isResume = false) {
        if (!isResume) {
            this.agentState.jobId = jobId;
            this.saveState();
        }
        
        let pollInterval;
        let pollCount = 0;
        const maxPolls = 120; // 4 minutes at 2-second intervals
        
        this.updateProgress(0, 'Analysis started...', 'Initializing GPT-5 deep analysis');
        
        const cleanup = () => {
            if (pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
            }
            this.agentState.jobId = null;
        };
        
        pollInterval = setInterval(async () => {
            try {
                pollCount++;
                
                if (pollCount > maxPolls) {
                    cleanup();
                    this.updateProgress(100, 'Checking for results...', 'Attempting to load completed analysis');
                    
                    // Try to fetch results one more time in case they're ready
                    try {
                        const finalCheck = await fetch(`/api/agencydb/status/${jobId}`);
                        if (finalCheck.ok) {
                            const finalStatus = await finalCheck.json();
                            if (finalStatus.status === 'completed' && finalStatus.data) {
                                // Analysis actually completed! Load the results
                                this.addMessage(`✅ Analysis complete! Found ${finalStatus.data.deliverables?.length || 0} deliverables. Loading results...`, 'assistant');
                                
                                // Load deliverables into the app
                                await this.loadAnalysisResults(finalStatus.data);
                                
                                // Navigate to Step 2
                                await this.navigateToStep('step2');
                                
                                // Auto-select top deliverables
                                await this.selectTopDeliverables(20);
                                
                                // Calculate pricing
                                await this.calculateScenarioA();
                                
                                this.addMessage('📊 I\'ve loaded your deliverables and calculated initial pricing. What would you like to adjust?', 'assistant');
                                return;
                            }
                        }
                    } catch (e) {
                        console.log('[CHARLES] Final check failed:', e);
                    }
                    
                    this.addMessage('⏱️ Analysis timed out. Let me check for results...', 'assistant');
                    
                    // Try alternative approach to get results
                    await this.attemptResultRecovery(jobId);
                    return;
                }
                
                const response = await this.retryWithBackoff(
                    () => fetch(`/api/agencydb/status/${jobId}`),
                    3,
                    1000
                );
                
                if (response.ok) {
                    const status = await response.json();
                    
                    // Update progress with real data
                    const progress = status.progress || 0;
                    const stage = status.stage || 'Processing';
                    
                    // Create detailed message based on stage
                    let details = '';
                    if (status.stage_details) {
                        details = `<ul>${Object.entries(status.stage_details).map(([k, v]) => 
                            `<li>${k}: ${v}</li>`
                        ).join('')}</ul>`;
                    }
                    
                    this.updateProgress(progress, stage, details);
                    
                    // Update task monitor if provided
                    if (taskMonitor) {
                        if (progress >= 30 && taskMonitor.tasks[3].status === 'in_progress') {
                            taskMonitor.updateTask(3, 'in_progress', progress);
                        }
                        
                        if (progress === 100 && status.status === 'completed') {
                            taskMonitor.updateTask(3, 'completed');
                            taskMonitor.updateTask(4, 'completed');
                        }
                    }
                    
                    if (status.status === 'completed') {
                        cleanup();
                        this.updateProgress(100, '✅ Analysis Complete!', 'Loading deliverables into app...');
                        
                        if (taskMonitor) {
                            taskMonitor.updateTask(3, 'completed');
                            taskMonitor.updateTask(4, 'in_progress');
                        }
                        
                        const deliverableCount = status.data?.deliverables?.length || status.deliverables_count || 0;
                        this.addMessage(`✅ Analysis complete! Found ${deliverableCount} deliverables. Loading into app...`, 'assistant');
                        
                        // Load the analysis results into the app
                        if (status.data) {
                            await this.loadAnalysisResults(status.data);
                            
                            // Navigate to Step 2
                            await this.navigateToStep('step2');
                            
                            // Auto-select top deliverables
                            await this.selectTopDeliverables(20);
                            
                            // Calculate pricing
                            await this.calculateScenarioA();
                            
                            // Ask user for input
                            this.addMessage('📊 I\'ve loaded your deliverables and calculated initial pricing. What would you like to adjust?', 'assistant');
                            
                            if (taskMonitor) {
                                taskMonitor.updateTask(4, 'completed');
                                taskMonitor.close();
                            }
                        }
                        
                        this.saveState();
                    } else if (status.status === 'failed') {
                        cleanup();
                        this.updateProgress(100, '❌ Analysis Failed', status.error || 'Unknown error');
                        this.handleError(new Error(status.error || 'Analysis failed'), 'analysis', { jobId });
                    }
                }
            } catch (error) {
                console.error('[CHARLES] Job tracking error:', error);
                this.handleError(error, 'job_tracking', { jobId });
            }
        }, 2000);
    }
    
    // ====================
    // VISUAL FEEDBACK SYSTEM
    // ====================
    
    showAgentWorking(message = 'CHARLES is working...') {
        let overlay = document.getElementById('charles-working-overlay');
        
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'charles-working-overlay';
            overlay.className = 'charles-working-overlay';
            document.body.appendChild(overlay);
        }
        
        overlay.innerHTML = `
            <div class="charles-working-content">
                <div class="charles-sphere-animated">🔮</div>
                <div class="charles-working-text">${message}</div>
                <div class="charles-working-spinner"></div>
            </div>
        `;
        
        overlay.style.display = 'flex';
        
        return () => {
            overlay.style.display = 'none';
        };
    }
    
    flashElement(element, duration = 500, color = '#667eea') {
        if (!element || this.activeHighlights.has(element)) return;
        
        this.activeHighlights.add(element);
        
        const originalStyle = {
            border: element.style.border,
            boxShadow: element.style.boxShadow,
            transition: element.style.transition
        };
        
        // Add pulsing animation
        element.style.transition = 'all 0.3s ease';
        element.style.border = `2px solid ${color}`;
        element.style.boxShadow = `0 0 20px ${color}`;
        element.classList.add('charles-element-highlight');
        
        setTimeout(() => {
            element.style.border = originalStyle.border;
            element.style.boxShadow = originalStyle.boxShadow;
            element.style.transition = originalStyle.transition;
            element.classList.remove('charles-element-highlight');
            this.activeHighlights.delete(element);
        }, duration);
    }
    
    showClickAnimation(element) {
        if (!element) return;
        
        // Create ripple effect at element center
        const rect = element.getBoundingClientRect();
        const ripple = document.createElement('div');
        ripple.className = 'charles-click-ripple';
        ripple.style.cssText = `
            position: fixed;
            left: ${rect.left + rect.width/2}px;
            top: ${rect.top + rect.height/2}px;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(102, 126, 234, 0.8) 0%, transparent 70%);
            transform: translate(-50%, -50%) scale(0);
            animation: charles-ripple 0.6s ease-out;
            pointer-events: none;
            z-index: 999999;
        `;
        
        document.body.appendChild(ripple);
        
        // Add animation keyframes if not already present
        if (!document.querySelector('#charles-ripple-style')) {
            const style = document.createElement('style');
            style.id = 'charles-ripple-style';
            style.textContent = `
                @keyframes charles-ripple {
                    to {
                        transform: translate(-50%, -50%) scale(4);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        // Clean up after animation
        setTimeout(() => ripple.remove(), 600);
        
        // Also flash the element
        this.flashElement(element, 300);
    }
    
    async monitorMainAppProgress(taskMonitor) {
        const parentWindow = window.parent || window;
        const parentDoc = parentWindow.document;
        
        let checkCount = 0;
        const maxChecks = 300; // 2.5 minutes
        
        return new Promise((resolve) => {
            const progressChecker = setInterval(async () => {
                checkCount++;
                
                // Look for progress bar - check multiple possible selectors
                const progressBar = parentDoc.querySelector('#ai-progress-bar, .progress-bar, [id*="progress-bar"]');
                const progressContainer = parentDoc.querySelector('#ai-progress-container, .ai-progress-modal, .progress-container, [id*="progress"]');
                const step2 = parentDoc.querySelector('#step2');
                const deliverablesList = parentDoc.querySelectorAll('#s2-deliv-list .deliverable-item, [data-deliverable-code]');
                
                // Check if progress modal/bar is showing
                const progressModal = parentDoc.querySelector('#ai-progress-bar');
                const progressFill = parentDoc.querySelector('#ai-progress-fill');
                const progressPercent = parentDoc.querySelector('#ai-progress-percent');
                
                if (progressModal && progressModal.style.display !== 'none') {
                    if (taskMonitor && checkCount === 1) {
                        this.addMessage('📊 Progress bar detected - analysis running...', 'assistant');
                    }
                    
                    // Report progress percentage if available
                    if (progressPercent && checkCount % 20 === 0) {
                        const percent = progressPercent.textContent;
                        this.addMessage(`⏳ Analysis progress: ${percent}`, 'assistant');
                    }
                }
                
                // Check if analysis complete (Step 2 visible with deliverables)
                if (step2 && step2.style.display !== 'none' && deliverablesList.length > 0) {
                    clearInterval(progressChecker);
                    
                    if (taskMonitor) {
                        taskMonitor.updateTask(2, 'completed');
                        taskMonitor.updateTask(3, 'in_progress');
                    }
                    
                    this.addMessage(`✅ Analysis complete! Found ${deliverablesList.length} deliverables.`, 'assistant');
                    
                    // Auto-navigate through workflow
                    await this.delay(1000);
                    
                    if (taskMonitor) {
                        taskMonitor.updateTask(3, 'completed');
                        taskMonitor.updateTask(4, 'in_progress');
                    }
                    
                    // Select deliverables
                    await this.selectDeliverablesInMainApp(20);
                    
                    // Calculate pricing
                    await this.calculatePricingInMainApp();
                    
                    if (taskMonitor) {
                        taskMonitor.updateTask(4, 'completed');
                        taskMonitor.close();
                    }
                    
                    this.addMessage('📊 I\'ve selected deliverables and calculated pricing. What would you like to adjust?', 'assistant');
                    resolve(true);
                }
                
                // Timeout check
                if (checkCount >= maxChecks) {
                    clearInterval(progressChecker);
                    
                    if (taskMonitor) {
                        taskMonitor.updateTask(2, 'completed');
                    }
                    
                    this.addMessage('⏱️ Analysis timed out. Checking for results...', 'assistant');
                    await this.attemptResultRecovery();
                    resolve(false);
                }
            }, 500);
        });
    }
    
    async selectDeliverablesInMainApp(count = 20) {
        const parentWindow = window.parent || window;
        const parentDoc = parentWindow.document;
        
        this.addMessage(`🎯 Selecting top ${count} deliverables...`, 'assistant');
        
        // Find deliverable checkboxes in main app
        const checkboxes = parentDoc.querySelectorAll('#s2-deliv-list input[type="checkbox"], [data-deliverable-code] input[type="checkbox"]');
        
        let selected = 0;
        for (const checkbox of checkboxes) {
            if (selected >= count) break;
            if (!checkbox.checked) {
                // Visual effect before clicking
                const parent = checkbox.closest('.deliverable-item, [data-deliverable-code]');
                if (parent) this.flashElement(parent);
                
                checkbox.checked = true;
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                selected++;
                await this.delay(50); // Small delay for visual effect
            }
        }
        
        this.addMessage(`✅ Selected ${selected} deliverables`, 'assistant');
        return selected;
    }
    
    async calculatePricingInMainApp() {
        const parentWindow = window.parent || window;
        const parentDoc = parentWindow.document;
        
        this.addMessage('💰 Moving to pricing calculation...', 'assistant');
        
        // Find and click Step 3 tab
        const step3Tab = parentDoc.querySelector('[onclick*="showStep(3)"], [data-step="3"], #tab-step3');
        if (step3Tab) {
            this.showClickAnimation(step3Tab);
            step3Tab.click();
            await this.delay(1000);
        }
        
        // Look for calculate button
        const calculateBtn = parentDoc.querySelector('#calculate-btn, button[onclick*="calculate"]');
        if (calculateBtn) {
            this.showClickAnimation(calculateBtn);
            calculateBtn.click();
            await this.delay(1500);
            
            // Check for results
            const totalCost = parentDoc.querySelector('#scenario-a-total, .scenario-total, .total-cost');
            if (totalCost) {
                this.addMessage(`✅ Total cost calculated: ${totalCost.textContent}`, 'assistant');
            }
        }
        
        return true;
    }
    
    showSuccessMessage(message, duration = 3000) {
        this.showFlashMessage(message, 'success', duration);
    }
    
    showErrorMessage(message, duration = 3000) {
        this.showFlashMessage(message, 'error', duration);
    }
    
    showInfoMessage(message, duration = 3000) {
        this.showFlashMessage(message, 'info', duration);
    }
    
    showFlashMessage(message, type = 'info', duration = 3000) {
        const flash = document.createElement('div');
        flash.className = `charles-flash-message charles-flash-${type}`;
        flash.innerHTML = `
            <span class="flash-icon">${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
            <span class="flash-text">${message}</span>
        `;
        
        document.body.appendChild(flash);
        
        // Animate in
        setTimeout(() => flash.classList.add('show'), 10);
        
        // Remove after duration
        setTimeout(() => {
            flash.classList.remove('show');
            setTimeout(() => flash.remove(), 300);
        }, duration);
    }
    
    // ====================
    // SELF-HEALING & ERROR RECOVERY
    // ====================
    
    initializeAutoRecovery() {
        // Monitor for errors
        window.addEventListener('error', (event) => {
            this.handleError(event.error, 'global', { message: event.message });
        });
        
        // Monitor for unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError(event.reason, 'promise', { promise: event.promise });
        });
        
        // Monitor for network errors
        this.interceptNetworkErrors();
        
        // Add Auto-Fix button to main application header (not sidebar)
        this.addAutoFixButton();
        
        // Initialize operation tracking
        this.initializeOperationTracking();
    }
    
    addAutoFixButton() {
        // Remove any existing button first
        const existingBtn = document.getElementById('charles-auto-fix-main');
        if (existingBtn) existingBtn.remove();
        
        // Create Auto-Fix button for main application header
        const autoFixBtn = document.createElement('button');
        autoFixBtn.id = 'charles-auto-fix-main';
        autoFixBtn.className = 'charles-auto-fix-btn-main';
        autoFixBtn.innerHTML = `
            <span class="auto-fix-icon">🔧</span>
            <span class="auto-fix-text">Auto-Fix OFF</span>
            <span class="auto-fix-status">●</span>
        `;
        autoFixBtn.onclick = () => this.toggleAutoFix();
        
        // Add button to main application header
        const mainHeader = document.querySelector('header');
        if (mainHeader) {
            // Create a controls container if it doesn't exist
            let controlsContainer = mainHeader.querySelector('.header-controls');
            if (!controlsContainer) {
                controlsContainer = document.createElement('div');
                controlsContainer.className = 'header-controls';
                controlsContainer.style.cssText = `
                    position: absolute;
                    top: 20px;
                    right: 20px;
                    display: flex;
                    gap: 12px;
                    align-items: center;
                `;
                mainHeader.appendChild(controlsContainer);
            }
            controlsContainer.appendChild(autoFixBtn);
        }
        
        // Add styles for the button
        if (!document.getElementById('auto-fix-main-styles')) {
            const styles = document.createElement('style');
            styles.id = 'auto-fix-main-styles';
            styles.textContent = `
                .charles-auto-fix-btn-main {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 10px 16px;
                    background: linear-gradient(135deg, rgba(50, 50, 60, 0.9), rgba(30, 30, 40, 0.9));
                    border: 2px solid rgba(100, 100, 255, 0.3);
                    border-radius: 25px;
                    color: #ffffff;
                    font-weight: 600;
                    font-size: 14px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
                    position: relative;
                    overflow: hidden;
                }
                
                .charles-auto-fix-btn-main:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(100, 100, 255, 0.4);
                    border-color: rgba(100, 100, 255, 0.6);
                }
                
                .charles-auto-fix-btn-main.active {
                    background: linear-gradient(135deg, rgba(100, 100, 255, 0.3), rgba(139, 92, 246, 0.3));
                    border-color: #6464ff;
                    animation: pulse-glow 2s ease-in-out infinite;
                }
                
                .charles-auto-fix-btn-main .auto-fix-icon {
                    font-size: 18px;
                    animation: rotate-tool 4s linear infinite;
                }
                
                .charles-auto-fix-btn-main.active .auto-fix-icon {
                    animation: rotate-tool 1s linear infinite;
                }
                
                .charles-auto-fix-btn-main .auto-fix-status {
                    font-size: 10px;
                    color: #ff4444;
                    transition: color 0.3s ease;
                }
                
                .charles-auto-fix-btn-main.active .auto-fix-status {
                    color: #44ff44;
                    animation: blink 1s ease-in-out infinite;
                }
                
                @keyframes pulse-glow {
                    0%, 100% {
                        box-shadow: 0 6px 20px rgba(100, 100, 255, 0.4);
                    }
                    50% {
                        box-shadow: 0 8px 30px rgba(139, 92, 246, 0.6);
                    }
                }
                
                @keyframes rotate-tool {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                
                @keyframes blink {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                
                /* Stuck state warning */
                .charles-auto-fix-btn-main.stuck-detected {
                    background: linear-gradient(135deg, rgba(255, 100, 0, 0.3), rgba(255, 50, 50, 0.3));
                    border-color: #ff6600;
                    animation: flash-warning 0.5s ease-in-out infinite;
                }
                
                @keyframes flash-warning {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.7; }
                }
            `;
            document.head.appendChild(styles);
        }
    }
    
    toggleAutoFix() {
        this.autoFixEnabled = !this.autoFixEnabled;
        
        // Update main button
        const mainBtn = document.getElementById('charles-auto-fix-main');
        if (mainBtn) {
            mainBtn.classList.toggle('active', this.autoFixEnabled);
            const textSpan = mainBtn.querySelector('.auto-fix-text');
            if (textSpan) {
                textSpan.textContent = this.autoFixEnabled ? 'Auto-Fix ON' : 'Auto-Fix OFF';
            }
        }
        
        if (this.autoFixEnabled) {
            this.showSuccessMessage('🔧 Auto-Fix ENABLED - Monitoring for stuck states and errors');
            this.addMessage('🔧 Auto-Fix is now ON. I will monitor for stuck operations and automatically recover from errors.', 'assistant');
            
            // Start health check monitoring
            this.startHealthCheckMonitoring();
            
            // Process any existing errors
            this.processErrorQueue();
        } else {
            this.showInfoMessage('🔧 Auto-Fix DISABLED - Manual intervention required for errors');
            this.addMessage('🔧 Auto-Fix is now OFF. You will need to handle errors manually.', 'assistant');
            
            // Stop health check monitoring
            this.stopHealthCheckMonitoring();
        }
    }
    
    async handleError(error, context, metadata = {}) {
        const errorInfo = {
            timestamp: Date.now(),
            error: error?.message || error,
            stack: error?.stack,
            context,
            metadata,
            retryCount: 0
        };
        
        // Log error
        this.logError(context, errorInfo);
        
        // Add to recovery queue
        this.errorRecoveryQueue.push(errorInfo);
        
        // Save state before attempting recovery
        this.saveState();
        
        // Attempt auto-recovery if enabled
        if (this.autoFixEnabled) {
            await this.attemptRecovery(errorInfo);
        }
        
        // Learn from error pattern
        this.learnErrorPattern(errorInfo);
    }
    
    async attemptRecovery(errorInfo) {
        const { error, context, metadata } = errorInfo;
        
        this.showAgentWorking('Attempting automatic recovery...');
        
        try {
            switch (context) {
                case 'analysis':
                    // Retry analysis with fallback options
                    await this.recoverAnalysis(metadata);
                    break;
                    
                case 'file_upload':
                    // Retry file upload
                    await this.recoverFileUpload(metadata);
                    break;
                    
                case 'network':
                    // Handle network errors
                    await this.recoverNetwork(metadata);
                    break;
                    
                case 'ui_manipulation':
                    // Retry UI action
                    await this.recoverUIAction(metadata);
                    break;
                    
                default:
                    // Generic recovery
                    await this.genericRecovery(errorInfo);
            }
            
            this.showSuccessMessage('Recovery successful!');
            this.errorRecoveryQueue = this.errorRecoveryQueue.filter(e => e !== errorInfo);
            
        } catch (recoveryError) {
            console.error('[CHARLES] Recovery failed:', recoveryError);
            this.showErrorMessage('Auto-recovery failed. Manual intervention may be required.');
        } finally {
            this.showAgentWorking()(); // Hide overlay
        }
    }
    
    async recoverAnalysis(metadata) {
        // Try different analysis modes
        const modes = ['fast', 'deep'];
        const currentMode = document.getElementById('analysis-mode')?.value || 'fast';
        const alternateMode = modes.find(m => m !== currentMode);
        
        this.addMessage(`🔧 Retrying analysis with ${alternateMode} mode...`, 'assistant');
        await this.triggerAnalysis(alternateMode);
    }
    
    async recoverFileUpload(metadata) {
        if (metadata.file) {
            this.addMessage('🔧 Retrying file upload...', 'assistant');
            await this.handleSingleFile(metadata.file);
        }
    }
    
    async recoverNetwork(metadata) {
        // Wait and retry
        await this.delay(2000);
        if (metadata.request) {
            await this.retryWithBackoff(metadata.request, 3, 1000);
        }
    }
    
    async recoverUIAction(metadata) {
        if (metadata.action) {
            await this.delay(500);
            await this.executeAction(metadata.action);
        }
    }
    
    async genericRecovery(errorInfo) {
        // Restore to last known good state
        const lastGoodState = this.agentState.stateHistory[this.agentState.stateHistory.length - 2];
        if (lastGoodState) {
            this.restoreState({ stateHistory: [lastGoodState] });
        }
    }
    
    async retryWithBackoff(fn, maxRetries = 3, initialDelay = 1000) {
        let lastError;
        
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await fn();
            } catch (error) {
                lastError = error;
                if (i < maxRetries - 1) {
                    const delay = initialDelay * Math.pow(2, i);
                    console.log(`[CHARLES] Retry ${i + 1}/${maxRetries} after ${delay}ms`);
                    await this.delay(delay);
                }
            }
        }
        
        throw lastError;
    }
    
    interceptNetworkErrors() {
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            try {
                const response = await originalFetch(...args);
                if (!response.ok && response.status >= 500) {
                    this.handleError(
                        new Error(`Network error: ${response.status}`),
                        'network',
                        { url: args[0], status: response.status }
                    );
                }
                return response;
            } catch (error) {
                this.handleError(error, 'network', { url: args[0] });
                throw error;
            }
        };
    }
    
    processErrorQueue() {
        if (!this.autoFixEnabled || this.errorRecoveryQueue.length === 0) return;
        
        const error = this.errorRecoveryQueue.shift();
        if (error && error.retryCount < this.maxRetries) {
            error.retryCount++;
            this.attemptRecovery(error);
        }
    }
    
    learnErrorPattern(errorInfo) {
        // Store error patterns for future prevention
        this.errorPatterns.push({
            pattern: errorInfo.error,
            context: errorInfo.context,
            timestamp: errorInfo.timestamp,
            resolution: null
        });
        
        // Keep only last 50 patterns
        if (this.errorPatterns.length > 50) {
            this.errorPatterns.shift();
        }
    }
    
    // ====================
    // OPERATION TRACKING & STUCK STATE DETECTION
    // ====================
    
    initializeOperationTracking() {
        console.log('[CHARLES] Initializing operation tracking system');
        
        // Set up stuck state detector
        setInterval(() => {
            if (this.autoFixEnabled) {
                this.checkForStuckOperations();
            }
        }, 2000); // Check every 2 seconds for stuck operations
    }
    
    startOperation(type, description, metadata = {}) {
        const operationId = `op_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const timeout = this.operationTracker.operationTimeouts[type] || this.operationTracker.operationTimeouts.default;
        
        const operation = {
            id: operationId,
            type,
            description,
            metadata,
            startTime: Date.now(),
            timeout,
            timeoutHandle: setTimeout(() => {
                this.handleOperationTimeout(operationId);
            }, timeout)
        };
        
        this.operationTracker.currentOperations.set(operationId, operation);
        
        console.log(`[CHARLES] Started operation: ${description} (${operationId})`);
        this.updateOperationStatus();
        
        return operationId;
    }
    
    completeOperation(operationId) {
        const operation = this.operationTracker.currentOperations.get(operationId);
        if (operation) {
            clearTimeout(operation.timeoutHandle);
            this.operationTracker.currentOperations.delete(operationId);
            this.operationTracker.stuckOperations.delete(operationId);
            
            const duration = Date.now() - operation.startTime;
            console.log(`[CHARLES] Completed operation: ${operation.description} (${operationId}) in ${duration}ms`);
            
            this.updateOperationStatus();
        }
    }
    
    handleOperationTimeout(operationId) {
        const operation = this.operationTracker.currentOperations.get(operationId);
        if (operation) {
            console.warn(`[CHARLES] Operation timeout: ${operation.description} (${operationId})`);
            
            // Mark as stuck
            this.operationTracker.stuckOperations.add(operationId);
            
            // Update UI to show stuck state
            const mainBtn = document.getElementById('charles-auto-fix-main');
            if (mainBtn) {
                mainBtn.classList.add('stuck-detected');
            }
            
            // Show warning
            this.addMessage(`⚠️ Operation stuck: ${operation.description}. Auto-Fix will attempt recovery...`, 'assistant');
            
            if (this.autoFixEnabled) {
                // Attempt automatic recovery
                this.recoverFromStuckOperation(operation);
            } else {
                this.addMessage(`🔧 Enable Auto-Fix to automatically recover from this stuck operation.`, 'assistant');
            }
        }
    }
    
    checkForStuckOperations() {
        const now = Date.now();
        const stuckFound = [];
        
        for (const [id, operation] of this.operationTracker.currentOperations.entries()) {
            const elapsed = now - operation.startTime;
            const isStuck = elapsed > operation.timeout;
            
            if (isStuck && !this.operationTracker.stuckOperations.has(id)) {
                this.operationTracker.stuckOperations.add(id);
                stuckFound.push(operation);
                
                console.warn(`[CHARLES] Detected stuck operation: ${operation.description} (running for ${elapsed}ms)`);
            }
        }
        
        // Update UI if stuck operations found
        const mainBtn = document.getElementById('charles-auto-fix-main');
        if (mainBtn) {
            if (this.operationTracker.stuckOperations.size > 0) {
                mainBtn.classList.add('stuck-detected');
                const textSpan = mainBtn.querySelector('.auto-fix-text');
                if (textSpan && this.autoFixEnabled) {
                    textSpan.textContent = `Fixing (${this.operationTracker.stuckOperations.size})...`;
                }
            } else {
                mainBtn.classList.remove('stuck-detected');
                const textSpan = mainBtn.querySelector('.auto-fix-text');
                if (textSpan && this.autoFixEnabled) {
                    textSpan.textContent = 'Auto-Fix ON';
                }
            }
        }
        
        // Attempt recovery for stuck operations
        if (this.autoFixEnabled && stuckFound.length > 0) {
            stuckFound.forEach(operation => {
                this.recoverFromStuckOperation(operation);
            });
        }
    }
    
    async recoverFromStuckOperation(operation) {
        console.log(`[CHARLES] Attempting recovery for stuck operation: ${operation.description}`);
        
        // Show recovery message
        this.showAgentWorking(`Recovering from stuck ${operation.type} operation...`);
        
        try {
            // First, try to cancel the stuck operation
            this.cancelOperation(operation.id);
            
            // Wait a bit before retrying
            await this.delay(1000);
            
            // Attempt recovery based on operation type
            switch (operation.type) {
                case 'file_upload':
                    await this.recoverFileUpload(operation.metadata);
                    break;
                
                case 'analysis':
                    await this.recoverAnalysis(operation.metadata);
                    break;
                
                case 'ui_action':
                    await this.recoverUIAction(operation.metadata);
                    break;
                
                case 'network':
                    await this.recoverNetwork(operation.metadata);
                    break;
                
                default:
                    // Generic recovery - refresh or reset state
                    await this.genericRecovery({
                        error: `Operation stuck: ${operation.description}`,
                        context: operation.type,
                        metadata: operation.metadata
                    });
            }
            
            this.addMessage(`✅ Successfully recovered from stuck ${operation.type} operation`, 'assistant');
            this.showSuccessMessage('Recovery successful!');
            
        } catch (error) {
            console.error(`[CHARLES] Failed to recover from stuck operation:`, error);
            this.addMessage(`❌ Could not automatically recover from stuck ${operation.type} operation. Manual intervention may be required.`, 'assistant');
            this.showErrorMessage('Recovery failed - manual intervention required');
        } finally {
            this.showAgentWorking()(); // Hide overlay
        }
    }
    
    cancelOperation(operationId) {
        const operation = this.operationTracker.currentOperations.get(operationId);
        if (operation) {
            clearTimeout(operation.timeoutHandle);
            this.operationTracker.currentOperations.delete(operationId);
            this.operationTracker.stuckOperations.delete(operationId);
            
            console.log(`[CHARLES] Cancelled operation: ${operation.description} (${operationId})`);
            this.updateOperationStatus();
        }
    }
    
    updateOperationStatus() {
        // Update UI to show current operations count
        const activeCount = this.operationTracker.currentOperations.size;
        const stuckCount = this.operationTracker.stuckOperations.size;
        
        if (activeCount > 0) {
            console.log(`[CHARLES] Active operations: ${activeCount}, Stuck: ${stuckCount}`);
        }
    }
    
    // ====================
    // HEALTH CHECK MONITORING
    // ====================
    
    startHealthCheckMonitoring() {
        console.log('[CHARLES] Starting health check monitoring');
        
        // Clear any existing interval
        this.stopHealthCheckMonitoring();
        
        // Run initial health check
        this.performHealthCheck();
        
        // Set up periodic health checks
        this.healthCheckInterval = setInterval(() => {
            if (this.autoFixEnabled) {
                this.performHealthCheck();
            }
        }, this.healthCheckFrequency);
    }
    
    stopHealthCheckMonitoring() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
            console.log('[CHARLES] Stopped health check monitoring');
        }
    }
    
    async performHealthCheck() {
        const now = Date.now();
        const timeSinceLastCheck = now - this.lastHealthCheck;
        
        // Skip if checked recently
        if (timeSinceLastCheck < this.healthCheckFrequency - 1000) {
            return;
        }
        
        this.lastHealthCheck = now;
        
        // Check various health indicators
        const healthStatus = {
            timestamp: now,
            operations: {
                active: this.operationTracker.currentOperations.size,
                stuck: this.operationTracker.stuckOperations.size
            },
            errors: {
                queue: this.errorRecoveryQueue.length,
                recent: this.errorPatterns.filter(e => now - e.timestamp < 60000).length // Errors in last minute
            },
            state: {
                step: this.detectCurrentStep(),
                hasData: this.agentState.uploadedFiles.length > 0 || this.agentState.selectedDeliverables.length > 0
            }
        };
        
        // Log health status
        if (healthStatus.operations.stuck > 0 || healthStatus.errors.queue > 0) {
            console.warn('[CHARLES] Health Check - Issues detected:', healthStatus);
            
            // Attempt to fix issues
            if (healthStatus.operations.stuck > 0) {
                this.addMessage(`🔧 Auto-Fix: Detected ${healthStatus.operations.stuck} stuck operations. Attempting recovery...`, 'assistant');
            }
            
            if (healthStatus.errors.queue > 0) {
                this.processErrorQueue();
            }
        } else {
            console.log('[CHARLES] Health Check - System healthy');
        }
        
        // Check for specific issues
        this.checkForCommonIssues();
        
        return healthStatus;
    }
    
    checkForCommonIssues() {
        // Check if analysis job is stuck
        if (this.agentState.jobId) {
            const jobAge = Date.now() - (this.agentState.jobStartTime || 0);
            if (jobAge > 240000) { // 4 minutes
                console.warn('[CHARLES] Long-running analysis job detected');
                this.addMessage('⚠️ Analysis is taking longer than expected. Checking status...', 'assistant');
                this.attemptResultRecovery(this.agentState.jobId);
            }
        }
        
        // Check for disconnected state
        if (navigator.onLine === false) {
            this.handleError(new Error('Network connection lost'), 'network', { online: false });
        }
        
        // Check for UI responsiveness
        const lastInteraction = Date.now() - (this.lastUserInteraction || Date.now());
        if (lastInteraction > 300000) { // 5 minutes of inactivity
            console.log('[CHARLES] No user interaction for 5 minutes');
        }
    }
    
    // Track wrapped operations
    async trackOperation(type, description, asyncFn, metadata = {}) {
        const operationId = this.startOperation(type, description, metadata);
        
        try {
            const result = await asyncFn();
            this.completeOperation(operationId);
            return result;
        } catch (error) {
            this.completeOperation(operationId);
            throw error;
        }
    }
    
    // Wrap common operations with tracking
    async trackedFetch(url, options = {}, operationType = 'network') {
        return this.trackOperation(
            operationType,
            `Fetching ${url}`,
            () => fetch(url, options),
            { url, method: options.method || 'GET' }
        );
    }
    
    // Add tracking to existing methods
    wrapMethodWithTracking(methodName, operationType, getDescription) {
        const originalMethod = this[methodName];
        if (originalMethod && typeof originalMethod === 'function') {
            this[methodName] = async function(...args) {
                const description = getDescription ? getDescription(...args) : methodName;
                return this.trackOperation(
                    operationType,
                    description,
                    () => originalMethod.apply(this, args),
                    { method: methodName, args: args.slice(0, 2) } // Only store first 2 args for safety
                );
            }.bind(this);
        }
    }
    
    // ====================
    // ENHANCED UI MANIPULATION
    // ====================
    
    simulateClick(selector, options = {}) {
        const element = typeof selector === 'string' ? document.querySelector(selector) : selector;
        
        if (!element) {
            throw new Error(`Element not found: ${selector}`);
        }
        
        // Visual feedback
        this.flashElement(element, options.flashDuration || 500);
        
        // Create and dispatch events
        const events = ['mousedown', 'mouseup', 'click'];
        events.forEach(eventType => {
            const event = new MouseEvent(eventType, {
                bubbles: true,
                cancelable: true,
                view: window,
                ...options.eventOptions
            });
            element.dispatchEvent(event);
        });
        
        // Also trigger change for inputs
        if (element.tagName === 'INPUT' || element.tagName === 'SELECT') {
            element.dispatchEvent(new Event('change', { bubbles: true }));
            element.dispatchEvent(new Event('input', { bubbles: true }));
        }
        
        this.logAction('click', { selector, element: element.tagName });
        
        return element;
    }
    
    fillForm(formData, formSelector = null) {
        const form = formSelector ? document.querySelector(formSelector) : document.querySelector('form');
        
        if (!form && !formSelector) {
            // Fill any matching inputs on the page
            Object.entries(formData).forEach(([key, value]) => {
                const input = document.getElementById(key) || 
                            document.querySelector(`[name="${key}"]`) ||
                            document.querySelector(`[data-field="${key}"]`);
                
                if (input) {
                    this.fillInput(input, value);
                }
            });
        } else if (form) {
            // Fill form fields
            Object.entries(formData).forEach(([key, value]) => {
                const input = form.querySelector(`#${key}`) || 
                            form.querySelector(`[name="${key}"]`) ||
                            form.querySelector(`[data-field="${key}"]`);
                
                if (input) {
                    this.fillInput(input, value);
                }
            });
        }
        
        this.logAction('fill_form', { fields: Object.keys(formData) });
    }
    
    fillInput(input, value) {
        this.flashElement(input);
        
        if (input.type === 'checkbox') {
            input.checked = !!value;
        } else if (input.type === 'radio') {
            if (input.value === value) {
                input.checked = true;
            }
        } else if (input.tagName === 'SELECT') {
            input.value = value;
            // Try setting by text if value doesn't work
            if (input.value !== value) {
                const option = Array.from(input.options).find(o => o.text === value);
                if (option) option.selected = true;
            }
        } else {
            // Simulate typing for text inputs
            input.focus();
            input.value = '';
            for (let char of value.toString()) {
                input.value += char;
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }
        
        // Trigger events
        input.dispatchEvent(new Event('change', { bubbles: true }));
        input.dispatchEvent(new Event('blur', { bubbles: true }));
    }
    
    async loadAnalysisResults(data) {
        this.addMessage('📥 Loading deliverables into the application...', 'assistant');
        
        // Call the global function to load data
        if (typeof window.loadScenarioData === 'function') {
            window.loadScenarioData(data);
            await this.delay(1000);
            this.addMessage(`✅ Loaded ${data.deliverables?.length || 0} deliverables`, 'assistant');
        } else {
            // Fallback - directly manipulate the UI
            const deliverables = data.deliverables || [];
            
            // Store in window for app to use
            window.analysisResults = data;
            window.availableDeliverables = deliverables;
            
            // Trigger any event listeners
            window.dispatchEvent(new CustomEvent('analysisComplete', { detail: data }));
        }
        
        return true;
    }
    
    async selectTopDeliverables(count = 20) {
        this.addMessage(`🎯 Selecting top ${count} recommended deliverables...`, 'assistant');
        
        // Find all deliverable checkboxes
        const checkboxes = document.querySelectorAll('input[type="checkbox"][data-deliverable-id], input[type="checkbox"][id^="check-"]');
        let selected = 0;
        
        // Select the first N checkboxes
        for (const checkbox of checkboxes) {
            if (selected >= count) break;
            if (!checkbox.checked) {
                checkbox.checked = true;
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                this.flashElement(checkbox.closest('.deliverable-item, .component-item'));
                selected++;
                await this.delay(50); // Small delay for visual effect
            }
        }
        
        // Also try the select all button if available
        if (selected === 0) {
            const selectAllBtn = document.querySelector('#select-all-btn, button[onclick*="selectAll"]');
            if (selectAllBtn) {
                this.simulateClick(selectAllBtn);
                this.addMessage('✅ Selected all recommended deliverables', 'assistant');
            }
        } else {
            this.addMessage(`✅ Selected ${selected} deliverables`, 'assistant');
        }
        
        return selected;
    }
    
    async calculateScenarioA() {
        this.addMessage('💰 Calculating pricing for Scenario A...', 'assistant');
        
        // Find and click the calculate button
        const calculateBtn = document.querySelector('#calculate-btn, button[onclick*="calculate"], button:contains("Calculate")');
        if (calculateBtn) {
            this.simulateClick(calculateBtn);
            this.flashElement(calculateBtn);
            await this.delay(1500);
            
            // Check if results appeared
            const totalCost = document.querySelector('#scenario-a-total, .scenario-total, .total-cost');
            if (totalCost) {
                const cost = totalCost.textContent;
                this.addMessage(`✅ Calculated total cost: ${cost}`, 'assistant');
            }
        }
        
        // Navigate to Step 3 for timeline
        setTimeout(() => {
            this.navigateToStep('step3');
        }, 1000);
        
        return true;
    }
    
    async attemptResultRecovery(jobId) {
        this.addMessage('🔄 Attempting to recover analysis results...', 'assistant');
        
        try {
            // Try different endpoints to get results
            const endpoints = [
                `/api/agencydb/status/${jobId}`,
                `/api/agencydb/result/${jobId}`,
                `/api/jobs/${jobId}`,
                `/api/analysis/${jobId}`
            ];
            
            for (const endpoint of endpoints) {
                try {
                    const response = await fetch(endpoint);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.deliverables || data.data?.deliverables || data.result?.deliverables) {
                            const results = data.data || data.result || data;
                            this.addMessage(`✅ Found results! Loading ${results.deliverables?.length || 0} deliverables...`, 'assistant');
                            
                            await this.loadAnalysisResults(results);
                            await this.navigateToStep('step2');
                            await this.selectTopDeliverables(20);
                            await this.calculateScenarioA();
                            
                            return true;
                        }
                    }
                } catch (e) {
                    console.log(`[CHARLES] Recovery attempt failed for ${endpoint}:`, e);
                }
            }
            
            // If all else fails, try to trigger a new analysis
            this.addMessage('❌ Could not recover results. Starting fresh analysis...', 'assistant');
            
            // Click the analyze button
            const analyzeBtn = document.querySelector('#analyze-btn, button[onclick*="analyze"], .analyze-with-ai');
            if (analyzeBtn) {
                this.simulateClick(analyzeBtn);
            }
            
        } catch (error) {
            this.handleError(error, 'recovery', { jobId });
        }
        
        return false;
    }
    
    navigateToStep(stepId) {
        const targetStep = document.getElementById(stepId);
        if (!targetStep) {
            console.warn(`[CHARLES] Step not found: ${stepId}`);
            return false;
        }
        
        // Hide all steps
        ['step1', 'step2', 'step3', 'step4'].forEach(id => {
            const step = document.getElementById(id);
            if (step) step.style.display = 'none';
        });
        
        // Show target step
        targetStep.style.display = 'block';
        
        // Scroll to step
        targetStep.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Update agent state
        this.agentState.currentStep = stepId;
        
        // Visual feedback
        this.flashElement(targetStep, 1000, '#10b981');
        
        return true;
    }
    
    selectCheckboxes(codes, checked = true) {
        const results = { success: [], failed: [] };
        
        codes.forEach(code => {
            const checkbox = document.querySelector(`input[type="checkbox"][data-deliverable="${code}"]`) ||
                           document.querySelector(`input[type="checkbox"][value="${code}"]`) ||
                           document.querySelector(`#${code}`);
            
            if (checkbox) {
                checkbox.checked = checked;
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                this.flashElement(checkbox, 300);
                results.success.push(code);
            } else {
                results.failed.push(code);
            }
        });
        
        return results;
    }
    
    
    // ====================
    // BATCH FILE PROCESSING
    // ====================
    
    async processFiles(files) {
        if (!files || files.length === 0) {
            this.addMessage('No files to process.', 'assistant');
            return;
        }
        
        this.batchProcessingStatus = {
            total: files.length,
            completed: 0,
            failed: 0,
            inProgress: true,
            fileStatuses: new Map()
        };
        
        this.addMessage(`📁 Processing ${files.length} file(s)...`, 'assistant');
        this.showBatchProgress();
        
        // Process files concurrently with limit
        const batchSize = 3;
        const results = [];
        
        for (let i = 0; i < files.length; i += batchSize) {
            const batch = Array.from(files).slice(i, i + batchSize);
            const batchPromises = batch.map(file => this.processSingleFile(file));
            const batchResults = await Promise.allSettled(batchPromises);
            results.push(...batchResults);
        }
        
        // Update final status
        this.batchProcessingStatus.inProgress = false;
        
        // Show summary
        this.showBatchSummary(results);
    }
    
    async processSingleFile(file) {
        const fileId = `${file.name}_${Date.now()}`;
        
        try {
            // Update status
            this.batchProcessingStatus.fileStatuses.set(fileId, {
                name: file.name,
                status: 'processing',
                progress: 0
            });
            this.updateBatchProgress();
            
            // Process based on file type
            const result = await this.handleSingleFile(file);
            
            // Update status
            this.batchProcessingStatus.completed++;
            this.batchProcessingStatus.fileStatuses.set(fileId, {
                name: file.name,
                status: 'completed',
                progress: 100,
                result
            });
            this.updateBatchProgress();
            
            return { file: file.name, success: true, result };
            
        } catch (error) {
            // Update status
            this.batchProcessingStatus.failed++;
            this.batchProcessingStatus.fileStatuses.set(fileId, {
                name: file.name,
                status: 'failed',
                progress: 0,
                error: error.message
            });
            this.updateBatchProgress();
            
            console.error(`[CHARLES] Failed to process ${file.name}:`, error);
            return { file: file.name, success: false, error: error.message };
        }
    }
    
    showBatchProgress() {
        let progressDiv = document.getElementById('charles-batch-progress');
        if (!progressDiv) {
            progressDiv = document.createElement('div');
            progressDiv.id = 'charles-batch-progress';
            progressDiv.className = 'charles-batch-progress';
            document.querySelector('.ai-chat-messages').appendChild(progressDiv);
        }
        
        this.updateBatchProgress();
    }
    
    updateBatchProgress() {
        const progressDiv = document.getElementById('charles-batch-progress');
        if (!progressDiv) return;
        
        const { total, completed, failed, fileStatuses } = this.batchProcessingStatus;
        const progress = total > 0 ? ((completed + failed) / total * 100).toFixed(0) : 0;
        
        const filesList = Array.from(fileStatuses.values()).map(file => {
            const icon = file.status === 'completed' ? '✅' : 
                        file.status === 'failed' ? '❌' : '⏳';
            const progressBar = file.status === 'processing' ? 
                `<div class="file-progress-bar"><div class="file-progress-fill" style="width: ${file.progress}%"></div></div>` : '';
            
            return `
                <div class="batch-file-item ${file.status}">
                    ${icon} ${file.name}
                    ${progressBar}
                    ${file.error ? `<div class="file-error">${file.error}</div>` : ''}
                </div>
            `;
        }).join('');
        
        progressDiv.innerHTML = `
            <div class="batch-progress-header">
                <strong>Batch Processing</strong>
                <span>${completed + failed}/${total} files (${progress}%)</span>
            </div>
            <div class="batch-progress-bar">
                <div class="batch-progress-fill" style="width: ${progress}%"></div>
            </div>
            <div class="batch-files-list">
                ${filesList}
            </div>
        `;
    }
    
    showBatchSummary(results) {
        const successful = results.filter(r => r.status === 'fulfilled' && r.value?.success).length;
        const failed = results.length - successful;
        
        const summary = `
            📊 **Batch Processing Complete**
            - Total files: ${results.length}
            - Successfully processed: ${successful}
            - Failed: ${failed}
            ${failed > 0 ? '\n⚠️ Some files failed to process. Check the details above.' : '\n✅ All files processed successfully!'}
        `;
        
        this.addMessage(summary, 'assistant');
        
        // Clear batch progress after delay
        setTimeout(() => {
            const progressDiv = document.getElementById('charles-batch-progress');
            if (progressDiv) progressDiv.remove();
        }, 5000);
    }
    
    // ====================
    // EXISTING METHODS (ENHANCED)
    // ====================
    
    createSidebar() {
        // Create main container
        const container = document.createElement('div');
        container.id = 'ai-assistant-container';
        container.className = 'ai-assistant-container';
        container.innerHTML = `
            <div class="ai-assistant-resize-handle" title="Drag to resize"></div>
            <div class="ai-assistant-sidebar ${this.isMinimized ? 'minimized' : ''}">
                <div class="ai-assistant-header">
                    <div class="ai-assistant-title">
                        <span class="ai-icon charles-sphere">🔮</span>
                        <span style="font-weight:700;">CHARLES AGENT</span>
                        <span style="font-size:10px;opacity:0.8;">ProBuFo v3.0</span>
                        <span class="ai-status-indicator" id="ai-status-indicator">●</span>
                    </div>
                    <div class="ai-assistant-controls">
                        <button class="ai-btn-minimize" id="ai-btn-minimize" title="Minimize">
                            <span>_</span>
                        </button>
                        <button class="ai-btn-close" id="ai-btn-close" title="Close">
                            <span>×</span>
                        </button>
                    </div>
                </div>
                
                <div class="ai-assistant-body">
                    <div class="ai-gpt5-selector">
                        <label style="color:#8b5cf6;font-size:12px;font-weight:600;">GPT-5 Intelligence Level</label>
                        <select id="gpt5-tier-selector" style="width:100%;padding:8px;background:#1a1a2e;color:white;border:1px solid #8b5cf6;border-radius:6px;margin-top:4px;">
                            <option value="auto">🚀 Auto (Fast & Smart)</option>
                            <option value="mini">⚡ GPT-5 Mini (Fastest)</option>
                            <option value="thinking-mini">🧠 Thinking Mini (Balanced)</option>
                            <option value="thinking">💭 Thinking (Deep Analysis)</option>
                            <option value="pro">👑 Pro (Maximum Intelligence)</option>
                        </select>
                    </div>
                    
                    <!-- State Management Controls -->
                    <div class="ai-state-controls">
                        <button class="ai-btn-save-state" onclick="window.aiAssistant.saveState()">💾 Save State</button>
                        <button class="ai-btn-restore-state" onclick="window.aiAssistant.restoreState()">📂 Restore State</button>
                    </div>
                    
                    <!-- File Staging Area -->
                    <div class="ai-file-staging" id="ai-file-staging" style="display: none;">
                        <div class="ai-staging-header">
                            <span>📁 Files Ready to Send</span>
                            <button class="ai-clear-files" id="ai-clear-files" title="Clear All">×</button>
                        </div>
                        <div class="ai-staged-files" id="ai-staged-files"></div>
                    </div>
                    
                    <div class="ai-chat-messages" id="ai-chat-messages">
                        <div class="ai-welcome-message">
                            <h4>🔮 Welcome to CHARLES AGENT: ProBuFo v3.0</h4>
                            <p style="font-style:italic;color:#8b5cf6;">Progressive Business Forecasting Oracle</p>
                            <p>Enhanced with autonomous self-healing, state preservation, and real-time progress tracking.</p>
                            <div class="ai-capabilities">
                                <p><strong>New Capabilities:</strong></p>
                                <ul>
                                    <li>🔄 Auto-recovery from errors</li>
                                    <li>💾 Complete state preservation</li>
                                    <li>📊 Real-time progress tracking</li>
                                    <li>🎯 Enhanced UI manipulation</li>
                                    <li>📁 Batch file processing</li>
                                </ul>
                            </div>
                            <div class="ai-suggestions">
                                <p><strong>Try commands like:</strong></p>
                                <ul>
                                    <li>📄 "Analyze the RFP in deep mode"</li>
                                    <li>💰 "Set Creative Strategy to $10k monthly"</li>
                                    <li>📊 "Add 20% markup to all deliverables"</li>
                                    <li>📅 "Generate an optimized timeline"</li>
                                    <li>💾 "Export to Excel"</li>
                                    <li>🔧 "Enable auto-recovery"</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    
                    <div class="ai-action-preview" id="ai-action-preview" style="display: none;">
                        <div class="ai-action-header">
                            <span>📋 Executing Actions</span>
                            <span class="ai-action-count" id="ai-action-count">0/0</span>
                        </div>
                        <div class="ai-action-list" id="ai-action-list"></div>
                    </div>
                    
                    <div class="ai-chat-input">
                        <textarea 
                            id="ai-chat-input" 
                            placeholder="Type your command or drag & drop files here..."
                            rows="2"
                            maxlength="500"
                        ></textarea>
                        <div class="ai-input-controls">
                            <input type="file" id="ai-file-input" accept=".pdf,.docx,.txt,.xlsx" multiple style="display:none;">
                            <button id="ai-file-btn" class="ai-file-btn" title="Upload Documents">
                                <span>📎</span>
                            </button>
                            <button id="ai-send-btn" class="ai-send-btn" disabled>
                                <span class="send-icon">➤</span>
                                <span class="loading-icon" style="display: none;">⏳</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <button class="ai-assistant-toggle" id="ai-assistant-toggle" title="Open CHARLES AGENT">
                <span class="toggle-icon charles-sphere">🔮</span>
                <span class="toggle-text">CHARLES</span>
                <span class="notification-badge" id="ai-notification-badge" style="display: none;">!</span>
            </button>
        `;
        
        console.log('[CHARLES] About to append container to body...');
        document.body.appendChild(container);
        console.log('[CHARLES] Container appended to body successfully!');
        
        // Verify the toggle button is present
        const toggle = document.getElementById('ai-assistant-toggle');
        if (toggle) {
            console.log('[CHARLES] Toggle button found after append:', toggle);
            // Force it to be visible
            toggle.style.display = 'flex';
            toggle.style.visibility = 'visible';
            toggle.style.opacity = '1';
            toggle.style.zIndex = '99999';
        } else {
            console.error('[CHARLES] Toggle button NOT found after append!');
        }
    }
    
    addEnhancedStyles() {
        const style = document.createElement('style');
        style.textContent = `
            ${this.getBaseStyles()}
            ${this.getProgressStyles()}
            ${this.getVisualFeedbackStyles()}
            ${this.getBatchProcessingStyles()}
            ${this.getEnhancedAnimations()}
        `;
        document.head.appendChild(style);
    }
    
    getBaseStyles() {
        return `
            .ai-assistant-container {
                position: fixed;
                right: 20px;
                bottom: 20px;
                z-index: 10000;
                font-family: system-ui, -apple-system, sans-serif;
            }
            
            .ai-assistant-sidebar {
                position: fixed;
                right: 20px;
                bottom: 80px;
                width: 420px;
                height: 650px;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3), 0 0 20px rgba(139, 92, 246, 0.2);
                display: none;
                flex-direction: column;
                border: 1px solid rgba(139, 92, 246, 0.3);
                animation: slideUp 0.3s ease-out;
            }
            
            .ai-assistant-sidebar.open {
                display: flex;
            }
            
            .ai-assistant-sidebar.minimized {
                height: 60px;
                overflow: hidden;
            }
            
            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .ai-state-controls {
                display: flex;
                gap: 8px;
                padding: 8px 16px;
                background: rgba(16, 185, 129, 0.1);
                border-bottom: 1px solid rgba(16, 185, 129, 0.2);
            }
            
            .ai-state-controls button {
                flex: 1;
                padding: 6px 12px;
                background: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.2s;
            }
            
            .ai-state-controls button:hover {
                background: rgba(255, 255, 255, 0.2);
                transform: translateY(-1px);
            }
            
            .charles-auto-fix-btn {
                padding: 4px 8px;
                background: rgba(251, 191, 36, 0.1);
                color: #fbbf24;
                border: 1px solid rgba(251, 191, 36, 0.3);
                border-radius: 4px;
                cursor: pointer;
                font-size: 11px;
                transition: all 0.2s;
            }
            
            .charles-auto-fix-btn.active {
                background: rgba(251, 191, 36, 0.3);
                border-color: #fbbf24;
            }
        `;
    }
    
    getProgressStyles() {
        return `
            .charles-floating-progress {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 350px;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
                z-index: 10001;
                animation: slideDown 0.3s ease-out;
            }
            
            @keyframes slideDown {
                from {
                    opacity: 0;
                    transform: translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .charles-progress-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                background: rgba(139, 92, 246, 0.1);
                border-bottom: 1px solid rgba(139, 92, 246, 0.2);
                border-radius: 12px 12px 0 0;
            }
            
            .charles-progress-title {
                color: white;
                font-weight: 600;
                font-size: 14px;
            }
            
            .charles-progress-close {
                color: rgba(255, 255, 255, 0.5);
                cursor: pointer;
                font-size: 20px;
                transition: color 0.2s;
            }
            
            .charles-progress-close:hover {
                color: white;
            }
            
            .charles-progress-content {
                padding: 16px;
            }
            
            .charles-progress-bar-container,
            .progress-bar-container {
                width: 100%;
                height: 8px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 4px;
                overflow: hidden;
                margin-bottom: 12px;
            }
            
            .charles-progress-bar,
            .progress-bar {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                border-radius: 4px;
                transition: width 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .charles-progress-bar::after,
            .progress-bar::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                bottom: 0;
                right: 0;
                background: linear-gradient(
                    90deg,
                    transparent,
                    rgba(255, 255, 255, 0.3),
                    transparent
                );
                animation: shimmer 2s infinite;
            }
            
            @keyframes shimmer {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }
            
            .charles-progress-text,
            .progress-text {
                color: white;
                font-size: 14px;
                margin-bottom: 8px;
            }
            
            .charles-progress-details {
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                line-height: 1.4;
            }
            
            .charles-progress-details ul {
                margin: 4px 0;
                padding-left: 20px;
            }
            
            .charles-step-progress {
                margin: 16px 0;
                padding: 12px;
                background: rgba(139, 92, 246, 0.1);
                border: 1px solid rgba(139, 92, 246, 0.2);
                border-radius: 8px;
            }
            
            .progress-indicator {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .progress-bar-mini {
                width: 100%;
                height: 4px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 2px;
                overflow: hidden;
            }
            
            .progress-fill {
                height: 100%;
                background: #10b981;
                transition: width 0.3s ease;
            }
            
            .progress-status {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 13px;
            }
            
            .progress-percentage {
                color: #10b981;
                font-weight: 600;
            }
        `;
    }
    
    getVisualFeedbackStyles() {
        return `
            .charles-working-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(4px);
                display: none;
                align-items: center;
                justify-content: center;
                z-index: 9999;
            }
            
            .charles-working-content {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 16px;
            }
            
            .charles-sphere-animated {
                font-size: 48px;
                animation: rotateSphere 2s infinite linear;
                filter: drop-shadow(0 0 30px rgba(139, 92, 246, 1));
            }
            
            .charles-working-text {
                color: white;
                font-size: 18px;
                font-weight: 600;
            }
            
            .charles-working-spinner {
                width: 40px;
                height: 40px;
                border: 3px solid rgba(139, 92, 246, 0.2);
                border-top: 3px solid #8b5cf6;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .charles-element-highlight {
                animation: pulse-highlight 0.5s ease;
            }
            
            @keyframes pulse-highlight {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            
            .charles-flash-message {
                position: fixed;
                top: 80px;
                right: 20px;
                padding: 16px 24px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                display: flex;
                align-items: center;
                gap: 12px;
                z-index: 10002;
                transform: translateX(400px);
                transition: transform 0.3s ease;
            }
            
            .charles-flash-message.show {
                transform: translateX(0);
            }
            
            .charles-flash-success {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
            }
            
            .charles-flash-error {
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                color: white;
            }
            
            .charles-flash-info {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: white;
            }
            
            .flash-icon {
                font-size: 20px;
            }
            
            .flash-text {
                font-size: 14px;
                font-weight: 500;
            }
        `;
    }
    
    
    getBatchProcessingStyles() {
        return `
            .charles-batch-progress {
                background: rgba(251, 191, 36, 0.1);
                border: 1px solid rgba(251, 191, 36, 0.2);
                border-radius: 8px;
                padding: 12px;
                margin: 12px 0;
            }
            
            .batch-progress-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                color: #fbbf24;
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            
            .batch-progress-bar {
                width: 100%;
                height: 6px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 3px;
                overflow: hidden;
                margin-bottom: 12px;
            }
            
            .batch-progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%);
                transition: width 0.3s ease;
            }
            
            .batch-files-list {
                max-height: 150px;
                overflow-y: auto;
            }
            
            .batch-file-item {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px;
                margin: 4px 0;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                font-size: 12px;
                color: rgba(255, 255, 255, 0.8);
            }
            
            .batch-file-item.completed {
                border-left: 2px solid #10b981;
            }
            
            .batch-file-item.failed {
                border-left: 2px solid #ef4444;
            }
            
            .batch-file-item.processing {
                border-left: 2px solid #fbbf24;
            }
            
            .file-progress-bar {
                flex: 1;
                height: 3px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 2px;
                overflow: hidden;
            }
            
            .file-progress-fill {
                height: 100%;
                background: #fbbf24;
                transition: width 0.3s ease;
            }
            
            .file-error {
                color: #ef4444;
                font-size: 11px;
                margin-top: 4px;
            }
        `;
    }
    
    getEnhancedAnimations() {
        return `
            @keyframes rotateSphere {
                0% { transform: rotateY(0deg) rotateX(0deg); }
                25% { transform: rotateY(90deg) rotateX(15deg); }
                50% { transform: rotateY(180deg) rotateX(0deg); }
                75% { transform: rotateY(270deg) rotateX(-15deg); }
                100% { transform: rotateY(360deg) rotateX(0deg); }
            }
            
            .charles-sphere {
                display: inline-block;
                animation: rotateSphere 8s infinite linear;
                filter: drop-shadow(0 0 10px rgba(139, 92, 246, 0.8));
            }
            
            /* Existing styles */
            .ai-assistant-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px;
                background: rgba(139, 92, 246, 0.1);
                border-bottom: 1px solid rgba(139, 92, 246, 0.2);
                border-radius: 12px 12px 0 0;
            }
            
            .ai-assistant-title {
                display: flex;
                align-items: center;
                gap: 8px;
                color: white;
                font-weight: 600;
                font-size: 15px;
            }
            
            .ai-icon {
                font-size: 20px;
            }
            
            .ai-gpt5-selector {
                padding: 12px 16px;
                border-bottom: 1px solid rgba(139, 92, 246, 0.2);
                background: rgba(139, 92, 246, 0.05);
            }
            
            .ai-file-staging {
                padding: 12px 16px;
                background: rgba(16, 185, 129, 0.1);
                border-bottom: 1px solid rgba(16, 185, 129, 0.2);
                max-height: 120px;
                overflow-y: auto;
            }
            
            .ai-staging-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                color: #10b981;
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            
            .ai-clear-files {
                background: rgba(239, 68, 68, 0.2);
                color: #ef4444;
                border: none;
                width: 24px;
                height: 24px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.2s;
            }
            
            .ai-clear-files:hover {
                background: rgba(239, 68, 68, 0.3);
                transform: scale(1.1);
            }
            
            .ai-staged-files {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            
            .ai-staged-file {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 6px 8px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 12px;
            }
            
            .ai-file-info {
                display: flex;
                align-items: center;
                gap: 6px;
                flex: 1;
            }
            
            .ai-file-remove {
                color: #ef4444;
                cursor: pointer;
                padding: 2px 6px;
                transition: transform 0.2s;
            }
            
            .ai-file-remove:hover {
                transform: scale(1.2);
            }
            
            .ai-status-indicator {
                font-size: 8px;
                color: #10b981;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .ai-status-indicator.offline {
                color: #ef4444;
                animation: none;
            }
            
            .ai-assistant-controls {
                display: flex;
                gap: 4px;
            }
            
            .ai-assistant-controls button {
                width: 28px;
                height: 28px;
                border: none;
                background: rgba(255, 255, 255, 0.1);
                color: white;
                border-radius: 6px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                font-size: 16px;
            }
            
            .ai-assistant-controls button:hover {
                background: rgba(255, 255, 255, 0.2);
                transform: scale(1.1);
            }
            
            .ai-assistant-body {
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .ai-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            
            .ai-chat-messages::-webkit-scrollbar {
                width: 6px;
            }
            
            .ai-chat-messages::-webkit-scrollbar-track {
                background: rgba(0, 0, 0, 0.1);
                border-radius: 3px;
            }
            
            .ai-chat-messages::-webkit-scrollbar-thumb {
                background: rgba(139, 92, 246, 0.3);
                border-radius: 3px;
            }
            
            .ai-welcome-message {
                color: white;
                padding: 16px;
                background: rgba(139, 92, 246, 0.1);
                border-radius: 8px;
                border: 1px solid rgba(139, 92, 246, 0.2);
            }
            
            .ai-welcome-message h4 {
                margin: 0 0 8px 0;
                color: #a78bfa;
                font-size: 16px;
            }
            
            .ai-welcome-message p {
                margin: 0 0 12px 0;
                color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
                line-height: 1.5;
            }
            
            .ai-capabilities {
                margin: 12px 0;
                padding: 12px;
                background: rgba(16, 185, 129, 0.1);
                border-radius: 6px;
                border: 1px solid rgba(16, 185, 129, 0.2);
            }
            
            .ai-capabilities ul {
                margin: 8px 0 0 0;
                padding-left: 20px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
            }
            
            .ai-suggestions {
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid rgba(139, 92, 246, 0.2);
            }
            
            .ai-suggestions ul {
                margin: 8px 0 0 0;
                padding-left: 20px;
                color: rgba(255, 255, 255, 0.7);
                font-size: 13px;
            }
            
            .ai-suggestions li {
                margin: 4px 0;
                cursor: pointer;
                transition: color 0.2s;
            }
            
            .ai-suggestions li:hover {
                color: #a78bfa;
            }
            
            .ai-message {
                display: flex;
                gap: 8px;
                animation: fadeIn 0.3s ease-out;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .ai-message.user {
                flex-direction: row-reverse;
            }
            
            .ai-message-avatar {
                width: 32px;
                height: 32px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                background: rgba(139, 92, 246, 0.2);
                flex-shrink: 0;
            }
            
            .ai-message.user .ai-message-avatar {
                background: rgba(59, 130, 246, 0.2);
            }
            
            .ai-message-content {
                flex: 1;
                padding: 10px 14px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                color: white;
                font-size: 14px;
                line-height: 1.5;
                border: 1px solid rgba(139, 92, 246, 0.2);
            }
            
            .ai-message.user .ai-message-content {
                background: rgba(59, 130, 246, 0.1);
                border-color: rgba(59, 130, 246, 0.3);
            }
            
            .ai-message-typing {
                display: flex;
                gap: 4px;
                padding: 10px 14px;
            }
            
            .ai-message-typing span {
                width: 8px;
                height: 8px;
                background: rgba(139, 92, 246, 0.6);
                border-radius: 50%;
                animation: typing 1.4s infinite;
            }
            
            .ai-message-typing span:nth-child(2) {
                animation-delay: 0.2s;
            }
            
            .ai-message-typing span:nth-child(3) {
                animation-delay: 0.4s;
            }
            
            @keyframes typing {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-10px); }
            }
            
            .ai-action-preview {
                padding: 12px;
                background: rgba(16, 185, 129, 0.1);
                border-top: 1px solid rgba(16, 185, 129, 0.2);
            }
            
            .ai-action-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                color: #10b981;
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            
            .ai-action-list {
                display: flex;
                flex-direction: column;
                gap: 4px;
                max-height: 120px;
                overflow-y: auto;
            }
            
            .ai-action-item {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px 8px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                transition: all 0.2s;
            }
            
            .ai-action-item.executing {
                background: rgba(16, 185, 129, 0.2);
                color: #10b981;
            }
            
            .ai-action-item.completed {
                opacity: 0.5;
                text-decoration: line-through;
            }
            
            .ai-chat-input {
                display: flex;
                flex-direction: column;
                gap: 8px;
                padding: 12px;
                background: rgba(0, 0, 0, 0.2);
                border-top: 1px solid rgba(139, 92, 246, 0.2);
                border-radius: 0 0 12px 12px;
            }
            
            .ai-input-controls {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            
            .ai-file-btn {
                background: rgba(139, 92, 246, 0.2);
                color: #8b5cf6;
                border: 1px solid rgba(139, 92, 246, 0.4);
                padding: 8px;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 18px;
            }
            
            .ai-file-btn:hover {
                background: rgba(139, 92, 246, 0.3);
                transform: scale(1.05);
            }
            
            #ai-chat-input {
                flex: 1;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(139, 92, 246, 0.2);
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 14px;
                resize: none;
                outline: none;
                transition: all 0.2s;
            }
            
            #ai-chat-input:focus {
                background: rgba(255, 255, 255, 0.08);
                border-color: rgba(139, 92, 246, 0.4);
            }
            
            #ai-chat-input::placeholder {
                color: rgba(255, 255, 255, 0.4);
            }
            
            .ai-send-btn {
                width: 40px;
                height: 40px;
                border: none;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 8px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                font-size: 18px;
            }
            
            .ai-send-btn:not(:disabled):hover {
                transform: scale(1.05);
                box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
            }
            
            .ai-send-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .ai-assistant-toggle {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 12px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 12px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
                box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
                transition: all 0.2s;
                position: relative;
            }
            
            .ai-assistant-toggle:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
            }
            
            .toggle-icon {
                font-size: 18px;
            }
            
            .notification-badge {
                position: absolute;
                top: -4px;
                right: -4px;
                width: 16px;
                height: 16px;
                background: #ef4444;
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                font-weight: 600;
                animation: bounce 2s infinite;
            }
            
            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-4px); }
            }
        `;
    }
    
    // Continue with existing methods (enhanced versions)
    
    attachEventListeners() {
        // Toggle button
        const toggleBtn = document.getElementById('ai-assistant-toggle');
        toggleBtn?.addEventListener('click', () => this.toggle());
        
        // Close button
        const closeBtn = document.getElementById('ai-btn-close');
        closeBtn?.addEventListener('click', () => this.close());
        
        // Minimize button
        const minimizeBtn = document.getElementById('ai-btn-minimize');
        minimizeBtn?.addEventListener('click', () => this.minimize());
        
        // Initialize resize handle
        this.initializeResize();
        
        // Send button
        const sendBtn = document.getElementById('ai-send-btn');
        sendBtn?.addEventListener('click', () => this.sendMessage());
        
        // Chat input
        const chatInput = document.getElementById('ai-chat-input');
        if (chatInput) {
            chatInput.addEventListener('input', () => this.updateSendButton());
            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            // Enable drag and drop
            chatInput.addEventListener('dragover', (e) => {
                e.preventDefault();
                chatInput.style.background = 'rgba(139, 92, 246, 0.1)';
            });
            
            chatInput.addEventListener('dragleave', () => {
                chatInput.style.background = '';
            });
            
            chatInput.addEventListener('drop', (e) => {
                e.preventDefault();
                chatInput.style.background = '';
                
                if (e.dataTransfer.files.length > 0) {
                    this.handleFileDrop(e.dataTransfer.files);
                }
            });
        }
        
        // File button
        const fileBtn = document.getElementById('ai-file-btn');
        const fileInput = document.getElementById('ai-file-input');
        fileBtn?.addEventListener('click', () => fileInput?.click());
        fileInput?.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileDrop(e.target.files);
            }
        });
        
        // Clear files button
        const clearFilesBtn = document.getElementById('ai-clear-files');
        clearFilesBtn?.addEventListener('click', () => {
            this.stagedFiles = [];
            this.updateStagedFiles();
            this.updateSendButton();
        });
        
        // Suggestion items
        const suggestions = document.querySelectorAll('.ai-suggestions li');
        suggestions.forEach(suggestion => {
            suggestion.addEventListener('click', () => {
                const input = document.getElementById('ai-chat-input');
                if (input) {
                    input.value = suggestion.textContent.replace(/^[^\s]+\s/, '');
                    this.updateSendButton();
                }
            });
        });
    }
    
    // Existing method implementations with enhancements...
    
    setAnalysisMode(mode) {
        const fastBtn = document.getElementById('mode-fast');
        const deepBtn = document.getElementById('mode-deep');
        const modeInput = document.getElementById('analysis-mode');
        
        if (mode === 'fast') {
            fastBtn?.classList.add('mode-active');
            deepBtn?.classList.remove('mode-active');
            if (modeInput) modeInput.value = 'fast';
        } else {
            deepBtn?.classList.add('mode-active');
            fastBtn?.classList.remove('mode-active');
            if (modeInput) modeInput.value = 'deep';
        }
        
        this.agentState.analysisMode = mode;
    }
    
    async triggerAnalysis(mode = 'deep') {
        // Start tracking this operation
        const operationId = this.startOperation('analysis', `AI analysis (${mode} mode)`, { mode });
        
        this.saveState();
        this.addMessage(`🧠 Starting ${mode} AI analysis with GPT-5...`, 'assistant');
        
        const hideOverlay = this.showAgentWorking(`Triggering ${mode} analysis...`);
        
        try {
            // Find and click the analyze button
            const analyzeBtn = document.querySelector(`[data-mode="${mode}"]`);
            if (analyzeBtn) {
                this.simulateClick(analyzeBtn);
                
                // Wait for analysis to start
                await this.delay(1000);
                
                // Check if a job was started
                const jobIdMatch = document.body.textContent.match(/Job ID: ([\w-]+)/);
                if (jobIdMatch) {
                    const jobId = jobIdMatch[1];
                    await this.trackAnalysisJob(jobId);
                } else {
                    // Wait and hope for the best
                    await this.delay(3000);
                    this.addMessage('✅ Analysis triggered. Check Step 2 for results.', 'assistant');
                }
                // Complete the operation successfully
                this.completeOperation(operationId);
            } else {
                this.completeOperation(operationId);
                throw new Error('Analyze button not found');
            }
        } catch (error) {
            this.completeOperation(operationId);
            this.handleError(error, 'analysis', { mode });
        } finally {
            hideOverlay();
        }
    }
    
    async handleFileUpload(files) {
        if (files.length > 1) {
            // Batch processing
            await this.processFiles(files);
        } else {
            // Single file
            await this.handleSingleFile(files[0]);
        }
    }
    
    async handleSingleFile(file) {
        const fileExt = file.name.split('.').pop().toLowerCase();
        
        if (['pdf', 'docx', 'txt'].includes(fileExt)) {
            // Start tracking this operation
            const operationId = this.startOperation('file_upload', `Uploading ${file.name}`, { file: file.name });
            
            // Create task monitor
            const taskMonitor = this.createTaskMonitor();
            taskMonitor.addTask('Upload document', 'in_progress');
            taskMonitor.addTask('Click Analyze with AI button', 'pending');
            taskMonitor.addTask('Wait for AI analysis', 'pending');
            taskMonitor.addTask('Load deliverables', 'pending');
            taskMonitor.addTask('Select and calculate pricing', 'pending');
            
            this.addMessage(`📄 Setting "${file.name}" in main application...`, 'assistant');
            
            try {
                // Access parent window (main app)
                const parentWindow = window.parent || window;
                const parentDoc = parentWindow.document;
                
                // Find the main app's file input and analyze button
                const mainFileInput = parentDoc.querySelector('#rfpFile');
                const analyzeBtn = parentDoc.querySelector('#btnAnalyze');
                
                if (!mainFileInput || !analyzeBtn) {
                    // Fallback to API if UI elements not found
                    this.addMessage('⚠️ Could not find UI elements, using direct upload...', 'assistant');
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('mode', this.agentState.analysisMode || 'deep');
                    formData.append('tier', document.getElementById('gpt5-tier-selector')?.value || 'thinking-mini');
                    
                    const response = await this.retryWithBackoff(
                        () => fetch('/api/upload_rfp', {
                            method: 'POST',
                            body: formData
                        }),
                        3,
                        2000
                    );
                    
                    if (response.ok) {
                        const result = await response.json();
                        taskMonitor.updateTask(0, 'completed');
                        
                        if (result.job_id) {
                            this.agentState.jobId = result.job_id;
                            this.saveState();
                            this.addMessage(`✅ Document uploaded! Job ID: ${result.job_id}`, 'assistant');
                            await this.trackAnalysisJob(result.job_id, taskMonitor);
                        }
                    }
                    return;
                }
                
                // Alternative approach: First extract text from file, then put it in textarea
                this.addMessage('📄 Extracting text from PDF...', 'assistant');
                
                // Upload file to extract text
                const formData = new FormData();
                formData.append('files', file);
                formData.append('analyze_images', 'true');
                
                const extractResponse = await fetch('/api/summarize_by_file', {
                    method: 'POST',
                    body: formData
                });
                
                if (!extractResponse.ok) {
                    throw new Error('Failed to extract text from file');
                }
                
                const summary = await extractResponse.json();
                const extractedText = summary.summary_text || '';
                
                if (!extractedText) {
                    this.addMessage('⚠️ No text extracted from file. Trying visual upload...', 'assistant');
                    
                    // Fallback: Try to set file directly (may not work across contexts)
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    mainFileInput.files = dt.files;
                    mainFileInput.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    taskMonitor.updateTask(0, 'completed');
                    this.addMessage(`✅ Extracted ${extractedText.length} characters from PDF`, 'assistant');
                    
                    // Put extracted text into the textarea instead
                    const rfpTextArea = parentDoc.querySelector('#rfpText');
                    if (rfpTextArea) {
                        // Visual effect on textarea
                        this.flashElement(rfpTextArea);
                        
                        // Set the text
                        rfpTextArea.value = extractedText;
                        rfpTextArea.dispatchEvent(new Event('input', { bubbles: true }));
                        rfpTextArea.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        this.addMessage('📝 Text loaded into RFP content field', 'assistant');
                        
                        // Clear any file input to avoid confusion
                        if (mainFileInput.files.length === 0) {
                            // Good - no file conflict
                        } else {
                            mainFileInput.value = '';
                        }
                    }
                }
                
                // Update the file list display if it exists
                const fileListDisplay = parentDoc.querySelector('#selected-files-list');
                if (fileListDisplay) {
                    fileListDisplay.textContent = `Processing: ${file.name}`;
                    this.flashElement(fileListDisplay);
                }
                
                // Wait a moment for UI to update
                await this.delay(800);
                
                // Click the analyze button with visual effect
                taskMonitor.updateTask(1, 'in_progress');
                this.addMessage('🖱️ Clicking "Analyze with AI" button...', 'assistant');
                
                // Add visual click effect
                this.showClickAnimation(analyzeBtn);
                await this.delay(300);
                
                // Actually click the button
                analyzeBtn.click();
                taskMonitor.updateTask(1, 'completed');
                
                this.addMessage('✅ Analysis started! Watch the progress bar...', 'assistant');
                
                // Monitor for the progress bar
                taskMonitor.updateTask(2, 'in_progress');
                await this.monitorMainAppProgress(taskMonitor);
                
            } catch (error) {
                console.error('[CHARLES] Error in visual upload:', error);
                this.handleError(error, 'visual_upload');
                
                // Fallback to old method - wrap in its own try-catch
                try {
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('mode', this.agentState.analysisMode || 'deep');
                    formData.append('tier', document.getElementById('gpt5-tier-selector')?.value || 'thinking-mini');
                    
                    const response = await this.retryWithBackoff(
                        () => fetch('/api/upload_rfp', {
                            method: 'POST',
                            body: formData
                        }),
                        3,
                        2000
                    );
                    
                    if (response.ok) {
                        const result = await response.json();
                        taskMonitor.updateTask(0, 'completed');
                        taskMonitor.updateTask(1, 'completed');
                        
                        // Store the job ID for tracking
                        if (result.job_id) {
                            this.agentState.jobId = result.job_id;
                            this.saveState();
                            
                            taskMonitor.updateTask(2, 'in_progress');
                            this.addMessage(`✅ Document uploaded! Job ID: ${result.job_id}`, 'assistant');
                            this.addMessage(`🔍 Starting AI analysis...`, 'assistant');
                            
                            // Start tracking the analysis job
                            taskMonitor.updateTask(3, 'in_progress');
                            await this.trackAnalysisJob(result.job_id, taskMonitor);
                        } else {
                            // Fallback for older API responses
                            const rfpTextEl = document.getElementById('rfpText');
                            if (rfpTextEl && result.text) {
                                rfpTextEl.value = result.text;
                                rfpTextEl.dispatchEvent(new Event('input', { bubbles: true }));
                                rfpTextEl.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            
                            taskMonitor.updateTask(2, 'completed');
                            this.addMessage(`✅ Document processed. Text extracted: ${result.text_length || 0} chars`, 'assistant');
                        }
                        
                        // Store in agent state
                        this.agentState.uploadedFiles.push({
                            name: file.name,
                            timestamp: Date.now(),
                            text: result.text,
                            job_id: result.job_id
                        });
                        
                        this.saveState();
                        this.showSuccessMessage(`File "${file.name}" submitted for analysis!`);
                        
                    } else {
                        throw new Error(`Upload failed: ${response.statusText}`);
                    }
                } catch (fallbackError) {
                    taskMonitor.updateAllPending('failed');
                    this.handleError(fallbackError, 'file_upload', { file });
                }
            }
        } else if (fileExt === 'xlsx') {
            this.addMessage(`📊 Processing Excel configuration file "${file.name}"...`, 'assistant');
            this.addMessage('⚠️ Excel configuration upload not yet implemented.', 'assistant');
        } else {
            this.addMessage(`⚠️ Unsupported file type: .${fileExt}. Please upload PDF, DOCX, TXT, or XLSX files.`, 'assistant');
        }
    }
    
    handleFileDrop(files) {
        // Add files to staging area
        Array.from(files).forEach(file => {
            if (!this.stagedFiles.find(f => f.name === file.name)) {
                this.stagedFiles.push(file);
            }
        });
        
        this.updateStagedFiles();
        this.updateSendButton();
    }
    
    updateStagedFiles() {
        const stagingArea = document.getElementById('ai-file-staging');
        const stagedFilesDiv = document.getElementById('ai-staged-files');
        
        if (this.stagedFiles.length === 0) {
            stagingArea.style.display = 'none';
            return;
        }
        
        stagingArea.style.display = 'block';
        
        stagedFilesDiv.innerHTML = this.stagedFiles.map((file, index) => `
            <div class="ai-staged-file">
                <div class="ai-file-info">
                    <span>📄</span>
                    <span>${file.name}</span>
                    <span style="color: rgba(255,255,255,0.5); font-size: 11px;">(${(file.size / 1024).toFixed(1)} KB)</span>
                </div>
                <span class="ai-file-remove" onclick="window.aiAssistant.removeStagedFile(${index})">×</span>
            </div>
        `).join('');
    }
    
    removeStagedFile(index) {
        this.stagedFiles.splice(index, 1);
        this.updateStagedFiles();
        this.updateSendButton();
    }
    
    updateSendButton() {
        const sendBtn = document.getElementById('ai-send-btn');
        const input = document.getElementById('ai-chat-input');
        
        if (sendBtn) {
            const hasInput = input?.value?.trim().length > 0;
            const hasFiles = this.stagedFiles.length > 0;
            sendBtn.disabled = !hasInput && !hasFiles;
        }
    }
    
    // Continue with existing methods...
    
    toggle() {
        this.isOpen = !this.isOpen;
        const sidebar = document.querySelector('.ai-assistant-sidebar');
        if (sidebar) {
            sidebar.classList.toggle('open', this.isOpen);
        }
        
        if (this.isOpen && this.isMinimized) {
            this.isMinimized = false;
            sidebar.classList.remove('minimized');
        }
    }
    
    close() {
        this.isOpen = false;
        const sidebar = document.querySelector('.ai-assistant-sidebar');
        if (sidebar) {
            sidebar.classList.remove('open');
        }
    }
    
    minimize() {
        this.isMinimized = !this.isMinimized;
        const sidebar = document.querySelector('.ai-assistant-sidebar');
        if (sidebar) {
            sidebar.classList.toggle('minimized', this.isMinimized);
        }
    }
    
    initializeResize() {
        const container = document.getElementById('ai-assistant-container');
        const resizeHandle = document.querySelector('.ai-assistant-resize-handle');
        
        if (!resizeHandle || !container) return;
        
        // Style the resize handle
        resizeHandle.style.cssText = `
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 5px;
            cursor: ew-resize;
            background: transparent;
            z-index: 10;
        `;
        
        // Add hover effect
        resizeHandle.addEventListener('mouseenter', () => {
            resizeHandle.style.background = 'linear-gradient(90deg, #667eea, #764ba2)';
        });
        
        resizeHandle.addEventListener('mouseleave', () => {
            if (!this.isResizing) {
                resizeHandle.style.background = 'transparent';
            }
        });
        
        let startX = 0;
        let startWidth = 0;
        this.isResizing = false;
        
        const startResize = (e) => {
            e.preventDefault();
            this.isResizing = true;
            startX = e.clientX;
            startWidth = container.offsetWidth;
            
            // Add resizing class for visual feedback
            container.classList.add('resizing');
            resizeHandle.style.background = 'linear-gradient(90deg, #667eea, #764ba2)';
            
            // Prevent text selection during resize
            document.body.style.userSelect = 'none';
            document.body.style.cursor = 'ew-resize';
            
            document.addEventListener('mousemove', doResize);
            document.addEventListener('mouseup', stopResize);
        };
        
        const doResize = (e) => {
            if (!this.isResizing) return;
            
            // Calculate new width (resize from left edge)
            const diff = startX - e.clientX;
            let newWidth = startWidth + diff;
            
            // Apply min/max constraints
            newWidth = Math.max(350, Math.min(600, newWidth));
            
            // Apply new width
            container.style.width = `${newWidth}px`;
            
            // Save the width preference
            localStorage.setItem('charles_width', newWidth);
        };
        
        const stopResize = () => {
            this.isResizing = false;
            container.classList.remove('resizing');
            resizeHandle.style.background = 'transparent';
            
            // Reset cursor
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
            
            document.removeEventListener('mousemove', doResize);
            document.removeEventListener('mouseup', stopResize);
        };
        
        resizeHandle.addEventListener('mousedown', startResize);
        
        // Restore saved width
        const savedWidth = localStorage.getItem('charles_width');
        if (savedWidth) {
            container.style.width = `${savedWidth}px`;
        }
    }
    
    checkAgentStatus() {
        // Check if agent API is available
        fetch('/api/agent/status')
            .then(response => {
                const indicator = document.getElementById('ai-status-indicator');
                if (response.ok) {
                    indicator?.classList.remove('offline');
                } else {
                    indicator?.classList.add('offline');
                }
            })
            .catch(() => {
                const indicator = document.getElementById('ai-status-indicator');
                indicator?.classList.add('offline');
            });
    }
    
    async sendMessage() {
        const input = document.getElementById('ai-chat-input');
        const message = input.value.trim();
        
        // Check if we have staged files to process
        if (this.stagedFiles.length > 0) {
            // Add message if any
            if (message) {
                this.addMessage(message, 'user');
            } else {
                this.addMessage('📁 Submitting staged files...', 'user');
            }
            
            // Clear input
            input.value = '';
            this.updateSendButton();
            
            // Process staged files
            await this.handleFileUpload(this.stagedFiles);
            
            // Clear staging area
            this.stagedFiles = [];
            this.updateStagedFiles();
            
            return;
        }
        
        if (!message || this.isProcessing) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input and disable send button
        input.value = '';
        this.updateSendButton();
        
        // Check for direct commands
        if (this.isAnalysisCommand(message)) {
            const mode = message.toLowerCase().includes('deep') ? 'deep' : 'fast';
            await this.triggerAnalysis(mode);
            return;
        }
        
        if (this.isSubmissionCommand(message)) {
            await this.executeSubmission();
            return;
        }
        
        // Show processing state
        this.setProcessing(true);
        const typingId = this.addTypingIndicator();
        
        try {
            // Get current app context
            const context = this.getCurrentContext();
            
            // Get selected GPT-5 tier
            const gpt5TierSelector = document.getElementById('gpt5-tier-selector');
            const gpt5Tier = gpt5TierSelector ? gpt5TierSelector.value : 'auto';
            
            // Send message to AI agent with retry
            const response = await this.retryWithBackoff(
                () => fetch('/api/agent/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: message,
                        context: context,
                        session_id: this.sessionId,
                        gpt5_tier: gpt5Tier
                    })
                }),
                2,
                1000
            );
            
            const result = await response.json();
            
            // Remove typing indicator
            this.removeTypingIndicator(typingId);
            
            // Add AI response
            this.addMessage(result.message, 'assistant');
            
            // Execute actions if any
            if (result.success && result.actions && result.actions.length > 0) {
                await this.executeActions(result.actions);
            }
            
        } catch (error) {
            console.error('[CHARLES] Error:', error);
            this.removeTypingIndicator(typingId);
            this.handleError(error, 'chat', { message });
        } finally {
            this.setProcessing(false);
        }
    }
    
    isAnalysisCommand(message) {
        const lowerMessage = message.toLowerCase();
        const analysisKeywords = ['analyze', 'analysis', 'deep mode', 'fast mode', 'scan', 'evaluate'];
        return analysisKeywords.some(keyword => lowerMessage.includes(keyword));
    }
    
    isSubmissionCommand(message) {
        const lowerMessage = message.toLowerCase();
        const submitKeywords = ['submit', 'upload', 'process', 'send it', 'go ahead', 'do it'];
        return submitKeywords.some(keyword => lowerMessage.includes(keyword));
    }
    
    async executeSubmission() {
        // Check if we have RFP text
        const rfpTextEl = document.getElementById('rfpText');
        if (!rfpTextEl || !rfpTextEl.value) {
            this.addMessage('⚠️ No RFP document found. Please upload a document first.', 'assistant');
            return;
        }
        
        this.addMessage('🚀 Submitting document for analysis...', 'assistant');
        
        // Trigger analysis
        await this.triggerAnalysis('deep');
    }
    
    getCurrentContext() {
        // Gather current application state
        const context = {
            currentStep: this.detectCurrentStep(),
            hasRfp: !!document.getElementById('rfpText')?.value,
            hasAnalysis: !!window.SCENARIOS,
            hasScenarioA: !!window.SCENARIOS?.scenario_a,
            hasScenarioB: !!window.SCENARIOS?.scenario_b,
            selectedDeliverables: this.getSelectedDeliverables()
        };
        
        return context;
    }
    
    detectCurrentStep() {
        // Detect which step is currently visible/active
        const steps = ['step1', 'step2', 'step3', 'step4'];
        for (let step of steps) {
            const element = document.getElementById(step);
            if (element && element.offsetHeight > 0 && element.style.display !== 'none') {
                return step;
            }
        }
        return 'step1';
    }
    
    getSelectedDeliverables() {
        // Get list of currently selected deliverables
        const selected = [];
        document.querySelectorAll('input[type="checkbox"][data-deliverable]:checked').forEach(cb => {
            selected.push(cb.getAttribute('data-deliverable'));
        });
        return selected;
    }
    
    addMessage(content, sender) {
        const messagesContainer = document.getElementById('ai-chat-messages');
        
        // Remove welcome message if this is the first real message
        const welcome = messagesContainer.querySelector('.ai-welcome-message');
        if (welcome && messagesContainer.children.length === 1) {
            welcome.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-message ${sender}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'ai-message-avatar';
        avatar.textContent = sender === 'user' ? '👤' : '🤖';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'ai-message-content';
        contentDiv.textContent = content;
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        
        messagesContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    addTypingIndicator() {
        const messagesContainer = document.getElementById('ai-chat-messages');
        
        // Generate unique ID for this typing indicator
        const typingId = 'typing-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'ai-message assistant';
        typingDiv.id = typingId;
        
        const avatar = document.createElement('div');
        avatar.className = 'ai-message-avatar';
        avatar.textContent = '🤖';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'ai-message-content ai-message-typing';
        contentDiv.innerHTML = '<span></span><span></span><span></span>';
        
        typingDiv.appendChild(avatar);
        typingDiv.appendChild(contentDiv);
        
        messagesContainer.appendChild(typingDiv);
        
        // Track this indicator
        this.currentTypingIndicators.add(typingId);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        return typingId;
    }
    
    removeTypingIndicator(typingId) {
        if (!typingId) {
            // Remove all typing indicators if no ID specified
            this.currentTypingIndicators.forEach(id => {
                const indicator = document.getElementById(id);
                if (indicator) {
                    indicator.remove();
                }
            });
            this.currentTypingIndicators.clear();
        } else {
            // Remove specific typing indicator
            const indicator = document.getElementById(typingId);
            if (indicator) {
                indicator.remove();
                this.currentTypingIndicators.delete(typingId);
            }
        }
    }
    
    setProcessing(isProcessing) {
        this.isProcessing = isProcessing;
        const sendBtn = document.getElementById('ai-send-btn');
        
        if (isProcessing) {
            sendBtn.disabled = true;
            sendBtn.querySelector('.send-icon').style.display = 'none';
            sendBtn.querySelector('.loading-icon').style.display = 'block';
        } else {
            this.updateSendButton();
            sendBtn.querySelector('.send-icon').style.display = 'block';
            sendBtn.querySelector('.loading-icon').style.display = 'none';
        }
    }
    
    async executeActions(actions) {
        if (!actions || actions.length === 0) return;
        
        // Show action preview
        const preview = document.getElementById('ai-action-preview');
        const actionList = document.getElementById('ai-action-list');
        const actionCount = document.getElementById('ai-action-count');
        
        preview.style.display = 'block';
        actionList.innerHTML = '';
        
        // Add actions to preview
        actions.forEach((action, index) => {
            const item = document.createElement('div');
            item.className = 'ai-action-item';
            item.id = `action-${index}`;
            item.innerHTML = `<span>${this.getActionIcon(action.type)}</span> ${action.description || action.type}`;
            actionList.appendChild(item);
        });
        
        // Execute actions sequentially
        for (let i = 0; i < actions.length; i++) {
            const action = actions[i];
            const actionItem = document.getElementById(`action-${i}`);
            
            // Update count
            actionCount.textContent = `${i + 1}/${actions.length}`;
            
            // Mark as executing
            actionItem.classList.add('executing');
            
            try {
                await this.executeAction(action);
                
                // Mark as completed
                actionItem.classList.remove('executing');
                actionItem.classList.add('completed');
                
            } catch (error) {
                console.error(`[CHARLES] Action failed:`, error);
                actionItem.classList.remove('executing');
                actionItem.style.color = '#ef4444';
                this.handleError(error, 'ui_manipulation', { action });
            }
            
            // Delay between actions for visibility
            if (i < actions.length - 1) {
                await this.delay(this.executionDelay);
            }
        }
        
        // Hide preview after a delay
        setTimeout(() => {
            preview.style.display = 'none';
        }, 2000);
    }
    
    async executeAction(action) {
        console.log('[CHARLES] Executing action:', action);
        
        // Start tracking this UI action
        const operationId = this.startOperation('ui_action', `${action.type} action: ${action.description || action.target}`, { action });
        
        try {
            let result;
            switch (action.type) {
                case 'click':
                    result = await this.simulateClick(action.target);
                    break;
                    
                case 'fill':
                    result = await this.fillForm({ [action.target]: action.value });
                    break;
                    
                case 'select':
                    result = await this.executeSelect(action.target, action.value);
                    break;
                    
                case 'scroll':
                    result = await this.executeScroll(action.target, action.value);
                    break;
                
                case 'focus':
                    result = await this.executeFocus(action.target);
                    break;
                    
                case 'highlight':
                    result = await this.executeHighlight(action.target);
                    break;
                    
                case 'toggle':
                    result = await this.executeToggle(action.target);
                    break;
                    
                case 'check':
                    result = await this.selectCheckboxes([action.target], true);
                    break;
                    
                case 'uncheck':
                    result = await this.selectCheckboxes([action.target], false);
                    break;
                    
                case 'wait':
                    result = await this.delay(action.value || 500);
                    break;
                    
                case 'execute':
                    result = await this.executeCustom(action.target, action.value);
                    break;
                    
                case 'confirm':
                    // Auto-confirm for demonstration
                    result = await Promise.resolve(true);
                    break;
                    
                default:
                    console.warn('[CHARLES] Unknown action type:', action.type);
            }
            
            // Complete the operation successfully
            this.completeOperation(operationId);
            return result;
            
        } catch (error) {
            // Complete the operation with error
            this.completeOperation(operationId);
            console.error('[CHARLES] Action execution failed:', error);
            throw error;
        }
    }
    
    executeSelect(selector, value) {
        const element = document.querySelector(selector);
        if (element && element.tagName === 'SELECT') {
            this.flashElement(element);
            element.value = value;
            element.dispatchEvent(new Event('change', { bubbles: true }));
            return this.delay(200);
        } else {
            throw new Error(`Select element not found: ${selector}`);
        }
    }
    
    executeScroll(target, options) {
        if (target === 'window') {
            window.scrollTo({
                top: options?.top || 0,
                behavior: 'smooth'
            });
        } else {
            const element = document.querySelector(target);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
        return this.delay(500);
    }
    
    executeFocus(selector) {
        const element = document.querySelector(selector);
        if (element) {
            element.focus();
            this.flashElement(element);
            return this.delay(200);
        }
    }
    
    executeHighlight(selector) {
        const element = document.querySelector(selector);
        if (element) {
            this.flashElement(element, 2000);
            return this.delay(200);
        }
    }
    
    executeToggle(selector) {
        const element = document.querySelector(selector);
        if (element && element.type === 'checkbox') {
            element.checked = !element.checked;
            element.dispatchEvent(new Event('change', { bubbles: true }));
            this.flashElement(element);
            return this.delay(200);
        }
    }
    
    async executeCustom(functionName, params) {
        // Execute custom functions based on name
        switch (functionName) {
            case 'extendTimeline':
                console.log('[CHARLES] Extending timeline:', params);
                // Would call actual timeline extension function here
                break;
                
            case 'clearAllData':
                if (window.confirm('Are you sure you want to clear all data?')) {
                    if (typeof clearAllDataWithConfirmation === 'function') {
                        clearAllDataWithConfirmation();
                    }
                }
                break;
                
            case 'saveState':
                this.saveState();
                break;
                
            case 'restoreState':
                this.restoreState();
                break;
                
            default:
                console.warn('[CHARLES] Unknown custom function:', functionName);
        }
        
        return this.delay(500);
    }
    
    getActionIcon(type) {
        const icons = {
            'click': '👆',
            'fill': '✏️',
            'select': '📋',
            'scroll': '📜',
            'focus': '👁️',
            'highlight': '💡',
            'toggle': '🔄',
            'check': '☑️',
            'uncheck': '⬜',
            'wait': '⏰',
            'execute': '⚙️',
            'confirm': '✅'
        };
        
        return icons[type] || '▶️';
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize AI Assistant with improved loading mechanism
function initializeCharles() {
    try {
        console.log('[CHARLES] Starting initialization...');
        window.aiAssistant = new AIAssistant();
        console.log('[CHARLES] Agent v3.0 initialized with full autonomy, self-healing, and state preservation.');
        
        // Force toggle button to be visible if it exists
        setTimeout(() => {
            const toggleBtn = document.getElementById('ai-assistant-toggle');
            if (toggleBtn) {
                console.log('[CHARLES] Toggle button found, ensuring visibility...');
                toggleBtn.style.display = 'flex';
                toggleBtn.style.visibility = 'visible';
                toggleBtn.style.opacity = '1';
            } else {
                console.error('[CHARLES] Toggle button not found! Attempting to recreate...');
                // Fallback: Create a simple toggle button if the main one failed
                const fallbackBtn = document.createElement('button');
                fallbackBtn.id = 'ai-assistant-toggle-fallback';
                fallbackBtn.style.cssText = `
                    position: fixed;
                    right: 20px;
                    bottom: 20px;
                    z-index: 99999;
                    padding: 12px 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 600;
                    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                `;
                fallbackBtn.innerHTML = '🔮 CHARLES';
                fallbackBtn.onclick = () => {
                    if (window.aiAssistant) {
                        window.aiAssistant.toggle();
                    }
                };
                document.body.appendChild(fallbackBtn);
                console.log('[CHARLES] Created fallback toggle button');
            }
        }, 100);
    } catch (error) {
        console.error('[CHARLES] CRITICAL ERROR during initialization:', error);
        console.error('[CHARLES] Stack trace:', error.stack);
        
        // Create emergency toggle button
        const emergencyBtn = document.createElement('button');
        emergencyBtn.style.cssText = `
            position: fixed;
            right: 20px;
            bottom: 20px;
            z-index: 99999;
            padding: 12px 20px;
            background: red;
            color: white;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-weight: 600;
        `;
        emergencyBtn.innerHTML = '⚠️ CHARLES ERROR (Click to retry)';
        emergencyBtn.onclick = () => {
            location.reload();
        };
        document.body.appendChild(emergencyBtn);
    }
}

// Initialize based on document state
if (document.readyState === 'loading') {
    console.log('[CHARLES] Document still loading, waiting for DOMContentLoaded...');
    document.addEventListener('DOMContentLoaded', initializeCharles);
} else {
    console.log('[CHARLES] Document ready, initializing immediately...');
    initializeCharles();
}

// Export for global access
window.AIAssistant = AIAssistant;