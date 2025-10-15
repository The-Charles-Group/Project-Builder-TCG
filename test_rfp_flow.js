// Test script for Uncommon Schools RFP flow
// This script will test the complete journey: RFP upload -> GPT-5 analysis -> Build scenario -> AI optimize -> Timeline -> Export

const RFP_CONTENT = `Media Agency Request For Proposal
May 2025

I. Introduction and Background
1.1 Introduction
Uncommon Schools is a non-profit network of 52 outstanding public charter schools in grades K-12 across New York, New Jersey, and Massachusetts. Our mission is to start and manage outstanding urban public charter schools that close the opportunity gap and prepare students from low-income backgrounds for success in college and beyond.

Years ago, the demand for and opening of Charter schools and networks saw consistent growth. In recent years, however, that growth has slowed. Charter schools and networks have faced challenges due to several factors, including reduced teacher talent as fewer graduates enter teacher training programs, new charter entrants filling the category, demographic shifts as families are priced out of urban areas, and reduced student population as Millennials have children later and less often.

As the competition for students and staff intensifies, we require effective, innovative, and data-driven paid media strategies that set us apart in a mature, crowded category.

1.2 About Uncommon Schools
For over 25 years, Uncommon Schools has been making education history by sending thousands of first-generation students to and through college. We provide outstanding PreK-12 education and the joyful, rigorous environment that students deserve to succeed in college and on their path to economic freedom.

Uncommon Schools by the Numbers:
• 25-year history (we're pioneers in the space)
• 5 regions: Brooklyn and Rochester, NY; Newark and Camden, NJ; and Boston, MA
• 20,000 students
• 52 schools serving Pre-K through 12th grade
• 85% of students are considered economically disadvantaged
• 70% of staff identify as people of color

1.3 Project Overview
This RFP will help us identify a media planning agency that can effectively support our organization in achieving our marketing and communication goals. We seek a partner who understands our unique brand, target audience, and market dynamics.

The selected agency will develop, execute, and regularly optimize a comprehensive paid media strategy aligned with our business objectives. This includes conducting thorough market research, identifying optimal media channels, and creating innovative campaigns to enhance our brand visibility and engagement.

1.4 Objectives and Goals
We are looking for a strong agency partner to support us in achieving our 5-year ambitions:
• Enhance Brand Awareness & Perception: Increase brand visibility and positive perceptions among current and prospective families and teachers. Goal: Achieve a 40% increase in high-quality leads for both teacher recruitment and student enrollment over the next five years.
• Drive Enrollment & Retention: Strengthen our recruitment strategies to ensure complete enrollment across all schools. Goal: Attain over 95% enrollment capacity for new schools and ensure 85% year-over-year persistence rates in every region by 2030.
• Measure & Optimize Campaign Effectiveness: Implement a robust measurement framework to evaluate campaign performance. Goal: Establish a real-time analytics dashboard within the first year of engagement.

1.5 Target Audience
Audience: Parents of preK-12 students, PreK-12 teachers and operations staff
Markets: Brooklyn, Rochester, Camden, Newark, Boston
Demographics:
• Parent Audience: Typically Black, Hispanic, Low/Moderate Income with school-aged children, particularly children aged 5-15
• Teacher Audience: College Degree Required, Master's Degree Optional; Career-changers and recent college graduates

1.6 Current Paid Media Tactics
Current channels include:
Paid: Meta, Google Search, Google Ad Grant, YouTube/Streaming TV, Streaming audio, Programmatic web ads, Out of Home, Direct Mail, Email Marketing, Indeed, LinkedIn
Owned: Social Media (FB, IG, YT, LinkedIn), Website, Email/CRM, OOH via school buildings, School Uniforms
Earned: News media coverage featuring student success stories, Placement of Uncommon-authored pieces/Op-Eds

II. Scope of Work and Requirements
2.1 Specific Services Required:
• Media Planning & Strategy Development
• Campaign Creation & Execution
• Performance Monitoring & Optimization
• Reporting & Analytics
• Creative Development Support`;

async function testRFPFlow() {
  console.log('Starting Uncommon Schools RFP test flow...');
  
  // Step 1: Paste RFP content
  const rfpTextarea = document.getElementById('rfpText');
  if (rfpTextarea) {
    rfpTextarea.value = RFP_CONTENT;
    console.log('✅ Step 1: RFP content pasted');
    
    // Store in session for later retrieval
    sessionStorage.setItem('apb.rfp_text', RFP_CONTENT);
  }
  
  // Set project details
  const projectName = document.getElementById('projectName');
  if (projectName) projectName.value = 'Uncommon Schools Media Campaign 2025';
  
  const clientBudget = document.getElementById('clientBudget');
  if (clientBudget) clientBudget.value = '500000';
  
  console.log('✅ Project details set');
  
  // Click Deep Mode for comprehensive analysis
  const deepModeBtn = document.querySelector('[onclick*="analyzeRFP(\'deep\')"]');
  if (deepModeBtn) {
    console.log('🔄 Starting Deep Mode GPT-5 Analysis...');
    // Note: Would click button here in real test
    // deepModeBtn.click();
  }
  
  console.log(`
Test Setup Complete! 

To complete the test flow:
1. Click "Deep Mode" to analyze the RFP with GPT-5
2. Wait for AI suggestions to appear
3. Select deliverables for Media Planning, Campaign Creation, Analytics
4. Click "Build Scenario" 
5. Use "AI Suggest Type" to classify deliverables
6. Use "Optimize All Pricing" with $500K budget
7. Generate AI Timeline
8. Export to XML

Expected Results:
- GPT-5 should identify key deliverables for media agency work
- Scenario should include mix of PROJECT and RETAINER items
- Timeline should show logical dependencies
- Resource Risk table should identify any gaps
- XML export should include all data
  `);
}

// Run test
testRFPFlow();