"""
Unit tests for TF-IDF selection mode feature.
Tests the should_select_deliverable function with all three selection modes.
"""

import sys
import os

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import should_select_deliverable, CONF_THRESHOLD, TFIDF_THRESHOLD


def test_confidence_only_mode():
    """Test confidence_only mode selects based on AI confidence only"""
    print("\n=== Testing confidence_only mode ===")
    
    # Case 1: High confidence, low TF-IDF -> should select
    result = should_select_deliverable(
        match_percent=80.0,
        tfidf_similarity=0.30,
        selection_mode="confidence_only"
    )
    assert result["selected"] == True, "Should select with high confidence"
    assert result["selection_reason"]["by_confidence"] == True
    assert result["selection_reason"]["by_tfidf"] == False
    print("✓ High confidence, low TF-IDF: selected")
    
    # Case 2: Low confidence, high TF-IDF -> should NOT select
    result = should_select_deliverable(
        match_percent=50.0,
        tfidf_similarity=0.85,
        selection_mode="confidence_only"
    )
    assert result["selected"] == False, "Should NOT select with low confidence"
    assert result["selection_reason"]["by_confidence"] == False
    assert result["selection_reason"]["by_tfidf"] == True
    print("✓ Low confidence, high TF-IDF: not selected")
    
    # Case 3: Both high -> should select
    result = should_select_deliverable(
        match_percent=85.0,
        tfidf_similarity=0.80,
        selection_mode="confidence_only"
    )
    assert result["selected"] == True
    print("✓ Both high: selected")
    
    # Case 4: Both low -> should NOT select
    result = should_select_deliverable(
        match_percent=50.0,
        tfidf_similarity=0.30,
        selection_mode="confidence_only"
    )
    assert result["selected"] == False
    print("✓ Both low: not selected")


def test_tfidf_only_mode():
    """Test tfidf_only mode selects based on TF-IDF similarity only"""
    print("\n=== Testing tfidf_only mode ===")
    
    # Case 1: Low confidence, high TF-IDF -> should select
    result = should_select_deliverable(
        match_percent=50.0,
        tfidf_similarity=0.85,
        selection_mode="tfidf_only"
    )
    assert result["selected"] == True, "Should select with high TF-IDF"
    assert result["selection_reason"]["by_confidence"] == False
    assert result["selection_reason"]["by_tfidf"] == True
    print("✓ Low confidence, high TF-IDF: selected")
    
    # Case 2: High confidence, low TF-IDF -> should NOT select
    result = should_select_deliverable(
        match_percent=85.0,
        tfidf_similarity=0.30,
        selection_mode="tfidf_only"
    )
    assert result["selected"] == False, "Should NOT select with low TF-IDF"
    assert result["selection_reason"]["by_confidence"] == True
    assert result["selection_reason"]["by_tfidf"] == False
    print("✓ High confidence, low TF-IDF: not selected")
    
    # Case 3: Both high -> should select
    result = should_select_deliverable(
        match_percent=85.0,
        tfidf_similarity=0.80,
        selection_mode="tfidf_only"
    )
    assert result["selected"] == True
    print("✓ Both high: selected")
    
    # Case 4: Both low -> should NOT select
    result = should_select_deliverable(
        match_percent=50.0,
        tfidf_similarity=0.30,
        selection_mode="tfidf_only"
    )
    assert result["selected"] == False
    print("✓ Both low: not selected")


def test_both_mode():
    """Test both mode selects if EITHER method meets threshold (union)"""
    print("\n=== Testing both (union) mode ===")
    
    # Case 1: High confidence, low TF-IDF -> should select
    result = should_select_deliverable(
        match_percent=80.0,
        tfidf_similarity=0.30,
        selection_mode="both"
    )
    assert result["selected"] == True, "Should select with high confidence (union)"
    assert result["selection_reason"]["by_confidence"] == True
    assert result["selection_reason"]["by_tfidf"] == False
    print("✓ High confidence only: selected (union)")
    
    # Case 2: Low confidence, high TF-IDF -> should select
    result = should_select_deliverable(
        match_percent=50.0,
        tfidf_similarity=0.85,
        selection_mode="both"
    )
    assert result["selected"] == True, "Should select with high TF-IDF (union)"
    assert result["selection_reason"]["by_confidence"] == False
    assert result["selection_reason"]["by_tfidf"] == True
    print("✓ High TF-IDF only: selected (union)")
    
    # Case 3: Both high -> should select
    result = should_select_deliverable(
        match_percent=85.0,
        tfidf_similarity=0.80,
        selection_mode="both"
    )
    assert result["selected"] == True
    assert result["selection_reason"]["by_confidence"] == True
    assert result["selection_reason"]["by_tfidf"] == True
    print("✓ Both high: selected")
    
    # Case 4: Both low -> should NOT select
    result = should_select_deliverable(
        match_percent=50.0,
        tfidf_similarity=0.30,
        selection_mode="both"
    )
    assert result["selected"] == False, "Should NOT select when both are low"
    assert result["selection_reason"]["by_confidence"] == False
    assert result["selection_reason"]["by_tfidf"] == False
    print("✓ Both low: not selected")


def test_threshold_boundaries():
    """Test exact threshold boundaries"""
    print("\n=== Testing threshold boundaries ===")
    
    # At exact threshold (confidence)
    result = should_select_deliverable(
        match_percent=CONF_THRESHOLD,
        tfidf_similarity=0.0,
        selection_mode="confidence_only"
    )
    assert result["selected"] == True, f"Should select at exact confidence threshold ({CONF_THRESHOLD})"
    print(f"✓ Exact confidence threshold ({CONF_THRESHOLD}): selected")
    
    # Just below threshold (confidence)
    result = should_select_deliverable(
        match_percent=CONF_THRESHOLD - 0.1,
        tfidf_similarity=0.0,
        selection_mode="confidence_only"
    )
    assert result["selected"] == False, f"Should NOT select below confidence threshold ({CONF_THRESHOLD - 0.1})"
    print(f"✓ Below confidence threshold ({CONF_THRESHOLD - 0.1}): not selected")
    
    # At exact threshold (TF-IDF)
    result = should_select_deliverable(
        match_percent=0.0,
        tfidf_similarity=TFIDF_THRESHOLD,
        selection_mode="tfidf_only"
    )
    assert result["selected"] == True, f"Should select at exact TF-IDF threshold ({TFIDF_THRESHOLD})"
    print(f"✓ Exact TF-IDF threshold ({TFIDF_THRESHOLD}): selected")
    
    # Just below threshold (TF-IDF)
    result = should_select_deliverable(
        match_percent=0.0,
        tfidf_similarity=TFIDF_THRESHOLD - 0.01,
        selection_mode="tfidf_only"
    )
    assert result["selected"] == False, f"Should NOT select below TF-IDF threshold ({TFIDF_THRESHOLD - 0.01})"
    print(f"✓ Below TF-IDF threshold ({TFIDF_THRESHOLD - 0.01}): not selected")


def test_invalid_mode_fallback():
    """Test that invalid mode defaults to confidence_only"""
    print("\n=== Testing invalid mode fallback ===")
    
    result = should_select_deliverable(
        match_percent=80.0,
        tfidf_similarity=0.30,
        selection_mode="invalid_mode"
    )
    assert result["selected"] == True, "Invalid mode should fallback to confidence_only"
    print("✓ Invalid mode falls back to confidence_only")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TF-IDF Selection Mode Unit Tests")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  CONF_THRESHOLD: {CONF_THRESHOLD}")
    print(f"  TFIDF_THRESHOLD: {TFIDF_THRESHOLD}")
    
    try:
        test_confidence_only_mode()
        test_tfidf_only_mode()
        test_both_mode()
        test_threshold_boundaries()
        test_invalid_mode_fallback()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60 + "\n")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
