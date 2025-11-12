# Agency Project Builder - Production Ready

## Overview
The Agency Project Builder is a web-based tool designed to automate and enhance the efficiency and accuracy of project proposal generation for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest deliverables, builds project scenarios based on complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to streamline the proposal creation process, significantly improving efficiency and accuracy in generating project estimates and timelines.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
The frontend uses Vanilla JavaScript, HTML, and CSS to create a single-page application with a step-based workflow focused on a single scenario. It features a 3-column layout (Deliverables | Components | Summary), search functionality, an enhanced summary panel, and a unified AI Planner UI with a real-time progress bar, evidence-backed suggestions, and risk indicators. Styling uses CSS custom properties for theming, including a dark mode. UI includes "Select All/Deselect All" buttons and department grouping for deliverables, and a UI toggle for optional inclusion of Start/End anchor milestones in XML exports.

### Technical Implementations
- **Backend Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data.
- **File Handling**: Supports parsing of PDF and DOCX documents, and Excel file uploads.
- **AI Planner v3 (GPT-5 + AgencyDB)**: An advanced reasoning-based AI layer for granular task selection, asynchronous processing, real-time progress updates, holistic project flow analysis, and evidence-based matching with calibrated confidence scores. Includes smart multipliers and auto-relaxation/rescue logic.
- **GPT-5 Enforcer System**: Centralized model enforcement that blocks all non-GPT-5 models, auto-converts Chat Completions API calls to Responses API, and enforces allowed GPT-5 models through `sitecustomize.py`.
- **Timeline Scheduler Kit**: AI-powered timeline optimization with Microsoft Project XML parsing, smart SS+lag overlaps, gatekeeper preservation, cycle breaking, duration rounding, and multi-format export.
- **PM-Brain Capacity Scheduling**: Production-ready timeline scheduling system replacing static patterns with capacity-based durations using an hours-to-duration formula. It includes resource leveling with `max_parallel` constraints, realistic SS/FS dependencies, and summary bar rollups. Gantt sync throttling prevents UI freezes, and a batch update endpoint handles multi-task edits efficiently. Role rows export as Assignments with seniority-aware resource UID mapping.
- **Parallel Processing**: Utilizes OpenAI Vision API for parallel PDF image processing with job tracking, retry logic, and error handling.
- **Smart Image Analysis**: A two-tier image processing system using pre-filtering, quick relevance scans (GPT-5), and deep analysis for relevant images to optimize processing time and cost.
- **Session Isolation System**: Provides complete data isolation between different RFPs using unique session IDs, auto-clear mechanisms, session-scoped embedding caches with a 24-hour TTL, and hourly background cleanup.
- **CORS**: Configured to allow cross-origin requests.

### Feature Specifications
- **Core Logic**: Implements RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **SCENARIO_STORE Architecture**: Centralized session-based data store for pricing, timeline, and Gantt synchronization, ensuring all edits operate on the same canonical scenario data and include automatic totals recalculation.
- **3-Level Workfront Hierarchy**: Exports a proper XML structure with Deliverable → Component → Task hierarchy (OutlineLevels 0/1/2), WBS codes, manual scheduling tags for date locking, and "Uncategorized" component handling. It eliminates duplicate tasks and unrealistic timelines by enabling parallel task execution within components.
- **Timeline Accuracy**: Incorporates business days calculation with US/MX holiday calendar and excludes weekends.

### System Design Choices
- **Data Storage Pattern**: Excel/CSV files serve as the main source for business rules and configuration data. In-memory DataFrames are loaded from spreadsheets to define tasks, deliverables, pricing rules, rate cards, timeline parameters, scaling factors, bundle configurations, hour allocations, and scenario templates.
- **Database Architecture**: The primary database (`Replit_App_DB_READABLE_FullRows_v4.xlsx`) is loaded into `app.state.db` during server startup, handling 24 configuration sheets and backward compatibility. Automatic discovery checks standard locations, then scans `attached_assets/` for timestamped v4 files, selecting the most recent. Pickle caching ensures sub-2ms load times with a validation system. Automatic fallback to mock data if Excel loading fails.
- **API Design**: Provides RESTful endpoints for data loading, options retrieval, and scenario generation. It supports file uploads for RFP documents and Excel configuration files, uses JSON for configuration data and calculated scenario responses, and serves static files for frontend assets. Includes endpoints for weighted AI suggestions, bulk L3 task retrieval, and scenario refetching.
- **Database Configuration**: Automatic database switching based on the environment (Replit's built-in PostgreSQL for development, separate production database). `database.py` module provides helper functions for managing connections, and models are defined in `models.py`.

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