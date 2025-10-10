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
- **AI Matching**: Integrates comprehensive AI matching rules for deliverables, components, and subtasks with priority scoring and configurable weights. Features a weighted scoring API and an interactive AI suggestions panel.
- **Parallel Processing**: Implemented parallel processing of PDF images with OpenAI Vision API for faster analysis and real-time progress tracking. Includes job tracking, retry logic, and robust error handling.
- **Smart Image Analysis**: Two-tier image processing system that dramatically reduces processing time and cost for PDFs with many decorative images:
  - **Pre-filtering**: Hash-based deduplication and size filtering (<100px) to eliminate logos, icons, and repeated images
  - **Quick Relevance Scan**: Fast 10-token GPT-5 check to identify images containing charts, diagrams, wireframes, or project requirements
  - **Deep Analysis**: Full 500-token analysis only for relevant images, reducing 72-image PDFs to ~8-10 relevant images
  - **User Control**: Optional toggle in UI to disable image analysis entirely for text-only processing
  - **Two-Phase Progress**: Real-time UI updates showing quick scan progress and deep analysis phase separately
- **Database Compatibility**: Supports v3 database structure with graceful handling of missing sheets and fallback values.
- **CORS**: Configured to allow cross-origin requests.

### Frontend Architecture
- **Technology**: Vanilla JavaScript, HTML, and CSS (framework-agnostic).
- **UI Pattern**: Single-page application with a step-based workflow, simplified to focus on a single scenario (Scenario A).
- **Styling**: Uses CSS custom properties for theming, including a dark mode.
- **State Management**: Centralized `selectionStore` as single source of truth with Proxy-backed compatibility layer for legacy code paths.
- **UI Improvements**: Features a 3-column layout (Deliverables | Components | Summary), search functionality, and enhanced summary panel with hierarchical display and individual remove buttons.
- **AI Integration**: Displays GPT-5 suggestions with reasoning, and action buttons for applying or replacing suggestions.
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