import requests
import json

# Test comprehensive beauty brand RFP
rfp_text = """
Glow Beauty is launching a revolutionary clean beauty skincare line with clinically proven 
anti-aging ingredients. We need a comprehensive campaign including:

1. Hero product launch for our Vitamin C serum with before/after clinical photography
2. Educational tutorial videos featuring professional MUAs and dermatologists  
3. Influencer seeding program targeting beauty gurus and micro-influencers on TikTok
4. Sephora and Ulta retail launch with in-store events and sampling programs
5. Sustainability story highlighting our refillable packaging and cruelty-free certification
6. Ingredient deep-dive content on our patented botanical technology
7. Holiday gift set campaign for Q4
8. Virtual consultation platform for personalized skincare routines
"""

# API base URL
base_url = "http://localhost:5000"

print("=" * 70)
print("BEAUTY BRAND RFP TEST - Glow Beauty Skincare Launch")
print("=" * 70)

# 1. Get available templates
print("\n1. AVAILABLE INDUSTRY TEMPLATES:")
templates = requests.get(f"{base_url}/api/industry/templates").json()
for template in templates["templates"]:
    if template["available"]:
        print(f"   ✓ {template['label']} ({template['value']})")

# 2. Get deliverable suggestions
print("\n2. SUGGESTED DELIVERABLES FOR GLOW BEAUTY:")
suggest_response = requests.post(
    f"{base_url}/api/industry/suggest-deliverables",
    json={"industry": "beauty", "rfp_text": rfp_text}
).json()

print(f"   Keywords found: {', '.join(suggest_response['keywords_found'])}")
print(f"   Total deliverables suggested: {suggest_response['total_suggested']}")
print("\n   Top deliverables:")
for i, deliverable in enumerate(suggest_response["deliverables"][:5], 1):
    print(f"   {i}. {deliverable['name']} ({deliverable['code']})")
    print(f"      - Category: {deliverable['category']}")
    print(f"      - Base hours: {deliverable['base_hours']}")
    print(f"      - Confidence: {deliverable['confidence']}")

# Extract deliverable codes for timeline and pricing
deliverable_codes = [d["code"] for d in suggest_response["deliverables"][:6]]

# 3. Calculate timeline
print("\n3. PROJECT TIMELINE:")
timeline_response = requests.post(
    f"{base_url}/api/industry/calculate-timeline",
    json={
        "industry": "beauty",
        "deliverable_codes": deliverable_codes,
        "start_date": "2025-02-01"
    }
).json()

timeline = timeline_response["timeline"]
print(f"   Total duration: {timeline['total_duration_weeks']} weeks")
print(f"   Start date: Feb 1, 2025")
print(f"   Launch date: ~May 2025")

print("\n   Project phases:")
for phase in timeline["phases"]:
    print(f"   • {phase['name']}: {phase['duration_weeks']} weeks")

if timeline.get("beauty_calendar_conflicts"):
    print("\n   ⚠️  Calendar conflicts:")
    for conflict in timeline["beauty_calendar_conflicts"]:
        print(f"   • {conflict['event']}: {conflict['impact']}")

if timeline.get("regulatory_requirements"):
    print("\n   📋 Regulatory requirements:")
    for req in timeline["regulatory_requirements"]:
        print(f"   • {req['requirement']}: {req['lead_time_weeks']} weeks lead time")

# 4. Calculate pricing
print("\n4. PROJECT PRICING:")
pricing_response = requests.post(
    f"{base_url}/api/industry/calculate-pricing",
    json={
        "industry": "beauty",
        "deliverable_codes": deliverable_codes,
        "base_rate": 175
    }
).json()

pricing = pricing_response["pricing"]
print(f"   Base rate: ${pricing_response['base_rate']}/hour")
print(f"   Subtotal: ${pricing['subtotal']:,.2f}")

if pricing.get("adjustments"):
    print("\n   Premium adjustments:")
    for adj in pricing["adjustments"]:
        print(f"   • {adj['type']}: ${adj['amount']:,.2f}")

print(f"\n   TOTAL PROJECT COST: ${pricing['total']:,.2f}")

print("\n" + "=" * 70)
print("Beauty template successfully tested with Glow Beauty skincare launch!")
print("=" * 70)
