/**
 * AI Assistant Chat Sidebar
 * Provides a collapsible chat interface for natural language UI control
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
        
        this.init();
    }
    
    generateSessionId() {
        return 'agent_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    init() {
        this.createSidebar();
        this.attachEventListeners();
        this.checkAgentStatus();
    }
    
    createSidebar() {
        // Create main container
        const container = document.createElement('div');
        container.id = 'ai-assistant-container';
        container.className = 'ai-assistant-container';
        container.innerHTML = `
            <div class="ai-assistant-sidebar ${this.isMinimized ? 'minimized' : ''}">
                <div class="ai-assistant-header">
                    <div class="ai-assistant-title">
                        <span class="ai-icon charles-sphere">🔮</span>
                        <span style="font-weight:700;">CHARLES AGENT</span>
                        <span style="font-size:10px;opacity:0.8;">ProBuFo</span>
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
                            <h4>🔮 Welcome to CHARLES AGENT: ProBuFo</h4>
                            <p style="font-style:italic;color:#8b5cf6;">Progressive Business Forecasting Oracle</p>
                            <p>Your pre-eminent executive project manager AI assistant for Agency Project Builder.</p>
                            <div class="ai-suggestions">
                                <p><strong>Try commands like:</strong></p>
                                <ul>
                                    <li>📄 "Analyze the RFP in deep mode"</li>
                                    <li>💰 "Set Creative Strategy to $10k monthly"</li>
                                    <li>📊 "Add 20% markup to all deliverables"</li>
                                    <li>📅 "Generate an optimized timeline"</li>
                                    <li>💾 "Export to Excel"</li>
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
        
        document.body.appendChild(container);
        
        // Add styles
        this.addStyles();
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
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
                width: 380px;
                height: 600px;
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
            
            .charles-sphere {
                display: inline-block;
                animation: rotateSphere 8s infinite linear;
                filter: drop-shadow(0 0 10px rgba(139, 92, 246, 0.8));
            }
            
            @keyframes rotateSphere {
                0% { transform: rotateY(0deg) rotateX(0deg); }
                25% { transform: rotateY(90deg) rotateX(15deg); }
                50% { transform: rotateY(180deg) rotateX(0deg); }
                75% { transform: rotateY(270deg) rotateX(-15deg); }
                100% { transform: rotateY(360deg) rotateX(0deg); }
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
                top: -5px;
                right: -5px;
                width: 20px;
                height: 20px;
                background: #ef4444;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                animation: bounce 2s infinite;
            }
            
            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-5px); }
            }
        `;
        
        document.head.appendChild(style);
    }
    
    attachEventListeners() {
        // Toggle button
        document.getElementById('ai-assistant-toggle').addEventListener('click', () => {
            this.toggle();
        });
        
        // Close button
        document.getElementById('ai-btn-close').addEventListener('click', () => {
            this.close();
        });
        
        // Minimize button
        document.getElementById('ai-btn-minimize').addEventListener('click', () => {
            this.toggleMinimize();
        });
        
        // Send button
        document.getElementById('ai-send-btn').addEventListener('click', () => {
            this.sendMessage();
        });
        
        // Input field - Enter to send
        document.getElementById('ai-chat-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Enable/disable send button based on input or staged files
        document.getElementById('ai-chat-input').addEventListener('input', (e) => {
            this.updateSendButton();
        });
        
        // Click on suggestions
        document.addEventListener('click', (e) => {
            if (e.target.closest('.ai-suggestions li')) {
                const command = e.target.textContent.replace(/^[^\s]+\s/, '').replace(/[""]/g, '');
                document.getElementById('ai-chat-input').value = command;
                this.updateSendButton();
            }
        });
        
        // File upload button
        document.getElementById('ai-file-btn').addEventListener('click', () => {
            document.getElementById('ai-file-input').click();
        });
        
        // File input change - support multiple files
        document.getElementById('ai-file-input').addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            if (files.length > 0) {
                this.stageFiles(files);
            }
            // Reset file input to allow same files to be selected again
            e.target.value = '';
        });
        
        // Clear staged files button
        document.getElementById('ai-clear-files').addEventListener('click', () => {
            this.clearStagedFiles();
        });
        
        // Drag and drop support for files
        const chatInput = document.getElementById('ai-chat-input');
        chatInput.addEventListener('dragover', (e) => {
            e.preventDefault();
            chatInput.style.background = 'rgba(139, 92, 246, 0.1)';
            chatInput.placeholder = '📥 Drop files here...';
        });
        
        chatInput.addEventListener('dragleave', (e) => {
            e.preventDefault();
            chatInput.style.background = '';
            chatInput.placeholder = 'Type your command or drag & drop files here...';
        });
        
        chatInput.addEventListener('drop', (e) => {
            e.preventDefault();
            chatInput.style.background = '';
            chatInput.placeholder = 'Type your command or drag & drop files here...';
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                this.stageFiles(files);
            }
        });
    }
    
    stageFiles(files) {
        // Add files to staging area
        files.forEach(file => {
            // Check if file already staged
            if (!this.stagedFiles.find(f => f.name === file.name)) {
                this.stagedFiles.push(file);
            }
        });
        
        this.updateFileStaging();
        this.updateSendButton();
    }
    
    updateFileStaging() {
        const stagingArea = document.getElementById('ai-file-staging');
        const stagedFilesList = document.getElementById('ai-staged-files');
        
        if (this.stagedFiles.length === 0) {
            stagingArea.style.display = 'none';
            stagedFilesList.innerHTML = '';
            return;
        }
        
        stagingArea.style.display = 'block';
        stagedFilesList.innerHTML = '';
        
        this.stagedFiles.forEach((file, index) => {
            const fileDiv = document.createElement('div');
            fileDiv.className = 'ai-staged-file';
            
            const fileIcon = this.getFileIcon(file.name);
            const fileSize = (file.size / 1024).toFixed(1) + ' KB';
            
            fileDiv.innerHTML = `
                <div class="ai-file-info">
                    <span>${fileIcon}</span>
                    <span>${file.name}</span>
                    <span style="color: #666; font-size: 11px;">(${fileSize})</span>
                </div>
                <span class="ai-file-remove" data-index="${index}">×</span>
            `;
            
            // Add click handler for remove button
            fileDiv.querySelector('.ai-file-remove').addEventListener('click', (e) => {
                this.removestagedFile(parseInt(e.target.dataset.index));
            });
            
            stagedFilesList.appendChild(fileDiv);
        });
    }
    
    removestagedFile(index) {
        this.stagedFiles.splice(index, 1);
        this.updateFileStaging();
        this.updateSendButton();
    }
    
    clearStagedFiles() {
        this.stagedFiles = [];
        this.updateFileStaging();
        this.updateSendButton();
    }
    
    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const icons = {
            'pdf': '📄',
            'docx': '📝',
            'doc': '📝',
            'txt': '📃',
            'xlsx': '📊',
            'xls': '📊'
        };
        return icons[ext] || '📎';
    }
    
    updateSendButton() {
        const sendBtn = document.getElementById('ai-send-btn');
        const input = document.getElementById('ai-chat-input');
        
        // Enable if there's text or staged files, and not processing
        const hasContent = input.value.trim() || this.stagedFiles.length > 0;
        sendBtn.disabled = !hasContent || this.isProcessing;
    }
    
    async checkAgentStatus() {
        try {
            const response = await fetch('/api/agent/status');
            const status = await response.json();
            
            const indicator = document.getElementById('ai-status-indicator');
            if (status.available) {
                indicator.classList.remove('offline');
                indicator.title = 'AI Agent Online';
            } else {
                indicator.classList.add('offline');
                indicator.title = 'AI Agent Offline';
            }
        } catch (error) {
            console.error('[AI Assistant] Status check failed:', error);
            const indicator = document.getElementById('ai-status-indicator');
            indicator.classList.add('offline');
            indicator.title = 'AI Agent Connection Error';
        }
    }
    
    toggle() {
        this.isOpen = !this.isOpen;
        const sidebar = document.querySelector('.ai-assistant-sidebar');
        
        if (this.isOpen) {
            sidebar.classList.add('open');
            document.getElementById('ai-chat-input').focus();
        } else {
            sidebar.classList.remove('open');
        }
    }
    
    open() {
        this.isOpen = true;
        const sidebar = document.querySelector('.ai-assistant-sidebar');
        sidebar.classList.add('open');
        document.getElementById('ai-chat-input').focus();
    }
    
    close() {
        this.isOpen = false;
        const sidebar = document.querySelector('.ai-assistant-sidebar');
        sidebar.classList.remove('open');
    }
    
    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        const sidebar = document.querySelector('.ai-assistant-sidebar');
        
        if (this.isMinimized) {
            sidebar.classList.add('minimized');
        } else {
            sidebar.classList.remove('minimized');
        }
    }
    
    async handleFileUpload(files) {
        // Handle single file for backward compatibility
        if (!Array.isArray(files)) {
            files = [files];
        }
        
        // Process staged files if any
        if (this.stagedFiles.length > 0) {
            for (const file of this.stagedFiles) {
                await this.processFile(file);
            }
            this.clearStagedFiles();
        }
        // Or process directly passed files
        else {
            for (const file of files) {
                await this.processFile(file);
            }
        }
    }
    
    async processFile(file) {
        // Show file info in chat
        this.addMessage(`📎 Processing: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`, 'user');
        
        // Check file type
        const fileExt = file.name.split('.').pop().toLowerCase();
        
        if (['pdf', 'docx', 'txt'].includes(fileExt)) {
            // This is likely an RFP document
            this.addMessage(`🔍 Analyzing document "${file.name}" as RFP...`, 'assistant');
            
            // Create typing indicator with unique ID
            const typingId = this.addTypingIndicator();
            
            // Upload the file to Step 1
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                // Create timeout wrapper
                const uploadWithTimeout = this.withTimeout(
                    fetch('/api/upload_rfp', {
                        method: 'POST',
                        body: formData
                    }),
                    this.apiTimeout
                );
                
                const uploadResponse = await uploadWithTimeout;
                
                if (uploadResponse.ok) {
                    const result = await uploadResponse.json();
                    
                    // Remove typing indicator
                    this.removeTypingIndicator(typingId);
                    
                    this.addMessage(`✅ RFP uploaded successfully! Extracted ${result.text_length || 0} characters.`, 'assistant');
                    
                    // Store the text for Step 1
                    if (result.text) {
                        const rfpTextEl = document.getElementById('rfpText');
                        if (rfpTextEl) {
                            rfpTextEl.value = result.text;
                        }
                        sessionStorage.setItem('rfp_text', result.text);
                    }
                    
                    // Auto-trigger analysis if not already started
                    if (result.job_id && result.analysis_started) {
                        this.addMessage(`🧠 AI analysis started (Job ID: ${result.job_id}). Tracking progress...`, 'assistant');
                        await this.trackAnalysisJob(result.job_id);
                    } else {
                        // Manually trigger deep analysis
                        await this.triggerAnalysis('deep');
                    }
                } else {
                    this.removeTypingIndicator(typingId);
                    this.addMessage(`❌ Failed to upload file. Server returned: ${uploadResponse.status}`, 'assistant');
                }
            } catch (error) {
                // Always remove typing indicator on error
                this.removeTypingIndicator(typingId);
                
                if (error.name === 'TimeoutError') {
                    this.addMessage(`⏱️ Upload timed out. The file may be too large or the server is slow.`, 'assistant');
                } else {
                    console.error('[CHARLES] File upload error:', error);
                    this.addMessage(`❌ Error uploading file: ${error.message}`, 'assistant');
                }
            }
        } else if (fileExt === 'xlsx') {
            // Excel file - likely configuration
            this.addMessage(`📊 Processing Excel configuration file "${file.name}"...`, 'assistant');
            this.addMessage('⚠️ Excel configuration upload not yet implemented.', 'assistant');
        } else {
            this.addMessage(`⚠️ Unsupported file type: .${fileExt}. Please upload PDF, DOCX, TXT, or XLSX files.`, 'assistant');
        }
    }
    
    async triggerAnalysis(mode = 'deep') {
        this.addMessage(`🧠 Starting ${mode} AI analysis with GPT-5...`, 'assistant');
        
        const typingId = this.addTypingIndicator();
        
        try {
            // Find and click the analyze button
            const analyzeBtn = document.querySelector(`[data-mode="${mode}"]`);
            if (analyzeBtn) {
                analyzeBtn.click();
                
                // Wait a moment for the analysis to start
                await this.delay(1000);
                
                // Check if a job was started by looking for job tracking
                const jobIdMatch = document.body.textContent.match(/Job ID: ([\w-]+)/);
                if (jobIdMatch) {
                    const jobId = jobIdMatch[1];
                    this.removeTypingIndicator(typingId);
                    await this.trackAnalysisJob(jobId);
                } else {
                    // Just wait and hope for the best
                    await this.delay(3000);
                    this.removeTypingIndicator(typingId);
                    this.addMessage('✅ Analysis triggered. Check Step 2 for results.', 'assistant');
                }
            } else {
                this.removeTypingIndicator(typingId);
                this.addMessage('❌ Could not find analyze button. Please trigger analysis manually.', 'assistant');
            }
        } catch (error) {
            this.removeTypingIndicator(typingId);
            this.addMessage(`❌ Failed to trigger analysis: ${error.message}`, 'assistant');
        }
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
            return;
        }
        
        if (!message || this.isProcessing) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input and disable send button
        input.value = '';
        this.updateSendButton();
        
        // Check for direct submission commands
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
            
            // Send message to AI agent with GPT-5 tier and timeout
            const responsePromise = fetch('/api/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    context: context,
                    session_id: this.sessionId,
                    gpt5_tier: gpt5Tier
                })
            });
            
            const response = await this.withTimeout(responsePromise, this.apiTimeout);
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
            console.error('[AI Assistant] Error:', error);
            this.removeTypingIndicator(typingId);
            
            if (error.name === 'TimeoutError') {
                this.addMessage('⏱️ Request timed out. Please try again with a simpler command.', 'assistant');
            } else {
                this.addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
            }
        } finally {
            this.setProcessing(false);
        }
    }
    
    isSubmissionCommand(message) {
        const lowerMessage = message.toLowerCase();
        const submitKeywords = ['submit', 'upload', 'analyze', 'process', 'send it', 'go ahead', 'do it'];
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
            if (element && element.offsetHeight > 0) {
                const rect = element.getBoundingClientRect();
                if (rect.top >= 0 && rect.top < window.innerHeight) {
                    return step;
                }
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
                console.error(`[AI Assistant] Action failed:`, error);
                actionItem.classList.remove('executing');
                actionItem.style.color = '#ef4444';
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
        console.log('[AI Assistant] Executing action:', action);
        
        switch (action.type) {
            case 'click':
                return this.executeClick(action.target);
                
            case 'fill':
                return this.executeFill(action.target, action.value);
                
            case 'select':
                return this.executeSelect(action.target, action.value);
                
            case 'scroll':
                return this.executeScroll(action.target, action.value);
                
            case 'focus':
                return this.executeFocus(action.target);
                
            case 'highlight':
                return this.executeHighlight(action.target);
                
            case 'toggle':
                return this.executeToggle(action.target);
                
            case 'check':
                return this.executeCheck(action.target, true);
                
            case 'uncheck':
                return this.executeCheck(action.target, false);
                
            case 'wait':
                return this.delay(action.value || 500);
                
            case 'execute':
                return this.executeCustom(action.target, action.value);
                
            case 'confirm':
                // Auto-confirm for demonstration
                return Promise.resolve(true);
                
            default:
                console.warn('[AI Assistant] Unknown action type:', action.type);
        }
    }
    
    executeClick(selector) {
        const element = document.querySelector(selector);
        if (element) {
            // Highlight briefly
            this.flashElement(element);
            
            // Trigger click
            element.click();
            
            // Also trigger change event for some elements
            if (element.tagName === 'INPUT' || element.tagName === 'SELECT') {
                element.dispatchEvent(new Event('change', { bubbles: true }));
            }
            
            return this.delay(200);
        } else {
            throw new Error(`Element not found: ${selector}`);
        }
    }
    
    executeFill(selector, value) {
        const element = document.querySelector(selector);
        if (element) {
            // Highlight briefly
            this.flashElement(element);
            
            // Set value
            element.value = value;
            
            // Trigger events
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
            
            return this.delay(200);
        } else {
            throw new Error(`Element not found: ${selector}`);
        }
    }
    
    executeSelect(selector, value) {
        const element = document.querySelector(selector);
        if (element && element.tagName === 'SELECT') {
            // Highlight briefly
            this.flashElement(element);
            
            // Set value
            element.value = value;
            
            // Trigger change event
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
    
    executeCheck(selector, checked) {
        const element = document.querySelector(selector);
        if (element && element.type === 'checkbox') {
            element.checked = checked;
            element.dispatchEvent(new Event('change', { bubbles: true }));
            this.flashElement(element);
            return this.delay(200);
        }
    }
    
    async executeCustom(functionName, params) {
        // Execute custom functions based on name
        switch (functionName) {
            case 'extendTimeline':
                // Custom timeline extension logic
                console.log('[AI Assistant] Extending timeline:', params);
                // Would call actual timeline extension function here
                break;
                
            case 'clearAllData':
                // Custom data clearing with confirmation
                if (window.confirm('Are you sure you want to clear all data?')) {
                    if (typeof clearAllDataWithConfirmation === 'function') {
                        clearAllDataWithConfirmation();
                    }
                }
                break;
                
            default:
                console.warn('[AI Assistant] Unknown custom function:', functionName);
        }
        
        return this.delay(500);
    }
    
    flashElement(element, duration = 500) {
        const originalBorder = element.style.border;
        const originalBoxShadow = element.style.boxShadow;
        
        element.style.border = '2px solid #667eea';
        element.style.boxShadow = '0 0 10px rgba(139, 92, 246, 0.5)';
        element.style.transition = 'all 0.2s';
        
        setTimeout(() => {
            element.style.border = originalBorder;
            element.style.boxShadow = originalBoxShadow;
        }, duration);
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
    
    // Helper function to add timeout to promises
    withTimeout(promise, timeout) {
        return Promise.race([
            promise,
            new Promise((_, reject) => 
                setTimeout(() => {
                    const error = new Error(`Operation timed out after ${timeout}ms`);
                    error.name = 'TimeoutError';
                    reject(error);
                }, timeout)
            )
        ]);
    }
    
    async trackAnalysisJob(jobId) {
        let pollInterval;
        let pollCount = 0;
        const maxPolls = 60; // Max 60 polls (2 minutes at 2-second intervals)
        
        const typingId = this.addTypingIndicator();
        
        const cleanup = () => {
            if (pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
            }
            this.removeTypingIndicator(typingId);
        };
        
        pollInterval = setInterval(async () => {
            try {
                pollCount++;
                
                // Check if we've exceeded max polls
                if (pollCount > maxPolls) {
                    cleanup();
                    this.addMessage('⏱️ Analysis is taking longer than expected. It may still be processing in the background.', 'assistant');
                    return;
                }
                
                const response = await this.withTimeout(
                    fetch(`/api/agencydb/status/${jobId}`),
                    5000 // 5 second timeout for status checks
                );
                
                if (response.ok) {
                    const status = await response.json();
                    
                    if (status.status === 'completed') {
                        cleanup();
                        this.addMessage('✅ Analysis complete! Results loaded in Step 2.', 'assistant');
                        
                        // Trigger any UI updates
                        if (typeof window.loadScenarioData === 'function' && status.result) {
                            window.loadScenarioData(status.result);
                        }
                    } else if (status.status === 'failed') {
                        cleanup();
                        this.addMessage(`❌ Analysis failed: ${status.error || 'Unknown error'}`, 'assistant');
                    } else if (status.progress) {
                        // Update progress message
                        console.log(`[CHARLES] Job ${jobId} progress: ${status.progress}%`);
                    }
                } else {
                    // Non-OK response
                    cleanup();
                    this.addMessage('⚠️ Could not check analysis status. It may still be running.', 'assistant');
                }
            } catch (error) {
                cleanup();
                
                if (error.name === 'TimeoutError') {
                    this.addMessage('⏱️ Status check timed out. Analysis may still be running in the background.', 'assistant');
                } else {
                    console.error('[CHARLES] Job tracking error:', error);
                    this.addMessage('⚠️ Lost connection to analysis job. Check Step 2 for results.', 'assistant');
                }
            }
        }, 2000); // Poll every 2 seconds
    }
}

// Initialize the AI Assistant when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.aiAssistant = new AIAssistant();
    });
} else {
    // DOM is already ready
    window.aiAssistant = new AIAssistant();
}