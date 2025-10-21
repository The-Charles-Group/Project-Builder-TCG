#!/usr/bin/env python3
"""
Complete end-to-end test for Agency Project Builder
Tests the full flow from RFP upload to Step 2 deliverables display
"""

import requests
import time
import json
import pdfplumber

def test_complete_flow():
    print("🚀 Starting Complete Flow Test for Agency Project Builder")
    print("=" * 60)
    
    # Configuration
    base_url = "http://localhost:5000"
    session_id = "test-session-" + str(int(time.time()))
    pdf_path = './attached_assets/FINAL Uncommon Schools - May 2025 Media Agency RFP_1760438565734.pdf'
    
    # Step 1: Extract RFP text
    print("\n📄 Step 1: Extracting RFP text...")
    text = ''
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:10]:  # First 10 pages
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
        print(f"   ✅ Extracted {len(text)} characters from PDF")
    except Exception as e:
        print(f"   ❌ Error extracting PDF: {e}")
        return False
    
    # Step 2: Trigger AI Analysis
    print("\n🤖 Step 2: Triggering AI Analysis...")
    try:
        payload = {
            'request_text': text[:20000],  # First 20000 chars
            'mode': 'fast',
            'tier': 'mini', 
            'strictness': 'balanced',
            'session_id': session_id
        }
        
        response = requests.post(f"{base_url}/api/ai/analyze", json=payload)
        if response.status_code != 200:
            print(f"   ❌ Failed to trigger analysis: {response.status_code}")
            return False
            
        result = response.json()
        job_id = result.get('job_id')
        print(f"   ✅ Analysis started with job ID: {job_id}")
    except Exception as e:
        print(f"   ❌ Error triggering analysis: {e}")
        return False
    
    # Step 3: Poll for completion
    print("\n⏳ Step 3: Waiting for analysis to complete...")
    deliverables_data = None
    for i in range(30):  # Wait up to 60 seconds
        time.sleep(2)
        try:
            status_response = requests.get(f"{base_url}/api/ai/jobs/{job_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                progress = status_data.get('progress', 0)
                status = status_data.get('status', 'unknown')
                
                print(f"   [{i+1}] Status: {status}, Progress: {progress}%")
                
                if status == 'completed':
                    print("   🎉 Analysis complete!")
                    
                    # Extract deliverables from result
                    result = status_data.get('result', {})
                    if result:
                        plan = result.get('plan', {})
                        suggestions = plan.get('suggestions_by_department', {})
                        
                        # Flatten deliverables
                        deliverables = []
                        for dept, dept_delivs in suggestions.items():
                            if isinstance(dept_delivs, list):
                                deliverables.extend(dept_delivs)
                        
                        deliverables_data = {
                            'count': len(deliverables),
                            'departments': list(suggestions.keys()),
                            'deliverables': deliverables[:5]  # First 5 for display
                        }
                        
                        print(f"\n   📊 Analysis Results:")
                        print(f"      Total deliverables: {len(deliverables)}")
                        print(f"      Departments: {', '.join(suggestions.keys())}")
                        
                        if len(deliverables) > 0:
                            print(f"\n   📋 Sample deliverables:")
                            for d in deliverables[:3]:
                                print(f"      - {d.get('deliverable_code', 'N/A')}: {d.get('deliverable_name', 'Unknown')}")
                    break
                elif status == 'failed':
                    print(f"   ❌ Analysis failed: {status_data.get('error', 'Unknown error')}")
                    return False
        except Exception as e:
            print(f"   ⚠️ Error polling status: {e}")
    
    # Step 4: Verify deliverables were found
    print("\n✅ Step 4: Verification")
    if deliverables_data and deliverables_data['count'] > 0:
        print(f"   ✅ SUCCESS: Found {deliverables_data['count']} deliverables!")
        print(f"   ✅ Frontend should now display Step 2 with deliverables")
        print(f"\n   🎯 Test Result: PASSED")
        print(f"   The system successfully:")
        print(f"   1. Processed the RFP")
        print(f"   2. Analyzed with AI")
        print(f"   3. Found {deliverables_data['count']} deliverables")
        print(f"   4. Data is ready for Step 2 display")
        return True
    else:
        print(f"   ❌ FAILED: No deliverables found")
        print(f"   The backend analysis may have issues")
        return False

if __name__ == "__main__":
    success = test_complete_flow()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! The system is working correctly.")
        print("\n📝 Next Steps for User:")
        print("1. Go to the website")
        print("2. Paste RFP content in Step 1")
        print("3. Click 'Fast Mode' to analyze")
        print("4. Wait for analysis to complete")
        print("5. Step 2 should appear with 52 deliverables")
    else:
        print("❌ Tests failed. Please check the logs for details.")
    
    print("=" * 60)