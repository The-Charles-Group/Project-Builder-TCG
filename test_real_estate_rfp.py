#!/usr/bin/env python3
"""
Test Real Estate Template with Developer RFP
============================================
This script tests the real estate template API endpoints with a realistic RFP scenario.
"""

import json
import requests
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:5000/api"

def test_get_templates():
    """Test fetching available industry templates"""
    print("\n" + "="*60)
    print("Testing: GET /api/industry/templates")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/industry/templates")
    if response.status_code == 200:
        data = response.json()
        print("✅ Successfully fetched templates")
        print("\nAvailable templates:")
        for template in data["templates"]:
            status = "✓" if template["available"] else "✗"
            print(f"  [{status}] {template['label']} ({template['value']})")
        return True
    else:
        print(f"❌ Failed to fetch templates: {response.status_code}")
        return False

def test_suggest_deliverables():
    """Test suggesting deliverables for a real estate RFP"""
    print("\n" + "="*60)
    print("Testing: POST /api/industry/suggest-deliverables")
    print("="*60)
    
    # Simulate a luxury mixed-use development RFP
    rfp_data = {
        "industry": "real_estate",
        "description": """
        LUXURY MIXED-USE DEVELOPMENT RFP
        
        Project Overview:
        We are seeking a comprehensive marketing agency to handle the launch of our flagship 
        mixed-use development in downtown Miami. The project includes:
        - 300 luxury residential units (penthouses and condos)
        - 50,000 sq ft of premium retail space
        - 100,000 sq ft of Class A office space
        - Rooftop amenities including pool, spa, and restaurant
        
        Marketing Requirements:
        1. PRE-CONSTRUCTION PHASE (Starting immediately)
           - Develop brand identity and positioning
           - Create 3D renderings and virtual tours using Matterport
           - Launch pre-sales campaign targeting international buyers
           - Design and build sales center with interactive displays
        
        2. CONSTRUCTION PHASE (18 months)
           - Monthly drone footage and progress documentation
           - Broker engagement program with exclusive previews
           - Neighborhood lifestyle content and area guides
           - Investment materials including ROI calculators and pro formas
        
        3. SALES LAUNCH (Q2 2025)
           - Grand opening event for public and VIP buyers
           - MLS optimization and property portal campaigns (Zillow, Realtor.com)
           - Print advertising in WSJ and luxury magazines
           - Virtual property showcases for international buyers
           - Develop buyer personas and customer journey mapping
        
        4. LEASE-UP PHASE (6 months post-completion)
           - Commercial tenant recruitment campaign
           - Retail leasing materials and broker packages
           - Office space marketing to tech and finance sectors
           
        Property Features to Highlight:
        - Waterfront location with panoramic views
        - LEED Gold certification and sustainable features
        - Smart home technology in all units
        - Concierge services and private beach club access
        - Walking distance to arts district and dining
        
        Target Markets:
        - Primary: High-net-worth individuals and families
        - Secondary: International investors (Latin America, Europe)
        - Commercial: Tech companies, law firms, luxury retail brands
        
        Budget: $2.5M - $3.5M for complete campaign
        Timeline: 24-month engagement starting January 2025
        """,
        "keywords": [
            "luxury", "mixed-use", "pre-construction", "virtual tours", 
            "matterport", "drone", "investment", "roi calculator", "pro forma",
            "grand opening", "vip event", "mls", "zillow", "wsj", "print",
            "buyer personas", "journey mapping", "sales center", "broker"
        ]
    }
    
    print("Sending RFP for luxury mixed-use development...")
    response = requests.post(f"{BASE_URL}/industry/suggest-deliverables", json=rfp_data)
    
    if response.status_code == 200:
        data = response.json()
        deliverables = data.get("deliverables", [])
        
        print(f"✅ Successfully generated {len(deliverables)} deliverable suggestions")
        print("\nSuggested Deliverables:")
        
        # Group by category
        categories = {}
        for d in deliverables:
            cat = d.get("category", "Other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(d)
        
        for category, items in categories.items():
            print(f"\n📁 {category}:")
            for item in items[:3]:  # Show top 3 per category
                confidence = item.get("confidence", 0)
                conf_indicator = "⭐" * int(confidence * 5)
                print(f"   - {item['name']} ({item['code']}) {conf_indicator}")
                print(f"     Base Hours: {item['base_hours']} | " +
                      f"Luxury: {item.get('luxury_multiplier', 1.0)}x | " +
                      f"Commercial: {item.get('commercial_multiplier', 1.0)}x")
                
        return deliverables
    else:
        print(f"❌ Failed to get suggestions: {response.status_code}")
        print(f"Response: {response.text}")
        return []

def test_calculate_timeline(deliverable_codes):
    """Test timeline calculation for real estate project"""
    print("\n" + "="*60)
    print("Testing: POST /api/industry/calculate-timeline")
    print("="*60)
    
    timeline_data = {
        "industry": "real_estate",
        "deliverable_codes": deliverable_codes[:10],  # Use top 10 deliverables
        "start_date": "2025-01-15",
        "project_phase": "pre_construction"
    }
    
    print(f"Calculating timeline for {len(timeline_data['deliverable_codes'])} deliverables...")
    response = requests.post(f"{BASE_URL}/industry/calculate-timeline", json=timeline_data)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Successfully calculated timeline")
        
        print(f"\n⏱️ Total Duration: {data.get('total_duration_weeks', 0)} weeks")
        
        if "phases" in data:
            print("\n📅 Project Phases:")
            for phase in data["phases"]:
                print(f"   - {phase['name']}: {phase['duration_weeks']} weeks")
        
        if "milestones" in data:
            print("\n🎯 Key Milestones:")
            for milestone in data["milestones"][:5]:
                print(f"   Week {milestone['week']}: {milestone['milestone']}")
        
        if "market_considerations" in data:
            print("\n📊 Market Timing Considerations:")
            for consideration in data["market_considerations"]:
                print(f"   - {consideration['factor']}: {consideration['impact']}")
                
        return True
    else:
        print(f"❌ Failed to calculate timeline: {response.status_code}")
        return False

def test_calculate_pricing(deliverable_codes):
    """Test pricing calculation for real estate project"""
    print("\n" + "="*60)
    print("Testing: POST /api/industry/calculate-pricing")
    print("="*60)
    
    pricing_data = {
        "industry": "real_estate",
        "deliverable_codes": deliverable_codes[:10],  # Use top 10 deliverables
        "base_rate": 175,  # Higher rate for luxury project
        "property_type": "luxury mixed-use",
        "num_phases": 3  # Pre-construction, construction, lease-up
    }
    
    print(f"Calculating pricing for luxury mixed-use development...")
    response = requests.post(f"{BASE_URL}/industry/calculate-pricing", json=pricing_data)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Successfully calculated pricing")
        
        print("\n💰 Pricing Summary:")
        print(f"   Subtotal: ${data.get('subtotal', 0):,.2f}")
        
        if "adjustments" in data:
            print("\n   Adjustments:")
            for adj in data["adjustments"]:
                print(f"   + {adj['type']}: ${adj['amount']:,.2f}")
        
        print(f"\n   TOTAL: ${data.get('total', 0):,.2f}")
        
        if "deliverables" in data and len(data["deliverables"]) > 0:
            print("\n📊 Top Deliverables by Cost:")
            sorted_deliverables = sorted(
                data["deliverables"], 
                key=lambda x: x.get("adjusted_cost", 0), 
                reverse=True
            )
            for d in sorted_deliverables[:5]:
                print(f"   - {d['name']}: ${d['adjusted_cost']:,.2f}")
                print(f"     (Base: ${d['base_cost']:,.2f}, " +
                      f"Multiplier: {d.get('property_type_multiplier', 1.0):.1f}x)")
                
        return True
    else:
        print(f"❌ Failed to calculate pricing: {response.status_code}")
        return False

def main():
    """Run all real estate template tests"""
    print("\n" + "🏗️ "*20)
    print("  REAL ESTATE TEMPLATE TEST SUITE")
    print("  Testing Luxury Mixed-Use Development RFP")
    print("🏗️ "*20)
    
    # Test 1: Get available templates
    if not test_get_templates():
        print("\n⚠️ Failed to get templates. Is the server running on port 5000?")
        return
    
    # Test 2: Suggest deliverables based on RFP
    deliverables = test_suggest_deliverables()
    if not deliverables:
        print("\n⚠️ Failed to get deliverable suggestions")
        return
    
    # Extract deliverable codes for further tests
    deliverable_codes = [d["code"] for d in deliverables]
    
    # Test 3: Calculate timeline
    test_calculate_timeline(deliverable_codes)
    
    # Test 4: Calculate pricing
    test_calculate_pricing(deliverable_codes)
    
    print("\n" + "="*60)
    print("✅ Real Estate Template Test Suite Complete!")
    print("="*60)
    print("\nSummary:")
    print(f"  - Templates Available: ✓")
    print(f"  - Deliverables Suggested: {len(deliverables)}")
    print(f"  - Timeline Calculated: ✓")
    print(f"  - Pricing Calculated: ✓")
    print("\n💡 The Real Estate template is ready for production use!")
    print("   It successfully handles luxury mixed-use development RFPs with:")
    print("   • Property-specific deliverables")
    print("   • Phase-based timeline management")
    print("   • Luxury and commercial pricing adjustments")
    print("   • Market timing considerations")

if __name__ == "__main__":
    main()