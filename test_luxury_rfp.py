#!/usr/bin/env python3
"""
Test script to verify GPT-5 analysis returns 100+ deliverables for luxury fashion RFPs
"""

import requests
import json
import sys
import os

# Test with comprehensive luxury fashion RFP content
LUXURY_FASHION_RFP = """
REQUEST FOR PROPOSAL: COMPREHENSIVE LUXURY FASHION BRAND MARKETING AGENCY

Our prestigious luxury fashion house seeks a full-service marketing agency partner for our 
complete brand transformation and global market expansion initiative.

PROJECT SCOPE: 
We require comprehensive integrated marketing services across all channels for our luxury 
fashion and haute couture collections. This is a complete agency-of-record engagement.

SERVICES REQUIRED:
- Full brand strategy and positioning for luxury market
- Complete creative development across all touchpoints
- Integrated digital marketing and e-commerce strategy
- Social media management across all platforms
- Influencer marketing and celebrity partnerships
- Content creation and storytelling
- Paid media planning and buying (digital and traditional)
- Event marketing and fashion show production
- PR and media relations
- Market research and consumer insights
- Analytics and performance measurement
- Technology integration and marketing automation
- Customer experience design
- Loyalty program development
- International market entry strategies
- Sustainability and CSR communications
- Crisis management preparedness
- Retail experience design
- Visual merchandising guidelines
- Partnership marketing strategies

TARGET MARKETS:
- Primary: North America, Europe, Asia-Pacific
- Secondary: Middle East, Latin America
- Emerging: Africa, Eastern Europe

CHANNELS:
- Digital: Website, Mobile App, Social Media, Email, SMS
- Traditional: Print, OOH, TV, Radio
- Retail: Flagship Stores, Department Stores, Pop-ups
- Events: Fashion Shows, Trunk Shows, VIP Events
- Partnerships: Influencers, Celebrities, Brand Collaborations

DELIVERABLES:
We expect comprehensive deliverables covering all aspects of luxury fashion marketing including 
but not limited to brand strategy documents, creative assets, campaign materials, digital 
properties, content calendars, media plans, analytics dashboards, and ongoing optimization.

BUDGET: $50M+ annual marketing investment
TIMELINE: 5-year strategic partnership starting Q1 2025

Please provide a detailed proposal outlining your approach, capabilities, and recommendations 
for achieving our ambitious growth objectives in the global luxury fashion market.
"""

def test_luxury_rfp():
    """Test that luxury fashion RFP returns 100+ deliverables"""
    
    # API endpoint
    url = "http://localhost:5000/api/ai/analyze"
    
    # Prepare the request
    payload = {
        "request_text": LUXURY_FASHION_RFP,
        "mode": "deep",
        "tier": "thinking"
    }
    
    print("Testing luxury fashion RFP analysis...")
    print("=" * 60)
    
    try:
        # Send request
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ Error: API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        data = response.json()
        
        # Check if we have a job ID (async processing)
        if "job_id" in data:
            job_id = data["job_id"]
            print(f"✅ Analysis job started: {job_id}")
            
            # Poll for results
            import time
            max_wait = 300  # 5 minutes (since job takes ~260s)
            poll_interval = 2
            elapsed = 0
            
            while elapsed < max_wait:
                time.sleep(poll_interval)
                elapsed += poll_interval
                
                # Check job status
                status_url = f"http://localhost:5000/api/ai/jobs/{job_id}"
                status_response = requests.get(status_url)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    
                    print(f"  Status: {status_data.get('status')} - {status_data.get('stage', 'Processing...')}")
                    
                    if status_data.get("status") == "completed":
                        # Get the results
                        plan = status_data.get("result", {}).get("plan", {})
                        break
                    elif status_data.get("status") == "failed":
                        print(f"❌ Analysis failed: {status_data.get('error')}")
                        return False
            else:
                print("❌ Timeout waiting for analysis to complete")
                return False
        else:
            # Synchronous response
            plan = data.get("plan", {})
        
        # Count deliverables
        total_deliverables = 0
        suggestions = plan.get("suggestions_by_department", {})
        
        print("\n📊 RESULTS:")
        print("-" * 60)
        
        for dept, deliverables in suggestions.items():
            dept_count = len(deliverables)
            total_deliverables += dept_count
            print(f"  {dept}: {dept_count} deliverables")
        
        print("-" * 60)
        print(f"📈 TOTAL DELIVERABLES: {total_deliverables}")
        
        # Check if we met the target
        if total_deliverables >= 100:
            print(f"✅ SUCCESS! Generated {total_deliverables} deliverables (target: 100+)")
            
            # Show sample deliverables
            print("\n📝 Sample deliverables:")
            count = 0
            for dept, delivs in suggestions.items():
                for deliv in delivs[:3]:  # First 3 from each dept
                    count += 1
                    if count <= 10:
                        print(f"  {count}. [{dept}] {deliv.get('name', deliv.get('title', 'Unknown'))}")
            
            return True
        else:
            print(f"❌ FAILED! Only generated {total_deliverables} deliverables (target: 100+)")
            
            # Diagnostic information
            print("\n🔍 Diagnostics:")
            diagnostics = plan.get("diagnostics", {})
            print(f"  Mode: {diagnostics.get('mode', 'unknown')}")
            print(f"  Candidates considered: {diagnostics.get('candidates_considered', 0)}")
            print(f"  Catalog items: {diagnostics.get('catalog_items', 0)}")
            
            # Check summary for complexity detection
            summary = plan.get("summary", {})
            print(f"  Detected complexity: {summary.get('complexity', 'unknown')}")
            print(f"  Budget tier: {summary.get('budget_tier', 'unknown')}")
            
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API - is the server running on port 5000?")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_environment():
    """Check environment variables that affect deliverable counts"""
    print("\n🔧 ENVIRONMENT SETTINGS:")
    print("-" * 60)
    
    env_vars = {
        "AI_MIN_DELIVERABLES": "100 (default)",
        "AI_FORCE_MIN_DELIVERABLES": "Not set (default)",
        "FAST_TOP_K": "120 (default)",
        "DEEP_TOP_K": "100 (default)",
        "AI_STRICTNESS_DEFAULT": "balanced (default)"
    }
    
    for var, default in env_vars.items():
        value = os.environ.get(var)
        if value:
            print(f"  {var}: {value}")
        else:
            print(f"  {var}: {default}")
    
    print("-" * 60)

if __name__ == "__main__":
    print("=" * 60)
    print("LUXURY FASHION RFP TEST - 100+ DELIVERABLES")
    print("=" * 60)
    
    check_environment()
    
    print("\n🚀 Starting test...")
    print("=" * 60)
    
    success = test_luxury_rfp()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("❌ TEST FAILED - Please review the fixes")
        sys.exit(1)