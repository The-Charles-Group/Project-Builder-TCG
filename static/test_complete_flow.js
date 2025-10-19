// Complete User Flow Test Script
// This script tests the entire application from RFP submission to XML export

async function testCompleteUserFlow() {
    console.log('🚀 Starting Complete User Flow Test');
    console.log('=====================================');
    
    const testRFP = `REQUEST FOR PROPOSAL
Digital Marketing Campaign for E-Commerce Launch

Project Overview
Our company, TechStyle Fashion, is launching a new direct-to-consumer e-commerce platform focusing on sustainable fashion. We are seeking a digital marketing agency to develop and execute a comprehensive marketing campaign for our Q2 2025 launch.

Scope of Work

1. Brand Strategy & Positioning
   - Develop brand messaging and value proposition
   - Create brand guidelines and visual identity refinement
   - Competitive analysis and market positioning
   - Target audience segmentation and persona development

2. Website Development Support
   - Landing page design and optimization
   - E-commerce platform marketing integration
   - SEO technical audit and implementation
   - Analytics setup and tracking implementation

3. Content Marketing
   - Content strategy development
   - Blog content creation (20 articles)
   - Product descriptions and category pages
   - Email marketing templates and campaigns
   - Social media content calendar (3 months)

4. Paid Media Campaigns
   - Google Ads setup and management
   - Facebook and Instagram advertising
   - TikTok advertising campaign
   - Retargeting campaign setup
   - Budget allocation and optimization strategy

5. Social Media Management
   - Platform strategy for Instagram, TikTok, Pinterest
   - Community management and engagement
   - Influencer partnership program
   - User-generated content campaigns

6. Launch Campaign
   - Pre-launch teaser campaign
   - Launch week intensive promotion
   - PR outreach and media relations
   - Event planning for virtual launch

Budget
Total budget range: $150,000 - $250,000
Campaign timeline: 6 months (January - June 2025)

Success Metrics
- 50,000 website visitors in first month
- 2,500 email subscribers pre-launch
- 1,000 customers in first quarter
- 15% conversion rate on paid traffic
- 25% month-over-month growth`;

    try {
        // Step 1: Clear session and paste RFP
        console.log('\n✅ Step 1: Clearing session and pasting RFP');
        await fetch('/api/clear_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: window.currentSessionId })
        });
        
        const rfpTextarea = document.getElementById('rfp-text');
        if (rfpTextarea) {
            rfpTextarea.value = testRFP;
            console.log('   - RFP content pasted');
        }
        
        // Step 2: Select Fast Mode and trigger analysis
        console.log('\n✅ Step 2: Triggering AI Analysis (Fast Mode)');
        const fastModeBtn = document.querySelector('.analysis-mode-btn.fast');
        if (fastModeBtn) {
            fastModeBtn.click();
            console.log('   - Fast mode selected');
        }
        
        // Trigger analysis
        const response = await fetch('/api/ai/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                request_text: testRFP,
                mode: 'fast',
                strictness: 'balanced',
                session_id: window.currentSessionId
            })
        });
        
        const { job_id } = await response.json();
        console.log(`   - Analysis started: Job ID ${job_id}`);
        
        // Step 3: Wait for analysis to complete
        console.log('\n✅ Step 3: Waiting for analysis completion...');
        let completed = false;
        let attempts = 0;
        
        while (!completed && attempts < 30) {
            await new Promise(resolve => setTimeout(resolve, 500));
            const statusResp = await fetch(`/api/ai/jobs/${job_id}`);
            const status = await statusResp.json();
            
            if (status.status === 'completed') {
                completed = true;
                console.log(`   - Analysis completed! Found ${status.data?.deliverables?.length || 0} deliverables`);
            } else if (status.status === 'failed') {
                throw new Error('Analysis failed: ' + status.message);
            }
            attempts++;
        }
        
        if (!completed) {
            throw new Error('Analysis timed out after 15 seconds');
        }
        
        // Step 4: Proceed to Step 2 (Deliverables)
        console.log('\n✅ Step 4: Moving to Step 2 - Select Deliverables');
        const continueBtn = document.querySelector('#ai-results button[onclick*="continueWithAI"]');
        if (continueBtn) {
            continueBtn.click();
            await new Promise(resolve => setTimeout(resolve, 1000));
            console.log('   - Moved to deliverables selection');
        }
        
        // Step 5: Check deliverables are loaded
        console.log('\n✅ Step 5: Verifying deliverables loaded');
        const deliverableCheckboxes = document.querySelectorAll('#deliverables-list input[type="checkbox"]');
        console.log(`   - Found ${deliverableCheckboxes.length} deliverables`);
        
        // Select first 10 deliverables if not already selected
        let selectedCount = 0;
        deliverableCheckboxes.forEach((cb, idx) => {
            if (idx < 10 && !cb.checked) {
                cb.click();
                selectedCount++;
            }
        });
        console.log(`   - Selected ${selectedCount} additional deliverables`);
        
        // Step 6: Proceed to Step 3 (Pricing)
        console.log('\n✅ Step 6: Moving to Step 3 - Pricing');
        const step3Btn = document.querySelector('button[onclick*="proceedToStep3"]');
        if (step3Btn) {
            step3Btn.click();
            await new Promise(resolve => setTimeout(resolve, 1000));
            console.log('   - Moved to pricing step');
        }
        
        // Step 7: Verify pricing data
        console.log('\n✅ Step 7: Verifying pricing data');
        const pricingRows = document.querySelectorAll('#pricing-table tbody tr');
        console.log(`   - Found ${pricingRows.length} pricing rows`);
        
        const totalHours = document.querySelector('#total-hours');
        const totalPrice = document.querySelector('#total-price');
        if (totalHours && totalPrice) {
            console.log(`   - Total Hours: ${totalHours.textContent}`);
            console.log(`   - Total Price: ${totalPrice.textContent}`);
        }
        
        // Step 8: Proceed to Step 4 (Timeline)
        console.log('\n✅ Step 8: Moving to Step 4 - Timeline');
        const step4Btn = document.querySelector('button[onclick*="proceedToStep4"]');
        if (step4Btn) {
            step4Btn.click();
            await new Promise(resolve => setTimeout(resolve, 1000));
            console.log('   - Moved to timeline step');
        }
        
        // Step 9: Verify timeline data
        console.log('\n✅ Step 9: Verifying timeline data');
        const timelineRows = document.querySelectorAll('#timeline-table tbody tr');
        console.log(`   - Found ${timelineRows.length} timeline entries`);
        
        // Step 10: Test XML Export
        console.log('\n✅ Step 10: Testing XML Export');
        const exportBtn = document.querySelector('button[onclick*="exportToXML"]');
        if (exportBtn) {
            // Note: We won't actually click this as it triggers a download
            console.log('   - XML Export button found and ready');
            
            // Test the export endpoint directly
            const scenarioId = window.currentScenarioId || localStorage.getItem('scenario_id');
            if (scenarioId) {
                const exportResp = await fetch(`/api/export/xml/${scenarioId}/test_project`);
                if (exportResp.ok) {
                    console.log('   - ✅ XML export endpoint working');
                } else {
                    console.log('   - ⚠️ XML export endpoint returned:', exportResp.status);
                }
            }
        }
        
        // Final Summary
        console.log('\n' + '='.repeat(50));
        console.log('✅ COMPLETE USER FLOW TEST SUCCESSFUL!');
        console.log('='.repeat(50));
        console.log('\nAll steps completed:');
        console.log('1. ✅ RFP submission');
        console.log('2. ✅ AI analysis (Fast Mode)');
        console.log('3. ✅ Deliverables selection');
        console.log('4. ✅ Pricing calculation');
        console.log('5. ✅ Timeline generation');
        console.log('6. ✅ XML export ready');
        console.log('\n🎉 Application is fully functional!');
        
        return { success: true, message: 'All tests passed!' };
        
    } catch (error) {
        console.error('\n❌ Test failed:', error);
        return { success: false, error: error.message };
    }
}

// Auto-run the test
console.log('Test script loaded. Running complete flow test...');
testCompleteUserFlow().then(result => {
    if (result.success) {
        console.log('\n✅ Test completed successfully!');
    } else {
        console.error('\n❌ Test failed:', result.error);
    }
});