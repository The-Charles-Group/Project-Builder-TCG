# Agency Project Builder

## Overview
This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- Single-page application with a step-based workflow.
- Uses CSS custom properties for theming, including a dark mode.
- 3-column layout (Deliverables | Components | Summary) with search functionality and enhanced summary panel.
- Unified AI Planner UI with real-time progress bar, evidence-backed suggestions, and risk indicators.
- UI toggle for optional inclusion of Start/End anchor milestones in XML exports.

### Technical Implementations
- **Backend Framework**: FastAPI (Python).
- **Data Processing**: Pandas DataFrames for Excel/CSV data; PDFPlumber and python-docx for RFP parsing.
- **Core Logic**: RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **SCENARIO_STORE Architecture**: Dual-entry session-based data store with immutable `baseline` and mutable `working` scenarios, with PostgreSQL persistence.
- **AI Planner v3**: Advanced reasoning-based AI layer (GPT-5 + AgencyDB) for granular task selection and holistic project flow analysis.
- **GPT 5.1 Pro Enhancements**: Structured RFP summaries, curated L3 task selection, and consistent Gantt/XML export. Includes specific logic for first L2 deliverable SNET constraint and child-task dependency filtering.
- **Timeline Scheduler Kit**: AI-powered timeline optimization with Microsoft Project XML parsing, smart dependencies, and multi-format export.
- **Workfront Integration**: Exports a 3-Level Workfront Hierarchy (Deliverable → Component → Task) with WBS codes and manual scheduling tags. Includes features for Gantt timeline date preservation and manual scheduling lock.
- **PM-Brain Capacity Scheduling**: Capacity-based timeline scheduling with resource leveling and realistic dependencies.
- **WBS-Based Dependencies + Multi-Assignment Export**: Feature-flagged system for dependency management and parallel role execution.
- **Chronological Waterfall Export**: Production-ready XML export system creating simple, chronological Gantt timelines in Workfront, flattening the WBS hierarchy to prioritize chronological flow over department grouping.
- **Tight Waterfall Scheduling System**: Feature-flagged L2 deliverable scheduling that eliminates work-wait-work gaps in Workfront using specific ConstraintType and DurationFormat settings.
- **Unified Pricing Data Flow**: Ensures the backend is the single source of truth for all pricing operations through a `syncScenarioToBackend()` and `rebuildPricingFromBackend()` pipeline.
- **GPT 5.1 Pro Step 3 Pricing Edit Preservation**: Preserves user edits to hours/rates in Pricing Details.
- **Component-to-Deliverable Cascade Pricing System**: Real-time cascade update system ensuring component edits flow through to deliverable totals and summary.
- **Pre-Export Sync Pipeline**: Ensures DOM edits reach exports through a rewritten `collectScenarioFromUi()` that reads all hours/rates from DOM inputs, updates global scenarios, and syncs to the backend before export functions.
- **Component-Level Hours Tracking System**: Granular component-level pricing overrides allowing users to edit individual component hours, which automatically cascade totals to parent deliverables.
- **Component Hours Preservation Guards**: Three-part protection ensuring `component_hours` survive the collect→sync→export pipeline without DOM overwrites.
- **3-Level WBS Hierarchy**: Refactored WBS structure to eliminate L5 role subtask rows. New hierarchy: L2 (Deliverable) → L3 (Component) → L4 (Task). Role assignments are stored as JSON metadata (`Assignments_JSON` field) on L4 tasks instead of separate rows. XML export reads this field to create MSP Assignment elements. Shared `scheduling_calendar.py` module provides single source of truth for business calendar math (8-hour workday, Mon-Fri).
- **Workfront Duration Alignment**: Step 4 UI and MSP/XML exports use business-day durations matching Workfront's "Duration" column. Child tasks are stretched to span the full deliverable window to ensure Workfront's calculated duration matches the intended working-day duration.
- **Workfront 7-Fix Export Patch (Dec 2025)**: Comprehensive XML export fixes: (1) Inclusive duration math without -1 subtraction; (2) Single source of truth via unified schedule map; (3) Summary=1 flag for ALL parent tasks; (4) Parent boundary enforcement via child extension; (5) Resources/Assignments preserved via STRIP_ASSIGNMENTS_FOR_WF=False; (6) Clean task titles without role suffixes (roles in Assignments only); (7) L4+ leaf-to-leaf predecessor filtering to prevent work-wait-work behavior.
- **Hard MSPDI Export Validator**: Pre-export validation ensuring UID uniqueness, valid Assignment/Predecessor references, and duration invariant (duration_minutes == business_days * 480). Exempts milestones and same-day tasks.
- **Effort-Based Waterfall Scheduling**: Feature-flagged system (PHASE_WINDOW_ENABLED) implementing the Final Scheduling Ruleset. Key behaviors: (1) Leaf task duration = ceil(hours/8) business days; (2) Waterfall sequencing per component: general → internal_review → client_review → qa with FS dependencies; (3) Bottom-up rollup: parents derive dates from children, not vice versa; (4) Constraints: Deliverables get SNET, leaves use ASAP with FS dependencies. TICKET B (child stretching) disabled.
- **Parallel Processing**: Utilizes OpenAI Vision API for parallel PDF image processing.
- **Smart Image Analysis**: Two-tier image processing system with pre-filtering and deep analysis.
- **Session Isolation System**: Complete data isolation between different RFPs using unique session IDs.
- **CORS**: Configured to allow cross-origin requests.

### System Design Choices
- **Data Storage Pattern**: Excel/CSV files as primary source for business rules and configuration, loaded into in-memory DataFrames and persisted to PostgreSQL.
- **API Design**: RESTful endpoints for data loading, options retrieval, scenario generation, file uploads, and static file serving.
- **Database Configuration**: Automatic switching based on environment (Replit's PostgreSQL for development, separate production database). Uses `Replit_App_DB_READABLE_FullRows_v3.xlsx` loaded into `app.state.db` at startup with pickle caching.

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
- **OpenAI Vision API**: For parallel image processing and analysis.
- **psycopg2-binary**: PostgreSQL database adapter.
- **SQLAlchemy**: ORM for database interaction.

### File Format Support
- **Excel/CSV**: Core data source.
- **PDF/DOCX**: For RFP document parsing.
- **JSON**: For API data exchange.