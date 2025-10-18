# Agency Project Builder - Production Ready

## Overview
This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data.
- **File Handling**: Supports parsing of PDF and DOCX documents, and Excel file uploads.
- **Core Logic**: Implements RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **SCENARIO_STORE Architecture**: Centralized session-based data store for pricing, timeline, and Gantt synchronization, ensuring all edits operate on the same canonical scenario data. Includes automatic totals recalculation.
- **AI Planner v3 (GPT-5 + AgencyDB)**: Advanced reasoning-based AI layer for granular task selection, asynchronous processing, real-time progress updates, holistic project flow analysis, and evidence-based matching with calibrated confidence scores. Incorporates smart multipliers and auto-relaxation/rescue logic.
- **GPT-5 Enforcer System**: Centralized model enforcement that blocks all non-GPT-5 models, auto-converts Chat Completions API calls to Responses API, and enforces allowed GPT-5 models through `sitecustomize.py`.
- **Timeline Scheduler Kit**: AI-powered timeline optimization with Microsoft Project XML parsing, smart SS+lag overlaps, gatekeeper preservation, cycle breaking, duration rounding, and multi-format export.
- **Parallel Processing**: Utilizes OpenAI Vision API for parallel PDF image processing with job tracking, retry logic, and error handling.
- **Smart Image Analysis**: Two-tier image processing system using pre-filtering, quick relevance scans (GPT-5), and deep analysis for relevant images to optimize processing time and cost.
- **Database Architecture**: Primary database (`Replit_App_DB_READABLE_FullRows_v4.xlsx`) loaded into `app.state.db` during server startup, containing 24 configuration sheets and handling backwards compatibility.
- **Session Isolation System**: Complete data isolation between different RFPs using unique session IDs, auto-clear mechanisms, session-scoped embedding caches with a 24-hour TTL, and hourly background cleanup.
- **CORS**: Configured to allow cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow focused on a single scenario.
- **Styling**: Uses CSS custom properties for theming, including a dark mode.
- **State Management**: Centralized `selectionStore` with Proxy-backed compatibility layer.
- **UI Improvements**: Features a 3-column layout (Deliverables | Components | Summary), search functionality, enhanced summary panel, and new unified AI Planner UI with real-time progress bar, evidence-backed suggestions, and risk indicators. Includes "Select All/Deselect All" buttons and department grouping for deliverables.
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
- **Automatic Switching**: Automatic database switching based on the environment (Replit's built-in PostgreSQL for development, separate production database when published).
- **Connection Helper**: `database.py` module provides helper functions for managing database connections.
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
- **SQLAlchemy**: ORM for database interaction.

### File Format Support
- **Excel/CSV**: Core data source.
- **PDF/DOCX**: For RFP document parsing.
- **JSON**: For API data exchange.