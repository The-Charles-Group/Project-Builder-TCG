# Agency Project Builder

## Overview

This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (October 2025)

### Single-Scenario Refactoring (Latest - October 9, 2025)
- **Complete Removal of Scenarios B and C**: Simplified the entire application to focus on Scenario A only
  - Backend: Removed B/C from SCENARIO_MULT, Pydantic models, and /api/build loop
  - Frontend: Removed all B/C rendering, export handlers, and event listeners
  - /api/build now returns only `{scenarios: {A: {...}}}`
  - Steps 3, 4, 5 display and export only Scenario A
  - Removed buildScenarioC, renderUpsellList, and all multi-scenario export functions
  - Cleaner UX with single-scenario focus throughout Steps 1-5
- **Architect Review**: ✅ Complete - all B/C references removed, single-scenario contract verified

### Compatibility Wrapper & Response Format Update (October 9, 2025)
- **Backend Compatibility Wrapper**: /api/build now returns both old and new response formats
  - New format: `{ok: true, scenarios: {A, B}, ...}`
  - Old format: Top-level A/B keys preserved for backward compatibility
  - Single response contains both formats using Python dict unpacking `**scenarios`
- **Frontend Defensive Parsing**: buildFromCurrentSelection() handles both response shapes
  - Extracts scenarios from json.scenarios OR constructs from {A: json.A, B: json.B}
  - Validates A and B exist before proceeding
  - Maintains legacy state variables (window.BUILD, window.latestScenarios, etc.)
- **New GET /api/scenarios**: Helper endpoint to refetch scenarios from server memory
  - Useful for Step 4 recovery if client has transient parsing issues
  - Returns `{ok: true, scenarios: {...}}`
- **Smoke Test Results**: All features verified working
  - ✅ Response includes both formats (scenarios.A == A verified)
  - ✅ Pricing accurate (Scenario A: $5,735/31hrs, B: $8,695/54hrs)
  - ✅ Schedule data embedded in deliverable items
  - ✅ XML export generates 874 lines of valid MSPDI
  - ✅ Backward compatibility maintained

### v3 Database Compatibility Fix (October 9, 2025)
- **Complete v3 Database Support**: Fixed all "NoneType object is not subscriptable" errors caused by missing sheets in v3 database
  - Added None checks for timeline_weighting, timeline_scaling, b_defaults, and scenario_templates
  - Default fallback values: wc=0.6, wt=0.4, cmult=1.0, tmult=1.0 for timeline calculations
  - All endpoints now work correctly with v3-only database structure
- **"Proceed to Pricing" Button Fixed**: Resolved 500 Internal Server Error in Step 3
  - /api/build endpoint now handles missing v3 sheets gracefully
  - Pricing calculations verified working: $5,735 for 31 hours test case
- **XML Export Verified**: Timeline and export functionality fully operational
  - /api/export/xml/a generates valid Workfront-compatible MSPDI XML
  - Business day calendars with US/MX holidays working correctly
  - XML post-processing optimizes parallel tasks (e.g., 28d → 21d makespan reduction)
- **End-to-End Testing**: Complete smoke test of Steps 1-5 confirms all features functional

### GPT-5 Pro AI Matching Integration (October 9, 2025)
- **1,583 AI Matching Rules**: Integrated comprehensive AI_Matching_Rules_full.xlsx database with admin-configurable matching rules
  - Covers all L1 (deliverables), L2 (components), and L3 (subtasks) with keyword matching
  - Priority scoring and auto-include related components
  - Configurable weights: rule-based (60%) + lexical TF-IDF (40%)
- **Weighted Scoring API**: New `/api/step2/ai/weights` endpoint provides 0-100% match percentages
  - Returns Service Department → Deliverable → Match % with detailed explanations
  - Example: "Paid Media Buying & Activation" correctly scores 97.38% for paid media RFPs
- **Interactive AI Suggestions Panel**: Enhanced UI for deliverable recommendations with full user control
  - Purple gradient button "🤖 Ask AI for Deliverable Suggestions"
  - Checkboxes for selective application (shows already-selected items grayed out)
  - "Select All" and "Select Top 3" quick actions
  - "Apply Selected Deliverables" button batch-adds selections via APB.step2.addDeliverables()
  - Real-time selection counter (e.g., "3 of 8 selected")
  - Weighted match results table shows Service Dept → Deliverable → Match % with expandable components/tasks
- **GPT-5 Pre-filter Enhancement**: Auto-suggest now uses weighted rules for improved accuracy
  - When deliverable selected, first calls `/api/step2/ai/weights` for rule-based context
  - Extracts top components and tasks as weighted_context
  - Passes weighted_context to GPT-5 with PRIORITY instruction highlighting top 3 components
  - Response includes `used_weighted_prefilter: true` flag when context applied
  - Reduces GPT-5 API costs by providing better targeting context
- **Step 2A Labeling**: Bottom section renamed to "Step 2A: Detail Review & Selection" with visual separator

### UI & Export Quality Improvements (October 8, 2025)
- **Deliverable Selection UX**: Row click now previews only (shows components if already selected); checkbox is sole source of truth for selection
- **XML Anchor Milestones**: Made optional with UI toggle in Step 2 Summary panel
  - Checkbox control: "Include Start/End anchors in XML" (default unchecked)
  - When enabled: START/END anchors use friendly names `Start — {Deliverable}` / `End — {Deliverable}` with `<Milestone>1</Milestone>` tags
  - Safe fallback prevents [nan] labels by using `safe_dcode` instead of raw deliverable code
  - Backend parameter: `add_deliverable_milestones` (default False) in `convert_excel_to_mspdi()` and export endpoints
- **L3 Task Restoration**: Component reselection now clears cache and refetches L3 from server, allowing removed L3 subtasks to be re-added
  - Added "↻ Reset" button next to each component in Summary panel for instant L3 restoration without needing to toggle component off/on
- **Summary Count Accuracy**: L3 count now only includes tasks for selected components (checks both deliverable AND component selection)
- **XML Export Integration**: Export buttons read checkbox state and pass `?add_anchors=true/false` to API endpoints

### Step 2 UI Restructure
- **Simplified Grid**: Changed from 4-column to 3-column layout (Deliverables | Components | Summary)
  - Removed dedicated L3 Subtasks column
  - L3 selection now handled within Summary panel for each component
  - Grid template updated to `1fr 1fr 350px` for better spacing
- **Search Functionality**: Search bars for Deliverables and Components filter the lists in real-time
- **Enhanced Summary**: Shows hierarchical Deliverable → Component → L3 structure with per-component controls

### L3 Bulk Query Endpoints
- **New Endpoint `/api/step2/l3/bulk`**: Returns L3 tasks grouped by component for efficient UI rendering
  - Input: `{"deliverable": "code", "components": ["comp1", "comp2"]}`
  - Output: `{"comp1": ["task1", "task2"], "comp2": ["task3"]}`
  - Preserves component grouping for summary panel display
- **Enhanced `/api/step2/l3`**: Now accepts both single component (string) or multiple components (array)
  - Returns merged, deduplicated L3 tasks
  - Fully backward compatible with existing callers

### Critical L3 Synchronization Fix
- **Issue**: L3 (Level 3) selections from Step 2 UI were not reaching Step 3 payload due to data synchronization problems between legacy code paths and the centralized state store.
- **Solution**: Implemented a Proxy-backed `selectedL3ByKey` object that intercepts all property operations (get, set, delete, enumerate) and synchronizes with `selectionStore.l3ByComponent` Map.
- **Implementation**: 
  - Lines 66-100 in app.js: Proxy with comprehensive traps for all operations
  - Lines 103-121 in app.js: Locked property definition to prevent accidental reassignment
  - Ensures all read/write paths use a single source of truth

### Enhanced Summary Panel
- **Feature**: Column 4 now displays hierarchical Deliverable → Component → L3 structure
- **Functionality**: Individual remove buttons for each level with cascading deletion
- **UI**: L3 chips grouped by parent component for clear visualization

### AI Suggest Features (Latest - October 8, 2025)
- **GPT-5 Auto-Suggest on Selection**: Automatically suggests components when a deliverable is selected
  - Enabled via `USE_GPT_FOR_AUTOSUGGEST = true` constant (uses GPT-5 if true, rules-based if false)
  - Endpoint: `/api/step2/ai/suggest` - GPT-5 analyzes RFP and deliverable catalog to suggest components and L3 tasks
  - Only triggers for deliverables with no components yet
  - Auto-selects top 6 relevant components and hydrates GPT-curated L3 tasks
  - Displays suggestions with reasoning in AI panel (`#ai-suggest-panel`)
  - Graceful fallback: If OpenAI unavailable, uses rules-based algorithm (frequency + RFP keyword overlap)
  - Rehydrated sessions (with existing selections) skip auto-suggest
- **AI Panel UI**: Shows GPT-5 suggestions with reasoning and action buttons
  - Source indicator: "GPT-5 (gpt-5)" or "Rules"
  - Component suggestions: Shows component name + why it was suggested
  - L3 task suggestions: Grouped by component with per-task reasoning
  - Action buttons: "Apply All" (adds to existing) and "Replace Current" (clears first)
  - Optional rationale summary from GPT-5
- **Manual Component Suggestions**: "Suggest" button in Components panel for manual suggestions
  - Endpoint: `/api/step2/suggest/components` - scores components by frequency + RFP keyword overlap
  - Auto-selects suggested components and hydrates their L3 tasks
  - Limit: Returns top 6 most relevant components
- **L3 Task Suggestions**: Per-component suggest functionality for L3 subtasks
  - Endpoint: `/api/step2/suggest/l3` - ranks tasks by frequency + RFP relevance
  - Global deduplication: Excludes tasks already selected across all deliverables/components
  - Merges suggestions into existing L3 selections

### Timeline Accuracy Improvements
- **Business Days Calculation**: Uses `numpy.busday_offset()` and `numpy.busday_count()` with US/MX holiday calendar
- **Memorial Day Fix**: Corrected calculation to always land on the last Monday of May
- **XML Export**: Saturday and Sunday configured as non-working days (DayWorking=0) in Workfront-compatible calendar export
- **No Weekend End Dates**: All timeline calculations exclude weekends and holidays

## System Architecture

### Backend Architecture
- **Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data, calculations, and manipulations.
- **File Handling**: Supports parsing of PDF and DOCX documents, and Excel file uploads.
- **Core Logic**: Implements RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **CORS**: Configured to allow cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow.
- **Styling**: Uses CSS custom properties for theming, including a dark mode.
- **State Management**: Centralized `selectionStore` as single source of truth with Proxy-backed compatibility layer for legacy code paths.

### Data Storage Pattern
- **Primary Storage**: Excel/CSV files serve as the main source for business rules and configuration data.
- **Data Models**: In-memory DataFrames are loaded from spreadsheets to define tasks, deliverables, pricing rules, rate cards, timeline parameters, scaling factors, bundle configurations, hour allocations, and scenario templates.

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