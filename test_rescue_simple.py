#!/usr/bin/env python3
"""
Simple test to verify the rescue function returns 25+ deliverables
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

# Simple RFP text
rfp_text = "We need a comprehensive digital marketing strategy."

# Start AI analysis with relaxed strictness to trigger rescue
response = requests.post(f"{BASE_URL}/api/ai/analyze", json={
    "request_text": rfp_text,
    "strictness": "relaxed", 
    "tier": "mini"
})

if response.status_code != 200:
    print(f"[ERROR] Failed to start: {response.text}")
    exit(1)

job_id = response.json()["job_id"]
print(f"[INFO] Job started: {job_id}")

# Poll for completion
for i in range(120):  # Wait up to 2 minutes
    status_response = requests.get(f"{BASE_URL}/api/ai/status/{job_id}")
    status_data = status_response.json()
    status = status_data.get("status")
    
    print(f"[{i+1}] Status: {status} - {status_data.get('current_stage', '')}")
    
    if status == "completed":
        result = status_data.get("result", {})
        plan = result.get("plan", {})
        deliverables_by_dept = plan.get("deliverables_by_dept", {})
        
        total = 0
        print("\n[DELIVERABLES BY DEPARTMENT]")
        for dept, delivs in deliverables_by_dept.items():
            count = len(delivs)
            print(f"  {dept}: {count} deliverables")
            total += count
        
        print(f"\n[RESULT] Total deliverables: {total}")
        
        if total >= 25:
            print(f"✅ SUCCESS: Rescue function works! Got {total} deliverables (>= 25)")
        elif total >= 15:
            print(f"⚠️  PARTIAL: Got {total} deliverables (>= 15 but < 25)")  
        else:
            print(f"❌ FAILURE: Only {total} deliverables (< 15 minimum)")
        break
        
    elif status == "failed":
        print(f"[ERROR] Job failed: {status_data.get('error')}")
        break
    
    time.sleep(1)
else:
    print("[ERROR] Timeout waiting for completion")