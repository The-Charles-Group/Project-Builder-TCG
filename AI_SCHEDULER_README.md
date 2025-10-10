# How to invoke the AI Scheduler

After your export writes Microsoft Project XML (MSPDI):

## Python call (inside your code):
```python
from AI_Scheduler_Kit_v2.src.orchestrator import run_pipeline

run_pipeline(
  xml_in="exports/latest_project.xml",
  xml_out="exports/latest_project_OUT.xml",
  gantt_json="exports/gantt.json",
  explanations_json="exports/explanations.json",
  excel_out="exports/audit.xlsx",
  changes=None,
  ai_callable=None,
  round_policy="ceil"
)
```

## Shell call (post-process step):
```bash
python ai_schedule_postprocess.py exports/latest_project.xml exports/latest_project_OUT.xml exports/gantt.json exports/explanations.json exports/audit.xlsx
```

## Node wrapper:
```bash
node scripts/ai_schedule_postprocess.js exports/latest_project.xml exports/latest_project_OUT.xml exports/gantt.json exports/explanations.json exports/audit.xlsx
```

The `_OUT.xml` is what you import to Workfront (ASAP constraints, no hard dates, SS+lag overlaps, whole-day durations, Units recomputed).

## Features:
- **Automatic SS+lag overlaps**: Converts FS dependencies to SS with lag based on predefined rules
- **Gatekeeper preservation**: Keeps review/approval chains intact
- **Cycle breaking**: Automatically resolves circular dependencies
- **Duration rounding**: Rounds to whole days
- **Units recalculation**: Recomputes resource units based on work and duration
- **Gantt JSON export**: Generates timeline data for visualization
- **Audit Excel**: Creates detailed audit trail with task hierarchy and assignments
