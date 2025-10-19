// Test script to verify AI assistant polling is working
console.log('🧪 Testing AI Assistant Polling Fix...\n');

async function testAIPolling() {
    // Wait for Charles to be ready
    if (!window.charles) {
        console.log('Waiting for CHARLES to initialize...');
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    const testRFP = `We need a digital marketing campaign including:
    - Social media management
    - Paid media campaigns  
    - Content creation
    - Email marketing
    - Website optimization`;
    
    // Set the RFP text
    const rfpTextarea = document.getElementById('rfp-text');
    if (rfpTextarea) {
        rfpTextarea.value = testRFP;
        console.log('✅ RFP text set');
    }
    
    // Trigger analysis directly through CHARLES
    if (window.charles && window.charles.triggerAnalysis) {
        console.log('\n📤 Triggering AI analysis through CHARLES...');
        await window.charles.triggerAnalysis('fast');
        
        // Monitor the polling
        console.log('\n👁️ Monitoring polling status...');
        let checkCount = 0;
        const checkInterval = setInterval(() => {
            checkCount++;
            
            // Check if polling is active
            const pollInterval = window.charles?.currentPollInterval;
            const jobId = window.charles?.agentState?.jobId;
            
            console.log(`[Check ${checkCount}] Polling active: ${!!pollInterval}, Job ID: ${jobId || 'none'}`);
            
            // Check progress bar
            const progressBar = document.getElementById('charles-main-progress-bar');
            if (progressBar) {
                const width = progressBar.style.width;
                console.log(`   Progress: ${width}`);
            }
            
            if (checkCount >= 10) {
                clearInterval(checkInterval);
                console.log('\n📊 Test complete!');
                
                if (pollInterval) {
                    console.log('✅ POLLING IS WORKING - Fix successful!');
                } else {
                    console.log('❌ POLLING NOT ACTIVE - Fix failed');
                }
            }
        }, 1000);
        
    } else {
        console.error('❌ CHARLES not available or triggerAnalysis method missing');
    }
}

// Run the test
testAIPolling();