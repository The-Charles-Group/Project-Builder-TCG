#!/usr/bin/env python3
"""Test GPT-5 analysis for luxury RFP to verify 100+ deliverables are suggested"""

import requests
import json

# Test luxury RFP content
luxury_rfp = """
Luxury Brand Campaign - Casa Dragones Ultra-Premium Tequila

Client: Casa Dragones - Ultra-luxury tequila brand
Campaign: Global luxury positioning and market expansion
Budget: $25 million
Duration: 12 months

Requirements:
- Complete brand repositioning for ultra-high-net-worth individuals
- Global campaign across 15 markets
- Digital-first luxury experience
- Exclusive events and partnerships
- Celebrity and influencer collaborations
- Content creation for all channels
- E-commerce and DTC strategy
- Luxury retail partnerships
- Premium packaging and unboxing experiences
- Metaverse and Web3 activations
- Sustainability storytelling
- Heritage and craftsmanship content
- Private jet and yacht partnerships
- Art Basel and luxury event presence
- Michelin-starred restaurant collaborations
- Private member club partnerships
- Luxury travel experiences
- Collector's edition releases
- NFT and digital collectibles
- Luxury lifestyle content
- Social media management
- Performance marketing
- PR and media relations
- Crisis management preparedness
"""

# Make request to analyze endpoint
print("Testing GPT-5 analysis for luxury RFP...")
print("=" * 60)

try:
    response = requests.post(
        "http://localhost:5000/api/suggest_by_text",
        json={
            "rfp_text": luxury_rfp,
            "category": "Marketing",
            "strictness": "relaxed",  # Allow maximum suggestions
            "limit": 200  # Allow up to 200 suggestions
        },
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        
        # Check deliverables count
        deliverables = result.get("deliverables", [])
        print(f"\n✅ Analysis returned {len(deliverables)} deliverables")
        
        if len(deliverables) < 50:
            print(f"⚠️ WARNING: Only {len(deliverables)} deliverables returned (expected 100+)")
            print("This suggests GPT-5 may still be falling back to embeddings!")
        elif len(deliverables) < 100:
            print(f"⚠️ PARTIAL: {len(deliverables)} deliverables (expected 100+ for luxury campaign)")
        else:
            print(f"✅ EXCELLENT: {len(deliverables)} deliverables for luxury campaign!")
        
        # Show first 10 deliverables as sample
        print("\nFirst 10 deliverables:")
        for i, deliv in enumerate(deliverables[:10], 1):
            print(f"{i}. {deliv.get('name', 'Unknown')}")
            if 'ai_confidence' in deliv:
                print(f"   Confidence: {deliv['ai_confidence']}")
        
        # Check if using GPT-5 or embeddings
        metadata = result.get("metadata", {})
        if metadata.get("analysis_method") == "embeddings":
            print("\n⚠️ CRITICAL: System is using EMBEDDINGS fallback, not GPT-5!")
        elif metadata.get("analysis_method") == "gpt5":
            print("\n✅ Confirmed: Using GPT-5 intelligence")
        
        # Show total components and tasks
        total_components = sum(len(d.get("components", [])) for d in deliverables)
        print(f"\nTotal components across all deliverables: {total_components}")
        
        if total_components < 200:
            print(f"⚠️ Low component count suggests incomplete analysis")
        else:
            print(f"✅ Good component coverage for comprehensive campaign")
            
    else:
        print(f"❌ Request failed with status {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error testing GPT-5: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete")