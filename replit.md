# Agency Project Builder

## Overview
This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- Single-page application with a step-based workflow.
- Uses CSS custom properties for theming, including a dark mode.
- 3-column layout (Deliverables | Components | Summary) with search functionality and enhanced summary panel.
- Unified AI Planner UI with real-time progress bar, evidence-backed suggestions, and risk indicators.
- "Select All/Deselect All" buttons and department grouping for deliverables.
- UI toggle for optional inclusion of Start/End anchor milestones in XML exports.

### Technical Implementations
- **Backend Framework**: FastAPI (Python).
- **Data Processing**: Pandas DataFrames for Excel/CSV data; PDFPlumber and python-docx for RFP parsing.
- **Core Logic**: RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **SCENARIO_STORE Architecture**: Dual-entry session-based data store with immutable `baseline` and mutable `working` scenarios. Step 3 working scenario is the authoritative source for all pricing, timeline, and export operations.
- **AI Planner v3**: Advanced reasoning-based AI layer (GPT-5 + AgencyDB) for granular task selection and holistic project flow analysis.
- **GPT 5.1 Pro Enhancements**: Structured RFP summaries, curated L3 task selection, and consistent Gantt/XML export through a single source of truth (`compress_deliverable_timeline()`). Includes specific logic for first L2 deliverable SNET constraint and child-task dependency filtering.
- **Timeline Scheduler Kit**: AI-powered timeline optimization with Microsoft Project XML parsing, smart dependencies, and multi-format export.
- **Workfront Integration**: Exports a 3-Level Workfront Hierarchy (Deliverable → Component → Task) with WBS codes and manual scheduling tags. Includes features for Gantt timeline date preservation and manual scheduling lock.
- **PM-Brain Capacity Scheduling**: Capacity-based timeline scheduling with resource leveling and realistic dependencies.
- **WBS-Based Dependencies + Multi-Assignment Export**: Feature-flagged system for dependency management and parallel role execution.
- **Chronological Waterfall Export**: Production-ready XML export system creating simple, chronological Gantt timelines in Workfront, flattening the WBS hierarchy to prioritize chronological flow over department grouping. Includes an L5+ Edge Filtering System and Sibling Auto-Chaining System for dependency management.
- **Tight Waterfall Scheduling System**: Feature-flagged L2 deliverable scheduling that eliminates work-wait-work gaps in Workfront using specific ConstraintType and DurationFormat settings.
- **Unified Pricing Data Flow**: Ensures the backend is the single source of truth for all pricing operations through a `syncScenarioToBackend()` and `rebuildPricingFromBackend()` pipeline.
- **GPT 5.1 Pro Step 3 Pricing Edit Preservation**: Preserves user edits to hours/rates in Pricing Details when Build Scenario is clicked on Step 3, using `initPricingStep()`, `updateScenarioItem()`, and `collectScenarioFromUi()`.
- **Component-to-Deliverable Cascade Pricing System**: Real-time cascade update system ensuring component edits flow through to deliverable totals, `SCENARIO_A`, and summary, using `updateDeliverableTotalFromComponents()` and `_lastKnownRate` caching.
- **Pre-Export Sync Pipeline**: Ensures DOM edits reach exports through a rewritten `collectScenarioFromUi()` that reads all hours/rates from DOM inputs, updates global scenarios, and syncs to the backend before export functions.
- **Component-Level Hours Tracking System**: Granular component-level pricing overrides allowing users to edit individual component hours, which automatically cascade totals to parent deliverables. This includes specific functions for finding scenario items, applying pricing edits, and event delegation.
- **Component-Hours Preservation Guards**: Three-part protection ensuring `component_hours` survive the collect→sync→export pipeline without DOM overwrites, including specific logic for using component hours sum and skipping DOM hydration.
- **Deliverable Hours Component Sum Fix**: Both `updatePricingTable()` and `updatePricingDisplay()` now calculate deliverable hours from component sum on initial render, ensuring consistency across pricing tables.
- **Component Hours Cascade Fix (Dec 2025)**: Fixed critical bug where editing one component (e.g., 33→34h) caused parent deliverable totals to collapse (306h→34h). Root cause: `collectScenarioFromUi` was recalculating parent hours from sparse `component_hours` map. Fix: Copy already-correct parent hours from `liveItem` (set by `updateDeliverableTotalFromComponents`) using nullish coalescing to preserve explicit zeros. Backend `get_hours_from_item` now prioritizes standard hour fields over component_hours sum.
- **Pricing Summary Synchronization Fix (Dec 2025)**: Fixed critical bug where three displays showed different values (Pricing Details: 306h/$64,260, One-Time summary: 302h/$63,420, Grand Total: $63,000). Root cause: `recalculatePricingSummary()` read stale scenario totals while `updatePricingDisplay()` used original_price snapshot. Fix: `recalculatePricingSummary()` now calculates hours from component sum using the same priority chain (pricingData customHours → component_hours → component defaults) and derives price from hours × rate. `updatePricingDisplay()` Grand Total now uses current prices instead of frozen original_price.
- **Parallel Processing**: Utilizes OpenAI Vision API for parallel PDF image processing.
- **Smart Image Analysis**: Two-tier image processing system with pre-filtering and deep analysis.
- **Session Isolation System**: Complete data isolation between different RFPs using unique session IDs.
- **CORS**: Configured to allow cross-origin requests.

### System Design Choices
- **Data Storage Pattern**: Excel/CSV files as primary source for business rules and configuration, loaded into in-memory DataFrames.
- **API Design**: RESTful endpoints for data loading, options retrieval, scenario generation, file uploads, and static file serving.
- **Database Configuration**: Automatic switching based on environment (Replit's PostgreSQL for development, separate production database). Uses `Replit_App_DB_READABLE_FullRows_v3.xlsx` loaded into `app.state.db` at startup with pickle caching.

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