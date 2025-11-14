#!/usr/bin/env python3
"""
Timeline Integration Test
Generates a real timeline scenario and validates holiday compliance end-to-end.
"""

import requests
import json
from datetime import date
from test_holiday_compliance import HolidayComplianceValidator


def test_simple_scenario():
    """Generate a simple scenario and validate it"""
    print("="*60)
    print("TIMELINE INTEGRATION TEST")
    print("="*60)
    
    # Step 1: Build a simple scenario
    print("\n📝 Step 1: Building test scenario...")
    
    build_payload = {
        "complexity": "Standard",
        "tier": "Standard", 
        "use_slack": True,
        "slack_after_internal": 2,
        "slack_after_client": 3,
        "slack_global_pct": 10,
        "selected_deliverable_codes": ["DEL-0001"],  # Simple deliverable
        "project_start": "2025-01-06"  # Monday Jan 6, 2025
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/api/build",
            json=build_payload,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Build failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        scenario_data = response.json()
        print(f"✅ Scenario built successfully")
        print(f"   Scenario letter: {scenario_data.get('scenario_letter')}")
        
        # Step 2: Validate the scenario
        print("\n📊 Step 2: Validating timeline dates...")
        validator = HolidayComplianceValidator()
        result = validator.validate_timeline(scenario_data, "Integration Test Scenario")
        
        if result:
            print("\n✅✅✅ INTEGRATION TEST PASSED ✅✅✅")
            print("Timeline generation + holiday validation successful!")
            return True
        else:
            print("\n❌❌❌ INTEGRATION TEST FAILED ❌❌❌")
            print("Timeline contains weekend/holiday violations")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running on http://localhost:5000?")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_simple_scenario()
    exit(0 if success else 1)
