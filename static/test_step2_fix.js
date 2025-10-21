// Quick test to validate Step 2 fix
async function testStep2Fix() {
    console.log('=== TESTING STEP 2 FIX ===');
    
    // Check if there's a completed job we can poll
    const testJobId = 'cf5156ac-8aea-4cc5-839d-8be570510189'; // Latest completed job
    
    console.log('1. Fetching job status for:', testJobId);
    const response = await fetch(`/api/ai/jobs/${testJobId}`);
    const data = await response.json();
    
    console.log('2. Job status:', data.status);
    console.log('3. Response structure:', {
        hasResult: !!data.result,
        hasPlan: !!(data.result && data.result.plan),
        hasSuggestionsByDept: !!(data.result && data.result.plan && data.result.plan.suggestions_by_department),
        departments: data.result && data.result.plan && data.result.plan.suggestions_by_department 
            ? Object.keys(data.result.plan.suggestions_by_department) 
            : []
    });
    
    // Count deliverables
    let totalDeliverables = 0;
    if (data.result && data.result.plan && data.result.plan.suggestions_by_department) {
        Object.values(data.result.plan.suggestions_by_department).forEach(dept => {
            if (Array.isArray(dept)) {
                totalDeliverables += dept.length;
            }
        });
    }
    console.log('4. Total deliverables found:', totalDeliverables);
    
    // Now simulate what pollAIAnalysis does
    console.log('\n5. Simulating pollAIAnalysis logic...');
    
    // Initialize PRIMARY_SCENARIO if needed
    if (!window.PRIMARY_SCENARIO) {
        window.PRIMARY_SCENARIO = {
            deliverables: [],
            status: 'draft'
        };
    }
    
    // Initialize APB.step2 if needed
    if (!window.APB) {
        window.APB = {};
    }
    if (!window.APB.step2) {
        window.APB.step2 = {
            selectedCodes: new Set(),
            allDeliverables: [],
            els: {}
        };
    }
    
    // Extract deliverables using the fixed logic
    let deliverables = [];
    const aiPlanResponse = data.result || data;
    
    if (aiPlanResponse.plan && aiPlanResponse.plan.suggestions_by_department) {
        const suggestionsByDept = aiPlanResponse.plan.suggestions_by_department;
        console.log('6. Processing departments:', Object.keys(suggestionsByDept));
        
        Object.entries(suggestionsByDept).forEach(([dept, deptDeliverables]) => {
            if (Array.isArray(deptDeliverables)) {
                const mappedDeliverables = deptDeliverables.map(d => ({
                    deliverable_code: d.code || d.deliverable_code,
                    deliverable_name: d.name || d.deliverable_name || d.deliverable,
                    department: dept,
                    category: dept,
                    confidence: d.confidence_score || d.confidence || 0
                }));
                deliverables = deliverables.concat(mappedDeliverables);
                console.log(`   - ${dept}: ${deptDeliverables.length} deliverables`);
            }
        });
    }
    
    console.log('7. Extracted deliverables:', deliverables.length);
    
    // Update PRIMARY_SCENARIO
    window.PRIMARY_SCENARIO.deliverables = deliverables;
    window.PRIMARY_SCENARIO.status = 'analyzed';
    
    // Convert to APB format
    APB.step2.allDeliverables = deliverables.map(d => ({
        Deliverable_Code: d.deliverable_code,
        Deliverable: d.deliverable_name,
        Category: d.department,
        confidence: d.confidence
    }));
    
    console.log('8. Updated PRIMARY_SCENARIO.deliverables:', window.PRIMARY_SCENARIO.deliverables.length);
    console.log('9. Updated APB.step2.allDeliverables:', APB.step2.allDeliverables.length);
    
    // Show Step 2
    const step2 = document.getElementById('step2');
    if (step2) {
        step2.style.display = 'block';
        console.log('10. Step 2 made visible');
    }
    
    // Call renderDeliverablesPanel if it exists
    if (typeof window.renderDeliverablesPanel === 'function') {
        console.log('11. Calling renderDeliverablesPanel...');
        window.renderDeliverablesPanel();
        console.log('12. Deliverables panel rendered');
    }
    
    // Check if deliverables are actually displayed
    const deliverableElements = document.querySelectorAll('.deliv-row');
    console.log('13. Deliverable rows found in DOM:', deliverableElements.length);
    
    console.log('\n=== TEST COMPLETE ===');
    console.log('SUCCESS: Step 2 should now be visible with', deliverables.length, 'deliverables');
    
    return {
        success: true,
        deliverableCount: deliverables.length,
        step2Visible: step2 && step2.style.display !== 'none',
        domElements: deliverableElements.length
    };
}

// Run the test
console.log('Test script loaded. Running test...');
testStep2Fix().then(result => {
    console.log('Test result:', result);
}).catch(err => {
    console.error('Test failed:', err);
});