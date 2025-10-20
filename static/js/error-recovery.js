// Error Recovery and Stuck State Detection
// Prevents blank blue screens and provides recovery UI

(function() {
  'use strict';
  
  const ErrorRecovery = {
    checkInterval: null,
    stuckDetectionDelay: 3000, // Check after 3 seconds
    isRecovering: false,
    hasShownError: false,
    
    // Initialize error recovery system
    init() {
      console.log('[ErrorRecovery] Initializing error recovery system');
      
      // Create fallback UI immediately (but hidden)
      this.createFallbackUI();
      
      // Set up global error handler
      this.setupGlobalErrorHandler();
      
      // Set up stuck state detection
      this.setupStuckDetection();
      
      // Hide fallback UI if page loads successfully
      this.setupSuccessHandler();
      
      // Set up unhandled promise rejection handler
      this.setupPromiseHandler();
      
      // Expose recovery functions globally
      window.recoverFromError = () => this.recoverFromError();
      window.forceRecovery = () => this.forceRecovery();
      window.checkIfStuck = () => this.detectStuckState();
      
      console.log('[ErrorRecovery] System initialized');
    },
    
    // Create fallback UI that's always available
    createFallbackUI() {
      // DOM-ready guard: if body doesn't exist yet, wait for DOMContentLoaded
      if (!document.body) {
        document.addEventListener('DOMContentLoaded', () => this.createFallbackUI());
        return;
      }
      
      // Check if already exists
      if (document.getElementById('error-recovery-fallback')) {
        return;
      }
      
      const fallbackHTML = `
        <div id="error-recovery-fallback" style="
          display: none;
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          z-index: 999999;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          color: white;
          padding: 20px;
          overflow: auto;
        ">
          <div style="
            max-width: 600px;
            margin: 50px auto;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
          ">
            <h1 style="
              margin: 0 0 20px 0;
              font-size: 28px;
              font-weight: 600;
              text-align: center;
            ">
              ⚠️ Application Error
            </h1>
            
            <p style="
              font-size: 16px;
              line-height: 1.6;
              margin: 20px 0;
              text-align: center;
              opacity: 0.9;
            ">
              The application encountered an issue and needs to be reloaded.
            </p>
            
            <div id="error-details" style="
              background: rgba(0, 0, 0, 0.2);
              border-radius: 8px;
              padding: 15px;
              margin: 20px 0;
              font-family: 'Courier New', monospace;
              font-size: 12px;
              max-height: 200px;
              overflow: auto;
              display: none;
            "></div>
            
            <div style="
              display: flex;
              gap: 10px;
              justify-content: center;
              margin-top: 30px;
              flex-wrap: wrap;
            ">
              <button onclick="window.location.reload()" style="
                background: white;
                color: #667eea;
                border: none;
                padding: 12px 30px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
              " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                🔄 Reload Page
              </button>
              
              <button onclick="window.recoverFromError()" style="
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: 2px solid white;
                padding: 12px 30px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
              " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                🔧 Try Recovery
              </button>
              
              <button onclick="window.clearDataAndReload()" style="
                background: rgba(244, 67, 54, 0.2);
                color: white;
                border: 2px solid #f44336;
                padding: 12px 30px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
              " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                🗑️ Clear & Restart
              </button>
            </div>
            
            <p style="
              font-size: 12px;
              text-align: center;
              margin-top: 30px;
              opacity: 0.7;
            ">
              If the problem persists, please contact support.<br>
              <a href="#" onclick="window.showDebugInfo()" style="color: white; text-decoration: underline;">Show debug information</a>
            </p>
          </div>
        </div>
      `;
      
      // Insert at the beginning of body
      document.body.insertAdjacentHTML('afterbegin', fallbackHTML);
      
      // Also create a minimal fallback that's always visible but transparent
      const minimalFallback = document.createElement('div');
      minimalFallback.id = 'minimal-error-indicator';
      minimalFallback.style.cssText = `
        position: fixed;
        bottom: 10px;
        right: 10px;
        background: rgba(244, 67, 54, 0.9);
        color: white;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 12px;
        z-index: 999998;
        display: none;
        cursor: pointer;
        font-family: sans-serif;
      `;
      minimalFallback.innerHTML = '⚠️ Error detected - Click to recover';
      minimalFallback.onclick = () => this.showFallbackUI();
      document.body.appendChild(minimalFallback);
    },
    
    // Set up global error handler
    setupGlobalErrorHandler() {
      const originalOnError = window.onerror;
      
      window.onerror = (message, source, lineno, colno, error) => {
        console.error('[ErrorRecovery] Global error caught:', {
          message,
          source,
          line: lineno,
          column: colno,
          error
        });
        
        // Track consecutive errors
        if (!this.errorCount) {
          this.errorCount = 0;
          this.errorTimestamp = Date.now();
        }
        
        this.errorCount++;
        
        // If too many errors in short time, show recovery UI
        if (this.errorCount > 5 && (Date.now() - this.errorTimestamp) < 5000) {
          console.error('[ErrorRecovery] Too many errors detected, showing recovery UI');
          this.showFallbackUI(error);
        }
        
        // Reset counter after 10 seconds
        setTimeout(() => {
          this.errorCount = 0;
        }, 10000);
        
        // Call original handler if exists
        if (originalOnError) {
          return originalOnError(message, source, lineno, colno, error);
        }
        
        return true; // Prevent default browser error handling
      };
    },
    
    // Set up unhandled promise rejection handler
    setupPromiseHandler() {
      window.addEventListener('unhandledrejection', (event) => {
        console.error('[ErrorRecovery] Unhandled promise rejection:', event.reason);
        
        // Check if it's a critical error
        if (this.isCriticalError(event.reason)) {
          this.showMinimalError('Unhandled promise rejection');
        }
      });
    },
    
    // Detect if the UI is stuck (blank screen)
    setupStuckDetection() {
      // DISABLED: Automatic stuck detection causes false positives
      // when users step away from the computer during AI analysis.
      // The app should only reload when explicitly requested by the user.
      console.log('[ErrorRecovery] Stuck detection disabled to prevent unwanted reloads');
      return;
      
      /* Original code commented out:
      // Initial check after page load
      setTimeout(() => {
        this.detectStuckState();
      }, this.stuckDetectionDelay);
      
      // Periodic checks
      this.checkInterval = setInterval(() => {
        if (!this.isRecovering && !this.hasShownError) {
          this.detectStuckState();
        }
      }, 10000); // Check every 10 seconds
      */
    },
    
    // Detect if UI is stuck
    detectStuckState() {
      // Check if main content is visible
      const mainContent = document.querySelector('main, .container, #app, body > header + *');
      const hasVisibleContent = mainContent && mainContent.offsetHeight > 0;
      
      // Check if body has minimal content
      const bodyText = document.body.innerText.trim();
      const hasBodyContent = bodyText.length > 50; // Arbitrary minimum
      
      // Check for specific stuck patterns
      const isBlankBlue = this.isBlankBlueScreen();
      const hasNoInteractiveElements = this.hasNoInteractiveElements();
      
      // Determine if stuck
      const isStuck = (!hasVisibleContent && !hasBodyContent) || isBlankBlue || hasNoInteractiveElements;
      
      if (isStuck) {
        console.warn('[ErrorRecovery] Stuck state detected!', {
          hasVisibleContent,
          hasBodyContent,
          isBlankBlue,
          hasNoInteractiveElements
        });
        
        this.showFallbackUI({
          message: 'The application appears to be stuck',
          type: 'stuck_state'
        });
      }
      
      return isStuck;
    },
    
    // Check for blank blue screen
    isBlankBlueScreen() {
      const bodyStyle = window.getComputedStyle(document.body);
      const bgColor = bodyStyle.backgroundColor;
      const bgImage = bodyStyle.backgroundImage;
      
      // Check if background is blue-ish
      const isBlueBackground = bgColor.includes('blue') || 
                               bgColor.includes('rgb(102') || // #667eea
                               bgImage.includes('gradient');
      
      // Check if there's minimal content
      const visibleElements = document.querySelectorAll('body > *:not(script):not(style):not(#error-recovery-fallback)');
      let visibleCount = 0;
      
      visibleElements.forEach(el => {
        if (el.offsetHeight > 0 && el.offsetWidth > 0) {
          visibleCount++;
        }
      });
      
      return isBlueBackground && visibleCount < 2;
    },
    
    // Check if page has no interactive elements
    hasNoInteractiveElements() {
      const interactiveElements = document.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled])');
      let visibleInteractive = 0;
      
      interactiveElements.forEach(el => {
        if (el.offsetHeight > 0 && el.offsetWidth > 0) {
          visibleInteractive++;
        }
      });
      
      return visibleInteractive === 0;
    },
    
    // Show fallback UI
    showFallbackUI(error) {
      const fallback = document.getElementById('error-recovery-fallback');
      if (fallback) {
        fallback.style.display = 'block';
        this.hasShownError = true;
        
        // Show error details if available
        if (error) {
          const details = document.getElementById('error-details');
          if (details) {
            details.style.display = 'block';
            details.innerHTML = `
              <strong>Error Details:</strong><br>
              ${error.message || error.toString()}<br>
              <br>
              <strong>Stack:</strong><br>
              ${error.stack || 'No stack trace available'}
            `.replace(/\n/g, '<br>');
          }
        }
        
        // Stop all polling to prevent further errors
        if (window.stopAllPolling) {
          window.stopAllPolling();
        }
      }
    },
    
    // Show minimal error indicator
    showMinimalError(message) {
      const indicator = document.getElementById('minimal-error-indicator');
      if (indicator) {
        indicator.style.display = 'block';
        indicator.title = message;
      }
    },
    
    // Hide fallback UI
    hideFallbackUI() {
      const fallback = document.getElementById('error-recovery-fallback');
      if (fallback) {
        fallback.style.display = 'none';
      }
      
      const indicator = document.getElementById('minimal-error-indicator');
      if (indicator) {
        indicator.style.display = 'none';
      }
    },
    
    // Set up success handler to hide fallback
    setupSuccessHandler() {
      // Hide fallback after successful load
      window.addEventListener('load', () => {
        setTimeout(() => {
          // Always hide fallback UI on successful load
          // Don't call detectStuckState since it can cause false positives
          this.hideFallbackUI();
          console.log('[ErrorRecovery] Page loaded successfully, hiding fallback UI');
        }, 1000);
      });
      
      // Also hide when main app initializes
      document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
          if (document.querySelector('main, .step-container, #step-1')) {
            this.hideFallbackUI();
          }
        }, 500);
      });
    },
    
    // Determine if error is critical
    isCriticalError(error) {
      if (!error) return false;
      
      const criticalPatterns = [
        'Cannot read property',
        'Cannot read properties',
        'undefined is not',
        'null is not',
        'Maximum call stack',
        'out of memory',
        'Network error',
        'Failed to fetch'
      ];
      
      const errorString = error.toString().toLowerCase();
      return criticalPatterns.some(pattern => 
        errorString.includes(pattern.toLowerCase())
      );
    },
    
    // Recover from error
    recoverFromError() {
      console.log('[ErrorRecovery] Attempting recovery...');
      this.isRecovering = true;
      
      // Stop all polling
      if (window.stopAllPolling) {
        window.stopAllPolling();
      }
      
      // Clear any stuck modals or overlays
      document.querySelectorAll('.modal, .overlay, .popup').forEach(el => {
        el.style.display = 'none';
      });
      
      // Reset body classes
      document.body.className = '';
      
      // Try to reinitialize the app
      if (window.APP && window.APP.init) {
        try {
          window.APP.init();
          this.hideFallbackUI();
          console.log('[ErrorRecovery] Recovery successful');
        } catch (e) {
          console.error('[ErrorRecovery] Recovery failed:', e);
          this.forceRecovery();
        }
      } else {
        this.forceRecovery();
      }
      
      this.isRecovering = false;
    },
    
    // Force recovery by clearing data and reloading
    forceRecovery() {
      console.log('[ErrorRecovery] Forcing recovery...');
      
      // Clear all local storage
      localStorage.clear();
      sessionStorage.clear();
      
      // Clear cookies
      document.cookie.split(";").forEach((c) => {
        document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
      });
      
      // Reload page
      window.location.reload(true);
    },
    
    // Clean up on unload
    cleanup() {
      if (this.checkInterval) {
        clearInterval(this.checkInterval);
        this.checkInterval = null;
      }
    }
  };
  
  // Global helper functions
  window.clearDataAndReload = function() {
    if (confirm('This will clear all saved data and reload the page. Continue?')) {
      ErrorRecovery.forceRecovery();
    }
  };
  
  window.showDebugInfo = function() {
    const details = document.getElementById('error-details');
    if (details) {
      details.style.display = details.style.display === 'none' ? 'block' : 'none';
      
      // Populate with system info
      details.innerHTML = `
        <strong>System Information:</strong><br>
        User Agent: ${navigator.userAgent}<br>
        Platform: ${navigator.platform}<br>
        Language: ${navigator.language}<br>
        Cookies Enabled: ${navigator.cookieEnabled}<br>
        Online: ${navigator.onLine}<br>
        <br>
        <strong>Page State:</strong><br>
        Ready State: ${document.readyState}<br>
        DOM Elements: ${document.all.length}<br>
        Scripts: ${document.scripts.length}<br>
        Stylesheets: ${document.styleSheets.length}<br>
        <br>
        <strong>Memory:</strong><br>
        ${performance.memory ? `
        Used JS Heap: ${(performance.memory.usedJSHeapSize / 1048576).toFixed(2)} MB<br>
        Total JS Heap: ${(performance.memory.totalJSHeapSize / 1048576).toFixed(2)} MB<br>
        Limit: ${(performance.memory.jsHeapSizeLimit / 1048576).toFixed(2)} MB
        ` : 'Not available'}
      `.replace(/\n/g, '<br>');
    }
  };
  
  // Initialize error recovery
  ErrorRecovery.init();
  
  // Clean up on page unload
  window.addEventListener('beforeunload', () => {
    ErrorRecovery.cleanup();
  });
  
  // Expose for debugging
  window.ErrorRecovery = ErrorRecovery;
  
  console.log('[ErrorRecovery] System ready - Use window.recoverFromError() or window.forceRecovery() if needed');
  
  return ErrorRecovery;
})();