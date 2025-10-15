#!/usr/bin/env python3
"""
Test RFP Processing with 100+ Deliverables
Tests the complete flow: API call -> Job processing -> Result retrieval
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any
import sys

# API Configuration
API_BASE_URL = "http://localhost:5000"

# Sample RFP text for luxury fashion brand
SAMPLE_RFP_TEXT = """
LUXURY FASHION BRAND RFP - Comprehensive Digital Marketing Services

We are a leading luxury fashion house seeking a full-service digital marketing agency for our 2025 global campaign. 

SCOPE OF WORK:
1. Brand Strategy & Positioning
   - Global brand strategy development
   - Market research and consumer insights
   - Competitive analysis and positioning
   - Brand architecture and portfolio strategy
   - Brand guidelines and governance

2. Creative Development
   - Campaign creative concepting
   - Art direction and visual design
   - Video production (hero films, social content)
   - Photography (product, lifestyle, editorial)
   - Motion graphics and animation
   - CGI and 3D rendering

3. Digital Marketing
   - Website design and development
   - E-commerce optimization
   - SEO and SEM strategy
   - Email marketing automation
   - CRM integration and personalization
   - Marketing automation setup

4. Social Media Marketing
   - Social media strategy across all platforms
   - Content creation and curation
   - Community management
   - Influencer marketing campaigns
   - Social commerce integration
   - Live streaming and virtual events

5. Paid Media
   - Media planning and buying
   - Programmatic advertising
   - Search advertising (Google, Bing)
   - Social media advertising
   - Display and video advertising
   - Retail media networks

6. Content Marketing
   - Editorial content strategy
   - Blog and magazine content
   - Video content series
   - Podcast production
   - User-generated content campaigns
   - Brand storytelling

7. Technology & Analytics
   - MarTech stack assessment
   - Data analytics and reporting
   - Attribution modeling
   - Customer data platform setup
   - AI and machine learning integration
   - Marketing mix modeling

8. Public Relations
   - PR strategy and planning
   - Media relations
   - Press release writing
   - Event marketing
   - Crisis management planning
   - Awards and recognition campaigns

9. Retail & Experience
   - In-store digital experiences
   - Pop-up store concepts
   - Virtual showroom development
   - AR/VR experiences
   - Clienteling tools
   - Retail analytics

10. International Markets
    - Localization for 15+ markets
    - Cultural adaptation
    - Regional campaign development
    - Local influencer partnerships
    - Market-specific strategies

DELIVERABLES NEEDED:
- Comprehensive brand audit
- Annual marketing strategy
- Creative campaign concepts
- Media plans by market
- Content calendars
- Technology roadmap
- Analytics dashboards
- Monthly performance reports
- Quarterly business reviews

BUDGET: $25-30 million annually
TIMELINE: 12-month retainer starting Q1 2025
MARKETS: US, UK, France, Italy, China, Japan, Korea, Middle East
"""

async def test_rfp_processing():
    """Test the complete RFP processing pipeline"""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("\n" + "="*80)
        print("🚀 TESTING RFP PROCESSING WITH 100+ DELIVERABLES")
        print("="*80 + "\n")
        
        # Step 1: Submit RFP for analysis
        print("📝 Step 1: Submitting RFP for AI analysis...")
        print(f"   RFP length: {len(SAMPLE_RFP_TEXT)} characters")
        
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/ai/analyze",
                json={
                    "request_text": SAMPLE_RFP_TEXT,
                    "strictness": "balanced",
                    "mode": "deep",
                    "tier": "thinking"
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to submit RFP: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
            job_info = response.json()
            job_id = job_info.get("job_id")
            
            if not job_id:
                print("❌ No job_id returned from API")
                return False
                
            print(f"✅ Job created: {job_id}")
            
        except Exception as e:
            print(f"❌ Error submitting RFP: {e}")
            return False
        
        # Step 2: Poll for job completion
        print("\n📊 Step 2: Monitoring job progress...")
        
        start_time = time.time()
        max_wait = 240  # 4 minutes timeout (increased for GPT-5 processing)
        poll_interval = 3  # seconds (reduced polling frequency)
        
        while time.time() - start_time < max_wait:
            try:
                status_response = await client.get(
                    f"{API_BASE_URL}/api/ai/jobs/{job_id}"
                )
                
                if status_response.status_code == 404:
                    print(f"❌ Job {job_id} not found")
                    return False
                
                if status_response.status_code != 200:
                    print(f"❌ Status check failed: {status_response.status_code}")
                    return False
                
                status = status_response.json()
                
                # Print progress update
                progress = status.get("progress", 0)
                stage = status.get("current_stage", "Processing...")
                elapsed = status.get("elapsed_seconds", 0)
                print(f"   Progress: {progress}% - {stage} (elapsed: {elapsed:.1f}s)")
                
                # Check if completed
                if status.get("status") == "completed":
                    print(f"✅ Job completed in {elapsed:.1f} seconds")
                    
                    # Step 3: Analyze results
                    print("\n📋 Step 3: Analyzing results...")
                    
                    result = status.get("result", {})
                    if not result:
                        print("❌ No result data in completed job")
                        return False
                    
                    plan = result.get("plan", {})
                    suggestions = plan.get("suggestions_by_department", {})
                    
                    # Count total deliverables
                    total_deliverables = 0
                    dept_counts = {}
                    
                    for dept, items in suggestions.items():
                        count = len(items)
                        total_deliverables += count
                        dept_counts[dept] = count
                    
                    print(f"\n   📊 DELIVERABLES SUMMARY:")
                    print(f"   {'='*50}")
                    print(f"   Total Deliverables: {total_deliverables}")
                    print(f"   {'='*50}")
                    
                    # Show breakdown by department
                    print(f"\n   Department Breakdown:")
                    for dept, count in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True):
                        bar = "█" * min(count, 50)
                        print(f"   {dept:30} {count:3} {bar}")
                    
                    # Check diagnostics
                    diagnostics = result.get("diagnostics", {})
                    print(f"\n   📈 DIAGNOSTICS:")
                    print(f"   Mode: {diagnostics.get('mode', 'N/A')}")
                    print(f"   Candidates considered: {diagnostics.get('candidates_considered', 0)}")
                    print(f"   Catalog items: {diagnostics.get('catalog_items', 0)}")
                    print(f"   Deliverables selected: {diagnostics.get('deliverables_selected', 0)}")
                    print(f"   Deliverables in plan: {diagnostics.get('deliverables_in_plan', 0)}")
                    print(f"   Tasks AI selected: {diagnostics.get('tasks_ai_selected', 0)}")
                    print(f"   Rescue triggered: {diagnostics.get('rescue_triggered', False)}")
                    print(f"   LLM scores available: {diagnostics.get('llm_scores_available', False)}")
                    
                    # Validate results
                    print(f"\n   🎯 VALIDATION:")
                    
                    if total_deliverables >= 100:
                        print(f"   ✅ SUCCESS: {total_deliverables} deliverables (>= 100 required)")
                        success = True
                    else:
                        print(f"   ❌ FAILURE: Only {total_deliverables} deliverables (< 100 required)")
                        success = False
                    
                    # Sample some deliverables
                    print(f"\n   📝 SAMPLE DELIVERABLES (first 5):")
                    sample_count = 0
                    for dept, items in suggestions.items():
                        for item in items[:2]:  # Show 2 from each department
                            if sample_count >= 5:
                                break
                            sample_count += 1
                            name = item.get("name", item.get("title", "Unknown"))
                            confidence = item.get("confidence", 0)
                            print(f"   {sample_count}. [{dept}] {name} (confidence: {confidence:.0%})")
                    
                    return success
                
                elif status.get("status") == "failed":
                    error = status.get("error", "Unknown error")
                    print(f"❌ Job failed: {error}")
                    return False
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                print(f"❌ Error checking status: {e}")
                await asyncio.sleep(poll_interval)
        
        print(f"⏱️ Timeout: Job did not complete within {max_wait} seconds")
        return False

async def main():
    """Main test runner"""
    try:
        # Check if server is running
        async with httpx.AsyncClient() as client:
            try:
                health = await client.get(f"{API_BASE_URL}/api/health")
                if health.status_code != 200:
                    print("❌ Server is not responding correctly")
                    return 1
            except:
                print("❌ Cannot connect to server at http://localhost:5000")
                print("   Please ensure the FastAPI server is running")
                return 1
        
        # Run the test
        success = await test_rfp_processing()
        
        print("\n" + "="*80)
        if success:
            print("✅ ALL TESTS PASSED - RFP PROCESSING WORKING CORRECTLY")
            print("   The system successfully generated 100+ deliverables!")
            return 0
        else:
            print("❌ TEST FAILED - RFP PROCESSING NEEDS FIXES")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)