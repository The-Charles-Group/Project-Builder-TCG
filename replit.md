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
- **XML Post-Processing**: Automatically parallelizes same-name tasks in MSPDI XML exports to prevent artificial serialization of parallel work streams.
- **CORS**: Configured to allow cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow.
- **Styling**: Uses CSS custom properties for theming, including a dark mode.
- **State Management**: Client-side caching for options and scenario data.

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
- **MSPDI XML**: Microsoft Project format with automatic parallelization post-processing.

## Recent Changes

### October 2025
- **Database Export Tool**: Added `export_db_v3_v4.py` script to export v3 and v4 databases to Excel workbooks (accessible via `/downloads` endpoint).
- **XML Parallelization**: Integrated automatic post-processing of XML exports to remove same-name task dependencies, enabling parallel execution of duplicate task names (e.g., multiple "Examples per Pillar" tasks). Controlled by `PARALLELIZE_IDENTICAL_NAMES` environment variable (default: enabled).
- **Download Endpoint**: Added `/downloads` page for easy browser-based downloading of exported database files.