#!/usr/bin/env python3
"""
Test script to verify that expand_deliverables_for_comprehensive_rfp generates 100+ deliverables
for comprehensive luxury fashion RFPs
"""

import sys
import json
from ai_planner_agencydb import expand_deliverables_for_comprehensive_rfp, compose_plan_from_agencydb

def create_luxury_fashion_rfp_summary():
    """Create a mock summary for a comprehensive luxury fashion RFP"""
    return {
        "summary": "Global luxury fashion brand campaign for Spring/Summer collection launch across multiple markets with integrated digital and traditional channels targeting affluent millennials and gen z consumers",
        "goals": [
            "Launch new Spring/Summer collection globally",
            "Increase brand awareness in emerging markets",
            "Drive e-commerce sales by 40%",
            "Establish leadership in sustainable luxury fashion"
        ],
        "channels": [
            "Digital",
            "Social Media",
            "Traditional Media",
            "Influencer Marketing",
            "Events"
        ],
        "markets": [
            "North America",
            "Europe",
            "Asia-Pacific",
            "Latin America",
            "Middle East"
        ],
        "compliance": ["GDPR", "CCPA", "Advertising Standards"],
        "languages": ["English", "French", "Chinese", "Spanish", "Arabic"],
        "timeline_weeks": 52,  # Annual engagement
        "budget_tier": "premium",
        "complexity": "high",
        "risk_flags": ["Global coordination", "Multiple time zones", "Luxury brand standards"]
    }

def create_mock_deliverables(count=40):
    """Create mock deliverables to test expansion"""
    deliverables = []
    departments = ["Strategy", "Creative", "Content", "Paid Media", "Technology", "Integrated Marketing Management"]
    
    deliverable_types = {
        "Strategy": ["Brand Strategy", "Market Analysis", "Consumer Research", "Competitive Audit", "Campaign Strategy", "Persona Development"],
        "Creative": ["Campaign Concept", "Visual Identity", "Brand Guidelines", "Ad Creative", "Video Production", "Photography"],
        "Content": ["Editorial Calendar", "Blog Content", "Social Content", "Email Templates", "Product Descriptions", "Influencer Brief"],
        "Paid Media": ["Media Plan", "Campaign Setup", "Performance Reports", "Budget Allocation", "Audience Targeting", "Ad Optimization"],
        "Technology": ["Website Development", "App Development", "Analytics Setup", "CRM Integration", "E-commerce Platform", "Marketing Automation"],
        "Integrated Marketing Management": ["Project Plan", "Status Reports", "Team Coordination", "Vendor Management", "Budget Tracking", "Performance Dashboard"]
    }
    
    for i in range(count):
        dept = departments[i % len(departments)]
        deliverable_type = deliverable_types[dept][i % len(deliverable_types[dept])]
        
        deliverables.append({
            "id": f"DELIV_{i:03d}",
            "dept": dept,
            "title": f"{deliverable_type} - Deliverable {i+1}",
            "calibrated_confidence": 0.7 + (i % 3) * 0.1,  # Vary confidence between 0.7-0.9
            "level": "deliverable",
            "pass": True
        })
    
    return deliverables

def test_expansion():
    """Test the expansion function for comprehensive RFPs"""
    print("=" * 80)
    print("TESTING LUXURY FASHION RFP EXPANSION")
    print("=" * 80)
    
    # Create test data
    summary = create_luxury_fashion_rfp_summary()
    initial_deliverables = create_mock_deliverables(40)  # Start with 40 deliverables
    
    print(f"\nInitial setup:")
    print(f"  - RFP Type: Luxury Fashion (Global, Multi-channel, Annual)")
    print(f"  - Markets: {', '.join(summary['markets'])}")
    print(f"  - Channels: {', '.join(summary['channels'])}")
    print(f"  - Timeline: {summary['timeline_weeks']} weeks")
    print(f"  - Complexity: {summary['complexity']}")
    print(f"  - Initial deliverables: {len(initial_deliverables)}")
    
    # Test expansion
    print(f"\nRunning expansion with target_count=100...")
    expanded_deliverables = expand_deliverables_for_comprehensive_rfp(
        deliverables=initial_deliverables,
        summary=summary,
        target_count=100
    )
    
    # Analyze results
    print(f"\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Final deliverable count: {len(expanded_deliverables)}")
    
    # Check if we hit the target
    if len(expanded_deliverables) >= 100:
        print("✅ SUCCESS: Generated 100+ deliverables!")
    else:
        print(f"❌ FAILED: Only generated {len(expanded_deliverables)} deliverables (target was 100+)")
        sys.exit(1)
    
    # Analyze variations by type
    variations = {
        "Regional": 0,
        "Phase": 0,
        "Channel": 0,
        "Quarter": 0,
        "Season": 0,
        "Collection": 0,
        "Audience": 0,
        "Product": 0,
        "Year": 0,
        "Other": 0
    }
    
    for deliv in expanded_deliverables:
        title = deliv.get("title", "")
        deliv_id = deliv.get("id", "")
        
        if any(region in title for region in ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East", "Africa"]):
            variations["Regional"] += 1
        elif any(phase in title for phase in ["Discovery", "Launch", "Growth", "Optimization"]):
            variations["Phase"] += 1
        elif any(channel in title for channel in ["Instagram", "Facebook", "TikTok", "Web", "Mobile", "Email", "Print", "TV"]):
            variations["Channel"] += 1
        elif any(quarter in title for quarter in ["Q1", "Q2", "Q3", "Q4"]):
            variations["Quarter"] += 1
        elif any(season in title for season in ["Spring", "Summer", "Fall", "Winter"]):
            variations["Season"] += 1
        elif any(collection in title for collection in ["Spring/Summer", "Fall/Winter", "Resort", "Pre-Fall"]):
            variations["Collection"] += 1
        elif any(segment in title for segment in ["Gen Z", "Millennials", "Gen X", "Boomers", "Affluent"]):
            variations["Audience"] += 1
        elif any(product in title for product in ["Menswear", "Womenswear", "Accessories", "Footwear", "Product"]):
            variations["Product"] += 1
        elif any(year in title for year in ["Year 1", "Year 2", "Year 3"]):
            variations["Year"] += 1
        elif deliv_id not in [d["id"] for d in initial_deliverables]:
            variations["Other"] += 1
    
    print(f"\nVariation Breakdown:")
    for var_type, count in variations.items():
        if count > 0:
            print(f"  - {var_type}: {count}")
    
    # Check department distribution
    dept_counts = {}
    for deliv in expanded_deliverables:
        dept = deliv.get("dept", "Unknown")
        dept_counts[dept] = dept_counts.get(dept, 0) + 1
    
    print(f"\nDepartment Distribution:")
    for dept, count in sorted(dept_counts.items()):
        print(f"  - {dept}: {count}")
    
    # Sample some expanded deliverables
    print(f"\nSample of Expanded Deliverables (showing variations):")
    samples = [d for d in expanded_deliverables if d["id"] not in [x["id"] for x in initial_deliverables]][:10]
    for i, sample in enumerate(samples, 1):
        print(f"  {i}. {sample['title']} (Dept: {sample['dept']}, Confidence: {sample.get('calibrated_confidence', 0):.2f})")
    
    print(f"\n" + "=" * 80)
    print("TEST COMPLETED SUCCESSFULLY")
    print("The enhanced expansion function generates 100+ deliverables for comprehensive RFPs")
    print("=" * 80)

if __name__ == "__main__":
    test_expansion()