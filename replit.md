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
- **GPT-5 Enforcer System**: Ensures exclusive use of GPT-5 for AI operations.
- **GPT 5.1 Pro RFP Summary**: Structured RFP summaries rendered in the frontend, consuming `summary_bullets` from the backend.
- **GPT 5.1 Pro Smart Selection L3 Filtering**: Curated L3 task selection system ensuring only AI-vetted tasks are presented in Step 3.
- **Timeline Scheduler Kit**: AI-powered timeline optimization with Microsoft Project XML parsing, smart dependencies, and multi-format export.
- **Workfront Integration**: Exports a 3-Level Workfront Hierarchy (Deliverable → Component → Task) with WBS codes and manual scheduling tags.
- **PM-Brain Capacity Scheduling**: Capacity-based timeline scheduling with resource leveling and realistic dependencies.
- **Gantt Timeline Date Preservation**: Preserves user-edited deliverable dates during XML export.
- **Workfront Manual Scheduling Lock**: Prevents Workfront from recalculating user-edited deliverable dates on XML import.
- **WBS-Based Dependencies + Multi-Assignment Export**: Feature-flagged system for dependency management and parallel role execution.
- **Chronological Waterfall Export**: Production-ready XML export system creating simple, chronological Gantt timelines in Workfront, flattening the WBS hierarchy to prioritize chronological flow over department grouping.
- **L5+ Edge Filtering System**: Filters out role-to-role dependencies (L5+ to L5+) in XML export, maintaining summary-level waterfall structure.
- **Sibling Auto-Chaining System**: Automatically generates waterfall dependencies for summary-level siblings (L2 deliverables, L3 components, L4 tasks) within each parent group, connecting consecutive siblings chronologically.
- **Tight Waterfall Scheduling System (Dec 2025)**: Feature-flagged L2 deliverable scheduling that eliminates work-wait-work gaps in Workfront. Controlled by `TIGHT_WATERFALL_ENABLED` flag (default: `true`). When enabled: L2 deliverables use ConstraintType=0 (ASAP), DurationFormat=7 (auto-scheduled), ManuallyScheduled=0 (explicit). 4-step pipeline: Step A collects L2 deliverable UIDs; Step B runs pre-chain cleanup removing existing L2→L2 PredecessorLinks; Step C builds clean FS chain (first deliverable has no predecessor, subsequent have exactly one); Step D runs sanity check raising ValueError to abort export if any deliverable has >1 predecessor. Milestones excluded via Milestone flag, PT0M duration, or keywords. Set `TIGHT_WATERFALL_ENABLED = False` for legacy SNET behavior.
- **GPT 5.1 Pro Enhancements (Dec 2025)**: Three-part implementation ensuring Step-4 Gantt and XML export consistency: (1) Single Source of Truth - `compress_deliverable_timeline()` now feeds both Step-4 Gantt and XML export via `compressed_timeline` parameter, ensuring identical dates; (2) First Deliverable Exception - First L2 deliverable gets SNET (ConstraintType=5) + ConstraintDate for project kick-off gate, subsequent deliverables get ASAP (ConstraintType=0) for tight waterfall scheduling; (3) Child-Task Dependency Filtering - L3+ cross-deliverable predecessors are filtered out, keeping only intra-deliverable dependency chains to prevent Workfront from recalculating child task dates based on external predecessors.
- **Unified Pricing Data Flow (Dec 2025)**: Single codepath for all pricing operations ensuring backend is source of truth. Implementation: (1) `syncScenarioToBackend()` POSTs to `/api/scenario/sync` to update SCENARIO_STORE; (2) `rebuildPricingFromBackend()` calls sync first (if scenario provided), then `/api/pricing/rebuild_breakdown` for authoritative totals; (3) Build Scenario button (`buildScenariosAB`) now calls `rebuildPricingFromBackend(scenarios.A)` at end for backend-aligned Step 3 load; (4) "Save & View Totals" button removed - Build Scenario handles all pricing sync; (5) Export triggers (Excel/XML) call `syncScenarioToBackend()` before invoking export endpoints to ensure SCENARIO_STORE freshness.
- **GPT 5.1 Pro Step 3 Pricing Edit Preservation (Dec 2025)**: Preserves user edits to hours/rates in Pricing Details when Build Scenario is clicked on Step 3. Key components: (1) `initPricingStep()` loads existing working scenario from backend on page load/refresh, hydrating `window.SCENARIO_A`; (2) `updateScenarioItem()` modifies `window.SCENARIO_A.items` when user edits hours/rate in Pricing Details panel; (3) `collectScenarioFromUi()` updates ONLY scenario-level metadata (project_start, pricing_mode, rate_band), NOT items; (4) `onStep3BuildScenarioClick()` uses collectScenarioFromUi + syncScenarioToBackend to persist edits; (5) Build Scenario button on Step 3 detects existing scenario and routes to edit-preserving handler instead of buildScenariosAB; (6) `pricingDetailsDirty` flag tracks unsaved edits; (7) 422 errors from `/api/scenarios` are handled gracefully for fresh sessions.
- **Component-to-Deliverable Cascade Pricing System (Dec 2025)**: Real-time cascade update system ensuring component edits flow through to deliverable totals, SCENARIO_A, and summary. Key features: (1) `updateDeliverableTotalFromComponents()` sums all component hours and recalculates deliverable price in real-time; (2) `window.pricingData` exposed globally for cross-file access to delta tracking maps; (3) Rate resolution priority: SCENARIO_A rate fields → `_lastKnownRate` cache → derived rate from price/hours → pricingData customRates → DOM inputs → 210 fallback; (4) `_lastKnownRate` caching prevents stale rate calculations on subsequent edits; (5) `recalculatePricingSummary()` updates One-Time/Grand Total displays with fractional hour precision (.toFixed(1)); (6) Both `updateComponentPricingHours()` and `updateComponentPricingRate()` trigger the cascade; (7) `onUpdatePricingDetailsClick()` syncs already-updated SCENARIO_A to backend without delta re-application.
- **Pre-Export Sync Pipeline (Dec 2025)**: Complete collect→sync→export pipeline ensuring DOM edits reach exports. Implementation: (1) `collectScenarioFromUi()` REWRIITEN to deep-clone scenario and read ALL hours/rates from DOM inputs (`#hours-${code}`, `#rate-${code}` for deliverables; component rows via `[data-component]` selector), then RETURNS the updated scenario; (2) `ensureScenarioSyncedBeforeExport()` calls collectScenarioFromUi, uses returned value to update local `scen` and global `window.SCENARIO_A`, then syncs to backend; (3) All export functions (`onExportScenario`, `onExportXMLScenario`, `exportPricingDetails`, `exportScenario`, `onExport`) use `let` for scenario variables, reassign to `window.SCENARIO_A` after sync for Scenario A exports, and send the UPDATED scenario in their payloads. Critical pattern: DOM edits → collectScenarioFromUi() RETURNS updated scenario → update globals → sync to backend → export with synced data.
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