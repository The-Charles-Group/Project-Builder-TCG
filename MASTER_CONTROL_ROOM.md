
# 🎛️ SYSTEM DESIGN DOCUMENT (SDD) - Agency Project Builder
**Complete System Architecture & Logic Flow Documentation**

*Also known as: Technical Architecture Documentation, Software Architecture Document (SAD)*

**Auto-Sync Enabled:** This document automatically updates when source code changes are detected.

---

## 📋 TABLE OF CONTENTS

1. [System Overview](#system-overview)
2. [Data Architecture](#data-architecture)
3. [User Journey & State Flow](#user-journey--state-flow)
4. [Backend Logic Map](#backend-logic-map)
5. [Frontend Component Map](#frontend-component-map)
6. [AI Intelligence Layer](#ai-intelligence-layer)
7. [Database Schema & Normalization](#database-schema--normalization)
8. [API Endpoint Directory](#api-endpoint-directory)
9. [Button-to-Logic Mapping](#button-to-logic-mapping)
10. [State Management Flow](#state-management-flow)
11. [Critical Decision Trees](#critical-decision-trees)
12. [Performance & Caching Systems](#performance--caching-systems)

---

## 1. SYSTEM OVERVIEW

### Core Purpose
Transform RFP documents → AI-analyzed deliverables → Priced scenarios → Timeline projections → Export-ready project plans

### Technology Stack
```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                     │
│ ├─ Vanilla JS (no framework dependencies)                   │
│ ├─ HTML5 with custom CSS properties                         │
│ ├─ Proxy-backed state management (selectionStore)           │
│ └─ Session-isolated storage (localStorage + sessionStorage) │
├─────────────────────────────────────────────────────────────┤
│ BACKEND                                                      │
│ ├─ FastAPI (async Python web framework)                     │
│ ├─ Pandas (DataFrame operations)                            │
│ ├─ NumPy (vector math for embeddings)                       │
│ └─ AsyncIO (concurrent processing)                          │
├─────────────────────────────────────────────────────────────┤
│ AI LAYER                                                     │
│ ├─ GPT-5 (via OpenAI Responses API)                         │
│ ├─ Embeddings (text-embedding-3-large)                      │
│ ├─ TF-IDF (sklearn vectorization)                           │
│ └─ Custom weighted matcher (hybrid scoring)                 │
├─────────────────────────────────────────────────────────────┤
│ DATA STORAGE                                                 │
│ ├─ Primary: Excel/CSV (v4 database)                         │
│ ├─ Cache: Pickle files (sub-2ms load times)                 │
│ ├─ Session: In-memory dictionaries                          │
│ └─ Persistence: localStorage (browser-side)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. DATA ARCHITECTURE

### 2.1 Primary Database: `Replit_App_DB_READABLE_FullRows_v4.xlsx`

**24 Configuration Sheets:**

```
┌─────────────────────────────────────────────────────────────┐
│ SHEET NAME                  │ PURPOSE                        │
├─────────────────────────────┼────────────────────────────────┤
│ All_Task_Rows               │ Complete task catalog (1916)   │
│ Deliverable_Index           │ L1 deliverable definitions     │
│ Bundle_Rules_Table          │ Task grouping logic            │
│ Bundle_Scenario_Defaults    │ Default complexity/tier        │
│ Bundles_By_Deliverable      │ Deliverable→Bundle mapping     │
│ Bundles_Hours_By_Role       │ Role-based hour allocation     │
│ Role_Rate_Card              │ Resource pricing ($/hour)      │
│ Role_Rate_Matrix            │ Seniority×Band rates           │
│ Rate_Bands                  │ Geographic rate multipliers    │
│ Timeline_Params             │ Duration formulas              │
│ Timeline_Scaling            │ Complexity/Tier multipliers    │
│ Timeline_Weighting          │ Task importance weights        │
│ Slack_Settings              │ Buffer configuration           │
│ Pricing_Settings            │ Global pricing rules           │
│ Scenario_Templates          │ Pre-built scenario configs     │
│ UI_Options                  │ Frontend behavior flags        │
│ RFP_Matching_Rules          │ Regex-based deliverable match  │
│ AI_Index                    │ AI matching catalog            │
│ AI_Matching_Rules           │ Weighted matching rules        │
│ AI_Config                   │ AI scoring parameters          │
│ Component_Library           │ Reusable component definitions │
│ Task_Library                │ Reusable task definitions      │
│ Industry_Templates          │ Vertical-specific configs      │
│ Governance_Milestones       │ Project governance rules       │
└─────────────────────────────┴────────────────────────────────┘
```

### 2.2 Normalized Column Structure

**Critical Normalization (performed at load time):**

```python
# Component normalization
Component_Task_L1 → Component  # Standardized name
Component L1 → Component
Component_L1 → Component

# Task normalization
Task_Task_L2 → Task_Label  # UI-friendly task name
Task_Name → Task_Label
Task_L1 → Task_Label

# Role normalization
Resource_Title → Resource_Title  # Consistent naming
Role_Title → Resource_Title
Role → Resource_Title

# Seniority standardization
"jr" / "junior" / "Jr." → "Junior"
"mid" / "midlevel" → "Mid"
"sr" / "senior" → "Senior"
"director" / "exec" → "Director"

# Code standardization
Deliverable Code → Deliverable_Code
Deliv_Code → Deliverable_Code
```

### 2.3 Data Flow Diagram

```
┌──────────────┐
│ Excel File   │
│ (v4.xlsx)    │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│ Pickle Cache Check                           │
│ ├─ Cache exists? → Load pickle (3ms)         │
│ └─ Cache missing? → Load Excel (200ms)       │
└──────┬───────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│ Normalization Pipeline                       │
│ ├─ _normalize_component_column()             │
│ ├─ _normalize_task_label_column()            │
│ ├─ _normalize_role_and_seniority_columns()   │
│ └─ _normalize_code_columns()                 │
└──────┬───────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│ In-Memory DataFrames (AgencyDB instance)     │
│ ├─ self.all_rows (1916 tasks)                │
│ ├─ self.deliverables (200+ L1)               │
│ ├─ self.role_rate_card (pricing)             │
│ └─ ... (21 more DataFrames)                  │
└──────┬───────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│ API Endpoints (app.state.db)                 │
│ ├─ /api/options                              │
│ ├─ /api/load                                 │
│ ├─ /api/scenarios                            │
│ └─ ... (40+ endpoints)                       │
└──────────────────────────────────────────────┘
```

---

## 3. USER JOURNEY & STATE FLOW

### 3.1 Step-by-Step User Flow

```
STEP 1: Upload RFP
├─ User Action: Paste text OR upload file (PDF/DOCX/TXT)
├─ UI Elements:
│  ├─ #rfpText (textarea)
│  ├─ #rfpFile (file input, multiple files supported)
│  ├─ #analysis-mode (Fast vs Deep selector)
│  ├─ #processing-tier (Batch size: mini/fast/balanced/thinking/accurate/pro)
│  └─ #btnAnalyze (trigger button)
├─ Frontend Logic: static/app.js → boot()
│  ├─ Validates input (text XOR file)
│  ├─ Calls /api/ai/analyze_job (POST)
│  └─ Starts polling /api/ai/jobs/{job_id}
├─ Backend Logic: ai_planner_agencydb.py
│  ├─ _run_analysis_background() [async background task]
│  ├─ Mode selection:
│  │  ├─ FAST: Lexical-only (TF-IDF), no embeddings
│  │  └─ DEEP: Embeddings (70%) + Lexical (30%)
│  ├─ Batch processing (chunks of 20-30 items)
│  ├─ GPT-5 scoring with retry logic
│  └─ Returns: {deliverables, components, tasks} grouped by department
└─ State Stored:
   ├─ sessionStorage: 'rfp_text', 'job_id'
   ├─ AI_JOB_STORE: {job_id: AIAnalysisJob}
   └─ window.APP.summary (in-memory)

STEP 2: Select Deliverables
├─ User Action: Review AI suggestions, select deliverables/components/L3 tasks
├─ UI Elements:
│  ├─ 3-Column Layout:
│  │  ├─ Column 1: Deliverables (L1) with checkboxes
│  │  ├─ Column 2: Components (L2) for selected deliverable
│  │  └─ Column 3: L2 Tasks (L3) for selected component
│  ├─ AI Suggestions Panel:
│  │  ├─ Evidence-backed recommendations
│  │  ├─ Confidence scores
│  │  └─ Risk indicators
│  ├─ Search Filters:
│  │  ├─ #s2-deliv-search (deliverables filter)
│  │  ├─ #s2-comp-search (components filter)
│  │  └─ #s2-l3-search (tasks filter)
│  └─ Bulk Actions:
│     ├─ Select All / Clear buttons (per column)
│     └─ AI Suggest buttons (components & tasks)
├─ Frontend Logic: static/app.js
│  ├─ renderDeliverablesPanel() → Renders L1 with department grouping
│  ├─ renderComponentsPanel() → Shows L2 for active deliverable
│  ├─ renderL3Panel() → Shows L3 for active component
│  └─ Centralized State: window.selectionStore
│     ├─ .deliverables (Set of deliverable codes)
│     ├─ .componentsByDeliv (Map<delivCode, Set<componentName>>)
│     └─ .l3ByComponent (Map<delivCode::componentKey, Set<l3Name>>)
├─ Backend Logic:
│  ├─ /api/agencydb/components/{deliv_code} → Returns components
│  ├─ /api/agencydb/l3tasks/{deliv_code}/{component_name} → Returns L3 tasks
│  └─ /api/agencydb/ai_suggest_components (GPT-5 suggestions)
└─ State Stored:
   ├─ localStorage: 'apb.{sessionId}.selections'
   ├─ window.selectionStore (canonical truth)
   └─ window.APB.step2.selectedCodes (alias for compatibility)

STEP 3: Configure Pricing
├─ User Action: Set project parameters, adjust pricing, build scenario
├─ UI Elements:
│  ├─ Project Configuration:
│  │  ├─ #projectStart (datetime-local, defaults to next Monday 09:00)
│  │  ├─ #projectName (text input)
│  │  ├─ #clientBudget (number input)
│  │  ├─ #pricingMode (Flat_Blended vs Per_Resource)
│  │  ├─ #blendedRate (optional override, default: $195)
│  │  ├─ #rateBand (geographic multiplier)
│  │  ├─ #complexity (Basic/Intermediate/Advanced)
│  │  └─ #volumeTier (T1/T2/T3/T4)
│  ├─ Pricing Details Table:
│  │  ├─ Deliverable/Component rows
│  │  ├─ Type (PROJECT vs RETAINER)
│  │  ├─ Months (for retainers)
│  │  ├─ Hours / Rate / Cost columns
│  │  └─ Resource breakdown
│  ├─ Summary Panels:
│  │  ├─ One-Time Deliverables total
│  │  └─ Monthly Retainer Services total
│  └─ Actions:
│     ├─ #btnBuild → Build initial scenario
│     ├─ #btn-rebuild-scenario → Rebuild after changes
│     └─ #btn-global-retainer-suggest → AI retainer analysis
├─ Frontend Logic: static/js/pricing-one-table.js
│  ├─ buildFromCurrentSelection() → Calls /api/scenarios
│  ├─ rebuildScenario() → Re-calls API with updated config
│  ├─ updatePricingTable() → Renders table from scenario data
│  └─ askAIForRetainerSuggestions() → GPT-5 retainer analysis
├─ Backend Logic:
│  ├─ /api/scenarios (POST) → build_scenarios_v4()
│  │  ├─ Fetches hours from All_Task_Rows
│  │  ├─ Applies complexity/tier multipliers
│  │  ├─ Joins role rates from Role_Rate_Card
│  │  ├─ Calculates Price_USD = Rate × Hours
│  │  └─ Groups by deliverable → component → task
│  ├─ /api/pricing/retainer_suggest → AI retainer recommendations
│  └─ /api/pricing/redistribute → Smart hour redistribution
└─ State Stored:
   ├─ SCENARIO_STORE[session_id] → Canonical scenario data
   ├─ window.pricingData → UI-side pricing metadata
   └─ localStorage: 'apb.{sessionId}.scenario'

STEP 4: Generate Timeline
├─ User Action: Generate AI-optimized timeline with dependencies
├─ UI Elements:
│  ├─ Timeline Controls:
│  │  ├─ #btnGenerateTimeline → Trigger AI timeline generation
│  │  ├─ #gantt-view-mode → Day/Week/Month view selector
│  │  └─ Governance toggles (steering reviews, QA gates, etc.)
│  ├─ Gantt Chart:
│  │  ├─ Frappe Gantt visualization
│  │  ├─ Department-colored tasks
│  │  ├─ Dependency arrows
│  │  └─ Critical path highlighting
│  └─ Resource Analysis:
│     ├─ Resource utilization chart
│     ├─ Conflict detection
│     └─ Risk indicators
├─ Frontend Logic: static/app.js
│  ├─ generateAITimeline() → Calls /api/timeline/generate_ai
│  ├─ initializeGanttChart() → Renders Frappe Gantt
│  └─ Polls /api/timeline/jobs/{job_id} for progress
├─ Backend Logic: ai_timeline_manager.py
│  ├─ generate_ai_timeline() [async]
│  │  ├─ Dependency analysis (GPT-5)
│  │  ├─ Critical Path Method (CPM) calculation
│  │  ├─ Resource leveling
│  │  ├─ CCPM buffer insertion
│  │  └─ Governance milestone injection
│  ├─ CPMCalculator class:
│  │  ├─ Forward pass (Early Start/Finish)
│  │  ├─ Backward pass (Late Start/Finish)
│  │  ├─ Float calculation (Total Float, Free Float)
│  │  └─ Critical path identification
│  └─ GovernanceFramework class:
│     ├─ Steering committee reviews (25%, 50%, 75%)
│     ├─ Quality gates
│     ├─ Risk checkpoints
│     └─ Communication cadence
└─ State Stored:
   ├─ SSE_JOB_STORE[job_id] → Timeline generation status
   ├─ window.currentTimelineTasks → Gantt data
   └─ localStorage: 'apb.{sessionId}.timeline'

EXPORT: Final Ship
├─ User Action: Export to Workfront XML, Excel, MS Project
├─ UI Elements:
│  ├─ Export format selector
│  ├─ #toggle-anchors → Include START/END milestones
│  └─ #btnFinalShip → Trigger final export
├─ Frontend Logic:
│  ├─ callFinalShip() → Calls /api/final_ship
│  └─ Downloads ZIP with all formats
├─ Backend Logic:
│  ├─ /api/final_ship → Builds WBS DataFrame
│  ├─ build_wbs_dataframe_from_scenario() → Task hierarchy
│  ├─ convert_to_xml() → Workfront XML format
│  ├─ convert_to_excel() → Excel export
│  └─ convert_excel_to_mspdi() → MS Project format
└─ Output:
   └─ ZIP file: {projectName}_Workfront_Export_FINAL_SHIP_{timestamp}_COMPLETE.zip
      ├─ Workfront_Export.xml
      ├─ Workfront_Export.xlsx
      └─ MS_Project_Export.xml
```

---

## 4. BACKEND LOGIC MAP

### 4.1 Core Classes

#### `AgencyDB` (main.py)
**Purpose:** Primary database interface and business logic

```python
class AgencyDB:
    """
    Singleton database manager. Loads v4 Excel → Normalizes → Exposes DataFrames
    """
    
    # === INITIALIZATION ===
    def __init__(self):
        self.loaded = False
        self.src = None
        # 24 DataFrame properties (see Data Architecture)
    
    def load(self):
        """
        Load order:
        1. Search for v4 file (standard paths → attached_assets/)
        2. Check pickle cache (if exists and newer)
        3. Load Excel → Normalize → Cache to pickle
        4. Fallback to mock data if no file found
        """
    
    # === NORMALIZATION METHODS ===
    def _normalize_component_column(self):
        """Component_Task_L1 → Component (empty → 'General')"""
    
    def _normalize_task_label_column(self):
        """Task_Task_L2 → Task_Label (UI display name)"""
    
    def _normalize_role_and_seniority_columns(self):
        """
        Resource_Title standardization
        Seniority canonicalization (jr→Junior, sr→Senior)
        """
    
    def _normalize_rate_card_seniority(self):
        """Ensure pricing joins work (no blank roles/seniority)"""
    
    # === SCENARIO BUILDING ===
    def build_scenarios_v4(self, codes, complexity, tier, ...):
        """
        CORE PRICING ENGINE
        1. Filter all_rows by deliverable codes
        2. Get scenario column: f"{complexity}__{tier}_Hours"
        3. Join role rates from role_rate_card
        4. Calculate: Price_USD = Rate_USD × Planned_Hours
        5. Group by deliverable → component → task
        6. Return nested dict structure
        """
    
    # === TIMELINE PROJECTION ===
    def project_timeline_v4(self, wbs_df, start_date, use_slack, ...):
        """
        TIMELINE CALCULATION ENGINE
        1. Group tasks by task_group (discovery, strategy, etc.)
        2. Get base duration from timeline_params
        3. Apply scaling:
           - Complexity multiplier from timeline_scaling
           - Tier multiplier from timeline_scaling
           - Weighted average using timeline_weighting
        4. Calculate start/end dates with dependencies
        5. Insert slack (internal review + client review buffers)
        6. Return DataFrame with Start_Date, End_Date columns
        """
    
    # === RFP PARSING ===
    def suggest_deliverables_from_text(self, rfp_text):
        """
        RULES-BASED RFP MATCHER
        1. Load RFP_Matching_Rules (regex patterns)
        2. Match patterns against RFP text
        3. Map to deliverable codes
        4. Apply UI_Options blocking (e.g., block Analytics)
        5. Return sorted by confidence (hit count)
        """
    
    # === RETAINER ANALYSIS ===
    def retainer_recommendation(self, rfp_text, deliverable_name):
        """
        RETAINER HEURISTIC
        1. Check for month count in RFP (e.g., "12 months")
        2. Look for signals: "retainer", "monthly", "ongoing"
        3. Check deliverable name for retainer keywords
        4. Return (is_retainer: bool, months: int [1-12])
        """
```

#### `AIAnalysisJob` (ai_planner_agencydb.py)
**Purpose:** Background job tracking for AI analysis

```python
@dataclass
class AIAnalysisJob:
    job_id: str
    status: AIJobStatus  # PENDING → RUNNING → COMPLETED/FAILED
    start_time: float
    end_time: Optional[float]
    total_chunks: int
    processed_chunks: int
    current_stage: str  # User-visible status message
    current_reasoning: str  # AI thinking steps (visible to user)
    reasoning_history: List[str]  # Full thinking log
    result: Optional[Dict[str, Any]]  # Final deliverables/components/tasks
    error: Optional[str]

# Global store
AI_JOB_STORE: Dict[str, AIAnalysisJob] = {}
```

### 4.2 AI Intelligence Flow

```
┌─────────────────────────────────────────────────────────────┐
│ AI ANALYSIS PIPELINE (ai_planner_agencydb.py)               │
└─────────────────────────────────────────────────────────────┘

FAST MODE (Lexical-only, ~60 seconds):
├─ 1. Summarize RFP (GPT-5 Mini) → Extract goals/channels/markets
├─ 2. TF-IDF Analysis:
│  ├─ Build document vectors (catalog items)
│  ├─ Build query vector (RFP text)
│  └─ Cosine similarity scoring
├─ 3. Lexical Prefilter:
│  ├─ Top 150 deliverables (by TF-IDF score)
│  ├─ Top 200 components
│  └─ Top 250 tasks
└─ 4. No GPT-5 rescoring (speed optimization)

DEEP MODE (Hybrid, ~2-5 minutes):
├─ 1. Summarize RFP (GPT-5 Thinking) → Detailed extraction
├─ 2. Embedding + Lexical Hybrid:
│  ├─ Embed catalog items (text-embedding-3-large)
│  ├─ Embed RFP text
│  ├─ Calculate embedding similarity (cosine)
│  ├─ Calculate lexical score (TF-IDF)
│  └─ Recall score = 70% embedding + 30% lexical
├─ 3. Smart Prefilter:
│  ├─ Top 100 deliverables (OR all above 0.3 recall)
│  ├─ Top 150 components (above 0.25 recall)
│  └─ Top 200 tasks (above 0.2 recall)
├─ 4. GPT-5 Batch Scoring:
│  ├─ Chunk candidates into batches (20-30 items)
│  ├─ For each batch:
│  │  ├─ Build JSON schema prompt
│  │  ├─ Call GPT-5 with retry logic (3 attempts)
│  │  ├─ Parse relevance scores (0-100)
│  │  └─ Extract reasoning/evidence
│  ├─ Aggregate scores across batches
│  └─ Sort by relevance
└─ 5. Post-processing:
   ├─ Direct keyword match boosting
   ├─ Service mapping (explicit phrase matches)
   └─ Group by department

BATCH SIZE TIERS (user-configurable):
├─ Mini: 30 items/batch (fastest, least precise)
├─ Fast: 30 items/batch
├─ Balanced: 25 items/batch (default, recommended)
├─ Thinking: 25 items/batch (GPT-5 deep reasoning)
├─ Accurate: 20 items/batch (highest quality)
└─ Pro: 20 items/batch (maximum precision)
```

### 4.3 Critical Decision Trees

#### Decision Tree 1: Mode Selection (Fast vs Deep)

```
User clicks "Analyze with AI"
│
├─ Is analysis-mode = "fast"?
│  │
│  ├─ YES → FAST MODE
│  │  ├─ Skip embeddings (performance)
│  │  ├─ Use TF-IDF only
│  │  ├─ Prefilter: 150/200/250 candidates
│  │  └─ No GPT-5 rescoring
│  │
│  └─ NO → DEEP MODE
│     ├─ Generate embeddings (text-embedding-3-large)
│     ├─ Hybrid recall: 70% embedding + 30% lexical
│     ├─ Smart prefilter (recall thresholds)
│     └─ GPT-5 batch scoring with retry
```

#### Decision Tree 2: Retainer vs Project

```
User requests retainer analysis (or auto-triggered)
│
├─ Check RFP text for explicit months ("12 months", "6 mo")
│  ├─ Found? → Extract month count (1-12)
│  └─ Not found? → Continue to heuristics
│
├─ Check signal keywords in RFP:
│  ├─ "retainer", "monthly", "per month", "ongoing"
│  ├─ "always-on", "maintenance", "management"
│  └─ "reporting cadence", "monthly report"
│
├─ Check deliverable name keywords:
│  ├─ "social", "community", "media", "measurement"
│  ├─ "seo", "maintenance", "support", "content"
│  └─ If match → Likely retainer
│
├─ AI Analysis (if requested):
│  ├─ Call GPT-5 with deliverable + RFP context
│  ├─ Get recommendation: PROJECT vs RETAINER
│  └─ Get suggested months (6/12/24)
│
└─ Final determination:
   ├─ is_retainer = (signals OR likely_by_name OR AI_recommends)
   └─ months = extracted OR AI_suggested OR default(12)
```

#### Decision Tree 3: Pricing Calculation

```
User clicks "Build Scenario"
│
├─ Collect selected deliverable codes
│
├─ For each code:
│  ├─ Query all_rows WHERE Deliverable_Code = code
│  ├─ Get scenario column: "{complexity}__{tier}_Hours"
│  │  ├─ Example: "Advanced__T2_MediumVolume_Hours"
│  │  └─ Fallback: "Advanced__T2_Hours" → "Advanced_Hours"
│  │
│  ├─ For each task row:
│  │  ├─ Get Resource_Title + Seniority
│  │  ├─ Lookup rate: JOIN role_rate_card ON (Resource_Title, Seniority)
│  │  ├─ Apply rate band multiplier (if selected)
│  │  ├─ Calculate: Price_USD = Rate_USD × Planned_Hours
│  │  └─ Store task with price
│  │
│  └─ Group tasks:
│     ├─ By Component (L2)
│     └─ By Task_Label (L3)
│
├─ Check pricing mode:
│  ├─ Flat_Blended?
│  │  ├─ Override all rates with blended_rate
│  │  └─ Recalculate all prices
│  └─ Per_Resource?
│     └─ Use individual role rates
│
├─ Check deliverable type:
│  ├─ RETAINER?
│  │  ├─ Multiply hours × retainer_months
│  │  ├─ Mark as recurring
│  │  └─ Calculate monthly breakdown
│  └─ PROJECT?
│     └─ One-time total
│
└─ Return scenario:
   ├─ items: List[{deliverable, component, task, hours, rate, price}]
   ├─ totals: {hours, price}
   └─ metadata: {complexity, tier, mode, start_date}
```

---

## 5. FRONTEND COMPONENT MAP

### 5.1 Key UI Components & Their Logic

```
┌─────────────────────────────────────────────────────────────┐
│ COMPONENT: Analysis Mode Selector                           │
│ Location: static/index.html (Step 1)                        │
│ IDs: #mode-fast, #mode-deep, #analysis-mode                 │
├─────────────────────────────────────────────────────────────┤
│ LOGIC:                                                       │
│ function setAnalysisMode(mode) {                            │
│   document.getElementById('analysis-mode').value = mode;    │
│   // Toggle active states on buttons                        │
│   // Update UI to show mode description                     │
│ }                                                            │
├─────────────────────────────────────────────────────────────┤
│ BACKEND INTERACTION:                                         │
│ → Passed to /api/ai/analyze_job as 'mode' parameter         │
│ → Determines Fast vs Deep processing path                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ COMPONENT: Deliverables Panel (3-Column Layout)             │
│ Location: static/app.js → renderDeliverablesPanel()         │
│ IDs: #s2-deliv-list, #s2-deliv-search                       │
├─────────────────────────────────────────────────────────────┤
│ LOGIC:                                                       │
│ function renderDeliverablesPanel() {                        │
│   const delivs = APB.step2.allDeliverables;                 │
│   const grouped = groupByDepartment(delivs);                │
│   for (const [dept, items] of grouped) {                    │
│     // Render department header                             │
│     for (const deliv of items) {                            │
│       // Render checkbox + label                            │
│       // Wire checkbox → toggleDeliverable(code)            │
│     }                                                        │
│   }                                                          │
│ }                                                            │
│                                                              │
│ function toggleDeliverable(code, isChecked) {               │
│   if (isChecked) {                                          │
│     selectionStore.deliverables.add(code);                  │
│     if (AUTO_SUGGEST) {                                     │
│       suggestComponents(code); // AI suggestion             │
│     }                                                        │
│   } else {                                                  │
│     selectionStore.deliverables.delete(code);               │
│     selectionStore.componentsByDeliv.delete(code);          │
│   }                                                          │
│   renderComponentsPanel(); // Refresh L2                    │
│   updateSelectionSummary(); // Update counters              │
│ }                                                            │
├─────────────────────────────────────────────────────────────┤
│ BACKEND INTERACTION:                                         │
│ → /api/load → Fetches all deliverables                      │
│ → /api/agencydb/ai_suggest_components → GPT-5 suggestions   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ COMPONENT: Pricing Details Table                            │
│ Location: static/js/pricing-one-table.js                    │
│ ID: #pricing-details-table                                  │
├─────────────────────────────────────────────────────────────┤
│ LOGIC:                                                       │
│ function updatePricingTable() {                             │
│   const scenario = SCENARIO_STORE[sessionId];               │
│   const tbody = document.getElementById('pricing-tbody');   │
│   tbody.innerHTML = ''; // Clear                            │
│                                                              │
│   for (const item of scenario.items) {                      │
│     const row = createTableRow(item);                       │
│     // Row contains:                                        │
│     //   - Deliverable/Component name                       │
│     //   - Type toggle (PROJECT/RETAINER)                   │
│     //   - Months input (if RETAINER)                       │
│     //   - Hours (editable)                                 │
│     //   - Rate (editable)                                  │
│     //   - Cost (calculated)                                │
│     //   - Resource breakdown                               │
│     tbody.appendChild(row);                                 │
│   }                                                          │
│                                                              │
│   updatePricingSummary(); // Recalculate totals             │
│ }                                                            │
│                                                              │
│ function toggleRetainerType(code, isRetainer) {             │
│   pricingData.deliverableTypes.set(code, isRetainer ?      │
│     'RETAINER' : 'PROJECT');                                │
│   if (isRetainer) {                                         │
│     pricingData.retainers.set(code, 12); // Default         │
│   } else {                                                  │
│     pricingData.retainers.delete(code);                     │
│   }                                                          │
│   updatePricingTable(); // Re-render                        │
│ }                                                            │
├─────────────────────────────────────────────────────────────┤
│ BACKEND INTERACTION:                                         │
│ → /api/scenarios → Fetches scenario data                    │
│ → /api/pricing/retainer_suggest → AI retainer analysis      │
│ → /api/pricing/redistribute → Smart hour redistribution     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ COMPONENT: Gantt Chart Timeline                             │
│ Location: static/app.js → initializeGanttChart()            │
│ ID: #gantt, Library: Frappe Gantt                           │
├─────────────────────────────────────────────────────────────┤
│ LOGIC:                                                       │
│ function initializeGanttChart(tasks) {                      │
│   const container = document.querySelector('#gantt');       │
│   if (!tasks || tasks.length === 0) {                       │
│     container.innerHTML = '<div>No timeline data</div>';    │
│     return;                                                 │
│   }                                                          │
│                                                              │
│   // Convert to Frappe Gantt format                         │
│   const ganttTasks = tasks.map(t => t.to_gantt_format());   │
│                                                              │
│   ganttChart = new Gantt(container, ganttTasks, {           │
│     view_mode: 'Day',                                       │
│     date_format: 'YYYY-MM-DD',                              │
│     popup_trigger: 'click',                                 │
│     custom_popup_html: (task) => renderTaskPopup(task)      │
│   });                                                        │
│                                                              │
│   // Apply critical path highlighting                       │
│   highlightCriticalPath(tasks.filter(t => t.is_critical)); │
│ }                                                            │
├─────────────────────────────────────────────────────────────┤
│ BACKEND INTERACTION:                                         │
│ → /api/timeline/generate_ai → GPT-5 timeline generation     │
│ → /api/timeline/jobs/{job_id} → SSE polling for progress    │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 State Management (selectionStore)

```javascript
// CANONICAL TRUTH: window.selectionStore
const selectionStore = {
  deliverables: new Set(),  // Set<deliverable_code>
  
  componentsByDeliv: new Map(),  // Map<delivCode, Set<componentName>>
  // Example: "deck_strategy" → Set("Research", "Analysis", "Deck Creation")
  
  l3ByComponent: new Map()  // Map<"delivCode::componentName", Set<l3Name>>
  // Example: "deck_strategy::Research" → Set("Competitive Analysis", "Market Research")
};

// PROXY LAYER (for backwards compatibility)
// Old code references S2.selectedL3ByKey["deck_strategy::Research"]
// Proxy intercepts and redirects to selectionStore.l3ByComponent.get()
const selectedL3Proxy = new Proxy({}, {
  get(target, key) {
    return selectionStore.l3ByComponent.get(String(key));
  },
  set(target, key, value) {
    selectionStore.l3ByComponent.set(String(key), 
      value instanceof Set ? value : new Set(value));
    return true;
  }
});

// PERSISTENCE
// On change → localStorage.setItem('apb.{sessionId}.selections', JSON.stringify({
//   deliverables: Array.from(selectionStore.deliverables),
//   components: Object.fromEntries(selectionStore.componentsByDeliv),
//   l3: Object.fromEntries(selectionStore.l3ByComponent)
// }));
```

---

## 6. AI INTELLIGENCE LAYER

### 6.1 Weighted Matcher (ai_weighted_matcher.py)

```python
"""
HYBRID SCORING ALGORITHM
Combines TF-IDF lexical matching with rule-based boosting
"""

def score_rfp(rfp_text: str, ai_xlsx_path: str) -> Dict[str, Any]:
    """
    1. Load AI_Matching_Rules_full.xlsx
    2. Build TF-IDF index from AI_Index sheet
    3. Calculate lexical scores (cosine similarity)
    4. Apply rule-based hits (regex keyword matching)
    5. Aggregate scores with weighted formula
    6. Normalize to percentages
    7. Return top matches with explanations
    """
    
    # TF-IDF Construction
    def build_tfidf(ai_index_df):
        """
        For each catalog item:
        - Tokenize: Deliverable + Component + Task + Keywords + Department
        - Build document vectors
        - Calculate IDF weights
        - Return {idf_dict, doc_vectors, doc_norms}
        """
    
    # Lexical Scoring
    def compute_lexical_scores(rfp_text, tfidf_idx):
        """
        - Tokenize RFP text
        - Build query vector
        - Cosine similarity: dot(query, doc) / (||query|| × ||doc||)
        - Return similarity scores [0.0 - 1.0]
        """
    
    # Rule Engine
    def eval_rules(rfp_text, ai_rules_df):
        """
        For each rule:
        - Check Keywords_Any (OR condition)
        - Check Keywords_All (AND condition)
        - Check Exclude_Keywords (NOT condition)
        - If match → Score = Priority / 10
        - Return [rule_scores, rule_explanations]
        """
    
    # Aggregation
    def aggregate_scores(ai_index_df, lex_scores, rule_hits, config):
        """
        Weighted formula:
        
        L1 (Deliverable):
          score = w_rule_l1 × rule_hit + w_lex_l1 × lex_score
        
        L2 (Component):
          comp_best = max(w_rule_l2 × rule + w_lex_l2 × lex)
        
        L3 (Task):
          task_best = max(w_rule_l3 × rule + w_lex_l3 × lex)
        
        Final:
          total_score = L1 + (comp_multiplier × comp_best) + 
                        (task_multiplier × task_best)
        
        Default weights (from AI_Config):
        - w_rule_l1 = 0.6, w_lex_l1 = 0.4
        - w_rule_l2 = 0.65, w_lex_l2 = 0.35
        - w_rule_l3 = 0.7, w_lex_l3 = 0.3
        - comp_multiplier = 0.9
        - task_multiplier = 0.8
        """
    
    # Direct Match Boosting
    def check_direct_matches(rfp_text, deliverable_name):
        """
        EXPLICIT PHRASE MATCHING
        
        1. Extract 2-3 word phrases from deliverable name
        2. Check if phrases appear in RFP text
        3. Apply boost:
           - 3-word match → 95% confidence
           - 2-word match → 92% confidence
           - Single important word → 90% confidence
        
        4. Special mappings (SERVICE_MAPPING):
           - "media planning" → ["media plan", "media strategy"]
           - "brand strategy" → ["branding strategy", "brand development"]
           - etc.
        
        5. "Required Services" section detection:
           - If deliverable mentioned in "Required Services" → 1.8× boost
        
        Return: (boost_percentage, matched_keywords)
        """
```

### 6.2 GPT-5 Integration (gpt5_helpers.py + sitecustomize.py)

```python
"""
ENFORCED GPT-5 USAGE
sitecustomize.py patches OpenAI SDK at import time to:
1. Block non-GPT-5 models (o1/o3/gpt-4)
2. Convert Chat Completions → Responses API
3. Add retry logic with exponential backoff
"""

# Allowed models (enforced)
_ALLOWED_MODELS = {
    "gpt-5",
    "gpt-5-pro",
    "gpt-5-mini",
    "gpt-5-thinking",
    "gpt-5-thinking-mini"
}

# Tier mapping (user-friendly names)
_TIER_TO_MODEL = {
    "mini": "gpt-5-mini",      # Fast, low compute
    "thinking": "gpt-5",       # Balanced
    "pro": "gpt-5-pro",        # Maximum precision
    "fast": "gpt-5-mini",
    "balanced": "gpt-5",
    "accurate": "gpt-5-pro"
}

# Reasoning effort (compute depth)
_TIER_TO_EFFORT = {
    "mini": "low",
    "thinking": "medium",
    "pro": "high"
}

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 4.0   # seconds

def retry_with_exponential_backoff(func, max_retries=3, ...):
    """
    Retry logic:
    1. Execute function
    2. On failure:
       - Check error type (rate_limit, timeout, other)
       - Calculate delay: min(base_delay × 2^attempt, max_delay)
       - Log attempt number
       - Retry
    3. After max_retries → Raise or return None
    """

# Helper functions
def gpt5_json_schema(client, messages, json_schema, tier="thinking", 
                     max_output_tokens=2200, use_retry=True):
    """
    STRICT JSON HELPER
    1. Inject system message with schema instructions
    2. Call GPT-5 Responses API
    3. Parse JSON response
    4. Validate against schema
    5. Retry on parse failure (if use_retry=True)
    """

def gpt5_text(client, messages, tier="thinking", 
              max_output_tokens=1500, use_retry=True):
    """
    SIMPLE TEXT HELPER
    1. Call GPT-5 Responses API
    2. Extract text from response
    3. Retry on empty/incomplete (if use_retry=True)
    """
```

### 6.3 Embedding Cache (embedding_cache.py)

```python
"""
SESSION-ISOLATED EMBEDDING CACHE
Prevents cross-contamination between different RFPs
"""

# Cache structure
_EMBEDDING_CACHE: Dict[str, Dict[str, List[float]]] = {}
# session_id → {text_hash → embedding_vector}

def embed_many(texts: List[str], client, session_id: str) -> List[List[float]]:
    """
    1. Generate session-specific cache key
    2. For each text:
       - Hash text → cache_key
       - Check cache: _EMBEDDING_CACHE[session_id].get(cache_key)
       - If hit → Return cached embedding
       - If miss → Call OpenAI API
    3. Store new embeddings in cache
    4. Return all embeddings (cached + new)
    
    TTL: 24 hours (automatic cleanup)
    """

# Cache statistics
def get_cache_stats() -> Dict[str, Any]:
    """
    Return:
    - total_sessions
    - total_cached_embeddings
    - cache_hit_rate
    - memory_usage_mb
    """
```

---

## 7. DATABASE SCHEMA & NORMALIZATION

### 7.1 All_Task_Rows Schema (Primary Data Source)

```
┌──────────────────────────┬────────────────────────────────────────┐
│ COLUMN NAME              │ PURPOSE / NOTES                        │
├──────────────────────────┼────────────────────────────────────────┤
│ Row_ID                   │ Unique task identifier                 │
│ Deliverable_Code         │ L1 deliverable code (e.g., "PM_01")    │
│ Deliverable              │ L1 friendly name                       │
│ Component_Task_L1        │ L2 component name (normalized→Component)│
│ Task_Task_L2             │ L3 task name (normalized→Task_Label)   │
│ Service_Department       │ Department (Strategy/Creative/etc.)    │
│ Category                 │ Deliverable category                   │
│ Resource_Title           │ Role name (Developer/Strategist/etc.)  │
│ Seniority                │ Junior/Mid/Senior/Director             │
│ Estimated_Hours          │ Base hours (v4 column name)            │
│ Advanced__T2_MediumVolume_Hours  │ Scenario-specific hours     │
│ Advanced__T3_HighVolume_Hours    │ Another scenario           │
│ ... (multiple scenario columns)  │ Pattern: {complexity}__{tier}_Hours │
│ task_group               │ Timeline grouping (discovery/strategy) │
│ Task_Code                │ Legacy task code (v3)                  │
└──────────────────────────┴────────────────────────────────────────┘

Total rows: 1,916 tasks (v4 database)
Scenario columns: ~50 combinations of complexity × tier
```

### 7.2 Normalization Rules (Applied at Load Time)

```python
# 1. Component Normalization
# Input variations: "Component_Task_L1", "Component L1", "Component_L1", "Component"
# Output: Always "Component" column
# Missing values → "" (not "General" globally, only per-row if needed)

# 2. Task Label Normalization
# Input variations: "Task_Task_L2", "Task_Name", "Task_L1", "Component_Task_L2"
# Output: Always "Task_Label" column
# This is the UI-friendly task display name

# 3. Role Normalization
# Input variations: "Resource_Title", "Role_Title", "Role", "Resource"
# Output: Always "Resource_Title"
# Missing values → "General Role" (placeholder for pricing joins)

# 4. Seniority Canonicalization
# Input → Output mapping:
{
    "jr", "junior", "Jr.", "associate", "coordinator": "Junior",
    "mid", "midlevel", "intermediate", "staff", "specialist": "Mid",
    "sr", "senior", "lead", "principal": "Senior",
    "director", "group director", "head", "exec": "Director"
}
# Missing values → "Mid" (default for pricing joins)

# 5. Deliverable Code Normalization
# Input variations: "Deliverable Code", "Deliv_Code", "DeliverableID"
# Output: Always "Deliverable_Code"
```

### 7.3 Role Rate Card Join Logic

```python
def get_rate_for_task(task_row: pd.Series, rate_card: pd.DataFrame, 
                      rate_band: str = "Standard_US") -> float:
    """
    PRICING JOIN ALGORITHM
    
    1. Extract from task:
       - resource_title = task_row['Resource_Title']
       - seniority = task_row['Seniority']
    
    2. Query rate card:
       rate_row = rate_card[
           (rate_card['Resource_Title'] == resource_title) &
           (rate_card['Seniority'] == seniority)
       ]
    
    3. If no match:
       - Try Resource_Title only (any seniority)
       - If still no match → Use default rate ($150)
    
    4. Apply rate band multiplier:
       base_rate = rate_row['Rate_USD']
       multiplier = rate_bands[rate_band]['Rate_Multiplier']
       final_rate = base_rate × multiplier
    
    5. Return final_rate
    """
```

---

## 8. API ENDPOINT DIRECTORY

### 8.1 Complete Endpoint Map

```
┌─────────────────────────────────────────────────────────────┐
│ ENDPOINT                     │ METHOD │ PURPOSE             │
├──────────────────────────────┼────────┼─────────────────────┤
│ /                            │ GET    │ Serve frontend      │
│ /api/health                  │ GET    │ Health check        │
│ /api/options                 │ GET    │ UI dropdowns config │
│ /api/load                    │ GET    │ Load deliverables   │
├──────────────────────────────┼────────┼─────────────────────┤
│ AI ANALYSIS                  │        │                     │
├──────────────────────────────┼────────┼─────────────────────┤
│ /api/ai/analyze_job          │ POST   │ Start AI analysis   │
│ /api/ai/jobs/{job_id}        │ GET    │ Poll job status     │
│ /api/agencydb/status/{job_id}│ GET    │ Job status (alias)  │
│ /api/agencydb/components/{code} │ GET │ Get components      │
│ /api/agencydb/l3tasks/{code}/{comp} │ GET │ Get L3 tasks │
│ /api/agencydb/ai_suggest_components │ POST │ GPT-5 suggestions │
├──────────────────────────────┼────────┼─────────────────────┤
│ PRICING & SCENARIOS          │        │                     │
├──────────────────────────────┼────────┼─────────────────────┤
│ /api/scenarios               │ POST   │ Build scenario      │
│ /api/scenario/save           │ POST   │ Save scenario       │
│ /api/scenario/load           │ GET    │ Load scenario       │
│ /api/pricing/retainer_suggest │ POST  │ AI retainer analysis│
│ /api/pricing/redistribute    │ POST   │ Smart hour redistrib│
├──────────────────────────────┼────────┼─────────────────────┤
│ TIMELINE                     │        │                     │
├──────────────────────────────┼────────┼─────────────────────┤
│ /api/timeline/generate_ai    │ POST   │ GPT-5 timeline gen  │
│ /api/timeline/jobs/{job_id}  │ GET    │ SSE stream progress │
│ /api/timeline/simple         │ POST   │ Rule-based timeline │
├──────────────────────────────┼────────┼─────────────────────┤
│ EXPORT                       │        │                     │
├──────────────────────────────┼────────┼─────────────────────┤
│ /api/final_ship              │ POST   │ Full export package │
│ /api/export/workfront        │ POST   │ Workfront XML only  │
│ /api/export/excel            │ POST   │ Excel export only   │
│ /api/export/msproject        │ POST   │ MS Project XML      │
├──────────────────────────────┼────────┼─────────────────────┤
│ WEIGHTED MATCHER             │        │                     │
├──────────────────────────────┼────────┼─────────────────────┤
│ /api/step2/ai/weights        │ POST   │ TF-IDF + rules match│
├──────────────────────────────┼────────┼─────────────────────┤
│ CHARLES AGENT                │        │                     │
├──────────────────────────────┼────────┼─────────────────────┤
│ /api/agent/chat              │ POST   │ AI assistant chat   │
│ /api/agent/status            │ GET    │ Agent availability  │
│ /api/upload_rfp              │ POST   │ Direct file upload  │
├──────────────────────────────┼────────┼─────────────────────┤
│ LEARNING BRAIN               │        │                     │
├──────────────────────────────┼────────┼─────────────────────┤
│ /api/brain/learn             │ POST   │ Record user edits   │
│ /api/brain/status            │ GET    │ Brain mode/stats    │
│ /admin/brain                 │ GET    │ Admin UI            │
└──────────────────────────────┴────────┴─────────────────────┘
```

### 8.2 Request/Response Examples

#### Example 1: /api/ai/analyze_job

**Request:**
```json
POST /api/ai/analyze_job
{
  "request_text": "We need a comprehensive digital marketing campaign...",
  "mode": "deep",
  "strictness": "balanced",
  "tier": "thinking",
  "session_id": "session_1234567890_abc123"
}
```

**Response:**
```json
{
  "job_id": "analyze_1234567890_xyz789",
  "status": "pending",
  "message": "Analysis started. Poll /api/ai/jobs/{job_id} for progress."
}
```

**Polling Response (in progress):**
```json
GET /api/ai/jobs/analyze_1234567890_xyz789
{
  "job_id": "analyze_1234567890_xyz789",
  "status": "processing",
  "progress": 45,
  "current_stage": "Stage 4/7: Scoring candidates with GPT-5 (batch 3/8)",
  "reasoning": "Analyzing media planning deliverables. High relevance detected for paid media campaigns based on RFP keywords: 'social media', 'digital advertising', 'performance metrics'.",
  "reasoning_history": [
    "Stage 1: Loaded 1916 catalog items from database",
    "Stage 2: RFP summary extracted: goals=['brand awareness'], channels=['social','display'], markets=['US','CA']",
    "Stage 3: Recalled 450 candidates using hybrid scoring",
    "Stage 4: Batch 1/8 scored - top item: PM.01 (Media Planning) at 92% relevance"
  ]
}
```

**Final Response (completed):**
```json
{
  "job_id": "analyze_1234567890_xyz789",
  "status": "completed",
  "progress": 100,
  "result": {
    "Strategy": [
      {
        "code": "CS.01",
        "name": "Campaign Strategy Development",
        "confidence": 95,
        "reasoning": "Explicit match: RFP mentions 'campaign strategy' 3 times",
        "components": ["Research", "Strategy Development", "Documentation"],
        "tasks": {
          "Research": ["Market Analysis", "Competitor Research", "Audience Insights"],
          "Strategy Development": ["Strategic Framework", "Channel Strategy", "KPI Definition"]
        }
      }
    ],
    "Paid Media": [
      {
        "code": "PM.01",
        "name": "Media Planning & Buying",
        "confidence": 92,
        "reasoning": "High relevance: 'paid media', 'media buying', 'social ads' detected",
        "components": ["Media Planning", "Media Buying", "Optimization"],
        "tasks": {
          "Media Planning": ["Audience Targeting", "Budget Allocation", "Channel Selection"]
        }
      }
    ]
  },
  "deliverables_count": 23
}
```

#### Example 2: /api/scenarios

**Request:**
```json
POST /api/scenarios
{
  "selectedDeliverableCodes": ["CS.01", "PM.01", "CR.02"],
  "complexity": "Advanced",
  "tier": "T2_MediumVolume",
  "rateBand": "Standard_US",
  "pricingMode": "Per_Resource",
  "blendedRate": null,
  "projectStart": "2025-01-13T09:00:00",
  "sessionId": "session_1234567890_abc123"
}
```

**Response:**
```json
{
  "scenario": {
    "items": [
      {
        "Deliverable_Code": "CS.01",
        "Deliverable": "Campaign Strategy Development",
        "Component": "Research",
        "Task_Label": "Market Analysis",
        "Resource_Title": "Sr. Strategist",
        "Seniority": "Senior",
        "Planned_Hours": 16.0,
        "Rate_USD": 175.0,
        "Price_USD": 2800.0,
        "Department": "Strategy"
      },
      {
        "Deliverable_Code": "CS.01",
        "Deliverable": "Campaign Strategy Development",
        "Component": "Research",
        "Task_Label": "Competitor Research",
        "Resource_Title": "Strategist",
        "Seniority": "Mid",
        "Planned_Hours": 12.0,
        "Rate_USD": 125.0,
        "Price_USD": 1500.0,
        "Department": "Strategy"
      }
      // ... more tasks
    ],
    "totals": {
      "hours": 248.5,
      "price": 42850.0
    },
    "metadata": {
      "complexity": "Advanced",
      "tier": "T2_MediumVolume",
      "mode": "Per_Resource",
      "start_date": "2025-01-13T09:00:00",
      "session_id": "session_1234567890_abc123"
    }
  }
}
```

---

## 9. BUTTON-TO-LOGIC MAPPING

### 9.1 Step 1 Buttons

```
┌─────────────────────────────────────────────────────────────┐
│ BUTTON: Analyze with AI (#btnAnalyze)                       │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: static/app.js → boot() event listener        │
│                                                              │
│ LOGIC FLOW:                                                 │
│ 1. Validate input (text XOR file)                           │
│ 2. Get analysis mode (#analysis-mode value)                 │
│ 3. Get processing tier (#processing-tier value)             │
│ 4. Call /api/ai/analyze_job (POST)                          │
│ 5. Start polling /api/ai/jobs/{job_id} (every 1s)           │
│ 6. Update progress bar and status text                      │
│ 7. On completion:                                           │
│    - Store results in window.APP.summary                    │
│    - Render AI suggestions panel                            │
│    - Enable Step 2 navigation                               │
│                                                              │
│ ERROR HANDLING:                                             │
│ - No input → Alert "Please provide RFP text or file"        │
│ - File too large (>20MB) → Alert "File too large"           │
│ - API error → Display error message with retry button       │
│ - Job timeout (5min) → Alert "Analysis timed out"           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BUTTON: Clear All Data (#btnClearAllData)                   │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: clearAllDataWithConfirmation()               │
│                                                              │
│ LOGIC FLOW:                                                 │
│ 1. Show confirmation dialog                                 │
│ 2. If confirmed:                                            │
│    - Clear localStorage (all 'apb.*' keys)                  │
│    - Clear sessionStorage (all keys)                        │
│    - Clear in-memory state (window.APP, window.SCENARIOS)   │
│    - Call /api/clear_session (POST) to clear server cache  │
│    - Start new session (SessionManager.startNewSession())   │
│    - Reload page for clean state                            │
│                                                              │
│ CONFIRMATION MESSAGE:                                       │
│ "⚠️ Clear All Data?                                         │
│  This will:                                                 │
│  • Delete all stored RFP data                               │
│  • Clear all analysis results                               │
│  • Clear AI Assistant history                               │
│  • Reset the application to fresh state                     │
│  • Clear server-side cache                                  │
│                                                              │
│  This action cannot be undone. Continue?"                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BUTTON: Apply Template (#btn-apply-template)                │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: applyIndustryTemplate()                      │
│                                                              │
│ LOGIC FLOW:                                                 │
│ 1. Get selected industry (#industry-selector value)         │
│ 2. Get RFP text (if available)                              │
│ 3. Call /api/industry/suggest-deliverables (POST)           │
│ 4. Store industry deliverables in sessionStorage            │
│ 5. Show success alert with deliverable count                │
│ 6. Enable "Analyze with AI" to incorporate template         │
│                                                              │
│ SUPPORTED INDUSTRIES:                                       │
│ - luxury_fashion: 1.5x-2x pricing multipliers               │
│ - beauty: Seasonal campaigns, influencer partnerships       │
│ - real_estate: Property marketing, virtual tours            │
│ - retail: E-commerce, in-store experiences                  │
│ - lifestyle: Brand storytelling, experiential               │
│ - tech: Product launches, developer marketing               │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Step 2 Buttons

```
┌─────────────────────────────────────────────────────────────┐
│ BUTTON: Select All (Deliverables) (#s2-deliv-selectall)     │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: Inline event listener                        │
│                                                              │
│ LOGIC FLOW:                                                 │
│ 1. Get all visible deliverable codes (respects search filter)│
│ 2. For each code:                                           │
│    - selectionStore.deliverables.add(code)                  │
│    - If AUTO_SUGGEST: suggestComponents(code)               │
│ 3. Re-render all panels                                     │
│ 4. Update selection summary counters                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BUTTON: AI Suggest (Components) (#s2-comp-suggest)          │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: suggestComponentsForActiveDeliverable()      │
│                                                              │
│ LOGIC FLOW:                                                 │
│ 1. Get active deliverable code (S2.activeDeliverableCode)   │
│ 2. Get RFP text from sessionStorage                         │
│ 3. Call /api/agencydb/ai_suggest_components (POST)          │
│    - Sends: deliverable_code, rfp_text                      │
│    - Receives: [{component, confidence, reasoning}]         │
│ 4. For each suggested component:                            │
│    - Auto-select if confidence > 70%                        │
│    - Mark with AI badge in UI                               │
│ 5. Re-render components panel                               │
│ 6. Show success toast with suggestion count                 │
│                                                              │
│ GPT-5 PROMPT (backend):                                     │
│ "Given this RFP context and deliverable '{name}', which     │
│  components are most relevant? Consider:                    │
│  - Explicit mentions in RFP                                 │
│  - Implied requirements                                     │
│  - Industry best practices                                  │
│  Return JSON array with component, confidence (0-100),      │
│  and reasoning."                                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BUTTON: Proceed to Pricing (#btnProceedToStep3)             │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: Inline event listener                        │
│                                                              │
│ LOGIC FLOW:                                                 │
│ 1. Validate selection (at least 1 deliverable)              │
│ 2. Store selections in localStorage                         │
│ 3. Hide Step 2, show Step 3                                 │
│ 4. Scroll to top                                            │
│ 5. Set default project start date (next Monday 09:00)       │
│ 6. Load UI dropdowns from /api/options                      │
│                                                              │
│ VALIDATION:                                                 │
│ - If no deliverables selected:                              │
│   Alert "Please select at least one deliverable"            │
│   Stay on Step 2                                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BUTTON: LEARN (opt-in) (#learnBtn)                          │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: Learning Brain integration                   │
│                                                              │
│ LOGIC FLOW:                                                 │
│ 1. Collect user's selection data:                           │
│    - Selected deliverable codes                             │
│    - Selected components (by deliverable)                   │
│    - RFP text                                               │
│ 2. Call /api/brain/learn (POST)                             │
│ 3. Learning Brain analyzes:                                 │
│    - What user added vs AI suggestions                      │
│    - What user removed                                      │
│    - Confidence adjustments needed                          │
│ 4. In SHADOW mode: Record only (no behavior change)         │
│ 5. In ACTIVE mode: Requires admin to publish changes        │
│ 6. Show success toast                                       │
│                                                              │
│ PURPOSE:                                                    │
│ - Improve AI suggestions over time                          │
│ - Learn from expert user selections                         │
│ - Adapt to industry-specific patterns                       │
│ - Maintain industry-agnostic core (bounded adjustments)     │
└─────────────────────────────────────────────────────────────┘
```

### 9.3 Step 3 Buttons

```
┌─────────────────────────────────────────────────────────────┐
│ BUTTON: Build Scenario (#btnBuild)                          │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: buildFromCurrentSelection()                  │
│                                                              │
│ LOGIC FLOW:                                                 │
│ 1. Collect project config from UI:                          │
│    - complexity (#complexity value)                         │
│    - tier (#volumeTier value)                               │
│    - rateBand (#rateBand value)                             │
│    - pricingMode (#pricingMode value)                       │
│    - blendedRate (#blendedRate value, if Flat_Blended)      │
│    - projectStart (#projectStart value)                     │
│    - clientBudget (#clientBudget value)                     │
│                                                              │
│ 2. Collect selected deliverables:                           │
│    - codes = Array.from(selectionStore.deliverables)        │
│                                                              │
│ 3. Build request payload:                                   │
│    {                                                         │
│      selectedDeliverableCodes: codes,                       │
│      complexity, tier, rateBand, pricingMode,               │
│      blendedRate, projectStart, sessionId                   │
│    }                                                         │
│                                                              │
│ 4. Call /api/scenarios (POST)                               │
│                                                              │
│ 5. On success:                                              │
│    - Store scenario in SCENARIO_STORE[sessionId]            │
│    - Call updatePricingTable()                              │
│    - Call updatePricingSummary()                            │
│    - Enable "Proceed to Timeline" button                    │
│                                                              │
│ 6. On error:                                                │
│    - Display error message                                  │
│    - Keep "Build Scenario" button enabled for retry         │
│                                                              │
│ BACKEND PROCESSING:                                         │
│ - Query all_rows for selected deliverables                  │
│ - Get scenario hours column: "{complexity}__{tier}_Hours"   │
│ - Join role rates from role_rate_card                       │
│ - Calculate Price_USD = Rate_USD × Planned_Hours            │
│ - Group by deliverable → component → task                   │
│ - Apply pricing mode (blended vs per-resource)              │
│ - Return nested structure with totals                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BUTTON: Re-build Scenario (#btn-rebuild-scenario)           │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: rebuildScenario()                            │
│                                                              │
│ LOGIC FLOW:                                                 │
│ Same as Build Scenario, but:                                │
│ 1. Preserves user edits:                                    │
│    - Retainer type changes (PROJECT vs RETAINER)            │
│    - Retainer months adjustments                            │
│    - Custom hour overrides                                  │
│    - Custom rate overrides                                  │
│                                                              │
│ 2. Re-fetches base data from database                       │
│                                                              │
│ 3. Re-applies user customizations on top                    │
│                                                              │
│ USE CASES:                                                  │
│ - User changed complexity/tier dropdowns                    │
│ - User changed rate band                                    │
│ - User toggled pricing mode                                 │
│ - User wants to refresh with latest database values         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BUTTON: AI Suggest Retainer Items                           │
│         (#btn-global-retainer-suggest)                      │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: askAIForRetainerSuggestions()                │
│                                                              │
│ LOGIC FLOW:                                                 │
│ 1. Get selected deliverable codes                           │
│ 2. Get RFP text from sessionStorage                         │
│ 3. Build request:                                           │
│    {                                                         │
│      deliverable_codes: codes,                              │
│      rfp_text: rfpText                                      │
│    }                                                         │
│                                                              │
│ 4. Call /api/pricing/retainer_suggest (POST)                │
│                                                              │
│ 5. Backend (GPT-5) analyzes each deliverable:               │
│    - Check for ongoing/recurring nature                     │
│    - Look for monthly/annual keywords                       │
│    - Analyze deliverable type (management vs development)   │
│    - Recommend: PROJECT vs RETAINER                         │
│    - If RETAINER: Suggest months (6/12/24)                  │
│                                                              │
│ 6. On response:                                             │
│    - For each suggested retainer:                           │
│      • pricingData.deliverableTypes.set(code, 'RETAINER')   │
│      • pricingData.retainers.set(code, suggested_months)    │
│    - For non-retainers:                                     │
│      • pricingData.deliverableTypes.set(code, 'PROJECT')    │
│                                                              │
│ 7. Re-render pricing table with retainer indicators         │
│                                                              │
│ 8. Show success alert:                                      │
│    "✅ AI Retainer Analysis Complete!                       │
│     {count} of {total} deliverables suggested as retainers: │
│     • {name} ({months} months)                              │
│     • ..."                                                  │
│                                                              │
│ ERROR HANDLING:                                             │
│ - No deliverables selected → Alert "Please select..."       │
│ - No RFP text → Alert "Please provide RFP text..."          │
│ - API error → Alert with retry suggestion                   │
└─────────────────────────────────────────────────────────────┘
```

### 9.4 Step 4 Buttons

```
┌─────────────────────────────────────────────────────────────┐
│ BUTTON: Generate AI Timeline (#btnGenerateTimeline)         │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: generateAITimeline()                         │
│                                                              │
│ LOGIC FLOW:                                                 │
│ 1. Get scenario data from SCENARIO_STORE                    │
│ 2. Get project config (start date, use_slack, etc.)         │
│ 3. Build request:                                           │
│    {                                                         │
│      scenario_data: scenario,                               │
│      project_start: projectStart,                           │
│      rfp_text: rfpText,                                     │
│      governance_level: "standard",                          │
│      session_id: sessionId                                  │
│    }                                                         │
│                                                              │
│ 4. Call /api/timeline/generate_ai (POST)                    │
│                                                              │
│ 5. Start SSE polling:                                       │
│    - Connect to /api/timeline/jobs/{job_id}                 │
│    - Listen for server-sent events                          │
│    - Update progress bar in real-time                       │
│    - Display current stage messages                         │
│                                                              │
│ 6. Backend processing (ai_timeline_manager.py):             │
│    Stage 1: Parse deliverables into tasks                   │
│    Stage 2: Analyze dependencies (GPT-5)                    │
│    Stage 3: Calculate durations                             │
│    Stage 4: Apply Critical Path Method (CPM)                │
│    Stage 5: Resource leveling                               │
│    Stage 6: Insert CCPM buffers                             │
│    Stage 7: Add governance milestones                       │
│                                                              │
│ 7. On completion:                                           │
│    - Receive timeline tasks array                           │
│    - Store in window.currentTimelineTasks                   │
│    - Call initializeGanttChart(tasks)                       │
│    - Show success toast                                     │
│    - Enable export buttons                                  │
│                                                              │
│ 8. On error:                                                │
│    - Display error message with details                     │
│    - Offer "Try Simple Timeline" fallback                   │
│    - Keep "Generate AI Timeline" enabled for retry          │
│                                                              │
│ TIMEOUT: 5 minutes (backend enforced)                       │
│ RETRY: Exponential backoff for API calls                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BUTTON: Final Ship Project (#btnFinalShip)                  │
├─────────────────────────────────────────────────────────────┤
│ CLICK HANDLER: callFinalShip()                              │
│                                                              │
│ LOGIC FLOW:                                                 │
│ 1. Validate prerequisites:                                  │
│    - Scenario exists?                                       │
│    - Timeline exists?                                       │
│    - Project name provided?                                 │
│                                                              │
│ 2. Collect export config:                                   │
│    - includeAnchors = #toggle-anchors checked               │
│    - projectName = #projectName value                       │
│    - projectStart = #projectStart value                     │
│                                                              │
│ 3. Build WBS DataFrame:                                     │
│    - Merge scenario + timeline data                         │
│    - Apply column ordering (WF_COLUMNS)                     │
│    - Calculate WBS_ID hierarchy                             │
│    - Add Service_Department                                 │
│                                                              │
│ 4. Call /api/final_ship (POST):                             │
│    {                                                         │
│      scenario: scenario_data,                               │
│      timeline: timeline_tasks,                              │
│      projectName, projectStart, includeAnchors,             │
│      sessionId                                              │
│    }                                                         │
│                                                              │
│ 5. Backend processing:                                      │
│    - Build WBS DataFrame                                    │
│    - Generate Workfront XML                                 │
│    - Generate Excel export                                  │
│    - Generate MS Project XML                                │
│    - Create ZIP archive                                     │
│                                                              │
│ 6. Download ZIP:                                            │
│    - Filename: "{projectName}_Workfront_Export_FINAL_SHIP_  │
│                {timestamp}_COMPLETE.zip"                    │
│    - Contains:                                              │
│      • Workfront_Export.xml                                 │
│      • Workfront_Export.xlsx                                │
│      • MS_Project_Export.xml                                │
│                                                              │
│ 7. Show success message:                                    │
│    "✅ Project exported successfully!                       │
│     Download includes:                                      │
│     • Workfront XML (ready to import)                       │
│     • Excel (for review/editing)                            │
│     • MS Project XML (for Microsoft Project)"               │
│                                                              │
│ ERROR HANDLING:                                             │
│ - Missing prerequisites → Alert with specific missing item  │
│ - Export failure → Display error with retry option          │
│ - Large export (>5000 tasks) → Show warning, proceed        │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. STATE MANAGEMENT FLOW

### 10.1 Session Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ SESSION CREATION                                            │
└─────────────────────────────────────────────────────────────┘

User opens app
│
├─ Check localStorage for existing session:
│  - Key: 'apb.currentSession'
│  - Exists? → Use existing session_id
│  - Missing? → Generate new session_id
│     Format: 'session_{timestamp}_{random}'
│     Example: 'session_1234567890_abc123'
│
├─ Initialize session-scoped storage:
│  - localStorage: Long-term persistence
│    • 'apb.{sessionId}.selections'
│    • 'apb.{sessionId}.scenario'
│    • 'apb.{sessionId}.timeline'
│    • 'apb.{sessionId}.rfpText'
│  
│  - sessionStorage: Tab-specific
│    • 'rfp_text' (current RFP)
│    • 'job_id' (current AI job)
│    • 'industry_template' (if selected)
│  
│  - In-memory: Runtime only
│    • window.APP.summary (AI analysis)
│    • window.SCENARIOS (scenario data)
│    • window.currentTimelineTasks
│
└─ Register cleanup hooks:
   - window.addEventListener('beforeunload') → Save state
   - Background timer (hourly) → Clean old sessions

┌─────────────────────────────────────────────────────────────┐
│ STATE PERSISTENCE STRATEGY                                  │
└─────────────────────────────────────────────────────────────┘

WHAT to persist WHERE:

localStorage (survives page reload, shared across tabs):
├─ User selections (Step 2)
├─ Built scenarios (Step 3)
├─ Timeline data (Step 4)
├─ Project config (dates, names, etc.)
└─ Session ID

sessionStorage (survives page reload, isolated per tab):
├─ RFP text (current analysis)
├─ Job IDs (polling state)
├─ Industry template selection
└─ Temporary UI state

In-memory (lost on page reload, fastest access):
├─ AI analysis results (can be large)
├─ Gantt chart instance
├─ UI component states
└─ Cached API responses

WHEN to persist:

Immediate (on change):
├─ User toggles deliverable → localStorage.setItem()
├─ User edits hours → pricingData.customHours.set()
├─ User uploads file → sessionStorage.setItem('rfp_text')

Debounced (after 500ms idle):
├─ Search filter changes
├─ Text input edits

On navigation:
├─ Step 1 → Step 2: Save RFP text + job_id
├─ Step 2 → Step 3: Save selections
├─ Step 3 → Step 4: Save scenario

Before unload:
├─ window.addEventListener('beforeunload')
├─ Save all current state
├─ Mark session as active

┌─────────────────────────────────────────────────────────────┐
│ STATE RESTORATION (on page load)                            │
└─────────────────────────────────────────────────────────────┘

boot() function in app.js:
│
├─ 1. Restore session:
│  - SessionManager.getCurrentSessionId()
│  - Check for 'apb.data_cleared' flag → If set, skip restore
│  
├─ 2. Restore Step 1 data:
│  - Get 'apb.{sessionId}.rfpText' from localStorage
│  - Populate #rfpText textarea
│  - Check sessionStorage for active job_id
│  - If found → Resume polling
│  
├─ 3. Restore Step 2 selections:
│  - Get 'apb.{sessionId}.selections' from localStorage
│  - Populate selectionStore:
│    • selectionStore.deliverables = new Set(data.deliverables)
│    • selectionStore.componentsByDeliv = new Map(data.components)
│    • selectionStore.l3ByComponent = new Map(data.l3)
│  - Render panels with restored selections
│  
├─ 4. Restore Step 3 scenario:
│  - Get 'apb.{sessionId}.scenario' from localStorage
│  - Load into SCENARIO_STORE[sessionId]
│  - Render pricing table
│  - Restore project config values
│  
└─ 5. Restore Step 4 timeline:
   - Get 'apb.{sessionId}.timeline' from localStorage
   - Load into window.currentTimelineTasks
   - Initialize Gantt chart
   - Restore view mode preference
```

### 10.2 Cross-Component Communication

```
┌─────────────────────────────────────────────────────────────┐
│ OBSERVABLE PATTERN (Pub/Sub)                                │
└─────────────────────────────────────────────────────────────┘

Event: Deliverable Selected
├─ Publisher: toggleDeliverable(code, isChecked)
├─ Actions:
│  1. Update selectionStore.deliverables
│  2. Fire event: window.dispatchEvent(new CustomEvent(
│       'deliverableChanged', { detail: { code, isChecked } }))
│  
└─ Subscribers:
   - Components Panel → Re-render if active deliverable changed
   - Summary Panel → Update deliverable count
   - AI Suggestions → Mark if AI-suggested
   - Pricing Preview → Update estimated hours/cost

Event: Scenario Built
├─ Publisher: buildFromCurrentSelection()
├─ Actions:
│  1. Store in SCENARIO_STORE[sessionId]
│  2. Fire event: window.dispatchEvent(new CustomEvent(
│       'scenarioBuilt', { detail: { sessionId, scenario } }))
│  
└─ Subscribers:
   - Pricing Table → Render new data
   - Summary Panels → Update totals
   - Timeline Button → Enable if disabled
   - Export Buttons → Enable if disabled

Event: Timeline Generated
├─ Publisher: generateAITimeline() → on completion
├─ Actions:
│  1. Store in window.currentTimelineTasks
│  2. Fire event: window.dispatchEvent(new CustomEvent(
│       'timelineGenerated', { detail: { tasks } }))
│  
└─ Subscribers:
   - Gantt Chart → Initialize/update visualization
   - Resource Analysis → Calculate utilization
   - Export Buttons → Enable final ship
   - Summary Panel → Show project duration
```

---

## 11. CRITICAL DECISION TREES

### 11.1 Component Auto-Suggestion Logic

```
User selects deliverable checkbox
│
├─ Is AUTO_SUGGEST_ON_SELECT enabled?
│  ├─ NO → Do nothing (user selects components manually)
│  └─ YES → Continue
│
├─ Is USE_GPT_FOR_AUTOSUGGEST enabled?
│  │
│  ├─ YES → AI-Powered Suggestion
│  │  1. Get RFP text from sessionStorage
│  │  2. Call /api/agencydb/ai_suggest_components
│  │     - Sends: deliverable_code, rfp_text
│  │     - GPT-5 analyzes: What components are relevant?
│  │  3. Receive: [{component, confidence, reasoning}]
│  │  4. Auto-select components with confidence > 70%
│  │  5. Mark with AI badge in UI
│  │  6. Store in selectionStore.componentsByDeliv
│  │
│  └─ NO → Rule-Based Suggestion
│     1. Call /api/agencydb/components/{deliverable_code}
│     2. Get all available components
│     3. Apply basic rules:
│        - If component name contains RFP keywords → Select
│        - If component is marked "default" → Select
│     4. Store in selectionStore.componentsByDeliv
│
└─ Render components panel with selections
```

### 11.2 Pricing Mode Selection Impact

```
User selects pricing mode (#pricingMode)
│
├─ Flat_Blended Selected
│  │
│  ├─ Enable #blendedRate input
│  ├─ Get blended rate value (default: $195)
│  │
│  ├─ For each task in scenario:
│  │  - Original: Rate_USD = role_rate_card[Resource_Title, Seniority]
│  │  - Override: Rate_USD = blended_rate
│  │  - Recalculate: Price_USD = blended_rate × Planned_Hours
│  │
│  └─ Benefits:
│     • Simpler client presentation (one rate)
│     • Faster calculation
│     • Hides resource-level detail
│
└─ Per_Resource Selected
   │
   ├─ Disable #blendedRate input
   │
   ├─ For each task in scenario:
   │  - Lookup: role_rate_card[Resource_Title, Seniority]
   │  - Apply rate band multiplier (if selected)
   │  - Calculate: Price_USD = Rate_USD × Planned_Hours
   │
   └─ Benefits:
      • Accurate resource-level pricing
      • Shows cost breakdown by role
      • Useful for internal planning
      • Required for resource allocation analysis
```

### 11.3 Timeline Buffer Insertion

```
User generates timeline
│
├─ Check use_slack setting (#useSlack or config)
│  │
│  ├─ FALSE → No buffers
│  │  - Calculate task durations only
│  │  - No review periods
│  │  - Back-to-back scheduling
│  │
│  └─ TRUE → Insert buffers
│
├─ Slack Type Selection:
│  │
│  ├─ 1. Internal Review Buffers
│  │  - After each milestone/deliverable
│  │  - Duration: slack_internal_days (default: 7)
│  │  - Purpose: Team review, QA, revisions
│  │
│  ├─ 2. Client Review Buffers
│  │  - After client-facing deliverables
│  │  - Duration: slack_client_days (default: 14)
│  │  - Purpose: Client feedback cycle
│  │
│  └─ 3. Global Slack Percentage
│     - Applied to entire timeline
│     - Percentage: slack_pct (default: 10%)
│     - Purpose: General contingency
│
├─ CCPM Buffer Strategy (if enabled):
│  │
│  ├─ Project Buffer:
│  │  - Location: End of critical path
│  │  - Size: 15% of critical path duration
│  │  - Purpose: Protect project deadline
│  │
│  └─ Feeding Buffers:
│     - Location: Where non-critical joins critical
│     - Size: 10% of feeding chain duration
│     - Purpose: Protect critical path from delays
│
└─ Final Timeline:
   - Original task durations
   + Internal review buffers
   + Client review buffers
   + Global slack percentage
   + CCPM buffers (if enabled)
   = Total project duration
```

---

## 12. PERFORMANCE & CACHING SYSTEMS

### 12.1 Database Caching Strategy

```
┌─────────────────────────────────────────────────────────────┐
│ PICKLE CACHE SYSTEM (Sub-2ms Load Times)                    │
└─────────────────────────────────────────────────────────────┘

Startup sequence:
│
├─ 1. Search for v4 database file:
│  Standard locations:
│  - test_outputs/Replit_App_DB_READABLE_FullRows_v4.xlsx
│  - Replit_App_DB_READABLE_FullRows_v4.xlsx
│  - data/Replit_App_DB_READABLE_FullRows_v4.xlsx
│  
│  Timestamped fallback:
│  - attached_assets/Replit_App_DB_READABLE_FullRows_v4_*.xlsx
│  - Select most recent by timestamp
│
├─ 2. Check for pickle cache:
│  Cache file: {excel_path}.pkl
│  
│  Validation:
│  - Exists?
│  - Newer than Excel file? (mtime check)
│  - Valid data? (>10 rows, has 'Component' column)
│  
│  If valid:
│    → Load pickle (3.3ms average)
│    → Skip Excel parsing
│    → Return cached AgencyDB instance
│  
│  If invalid/missing:
│    → Continue to Excel load
│
├─ 3. Load from Excel:
│  - Read 24 sheets into pandas DataFrames (200ms)
│  - Apply normalization pipeline:
│    • _normalize_component_column()
│    • _normalize_task_label_column()
│    • _normalize_role_and_seniority_columns()
│    • _normalize_rate_card_seniority()
│    • _normalize_code_columns()
│  
│  - Save to pickle for next boot:
│    pickle.dump(db, file)
│  
│  - Return AgencyDB instance
│
└─ 4. Store in app.state.db (global singleton)
   - Available to all API endpoints
   - No re-loading during runtime
   - Thread-safe (Python GIL)

CACHE INVALIDATION:
- Excel file modified → Pickle outdated (mtime check)
- Pickle file deleted → Regenerate on next load
- Code change to normalization → Manual cache clear needed
  (Delete .pkl files to force regeneration)
```

### 12.2 Embedding Cache (Session-Isolated)

```
┌─────────────────────────────────────────────────────────────┐
│ EMBEDDING CACHE (Prevents Cross-RFP Contamination)          │
└─────────────────────────────────────────────────────────────┘

Structure:
_EMBEDDING_CACHE = {
  'session_1234567890_abc123': {
    'hash_of_text_1': [0.123, 0.456, ...],  # 3072-dim vector
    'hash_of_text_2': [0.789, 0.012, ...],
    ...
  },
  'session_9876543210_xyz789': {
    'hash_of_text_3': [0.234, 0.567, ...],
    ...
  }
}

Cache flow:
│
├─ embed_many(texts, client, session_id)
│  │
│  ├─ For each text:
│  │  1. Hash text → cache_key
│  │  2. Check: _EMBEDDING_CACHE[session_id].get(cache_key)
│  │  3. Hit? → Return cached vector (0ms API call saved)
│  │  4. Miss? → Continue to API
│  │
│  ├─ Batch uncached texts
│  ├─ Call OpenAI API: client.embeddings.create(
│  │    model="text-embedding-3-large",
│  │    input=uncached_texts
│  │  )
│  │
│  ├─ Store new embeddings in cache:
│  │  _EMBEDDING_CACHE[session_id][cache_key] = vector
│  │
│  └─ Return all vectors (cached + new)
│
└─ Benefits:
   - Same RFP re-analyzed → 100% cache hit (0 API calls)
   - Different RFP → 0% cache hit (isolated session)
   - Catalog embeddings → Shared across sessions
   - TTL: 24 hours → Automatic cleanup

Cache statistics:
├─ Total sessions: len(_EMBEDDING_CACHE)
├─ Total cached: sum(len(cache) for cache in _EMBEDDING_CACHE.values())
├─ Hit rate: (cache_hits / total_requests) × 100%
└─ Memory usage: ~12KB per 3072-dim vector
```

### 12.3 TF-IDF Analyzer Cache

```
┌─────────────────────────────────────────────────────────────┐
│ TF-IDF ANALYZER CACHE (Fast2 Pipeline)                      │
└─────────────────────────────────────────────────────────────┘

Cache location: /tmp/tfidf_cache/tfidf_{hash}.pkl

Build process:
│
├─ 1. Load AI_Index from database
│  - Contains: Deliverables, Components, Tasks, Keywords
│  - Rows: ~2000 catalog items
│
├─ 2. Build TF-IDF matrix:
│  - Tokenize all catalog items
│  - Calculate term frequencies (TF)
│  - Calculate inverse document frequencies (IDF)
│  - Build sparse matrix (scipy.sparse)
│
├─ 3. Save to pickle:
│  - Hash: Hash of AI_Index content
│  - File: /tmp/tfidf_cache/tfidf_{hash}.pkl
│  - Size: ~2MB
│
└─ 4. Load on subsequent requests:
   - Check cache by hash
   - Load pickle (5ms)
   - Skip TF-IDF rebuild (saves 100ms)

Usage in Fast Mode:
│
├─ Preload at startup (app_perf/fast_pipeline.py)
│  - initialize_analyzer(app.state)
│  - Store in app.state.tfidf_analyzer
│
├─ On RFP analysis:
│  - Get analyzer from app.state (no load time)
│  - Transform RFP text → TF-IDF vector
│  - Calculate cosine similarity with catalog
│  - Return top matches
│
└─ Performance gain:
   - Without cache: ~150ms per analysis
   - With cache: ~5ms per analysis
   - 30× speedup
```

### 12.4 Batch Processing Optimization

```
┌─────────────────────────────────────────────────────────────┐
│ GPT-5 BATCH PROCESSING (Parallel + Retry)                   │
└─────────────────────────────────────────────────────────────┘

Configuration (user-selectable tiers):
├─ Mini: 30 items/batch (fastest)
├─ Fast: 30 items/batch
├─ Balanced: 25 items/batch (default, recommended)
├─ Thinking: 25 items/batch (GPT-5 deep reasoning)
├─ Accurate: 20 items/batch
└─ Pro: 20 items/batch (maximum precision)

Processing flow:
│
├─ 1. Chunk candidates into batches:
│  Example: 450 candidates, batch_size=25
│  → 18 batches of 25 items each
│
├─ 2. For each batch (sequential for now, parallel later):
│  │
│  ├─ Build JSON schema prompt:
│  │  {
│  │    "items": [
│  │      {
│  │        "id": "deliverable_code",
│  │        "relevance": 0-100,
│  │        "confidence": 0-100,
│  │        "reasoning": "evidence",
│  │        "risks": ["potential issues"]
│  │      }
│  │    ]
│  │  }
│  │
│  ├─ Call GPT-5 with retry logic:
│  │  - Max retries: 3
│  │  - Backoff: 1s → 2s → 4s
│  │  - On rate limit: 2× delay
│  │  - On timeout: 1.5× delay
│  │
│  └─ Parse response:
│     - Validate JSON structure
│     - Repair if malformed (repair_json_response)
│     - Extract scores and reasoning
│
├─ 3. Aggregate results across batches:
│  - Merge scores by deliverable code
│  - Combine reasoning from all batches
│  - Calculate overall confidence
│
└─ 4. Sort and return top matches:
   - Sort by relevance score (descending)
   - Group by department
   - Include evidence and reasoning

Performance metrics:
├─ Fast Mode (lexical-only):
│  - 450 candidates
│  - 0 GPT-5 calls
│  - ~60 seconds total
│
└─ Deep Mode (hybrid + GPT-5):
   - 450 candidates → 18 batches
   - 18 GPT-5 calls
   - ~2-5 minutes total
   - Parallelization potential: 4× speedup with 4 workers
```

---

## CONCLUSION

This Master Control Room document provides:

1. **Complete system map** - Every component, logic flow, and decision tree
2. **Button-to-backend traceability** - Know exactly what each UI element does
3. **Database schema understanding** - How data flows from Excel → API → UI
4. **AI intelligence breakdown** - Fast vs Deep modes, GPT-5 integration, caching
5. **State management clarity** - Session isolation, persistence, restoration
6. **Performance optimization insights** - Pickle caching, embedding cache, TF-IDF
7. **API endpoint directory** - Every endpoint with request/response examples
8. **Critical decision trees** - Component auto-suggest, pricing modes, buffers

**How to use this document:**

- **Architecture discussions** - Reference data flow diagrams
- **Feature development** - Follow button-to-logic mappings
- **Debugging** - Trace decision trees and state flows
- **Performance tuning** - Check caching strategies
- **API integration** - Use endpoint directory with examples
- **Onboarding** - System overview + user journey sections

**Next steps:**

1. Review specific sections relevant to your current work
2. Use this as a reference when proposing changes
3. Update this document as the system evolves
4. Create sub-documents for complex subsystems (e.g., "Timeline Generation Deep Dive")

This document is a **living blueprint** - it should grow with the application.
