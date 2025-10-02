# Agency Project Builder

## Overview

This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### UI Enhancements & Code Quality Improvements (October 2025)
- **AI Loading Indicator**: Added animated spinner that displays during RFP analysis (both file and text modes)
  - Shows immediately when analysis starts, hides when complete or on error
  - Implemented using CSS-only animation with spinning border for accessibility
- **Step 2 Search Filter**: Verified existing search functionality in deliverables picker
  - Search box filters deliverables in real-time as user types
  - Filters by deliverable name, category, and code
  - Implementation in app.js (line 953) re-renders list with filtered results
- **Dropdown Population Enhancement**: Updated `populateDropdown()` to use `replaceChildren()` instead of `innerHTML = ''`
  - Prevents duplicate options from appearing in dropdowns
  - Always ensures a valid selection (defaultValue or first option)
  - Handles edge cases: missing defaultValue, defaultValue not in options list, empty arrays
  - Uses matchFound flag to guarantee fallback to first option when needed
- **Cache Busting**: Updated static assets to v=5.5 to ensure browser reload of new features
- **Data Attributes**: Added null-safe `data-name` attribute to deliverable list items for consistency

### Retainer & Component Inflation Fixes (October 2025)
- **Retainer Zero-Month Fix**: Changed retainer map to use `max(0, min(12, ...))` instead of `max(1, ...)` to allow months=0 (one-time deliverables) without zeroing hours
- **Component Inflation**: Already implemented - `_inflate_components_if_missing()` called in `/api/build` (line 2767) and `build_wbs_with_pricing()` (line 1525) to prevent flat exports
- **None Hours Handling**: Added defensive check for None values in component hours dict (line 2676)

### Step 3 Payload Improvements (October 2025)
- **Simplified buildScenariosAB Function**: Refactored to read selected deliverables directly from DOM via `#yourSelection [data-code]` selector
- **data-code Attributes**: Added to selection items in `renderYourSelection()` for reliable DOM-based selection reading
- **Retainer Payload Fix**: Corrected retainer selector to `#retainer-list-controls input[type=number][data-code]` to properly capture configured months
- **Dropdown De-duplication**: Already implemented via `populateDropdown()` clearing innerHTML before re-populating
- **Auto-populated Project Names**: Already implemented to set project name from uploaded filename when input is empty

### GPT-5 Patches Implementation (October 2025)
- **Backend Enhancements**:
  - Added component inflation at start of `build_wbs_with_pricing()` to ensure AI picks always include full component trees
  - Implemented 480-minute (8-hour day) duration snapping for Workfront compatibility: `((minutes + 479) // 480) * 480`
  - Verified XML export hierarchy with Summary=1 for parents, OutlineLevel based on WBS depth, and no assignments on summary tasks
  - Confirmed retainer months properly multiply hours/price/duration through month-by-month repetition

- **Frontend Enhancements**:
  - Added project name auto-fill from `/api/last_upload_name` endpoint after AI analysis
  - Fixed `selected_components_map` payload in `s2ApplyAndBuild()` to properly send `"__ALL__"` sentinel for non-customized deliverables
  - Ensured consistent `"__ALL__"` sentinel handling between `buildFromCurrentSelection()` and `s2ApplyAndBuild()`
  - Verified AI spinner, search functionality, and component defaults all working correctly
  - Implemented "Refresh AI Suggestions" link to call `/api/suggest_by_text` using stored RFP text without re-upload
  - Enhanced AI Summary panel with Copy button (clipboard), Hide/Show toggle, and refresh functionality

- **Key Improvements**:
  - Prevents flat exports by ensuring all deliverables have component data before WBS building
  - Workfront-compatible durations eliminate fractional day display (e.g., "1.875d" now shows as "2d")
  - Project names auto-populate from uploaded filename without overriding user input
  - Component selection payload format matches backend expectations for proper inflation

### Component Selection Modal Fixes (October 2025)
- **Fixed TypeError Bug**: Resolved `current.has is not a function` error when opening component picker
  - Added type checking to handle `"__ALL__"` sentinel, Set objects, plain objects, and undefined values
  - Converts stored component selections to Set when opening modal
  - Defaults to all components selected when opening modal for first time or with `"__ALL__"` sentinel

- **Added Select All/Unselect All Buttons**: Enhanced component picker modal with bulk selection controls
  - Added "Select All" button to check all component checkboxes at once
  - Added "Unselect All" button to clear all component checkboxes
  - Both buttons update the internal `selectedComponentsMap` state in real-time
  - Modal now includes: title bar with Done button, Select All/Unselect All row, scrollable component list

- **Default Behavior**: Components are now pre-selected by default when opening the modal
  - Improves user experience by showing all components checked initially
  - User can then unselect specific components if needed
  - Aligns with `"__ALL__"` sentinel pattern used throughout the application

## System Architecture

### Backend Architecture
- **Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data, calculations, and manipulations.
- **File Handling**: Supports parsing of PDF and DOCX documents, and Excel file uploads.
- **CORS**: Configured to allow cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow.
- **Styling**: Uses CSS custom properties for theming, including a dark mode.
- **State Management**: Client-side caching for options and scenario data.

### Data Storage Pattern
- **Primary Storage**: Excel/CSV files serve as the main source for business rules and configuration data.
- **Data Models**: In-memory DataFrames are loaded from spreadsheets to define tasks, deliverables, pricing rules, rate cards, timeline parameters, scaling factors, bundle configurations, hour allocations, and scenario templates.

### Core Business Logic
- **RFP Analysis**: Extracts key information from RFPs to suggest deliverables.
- **Scenario Building**: Generates project scenarios with varying complexity and tier combinations.
- **Pricing Engine**: Calculates costs using blended or role-based rate bands.
- **Timeline Calculation**: Determines project duration, incorporating configurable slack.
- **Export Capability**: Generates Workfront-compatible project structures.

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

### Deployment Requirements
- **Static File Serving**: Handled by FastAPI.
- **File Upload Handling**: Processes multipart form data.
- **Cross-Origin Support**: Utilizes CORS middleware.