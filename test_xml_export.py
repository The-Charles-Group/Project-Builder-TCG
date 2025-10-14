#!/usr/bin/env python3
"""
Test script for the fixed convert_excel_to_mspdi function
"""

import pandas as pd
import os
from convert_excel_to_mspdi import convert_excel_to_mspdi

def test_xml_conversion():
    """Test the XML conversion with sample data"""
    
    # Create test data with potential issues that were fixed
    test_data = {
        'Deliverable': ['Discovery', 'Discovery', 'Design', 'Design', 'Development', None],
        'Component': ['Research', 'Analysis', 'Wireframes', 'Mockups', 'Frontend', 'Testing'],
        'Task_Name': ['User Research', 'Market Analysis', 'Create Wireframes', 'Design Mockups', 'Build Frontend', 'QA Testing'],
        'Planned_Hours': [40, None, 80, 60, 120, None],  # Include None values to test null handling
        'Hours': [40, 30, None, 60, None, 40],  # Backup hours column
        'Role': ['UX Researcher', None, 'UX Designer', 'UI Designer', 'Frontend Developer', 'QA Engineer'],
        'Rate_USD': [150, 125, None, 140, 160, 120],  # Include None to test handling
        'Price_USD': [6000, None, 10000, 8400, 19200, 4800]  # Include None values
    }
    
    # Create DataFrame
    df = pd.DataFrame(test_data)
    
    # Save to Excel
    test_excel = 'test_data.xlsx'
    test_xml = 'test_output.xml'
    
    try:
        # Write test Excel file
        with pd.ExcelWriter(test_excel, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Scenario A', index=False)
        
        print("Test Excel file created successfully")
        
        # Test conversion with various settings
        stats = convert_excel_to_mspdi(
            input_xlsx=test_excel,
            output_xml=test_xml,
            sheet_name='Scenario A',
            start_date_mode='next_monday',
            project_name='Test Project',
            hours_per_day=8.0,
            pricing_mode='Flat_Blended',
            blended_rate=150.0,
            add_deliverable_milestones=True
        )
        
        print(f"✅ XML conversion successful!")
        print(f"   Statistics: {stats}")
        
        # Verify XML file was created
        if os.path.exists(test_xml):
            file_size = os.path.getsize(test_xml)
            print(f"✅ XML file created: {test_xml} ({file_size} bytes)")
            
            # Read first few lines to verify it's valid XML
            with open(test_xml, 'r') as f:
                first_lines = f.read(500)
                if '<?xml' in first_lines and '<Project' in first_lines:
                    print("✅ XML file appears to be valid Microsoft Project format")
                else:
                    print("⚠️  XML file may not be in correct format")
        else:
            print("❌ XML file was not created")
            
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up test files
        for file in [test_excel, test_xml]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    print(f"Cleaned up: {file}")
                except:
                    pass

if __name__ == "__main__":
    print("Testing XML export functionality with fixed convert_excel_to_mspdi...")
    print("=" * 60)
    test_xml_conversion()
    print("=" * 60)
    print("Test completed!")