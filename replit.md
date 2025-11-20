# Agency Project Builder - Production Ready

## Overview
This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation, and improving market competitiveness.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core System
The system is built on a FastAPI (Python) backend for its REST API, utilizing Pandas DataFrames for efficient data manipulation. It supports robust file handling, capable of parsing PDF, DOCX, and Excel documents for RFP analysis. The core logic encompasses RFP analysis, scenario building, a sophisticated pricing engine, and timeline calculation, with a focus on generating Workfront-compatible exports.

### Advanced AI and Scheduling
A key component is the AI Planner v3 (GPT-5 + AgencyDB), an advanced reasoning-based AI layer that handles granular task selection, asynchronous processing, and real-time progress updates. It incorporates smart multipliers and auto-relaxation/rescue logic for dynamic project adjustments. The GPT-5 Enforcer System centralizes model enforcement, ensuring all AI operations use GPT-5 models.

The Timeline Scheduler Kit provides AI-powered timeline optimization, including Microsoft Project XML parsing, smart SS+lag overlaps, and gatekeeper preservation. It features a PM-Brain Capacity Scheduling system that dynamically calculates task durations based on resources and hours, replacing static patterns with defensible, capacity-based durations. This includes resource leveling and realistic dependency handling.

A critical feature is the Gantt Timeline Date Preservation and Workfront Manual Scheduling Lock, which ensures that user-edited deliverable dates from the interactive Gantt timeline are precisely maintained upon XML export and Workfront import, preventing recalculation and timeline inflation. This is achieved through the use of Microsoft Project manual scheduling tags.

The system also incorporates WBS-Based Dependencies and Multi-Assignment Export, implementing GPT-5 specifications for dependency normalization to L5 (OutlineLevel ≤ 5) and parallel role execution, enhancing accuracy in project structure and resource allocation.

### XML Export Modes (Mode A vs Mode B)
The XML export supports two architectures for Workfront compatibility, controlled by `EXPORT_MODE` flag:

#### Mode A - L5-Only Export (Legacy)
Set `EXPORT_MODE = "A"` for L5-only export:
- **L6 Role Aggregation**: All OutlineLevel > 5 (role rows) are aggregated into their L5 parent components, completely removing L6 tasks from the export
- **Output**: Only L5 summary tasks with multi-assignments

#### Mode B - L5 Summaries + L6 Children (Current)
Set `EXPORT_MODE = "B"` for Mode B specification (ACTIVE):
- **L6 Tasks Retained**: All OutlineLevel > 5 (role rows) are kept in the task list
- **L6 Date Synchronization**: L6 child task dates are synchronized to match their L5 parent (Start, Finish, Duration)
- **L6 No Dependencies**: L6 tasks have NO dependency links (all dependencies normalized to L5→L5)
- **L5 Summary Tasks**: L5 components receive aggregated metrics (min/max dates, sum hours/revenue) and multiple `<Assignment>` entries
- **Output**: Complete task list with both L5 summary tasks (with multi-assignments) and L6 role children (with synced dates)

#### Common Features (Both Modes)
- **Multi-Assignment XML**: Each L5 component exports with multiple `<Assignment>` entries, one per role, with correct hours/rates
- **WBS Dependency Normalization**: All dependencies are normalized to L5 (OutlineLevel ≤ 5) by walking parent WBS hierarchy
- **Feature Flags** (main.py lines 36-43):
  - `EXPORT_MODE = "B"`: Mode A (L5-only) or Mode B (L5+L6 with synced dates)
  - `ENABLE_MULTI_ASSIGNMENT = True`: Aggregates L6 role hours into L5 multi-assignments
  - `ENABLE_WBS_DEPENDENCIES = True`: Uses WBS-based dependencies with L5 normalization
- **Implementation**: 
  - `aggregate_l5_tasks()` function (lines 9612-9837) performs aggregation and date synchronization based on export mode
  - `build_wbs_dependencies()` function (lines 9383-9528) normalizes dependencies to L5, ensuring no L6 dependency links
  - Validation logging confirms L6 count, date syncing, and L5→L5 dependencies only

### User Interface and Data Management
The frontend is a vanilla JavaScript, HTML, and CSS single-page application with a step-based workflow. It features a 3-column layout (Deliverables | Components | Summary), search functionality, and a unified AI Planner UI with real-time progress. Timeline accuracy is ensured through business day calculations, including holiday calendars.

Data storage primarily relies on Excel/CSV files for business rules and configuration data, loaded into in-memory DataFrames. The system includes a robust Session Isolation System, providing complete data isolation for different RFPs, with unique session IDs and automatic cleanup.

### Database
The system uses a primary database (`Replit_App_DB_READABLE_FullRows_v4.xlsx`) loaded into `app.state.db` during server startup, which includes 24 configuration sheets and handles backward compatibility. It supports automatic database switching based on the environment (Replit's built-in PostgreSQL for development) and uses SQLAlchemy for ORM.

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