#!/usr/bin/env python3
"""
Test script to verify the enhanced scoring system properly recognizes direct matches.
Should show 90%+ confidence when deliverable names directly match RFP content.
"""

import json
from ai_weighted_matcher import score_rfp

# Sample RFP text from Uncommon Schools that explicitly mentions media services
UNCOMMON_SCHOOLS_RFP_SAMPLE = """
Uncommon Schools is seeking a media agency partner to manage our comprehensive media planning, 
media buying, and media strategy efforts. The selected agency will be responsible for:

1. Media Planning: Develop comprehensive media plans across all channels
2. Media Buying: Execute media purchases across digital and traditional channels
3. Media Strategy: Create strategic approaches for reaching our target audiences
4. Media Trafficking: Manage the delivery and tracking of all media assets
5. Brand Strategy: Develop and maintain our brand positioning and messaging
6. Creative Development: Create compelling creative assets for campaigns
7. Social Media Management: Oversee all social media channels and campaigns
8. Influencer Marketing: Identify and manage influencer partnerships
9. Content Creation: Develop engaging content for various platforms

We need expertise in paid media planning, programmatic buying, and comprehensive 
media optimization. The agency should have experience with education sector marketing
and non-profit campaigns.
"""

def test_direct_match_scoring():
    """Test that direct keyword matches get 90%+ confidence"""
    print("=" * 80)
    print("TESTING DIRECT MATCH SCORING ENHANCEMENT")
    print("=" * 80)
    
    # Run the scoring
    result = score_rfp(
        rfp_text=UNCOMMON_SCHOOLS_RFP_SAMPLE,
        ai_xlsx_path="AI_Matching_Rules_full.xlsx"
    )
    
    # Define expected direct matches
    expected_high_confidence = [
        "media planning",
        "media buying", 
        "media strategy",
        "media trafficking",
        "brand strategy",
        "creative development",
        "social media",
        "influencer marketing",
        "content creation"
    ]
    
    print("\nDELIVERABLES WITH DIRECT MATCHES (Should be 90%+):")
    print("-" * 80)
    
    # Check top deliverables
    high_confidence_count = 0
    direct_match_count = 0
    
    for item in result["deliverables"][:20]:  # Check top 20 results
        deliverable_name = item["deliverable"].lower()
        confidence = item["match_percent"]
        tfidf_sim = item.get("tfidf_similarity", 0)
        is_direct_match = item.get("direct_match", False)
        matched_keywords = item.get("matched_keywords", [])
        base_percent = item.get("base_percent", confidence)
        
        # Check if this is a media-related or other expected deliverable
        is_expected = any(keyword in deliverable_name for keyword in expected_high_confidence)
        
        if is_direct_match:
            direct_match_count += 1
            print(f"\n✓ {item['deliverable']}")
            print(f"  Confidence: {confidence:.1f}% {'✅' if confidence >= 90 else '⚠️ NEEDS BOOST'}")
            print(f"  Base Score: {base_percent:.1f}% → Boosted to: {confidence:.1f}%")
            print(f"  TF-IDF: {tfidf_sim:.3f}")
            print(f"  Matched Keywords: {', '.join(matched_keywords[:3])}")
            
            if confidence >= 90:
                high_confidence_count += 1
            elif is_expected:
                print(f"  ⚠️ WARNING: Expected 90%+ for '{item['deliverable']}' but got {confidence:.1f}%")
        
        # Also show high-scoring items without direct match for comparison
        elif confidence >= 70:
            print(f"\n  {item['deliverable']}")
            print(f"  Confidence: {confidence:.1f}% (no direct match)")
            print(f"  TF-IDF: {tfidf_sim:.3f}")
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"• Total direct matches found: {direct_match_count}")
    print(f"• Direct matches with 90%+ confidence: {high_confidence_count}/{direct_match_count}")
    
    # Check specific expected deliverables
    print("\nSPECIFIC CHECKS FOR MEDIA DELIVERABLES:")
    print("-" * 80)
    
    media_deliverables = [d for d in result["deliverables"] 
                         if any(term in d["deliverable"].lower() 
                               for term in ["media", "brand strategy", "creative", "social", "influencer", "content"])]
    
    for d in media_deliverables[:10]:
        status = "✅" if d["match_percent"] >= 90 else "❌"
        boost_info = f" (boosted from {d.get('base_percent', d['match_percent']):.1f}%)" if d.get('direct_match') else ""
        print(f"{status} {d['deliverable']}: {d['match_percent']:.1f}%{boost_info}")
    
    # Test pass/fail
    print("\n" + "=" * 80)
    if high_confidence_count >= direct_match_count * 0.8:  # 80% of direct matches should be 90%+
        print("✅ TEST PASSED: Direct match boosting is working correctly!")
    else:
        print("❌ TEST FAILED: Direct matches are not getting sufficient confidence boost")
    
    return result

if __name__ == "__main__":
    test_direct_match_scoring()