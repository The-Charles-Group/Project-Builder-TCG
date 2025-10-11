#!/usr/bin/env python3
"""Test 2: Selection & Pricing - Test deliverable selection and pricing functionality"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_selection_pricing():
    print("\n" + "="*50)
    print("TEST 2: SELECTION & PRICING")
    print("="*50)
    
    # Get the AI analysis results
    print("\n[1] Fetching AI analysis results...")
    status_response = requests.get(f"{BASE_URL}/api/ai/status/be4ae262-06f9-41ea-a3f7-bf496c279f95")
    status_response.raise_for_status()
    result = status_response.json()
    
    # Extract suggestions from the correct path
    suggestions = []
    if 'result' in result and 'plan' in result['result']:
        for dept, dept_suggestions in result['result']['plan'].get('suggestions_by_department', {}).items():
            suggestions.extend(dept_suggestions)
    
    print(f"Found {len(suggestions)} deliverable suggestions")
    
    # Select first 5 deliverables
    selected_deliverables = []
    for i, sug in enumerate(suggestions[:5]):
        code = sug.get('deliverable_code', sug.get('code'))
        name = sug.get('deliverable_title', sug.get('name'))
        components = [c['title'] for c in sug.get('components', [])[:2]]
        
        selected_deliverables.append({
            'code': code,
            'name': name,
            'components': components
        })
        print(f"  {i+1}. {code}: {name}")
        if components:
            print(f"     Components: {', '.join(components)}")
    
    # Build scenario with selections
    print("\n[2] Building pricing scenario...")
    
    scenario_payload = {
        'selected_codes': [d['code'] for d in selected_deliverables],
        'selected_components': {d['code']: d['components'] for d in selected_deliverables},
        'rate_band': 'T2_MediumVolume',
        'complexity': 'Advanced',
        'project_name': 'Uncommon Schools Campaign',
        'start_date': '2025-07-01'
    }
    
    print(f"Payload: {json.dumps(scenario_payload, indent=2)[:500]}...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/build", json=scenario_payload)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            scenarios = response.json()
            print("✓ Scenarios built successfully")
            
            scenario_a = scenarios.get('scenario_a', {})
            total_hours = scenario_a.get('total_hours', 0)
            total_price = scenario_a.get('total_price', 0)
            
            print(f"\nScenario A Summary:")
            print(f"  Total Tasks: {len(scenario_a.get('tasks', []))}")
            print(f"  Total Hours: {total_hours}")
            print(f"  Total Price: ${total_price:,.2f}")
            
            # Test hour redistribution
            print("\n[3] Testing hour redistribution...")
            if scenario_a.get('tasks'):
                first_task = scenario_a['tasks'][0]
                original_hours = first_task.get('Hours', 0)
                new_hours = original_hours * 1.5  # Increase by 50%
                
                print(f"  Original hours for first task: {original_hours}")
                print(f"  New hours: {new_hours}")
                
                redistribute_payload = {
                    'scenario': scenario_a,
                    'task_index': 0,
                    'new_hours': new_hours
                }
                
                redis_response = requests.post(f"{BASE_URL}/api/redistribute_hours", json=redistribute_payload)
                print(f"  Redistribution response: {redis_response.status_code}")
                
                if redis_response.status_code == 200:
                    print("✓ Hour redistribution successful")
                    redistributed = redis_response.json()
                    new_total = redistributed.get('total_hours', 0)
                    print(f"  New total hours: {new_total}")
                else:
                    print(f"⚠️ Hour redistribution failed: {redis_response.text[:200]}")
            
            # Test retainer analysis
            print("\n[4] Testing retainer functionality...")
            
            retainer_payload = {
                'scenario': scenario_a,
                'retainer_percentage': 0.3,  # 30% as retainer
                'retainer_months': 6
            }
            
            retainer_response = requests.post(f"{BASE_URL}/api/analyze_retainer", json=retainer_payload)
            print(f"  Retainer analysis response: {retainer_response.status_code}")
            
            if retainer_response.status_code == 200:
                retainer_data = retainer_response.json()
                print("✓ Retainer analysis successful")
                print(f"  Project hours: {retainer_data.get('project_hours', 0):.1f}")
                print(f"  Retainer total hours: {retainer_data.get('retainer_hours', 0):.1f}")
                print(f"  Monthly retainer hours: {retainer_data.get('monthly_hours', 0):.1f}")
            else:
                print(f"⚠️ Retainer analysis failed: {retainer_response.text[:200]}")
            
            return True, scenario_a
            
        else:
            print(f"✗ Build failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False, None
            
    except Exception as e:
        print(f"✗ Selection/pricing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == "__main__":
    success, scenario = test_selection_pricing()
    
    print("\n" + "="*50)
    if success:
        print("TEST 2: ✓ PASSED")
        print(f"Successfully tested selection & pricing with {len(scenario.get('tasks', []))} tasks")
    else:
        print("TEST 2: ✗ FAILED")
    print("="*50)