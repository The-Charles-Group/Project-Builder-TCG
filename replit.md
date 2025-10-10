# Agency Project Builder

## Overview
This project is a web-based Agency Project Builder designed to streamline the proposal creation process for creative and digital agencies. It analyzes Request for Proposal (RFP) content to suggest relevant deliverables, builds project scenarios based on different complexity and tier combinations, calculates pricing using role rates and hours, and generates timeline projections with built-in slack. The system aims to automate and enhance the efficiency of creating project estimates and timelines, thereby enhancing efficiency and accuracy in project proposal generation.

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Changes

### October 10, 2025 - Workspace Cleanup & Database Consolidation
- **Workspace Organization**: Reduced root directory from 40+ files to 25 organized files by archiving 23 old/duplicate files
- **Database Consolidation**: v4 database (`test_outputs/Replit_App_DB_READABLE_FullRows_v4.xlsx`) is now the primary database with 1,916 rows and 52 deliverable codes
- **Archive Structure**: Created `archive/` directory with three subdirectories:
  - `old_code/`: Legacy AI planner and old main.py backups (preserved for reference)
  - `old_databases/`: v3 database and duplicate v4 files
  - `test_exports/`: 15 XML/XLSX test export files from Oct 9-10
- **Critical Fix**: Added `app.state.db` initialization in startup event to properly load AgencyDB for AI planner
- **Database Loading**: v4 database successfully loads at startup with 24 configuration sheets including Rate_Bands, Bundle_Rules_Table, Timeline_Scaling, UI_Options
- **Active Dependencies**: `ai_weighted_matcher.py` (Step 1 RFP analysis) and `parallelize_same_name_links.py` (timeline parallelization) remain in root as they are actively used

## System Architecture

### Backend Architecture
- **Framework**: FastAPI (Python) for the REST API.
- **Data Processing**: Pandas DataFrames for handling Excel/CSV data, calculations, and manipulations.
- **File Handling**: Supports parsing of PDF and DOCX documents, and Excel file uploads.
- **Core Logic**: Implements RFP analysis, scenario building, pricing engine, timeline calculation, and Workfront-compatible export.
- **AI Planner v3 (GPT-4o + AgencyDB)**: Advanced reasoning-based AI intelligence layer connected to real database with granular task selection:
  - **AgencyDB Integration**: Directly connects to AgencyDB (app.state.db) instead of ZIP catalogs, returns REAL deliverable codes (DEL-0027, etc.)
  - **Granular L2 Task Selection**: AI explicitly selects/deselects individual L2 tasks based on relevance (not bulk inclusion) - sets select=true/false per task
  - **Holistic Analysis**: Considers complete project flow from start to finish, includes dependency expansion automatically
  - **One-Click Workflow**: "Analyze with AI" button triggers summary + deliverable suggestions simultaneously
  - **Evidence-Based Matching**: High-recall semantic retrieval (embeddings + lexical scoring) → LLM re-ranking → calibrated confidence scores
  - **Calibrated Confidence**: Bayesian-style calibration with configurable strictness (high/balanced/recall gates at 70%/58%/48%)
  - **Smart Multipliers**: Complexity, channel count, market count, and compliance factors dynamically adjust planned hours
  - **Auto-Relax & Rescue**: Automatically relaxes thresholds and has fallback logic to guarantee non-empty suggestions
  - **Six Departments**: Creative, Strategy, Paid Media, Content, Technology, Integrated Marketing Management
  - **API Endpoints**: `/api/ai/analyze` (main planner with AgencyDB), `/api/ai/health` (status check with catalog stats)
- **Timeline Scheduler Kit**: AI-powered timeline optimization with SS+lag overlaps:
  - **MSPDI Pipeline**: Complete Microsoft Project XML parser, optimizer, and writer
  - **Smart Overlaps**: Automatically converts FS dependencies to SS+lag based on predefined rules (e.g., Design 60% → Dev starts)
  - **Gatekeeper Preservation**: Keeps review/approval chains intact (Internal Review → Client Review → Revisions → Final)
  - **Cycle Breaking**: Automatically resolves circular dependencies
  - **Duration Rounding**: Rounds all durations to whole days for cleaner timelines
  - **Units Recalculation**: Recomputes resource units based on work and duration
  - **Multi-Format Export**: Generates optimized XML, Gantt JSON, explanations JSON, and Excel audit trail
  - **API Endpoints**: `/api/schedule/optimize` (run optimization), `/api/schedule/download/{file_type}/{base_name}` (download results)
  - **Security**: Path traversal protection with regex validation and absolute path verification
- **Legacy AI Matching**: Original weighted matching rules system (now deprecated in favor of GPT-4o planner but kept for reference)
- **Parallel Processing**: Implemented parallel processing of PDF images with OpenAI Vision API for faster analysis and real-time progress tracking. Includes job tracking, retry logic, and robust error handling.
- **Smart Image Analysis**: Two-tier image processing system that dramatically reduces processing time and cost for PDFs with many decorative images:
  - **Pre-filtering**: Hash-based deduplication and size filtering (<100px) to eliminate logos, icons, and repeated images
  - **Quick Relevance Scan**: Fast 10-token GPT-5 check to identify images containing charts, diagrams, wireframes, or project requirements
  - **Deep Analysis**: Full 500-token analysis only for relevant images, reducing 72-image PDFs to ~8-10 relevant images
  - **User Control**: Optional toggle in UI to disable image analysis entirely for text-only processing
  - **Two-Phase Progress**: Real-time UI updates showing quick scan progress and deep analysis phase separately
- **Database Architecture**: 
  - **Primary Database**: v4 (`test_outputs/Replit_App_DB_READABLE_FullRows_v4.xlsx`) with 1,916 rows, 52 deliverable codes (DEL-0001 to DEL-0052)
  - **Initialization**: AgencyDB loaded into `app.state.db` during server startup via `@app.on_event("startup")` decorator
  - **v4 Features**: 24 configuration sheets including Rate_Bands, Bundle_Rules_Table, Timeline_Scaling, UI_Options (removed "Category" column from v3)
  - **Backwards Compatibility**: Gracefully handles v3 database structure with missing sheet detection and fallback values
- **CORS**: Configured to allow cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow, simplified to focus on a single scenario (Scenario A).
- **Styling**: Uses CSS custom properties for theming, including a dark mode.
- **State Management**: Centralized `selectionStore` as single source of truth with Proxy-backed compatibility layer for legacy code paths.
- **UI Improvements**: Features a 3-column layout (Deliverables | Components | Summary), search functionality, and enhanced summary panel with hierarchical display and individual remove buttons.
- **AI Planner UI**: New unified interface showing GPT-4o analysis results with:
  - **Summary Panel**: RFP summary with goals, channels, markets, complexity, and total planned hours
  - **Suggestions Panel**: Evidence-backed deliverable suggestions organized by department with calibrated confidence scores (75%+ green, 50-75% yellow, <50% red)
  - **Component Details**: Expandable component and task breakdowns with reasoning and hour estimates
  - **Risk Indicators**: Highlighted compliance and risk flags for alcohol/regulated industries
- **Timeline Accuracy**: Incorporates business days calculation with US/MX holiday calendar and excludes weekends from timeline end dates.
- **XML Export Control**: UI toggle for optional inclusion of Start/End anchor milestones in XML exports.

### Data Storage Pattern
- **Primary Storage**: Excel/CSV files serve as the main source for business rules and configuration data.
- **Data Models**: In-memory DataFrames are loaded from spreadsheets to define tasks, deliverables, pricing rules, rate cards, timeline parameters, scaling factors, bundle configurations, hour allocations, and scenario templates.

### API Design
- Provides RESTful endpoints for data loading, options retrieval, and scenario generation.
- Supports file uploads for RFP documents and Excel configuration files.
- Uses JSON for configuration data and calculated scenario responses.
- Serves static files for frontend assets.
- Includes new endpoints for weighted AI suggestions (`/api/step2/ai/weights`), bulk L3 task retrieval (`/api/step2/l3/bulk`), and scenario refetching (`/api/scenarios`).

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

### File Format Support
- **Excel/CSV**: Core data source.
- **PDF/DOCX**: For RFP document parsing.
- **JSON**: For API data exchange.

## Database Configuration

### Development vs Production Database
The application uses **automatic database switching** based on the environment:

#### **Development Environment** (Current)
- Uses Replit's built-in PostgreSQL database
- Connection via `DATABASE_URL` environment variable
- Database credentials available as environment variables: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- Safe for testing and feature development
- Database: Neon PostgreSQL 16.9

#### **Production Environment** (When Published)
- Automatically switches to production database
- Connection string stored in `/tmp/replitdb` file
- Completely separate from development database
- Ensures production data is isolated from development

### How to Use the Database

#### **In Your Code**
Use the `database.py` helper module to get the correct database connection:

```python
from database import get_database_url, get_connection_params

# Get the full database URL (works in both dev and production)
db_url = get_database_url()

# Or get individual connection parameters
params = get_connection_params()
# params = {"host": "...", "port": 5432, "user": "...", "password": "...", "database": "..."}
```

The helper automatically:
1. Checks for `/tmp/replitdb` (production) first
2. Falls back to `DATABASE_URL` environment variable (development)
3. Prints which environment is being used

#### **Testing the Connection**
Run the test script to verify database connectivity:
```bash
python test_db_connection.py
```

### Publishing with Production Database

When you're ready to publish your app:

1. **Click "Publish"** in Replit
2. **Enable "Production Database"** option in the publish settings
3. **Deploy** - Replit automatically creates `/tmp/replitdb` with production credentials
4. **Your app automatically connects** to the production database (no code changes needed!)

### Adding Database Models

Database models should be defined in `models.py`. Example using SQLAlchemy:

```python
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from database import get_database_url
from datetime import datetime

Base = declarative_base()

class YourModel(Base):
    __tablename__ = 'your_table'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
engine = create_engine(get_database_url())
Base.metadata.create_all(engine)

# Use in your app
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### Database Files
- `database.py` - Connection helper with automatic dev/prod switching
- `models.py` - Database models template (add your models here)
- `test_db_connection.py` - Test script to verify connection