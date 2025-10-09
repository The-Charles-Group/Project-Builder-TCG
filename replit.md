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
- **AI Matching**: Integrates comprehensive AI matching rules for deliverables, components, and subtasks with priority scoring and configurable weights. Features a weighted scoring API and an interactive AI suggestions panel.
- **Parallel Processing**: Implemented parallel processing of PDF images with OpenAI Vision API for faster analysis and real-time progress tracking. Includes job tracking, retry logic, and robust error handling.
- **Database Compatibility**: Supports v3 database structure with graceful handling of missing sheets and fallback values.
- **CORS**: Configured to allow cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow, simplified to focus on a single scenario (Scenario A).
- **Styling**: Uses CSS custom properties for theming, including a dark mode.
- **State Management**: Centralized `selectionStore` as single source of truth with Proxy-backed compatibility layer for legacy code paths.
- **UI Improvements**: Features a 3-column layout (Deliverables | Components | Summary), search functionality, and enhanced summary panel with hierarchical display and individual remove buttons.
- **AI Integration**: Displays GPT-5 suggestions with reasoning, and action buttons for applying or replacing suggestions.
- **Timeline Accuracy**: Incorporates business days calculation with US/MX holiday calendar and excludes weekends from timeline end dates.
- **XML Export Control**: UI toggle for optional inclusion of Start/End anchor milestones in XML exports.

### Data Storage Pattern
- **Primary Storage**: Excel/CSV files serve as the main source for business rules and configuration data.
- **Data Models**: In-memory DataFrames are loaded from spreadsheets to define tasks, deliverables, pricing rules, rate cards, timeline parameters, scaling factors, bundle configurations, hour allocations, and scenario templates.

### API Design
- Provides RESTful endpoints for data loading, options retrieval, and scenario generation.
- Supports file uploads for RFP documents and Excel configuration files.
- Uses JSON for configuration data and calculated scenario responses.
- Serves static files for frontend assets.
- Includes new endpoints for weighted AI suggestions (`/api/step2/ai/weights`), bulk L3 task retrieval (`/api/step2/l3/bulk`), and scenario refetching (`/api/scenarios`).

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

### File Format Support
- **Excel/CSV**: Core data source.
- **PDF/DOCX**: For RFP document parsing.
- **JSON**: For API data exchange.