#!/usr/bin/env python3
"""
Workfront XML Validator
Validates MSPDI XML files for Workfront import compatibility
"""

import xml.etree.ElementTree as ET
import sys
import re
from typing import List, Dict, Set, Tuple
from collections import defaultdict
from datetime import datetime


class WorkfrontXMLValidator:
    def __init__(self, xml_file: str):
        self.xml_file = xml_file
        self.tree = None
        self.root = None
        self.ns = {'ms': 'http://schemas.microsoft.com/project'}
        self.errors = []
        self.warnings = []
    
    def check_xml_declaration(self) -> bool:
        """Check XML declaration matches Microsoft Project/Workfront format"""
        try:
            with open(self.xml_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
            
            # Expected format: <?xml version="1.0" encoding="UTF-8"?>
            expected = '<?xml version="1.0" encoding="UTF-8"?>'
            
            if first_line != expected:
                # Check for common issues
                if "version='1.0'" in first_line or "encoding='utf-8'" in first_line:
                    self.errors.append(
                        f"XML declaration uses single quotes instead of double quotes. "
                        f"Expected: {expected}, Found: {first_line}"
                    )
                elif 'encoding="utf-8"' in first_line:
                    self.errors.append(
                        f"XML declaration uses lowercase 'utf-8'. "
                        f"Workfront requires uppercase 'UTF-8'. Found: {first_line}"
                    )
                elif not first_line.startswith('<?xml'):
                    self.warnings.append(
                        f"XML declaration not found or malformed. Expected: {expected}"
                    )
                else:
                    self.errors.append(
                        f"XML declaration format incorrect. "
                        f"Expected: {expected}, Found: {first_line}"
                    )
                return False
            
            print(f"  Declaration format correct: {expected}")
            return True
        except Exception as e:
            self.errors.append(f"Error reading XML declaration: {e}")
            return False
        
    def load_xml(self) -> bool:
        """Load and parse XML file"""
        try:
            self.tree = ET.parse(self.xml_file)
            self.root = self.tree.getroot()
            
            if self.root.tag == '{http://schemas.microsoft.com/project}Project':
                self.ns = {'ms': 'http://schemas.microsoft.com/project'}
            elif self.root.tag == 'Project':
                self.ns = {'ms': ''}
            else:
                self.errors.append(f"Unexpected root element: {self.root.tag}")
                return False
                
            return True
        except ET.ParseError as e:
            self.errors.append(f"XML Parse Error: {e}")
            return False
        except FileNotFoundError:
            self.errors.append(f"File not found: {self.xml_file}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected error loading XML: {e}")
            return False
    
    def _find_all(self, path: str):
        """Helper to find elements with or without namespace"""
        if self.ns['ms']:
            return self.root.findall(path, self.ns)
        else:
            return self.root.findall(path.replace('ms:', ''))
    
    def _find(self, element, path: str):
        """Helper to find child elements with or without namespace"""
        if self.ns['ms']:
            return element.find(path, self.ns)
        else:
            return element.find(path.replace('ms:', ''))
    
    def _findtext(self, element, path: str, default=''):
        """Helper to find text with or without namespace"""
        if self.ns['ms']:
            return element.findtext(path, default, self.ns)
        else:
            return element.findtext(path.replace('ms:', ''), default)
    
    def check_duplicate_uids(self):
        """Check for duplicate Resource, Task, and Assignment UIDs"""
        print("✓ Checking duplicate UIDs...")
        
        resource_uids = defaultdict(list)
        task_uids = defaultdict(list)
        assignment_uids = defaultdict(list)
        
        for idx, resource in enumerate(self._find_all('.//ms:Resource' if self.ns['ms'] else './/Resource')):
            uid = self._findtext(resource, 'ms:UID' if self.ns['ms'] else 'UID')
            if uid:
                resource_uids[uid].append(idx + 1)
        
        for idx, task in enumerate(self._find_all('.//ms:Task' if self.ns['ms'] else './/Task')):
            uid = self._findtext(task, 'ms:UID' if self.ns['ms'] else 'UID')
            if uid:
                task_uids[uid].append(idx + 1)
        
        for idx, assignment in enumerate(self._find_all('.//ms:Assignment' if self.ns['ms'] else './/Assignment')):
            uid = self._findtext(assignment, 'ms:UID' if self.ns['ms'] else 'UID')
            if uid:
                assignment_uids[uid].append(idx + 1)
        
        duplicates_found = False
        
        for uid, occurrences in resource_uids.items():
            if len(occurrences) > 1:
                self.errors.append(
                    f"Duplicate Resource UID '{uid}' found at positions: {occurrences}"
                )
                duplicates_found = True
        
        for uid, occurrences in task_uids.items():
            if len(occurrences) > 1:
                self.errors.append(
                    f"Duplicate Task UID '{uid}' found at positions: {occurrences}"
                )
                duplicates_found = True
        
        for uid, occurrences in assignment_uids.items():
            if len(occurrences) > 1:
                self.errors.append(
                    f"Duplicate Assignment UID '{uid}' found at positions: {occurrences}"
                )
                duplicates_found = True
        
        if not duplicates_found:
            resource_count = len([uid for uid in resource_uids.keys() if uid])
            task_count = len([uid for uid in task_uids.keys() if uid])
            assignment_count = len([uid for uid in assignment_uids.keys() if uid])
            
            print(f"  Resources: {resource_count} unique UIDs")
            print(f"  Tasks: {task_count} unique UIDs")
            print(f"  Assignments: {assignment_count} unique UIDs")
    
    def check_reference_integrity(self):
        """Verify all assignments reference valid resources and tasks"""
        print("\n✓ Checking reference integrity...")
        
        resource_uids = set()
        for resource in self._find_all('.//ms:Resource' if self.ns['ms'] else './/Resource'):
            uid = self._findtext(resource, 'ms:UID' if self.ns['ms'] else 'UID')
            if uid:
                resource_uids.add(uid)
        
        task_uids = set()
        for task in self._find_all('.//ms:Task' if self.ns['ms'] else './/Task'):
            uid = self._findtext(task, 'ms:UID' if self.ns['ms'] else 'UID')
            if uid:
                task_uids.add(uid)
        
        orphaned_assignments = []
        assignment_count = 0
        
        for idx, assignment in enumerate(self._find_all('.//ms:Assignment' if self.ns['ms'] else './/Assignment')):
            assignment_count += 1
            assignment_uid = self._findtext(assignment, 'ms:UID' if self.ns['ms'] else 'UID')
            resource_uid = self._findtext(assignment, 'ms:ResourceUID' if self.ns['ms'] else 'ResourceUID')
            task_uid = self._findtext(assignment, 'ms:TaskUID' if self.ns['ms'] else 'TaskUID')
            
            if resource_uid and resource_uid not in resource_uids:
                self.errors.append(
                    f"Assignment UID={assignment_uid} references non-existent Resource UID={resource_uid}"
                )
                orphaned_assignments.append(assignment_uid)
            
            if task_uid and task_uid not in task_uids:
                self.errors.append(
                    f"Assignment UID={assignment_uid} references non-existent Task UID={task_uid}"
                )
                orphaned_assignments.append(assignment_uid)
        
        if not orphaned_assignments:
            if assignment_count > 0:
                print(f"  All {assignment_count} assignments reference valid resources and tasks")
            else:
                print(f"  No assignments found (this may be expected)")
    
    def check_hierarchy(self):
        """Validate OutlineLevel hierarchy"""
        print("\n✓ Checking hierarchy...")
        
        tasks = []
        for task in self._find_all('.//ms:Task' if self.ns['ms'] else './/Task'):
            uid = self._findtext(task, 'ms:UID' if self.ns['ms'] else 'UID')
            name = self._findtext(task, 'ms:Name' if self.ns['ms'] else 'Name')
            outline_level = self._findtext(task, 'ms:OutlineLevel' if self.ns['ms'] else 'OutlineLevel')
            wbs = self._findtext(task, 'ms:WBS' if self.ns['ms'] else 'WBS')
            
            if outline_level:
                try:
                    outline_level = int(outline_level)
                    tasks.append({
                        'uid': uid,
                        'name': name,
                        'outline_level': outline_level,
                        'wbs': wbs
                    })
                except ValueError:
                    self.errors.append(
                        f"Task UID={uid} has invalid OutlineLevel: '{outline_level}'"
                    )
        
        tasks.sort(key=lambda x: x['uid'])
        
        if tasks:
            level_counts = defaultdict(int)
            deep_tasks = []
            
            for task in tasks:
                level = task['outline_level']
                level_counts[level] += 1
                
                # Only warn about very deep nesting (beyond level 6)
                if level > 6:
                    deep_tasks.append(task)
            
            # Report distribution
            level_summary = ", ".join([f"L{level}={count}" for level, count in sorted(level_counts.items())])
            print(f"  OutlineLevel distribution: {level_summary}")
            
            # Warn about excessive nesting
            if deep_tasks:
                if len(deep_tasks) <= 5:
                    for task in deep_tasks:
                        self.warnings.append(
                            f"Task UID={task['uid']} ('{task['name']}') has very deep nesting: OutlineLevel={task['outline_level']}"
                        )
                else:
                    self.warnings.append(
                        f"{len(deep_tasks)} tasks have very deep nesting (OutlineLevel > 6)"
                    )
            
            # Check for typical structure (0, 1, 2, 3 levels present)
            expected_levels = {0, 1, 2, 3}
            actual_levels = set(level_counts.keys())
            
            if expected_levels.issubset(actual_levels):
                print(f"  Standard hierarchy structure present (Levels 0-3)")
            else:
                missing = expected_levels - actual_levels
                if missing:
                    print(f"  Note: Some standard levels missing: {sorted(missing)}")
            
            if not any([e for e in self.errors if 'OutlineLevel' in e]):
                print(f"  Hierarchy validation passed")
    
    def check_wbs_codes(self):
        """Validate WBS code formatting"""
        print("\n✓ Checking WBS codes...")
        
        wbs_pattern = re.compile(r'^(\d+\.)*\d+$')
        malformed_wbs = []
        
        for task in self._find_all('.//ms:Task' if self.ns['ms'] else './/Task'):
            uid = self._findtext(task, 'ms:UID' if self.ns['ms'] else 'UID')
            name = self._findtext(task, 'ms:Name' if self.ns['ms'] else 'Name')
            wbs = self._findtext(task, 'ms:WBS' if self.ns['ms'] else 'WBS')
            outline_level = self._findtext(task, 'ms:OutlineLevel' if self.ns['ms'] else 'OutlineLevel')
            
            if wbs and wbs != '0':
                if not wbs_pattern.match(wbs):
                    self.errors.append(
                        f"Task UID={uid} ('{name}') has malformed WBS code: '{wbs}'"
                    )
                    malformed_wbs.append(wbs)
                else:
                    wbs_depth = len(wbs.split('.'))
                    try:
                        expected_depth = int(outline_level) if outline_level else 0
                        if wbs_depth != expected_depth and expected_depth != 0:
                            self.warnings.append(
                                f"Task UID={uid} ('{name}') WBS depth ({wbs_depth}) doesn't match OutlineLevel ({outline_level})"
                            )
                    except ValueError:
                        pass
        
        if not malformed_wbs:
            print(f"  All WBS codes properly formatted")
    
    def check_data_types(self):
        """Validate numeric fields and date formats"""
        print("\n✓ Checking data types...")
        
        iso_date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
        
        for resource in self._find_all('.//ms:Resource' if self.ns['ms'] else './/Resource'):
            uid = self._findtext(resource, 'ms:UID' if self.ns['ms'] else 'UID')
            name = self._findtext(resource, 'ms:Name' if self.ns['ms'] else 'Name')
            standard_rate = self._findtext(resource, 'ms:StandardRate' if self.ns['ms'] else 'StandardRate')
            overtime_rate = self._findtext(resource, 'ms:OvertimeRate' if self.ns['ms'] else 'OvertimeRate')
            
            if standard_rate:
                if '$' in standard_rate or '/h' in standard_rate or '/hr' in standard_rate:
                    self.errors.append(
                        f"Resource UID={uid} ('{name}') StandardRate contains non-numeric value: '{standard_rate}'"
                    )
                else:
                    try:
                        float(standard_rate)
                    except ValueError:
                        self.errors.append(
                            f"Resource UID={uid} ('{name}') StandardRate is not a valid number: '{standard_rate}'"
                        )
            
            if overtime_rate:
                if '$' in overtime_rate or '/h' in overtime_rate or '/hr' in overtime_rate:
                    self.errors.append(
                        f"Resource UID={uid} ('{name}') OvertimeRate contains non-numeric value: '{overtime_rate}'"
                    )
                else:
                    try:
                        float(overtime_rate)
                    except ValueError:
                        self.errors.append(
                            f"Resource UID={uid} ('{name}') OvertimeRate is not a valid number: '{overtime_rate}'"
                        )
        
        for task in self._find_all('.//ms:Task' if self.ns['ms'] else './/Task'):
            uid = self._findtext(task, 'ms:UID' if self.ns['ms'] else 'UID')
            name = self._findtext(task, 'ms:Name' if self.ns['ms'] else 'Name')
            start = self._findtext(task, 'ms:Start' if self.ns['ms'] else 'Start')
            finish = self._findtext(task, 'ms:Finish' if self.ns['ms'] else 'Finish')
            cost = self._findtext(task, 'ms:Cost' if self.ns['ms'] else 'Cost')
            work = self._findtext(task, 'ms:Work' if self.ns['ms'] else 'Work')
            
            if start and not iso_date_pattern.match(start):
                self.errors.append(
                    f"Task UID={uid} ('{name}') Start date not in ISO 8601 format: '{start}'"
                )
            
            if finish and not iso_date_pattern.match(finish):
                self.errors.append(
                    f"Task UID={uid} ('{name}') Finish date not in ISO 8601 format: '{finish}'"
                )
            
            if cost:
                try:
                    float(cost)
                except ValueError:
                    self.errors.append(
                        f"Task UID={uid} ('{name}') Cost is not a valid number: '{cost}'"
                    )
        
        project_start = self._findtext(self.root, 'ms:StartDate' if self.ns['ms'] else 'StartDate')
        project_finish = self._findtext(self.root, 'ms:FinishDate' if self.ns['ms'] else 'FinishDate')
        
        if project_start and not iso_date_pattern.match(project_start):
            self.errors.append(f"Project StartDate not in ISO 8601 format: '{project_start}'")
        
        if project_finish and not iso_date_pattern.match(project_finish):
            self.errors.append(f"Project FinishDate not in ISO 8601 format: '{project_finish}'")
        
        data_type_errors = [e for e in self.errors if 'non-numeric' in e or 'not a valid number' in e or 'not in ISO 8601' in e]
        if not data_type_errors:
            print(f"  All data types valid (rates are numeric, dates are ISO 8601)")
    
    def check_required_fields(self):
        """Check for required MSPDI elements"""
        print("\n✓ Checking required fields...")
        
        project_name = self._findtext(self.root, 'ms:Name' if self.ns['ms'] else 'Name')
        if not project_name:
            self.errors.append("Project Name is missing")
        
        project_start = self._findtext(self.root, 'ms:StartDate' if self.ns['ms'] else 'StartDate')
        if not project_start:
            self.warnings.append("Project StartDate is missing")
        
        for resource in self._find_all('.//ms:Resource' if self.ns['ms'] else './/Resource'):
            uid = self._findtext(resource, 'ms:UID' if self.ns['ms'] else 'UID')
            res_id = self._findtext(resource, 'ms:ID' if self.ns['ms'] else 'ID')
            name = self._findtext(resource, 'ms:Name' if self.ns['ms'] else 'Name')
            
            if not uid:
                self.errors.append(f"Resource missing UID (Name: '{name}')")
            if not res_id:
                self.errors.append(f"Resource UID={uid} missing ID")
            if not name:
                self.warnings.append(f"Resource UID={uid} missing Name")
        
        for task in self._find_all('.//ms:Task' if self.ns['ms'] else './/Task'):
            uid = self._findtext(task, 'ms:UID' if self.ns['ms'] else 'UID')
            task_id = self._findtext(task, 'ms:ID' if self.ns['ms'] else 'ID')
            name = self._findtext(task, 'ms:Name' if self.ns['ms'] else 'Name')
            
            if not uid:
                self.errors.append(f"Task missing UID (Name: '{name}')")
            if not task_id:
                self.errors.append(f"Task UID={uid} missing ID")
            if not name:
                self.warnings.append(f"Task UID={uid} missing Name")
        
        required_errors = [e for e in self.errors if 'missing' in e.lower()]
        if not required_errors:
            print(f"  All required fields present")
    
    def check_workfront_compatibility(self):
        """Check Workfront-specific requirements for units and dependency types"""
        print("\n✓ Checking Workfront compatibility...")
        
        # Check Assignment Units (must be fractional ≤ 1.0, not percentage like 100)
        invalid_assignment_units = []
        for assignment in self._find_all('.//ms:Assignment' if self.ns['ms'] else './/Assignment'):
            uid = self._findtext(assignment, 'ms:UID' if self.ns['ms'] else 'UID')
            units = self._findtext(assignment, 'ms:Units' if self.ns['ms'] else 'Units')
            
            if units:
                try:
                    units_val = float(units)
                    if units_val > 1.0:
                        self.errors.append(
                            f"Assignment UID={uid} has Units={units} (must be ≤ 1.0 for Workfront). "
                            f"Use fractional format: 1.0 = 100%, not percentage format 100 = 100%"
                        )
                        invalid_assignment_units.append(uid)
                except ValueError:
                    self.errors.append(
                        f"Assignment UID={uid} has invalid Units value: '{units}'"
                    )
        
        # Check Resource MaxUnits and PeakUnits (must be fractional ≤ 1.0)
        invalid_resource_units = []
        for resource in self._find_all('.//ms:Resource' if self.ns['ms'] else './/Resource'):
            uid = self._findtext(resource, 'ms:UID' if self.ns['ms'] else 'UID')
            name = self._findtext(resource, 'ms:Name' if self.ns['ms'] else 'Name')
            max_units = self._findtext(resource, 'ms:MaxUnits' if self.ns['ms'] else 'MaxUnits')
            peak_units = self._findtext(resource, 'ms:PeakUnits' if self.ns['ms'] else 'PeakUnits')
            
            if max_units:
                try:
                    max_units_val = float(max_units)
                    if max_units_val > 1.0:
                        self.errors.append(
                            f"Resource UID={uid} ('{name}') has MaxUnits={max_units} (must be ≤ 1.0 for Workfront). "
                            f"Use fractional format: 1.0 = 100%"
                        )
                        invalid_resource_units.append(uid)
                except ValueError:
                    self.errors.append(
                        f"Resource UID={uid} ('{name}') has invalid MaxUnits value: '{max_units}'"
                    )
            
            if peak_units:
                try:
                    peak_units_val = float(peak_units)
                    if peak_units_val > 1.0:
                        self.errors.append(
                            f"Resource UID={uid} ('{name}') has PeakUnits={peak_units} (must be ≤ 1.0 for Workfront). "
                            f"Use fractional format: 1.0 = 100%"
                        )
                        if uid not in invalid_resource_units:
                            invalid_resource_units.append(uid)
                except ValueError:
                    self.errors.append(
                        f"Resource UID={uid} ('{name}') has invalid PeakUnits value: '{peak_units}'"
                    )
        
        # Check PredecessorLink Type (must be 1=FS, 2=SS, or 3=FF - NOT 0)
        invalid_predecessor_types = []
        for pred_link in self._find_all('.//ms:PredecessorLink' if self.ns['ms'] else './/PredecessorLink'):
            pred_uid = self._findtext(pred_link, 'ms:PredecessorUID' if self.ns['ms'] else 'PredecessorUID')
            link_type = self._findtext(pred_link, 'ms:Type' if self.ns['ms'] else 'Type')
            
            if link_type:
                if link_type.strip() not in {'1', '2', '3'}:
                    self.errors.append(
                        f"PredecessorLink to UID={pred_uid} has invalid Type={link_type}. "
                        f"Workfront requires: 1=FS (Finish-to-Start), 2=SS (Start-to-Start), or 3=FF (Finish-to-Finish)"
                    )
                    invalid_predecessor_types.append(pred_uid)
        
        # Summary
        if not invalid_assignment_units and not invalid_resource_units and not invalid_predecessor_types:
            print(f"  Assignment Units: All values ≤ 1.0 (fractional format) ✓")
            print(f"  Resource MaxUnits/PeakUnits: All values ≤ 1.0 (fractional format) ✓")
            print(f"  PredecessorLink Types: All values valid (1, 2, or 3) ✓")
            print(f"  Workfront compatibility checks passed")
        else:
            if invalid_assignment_units:
                print(f"  ❌ Found {len(invalid_assignment_units)} assignment(s) with invalid Units")
            if invalid_resource_units:
                print(f"  ❌ Found {len(invalid_resource_units)} resource(s) with invalid MaxUnits/PeakUnits")
            if invalid_predecessor_types:
                print(f"  ❌ Found {len(invalid_predecessor_types)} dependency/ies with invalid Type")
    
    def check_extended_attributes(self):
        """Check ExtendedAttributes usage and proper MSPDI schema structure"""
        print("\n✓ Checking ExtendedAttributes usage and schema structure...")
        
        # Count ExtendedAttribute definitions in header
        ext_attr_defs = self._find_all('.//ms:ExtendedAttributes/ms:ExtendedAttribute' if self.ns['ms'] else './/ExtendedAttributes/ExtendedAttribute')
        num_definitions = len(ext_attr_defs)
        
        # Check tasks for proper ExtendedAttributes structure
        tasks_with_values = 0
        total_values = 0
        bare_ext_attrs = 0  # ExtendedAttribute elements NOT wrapped in ExtendedAttributes container
        missing_metadata = []  # ExtendedAttribute elements missing required metadata
        
        for task in self._find_all('.//ms:Task' if self.ns['ms'] else './/Task'):
            task_uid = self._findtext(task, 'ms:UID' if self.ns['ms'] else 'UID')
            
            # Check for bare ExtendedAttribute elements (WRONG - old schema)
            bare_attrs = task.findall('ms:ExtendedAttribute' if self.ns['ms'] else 'ExtendedAttribute', self.ns if self.ns['ms'] else None)
            if bare_attrs:
                bare_ext_attrs += len(bare_attrs)
                self.errors.append(
                    f"Task UID={task_uid}: Found {len(bare_attrs)} bare <ExtendedAttribute> element(s) "
                    f"not wrapped in <ExtendedAttributes> container. Workfront requires proper MSPDI schema: "
                    f"<ExtendedAttributes><ExtendedAttribute>...</ExtendedAttribute></ExtendedAttributes>"
                )
            
            # Check for properly wrapped ExtendedAttributes (CORRECT - new schema)
            ext_attrs_container = task.find('ms:ExtendedAttributes' if self.ns['ms'] else 'ExtendedAttributes', self.ns if self.ns['ms'] else None)
            if ext_attrs_container is not None:
                tasks_with_values += 1
                ext_attrs = ext_attrs_container.findall('ms:ExtendedAttribute' if self.ns['ms'] else 'ExtendedAttribute', self.ns if self.ns['ms'] else None)
                total_values += len(ext_attrs)
                
                # Validate each ExtendedAttribute has required metadata
                for ext_attr in ext_attrs:
                    uid = self._findtext(ext_attr, 'ms:UID' if self.ns['ms'] else 'UID')
                    field_id = self._findtext(ext_attr, 'ms:FieldID' if self.ns['ms'] else 'FieldID')
                    element_type = self._findtext(ext_attr, 'ms:ElementType' if self.ns['ms'] else 'ElementType')
                    cf_type = self._findtext(ext_attr, 'ms:CfType' if self.ns['ms'] else 'CfType')
                    
                    missing_fields = []
                    if not uid:
                        missing_fields.append('UID')
                    if not element_type:
                        missing_fields.append('ElementType')
                    if not cf_type:
                        missing_fields.append('CfType')
                    
                    if missing_fields:
                        missing_metadata.append({
                            'task_uid': task_uid,
                            'field_id': field_id,
                            'missing': missing_fields
                        })
        
        # Report findings
        if bare_ext_attrs > 0:
            print(f"  ❌ Found {bare_ext_attrs} bare ExtendedAttribute element(s) without proper wrapper")
            print(f"  ❌ Workfront will reject this file due to schema violations")
        
        if missing_metadata:
            for item in missing_metadata[:5]:  # Show first 5
                self.errors.append(
                    f"Task UID={item['task_uid']}, FieldID={item['field_id']}: "
                    f"ExtendedAttribute missing required fields: {', '.join(item['missing'])}"
                )
            if len(missing_metadata) > 5:
                self.errors.append(f"... and {len(missing_metadata) - 5} more ExtendedAttribute(s) with missing metadata")
            print(f"  ❌ Found {len(missing_metadata)} ExtendedAttribute(s) missing required metadata")
        
        # Check for unused definitions
        if num_definitions > 0 and total_values == 0 and bare_ext_attrs == 0:
            self.warnings.append(
                f"Found {num_definitions} ExtendedAttribute definition(s) in header but 0 tasks use them. "
                f"Workfront may reject this as corrupted/incomplete."
            )
            print(f"  ⚠️  {num_definitions} custom field(s) defined but never used")
        
        # Success message
        if bare_ext_attrs == 0 and len(missing_metadata) == 0:
            if num_definitions > 0:
                print(f"  {num_definitions} custom field(s) defined")
                print(f"  {total_values} ExtendedAttribute(s) in {tasks_with_values} task(s)")
                print(f"  All ExtendedAttributes properly wrapped and structured ✓")
            else:
                print(f"  No ExtendedAttributes defined (clean export) ✓")
    
    def validate(self) -> bool:
        """Run all validation checks"""
        print(f"Validating: {self.xml_file}")
        print("=" * 70)
        
        # Check XML declaration FIRST (before parsing)
        print("\n✓ Checking XML declaration format...")
        self.check_xml_declaration()
        
        if not self.load_xml():
            return False
        
        self.check_duplicate_uids()
        self.check_reference_integrity()
        self.check_hierarchy()
        self.check_wbs_codes()
        self.check_data_types()
        self.check_required_fields()
        self.check_workfront_compatibility()
        self.check_extended_attributes()
        
        return self.print_results()
    
    def print_results(self) -> bool:
        """Print validation results"""
        print("\n" + "=" * 70)
        
        if not self.errors and not self.warnings:
            print("✅ VALIDATION PASSED - XML is Workfront-compatible")
            return True
        
        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} WARNING(S):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if self.errors:
            print(f"\n❌ {len(self.errors)} ERROR(S):")
            for error in self.errors:
                print(f"  - {error}")
            print("\n❌ XML NOT ready for Workfront import!")
            return False
        
        print("\n✅ VALIDATION PASSED - XML is Workfront-compatible (with warnings)")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_workfront_xml.py <xml_file>")
        print("\nExample:")
        print("  python validate_workfront_xml.py project.xml")
        sys.exit(1)
    
    validator = WorkfrontXMLValidator(sys.argv[1])
    success = validator.validate()
    sys.exit(0 if success else 1)
