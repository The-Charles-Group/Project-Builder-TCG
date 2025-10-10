# AI Scheduler Kit v2 (Timeline Optimizer)

Added:
- AI_Scheduler_Kit_v2/ (Python package with MSPDI post-processor)
- ai_schedule_postprocess.py (Python CLI)
- scripts/ai_schedule_postprocess.js (Node wrapper)
- AI_SCHEDULER_README.md (how to call)

## Quick use:
```bash
python ai_schedule_postprocess.py exports/latest_project.xml exports/latest_project_OUT.xml exports/gantt.json exports/explanations.json exports/audit.xlsx
```

The _OUT.xml is what you import to Workfront (ASAP constraints, no hard dates, SS+lag overlaps, whole-day durations, Units recomputed).
