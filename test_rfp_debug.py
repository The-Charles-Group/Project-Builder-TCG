#!/usr/bin/env python3
"""Debug test for RFP analysis - checks GPT-5 and comprehensive deliverable generation"""

import asyncio
import httpx
import json
import time

API_BASE_URL = "http://localhost:5000"

# Sample comprehensive RFP text
COMPREHENSIVE_RFP = """
Luxury Fashion House Annual Marketing Retainer

We are seeking a comprehensive agency partner for our luxury fashion brand's 
global marketing initiatives. This annual retainer covers:

Scope of Work:
- Global brand strategy and positioning across 15 markets
- Seasonal campaign development (4 collections per year)
- Digital and social media management across all channels
- Influencer partnerships and celebrity collaborations
- Retail and e-commerce marketing
- Event marketing for fashion weeks in Paris, Milan, New York, Tokyo
- Content creation including photography, video, and editorial
- Paid media management with $50M annual budget
- Brand partnerships and collaborations
- Customer experience and loyalty programs
- Data analytics and insights
- Marketing technology implementation

Markets: USA, UK, France, Italy, Germany, China, Japan, Korea, UAE, Australia
Channels: Digital, Social, Retail, E-commerce, Events, PR, Influencer
Timeline: 12-month retainer starting Q1 2025
Budget: $10M agency fees + $50M media spend

We need comprehensive deliverables covering all aspects of luxury fashion 
marketing including creative development, production, media planning and buying, 
digital marketing, social media, influencer relations, events, retail marketing, 
and ongoing optimization.
"""

async def test_rfp_analysis():
    """Test the full RFP analysis pipeline"""
    print("="*80)
    print("RFP ANALYSIS DEBUG TEST")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Step 1: Submit RFP for analysis
        print("\n1. Submitting RFP for analysis...")
        print(f"   RFP Length: {len(COMPREHENSIVE_RFP)} characters")
        
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/ai/analyze",
                json={
                    "request_text": COMPREHENSIVE_RFP,
                    "mode": "deep",  # Use deep mode to trigger GPT-5
                    "tier": "thinking",  # Use thinking tier for comprehensive analysis
                    "strictness": "balanced"
                }
            )
            response.raise_for_status()
            result = response.json()
            job_id = result.get("job_id")
            print(f"   ✓ Job started: {job_id}")
            
        except Exception as e:
            print(f"   ✗ Failed to start analysis: {e}")
            return
        
        # Step 2: Poll for job completion
        print("\n2. Waiting for analysis to complete...")
        max_wait = 60  # seconds
        poll_interval = 2
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait:
            try:
                status_response = await client.get(f"{API_BASE_URL}/api/ai/jobs/{job_id}")
                status_response.raise_for_status()
                job_status = status_response.json()
                
                status = job_status.get("status")
                stage = job_status.get("current_stage", "")
                progress = job_status.get("progress", {})
                
                print(f"   Status: {status} - {stage}")
                
                if status == "completed":
                    print("   ✓ Analysis completed!")
                    break
                elif status == "failed":
                    error = job_status.get("error", "Unknown error")
                    print(f"   ✗ Analysis failed: {error}")
                    return
                    
            except Exception as e:
                print(f"   ✗ Error checking status: {e}")
                
            await asyncio.sleep(poll_interval)
        
        if status != "completed":
            print(f"   ✗ Analysis timed out after {max_wait} seconds")
            return
        
        # Step 3: Get the results
        print("\n3. Retrieving analysis results...")
        try:
            result_response = await client.get(f"{API_BASE_URL}/api/ai/jobs/{job_id}/result")
            result_response.raise_for_status()
            analysis_result = result_response.json()
            
            # Check if we have results
            if not analysis_result:
                print("   ✗ No results returned")
                return
                
            # Analyze the results
            plan = analysis_result.get("plan", {})
            suggestions = plan.get("suggestions_by_department", {})
            diagnostics = analysis_result.get("diagnostics", {})
            
            print("\n4. Analysis Results Summary:")
            print(f"   Mode: {diagnostics.get('mode', 'unknown')}")
            print(f"   Candidates considered: {diagnostics.get('candidates_considered', 0)}")
            print(f"   Filtered candidates: {diagnostics.get('filtered_candidates', 0)}")
            print(f"   Selected candidates: {diagnostics.get('selected_candidates', 0)}")
            print(f"   GPT-5 used: {diagnostics.get('llm_used', False)}")
            print(f"   Fallback used: {diagnostics.get('fallback_used', False)}")
            
            # Count deliverables
            total_deliverables = 0
            dept_counts = {}
            
            for dept, items in suggestions.items():
                dept_count = len(items) if isinstance(items, list) else 0
                dept_counts[dept] = dept_count
                total_deliverables += dept_count
            
            print("\n5. Deliverable Counts by Department:")
            for dept, count in dept_counts.items():
                print(f"   {dept}: {count} deliverables")
            
            print(f"\n   TOTAL DELIVERABLES: {total_deliverables}")
            
            # Check for comprehensive RFP expansion
            if total_deliverables < 100:
                print(f"\n   ⚠️ WARNING: Only {total_deliverables} deliverables returned (expected 100+)")
                print("   Possible issues:")
                print("   - expand_deliverables_for_comprehensive_rfp() not called")
                print("   - GPT-5 not returning enough items")
                print("   - Filtering too aggressive")
            else:
                print(f"\n   ✓ SUCCESS: {total_deliverables} deliverables returned!")
            
            # Check if expand_deliverables_for_comprehensive_rfp was called
            if diagnostics.get("expansion_applied"):
                print("\n   ✓ Comprehensive RFP expansion was applied")
            else:
                print("\n   ✗ Comprehensive RFP expansion was NOT applied")
            
            # Save results for inspection
            with open("rfp_analysis_debug.json", "w") as f:
                json.dump(analysis_result, f, indent=2)
            print("\n   Results saved to rfp_analysis_debug.json")
            
        except Exception as e:
            print(f"   ✗ Failed to retrieve results: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("Starting RFP Analysis Debug Test...")
    asyncio.run(test_rfp_analysis())
    print("\nTest complete!")