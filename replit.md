# Agency Project Builder

## Overview

This is a web-based Agency Project Builder that helps agencies create project estimates and timelines from RFPs (Request for Proposals). The system analyzes RFP content, suggests relevant deliverables, builds project scenarios with different complexity/tier combinations, calculates pricing based on role rates and hours, and generates timeline projections with slack considerations. It's designed to streamline the proposal creation process for creative and digital agencies.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### XML Export Component Hierarchy Fix & UI Enhancements (October 2025)
- **XML Export Fix**: Updated `_inflate_components_if_missing()` to handle `"__ALL__"` sentinel values
  - Function now populates `included_task_groups` when component map is empty or contains `"__ALL__"`
  - Ensures all exports contain full 6-level hierarchy: Project → Department → Deliverable → Component → Task → Role
  - Prevents flat exports with only deliverable-level data
  - Converts `"__ALL__"` sentinel to empty dict for downstream processing

- **Project Name Defaults**: Added `/api/last_upload_name` endpoint
  - Returns sanitized project name from most recent file upload
  - Uses existing `_upload_title_default()` helper for safe filename extraction
  - Frontend can prefill project name input in Step 3 with uploaded filename

- **Existing UI Features Verified**: Confirmed all component selection, search, and retainer functionality working
  - Component picker modal with event delegation on "Components..." buttons
  - Build payload correctly sends `selected_components_map` with `"__ALL__"` support
  - Deliverable names display using defensive `labelFor()` helper across all UI surfaces
  - Search bar filtering in Step 2 left panel
  - Retainer configuration panel using `labelFor()` for name resolution
  - Loading states on "Analyze with AI" button with disable/enable

### Front-End Deliverable Lookup Fix (October 2025)
- **Code→Name Lookup Index**: Implemented DELIV_INDEX for O(1) deliverable lookups
  - Global object maps deliverable codes to full deliverable data
  - Built during both boot() and s2LoadDeliverables() initialization
  - Helper functions labelFor(code) and categoryFor(code) provide safe access
  - Fallback to displaying raw code if lookup misses

- **Defensive Lookup Pattern**: Added case-insensitive fallback for robustness
  - DELIV_INDEX_LO provides lowercase key lookup for mixed-case codes
  - key(s) function normalizes strings (trim + lowercase)
  - fromAny(code) tries exact match first, then case-insensitive
  - Handles legacy slugs, trimming, and case differences gracefully

- **Fixed AI Suggestions Display**: AI-suggested deliverables now show friendly names
  - Previously showed codes (DEL-00xx) instead of names in "Your Selection" panel
  - renderYourSelection() updated to use helper functions instead of array.find()
  - renderRemovedItems() also updated for consistency
  - s2RenderLeft() uses labelFor()/categoryFor() instead of S2.selectedMeta
  - codeToName() in retainer panel uses labelFor() with defensive fallback
  - Works for both AI-suggested and manually selected deliverables
  - Proper escaping of single quotes in onclick attributes
  - DELIV_INDEX is now single source of truth for all deliverable display names

### Department Grouping & UI Enhancements (October 2025)
- **Search Functionality**: Added instant search to Step 2 deliverables panel
  - Search input filters by deliverable name, category, and service department
  - Real-time filtering with data-search attributes for fast performance
  - Wired through existing S2.els.search infrastructure

- **Service Department Grouping**: Deliverables organized by department in UI
  - Added Service Department and Sort_Order fields to /api/options endpoint
  - Step 2 left panel groups deliverables by department with visual headers
  - Departments ordered: Strategy, Creative, Content, Production, Technology, PM, Other
  - Within each department, deliverables sorted by Sort_Order then name

- **AI Component Defaults**: Auto-selected deliverables include all components by default
  - When adding deliverables from AI suggestions, sets component map to '__ALL__' sentinel
  - Ensures AI and manual flows produce consistent structure
  - User can still manually select specific components via "Components..." button

- **XML Export Department Hierarchy**: Complete implementation ✓
  - WBS builder enriches deliverables with Service Department metadata
  - Department summary rows added to export structure (WBS level 2: 1.1, 1.2, etc.)
  - Deliverables properly nested under departments (WBS level 3: 1.1.1, 1.1.2, etc.)
  - Components and tasks maintain full hierarchy depth
  - XML exports now show full structure: Department → Deliverable → Component → Task → Role
  - Fixed 250+ lines of indentation to properly nest all loops

### AI Summary & Enhanced Suggestions (October 2025)
- **AI Summary Panel**: Added comprehensive RFP summary display in Step 2
  - Shows 500-word prose summary generated from RFP analysis
  - Word count display to track summary length
  - Copy to clipboard functionality for easy sharing
  - Collapsible panel with Hide/Show toggle
  - Persistent storage in sessionStorage for cross-reload availability

- **Enhanced AI Suggestions**: Upgraded reconciliation interface with interactive controls
  - Replaced simple suggestion list with categorized Add/Delete/Unchanged groups
  - Accept/Remove buttons for each suggestion with real-time selection sync
  - "Selected ✓" badges show current selection state
  - Integrated with `/api/reconcile` endpoint for intelligent deliverable matching
  - AI deliverable labels compared against current DB selection
  - Refresh functionality updates suggestions based on current selections

- **Workflow Integration**: Seamless Step 1 → Step 2 transition
  - "Analyze with AI" button calls `/api/summarize` or `/api/summarize_by_file`
  - Summary and deliverable labels persisted for Step 2 rendering
  - Direct button wiring in boot() ensures reliable event handling
  - Reconciliation automatically runs when AI analysis completes

### Robust Component Handling Implementation (October 2025)
- **Client-Side Enhancement**: Ensured all selected deliverables send component data to backend
  - Updated `buildFromCurrentSelection()` to explicitly handle all deliverable codes
  - Sends "__ALL__" sentinel value for deliverables without specific component selections
  - Preserves explicit component selections in dictionary format with proper instanceof check
  - Fixed precedence bug in instanceof operator with proper parentheses
  
- **Server-Side Schema Update**: Enhanced BuildPayload model to accept sentinel values
  - Updated `selected_components_map` type to `Optional[Dict[str, Union[str, List[str], Dict[str, Optional[float]]]]]`
  - Now accepts "__ALL__" string sentinel in addition to legacy list and dict formats
  - Handler converts "__ALL__" → {} for downstream "include all" semantics
  
- **Defensive Inflation System**: Automatic task group population for incomplete scenario data
  - Added `DB.task_groups_for_deliverable()` helper method for database retrieval
  - Implemented `_inflate_components_if_missing()` function that populates missing `included_task_groups`
  - Integrated inflation into `/api/build` (pre-storage) and all export endpoints
  - Prevents flat exports by guaranteeing hierarchical deliverable→component→task structure
  - WBS builder now guaranteed to produce detailed structure (1,000+ lines) for all scenarios

### Component-Level Selection & Export Robustness (September 2025)
- **Component-Level Selection Feature**: Complete implementation of granular deliverable component control in Step 2
  - Added `/api/components_for` endpoint for retrieving components with hours breakdown by deliverable
  - Enhanced BuildPayload model with `selected_components_map` field for per-deliverable component selections
  - Updated backend logic to filter scenarios based on selected components with intelligent fallbacks
  - Implemented modal picker UI with "Components..." button showing checkboxes and hour counts
  - Global `selectedComponentsMap` state management across all build operations
  - Component count display in deliverable selection UI when components are chosen

- **Export Robustness Enhancements**: Bulletproof XML/Excel exports with automatic data synthesis
  - Auto-generation of missing task groups from database when scenario data is incomplete
  - Schedule synthesis using `DB.build_schedule` when schedules are missing from scenarios
  - Hours by role derivation from raw database when scenario calculations are incomplete
  - Enhanced deliverable name resolution with robust database fallbacks
  - Export validation guards to prevent empty scenario exports
  - WBS builder guarantees detailed structure generation (1,000+ lines, 28+ resources)

### v3 Drivers Support Implementation Complete (September 2025)
- **Backend Implementation**: Added v3 Drivers support with complete token normalization and mapping functionality
  - Added helper methods to AgencyDB class: `_norm_token`, `_v4_complexity_tokens`, `_v4_tier_tokens`, `_map_to_v4_token`, and `drivers_complexities_tiers_v3`
  - Updated `/api/options` endpoint to provide exactly 3 standardized options each for complexity, tiers, and rate bands
  - Enhanced `scenario_hours_col` method to handle v3 labels mapping to v4 columns with intelligent fallback
  - Implemented robust fallback logic when no v3 Excel file is available, using v4 data with 3-option limits

- **Frontend Enhancement**: Complete UI integration for v3 Drivers functionality  
  - Converted Rate Band input field to dropdown and added Complexity and Volume Tier dropdowns
  - Updated JavaScript to populate all dropdowns from `/api/options` API data with smart defaults
  - Modified `buildFromSuggestions` and `regenerateWithEdits` functions to send selected values to `/api/build`
  - All dropdowns now provide exactly 3 options: Complexities (Core/Advanced/Complex), Tiers (T1/T2/T3), Rate Bands (Standard_US/Premium_US/Nearshore_Value)

- **Integration Testing**: Full end-to-end validation confirms proper functionality
  - API returns exactly 3 options per category as designed
  - Backend correctly processes complexity and tier overrides in scenario specifications
  - Pricing calculations work correctly with v3 parameter combinations  
  - System maintains backward compatibility through intelligent v4 column mapping

## System Architecture

### Backend Architecture
- **Framework**: FastAPI with Python for REST API backend
- **Data Processing**: Pandas DataFrames for Excel/CSV data manipulation and calculations
- **File Handling**: Support for document parsing (PDF, DOCX) and Excel file uploads
- **CORS**: Configured for cross-origin requests to support frontend-backend separation

### Frontend Architecture  
- **Technology**: Vanilla JavaScript with HTML/CSS (no framework dependencies)
- **UI Pattern**: Single-page application with step-based workflow
- **Styling**: CSS custom properties for theming with dark mode design
- **State Management**: Client-side caching of options and scenarios data

### Data Storage Pattern
- **Primary Storage**: Excel/CSV files containing business rules and configuration data
- **Data Models**: In-memory DataFrames loaded from spreadsheets including:
  - Task and deliverable definitions
  - Pricing rules and rate cards  
  - Timeline parameters and scaling factors
  - Bundle configurations and hour allocations
  - Scenario templates and defaults

### Core Business Logic
- **RFP Analysis**: Text parsing to suggest relevant deliverables
- **Scenario Building**: Multiple complexity/tier combinations (e.g., MED_LOW vs MED_HIGH)
- **Pricing Engine**: Support for blended rates or role-based rate bands
- **Timeline Calculation**: Project duration with configurable slack factors
- **Export Capability**: Workfront-compatible project structure generation

### API Design
- RESTful endpoints for data loading, options retrieval, and scenario generation
- File upload support for RFP documents and Excel configuration files
- JSON responses for configuration data and calculated scenarios
- Static file serving for frontend assets

## External Dependencies

### Python Libraries
- **FastAPI**: Web framework for API development
- **Pandas**: Data manipulation and analysis for Excel/CSV processing
- **NumPy**: Numerical computing support
- **OpenPyXL**: Excel file reading and writing
- **PDFPlumber**: PDF document text extraction
- **python-docx**: Word document processing
- **Jinja2**: Template engine for report generation
- **Uvicorn**: ASGI server for FastAPI deployment

### File Format Support
- **Excel/CSV**: Primary data source for business rules and configurations
- **PDF/DOCX**: RFP document parsing for automated deliverable suggestion
- **JSON**: API data exchange format

### Deployment Requirements
- **Static File Serving**: Frontend assets served through FastAPI
- **File Upload Handling**: Multipart form data processing for document uploads
- **Cross-Origin Support**: CORS middleware for browser compatibility