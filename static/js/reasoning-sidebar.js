/**
 * AI Reasoning Sidebar
 * 
 * Right-side collapsible panel that displays live AI thinking steps
 * during Deep Mode analysis. Features:
 * - Fixed right positioning, doesn't block main content
 * - Minimize/maximize button for user control
 * - Auto-hides on analysis completion
 * - Click-outside-to-close functionality
 * - Persists collapsed state in sessionStorage
 * - Real-time reasoning updates from backend
 */

class ReasoningSidebar {
    constructor() {
        this.container = null;
        this.logContainer = null;
        this.stageIndicator = null;
        this.progressBar = null;
        this.minimizeBtn = null;
        this.initialized = false;
        this.isMinimized = false;
        this.currentJobId = null;
        this.reasoningHistory = [];
        
        // Initialize on page load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        if (this.initialized) return;

        // Create main container
        this.container = document.createElement('div');
        this.container.id = 'ai-reasoning-sidebar';
        this.container.className = 'reasoning-sidebar';

        // Create header with minimize button
        const header = document.createElement('div');
        header.className = 'reasoning-sidebar-header';
        
        const title = document.createElement('div');
        title.className = 'reasoning-sidebar-title';
        title.innerHTML = '🧠 AI Thinking';
        
        this.minimizeBtn = document.createElement('button');
        this.minimizeBtn.className = 'reasoning-sidebar-minimize';
        this.minimizeBtn.innerHTML = '−';
        this.minimizeBtn.title = 'Minimize';
        this.minimizeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleMinimize();
        });
        
        header.appendChild(title);
        header.appendChild(this.minimizeBtn);

        // Create stage indicator
        this.stageIndicator = document.createElement('div');
        this.stageIndicator.className = 'reasoning-sidebar-stage';
        this.stageIndicator.textContent = 'Initializing...';

        // Create progress bar
        const progressContainer = document.createElement('div');
        progressContainer.className = 'reasoning-sidebar-progress-container';
        
        this.progressBar = document.createElement('div');
        this.progressBar.className = 'reasoning-sidebar-progress-bar';
        this.progressBar.style.width = '0%';
        
        progressContainer.appendChild(this.progressBar);

        // Create scrollable log container
        this.logContainer = document.createElement('div');
        this.logContainer.className = 'reasoning-sidebar-log';

        // Assemble components
        this.container.appendChild(header);
        this.container.appendChild(this.stageIndicator);
        this.container.appendChild(progressContainer);
        this.container.appendChild(this.logContainer);

        // Add to page
        document.body.appendChild(this.container);

        // Click outside to close
        document.addEventListener('click', (e) => {
            if (this.container.classList.contains('visible') && 
                !this.container.contains(e.target)) {
                this.hide();
            }
        });

        // Restore minimized state from session
        const wasMinimized = sessionStorage.getItem('reasoning-sidebar-minimized');
        if (wasMinimized === 'true') {
            this.isMinimized = true;
            this.container.classList.add('minimized');
        }

        this.initialized = true;
        console.log('[REASONING SIDEBAR] Initialized');
    }

    /**
     * Show sidebar and start new job tracking
     */
    show(jobId = null) {
        if (!this.initialized) this.init();

        // If new job, reset everything
        if (jobId && jobId !== this.currentJobId) {
            this.reset();
            this.currentJobId = jobId;
        }

        this.container.classList.add('visible');
        
        // Don't auto-expand if user previously minimized
        if (sessionStorage.getItem('reasoning-sidebar-minimized') !== 'true') {
            this.isMinimized = false;
            this.container.classList.remove('minimized');
        }

        console.log('[REASONING SIDEBAR] Shown for job:', jobId);
    }

    /**
     * Hide sidebar
     */
    hide() {
        if (!this.initialized) return;
        this.container.classList.remove('visible');
        console.log('[REASONING SIDEBAR] Hidden');
    }

    /**
     * Toggle minimize/maximize
     */
    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        
        if (this.isMinimized) {
            this.container.classList.add('minimized');
            this.minimizeBtn.innerHTML = '+';
            this.minimizeBtn.title = 'Maximize';
            sessionStorage.setItem('reasoning-sidebar-minimized', 'true');
        } else {
            this.container.classList.remove('minimized');
            this.minimizeBtn.innerHTML = '−';
            this.minimizeBtn.title = 'Minimize';
            sessionStorage.setItem('reasoning-sidebar-minimized', 'false');
        }

        console.log('[REASONING SIDEBAR] Minimized:', this.isMinimized);
    }

    /**
     * Update sidebar with new reasoning data
     */
    update(reasoning, stage = '', progress = 0, status = 'processing') {
        if (!this.initialized) this.init();

        // Update stage
        if (stage) {
            this.stageIndicator.textContent = stage;
        }

        // Update progress bar
        if (progress !== null && progress !== undefined) {
            this.progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
        }

        // Add new reasoning entry (avoid duplicates)
        if (reasoning && reasoning.trim()) {
            const lastEntry = this.reasoningHistory[this.reasoningHistory.length - 1];
            if (lastEntry !== reasoning) {
                this.reasoningHistory.push(reasoning);
                this.addLogEntry(reasoning);
            }
        }

        // Auto-hide on completion
        if (status === 'completed' || status === 'failed') {
            setTimeout(() => {
                this.hide();
                console.log('[REASONING SIDEBAR] Auto-hidden after completion');
            }, 3000);
        }
    }

    /**
     * Add a log entry to the display
     */
    addLogEntry(text) {
        const entry = document.createElement('div');
        entry.className = 'reasoning-sidebar-entry';
        
        const timestamp = document.createElement('span');
        timestamp.className = 'reasoning-sidebar-timestamp';
        timestamp.textContent = new Date().toLocaleTimeString();
        
        const message = document.createElement('span');
        message.className = 'reasoning-sidebar-message';
        message.textContent = text;
        
        entry.appendChild(timestamp);
        entry.appendChild(message);
        this.logContainer.appendChild(entry);

        // Auto-scroll to bottom
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
    }

    /**
     * Reset sidebar for new job
     */
    reset() {
        this.reasoningHistory = [];
        this.logContainer.innerHTML = '';
        this.stageIndicator.textContent = 'Initializing...';
        this.progressBar.style.width = '0%';
        this.currentJobId = null;
        console.log('[REASONING SIDEBAR] Reset');
    }

    /**
     * Cleanup on navigation away
     */
    destroy() {
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
        this.initialized = false;
        console.log('[REASONING SIDEBAR] Destroyed');
    }
}

// Create global singleton instance
window.reasoningSidebar = new ReasoningSidebar();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.reasoningSidebar) {
        window.reasoningSidebar.destroy();
    }
});
