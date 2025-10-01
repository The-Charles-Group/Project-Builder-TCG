# Agency Project Builder

## Overview
This web-based Agency Project Builder streamlines the proposal creation process for creative and digital agencies. It analyzes RFPs to suggest deliverables, builds project scenarios with varying complexity and tiers, calculates pricing based on role rates and hours, and generates timeline projections with slack. The system aims to provide comprehensive project estimates and timelines efficiently.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: FastAPI with Python.
- **Data Processing**: Pandas DataFrames for Excel/CSV manipulation.
- **File Handling**: Supports PDF and DOCX parsing, and Excel file uploads.
- **CORS**: Configured for cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow.
- **Styling**: CSS custom properties for theming, including dark mode.
- **State Management**: Client-side caching for options and scenario data.

### Data Storage Pattern
- **Primary Storage**: Excel/CSV files for business rules and configurations.
- **Data Models**: In-memory DataFrames loaded from spreadsheets, defining tasks, deliverables, pricing, timelines, bundles, and scenarios.

### Core Business Logic
- **RFP Analysis**: Extracts key information from RFPs to suggest deliverables.
- **Scenario Building**: Generates project scenarios with different complexity and tier combinations.
- **Pricing Engine**: Calculates costs using blended or role-based rate cards.
- **Timeline Calculation**: Determines project durations, incorporating configurable slack factors.
- **Export Capability**: Generates Workfront-compatible project structures.

### API Design
- **Endpoints**: RESTful API for data loading, options retrieval, and scenario generation.
- **File Uploads**: Supports RFP documents and Excel configuration files.
- **Responses**: JSON format for configuration and calculated scenario data.
- **Static Files**: Serves frontend assets.

### UI/UX Decisions
- **Step-based workflow**: Guides users through the proposal creation process.
- **Three-Panel Design for Step 2**: Left for deliverable picker, Middle for selected items, Right for AI suggestions.
- **Granular Component Selection**: Allows detailed control over deliverable components within Step 2.

### Technical Implementations
- **XML Export Validations (v2.9)**: Includes rigorous checks for Workfront compatibility:
  - Units ≤ 1.0 enforcement with automatic duration adjustment
  - Ceil rounding policy for whole-day durations
  - Cycle detection and removal using Kahn's algorithm
  - Leaf-only predecessor links (summary tasks filtered)
  - Smart date handling (Start/Finish only on summary tasks)
  - WBS canonicalization with 1-based OutlineLevel calculation (root=1, deliverable=2, component=3)
  - Proper MSPDI hierarchy with correct indentation in Workfront
- **XML Export Enhancements**: Proper summary task handling (Summary=1 for parents, Work=PT0M), ASAP constraints (ConstraintType=0), optional whole-day duration rounding, and consistent date/duration calculations.
- **v3 Drivers Support**: Implemented for token normalization and mapping in the backend, with a corresponding UI integration for complexity, tiers, and rate bands.

### Feature Specifications
- **Component-Level Selection**: Enables users to select specific components within deliverables, impacting scenario generation.
- **Export Robustness**: Automatic data synthesis for missing task groups, schedules, and hours by role, ensuring complete and valid exports.

## External Dependencies

### Python Libraries
- **FastAPI**: For web framework.
- **Pandas**: For data manipulation.
- **NumPy**: For numerical operations.
- **OpenPyXL**: For Excel file I/O.
- **PDFPlumber**: For PDF text extraction.
- **python-docx**: For Word document processing.
- **Jinja2**: For templating.
- **Uvicorn**: For ASGI server.

### File Format Support
- **Excel/CSV**: Primary data source.
- **PDF/DOCX**: For RFP document parsing.
- **JSON**: For API data exchange.

### Deployment Requirements
- **Static File Serving**.
- **File Upload Handling**.
- **Cross-Origin Support**.