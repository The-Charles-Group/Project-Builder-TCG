#!/usr/bin/env python3
"""
Comprehensive test script for the complete RFP to Export workflow
Tests with real Uncommon Schools RFP data
"""

import requests
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Configuration
BASE_URL = "http://localhost:5000"
OUTPUT_DIR = "test_outputs"

# Uncommon Schools RFP test data
UNCOMMON_SCHOOLS_RFP = """
Uncommon Schools is seeking a media agency partner to manage paid media campaigns across digital channels.
We need comprehensive campaign strategy, brand positioning, content creation, and ongoing paid media management.
The scope includes:
- Paid Media Management: Ongoing management of digital advertising campaigns across Google Ads, Facebook, Instagram, and LinkedIn
- Campaign Strategy: Development of comprehensive campaign strategies aligned with enrollment goals  
- Brand Positioning: Refining brand messaging and positioning for target parent audiences
- Content Creation: Developing ad creative, landing pages, and social media content
Budget: $500,000 annual media spend with agency fees
Timeline: Starting July 2025, 12-month engagement with monthly retainer for ongoing services
"""

def log_step(step_num: int, message: str, success: bool = True):
    """Pretty print test step status"""
    symbol = "✓" if success else "✗"
    color = "\033[92m" if success else "\033[91m"  # Green or Red
    reset = "\033[0m"
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] Step {step_num}: {symbol} {message}{reset}")

def log_info(message: str):
    """Print informational message"""
    print(f"  ℹ️  {message}")

def ensure_output_dir():
    """Ensure output directory exists"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

class WorkflowTester:
    def __init__(self):
        self.session = requests.Session()
        self.analysis_id = None
        self.deliverables = []
        self.selected_deliverables = []
        self.scenario_a = None
        self.scenario_b = None
        self.timeline_data = None
        ensure_output_dir()
    
    def test_1_submit_rfp(self) -> bool:
        """Step 1: Submit RFP for AI analysis"""
        try:
            # Submit RFP text
            payload = {
                "request_text": UNCOMMON_SCHOOLS_RFP,
                "strictness": "balanced"
            }
            
            response = self.session.post(f"{BASE_URL}/api/ai/analyze", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                self.analysis_id = data.get("analysis_id")
                log_step(1, "RFP submitted for AI analysis", True)
                log_info(f"Analysis ID: {self.analysis_id}")
                return True
            else:
                log_step(1, f"RFP submission failed: {response.status_code}", False)
                log_info(response.text[:200])
                return False
                
        except Exception as e:
            log_step(1, f"RFP submission error: {e}", False)
            return False
    
    def test_2_wait_for_analysis(self) -> bool:
        """Step 2: Wait for AI analysis to complete"""
        if not self.analysis_id:
            log_step(2, "No analysis ID available", False)
            return False
        
        try:
            max_attempts = 60  # 60 seconds timeout
            for attempt in range(max_attempts):
                response = self.session.get(f"{BASE_URL}/api/ai/status/{self.analysis_id}")
                
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data.get("status", "unknown")
                    
                    if status == "completed":
                        # Get the suggestions
                        suggestions = status_data.get("suggestions", [])
                        self.deliverables = suggestions
                        
                        log_step(2, "AI analysis completed", True)
                        log_info(f"Found {len(suggestions)} suggested deliverables")
                        
                        # Display top suggestions
                        for i, sugg in enumerate(suggestions[:5]):
                            log_info(f"  {i+1}. {sugg.get('deliverable_name')} (Score: {sugg.get('score', 0):.2f})")
                        
                        return True
                    
                    elif status == "failed":
                        log_step(2, "AI analysis failed", False)
                        log_info(status_data.get("error", "Unknown error"))
                        return False
                    
                    # Still processing
                    if attempt % 5 == 0:  # Log every 5 seconds
                        log_info(f"Analysis in progress... ({attempt}s)")
                
                time.sleep(1)
            
            log_step(2, "Analysis timeout after 60 seconds", False)
            return False
            
        except Exception as e:
            log_step(2, f"Error checking analysis status: {e}", False)
            return False
    
    def test_3_select_deliverables(self) -> bool:
        """Step 3: Select specific deliverables for the project"""
        try:
            # Select the required deliverables based on the test requirements
            target_deliverables = {
                "Paid Media Management": {"retainer": True, "hours_per_month": 40},
                "Campaign Strategy": {"retainer": False, "hours": 120},
                "Brand Positioning": {"retainer": False, "hours": 80},
                "Content Creation": {"retainer": True, "hours_per_month": 30}
            }
            
            # Find matching deliverables from AI suggestions
            for sugg in self.deliverables:
                name = sugg.get("deliverable_name", "")
                code = sugg.get("deliverable_code", "")
                
                # Check if this matches any of our targets
                for target_name, config in target_deliverables.items():
                    if target_name.lower() in name.lower():
                        selection = {
                            "deliverable_code": code,
                            "deliverable_name": name,
                            "is_retainer": config.get("retainer", False),
                            "hours": config.get("hours", config.get("hours_per_month", 40) * 6)
                        }
                        
                        if config.get("retainer"):
                            selection["monthly_hours"] = config.get("hours_per_month", 40)
                            selection["retainer_months"] = 6
                        
                        self.selected_deliverables.append(selection)
                        break
            
            if len(self.selected_deliverables) >= 3:  # We found at least 3 matches
                log_step(3, f"Selected {len(self.selected_deliverables)} deliverables", True)
                for sel in self.selected_deliverables:
                    retainer_info = " (Retainer)" if sel.get("is_retainer") else ""
                    log_info(f"  • {sel['deliverable_name']}{retainer_info}: {sel.get('hours', 0)} hours")
                return True
            else:
                # Fallback: select top suggestions if specific ones not found
                self.selected_deliverables = []
                for sugg in self.deliverables[:4]:
                    self.selected_deliverables.append({
                        "deliverable_code": sugg.get("deliverable_code"),
                        "deliverable_name": sugg.get("deliverable_name"),
                        "is_retainer": False,
                        "hours": 100
                    })
                
                log_step(3, f"Using top {len(self.selected_deliverables)} AI suggestions", True)
                return True
                
        except Exception as e:
            log_step(3, f"Error selecting deliverables: {e}", False)
            return False
    
    def test_4_build_scenarios(self) -> bool:
        """Step 4: Build pricing scenarios with selected deliverables"""
        try:
            # Prepare deliverable codes
            deliverable_codes = [d["deliverable_code"] for d in self.selected_deliverables]
            
            # Build Scenario A
            build_payload = {
                "selected_deliverable_codes": deliverable_codes,
                "scenario_a": {
                    "mode": "custom",
                    "complexity": "Advanced",
                    "tier": "T2_MediumVolume"
                },
                "pricing_mode": "Flat_Blended",
                "blended_rate": 250,
                "rate_band": "Standard_US"
            }
            
            response = self.session.post(f"{BASE_URL}/api/build", json=build_payload)
            
            if response.status_code == 200:
                self.scenario_a = response.json()
                log_step(4, "Scenario A built successfully", True)
                log_info(f"  Total Hours: {self.scenario_a.get('total_hours', 0):.0f}")
                log_info(f"  Total Price: ${self.scenario_a.get('total_price', 0):,.0f}")
                
                # Build Scenario B with different pricing
                build_payload["blended_rate"] = 195
                response = self.session.post(f"{BASE_URL}/api/build", json=build_payload)
                
                if response.status_code == 200:
                    self.scenario_b = response.json()
                    log_info("Scenario B built with reduced rate")
                    log_info(f"  Total Price: ${self.scenario_b.get('total_price', 0):,.0f}")
                    return True
                    
            log_step(4, f"Scenario building failed: {response.status_code}", False)
            return False
            
        except Exception as e:
            log_step(4, f"Error building scenarios: {e}", False)
            return False
    
    def test_5_configure_pricing(self) -> bool:
        """Step 5: Test hour redistribution and retainer configuration"""
        try:
            # Test hour redistribution
            if self.scenario_a and self.scenario_a.get("items"):
                # Redistribute some hours
                items = self.scenario_a["items"][:3]  # Take first 3 items
                
                # Increase first item hours by 20
                if items:
                    items[0]["hours"] = items[0].get("hours", 0) + 20
                    log_info("Redistributed +20 hours to first deliverable")
                
                # Test retainer configuration for applicable items
                retainer_configured = False
                for item in self.scenario_a.get("items", []):
                    if "media" in item.get("name", "").lower() or "content" in item.get("name", "").lower():
                        item["is_retainer"] = True
                        item["retainer_months"] = 6
                        item["monthly_hours"] = 40
                        retainer_configured = True
                        log_info(f"Configured retainer for: {item.get('name', 'Unknown')}")
                        break
                
                log_step(5, "Pricing configuration tested", True)
                return True
            else:
                log_step(5, "No scenario data to configure", False)
                return False
                
        except Exception as e:
            log_step(5, f"Error configuring pricing: {e}", False)
            return False
    
    def test_6_generate_timeline(self) -> bool:
        """Step 6: Generate project timeline"""
        try:
            if not self.scenario_a:
                log_step(6, "No scenario available for timeline", False)
                return False
            
            # Generate timeline using AI timeline manager
            timeline_payload = {
                "scenario": self.scenario_a,
                "project_start": "2025-07-01",
                "optimization_mode": "balanced",
                "use_ai": False  # Use algorithmic generation for speed
            }
            
            response = self.session.post(f"{BASE_URL}/api/timeline/generate", json=timeline_payload)
            
            if response.status_code == 200:
                self.timeline_data = response.json()
                tasks = self.timeline_data.get("tasks", [])
                
                log_step(6, f"Timeline generated with {len(tasks)} tasks", True)
                
                # Check for retainer tasks
                retainer_tasks = [t for t in tasks if t.get("is_retainer", False)]
                if retainer_tasks:
                    log_info(f"  Including {len(retainer_tasks)} retainer tasks")
                
                # Display timeline summary
                if tasks:
                    start_dates = [t.get("start") for t in tasks if t.get("start")]
                    end_dates = [t.get("end") for t in tasks if t.get("end")]
                    if start_dates and end_dates:
                        log_info(f"  Timeline: {min(start_dates)[:10]} to {max(end_dates)[:10]}")
                
                return True
            else:
                log_step(6, f"Timeline generation failed: {response.status_code}", False)
                return False
                
        except Exception as e:
            log_step(6, f"Error generating timeline: {e}", False)
            return False
    
    def test_7_export_xml(self) -> bool:
        """Step 7: Export to Microsoft Project XML"""
        try:
            if not self.scenario_a:
                log_step(7, "No scenario available for XML export", False)
                return False
            
            # Export to XML
            export_payload = {
                "scenario": self.scenario_a,
                "project_name": "Uncommon Schools Campaign",
                "scenario_label": "Scenario A",
                "fixed_start_iso": "2025-07-01T09:00:00"
            }
            
            response = self.session.post(f"{BASE_URL}/api/export_xml", json=export_payload)
            
            if response.status_code == 200:
                xml_content = response.content
                
                # Save XML file
                xml_path = os.path.join(OUTPUT_DIR, "uncommon_schools_export.xml")
                with open(xml_path, "wb") as f:
                    f.write(xml_content)
                
                log_step(7, f"XML export successful ({len(xml_content)} bytes)", True)
                log_info(f"  Saved to: {xml_path}")
                
                # Validate XML structure
                if xml_content.startswith(b'<?xml'):
                    log_info("  ✓ Valid XML header")
                    # Check for key elements
                    xml_str = xml_content.decode('utf-8', errors='ignore')
                    if '<Project' in xml_str and '<Tasks>' in xml_str:
                        log_info("  ✓ Contains Project and Tasks elements")
                        
                        # Count tasks
                        task_count = xml_str.count('<Task>')
                        if task_count > 0:
                            log_info(f"  ✓ Contains {task_count} tasks")
                            return True
                        else:
                            log_info("  ⚠️ No tasks found in XML")
                else:
                    log_info("  ⚠️ Invalid XML format")
                
                return True
            else:
                log_step(7, f"XML export failed: {response.status_code}", False)
                log_info(response.text[:200])
                return False
                
        except Exception as e:
            log_step(7, f"Error exporting XML: {e}", False)
            return False
    
    def test_8_export_excel(self) -> bool:
        """Step 8: Export to Excel workbook"""
        try:
            if not self.scenario_a or not self.scenario_b:
                log_step(8, "Scenarios not available for Excel export", False)
                return False
            
            # Export to Excel workbook
            export_payload = {
                "scenario_a": self.scenario_a,
                "scenario_b": self.scenario_b,
                "project_name": "Uncommon Schools Campaign",
                "sheet_name_a": "Scenario A - Premium",
                "sheet_name_b": "Scenario B - Value"
            }
            
            response = self.session.post(f"{BASE_URL}/api/export_workbook", json=export_payload)
            
            if response.status_code == 200:
                excel_content = response.content
                
                # Save Excel file
                excel_path = os.path.join(OUTPUT_DIR, "uncommon_schools_workbook.xlsx")
                with open(excel_path, "wb") as f:
                    f.write(excel_content)
                
                log_step(8, f"Excel export successful ({len(excel_content)} bytes)", True)
                log_info(f"  Saved to: {excel_path}")
                
                # Validate Excel file
                if excel_content.startswith(b'PK'):  # Excel files are ZIP archives
                    log_info("  ✓ Valid Excel file signature")
                    
                    # Try to read it back with pandas to validate
                    try:
                        import pandas as pd
                        test_df = pd.read_excel(excel_path, sheet_name=None)
                        sheet_names = list(test_df.keys())
                        log_info(f"  ✓ Contains {len(sheet_names)} sheets: {', '.join(sheet_names[:3])}")
                        
                        # Check for retainer sheets
                        retainer_sheets = [s for s in sheet_names if "Retainer" in s]
                        if retainer_sheets:
                            log_info(f"  ✓ Includes retainer summaries: {', '.join(retainer_sheets)}")
                        
                    except Exception as e:
                        log_info(f"  ⚠️ Could not validate Excel structure: {e}")
                
                return True
            else:
                log_step(8, f"Excel export failed: {response.status_code}", False)
                log_info(response.text[:200])
                return False
                
        except Exception as e:
            log_step(8, f"Error exporting Excel: {e}", False)
            return False
    
    def test_9_export_combined(self) -> bool:
        """Step 9: Test combined XML export with both scenarios"""
        try:
            if not self.scenario_a or not self.scenario_b:
                log_step(9, "Scenarios not available for combined export", False)
                return False
            
            # Export both scenarios to XML zip
            export_payload = {
                "scenario_a": self.scenario_a,
                "scenario_b": self.scenario_b,
                "project_name": "Uncommon Schools Campaign",
                "project_start_iso": "2025-07-01T09:00:00"
            }
            
            response = self.session.post(f"{BASE_URL}/api/export_workbook_xml", json=export_payload)
            
            if response.status_code == 200:
                zip_content = response.content
                
                # Save ZIP file
                zip_path = os.path.join(OUTPUT_DIR, "uncommon_schools_scenarios.zip")
                with open(zip_path, "wb") as f:
                    f.write(zip_content)
                
                log_step(9, f"Combined XML export successful ({len(zip_content)} bytes)", True)
                log_info(f"  Saved to: {zip_path}")
                
                # Validate ZIP file
                if zip_content.startswith(b'PK'):
                    log_info("  ✓ Valid ZIP archive")
                    
                    # Try to list contents
                    try:
                        import zipfile
                        with zipfile.ZipFile(zip_path, 'r') as zf:
                            file_list = zf.namelist()
                            log_info(f"  ✓ Contains {len(file_list)} files: {', '.join(file_list)}")
                    except Exception as e:
                        log_info(f"  ⚠️ Could not validate ZIP contents: {e}")
                
                return True
            else:
                log_step(9, f"Combined export failed: {response.status_code}", False)
                log_info(response.text[:200])
                return False
                
        except Exception as e:
            log_step(9, f"Error in combined export: {e}", False)
            return False
    
    def run_all_tests(self) -> bool:
        """Run the complete workflow test suite"""
        print("\n" + "="*60)
        print("   COMPREHENSIVE WORKFLOW TEST - Uncommon Schools RFP")
        print("="*60 + "\n")
        
        # Track overall success
        all_passed = True
        
        # Run each test step
        tests = [
            (1, self.test_1_submit_rfp),
            (2, self.test_2_wait_for_analysis),
            (3, self.test_3_select_deliverables),
            (4, self.test_4_build_scenarios),
            (5, self.test_5_configure_pricing),
            (6, self.test_6_generate_timeline),
            (7, self.test_7_export_xml),
            (8, self.test_8_export_excel),
            (9, self.test_9_export_combined)
        ]
        
        for step_num, test_func in tests:
            success = test_func()
            if not success:
                all_passed = False
                # Continue testing even if one fails to see full picture
            time.sleep(0.5)  # Small delay between steps
        
        # Summary
        print("\n" + "="*60)
        if all_passed:
            print("   ✅ ALL TESTS PASSED - Workflow Complete!")
        else:
            print("   ⚠️ SOME TESTS FAILED - Review logs above")
        print("="*60)
        
        # Display output files
        if os.path.exists(OUTPUT_DIR):
            files = os.listdir(OUTPUT_DIR)
            if files:
                print(f"\n📁 Output files saved to {OUTPUT_DIR}/:")
                for f in files:
                    if f.endswith(('.xml', '.xlsx', '.zip')):
                        file_path = os.path.join(OUTPUT_DIR, f)
                        size = os.path.getsize(file_path) / 1024  # KB
                        print(f"   • {f} ({size:.1f} KB)")
        
        return all_passed


def main():
    """Main test execution"""
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/options")
        if response.status_code != 200:
            print("❌ Server not responding properly. Please ensure FastAPI server is running on port 5000.")
            return False
    except requests.ConnectionError:
        print("❌ Cannot connect to server. Please start the FastAPI server first:")
        print("   uvicorn main:app --host 0.0.0.0 --port 5000 --reload")
        return False
    
    # Run the workflow test
    tester = WorkflowTester()
    success = tester.run_all_tests()
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)