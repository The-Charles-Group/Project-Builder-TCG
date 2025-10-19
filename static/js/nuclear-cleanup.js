// NUCLEAR CLEANUP - Stop all polling and clear problematic job IDs
// This runs IMMEDIATELY on page load to prevent any polling from starting

(function() {
    'use strict';
    
    console.log('☢️ NUCLEAR CLEANUP ACTIVATED ☢️');
    console.log('Timestamp:', new Date().toISOString());
    
    // 1. IMMEDIATELY stop any existing intervals
    const highestIntervalId = setInterval(() => {}, 0);
    for (let i = 0; i < highestIntervalId; i++) {
        clearInterval(i);
    }
    console.log('☢️ Cleared all intervals up to ID:', highestIntervalId);
    
    // 2. Clear ALL localStorage items containing job IDs
    const keysToNuke = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        const value = localStorage.getItem(key);
        if (value && value.includes('642a96bd-f94b-440e-b865-d160839a57c0')) {
            keysToNuke.push(key);
            console.log('☢️ Found problematic job ID in localStorage:', key);
        }
    }
    
    // Remove all problematic keys
    keysToNuke.forEach(key => {
        console.log('☢️ Nuking localStorage key:', key);
        localStorage.removeItem(key);
    });
    
    // 3. Specifically target charles_agent_state
    try {
        const charlesState = JSON.parse(localStorage.getItem('charles_agent_state') || '{}');
        let cleaned = false;
        
        // Clear top-level jobId
        if (charlesState.jobId) {
            console.log('☢️ Clearing top-level jobId:', charlesState.jobId);
            charlesState.jobId = null;
            charlesState.jobIdTimestamp = null;
            cleaned = true;
        }
        
        // Clear from ALL stateHistory
        if (charlesState.stateHistory && Array.isArray(charlesState.stateHistory)) {
            charlesState.stateHistory.forEach((state, idx) => {
                if (state.jobId) {
                    console.log(`☢️ Clearing jobId from stateHistory[${idx}]:`, state.jobId);
                    state.jobId = null;
                    state.jobIdTimestamp = null;
                    cleaned = true;
                }
                if (state.agentState && state.agentState.jobId) {
                    console.log(`☢️ Clearing agentState.jobId from stateHistory[${idx}]:`, state.agentState.jobId);
                    state.agentState.jobId = null;
                    cleaned = true;
                }
            });
        }
        
        if (cleaned) {
            localStorage.setItem('charles_agent_state', JSON.stringify(charlesState));
            console.log('☢️ Saved cleaned charles_agent_state');
        }
    } catch (e) {
        console.error('☢️ Error cleaning charles_agent_state:', e);
    }
    
    // 4. Override setInterval to prevent any polling of the problematic job
    const originalSetInterval = window.setInterval;
    window.setInterval = function(callback, delay, ...args) {
        // Check if the callback contains the problematic job ID
        const callbackStr = callback.toString();
        if (callbackStr.includes('642a96bd-f94b-440e-b865-d160839a57c0')) {
            console.log('☢️ BLOCKED polling attempt for job 642a96bd-f94b-440e-b865-d160839a57c0');
            return null; // Don't create the interval
        }
        
        // Check if it's trying to poll /api/ai/jobs
        if (callbackStr.includes('/api/ai/jobs/')) {
            console.log('☢️ WARNING: Attempt to poll /api/ai/jobs/ detected, checking...');
            // Allow it but log it
        }
        
        return originalSetInterval.apply(this, arguments);
    };
    
    // 5. Override XMLHttpRequest to block requests to problematic jobs
    const originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...args) {
        // Block ALL polling to /api/ai/jobs/ endpoints for first 10 seconds
        const timeSinceLoad = Date.now() - window.pageLoadTime;
        if (url && url.includes('/api/ai/jobs/') && timeSinceLoad < 10000) {
            console.log('☢️ BLOCKED XHR request to AI jobs endpoint (within 10s of page load):', url);
            // Replace with a dummy URL that will return 404 but won't flood logs
            url = '/api/null';
        } else if (url && url.includes('642a96bd-f94b-440e-b865-d160839a57c0')) {
            console.log('☢️ BLOCKED XHR request to problematic job ID:', url);
            url = '/api/null';
        }
        return originalOpen.apply(this, [method, url, ...args]);
    };
    
    // 6. Override fetch to block requests to problematic jobs
    const originalFetch = window.fetch;
    window.fetch = function(url, ...args) {
        // Block ALL polling to /api/ai/jobs/ endpoints for first 10 seconds
        const timeSinceLoad = Date.now() - window.pageLoadTime;
        if (url && url.toString().includes('/api/ai/jobs/') && timeSinceLoad < 10000) {
            console.log('☢️ BLOCKED fetch request to AI jobs endpoint (within 10s of page load):', url);
            // Return a fake 404 response
            return Promise.resolve(new Response(null, { status: 404, statusText: 'Not Found' }));
        } else if (url && url.toString().includes('642a96bd-f94b-440e-b865-d160839a57c0')) {
            console.log('☢️ BLOCKED fetch request to problematic job ID:', url);
            return Promise.resolve(new Response(null, { status: 404, statusText: 'Not Found' }));
        }
        return originalFetch.apply(this, arguments);
    };
    
    // 7. Set page load time for blocking logic
    window.pageLoadTime = Date.now();
    
    console.log('☢️ NUCLEAR CLEANUP COMPLETE ☢️');
    console.log('- All intervals cleared');
    console.log('- LocalStorage cleaned');
    console.log('- Polling interceptors installed');
    console.log('- Problematic job ID 642a96bd-f94b-440e-b865-d160839a57c0 will be blocked');
    
})();