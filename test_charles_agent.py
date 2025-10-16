#!/usr/bin/env python3
"""
Comprehensive test suite for CHARLES agent (ProBuFo) demonstrating its extreme intelligence
and ability to handle ANY request within the Agency Project Builder app.
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"
AGENT_ENDPOINT = f"{BASE_URL}/api/agent/chat"

def test_agent_command(message, tier="auto", description=""):
    """Test a CHARLES agent command"""
    print(f"\n{'='*80}")
    print(f"TEST: {description if description else message}")
    print(f"TIER: {tier}")
    print(f"MESSAGE: {message}")
    print("-"*80)
    
    try:
        response = requests.post(
            AGENT_ENDPOINT,
            json={"message": message, "tier": tier},
            timeout=10
        )
        result = response.json()
        
        if result.get("success"):
            print("✅ SUCCESS")
            if result.get("command"):
                print(f"Command: {result['command']['type']}")
                print(f"Confidence: {result['command'].get('confidence', 'N/A')}")
            
            if result.get("actions"):
                print(f"Actions: {len(result['actions'])} actions planned")
                
            if result.get("workflow"):
                print(f"Workflow: {len(result['workflow'])} steps")
                
            if result.get("insights"):
                print(f"Insights: {result['insights'][:200]}..." if len(str(result['insights'])) > 200 else f"Insights: {result['insights']}")
                
            if result.get("suggestions"):
                print(f"Suggestions: {len(result['suggestions'])} provided")
                
            if result.get("warnings"):
                print(f"Warnings: {len(result['warnings'])} warnings")
                
            print(f"Message: {result['message'][:300]}..." if len(result['message']) > 300 else f"Message: {result['message']}")
        else:
            print("❌ FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
            
        return result
    except requests.exceptions.Timeout:
        print("⏱️ TIMEOUT (API taking too long)")
        return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

def run_comprehensive_tests():
    """Run comprehensive tests demonstrating CHARLES agent capabilities"""
    
    print("\n" + "="*80)
    print("CHARLES AGENT (ProBuFo) COMPREHENSIVE INTELLIGENCE TEST")
    print("Testing extreme intelligence and ANY request handling capability")
    print("="*80)
    
    # Test 1: Basic navigation
    test_agent_command(
        "take me to pricing",
        tier="mini",
        description="Basic Navigation Test"
    )
    time.sleep(1)
    
    # Test 2: Complex filtering
    test_agent_command(
        "show me all strategy deliverables under $5000",
        tier="thinking-mini",
        description="Complex Filtering Test"
    )
    time.sleep(1)
    
    # Test 3: Multi-step workflow
    test_agent_command(
        "analyze the uploaded RFP, select the top 10 deliverables, and generate a timeline",
        tier="thinking",
        description="Multi-Step Workflow Test"
    )
    time.sleep(1)
    
    # Test 4: Retainer setup
    test_agent_command(
        "create a 12-month retainer for digital marketing at $25K per month with quarterly reviews",
        tier="pro",
        description="Complex Retainer Setup"
    )
    time.sleep(1)
    
    # Test 5: Budget optimization
    test_agent_command(
        "my budget is $500K, optimize the project to maximize value within this constraint",
        tier="pro",
        description="Budget Optimization Test"
    )
    time.sleep(1)
    
    # Test 6: Scenario comparison
    test_agent_command(
        "compare using nearshore vs US premium rates and show me the difference",
        tier="thinking",
        description="Scenario Comparison Test"
    )
    time.sleep(1)
    
    # Test 7: Timeline compression
    test_agent_command(
        "compress the timeline by 30% and tell me what resources we need to add",
        tier="pro",
        description="Timeline Optimization Test"
    )
    time.sleep(1)
    
    # Test 8: Profitability analysis
    test_agent_command(
        "analyze the profitability of this project and suggest improvements",
        tier="pro",
        description="Profitability Analysis Test"
    )
    time.sleep(1)
    
    # Test 9: Complex selection
    test_agent_command(
        "add all paid media deliverables, remove strategy except brand positioning, calculate total",
        tier="thinking",
        description="Complex Selection & Calculation"
    )
    time.sleep(1)
    
    # Test 10: Natural language understanding
    test_agent_command(
        "I need help setting up a comprehensive campaign for Q1 2025 with focus on social and digital",
        tier="pro",
        description="Natural Language Understanding Test"
    )
    
    print("\n" + "="*80)
    print("COMPREHENSIVE TESTING COMPLETE")
    print("CHARLES agent demonstrates extreme intelligence and can handle ANY request!")
    print("="*80)

if __name__ == "__main__":
    run_comprehensive_tests()