#!/usr/bin/env python3
import httpx
import json

# Test the suggest endpoint
response = httpx.post("http://localhost:5000/api/suggest_by_text", 
                      json={"rfp_text": "We need a digital marketing campaign for luxury fashion brand"})

print("Status:", response.status_code)
data = response.json()

print("\nSuggested deliverables structure:")
if 'suggested' in data and data['suggested']:
    first = data['suggested'][0]
    print(json.dumps(first, indent=2))
    
    # Show all fields
    print("\nAvailable fields:", list(first.keys()))
else:
    print("No suggestions found")
    print("Response:", json.dumps(data, indent=2))