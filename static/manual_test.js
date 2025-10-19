// Manual test script - run this in browser console
(function() {
    console.log('=== MANUAL TEST STARTING ===');
    
    // 1. Insert RFP content
    const rfpContent = `REQUEST FOR PROPOSAL
Digital Marketing Campaign for E-Commerce Launch

Project Overview
Our company, TechStyle Fashion, is launching a new direct-to-consumer e-commerce platform focusing on sustainable fashion. We are seeking a digital marketing agency to develop and execute a comprehensive marketing campaign for our Q2 2025 launch.

Scope of Work
1. Brand Strategy & Positioning
2. Website Development Support  
3. Content Marketing
4. Paid Media Campaigns
5. Social Media Management
6. Launch Campaign

Budget: $150,000 - $250,000
Timeline: 6 months (January - June 2025)`;

    const rfpTextArea = document.getElementById('rfpText');
    if (rfpTextArea) {
        rfpTextArea.value = rfpContent;
        console.log('✅ RFP content inserted');
        
        // 2. Click the Analyze button
        const analyzeBtn = document.getElementById('btnAnalyze');
        if (analyzeBtn) {
            console.log('✅ Clicking Analyze button...');
            analyzeBtn.click();
        } else {
            console.error('❌ Analyze button not found');
        }
    } else {
        console.error('❌ RFP textarea not found');
    }
})();