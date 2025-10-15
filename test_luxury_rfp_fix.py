#!/usr/bin/env python3
"""
Test script to verify that luxury fashion RFPs generate 100+ deliverables
after fixing the AI analysis system.
"""

import os
import asyncio
from ai_planner_agencydb import analyze_with_agencydb, expand_deliverables_for_comprehensive_rfp
from main import AgencyDB

# Set environment variables to force comprehensive expansion
os.environ["AI_MIN_DELIVERABLES"] = "100"
os.environ["AI_MIN_COMPONENTS_PER_DELIV"] = "3"
os.environ["AI_MIN_TASKS_PER_COMPONENT"] = "3"
os.environ["AI_AUTORELAX"] = "true"
os.environ["AI_STRICTNESS_DEFAULT"] = "recall"  # Use lowest gate threshold

def test_luxury_fashion_rfp():
    """Test that luxury fashion RFPs generate 100+ deliverables"""
    
    print("=" * 80)
    print("Testing Luxury Fashion RFP Expansion")
    print("=" * 80)
    
    # Create a comprehensive luxury fashion RFP text
    rfp_text = """
    We are seeking a full-service agency partner for Maison Luxe, a prestigious luxury fashion house,
    to develop and execute a comprehensive global marketing strategy for our 2025 collections.
    
    This is a luxury fashion brand with haute couture collections targeting affluent consumers worldwide.
    
    Scope includes:
    - Global brand strategy across North America, Europe, Asia-Pacific, Latin America, and Middle East
    - Integrated marketing campaigns for Spring/Summer, Fall/Winter, Resort, and Pre-Fall collections
    - Digital transformation and e-commerce strategy
    - Social media management across Instagram, Facebook, TikTok, YouTube, LinkedIn
    - Influencer partnerships with top-tier fashion influencers and celebrities
    - Content creation for all channels including website, mobile app, email, SMS
    - Paid media management across all digital and traditional channels
    - Event marketing for fashion weeks, store openings, and VIP experiences
    - Customer segmentation targeting Gen Z, Millennials, Gen X, and Affluent consumers
    - Comprehensive analytics and reporting
    - Multi-year engagement with quarterly reviews
    
    Budget: $10M+ annually
    Timeline: 3-year partnership starting Q1 2025
    
    We need a comprehensive, full-service approach with deep expertise in luxury fashion marketing.
    """
    
    # Load database
    print("\n1. Loading database...")
    db = AgencyDB()
    db.load()
    print(f"   Database loaded with {len(db.all_rows)} rows")
    
    # Run AI analysis
    print("\n2. Running AI analysis...")
    result = analyze_with_agencydb(
        request_text=rfp_text,
        db=db,
        strictness="recall",  # Use lowest strictness
        mode="deep"  # Use deep mode for comprehensive analysis
    )
    
    # Check results
    print("\n3. Analyzing results...")
    
    if not result or 'plan' not in result:
        print("   ERROR: No plan generated")
        return False
    
    plan = result['plan']
    suggestions_by_dept = plan.get('suggestions_by_department', {})
    
    # Count total deliverables
    total_deliverables = 0
    dept_counts = {}
    for dept, deliverables in suggestions_by_dept.items():
        count = len(deliverables)
        dept_counts[dept] = count
        total_deliverables += count
    
    print(f"\n4. Results Summary:")
    print(f"   Total deliverables: {total_deliverables}")
    print(f"   By department:")
    for dept, count in dept_counts.items():
        print(f"      - {dept}: {count}")
    
    # Check diagnostics
    diagnostics = result.get('diagnostics', {})
    print(f"\n5. Diagnostics:")
    print(f"   Mode: {diagnostics.get('mode', 'unknown')}")
    print(f"   Candidates considered: {diagnostics.get('candidates_considered', 0)}")
    print(f"   Deliverables selected: {diagnostics.get('deliverables_selected', 0)}")
    print(f"   Deliverables in plan: {diagnostics.get('deliverables_in_plan', 0)}")
    print(f"   Rescue triggered: {diagnostics.get('rescue_triggered', False)}")
    print(f"   LLM scores available: {diagnostics.get('llm_scores_available', False)}")
    
    # Verify expansion worked
    success = total_deliverables >= 100
    
    print("\n" + "=" * 80)
    if success:
        print(f"✅ SUCCESS: Generated {total_deliverables} deliverables (>= 100)")
    else:
        print(f"❌ FAILURE: Only generated {total_deliverables} deliverables (< 100)")
    print("=" * 80)
    
    # Test direct expansion function
    print("\n6. Testing direct expansion function...")
    
    # Create sample deliverables
    sample_deliverables = [
        {"id": f"DEL-{i:04d}", "title": f"Deliverable {i}", "dept": "Strategy", 
         "level": "deliverable", "calibrated_confidence": 0.7}
        for i in range(1, 27)  # Start with 26 deliverables like the original issue
    ]
    
    # Create summary for luxury fashion
    summary = {
        "summary": rfp_text.lower(),
        "complexity": "high",
        "markets": ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East"],
        "channels": ["Instagram", "Facebook", "TikTok", "YouTube", "LinkedIn", "Email", "SMS", "Web"],
        "timeline_weeks": 156,  # 3 years
        "budget_tier": "high"
    }
    
    # Test expansion
    expanded = expand_deliverables_for_comprehensive_rfp(
        deliverables=sample_deliverables,
        summary=summary,
        target_count=100
    )
    
    print(f"   Expanded from {len(sample_deliverables)} to {len(expanded)} deliverables")
    
    if len(expanded) >= 100:
        print(f"   ✅ Direct expansion successful: {len(expanded)} deliverables")
    else:
        print(f"   ❌ Direct expansion failed: Only {len(expanded)} deliverables")
    
    return success

if __name__ == "__main__":
    try:
        success = test_luxury_fashion_rfp()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)