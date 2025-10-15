#!/usr/bin/env python3
"""
Quick GPT-5 RFP Analysis Test Suite
Tests core functionality with smaller payloads for faster execution
"""

import asyncio
import httpx
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Optional
from colorama import init, Fore, Style

init(autoreset=True)

# Configuration
BASE_URL = "http://localhost:5000"
TEST_TIMEOUT = 60  # Reduced timeout for quick tests

# ============================================================================
# TEST DATA GENERATION
# ============================================================================

def create_minimal_rfp() -> str:
    """Create minimal RFP to test auto-rescue logic"""
    return """
    Looking for marketing help.
    Need website and social media.
    """

def create_simple_rfp() -> str:
    """Create simple but valid RFP"""
    return """
    Marketing Agency RFP
    
    We need:
    1. Brand refresh and positioning
    2. New website development
    3. Social media campaign management
    4. Email marketing automation
    5. Content creation and strategy
    
    Timeline: 3 months
    Budget: $50,000
    """

def create_medium_rfp() -> str:
    """Create medium complexity RFP"""
    return """
    Digital Transformation RFP
    
    Project Overview:
    Complete digital transformation for our retail brand including:
    
    1. E-commerce Platform Development
       - Custom shopping cart
       - Payment integration
       - Inventory management
       - Mobile-responsive design
    
    2. Digital Marketing Strategy
       - SEO optimization
       - PPC campaigns
       - Social media advertising
       - Influencer partnerships
    
    3. Brand Identity Refresh
       - Logo redesign
       - Brand guidelines
       - Marketing collateral
       - Packaging design
    
    4. Content Production
       - Product photography
       - Video production
       - Blog content
       - Email templates
    
    5. Analytics Setup
       - Google Analytics 4
       - Conversion tracking
       - Custom dashboards
       - Monthly reporting
    
    Timeline: 6 months
    Budget: $200,000
    Target Launch: Q2 2025
    """

# ============================================================================
# API INTERACTION
# ============================================================================

async def analyze_rfp(client: httpx.AsyncClient, rfp_text: str, 
                     tier: str = "thinking", mode: str = "deep") -> Dict:
    """Submit RFP for analysis and wait for results"""
    
    # Start analysis job
    request_data = {
        "request_text": rfp_text,
        "mode": mode,
        "tier": tier,
        "strictness": "balanced"
    }
    
    try:
        print(f"   {Fore.CYAN}➤ Submitting RFP for analysis...")
        response = await client.post(
            f"{BASE_URL}/api/ai/analyze",
            json=request_data,
            timeout=30.0
        )
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to start job: {response.status_code}"}
        
        job_data = response.json()
        job_id = job_data.get("job_id")
        
        if not job_id:
            return {"success": False, "error": "No job ID returned"}
        
        print(f"   {Fore.GREEN}✓ Job started: {job_id}")
        
        # Poll for results
        start_time = time.time()
        last_stage = ""
        
        while (time.time() - start_time) < TEST_TIMEOUT:
            status_response = await client.get(f"{BASE_URL}/api/ai/status/{job_id}")
            
            if status_response.status_code != 200:
                return {"success": False, "error": f"Status check failed: {status_response.status_code}"}
            
            status_data = status_response.json()
            status = status_data.get("status")
            progress = status_data.get("progress", 0)
            stage = status_data.get("current_stage", "")
            
            # Show progress
            if stage != last_stage:
                print(f"   {Fore.YELLOW}⏳ Progress: {progress}% - {stage}")
                last_stage = stage
            
            if status == "completed":
                elapsed = time.time() - start_time
                result = status_data.get("result", {})
                print(f"   {Fore.GREEN}✓ Completed in {elapsed:.1f}s")
                return {
                    "success": True,
                    "job_id": job_id,
                    "elapsed": elapsed,
                    "result": result
                }
            elif status == "failed":
                error = status_data.get("error", "Unknown error")
                return {"success": False, "error": f"Job failed: {error}"}
            
            await asyncio.sleep(2)
        
        return {"success": False, "error": "Timeout waiting for results"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

async def test_basic_functionality():
    """Test 1: Basic GPT-5 functionality"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}TEST 1: BASIC FUNCTIONALITY")
    print(f"{Fore.CYAN}{'='*60}")
    
    results = []
    
    async with httpx.AsyncClient() as client:
        # Test with simple RFP
        print(f"\n{Fore.WHITE}Testing with simple RFP...")
        result = await analyze_rfp(client, create_simple_rfp())
        
        if result["success"]:
            deliverables = result["result"].get("deliverables_by_dept", {})
            total_delivs = sum(len(d) for d in deliverables.values())
            
            print(f"   {Fore.GREEN}✓ Analysis completed")
            print(f"   {Fore.WHITE}  Deliverables found: {total_delivs}")
            print(f"   {Fore.WHITE}  Departments: {list(deliverables.keys())}")
            
            results.append({
                "test": "Simple RFP",
                "status": "PASS",
                "deliverables": total_delivs,
                "time": result["elapsed"]
            })
        else:
            print(f"   {Fore.RED}✗ Analysis failed: {result['error']}")
            results.append({
                "test": "Simple RFP",
                "status": "FAIL",
                "error": result["error"]
            })
    
    return results

async def test_auto_rescue():
    """Test 2: Auto-rescue logic"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}TEST 2: AUTO-RESCUE LOGIC")
    print(f"{Fore.CYAN}{'='*60}")
    
    results = []
    
    async with httpx.AsyncClient() as client:
        # Test with minimal RFP (should trigger rescue)
        print(f"\n{Fore.WHITE}Testing with minimal RFP (should trigger rescue)...")
        result = await analyze_rfp(client, create_minimal_rfp())
        
        if result["success"]:
            deliverables = result["result"].get("deliverables_by_dept", {})
            total_delivs = sum(len(d) for d in deliverables.values())
            
            # Minimal RFP should still return some deliverables due to rescue
            if total_delivs > 5:
                print(f"   {Fore.GREEN}✓ Auto-rescue worked: {total_delivs} deliverables")
                results.append({
                    "test": "Minimal RFP Rescue",
                    "status": "PASS",
                    "deliverables": total_delivs
                })
            else:
                print(f"   {Fore.YELLOW}⚠ Low deliverable count: {total_delivs}")
                results.append({
                    "test": "Minimal RFP Rescue",
                    "status": "WARN",
                    "deliverables": total_delivs
                })
        else:
            print(f"   {Fore.RED}✗ Analysis failed: {result['error']}")
            results.append({
                "test": "Minimal RFP Rescue",
                "status": "FAIL",
                "error": result["error"]
            })
    
    return results

async def test_gpt5_features():
    """Test 3: GPT-5 specific features"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}TEST 3: GPT-5 INTELLIGENCE FEATURES")
    print(f"{Fore.CYAN}{'='*60}")
    
    results = []
    
    async with httpx.AsyncClient() as client:
        # Test with medium RFP to get detailed results
        print(f"\n{Fore.WHITE}Testing GPT-5 features with medium RFP...")
        result = await analyze_rfp(client, create_medium_rfp())
        
        if result["success"]:
            deliverables = result["result"].get("deliverables_by_dept", {})
            
            # Check for GPT-5 specific features
            has_confidence = False
            has_rationale = False
            has_multipliers = False
            
            for dept, items in deliverables.items():
                for item in items:
                    if "confidence" in item:
                        has_confidence = True
                    if "rationale" in item or "why" in item:
                        has_rationale = True
                    if "smart_multipliers" in item or "complexity" in item:
                        has_multipliers = True
            
            print(f"   {Fore.WHITE}Feature checks:")
            print(f"   {'✓' if has_confidence else '✗'} Confidence scores: {Fore.GREEN if has_confidence else Fore.RED}{'Found' if has_confidence else 'Not found'}")
            print(f"   {'✓' if has_rationale else '✗'} Rationales/Evidence: {Fore.GREEN if has_rationale else Fore.RED}{'Found' if has_rationale else 'Not found'}")
            print(f"   {'✓' if has_multipliers else '✗'} Smart multipliers: {Fore.GREEN if has_multipliers else Fore.RED}{'Found' if has_multipliers else 'Not found'}")
            
            results.append({
                "test": "GPT-5 Features",
                "status": "PASS" if (has_confidence or has_rationale) else "PARTIAL",
                "features": {
                    "confidence": has_confidence,
                    "rationale": has_rationale,
                    "multipliers": has_multipliers
                }
            })
        else:
            print(f"   {Fore.RED}✗ Analysis failed: {result['error']}")
            results.append({
                "test": "GPT-5 Features",
                "status": "FAIL",
                "error": result["error"]
            })
    
    return results

async def test_api_format():
    """Test 4: API response format"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}TEST 4: API RESPONSE FORMAT")
    print(f"{Fore.CYAN}{'='*60}")
    
    results = []
    
    async with httpx.AsyncClient() as client:
        # Test job creation response
        print(f"\n{Fore.WHITE}Testing API response format...")
        
        request_data = {
            "request_text": create_simple_rfp(),
            "mode": "deep",
            "tier": "thinking",
            "strictness": "balanced"
        }
        
        response = await client.post(f"{BASE_URL}/api/ai/analyze", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check required fields
            has_job_id = "job_id" in data
            has_status = "status" in data
            
            print(f"   {'✓' if has_job_id else '✗'} Job ID present: {Fore.GREEN if has_job_id else Fore.RED}{'Yes' if has_job_id else 'No'}")
            print(f"   {'✓' if has_status else '✗'} Status present: {Fore.GREEN if has_status else Fore.RED}{'Yes' if has_status else 'No'}")
            
            if has_job_id:
                job_id = data["job_id"]
                
                # Test status endpoint
                status_response = await client.get(f"{BASE_URL}/api/ai/status/{job_id}")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    
                    has_progress = "progress" in status_data
                    has_stage = "current_stage" in status_data
                    
                    print(f"   {'✓' if has_progress else '✗'} Progress field: {Fore.GREEN if has_progress else Fore.RED}{'Yes' if has_progress else 'No'}")
                    print(f"   {'✓' if has_stage else '✗'} Stage field: {Fore.GREEN if has_stage else Fore.RED}{'Yes' if has_stage else 'No'}")
                    
                    results.append({
                        "test": "API Format",
                        "status": "PASS",
                        "fields_present": {
                            "job_id": has_job_id,
                            "status": has_status,
                            "progress": has_progress,
                            "stage": has_stage
                        }
                    })
                else:
                    results.append({
                        "test": "API Format",
                        "status": "FAIL",
                        "error": f"Status endpoint failed: {status_response.status_code}"
                    })
            else:
                results.append({
                    "test": "API Format",
                    "status": "FAIL",
                    "error": "Missing job_id in response"
                })
        else:
            results.append({
                "test": "API Format",
                "status": "FAIL",
                "error": f"Failed to create job: {response.status_code}"
            })
        
        # Test error handling
        print(f"\n{Fore.WHITE}Testing error handling...")
        
        # Send invalid request (missing required field)
        bad_response = await client.post(f"{BASE_URL}/api/ai/analyze", json={})
        
        if bad_response.status_code in [400, 422]:
            print(f"   {Fore.GREEN}✓ Proper error handling for bad request: {bad_response.status_code}")
            results.append({
                "test": "Error Handling",
                "status": "PASS",
                "status_code": bad_response.status_code
            })
        else:
            print(f"   {Fore.RED}✗ Unexpected response for bad request: {bad_response.status_code}")
            results.append({
                "test": "Error Handling",
                "status": "FAIL",
                "status_code": bad_response.status_code
            })
    
    return results

# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_report(all_results: Dict[str, List]) -> str:
    """Generate comprehensive test report"""
    
    report = []
    report.append("="*80)
    report.append("GPT-5 RFP ANALYSIS TEST REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*80)
    report.append("")
    
    total_tests = 0
    passed = 0
    failed = 0
    warnings = 0
    
    for test_name, results in all_results.items():
        report.append(f"\n{test_name}")
        report.append("-" * len(test_name))
        
        for result in results:
            total_tests += 1
            status = result.get("status", "UNKNOWN")
            
            if status == "PASS":
                passed += 1
                symbol = "✓"
            elif status == "FAIL":
                failed += 1
                symbol = "✗"
            elif status == "WARN" or status == "PARTIAL":
                warnings += 1
                symbol = "⚠"
            else:
                symbol = "?"
            
            test_desc = result.get("test", "Unknown test")
            report.append(f"{symbol} {test_desc}: {status}")
            
            # Add details
            if "error" in result:
                report.append(f"  Error: {result['error']}")
            if "deliverables" in result:
                report.append(f"  Deliverables: {result['deliverables']}")
            if "time" in result:
                report.append(f"  Time: {result['time']:.1f}s")
            if "features" in result:
                for feature, present in result['features'].items():
                    report.append(f"  {feature}: {'Yes' if present else 'No'}")
            if "fields_present" in result:
                for field, present in result['fields_present'].items():
                    report.append(f"  {field}: {'Present' if present else 'Missing'}")
    
    # Summary
    report.append("")
    report.append("="*80)
    report.append("SUMMARY")
    report.append("="*80)
    report.append(f"Total Tests: {total_tests}")
    report.append(f"Passed: {passed} ({passed/total_tests*100:.1f}%)" if total_tests > 0 else "Passed: 0")
    report.append(f"Failed: {failed} ({failed/total_tests*100:.1f}%)" if total_tests > 0 else "Failed: 0")
    report.append(f"Warnings: {warnings} ({warnings/total_tests*100:.1f}%)" if total_tests > 0 else "Warnings: 0")
    
    # Key findings
    report.append("")
    report.append("KEY FINDINGS:")
    report.append("-" * 13)
    
    if failed == 0:
        report.append("✓ All critical tests passed successfully")
    else:
        report.append(f"✗ {failed} tests failed - investigation needed")
    
    if warnings > 0:
        report.append(f"⚠ {warnings} tests had warnings - review recommended")
    
    # Recommendations
    report.append("")
    report.append("RECOMMENDATIONS:")
    report.append("-" * 16)
    
    if failed > 0:
        report.append("1. Review failed tests and error logs")
        report.append("2. Check GPT-5 API connectivity and credentials")
        report.append("3. Verify database is loaded correctly")
    
    if warnings > 0:
        report.append("1. Review tests with warnings for partial failures")
        report.append("2. Consider adjusting timeout values for slow tests")
    
    if failed == 0 and warnings == 0:
        report.append("1. System appears to be working correctly")
        report.append("2. Consider running extended tests with larger RFPs")
        report.append("3. Monitor performance metrics in production")
    
    return "\n".join(report)

# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run all quick tests"""
    
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}GPT-5 RFP ANALYSIS QUICK TEST SUITE")
    print(f"{Fore.CYAN}Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.CYAN}{'='*80}")
    
    all_results = {}
    
    # Run tests
    try:
        all_results["BASIC FUNCTIONALITY"] = await test_basic_functionality()
        all_results["AUTO-RESCUE LOGIC"] = await test_auto_rescue()
        all_results["GPT-5 FEATURES"] = await test_gpt5_features()
        all_results["API FORMAT"] = await test_api_format()
    except Exception as e:
        print(f"\n{Fore.RED}Critical error during testing: {e}")
        all_results["ERROR"] = [{"test": "Test Suite", "status": "FAIL", "error": str(e)}]
    
    # Generate and save report
    report = generate_report(all_results)
    
    # Save report
    report_file = f"test_report_gpt5_quick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, "w") as f:
        f.write(report)
    
    # Display report
    print(f"\n{Fore.WHITE}{report}")
    
    print(f"\n{Fore.GREEN}Report saved to: {report_file}")

if __name__ == "__main__":
    asyncio.run(main())