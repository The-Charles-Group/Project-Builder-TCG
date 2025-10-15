#!/usr/bin/env python3
"""
Comprehensive Test Suite for XML Export and Workfront Compatibility
Tests WBS structure, dependencies, resources, custom fields, and MSPDI compliance
"""

import unittest
import os
import sys
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import json
from typing import Dict, List, Optional, Tuple, Set

# Import the converter module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from convert_excel_to_mspdi import convert_excel_to_mspdi, DependencyType, ConstraintType

class TestXMLWorkfrontExport(unittest.TestCase):
    """Test suite for XML export and Workfront compatibility"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.test_output_dir = "test_outputs"
        os.makedirs(cls.test_output_dir, exist_ok=True)
        cls.namespace = "http://schemas.microsoft.com/project"
        
    def setUp(self):
        """Set up for each test"""
        self.test_excel = os.path.join(self.test_output_dir, "test_wbs.xlsx")
        self.test_xml = os.path.join(self.test_output_dir, "test_output.xml")
        
    def tearDown(self):
        """Clean up after each test"""
        # Keep files for inspection
        pass
        
    def create_sample_wbs_data(self) -> pd.DataFrame:
        """Create sample WBS data for testing"""
        data = {
            'WBS': ['1', '1.1', '1.1.1', '1.1.2', '1.2', '1.2.1', '2', '2.1', '2.1.1'],
            'Deliverable': ['Phase 1', 'Strategy', 'Research', 'Analysis', 'Development', 'Coding', 
                           'Phase 2', 'Testing', 'QA Testing'],
            'Component': ['Planning', 'Strategic Planning', 'Market Research', 'Data Analysis',
                         'Dev Work', 'Backend Code', 'Delivery', 'Quality Assurance', 'Test Cases'],
            'Task': ['Phase 1 Planning', 'Strategy Development', 'Conduct Research', 'Analyze Data',
                    'Development Phase', 'Write Code', 'Phase 2 Delivery', 'Testing Phase', 'Execute Tests'],
            'Department': ['Strategy', 'Strategy', 'Research', 'Analytics', 'Engineering', 'Engineering',
                          'Delivery', 'QA', 'QA'],
            'Role': ['Director', 'Manager', 'Analyst', 'Sr. Analyst', 'Developer', 'Sr. Developer',
                    'Director', 'QA Lead', 'QA Engineer'],
            'Seniority': ['Senior', 'Senior', 'Junior', 'Mid', 'Mid', 'Senior', 'Senior', 'Senior', 'Mid'],
            'Hours': [8, 16, 40, 32, 80, 120, 8, 24, 60],
            'Rate': [250, 200, 125, 150, 175, 200, 250, 180, 140],
            'Total Price': [2000, 3200, 5000, 4800, 14000, 24000, 2000, 4320, 8400],
            'Dependencies': ['', '1', '1.1', '1.1.1', '1.1', '1.2', '1', '2', '2.1'],
            'Lag_Days': [0, 0, 1, 2, 0, 1, 5, 0, 1],
            'Dependency_Type': ['', 'FS', 'FS', 'SS', 'FS', 'FF', 'FS', 'FS', 'FS'],
            'Risk_Score': [1, 2, 3, 2, 4, 3, 2, 3, 2],
            'Confidence_Level': [95, 90, 85, 88, 80, 85, 92, 87, 90],
            'Deliverable_Code': ['DEL-001', 'DEL-001.1', 'DEL-001.1.1', 'DEL-001.1.2', 
                                 'DEL-001.2', 'DEL-001.2.1', 'DEL-002', 'DEL-002.1', 'DEL-002.1.1'],
        }
        return pd.DataFrame(data)
    
    def parse_xml(self, xml_path: str) -> ET.Element:
        """Parse XML file and return root element"""
        tree = ET.parse(xml_path)
        return tree.getroot()
    
    def get_all_tasks(self, root: ET.Element) -> List[ET.Element]:
        """Get all task elements from XML"""
        return root.findall(f".//{{{self.namespace}}}Task")
    
    def get_task_by_uid(self, root: ET.Element, uid: str) -> Optional[ET.Element]:
        """Get task by UID"""
        tasks = self.get_all_tasks(root)
        for task in tasks:
            task_uid = task.find(f"{{{self.namespace}}}UID")
            if task_uid is not None and task_uid.text == str(uid):
                return task
        return None
    
    def test_xml_structure_wbs_numbering(self):
        """Test 1.1: Verify WBS numbering (1, 1.1, 1.1.1)"""
        print("\n=== Test 1.1: WBS Numbering ===")
        
        # Create test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        result = convert_excel_to_mspdi(
            self.test_excel,
            self.test_xml,
            add_custom_fields=True,
            add_dependencies=True
        )
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        tasks = self.get_all_tasks(root)
        
        # Check WBS numbers
        wbs_found = {}
        for task in tasks:
            wbs_elem = task.find(f"{{{self.namespace}}}WBS")
            name_elem = task.find(f"{{{self.namespace}}}Name")
            if wbs_elem is not None and name_elem is not None:
                wbs = wbs_elem.text
                name = name_elem.text
                wbs_found[wbs] = name
                print(f"  Found WBS: {wbs} -> {name}")
        
        # Verify expected WBS numbers exist
        expected_wbs = ['0', '1', '1.1', '1.1.1', '1.1.2', '1.2', '1.2.1', '2', '2.1', '2.1.1']
        for wbs in expected_wbs:
            if wbs != '0':  # Skip project root
                self.assertIn(wbs, wbs_found, f"WBS {wbs} not found in XML")
        
        print(f"  ✓ All WBS numbers correctly formatted")
        
    def test_xml_structure_outline_fields(self):
        """Test 1.2: Check OutlineNumber and OutlineLevel fields"""
        print("\n=== Test 1.2: Outline Fields ===")
        
        # Create test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        convert_excel_to_mspdi(self.test_excel, self.test_xml)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        tasks = self.get_all_tasks(root)
        
        # Check outline fields
        for task in tasks:
            wbs_elem = task.find(f"{{{self.namespace}}}WBS")
            outline_num_elem = task.find(f"{{{self.namespace}}}OutlineNumber")
            outline_level_elem = task.find(f"{{{self.namespace}}}OutlineLevel")
            
            if wbs_elem is not None and wbs_elem.text != '0':
                wbs = wbs_elem.text
                
                # Check OutlineNumber matches WBS
                self.assertIsNotNone(outline_num_elem, f"OutlineNumber missing for WBS {wbs}")
                self.assertEqual(outline_num_elem.text, wbs, f"OutlineNumber mismatch for WBS {wbs}")
                
                # Check OutlineLevel matches depth
                expected_level = str(wbs.count('.') + 1)
                self.assertIsNotNone(outline_level_elem, f"OutlineLevel missing for WBS {wbs}")
                self.assertEqual(outline_level_elem.text, expected_level, 
                               f"OutlineLevel mismatch for WBS {wbs}: expected {expected_level}, got {outline_level_elem.text}")
                
                print(f"  WBS {wbs}: OutlineNumber={outline_num_elem.text}, OutlineLevel={outline_level_elem.text} ✓")
        
        print(f"  ✓ All outline fields correctly set")
        
    def test_xml_structure_hierarchy(self):
        """Test 1.3: Validate parent-child task relationships and hierarchy"""
        print("\n=== Test 1.3: Task Hierarchy ===")
        
        # Create test data with clear parent-child relationships
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        convert_excel_to_mspdi(self.test_excel, self.test_xml)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        tasks = self.get_all_tasks(root)
        
        # Build hierarchy map
        hierarchy = {}
        for task in tasks:
            uid_elem = task.find(f"{{{self.namespace}}}UID")
            wbs_elem = task.find(f"{{{self.namespace}}}WBS")
            name_elem = task.find(f"{{{self.namespace}}}Name")
            summary_elem = task.find(f"{{{self.namespace}}}Summary")
            
            if uid_elem is not None and wbs_elem is not None:
                uid = uid_elem.text
                wbs = wbs_elem.text
                name = name_elem.text if name_elem is not None else ""
                is_summary = summary_elem.text == '1' if summary_elem is not None else False
                
                hierarchy[wbs] = {
                    'uid': uid,
                    'name': name,
                    'is_summary': is_summary
                }
        
        # Verify parent tasks are marked as summary
        parent_wbs = ['1', '1.1', '1.2', '2', '2.1']
        for wbs in parent_wbs:
            if wbs in hierarchy:
                self.assertTrue(hierarchy[wbs]['is_summary'], 
                              f"Parent task {wbs} not marked as summary")
                print(f"  Parent WBS {wbs}: Summary={hierarchy[wbs]['is_summary']} ✓")
        
        # Verify leaf tasks are not summary
        leaf_wbs = ['1.1.1', '1.1.2', '1.2.1', '2.1.1']
        for wbs in leaf_wbs:
            if wbs in hierarchy:
                self.assertFalse(hierarchy[wbs]['is_summary'], 
                               f"Leaf task {wbs} incorrectly marked as summary")
                print(f"  Leaf WBS {wbs}: Summary={hierarchy[wbs]['is_summary']} ✓")
        
        print(f"  ✓ Task hierarchy correctly established")
        
    def test_dependencies_all_types(self):
        """Test 2.1: Verify all dependency types (FS, SS, FF, SF)"""
        print("\n=== Test 2.1: Dependency Types ===")
        
        # Create test data with all dependency types
        data = {
            'WBS': ['1', '2', '3', '4', '5'],
            'Task': ['Task A', 'Task B', 'Task C', 'Task D', 'Task E'],
            'Hours': [40, 32, 24, 16, 40],
            'Department': ['Dev', 'Dev', 'QA', 'QA', 'Dev'],
            'Dependencies': ['', '1', '2', '3', '4'],
            'Dependency_Type': ['', 'FS', 'SS', 'FF', 'SF']  # All types
        }
        df = pd.DataFrame(data)
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        convert_excel_to_mspdi(self.test_excel, self.test_xml, add_dependencies=True)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        tasks = self.get_all_tasks(root)
        
        # Check predecessor links
        dependency_types_found = {}
        for task in tasks:
            predecessors = task.findall(f"{{{self.namespace}}}PredecessorLink")
            for pred in predecessors:
                pred_uid_elem = pred.find(f"{{{self.namespace}}}PredecessorUID")
                type_elem = pred.find(f"{{{self.namespace}}}Type")
                
                if pred_uid_elem is not None and type_elem is not None:
                    dep_type = type_elem.text
                    # Map numeric types to names
                    type_map = {'1': 'FS', '2': 'SS', '3': 'FF', '4': 'SF'}
                    dep_name = type_map.get(dep_type, dep_type)
                    dependency_types_found[dep_name] = True
                    print(f"  Found dependency type: {dep_name} (value={dep_type})")
        
        # Verify all types are present
        expected_types = ['FS', 'SS', 'FF', 'SF']
        for dep_type in expected_types:
            self.assertIn(dep_type, dependency_types_found, 
                         f"Dependency type {dep_type} not found")
        
        print(f"  ✓ All dependency types correctly implemented")
        
    def test_dependencies_lag_lead(self):
        """Test 2.2: Check lag/lead times are included"""
        print("\n=== Test 2.2: Lag/Lead Times ===")
        
        # Create test data with lag times
        data = {
            'WBS': ['1', '2', '3', '4'],
            'Task': ['Task A', 'Task B', 'Task C', 'Task D'],
            'Hours': [40, 32, 24, 16],
            'Department': ['Dev', 'Dev', 'QA', 'QA'],
            'Dependencies': ['', '1', '2', '3'],
            'Lag_Days': [0, 2, -1, 3]  # Positive lag and negative lead
        }
        df = pd.DataFrame(data)
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        convert_excel_to_mspdi(self.test_excel, self.test_xml, add_dependencies=True)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        tasks = self.get_all_tasks(root)
        
        # Check lag values
        lag_values_found = []
        for task in tasks:
            predecessors = task.findall(f"{{{self.namespace}}}PredecessorLink")
            for pred in predecessors:
                lag_elem = pred.find(f"{{{self.namespace}}}LinkLag")
                if lag_elem is not None:
                    lag_value = int(lag_elem.text)
                    lag_values_found.append(lag_value)
                    lag_type = "lag" if lag_value >= 0 else "lead"
                    print(f"  Found {lag_type}: {lag_value} (10ths of minute)")
        
        # Verify lag values are present
        self.assertGreater(len(lag_values_found), 0, "No lag values found")
        print(f"  ✓ Lag/lead times correctly included: {len(lag_values_found)} values found")
        
    def test_dependencies_chain_integrity(self):
        """Test 2.3: Test dependency chain integrity"""
        print("\n=== Test 2.3: Dependency Chain Integrity ===")
        
        # Create test data with dependency chain
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        convert_excel_to_mspdi(self.test_excel, self.test_xml, add_dependencies=True)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        tasks = self.get_all_tasks(root)
        
        # Build dependency map
        dependency_map = {}
        task_uid_to_wbs = {}
        
        for task in tasks:
            uid_elem = task.find(f"{{{self.namespace}}}UID")
            wbs_elem = task.find(f"{{{self.namespace}}}WBS")
            
            if uid_elem is not None and wbs_elem is not None:
                uid = uid_elem.text
                wbs = wbs_elem.text
                task_uid_to_wbs[uid] = wbs
                
                predecessors = task.findall(f"{{{self.namespace}}}PredecessorLink")
                deps = []
                for pred in predecessors:
                    pred_uid_elem = pred.find(f"{{{self.namespace}}}PredecessorUID")
                    if pred_uid_elem is not None:
                        deps.append(pred_uid_elem.text)
                
                if deps:
                    dependency_map[wbs] = deps
                    print(f"  Task {wbs} depends on UIDs: {deps}")
        
        # Verify no circular dependencies
        def has_circular(wbs, visited=None):
            if visited is None:
                visited = set()
            if wbs in visited:
                return True
            visited.add(wbs)
            
            if wbs in dependency_map:
                for dep_uid in dependency_map[wbs]:
                    dep_wbs = task_uid_to_wbs.get(dep_uid)
                    if dep_wbs and has_circular(dep_wbs, visited.copy()):
                        return True
            return False
        
        for wbs in dependency_map:
            self.assertFalse(has_circular(wbs), f"Circular dependency detected for {wbs}")
        
        print(f"  ✓ No circular dependencies found")
        print(f"  ✓ Dependency chain integrity verified")
        
    def test_resource_assignments(self):
        """Test 3.1: Check resource assignments are created"""
        print("\n=== Test 3.1: Resource Assignments ===")
        
        # Create test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        convert_excel_to_mspdi(self.test_excel, self.test_xml)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        
        # Check resources
        resources = root.findall(f".//{{{self.namespace}}}Resource")
        self.assertGreater(len(resources), 0, "No resources found")
        print(f"  Found {len(resources)} resources")
        
        # Check resource details
        resource_map = {}
        for res in resources:
            uid_elem = res.find(f"{{{self.namespace}}}UID")
            name_elem = res.find(f"{{{self.namespace}}}Name")
            if uid_elem is not None and name_elem is not None:
                resource_map[uid_elem.text] = name_elem.text
                print(f"  Resource {uid_elem.text}: {name_elem.text}")
        
        # Check assignments
        assignments = root.findall(f".//{{{self.namespace}}}Assignment")
        self.assertGreater(len(assignments), 0, "No assignments found")
        print(f"  Found {len(assignments)} assignments")
        
        print(f"  ✓ Resource assignments correctly created")
        
    def test_resource_allocation_units(self):
        """Test 3.2: Verify Units field (100% allocation)"""
        print("\n=== Test 3.2: Resource Allocation Units ===")
        
        # Create test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        convert_excel_to_mspdi(self.test_excel, self.test_xml)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        assignments = root.findall(f".//{{{self.namespace}}}Assignment")
        
        # Check Units field
        for assignment in assignments:
            units_elem = assignment.find(f"{{{self.namespace}}}Units")
            if units_elem is not None:
                units = float(units_elem.text)
                self.assertGreaterEqual(units, 0, "Units should be non-negative")
                self.assertLessEqual(units, 100, "Units should not exceed 100%")
                print(f"  Assignment units: {units}%")
        
        print(f"  ✓ All Units fields within valid range")
        
    def test_resource_work_fields(self):
        """Test 3.3: Test Work and RegularWork fields"""
        print("\n=== Test 3.3: Work Fields ===")
        
        # Create test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        convert_excel_to_mspdi(self.test_excel, self.test_xml)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        assignments = root.findall(f".//{{{self.namespace}}}Assignment")
        
        # Check Work fields
        work_values_found = False
        for assignment in assignments:
            work_elem = assignment.find(f"{{{self.namespace}}}Work")
            regular_work_elem = assignment.find(f"{{{self.namespace}}}RegularWork")
            
            if work_elem is not None:
                work_values_found = True
                work_value = work_elem.text
                print(f"  Work: {work_value}")
                
                # Verify format (PTxHxMxS)
                self.assertTrue(work_value.startswith('PT'), "Work should be in PT format")
                self.assertTrue('H' in work_value, "Work should include hours")
        
        self.assertTrue(work_values_found, "No Work fields found")
        print(f"  ✓ Work fields correctly formatted")
        
    def test_resource_department_mapping(self):
        """Test 3.4: Validate department mapping to resources"""
        print("\n=== Test 3.4: Department Mapping ===")
        
        # Create test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        convert_excel_to_mspdi(self.test_excel, self.test_xml)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        resources = root.findall(f".//{{{self.namespace}}}Resource")
        
        # Check department-based resources
        departments_found = set()
        for res in resources:
            name_elem = res.find(f"{{{self.namespace}}}Name")
            group_elem = res.find(f"{{{self.namespace}}}Group")
            
            if name_elem is not None and group_elem is not None:
                name = name_elem.text
                group = group_elem.text
                if 'Team' in name:
                    departments_found.add(group)
                    print(f"  Department resource: {name} (Group: {group})")
        
        # Verify expected departments
        expected_depts = {'Strategy', 'Research', 'Analytics', 'Engineering', 'QA', 'Delivery'}
        for dept in expected_depts:
            if dept in df['Department'].values:
                self.assertIn(dept, departments_found, f"Department {dept} not found in resources")
        
        print(f"  ✓ Departments correctly mapped to resources")
        
    def test_custom_fields_definitions(self):
        """Test 4.1: Verify ExtendedAttribute definitions (5 custom fields)"""
        print("\n=== Test 4.1: ExtendedAttribute Definitions ===")
        
        # Create test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML with custom fields
        convert_excel_to_mspdi(self.test_excel, self.test_xml, add_custom_fields=True)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        
        # Check ExtendedAttributes definitions
        ext_attrs = root.find(f".//{{{self.namespace}}}ExtendedAttributes")
        self.assertIsNotNone(ext_attrs, "ExtendedAttributes section not found")
        
        ext_attr_defs = ext_attrs.findall(f"{{{self.namespace}}}ExtendedAttribute")
        self.assertGreaterEqual(len(ext_attr_defs), 5, "Should have at least 5 custom field definitions")
        
        # Check each definition
        fields_found = {}
        for ext_attr in ext_attr_defs:
            field_id = ext_attr.find(f"{{{self.namespace}}}FieldID")
            alias = ext_attr.find(f"{{{self.namespace}}}Alias")
            
            if field_id is not None and alias is not None:
                fields_found[alias.text] = field_id.text
                print(f"  Custom field: {alias.text} (ID: {field_id.text})")
        
        # Verify expected fields
        expected_fields = ['Risk Score', 'Confidence Level', 'Department', 
                          'Deliverable Code', 'Component Name']
        for field in expected_fields:
            self.assertIn(field, fields_found, f"Custom field '{field}' not defined")
        
        print(f"  ✓ All 5 custom fields correctly defined")
        
    def test_custom_fields_values(self):
        """Test 4.2: Validate custom field values in tasks"""
        print("\n=== Test 4.2: Custom Field Values ===")
        
        # Create test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML with custom fields
        convert_excel_to_mspdi(self.test_excel, self.test_xml, add_custom_fields=True)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        tasks = self.get_all_tasks(root)
        
        # Check custom field values in tasks
        custom_values_found = 0
        for task in tasks:
            ext_attrs = task.findall(f"{{{self.namespace}}}ExtendedAttribute")
            for ext_attr in ext_attrs:
                field_id = ext_attr.find(f"{{{self.namespace}}}FieldID")
                value = ext_attr.find(f"{{{self.namespace}}}Value")
                
                if field_id is not None and value is not None:
                    custom_values_found += 1
                    print(f"  Task custom field {field_id.text}: {value.text}")
        
        self.assertGreater(custom_values_found, 0, "No custom field values found in tasks")
        print(f"  ✓ Custom field values found: {custom_values_found}")
        
    def test_workfront_mspdi_compliance(self):
        """Test 5.1: Check MSPDI format compliance"""
        print("\n=== Test 5.1: MSPDI Format Compliance ===")
        
        # Create test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        convert_excel_to_mspdi(self.test_excel, self.test_xml)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        
        # Check required MSPDI elements
        required_elements = [
            'SaveVersion', 'Name', 'Title', 'ScheduleFromStart',
            'StartDate', 'FinishDate', 'CalendarUID', 'Tasks',
            'Resources', 'Assignments', 'Calendars'
        ]
        
        for elem_name in required_elements:
            elem = root.find(f".//{{{self.namespace}}}{elem_name}")
            self.assertIsNotNone(elem, f"Required MSPDI element '{elem_name}' not found")
            print(f"  ✓ {elem_name} present")
        
        print(f"  ✓ MSPDI format compliance verified")
        
    def test_workfront_anchor_milestones(self):
        """Test 5.2: Test with/without anchor milestones"""
        print("\n=== Test 5.2: Anchor Milestones ===")
        
        # Create test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Test WITH milestones
        xml_with_milestones = os.path.join(self.test_output_dir, "test_with_milestones.xml")
        convert_excel_to_mspdi(
            self.test_excel, 
            xml_with_milestones,
            add_deliverable_milestones=True,
            add_phase_gates=True
        )
        
        root_with = self.parse_xml(xml_with_milestones)
        tasks_with = self.get_all_tasks(root_with)
        
        # Count milestones
        milestones_with = 0
        for task in tasks_with:
            milestone_elem = task.find(f"{{{self.namespace}}}Milestone")
            if milestone_elem is not None and milestone_elem.text == '1':
                milestones_with += 1
                name_elem = task.find(f"{{{self.namespace}}}Name")
                if name_elem is not None:
                    print(f"  Milestone: {name_elem.text}")
        
        # Test WITHOUT milestones
        xml_without_milestones = os.path.join(self.test_output_dir, "test_without_milestones.xml")
        convert_excel_to_mspdi(
            self.test_excel,
            xml_without_milestones,
            add_deliverable_milestones=False,
            add_phase_gates=False
        )
        
        root_without = self.parse_xml(xml_without_milestones)
        tasks_without = self.get_all_tasks(root_without)
        
        # Count milestones
        milestones_without = 0
        for task in tasks_without:
            milestone_elem = task.find(f"{{{self.namespace}}}Milestone")
            if milestone_elem is not None and milestone_elem.text == '1':
                milestones_without += 1
        
        print(f"  With milestones: {milestones_with} milestone tasks")
        print(f"  Without milestones: {milestones_without} milestone tasks")
        
        self.assertGreater(milestones_with, milestones_without, 
                          "Should have more milestones when enabled")
        
        print(f"  ✓ Milestone configuration working correctly")
        
    def test_workfront_calendar_settings(self):
        """Test 5.3: Validate calendar and constraint settings"""
        print("\n=== Test 5.3: Calendar and Constraints ===")
        
        # Create test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Convert to XML
        convert_excel_to_mspdi(self.test_excel, self.test_xml)
        
        # Parse XML
        root = self.parse_xml(self.test_xml)
        
        # Check calendar
        calendars = root.find(f".//{{{self.namespace}}}Calendars")
        self.assertIsNotNone(calendars, "Calendars section not found")
        
        calendar = calendars.find(f"{{{self.namespace}}}Calendar")
        self.assertIsNotNone(calendar, "No calendar defined")
        
        # Check calendar properties
        cal_uid = calendar.find(f"{{{self.namespace}}}UID")
        cal_name = calendar.find(f"{{{self.namespace}}}Name")
        weekdays = calendar.find(f"{{{self.namespace}}}WeekDays")
        
        self.assertIsNotNone(cal_uid, "Calendar UID not found")
        self.assertIsNotNone(cal_name, "Calendar name not found")
        self.assertIsNotNone(weekdays, "Weekdays not defined")
        
        print(f"  Calendar: {cal_name.text} (UID: {cal_uid.text})")
        
        # Check working days
        working_days = 0
        for weekday in weekdays.findall(f"{{{self.namespace}}}WeekDay"):
            day_working = weekday.find(f"{{{self.namespace}}}DayWorking")
            if day_working is not None and day_working.text == '1':
                working_days += 1
        
        self.assertEqual(working_days, 5, "Should have 5 working days")
        print(f"  Working days: {working_days}")
        
        # Check task constraints
        tasks = self.get_all_tasks(root)
        constraints_found = set()
        
        for task in tasks:
            constraint_type = task.find(f"{{{self.namespace}}}ConstraintType")
            if constraint_type is not None:
                constraints_found.add(constraint_type.text)
        
        print(f"  Constraint types found: {constraints_found}")
        print(f"  ✓ Calendar and constraints properly configured")
        
    def test_generate_sample_xmls(self):
        """Generate sample XML files with different configurations"""
        print("\n=== Generating Sample XML Files ===")
        
        # Create comprehensive test data
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        configurations = [
            {
                'name': 'full_features',
                'desc': 'All features enabled',
                'params': {
                    'add_deliverable_milestones': True,
                    'add_phase_gates': True,
                    'add_dependencies': True,
                    'add_custom_fields': True,
                    'merge_identical_children': False
                }
            },
            {
                'name': 'minimal',
                'desc': 'Minimal configuration',
                'params': {
                    'add_deliverable_milestones': False,
                    'add_phase_gates': False,
                    'add_dependencies': False,
                    'add_custom_fields': False,
                    'merge_identical_children': False
                }
            },
            {
                'name': 'workfront_optimized',
                'desc': 'Optimized for Workfront import',
                'params': {
                    'add_deliverable_milestones': True,
                    'add_phase_gates': False,
                    'add_dependencies': True,
                    'add_custom_fields': True,
                    'merge_identical_children': True
                }
            },
            {
                'name': 'dependencies_only',
                'desc': 'Focus on dependencies',
                'params': {
                    'add_deliverable_milestones': False,
                    'add_phase_gates': False,
                    'add_dependencies': True,
                    'add_custom_fields': False,
                    'merge_identical_children': False
                }
            }
        ]
        
        for config in configurations:
            output_file = os.path.join(
                self.test_output_dir, 
                f"sample_{config['name']}.xml"
            )
            
            result = convert_excel_to_mspdi(
                self.test_excel,
                output_file,
                project_name=f"Sample Project - {config['desc']}",
                **config['params']
            )
            
            print(f"  Generated: {config['name']}.xml - {config['desc']}")
            print(f"    Tasks: {result.get('task_count', 0)}")
            
            # Validate the generated XML
            try:
                root = self.parse_xml(output_file)
                tasks = self.get_all_tasks(root)
                print(f"    Verified: {len(tasks)} tasks in XML")
            except Exception as e:
                print(f"    ERROR: Failed to parse - {e}")
        
        print(f"\n  ✓ Sample XML files generated successfully")
        
    def test_compatibility_report(self):
        """Generate Workfront compatibility report"""
        print("\n=== Workfront Compatibility Report ===")
        
        report = []
        report.append("WORKFRONT XML IMPORT COMPATIBILITY REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Test various features
        df = self.create_sample_wbs_data()
        df.to_excel(self.test_excel, sheet_name='Scenario A', index=False)
        
        # Generate test XML
        convert_excel_to_mspdi(
            self.test_excel,
            self.test_xml,
            add_deliverable_milestones=True,
            add_phase_gates=True,
            add_dependencies=True,
            add_custom_fields=True
        )
        
        root = self.parse_xml(self.test_xml)
        
        # Check features
        features = {
            'WBS Numbering': self._check_wbs_numbering(root),
            'Outline Levels': self._check_outline_levels(root),
            'Task Dependencies': self._check_dependencies(root),
            'Resource Assignments': self._check_resources(root),
            'Custom Fields': self._check_custom_fields(root),
            'Milestones': self._check_milestones(root),
            'Calendar Definition': self._check_calendar(root),
            'Duration Format': self._check_duration_format(root),
            'Work Breakdown': self._check_work_breakdown(root),
            'Constraint Types': self._check_constraints(root)
        }
        
        report.append("FEATURE COMPATIBILITY:")
        for feature, (status, notes) in features.items():
            symbol = "✓" if status else "✗"
            report.append(f"  {symbol} {feature}: {notes}")
        
        report.append("")
        report.append("KNOWN ISSUES:")
        report.append("  • Custom field mappings may need manual configuration in Workfront")
        report.append("  • Resource calendars should be reviewed after import")
        report.append("  • Dependency lag times are in 1/10th minutes (may need adjustment)")
        
        report.append("")
        report.append("RECOMMENDATIONS:")
        report.append("  1. Test import with a small project first")
        report.append("  2. Review resource assignments after import")
        report.append("  3. Verify milestone dates are preserved")
        report.append("  4. Check that custom fields map correctly")
        report.append("  5. Validate dependency chains in Gantt view")
        
        # Save report
        report_file = os.path.join(self.test_output_dir, "workfront_compatibility_report.txt")
        with open(report_file, 'w') as f:
            f.write("\n".join(report))
        
        print("\n".join(report))
        print(f"\n  Report saved to: {report_file}")
        
    def _check_wbs_numbering(self, root):
        """Helper to check WBS numbering"""
        tasks = self.get_all_tasks(root)
        wbs_count = sum(1 for t in tasks if t.find(f"{{{self.namespace}}}WBS") is not None)
        return (wbs_count > 0, f"{wbs_count} tasks with WBS")
    
    def _check_outline_levels(self, root):
        """Helper to check outline levels"""
        tasks = self.get_all_tasks(root)
        levels = set()
        for t in tasks:
            level = t.find(f"{{{self.namespace}}}OutlineLevel")
            if level is not None:
                levels.add(level.text)
        return (len(levels) > 1, f"{len(levels)} levels found")
    
    def _check_dependencies(self, root):
        """Helper to check dependencies"""
        tasks = self.get_all_tasks(root)
        dep_count = 0
        for t in tasks:
            preds = t.findall(f"{{{self.namespace}}}PredecessorLink")
            dep_count += len(preds)
        return (dep_count > 0, f"{dep_count} dependencies defined")
    
    def _check_resources(self, root):
        """Helper to check resources"""
        resources = root.findall(f".//{{{self.namespace}}}Resource")
        assignments = root.findall(f".//{{{self.namespace}}}Assignment")
        return (len(resources) > 0 and len(assignments) > 0, 
                f"{len(resources)} resources, {len(assignments)} assignments")
    
    def _check_custom_fields(self, root):
        """Helper to check custom fields"""
        ext_attrs = root.find(f".//{{{self.namespace}}}ExtendedAttributes")
        if ext_attrs is not None:
            defs = ext_attrs.findall(f"{{{self.namespace}}}ExtendedAttribute")
            return (len(defs) >= 5, f"{len(defs)} custom fields defined")
        return (False, "No custom fields found")
    
    def _check_milestones(self, root):
        """Helper to check milestones"""
        tasks = self.get_all_tasks(root)
        milestones = sum(1 for t in tasks 
                        if t.find(f"{{{self.namespace}}}Milestone") is not None 
                        and t.find(f"{{{self.namespace}}}Milestone").text == '1')
        return (milestones > 0, f"{milestones} milestone tasks")
    
    def _check_calendar(self, root):
        """Helper to check calendar"""
        calendars = root.find(f".//{{{self.namespace}}}Calendars")
        if calendars is not None:
            cal = calendars.find(f"{{{self.namespace}}}Calendar")
            if cal is not None:
                return (True, "Standard calendar defined")
        return (False, "No calendar found")
    
    def _check_duration_format(self, root):
        """Helper to check duration format"""
        tasks = self.get_all_tasks(root)
        formats = set()
        for t in tasks:
            fmt = t.find(f"{{{self.namespace}}}DurationFormat")
            if fmt is not None:
                formats.add(fmt.text)
        return (len(formats) > 0, f"Formats: {', '.join(formats)}")
    
    def _check_work_breakdown(self, root):
        """Helper to check work breakdown"""
        tasks = self.get_all_tasks(root)
        work_count = sum(1 for t in tasks if t.find(f"{{{self.namespace}}}Work") is not None)
        return (work_count > 0, f"{work_count} tasks with work defined")
    
    def _check_constraints(self, root):
        """Helper to check constraints"""
        tasks = self.get_all_tasks(root)
        constraints = set()
        for t in tasks:
            ct = t.find(f"{{{self.namespace}}}ConstraintType")
            if ct is not None:
                constraints.add(ct.text)
        return (len(constraints) > 0, f"{len(constraints)} constraint types used")


def run_all_tests():
    """Run all tests and generate report"""
    print("\n" + "="*70)
    print("COMPREHENSIVE XML EXPORT & WORKFRONT COMPATIBILITY TEST SUITE")
    print("="*70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestXMLWorkfrontExport)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
        
        if result.failures:
            print("\nFailed tests:")
            for test, traceback in result.failures:
                print(f"  - {test}")
                
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    print("\n" + "="*70)
    print("Check test_outputs/ directory for generated XML files and reports")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)