// Global Polling Manager
// Centralized management of all intervals and timeouts to prevent memory leaks and phantom polling

(function() {
  'use strict';
  
  const GlobalPollingManager = {
    intervals: new Map(),
    timeouts: new Map(),
    animationFrames: new Set(),
    observers: new Map(),
    eventListeners: [],
    pollingIdCounter: 0,
    isShuttingDown: false,
    debugMode: false,
    
    // Generate unique ID for tracking
    generateId(type) {
      return `${type}_${Date.now()}_${++this.pollingIdCounter}`;
    },
    
    // Register an interval with tracking
    registerInterval(callback, delay, description = 'Unknown interval') {
      if (this.isShuttingDown) {
        console.warn('[PollingManager] Cannot register interval during shutdown');
        return null;
      }
      
      const id = this.generateId('interval');
      const intervalId = setInterval(() => {
        try {
          callback();
        } catch (error) {
          console.error(`[PollingManager] Error in interval "${description}":`, error);
          this.clearInterval(id);
        }
      }, delay);
      
      this.intervals.set(id, {
        intervalId,
        description,
        startTime: Date.now(),
        delay,
        callback: callback.toString().substring(0, 100) // Store first 100 chars for debugging
      });
      
      if (this.debugMode) {
        console.log(`[PollingManager] Registered interval: ${description} (${id})`);
      }
      
      return id;
    },
    
    // Register a timeout with tracking
    registerTimeout(callback, delay, description = 'Unknown timeout') {
      if (this.isShuttingDown) {
        console.warn('[PollingManager] Cannot register timeout during shutdown');
        return null;
      }
      
      const id = this.generateId('timeout');
      const timeoutId = setTimeout(() => {
        try {
          callback();
          this.timeouts.delete(id); // Auto-cleanup after execution
        } catch (error) {
          console.error(`[PollingManager] Error in timeout "${description}":`, error);
        }
      }, delay);
      
      this.timeouts.set(id, {
        timeoutId,
        description,
        startTime: Date.now(),
        delay
      });
      
      if (this.debugMode) {
        console.log(`[PollingManager] Registered timeout: ${description} (${id})`);
      }
      
      return id;
    },
    
    // Clear specific interval
    clearInterval(id) {
      const interval = this.intervals.get(id);
      if (interval) {
        clearInterval(interval.intervalId);
        this.intervals.delete(id);
        if (this.debugMode) {
          console.log(`[PollingManager] Cleared interval: ${interval.description}`);
        }
      }
    },
    
    // Clear specific timeout
    clearTimeout(id) {
      const timeout = this.timeouts.get(id);
      if (timeout) {
        clearTimeout(timeout.timeoutId);
        this.timeouts.delete(id);
        if (this.debugMode) {
          console.log(`[PollingManager] Cleared timeout: ${timeout.description}`);
        }
      }
    },
    
    // Stop ALL polling - Master kill switch
    stopAllPolling(permanent = false) {
      console.warn('[PollingManager] 🛑 STOPPING ALL POLLING');
      
      // Only permanently shutdown if explicitly requested
      if (permanent) {
        this.isShuttingDown = true;
      }
      
      // Clear all intervals
      let clearedIntervals = 0;
      this.intervals.forEach((interval, id) => {
        clearInterval(interval.intervalId);
        clearedIntervals++;
        if (this.debugMode) {
          console.log(`[PollingManager] Clearing interval: ${interval.description}`);
        }
      });
      this.intervals.clear();
      
      // Clear all timeouts
      let clearedTimeouts = 0;
      this.timeouts.forEach((timeout, id) => {
        clearTimeout(timeout.timeoutId);
        clearedTimeouts++;
        if (this.debugMode) {
          console.log(`[PollingManager] Clearing timeout: ${timeout.description}`);
        }
      });
      this.timeouts.clear();
      
      // Cancel animation frames
      let cancelledFrames = 0;
      this.animationFrames.forEach(frameId => {
        cancelAnimationFrame(frameId);
        cancelledFrames++;
      });
      this.animationFrames.clear();
      
      // Disconnect observers
      let disconnectedObservers = 0;
      this.observers.forEach((observer, id) => {
        observer.disconnect();
        disconnectedObservers++;
      });
      this.observers.clear();
      
      // Try to stop specific known polling from the app
      this.stopKnownPolling();
      
      console.log(`[PollingManager] ✅ Cleared ${clearedIntervals} intervals, ${clearedTimeouts} timeouts, ${cancelledFrames} animation frames, ${disconnectedObservers} observers`);
      
      return {
        intervals: clearedIntervals,
        timeouts: clearedTimeouts,
        animationFrames: cancelledFrames,
        observers: disconnectedObservers
      };
    },
    
    // Stop known polling patterns in the app
    stopKnownPolling() {
      // Stop AI Assistant polling
      if (window.aiAssistant) {
        if (window.aiAssistant.currentPollInterval) {
          clearInterval(window.aiAssistant.currentPollInterval);
          window.aiAssistant.currentPollInterval = null;
        }
        if (window.aiAssistant.healthCheckInterval) {
          clearInterval(window.aiAssistant.healthCheckInterval);
          window.aiAssistant.healthCheckInterval = null;
        }
        window.aiAssistant.stopJobPolling && window.aiAssistant.stopJobPolling();
      }
      
      // Stop app polling
      if (window.pollingIntervalId) {
        clearInterval(window.pollingIntervalId);
        window.pollingIntervalId = null;
      }
      // CRITICAL: Do NOT stop AI analysis polling if it's protected
      if (window.aiAnalysisInterval && !window.PROTECTED_AI_POLLING) {
        console.log('[PollingManager] Clearing aiAnalysisInterval (not protected)');
        clearInterval(window.aiAnalysisInterval);
        window.aiAnalysisInterval = null;
      } else if (window.PROTECTED_AI_POLLING) {
        console.log('[PollingManager] ⚠️ NOT clearing aiAnalysisInterval - it is PROTECTED');
      }
      if (window.progressInterval) {
        clearInterval(window.progressInterval);
        window.progressInterval = null;
      }
      
      // Stop ScenarioManager polling
      if (window.ScenarioManager && window.ScenarioManager.stopSyncPolling) {
        window.ScenarioManager.stopSyncPolling();
      }
      
      // Stop any jQuery/other library timers (defensive)
      try {
        if (typeof $ !== 'undefined' && $.timers) {
          $.timers = [];
        }
      } catch (e) {
        // Ignore if jQuery not present
      }
    },
    
    // Get status of all active polling
    getStatus() {
      return {
        intervals: Array.from(this.intervals.entries()).map(([id, info]) => ({
          id,
          description: info.description,
          runningFor: Date.now() - info.startTime,
          delay: info.delay
        })),
        timeouts: Array.from(this.timeouts.entries()).map(([id, info]) => ({
          id,
          description: info.description,
          remainingTime: Math.max(0, info.delay - (Date.now() - info.startTime))
        })),
        isShuttingDown: this.isShuttingDown
      };
    },
    
    // Resume polling after cleanup
    resumePolling() {
      this.isShuttingDown = false;
      console.log('[PollingManager] ✅ Polling resumed - new intervals/timeouts allowed');
    },
    
    // Enable debug logging
    enableDebug() {
      this.debugMode = true;
      console.log('[PollingManager] Debug mode enabled');
    },
    
    // Disable debug logging
    disableDebug() {
      this.debugMode = false;
      console.log('[PollingManager] Debug mode disabled');
    },
    
    // Override native functions to track all intervals/timeouts
    interceptNativeFunctions() {
      const originalSetInterval = window.setInterval;
      const originalSetTimeout = window.setTimeout;
      const originalClearInterval = window.clearInterval;
      const originalClearTimeout = window.clearTimeout;
      
      // Track all intervals globally
      window.setInterval = (callback, delay, ...args) => {
        const stackTrace = new Error().stack;
        const caller = stackTrace.split('\n')[2] || 'unknown';
        const callbackStr = callback.toString();
        
        // CRITICAL: Always allow AI analysis polling, even during shutdown
        const isAIAnalysisPolling = callbackStr.includes('pollAIAnalysis') || 
                                     callbackStr.includes('job_id') ||
                                     callbackStr.includes('jobId') ||
                                     caller.includes('analyzeRFP') ||
                                     caller.includes('AI') ||
                                     window.PROTECTED_AI_POLLING === true;
        
        if (this.isShuttingDown && !isAIAnalysisPolling) {
          console.warn('[PollingManager] Blocked setInterval during shutdown from:', caller);
          return null;
        }
        
        if (isAIAnalysisPolling) {
          console.log('[PollingManager] ✅ Allowing AI Analysis polling (protected)');
        }
        
        const intervalId = originalSetInterval.call(window, callback, delay, ...args);
        
        // Store in a global tracking array (but mark protected ones)
        if (!window.__allIntervals) {
          window.__allIntervals = new Set();
        }
        if (!window.__protectedIntervals) {
          window.__protectedIntervals = new Set();
        }
        
        window.__allIntervals.add(intervalId);
        if (isAIAnalysisPolling) {
          window.__protectedIntervals.add(intervalId);
        }
        
        if (this.debugMode) {
          console.log('[PollingManager] Native interval created:', intervalId, 'from:', caller, 'protected:', isAIAnalysisPolling);
        }
        
        return intervalId;
      };
      
      // CRITICAL: Override clearInterval to never clear protected intervals
      window.clearInterval = (intervalId) => {
        if (window.__protectedIntervals && window.__protectedIntervals.has(intervalId) && window.PROTECTED_AI_POLLING) {
          console.warn('[PollingManager] ⚠️ Blocked attempt to clear protected AI polling interval:', intervalId);
          return; // Don't clear it
        }
        if (window.__allIntervals) {
          window.__allIntervals.delete(intervalId);
        }
        if (window.__protectedIntervals) {
          window.__protectedIntervals.delete(intervalId);
        }
        return originalClearInterval.call(window, intervalId);
      };
      
      // Track interval clearing
      window.clearInterval = (intervalId) => {
        if (window.__allIntervals) {
          window.__allIntervals.delete(intervalId);
        }
        return originalClearInterval.call(window, intervalId);
      };
      
      // Track all timeouts globally
      window.setTimeout = (callback, delay, ...args) => {
        // CRITICAL: Check for protected AI polling FIRST
        if (window.PROTECTED_AI_POLLING || (callback && callback.toString().includes('pollAIAnalysis'))) {
          console.log('[PollingManager] Allowing protected AI polling');
          return originalSetTimeout.call(window, callback, delay, ...args);
        }
        
        const stackTrace = new Error().stack;
        const caller = stackTrace.split('\n')[2] || 'unknown';
        const callbackStr = callback.toString();
        
        // CRITICAL: Always allow AI analysis polling, even during shutdown
        const isAIAnalysisPolling = callbackStr.includes('pollAIAnalysis') || 
                                     callbackStr.includes('job_id') ||
                                     callbackStr.includes('jobId') ||
                                     caller.includes('analyzeRFP') ||
                                     caller.includes('AI') ||
                                     window.PROTECTED_AI_POLLING === true;
        
        if (this.isShuttingDown && delay > 100 && !isAIAnalysisPolling) { // Allow short timeouts for cleanup and AI polling
          console.warn('[PollingManager] Blocked setTimeout during shutdown from:', caller);
          return null;
        }
        
        if (isAIAnalysisPolling) {
          console.log('[PollingManager] ✅ Allowing AI Analysis timeout (protected)');
        }
        
        const timeoutId = originalSetTimeout.call(window, callback, delay, ...args);
        
        // Store in a global tracking array
        if (!window.__allTimeouts) {
          window.__allTimeouts = new Set();
        }
        window.__allTimeouts.add(timeoutId);
        
        // Auto-remove after execution
        originalSetTimeout.call(window, () => {
          if (window.__allTimeouts) {
            window.__allTimeouts.delete(timeoutId);
          }
        }, delay);
        
        return timeoutId;
      };
      
      // Track timeout clearing
      window.clearTimeout = (timeoutId) => {
        if (window.__allTimeouts) {
          window.__allTimeouts.delete(timeoutId);
        }
        return originalClearTimeout.call(window, timeoutId);
      };
    },
    
    // Nuclear option - clear ALL native intervals and timeouts
    clearAllNative() {
      console.warn('[PollingManager] 🔥 NUCLEAR CLEAR - Stopping ALL native intervals and timeouts');
      
      // Clear all tracked intervals
      if (window.__allIntervals) {
        window.__allIntervals.forEach(id => clearInterval(id));
        window.__allIntervals.clear();
      }
      
      // Clear all tracked timeouts
      if (window.__allTimeouts) {
        window.__allTimeouts.forEach(id => clearTimeout(id));
        window.__allTimeouts.clear();
      }
      
      // Brute force clear (last resort)
      for (let i = 1; i < 99999; i++) {
        clearInterval(i);
        clearTimeout(i);
      }
      
      console.log('[PollingManager] Nuclear clear complete');
    },
    
    // Initialize the manager
    init() {
      // Intercept native functions to track everything
      this.interceptNativeFunctions();
      
      // Set up cleanup on page unload
      window.addEventListener('beforeunload', () => {
        this.stopAllPolling();
      });
      
      // Set up cleanup on page visibility change
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          console.log('[PollingManager] Page hidden - pausing non-critical polling');
          // Could implement pause logic here
        }
      });
      
      // Expose to window for debugging
      window.GlobalPollingManager = this;
      window.stopAllPolling = () => this.stopAllPolling();
      window.pollingStatus = () => this.getStatus();
      window.resumePolling = () => this.resumePolling();  // CRITICAL: Expose resumePolling
      
      console.log('[PollingManager] Initialized - Use window.stopAllPolling() to stop everything');
    }
  };
  
  // Initialize immediately
  GlobalPollingManager.init();
  
  // Return for module use
  return GlobalPollingManager;
})();