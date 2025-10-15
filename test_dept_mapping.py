#!/usr/bin/env python3
"""
Direct test of department mapping for deliverables
"""

import sys
sys.path.insert(0, '.')

# Import the database class
from main import AgencyDB
import pandas as pd

def test_department_mapping():
    """Test that deliverables get proper department mappings"""
    
    print("Testing Department Mapping in Database...")
    print("=" * 50)
    
    # Initialize database
    db = AgencyDB()
    db.load()
    
    print("\n1. Checking database loaded...")
    if db.all_rows is None or db.all_rows.empty:
        print("   ✗ Database not loaded properly")
        return False
    print(f"   ✓ Database loaded with {len(db.all_rows)} rows")
    
    # Check for department columns
    print("\n2. Checking for department columns in all_rows...")
    dept_columns = []
    for col in ['Service_Department', 'Service Department', 'Department']:
        if col in db.all_rows.columns:
            dept_columns.append(col)
            print(f"   ✓ Found column: {col}")
    
    if not dept_columns:
        print("   ✗ No department columns found!")
        return False
    
    # Check department values for specific deliverables
    print("\n3. Checking department values for sample deliverables...")
    
    # Get unique deliverable codes
    if 'Deliverable_Code' in db.all_rows.columns:
        unique_codes = db.all_rows['Deliverable_Code'].dropna().unique()[:10]  # Check first 10
        
        dept_mappings = {}
        for code in unique_codes:
            rows = db.all_rows[db.all_rows['Deliverable_Code'] == code]
            if not rows.empty:
                # Try to get department
                for col in dept_columns:
                    dept_values = rows[col].dropna()
                    if not dept_values.empty:
                        # Get most common department
                        dept = dept_values.value_counts().idxmax()
                        if dept and str(dept) != 'nan':
                            dept_mappings[code] = dept
                            break
        
        print(f"   Found {len(dept_mappings)} deliverables with departments:")
        for code, dept in list(dept_mappings.items())[:5]:
            print(f"      {code}: {dept}")
    
    # Check if deliverables table has department info
    if db.deliverables is not None:
        print("\n4. Checking deliverables index table...")
        print(f"   Columns: {list(db.deliverables.columns)}")
        
        # Check for department columns
        has_dept = False
        for col in dept_columns:
            if col in db.deliverables.columns:
                has_dept = True
                print(f"   ✓ Found department column: {col}")
                
                # Show some values
                dept_values = db.deliverables[col].dropna().unique()[:5]
                print(f"   Sample departments: {list(dept_values)}")
        
        if not has_dept:
            print("   ℹ️ No department column in deliverables index (will need to look up from all_rows)")
    
    print("\n5. Testing department normalization...")
    
    # Test normalization function
    def normalize_department(dept_str):
        """Normalize department names to match frontend expectations"""
        if not dept_str or str(dept_str).strip() == 'nan':
            return 'Strategy'
        
        dept_lower = str(dept_str).strip().lower()
        
        # Map to standard departments
        if 'creative' in dept_lower:
            return 'Creative'
        elif 'paid' in dept_lower or 'media' in dept_lower:
            return 'Paid Media'
        elif 'tech' in dept_lower or 'dev' in dept_lower:
            return 'Technology'
        elif 'content' in dept_lower:
            return 'Content'
        elif 'integrated' in dept_lower or 'marketing management' in dept_lower:
            return 'Integrated Marketing Management'
        elif 'project' in dept_lower and 'management' in dept_lower:
            return 'Project Management'
        elif 'quality' in dept_lower or 'qa' in dept_lower:
            return 'Quality Assurance'
        elif 'account' in dept_lower:
            return 'Account Management'
        elif 'strategy' in dept_lower or 'strategic' in dept_lower:
            return 'Strategy'
        else:
            return ' '.join(word.capitalize() for word in str(dept_str).strip().split())
    
    test_names = [
        "Creative",
        "Paid Media",
        "Technology", 
        "Content Creation",
        "Strategic Planning",
        "Dev Team",
        "Media Planning"
    ]
    
    for name in test_names:
        normalized = normalize_department(name)
        print(f"   '{name}' -> '{normalized}'")
    
    print("\n✅ Department mapping test complete!")
    return True

if __name__ == "__main__":
    try:
        success = test_department_mapping()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()
        exit(1)