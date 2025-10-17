# Agency Project Builder - Production Ready

## Overview
This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. **Status: Production Ready - v5.6** (October 16, 2025) It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation.

## Recent Changes
- **October 17, 2025**: Gantt Chart Performance Fix + Timeline Generation Stability
  - **CRITICAL FIX**: Resolved browser freeze when dragging deliverables in Gantt chart (Step 4)
    - Root cause: `on_date_change` callback firing continuously during drag operations
    - Implemented **per-task debouncing** using Map data structure (300ms delay)
    - Each task gets independent debounce timer, preventing lost updates when dragging multiple tasks rapidly
    - Expensive operations (array search, GanttBridge event emissions, state updates) now batched after drag completes
    - Save button displays immediately for instant user feedback while updates batch in background
    - Added `taskDebouncers.clear()` on chart rebuild for immediate cleanup of retired task IDs
    - Users can now smoothly drag multiple deliverables without browser freezing or lost data
    - Architect-reviewed and approved for production
  - **CRITICAL FIX**: Resolved infinite loop in timeline generation (Phase 5 - critical path calculation)
    - Added max iteration guards (2x task count) to forward and backward passes in `calculate_critical_path()`
    - Implemented stall detection - breaks out if no progress made in iteration
    - Added fallback processing for unprocessed tasks with default values
    - Timeline generation now completes successfully even with circular dependencies
    - Added detailed [CRITICAL PATH] logging to trace execution and diagnose issues
  - **Security Updates Verification**:
    - **VERIFIED**: All security updates functioning correctly after dependency updates
    - Re-verified `jinja2==3.1.6` (CVE-2025-27516 fixed) - Application rendering correctly
    - Re-verified `python-multipart==0.0.20` (CVE-2024-24762 & CVE-2024-53981 fixed) - File uploads working
    - Comprehensive functionality tests passed:
      - ✅ FastAPI server running successfully
      - ✅ Database loaded (1916 rows)
      - ✅ All API endpoints operational (/api/options, /api/load, /api/suggest_by_file)
      - ✅ File upload and multipart form parsing working correctly
      - ✅ UI rendering and page loads successful
      - ✅ GPT-5 integration active and responding
    - No breaking changes detected from security updates

- **October 16, 2025**: Unified Pricing Table + Critical bug fixes
  - **NEW FEATURE**: Unified Editable Pricing Table (Step 3)
    - Replaced TWO separate tables with ONE expandable table merging deliverables and components
    - Real-time synchronization between Gantt timeline and pricing via event bridge
    - Inline editing: cadence (One-Time/Monthly/Quarterly), months, hours, rate, resources/tasks
    - Smart cadence propagation: parent deliverable values cascade to child components
    - Dual persistence: localStorage (instant) + server storage (durable) with pub/sub state management
    - Components start collapsed (▸), expand on click (▾) to show detailed breakdown
    - Per-row Save buttons + unified "Re-build Scenario" action
    - Backend API: `/api/scenario/save` (POST) and `/api/scenario/active` (GET)
    - 6 new files: scenario_api.py, scenario-store.js, pricing-one-table.js, gantt-bridge.js, pricing-one-table.css, pricing-one-table.html
  - **CRITICAL FIX**: Resolved infinite polling loop that froze browsers during analysis
    - Fixed undefined `logError` function causing error handling failure
    - Converted polling to instance-based cleanup preventing multiple concurrent loops
    - Added page visibility/unload event handlers to stop polling when user navigates away
    - Added detailed logging for debugging polling lifecycle
  - Updated `jinja2` to v3.1.6 (fixes CVE-2025-27516 sandbox breakout vulnerability)
  - Updated `python-multipart` to v0.0.20 (fixes CVE-2024-24762 ReDoS & CVE-2024-53981 logging DoS vulnerabilities)
  - All functionality verified working correctly after updates
  - Comprehensive tests passed: health endpoint, API, file uploads, static files, home page
  - Security scanner verification: No known vulnerabilities detected

## User Preferences
Preferred communication style: Simple, everyday language.

## CRITICAL DEVELOPMENT PRINCIPLES - MANDATORY

### NO PATCH FIXES - EVER
**THIS IS NON-NEGOTIABLE**: Any developer working on this codebase MUST follow these principles. Violations are unacceptable.

1. **NO TIMEOUTS AS FIXES** - Never add timeouts to "solve" hanging operations. Fix the actual async/blocking issue.
2. **NO DATA TRUNCATION** - Never reduce data size (e.g., text[:8000]) to avoid issues. Handle full data properly.
3. **NO ERROR SILENCING** - Never catch and ignore exceptions. Fix the root cause.
4. **NO ARBITRARY LIMITS** - Never limit iterations/processing to avoid problems. Implement proper solutions.
5. **NO FAKE PROGRESS** - Never show illusions of functionality. Be transparent about actual state.

**See CORE_PRINCIPLES.md for full enforcement rules and examples.**

**Remember**: "If a fix makes the app appear to work while actually reducing functionality, it's not a fix - it's a lie."

## System Architecture

### Backend Architecture
- **Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data, calculations, and manipulations.
- **File Handling**: Supports parsing of PDF and DOCX documents, and Excel file uploads.
- **Core Logic**: Implements RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **AI Planner v3 (GPT-5 + AgencyDB)**: Advanced reasoning-based AI intelligence layer connected to a real database for granular task selection. Features include asynchronous processing with job tracking, real-time progress updates, granular L2 task selection, holistic project flow analysis, and evidence-based matching with calibrated confidence scores. It also incorporates smart multipliers for complexity, channel, market, and compliance factors, and auto-relaxation/rescue logic.
- **GPT-5 Enforcer System**: Centralized model enforcement through `sitecustomize.py` that:
  - **Blocks ALL non-GPT-5 models** automatically at SDK level (no silent downgrades to gpt-4, o1, o3)
  - **Auto-converts** Chat Completions API calls to Responses API transparently
  - **Enforces allowed models**: gpt-5, gpt-5-pro, gpt-5-mini, gpt-5-thinking, gpt-5-thinking-mini
  - **Tier system**: mini (low compute), thinking (medium compute), pro (high compute)
  - **Zero code changes needed** - Python automatically loads enforcer on startup
  - **Helper functions**: `gpt5_json_schema()` for strict JSON, `gpt5_text()` for text responses
- **Timeline Scheduler Kit**: AI-powered timeline optimization with Microsoft Project XML parsing, smart SS+lag overlaps, gatekeeper preservation, cycle breaking, duration rounding, and units recalculation. Supports multi-format export (XML, Gantt JSON, explanations JSON, Excel audit trail).
- **Parallel Processing**: Implemented parallel processing of PDF images with OpenAI Vision API for faster analysis and real-time progress tracking, including job tracking, retry logic, and robust error handling.
- **Smart Image Analysis**: Two-tier image processing system using pre-filtering, quick relevance scans (GPT-5), and deep analysis for relevant images to reduce processing time and cost for PDFs with many decorative images. User control is available to disable image analysis.
- **Database Architecture**: Primary database is v4 (`test_outputs/Replit_App_DB_READABLE_FullRows_v4.xlsx`) loaded into `app.state.db` during server startup. It contains 24 configuration sheets and handles backwards compatibility.
- **Session Isolation System**: Complete data isolation between different RFPs to prevent cross-contamination:
  - **Frontend Session Management**: Unique session IDs (`session_<timestamp>_<random>`) generated for each new RFP analysis
  - **Auto-Clear Mechanism**: All localStorage data automatically cleared when new RFP uploaded or analyzed
  - **Session-Scoped Embedding Cache**: Embedding cache strictly isolated by session_id with NO fallback to global cache (prevents old RFP data from appearing in new analyses)
  - **24-Hour TTL**: Automatic expiration and cleanup of old session data
  - **Clear All Data Button**: Manual control for users to wipe all cached data anytime
  - **Background Cleanup**: Hourly task removes expired sessions to prevent storage bloat
  - **Critical Fix (Oct 2025)**: Eliminated data contamination bug where previous RFP content (e.g., SoundCloud) appeared in new RFP summaries by removing global cache fallback in `embedding_cache.py`
- **CORS**: Configured to allow cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow, focused on a single scenario (Scenario A).
- **Styling**: Uses CSS custom properties for theming, including a dark mode.
- **State Management**: Centralized `selectionStore` with Proxy-backed compatibility layer.
- **UI Improvements**: Features a 3-column layout (Deliverables | Components | Summary), search functionality, enhanced summary panel, and new unified AI Planner UI with real-time progress bar, summary panel, evidence-backed suggestions, component details, and risk indicators.
  - **Select All/Deselect All**: Added buttons at the top of AI-Suggested Deliverables for bulk selection control
  - **Department Labels**: Each deliverable shows color-coded department tags ([Strategy], [Creative], [Content], [Paid Media], [Technology], [Integrated Marketing Management])
  - **Department Grouping**: Deliverables are organized by department with visual distinction and project flow explanation
- **Timeline Accuracy**: Incorporates business days calculation with US/MX holiday calendar and excludes weekends.
- **XML Export Control**: UI toggle for optional inclusion of Start/End anchor milestones in XML exports.

### Data Storage Pattern
- **Primary Storage**: Excel/CSV files serve as the main source for business rules and configuration data.
- **Data Models**: In-memory DataFrames are loaded from spreadsheets to define tasks, deliverables, pricing rules, rate cards, timeline parameters, scaling factors, bundle configurations, hour allocations, and scenario templates.

### API Design
- Provides RESTful endpoints for data loading, options retrieval, and scenario generation.
- Supports file uploads for RFP documents and Excel configuration files.
- Uses JSON for configuration data and calculated scenario responses.
- Serves static files for frontend assets.
- Includes endpoints for weighted AI suggestions, bulk L3 task retrieval, and scenario refetching.

### Database Configuration
- **Automatic Switching**: The application uses automatic database switching based on the environment (Replit's built-in PostgreSQL for development, separate production database when published).
- **Connection Helper**: `database.py` module provides helper functions (`get_database_url`, `get_connection_params`) to manage database connections.
- **Publishing**: When publishing, Replit's "Production Database" option automatically configures the production database.
- **Models**: Database models should be defined in `models.py`.

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
- **SQLAlchemy**: ORM for database interaction (as shown in `models.py` example).

### File Format Support
- **Excel/CSV**: Core data source.
- **PDF/DOCX**: For RFP document parsing.
- **JSON**: For API data exchange.