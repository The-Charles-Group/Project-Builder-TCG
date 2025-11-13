#!/usr/bin/env python3
"""
Fix Workfront XML hours by normalizing minutes, removing cost back-calculations,
and correcting summary task Work rollups.

This script processes Microsoft Project XML files to ensure:
1. Project uses 8-hour day settings (480 min/day, 2400 min/week)
2. Cost fields are removed to prevent Work back-calculation
3. Summary task Work equals sum of leaf descendant Work values
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Set, Optional


# Microsoft Project namespace
NS = "{http://schemas.microsoft.com/project}"


class WorkfrontXMLError(Exception):
    """Custom exception for Workfront XML processing errors."""
    pass


def parse_work_minutes(work_text: Optional[str]) -> int:
    """
    Parse ISO8601 duration format to minutes.
    Handles: PT3480M, PT8H0M0S, PT8H, PT0M, etc.
    Returns 0 if missing or invalid.
    """
    if not work_text:
        return 0
    try:
        # Remove PT prefix
        work_text = work_text.strip()
        if not work_text.startswith("PT"):
            return 0
        
        remaining = work_text[2:]  # Skip "PT"
        
        hours = 0
        minutes = 0
        seconds = 0
        
        # Parse hours
        if "H" in remaining:
            h_idx = remaining.index("H")
            hours = int(remaining[:h_idx]) if remaining[:h_idx] else 0
            remaining = remaining[h_idx + 1:]
        
        # Parse minutes
        if "M" in remaining:
            m_idx = remaining.index("M")
            minutes = int(remaining[:m_idx]) if remaining[:m_idx] else 0
            remaining = remaining[m_idx + 1:]
        
        # Parse seconds (ignore for minute calculation)
        if "S" in remaining:
            s_idx = remaining.index("S")
            seconds = int(remaining[:s_idx]) if remaining[:s_idx] else 0
        
        # Convert to total minutes (ignore seconds)
        return hours * 60 + minutes
    except (ValueError, AttributeError):
        return 0


def format_work_minutes(minutes: int) -> str:
    """Format minutes as ISO8601 duration (PT{minutes}M)."""
    return f"PT{minutes}M"


class TaskNode:
    """Represents a task in the WBS hierarchy."""
    def __init__(self, uid: int, elem: ET.Element):
        self.uid = uid
        self.elem = elem
        self.children: List['TaskNode'] = []
        self.wbs = ""
        self.outline_level = 0
        self.is_summary = False
        self.name = ""
        self.work_minutes = 0
        
        # Parse task properties
        wbs_elem = elem.find(f"{NS}WBS")
        self.wbs = wbs_elem.text if wbs_elem is not None and wbs_elem.text else ""
        
        level_elem = elem.find(f"{NS}OutlineLevel")
        self.outline_level = int(level_elem.text) if level_elem is not None and level_elem.text else 0
        
        summary_elem = elem.find(f"{NS}Summary")
        self.is_summary = summary_elem is not None and summary_elem.text == "1"
        
        name_elem = elem.find(f"{NS}Name")
        self.name = name_elem.text if name_elem is not None and name_elem.text else ""
        
        work_elem = elem.find(f"{NS}Work")
        self.work_minutes = parse_work_minutes(work_elem.text if work_elem is not None else "")


def build_task_tree(tasks: List[ET.Element]) -> Dict[int, TaskNode]:
    """
    Build task tree from flat list using UID and WBS hierarchy.
    Returns dict mapping UID to TaskNode.
    """
    uid_to_node: Dict[int, TaskNode] = {}
    
    # First pass: create all nodes
    for task_elem in tasks:
        uid_elem = task_elem.find(f"{NS}UID")
        if uid_elem is None or not uid_elem.text:
            continue
        
        uid = int(uid_elem.text)
        node = TaskNode(uid, task_elem)
        uid_to_node[uid] = node
    
    # Second pass: build parent-child relationships using WBS
    for uid, node in uid_to_node.items():
        if not node.wbs:
            continue
        
        # Find parent by checking if another task's WBS is a prefix
        # Parent WBS is node.wbs with last segment removed
        wbs_parts = node.wbs.split(".")
        if len(wbs_parts) > 1:
            parent_wbs = ".".join(wbs_parts[:-1])
            
            # Find task with this parent WBS
            for candidate_uid, candidate_node in uid_to_node.items():
                if candidate_node.wbs == parent_wbs:
                    candidate_node.children.append(node)
                    break
    
    return uid_to_node


def rollup_work_recursive(node: TaskNode, uid_to_node: Dict[int, TaskNode]) -> int:
    """
    Post-order traversal: calculate work for this node.
    - Leaf tasks: return their own Work
    - Summary tasks: return sum of all descendant leaf Work
    """
    if not node.is_summary:
        # Leaf task: return its work
        return node.work_minutes
    
    # Summary task: sum children
    total_work = 0
    for child in node.children:
        total_work += rollup_work_recursive(child, uid_to_node)
    
    return total_work


def fix_workfront_xml_hours(input_path: str, output_path: str, zero_summary_work: bool = False):
    """
    Main processing function.
    
    Args:
        input_path: Path to input XML file
        output_path: Path to output fixed XML file
        zero_summary_work: If True, set summary Work to PT0M instead of rollups
    """
    print(f"[INFO] Parsing XML from: {input_path}")
    
    try:
        # Parse XML with namespace preservation
        ET.register_namespace('', 'http://schemas.microsoft.com/project')
        tree = ET.parse(input_path)
        root = tree.getroot()
    except Exception as e:
        error_msg = f"Failed to parse XML: {e}"
        print(f"[ERROR] {error_msg}")
        raise WorkfrontXMLError(error_msg)
    
    print("[INFO] XML parsed successfully")
    
    # Step 1: Ensure project-level sanity
    print("[INFO] Checking project-level settings...")
    
    minutes_per_day = root.find(f"{NS}MinutesPerDay")
    if minutes_per_day is None:
        minutes_per_day = ET.SubElement(root, f"{NS}MinutesPerDay")
        minutes_per_day.text = "480"
        print("[INFO] Added MinutesPerDay=480")
    elif minutes_per_day.text != "480":
        print(f"[WARN] MinutesPerDay was {minutes_per_day.text}, setting to 480")
        minutes_per_day.text = "480"
    
    minutes_per_week = root.find(f"{NS}MinutesPerWeek")
    if minutes_per_week is None:
        minutes_per_week = ET.SubElement(root, f"{NS}MinutesPerWeek")
        minutes_per_week.text = "2400"
        print("[INFO] Added MinutesPerWeek=2400")
    elif minutes_per_week.text != "2400":
        print(f"[WARN] MinutesPerWeek was {minutes_per_week.text}, setting to 2400")
        minutes_per_week.text = "2400"
    
    work_format = root.find(f"{NS}WorkFormat")
    if work_format is None:
        work_format = ET.SubElement(root, f"{NS}WorkFormat")
        work_format.text = "2"
        print("[INFO] Added WorkFormat=2 (minutes)")
    elif work_format.text != "2":
        print(f"[WARN] WorkFormat was {work_format.text}, setting to 2 (minutes)")
        work_format.text = "2"
    
    # Step 2: Remove cost back-calculation fields
    print("[INFO] Removing cost back-calculation fields...")
    
    tasks_container = root.find(f"{NS}Tasks")
    if tasks_container is None:
        error_msg = "No Tasks container found in XML"
        print(f"[ERROR] {error_msg}")
        raise WorkfrontXMLError(error_msg)
    
    tasks = tasks_container.findall(f"{NS}Task")
    cost_removed = 0
    fixed_cost_removed = 0
    revenue_removed = 0
    
    for task in tasks:
        # Remove Cost element
        cost_elem = task.find(f"{NS}Cost")
        if cost_elem is not None:
            task.remove(cost_elem)
            cost_removed += 1
        
        # Remove FixedCost element
        fixed_cost_elem = task.find(f"{NS}FixedCost")
        if fixed_cost_elem is not None:
            task.remove(fixed_cost_elem)
            fixed_cost_removed += 1
        
        # Remove Revenue ExtendedAttribute (FieldID 188743715)
        ext_attrs = task.findall(f"{NS}ExtendedAttribute")
        for ext_attr in ext_attrs:
            field_id = ext_attr.find(f"{NS}FieldID")
            if field_id is not None and field_id.text == "188743715":
                task.remove(ext_attr)
                revenue_removed += 1
    
    print(f"[INFO] Removed {cost_removed} Cost elements")
    print(f"[INFO] Removed {fixed_cost_removed} FixedCost elements")
    print(f"[INFO] Removed {revenue_removed} Revenue ExtendedAttributes")
    
    # Step 3: Build task tree and calculate leaf work before changes
    print("[INFO] Building task tree...")
    uid_to_node = build_task_tree(tasks)
    print(f"[INFO] Found {len(uid_to_node)} tasks")
    
    # Calculate total leaf work BEFORE changes
    total_leaf_work_before = 0
    leaf_count = 0
    summary_count = 0
    
    for node in uid_to_node.values():
        if not node.is_summary:
            total_leaf_work_before += node.work_minutes
            leaf_count += 1
            
            # Validate leaf work is not negative or NaN
            if node.work_minutes < 0:
                error_msg = f"Leaf task UID={node.uid} '{node.name}' has negative Work: {node.work_minutes}"
                print(f"[ERROR] {error_msg}")
                raise WorkfrontXMLError(error_msg)
        else:
            summary_count += 1
    
    print(f"[INFO] Found {leaf_count} leaf tasks, {summary_count} summary tasks")
    print(f"[INFO] Total leaf work BEFORE: {total_leaf_work_before} minutes ({total_leaf_work_before / 60:.2f} hours)")
    
    # Step 4: Roll up work from leaf to summary tasks
    print("[INFO] Rolling up Work from leaf to summary tasks...")
    
    summary_changes = []
    
    for uid, node in uid_to_node.items():
        if not node.is_summary:
            continue  # Skip leaf tasks
        
        # Calculate rolled-up work
        old_work_minutes = node.work_minutes
        
        if zero_summary_work:
            new_work_minutes = 0
        else:
            new_work_minutes = rollup_work_recursive(node, uid_to_node)
        
        old_work_hours = old_work_minutes / 60
        new_work_hours = new_work_minutes / 60
        delta_hours = new_work_hours - old_work_hours
        
        # Update Work element
        work_elem = node.elem.find(f"{NS}Work")
        if work_elem is not None:
            work_elem.text = format_work_minutes(new_work_minutes)
        else:
            work_elem = ET.SubElement(node.elem, f"{NS}Work")
            work_elem.text = format_work_minutes(new_work_minutes)
        
        # Update RegularWork if exists
        regular_work_elem = node.elem.find(f"{NS}RegularWork")
        if regular_work_elem is not None:
            regular_work_elem.text = format_work_minutes(new_work_minutes)
        
        # Update RemainingWork if exists
        remaining_work_elem = node.elem.find(f"{NS}RemainingWork")
        if remaining_work_elem is not None:
            remaining_work_elem.text = format_work_minutes(new_work_minutes)
        
        summary_changes.append({
            'uid': uid,
            'name': node.name,
            'old_h': old_work_hours,
            'new_h': new_work_hours,
            'delta_h': delta_hours
        })
    
    # Calculate total leaf work AFTER changes (should be unchanged)
    total_leaf_work_after = 0
    for node in uid_to_node.values():
        if not node.is_summary:
            # Re-read from XML to verify
            work_elem = node.elem.find(f"{NS}Work")
            work_minutes = parse_work_minutes(work_elem.text if work_elem is not None else "")
            total_leaf_work_after += work_minutes
            
            # Validate again
            if work_minutes < 0:
                error_msg = f"Leaf task UID={node.uid} '{node.name}' has negative Work after changes: {work_minutes}"
                print(f"[ERROR] {error_msg}")
                raise WorkfrontXMLError(error_msg)
    
    print(f"[INFO] Total leaf work AFTER: {total_leaf_work_after} minutes ({total_leaf_work_after / 60:.2f} hours)")
    
    if total_leaf_work_before != total_leaf_work_after:
        print(f"[WARN] Leaf work changed! Before: {total_leaf_work_before}, After: {total_leaf_work_after}")
    
    # Print summary changes
    print("\n[INFO] Summary task Work changes:")
    print(f"{'UID':<8} {'Name':<50} {'Old Hours':<12} {'New Hours':<12} {'Delta Hours':<12}")
    print("-" * 100)
    
    for change in summary_changes:
        print(f"{change['uid']:<8} {change['name']:<50} {change['old_h']:<12.2f} {change['new_h']:<12.2f} {change['delta_h']:<12.2f}")
    
    # Step 5: Write output XML
    print(f"\n[INFO] Writing fixed XML to: {output_path}")
    
    try:
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        print("[INFO] XML written successfully")
    except Exception as e:
        error_msg = f"Failed to write XML: {e}"
        print(f"[ERROR] {error_msg}")
        raise WorkfrontXMLError(error_msg)
    
    print(f"\n[SUCCESS] Processing complete!")
    print(f"[SUCCESS] Total leaf tasks: {leaf_count} ({total_leaf_work_after / 60:.2f} hours)")
    print(f"[SUCCESS] Summary tasks updated: {len(summary_changes)}")


def main():
    parser = argparse.ArgumentParser(
        description="Fix Workfront XML hours by normalizing minutes, removing cost back-calculations, and correcting summary rollups"
    )
    parser.add_argument('--in', dest='input', required=True, help='Path to input XML file')
    parser.add_argument('--out', dest='output', required=True, help='Path to output fixed XML file')
    parser.add_argument(
        '--zero-summary-work',
        dest='zero_summary_work',
        action='store_true',
        help='Set all summary task Work to PT0M instead of rollups (some PMOs prefer tools to compute rollups themselves)'
    )
    
    args = parser.parse_args()
    
    try:
        fix_workfront_xml_hours(args.input, args.output, args.zero_summary_work)
    except WorkfrontXMLError as e:
        print(f"\n[FATAL] {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
