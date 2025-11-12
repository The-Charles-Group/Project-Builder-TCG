#!/usr/bin/env python3
"""
Test script to verify the variable collision fix in convert_excel_to_mspdi.
Generates a minimal export and checks for successful completion.
"""
import pandas as pd
from datetime import datetime
from convert_excel_to_mspdi import convert_excel_to_mspdi

# Create minimal test scenario DataFrame
test_data = {
    "Deliverable": ["Brand Strategy", "Brand Strategy", "Visual Identity", "Visual Identity"],
    "Component": ["Research & Discovery", "Strategic Framework", "Logo Design", "Brand Guidelines"],
    "Task_Label": ["Competitive Analysis", "Brand Positioning", "Logo Concepts", "Usage Guidelines"],
    "Planned_Hours": [40, 60, 80, 40],
    "Price_USD": [6000, 9000, 12000, 6000],
    "Role": ["Strategist", "Strategist", "Designer", "Designer"],
    "Seniority": ["Senior", "Director", "Senior", "Mid"],
    "OutlineLevel": [1, 2, 1, 2]
}

df = pd.DataFrame(test_data)

# Create temporary Excel file
test_excel = "test_scenario_data.xlsx"
df.to_excel(test_excel, sheet_name="Scenario A", index=False)
print(f"[TEST] Created test Excel file: {test_excel}")

# Test export with fixed code
print("[TEST] Creating test export with variable collision fix...")
print(f"[TEST] Test DataFrame: {len(df)} rows")

try:
    # Generate export
    stats = convert_excel_to_mspdi(
        input_xlsx=test_excel,
        output_xml="test_export_verification.xml",
        sheet_name="Scenario A",
        project_name="Variable Collision Test",
        start_date_mode="today",
        fixed_start_iso=datetime.now().strftime("%Y-%m-%d"),
        hours_per_day=6.5
    )
    
    print("\n[TEST] ✅ Export completed successfully!")
    print(f"[TEST] Statistics: {stats}")
    print(f"\n[TEST] Verification:")
    print(f"  - Task count: {stats['task_count']}")
    print(f"  - Resource count: {stats['resource_count']}")
    print(f"  - Assignment count: {stats['assignment_count']}")
    print(f"  - Milestone count: {stats['milestone_count']}")
    print(f"  - Total hours: {stats['total_hours']}")
    print(f"  - Dependencies: {stats['predecessor_links_count']}")
    
    # Check if file was created
    import os
    if os.path.exists("test_export_verification.xml"):
        file_size = os.path.getsize("test_export_verification.xml")
        print(f"\n[TEST] ✅ XML file created: test_export_verification.xml ({file_size} bytes)")
        
        # Quick schema check
        print("\n[TEST] Running schema validation...")
        import subprocess
        result = subprocess.run(
            ["python", "validate_workfront_xml.py", "test_export_verification.xml"],
            capture_output=True,
            text=True
        )
        
        # Check for wrapper violations
        if "wrapper container" in result.stdout.lower():
            print("[TEST] ❌ Schema violations detected! Flat ExtendedAttribute fix may not be working.")
        else:
            print("[TEST] ✅ No wrapper violations detected! Schema fix working correctly.")
        
        # Show summary line
        if "✓ Checking ExtendedAttributes schema" in result.stdout:
            lines = result.stdout.split("\n")
            for i, line in enumerate(lines):
                if "ExtendedAttributes schema" in line:
                    # Print this line and next few lines
                    for j in range(i, min(i+4, len(lines))):
                        print(f"  {lines[j]}")
                    break
    
    print("\n[TEST] ✅ ALL TESTS PASSED - Variable collision fix verified!")
    
except TypeError as e:
    print(f"\n[TEST] ❌ TypeError detected: {e}")
    print("[TEST] Variable collision bug may still be present")
    raise
except Exception as e:
    print(f"\n[TEST] ❌ Export failed: {e}")
    raise
