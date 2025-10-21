/**
 * File Staging Module - Replit-Style File Upload UI
 * 
 * Handles:
 * - File upload staging (no text extraction)
 * - Replit-style file cards display
 */

(function() {
    'use strict';

    console.log('[FILE STAGING] Module loading...');

    // Module state
    const state = {
        sessionId: null,
        stagedFiles: []
    };

    // DOM elements (initialized on DOMContentLoaded)
    let elements = {
        fileInput: null,
        fileCardsContainer: null
    };

    /**
     * Initialize the file staging module
     */
    function init() {
        // Idempotent guard - prevent double initialization
        if (window.__fileStagingInitDone) {
            console.log('[FILE STAGING] Already initialized, skipping');
            return;
        }

        console.log('[FILE STAGING] Initializing...');

        // Get or create session ID
        state.sessionId = localStorage.getItem('apb.currentSession') || generateSessionId();
        localStorage.setItem('apb.currentSession', state.sessionId);

        // Get DOM elements
        elements.fileInput = document.getElementById('rfpFile');
        elements.fileCardsContainer = document.getElementById('file-cards-container');

        if (!elements.fileInput) {
            console.error('[FILE STAGING] File input #rfpFile not found - will retry');
            return;
        }

        if (!elements.fileCardsContainer) {
            console.error('[FILE STAGING] File cards container #file-cards-container not found - will retry');
            return;
        }

        // Attach event listeners
        setupEventListeners();

        // Load any previously staged files for this session
        loadStagedFiles();

        // Mark as initialized
        window.__fileStagingInitDone = true;
        console.log('[FILE STAGING] Initialized successfully');
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // File input change handler
        elements.fileInput.addEventListener('change', handleFileInputChange);

        // Prevent old app.js handlers from running
        elements.fileInput.dataset.fileStagingActive = 'true';
    }

    /**
     * Handle file input change
     */
    async function handleFileInputChange(e) {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        console.log('[FILE STAGING] Files selected:', files.length);

        // Upload each file
        for (const file of files) {
            await uploadFile(file);
        }

        // Clear the input so the same file can be selected again
        e.target.value = '';
    }

    /**
     * Upload a file to the staging API
     */
    async function uploadFile(file) {
        console.log('[FILE STAGING] Uploading file:', file.name);

        // Create temporary card with loading state
        const tempFileId = 'temp_' + Date.now();
        const tempFile = {
            file_id: tempFileId,
            filename: file.name,
            size: file.size,
            uploading: true
        };
        
        state.stagedFiles.push(tempFile);
        renderFileCards();

        try {
            // Prepare FormData
            const formData = new FormData();
            formData.append('files', file);
            formData.append('session_id', state.sessionId);

            // POST to staging API
            const response = await fetch('/api/stage/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();
            console.log('[FILE STAGING] Upload successful:', result);

            // Replace temp file with real file data
            const index = state.stagedFiles.findIndex(f => f.file_id === tempFileId);
            if (index !== -1) {
                state.stagedFiles[index] = {
                    file_id: result.file_id || result.files?.[0]?.file_id,
                    filename: file.name,
                    size: file.size,
                    uploading: false
                };
            }

            renderFileCards();

        } catch (error) {
            console.error('[FILE STAGING] Upload error:', error);
            
            // Remove the temp file
            state.stagedFiles = state.stagedFiles.filter(f => f.file_id !== tempFileId);
            renderFileCards();

            alert(`Failed to upload ${file.name}: ${error.message}`);
        }
    }

    /**
     * Remove a staged file
     */
    async function removeFile(fileId) {
        console.log('[FILE STAGING] Removing file:', fileId);

        try {
            // Call DELETE API
            const response = await fetch(`/api/stage/file/${fileId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                console.warn('[FILE STAGING] Delete API returned:', response.status);
            }

            // Remove from state regardless of API response
            state.stagedFiles = state.stagedFiles.filter(f => f.file_id !== fileId);
            renderFileCards();

        } catch (error) {
            console.error('[FILE STAGING] Delete error:', error);
            // Still remove from UI
            state.stagedFiles = state.stagedFiles.filter(f => f.file_id !== fileId);
            renderFileCards();
        }
    }

    /**
     * Render file cards in the container
     */
    function renderFileCards() {
        if (!elements.fileCardsContainer) return;

        if (state.stagedFiles.length === 0) {
            elements.fileCardsContainer.innerHTML = '';
            elements.fileCardsContainer.style.display = 'none';
            return;
        }

        elements.fileCardsContainer.style.display = 'grid';

        const html = state.stagedFiles.map(file => {
            const icon = getFileIcon(file.filename);
            const size = formatFileSize(file.size);
            const isUploading = file.uploading;

            return `
                <div class="file-card ${isUploading ? 'uploading' : ''}" data-file-id="${file.file_id}">
                    <div class="file-card-icon">${icon}</div>
                    <div class="file-card-info">
                        <div class="file-card-name" title="${escapeHtml(file.filename)}">${escapeHtml(file.filename)}</div>
                        <div class="file-card-size">${size}</div>
                    </div>
                    ${isUploading ? `
                        <div class="file-card-spinner">
                            <div class="spinner"></div>
                        </div>
                    ` : `
                        <button class="file-card-remove" onclick="window.FileStagingModule.removeFile('${file.file_id}')" title="Remove file">
                            ×
                        </button>
                    `}
                </div>
            `;
        }).join('');

        elements.fileCardsContainer.innerHTML = html;
    }

    /**
     * Get file icon based on extension
     */
    function getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        switch (ext) {
            case 'pdf':
                return '📄';
            case 'docx':
            case 'doc':
                return '📝';
            case 'txt':
            case 'md':
                return '📃';
            default:
                return '📎';
        }
    }

    /**
     * Format file size for display
     */
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Load staged files from session (if API supports it)
     */
    async function loadStagedFiles() {
        // This would call GET /api/stage/files?session_id={sessionId}
        // For now, we start with empty state
        console.log('[FILE STAGING] Session:', state.sessionId);
    }

    /**
     * Generate session ID
     */
    function generateSessionId() {
        if (typeof crypto !== 'undefined' && crypto.randomUUID) {
            return crypto.randomUUID();
        }
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    // Multi-strategy initialization to bypass listener interference
    function tryInit() {
        const readyState = document.readyState;
        console.log('[FILE STAGING] tryInit called, readyState:', readyState);
        
        if (window.__fileStagingInitDone) {
            console.log('[FILE STAGING] Already initialized, skipping');
            return;
        }
        
        // Check if DOM is ready AND required elements exist
        if (readyState === 'complete' || readyState === 'interactive') {
            const hasElements = document.getElementById('rfpFile') && document.getElementById('file-cards-container');
            console.log('[FILE STAGING] DOM ready, elements exist:', hasElements);
            
            if (hasElements) {
                init();
            }
        }
    }

    // Strategy 1: Immediate if DOM is ready
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        console.log('[FILE STAGING] DOM already ready, initializing immediately');
        tryInit();
    } else {
        console.log('[FILE STAGING] DOM not ready, starting watchdog');
        
        // Strategy 2: Bounded polling watchdog (every 250ms, max 10s)
        let watchdogAttempts = 0;
        const maxAttempts = 40; // 10 seconds / 250ms
        const watchdog = setInterval(() => {
            watchdogAttempts++;
            console.log('[FILE STAGING] Watchdog attempt', watchdogAttempts, '/', maxAttempts);
            
            if (window.__fileStagingInitDone) {
                console.log('[FILE STAGING] Initialized by other strategy, stopping watchdog');
                clearInterval(watchdog);
                return;
            }
            
            tryInit();
            
            if (window.__fileStagingInitDone || watchdogAttempts >= maxAttempts) {
                if (watchdogAttempts >= maxAttempts) {
                    console.error('[FILE STAGING] Watchdog timeout - initialization failed');
                }
                clearInterval(watchdog);
            }
        }, 250);
        
        // Strategy 3: readystatechange listener
        document.addEventListener('readystatechange', () => {
            console.log('[FILE STAGING] readystatechange:', document.readyState);
            tryInit();
        });
        
        // Strategy 4: DOMContentLoaded on document (may be intercepted)
        document.addEventListener('DOMContentLoaded', tryInit);
        
        // Strategy 5: window.load (last resort)
        window.addEventListener('load', tryInit);
    }

    // Export public API with init exposed for manual activation
    window.FileStagingModule = {
        init: init,  // Expose init for manual calls
        removeFile: removeFile,
        getState: () => ({ ...state })
    };

    console.log('[FILE STAGING] Module loaded');

})();
