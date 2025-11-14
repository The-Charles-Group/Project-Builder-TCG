# Agency Project Builder - Production Ready

## Overview
This project is a web-based Agency Project Builder designed to automate and enhance the efficiency of creating project estimates and timelines. It analyzes Request for Proposal (RFP) content to suggest deliverables, builds project scenarios based on complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to streamline the proposal creation process for creative and digital agencies, improving efficiency and accuracy.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
The frontend uses Vanilla JavaScript, HTML, and CSS in a single-page application with a step-based workflow. It features a 3-column layout (Deliverables | Components | Summary), search functionality, a unified AI Planner UI with real-time progress, and dark mode support via CSS custom properties.

### Technical Implementations
- **Backend**: FastAPI (Python) for the REST API, using Pandas DataFrames for data processing.
- **AI Planner v3**: Advanced reasoning-based AI (GPT-5 + AgencyDB) for granular task selection, asynchronous processing, and evidence-based matching with calibrated confidence scores.
- **GPT-5 Enforcer System**: Blocks non-GPT-5 models, converts Chat Completions API calls to Responses API, and enforces allowed GPT-5 models.
- **Timeline Scheduler Kit**: AI-powered timeline optimization, including Microsoft Project XML parsing, smart SS+lag overlaps, and multi-format export.
- **PM-Brain Capacity Scheduling**: Production-ready system calculating durations based on hours-to-duration formula using resources and focus factors, with resource leveling and realistic dependencies.
- **BusinessCalendar System**: Centralized calendar authority enforcing Monday-Friday scheduling with TCG company holidays, ensuring all date calculations respect the company calendar.
- **Parallel Processing**: Utilizes OpenAI Vision API for parallel PDF image processing with job tracking and retry logic.
- **Smart Image Analysis**: Two-tier image processing system using pre-filtering and deep analysis with GPT-5.
- **3-Level Workfront Hierarchy**: Proper XML export structure with Deliverable → Component → Task hierarchy and WBS codes, supporting manual scheduling tags and "Uncategorized" component handling.
- **Session Isolation System**: Provides complete data isolation between different RFPs using unique session IDs, auto-clear mechanisms, and session-scoped embedding caches.

### Data Storage Pattern
Primary storage uses Excel/CSV files for business rules and configuration data, loaded into in-memory DataFrames. The main database (`Replit_App_DB_READABLE_FullRows_v4.xlsx`) is loaded into `app.state.db` at server startup, with automatic discovery and pickle caching for fast access.

### API Design
Provides RESTful endpoints for data loading, options retrieval, and scenario generation. It supports file uploads, uses JSON for data exchange, and serves static files.

## External Dependencies

### Python Libraries
- **FastAPI**: Web framework.
- **Pandas**: Data manipulation.
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

## Known Issues

### Workfront XML Export - PredecessorLink Generation (Nov 2025)
**Status**: Documented - Deferred for future work

**Issue**: The `convert_excel_to_mspdi.py` exporter does NOT generate `<PredecessorLink>` elements in the XML output, resulting in tasks without dependency relationships in Workfront.

**Root Cause**: The export function expects a "Dependencies" column in the DataFrame containing predecessor information (e.g., "2FS", "1SS+2d"), but:
1. The Dependencies column is NOT populated by `build_schedule()` in `timeline_scheduler.py`
2. Dependencies are calculated internally during CPM scheduling but never added back to the DataFrame
3. The exporter has placeholder code for dependency parsing but receives empty data

**Impact**:
- Tasks import into Workfront with correct Start/Finish dates but no visible predecessor links
- Project managers must manually recreate task dependencies in Workfront
- Timeline changes in Workfront don't automatically propagate to dependent tasks

**Workaround**: None currently - manual dependency creation required in Workfront after import

**Future Fix** (requires significant work):
1. Modify `build_schedule()` to populate DataFrame["Dependencies"] column after CPM calculation
2. Convert internal dependency objects to MSP format strings (e.g., "2FS+0", "1SS+50%")
3. Test XML generation with populated Dependencies column
4. Validate import into Workfront shows correct predecessor links

**Related Files**:
- `convert_excel_to_mspdi.py` (lines 1400-1500): PredecessorLink generation code
- `timeline_scheduler.py`: CPM scheduling and dependency calculation
- `scripts/test_predecessor_sanity.py`: Test script demonstrating correct PredecessorLink XML structure

**Verification**: The sanity test script (`scripts/test_predecessor_sanity.py`) proves that Workfront correctly respects PredecessorLink elements when present in XML - Task B with FS predecessor to Task A starts immediately after Task A with no gaps.

### Code Quality - PATCH VIOLATIONS (Nov 2025)
**Status**: Documented - Cleanup required

**Issue**: Multiple code quality violations detected by CORE_PRINCIPLES.md linter:
- **Data Truncation** (~80 instances): Arbitrary slice limits like `[:100]`, `[:3000]` in various files
- **Error Silencing** (~15 instances): Bare `except:` blocks and broad `except Exception:` handlers
- **Fake Progress** (~2 instances): Placeholder return values in status functions

**Impact**: 
- Potential data loss from truncation
- Silent failures masking real errors
- Misleading status information

**Files Affected**:
- `main.py`: Majority of violations (data truncation, error handling)
- `ai_planner_agencydb.py`: Data truncation in candidate filtering
- `ai_timeline_manager.py`: Data truncation in milestone generation
- `ai_weighted_matcher.py`: List slicing in suggestion generation

**Future Fix**: Systematic cleanup pass required to:
1. Replace arbitrary limits with configurable thresholds or pagination
2. Add specific exception handling with logging
3. Implement proper status tracking
4. Add comprehensive error recovery logic