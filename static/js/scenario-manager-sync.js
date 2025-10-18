// scenario-manager-sync.js
// Enhanced ScenarioManager with real-time synchronization capabilities
// This version adds polling-based sync, conflict resolution, and visual indicators

(function() {
  // Extend the existing ScenarioManager with sync capabilities
  const originalScenarioManager = window.ScenarioManager || {};
  
  const ScenarioManagerSync = {
    // Keep all original methods and state
    ...originalScenarioManager,
    
    // Enhanced state with sync metadata
    state: {
      ...(originalScenarioManager.state || {}),
      lastModified: Date.now(),
      lastSyncedAt: null,
      syncVersion: 0,
      isSyncing: false,
      connectionStatus: 'connected', // 'connected', 'syncing', 'offline', 'error'
      pendingChanges: [],
      conflictQueue: [],
      syncIndicatorElement: null
    },
    
    // Real-time sync configuration
    syncConfig: {
      enabled: true,
      interval: 2000, // 2 seconds for active sync
      retryInterval: 5000, // 5 seconds on error
      maxRetries: 3,
      syncTimer: null,
      retryCount: 0,
      isTabActive: true,
      conflictResolution: 'server-wins', // 'server-wins', 'client-wins', 'merge'
      lastServerVersion: 0,
      pauseSync: false
    },
    
    // Initialize real-time sync
    initRealTimeSync() {
      console.log('[ScenarioSync] Initializing real-time sync');
      
      // Set up Page Visibility API
      this.setupVisibilityHandling();
      
      // Set up online/offline detection
      this.setupNetworkHandling();
      
      // Create sync indicator UI
      this.createSyncIndicator();
      
      // Start polling
      this.startSyncPolling();
      
      // Override emit to track changes
      const originalEmit = this.emit.bind(this);
      this.emit = () => {
        this.state.lastModified = Date.now();
        this.state.syncVersion++;
        originalEmit();
        
        // Queue change for sync
        if (!this.syncConfig.pauseSync) {
          this.queueSync();
        }
      };
      
      // Listen for external sync triggers
      document.addEventListener('scenario:force-sync', () => this.syncNow());
      document.addEventListener('scenario:pause-sync', () => this.pauseSync());
      document.addEventListener('scenario:resume-sync', () => this.resumeSync());
      
      return this;
    },
    
    // Setup Page Visibility API handling
    setupVisibilityHandling() {
      document.addEventListener('visibilitychange', () => {
        this.syncConfig.isTabActive = !document.hidden;
        
        if (document.hidden) {
          console.log('[ScenarioSync] Tab inactive, pausing frequent sync');
          this.stopSyncPolling();
        } else {
          console.log('[ScenarioSync] Tab active, resuming sync');
          this.startSyncPolling();
          this.syncNow(); // Immediate sync on tab activation
        }
      });
    },
    
    // Setup network online/offline detection
    setupNetworkHandling() {
      window.addEventListener('online', () => {
        console.log('[ScenarioSync] Network online');
        this.state.connectionStatus = 'connected';
        this.updateSyncIndicator();
        this.syncNow(); // Immediate sync when coming online
      });
      
      window.addEventListener('offline', () => {
        console.log('[ScenarioSync] Network offline');
        this.state.connectionStatus = 'offline';
        this.updateSyncIndicator();
      });
    },
    
    // Create visual sync indicator
    createSyncIndicator() {
      // Remove existing if any
      const existing = document.getElementById('scenario-sync-indicator');
      if (existing) existing.remove();
      
      const indicator = document.createElement('div');
      indicator.id = 'scenario-sync-indicator';
      indicator.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 12px;
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 8px;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
        opacity: 0.9;
      `;
      
      indicator.innerHTML = `
        <span class="sync-status-dot" style="
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #10b981;
          animation: pulse 2s infinite;
        "></span>
        <span class="sync-status-text">Connected</span>
        <span class="sync-timestamp" style="
          color: #9ca3af;
          font-size: 11px;
        "></span>
      `;
      
      document.body.appendChild(indicator);
      this.state.syncIndicatorElement = indicator;
      
      // Add pulse animation
      const style = document.createElement('style');
      style.textContent = `
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .sync-flash {
          animation: flash 0.5s ease;
        }
        @keyframes flash {
          0%, 100% { background: rgba(59, 130, 246, 0.1); }
          50% { background: rgba(59, 130, 246, 0.3); }
        }
      `;
      document.head.appendChild(style);
      
      this.updateSyncIndicator();
    },
    
    // Update sync indicator UI
    updateSyncIndicator() {
      const indicator = this.state.syncIndicatorElement;
      if (!indicator) return;
      
      const statusDot = indicator.querySelector('.sync-status-dot');
      const statusText = indicator.querySelector('.sync-status-text');
      const timestamp = indicator.querySelector('.sync-timestamp');
      
      const statusConfig = {
        connected: { color: '#10b981', text: 'Connected', animation: 'pulse 2s infinite' },
        syncing: { color: '#3b82f6', text: 'Syncing...', animation: 'spin 1s linear infinite' },
        offline: { color: '#ef4444', text: 'Offline', animation: 'none' },
        error: { color: '#f59e0b', text: 'Sync Error', animation: 'pulse 1s infinite' }
      };
      
      const config = statusConfig[this.state.connectionStatus] || statusConfig.connected;
      
      statusDot.style.background = config.color;
      statusDot.style.animation = config.animation;
      statusText.textContent = config.text;
      
      // Update timestamp
      if (this.state.lastSyncedAt) {
        const secondsAgo = Math.floor((Date.now() - this.state.lastSyncedAt) / 1000);
        if (secondsAgo < 60) {
          timestamp.textContent = `${secondsAgo}s ago`;
        } else {
          const minutesAgo = Math.floor(secondsAgo / 60);
          timestamp.textContent = `${minutesAgo}m ago`;
        }
      } else {
        timestamp.textContent = 'Never synced';
      }
    },
    
    // Start polling for sync
    startSyncPolling() {
      if (this.syncConfig.syncTimer) {
        clearInterval(this.syncConfig.syncTimer);
      }
      
      // Initial sync
      this.syncNow();
      
      // Set up polling
      this.syncConfig.syncTimer = setInterval(() => {
        if (this.syncConfig.enabled && this.syncConfig.isTabActive && !this.syncConfig.pauseSync) {
          this.syncWithBackend();
        }
        
        // Always update timestamp
        this.updateSyncIndicator();
      }, this.syncConfig.interval);
      
      console.log('[ScenarioSync] Started sync polling');
    },
    
    // Stop sync polling
    stopSyncPolling() {
      if (this.syncConfig.syncTimer) {
        clearInterval(this.syncConfig.syncTimer);
        this.syncConfig.syncTimer = null;
      }
      console.log('[ScenarioSync] Stopped sync polling');
    },
    
    // Queue a sync operation
    queueSync() {
      // Debounce rapid changes
      if (this.syncDebounceTimer) {
        clearTimeout(this.syncDebounceTimer);
      }
      
      this.syncDebounceTimer = setTimeout(() => {
        this.syncNow();
      }, 500); // Wait 500ms after last change
    },
    
    // Force immediate sync
    syncNow() {
      if (navigator.onLine && !this.state.isSyncing) {
        this.syncWithBackend();
      }
    },
    
    // Pause sync (for bulk operations)
    pauseSync() {
      this.syncConfig.pauseSync = true;
      console.log('[ScenarioSync] Sync paused');
    },
    
    // Resume sync
    resumeSync() {
      this.syncConfig.pauseSync = false;
      this.syncNow();
      console.log('[ScenarioSync] Sync resumed');
    },
    
    // Main sync function with backend
    async syncWithBackend() {
      if (this.state.isSyncing || !navigator.onLine) return;
      
      this.state.isSyncing = true;
      this.state.connectionStatus = 'syncing';
      this.updateSyncIndicator();
      
      try {
        const payload = {
          sessionId: this.state.sessionId,
          clientVersion: this.state.syncVersion,
          lastServerVersion: this.syncConfig.lastServerVersion,
          scenario: this.getCurrentScenario(),
          selections: {
            deliverables: Array.from(this.state.selectedDeliverables || []),
            components: this.state.selectedComponents || {},
            l3Tasks: this.state.selectedL3Tasks || {}
          },
          timestamp: Date.now(),
          checksum: this.calculateChecksum()
        };
        
        const response = await fetch('/api/scenario/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
          throw new Error(`Sync failed: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Process sync response
        await this.processSyncResponse(data);
        
        // Success
        this.state.lastSyncedAt = Date.now();
        this.state.connectionStatus = 'connected';
        this.syncConfig.retryCount = 0;
        this.syncConfig.lastServerVersion = data.serverVersion || this.syncConfig.lastServerVersion;
        
        console.log('[ScenarioSync] Sync successful');
        
      } catch (error) {
        console.error('[ScenarioSync] Sync error:', error);
        
        this.state.connectionStatus = 'error';
        this.syncConfig.retryCount++;
        
        // Retry logic
        if (this.syncConfig.retryCount < this.syncConfig.maxRetries) {
          setTimeout(() => this.syncNow(), this.syncConfig.retryInterval);
        }
      } finally {
        this.state.isSyncing = false;
        this.updateSyncIndicator();
      }
    },
    
    // Process sync response from server
    async processSyncResponse(data) {
      if (!data) return;
      
      // Check if server has newer data
      if (data.hasChanges) {
        console.log('[ScenarioSync] Server has changes, applying...');
        
        // Handle conflicts
        if (data.hasConflicts) {
          await this.resolveConflicts(data.conflicts);
        }
        
        // Apply server changes
        if (data.scenario) {
          await this.applyServerChanges(data.scenario, data.selections);
        }
        
        // Notify subscribers of external changes
        this.notifyExternalChange(data.changedElements);
      }
      
      // Update sync metadata
      if (data.serverVersion) {
        this.syncConfig.lastServerVersion = data.serverVersion;
      }
    },
    
    // Resolve conflicts between client and server
    async resolveConflicts(conflicts) {
      if (!conflicts || conflicts.length === 0) return;
      
      console.log('[ScenarioSync] Resolving conflicts:', conflicts);
      
      for (const conflict of conflicts) {
        switch (this.syncConfig.conflictResolution) {
          case 'server-wins':
            // Server data takes precedence
            console.log('[ScenarioSync] Server wins for conflict:', conflict.field);
            break;
            
          case 'client-wins':
            // Keep client data, will be sent in next sync
            console.log('[ScenarioSync] Client wins for conflict:', conflict.field);
            this.state.pendingChanges.push(conflict.field);
            break;
            
          case 'merge':
            // Attempt to merge changes
            await this.mergeConflict(conflict);
            break;
        }
      }
    },
    
    // Apply changes from server
    async applyServerChanges(scenario, selections) {
      // Pause local sync to prevent loops
      this.pauseSync();
      
      try {
        // Update selections if provided
        if (selections) {
          if (selections.deliverables) {
            this.state.selectedDeliverables = new Set(selections.deliverables);
          }
          if (selections.components) {
            this.state.selectedComponents = selections.components;
          }
          if (selections.l3Tasks) {
            this.state.selectedL3Tasks = selections.l3Tasks;
          }
        }
        
        // Update scenario data
        if (scenario) {
          this.updateDeliverablesFromAPI({ scenario });
        }
        
        // Flash changed elements
        this.flashChangedElements();
        
      } finally {
        // Resume sync after applying changes
        setTimeout(() => this.resumeSync(), 100);
      }
    },
    
    // Notify subscribers of external changes
    notifyExternalChange(changedElements) {
      // Emit custom event for steps to react
      document.dispatchEvent(new CustomEvent('scenario:external-change', {
        detail: {
          changedElements: changedElements || [],
          timestamp: Date.now(),
          source: 'sync'
        }
      }));
      
      // Show notification
      this.showSyncNotification('Data updated from another tab');
    },
    
    // Flash changed elements in UI
    flashChangedElements() {
      // Find all pricing table rows
      const pricingRows = document.querySelectorAll('.pricing-table-row, .deliverable-row');
      pricingRows.forEach(row => {
        row.classList.add('sync-flash');
        setTimeout(() => row.classList.remove('sync-flash'), 500);
      });
      
      // Flash Step 2 checkboxes if visible
      const checkboxes = document.querySelectorAll('#step2 input[type="checkbox"]:checked');
      checkboxes.forEach(cb => {
        const parent = cb.closest('.deliverable-item');
        if (parent) {
          parent.classList.add('sync-flash');
          setTimeout(() => parent.classList.remove('sync-flash'), 500);
        }
      });
    },
    
    // Show sync notification
    showSyncNotification(message) {
      const notification = document.createElement('div');
      notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 10001;
        animation: slideIn 0.3s ease;
      `;
      notification.textContent = message;
      
      document.body.appendChild(notification);
      
      setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
      }, 3000);
    },
    
    // Calculate checksum for change detection
    calculateChecksum() {
      const data = JSON.stringify({
        deliverables: this.state.deliverables.length,
        total: this.state.totals.grandTotal12,
        selections: Array.from(this.state.selectedDeliverables || []).length
      });
      
      // Simple hash function
      let hash = 0;
      for (let i = 0; i < data.length; i++) {
        const char = data.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
      }
      return hash.toString(16);
    },
    
    // Merge conflict resolution
    async mergeConflict(conflict) {
      console.log('[ScenarioSync] Attempting to merge conflict:', conflict);
      
      // Simple merge strategy: combine arrays, use latest for primitives
      if (Array.isArray(conflict.clientValue) && Array.isArray(conflict.serverValue)) {
        // Merge arrays by combining unique values
        const merged = [...new Set([...conflict.clientValue, ...conflict.serverValue])];
        console.log('[ScenarioSync] Merged array conflict:', merged);
        return merged;
      } else if (typeof conflict.clientValue === 'number' && typeof conflict.serverValue === 'number') {
        // For numbers, use the larger value (conservative approach)
        return Math.max(conflict.clientValue, conflict.serverValue);
      } else {
        // For other types, use server value
        return conflict.serverValue;
      }
    },
    
    // Clean up on page unload
    cleanup() {
      this.stopSyncPolling();
      if (this.state.syncIndicatorElement) {
        this.state.syncIndicatorElement.remove();
      }
    }
  };
  
  // Replace global ScenarioManager with enhanced version
  window.ScenarioManager = ScenarioManagerSync;
  
  // Auto-initialize sync when ScenarioManager is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      if (window.ScenarioManager && window.ScenarioManager.initRealTimeSync) {
        window.ScenarioManager.initRealTimeSync();
      }
    });
  } else {
    if (window.ScenarioManager && window.ScenarioManager.initRealTimeSync) {
      window.ScenarioManager.initRealTimeSync();
    }
  }
  
  // Clean up on page unload
  window.addEventListener('beforeunload', () => {
    window.ScenarioManager.cleanup();
  });
  
  console.log('[ScenarioSync] Enhanced ScenarioManager with real-time sync loaded');
})();