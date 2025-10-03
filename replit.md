# Agency Project Builder

## Overview

This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### Project Start Date & Budget Features (October 2025)
- **Feature A - Project Start Date**: Added user-settable project start date for Workfront XML exports
  - Frontend: Date-time picker in Step 3 with ISO8601 format, defaults to next Monday at 9:00 AM
  - Backend: Updated API models and endpoints to accept `project_start_iso` parameter
  - XML Export: `convert_excel_to_mspdi` now writes user-specified start date to Project StartDate element
  
- **Feature B - Duration Display**: Task durations now display as days in Workfront
  - All tasks use DurationFormat=7 (Days) in XML export
  - Parent tasks properly marked with Summary=1 to distinguish from leaf tasks
  
- **Feature C - Fixed Duration Tasks**: Application timeline now matches Workfront duration exactly
  - Leaf tasks set as Fixed Duration (Type=1) with IsEffortDriven=0
  - Assignment Units calculated as work_minutes / duration_minutes for proper resource loading
  - Non-root tasks use ASAP constraints (ConstraintType=0) for flexible scheduling
  
- **Feature D - Client Budget Tracking**: Added budget comparison and metrics
  - Frontend: Client budget input field with over/under budget display
  - Backend: Per-scenario budget metrics (coverage_pct, budget_delta, scale_factor)
  - Each scenario calculates its own budget metrics independently
  
- **Bug Fix - ISO8601 Date Parsing**: Fixed "Internal Server Error" when building scenarios
  - Updated `build_schedule()` to handle ISO8601 timestamps (e.g., "2025-10-07T01:00:00.000Z")
  - Extracts date portion before parsing to support both ISO8601 and simple date formats
  - Prevents ValueError: "unconverted data remains" error

- **XML Project Name & Summary Task Fixes**: Corrected MSPDI project naming and root task structure
  - **Project Name**: XML <Project><Name> now uses user-entered project name (from Step 3) instead of "Scenario A/B"
  - **Name Derivation**: Extracts project title from root WBS row (WBS_ID "1") Task_Name, with fallback to Project_Name column
  - **Root Task**: First task row is now a proper Project Summary task with Summary=1, PT0M Work/Duration
  - **WBS DataFrame**: Root row now has Planned_Hours=0 and Duration_Days=0 (not empty strings)
  - **Workfront Display**: Workfront header now shows the actual project name, with clean roll-up from child tasks

### GPT-5 Patches Implementation (October 2025)
- **Backend Enhancements**:
  - Added component inflation at start of `build_wbs_with_pricing()` to ensure AI picks always include full component trees
  - Implemented 480-minute (8-hour day) duration snapping for Workfront compatibility: `((minutes + 479) // 480) * 480`
  - Verified XML export hierarchy with Summary=1 for parents, OutlineLevel based on WBS depth, and no assignments on summary tasks
  - Confirmed retainer months properly multiply hours/price/duration through month-by-month repetition

- **Frontend Enhancements**:
  - Added project name auto-fill from `/api/last_upload_name` endpoint after AI analysis
  - Fixed `selected_components_map` payload in `s2ApplyAndBuild()` to properly send `"__ALL__"` sentinel for non-customized deliverables
  - Ensured consistent `"__ALL__"` sentinel handling between `buildFromCurrentSelection()` and `s2ApplyAndBuild()`
  - Verified AI spinner, search functionality, and component defaults all working correctly
  - Implemented "Refresh AI Suggestions" link to call `/api/suggest_by_text` using stored RFP text without re-upload
  - Enhanced AI Summary panel with Copy button (clipboard), Hide/Show toggle, and refresh functionality

- **Key Improvements**:
  - Prevents flat exports by ensuring all deliverables have component data before WBS building
  - Workfront-compatible durations eliminate fractional day display (e.g., "1.875d" now shows as "2d")
  - Project names auto-populate from uploaded filename without overriding user input
  - Component selection payload format matches backend expectations for proper inflation

### Component Selection Modal Fixes (October 2025)
- **Fixed TypeError Bug**: Resolved `current.has is not a function` error when opening component picker
  - Added type checking to handle `"__ALL__"` sentinel, Set objects, plain objects, and undefined values
  - Converts stored component selections to Set when opening modal
  - Defaults to all components selected when opening modal for first time or with `"__ALL__"` sentinel

- **Added Select All/Unselect All Buttons**: Enhanced component picker modal with bulk selection controls
  - Added "Select All" button to check all component checkboxes at once
  - Added "Unselect All" button to clear all component checkboxes
  - Both buttons update the internal `selectedComponentsMap` state in real-time
  - Modal now includes: title bar with Done button, Select All/Unselect All row, scrollable component list

- **Default Behavior**: Components are now pre-selected by default when opening the modal
  - Improves user experience by showing all components checked initially
  - User can then unselect specific components if needed
  - Aligns with `"__ALL__"` sentinel pattern used throughout the application

### Defensive Component Selection Handling (October 2025)
- **Backend Sanitization in /api/build**: Enhanced component map processing to prevent invalid hours
  - Treats hours <= 0 as "unselected" and drops them from component selection
  - Preserves None values to signal "use default hours for this component"
  - Prevents accidental "all selected but all at 0h" payloads from reaching calculations

- **Zero-Hours Fallback in _scenario_for_deliverable**: Added safety net for component selections
  - If selected components total 0 hours after scaling, automatically falls back to deliverable-level defaults
  - Prevents zeroed deliverables from appearing in scenarios due to invalid component selections
  - Logs fallback events for debugging: "component selection totals 0h -> fallback to deliverable defaults"

- **WBS Export Guard**: Enhanced export robustness to handle edge cases
  - Extended empty-hours check to also catch hours_by_role that totals 0
  - Recomputes from database when hours sum is 0 or less
  - Makes XML exports resilient even if older scenarios contain 0-hour items

- **Sentinel State Management**: Fixed frontend to delete map keys when all components selected
  - Select All now deletes the deliverable key instead of storing "__ALL__" string
  - Prevents invalid `{'__ALL__': null}` payloads that would drop all tasks
  - Proper transitions: all selected (key deleted) → partial (object map) → none (empty object)

### AI-Suggested Items & Department Grouping Fixes (October 2025)
- **Scenario Column Validation**: Enhanced scenario_col resolution in build_wbs_with_pricing
  - Validates scenario_col exists in database columns before using it
  - Falls back to deriving from complexity & tier when missing or invalid
  - Applied to both "enrich items" pass and deliverable processing loop
  - Ensures AI-suggested items align with valid hour columns

- **V3 Department Inference Priority**: Updated all department lookups to prefer v3 methods
  - Deliverable level: Calls `service_department_for_deliverable` (v3) before `service_dept_for_deliverable` (v2)
  - Component level: Calls `service_department_for_component` (v3) before `service_dept_for_component` (v2)
  - Task level: Calls `service_department_for_task` (v3) before v2 fallback
  - V3 methods don't require scenario_col parameter, preventing "Other" department collapse for AI items

- **Benefits**:
  - AI-suggested deliverables now properly grouped by Service Department in exports
  - Prevents all AI items from defaulting to "Other" department
  - Maintains backward compatibility with v2 methods as fallback

## System Architecture

### Backend Architecture
- **Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data, calculations, and manipulations.
- **File Handling**: Supports parsing of PDF and DOCX documents, and Excel file uploads.
- **CORS**: Configured to allow cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow.
- **Styling**: Uses CSS custom properties for theming, including a dark mode.
- **State Management**: Client-side caching for options and scenario data.

### Data Storage Pattern
- **Primary Storage**: Excel/CSV files serve as the main source for business rules and configuration data.
- **Data Models**: In-memory DataFrames are loaded from spreadsheets to define tasks, deliverables, pricing rules, rate cards, timeline parameters, scaling factors, bundle configurations, hour allocations, and scenario templates.

### Core Business Logic
- **RFP Analysis**: Extracts key information from RFPs to suggest deliverables.
- **Scenario Building**: Generates project scenarios with varying complexity and tier combinations.
- **Pricing Engine**: Calculates costs using blended or role-based rate bands.
- **Timeline Calculation**: Determines project duration, incorporating configurable slack.
- **Export Capability**: Generates Workfront-compatible project structures.

### API Design
- Provides RESTful endpoints for data loading, options retrieval, and scenario generation.
- Supports file uploads for RFP documents and Excel configuration files.
- Uses JSON for configuration data and calculated scenario responses.
- Serves static files for frontend assets.

## External Dependencies

### Python Libraries
- **FastAPI**: Web framework.
- **Pandas**: Data manipulation and analysis.
- **NumPy**: Numerical operations.
- **OpenPyXL**: Excel file processing.
- **PDFPlumber**: PDF text extraction.
- **python-docx**: Word document processing.
- **Jinja2**: Template engine.
- **Uvicorn**: ASGI server.

### File Format Support
- **Excel/CSV**: Core data source.
- **PDF/DOCX**: For RFP document parsing.
- **JSON**: For API data exchange.

### Deployment Requirements
- **Static File Serving**: Handled by FastAPI.
- **File Upload Handling**: Processes multipart form data.
- **Cross-Origin Support**: Utilizes CORS middleware.