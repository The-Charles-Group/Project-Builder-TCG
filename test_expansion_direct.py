#!/usr/bin/env python3
"""
Direct test of the expansion function without API calls
"""

import os
import sys
sys.path.insert(0, '.')

from ai_planner_agencydb import expand_deliverables_for_comprehensive_rfp

def test_direct_expansion():
    """Test the expansion function directly"""
    
    print("=" * 80)
    print("Testing Direct Expansion for Luxury Fashion RFP")
    print("=" * 80)
    
    # Create initial deliverables (simulating what AI might return)
    initial_deliverables = []
    
    # Add some realistic deliverables from different departments
    departments = {
        "Strategy": [
            "Brand Strategy Development",
            "Market Analysis & Research", 
            "Competitive Intelligence Report",
            "Consumer Insights Study",
            "Positioning Framework"
        ],
        "Creative": [
            "Creative Campaign Concept",
            "Visual Identity System",
            "Brand Guidelines",
            "Content Strategy",
            "Art Direction"
        ],
        "Paid Media": [
            "Media Planning & Strategy",
            "Paid Social Campaign",
            "Search Marketing Strategy",
            "Programmatic Buying Strategy"
        ],
        "Content": [
            "Content Calendar Development",
            "Editorial Strategy",
            "Social Content Creation",
            "Blog Content Strategy"
        ],
        "Technology": [
            "Website Development",
            "Mobile App Strategy", 
            "Marketing Automation Setup"
        ]
    }
    
    deliv_id = 1
    for dept, titles in departments.items():
        for title in titles:
            initial_deliverables.append({
                "id": f"DEL-{deliv_id:04d}",
                "title": title,
                "dept": dept,
                "level": "deliverable",
                "calibrated_confidence": 0.70,
                "pass": True
            })
            deliv_id += 1
    
    print(f"\n1. Starting with {len(initial_deliverables)} initial deliverables:")
    for dept in departments.keys():
        count = len([d for d in initial_deliverables if d["dept"] == dept])
        print(f"   - {dept}: {count}")
    
    # Create a luxury fashion RFP summary
    luxury_fashion_summary = {
        "summary": """luxury fashion brand haute couture premium designer collection 
                     global marketing strategy comprehensive full-service agency
                     spring summer fall winter resort collections
                     affluent consumers worldwide multi-channel campaign""",
        "complexity": "high",
        "budget_tier": "high",
        "markets": ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East"],
        "channels": ["Instagram", "Facebook", "TikTok", "YouTube", "LinkedIn", 
                    "Email", "SMS", "Web", "Mobile App", "Print", "Events"],
        "timeline_weeks": 156,  # 3 years
        "compliance": ["GDPR", "CCPA"],
        "languages": ["English", "French", "Italian", "Chinese", "Japanese"]
    }
    
    print("\n2. RFP Characteristics:")
    print(f"   - Markets: {len(luxury_fashion_summary['markets'])} regions")
    print(f"   - Channels: {len(luxury_fashion_summary['channels'])} channels")
    print(f"   - Timeline: {luxury_fashion_summary['timeline_weeks']} weeks")
    print(f"   - Complexity: {luxury_fashion_summary['complexity']}")
    
    # Test expansion
    print("\n3. Running expansion...")
    expanded = expand_deliverables_for_comprehensive_rfp(
        deliverables=initial_deliverables,
        summary=luxury_fashion_summary,
        target_count=100
    )
    
    # Count results by department
    expanded_by_dept = {}
    for d in expanded:
        dept = d.get("dept", "Unknown")
        if dept not in expanded_by_dept:
            expanded_by_dept[dept] = []
        expanded_by_dept[dept].append(d)
    
    print(f"\n4. Expansion Results:")
    print(f"   Total deliverables after expansion: {len(expanded)}")
    print(f"   By department:")
    for dept, delivs in expanded_by_dept.items():
        print(f"      - {dept}: {len(delivs)}")
    
    # Show some examples of expanded deliverables
    print("\n5. Sample Expanded Deliverables:")
    # Get the new deliverables (not in original list)
    original_ids = {d["id"] for d in initial_deliverables}
    new_deliverables = [d for d in expanded if d["id"] not in original_ids]
    
    # Show first 10 new deliverables
    for i, d in enumerate(new_deliverables[:10], 1):
        print(f"   {i}. [{d['dept']}] {d['title']} (conf: {d['calibrated_confidence']:.2f})")
    
    if len(new_deliverables) > 10:
        print(f"   ... and {len(new_deliverables) - 10} more new deliverables")
    
    # Verify confidence scores
    print("\n6. Confidence Score Analysis:")
    conf_ranges = {
        "0.70+": 0,
        "0.60-0.69": 0,
        "0.50-0.59": 0,
        "0.40-0.49": 0,
        "< 0.40": 0
    }
    
    for d in expanded:
        conf = d.get("calibrated_confidence", 0)
        if conf >= 0.70:
            conf_ranges["0.70+"] += 1
        elif conf >= 0.60:
            conf_ranges["0.60-0.69"] += 1
        elif conf >= 0.50:
            conf_ranges["0.50-0.59"] += 1
        elif conf >= 0.40:
            conf_ranges["0.40-0.49"] += 1
        else:
            conf_ranges["< 0.40"] += 1
    
    for range_name, count in conf_ranges.items():
        print(f"   {range_name}: {count} deliverables")
    
    # Check success
    success = len(expanded) >= 100
    
    print("\n" + "=" * 80)
    if success:
        print(f"✅ SUCCESS: Expanded to {len(expanded)} deliverables (>= 100)")
        print(f"   Added {len(new_deliverables)} new variations")
    else:
        print(f"❌ FAILURE: Only expanded to {len(expanded)} deliverables (< 100)")
    print("=" * 80)
    
    return success

if __name__ == "__main__":
    try:
        success = test_direct_expansion()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)