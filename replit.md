# Agency Project Builder

## Overview

This is a web-based Agency Project Builder that helps agencies create project estimates and timelines from RFPs (Request for Proposals). The system analyzes RFP content, suggests relevant deliverables, builds project scenarios with different complexity/tier combinations, calculates pricing based on role rates and hours, and generates timeline projections with slack considerations. It's designed to streamline the proposal creation process for creative and digital agencies.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### Step 2 Workflow Redesign (September 30, 2025)
- **Removed Confusing "Get AI Suggestions" Button**: Eliminated the secondary button that required analysis data (which should already exist after Step 1)
- **Streamlined AI Integration**: Step 1 now calls `/api/auto_build` to get both scenarios AND AI suggestions in one call
- **Three-Panel Design**:
  - Left: Deliverable picker (all database deliverables with search/filter)
  - Middle: Your Selection (final merged selection with component controls)
  - Right: AI Suggestions (pre-populated from Step 1 analysis, with checkboxes)
- **Clear Merge Workflow**: "Apply selection" merges Left + Right panels into Middle (Your Selection)
- **Single Source of Truth**: "Proceed to Pricing" builds only from Middle panel selections
- **Improved Help Text**: Updated Step 2 instructions to reflect new workflow: select left → check AI right → apply → configure components → proceed

### Step 2 Production Integration Complete (September 30, 2025)
- **Single Source of Truth**: Established S2 object as authoritative state for deliverable selection and component granularity
  - S2.selectedCodes (Set) tracks selected deliverable codes
  - S2.componentsByDeliv (Map) tracks per-deliverable component selections ('ALL' or Set)
  - Made globally accessible via window.S2 for cross-file integration

- **State Flow Integration**: Complete bidirectional synchronization across workflow
  - AI suggestions → S2 hydration on initStep2() with automatic component defaults
  - S2 → appState sync on every selection change (apply/remove)
  - Pre-checked deliverables rendering based on S2.selectedCodes
  - Component modal with Set-based selection and array serialization for API

- **Unified Payload Building**: Single buildPayloadForApi() function eliminates code duplication
  - Accepts optional overrides for scenario specs, retainers, and pricing settings
  - Uses helper functions for Slack settings (getSlack*FromUI) ensuring consistency
  - Globally accessible for reuse across Step 2 and Step 3 build flows
  - buildScenariosAB() now uses unified builder instead of manual payload construction

- **Step 2 Action Bar**: Primary workflow controls with sticky positioning
  - "Proceed to Pricing" button builds scenarios directly from S2 state (no silent AI merges)
  - "Get AI Suggestions" button calls /api/reconcile for ADD/DELETE recommendations
  - AI suggestions render in right panel with explicit Apply button for user control
  - Console logging tracks selected_deliverable_codes and selected_components_map for debugging

- **Bug Fixes and Cleanup**: Resolved critical state management issues
  - Removed legacy renderDeliverableList(items) function causing override collision
  - Fixed Set.length → Set.size for proper collection size checks
  - Changed implicit global to explicit window.selectedCodes declaration
  - Eliminated 700+ lines of conflicting legacy Step 2 code

- **Developer Experience**: Added console verification helper
  - verifyS2() function for real-time state inspection
  - Shows selected deliverables, component selections, and payload preview
  - Accessible from browser console for QA and debugging

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