#!/usr/bin/env python
"""Fix indentation errors in all template files"""

import re

def fix_template_indentation(filename):
    """Fix indentation in template file"""
    print(f"Fixing {filename}...")
    
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        fixed_lines = []
        for i, line in enumerate(lines):
            # Check for misplaced timeline["duration_weeks"] lines
            if 'timeline["duration_weeks"] = timeline.get("total_duration_weeks"' in line:
                # This line should have the same indentation as the return statement after it
                if i + 1 < len(lines) and 'return timeline' in lines[i + 1]:
                    # Get indentation from return statement
                    next_line = lines[i + 1]
                    indent = len(next_line) - len(next_line.lstrip())
                    # Apply same indentation
                    fixed_line = ' ' * indent + line.lstrip()
                    fixed_lines.append(fixed_line)
                else:
                    # Default to 8 spaces (2 levels of indentation)
                    fixed_lines.append('        ' + line.lstrip())
            else:
                fixed_lines.append(line)
        
        with open(filename, 'w') as f:
            f.writelines(fixed_lines)
        
        print(f"✓ Fixed {filename}")
        return True
    except Exception as e:
        print(f"✗ Error fixing {filename}: {e}")
        return False

# Fix all template files
templates = [
    'beauty_template.py',
    'real_estate_template.py',
    'retail_template.py',
    'lifestyle_template.py'
]

for template in templates:
    fix_template_indentation(template)

print("\n✅ Indentation fixes complete!")