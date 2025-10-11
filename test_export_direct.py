#!/usr/bin/env python3
"""
Direct test of export functionality without AI analysis
Tests the XML and Excel export with pre-selected deliverables
"""

import requests
import json
import os
from datetime import datetime

BASE_URL = "http://localhost:5000"
OUTPUT_DIR = "test_outputs"

def ensure_output_dir():
    """Ensure output directory exists"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_available_deliverables():
    """Get available deliverables from the system"""
    response = requests.get(f"{BASE_URL}/api/options")
    if response.status_code == 200:
        data = response.json()
        return data.get("deliverables", [])
    return []

def test_direct_export():
    """Test export functionality directly with known deliverables"""
    
    print("\n" + "="*60)
    print("   DIRECT EXPORT TEST - Testing XML and Excel Export")
    print("="*60 + "\n")
    
    ensure_output_dir()
    
    # Step 1: Get available deliverables
    print("[1] Getting available deliverables...")
    deliverables = get_available_deliverables()
    
    if not deliverables:
        print("❌ No deliverables available")
        return False
    
    print(f"✓ Found {len(deliverables)} deliverables")
    
    # Select specific deliverables (or use first 4 if specific ones not found)
    selected_codes = []
    target_keywords = ["paid media", "campaign", "brand", "content", "strategy", "creative"]
    
    for d in deliverables:
        name = d.get("Deliverable", "").lower()
        code = d.get("Deliverable_Code", "")
        
        if any(keyword in name for keyword in target_keywords):
            selected_codes.append(code)
            print(f"  • Selected: {d.get('Deliverable')} ({code})")
            
            if len(selected_codes) >= 4:
                break
    
    # Fallback: use first 4 if we didn't find specific ones
    if len(selected_codes) < 2:
        selected_codes = [d.get("Deliverable_Code") for d in deliverables[:4]]
        print("  Using first 4 deliverables as fallback")
    
    # Step 2: Build scenarios
    print("\n[2] Building scenarios...")
    
    build_payload = {
        "selected_deliverable_codes": selected_codes,
        "scenario_a": {
            "mode": "custom",
            "complexity": "Advanced",
            "tier": "T2_MediumVolume"
        },
        "pricing_mode": "Flat_Blended",
        "blended_rate": 250,
        "rate_band": "Standard_US"
    }
    
    response = requests.post(f"{BASE_URL}/api/build", json=build_payload)
    
    if response.status_code != 200:
        print(f"❌ Build failed: {response.status_code}")
        print(f"   {response.text[:200]}")
        return False
    
    scenario_a = response.json()
    print(f"✓ Scenario A built successfully")
    print(f"  Total hours: {scenario_a.get('total_hours', 0):.0f}")
    print(f"  Total price: ${scenario_a.get('total_price', 0):,.0f}")
    
    # Build Scenario B with different rate
    build_payload["blended_rate"] = 195
    response = requests.post(f"{BASE_URL}/api/build", json=build_payload)
    scenario_b = response.json() if response.status_code == 200 else scenario_a
    
    # Step 3: Test XML Export
    print("\n[3] Testing XML export...")
    
    xml_payload = {
        "scenario": scenario_a,
        "project_name": "Direct Test Project",
        "scenario_label": "Scenario A",
        "fixed_start_iso": "2025-07-01T09:00:00"
    }
    
    response = requests.post(f"{BASE_URL}/api/export_xml", json=xml_payload)
    
    if response.status_code == 200:
        xml_content = response.content
        xml_path = os.path.join(OUTPUT_DIR, "direct_test_export.xml")
        
        with open(xml_path, "wb") as f:
            f.write(xml_content)
        
        print(f"✓ XML export successful ({len(xml_content)} bytes)")
        print(f"  Saved to: {xml_path}")
        
        # Validate XML
        if xml_content.startswith(b'<?xml'):
            xml_str = xml_content.decode('utf-8', errors='ignore')
            task_count = xml_str.count('<Task>')
            print(f"  ✓ Valid XML with {task_count} tasks")
            
            # Check if it's not empty (more than just header)
            if task_count > 1:  # Should have at least project task and one actual task
                print("  ✓ XML contains actual task data")
            else:
                print("  ⚠️ XML appears to be empty (only project task)")
        else:
            print("  ❌ Invalid XML format")
    else:
        print(f"❌ XML export failed: {response.status_code}")
        print(f"   {response.text[:200]}")
    
    # Step 4: Test Excel Export
    print("\n[4] Testing Excel export...")
    
    excel_payload = {
        "scenario_a": scenario_a,
        "scenario_b": scenario_b,
        "project_name": "Direct Test Project",
        "sheet_name_a": "Scenario A",
        "sheet_name_b": "Scenario B"
    }
    
    response = requests.post(f"{BASE_URL}/api/export_workbook", json=excel_payload)
    
    if response.status_code == 200:
        excel_content = response.content
        excel_path = os.path.join(OUTPUT_DIR, "direct_test_workbook.xlsx")
        
        with open(excel_path, "wb") as f:
            f.write(excel_content)
        
        print(f"✓ Excel export successful ({len(excel_content)} bytes)")
        print(f"  Saved to: {excel_path}")
        
        # Validate Excel
        if excel_content.startswith(b'PK'):
            print("  ✓ Valid Excel file signature")
            
            # Try to read it back
            try:
                import pandas as pd
                test_df = pd.read_excel(excel_path, sheet_name=None)
                sheet_names = list(test_df.keys())
                print(f"  ✓ Contains {len(sheet_names)} sheets: {', '.join(sheet_names)}")
                
                # Check content
                for sheet_name in sheet_names[:2]:  # Check first 2 sheets
                    df = test_df[sheet_name]
                    if not df.empty:
                        print(f"    • {sheet_name}: {len(df)} rows, {len(df.columns)} columns")
            except Exception as e:
                print(f"  ⚠️ Could not validate Excel content: {e}")
        else:
            print("  ❌ Invalid Excel format")
    else:
        print(f"❌ Excel export failed: {response.status_code}")
        print(f"   {response.text[:200]}")
    
    # Step 5: Test Combined XML Export
    print("\n[5] Testing combined XML export (ZIP)...")
    
    zip_payload = {
        "scenario_a": scenario_a,
        "scenario_b": scenario_b,
        "project_name": "Direct Test Project",
        "project_start_iso": "2025-07-01T09:00:00"
    }
    
    response = requests.post(f"{BASE_URL}/api/export_workbook_xml", json=zip_payload)
    
    if response.status_code == 200:
        zip_content = response.content
        zip_path = os.path.join(OUTPUT_DIR, "direct_test_scenarios.zip")
        
        with open(zip_path, "wb") as f:
            f.write(zip_content)
        
        print(f"✓ Combined XML export successful ({len(zip_content)} bytes)")
        print(f"  Saved to: {zip_path}")
        
        # Validate ZIP
        if zip_content.startswith(b'PK'):
            print("  ✓ Valid ZIP archive")
            
            try:
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    file_list = zf.namelist()
                    print(f"  ✓ Contains {len(file_list)} files: {', '.join(file_list)}")
                    
                    # Check XML files in the ZIP
                    for file_name in file_list:
                        if file_name.endswith('.xml'):
                            with zf.open(file_name) as xml_file:
                                xml_data = xml_file.read()
                                if xml_data.startswith(b'<?xml'):
                                    task_count = xml_data.decode('utf-8', errors='ignore').count('<Task>')
                                    print(f"    • {file_name}: {task_count} tasks")
            except Exception as e:
                print(f"  ⚠️ Could not validate ZIP content: {e}")
    else:
        print(f"❌ Combined export failed: {response.status_code}")
        print(f"   {response.text[:200]}")
    
    print("\n" + "="*60)
    print("   DIRECT EXPORT TEST COMPLETE")
    print("="*60)
    
    return True


def main():
    """Main test execution"""
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/options")
        if response.status_code != 200:
            print("❌ Server not responding. Please ensure FastAPI server is running on port 5000.")
            return False
    except requests.ConnectionError:
        print("❌ Cannot connect to server at localhost:5000")
        print("   Please start the FastAPI server first:")
        print("   uvicorn main:app --host 0.0.0.0 --port 5000 --reload")
        return False
    
    # Run the direct export test
    return test_direct_export()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)