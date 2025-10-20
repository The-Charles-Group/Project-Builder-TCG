# Agency Project Builder - Production Ready

## Overview
This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation.

## User Preferences
Preferred communication style: Simple, everyday language.

## Development Principles
**CRITICAL**: This project follows strict development principles documented in `DEVELOPMENT_PRINCIPLES.md`:
- **Never destroy functionality to simplify code** - Always debug and fix the root cause
- **Preserve all user features** - Component selections, L2 tasks, retainers, state management, etc.
- **Build additional code if needed** - Add more logic/features to solve problems properly
- **Debug thoroughly before changing** - Identify root causes with comprehensive logging
- **Test completely** - Verify all features work after fixes

## Naming Conventions
**Hierarchy Levels**: The system uses a 3-level hierarchy for project structure:
- **Deliverables** (Level 0): Top-level project deliverables (e.g., "Social Media Campaign", "Website Redesign")
- **Components/L1** (Level 1): Sub-components within deliverables (e.g., "Content Strategy", "Visual Design")
- **Tasks/L2** (Level 2): Individual tasks within components (e.g., "Create Mood Board", "Design Hero Section")

All code, API endpoints, and documentation use L1 for components and L2 for tasks to maintain consistency.

## System Architecture

### Backend Architecture
- **Framework**: FastAPI (Python) for the REST API.
- **Static File Serving**: Root route (`@app.get("/")`) serves index.html from static directory; static files mounted at `/static` endpoint.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data.
- **File Handling**: Supports parsing of PDF and DOCX documents, and Excel file uploads.
- **Core Logic**: Implements RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **SCENARIO_STORE Architecture**: Centralized session-based data store for pricing, timeline, and Gantt synchronization, ensuring all edits operate on the same canonical scenario data. Includes automatic totals recalculation.
- **AI Planner v3 (GPT-5 + AgencyDB)**: Advanced reasoning-based AI layer for granular task selection, asynchronous processing, real-time progress updates, holistic project flow analysis, and evidence-based matching with calibrated confidence scores. Incorporates smart multipliers and auto-relaxation/rescue logic.
- **GPT-5 Enforcer System**: Centralized model enforcement that blocks all non-GPT-5 models, auto-converts Chat Completions API calls to Responses API, and enforces allowed GPT-5 models through `sitecustomize.py`.
- **Timeline Scheduler Kit**: AI-powered timeline optimization with Microsoft Project XML parsing, smart SS+lag overlaps, gatekeeper preservation, cycle breaking, duration rounding, and multi-format export.
- **Parallel Processing**: Utilizes OpenAI Vision API for parallel PDF image processing with job tracking, retry logic, and error handling.
- **Smart Image Analysis**: Two-tier image processing system using pre-filtering, quick relevance scans (GPT-5), and deep analysis for relevant images to optimize processing time and cost.
- **Database Architecture**: Primary database (`Replit_App_DB_READABLE_FullRows_v4.xlsx`) loaded into `app.state.db` during server startup, containing 24 configuration sheets and handling backwards compatibility.
- **Session Isolation System**: Complete data isolation between different RFPs using unique session IDs, auto-clear mechanisms, session-scoped embedding caches with a 24-hour TTL, and hourly background cleanup.
- **CORS**: Configured to allow cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow focused on a single scenario.
- **Styling**: Uses CSS custom properties for theming, including a dark mode.
- **State Management**: Centralized `selectionStore` with Proxy-backed compatibility layer.
- **UI Improvements**: Features a 3-column layout (Deliverables | Components | Summary), search functionality, enhanced summary panel, and new unified AI Planner UI with real-time progress bar, evidence-backed suggestions, and risk indicators. Includes "Select All/Deselect All" buttons and department grouping for deliverables.
- **Timeline Accuracy**: Incorporates business days calculation with US/MX holiday calendar and excludes weekends.
- **XML Export Control**: UI toggle for optional inclusion of Start/End anchor milestones in XML exports.

### Data Storage Pattern
- **Primary Storage**: Excel/CSV files serve as the main source for business rules and configuration data.
- **Data Models**: In-memory DataFrames are loaded from spreadsheets to define tasks, deliverables, pricing rules, rate cards, timeline parameters, scaling factors, bundle configurations, hour allocations, and scenario templates.

### API Design
- Provides RESTful endpoints for data loading, options retrieval, and scenario generation.
- Supports file uploads for RFP documents and Excel configuration files.
- Uses JSON for configuration data and calculated scenario responses.
- Serves static files for frontend assets.
- Includes endpoints for weighted AI suggestions, bulk L2 task retrieval, and scenario refetching.
- **Key API Endpoints**: `/api/l2`, `/api/step2/l2`, `/api/step2/l2/bulk` for L2 task operations.

### Database Configuration
- **Automatic Switching**: Automatic database switching based on the environment (Replit's built-in PostgreSQL for development, separate production database when published).
- **Connection Helper**: `database.py` module provides helper functions for managing database connections.
- **Models**: Database models should be defined in `models.py`.

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

## Planned Enhancements

### Dual OpenAI API Key Configuration (NOT YET IMPLEMENTED)
**Status**: Planned - To be implemented later

**Objective**: Configure the application to support two different OpenAI API keys for optimized cost and performance management:
- **Standard Tier Key**: For routine operations at standard rates and speed
- **Priority Processing Key**: For critical, time-sensitive operations at premium rates with guaranteed low latency

**Key Findings from Research**:
- OpenAI enforces rate limits at the **organization level**, not per API key
- Multiple keys from the same organization share the same rate limit pool
- Priority Processing requires an **OpenAI Enterprise account**
- Priority tier is activated using `service_tier="priority"` parameter in API calls
- Same API key can handle both standard and priority requests
- Priority Processing offers:
  - Lower latency and more consistent performance
  - Enhanced SLA (99.9% uptime for enterprise)
  - Premium pricing (exact markup negotiated with OpenAI)
  - Strict ramp rate limits to maintain quality

**Implementation Approach** (when ready):
1. Store two API keys as Replit secrets:
   - `OPENAI_API_KEY_STANDARD` - for routine calls
   - `OPENAI_API_KEY_PRIORITY` - for mission-critical calls (if different org)
2. Implement smart routing logic to determine which tier to use based on:
   - Request type (GPT-5 deep analysis vs routine tasks)
   - User tier (premium customers vs standard)
   - Time sensitivity (real-time UI updates vs background processing)
3. Add `service_tier` parameter to API calls
4. Monitor usage dashboard to track costs per tier
5. Consider alternative tiers for cost optimization:
   - **Batch Processing**: 50% cheaper for non-urgent background jobs
   - **Flex Processing**: ~50% cheaper for internal tools

**Use Cases**:
- Standard tier: Routine deliverable matching, basic RFP analysis, cached results
- Priority tier: Real-time GPT-5 deep analysis, live timeline optimization, critical user-facing features

**Requirements**:
- Verify OpenAI account tier and enterprise status
- Review Terms of Service for multi-organization usage
- Implement usage tracking and cost monitoring
- Add configuration UI for tier selection preferences

**Notes**:
- DO NOT implement until other priority items are completed
- Requires coordination with OpenAI account team if pursuing enterprise features
- Consider cost-benefit analysis before implementation