#!/usr/bin/env python3
"""
Comprehensive test script for Uncommon Schools RFP
Tests RFP submission, AI analysis, selection, pricing, timeline, and exports
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:5000"

# Read and clean the RFP text
def get_rfp_text():
    """Get the Uncommon Schools RFP text"""
    with open("/tmp/uncommon_schools_rfp.txt", "r") as f:
        text = f.read()
    
    # Clean up text - remove excessive spaces and newlines
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Join words that were split
        line = ' '.join(line.split())
        if line.strip():
            cleaned_lines.append(line)
    
    full_text = '\n'.join(cleaned_lines)
    
    # Add specific test parameters
    test_rfp = f"""
{full_text}

BUDGET: $4,000,000
TARGET AUDIENCES: Parents of school-age children, Teachers and education professionals  
MARKETS: New York, New Jersey, Massachusetts, Brooklyn, Newark
CHANNELS: Digital (social media, search, display), Out-of-home (billboards, transit)
TIMELINE: July 2025 - June 2026 (12 months)
OBJECTIVE: Increase student enrollment and teacher recruitment
"""
    
    return test_rfp

def test_ai_analysis():
    """Test 1: Submit RFP and run AI analysis"""
    print("\n" + "="*50)
    print("TEST 1: RFP SUBMISSION & AI ANALYSIS")
    print("="*50)
    
    rfp_text = get_rfp_text()
    print(f"RFP Text Length: {len(rfp_text)} characters")
    print("First 500 chars of RFP:")
    print(rfp_text[:500])
    
    # Submit for AI analysis
    print("\n[1] Submitting RFP for AI analysis...")
    
    payload = {
        "request_text": rfp_text,
        "strictness": "balanced"
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(f"{BASE_URL}/api/ai/analyze", json=payload)
        response.raise_for_status()
        result = response.json()
        
        if 'job_id' in result:
            job_id = result['job_id']
            print(f"✓ Analysis started with job_id: {job_id}")
            
            # Monitor progress
            print("\n[2] Monitoring analysis progress...")
            while True:
                status_response = requests.get(f"{BASE_URL}/api/ai/status/{job_id}")
                status_response.raise_for_status()
                status = status_response.json()
                
                print(f"  Status: {status['status']} | Stage: {status.get('current_stage', 'N/A')} | Progress: {status.get('processed_chunks', 0)}/{status.get('total_chunks', 0)}")
                
                if status['status'] == 'completed':
                    elapsed = time.time() - start_time
                    print(f"\n✓ Analysis completed in {elapsed:.1f} seconds")
                    
                    if elapsed > 180:  # 3 minutes
                        print("⚠️ WARNING: Analysis took longer than 3 minutes")
                    
                    # Get the results
                    if 'result' in status:
                        suggestions = status['result'].get('suggestions', [])
                        print(f"\n[3] Received {len(suggestions)} deliverable suggestions")
                        
                        # Sample first few suggestions
                        for i, sug in enumerate(suggestions[:5]):
                            print(f"  {i+1}. {sug.get('deliverable', 'Unknown')} - {sug.get('category', 'Unknown')}")
                            if 'components' in sug:
                                print(f"     Components: {', '.join(c.get('name', '') for c in sug['components'][:3])}")
                        
                        return {'success': True, 'suggestions': suggestions, 'time': elapsed}
                    break
                
                elif status['status'] == 'failed':
                    error = status.get('error', 'Unknown error')
                    print(f"\n✗ Analysis failed: {error}")
                    
                    # Check for JSON parsing errors
                    if 'JSON' in error or 'json' in error.lower():
                        print("⚠️ JSON PARSING ERROR DETECTED - needs fixing")
                    
                    return {'success': False, 'error': error}
                
                time.sleep(2)  # Poll every 2 seconds
                
        else:
            print(f"✗ Unexpected response: {result}")
            return {'success': False, 'error': 'No job_id in response'}
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
        return {'success': False, 'error': str(e)}
    except json.JSONDecodeError as e:
        print(f"✗ JSON decode error: {e}")
        return {'success': False, 'error': f'JSON error: {e}'}
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return {'success': False, 'error': str(e)}

def test_selection_pricing(suggestions):
    """Test 2: Select deliverables and test pricing"""
    print("\n" + "="*50)
    print("TEST 2: SELECTION & PRICING")
    print("="*50)
    
    if not suggestions:
        print("✗ No suggestions to test with")
        return {'success': False}
    
    # Select first 5 deliverables
    selected = []
    for sug in suggestions[:5]:
        if 'deliverable_code' in sug:
            selected.append({
                'deliverable_code': sug['deliverable_code'],
                'components': [c['name'] for c in sug.get('components', [])[:2]]  # Select first 2 components
            })
    
    print(f"[1] Selected {len(selected)} deliverables for testing")
    
    # Build scenario with selections
    print("\n[2] Building pricing scenario...")
    
    scenario_payload = {
        'selected_codes': [s['deliverable_code'] for s in selected],
        'selected_components': {s['deliverable_code']: s['components'] for s in selected},
        'rate_band': 'T2_MediumVolume',
        'complexity': 'Advanced',
        'project_name': 'Uncommon Schools Campaign',
        'start_date': '2025-07-01'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/build", json=scenario_payload)
        response.raise_for_status()
        scenarios = response.json()
        
        print(f"✓ Scenarios built successfully")
        
        scenario_a = scenarios.get('scenario_a', {})
        total_hours = scenario_a.get('total_hours', 0)
        total_price = scenario_a.get('total_price', 0)
        
        print(f"  Total Hours: {total_hours}")
        print(f"  Total Price: ${total_price:,.2f}")
        
        # Test hour redistribution
        print("\n[3] Testing hour redistribution...")
        
        # Modify hours for first deliverable
        if scenario_a.get('tasks'):
            first_task = scenario_a['tasks'][0]
            new_hours = first_task['Hours'] * 1.5  # Increase by 50%
            
            redistribute_payload = {
                'scenario': scenario_a,
                'task_id': first_task.get('id', 0),
                'new_hours': new_hours,
                'method': 'proportional'
            }
            
            redis_response = requests.post(f"{BASE_URL}/api/redistribute_hours", json=redistribute_payload)
            if redis_response.status_code == 200:
                print("✓ Hour redistribution successful")
            else:
                print(f"⚠️ Hour redistribution failed: {redis_response.status_code}")
        
        # Test retainer toggle
        print("\n[4] Testing retainer functionality...")
        
        retainer_payload = {
            'scenario': scenario_a,
            'enable_retainer': True,
            'retainer_percentage': 0.3,  # 30% as retainer
            'retainer_months': 6
        }
        
        retainer_response = requests.post(f"{BASE_URL}/api/analyze_retainer", json=retainer_payload)
        if retainer_response.status_code == 200:
            retainer_data = retainer_response.json()
            print(f"✓ Retainer analysis successful")
            print(f"  Project hours: {retainer_data.get('project_hours', 0)}")
            print(f"  Retainer hours: {retainer_data.get('retainer_hours', 0)}")
        else:
            print(f"⚠️ Retainer analysis failed: {retainer_response.status_code}")
        
        return {'success': True, 'scenario': scenario_a}
        
    except Exception as e:
        print(f"✗ Selection/pricing test failed: {e}")
        return {'success': False, 'error': str(e)}

def test_timeline_export(scenario):
    """Test 3: Generate timeline and test exports"""
    print("\n" + "="*50)
    print("TEST 3: TIMELINE & EXPORT")
    print("="*50)
    
    if not scenario:
        print("✗ No scenario to test with")
        return {'success': False}
    
    # Generate timeline
    print("[1] Generating timeline...")
    
    timeline_payload = {
        'scenario': scenario,
        'start_date': '2025-07-01',
        'use_ai': True,
        'include_dependencies': True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/generate_timeline", json=timeline_payload)
        response.raise_for_status()
        timeline_data = response.json()
        
        tasks = timeline_data.get('tasks', [])
        print(f"✓ Timeline generated with {len(tasks)} tasks")
        
        if tasks:
            print(f"  First task: {tasks[0].get('name', 'Unknown')}")
            print(f"  Start: {tasks[0].get('start', 'N/A')}, End: {tasks[0].get('end', 'N/A')}")
        
        # Test XML export
        print("\n[2] Testing XML export...")
        
        xml_payload = {
            'scenario': scenario,
            'project_name': 'Uncommon Schools Campaign',
            'export_format': 'xml'
        }
        
        xml_response = requests.post(f"{BASE_URL}/api/export", json=xml_payload)
        if xml_response.status_code == 200:
            print("✓ XML export successful")
            
            # Save to test file
            with open('test_outputs/uncommon_schools_test.xml', 'wb') as f:
                f.write(xml_response.content)
            print("  Saved to test_outputs/uncommon_schools_test.xml")
        else:
            print(f"⚠️ XML export failed: {xml_response.status_code}")
        
        # Test Excel export
        print("\n[3] Testing Excel export...")
        
        excel_payload = {
            'scenario': scenario,
            'project_name': 'Uncommon Schools Campaign',
            'export_format': 'xlsx',
            'include_retainer': True
        }
        
        excel_response = requests.post(f"{BASE_URL}/api/export_workbook", json=excel_payload)
        if excel_response.status_code == 200:
            print("✓ Excel export successful")
            
            # Save to test file
            with open('test_outputs/uncommon_schools_test.xlsx', 'wb') as f:
                f.write(excel_response.content)
            print("  Saved to test_outputs/uncommon_schools_test.xlsx")
        else:
            print(f"⚠️ Excel export failed: {excel_response.status_code}")
            
        return {'success': True, 'timeline': timeline_data}
        
    except Exception as e:
        print(f"✗ Timeline/export test failed: {e}")
        return {'success': False, 'error': str(e)}

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("UNCOMMON SCHOOLS RFP - COMPREHENSIVE END-TO-END TEST")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create test outputs directory
    import os
    os.makedirs('test_outputs', exist_ok=True)
    
    # Test 1: AI Analysis
    test1_result = test_ai_analysis()
    
    if not test1_result['success']:
        print("\n✗ TEST 1 FAILED - Cannot continue")
        return 1
    
    suggestions = test1_result.get('suggestions', [])
    
    # Test 2: Selection & Pricing
    test2_result = test_selection_pricing(suggestions)
    
    if not test2_result['success']:
        print("\n⚠️ TEST 2 FAILED - Continuing to Test 3 with mock data")
    
    scenario = test2_result.get('scenario') if test2_result['success'] else None
    
    # Test 3: Timeline & Export
    if scenario:
        test3_result = test_timeline_export(scenario)
    else:
        print("\n⚠️ Skipping TEST 3 due to no scenario data")
        test3_result = {'success': False}
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    print(f"Test 1 (AI Analysis): {'✓ PASSED' if test1_result['success'] else '✗ FAILED'}")
    if test1_result['success']:
        print(f"  - Analysis time: {test1_result.get('time', 0):.1f}s")
        print(f"  - Suggestions: {len(suggestions)}")
    
    print(f"Test 2 (Selection & Pricing): {'✓ PASSED' if test2_result['success'] else '✗ FAILED'}")
    
    print(f"Test 3 (Timeline & Export): {'✓ PASSED' if test3_result['success'] else '✗ FAILED'}")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Return 0 if all tests passed
    all_passed = test1_result['success'] and test2_result['success'] and test3_result['success']
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())