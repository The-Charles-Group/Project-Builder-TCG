# Agency Project Builder - Production Ready

## Overview
This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- Single-page application with a step-based workflow focused on a single scenario.
- Uses CSS custom properties for theming, including a dark mode.
- 3-column layout (Deliverables | Components | Summary), search functionality, enhanced summary panel.
- Unified AI Planner UI with real-time progress bar, evidence-backed suggestions, and risk indicators.
- "Select All/Deselect All" buttons and department grouping for deliverables.
- UI toggle for optional inclusion of Start/End anchor milestones in XML exports.

### Technical Implementations
- **Backend Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data.
- **File Handling**: Parses PDF, DOCX, and Excel files.
- **Core Logic**: Implements RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **SCENARIO_STORE Architecture (Nov 2025)**: Dual-entry session-based data store with immutable `baseline` (from Step 2) and mutable `working` scenario (for Step 3 edits). Session structure: `{baseline, scenario, totals, metadata}`. Key endpoints: PATCH `/api/pricing/scenario/item` (supports both deliverable and component-level edits via optional `component_id`), POST `/api/pricing/rebuild_breakdown` (recalculates totals from working scenario only), POST `/api/pricing/reset_from_step2` (deep-copies baseline to working). All exports read from `get_working_scenario()` to preserve Step 3 pricing edits. Migration layer in `get_session_state()` auto-converts legacy single-entry format to dual-entry with independent deep copies. **GPT-5 Pro Single Source of Truth (Nov 26, 2025)**: Implemented canonical access pattern where Step 3 working scenario is the authoritative source for all pricing, timeline, and export operations. Key helpers: `get_working_scenario()` returns live object for direct mutation (auto-clones from baseline if missing), `make_item_key()` uses pipe-separated format (deliverable|component|task) for canonical matching. `_get_scenarios()` calls `get_session_state()` unconditionally to ensure migration runs before export. Updated 5+ endpoints to use `get_working_scenario()` instead of direct SCENARIO_STORE access: `/api/pricing/optimize`, `/api/pricing/cadence_suggestion`, `/api/pricing/retainer_suggestions`, `/api/timeline/update_task`, `/api/timeline/update_tasks_batch`. This ensures Step 3 edits (hours, rates, dates) persist through rebuilds, exports, and timeline updates.
- **AI Planner v3**: Advanced reasoning-based AI layer (GPT-5 + AgencyDB) for granular task selection, asynchronous processing, and holistic project flow analysis.
- **GPT-5 Enforcer System**: Centralized model enforcement ensuring exclusive use of GPT-5, converting Chat Completions to Responses API, and enforcing allowed models.
- **GPT 5.1 Pro RFP Summary (Dec 2025 - Bradley Spec)**: Frontend `renderRfpSummary()` consumes structured `summary_bullets` array from backend (3-6 bullets guaranteed, each with `{label, short_desc}`). Renders as `<ul class="rfp-summary-list">` with `<strong>Label</strong> — description` format. Uses inline styles with `!important` for guaranteed bullet visibility (`display: list-item`, `list-style: disc outside`). Enforces minimum 3 bullets with fallback placeholders (Strategy/Creative/Execution). Layout per Bradley spec: Summary bullets → Key Deliverables list → Channels/Markets/Complexity footer with "Not specified" defaults. Both Fast and Deep modes share identical `renderSummaryCard()` → `renderRfpSummary()` pipeline; only model-generated content differs. Debug features: `[RFP_SUMMARY]` console logs trace execution, `window.testRfpBullets()` test function for verification, try-catch wrapper for error handling. Designed for <10 second PM/exec scannability.
- **GPT 5.1 Pro Smart Selection L3 Filtering (Dec 2025)**: Curated L3 task selection system that ensures only AI-vetted tasks flow through Smart Selection to Step 3, instead of fetching all database tasks. Key components: `SmartSelectionState` global object stores `{selectedDeliverableCodes, selectedComponentsMap, selectedL3Map}` populated from AI's `l3_by_component` response data. `applySmartSelection(mode)` extracts task labels from `deliv.l3_by_component[compName]` for each threshold-qualified deliverable and stores them in SmartSelectionState. `applyAllSelectedFromAI()` uses SmartSelectionState for curated L3 tasks instead of DOM checkboxes, bypassing database fetch when SmartSelectionState is populated. Payload builder prioritizes `SmartSelectionState.selectedL3Map` for `/api/build` request. Fallback behavior: When SmartSelectionState is empty (no Smart Selection applied), original DOM checkbox reading and database fetching behavior is preserved. Debug console logs with `[SmartSelection]` prefix trace data flow. Solves issue where 15 AI-selected tasks became 187 database tasks in Step 3.
- **Timeline Scheduler Kit**: AI-powered timeline optimization with Microsoft Project XML parsing, smart dependencies, duration rounding, and multi-format export.
- **3-Level Workfront Hierarchy**: Proper XML export structure (Deliverable → Component → Task) with WBS codes, manual scheduling tags, and "Uncategorized" component handling.
- **PM-Brain Capacity Scheduling**: Production-ready timeline scheduling using capacity-based durations, resource leveling, realistic dependencies, and Gantt sync throttling.
- **Gantt Timeline Date Preservation**: XML export system preserving user-edited deliverable dates from the interactive Gantt timeline, ensuring Workfront imports match.
- **Workfront Manual Scheduling Lock**: Prevents Workfront from recalculating user-edited deliverable dates on XML import by adding Microsoft Project manual scheduling tags.
- **WBS-Based Dependencies + Multi-Assignment Export**: Feature-flagged system for simpler dependency management and parallel role execution within tasks.
- **Chronological Waterfall Export (Nov 2025)**: Production-ready XML export system that creates simple, chronological Gantt timelines in Workfront with no Service Department grouping. Solves critical Workfront UX issue where department-based hierarchy (Strategy → Creative → Technology) created confusing multi-tier groupings with three colored summary bars, replaced with single red Project Summary bar and date-based task flow. Implementation in `build_wbs_with_pricing()` (lines 3081-3212) completely removes Service Department summary row creation (deleted lines 3124-3148 that appended Strategy/Creative/Technology dicts) and eliminates department-based sorting/grouping loop (removed lines 3098-3112 items_by_dept groupby). Flattens WBS hierarchy so deliverables are direct children of Project Summary: deliverables now use WBS format "1.{n}" at OutlineLevel=2 (changed from "1.{dept}.{n}" at OutlineLevel=3), components become "1.{deliv}.{comp}" at OutlineLevel=3, and tasks follow as "1.{deliv}.{comp}.{task}" at OutlineLevel=4+. Service_Department preserved as metadata field for reporting only. Chronological sorting in `convert_excel_to_mspdi()` (lines 10167-10279) uses parent-aware tree-building algorithm (`sort_rows_chronologically()`) that reorders all tasks by Start_Date while preserving parent-child adjacency: sorts siblings at each level, then recursively flattens children immediately after parents. UID remapping system (lines 10284-10330) reassigns UIDs sequentially (1, 2, 3...) after reordering, builds old_uid_to_new_uid mapping, updates uid_to_sched dictionary keys, remaps assignment TaskUID references, and rebuilds summary_set with new UIDs. Includes wbs_sort_key() helper for proper WBS numeric sorting (handles multi-digit segments like "1.1.1.10" correctly after "1.1.1.2"). Critical dependency fix (lines 10926-10930): PredecessorLink elements use wbs_to_new_uid mapping instead of stale wbs_to_uid to ensure dependency integrity after chronological reordering—prevents broken predecessor references that would cause Workfront scheduling chaos. Results in clean waterfall Gantt view with deliverables in chronological order (Jan → Feb → ... → Nov), all hours/rates/costs/roles/assignments preserved, and dependencies intact.
- **L5+ Edge Filtering System (Nov 2025)**: Production-ready dependency filtering that enables parallel role execution while maintaining summary-level waterfall structure. Implementation in `convert_excel_to_mspdi()` immediately after dependency remapping (lines 10366-10399) uses `outline_level_from_wbs()` helper to calculate WBS depth, then filters valid_normalized_edges to drop all L5+ → L5+ edges (role-to-role dependencies), keeping only edges where at least one endpoint is ≤L4 (deliverable/component/task level). Logs dropped role-to-role edges for visibility (first 10 shown), updates normalized_edges = filtered_edges for downstream compatibility. Results in AM/CW/Strategist/Developer tasks under same component starting simultaneously with no dependency arrows between them, while higher-level milestones maintain chronological waterfall sequence.
- **Sibling Auto-Chaining System (Nov 2025)**: Automatic waterfall dependency generation for summary-level siblings (L2 deliverables, L3 components, and L4 tasks) within each parent group. Implementation in `convert_excel_to_mspdi()` (lines 10401-10458) builds parent→children mapping after chronological sort, identifies L2/L3/L4 summary rows by OutlineLevel (2, 3, or 4), groups them by parent WBS, sorts siblings chronologically by Start_Date (with datetime.min fallback for deterministic ordering), and generates forced_edges connecting consecutive siblings only when no manual dependency already exists (preserves user intent). Merges filtered_edges (post-L5+ filtering) with forced_edges to create canonical all_edges set, then updates normalized_edges = all_edges to propagate forced edges through both WBS and legacy dependency modes. Dependency remapping layer (lines 10335-10361) filters out stale WBS references after flattening (e.g., "1.Strategy.2" dropped post-flatten to "1.2"), logs dropped dependencies for debugging. Brand chain validation (lines 10461-10491) runs after auto-chaining to verify critical deliverable sequence (Key Pillars → Brand Narrative → Brand Values Statement → Brand Vision Statement → Purpose Statement) exists in final all_edges dependency graph. Results in clean left-to-right staircase Gantt view for deliverables/components/tasks, with comprehensive logging showing dropped L5+ edges and auto-added sibling chains during XML generation.
- **Parallel Processing**: Utilizes OpenAI Vision API for parallel PDF image processing with job tracking and retry logic.
- **Smart Image Analysis**: Two-tier image processing system using pre-filtering, quick relevance scans, and deep analysis.
- **Session Isolation System**: Complete data isolation between different RFPs using unique session IDs, auto-clear mechanisms, and session-scoped embedding caches.
- **CORS**: Configured to allow cross-origin requests.

### System Design Choices
- **Data Storage Pattern**: Excel/CSV files as primary source for business rules and configuration, loaded into in-memory DataFrames.
- **API Design**: RESTful endpoints for data loading, options retrieval, scenario generation, file uploads, and static file serving.
- **Database Configuration**: Automatic switching based on environment (Replit's PostgreSQL for development, separate production database). `Replit_App_DB_READABLE_FullRows_v4.xlsx` loaded into `app.state.db` at startup, with pickle caching and fallback to mock data.

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