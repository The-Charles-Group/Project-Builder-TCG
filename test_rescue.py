#!/usr/bin/env python3
"""Test script to verify the rescue function works when GPT-5 fails"""

import os
import sys
# Simulate no OpenAI key to force fallback
os.environ['OPENAI_API_KEY'] = ''

# Import after setting env var
from ai_planner_agencydb import (
    analyze_with_agencydb, build_catalog_from_agencydb, 
    recall_candidates, rescore_with_llm_granular, fuse_and_calibrate,
    _auto_rescue_if_empty, compose_plan_from_agencydb
)
from main import AgencyDB

def test_rescue_function():
    """Test the rescue function with simulated GPT-5 failure"""
    
    print("\n" + "="*80)
    print("TESTING RESCUE FUNCTION WITH SIMULATED GPT-5 FAILURE")
    print("="*80 + "\n")
    
    # Load database
    db = AgencyDB()
    db.load()
    print(f"✓ Database loaded: {len(db.all_rows)} rows")
    
    # Test RFP text
    request_text = """
    We are seeking a comprehensive media agency to handle our digital advertising campaigns. 
    We need expertise in social media marketing, programmatic advertising, content creation, 
    brand strategy, analytics and reporting, campaign optimization, and creative development. 
    Budget is moderate and timeline is 12 weeks.
    """
    
    # Build catalog
    catalog = build_catalog_from_agencydb(db)
    deliverable_count = len([x for x in catalog if x["level"] == "deliverable"])
    print(f"✓ Catalog built: {len(catalog)} items ({deliverable_count} deliverables)")
    
    # Get candidates  
    candidates, all_recall = recall_candidates(request_text, catalog)
    print(f"✓ Candidates found: {len(candidates)}")
    
    # Simulate GPT-5 failure - empty LLM scores
    llm_scores = []
    print("✗ Simulating GPT-5 failure (empty LLM scores)")
    
    # Test fusion with no LLM scores
    fused = fuse_and_calibrate(candidates, llm_scores, "recall")
    passed_before_rescue = len([x for x in fused if x["level"] == "deliverable" and x["pass"]])
    print(f"  Before rescue: {passed_before_rescue} deliverables passed")
    
    # Run rescue function
    fused_after_rescue = _auto_rescue_if_empty(fused, all_recall, llm_scores)
    passed_after_rescue = len([x for x in fused_after_rescue if x["level"] == "deliverable" and x["pass"]])
    print(f"  After rescue: {passed_after_rescue} deliverables passed")
    
    # Compose plan
    summary = {
        "summary": "Media agency services",
        "goals": ["Digital advertising", "Brand awareness"],
        "channels": ["Digital", "Social"],
        "markets": ["US"],
        "compliance": [],
        "languages": ["English"],
        "timeline_weeks": 12,
        "budget_tier": "moderate",
        "complexity": "medium",
        "risk_flags": []
    }
    
    plan = compose_plan_from_agencydb(fused_after_rescue, summary, catalog, db, all_recall)
    
    # Count deliverables in final plan
    delivs_in_plan = sum(len(dept_items) for dept_items in plan.get("suggestions_by_department", {}).values())
    
    print("\n" + "="*80)
    print("TEST RESULTS:")
    print(f"  ✓ Deliverables before rescue: {passed_before_rescue}")
    print(f"  ✓ Deliverables after rescue: {passed_after_rescue}")
    print(f"  ✓ Deliverables in final plan: {delivs_in_plan}")
    
    if delivs_in_plan >= 15:
        print(f"\n✅ SUCCESS: Rescue function works! Returned {delivs_in_plan} deliverables (≥15)")
    else:
        print(f"\n❌ FAILURE: Only {delivs_in_plan} deliverables returned (need ≥15)")
    
    print("="*80)
    
    # Show departments with deliverables
    print("\nDeliverables by department:")
    for dept, items in plan.get("suggestions_by_department", {}).items():
        print(f"  - {dept}: {len(items)} deliverables")
    
    return delivs_in_plan

if __name__ == "__main__":
    result = test_rescue_function()
    sys.exit(0 if result >= 15 else 1)