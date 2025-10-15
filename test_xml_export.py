#!/usr/bin/env python3
"""
Test the new flexible /api/xml endpoint
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

def test_xml_export_with_full_scenario():
    """Test with a complete scenario including items"""
    print("\n1. Testing XML export with full scenario...")
    
    payload = {
        "project_name": "Test XML Export Project",
        "scenario": {
            "items": [
                {
                    "deliverable_code": "web_launch",
                    "deliverable": "Website Launch",
                    "included_task_groups": ["strategy", "design", "development"],
                    "hours": 200,
                    "price": 30000,
                    "complexity": "Advanced",
                    "tier": "T2_MediumVolume"
                },
                {
                    "deliverable_code": "deck_strategy",
                    "deliverable": "Strategy Deck",
                    "included_task_groups": ["research", "strategy", "design"],
                    "hours": 150,
                    "price": 25000,
                    "complexity": "Advanced",
                    "tier": "T2_MediumVolume"
                },
                {
                    "deliverable_code": "email_campaign",
                    "deliverable": "Email Campaign",
                    "included_task_groups": ["strategy", "creative", "production"],
                    "hours": 100,
                    "price": 15000,
                    "complexity": "Baseline",
                    "tier": "T2_MediumVolume"
                }
            ],
            "pricing_mode": "Flat_Blended",
            "rate_band": "Standard_US",
            "blended_rate": 195.0,
            "project_start": "2025-10-20T09:00:00"
        },
        "fixed_start_iso": "2025-10-20T09:00:00",
        "add_dependencies": True,
        "add_milestones": True,
        "add_custom_fields": True
    }
    
    response = requests.post(f"{BASE_URL}/api/xml", json=payload)
    
    if response.status_code == 200:
        print(f"✅ Success! XML file generated")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        print(f"   File Size: {len(response.content)} bytes")
        
        # Save the XML file
        filename = "test_full_scenario.xml"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"   Saved as: {filename}")
        
        # Check if it's valid XML
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.content)
            print(f"   XML Root Tag: {root.tag}")
            
            # Count tasks
            ns = {"": "http://schemas.microsoft.com/project"}
            tasks = root.findall(".//Task", ns)
            print(f"   Total Tasks: {len(tasks)}")
            
            # Check for WBS structure
            wbs_elements = root.findall(".//WBS", ns)
            if wbs_elements:
                print(f"   WBS Elements Found: {len(wbs_elements)}")
            
            # Check for dependencies
            predecessors = root.findall(".//PredecessorLink", ns)
            if predecessors:
                print(f"   Dependencies Found: {len(predecessors)}")
                
        except Exception as e:
            print(f"   ⚠️ XML parsing error: {e}")
    else:
        print(f"❌ Failed with status {response.status_code}")
        print(f"   Error: {response.text}")


def test_xml_export_with_deliverable_codes():
    """Test with just deliverable codes"""
    print("\n2. Testing XML export with deliverable codes only...")
    
    payload = {
        "project_name": "Test Project from Codes",
        "selected_deliverables": ["web_launch", "deck_strategy", "email_campaign", "social_paid"],
        "pricing_mode": "Per_Resource",
        "rate_band": "Premium_US",
        "fixed_start_iso": "2025-11-01T09:00:00",
        "add_dependencies": True,
        "add_milestones": True
    }
    
    response = requests.post(f"{BASE_URL}/api/xml", json=payload)
    
    if response.status_code == 200:
        print(f"✅ Success! XML file generated from deliverable codes")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        print(f"   File Size: {len(response.content)} bytes")
        
        # Save the XML file
        filename = "test_from_codes.xml"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"   Saved as: {filename}")
        
        # Basic validation
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.content)
            ns = {"": "http://schemas.microsoft.com/project"}
            tasks = root.findall(".//Task", ns)
            print(f"   Total Tasks Generated: {len(tasks)}")
        except Exception as e:
            print(f"   ⚠️ XML parsing error: {e}")
    else:
        print(f"❌ Failed with status {response.status_code}")
        print(f"   Error: {response.text}")


def test_xml_export_empty():
    """Test with empty/minimal payload"""
    print("\n3. Testing XML export with minimal payload...")
    
    payload = {
        "project_name": "Sample Project"
    }
    
    response = requests.post(f"{BASE_URL}/api/xml", json=payload)
    
    if response.status_code == 200:
        print(f"✅ Success! XML file generated with sample data")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        print(f"   File Size: {len(response.content)} bytes")
        
        # Save the XML file
        filename = "test_sample.xml"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"   Saved as: {filename}")
        
        # Basic validation
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.content)
            ns = {"": "http://schemas.microsoft.com/project"}
            
            # Check project name
            project_name = root.find(".//Name", ns)
            if project_name is not None:
                print(f"   Project Name: {project_name.text}")
            
            tasks = root.findall(".//Task", ns)
            print(f"   Sample Tasks Generated: {len(tasks)}")
        except Exception as e:
            print(f"   ⚠️ XML parsing error: {e}")
    else:
        print(f"❌ Failed with status {response.status_code}")
        print(f"   Error: {response.text}")


def test_xml_export_with_scenario_no_items():
    """Test with scenario but no items (should build them)"""
    print("\n4. Testing XML export with scenario but no items...")
    
    payload = {
        "project_name": "Test Scenario Without Items",
        "scenario": {
            "pricing_mode": "Flat_Blended",
            "rate_band": "Standard_US",
            "blended_rate": 200.0
        },
        "selected_deliverables": ["web_launch", "deck_strategy"],
        "fixed_start_iso": "2025-12-01T09:00:00"
    }
    
    response = requests.post(f"{BASE_URL}/api/xml", json=payload)
    
    if response.status_code == 200:
        print(f"✅ Success! XML file generated with auto-built items")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        print(f"   File Size: {len(response.content)} bytes")
        
        # Save the XML file
        filename = "test_auto_build.xml"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"   Saved as: {filename}")
        
        # Detailed validation
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.content)
            ns = {"": "http://schemas.microsoft.com/project"}
            
            # Check start date
            start_date = root.find(".//StartDate", ns)
            if start_date is not None:
                print(f"   Project Start Date: {start_date.text}")
            
            # Check tasks
            tasks = root.findall(".//Task", ns)
            print(f"   Total Tasks: {len(tasks)}")
            
            # Check for WBS hierarchy
            outline_levels = set()
            for task in tasks[:10]:  # Check first 10 tasks
                outline_level = task.find(".//OutlineLevel", ns)
                if outline_level is not None:
                    outline_levels.add(outline_level.text)
            
            if outline_levels:
                print(f"   WBS Outline Levels: {sorted(outline_levels)}")
            
            # Check resources
            resources = root.findall(".//Resource", ns)
            if resources:
                print(f"   Resources Found: {len(resources)}")
                
            # Check calendars
            calendars = root.findall(".//Calendar", ns)
            if calendars:
                print(f"   Calendars Found: {len(calendars)}")
                
        except Exception as e:
            print(f"   ⚠️ XML parsing error: {e}")
    else:
        print(f"❌ Failed with status {response.status_code}")
        print(f"   Error: {response.text}")


def main():
    print("=" * 60)
    print("Testing New Flexible /api/xml Endpoint")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/options")
        if response.status_code != 200:
            print("⚠️ Server may not be ready. Waiting...")
            import time
            time.sleep(2)
    except:
        print("❌ Cannot connect to server at http://localhost:5000")
        print("   Please ensure the FastAPI server is running")
        return
    
    # Run all tests
    test_xml_export_with_full_scenario()
    test_xml_export_with_deliverable_codes()
    test_xml_export_empty()
    test_xml_export_with_scenario_no_items()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()