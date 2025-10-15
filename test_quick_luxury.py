#!/usr/bin/env python3
"""Quick test to verify 100+ deliverables in fast mode"""

import requests
import time

# Set environment variable to force 100 minimum deliverables
import os
os.environ["AI_FORCE_MIN_DELIVERABLES"] = "100"

# Comprehensive luxury fashion RFP
RFP = """
COMPREHENSIVE LUXURY FASHION BRAND MARKETING SERVICES

We need a full-service agency for our luxury fashion brand global expansion.
Services needed: brand strategy, creative development, digital marketing, 
social media, influencer marketing, paid media, events, PR, analytics, 
technology integration, customer experience, loyalty programs, international 
market entry, sustainability communications, retail experience design.

Budget: $50M+ annual. Timeline: 5 years. Markets: Global.
"""

url = "http://localhost:5000/api/ai/analyze"
payload = {
    "request_text": RFP,
    "mode": "fast",  # Use fast mode for quick testing
    "tier": "mini"
}

print("Testing with fast mode...")
response = requests.post(url, json=payload, timeout=60)

if response.status_code == 200:
    data = response.json()
    
    # Handle async job
    if "job_id" in data:
        job_id = data["job_id"]
        print(f"Job started: {job_id}")
        
        # Poll for results (max 30 seconds)
        for i in range(15):
            time.sleep(2)
            status = requests.get(f"http://localhost:5000/api/ai/status/{job_id}")
            if status.status_code == 200:
                status_data = status.json()
                print(f"Status: {status_data.get('status')} - {status_data.get('current_stage', 'Processing...')}")
                if status_data.get("status") == "completed":
                    plan = status_data.get("result", {}).get("plan", {})
                    break
    else:
        plan = data.get("plan", {})
    
    # Count deliverables
    total = 0
    suggestions = plan.get("suggestions_by_department", {})
    for dept, delivs in suggestions.items():
        count = len(delivs)
        total += count
        print(f"{dept}: {count} deliverables")
    
    print(f"\nTOTAL: {total} deliverables")
    
    if total >= 100:
        print(f"✅ SUCCESS! {total} deliverables")
    else:
        print(f"❌ FAILED! Only {total} deliverables")
else:
    print(f"Error: {response.status_code}")
    print(response.text[:500])