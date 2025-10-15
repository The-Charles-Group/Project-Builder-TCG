#!/usr/bin/env python3
"""Check how many deliverables are available in the database"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the database
from main import AgencyDB
from ai_planner_agencydb import build_catalog_from_agencydb

# Load database
db = AgencyDB()
db.load()

# Build catalog
catalog = build_catalog_from_agencydb(db)

# Count deliverables
deliverables = [x for x in catalog if x["level"] == "deliverable"]
components = [x for x in catalog if x["level"] == "component"]
tasks = [x for x in catalog if x["level"] == "task"]

print(f"Database Statistics:")
print(f"  Total catalog items: {len(catalog)}")
print(f"  Deliverables: {len(deliverables)}")
print(f"  Components: {len(components)}")
print(f"  Tasks: {len(tasks)}")
print()

# Show deliverable codes
print("Available deliverable codes:")
for i, d in enumerate(deliverables[:10], 1):
    print(f"  {i}. {d['id']}: {d['title']} ({d['dept']})")
if len(deliverables) > 10:
    print(f"  ... and {len(deliverables) - 10} more")
print()

# Group by department
by_dept = {}
for d in deliverables:
    dept = d.get("dept", "Unknown")
    if dept not in by_dept:
        by_dept[dept] = []
    by_dept[dept].append(d)

print("Deliverables by department:")
for dept, items in sorted(by_dept.items()):
    print(f"  {dept}: {len(items)} deliverables")