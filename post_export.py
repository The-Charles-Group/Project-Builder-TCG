from parallelize_same_name_links import parallelize_same_name_links, makespan_days
import os
import xml.etree.ElementTree as ET
import sys

# Import the fix script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_workfront_xml_hours import fix_workfront_xml_hours, WorkfrontXMLError

def post_process_xml(input_xml_path: str) -> str:
    """
    Post-process XML to:
    1. Parallelize tasks with identical names
    2. Fix Workfront hours (normalize minutes, remove cost back-calcs, correct summary rollups)
    
    Returns the path to the processed XML file.
    """
    # Validate XML is readable before processing
    try:
        ET.parse(input_xml_path)
    except ET.ParseError as e:
        print(f"[XML post-process] XML validation failed: {e}")
        print(f"[XML post-process] Returning original file without processing")
        return input_xml_path
    
    # Step 1: Parallelize same-name tasks
    try:
        before = makespan_days(input_xml_path)
        parallel_path = input_xml_path.replace(".xml", "_PARALLELIZED.xml")
        removed = parallelize_same_name_links(input_xml_path, parallel_path)
        after = makespan_days(parallel_path)
        print(f"[XML post-process] Parallelization: removed {removed} same-name links; makespan {before:.1f}d → {after:.1f}d")
        current_path = parallel_path
    except Exception as e:
        print(f"[XML post-process] Parallelization failed: {e}")
        print(f"[XML post-process] Continuing with original file")
        current_path = input_xml_path
    
    # Step 2: Fix Workfront hours (normalize minutes, remove cost back-calcs, correct summary rollups)
    try:
        print(f"[XML post-process] Fixing Workfront hours...")
        fixed_path = current_path.replace(".xml", "_FIXED.xml")
        
        # Call the fix script function
        fix_workfront_xml_hours(current_path, fixed_path, zero_summary_work=False)
        
        print(f"[XML post-process] Hours fix complete: {fixed_path}")
        return fixed_path
    except WorkfrontXMLError as e:
        print(f"[XML post-process] Hours fix failed (validation error): {e}")
        print(f"[XML post-process] Returning parallelized file")
        return current_path
    except Exception as e:
        print(f"[XML post-process] Hours fix failed (unexpected error): {e}")
        print(f"[XML post-process] Returning parallelized file")
        return current_path
