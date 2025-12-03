# Agency Project Builder - Production Ready

## Overview
This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It automates RFP analysis to suggest deliverables, builds project scenarios based on complexity and tiers, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to enhance efficiency and accuracy in project proposal generation, offering significant market potential for agencies.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- Single-page application with a step-based workflow.
- Uses CSS custom properties for theming, including dark mode.
- 3-column layout (Deliverables | Components | Summary) with search and an enhanced summary panel.
- Unified AI Planner UI with real-time progress, evidence-backed suggestions, and risk indicators.
- UI toggle for optional inclusion of Start/End anchor milestones in XML exports.

### Technical Implementations
- **Backend Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for Excel/CSV data.
- **File Handling**: Parses PDF, DOCX, and Excel files.
- **Core Logic**: Implements RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **SCENARIO_STORE Architecture**: Dual-entry session-based data store with immutable `baseline` and mutable `working` scenarios, ensuring Step 3 edits persist across operations.
- **AI Planner v3**: Advanced reasoning-based AI (GPT-5 + AgencyDB) for granular task selection and holistic project flow analysis.
- **GPT-5 Enforcer System**: Centralized model enforcement ensuring exclusive use of GPT-5 and proper API usage.
- **GPT 5.1 Pro RFP Summary**: Frontend rendering of structured RFP summary bullets for quick review.
- **GPT 5.1 Pro Smart Selection L3 Filtering**: Curated L3 task selection system ensures only AI-vetted tasks flow to Step 3.
- **Retainer Flow System**: End-to-end retainer/cadence wiring from AI suggestions to pricing display and backend sync.
- **Timeline Scheduler Kit**: AI-powered timeline optimization with Microsoft Project XML parsing, smart dependencies, and multi-format export.
- **3-Level Workfront Hierarchy**: Proper XML export structure (Deliverable → Component → Task) with WBS codes and manual scheduling tags.
- **PM-Brain Capacity Scheduling**: Capacity-based durations, resource leveling, and realistic dependencies for timeline scheduling.
- **Gantt Timeline Date Preservation**: XML export preserves user-edited deliverable dates from the interactive Gantt.
- **Workfront Manual Scheduling Lock**: Prevents Workfront recalculation of user-edited dates on XML import.
- **Chronological Waterfall Export**: XML export system creates simple, chronological Gantt timelines in Workfront without Service Department grouping, flattening WBS hierarchy.
- **L5+ Edge Filtering System**: Dependency filtering to enable parallel role execution while maintaining summary-level waterfall structure.
- **Sibling Auto-Chaining System**: Automatic waterfall dependency generation for summary-level siblings within each parent group, supporting brand chain validation.
- **Parallel Processing**: Utilizes OpenAI Vision API for parallel PDF image processing.
- **Smart Image Analysis**: Two-tier image processing system with pre-filtering and deep analysis.
- **Session Isolation System**: Complete data isolation between RFPs using unique session IDs.
- **CORS**: Configured to allow cross-origin requests.

### System Design Choices
- **Data Storage Pattern**: Excel/CSV files as primary source for business rules, loaded into in-memory DataFrames.
- **API Design**: RESTful endpoints for data loading, options retrieval, scenario generation, file uploads, and static file serving.
- **Database Configuration**: Automatic switching based on environment (Replit's PostgreSQL for development, separate production database).

## External Dependencies

### Python Libraries
- **FastAPI**: Web framework.
- **Pandas**: Data manipulation.
- **NumPy**: Numerical operations.
- **OpenPyXL**: Excel processing.
- **PDFPlumber**: PDF text extraction.
- **python-docx**: Word document processing.
- **Jinja2**: Template engine.
- **Uvicorn**: ASGI server.
- **OpenAI Vision API**: Image processing and analysis.
- **psycopg2-binary**: PostgreSQL adapter.
- **SQLAlchemy**: ORM.

### File Format Support
- **Excel/CSV**: Core data.
- **PDF/DOCX**: RFP document parsing.
- **JSON**: API data exchange.