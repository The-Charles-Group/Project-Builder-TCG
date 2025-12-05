# Agency Project Builder - Production Ready

## Overview
This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- Single-page application with a step-based workflow focused on a single scenario.
- Uses CSS custom properties for theming, including a dark mode.
- 3-column layout (Deliverables | Components | Summary), search functionality, enhanced summary panel.
- Unified AI Planner UI with real-time progress bar, evidence-backed suggestions, and risk indicators.
- "Select All/Deselect All" buttons and department grouping for deliverables.
- UI toggle for optional inclusion of Start/End anchor milestones in XML exports.

### Technical Implementations
- **Backend Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data.
- **File Handling**: Parses PDF, DOCX, and Excel files.
- **Core Logic**: Implements RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **SCENARIO_STORE Architecture**: Dual-entry session-based data store with immutable `baseline` and mutable `working` scenario for Step 3 edits.
- **AI Planner v3**: Advanced reasoning-based AI layer (GPT-5 + AgencyDB) for granular task selection, asynchronous processing, and holistic project flow analysis.
- **GPT-5 Enforcer System**: Centralized model enforcement ensuring exclusive use of GPT-5.
- **GPT 5.1 Pro RFP Summary**: Frontend rendering of structured `summary_bullets` from backend for quick executive scanning.
- **GPT 5.1 Pro Smart Selection L3 Filtering**: Curated L3 task selection system ensuring only AI-vetted tasks flow through Smart Selection to Step 3.
- **Timeline Scheduler Kit**: AI-powered timeline optimization with Microsoft Project XML parsing, smart dependencies, duration rounding, and multi-format export.
- **3-Level Workfront Hierarchy**: Proper XML export structure (Deliverable → Component → Task) with WBS codes and manual scheduling tags.
- **PM-Brain Capacity Scheduling**: Production-ready timeline scheduling using capacity-based durations, resource leveling, and realistic dependencies.
- **Workfront Manual Scheduling Lock**: Prevents Workfront from recalculating user-edited deliverable dates on XML import.
- **Chronological Waterfall Export**: Production-ready XML export system creating simple, chronological Gantt timelines in Workfront by flattening WBS hierarchy and chronologically sorting tasks while preserving parent-child adjacency and dependencies.
- **L5+ Edge Filtering System**: Enables parallel role execution by filtering out L5+ to L5+ dependencies while maintaining summary-level waterfall structure.
- **Sibling Auto-Chaining System**: Automatic waterfall dependency generation for summary-level siblings within each parent group, creating a clean left-to-right staircase Gantt view.
- **Parallel Processing**: Utilizes OpenAI Vision API for parallel PDF image processing with job tracking and retry logic.
- **Smart Image Analysis**: Two-tier image processing system using pre-filtering, quick relevance scans, and deep analysis.
- **Session Isolation System**: Complete data isolation between different RFPs using unique session IDs and auto-clear mechanisms.
- **Build-Driven Pricing Flow**: Unified pricing calculation architecture eliminating double-counting bugs by centralizing calculations through a single `/api/build` endpoint.

### System Design Choices
- **Data Storage Pattern**: Excel/CSV files as primary source for business rules and configuration, loaded into in-memory DataFrames.
- **API Design**: RESTful endpoints for data loading, options retrieval, scenario generation, file uploads, and static file serving.
- **Database Configuration**: Automatic switching based on environment (Replit's PostgreSQL for development, separate production database). In-memory `app.state.db` initialized from `Replit_App_DB_READABLE_FullRows_v3.xlsx` with pickle caching.

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