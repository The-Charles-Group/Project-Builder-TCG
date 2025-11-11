#!/usr/bin/env python3
"""
Test Script: Rate Formatting Fix Verification
Validates that StandardRate and OvertimeRate fields contain bare decimals (no $ or /h)
"""

import pandas as pd
import xml.etree.ElementTree as ET
import subprocess
import sys
import os
from datetime import datetime
from convert_excel_to_mspdi import convert_excel_to_mspdi


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_step(step_num: int, text: str):
    """Print a step message"""
    print(f"\nStep {step_num}: {text}")


def print_check(text: str, passed: bool = True):
    """Print a check result"""
    symbol = "✓" if passed else "✗"
    print(f"  {text} {symbol}")


def create_test_data():
    """
    Create minimal test scenario data
    Returns DataFrames for the test scenario
    """
    print_step(1, "Creating test scenario data...")
    
    # Create 3 resources with different roles and rates
    resources_data = {
        'Deliverable': ['Website Redesign'] * 3,
        'Component': ['Design'] * 2 + ['Strategy'],
        'Task_Name': [
            'Visual Design',
            'UX Design',
            'Market Research'
        ],
        'Role': [
            'Designer (Mid)',
            'Designer (Mid)',
            'Strategist (Mid)'
        ],
        'Hours': [40.0, 30.0, 20.0],
        'Rate': [150.00, 150.00, 175.00]
    }
    
    df = pd.DataFrame(resources_data)
    
    # Add a fourth task to meet the requirement of 4 tasks
    additional_task = pd.DataFrame({
        'Deliverable': ['Website Redesign'],
        'Component': ['Strategy'],
        'Task_Name': ['Competitive Analysis'],
        'Role': ['Strategist (Mid)'],
        'Hours': [15.0],
        'Rate': [175.00]
    })
    
    df = pd.concat([df, additional_task], ignore_index=True)
    
    print(f"  Created {len(df)} tasks")
    print(f"  Resources: Designer (Mid) @ $150/h, Strategist (Mid) @ $175/h")
    print(f"  1 Deliverable: Website Redesign")
    print(f"  2 Components: Design, Strategy")
    
    return df


def save_test_excel(df: pd.DataFrame, filename: str):
    """Save test data to Excel file"""
    # Create WBS structure with proper hierarchy
    wbs_data = []
    current_wbs = {"deliverable": 0, "component": {}, "task": 0}
    
    grouped = df.groupby(['Deliverable', 'Component'])
    
    for (deliverable, component), group in grouped:
        # Create deliverable row if new
        if deliverable not in [row.get('Task_Name') for row in wbs_data]:
            current_wbs["deliverable"] += 1
            wbs_data.append({
                'WBS_ID': f"{current_wbs['deliverable']}",
                'Task_Name': deliverable,
                'Deliverable': deliverable,
                'Component': '',
                'Role': '',
                'Hours': 0,
                'Rate': 0
            })
        
        # Create component row
        comp_key = f"{deliverable}_{component}"
        if comp_key not in current_wbs["component"]:
            current_wbs["component"][comp_key] = len([k for k in current_wbs["component"].keys() if k.startswith(deliverable)]) + 1
        
        wbs_data.append({
            'WBS_ID': f"{current_wbs['deliverable']}.{current_wbs['component'][comp_key]}",
            'Task_Name': component,
            'Deliverable': deliverable,
            'Component': component,
            'Role': '',
            'Hours': 0,
            'Rate': 0
        })
        
        # Add tasks under component
        task_num = 0
        for _, row in group.iterrows():
            task_num += 1
            wbs_data.append({
                'WBS_ID': f"{current_wbs['deliverable']}.{current_wbs['component'][comp_key]}.{task_num}",
                'Task_Name': row['Task_Name'],
                'Deliverable': deliverable,
                'Component': component,
                'Role': row['Role'],
                'Hours': row['Hours'],
                'Rate': row['Rate']
            })
    
    wbs_df = pd.DataFrame(wbs_data)
    
    # Save to Excel
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        wbs_df.to_excel(writer, sheet_name='Scenario A', index=False)
    
    print(f"  Saved test data to {filename}")


def generate_xml(excel_file: str, xml_file: str):
    """Generate XML using convert_excel_to_mspdi"""
    print_step(2, "Generating XML with convert_excel_to_mspdi...")
    
    try:
        result = convert_excel_to_mspdi(
            input_xlsx=excel_file,
            output_xml=xml_file,
            sheet_name='Scenario A',
            project_name='Rate Format Test Project',
            start_date_mode='next_monday',
            pricing_mode='Flat_Blended',
            rate_band='Standard_US',
            blended_rate=150.0
        )
        
        if 'error' in result:
            print(f"  ✗ Error generating XML: {result['error']}")
            return False
        
        print(f"  Generated {result.get('task_count', 0)} tasks")
        print(f"  Output: {xml_file}")
        print_check("XML generation completed")
        return True
        
    except Exception as e:
        print(f"  ✗ Exception during XML generation: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_validator(xml_file: str):
    """Run the comprehensive validator"""
    print_step(3, "Running comprehensive validator...")
    
    try:
        result = subprocess.run(
            ['python', 'validate_workfront_xml.py', xml_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check if validation passed (exit code 0 means passed)
        if result.returncode == 0:
            print_check("Validation passed - no errors found")
            return True, 0
        else:
            # Parse error count from output
            error_count = result.stdout.count('ERROR:') if result.stdout else 1
            print(f"  ✗ Validation failed with {error_count} errors")
            if result.stdout:
                print("\n  Validation output:")
                for line in result.stdout.split('\n')[:20]:  # Show first 20 lines
                    print(f"    {line}")
            return False, error_count
            
    except subprocess.TimeoutExpired:
        print("  ✗ Validator timed out")
        return False, -1
    except Exception as e:
        print(f"  ✗ Error running validator: {e}")
        return False, -1


def check_rate_formats(xml_file: str):
    """Parse XML and verify rate field formats"""
    print_step(4, "Checking rate field formats...")
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Handle namespace
        ns = {'ms': 'http://schemas.microsoft.com/project'}
        if root.tag == '{http://schemas.microsoft.com/project}Project':
            use_ns = True
        else:
            use_ns = False
            ns = {'ms': ''}
        
        resources = root.findall('.//ms:Resource' if use_ns else './/Resource', ns if use_ns else None)
        
        all_passed = True
        errors = []
        
        for resource in resources:
            name_elem = resource.find('ms:Name' if use_ns else 'Name', ns if use_ns else None)
            standard_rate_elem = resource.find('ms:StandardRate' if use_ns else 'StandardRate', ns if use_ns else None)
            overtime_rate_elem = resource.find('ms:OvertimeRate' if use_ns else 'OvertimeRate', ns if use_ns else None)
            
            if name_elem is None or not name_elem.text:
                continue
                
            name = name_elem.text
            
            # Check StandardRate
            if standard_rate_elem is not None and standard_rate_elem.text:
                standard_rate = standard_rate_elem.text
                
                # Check for invalid formats
                has_dollar = '$' in standard_rate
                has_per_hour = '/h' in standard_rate or '/hr' in standard_rate
                
                if has_dollar or has_per_hour:
                    print_check(f"Resource '{name}' StandardRate: {standard_rate}", passed=False)
                    errors.append(f"StandardRate contains invalid format: '{standard_rate}'")
                    all_passed = False
                else:
                    # Verify it's a valid number
                    try:
                        rate_value = float(standard_rate)
                        print_check(f"Resource '{name}' StandardRate: {rate_value:.2f}")
                    except ValueError:
                        print_check(f"Resource '{name}' StandardRate: {standard_rate}", passed=False)
                        errors.append(f"StandardRate is not a valid number: '{standard_rate}'")
                        all_passed = False
            
            # Check OvertimeRate
            if overtime_rate_elem is not None and overtime_rate_elem.text:
                overtime_rate = overtime_rate_elem.text
                
                # Check for invalid formats
                has_dollar = '$' in overtime_rate
                has_per_hour = '/h' in overtime_rate or '/hr' in overtime_rate
                
                if has_dollar or has_per_hour:
                    print_check(f"Resource '{name}' OvertimeRate: {overtime_rate}", passed=False)
                    errors.append(f"OvertimeRate contains invalid format: '{overtime_rate}'")
                    all_passed = False
                else:
                    # Verify it's a valid number
                    try:
                        rate_value = float(overtime_rate)
                        print_check(f"Resource '{name}' OvertimeRate: {rate_value:.2f}")
                    except ValueError:
                        print_check(f"Resource '{name}' OvertimeRate: {overtime_rate}", passed=False)
                        errors.append(f"OvertimeRate is not a valid number: '{overtime_rate}'")
                        all_passed = False
        
        return all_passed, errors
        
    except ET.ParseError as e:
        print(f"  ✗ XML Parse Error: {e}")
        return False, [f"XML Parse Error: {e}"]
    except Exception as e:
        print(f"  ✗ Error checking rates: {e}")
        return False, [f"Error: {e}"]


def main():
    """Main test execution"""
    print_header("Testing Rate Formatting Fix")
    
    # File paths
    test_excel = "test_rate_fix_data.xlsx"
    test_xml = "test_rate_fix_output.xml"
    
    # Track overall success
    all_tests_passed = True
    validation_errors = 0
    rate_errors = []
    
    try:
        # Step 1: Create test data
        df = create_test_data()
        save_test_excel(df, test_excel)
        print_check("Test data created")
        
        # Step 2: Generate XML
        if not generate_xml(test_excel, test_xml):
            print("\n❌ XML generation failed!")
            return 1
        
        # Step 3: Run validator
        validator_passed, validation_errors = run_validator(test_xml)
        if not validator_passed:
            all_tests_passed = False
        
        # Step 4: Check rate formats
        rates_passed, rate_errors = check_rate_formats(test_xml)
        if not rates_passed:
            all_tests_passed = False
        
        # Final report
        print_header("TEST RESULTS")
        
        if all_tests_passed:
            print("\n✅ ALL TESTS PASSED - Rate fix verified!")
            print(f"  - {validation_errors} validation errors")
            print(f"  - All rates are bare decimals (no $ or /h)")
            print(f"  - XML is Workfront-compatible")
            return 0
        else:
            print("\n❌ TESTS FAILED")
            if validation_errors > 0:
                print(f"  - {validation_errors} validation errors")
            if rate_errors:
                print(f"  - {len(rate_errors)} rate format errors:")
                for error in rate_errors[:5]:  # Show first 5
                    print(f"    • {error}")
            return 1
            
    except Exception as e:
        print(f"\n❌ TEST EXECUTION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup temporary files (optional - keep for debugging)
        if os.path.exists(test_excel):
            print(f"\nTest files kept for inspection:")
            print(f"  - {test_excel}")
        if os.path.exists(test_xml):
            print(f"  - {test_xml}")


if __name__ == "__main__":
    sys.exit(main())
