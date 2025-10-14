#!/usr/bin/env python3
"""Test with Uncommon Schools media agency RFP"""

import os
import json
os.environ['OPENAI_API_KEY'] = ''  # Force fallback

from ai_planner_agencydb import analyze_with_agencydb
from main import AgencyDB

def test_uncommon_schools():
    """Test with the exact RFP mentioned by the user"""
    
    print("\n" + "="*80)
    print("TESTING WITH UNCOMMON SCHOOLS MEDIA AGENCY RFP")
    print("="*80 + "\n")
    
    # Load database
    db = AgencyDB()
    db.load()
    print(f"✓ Database loaded: {len(db.all_rows)} rows")
    
    # Exact RFP text mentioned
    request_text = """
    We are Uncommon Schools, a charter school network, seeking a comprehensive media agency 
    to handle our marketing and recruitment campaigns. We need expertise in:
    - Digital advertising and social media campaigns
    - Content creation and storytelling
    - Brand strategy and positioning
    - Community outreach and engagement
    - Analytics and performance tracking
    - Creative development for diverse audiences
    - Multi-channel campaign management
    """
    
    # Run analysis with simulated GPT-5 failure
    # Note: analyze_with_agencydb parameters are (request_text, db, strictness, tier)
    result = analyze_with_agencydb(request_text, db, "recall", "thinking")
    
    # Count deliverables - check both result and nested plan
    if "plan" in result and "suggestions_by_department" in result["plan"]:
        deliverables = sum(len(dept) for dept in result["plan"]["suggestions_by_department"].values())
    else:
        deliverables = sum(len(dept) for dept in result.get("suggestions_by_department", {}).values())
    
    print("\n" + "="*80)
    print("RESULTS:")
    print(f"  ✓ Total deliverables returned: {deliverables}")
    
    if deliverables >= 15:
        print(f"\n✅ SUCCESS: System returned {deliverables} deliverables (≥15 required)")
    else:
        print(f"\n❌ FAILURE: Only {deliverables} deliverables (need ≥15)")
    
    # Show breakdown
    print("\nDeliverables by department:")
    
    # Get the correct suggestions_by_department
    if "plan" in result and "suggestions_by_department" in result["plan"]:
        suggestions = result["plan"]["suggestions_by_department"]
    else:
        suggestions = result.get("suggestions_by_department", {})
    
    for dept, items in suggestions.items():
        print(f"  - {dept}: {len(items)} deliverables")
        # Show first 3 items
        for i, item in enumerate(items[:3]):
            code = item.get('code', item.get('Deliverable_Code', 'N/A'))
            name = item.get('name', item.get('Deliverable_Name', 'N/A'))
            print(f"      {i+1}. {code}: {name}")
    
    print("="*80)
    return deliverables

if __name__ == "__main__":
    count = test_uncommon_schools()
    print(f"\nFinal result: {count} deliverables")
    
    # Also save result to file
    with open("test_result.txt", "w") as f:
        f.write(f"Test result: {count} deliverables returned (minimum 15 required)\n")
        f.write(f"Status: {'PASS' if count >= 15 else 'FAIL'}\n")