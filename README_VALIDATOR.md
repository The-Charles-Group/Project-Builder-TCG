# Workfront XML Validator

A comprehensive validation tool for MSPDI XML files to ensure Workfront import compatibility.

## Overview

This validator performs 6 critical checks on Microsoft Project (MSPDI) XML files before importing them into Workfront, catching common issues that can cause import failures or data corruption.

## Features

### 1. Duplicate UID Detection
- Checks all Resource UIDs are unique
- Checks all Task UIDs are unique  
- Checks all Assignment UIDs are unique
- Reports exact duplicate values with positions

### 2. Reference Integrity
- Verifies every Assignment.ResourceUID references an existing Resource.UID
- Verifies every Assignment.TaskUID references an existing Task.UID
- Reports orphaned assignments with full details

### 3. Hierarchy Validation
- Validates OutlineLevel structure
- Checks for standard hierarchy levels (0, 1, 2, 3)
- Warns about very deep nesting (beyond level 6)
- Reports level distribution

### 4. WBS Code Format
- Validates WBS codes follow proper numbering (e.g., 1.2.3)
- Checks WBS depth matches OutlineLevel
- Reports malformed WBS codes

### 5. Data Type Validation
- Ensures StandardRate and OvertimeRate contain only numeric values (no "$" or "/h")
- Validates dates are in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
- Checks numeric fields (Cost, Work, Duration) are properly formatted
- Reports type violations with element names and values

### 6. Required Fields
- Checks critical elements exist (Name, UID, ID for Resources/Tasks)
- Verifies project metadata is present
- Reports missing required fields

## Usage

### Basic Usage

```bash
python validate_workfront_xml.py <xml_file>
```

### Example

```bash
python validate_workfront_xml.py project.xml
```

### Exit Codes

- `0`: Validation passed (file is Workfront-compatible)
- `1`: Validation failed (errors found)

## Output Examples

### Successful Validation

```
Validating: project.xml
======================================================================
✓ Checking duplicate UIDs...
  Resources: 20 unique UIDs
  Tasks: 857 unique UIDs
  Assignments: 0 unique UIDs

✓ Checking reference integrity...
  No assignments found (this may be expected)

✓ Checking hierarchy...
  OutlineLevel distribution: L0=1, L1=10, L2=82, L3=764
  Standard hierarchy structure present (Levels 0-3)
  Hierarchy validation passed

✓ Checking WBS codes...
  All WBS codes properly formatted

✓ Checking data types...
  All data types valid (rates are numeric, dates are ISO 8601)

✓ Checking required fields...
  All required fields present

======================================================================
✅ VALIDATION PASSED - XML is Workfront-compatible
```

### Failed Validation

```
Validating: bad_project.xml
======================================================================
✓ Checking duplicate UIDs...
  Resources: 156 unique UIDs
  Tasks: 892 unique UIDs
  Assignments: 1,024 unique UIDs

✓ Checking reference integrity...
  All 1,024 assignments reference valid resources and tasks

✓ Checking hierarchy...
  OutlineLevel distribution: L0=1, L1=12, L2=95, L3=784
  Standard hierarchy structure present (Levels 0-3)
  Hierarchy validation passed

✓ Checking WBS codes...
  All WBS codes properly formatted

❌ Checking data types...

✓ Checking required fields...
  All required fields present

======================================================================
❌ 2 ERRORS:
  - Resource UID=5 (Copywriter) StandardRate contains non-numeric value: "$195.00/h"
  - Resource UID=12 (Designer) OvertimeRate contains non-numeric value: "$292.50/hr"

❌ XML NOT ready for Workfront import!
```

## Common Issues Detected

### 1. Non-Numeric Rates
**Problem:** StandardRate or OvertimeRate fields contain currency symbols or units
```xml
<StandardRate>$195.00/h</StandardRate>  <!-- ❌ WRONG -->
<StandardRate>195.00</StandardRate>      <!-- ✅ CORRECT -->
```

### 2. Invalid Date Formats
**Problem:** Dates not in ISO 8601 format
```xml
<StartDate>11/10/2025</StartDate>              <!-- ❌ WRONG -->
<StartDate>2025-11-10T09:00:00</StartDate>     <!-- ✅ CORRECT -->
```

### 3. Duplicate UIDs
**Problem:** Multiple resources, tasks, or assignments share the same UID
```
❌ Duplicate Resource UID '5' found at positions: [3, 7]
```

### 4. Broken References
**Problem:** Assignments reference non-existent resources or tasks
```
❌ Assignment UID=42 references non-existent Resource UID=999
```

### 5. Malformed WBS Codes
**Problem:** WBS codes don't follow proper numbering
```xml
<WBS>1.A.3</WBS>     <!-- ❌ WRONG -->
<WBS>1.1.3</WBS>     <!-- ✅ CORRECT -->
```

## Requirements

- Python 3.6+
- Standard library only (no external dependencies)

## Technical Details

### XML Namespace Support
The validator automatically handles both:
- Namespaced XML: `<Project xmlns="http://schemas.microsoft.com/project">`
- Non-namespaced XML: `<Project>`

### Validation Categories
- **Errors**: Critical issues that will cause import failures
- **Warnings**: Non-critical issues that should be reviewed

## Integration

### In CI/CD Pipeline

```bash
#!/bin/bash
# Validate XML before upload to Workfront
python validate_workfront_xml.py exported_project.xml
if [ $? -eq 0 ]; then
    echo "✅ XML validated successfully - proceeding with upload"
    # ... upload to Workfront
else
    echo "❌ XML validation failed - fix errors before upload"
    exit 1
fi
```

### Batch Validation

```bash
# Validate all XML files in a directory
for xml_file in exports/*.xml; do
    echo "Validating: $xml_file"
    python validate_workfront_xml.py "$xml_file"
    echo "---"
done
```

## Troubleshooting

### XML Parse Errors
If you see `XML Parse Error`, the file may be:
- Corrupted
- Not valid XML
- Incompletely saved

Try opening the file in a text editor to verify it's well-formed XML.

### File Not Found
Ensure you provide the correct path to the XML file:
```bash
python validate_workfront_xml.py /full/path/to/project.xml
```

## Author

Created for validating MSPDI (Microsoft Project) XML files before Workfront import.

## License

Free to use and modify.
