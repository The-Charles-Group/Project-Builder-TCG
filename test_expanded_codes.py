#!/usr/bin/env python3
"""Test script to verify the expanded deliverable code mapping fix"""

# Import the function from main.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import extract_base_deliverable_code

def test_extract_base_deliverable_code():
    """Test the extract_base_deliverable_code function with various inputs"""
    
    test_cases = [
        # (input, expected_output)
        ('DEL-0027-Google_Ads', 'DEL-0027'),
        ('DEL-0036-North_America', 'DEL-0036'),
        ('DEL-0042-Strategy-Q1', 'DEL-0042'),
        ('DEL-0015-Creative-Launch', 'DEL-0015'),
        ('DEL-0001', 'DEL-0001'),  # No suffix, should remain unchanged
        ('DEL-9999-Media-Instagram_Ads', 'DEL-9999'),
        ('DEL-1234-Content-Q2-Review', 'DEL-1234'),
        ('DEL-0050-IMM-Discovery', 'DEL-0050'),
        ('DEL-0123-Tech-Development', 'DEL-0123'),
        ('', ''),  # Empty string
        (None, None),  # None value
        ('INVALID-CODE', 'INVALID-CODE'),  # Invalid format, should return as-is
        ('DEL-ABC', 'DEL-ABC'),  # Non-numeric code, should return as-is
    ]
    
    passed = 0
    failed = 0
    
    print("Testing extract_base_deliverable_code function...")
    print("-" * 60)
    
    for input_code, expected in test_cases:
        try:
            result = extract_base_deliverable_code(input_code)
            if result == expected:
                print(f"✅ PASS: '{input_code}' -> '{result}'")
                passed += 1
            else:
                print(f"❌ FAIL: '{input_code}' -> '{result}' (expected '{expected}')")
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: '{input_code}' raised {e}")
            failed += 1
    
    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    # Test the integration with a mock scenario
    print("\nTesting integration scenario:")
    print("-" * 60)
    
    # Example of how the expanded code would be used in the build process
    expanded_codes = [
        'DEL-0027-Google_Ads',
        'DEL-0036-Media-North_America', 
        'DEL-0042-Strategy-Q1'
    ]
    
    print("Simulating build process with expanded codes:")
    for code in expanded_codes:
        base = extract_base_deliverable_code(code)
        suffix = code[len(base):] if len(code) > len(base) else ""
        suffix_clean = suffix.lstrip('-').replace('_', ' ') if suffix else "(no suffix)"
        print(f"  Code: {code}")
        print(f"    -> Base: {base}")
        print(f"    -> Suffix: {suffix_clean}")
        print()
    
    return passed, failed

if __name__ == "__main__":
    passed, failed = test_extract_base_deliverable_code()
    exit(0 if failed == 0 else 1)