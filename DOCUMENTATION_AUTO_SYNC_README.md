
# 📚 Auto-Sync Documentation System

## Overview

This system maintains **living documentation** that automatically updates as your codebase evolves. The documentation is available in two formats:

1. **Markdown** (`MASTER_CONTROL_ROOM.md`) - Human-readable, Git-trackable
2. **Excel** (`MASTER_CONTROL_ROOM.xlsx`) - Spreadsheet format with multiple sheets

## Industry Standard Naming

This type of document is known by several names in the software industry:

- **System Design Document (SDD)** ⭐ (Most common)
- **Software Architecture Document (SAD)**
- **Technical Design Document (TDD)**
- **System Architecture Documentation**
- **Living Documentation** (when auto-updated)

## How Auto-Sync Works

The system monitors key source files for changes:

```
main.py
ai_planner_agencydb.py
ai_timeline_manager.py
ai_weighted_matcher.py
backend/scenario_api.py
static/app.js
static/js/*.js
```

When changes are detected:
1. 🔍 File watcher detects modification (via MD5 hash comparison)
2. ⏱️ Waits 2 seconds for additional changes (debouncing)
3. 📝 Regenerates `MASTER_CONTROL_ROOM.md`
4. 📊 Regenerates `MASTER_CONTROL_ROOM.xlsx`
5. ✅ Logs completion with timestamp

## Usage

### Start Auto-Sync

Run the auto-sync workflow:

```bash
python auto_sync_documentation.py
```

Or use the Replit workflow:
- Click on the workflows dropdown
- Select **"Auto-Sync Documentation"**

### Manual Sync

If you want to manually regenerate documentation:

```bash
# Generate Excel from current Markdown
python convert_md_to_excel.py

# Or generate Google Sheets (one-time)
python convert_md_to_google_sheets.py

# Or enable live Google Sheets sync
python convert_md_to_google_sheets.py --watch
```

## What Gets Tracked

The auto-sync system tracks and updates:

✅ **API Endpoints** - Count and details of all routes  
✅ **Functions & Classes** - Inventory of code components  
✅ **Data Architecture** - Database schemas and structures  
✅ **Component Map** - Frontend and backend component relationships  
✅ **State Management** - How data flows through the system  
✅ **Button-to-Logic Mapping** - UI interactions and their handlers  

## File Locations

- **Source Markdown**: `MASTER_CONTROL_ROOM.md`
- **Excel Export**: `MASTER_CONTROL_ROOM.xlsx`
- **Google Sheets ID**: `.google_sheet_id` (if using Google Sheets sync)

## Benefits

🔄 **Always Current** - Documentation stays in sync with code  
📊 **Multiple Formats** - Markdown for developers, Excel for stakeholders  
🔍 **Version Controlled** - Markdown tracked in Git for history  
⚡ **Zero Manual Work** - Automatic updates as you code  
🎯 **Single Source of Truth** - Code generates documentation, not vice versa  

## Integration with Development Workflow

The auto-sync system integrates seamlessly:

1. **During Development**: Runs in background, updates docs as you code
2. **Code Review**: Reviewers see documentation changes in Git diffs
3. **Onboarding**: New team members get accurate, current docs
4. **Stakeholder Updates**: Export Excel anytime for presentations

## Troubleshooting

**Documentation not updating?**
- Check if auto-sync process is running
- Verify monitored files are being modified
- Check console for error messages

**Excel file locked?**
- Close Excel before regeneration
- Or use Google Sheets for live editing

**Need to customize what's tracked?**
- Edit `MONITORED_FILES` list in `auto_sync_documentation.py`
- Add new metrics in `_extract_metrics()` method

## Best Practices

✅ **Run auto-sync during development** - Keep docs current  
✅ **Commit markdown changes** - Track documentation evolution  
✅ **Review doc diffs in PRs** - Ensure docs match code changes  
✅ **Export Excel for stakeholders** - Share formatted documentation  
✅ **Use Google Sheets for collaboration** - Real-time team access  

---

**Industry Standard Alignment:**

This documentation approach aligns with industry standards like:
- IEEE 1016-2009 (Software Design Descriptions)
- C4 Model (Context, Containers, Components, Code)
- Arc42 (Software Architecture Documentation Template)
- Agile Documentation Principles (Living Documentation)
