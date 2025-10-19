/**
 * ChatGPT-Style Left Sidebar for CHARLES Agent
 * 
 * Features:
 * - Fixed left positioning
 * - Collapsible with hamburger menu
 * - Status bar with progress indicator
 * - Full chat functionality
 * - Smooth animations
 * - LocalStorage persistence
 */

class ChatGPTSidebar {
    constructor() {
        this.isExpanded = false;
        this.container = null;
        this.statusText = null;
        this.progressBar = null;
        this.chatSection = null;
        this.floatingToggle = null;
        this.initialized = false;
        
        // Initialize on page load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        if (this.initialized) return;
        
        this.createFloatingToggleButton();
        this.createSidebarHTML();
        this.attachEventListeners();
        this.restoreExpandedState();
        this.addStyles();
        
        this.initialized = true;
        
        // Expose globally for AIAssistant integration
        window.chatgptSidebar = this;
        
        console.log('[CHATGPT SIDEBAR] Initialized and exposed globally');
    }

    createFloatingToggleButton() {
        // Create the always-visible floating toggle button
        this.floatingToggle = document.createElement('button');
        this.floatingToggle.id = 'chatgpt-toggle-btn';
        this.floatingToggle.className = 'chatgpt-floating-toggle';
        this.floatingToggle.innerHTML = '<span class="vertical-bars">|||</span>';
        this.floatingToggle.title = 'Toggle ChatGPT Sidebar';
        
        // Add to body directly (not inside sidebar)
        document.body.appendChild(this.floatingToggle);
        
        console.log('[CHATGPT SIDEBAR] Floating toggle button created');
    }

    createSidebarHTML() {
        // Create main container
        this.container = document.createElement('div');
        this.container.id = 'chatgpt-sidebar';
        this.container.className = 'chatgpt-sidebar collapsed';
        
        this.container.innerHTML = `
            <!-- Status Bar (Top 10%) -->
            <div class="chatgpt-status-bar">
                <button class="chatgpt-hamburger" id="chatgpt-hamburger" title="Toggle sidebar">
                    ☰
                </button>
                <div class="chatgpt-status-content">
                    <div class="chatgpt-status-text" id="chatgpt-status-text">Ready</div>
                    <div class="chatgpt-progress-container" id="chatgpt-progress-container" style="display: none;">
                        <div class="chatgpt-progress-bar" id="chatgpt-progress-bar"></div>
                    </div>
                </div>
                <button class="chatgpt-close" id="chatgpt-close" title="Close sidebar">
                    ✕
                </button>
            </div>
            
            <!-- Chat Section (Bottom 90%) -->
            <div class="chatgpt-chat-section" id="chatgpt-chat-section">
                <div class="chatgpt-chat-header">
                    <div class="chatgpt-chat-title">
                        <span class="chatgpt-icon">🔮</span>
                        <span class="chatgpt-title-text">CHARLES AGENT</span>
                    </div>
                    <div class="chatgpt-version">ProBuFo v3.0</div>
                </div>
                
                <div class="chatgpt-gpt5-selector">
                    <label style="color:#8b5cf6;font-size:11px;font-weight:600;">GPT-5 Intelligence</label>
                    <select id="chatgpt-gpt5-tier" style="width:100%;padding:6px;background:#1a1a2e;color:white;border:1px solid #8b5cf6;border-radius:4px;margin-top:4px;font-size:12px;">
                        <option value="auto">🚀 Auto (Fast & Smart)</option>
                        <option value="mini">⚡ GPT-5 Mini (Fastest)</option>
                        <option value="thinking-mini">🧠 Thinking Mini (Balanced)</option>
                        <option value="thinking">💭 Thinking (Deep Analysis)</option>
                        <option value="pro">👑 Pro (Maximum Intelligence)</option>
                    </select>
                </div>
                
                <!-- State Management Controls -->
                <div class="chatgpt-state-controls">
                    <button class="chatgpt-btn-save" id="chatgpt-btn-save" title="Save State">💾</button>
                    <button class="chatgpt-btn-restore" id="chatgpt-btn-restore" title="Restore State">📂</button>
                </div>
                
                <!-- File Staging Area -->
                <div class="chatgpt-file-staging" id="chatgpt-file-staging" style="display: none;">
                    <div class="chatgpt-staging-header">
                        <span>📁 Files Ready</span>
                        <button class="chatgpt-clear-files" id="chatgpt-clear-files">×</button>
                    </div>
                    <div class="chatgpt-staged-files" id="chatgpt-staged-files"></div>
                </div>
                
                <!-- Chat Messages -->
                <div class="chatgpt-messages" id="chatgpt-messages">
                    <div class="chatgpt-welcome">
                        <h4>🔮 Welcome to CHARLES AGENT</h4>
                        <p style="font-style:italic;color:#8b5cf6;">Progressive Business Forecasting Oracle v3.0</p>
                        <p style="font-size:12px;margin-top:8px;">Enhanced with autonomous self-healing and state preservation.</p>
                        <div class="chatgpt-capabilities">
                            <p><strong>Capabilities:</strong></p>
                            <ul>
                                <li>🔄 Auto-recovery from errors</li>
                                <li>💾 Complete state preservation</li>
                                <li>📊 Real-time progress tracking</li>
                                <li>🎯 Enhanced UI manipulation</li>
                                <li>📁 Batch file processing</li>
                            </ul>
                        </div>
                        <div class="chatgpt-suggestions">
                            <p><strong>Try commands like:</strong></p>
                            <ul>
                                <li>"Analyze the RFP in deep mode"</li>
                                <li>"Set Creative Strategy to $10k monthly"</li>
                                <li>"Add 20% markup to all deliverables"</li>
                                <li>"Generate an optimized timeline"</li>
                                <li>"Export to Excel"</li>
                            </ul>
                        </div>
                    </div>
                </div>
                
                <!-- Action Preview -->
                <div class="chatgpt-action-preview" id="chatgpt-action-preview" style="display: none;">
                    <div class="chatgpt-action-header">
                        <span>📋 Executing Actions</span>
                        <span class="chatgpt-action-count" id="chatgpt-action-count">0/0</span>
                    </div>
                    <div class="chatgpt-action-list" id="chatgpt-action-list"></div>
                </div>
                
                <!-- Chat Input -->
                <div class="chatgpt-input-area">
                    <textarea 
                        id="chatgpt-input" 
                        placeholder="Type your command or drag & drop files..."
                        rows="2"
                        maxlength="500"
                    ></textarea>
                    <div class="chatgpt-input-controls">
                        <input type="file" id="chatgpt-file-input" accept=".pdf,.docx,.txt,.xlsx" multiple style="display:none;">
                        <button id="chatgpt-file-btn" class="chatgpt-file-btn" title="Upload Documents">📎</button>
                        <button id="chatgpt-send-btn" class="chatgpt-send-btn" disabled>
                            <span class="send-icon">➤</span>
                            <span class="loading-icon" style="display: none;">⏳</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.container);
        
        // Store references
        this.statusText = document.getElementById('chatgpt-status-text');
        this.progressBar = document.getElementById('chatgpt-progress-bar');
        this.progressContainer = document.getElementById('chatgpt-progress-container');
        this.chatSection = document.getElementById('chatgpt-chat-section');
    }

    attachEventListeners() {
        // Floating toggle button (always visible)
        if (this.floatingToggle) {
            this.floatingToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleSidebar();
            });
        }
        
        // Hamburger toggle (inside sidebar)
        const hamburger = document.getElementById('chatgpt-hamburger');
        if (hamburger) {
            hamburger.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleSidebar();
            });
        }
        
        // Close button
        const closeBtn = document.getElementById('chatgpt-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.collapse();
            });
        }
        
        // Click outside to close (exclude floating toggle button)
        document.addEventListener('click', (e) => {
            if (this.isExpanded && 
                !this.container.contains(e.target) &&
                e.target.id !== 'chatgpt-hamburger' &&
                e.target.id !== 'chatgpt-toggle-btn' &&
                !this.floatingToggle.contains(e.target)) {
                this.collapse();
            }
        });
        
        // State management buttons
        const saveBtn = document.getElementById('chatgpt-btn-save');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveState());
        }
        
        const restoreBtn = document.getElementById('chatgpt-btn-restore');
        if (restoreBtn) {
            restoreBtn.addEventListener('click', () => this.restoreState());
        }
        
        // Input handling
        const input = document.getElementById('chatgpt-input');
        const sendBtn = document.getElementById('chatgpt-send-btn');
        
        if (input) {
            input.addEventListener('input', () => {
                // Enable send button if there's text OR staged files
                if (sendBtn && window.aiAssistant) {
                    const hasInput = input.value.trim().length > 0;
                    const hasFiles = window.aiAssistant.stagedFiles?.length > 0;
                    sendBtn.disabled = !hasInput && !hasFiles;
                }
            });
            
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    // Allow sending if there's text OR staged files
                    const hasInput = input.value.trim().length > 0;
                    const hasFiles = window.aiAssistant?.stagedFiles?.length > 0;
                    if (hasInput || hasFiles) {
                        this.sendMessage();
                    }
                }
            });
        }
        
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }
        
        // File upload
        const fileBtn = document.getElementById('chatgpt-file-btn');
        const fileInput = document.getElementById('chatgpt-file-input');
        
        if (fileBtn && fileInput) {
            fileBtn.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        }
        
        // Drag and drop
        const inputArea = document.getElementById('chatgpt-input');
        if (inputArea) {
            inputArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                inputArea.style.borderColor = '#8b5cf6';
            });
            
            inputArea.addEventListener('dragleave', () => {
                inputArea.style.borderColor = '';
            });
            
            inputArea.addEventListener('drop', (e) => {
                e.preventDefault();
                inputArea.style.borderColor = '';
                this.handleFileDrop(e);
            });
        }
        
        // Sync GPT-5 selector with main AI assistant
        const gpt5Selector = document.getElementById('chatgpt-gpt5-tier');
        if (gpt5Selector) {
            gpt5Selector.addEventListener('change', (e) => {
                // Sync with main assistant if it exists
                const mainSelector = document.getElementById('gpt5-tier-selector');
                if (mainSelector) {
                    mainSelector.value = e.target.value;
                }
            });
        }
    }

    toggleSidebar() {
        if (this.isExpanded) {
            this.collapse();
        } else {
            this.expand();
        }
    }

    expand() {
        this.isExpanded = true;
        this.container.classList.remove('collapsed');
        this.container.classList.add('expanded');
        document.body.classList.add('chatgpt-sidebar-expanded');
        this.saveExpandedState(true);
        console.log('[CHATGPT SIDEBAR] Expanded');
    }

    collapse() {
        this.isExpanded = false;
        this.container.classList.remove('expanded');
        this.container.classList.add('collapsed');
        document.body.classList.remove('chatgpt-sidebar-expanded');
        this.saveExpandedState(false);
        console.log('[CHATGPT SIDEBAR] Collapsed');
    }

    updateStatus(text, showProgress = false, progress = 0) {
        if (this.statusText) {
            this.statusText.textContent = text;
        }
        
        if (this.progressContainer) {
            this.progressContainer.style.display = showProgress ? 'block' : 'none';
        }
        
        if (this.progressBar && showProgress) {
            this.progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
        }
    }

    sendMessage() {
        const input = document.getElementById('chatgpt-input');
        if (!input || !input.value.trim()) return;
        
        const message = input.value.trim();
        input.value = '';
        
        // Disable send button
        const sendBtn = document.getElementById('chatgpt-send-btn');
        if (sendBtn) sendBtn.disabled = true;
        
        // Forward to main AI assistant if it exists
        if (window.aiAssistant) {
            window.aiAssistant.handleUserMessage(message);
        } else {
            this.addMessage(message, 'user');
            this.addMessage('⚠️ AI Assistant not initialized. Please refresh the page.', 'assistant');
        }
    }

    addMessage(content, type = 'assistant') {
        const messagesDiv = document.getElementById('chatgpt-messages');
        if (!messagesDiv) return;
        
        const messageEl = document.createElement('div');
        messageEl.className = `chatgpt-message chatgpt-message-${type}`;
        messageEl.innerHTML = `
            <div class="chatgpt-message-content">${this.formatMessage(content)}</div>
        `;
        
        messagesDiv.appendChild(messageEl);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    formatMessage(content) {
        // Simple markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    handleFileUpload(event) {
        const files = Array.from(event.target.files);
        if (files.length === 0) return;
        
        // Forward to main AI assistant if it exists
        if (window.aiAssistant) {
            window.aiAssistant.handleFileUpload(files);
        } else {
            this.addMessage('⚠️ AI Assistant not initialized. Cannot upload files.', 'assistant');
        }
    }

    handleFileDrop(event) {
        const files = Array.from(event.dataTransfer.files);
        if (files.length === 0) return;
        
        // Forward to main AI assistant if it exists
        if (window.aiAssistant) {
            window.aiAssistant.handleFileUpload(files);
        } else {
            this.addMessage('⚠️ AI Assistant not initialized. Cannot upload files.', 'assistant');
        }
    }

    saveState() {
        if (window.aiAssistant) {
            window.aiAssistant.saveState();
            this.addMessage('✅ State saved successfully', 'assistant');
        }
    }

    restoreState() {
        if (window.aiAssistant) {
            window.aiAssistant.restoreState();
            this.addMessage('✅ State restored successfully', 'assistant');
        }
    }

    saveExpandedState(expanded) {
        localStorage.setItem('chatgpt_sidebar_expanded', expanded ? 'true' : 'false');
    }

    restoreExpandedState() {
        const expanded = localStorage.getItem('chatgpt_sidebar_expanded') === 'true';
        if (expanded) {
            this.expand();
        }
    }

    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Floating Toggle Button - Always Visible */
            .chatgpt-floating-toggle {
                position: fixed;
                top: 10px;
                left: 10px;
                z-index: 10000;
                width: 40px;
                height: 40px;
                background: rgba(32, 33, 35, 0.9);
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 2px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s ease;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            }

            .chatgpt-floating-toggle:hover {
                background: rgba(52, 53, 65, 0.95);
            }

            .chatgpt-floating-toggle:active {
                transform: scale(0.95);
            }

            .chatgpt-floating-toggle .vertical-bars {
                font-family: monospace;
                font-size: 16px;
                line-height: 1;
                letter-spacing: 2px;
            }

            /* ChatGPT Sidebar Container */
            .chatgpt-sidebar {
                position: fixed;
                left: 0;
                top: 0;
                height: 100vh;
                width: 280px;
                background: #202123;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 2px 0 10px rgba(0, 0, 0, 0.3);
            }

            .chatgpt-sidebar.collapsed {
                transform: translateX(-240px);
            }

            .chatgpt-sidebar.expanded {
                transform: translateX(0);
            }

            /* Status Bar (Top 10%) */
            .chatgpt-status-bar {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 12px;
                background: #343541;
                border-bottom: 1px solid #40414f;
                min-height: 50px;
                max-height: 50px;
                position: relative;
            }

            .chatgpt-hamburger,
            .chatgpt-close {
                background: transparent;
                border: none;
                color: #fff;
                font-size: 18px;
                cursor: pointer;
                padding: 6px 8px;
                border-radius: 4px;
                transition: all 0.2s;
                min-width: 32px;
            }

            .chatgpt-hamburger:hover,
            .chatgpt-close:hover {
                background: rgba(255, 255, 255, 0.1);
            }

            /* Button visibility based on state */
            .chatgpt-sidebar.collapsed .chatgpt-close {
                display: none;
            }

            .chatgpt-sidebar.collapsed .chatgpt-status-content {
                display: none;
            }

            .chatgpt-sidebar.collapsed .chatgpt-chat-section {
                display: none;
            }

            .chatgpt-sidebar.expanded .chatgpt-hamburger {
                display: none;
            }

            .chatgpt-status-content {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 4px;
            }

            .chatgpt-status-text {
                color: #fff;
                font-size: 13px;
                font-weight: 500;
                text-align: center;
            }

            .chatgpt-progress-container {
                width: 100%;
                height: 3px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
                overflow: hidden;
            }

            .chatgpt-progress-bar {
                height: 100%;
                background: #8b5cf6;
                transition: width 0.3s ease;
            }

            /* Chat Section (Bottom 90%) */
            .chatgpt-chat-section {
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                padding: 12px;
            }

            .chatgpt-chat-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 12px;
                padding-bottom: 8px;
                border-bottom: 1px solid #40414f;
            }

            .chatgpt-chat-title {
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .chatgpt-icon {
                font-size: 20px;
            }

            .chatgpt-title-text {
                color: #fff;
                font-weight: 600;
                font-size: 14px;
            }

            .chatgpt-version {
                color: #8b5cf6;
                font-size: 10px;
            }

            /* GPT-5 Selector */
            .chatgpt-gpt5-selector {
                margin-bottom: 10px;
            }

            /* State Controls */
            .chatgpt-state-controls {
                display: flex;
                gap: 6px;
                margin-bottom: 10px;
            }

            .chatgpt-btn-save,
            .chatgpt-btn-restore {
                flex: 1;
                background: #343541;
                border: 1px solid #565869;
                color: #fff;
                padding: 6px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
                transition: background 0.2s;
            }

            .chatgpt-btn-save:hover,
            .chatgpt-btn-restore:hover {
                background: #40414f;
            }

            /* File Staging */
            .chatgpt-file-staging {
                background: #343541;
                border-radius: 6px;
                padding: 8px;
                margin-bottom: 10px;
            }

            .chatgpt-staging-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                color: #fff;
                font-size: 12px;
                margin-bottom: 6px;
            }

            .chatgpt-clear-files {
                background: transparent;
                border: none;
                color: #fff;
                font-size: 16px;
                cursor: pointer;
                padding: 0 4px;
            }

            /* Messages */
            .chatgpt-messages {
                flex: 1;
                overflow-y: auto;
                margin-bottom: 10px;
                padding-right: 4px;
            }

            .chatgpt-messages::-webkit-scrollbar {
                width: 6px;
            }

            .chatgpt-messages::-webkit-scrollbar-thumb {
                background: #565869;
                border-radius: 3px;
            }

            .chatgpt-welcome {
                color: #fff;
                font-size: 12px;
            }

            .chatgpt-welcome h4 {
                margin: 0 0 8px 0;
                font-size: 14px;
            }

            .chatgpt-welcome p {
                margin: 4px 0;
            }

            .chatgpt-welcome ul {
                margin: 6px 0;
                padding-left: 20px;
            }

            .chatgpt-welcome li {
                margin: 3px 0;
            }

            .chatgpt-capabilities,
            .chatgpt-suggestions {
                margin-top: 12px;
            }

            .chatgpt-message {
                margin-bottom: 12px;
                padding: 8px 10px;
                border-radius: 6px;
                font-size: 13px;
                line-height: 1.5;
            }

            .chatgpt-message-user {
                background: #343541;
                color: #fff;
                margin-left: 20px;
            }

            .chatgpt-message-assistant {
                background: #40414f;
                color: #d1d5db;
            }

            /* Action Preview */
            .chatgpt-action-preview {
                background: #343541;
                border-radius: 6px;
                padding: 8px;
                margin-bottom: 10px;
            }

            .chatgpt-action-header {
                display: flex;
                justify-content: space-between;
                color: #fff;
                font-size: 12px;
                margin-bottom: 6px;
            }

            /* Input Area */
            .chatgpt-input-area {
                background: #343541;
                border-radius: 8px;
                padding: 8px;
                border: 1px solid #565869;
            }

            #chatgpt-input {
                width: 100%;
                background: transparent;
                border: none;
                color: #fff;
                resize: none;
                font-size: 13px;
                font-family: inherit;
                outline: none;
            }

            #chatgpt-input::placeholder {
                color: #8e8ea0;
            }

            .chatgpt-input-controls {
                display: flex;
                gap: 6px;
                margin-top: 6px;
                justify-content: flex-end;
            }

            .chatgpt-file-btn,
            .chatgpt-send-btn {
                background: #8b5cf6;
                border: none;
                color: #fff;
                padding: 6px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                transition: background 0.2s;
            }

            .chatgpt-file-btn:hover,
            .chatgpt-send-btn:hover {
                background: #7c3aed;
            }

            .chatgpt-send-btn:disabled {
                background: #565869;
                cursor: not-allowed;
            }

            /* Responsive */
            @media (max-width: 768px) {
                .chatgpt-sidebar {
                    width: 250px;
                }
                
                .chatgpt-sidebar.collapsed {
                    transform: translateX(-210px);
                }
            }
        `;
        document.head.appendChild(style);
    }

    // Public API for main AI assistant to use
    showProgress(text, progress) {
        this.updateStatus(text, true, progress);
    }

    hideProgress() {
        this.updateStatus('Ready', false, 0);
    }

    appendMessage(content, type) {
        this.addMessage(content, type);
    }
}

// Create global singleton instance (exposed in init() method to prevent race conditions)
if (!window.chatgptSidebar) {
    new ChatGPTSidebar();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.chatgptSidebar) {
        // Save state before unload
        if (window.chatgptSidebar.isExpanded) {
            window.chatgptSidebar.saveExpandedState(true);
        }
    }
});
