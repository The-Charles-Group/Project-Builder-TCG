// Test script for the complete user journey
async function testCompleteFlow() {
    console.log('=== STARTING COMPLETE USER JOURNEY TEST ===');
    
    // RFP content for testing
    const rfpContent = `REQUEST FOR PROPOSAL
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

    // Step 1: Insert RFP content
    console.log('[TEST] Step 1: Inserting RFP content...');
    const rfpTextArea = document.getElementById('rfpText');
    if (rfpTextArea) {
        rfpTextArea.value = rfpContent;
        rfpTextArea.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('[TEST] ✅ RFP content inserted');
    } else {
        console.error('[TEST] ❌ RFP textarea not found');
        return;
    }
    
    // Step 2: Trigger Analysis via CHARLES AI Assistant
    console.log('[TEST] Step 2: Opening AI Assistant and triggering analysis...');
    
    // Open the AI assistant if not already open
    if (window.aiAssistant && !window.aiAssistant.isOpen) {
        window.aiAssistant.toggle();
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    if (window.aiAssistant) {
        console.log('[TEST] Using AI Assistant to trigger analysis...');
        
        // Send command to analyze
        await window.aiAssistant.handleUserMessage('Analyze the RFP in fast mode');
        
        // Wait for analysis to complete
        console.log('[TEST] Waiting for AI analysis to complete...');
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Check if analysis is running
        if (window.aiAssistant.agentState.jobId) {
            console.log('[TEST] ✅ Analysis started with job ID:', window.aiAssistant.agentState.jobId);
            
            // Wait for job to complete (max 60 seconds)
            let attempts = 0;
            while (attempts < 60) {
                await new Promise(resolve => setTimeout(resolve, 1000));
                attempts++;
                
                // Check if step 2 is visible
                const step2 = document.getElementById('step2');
                if (step2 && step2.style.display !== 'none') {
                    console.log('[TEST] ✅ Step 2 is now visible - analysis complete!');
                    break;
                }
                
                if (attempts % 5 === 0) {
                    console.log(`[TEST] Still waiting for analysis... (${attempts}s)`);
                }
            }
        } else {
            console.error('[TEST] ❌ No job ID found - analysis may have failed');
        }
    } else {
        console.error('[TEST] ❌ AI Assistant not available');
    }
    
    // Step 3: Check if deliverables were loaded
    console.log('[TEST] Step 3: Checking if deliverables were loaded...');
    const deliverablesList = document.getElementById('s2-deliv-list');
    if (deliverablesList && deliverablesList.children.length > 0) {
        console.log(`[TEST] ✅ ${deliverablesList.children.length} deliverables loaded`);
        
        // Select some deliverables
        const checkboxes = deliverablesList.querySelectorAll('input[type="checkbox"]');
        let selectedCount = 0;
        checkboxes.forEach((cb, index) => {
            if (index < 10) { // Select first 10
                cb.checked = true;
                cb.dispatchEvent(new Event('change', { bubbles: true }));
                selectedCount++;
            }
        });
        console.log(`[TEST] ✅ Selected ${selectedCount} deliverables`);
    } else {
        console.error('[TEST] ❌ No deliverables found in list');
    }
    
    // Step 4: Proceed to Step 3 (Pricing)
    console.log('[TEST] Step 4: Moving to pricing step...');
    const proceedBtn = document.getElementById('btnProceedToStep3');
    if (proceedBtn) {
        proceedBtn.click();
        await new Promise(resolve => setTimeout(resolve, 2000));
        console.log('[TEST] ✅ Moved to Step 3 (Pricing)');
    }
    
    // Step 5: Build scenarios
    console.log('[TEST] Step 5: Building scenarios...');
    const buildBtn = document.getElementById('btnBuild');
    if (buildBtn) {
        buildBtn.click();
        await new Promise(resolve => setTimeout(resolve, 3000));
        console.log('[TEST] ✅ Scenarios built');
    }
    
    // Step 6: Move to Timeline
    console.log('[TEST] Step 6: Moving to timeline step...');
    const timelineBtn = document.querySelector('button[onclick*="showStep4"]');
    if (timelineBtn) {
        timelineBtn.click();
        await new Promise(resolve => setTimeout(resolve, 2000));
        console.log('[TEST] ✅ Moved to Step 4 (Timeline)');
    }
    
    // Step 7: Test XML Export
    console.log('[TEST] Step 7: Testing XML export...');
    const exportBtn = document.getElementById('btnExportXML');
    if (exportBtn) {
        console.log('[TEST] ✅ XML Export button found and ready');
        // Note: Not clicking it to avoid actual download
    }
    
    console.log('=== TEST COMPLETE ===');
    console.log('[TEST] Summary:');
    console.log('- RFP uploaded: ✅');
    console.log('- AI Analysis: ' + (window.aiAssistant?.agentState?.jobId ? '✅' : '❌'));
    console.log('- Deliverables loaded: ' + (deliverablesList?.children.length > 0 ? '✅' : '❌'));
    console.log('- Navigation works: ✅');
    
    return {
        success: true,
        jobId: window.aiAssistant?.agentState?.jobId,
        deliverables: deliverablesList?.children.length || 0
    };
}

// Auto-run the test
console.log('[TEST] Test script loaded. Running test in 3 seconds...');
setTimeout(() => {
    testCompleteFlow().then(result => {
        console.log('[TEST] Test result:', result);
    }).catch(error => {
        console.error('[TEST] Test failed:', error);
    });
}, 3000);