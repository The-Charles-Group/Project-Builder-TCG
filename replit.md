# Agency Project Builder

## Overview
This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data, calculations, and manipulations.
- **File Handling**: Supports parsing of PDF and DOCX documents, and Excel file uploads.
- **Core Logic**: Implements RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **AI Planner v3 (GPT-5 + AgencyDB)**: Advanced reasoning-based AI intelligence layer connected to a real database for granular task selection. Features include asynchronous processing with job tracking, real-time progress updates, granular L2 task selection, holistic project flow analysis, and evidence-based matching with calibrated confidence scores. It also incorporates smart multipliers for complexity, channel, market, and compliance factors, and auto-relaxation/rescue logic.
- **Timeline Scheduler Kit**: AI-powered timeline optimization with Microsoft Project XML parsing, smart SS+lag overlaps, gatekeeper preservation, cycle breaking, duration rounding, and units recalculation. Supports multi-format export (XML, Gantt JSON, explanations JSON, Excel audit trail).
- **Parallel Processing**: Implemented parallel processing of PDF images with OpenAI Vision API for faster analysis and real-time progress tracking, including job tracking, retry logic, and robust error handling.
- **Smart Image Analysis**: Two-tier image processing system using pre-filtering, quick relevance scans (GPT-5), and deep analysis for relevant images to reduce processing time and cost for PDFs with many decorative images. User control is available to disable image analysis.
- **Database Architecture**: Primary database is v4 (`test_outputs/Replit_App_DB_READABLE_FullRows_v4.xlsx`) loaded into `app.state.db` during server startup. It contains 24 configuration sheets and handles backwards compatibility.
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