from parallelize_same_name_links import parallelize_same_name_links, makespan_days
import os

def post_process_xml(input_xml_path: str) -> str:
    """
    Post-process XML to parallelize tasks with identical names.
    Returns the path to the processed XML file.
    """
    before = makespan_days(input_xml_path)
    out_path = input_xml_path.replace(".xml", "_PARALLELIZED.xml")
    removed = parallelize_same_name_links(input_xml_path, out_path)
    after = makespan_days(out_path)
    print(f"[XML post-process] removed {removed} same-name links; makespan {before:.1f}d → {after:.1f}d")
    return out_path
