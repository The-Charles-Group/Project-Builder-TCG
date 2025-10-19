// Utility script to stop phantom job polling
// Can be executed in browser console or added to the page

(function stopPhantomPolling() {
    console.log('[STOP POLLING] Executing emergency stop for phantom job polling...');
    
    // Stop all intervals in a range (brute force)
    for (let i = 1; i < 10000; i++) {
        try {
            clearInterval(i);
        } catch (e) {
            // Ignore errors
        }
    }
    
    // Clear specific known intervals
    if (window.aiAnalysisInterval) {
        clearInterval(window.aiAnalysisInterval);
        window.aiAnalysisInterval = null;
        console.log('[STOP POLLING] Cleared aiAnalysisInterval');
    }
    
    // Clear aiAnalysisJobId
    if (window.aiAnalysisJobId) {
        console.log('[STOP POLLING] Clearing aiAnalysisJobId:', window.aiAnalysisJobId);
        window.aiAnalysisJobId = null;
    }
    
    // Clear from AI assistant
    if (window.aiAssistant) {
        if (window.aiAssistant.currentPollInterval) {
            clearInterval(window.aiAssistant.currentPollInterval);
            window.aiAssistant.currentPollInterval = null;
            console.log('[STOP POLLING] Cleared AI assistant poll interval');
        }
        window.aiAssistant.agentState.jobId = null;
    }
    
    // Clear from localStorage
    const savedState = localStorage.getItem('charles_agent_state');
    if (savedState) {
        try {
            const state = JSON.parse(savedState);
            if (state && state.jobId) {
                console.log('[STOP POLLING] Clearing job ID from localStorage:', state.jobId);
                state.jobId = null;
                state.jobIdTimestamp = null;
                localStorage.setItem('charles_agent_state', JSON.stringify(state));
            }
        } catch (e) {
            console.error('[STOP POLLING] Failed to clear localStorage:', e);
        }
    }
    
    // Reset consecutive 404 counter
    window.consecutive404Count = 0;
    
    console.log('[STOP POLLING] ✅ All phantom polling should be stopped now');
    console.log('[STOP POLLING] If polling continues, refresh the page or check for other sources');
})();