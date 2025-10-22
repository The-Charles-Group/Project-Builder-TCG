// STALE JOB CLEANUP - Clean up any stale job IDs on page load
// This runs on page load to clear old job IDs from localStorage

(function() {
    'use strict';
    
    console.log('[CLEANUP] Checking for stale job IDs on page load...');
    console.log('[CLEANUP] Timestamp:', new Date().toISOString());
    
    // CRITICAL: Stop any existing polling immediately on page load
    // Clear ALL intervals that might be running from previous page loads
    const highestIntervalId = setInterval(() => {}, 0);
    for (let i = 0; i < highestIntervalId; i++) {
        clearInterval(i);
    }
    console.log('[CLEANUP] Cleared all intervals up to ID:', highestIntervalId);
    
    // List of known problematic job IDs that should be cleared
    const problematicJobIds = [
        '642a96bd-f94b-440e-b865-d160839a57c0'
        // Add more problematic IDs here as needed
    ];
    
    let cleanedCount = 0;
    
    // 1. Clean charles_agent_state
    try {
        const charlesState = JSON.parse(localStorage.getItem('charles_agent_state') || '{}');
        let cleaned = false;
        
        // Clear top-level jobId if it's stale (older than 10 minutes) or problematic
        if (charlesState.jobId) {
            const jobIdAge = charlesState.jobIdTimestamp ? (Date.now() - charlesState.jobIdTimestamp) : Infinity;
            const tenMinutes = 10 * 60 * 1000;
            
            if (jobIdAge > tenMinutes || problematicJobIds.includes(charlesState.jobId)) {
                console.log('[CLEANUP] Clearing stale/problematic jobId:', charlesState.jobId, 
                           'Age:', Math.floor(jobIdAge/1000), 'seconds');
                charlesState.jobId = null;
                charlesState.jobIdTimestamp = null;
                cleaned = true;
                cleanedCount++;
            }
        }
        
        // Clear from stateHistory
        if (charlesState.stateHistory && Array.isArray(charlesState.stateHistory)) {
            charlesState.stateHistory.forEach((state, idx) => {
                if (state.jobId && problematicJobIds.includes(state.jobId)) {
                    console.log(`[CLEANUP] Clearing problematic jobId from stateHistory[${idx}]:`, state.jobId);
                    state.jobId = null;
                    state.jobIdTimestamp = null;
                    cleaned = true;
                    cleanedCount++;
                }
                if (state.agentState && state.agentState.jobId && 
                    problematicJobIds.includes(state.agentState.jobId)) {
                    console.log(`[CLEANUP] Clearing problematic agentState.jobId from stateHistory[${idx}]:`, 
                               state.agentState.jobId);
                    state.agentState.jobId = null;
                    cleaned = true;
                    cleanedCount++;
                }
            });
        }
        
        if (cleaned) {
            localStorage.setItem('charles_agent_state', JSON.stringify(charlesState));
            console.log('[CLEANUP] Saved cleaned charles_agent_state');
        }
    } catch (e) {
        console.error('[CLEANUP] Error cleaning charles_agent_state:', e);
    }
    
    // 2. Clear any localStorage entries containing problematic job IDs
    const keysToClean = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        const value = localStorage.getItem(key);
        
        // Check if value contains any problematic job IDs
        for (const jobId of problematicJobIds) {
            if (value && value.includes(jobId)) {
                keysToClean.push(key);
                console.log('[CLEANUP] Found problematic job ID in localStorage:', key);
                break;
            }
        }
    }
    
    // Remove problematic keys
    keysToClean.forEach(key => {
        console.log('[CLEANUP] Removing localStorage key:', key);
        localStorage.removeItem(key);
        cleanedCount++;
    });
    
    if (cleanedCount > 0) {
        console.log(`[CLEANUP] ✓ Cleaned ${cleanedCount} stale/problematic job references`);
    } else {
        console.log('[CLEANUP] ✓ No stale job IDs found');
    }
    
})();