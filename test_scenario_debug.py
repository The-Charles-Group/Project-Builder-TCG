#!/usr/bin/env python3
import httpx
import json

# Test the build endpoint with valid deliverables
response = httpx.post("http://localhost:5000/api/build", 
                      json={
                          "selected_deliverable_codes": ["DEL-0001", "DEL-0008"],
                          "selected_components_map": {},
                          "pricing_mode": "Flat_Blended",
                          "rate_band": "Standard_US",
                          "scenario_a": {
                              "mode": "template",
                              "complexity": "Core",
                              "tier": "T2_MediumVolume"
                          },
                          "retainers": []
                      })

print("Status:", response.status_code)
data = response.json()

print("\nResponse structure:")
print("Keys at root:", list(data.keys()))

if 'scenarios' in data:
    print("\n'scenarios' key structure:")
    scenarios = data['scenarios']
    print("Keys in scenarios:", list(scenarios.keys()))
    
    if 'A' in scenarios:
        scenario_a = scenarios['A']
        print("\nScenario A keys:", list(scenario_a.keys())[:20])  # Show first 20 keys
        
        # Check for items
        if 'items' in scenario_a:
            items = scenario_a['items']
            print(f"\nFound {len(items)} items")
            if items:
                print("First item keys:", list(items[0].keys()))
                
        # Check for totals
        for field in ['total_hours', 'total_price', 'deliverables', 'Total Hours', 'Total Price']:
            if field in scenario_a:
                print(f"Found field '{field}': {scenario_a[field]}")
else:
    print("\nNo 'scenarios' key. Full response:")
    print(json.dumps(data, indent=2)[:1000])