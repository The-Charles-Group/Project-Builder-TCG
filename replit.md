# Agency Project Builder

## Overview

This is a web-based Agency Project Builder that helps agencies create project estimates and timelines from RFPs (Request for Proposals). The system analyzes RFP content, suggests relevant deliverables, builds project scenarios with different complexity/tier combinations, calculates pricing based on role rates and hours, and generates timeline projections with slack considerations. It's designed to streamline the proposal creation process for creative and digital agencies.

## User Preferences

Preferred communication style: Simple, everyday language.

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