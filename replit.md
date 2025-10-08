# Agency Project Builder

## Overview

This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (October 2025)

### Workfront XML Export Enhancements (Latest)
- **Milestone Anchors**: START/END anchor tasks now display as friendly milestones
  - Names changed from `[DEL-xxxx] START/END` to `Start — {Deliverable Name}` / `End — {Deliverable Name}`
  - All anchor tasks marked with `<Milestone>1</Milestone>` for visual de-emphasis in Workfront
  - Located in `enrich_wbs_for_workfront()` function (lines 4799-4907 in main.py)
  - XML milestone tag added at line 5278-5280 in main.py
- **No [nan] Labels**: Safe fallback code generation prevents any [nan] entries in exports

### Step 2 UI Restructure
- **Simplified Grid**: Changed from 4-column to 3-column layout (Deliverables | Components | Summary)
  - Removed dedicated L3 Subtasks column
  - L3 selection now handled within Summary panel for each component
  - Grid template updated to `1fr 1fr 350px` for better spacing
- **Search Functionality**: Search bars for Deliverables and Components filter the lists in real-time
- **Enhanced Summary**: Shows hierarchical Deliverable → Component → L3 structure with per-component controls

### L3 Bulk Query Endpoints
- **New Endpoint `/api/step2/l3/bulk`**: Returns L3 tasks grouped by component for efficient UI rendering
  - Input: `{"deliverable": "code", "components": ["comp1", "comp2"]}`
  - Output: `{"comp1": ["task1", "task2"], "comp2": ["task3"]}`
  - Preserves component grouping for summary panel display
- **Enhanced `/api/step2/l3`**: Now accepts both single component (string) or multiple components (array)
  - Returns merged, deduplicated L3 tasks
  - Fully backward compatible with existing callers

### Critical L3 Synchronization Fix
- **Issue**: L3 (Level 3) selections from Step 2 UI were not reaching Step 3 payload due to data synchronization problems between legacy code paths and the centralized state store.
- **Solution**: Implemented a Proxy-backed `selectedL3ByKey` object that intercepts all property operations (get, set, delete, enumerate) and synchronizes with `selectionStore.l3ByComponent` Map.
- **Implementation**: 
  - Lines 66-100 in app.js: Proxy with comprehensive traps for all operations
  - Lines 103-121 in app.js: Locked property definition to prevent accidental reassignment
  - Ensures all read/write paths use a single source of truth

### Enhanced Summary Panel
- **Feature**: Column 4 now displays hierarchical Deliverable → Component → L3 structure
- **Functionality**: Individual remove buttons for each level with cascading deletion
- **UI**: L3 chips grouped by parent component for clear visualization

### Timeline Accuracy Improvements
- **Business Days Calculation**: Uses `numpy.busday_offset()` and `numpy.busday_count()` with US/MX holiday calendar
- **Memorial Day Fix**: Corrected calculation to always land on the last Monday of May
- **XML Export**: Saturday and Sunday configured as non-working days (DayWorking=0) in Workfront-compatible calendar export
- **No Weekend End Dates**: All timeline calculations exclude weekends and holidays

## System Architecture

### Backend Architecture
- **Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data, calculations, and manipulations.
- **File Handling**: Supports parsing of PDF and DOCX documents, and Excel file uploads.
- **Core Logic**: Implements RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **CORS**: Configured to allow cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow.
- **Styling**: Uses CSS custom properties for theming, including a dark mode.
- **State Management**: Centralized `selectionStore` as single source of truth with Proxy-backed compatibility layer for legacy code paths.

### Data Storage Pattern
- **Primary Storage**: Excel/CSV files serve as the main source for business rules and configuration data.
- **Data Models**: In-memory DataFrames are loaded from spreadsheets to define tasks, deliverables, pricing rules, rate cards, timeline parameters, scaling factors, bundle configurations, hour allocations, and scenario templates.

### API Design
- Provides RESTful endpoints for data loading, options retrieval, and scenario generation.
- Supports file uploads for RFP documents and Excel configuration files.
- Uses JSON for configuration data and calculated scenario responses.
- Serves static files for frontend assets.

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

### File Format Support
- **Excel/CSV**: Core data source.
- **PDF/DOCX**: For RFP document parsing.
- **JSON**: For API data exchange.