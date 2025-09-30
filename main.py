import os, re, io, math, json, datetime, urllib.parse, tempfile
from typing import List, Optional, Dict, Any, Tuple, Set, Union
from zoneinfo import ZoneInfo  # Python 3.9+
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
import numpy as np

try:
    from docx import Document  # pip install python-docx
except Exception:
    Document = None

try:
    from pypdf import PdfReader  # pip install pypdf
except Exception:
    PdfReader = None

# ---------- App & CORS ----------
app = FastAPI(title="Agency Project Builder", version="1.0")

# Global to track last uploaded filename for export defaults
LAST_UPLOAD_FILENAME: str | None = None

# Configure file upload limits - allow up to 20MB files
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

class FileSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 20 * 1024 * 1024):  # 20MB
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_size:
                return JSONResponse(
                    {"error": f"File too large. Maximum size is {self.max_size // (1024*1024)}MB."},
                    status_code=413
                )
        return await call_next(request)

app.add_middleware(FileSizeMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
    expose_headers=["Content-Disposition"],  # Allow browser to read server-suggested filename
)

# Serve static frontend
if not os.path.exists("static"):
    os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ===== Workfront column order (now includes Service_Department) =====
WF_COLUMNS = [
    "Project_Name", "WBS_ID", "Parent_WBS_ID",
    "Task_Name", "Deliverable", "Component", "Task",
    "Service Department",            # <-- exact header, its own column
    "Role", "Seniority",
    "Planned_Hours", "Start_Offset_Days", "Duration_Days",
    "Dependencies", "Assignee_External_ID", "Notes",
    "Rate_USD", "Price_USD"
]

# Helper to find v3 database by environment or common paths
def _find_v3_path() -> str | None:
    for p in [
        os.getenv("APB_V3_DB"),                                      # prefer Replit Secret
        "Replit_App_DB_READABLE_FullRows_v3.xlsx",                   # project root
        "data/Replit_App_DB_READABLE_FullRows_v3.xlsx",              # ./data
        "static/data/Replit_App_DB_READABLE_FullRows_v3.xlsx",       # ./static/data
    ]:
        if p and os.path.exists(p):
            return p
    return None

# ---------- OpenAI Integration (Stage 2) ----------
from openai import OpenAI

# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
# Initialize OpenAI client - will be set after models are defined

# ---------- Helper: DB Loader ----------
class AgencyDB:
    def __init__(self):
        self.loaded = False
        self.src = None
        # DataFrames
        self.all_rows = None                # All_Task_Rows
        self.deliverables = None            # Deliverable_Index
        self.b_rules = None                 # Bundle_Rules_Table
        self.b_defaults = None              # Bundle_Scenario_Defaults
        self.b_by_deliv = None              # Bundles_By_Deliverable
        self.b_hours_by_role = None         # Bundles_Hours_By_Role
        self.role_rate_card = None          # Role_Rate_Card
        self.rate_matrix = None             # Role_Rate_Matrix
        self.rate_bands = None              # Rate_Bands
        self.timeline_params = None         # Timeline_Params
        self.timeline_scaling = None        # Timeline_Scaling
        self.timeline_weighting = None      # Timeline_Weighting
        self.slack_settings = None          # Slack_Settings
        self.pricing_settings = None        # Pricing_Settings
        self.scenario_templates = None      # Scenario_Templates
        self.drivers_v3 = None              # v3 Drivers sheet
        self.ui_options = None              # UI_Options
        self.rfp_rules = None               # RFP_Matching_Rules
        self.v3_all_rows = None             # All_Task_Rows from v3 (source of Service Department)

    def _scenario_col(self, complexity: str, tier: str) -> str:
        return f"{complexity}__{tier}_Hours"

    def load(self):
        # Try Excel v4b first, then v4, else CSV bundle, else create mock data
        xlsx_candidates = ["Replit_App_DB_READABLE_FullRows_v4b.xlsx",
                          "Replit_App_DB_READABLE_FullRows_v4.xlsx"]
        xlsx_name = None
        for name in xlsx_candidates:
            if os.path.exists(name):
                xlsx_name = name
                break
        
        csv_dir  = "Replit_App_DB_READABLE_FullRows_v4_csvs"
        if xlsx_name:
            xls = pd.ExcelFile(xlsx_name)
            read = lambda sh: pd.read_excel(xlsx_name, sheet_name=sh)
            self.src = xlsx_name
        elif os.path.exists(csv_dir):
            def read_csv(sh):
                path = os.path.join(csv_dir, f"{sh}.csv")
                if not os.path.exists(path):
                    raise FileNotFoundError(path)
                return pd.read_csv(path)
            read = read_csv
            self.src = csv_dir
        else:
            # Create minimal mock data for demo purposes
            self._create_mock_data()
            self.loaded = True
            return True

        # Load sheets
        self.all_rows          = read("All_Task_Rows")
        self.deliverables      = read("Deliverable_Index")
        self.b_rules           = read("Bundle_Rules_Table")
        self.b_defaults        = read("Bundle_Scenario_Defaults")
        self.b_by_deliv        = read("Bundles_By_Deliverable")
        self.b_hours_by_role   = read("Bundles_Hours_By_Role")
        self.role_rate_card    = read("Role_Rate_Card")
        self.rate_matrix       = read("Role_Rate_Matrix")
        self.rate_bands        = read("Rate_Bands")
        self.timeline_params   = read("Timeline_Params")
        self.timeline_scaling  = read("Timeline_Scaling")
        self.timeline_weighting= read("Timeline_Weighting")
        self.slack_settings    = read("Slack_Settings")
        self.pricing_settings  = read("Pricing_Settings")
        self.scenario_templates= read("Scenario_Templates")
        self.ui_options        = read("UI_Options")
        self.rfp_rules         = read("RFP_Matching_Rules")

        # Normalize
        for c in ["Deliverable_Code","Deliverable","Category"]:
            if c in self.deliverables.columns:
                self.deliverables[c] = self.deliverables[c].astype(str)

        # Normalize component column from v4 spreadsheet
        self._normalize_component_column()
        # Normalize task label column from v4b spreadsheet
        self._normalize_task_label_column()
        # Normalize role and seniority columns 
        self._normalize_role_and_seniority_columns()
        self._normalize_rate_card_seniority()
        
        # Try to read v3 data using path-aware helper
        v3_path = _find_v3_path()
        if v3_path:
            try:
                self.drivers_v3 = pd.read_excel(v3_path, sheet_name="Drivers")
            except Exception:
                self.drivers_v3 = None
            try:
                self.v3_all_rows = pd.read_excel(v3_path, sheet_name="All_Task_Rows")
            except Exception:
                self.v3_all_rows = None
            print(f"[DB] v3 loaded from: {v3_path}")
        else:
            self.drivers_v3 = None
            self.v3_all_rows = None
            print("[DB] v3 not found")

        # normalize v3 columns for lookups
        self._normalize_v3_service_department()
        # normalize code columns from v4/v4b for canonical naming
        self._normalize_code_columns()
        
        self.loaded = True
        return True

    def _normalize_component_column(self):
        """
        Ensure self.all_rows has a 'Component' column populated from v4's Component_Task_L1 (Column F).
        If other synonyms exist, prefer them in this order.
        """
        if self.all_rows is None or self.all_rows.empty:
            return
        # Known header names (case-insensitive)
        candidates = ["Component_Task_L1", "Component L1", "Component_L1", "Component"]
        cols_lc = {c.lower(): c for c in self.all_rows.columns}
        found = None
        for cand in candidates:
            if cand.lower() in cols_lc:
                found = cols_lc[cand.lower()]
                break

        if found:
            # Standardize to 'Component' - fix order to handle NaN properly
            self.all_rows["Component"] = (
                self.all_rows[found]
                .fillna("")
                .astype(str)
                .str.strip()
                .replace({"nan": ""})  # Handle any literal "nan" strings
            )
        else:
            # Create empty for downstream logic; we'll only use 'General' per missing row, not globally
            self.all_rows["Component"] = ""

    def _normalize_task_label_column(self):
        """
        Ensure self.all_rows has a 'Task_Label' column populated from v4b's Column G.
        Map v4b column G → 'Task_Label' (UI-display name for tasks)
        """
        if self.all_rows is None or self.all_rows.empty:
            return

        # optional UI override from UI_Options.Key == 'Task_Label_Column_Name'
        preferred = None
        try:
            row = self.ui_options[self.ui_options["Key"] == "Task_Label_Column_Name"]
            if not row.empty:
                preferred = str(row["Value"].iloc[0]).strip()
        except Exception:
            pass

        candidates = [preferred] if preferred else []
        # common headers we've seen for column G in v4b
        candidates += ["Task_Label", "Task_Name", "Task_L1", "Component_Task_L2", "Task"]

        cols_lc = {c.lower(): c for c in self.all_rows.columns}
        found = None
        for cand in candidates:
            if cand and cand.lower() in cols_lc:
                found = cols_lc[cand.lower()]
                break
        if not found:
            # last‑ditch: pick column index G (0‑based 6) if it exists
            try:
                found = self.all_rows.columns[6]
            except Exception:
                found = None

        if found:
            self.all_rows["Task_Label"] = (
                self.all_rows[found].astype(str).fillna("").str.strip()
            )
        else:
            # fallback; we'll still display task_group if label missing
            self.all_rows["Task_Label"] = ""

    def _normalize_v3_service_department(self):
        """Ensure v3 has standard columns for lookups:
           Deliverable_Code, task_group, Component (from Component_Task_L1), Service_Department (from column D)."""
        if self.v3_all_rows is None or self.v3_all_rows.empty:
            return
        df = self.v3_all_rows

        # align column names case-insensitively
        cols = {c.lower(): c for c in df.columns}
        # required keys
        dcode_col = cols.get("deliverable_code", None)
        tg_col    = cols.get("task_group", None)
        comp_col  = cols.get("component_task_l1", cols.get("component", None))
        svc_col   = cols.get("service department", cols.get("service_department", None))

        # create standardized columns
        if dcode_col: df["Deliverable_Code"] = df[dcode_col].astype(str)
        else: df["Deliverable_Code"] = ""

        if tg_col: df["task_group"] = df[tg_col].astype(str)
        else: df["task_group"] = ""

        if comp_col: df["Component"] = df[comp_col].astype(str).fillna("").str.strip()
        else: df["Component"] = ""

        if svc_col: df["Service Department"] = df[svc_col].astype(str).fillna("").str.strip()
        else: df["Service Department"] = ""

    def _normalize_code_columns(self):
        """Map v4/v4b All_Task_Rows code columns to canonical names we use downstream."""
        if self.all_rows is None or self.all_rows.empty:
            return
        cols = {c.lower(): c for c in self.all_rows.columns}

        def pick(*names):
            for n in names:
                if n and n.lower() in cols:
                    return cols[n.lower()]
            return None

        # canonical: Deliverable_Code already exists in v4/v4b; keep synonyms just in case
        if "Deliverable_Code" not in self.all_rows.columns:
            alt = pick("Deliverable Code", "Deliv_Code", "DeliverableID")
            if alt: self.all_rows["Deliverable_Code"] = self.all_rows[alt].astype(str)

        # Row_ID (v3 style)
        self._col_row_id        = pick("Row_ID", "RowID", "Row Id", "ID")

        # Task_Code (v3 style)
        self._col_task_code     = pick("Task_Code", "Task Code", "TaskCode", "Task_Code_L1", "Task_Group_Code")

        # Service_Department (v3 style)
        self._col_service_dept  = pick("Service_Department", "Service Department", "Service_Dept", "Department", "Dept")

        # Make sure we have Component + Task_Label from prior patches
        if "Component" not in self.all_rows.columns:
            self.all_rows["Component"] = ""
        if "Task_Label" not in self.all_rows.columns:
            self.all_rows["Task_Label"] = ""

    def _canonical_seniority(self, v: str) -> str:
        """Standardize seniority levels to canonical values: Junior, Mid, Senior, Director"""
        x = (str(v) or "").strip().lower()
        x = x.replace(".", "")
        if x in {"jr", "junior", "jr-level", "associate", "coordinator", "assistant", "l1", "level 1"}:
            return "Junior"
        if x in {"mid", "midlevel", "intermediate", "standard", "staff", "specialist", "producer", "manager", "l2", "level 2"}:
            return "Mid"
        if x in {"sr", "senior", "lead", "principal", "l3", "level 3"}:
            return "Senior"
        if x in {"director", "group director", "head", "executive director"}:
            return "Director"
        return (str(v) or "").strip()

    def _canonical_deliverable_code(self, v: str) -> str:
        """Map a free-text label to a DB deliverable code"""
        if not v or self.deliverables is None:
            return ""
        
        v_norm = (str(v) or "").strip().lower()
        if not v_norm:
            return ""
        
        # Try exact match on deliverable code first
        exact_code_match = self.deliverables[
            self.deliverables["Deliverable_Code"].astype(str).str.lower() == v_norm
        ]
        if not exact_code_match.empty:
            return str(exact_code_match["Deliverable_Code"].iloc[0])
        
        # Try exact match on deliverable name
        exact_name_match = self.deliverables[
            self.deliverables["Deliverable"].astype(str).str.lower() == v_norm
        ]
        if not exact_name_match.empty:
            return str(exact_name_match["Deliverable_Code"].iloc[0])
        
        # Try substring match on deliverable name
        substring_match = self.deliverables[
            self.deliverables["Deliverable"].astype(str).str.lower().str.contains(v_norm, na=False)
        ]
        if not substring_match.empty:
            return str(substring_match["Deliverable_Code"].iloc[0])
        
        # Try substring match on category
        category_match = self.deliverables[
            self.deliverables["Category"].astype(str).str.lower().str.contains(v_norm, na=False)
        ]
        if not category_match.empty:
            return str(category_match["Deliverable_Code"].iloc[0])
        
        # No match found
        return ""

    def _normalize_role_and_seniority_columns(self):
        """Normalize Role and Seniority columns to ensure consistent data format"""
        if self.all_rows is None or self.all_rows.empty:
            return
        cols = {c.lower(): c for c in self.all_rows.columns}

        # Role column ➜ Resource_Title
        for cand in ["Resource_Title", "Role_Title", "Role", "Resource"]:
            if cand.lower() in cols:
                self.all_rows["Resource_Title"] = (
                    self.all_rows[cols[cand.lower()]]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .replace({"nan": ""})  # Handle literal "nan" strings
                )
                break
        if "Resource_Title" not in self.all_rows.columns:
            self.all_rows["Resource_Title"] = ""
        
        # Ensure no blank roles - use placeholder for empty values
        self.all_rows["Resource_Title"] = self.all_rows["Resource_Title"].where(
            self.all_rows["Resource_Title"].str.len() > 0, "General Role"
        )

        # Seniority column ➜ Seniority (canonical labels)
        sen_src = None
        for cand in ["Seniority", "Seniority_Level", "Seniority L1", "Seniority_Title", "Level"]:
            if cand.lower() in cols:
                sen_src = cols[cand.lower()]
                break
        if sen_src:
            ser = (self.all_rows[sen_src]
                   .fillna("")
                   .astype(str)
                   .str.strip()
                   .replace({"nan": ""}))
        else:
            ser = pd.Series([""]*len(self.all_rows))
        self.all_rows["Seniority"] = ser.apply(self._canonical_seniority)
        
        # Ensure no blank seniority values - default to "Mid"
        self.all_rows["Seniority"] = self.all_rows["Seniority"].where(
            self.all_rows["Seniority"].str.len() > 0, "Mid"
        )

    def _normalize_rate_card_seniority(self):
        """Normalize role and seniority values in the role rate card to ensure pricing joins work properly"""
        if self.role_rate_card is None or self.role_rate_card.empty:
            return
        rc = self.role_rate_card.copy()
        
        # Normalize Resource_Title in rate card
        if "Resource_Title" in rc.columns:
            rc["Resource_Title"] = (rc["Resource_Title"]
                                   .fillna("")
                                   .astype(str)
                                   .str.strip()
                                   .replace({"nan": ""}))
            # Ensure no blank roles in rate card - use placeholder
            rc["Resource_Title"] = rc["Resource_Title"].where(
                rc["Resource_Title"].str.len() > 0, "General Role"
            )
        
        # Normalize Seniority in rate card
        if "Seniority" in rc.columns:
            rc["Seniority"] = (rc["Seniority"]
                              .fillna("")
                              .astype(str)
                              .str.strip()
                              .replace({"nan": ""})
                              .apply(self._canonical_seniority))
            # Ensure no blank seniority in rate card - default to "Mid"
            rc["Seniority"] = rc["Seniority"].where(rc["Seniority"].str.len() > 0, "Mid")
        
        self.role_rate_card = rc

    # ---------- v3 Drivers helper methods ----------
    def _norm_token(self, s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())

    def _v4_complexity_tokens(self) -> list[str]:
        toks = set()
        for c in self.all_rows.columns:
            if c.endswith("_Hours") and "__" in c:
                toks.add(c.split("__", 1)[0])
        return sorted(toks)

    def _v4_tier_tokens(self) -> list[str]:
        toks = set()
        for c in self.all_rows.columns:
            if c.endswith("_Hours") and "__" in c:
                # Safety check: ensure column has expected format before splitting
                parts = c.rsplit("__", 1)[0].split("__", 1)
                if len(parts) > 1:
                    toks.add(parts[1].replace("_Hours", ""))
        return sorted(toks)

    def _map_to_v4_token(self, label: str, candidates: list[str]) -> str:
        if not label: return ""
        z = self._norm_token(label)
        # exact normalized match first
        for c in candidates:
            if self._norm_token(c) == z:
                return c
        # relaxed: startswith / contains
        for c in candidates:
            if z and (self._norm_token(c).startswith(z) or z.startswith(self._norm_token(c))):
                return c
        # fallback to first
        return candidates[0] if candidates else ""

    def drivers_complexities_tiers_v3(self) -> tuple[list[str], list[str]]:
        """Return display labels from v3 Drivers (max 3 each)."""
        if self.drivers_v3 is None or self.drivers_v3.empty:
            return ([], [])
        df = self.drivers_v3.copy()
        cols = {c.lower(): c for c in df.columns}
        # Try to find the columns
        type_col = next((cols.get(x) for x in ["type","driver","driver_type","category"]), None)
        key_col  = next((cols.get(x) for x in ["key","value","name","label","option"]), None)
        order_col= next((cols.get(x) for x in ["sort","order","seq","priority"]), None)
        if not type_col or not key_col:
            return ([], [])
        if order_col:
            df = df.sort_values(order_col, kind="stable")
        df[key_col] = df[key_col].astype(str).str.strip()
        comp = df[df[type_col].str.contains("complex", case=False, na=False)][key_col].dropna().unique().tolist()
        tier = df[df[type_col].str.contains("tier", case=False, na=False)][key_col].dropna().unique().tolist()
        return (comp[:3], tier[:3])

    def _create_mock_data(self):
        """Create minimal mock data for demo purposes when database files are not available"""
        # Basic deliverables
        self.deliverables = pd.DataFrame([
            {"Deliverable_Code": "WEB_DEV", "Deliverable": "Website Development", "Category": "Digital"},
            {"Deliverable_Code": "BRAND_STR", "Deliverable": "Brand Strategy", "Category": "Branding"},
            {"Deliverable_Code": "CONTENT", "Deliverable": "Content Creation", "Category": "Content"}
        ])
        
        # Mock scenario data
        self.all_rows = pd.DataFrame([
            {"Deliverable_Code": "WEB_DEV", "task_group": "discovery", "Resource_Title": "Developer", "Seniority": "Senior", "Advanced__T2_MediumVolume_Hours": 40},
            {"Deliverable_Code": "WEB_DEV", "task_group": "development", "Resource_Title": "Developer", "Seniority": "Senior", "Advanced__T2_MediumVolume_Hours": 80},
            {"Deliverable_Code": "BRAND_STR", "task_group": "strategy", "Resource_Title": "Strategist", "Seniority": "Mid", "Advanced__T2_MediumVolume_Hours": 30}
        ])
        
        # Timeline and pricing settings
        self.timeline_params = pd.DataFrame([
            {"Task_Group": "discovery", "Nominal_Duration_Days": 5},
            {"Task_Group": "development", "Nominal_Duration_Days": 15},
            {"Task_Group": "strategy", "Nominal_Duration_Days": 10}
        ])
        
        self.timeline_scaling = pd.DataFrame([
            {"Scale_Type": "Complexity", "Key": "Advanced", "Multiplier": 1.2},
            {"Scale_Type": "Tier", "Key": "T2_MediumVolume", "Multiplier": 1.0}
        ])
        
        self.timeline_weighting = pd.DataFrame([
            {"Task_Group": "discovery", "Weight_Complexity": 0.6, "Weight_Tier": 0.4},
            {"Task_Group": "development", "Weight_Complexity": 0.6, "Weight_Tier": 0.4},
            {"Task_Group": "strategy", "Weight_Complexity": 0.6, "Weight_Tier": 0.4}
        ])
        
        # Basic settings
        self.pricing_settings = pd.DataFrame([
            {"Key": "Default_Blended_Rate", "Default": 185}
        ])
        
        self.slack_settings = pd.DataFrame([
            {"Key": "Use_Slack", "Default": True},
            {"Key": "Slack_After_Internal_Review_Days", "Default": 1},
            {"Key": "Slack_After_Client_Review_Days", "Default": 2},
            {"Key": "Slack_Global_Percent", "Default": 0.05}
        ])
        
        self.scenario_templates = pd.DataFrame([
            {"Scenario_Key": "MED_LOW", "Complexity": "Advanced", "Tier": "T2_MediumVolume"},
            {"Scenario_Key": "MED_HIGH", "Complexity": "Advanced", "Tier": "T2_MediumVolume"}
        ])
        
        self.rate_bands = pd.DataFrame([
            {"Band_Name": "Standard_US", "Rate_Multiplier": 1.0}
        ])
        
        self.role_rate_card = pd.DataFrame([
            {"Resource_Title": "Developer", "Seniority": "Senior", "Rate_USD": 150},
            {"Resource_Title": "Strategist", "Seniority": "Mid", "Rate_USD": 120}
        ])
        
        # Initialize empty tables for bundle functionality
        self.b_rules = pd.DataFrame(columns=["Category", "Bundle", "Task_Group", "Sort_Order"])
        self.b_defaults = pd.DataFrame(columns=["Bundle", "Default_Complexity", "Default_Tier"])
        self.b_by_deliv = pd.DataFrame()
        self.b_hours_by_role = pd.DataFrame()
        self.rate_matrix = pd.DataFrame()
        self.ui_options = pd.DataFrame()
        self.rfp_rules = pd.DataFrame(columns=["Regex_Keywords", "Map_To_Deliverable"])
        
        self.src = "mock_data"

    # ---------- RFP parsing via rules ----------
    def _ui_blocked_categories(self) -> set:
        try:
            if self.ui_options is not None and "Key" in self.ui_options.columns:
                row = self.ui_options[self.ui_options["Key"]=="Suggest_Block_Categories"]
                if not row.empty:
                    raw = str(row["Value"].iloc[0])
                    return {x.strip() for x in raw.split(";") if x.strip()}
        except Exception:
            pass
        # Default: block analytics unless explicitly asked for
        return {"Analytics"}

    def _ui_strict_mode(self) -> bool:
        try:
            if self.ui_options is not None and "Key" in self.ui_options.columns:
                row = self.ui_options[self.ui_options["Key"]=="RFP_Suggest_Strict"]
                if not row.empty:
                    v = str(row["Value"].iloc[0]).strip().lower()
                    return v in ("1","true","yes","y")
        except Exception:
            pass
        return True  # strict by default

    def suggest_deliverables_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Strict rules-first RFP matching. Returns [{
          deliverable_code, deliverable, category, confidence, matches: [...]
        }]
        - Uses RFP_Matching_Rules.Regex_Keywords -> Map_To_Deliverable
        - Applies optional UI_Options.Suggest_Block_Categories
        - NO fuzzy fallback in strict mode (prevents false positives)
        """
        if not text:
            return []
        strict = self._ui_strict_mode()
        blocked = self._ui_blocked_categories()

        text = str(text)
        found: Dict[str, Dict[str, Any]] = {}

        # 1) Rule-based suggestions
        for _, row in self.rfp_rules.iterrows():
            patt = str(row.get("Regex_Keywords", "") or "")
            target = str(row.get("Map_To_Deliverable", "") or "")
            if not patt or not target:
                continue
            try:
                hits = re.findall(patt, text, flags=re.IGNORECASE)
            except re.error:
                continue
            if not hits:
                continue

            # Find deliverable row(s)
            match_df = self.deliverables[self.deliverables["Deliverable"] == target]
            if match_df.empty:
                continue

            for __, r in match_df.iterrows():
                code = str(r["Deliverable_Code"]); cat = str(r.get("Category",""))
                if cat in blocked:
                    # allow through only if there are at least 2 strong hits
                    if len(hits) < 2:
                        continue

                entry = found.setdefault(code, {
                    "deliverable_code": code,
                    "deliverable": str(r["Deliverable"]),
                    "category": cat,
                    "confidence": 0,
                    "matches": []
                })
                entry["confidence"] += len(hits)
                uniq = list({str(h).lower() for h in hits if str(h).strip()})
                for m in uniq:
                    if m not in entry["matches"]:
                        entry["matches"].append(m)

        # 2) NO fuzzy fallback when strict (prevents "not in RFP" picks)
        if strict:
            out = list(found.values())
            out.sort(key=lambda x: (-x["confidence"], x["deliverable"]))
            return out

        # Optional: gentle fallback if strict is off (rare)
        for _, r in self.deliverables.iterrows():
            name = str(r["Deliverable"])
            code = str(r["Deliverable_Code"])
            if re.search(r"\b" + re.escape(name) + r"\b", text, flags=re.IGNORECASE):
                if code not in found:
                    found[code] = {
                        "deliverable_code": code,
                        "deliverable": name,
                        "category": str(r.get("Category","")),
                        "confidence": 1,
                        "matches": [name]
                    }

        out = list(found.values())
        out.sort(key=lambda x: (-x["confidence"], x["deliverable"]))
        return out

    def retainer_recommendation(self, text: str, deliverable_name: str) -> tuple[bool, int]:
        """
        Very simple rule-of-thumb to suggest retainer and months.
        Returns (is_retainer, months) where months in [1..12].
        """
        t = (text or "").lower()

        # If RFP states an explicit month count, respect that (clamped to 1..12)
        import re
        m = re.search(r'\b(\d{1,2})\s*(?:months|mos|mo)\b', t)
        months = 0
        if m:
            try:
                months = max(1, min(12, int(m.group(1))))
            except Exception:
                months = 0

        # Soft indicators that the work is monthly/ongoing
        signals = [
            "retainer", "monthly", "per month", "each month", "every month",
            "always-on", "always on", "ongoing", "maintenance", "management",
            "reporting cadence", "monthly report", "social calendar", "community"
        ]

        is_signal = any(s in t for s in signals)

        # Some deliverables are very often retainers
        likely_retainer_keywords = [
            "social", "community", "media", "measurement", "reporting",
            "seo", "maintenance", "support", "content", "blog"
        ]
        is_likely_by_name = any(k in (deliverable_name or "").lower() for k in likely_retainer_keywords)

        is_ret = bool(is_signal or is_likely_by_name)
        if is_ret and months == 0:
            # Default sensible guess
            months = 12 if "year" in t or "annual" in t else 6

        return (is_ret, max(1, min(12, months)) if months else (12 if is_ret else 0))

    # ---------- Bundle helpers ----------
    def included_task_groups(self, category: str, bundle: str) -> List[str]:
        sub = self.b_rules[(self.b_rules["Category"]==category) & (self.b_rules["Bundle"]==bundle)]
        if sub.empty:
            return []
        sub = sub.sort_values("Sort_Order")
        return [str(x) for x in sub["Task_Group"].tolist()]

    def default_complexity_tier_for_bundle(self, bundle: str) -> tuple[str, str]:
        row = self.b_defaults[self.b_defaults["Bundle"]==bundle]
        if row.empty:
            return ("Advanced","T2_MediumVolume")
        r = row.iloc[0]
        return str(r["Default_Complexity"]), str(r["Default_Tier"])

    # ---------- Pricing ----------
    def blended_price(self, total_hours: float, blended_rate: float) -> float:
        return float(total_hours) * float(blended_rate)

    def per_resource_price(self, hrs_by_role: pd.DataFrame, rate_band: str="Standard_US") -> float:
        # hrs_by_role columns: Resource_Title, Seniority, Hours
        band = self.rate_bands[self.rate_bands["Band_Name"]==rate_band]
        mult = float(band["Rate_Multiplier"].iloc[0]) if not band.empty else 1.0
        # join to rate card
        rc = self.role_rate_card[["Resource_Title","Seniority","Rate_USD"]].copy()
        merged = hrs_by_role.merge(rc, on=["Resource_Title","Seniority"], how="left")
        merged["Rate_USD"] = merged["Rate_USD"].fillna(0)
        merged["Price"] = merged["Hours"] * merged["Rate_USD"] * mult
        return float(merged["Price"].sum())

    # ---------- Hours aggregation ----------
    def scenario_hours_col(self, complexity: str, tier: str) -> str:
        # exact
        col = f"{complexity}__{tier}_Hours"
        if col in self.all_rows.columns:
            return col
        # try mapping display labels -> v4 tokens
        c_tok = self._map_to_v4_token(complexity, self._v4_complexity_tokens())
        t_tok = self._map_to_v4_token(tier,        self._v4_tier_tokens())
        col2 = f"{c_tok}__{t_tok}_Hours"
        if col2 not in self.all_rows.columns:
            raise HTTPException(400, f"Scenario column not found for ({complexity}, {tier}).")
        return col2

    def hours_by_role_for_deliverable(
        self, deliverable_code: str, included_task_groups: List[str], scenario_col: str
    ) -> pd.DataFrame:
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str)==str(deliverable_code)) &
            (self.all_rows["task_group"].isin(included_task_groups))
        ]
        if sub.empty or scenario_col not in sub.columns:
            return pd.DataFrame(columns=["Resource_Title","Seniority","Hours"])
        g = sub.groupby(["Resource_Title","Seniority"], as_index=False)[scenario_col].sum()
        g = g.rename(columns={scenario_col:"Hours"})
        return g

    # ---------- Timeline ----------
    def task_group_duration_days(self, task_group: str, complexity: str, tier: str, use_slack: bool,
                                 slack_after_internal: int, slack_after_client: int, slack_global_pct: float) -> float:
        # Base nominal
        tp = self.timeline_params[self.timeline_params["Task_Group"]==task_group]
        if tp.empty:
            return 0.0
        base = float(tp["Nominal_Duration_Days"].iloc[0])

        # Scaling
        cw = self.timeline_weighting[self.timeline_weighting["Task_Group"]==task_group]
        wc = float(cw["Weight_Complexity"].iloc[0]) if not cw.empty else 0.6
        wt = float(cw["Weight_Tier"].iloc[0])        if not cw.empty else 0.4

        cm = self.timeline_scaling[(self.timeline_scaling["Scale_Type"]=="Complexity") &
                                   (self.timeline_scaling["Key"]==complexity)]
        tm = self.timeline_scaling[(self.timeline_scaling["Scale_Type"]=="Tier") &
                                   (self.timeline_scaling["Key"]==tier)]
        cmult = float(cm["Multiplier"].iloc[0]) if not cm.empty else 1.0
        tmult = float(tm["Multiplier"].iloc[0]) if not tm.empty else 1.0

        dur = base * (1 + (cmult - 1)*wc) * (1 + (tmult - 1)*wt)
        if use_slack and slack_global_pct > 0:
            dur *= (1.0 + float(slack_global_pct))
        return max(1.0, round(dur, 2))

    def build_schedule(self, deliverable_code: str, included_task_groups: List[str],
                       complexity: str, tier: str,
                       use_slack: bool, slack_after_internal: int, slack_after_client: int, slack_global_pct: float,
                       project_start: Optional[str]=None, scenario_letter: str="A") -> List[Dict[str, Any]]:
        order_map = {tg:i for i, tg in enumerate(self.timeline_params["Task_Group"].astype(str).tolist())}
        tgs = self.sort_task_groups(included_task_groups, scenario_letter)

        # Start date
        if project_start:
            start_date = datetime.datetime.strptime(project_start, "%Y-%m-%d").date()
        else:
            start_date = datetime.date.today()

        cursor_day = 0
        rows = []
        for tg in tgs:
            dur = self.task_group_duration_days(tg, complexity, tier, use_slack,
                                                slack_after_internal, slack_after_client, slack_global_pct)
            start = start_date + datetime.timedelta(days=cursor_day)
            end   = start + datetime.timedelta(days=math.ceil(dur))
            rows.append({
                "task_group": tg,
                "start_date": str(start),
                "end_date": str(end),
                "duration_days": math.ceil(dur)
            })
            cursor_day += math.ceil(dur)

            # Slack after reviews
            if use_slack and tg == "internal_review":
                cursor_day += int(slack_after_internal)
            if use_slack and tg == "client_review":
                cursor_day += int(slack_after_client)

        return rows

    def _order_overrides(self, letter: str) -> list[tuple[str,str]]:
        """
        Optional UI_Options row(s):
          - Key: Task_Order_Overrides_A  Value: post_production<development; qa<launch
          - Key: Task_Order_Overrides_B  Value: ...
        Fallback: ensure post_production < development for Scenario A.
        """
        try:
            key = f"Task_Order_Overrides_{letter.upper()}"
            row = self.ui_options[self.ui_options["Key"] == key]
            if not row.empty:
                parts = str(row["Value"].iloc[0]).split(";")
                pairs = []
                for p in parts:
                    if "<" in p:
                        a, b = [x.strip() for x in p.split("<", 1)]
                        if a and b: pairs.append((a, b))
                if pairs:
                    return pairs
        except Exception:
            pass
        if letter.upper() == "A":
            return [("post_production", "development")]
        return []

    def sort_task_groups(self, tgs: list[str], letter: str) -> list[str]:
        """Topological sort using Timeline_Params order as baseline + overrides."""
        base = {str(tg): i for i, tg in enumerate(self.timeline_params["Task_Group"].astype(str).tolist())}
        nodes = [str(x) for x in tgs]
        edges = [(a, b) for (a, b) in self._order_overrides(letter) if a in nodes and b in nodes]
        # Kahn's algorithm with baseline tie-break
        preds = {n: set() for n in nodes}
        succs = {n: set() for n in nodes}
        for a, b in edges:
            succs[a].add(b); preds[b].add(a)
        ready = [n for n in nodes if not preds[n]]
        ready.sort(key=lambda n: base.get(n, 999))
        out = []
        while ready:
            n = ready.pop(0)
            out.append(n)
            for m in sorted(list(succs[n]), key=lambda x: base.get(x, 999)):
                preds[m].discard(n)
                if not preds[m] and m not in out and m in nodes and m not in ready:
                    ready.append(m)
            ready.sort(key=lambda x: base.get(x, 999))
        # append any left (cycle or unrelated), preserving baseline
        tail = [n for n in nodes if n not in out]
        tail.sort(key=lambda n: base.get(n, 999))
        return out + tail

    # ---------- Helper methods for task ordering and role detection ----------
    def sorted_task_groups(self, included: List[str]) -> List[str]:
        order_map = {tg: i for i, tg in enumerate(self.timeline_params["Task_Group"].astype(str).tolist())}
        return sorted([str(x) for x in included], key=lambda tg: order_map.get(tg, 999))

    def task_hours_by_task_group(self, deliverable_code: str, included: List[str], scenario_col: str) -> Dict[str, float]:
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].isin(included))
        ]
        if sub.empty or scenario_col not in sub.columns:
            return {}
        g = sub.groupby(["task_group"], as_index=False)[scenario_col].sum()
        return {str(r["task_group"]): float(r[scenario_col]) for _, r in g.iterrows()}

    def dominant_role_for_task_group(self, deliverable_code: str, task_group: str, scenario_col: str):
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str) == str(task_group))
        ]
        if sub.empty or scenario_col not in sub.columns:
            return ("","")
        g = sub.groupby(["Resource_Title","Seniority"], as_index=False)[scenario_col].sum()
        r = g.sort_values(scenario_col, ascending=False).iloc[0]
        return (str(r["Resource_Title"]), str(r["Seniority"]))

    # ---------- Component-level helper methods ----------
    def components_for_deliverable(self, deliverable_code: str, included_tgs: list[str]) -> list[str]:
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str).isin([str(x) for x in included_tgs]))
        ].copy()
        # Fill per-row only if blank
        sub["Component"] = sub["Component"].fillna("").astype(str).str.strip()
        comps = [c for c in sub["Component"].unique().tolist() if c]
        has_blanks = (sub["Component"] == "").any()

        if not comps and not has_blanks:
            # No component values at all for this deliverable → one placeholder bucket
            return ["General"]
        
        # Include "General" if there are any blank component rows (avoid duplicates)
        if has_blanks and "General" not in comps:
            comps.append("General")

        # Order components by earliest task_group position from Timeline_Params
        order_map = {str(tg): i for i, tg in enumerate(self.timeline_params["Task_Group"].astype(str).tolist())}
        comp_earliest = {}
        for comp in comps:
            if comp == "General":
                # For General, find earliest task_group among blank component rows
                blank_tgs = sub.loc[sub["Component"] == "", "task_group"].astype(str).unique().tolist()
                comp_earliest[comp] = min([order_map.get(tg, 999) for tg in blank_tgs]) if blank_tgs else 999
            else:
                tgs = sub.loc[sub["Component"] == comp, "task_group"].astype(str).unique().tolist()
                comp_earliest[comp] = min([order_map.get(tg, 999) for tg in tgs]) if tgs else 999
        return sorted(comps, key=lambda c: (comp_earliest.get(c, 999), c))

    def hours_by_component(self, deliverable_code: str, included_tgs: list[str], scenario_col: str) -> dict[str, float]:
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str).isin([str(x) for x in included_tgs]))
        ].copy()
        sub["Component"] = sub["Component"].fillna("").astype(str).str.strip()
        # Only attach 'General' to rows that are actually blank
        sub.loc[sub["Component"] == "", "Component"] = "General"
        if sub.empty or scenario_col not in sub.columns:
            return {}
        g = sub.groupby("Component", as_index=False)[scenario_col].sum()
        return {str(r["Component"]): float(r[scenario_col]) for _, r in g.iterrows()}

    def hours_by_taskgroup_for_component(self, deliverable_code: str, component: str,
                                         included_tgs: list[str], scenario_col: str) -> dict[str, float]:
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str).isin([str(x) for x in included_tgs]))
        ].copy()
        sub["Component"] = sub["Component"].fillna("").astype(str).str.strip()
        # Remap blanks to "General" before filtering (consistent with hours_by_component)
        sub.loc[sub["Component"] == "", "Component"] = "General"
        
        comp_key = (component or "").strip() or "General"
        sub = sub[sub["Component"] == comp_key]

        if sub.empty or scenario_col not in sub.columns:
            return {}
        g = sub.groupby("task_group", as_index=False)[scenario_col].sum()
        return {str(r["task_group"]): float(r[scenario_col]) for _, r in g.iterrows()}

    def dominant_role_for_component_task(self, deliverable_code: str, component: str,
                                         task_group: str, scenario_col: str) -> tuple[str, str]:
        """Enhanced role picker that prefers non-blank seniority with robust fallbacks"""
        # Narrow to this deliverable + task_group (+ component if present)
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str) == str(task_group))
        ].copy()

        if "Component" in sub.columns and (component or "").strip():
            sub["Component"] = sub["Component"].astype(str).fillna("").str.strip()
            sub = sub[sub["Component"] == str(component).strip()]

        if sub.empty:
            # Fallback: ignore component filter
            sub = self.all_rows[
                (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
                (self.all_rows["task_group"].astype(str) == str(task_group))
            ].copy()

        if sub.empty:
            # Second fallback: any rows for this deliverable
            sub = self.all_rows[self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)].copy()

        if sub.empty:
            return ("", "Mid")

        # Prefer rows with non-blank seniority
        sub["Resource_Title"] = sub["Resource_Title"].astype(str).fillna("").str.strip()
        sub["Seniority"] = sub["Seniority"].astype(str).fillna("").str.strip()

        pref = sub[sub["Seniority"] != ""]
        pick_from = pref if not pref.empty else sub

        g = pick_from.groupby(["Resource_Title", "Seniority"], as_index=False)[scenario_col].sum()
        r = g.sort_values(scenario_col, ascending=False).iloc[0]

        role = str(r["Resource_Title"]).strip()
        sen  = self._canonical_seniority(str(r["Seniority"]).strip())
        if sen == "":
            sen = "Mid"  # last-resort default

        return (role, sen)

    def task_label_for_component_tg(self, deliverable_code: str, component: str, task_group: str) -> str:
        """Get user-friendly task label from Task_Label column for UI display."""
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str) == str(task_group))
        ].copy()
        if "Component" in sub.columns:
            sub["Component"] = sub["Component"].fillna("").astype(str).str.strip()
            # Remap blanks to "General" before filtering (consistent with other helpers)
            sub.loc[sub["Component"] == "", "Component"] = "General"
            comp_key = (component or "").strip() or "General"
            sub = sub[sub["Component"] == comp_key]

        if "Task_Label" in sub.columns:
            lab = sub["Task_Label"].dropna().astype(str).str.strip()
            lab = lab[lab != ""]
            if not lab.empty:
                # most frequent non‑empty label for that component+task_group
                return lab.value_counts().idxmax()
        return str(task_group)

    # ---------- Pricing helper methods ----------
    def role_rates_table(self, rate_band: str = "Standard_US") -> pd.DataFrame:
        """Rate card with band multiplier applied + normalized Seniority."""
        band = self.rate_bands[self.rate_bands["Band_Name"] == rate_band]
        mult = float(band["Rate_Multiplier"].iloc[0]) if not band.empty else 1.0
        rc = self.role_rate_card[["Resource_Title", "Seniority", "Rate_USD"]].copy()
        # normalize seniority if you added _canonical_seniority() earlier
        if "Seniority" in rc.columns:
            try:
                rc["Seniority"] = rc["Seniority"].astype(str).fillna("").apply(self._canonical_seniority)
            except Exception:
                rc["Seniority"] = rc["Seniority"].astype(str).fillna("")
        rc["Rate_USD"] = rc["Rate_USD"].astype(float) * mult
        return rc

    def price_for_hours_by_role(self, hrs_by_role: pd.DataFrame, rate_band: str) -> tuple[float, pd.DataFrame]:
        """Return (price_total, merged_breakdown) for a df with columns: Resource_Title, Seniority, Hours.
        Enforces rate integrity - uses fallback rates with warnings if role/seniority combinations are missing."""
        if hrs_by_role is None or hrs_by_role.empty:
            return (0.0, pd.DataFrame(columns=["Resource_Title","Seniority","Hours","Rate_USD","Price"]))
        
        rc = self.role_rates_table(rate_band)
        merged = hrs_by_role.merge(rc, on=["Resource_Title","Seniority"], how="left")
        merged["Hours"] = merged["Hours"].fillna(0.0).astype(float)
        
        # Check for missing rates before proceeding
        missing_rates = merged[merged["Rate_USD"].isna()]
        if not missing_rates.empty:
            # Try fallback: role-only matching (ignore seniority)
            fallback_merged = merged.copy()
            for idx, row in missing_rates.iterrows():
                role_only_match = rc[rc["Resource_Title"] == row["Resource_Title"]]
                if not role_only_match.empty:
                    # Use first available rate for this role (with any seniority)
                    fallback_rate = role_only_match["Rate_USD"].iloc[0]
                    fallback_merged.loc[idx, "Rate_USD"] = fallback_rate
                    print(f"Warning: Used fallback rate for {row['Resource_Title']} {row['Seniority']} -> {fallback_rate}")
            
            # Check if fallbacks resolved all issues
            still_missing = fallback_merged[fallback_merged["Rate_USD"].isna()]
            if not still_missing.empty:
                # Apply band-aware default rate as last resort
                ps = self.pricing_settings[self.pricing_settings["Key"]=="Default_Blended_Rate"]
                base_default = float(ps["Default"].iloc[0]) if not ps.empty else 185.0
                band = self.rate_bands[self.rate_bands["Band_Name"] == rate_band]
                mult = float(band["Rate_Multiplier"].iloc[0]) if not band.empty else 1.0
                default_rate = base_default * mult
                fallback_merged["Rate_USD"] = fallback_merged["Rate_USD"].fillna(default_rate)
                missing_list = [(row["Resource_Title"], row["Seniority"]) for _, row in still_missing.iterrows()]
                print(f"Warning: Applied band-aware default rate ${default_rate}/hr for missing roles: {missing_list}")
            
            merged = fallback_merged
        
        merged["Rate_USD"] = merged["Rate_USD"].astype(float)
        merged["Price"] = merged["Hours"] * merged["Rate_USD"]
        return float(merged["Price"].sum()), merged

    def hours_by_role_for_deliverable(self, deliverable_code: str, included_tgs: list[str], scenario_col: str) -> pd.DataFrame:
        """Get hours by role+seniority for an entire deliverable across all included task groups."""
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str).isin([str(x) for x in included_tgs]))
        ].copy()
        if sub.empty or scenario_col not in sub.columns:
            return pd.DataFrame(columns=["Resource_Title","Seniority","Hours"])
        g = sub.groupby(["Resource_Title","Seniority"], as_index=False)[scenario_col].sum()
        return g.rename(columns={scenario_col: "Hours"})

    def hours_by_role_for_component(self, deliverable_code: str, component: str,
                                    included_tgs: list[str], scenario_col: str) -> pd.DataFrame:
        """Get hours by role+seniority for a specific component."""
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str).isin([str(x) for x in included_tgs]))
        ].copy()
        sub["Component"] = sub.get("Component", "").astype(str).fillna("").str.strip()
        if (component or "").strip() and component != "General":
            sub = sub[sub["Component"] == component]
        else:
            sub = sub[(sub["Component"] == "") | (sub["Component"] == "General")]
        if sub.empty or scenario_col not in sub.columns:
            return pd.DataFrame(columns=["Resource_Title","Seniority","Hours"])
        g = sub.groupby(["Resource_Title","Seniority"], as_index=False)[scenario_col].sum()
        return g.rename(columns={scenario_col: "Hours"})

    def hours_by_role_for_component_task(self, deliverable_code: str, component: str,
                                         task_group: str, scenario_col: str) -> pd.DataFrame:
        """Get hours by role+seniority for a specific component+task combination."""
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str) == str(task_group))
        ].copy()
        sub["Component"] = sub.get("Component", "").astype(str).fillna("").str.strip()
        if (component or "").strip() and component != "General":
            sub = sub[sub["Component"] == component]
        else:
            sub = sub[(sub["Component"] == "") | (sub["Component"] == "General")]
        if sub.empty or scenario_col not in sub.columns:
            return pd.DataFrame(columns=["Resource_Title","Seniority","Hours"])
        g = sub.groupby(["Resource_Title","Seniority"], as_index=False)[scenario_col].sum()
        return g.rename(columns={scenario_col: "Hours"})

    def _svc_mode(self, series: pd.Series) -> str:
        if series is None or series.empty: return ""
        s = series.dropna().astype(str).str.strip()
        s = s[s != ""]
        return s.value_counts().idxmax() if not s.empty else ""

    def service_department_for_task(self, deliverable_code: str, component: str, task_group: str) -> str:
        if self.v3_all_rows is None or self.v3_all_rows.empty:
            return ""
        sub = self.v3_all_rows[
            (self.v3_all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.v3_all_rows["task_group"].astype(str) == str(task_group))
        ].copy()
        if component:
            sub = sub[sub["Component"].astype(str) == str(component)]
        return self._svc_mode(sub["Service Department"])

    def service_department_for_component(self, deliverable_code: str, component: str, task_groups: list[str]) -> str:
        if self.v3_all_rows is None or self.v3_all_rows.empty:
            return ""
        sub = self.v3_all_rows[
            (self.v3_all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.v3_all_rows["task_group"].astype(str).isin([str(x) for x in task_groups]))
        ].copy()
        if component:
            sub = sub[sub["Component"].astype(str) == str(component)]
        return self._svc_mode(sub["Service Department"])

    def service_department_for_deliverable(self, deliverable_code: str, task_groups: list[str]) -> str:
        if self.v3_all_rows is None or self.v3_all_rows.empty:
            return ""
        sub = self.v3_all_rows[
            (self.v3_all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.v3_all_rows["task_group"].astype(str).isin([str(x) for x in task_groups]))
        ]
        return self._svc_mode(sub["Service Department"])

    def _majority_by_hours(self, sub: pd.DataFrame, col: str, scenario_col: str) -> str:
        if sub.empty or col not in sub.columns or scenario_col not in sub.columns:
            return ""
        g = sub.groupby(col, as_index=False)[scenario_col].sum()
        g = g[g[col].astype(str).str.strip() != ""]
        if g.empty: return ""
        return str(g.sort_values(scenario_col, ascending=False).iloc[0][col]).strip()

    def service_dept_for_deliverable(self, deliverable_code: str, included_tgs: list[str], scenario_col: str) -> str:
        if not getattr(self, "_col_service_dept", None): return ""
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str)==str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str).isin([str(x) for x in included_tgs]))
        ]
        return self._majority_by_hours(sub, self._col_service_dept, scenario_col)

    def service_dept_for_component(self, deliverable_code: str, component: str, included_tgs: list[str], scenario_col: str) -> str:
        if not getattr(self, "_col_service_dept", None): return ""
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str)==str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str).isin([str(x) for x in included_tgs]))
        ].copy()
        if "Component" in sub.columns:
            sub["Component"] = sub["Component"].astype(str).fillna("").str.strip()
            sub = sub[sub["Component"]==str(component).strip()]
        return self._majority_by_hours(sub, self._col_service_dept, scenario_col)

    def hours_by_role_for_component_task(
        self, deliverable_code: str, component: str, task_group: str, scenario_col: str
    ) -> pd.DataFrame:
        """Return hours by (Resource_Title, Seniority) for one component+task_group."""
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str) == str(task_group))
        ].copy()
        if "Component" in sub.columns and str(component).strip():
            sub["Component"] = sub["Component"].astype(str).fillna("").str.strip()
            sub = sub[sub["Component"] == str(component).strip()]
        if sub.empty or scenario_col not in sub.columns:
            return pd.DataFrame(columns=["Resource_Title","Seniority","Hours"])
        g = sub.groupby(["Resource_Title","Seniority"], as_index=False)[scenario_col].sum()
        return g.rename(columns={scenario_col: "Hours"})

    def codes_for_component_task_role(
        self, deliverable_code: str, component: str, task_group: str,
        role: str, seniority: str, scenario_col: str
    ) -> tuple[str, str, str]:
        """Return (Row_ID, Task_Code, Service_Department) for one Role on a component+task_group."""
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str) == str(task_group)) &
            (self.all_rows["Resource_Title"].astype(str) == str(role)) &
            (self.all_rows["Seniority"].astype(str) == str(seniority))
        ].copy()
        if "Component" in sub.columns and str(component).strip():
            sub["Component"] = sub["Component"].astype(str).fillna("").str.strip()
            sub = sub[sub["Component"] == str(component).strip()]

        # Row_ID
        row_id = ""
        if getattr(self, "_col_row_id", None) and self._col_row_id in sub.columns:
            vals = sub[self._col_row_id].dropna().astype(str).str.strip()
            if not vals.empty:
                row_id = sorted(vals.tolist(), key=lambda x: (len(x), x))[0]

        # Task_Code
        task_code = ""
        if getattr(self, "_col_task_code", None) and self._col_task_code in sub.columns:
            v = sub[self._col_task_code].dropna().astype(str).str.strip()
            if not v.empty:
                task_code = v.value_counts().idxmax()
        if not task_code:
            task_code = str(task_group).upper().replace(" ", "_")

        # Service_Department (majority by hours in this subset)
        service = ""
        if getattr(self, "_col_service_dept", None) and self._col_service_dept in sub.columns:
            g = sub.groupby(self._col_service_dept, as_index=False)[scenario_col].sum()
            g = g[g[self._col_service_dept].astype(str).str.strip() != ""]
            if not g.empty:
                service = str(g.sort_values(scenario_col, ascending=False).iloc[0][self._col_service_dept]).strip()

        return (row_id, task_code, service)

    def codes_for_component_task(self, deliverable_code: str, component: str, task_group: str, scenario_col: str) -> tuple[str,str,str]:
        """Return (Row_ID, Task_Code, Service_Department) for a task row under a component."""
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str)==str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str)==str(task_group))
        ].copy()
        if "Component" in sub.columns and component:
            sub["Component"] = sub["Component"].astype(str).fillna("").str.strip()
            sub = sub[sub["Component"]==str(component).strip()]

        # Row_ID: stable pick (min or first non-empty)
        row_id = ""
        if getattr(self, "_col_row_id", None) and self._col_row_id in sub.columns:
            vals = sub[self._col_row_id].dropna().astype(str).str.strip()
            if not vals.empty:
                row_id = sorted(vals.tolist(), key=lambda x: (len(x), x))[0]

        # Task_Code: majority by count (or fallback to task_group)
        task_code = ""
        if getattr(self, "_col_task_code", None) and self._col_task_code in sub.columns:
            v = sub[self._col_task_code].dropna().astype(str).str.strip()
            if not v.empty:
                task_code = v.value_counts().idxmax()
        if not task_code:
            task_code = str(task_group).upper().replace(" ", "_")

        # Service_Department: majority by hours
        service = ""
        if getattr(self, "_col_service_dept", None) and self._col_service_dept in sub.columns:
            service = self._majority_by_hours(sub, self._col_service_dept, scenario_col)

        return (row_id, task_code, service)

DB = AgencyDB()

# ---------- Helper: extract text from uploaded file bytes ----------
def _extract_text_from_upload(content: bytes, filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()

    # Plain text-like
    if ext in (".txt", ".md", ".csv"):
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="ignore")

    # DOCX
    if ext == ".docx":
        if not Document:
            raise HTTPException(400, "DOCX support requires 'python-docx'. Install it and redeploy.")
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)

    # PDF
    if ext == ".pdf":
        if not PdfReader:
            raise HTTPException(400, "PDF support requires 'pypdf'. Install it and redeploy.")
        reader = PdfReader(io.BytesIO(content))
        buf = []
        for page in reader.pages:
            # pypdf exposes .extract_text()
            t = page.extract_text() or ""
            buf.append(t)
        return "\n".join(buf)

    raise HTTPException(415, f"Unsupported file type: {ext}. Use .pdf, .docx, or .txt.")

# ---------- Helper: sanitize filenames ----------
def _safe_filename(s: str) -> str:
    s = (s or "Proposal").strip()
    # Replace characters that are invalid on Windows/macOS and path separators for security
    s = re.sub(r'[\\/:*?"<>|]+', '-', s)
    # Remove any path traversal attempts
    s = re.sub(r'\.\.+', '', s)
    # Only allow alphanumeric, spaces, underscores, hyphens, and dots
    s = re.sub(r'[^A-Za-z0-9 _.-]', '', s)
    # Collapse whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    # Ensure it's not empty after sanitization
    return s if s else "Proposal"

def _upload_title_default() -> str | None:
    """Base title from the most recent uploaded file (sans extension), sanitized."""
    if not LAST_UPLOAD_FILENAME:
        return None
    base = os.path.splitext(os.path.basename(LAST_UPLOAD_FILENAME))[0]
    return _safe_filename(base)

def _est_stamp_for_filename() -> str:
    """
    Eastern time, 12-hour with AM/PM. Use dot instead of colon because
    ':' is illegal in filenames on Windows.
    Example: 2025-09-13 09.30AM EST
    """
    now_est = datetime.datetime.now(ZoneInfo("America/New_York"))
    return now_est.strftime("%Y-%m-%d %I.%M%p EST")

def _export_basename(project_name: str, scenario_label: str | None = None) -> str:
    """Project - Workfront_Export - [Scenario?] - 2025-09-13 09.30AM EST"""
    title = _safe_filename(project_name or "Proposal")
    parts = [title, "Workfront_Export"]
    if scenario_label:
        parts.append(_safe_filename(scenario_label))
    parts.append(_est_stamp_for_filename())
    return " - ".join(parts)

def _safe_sheet_name(s: str) -> str:
    # Excel sheet name rules: max 31 chars, no : \ / ? * [ ]
    s = re.sub(r'[:\\/?*\[\]]+', "-", (s or "Sheet"))
    s = s.strip() or "Sheet"
    return s[:31]

def _apply_number_formats(ws, df):
    """Format numeric columns: Hours & Price -> 0 decimals, Rate -> 2 decimals."""
    col_idx = {c: i+1 for i, c in enumerate(df.columns)}  # 1-based
    # Whole-number columns
    for col in ["Planned_Hours", "Start_Offset_Days", "Duration_Days", "Price_USD"]:
        if col in col_idx:
            j = col_idx[col]
            for col_cells in ws.iter_cols(min_col=j, max_col=j, min_row=2, max_row=ws.max_row):
                for cell in col_cells:
                    cell.number_format = "0"
    # Rate with 2 decimals
    if "Rate_USD" in col_idx:
        j = col_idx["Rate_USD"]
        for col_cells in ws.iter_cols(min_col=j, max_col=j, min_row=2, max_row=ws.max_row):
            for cell in col_cells:
                cell.number_format = "0.00"

def _finalize_wf_df(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure all expected columns exist
    for col in WF_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col not in {"Planned_Hours","Start_Offset_Days","Duration_Days","Rate_USD","Price_USD"} else 0

    # Reindex to canonical order
    df = df[WF_COLUMNS].copy()

    # Enforce numeric types & pricing identity
    df["Planned_Hours"]     = pd.to_numeric(df["Planned_Hours"], errors="coerce").fillna(0).round(0).astype(int)
    df["Start_Offset_Days"] = pd.to_numeric(df["Start_Offset_Days"], errors="coerce").fillna(0).round(0).astype(int)
    df["Duration_Days"]     = pd.to_numeric(df["Duration_Days"], errors="coerce").fillna(0).round(0).astype(int)
    df["Rate_USD"]          = pd.to_numeric(df["Rate_USD"], errors="coerce").fillna(0).round(2)
    df["Price_USD"]         = (df["Planned_Hours"] * df["Rate_USD"]).round(0).astype(int)  # Hours × Rate (whole USD)

    return df

# ---------- v3 A-E Column Ordering Helper ----------
V3_AE_ORDER = ["Row_ID", "Deliverable_Code", "Task_Code", "Service_Department", "Deliverable"]

def _ensure_v3_ae_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure v3 A-E columns exist and are positioned first (leftmost) in exports."""
    # Create columns if missing
    for c in V3_AE_ORDER:
        if c not in df.columns:
            df[c] = ""
    # Reorder so A–E are leftmost
    rest = [c for c in df.columns if c not in V3_AE_ORDER]
    return df[V3_AE_ORDER + rest]

# ---------- WBS builder functions ----------
def _round_int(x: float) -> int:
    try:
        return int(round(float(x)))
    except Exception:
        return 0

def _largest_remainder(target_total: int, parts: dict[str, float]) -> dict[str, int]:
    if not parts:
        return {}
    total = sum(parts.values())
    if total <= 0:
        return {k: 0 for k in parts.keys()}
    raw = {k: (v / total) * target_total for k, v in parts.items()}
    flo = {k: int(v) for k, v in raw.items()}
    rem = target_total - sum(flo.values())
    order = sorted(parts.keys(), key=lambda k: (raw[k] - flo[k]), reverse=True)
    for k in order[:max(0, rem)]:
        flo[k] += 1
    return flo

def _eff_rate(price: float, hours: float) -> float:
    """Calculate effective rate: price / hours with rounding."""
    return round(price / hours, 2) if hours and hours > 0 else 0.0

def _band_multiplier(rate_band: str) -> float:
    band = DB.rate_bands[DB.rate_bands["Band_Name"] == (rate_band or "Standard_US")]
    return float(band["Rate_Multiplier"].iloc[0]) if not band.empty else 1.0

def _wbs_order_mode():
    return "timeline"

def build_wbs_with_pricing(scenario: dict, project_name: str) -> pd.DataFrame:
    """
    Adds Rate_USD and Price_USD at deliverable/component/task level.
    Flat_Blended -> uses blended_rate
    Per_Resource -> weighted effective per level
    """
    rows = []
    pricing_mode = (scenario.get("pricing_mode") or "Flat_Blended").strip()
    rate_band    = (scenario.get("rate_band") or "Standard_US").strip()
    blended_rate = scenario.get("blended_rate")
    if blended_rate is None:
        # fallback to default from Pricing_Settings already loaded in v2
        ps = DB.pricing_settings[DB.pricing_settings["Key"]=="Default_Blended_Rate"]
        blended_rate = float(ps["Default"].iloc[0]) if not ps.empty else 185.0
    blended_rate = float(blended_rate)

    # project parent
    rows.append({
        "Row_ID": "",
        "Deliverable_Code": "",
        "Task_Code": "",
        "Service_Department": "",
        "Deliverable": "",
        "Project_Name": project_name, "WBS_ID": "1", "Parent_WBS_ID": "",
        "Task_Name": project_name, "Component": "Project", "Task": "",
        "Role": "", "Seniority": "", "Planned_Hours": "", "Start_Offset_Days": 0, "Duration_Days": "",
        "Dependencies": "", "Assignee_External_ID": "", "Notes": "",
        "Rate_USD": "", "Price_USD": ""
    })

    items = scenario.get("items", [])
    order_map = {str(tg): i for i, tg in enumerate(DB.timeline_params["Task_Group"].astype(str).tolist())}

    if _wbs_order_mode() == "timeline":
        def deliv_key(d):
            tgs = [str(x) for x in d.get("included_task_groups", [])]
            idxs = [order_map.get(tg, 999) for tg in tgs]
            return (min(idxs) if idxs else 999, str(d.get("deliverable","")))
        items_sorted = sorted(items, key=deliv_key)
    else:
        items_sorted = list(scenario.get("items", []))

    day_cursor = 0
    prev_deliv_wbs = ""

    for i, d in enumerate(items_sorted, start=1):
        dcode = str(d.get("deliverable_code", d.get("code", f"DELIV_{i}")))
        scen_col = d.get("scenario_col", "MED_LOW")
        included = [str(x) for x in d.get("included_task_groups", [])]
        if not included:
            # derive from the database for this deliverable
            sub = DB.all_rows[DB.all_rows["Deliverable_Code"].astype(str) == str(dcode)]
            included = sorted(set(sub["task_group"].dropna().astype(str).tolist()))

        # Get deliverable name - try from scenario first, then lookup from database
        deliv_label = str(d.get("deliverable", "")).strip()
        if not deliv_label:
            # Fallback: lookup deliverable name from database using code
            row = DB.deliverables[DB.deliverables["Deliverable_Code"].astype(str)==str(dcode)]
            if not row.empty:
                deliv_label = str(row["Deliverable"].iloc[0])
            else:
                deliv_label = f"Deliverable {dcode}"

        # schedule offsets/durations by task_group
        schedule = d.get("schedule", [])
        if not schedule:
            complexity = d.get("complexity", "Advanced")
            tier = d.get("tier", "T2_MediumVolume")
            schedule = DB.build_schedule(
                deliverable_code=dcode,
                included_task_groups=included,
                complexity=complexity,
                tier=tier,
                use_slack=scenario.get("use_slack", True),
                slack_after_internal=scenario.get("slack_after_internal", 1),
                slack_after_client=scenario.get("slack_after_client", 2),
                slack_global_pct=scenario.get("slack_global_pct", 0.05),
                project_start=scenario.get("project_start"),
                scenario_letter=scenario.get("scenario_label", "A")
            )
        tg_order = sorted(included, key=lambda tg: order_map.get(tg, 999))
        duration_by_tg = {str(t["task_group"]): int(t["duration_days"]) for t in schedule}
        offset_by_tg = {}
        run = 0
        for tg in tg_order:
            offset_by_tg[tg] = run
            run += int(duration_by_tg.get(tg, 1))
        total_deliv_duration = run

        # Derive hours_by_role if missing (robustness fix)
        hrs_df = pd.DataFrame(d.get("hours_by_role") or [])
        if hrs_df.empty:
            scen_col_resolved = DB.scenario_hours_col(d.get("complexity","Advanced"), d.get("tier","T2_MediumVolume"))
            hrs_df = DB.hours_by_role_for_deliverable(dcode, included, scen_col_resolved)
            d["hours_by_role"] = hrs_df.to_dict("records")
        
        # Ensure total_hours is calculated correctly
        calculated_total = float(hrs_df["Hours"].sum()) if not hrs_df.empty else 0.0
        if not d.get("total_hours") or float(d.get("total_hours", 0.0)) == 0.0:
            d["total_hours"] = calculated_total
        
        # hours (use exact for pricing, round for display)
        parent_hours_exact = float(d.get("total_hours", calculated_total))
        parent_hours_display = int(round(parent_hours_exact))

        months = int((d.get("retainer") or {}).get("months", 0))
        monthly_hours = int(d.get("monthly_hours") or 0)
        monthly_price = int(d.get("monthly_price") or 0)

        # price/rate at deliverable
        if pricing_mode == "Flat_Blended":
            deliv_rate = blended_rate
            deliv_price = round((monthly_hours if months else parent_hours_display) * deliv_rate, 2)
        else:
            hrs_by_role_deliv = DB.hours_by_role_for_deliverable(dcode, tg_order, scen_col)
            deliv_price, _ = DB.price_for_hours_by_role(hrs_by_role_deliv, rate_band)
            deliv_price = round(deliv_price, 2)
        if months:
            deliv_price = round(deliv_price * months, 2)

        # Build deliverable node
        wbs_deliv = f"1.{i}"
        svc_deliv = DB.service_dept_for_deliverable(dcode, tg_order, scen_col)
        # deliv_label already set above with database fallback - don't override it
        deliv_notes = f'{d.get("complexity","")}/{d.get("tier","")}' + (f' | Retainer x{months} months' if months else '')
        total_deliv_duration = sum(int(t["duration_days"]) for t in schedule)  # one-cycle length
        rows.append({
            "Row_ID": "",
            "Deliverable_Code": dcode,
            "Task_Code": "",
            "Service_Department": svc_deliv,
            "Deliverable": deliv_label,
            "Project_Name": project_name, "WBS_ID": wbs_deliv, "Parent_WBS_ID": "1",
            "Task_Name": deliv_label,
            "Component": "", "Task": "", "Role": "", "Seniority": "",
            "Planned_Hours": (monthly_hours * months) if months else parent_hours_display,
            "Start_Offset_Days": day_cursor,
            "Duration_Days": (total_deliv_duration * months) if months else total_deliv_duration,
            "Dependencies": prev_deliv_wbs, "Assignee_External_ID": "", "Notes": deliv_notes,
            "Rate_USD": round(deliv_rate if pricing_mode=="Flat_Blended" else _eff_rate(deliv_price, (monthly_hours*months) if months else parent_hours_display), 2),
            "Price_USD": round(deliv_price, 2)
        })

        comps = DB.components_for_deliverable(dcode, tg_order)
        # Per-month hours by component (exact) and rounded for display
        comp_hours_map_month = DB.hours_by_component(dcode, tg_order, scen_col)
        # If not a retainer, treat "month" as the whole
        base_comp_hours_display = _largest_remainder((monthly_hours if months else parent_hours_display), comp_hours_map_month if months else comp_hours_map_month)

        prev_comp_wbs = ""

        for j, comp in enumerate(comps, start=1):
            tg_hours_in_comp = DB.hours_by_taskgroup_for_component(dcode, comp, tg_order, scen_col)  # per 'month' basis
            tg_in_comp = [tg for tg in tg_order if tg in tg_hours_in_comp.keys()]
            if not tg_in_comp:
                continue

            comp_offset = min(offset_by_tg[tg] for tg in tg_in_comp)
            comp_duration = sum(int(duration_by_tg.get(tg, 1)) for tg in tg_in_comp)

            comp_hours_month_display = int(base_comp_hours_display.get(comp, 0))
            comp_hours_total_display = comp_hours_month_display * months if months else comp_hours_month_display

            # Compute component-level price in Per_Resource mode (band-aware), monthly then scale
            if pricing_mode == "Flat_Blended":
                comp_rate = blended_rate
                comp_price = round((comp_hours_month_display if months else comp_hours_total_display) * comp_rate, 2)
                if months:
                    comp_price = round(comp_price * months, 2)
            else:
                hrs_by_role_comp = DB.hours_by_role_for_component(dcode, comp, tg_in_comp, scen_col)
                comp_price_month, _ = DB.price_for_hours_by_role(hrs_by_role_comp, rate_band)
                comp_price = round(comp_price_month * (months if months else 1), 2)

            wbs_comp = f"{wbs_deliv}.{j}"
            svc_comp = DB.service_dept_for_component(dcode, comp, tg_in_comp, scen_col)
            rows.append({
                "Row_ID": "", "Deliverable_Code": dcode, "Task_Code": "", "Service_Department": svc_comp,
                "Deliverable": deliv_label,
                "Project_Name": project_name, "WBS_ID": wbs_comp, "Parent_WBS_ID": wbs_deliv,
                "Task_Name": comp, "Component": comp, "Task": "", "Role": "", "Seniority": "",
                "Planned_Hours": comp_hours_total_display,
                "Start_Offset_Days": day_cursor + comp_offset,
                "Duration_Days": (comp_duration * months) if months else comp_duration,
                "Dependencies": (wbs_deliv if j == 1 else prev_comp_wbs),
                "Assignee_External_ID": "", "Notes": "",
                "Rate_USD": round(comp_rate if pricing_mode=="Flat_Blended" else _eff_rate(comp_price, comp_hours_total_display or 0), 2),
                "Price_USD": round(comp_price, 2)
            })

            # --- Tasks under the component ---
            # Per-month target hours for each task group, then repeat Month 01..N
            tg_hours_month = {tg: float(tg_hours_in_comp.get(tg, 0.0)) for tg in tg_in_comp}
            tg_target_month = _largest_remainder(comp_hours_month_display, tg_hours_month)

            # Build month-by-month repetition
            total_tasks_per_month = len(tg_in_comp)
            prev_month_last_wbs = ""  # chain months sequentially per component

            for month_idx in range(1, (months if months else 1) + 1):
                # enumerates tasks within this month
                prev_task_last_wbs = ""
                for k, tg in enumerate(tg_in_comp, start=1):
                    dur = int(duration_by_tg.get(tg, 1))
                    label_core = DB.task_label_for_component_tg(dcode, comp, tg) if hasattr(DB, "task_label_for_component_tg") else tg
                    label = (f"Month {month_idx:02d} – {label_core}") if months else label_core

                    # Unique task index within the component across months
                    task_ordinal = (month_idx-1)*total_tasks_per_month + k
                    wbs_task = f"{wbs_comp}.{task_ordinal}"

                    base_offset = day_cursor + offset_by_tg[tg] + ((month_idx-1) * total_deliv_duration)

                    rows.append({
                        "Row_ID": "", "Deliverable_Code": dcode, "Task_Code": "", "Service_Department": svc_comp,
                        "Deliverable": deliv_label,
                        "Project_Name": project_name, "WBS_ID": wbs_task, "Parent_WBS_ID": wbs_comp,
                        "Task_Name": label, "Component": comp, "Task": label,
                        "Role": "", "Seniority": "",
                        "Planned_Hours": "",   # stays on role rows
                        "Start_Offset_Days": base_offset,
                        "Duration_Days": dur,
                        "Dependencies": (wbs_comp if (k==1 and month_idx==1) else (prev_task_last_wbs if k>1 else prev_month_last_wbs)),
                        "Assignee_External_ID": "", "Notes": ""
                    })

                    # Role rows for this task in this month
                    hrs_role_df = DB.hours_by_role_for_component_task(dcode, comp, tg, scen_col)
                    role_rows = hrs_role_df.to_dict(orient="records")
                    target_task_hours = int(tg_target_month.get(tg, 0)) if months else int(tg_target_month.get(tg, 0))

                    raw_map = {(r["Resource_Title"], r["Seniority"]): float(r["Hours"]) for r in role_rows}
                    if not raw_map:
                        raw_map = {("","Mid"): float(target_task_hours)}
                    total = sum(raw_map.values()) or 1.0
                    raw_scaled = {key: (val/total)*target_task_hours for key, val in raw_map.items()}
                    flo = {key: int(val) for key, val in raw_scaled.items()}
                    rem = target_task_hours - sum(flo.values())
                    order = sorted(raw_map.keys(), key=lambda kk: (raw_scaled[kk]-flo[kk]), reverse=True)
                    for kk in order[:max(0, rem)]:
                        flo[kk] += 1

                    prev_role_wbs = ""
                    r_index = 0
                    for (role, sen), h in flo.items():
                        if h <= 0:
                            continue
                        r_index += 1
                        row_id, task_code, svc_task = DB.codes_for_component_task_role(dcode, comp, tg, role or "", sen or "", scen_col)
                        wbs_role = f"{wbs_task}.{r_index}"

                        # Compute role rate
                        if pricing_mode == "Flat_Blended":
                            role_rate = float(blended_rate)
                        else:
                            rr = DB.role_rates_table(rate_band)
                            match = rr[(rr["Resource_Title"] == str(role)) & (rr["Seniority"] == str(sen))]
                            if not match.empty:
                                role_rate = float(match["Rate_USD"].iloc[0])
                            else:
                                match2 = rr[rr["Resource_Title"] == str(role)]
                                if not match2.empty:
                                    role_rate = float(match2["Rate_USD"].iloc[0])
                                else:
                                    ps = DB.pricing_settings[DB.pricing_settings["Key"] == "Default_Blended_Rate"]
                                    base_default = float(ps["Default"].iloc[0]) if not ps.empty else 185.0
                                    role_rate = base_default * _band_multiplier(rate_band)

                        row_hours = int(h)
                        row_price = int(round(role_rate * row_hours))

                        rows.append({
                            "Row_ID": row_id,
                            "Deliverable_Code": dcode,
                            "Task_Code": task_code,
                            "Service_Department": (svc_task or svc_comp),
                            "Deliverable": deliv_label,
                            "Project_Name": project_name, "WBS_ID": wbs_role, "Parent_WBS_ID": wbs_task,
                            "Task_Name": label, "Component": comp, "Task": label,
                            "Role": role or "", "Seniority": sen or "",
                            "Planned_Hours": row_hours,
                            "Start_Offset_Days": "", "Duration_Days": "",
                            "Dependencies": wbs_task if r_index == 1 else prev_role_wbs,
                            "Assignee_External_ID": "", "Notes": "",
                            "Rate_USD": round(role_rate, 2),
                            "Price_USD": row_price
                        })
                        prev_role_wbs = wbs_role

                    prev_task_last_wbs = prev_role_wbs or wbs_task

                prev_month_last_wbs = prev_task_last_wbs

            prev_comp_wbs = wbs_comp

        day_cursor += total_deliv_duration
        prev_deliv_wbs = wbs_deliv

    df = pd.DataFrame(rows)
    
    # --- ENFORCE A-E COLUMN ORDER FOR v3 COMPATIBILITY ---
    order_ae = ["Row_ID","Deliverable_Code","Task_Code","Service_Department","Deliverable"]
    # Ensure all required columns exist before reordering
    for col in order_ae:
        if col not in df.columns:
            df[col] = ""
    rest = [c for c in df.columns if c not in order_ae]
    df = df.reindex(columns=order_ae + rest, fill_value="")
    
    # --- ENFORCE NUMERIC TYPES & PRICE FORMULA ---
    # Coerce to numeric and fill blanks
    if "Planned_Hours" in df.columns:
        df["Planned_Hours"] = pd.to_numeric(df["Planned_Hours"], errors="coerce").fillna(0).round(0).astype(int)

    # Rate shown with 2 decimals; blanks -> 0
    if "Rate_USD" in df.columns:
        df["Rate_USD"] = pd.to_numeric(df["Rate_USD"], errors="coerce").fillna(0).round(2)

    # Always compute Price from Hours × Rate, then round to whole dollars (no cents)
    if "Planned_Hours" in df.columns and "Rate_USD" in df.columns:
        df["Price_USD"] = (df["Planned_Hours"] * df["Rate_USD"]).round(0).astype(int)
    else:
        df["Price_USD"] = 0

    return df

def build_wbs_dataframe_from_scenario(scenario: dict, project_name: str) -> pd.DataFrame:
    """Build WBS with pricing - delegates to the enhanced pricing-aware version."""
    return build_wbs_with_pricing(scenario, project_name)

# For backward compatibility, keep the old function name pointing to the new one
def _wbs_dataframe_from_scenario(scenario: dict, project_name: str) -> pd.DataFrame:
    """Legacy function name - redirects to the new WBS builder."""
    return build_wbs_dataframe_from_scenario(scenario, project_name)

# ---------- Pydantic models ----------
class SuggestPayload(BaseModel):
    rfp_text: str

class ResolveDeliverablesPayload(BaseModel):
    inputs: list[str] = []

# --- NEW: Retainer selection model ---
class RetainerSelection(BaseModel):
    deliverable_code: str
    months: int  # 1..12

class ScenarioSpec(BaseModel):
    mode: str                               # "template" or "bundle"
    # if mode == "template"
    scenario_key: Optional[str] = None      # e.g., "MED_LOW" or "MED_HIGH"
    complexity: Optional[str] = None        # override complexity
    tier: Optional[str] = None              # override tier
    # if mode == "bundle"
    bundle: Optional[str] = None            # Express/Good/Better/Best

class BuildPayload(BaseModel):
    selected_deliverable_codes: List[str]
    scenario_a: ScenarioSpec
    scenario_b: ScenarioSpec
    pricing_mode: str                       # "Flat_Blended" or "Per_Resource"
    blended_rate: Optional[float] = None
    rate_band: Optional[str] = "Standard_US"
    use_slack: bool = True
    slack_after_internal: int = 1
    slack_after_client: int = 2
    slack_global_pct: float = 0.05
    project_start: Optional[str] = None     # "YYYY-MM-DD"
    # NEW: monthly retainers selected on the second screen
    retainers: Optional[List[RetainerSelection]] = []
    # NEW: component-level selection per deliverable (supports both formats)
    selected_components_map: Optional[Dict[str, Union[List[str], Dict[str, float]]]] = None

class AutoBuildPayload(BaseModel):
    rfp_text: str
    scenario_a: ScenarioSpec
    scenario_b: ScenarioSpec
    pricing_mode: str                       # "Flat_Blended" or "Per_Resource"
    blended_rate: Optional[float] = None
    rate_band: Optional[str] = "Standard_US"
    use_slack: bool = True
    slack_after_internal: int = 1
    slack_after_client: int = 2
    slack_global_pct: float = 0.05
    project_start: Optional[str] = None     # "YYYY-MM-DD"
    # NEW: optional retainers alongside auto suggestions
    retainers: Optional[List[RetainerSelection]] = []

class ExportPayload(BaseModel):
    scenario: Dict[str, Any]
    project_name: Optional[str] = None       # e.g., "Casa Dragones"
    file_format: Optional[str] = "csv"       # "csv" or "xlsx"
    scenario_label: Optional[str] = None     # e.g., "Scenario A"
    add_timestamp: Optional[bool] = False    # include yyyymmdd-HHMM in filename?                # a scenario dict returned from /api/build

class ExportWorkbookPayload(BaseModel):
    scenario_a: dict
    scenario_b: dict
    project_name: str | None = None
    sheet_name_a: str | None = "Scenario A"
    sheet_name_b: str | None = "Scenario B"
    add_timestamp: bool | None = False

class ExportWorkbookABCPayload(BaseModel):
    scenario_a: dict
    scenario_b: dict
    scenario_c: dict
    project_name: str | None = None
    sheet_name_a: str | None = "Scenario A"
    sheet_name_b: str | None = "Scenario B"
    sheet_name_c: str | None = "Scenario C"
    add_timestamp: bool | None = False

class ExportXMLPayload(BaseModel):
    scenario: Optional[Dict[str, Any]] = None
    project_name: Optional[str] = None
    scenario_label: Optional[str] = None
    sheet_name: str = "Scenario A"
    start_date_mode: str = "next_monday"
    fixed_start_iso: Optional[str] = None
    hours_per_day: float = 8.0
    merge_identical_children: bool = False

class ExportWorkbookXMLPayload(BaseModel):
    scenario_a: Optional[Dict[str, Any]] = None
    scenario_b: Optional[Dict[str, Any]] = None  
    project_name: Optional[str] = None
    merge_identical_children: bool = False

class AuditPricingPayload(BaseModel):
    scenario: Dict[str, Any]           # scenario object from /api/build
    pricing_mode: str                  # "Flat_Blended" | "Per_Resource"
    blended_rate: Optional[float] = None
    rate_band: Optional[str] = "Standard_US"
    price_uses_rounded_hours: bool = True  # bill with rounded hours to match export

class BuildScenarioCPayload(BaseModel):
    base: str  # "A" or "B"
    add_on_codes: List[str] = []
    pricing_mode: str = "Flat_Blended"   # or "Per_Resource"
    blended_rate: Optional[float] = 195.0
    rate_band: str = "Standard_US"
    complexity: Optional[str] = None        # default to base scenario's
    tier: Optional[str] = None
    use_slack: Optional[bool] = None
    slack_after_internal: Optional[int] = None
    slack_after_client: Optional[int] = None
    slack_global_pct: Optional[float] = None
    project_start: Optional[str] = None     # "YYYY-MM-DD"
    # NEW: override or inherit from base scenario
    retainers: Optional[List[RetainerSelection]] = []

# --- AI Summary models (Stage 2) ---
class RfpSummaryItem(BaseModel):
    label: str                       # deliverable name (human-friendly)
    short_desc: str                  # <= 2 sentences
    tasks: list[str] | None = []     # optional, zero or more tasks (strings)

class RfpSummary(BaseModel):
    summary_text: str                # rendered text for right panel (<= 500 words)
    deliverables: list[RfpSummaryItem]
    word_count: int

class SummarizePayload(BaseModel):
    rfp_text: str | None = None      # optional if using file route

# --- Reconcile (Stage 2, middle panel) ---
class ReconcilePayload(BaseModel):
    summary_deliverables: List[str]                 # from the right-panel AI summary (labels only)
    db_selected_deliverable_codes: Optional[List[str]] = None  # current selection on the left (codes)
    rfp_text: Optional[str] = None

class ReconcileSuggestion(BaseModel):
    code: str
    label: str
    reason: str
    preselect: bool = True

class ReconcileResult(BaseModel):
    add: list[ReconcileSuggestion]
    delete: list[ReconcileSuggestion]
    unchanged: list[str]
    db_used_codes: list[str]          # NEW: actual codes reconcile compared
    db_used_labels: list[str]         # NEW: labels for those codes

class ReorderPayload(BaseModel):
    scenario_letter: str
    deliverable_codes: list[str]                        # new order
    included_map: dict[str, list[str]] | None = None   # {code: [task_groups]}
    use_slack: bool = True
    slack_after_internal: int = 1
    slack_after_client: int = 2
    slack_global_pct: float = 0.0
    project_start: str | None = None                   # "YYYY-MM-DD"
    complexity: str = "Advanced"
    tier: str = "T2_MediumVolume"

# ---------- Global Scenario Storage for Reordering ----------
_CURRENT_SCENARIOS = {}  # Store scenarios for reordering

def _current_scenarios():
    """Access current scenarios for reordering operations."""
    return _CURRENT_SCENARIOS

# ---------- OpenAI Integration Functions (Stage 2) ----------

# Initialize OpenAI client now that we can import it
try:
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
        print(f"OpenAI client initialized successfully")
    else:
        print("No OPENAI_API_KEY found in environment")
        openai_client = None
except Exception as e:
    print(f"Failed to initialize OpenAI client: {e}")
    openai_client = None  # Optional OpenAI integration

# --- Reconciliation Helper Functions ---
def _norm_tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))

def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

# --- LLM adapter: must not touch DB ---
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')

def _count_words(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s or ""))

def _truncate_to_2_sentences(s: str) -> str:
    parts = _SENT_SPLIT.split((s or "").strip())
    return " ".join(parts[:2]).strip()

def ai_summarize_rfp_text(text: str) -> RfpSummary:
    """
    Call GPT‑5 (max compute) with a structured prompt that returns JSON:
      { "deliverables": [{"label": "...", "short_desc": "...", "tasks": [".."]}, ...] }
    and a prose summary <= 500 words.
    This function intentionally avoids any DB lookups.
    """
    try:
        # Create structured prompt for GPT-5
        system_prompt = """
You are an agency executive producer.
Read the RFP text and output JSON ONLY in this exact schema:

{
  "deliverables": [
    {"label": "...", "short_desc": "...", "tasks": ["...", "..."]}
  ]
}

Guidelines:
- Identify 3–8 concrete agency deliverables needed to fulfill the request:
  strategy, campaign creative, content production (video/audio/stills), social/community, editorial web/livestream, experiential/IRL, media planning/buying, measurement & reporting, program management/timeline.
- Each "short_desc" is ≤2 sentences, specific to this RFP, action‑oriented.
- Use common agency taxonomy for "label" so it will match a database later (e.g., "Brand Strategy", "Campaign Creative", "Content Production (Video/Audio)", "Social Media & Community", "Editorial Microsite & Livestream", "Experiential Activation", "Media Planning & Buying", "Measurement & Reporting", "Program Management & Timeline").
- Do NOT quote the RFP; summarize the work we must deliver.
- Keep total text concise (UI cap is 500 words).
"""

        user_prompt = f"Analyze this RFP text and extract the key deliverables:\n\n{text[:8000]}"  # Limit input size
        
        response = openai_client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse JSON response
        import json
        result = json.loads(response.choices[0].message.content)
        deliverables = result.get("deliverables", [])
        
    except Exception as e:
        print(f"OpenAI error (using smarter fallback): {e}")
        t = (text or "").lower()
        deliverables = []

        def add(label, desc, *keys):
            if any(k in t for k in keys) and not any(d["label"] == label for d in deliverables):
                deliverables.append({"label": label, "short_desc": desc[:300], "tasks": []})

        add("Program Design (Artist Accelerator)",
            "Define cohort structure, creator services, milestones and governance for a year‑long program that introduces, elevates and celebrates artists.", 
            "accelerator", "year long", "program")
        add("Campaign Strategy & Creative Platform",
            "Create the organizing idea, audience strategy, KPIs and messaging architecture anchored to 'What's next in music is first on SoundCloud.'",
            "objectives", "kpi", "platform", "strategy", "creative")
        add("Content Production (Video/Audio/Stills)",
            "Produce hero and cutdown assets telling authentic artist stories across video, audio and stills sized for paid/owned social, digital and OOH.",
            "video", "audio", "stills")
        add("Editorial Microsite & Livestream",
            "Propose an editorial destination and livestream approach with UX outline, tech options and content governance.",
            "editorial", "platform", "live streaming")
        add("Social Media & Community",
            "Define an always‑on social calendar, creator collab mechanics and community management playbook.",
            "social")
        add("Experiential Activation",
            "Design a nimble IRL/virtual activation concept with budget tiers and contingency planning.",
            "experiential")
        add("Media Planning & Buying",
            "Provide paid media plan and flighting to support brand spend, with channel mix and pacing across the year.",
            "media")
        add("Measurement & Reporting",
            "Define KPI framework, reporting cadence and learning agenda; include a production timeline and rollout plan.",
            "measurement", "kpi", "production timeline", "rollout")

        if not deliverables:
            deliverables = [{"label":"Program Management & Timeline",
                             "short_desc":"Create a production timeline and rollout schedule with milestones and owners.",
                             "tasks":[]}]

    # enforce constraints
    for d in deliverables:
        d["short_desc"] = _truncate_to_2_sentences(d.get("short_desc",""))

    # concise prose capped at 500 words
    bullets = [f"• {d['label']}: {d['short_desc']}" for d in deliverables]
    prose = "\n".join(bullets)
    words = _count_words(prose)
    if words > 500:
        # trim from the end
        # (simple conservative trimming; UI also shows a counter)
        while bullets and _count_words("\n".join(bullets)) > 500:
            bullets.pop()
        prose = "\n".join(bullets)
        words = _count_words(prose)

    return RfpSummary(summary_text=prose, deliverables=[RfpSummaryItem(**d) for d in deliverables], word_count=words)

# --- Name matching for reconciliation (deterministic; DB only used here) ---

def _norm(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))

def _best_match(label: str, db_rows: pd.DataFrame) -> tuple[str,str,float] | None:
    tokens = _norm(label)
    best = None
    for _, r in db_rows.iterrows():
        code = str(r["Deliverable_Code"]); name = str(r["Deliverable"])
        t2 = _norm(name)
        if not tokens or not t2: 
            continue
        jacc = len(tokens & t2) / max(1, len(tokens | t2))
        if best is None or jacc > best[2]:
            best = (code, name, jacc)
    return best

def _average_spec_for(category: str) -> dict:
    # Prefer a template key containing "MED" if present, else default constants already used in v4 hours
    row = DB.scenario_templates[DB.scenario_templates["Scenario_Key"].str.contains("MED", case=False, na=False)]
    if not row.empty:
        c = str(row.iloc[0]["Complexity"]); t = str(row.iloc[0]["Tier"])
        return {"mode":"template","scenario_key":str(row.iloc[0]["Scenario_Key"]), "complexity":c, "tier":t}
    return {"mode":"template","scenario_key":"AVERAGE","complexity":"Advanced","tier":"T2_MediumVolume"}

# ---- Deliverable ordering helpers ----
def _phase_rank_for(deliv_name: str, included_tgs: list[str]) -> int:
    """Lower rank = earlier phase. Name takes precedence, then task_groups."""
    n = (deliv_name or "").strip().lower()
    if "discovery" in n or "research" in n or "strategy" in n:
        return 0
    if "design" in n or "creative" in n or "concept" in n:
        return 10
    if "post" in n:  # covers "post-production" - check this BEFORE production
        return 30
    if "development" in n or "build" in n or "production" in n:
        return 20
    if "qa" in n or "review" in n or "test" in n:
        return 40
    if "launch" in n or "deploy" in n:
        return 50
    # fall back to included task groups against Timeline_Params order
    base = {str(tg): i for i, tg in enumerate(DB.timeline_params["Task_Group"].astype(str).tolist())}
    if included_tgs:
        return min([base.get(str(tg), 999) for tg in included_tgs])
    return 999

def _deliverable_order_overrides(letter: str) -> list[tuple[str,str]]:
    """
    Optional: UI_Options keys:
      Deliverable_Order_Overrides_A = Development<Post-Production; QA<Launch
      Deliverable_Order_Overrides_B = ...
    Default for both A & B ensures Development comes before Post-Production.
    """
    try:
        key = f"Deliverable_Order_Overrides_{letter.upper()}"
        row = DB.ui_options[DB.ui_options["Key"] == key]
        if not row.empty:
            pairs = []
            for p in str(row["Value"].iloc[0]).split(";"):
                if "<" in p:
                    a, b = [x.strip().lower() for x in p.split("<", 1)]
                    if a and b: pairs.append((a, b))
            if pairs: return pairs
    except Exception:
        pass
    return [("production", "post-production")]  # default: Production < Post-Production

def _sort_deliverables(per_deliv: list[dict], letter: str) -> list[dict]:
    # base rank from phase
    def base_rank(d):
        return _phase_rank_for(d.get("deliverable",""), d.get("included_task_groups", []))
    # topological sort from overrides + base rank as tiebreak
    nodes = list(range(len(per_deliv)))
    name_lc = [str(d.get("deliverable","")).lower() for d in per_deliv]
    edges = []
    for a,b in _deliverable_order_overrides(letter):
        for i, n in enumerate(name_lc):
            if a in n:
                for j, m in enumerate(name_lc):
                    if b in m: edges.append((i,j))
    preds = {i:set() for i in nodes}; succs = {i:set() for i in nodes}
    for i,j in edges: succs[i].add(j); preds[j].add(i)
    ready = [i for i in nodes if not preds[i]]
    ready.sort(key=lambda i: (base_rank(per_deliv[i]), name_lc[i]))
    out = []
    while ready:
        i = ready.pop(0)
        out.append(i)
        for j in sorted(list(succs[i]), key=lambda k: (base_rank(per_deliv[k]), name_lc[k])):
            preds[j].discard(i)
            if not preds[j] and j not in out and j not in ready:
                ready.append(j)
        ready.sort(key=lambda k: (base_rank(per_deliv[k]), name_lc[k]))
    tail = [i for i in nodes if i not in out]
    tail.sort(key=lambda i: (base_rank(per_deliv[i]), name_lc[i]))
    return [per_deliv[i] for i in out + tail]

# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/load")
def api_load():
    if not DB.loaded:
        DB.load()
    return {"ok": True, "src": DB.src}

@app.get("/api/options")
def api_options():
    if not DB.loaded:
        DB.load()

    # Prefer v3 Drivers (3 each)
    v3_complexities, v3_tiers = DB.drivers_complexities_tiers_v3()
    if not v3_complexities:
        v3_complexities = DB.timeline_scaling[DB.timeline_scaling["Scale_Type"]=="Complexity"]["Key"].head(3).tolist()
    if not v3_tiers:
        v3_tiers = DB.timeline_scaling[DB.timeline_scaling["Scale_Type"]=="Tier"]["Key"].head(3).tolist()

    rate_bands = DB.rate_bands["Band_Name"].head(3).tolist()  # 3 bands max
    pricing_modes = ["Flat_Blended","Per_Resource"]
    deliverables = DB.deliverables[["Deliverable_Code","Deliverable","Category"]].to_dict(orient="records")

    return {
        "complexities": v3_complexities,
        "tiers": v3_tiers,
        "rate_bands": rate_bands,
        "pricing_modes": pricing_modes,
        "bundles": DB.b_defaults["Bundle"].tolist(),
        "deliverables": deliverables,
        "scenario_templates": DB.scenario_templates.to_dict(orient="records"),
        "pricing_settings": DB.pricing_settings.to_dict(orient="records"),
        "slack_settings": DB.slack_settings.to_dict(orient="records"),
    }

@app.get("/api/search_deliverables")
def api_search_deliverables(q: str = "", limit: int = 50):
    if not DB.loaded: DB.load()
    df = DB.deliverables.copy()
    q = (q or "").strip().lower()
    if q:
        mask = (
            df["Deliverable"].astype(str).str.lower().str.contains(q)
            | df["Category"].astype(str).str.lower().str.contains(q)
            | df["Deliverable_Code"].astype(str).str.lower().str.contains(q)
        )
        df = df[mask]
    rows = df[["Deliverable_Code", "Deliverable", "Category"]].head(limit).to_dict("records")
    return {"items": rows}

@app.post("/api/resolve_deliverables")
def api_resolve_deliverables(p: ResolveDeliverablesPayload):
    if not DB.loaded: DB.load()
    out = []
    for s in (p.inputs or []):
        code = DB._canonical_deliverable_code(s)   # v2.7 helper
        row = DB.deliverables[DB.deliverables["Deliverable_Code"].astype(str)==str(code)]
        if row.empty: 
            continue
        out.append({
            "input": s,
            "code": code,
            "deliverable": str(row["Deliverable"].iloc[0]),
            "category":  str(row["Category"].iloc[0]),
        })
    return {"resolved": out}

@app.get("/api/components_for")
def api_components_for(deliverable_code: str, complexity: str="Advanced", tier: str="T2_MediumVolume"):
    """List components for a deliverable with hours breakdown."""
    if not DB.loaded: DB.load()
    
    # Get included task groups for this deliverable
    try:
        # Use the database method to get task groups for deliverable
        sub = DB.all_rows[DB.all_rows["Deliverable_Code"].astype(str)==str(deliverable_code)]
        included = sorted(set(sub["task_group"].dropna().astype(str).tolist()))
    except Exception:
        included = []
    
    if not included:
        return {"items": []}
    
    scen_col = DB.scenario_hours_col(complexity, tier)
    
    # Get components list 
    comp_names = sorted(c for c in set(sub.get("Component","").astype(str)) if c and c!="nan")
    
    # Hours by component
    try:
        hours_map = DB.hours_by_component(deliverable_code, included, scen_col)
    except Exception:
        # Fallback: sum directly
        g = (sub[sub["task_group"].isin(included)]
             .groupby("Component")[scen_col].sum(numeric_only=True))
        hours_map = {k: float(v) for k, v in g.items()}
    
    return {"items": [{"name": c, "hours": float(hours_map.get(c, 0.0))} for c in comp_names]}

@app.get("/api/db/status")
def db_status():
    if not DB.loaded: DB.load()
    def ok(df): return (df is not None) and (getattr(df, "empty", True) is False)
    return {
        "loaded": DB.loaded,
        "source": DB.src,
        "has_v3": ok(DB.v3_all_rows),
        "v3_sheets": {"drivers": ok(DB.drivers_v3), "all_rows": ok(DB.v3_all_rows)}
    }

@app.post("/api/db/reload")
def db_reload():
    DB.loaded = False
    DB.load()
    return {"ok": True}

@app.post("/api/suggest_by_text")
def api_suggest(payload: SuggestPayload):
    if not DB.loaded:
        DB.load()
    recs = DB.suggest_deliverables_from_text(payload.rfp_text or "")
    # NEW: attach retainer hints
    for r in recs:
        is_ret, months = DB.retainer_recommendation(payload.rfp_text or "", r.get("deliverable",""))
        r["retainer_hint"] = bool(is_ret)
        r["retainer_months_suggested"] = int(months or 0)
    return {"suggested": recs}

@app.post("/api/suggest_by_file")
async def api_suggest_by_file(file: UploadFile = File(...)):
    if not DB.loaded:
        DB.load()

    # Read content
    content = await file.read()
    if not content or len(content) == 0:
        raise HTTPException(400, "Empty upload.")

    # Basic size guard (20 MB to match middleware)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "File too large. Maximum size is 20MB.")

    text = _extract_text_from_upload(content, file.filename)
    # Hard cap text length to protect downstream regex scan
    if len(text) > 200_000:
        text = text[:200_000]

    recs = DB.suggest_deliverables_from_text(text or "")
    # NEW: attach retainer hints per deliverable
    for r in recs:
        is_ret, months = DB.retainer_recommendation(text or "", r.get("deliverable",""))
        r["retainer_hint"] = bool(is_ret)
        r["retainer_months_suggested"] = int(months or 0)
    # NEW: remember for default project name
    global LAST_UPLOAD_FILENAME
    LAST_UPLOAD_FILENAME = file.filename
    return {"suggested": recs, "filename": file.filename}

def _resolve_scenario(spec: ScenarioSpec, category: str) -> Dict[str, Any]:
    if spec.mode == "template":
        # either use key or explicit complexity/tier
        if spec.scenario_key:
            s = DB.scenario_templates[DB.scenario_templates["Scenario_Key"]==spec.scenario_key]
            if not s.empty:
                c = str(s["Complexity"].iloc[0]); t = str(s["Tier"].iloc[0])
                return {"mode":"template","complexity":c,"tier":t,"scenario_key":spec.scenario_key}
        # fallback to provided complexity/tier
        return {"mode":"template","complexity":spec.complexity or "Advanced","tier":spec.tier or "T2_MediumVolume","scenario_key":spec.scenario_key or "CUSTOM"}
    elif spec.mode == "bundle":
        # use bundle defaults
        b = spec.bundle or "Better"
        c,t = DB.default_complexity_tier_for_bundle(b)
        return {"mode":"bundle","bundle":b,"complexity":c,"tier":t}
    else:
        raise HTTPException(400, f"Unknown scenario mode: {spec.mode}")

def _scenario_for_deliverable(deliv_code: str, category: str, spec: Dict[str, Any],
                              pricing_mode: str, blended_rate: Optional[float], rate_band: str,
                              use_slack: bool, slack_i: int, slack_c: int, slack_pct: float,
                              project_start: Optional[str], scenario_letter: str,
                              retainer_months: int = 0, selected_components: Optional[Union[List[str], Dict[str, Optional[float]]]] = None) -> Dict[str, Any]:
    # Which task groups to include?
    if spec["mode"] == "bundle":
        included = DB.included_task_groups(category, spec["bundle"])
    else:
        # Template mode: include all task_groups that exist in data for this deliverable (collapsed to unique)
        sub = DB.all_rows[DB.all_rows["Deliverable_Code"].astype(str)==str(deliv_code)]
        included = sorted(set(sub["task_group"].dropna().astype(str).tolist()))

    complexity, tier = spec["complexity"], spec["tier"]
    scen_col = DB.scenario_hours_col(complexity, tier)
    
    # Handle component-level selection (both old and new formats)
    if selected_components:
        frames = []
        
        # Handle both old format (list) and new format (dict)
        if isinstance(selected_components, list):
            # Old format: ["component1", "component2"]
            component_dict = {comp: None for comp in selected_components}  # None = use default hours
        else:
            # New format: {"component1": 5.5, "component2": None} 
            component_dict = selected_components
            
        print(f"DEBUG Component processing for {deliv_code}: {component_dict}")
        
        for comp, custom_hours in component_dict.items():
            try:
                fr = DB.hours_by_role_for_component(deliv_code, comp, included, scen_col)
                if fr is not None and not fr.empty:
                    # Apply custom hours if provided
                    if custom_hours is not None:
                        # Scale the role distribution proportionally to match custom hours
                        original_total = fr["Hours"].sum()
                        if original_total > 0:
                            scale_factor = custom_hours / original_total
                            fr = fr.copy()  # Avoid modifying original
                            fr["Hours"] = fr["Hours"] * scale_factor
                            print(f"DEBUG Scaled component '{comp}' from {original_total}h to {custom_hours}h (factor: {scale_factor:.3f})")
                    
                    frames.append(fr)
            except Exception:
                # Fallback: get data for this component directly from all_rows
                sub = DB.all_rows[
                    (DB.all_rows["Deliverable_Code"].astype(str)==str(deliv_code)) &
                    (DB.all_rows["Component"].astype(str)==str(comp)) &
                    (DB.all_rows["task_group"].isin(included))
                ]
                if not sub.empty:
                    # Group by Resource_Title, Seniority and sum hours
                    grouped = sub.groupby(["Resource_Title", "Seniority"])[scen_col].sum().reset_index()
                    grouped.columns = ["Resource_Title", "Seniority", "Hours"]
                    
                    # Apply custom hours if provided
                    if custom_hours is not None:
                        original_total = grouped["Hours"].sum()
                        if original_total > 0:
                            scale_factor = custom_hours / original_total
                            grouped["Hours"] = grouped["Hours"] * scale_factor
                            print(f"DEBUG Scaled component '{comp}' (fallback) from {original_total}h to {custom_hours}h")
                    
                    frames.append(grouped)
        
        hrs_by_role = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["Resource_Title","Seniority","Hours"])
        if not hrs_by_role.empty:
            hrs_by_role = hrs_by_role.groupby(["Resource_Title","Seniority"], as_index=False)["Hours"].sum()
    else:
        hrs_by_role = DB.hours_by_role_for_deliverable(deliv_code, included, scen_col)
    
    # ---- after total_hours is computed - RETAINER-AWARE PRICING ----
    total_hours_raw = float(hrs_by_role["Hours"].sum()) if not hrs_by_role.empty else 0.0
    
    monthly_hours_int = int(round(total_hours_raw))
    if pricing_mode == "Flat_Blended":
        eff_rate = float(blended_rate if blended_rate is not None else
                         DB.pricing_settings.loc[DB.pricing_settings["Key"]=="Default_Blended_Rate","Default"].astype(float).iloc[0])
        monthly_price_int = int(round(monthly_hours_int * eff_rate))
    else:
        price_raw = DB.per_resource_price(hrs_by_role, rate_band=rate_band or "Standard_US")
        eff_rate = round((price_raw / total_hours_raw), 2) if total_hours_raw > 0 else 0.0
        monthly_price_int = int(round(monthly_hours_int * eff_rate))

    months = max(0, int(retainer_months or 0))
    if months > 0:
        total_hours = monthly_hours_int * months
        price_int = monthly_price_int * months
    else:
        total_hours = monthly_hours_int
        price_int = monthly_price_int

    # Schedule
    schedule = DB.build_schedule(
        deliv_code, included, complexity, tier,
        use_slack, slack_i, slack_c, slack_pct, project_start,
        scenario_letter=scenario_letter
    )

    # Expose components for UI
    sub = DB.all_rows[DB.all_rows["Deliverable_Code"].astype(str)==str(deliv_code)]
    comp_names = sorted(set(sub["Component"].astype(str))) if not sub.empty else []
    comp_names = [c for c in comp_names if c and c != "nan"]
    
    try:
        comp_hours = DB.hours_by_component(deliv_code, included, scen_col)
    except Exception:
        # Fallback: calculate from raw data
        comp_hours = {}
        if not sub.empty:
            comp_sub = sub[sub["task_group"].isin(included)]
            for comp in comp_names:
                comp_data = comp_sub[comp_sub["Component"].astype(str)==str(comp)]
                comp_hours[comp] = float(comp_data[scen_col].sum()) if not comp_data.empty else 0.0
    
    return {
        "deliverable_code": deliv_code,
        "included_task_groups": included,
        "complexity": complexity,
        "tier": tier,
        "scenario_col": scen_col,
        "hours_by_role": hrs_by_role.to_dict(orient="records"),
        "total_hours": total_hours,                # total (months × monthly)
        "effective_rate": round(eff_rate, 2),
        "price": price_int,                        # total (months × monthly)
        "schedule": schedule,
        # NEW:
        "retainer": {"months": months} if months > 0 else None,
        "monthly_hours": monthly_hours_int if months > 0 else None,
        "monthly_price": monthly_price_int if months > 0 else None,
        "components": [{"name": c, "hours": float(comp_hours.get(c,0.0)), "selected": (not selected_components or c in selected_components)} for c in comp_names]
    }

@app.post("/api/build")
def api_build(payload: BuildPayload):
    if not DB.loaded:
        DB.load()

    # Prepare UI intent
    pricing_mode = payload.pricing_mode
    blended_rate = payload.blended_rate
    rate_band    = payload.rate_band or "Standard_US"

    # Slack/timeline
    use_slack = bool(payload.use_slack)
    slack_i   = int(payload.slack_after_internal)
    slack_c   = int(payload.slack_after_client)
    slack_pct = float(payload.slack_global_pct or 0)
    project_start = payload.project_start

    # Build retainer map
    ret_map = {r.deliverable_code: max(1, min(12, int(r.months))) for r in (payload.retainers or []) if str(r.deliverable_code).strip()}
    
    # Build component selection map (supports both formats)
    comp_map = {}
    for k, v in (payload.selected_components_map or {}).items():
        if isinstance(v, list):
            # Old format: ["component1", "component2"]
            comp_map[str(k)] = {str(x): None for x in v}  # None means use default hours
        elif isinstance(v, dict):
            # New format: {"component1": 5.5, "component2": 10.0}
            comp_map[str(k)] = {str(name): float(hours) for name, hours in v.items()}
        else:
            comp_map[str(k)] = {}
    
    print(f"DEBUG Build: Component map processed: {comp_map}")

    # Build scenarios
    scenarios = {}
    for letter, spec_in in [("A", payload.scenario_a), ("B", payload.scenario_b)]:
        per_deliv = []
        for code in payload.selected_deliverable_codes:
            row = DB.deliverables[DB.deliverables["Deliverable_Code"].astype(str)==str(code)]
            if row.empty: 
                print(f"DEBUG Build: No deliverable found for code '{code}'")
                continue
            
            deliverable_name = str(row["Deliverable"].iloc[0])
            cat = str(row["Category"].iloc[0])
            print(f"DEBUG Build: Code '{code}' -> Name '{deliverable_name}' (Category: {cat})")
            
            spec_resolved = _resolve_scenario(spec_in, cat)
            months = int(ret_map.get(code, 0))
            selected_components_dict = comp_map.get(str(code), {})
            out = _scenario_for_deliverable(
                code, cat, spec_resolved,
                pricing_mode, blended_rate, rate_band,
                use_slack, slack_i, slack_c, slack_pct, project_start,
                scenario_letter=letter,
                retainer_months=months,   # NEW
                selected_components=selected_components_dict  # NEW
            )
            # Add names for readability
            out["deliverable"] = deliverable_name
            out["category"]    = cat
            print(f"DEBUG Build: Added to scenario - deliverable field: '{out.get('deliverable', 'MISSING')}')")
            per_deliv.append(out)

        # Look up any previously built scenario so we can preserve a user-locked timeline
        _prev = _current_scenarios().get(letter) or {}
        locked = bool(_prev.get("manual_order_locked"))

        if locked:
            # 1) Preserve the user's order (keep intersection, append any new codes at the end)
            built_by_code = {str(it["deliverable_code"]): it for it in per_deliv}
            prev_order = [str(c) for c in (_prev.get("user_order") or [])]
            keep = [c for c in prev_order if c in built_by_code]
            tail = [c for c in built_by_code.keys() if c not in keep]
            ordered_codes = keep + tail
            per_deliv = [built_by_code[c] for c in ordered_codes]

            # 2) Carry forward the sequential schedule/dates computed by Save Order
            prev_by_code = {str(it.get("deliverable_code")): it for it in (_prev.get("items") or [])}
            for it in per_deliv:
                code = str(it["deliverable_code"])
                prev_it = prev_by_code.get(code)
                if prev_it and prev_it.get("schedule"):
                    sched = prev_it["schedule"]
                    it["schedule"] = sched
                    it["start"] = sched[0]["start_date"]
                    it["end"]   = sched[-1]["end_date"]
                    it["duration_days"] = sum(int(r["duration_days"]) for r in sched)
        else:
            # Default behavior when user hasn't locked a timeline yet
            per_deliv = _sort_deliverables(per_deliv, letter)

        # Totals after order is finalized
        price_sum = sum(int(x["price"]) for x in per_deliv)
        hours_sum = sum(int(round(x["total_hours"])) for x in per_deliv)

        # Build the scenario object
        scenario_out = {
            "pricing_mode": pricing_mode,
            "rate_band": rate_band,
            "blended_rate": blended_rate,
            "use_slack": use_slack,
            "slack_after_internal": slack_i,
            "slack_after_client": slack_c,
            "slack_global_pct": slack_pct,
            "project_start": project_start,
            "items": per_deliv,
            "totals": {"hours": int(hours_sum), "price": int(price_sum)}
        }

        # Preserve/Set order tracking flags
        if locked:
            scenario_out["ai_order"] = list(_prev.get("ai_order") or [it["deliverable_code"] for it in per_deliv])
            scenario_out["user_order"] = ordered_codes
            scenario_out["manual_order_locked"] = True
        else:
            scenario_out["ai_order"] = [it["deliverable_code"] for it in per_deliv]
            scenario_out["user_order"] = list(scenario_out["ai_order"])
            scenario_out["manual_order_locked"] = False

        scenarios[letter] = scenario_out

    # Store scenarios globally for reordering
    global _CURRENT_SCENARIOS
    _CURRENT_SCENARIOS.update(scenarios)
    
    return scenarios

@app.post("/api/build_scenario_c")
def api_build_scenario_c(payload: BuildScenarioCPayload):
    if not DB.loaded:
        DB.load()

    # 1) Fetch the base scenario (A or B) from current scenarios store
    base_letter = payload.base.upper()
    base = _current_scenarios().get(base_letter)
    if not base:
        raise HTTPException(status_code=400, detail=f"Base scenario {base_letter} not found. Please build scenarios A and B first.")

    # 2) Union of deliverable codes (base codes + add-on codes)
    base_codes = [item["deliverable_code"] for item in (base.get("items") or [])]
    # Use dict.fromkeys to maintain order and remove duplicates
    union_codes = list(dict.fromkeys(base_codes + payload.add_on_codes))
    
    # Filter out any unknown codes
    valid_codes = []
    for code in union_codes:
        if not DB.deliverables[DB.deliverables["Deliverable_Code"].astype(str)==str(code)].empty:
            valid_codes.append(code)
    
    # 3) Inherit parameters from base unless explicitly provided
    complexity = payload.complexity or base.get("complexity", "Advanced")
    tier = payload.tier or base.get("tier", "T2_MediumVolume")
    use_slack = base.get("use_slack", True) if payload.use_slack is None else payload.use_slack
    slack_i = base.get("slack_after_internal", 1) if payload.slack_after_internal is None else payload.slack_after_internal
    slack_c = base.get("slack_after_client", 2) if payload.slack_after_client is None else payload.slack_after_client
    slack_pct = base.get("slack_global_pct", 0.05) if payload.slack_global_pct is None else payload.slack_global_pct
    project_start = payload.project_start or base.get("project_start")
    
    # Build inheritance map from base unless overridden
    base_ret_map = {}
    for it in (base.get("items") or []):
        if it.get("retainer", {}) and int(it["retainer"].get("months", 0)) > 0:
            base_ret_map[it["deliverable_code"]] = int(it["retainer"]["months"])
    override_map = {r.deliverable_code: max(1, min(12, int(r.months))) for r in (payload.retainers or [])}
    ret_map = {**base_ret_map, **override_map}

    # 4) Build scenario items using existing logic (same as /api/build)
    per_deliv = []
    for code in valid_codes:
        row = DB.deliverables[DB.deliverables["Deliverable_Code"].astype(str)==str(code)]
        if row.empty:
            continue
        cat = str(row["Category"].iloc[0])
        
        # Create scenario spec for this deliverable
        spec_resolved = {"mode": "template", "complexity": complexity, "tier": tier}
        
        months = int(ret_map.get(code, 0))
        # For Scenario C, no component selection yet - use default
        out = _scenario_for_deliverable(
            code, cat, spec_resolved,
            payload.pricing_mode, payload.blended_rate, payload.rate_band,
            use_slack, slack_i, slack_c, slack_pct, project_start,
            scenario_letter="C",
            retainer_months=months,   # NEW
            selected_components=None  # No component selection for Scenario C yet
        )
        # Add names for readability
        out["deliverable"] = str(row["Deliverable"].iloc[0])
        out["category"] = cat
        per_deliv.append(out)

    # Sort deliverables by phase order
    per_deliv = _sort_deliverables(per_deliv, "C")
    price_sum = sum(int(x["price"]) for x in per_deliv)
    hours_sum = sum(int(round(x["total_hours"])) for x in per_deliv)

    # 5) Create Scenario C
    scenario_c = {
        "label": "Scenario C (Upsell)",
        "pricing_mode": payload.pricing_mode,
        "rate_band": payload.rate_band,
        "blended_rate": payload.blended_rate,
        "complexity": complexity,
        "tier": tier,
        "use_slack": use_slack,
        "slack_after_internal": slack_i,
        "slack_after_client": slack_c,
        "slack_global_pct": slack_pct,
        "project_start": project_start,
        "items": per_deliv,
        "totals": {"hours": int(hours_sum), "price": int(price_sum)}
    }

    # 6) Store/update in memory next to A/B for this session
    global _CURRENT_SCENARIOS
    _CURRENT_SCENARIOS["C"] = scenario_c
    
    return {"C": scenario_c}

@app.post("/api/auto_build")
def api_auto_build(payload: AutoBuildPayload):
    if not DB.loaded:
        DB.load()

    # 1) Get AI suggestions
    suggestions = DB.suggest_deliverables_from_text(payload.rfp_text or "")
    selected_codes = [s["deliverable_code"] for s in suggestions]

    # Build retainer map
    ret_map = {r.deliverable_code: max(1, min(12, int(r.months))) for r in (payload.retainers or []) if str(r.deliverable_code).strip()}

    # 2) If nothing matched, return an empty set so frontend can prompt to add
    if not selected_codes:
        return {
            "suggested": suggestions,
            "scenarios": {
                "A": {"items": [], "totals": {"hours": 0.0, "price": 0.0}},
                "B": {"items": [], "totals": {"hours": 0.0, "price": 0.0}},
            }
        }

    # 3) Reuse the same logic as /api/build to assemble scenarios
    #    (We inline the essential parts to keep it simple.)
    def _build_for(selected_deliverable_codes, scen_spec):
        per_deliv = []
        price_sum = 0.0
        hours_sum = 0.0
        for code in selected_deliverable_codes:
            row = DB.deliverables[DB.deliverables["Deliverable_Code"].astype(str) == str(code)]
            if row.empty:
                continue
            cat = str(row["Category"].iloc[0])
            spec_resolved = _resolve_scenario(scen_spec, cat)
            months = int(ret_map.get(code, 0))
            out = _scenario_for_deliverable(
                code, cat, spec_resolved,
                payload.pricing_mode, payload.blended_rate, payload.rate_band or "Standard_US",
                bool(payload.use_slack), int(payload.slack_after_internal), int(payload.slack_after_client),
                float(payload.slack_global_pct or 0), payload.project_start,
                scenario_letter="A",  # letter doesn't affect numbers; acceptable here
                retainer_months=months  # NEW
            )
            out["deliverable"] = str(row["Deliverable"].iloc[0])
            out["category"] = cat
            per_deliv.append(out)
            price_sum += out["price"]
            hours_sum += out["total_hours"]
        return {
            "pricing_mode": payload.pricing_mode,
            "rate_band": payload.rate_band or "Standard_US",
            "blended_rate": payload.blended_rate,
            "use_slack": bool(payload.use_slack),
            "slack_after_internal": int(payload.slack_after_internal),
            "slack_after_client": int(payload.slack_after_client),
            "slack_global_pct": float(payload.slack_global_pct or 0),
            "project_start": payload.project_start,
            "items": per_deliv,
            "totals": {"hours": round(hours_sum, 2), "price": round(price_sum, 2)}
        }

    scenarios = {
        "A": _build_for(selected_codes, payload.scenario_a),
        "B": _build_for(selected_codes, payload.scenario_b),
    }

    return {"suggested": suggestions, "scenarios": scenarios}

@app.post("/api/export")
def api_export(payload: ExportPayload):
    """
    Export a Workfront file (CSV or XLSX) from a single scenario payload.
    The 'Project_Name' column is set to payload.project_name if provided.
    The download filename is derived from project/scenario.
    """
    if not DB.loaded:
        DB.load()

    project_name = (payload.project_name
                    or _upload_title_default()
                    or f"Proposal {datetime.date.today().isoformat()}")

    df = build_wbs_dataframe_from_scenario(payload.scenario or {}, project_name)
    # <<< force A–E to the left and guarantee presence
    df = _ensure_v3_ae_columns(df)

    base = _export_basename(project_name, payload.scenario_label)  # always adds EST timestamp

    fmt = (payload.file_format or "csv").lower()
    if fmt == "csv":
        out_path = f"{base}.csv"
        df.to_csv(out_path, index=False)
        return FileResponse(out_path, filename=os.path.basename(out_path), media_type="text/csv")

    # xlsx
    try:
        out_path = f"{base}.xlsx"
        with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
            df.to_excel(xw, index=False)
            _apply_number_formats(xw.sheets[list(xw.sheets.keys())[0]], df)
        return FileResponse(
            out_path, filename=os.path.basename(out_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as ex:
        raise HTTPException(400, "XLSX export requires 'openpyxl'.") from ex

@app.post("/api/export_workbook")
def api_export_workbook(payload: ExportWorkbookPayload):
    if not DB.loaded:
        DB.load()
    project = (payload.project_name
               or _upload_title_default()
               or f"Proposal {datetime.date.today().isoformat()}").strip()
    dfA = build_wbs_dataframe_from_scenario(payload.scenario_a or {}, project)
    dfB = build_wbs_dataframe_from_scenario(payload.scenario_b or {}, project)
    
    dfA = _ensure_v3_ae_columns(dfA)
    dfB = _ensure_v3_ae_columns(dfB)
    base = _export_basename(project, "Scenarios A & B")  # includes EST timestamp
    out_path = f"{base}.xlsx"
    # Always use stable, distinct tab names to prevent accidental overwrite
    sheetA = "Scenario A"
    sheetB = "Scenario B"
    with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
        dfA.to_excel(xw, sheet_name=sheetA, index=False)
        dfB.to_excel(xw, sheet_name=sheetB, index=False)
        _apply_number_formats(xw.sheets[sheetA], dfA)
        _apply_number_formats(xw.sheets[sheetB], dfB)
    return FileResponse(
        out_path, filename=os.path.basename(out_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.post("/api/export_workbook_abc")
def api_export_workbook_abc(payload: ExportWorkbookABCPayload):
    """Export scenarios A, B, and C to a single Excel file with separate sheets."""
    if not DB.loaded:
        DB.load()
    
    project = (payload.project_name
               or _upload_title_default()
               or f"Proposal {datetime.date.today().isoformat()}").strip()
    
    # Build DataFrames for all three scenarios
    dfA = build_wbs_dataframe_from_scenario(payload.scenario_a or {}, project)
    dfB = build_wbs_dataframe_from_scenario(payload.scenario_b or {}, project)
    dfC = build_wbs_dataframe_from_scenario(payload.scenario_c or {}, project)
    
    # Ensure consistent column formatting
    dfA = _ensure_v3_ae_columns(dfA)
    dfB = _ensure_v3_ae_columns(dfB)
    dfC = _ensure_v3_ae_columns(dfC)
    
    # Generate filename with EST timestamp
    base = _export_basename(project, "Scenarios A, B & C")  # includes EST timestamp
    out_path = f"{base}.xlsx"
    
    # Create Excel file with three sheets
    with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
        dfA.to_excel(xw, sheet_name=payload.sheet_name_a or "Scenario A", index=False)
        dfB.to_excel(xw, sheet_name=payload.sheet_name_b or "Scenario B", index=False)
        dfC.to_excel(xw, sheet_name=payload.sheet_name_c or "Scenario C", index=False)
        
        # Apply number formatting to all sheets
        _apply_number_formats(xw.sheets[payload.sheet_name_a or "Scenario A"], dfA)
        _apply_number_formats(xw.sheets[payload.sheet_name_b or "Scenario B"], dfB)
        _apply_number_formats(xw.sheets[payload.sheet_name_c or "Scenario C"], dfC)
    
    return FileResponse(
        out_path, filename=os.path.basename(out_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def _assert_has_items(scen: dict, label: str):
    """Guard to ensure scenario has items before export"""
    if not scen or not scen.get("items"):
        raise HTTPException(400, f"No build context for {label}. Run Build once in Step 3.")

@app.post("/api/export_xml")
def api_export_xml(payload: ExportXMLPayload):
    """
    Export a single scenario as Microsoft Project XML (MSPDI) format.
    Uses the convert_excel_to_mspdi function with multi-resource merge capability.
    """
    if not DB.loaded:
        DB.load()

    project_name = (payload.project_name
                    or _upload_title_default()
                    or f"Proposal {datetime.date.today().isoformat()}")

    # Guard: ensure scenario has items
    _assert_has_items(payload.scenario or {}, "XML export")
    
    # Build WBS DataFrame
    df = build_wbs_dataframe_from_scenario(payload.scenario or {}, project_name)
    df = _ensure_v3_ae_columns(df)

    # Create temporary Excel file for MSPDI conversion
    base = _export_basename(project_name, payload.scenario_label or "Scenario")
    temp_xlsx = f"{base}_temp.xlsx"
    output_xml = f"{base}.xml"
    
    try:
        # Write to temporary Excel file
        with pd.ExcelWriter(temp_xlsx, engine="openpyxl") as xw:
            df.to_excel(xw, sheet_name=payload.sheet_name, index=False)
            _apply_number_formats(xw.sheets[payload.sheet_name], df)

        # Convert to MSPDI XML
        stats = convert_excel_to_mspdi(
            input_xlsx=temp_xlsx,
            output_xml=output_xml,
            sheet_name=payload.sheet_name,
            start_date_mode=payload.start_date_mode,
            fixed_start_iso=payload.fixed_start_iso,
            hours_per_day=payload.hours_per_day,
            merge_identical_children=False,
            project_name=project_name
        )

        return FileResponse(
            output_xml,
            filename=os.path.basename(output_xml),
            media_type="application/xml",
            headers={"X-Export-Stats": json.dumps(stats)}
        )

    finally:
        # Clean up temporary Excel file
        if os.path.exists(temp_xlsx):
            os.remove(temp_xlsx)

@app.post("/api/export_workbook_xml")
def api_export_workbook_xml(payload: ExportWorkbookXMLPayload):
    """
    Export scenarios A and B to separate XML files in a zip archive.
    Each XML uses the convert_excel_to_mspdi function with multi-resource merge.
    """
    if not DB.loaded:
        DB.load()
    
    project = (payload.project_name
               or _upload_title_default()
               or f"Proposal {datetime.date.today().isoformat()}").strip()
    
    # Guard: ensure scenarios have items
    _assert_has_items(payload.scenario_a or {}, "Scenario A XML export")
    _assert_has_items(payload.scenario_b or {}, "Scenario B XML export")
    
    # Build DataFrames
    dfA = build_wbs_dataframe_from_scenario(payload.scenario_a or {}, project)
    dfB = build_wbs_dataframe_from_scenario(payload.scenario_b or {}, project)
    
    dfA = _ensure_v3_ae_columns(dfA)
    dfB = _ensure_v3_ae_columns(dfB)
    
    base = _export_basename(project, "Scenarios A & B XML")
    temp_files = []
    
    try:
        # Create XML for Scenario A
        temp_xlsx_a = f"{base}_A_temp.xlsx"
        output_xml_a = f"{base}_Scenario_A.xml"
        temp_files.extend([temp_xlsx_a, output_xml_a])
        
        with pd.ExcelWriter(temp_xlsx_a, engine="openpyxl") as xw:
            dfA.to_excel(xw, sheet_name="Scenario A", index=False)
            _apply_number_formats(xw.sheets["Scenario A"], dfA)
        
        stats_a = convert_excel_to_mspdi(
            input_xlsx=temp_xlsx_a,
            output_xml=output_xml_a,
            sheet_name="Scenario A",
            merge_identical_children=False,
            project_name=project
        )
        
        # Create XML for Scenario B
        temp_xlsx_b = f"{base}_B_temp.xlsx"
        output_xml_b = f"{base}_Scenario_B.xml"
        temp_files.extend([temp_xlsx_b, output_xml_b])
        
        with pd.ExcelWriter(temp_xlsx_b, engine="openpyxl") as xw:
            dfB.to_excel(xw, sheet_name="Scenario B", index=False)
            _apply_number_formats(xw.sheets["Scenario B"], dfB)
        
        stats_b = convert_excel_to_mspdi(
            input_xlsx=temp_xlsx_b,
            output_xml=output_xml_b,
            sheet_name="Scenario B",
            merge_identical_children=False,
            project_name=project
        )
        
        # Create zip file with both XMLs
        import zipfile
        zip_path = f"{base}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(output_xml_a, f"Scenario_A.xml")
            zipf.write(output_xml_b, f"Scenario_B.xml")
            # Add stats as JSON file
            stats_json = json.dumps({
                "scenario_a": stats_a,
                "scenario_b": stats_b
            }, indent=2)
            zipf.writestr("export_stats.json", stats_json)
        
        return FileResponse(
            zip_path,
            filename=os.path.basename(zip_path),
            media_type="application/zip"
        )
        
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

@app.post("/api/audit_pricing")
def api_audit_pricing(p: AuditPricingPayload):
    if not DB.loaded:
        DB.load()

    items = p.scenario.get("items", [])
    m = _band_multiplier(p.rate_band)
    deliverables = []
    tot_expected = 0.0
    tot_shown = 0.0
    warnings = []

    for d in items:
        # hours by role from scenario
        hrs = pd.DataFrame(d.get("hours_by_role", []))
        if hrs.empty:
            hrs = pd.DataFrame(columns=["Resource_Title","Seniority","Hours"]).assign(Hours=0.0)
        total_raw = float(hrs["Hours"].sum())

        # decide billable hours basis
        billable_total = round(total_raw) if p.price_uses_rounded_hours else total_raw
        scale = (billable_total / total_raw) if total_raw > 0 else 0.0
        hrs_bill = hrs.copy()
        hrs_bill["Hours"] = hrs_bill["Hours"] * scale

        if p.pricing_mode == "Flat_Blended":
            # default blended rate if omitted
            if p.blended_rate is None:
                ps = DB.pricing_settings[DB.pricing_settings["Key"]=="Default_Blended_Rate"]
                p.blended_rate = float(ps["Default"].iloc[0]) if not ps.empty else 185.0
            expected = billable_total * float(p.blended_rate)
            missing_roles = []
        else:
            # per-resource: join to rate card
            rc = DB.role_rate_card[["Resource_Title","Seniority","Rate_USD"]].copy()
            merged = hrs_bill.merge(rc, on=["Resource_Title","Seniority"], how="left")
            miss = merged[merged["Rate_USD"].isna()][["Resource_Title","Seniority"]].drop_duplicates()
            missing_roles = miss.to_dict(orient="records")
            merged["Rate_USD"] = merged["Rate_USD"].fillna(0.0)
            merged["Cost"] = merged["Hours"] * merged["Rate_USD"] * m
            expected = float(merged["Cost"].sum())
            if missing_roles:
                warnings.append({
                    "deliverable": d.get("deliverable"),
                    "missing_rate_roles": missing_roles
                })

        shown = float(d.get("price", 0.0))
        diff = round(expected - shown, 2)
        deliverables.append({
            "deliverable": d.get("deliverable"),
            "hours_raw": round(total_raw, 2),
            "hours_billed": round(billable_total, 2),
            "expected_price": round(expected, 2),
            "shown_price": round(shown, 2),
            "delta": diff,
        })
        tot_expected += expected
        tot_shown += shown

    scenario_delta = round(tot_expected - tot_shown, 2)
    return {
        "pricing_mode": p.pricing_mode,
        "rate_band": p.rate_band,
        "blended_rate": p.blended_rate,
        "uses_rounded_hours_for_pricing": bool(p.price_uses_rounded_hours),
        "deliverables": deliverables,
        "totals": {
            "expected": round(tot_expected, 2),
            "shown": round(tot_shown, 2),
            "delta": scenario_delta
        },
        "ok": abs(scenario_delta) < 0.01 and not warnings,
        "warnings": warnings
    }

@app.post("/api/summarize", response_model=RfpSummary)
def api_summarize(p: SummarizePayload):
    if not p.rfp_text:
        raise HTTPException(400, "rfp_text is required for /api/summarize (use /api/summarize_by_file for uploads).")
    return ai_summarize_rfp_text(p.rfp_text)

@app.post("/api/summarize_by_file", response_model=RfpSummary)
async def api_summarize_by_file(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty upload.")
    text = _extract_text_from_upload(content, file.filename)   # reuses existing extractor
    # Hard cap already present in /api/suggest_by_file; can reapply if desired
    if len(text) > 200_000:
        text = text[:200_000]
    # NEW: remember for default project name
    global LAST_UPLOAD_FILENAME
    LAST_UPLOAD_FILENAME = file.filename
    return ai_summarize_rfp_text(text)

@app.post("/api/retainer_detect")
def api_retainer_detect(p: dict):
    """Detect retainer opportunities for given deliverables."""
    if not DB.loaded:
        DB.load()
    
    rfp_text = str(p.get("rfp_text", "") or "")
    deliverable_codes = [str(x) for x in (p.get("deliverable_codes", []) or [])]
    
    # Fallback: use codes from the last built A scenario if none provided
    if not deliverable_codes:
        scen = _current_scenarios().get("A") or {}
        deliverable_codes = [str(it.get("deliverable_code")) for it in (scen.get("items") or []) if it.get("deliverable_code")]
        
    if not deliverable_codes:
        return {"retainers": []}
    
    # Get deliverable names from codes
    db_delivs = DB.deliverables[["Deliverable_Code", "Deliverable"]].copy()
    db_delivs["Deliverable_Code"] = db_delivs["Deliverable_Code"].astype(str)
    code_to_name = {r["Deliverable_Code"]: r["Deliverable"] for _, r in db_delivs.iterrows()}
    
    retainers = []
    for code in deliverable_codes:
        deliv_name = code_to_name.get(code, "")
        if deliv_name:
            is_retainer, months = DB.retainer_recommendation(rfp_text, deliv_name)
            if is_retainer:
                retainers.append({
                    "deliverable_code": code,
                    "deliverable_name": deliv_name,
                    "suggested_months": int(months or 6),
                    "confidence": "high" if months and months >= 6 else "medium"
                })
    
    return {"retainers": retainers}

@app.post("/api/reconcile", response_model=ReconcileResult)
def api_reconcile(p: ReconcilePayload):
    if not DB.loaded:
        DB.load()

    try:
        # Normalize inputs
        ai_labels: List[str] = [str(x).strip() for x in (p.summary_deliverables or []) if str(x).strip()]
        if not ai_labels:
            # Nothing to reconcile
            return ReconcileResult(add=[], delete=[], unchanged=[])

        sel_codes: List[str] = [str(x) for x in (p.db_selected_deliverable_codes or [])]

        # DB deliverables map
        db_all = DB.deliverables[["Deliverable_Code", "Deliverable"]].copy()
        db_all["Deliverable_Code"] = db_all["Deliverable_Code"].astype(str)
        db_all["Deliverable"] = db_all["Deliverable"].astype(str)

        # Selected map (left panel)
        db_sel = db_all[db_all["Deliverable_Code"].isin(sel_codes)]
        code_to_name = {r["Deliverable_Code"]: r["Deliverable"] for _, r in db_sel.iterrows()}

        # Precompute tokens for speed
        ai_tok = [(lab, _norm_tokens(lab)) for lab in ai_labels]
        db_tok = [(r["Deliverable_Code"], r["Deliverable"], _norm_tokens(r["Deliverable"])) for _, r in db_all.iterrows()]

        ADD_THRESHOLD = 0.35     # how close an AI label must be to a DB deliverable to recommend ADD (lowered from 0.45)
        DELETE_THRESHOLD = 0.25  # if no AI label is at least this close, recommend DELETE

        add: List[ReconcileSuggestion] = []
        unchanged: List[str] = []
        delete: List[ReconcileSuggestion] = []

        # --- ADD & UNCHANGED ---
        # For each AI label, find the best matching DB deliverable by token Jaccard
        for lab, lab_tok in ai_tok:
            best_code = None
            best_name = ""
            best_score = 0.0
            for code, name, name_tok in db_tok:
                s = _jaccard(lab_tok, name_tok)
                if s > best_score:
                    best_code, best_name, best_score = code, name, s

            if not best_code:
                continue

            if best_code in sel_codes:
                # Already selected -> unchanged (count it if reasonably close)
                if best_score >= DELETE_THRESHOLD:
                    unchanged.append(best_name)
            else:
                # Not selected yet -> recommend ADD if strong enough
                if best_score >= 0.35:
                    add.append(ReconcileSuggestion(
                        code=best_code, label=best_name,
                        reason=f"Matches AI summary item \"{lab}\" (score {best_score:.2f}).",
                        preselect=True
                    ))

        # --- DELETE ---
        # Safe delete block - prevents DataFrame errors with unequal column lengths
        ai_labels = [str(x) for x in (p.summary_deliverables or []) if str(x).strip()]
        for code in sel_codes:
            name = code_to_name.get(code, code)
            name_tokens = _norm_tokens(name)
            max_score = 0.0
            for lbl in ai_labels:
                max_score = max(max_score, _jaccard(name_tokens, _norm_tokens(lbl)))
            if max_score < 0.25:
                delete.append(ReconcileSuggestion(
                    code=code, label=name, reason="Not found in AI Summary.", preselect=True
                ))

        # Deduplicate unchanged list & sort
        unchanged = sorted(set(unchanged))

        # Add the actual selection the server used
        db_used_labels = [code_to_name.get(c, c) for c in sel_codes]

        return ReconcileResult(
            add=add, delete=delete, unchanged=unchanged,
            db_used_codes=sel_codes, db_used_labels=db_used_labels
        )

    except Exception as ex:
        # Return a clear 400 instead of a 500 so the UI can show a friendly message
        raise HTTPException(status_code=400, detail=f"Reconciliation error: {ex}")

@app.post("/api/reorder_timeline")
def api_reorder_timeline(p: ReorderPayload):
    if not DB.loaded:
        DB.load()

    letter = (p.scenario_letter or "A").upper()
    scen = _current_scenarios().get(letter)
    if not scen:
        raise HTTPException(400, f"Scenario {letter} not built")

    # Get current items and create mapping by deliverable code
    current_items = list(scen.get("items") or [])
    by_code = {str(it.get("deliverable_code") or it.get("code")): it for it in current_items}
    want = [str(c) for c in p.deliverable_codes]

    # Build new schedules in the requested order, sequentially
    reordered_items: list[dict] = []
    cursor_date = None  # None -> use project_start for first

    for code in want:
        # Get existing item for metadata
        existing_item = by_code.get(code)
        if not existing_item:
            continue

        # included task groups (from client), else derive all TGs present for that deliverable
        included = (p.included_map or {}).get(code)
        if not included:
            sub = DB.all_rows[DB.all_rows["Deliverable_Code"].astype(str) == str(code)]
            included = sorted(set(sub["task_group"].dropna().astype(str).tolist()))

        # sequential packing: first item uses project_start, others start the day after previous end
        start = p.project_start
        if cursor_date is not None:
            start = str(cursor_date)

        sched = DB.build_schedule(
            deliverable_code=code,
            included_task_groups=included,
            complexity=p.complexity or existing_item.get("complexity"), 
            tier=p.tier or existing_item.get("tier"),
            use_slack=p.use_slack,
            slack_after_internal=p.slack_after_internal,
            slack_after_client=p.slack_after_client,
            slack_global_pct=p.slack_global_pct,
            project_start=start,
            scenario_letter=letter
        )

        # Update existing item with new schedule
        updated_item = existing_item.copy()
        updated_item["schedule"] = sched
        reordered_items.append(updated_item)

        # advance cursor to the day after this deliverable's last end date
        if sched:
            last_end = sched[-1]["end_date"]
            y, m, d = map(int, last_end.split("-"))
            cursor_date = datetime.date(y, m, d) + datetime.timedelta(days=1)

    # Update scenario with new order and persist
    scen["items"] = reordered_items
    if reordered_items:
        scen["timeline"] = {
            "start": reordered_items[0]["schedule"][0]["start_date"] if reordered_items[0].get("schedule") else None,
            "end": reordered_items[-1]["schedule"][-1]["end_date"] if reordered_items[-1].get("schedule") else None,
        }
    scen["user_order"] = want
    scen["ai_order"] = scen.get("ai_order") or list(want)
    scen["manual_order_locked"] = True
    _CURRENT_SCENARIOS[letter] = scen  # persist

    # Return items for frontend and full scenario for persistence
    return {"items": [{"deliverable_code": d["deliverable_code"], "deliverable": d.get("deliverable"), "schedule": d["schedule"]} for d in reordered_items],
            "scenario": scen}


# ---------- MSPDI Export Function ----------
def convert_excel_to_mspdi(
    input_xlsx: str,
    output_xml: str,
    sheet_name: str = "Scenario A",
    start_date_mode: str = "next_monday",
    fixed_start_iso: Optional[str] = None,
    hours_per_day: float = 8.0,
    calendar_blocks: List[Tuple[str, str]] = [("08:00:00","12:00:00"), ("13:00:00","17:00:00")],
    roles_split_rule: str = "even",
    role_weights: Optional[Dict[str, float]] = None,
    preserve_predecessors: str = "normalize",
    allow_unassigned: bool = True,
    include_audits: bool = True,
    audits_dir: Optional[str] = None,
    merge_identical_children: bool = False,   # <— toggle for multi-resource merge
    project_name: Optional[str] = None,
    round_to_whole_days: bool = False  # <— toggle for whole-day duration rounding
) -> Dict[str, int]:
    """
    Convert Excel WBS data to Microsoft Project XML (MSPDI) format with multi-resource merge capability.
    
    Returns a dictionary with statistics about the conversion process.
    """
    try:
        # Load Excel data
        df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
        
        # Convert DataFrame to list of row dictionaries for processing
        rows = []
        for _, row in df.iterrows():
            # Extract basic task information with NaN handling
            def safe_int(value, default=0):
                """Convert value to int, handling NaN and None."""
                if pd.isna(value) or value is None:
                    return default
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    return default
            
            def safe_float(value, default=0.0):
                """Convert value to float, handling NaN and None."""
                if pd.isna(value) or value is None:
                    return default
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default
                    
            # Clean up task name and role
            task_name = str(row.get("Task_Name", ""))
            if not task_name or task_name.lower() in ['nan', 'none', '']:
                task_name = "Unnamed Task"
                
            role = str(row.get("Role", "Unassigned"))
            if not role or role.lower() in ['nan', 'none', '']:
                role = "Unassigned"
                
            task_row = {
                "WBS": str(row.get("WBS_ID", "")),
                "ParentWBS": str(row.get("Parent_WBS_ID", "")),
                "Name": task_name,
                "PlannedHours": safe_float(row.get("Planned_Hours"), 0),
                "StartOffset": safe_int(row.get("Start_Offset_Days"), 0),
                "Duration": safe_int(row.get("Duration_Days"), 1),
                "Dependencies": str(row.get("Dependencies", "")),
                "RoleList": [role],
                "RoleStr": role,
                "UID": 0  # Will be assigned later
            }
            rows.append(task_row)
        
        # Assign UIDs
        for i, row in enumerate(rows, 1):
            row["UID"] = i
        
        # --- NEW: merge siblings with the same name into their parent as multi-assignments
        prealloc_by_parent_wbs: Dict[str, Dict[str, float]] = {}
        removed_child_wbs: Set[str] = set()

        if merge_identical_children:
            # index helpers
            by_wbs = {r["WBS"]: r for r in rows if r.get("WBS")}
            kids_by_parent: Dict[str, List[str]] = {}
            for r in rows:
                p = r.get("ParentWBS")
                if p:
                    kids_by_parent.setdefault(p, []).append(r["WBS"])

            for parent_wbs, kid_wbs_list in list(kids_by_parent.items()):
                # Only immediate children and all must be leaves
                kid_rows = [by_wbs[k] for k in kid_wbs_list if k in by_wbs]
                if not kid_rows:
                    continue
                # skip if any child itself has children (not a leaf)
                if any(k in kids_by_parent for k in kid_wbs_list):
                    continue

                parent = by_wbs.get(parent_wbs)
                if not parent:
                    continue

                # Heuristic:
                # - every child has same Name as parent
                # - each child has exactly ONE role
                # - each child has >0 planned hours
                same_name = all(kr["Name"] == parent["Name"] for kr in kid_rows)
                one_role  = all(len(kr["RoleList"]) == 1 for kr in kid_rows)
                has_hours = all((kr["PlannedHours"] or 0) > 0 for kr in kid_rows)
                if not (same_name and one_role and has_hours):
                    continue

                # Aggregate hours by role
                agg: Dict[str, float] = {}
                for kr in kid_rows:
                    role = kr["RoleList"][0]
                    agg[role] = agg.get(role, 0.0) + float(kr["PlannedHours"])

                if len(agg) < 2:
                    continue

                # Record prealloc for the parent
                prealloc_by_parent_wbs[parent_wbs] = agg

                # Make the parent a single multi-role leaf
                parent["RoleList"] = list(agg.keys())
                parent["RoleStr"]  = ",".join(parent["RoleList"])
                if (parent.get("PlannedHours") or 0) <= 0:
                    parent["PlannedHours"] = sum(agg.values())

                # Remove the children
                removed_child_wbs.update(kid_wbs_list)

        # If we merged anything, drop the children now
        if removed_child_wbs:
            rows = [r for r in rows if r["WBS"] not in removed_child_wbs]

        # Build a universal WBS index (needed even when merge is OFF)
        by_wbs = {r["WBS"]: r for r in rows if r.get("WBS")}

        # Build children_by_parent map and child_to_parent for dep rewrites
        children_by_parent: Dict[str, List[str]] = {}
        for r in rows:
            p = r["ParentWBS"]
            if p:
                children_by_parent.setdefault(p, []).append(r["WBS"])
        summary_set: Set[str] = set(children_by_parent.keys())

        child_to_parent: Dict[str, str] = {}
        for p, kids in children_by_parent.items():
            for k in kids:
                if k in removed_child_wbs:   # only those removed pre-merge
                    child_to_parent[k] = p

        # Helper functions for dependency normalization
        def is_ancestor(ancestor_wbs: str, descendant_wbs: str) -> bool:
            current = descendant_wbs
            visited = set()
            while current and current not in visited:
                visited.add(current)
                if current == ancestor_wbs:
                    return True
                # Find parent of current
                parent_found = None
                for r in rows:
                    if r["WBS"] == current:
                        parent_found = r.get("ParentWBS")
                        break
                current = parent_found
            return False

        def list_leaves_under(parent_wbs: str) -> List[str]:
            leaves = []
            for r in rows:
                if r.get("ParentWBS") == parent_wbs and r["WBS"] not in summary_set:
                    leaves.append(r["WBS"])
            return leaves

        def first_leaf(wbs: str) -> str:
            if wbs in summary_set:
                children = children_by_parent.get(wbs, [])
                if children:
                    return first_leaf(children[0])
            return wbs

        def last_leaf(wbs: str) -> str:
            if wbs in summary_set:
                children = children_by_parent.get(wbs, [])
                if children:
                    return last_leaf(children[-1])
            return wbs

        # Normalize dependencies & drop unsafe hierarchy edges
        init_edges = []
        for r in rows:
            deps = r.get("Dependencies", "").strip()
            if deps:
                for dep in deps.split(","):
                    dep = dep.strip()
                    if dep:
                        init_edges.append((dep, r["WBS"]))

        normalized_edges = []
        for pred_wbs, succ_wbs in init_edges:
            # Rewrite removed children to their parents
            actual_pred = child_to_parent.get(pred_wbs, pred_wbs)
            actual_succ = child_to_parent.get(succ_wbs, succ_wbs)
            
            # Skip if either doesn't exist after merge
            if actual_pred not in by_wbs or actual_succ not in by_wbs:
                continue
                
            # Skip hierarchy edges (ancestor -> descendant)
            if is_ancestor(actual_pred, actual_succ) or is_ancestor(actual_succ, actual_pred):
                continue
                
            # Convert summary tasks to their representative leaves
            if actual_pred in summary_set:
                actual_pred = last_leaf(actual_pred)
            if actual_succ in summary_set:
                actual_succ = first_leaf(actual_succ)
                
            if actual_pred != actual_succ:
                normalized_edges.append((actual_pred, actual_succ))

        # Calculate project start date
        if fixed_start_iso:
            project_start = datetime.datetime.fromisoformat(fixed_start_iso.replace('Z', '+00:00'))
        elif start_date_mode == "next_monday":
            today = datetime.date.today()
            days_ahead = 0 - today.weekday()  # Monday is 0
            if days_ahead <= 0:
                days_ahead += 7
            project_start = datetime.datetime.combine(today + datetime.timedelta(days=days_ahead), datetime.time(9, 0))
        elif start_date_mode == "fixed":
            # Use current date with business hours start if no fixed_start_iso provided
            project_start = datetime.datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        else:
            project_start = datetime.datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

        # Business calendar helpers (using same Mon-Fri, 8-12 & 13-17 schedule)
        from datetime import time, date
        
        BUS_BLOCKS = [(time(8,0), time(12,0)), (time(13,0), time(17,0))]

        def is_business_day(d):
            return d.weekday() < 5  # Mon–Fri

        def business_minutes_in_range(day: date, start_t: time, end_t: time) -> int:
            # minutes worked on a single day between start_t and end_t
            if not is_business_day(day): 
                return 0
            start_t = max(start_t, BUS_BLOCKS[0][0])
            end_t   = min(end_t,   BUS_BLOCKS[-1][1])
            if end_t <= start_t:
                return 0
            total = 0
            for a,b in BUS_BLOCKS:
                s = max(start_t, a)
                e = min(end_t,   b)
                if e > s:
                    total += int((datetime.datetime.combine(day,e) - datetime.datetime.combine(day,s)).total_seconds() // 60)
            return total

        def business_minutes_between(start_dt: datetime.datetime, end_dt: datetime.datetime) -> int:
            if end_dt <= start_dt:
                return 0
            cur = start_dt.date()
            end = end_dt.date()
            minutes = 0
            # first day (partial)
            minutes += business_minutes_in_range(cur, start_dt.time(), time(17,0))
            # middle full days
            d = cur + datetime.timedelta(days=1)
            while d < end:
                if is_business_day(d):
                    minutes += 480  # 8h
                d += datetime.timedelta(days=1)
            # last day (partial)
            minutes += business_minutes_in_range(end, time(8,0), end_dt.time())
            return minutes

        # Calculate task schedules
        uid_to_sched = {}
        for r in rows:
            start_date = project_start + datetime.timedelta(days=r["StartOffset"])
            duration_hours = max(r["Duration"] * hours_per_day, r["PlannedHours"])
            end_date = start_date + datetime.timedelta(hours=duration_hours)
            
            uid_to_sched[r["UID"]] = {
                "Start": start_date,
                "Finish": end_date,
                "PlannedHours": r["PlannedHours"],
                "DurationHours": duration_hours
            }

        # Build UID-based children mapping for rollup (as expected by patch)
        wbs_to_uid = {r["WBS"]: r["UID"] for r in rows}
        wbs_children = children_by_parent  # Save original WBS-based mapping
        children_by_parent = {}  # UID-based mapping for rollup
        for wbs, child_wbs_list in wbs_children.items():
            parent_uid = wbs_to_uid.get(wbs)
            if parent_uid:
                children_by_parent[parent_uid] = [wbs_to_uid.get(child_wbs) for child_wbs in child_wbs_list if wbs_to_uid.get(child_wbs)]
        summary_set = set(children_by_parent.keys())

        # 1) roll up start/finish for every summary from its direct/indirect leaves
        def rollup_summary(uid):
            kids = children_by_parent.get(uid, [])
            if not kids:
                return uid_to_sched[uid]["Start"], uid_to_sched[uid]["Finish"]
            starts, finishes = [], []
            for k in kids:
                s,f = rollup_summary(k) if k in summary_set else (uid_to_sched[k]["Start"], uid_to_sched[k]["Finish"])
                starts.append(s); finishes.append(f)
            uid_to_sched[uid]["Start"]  = min(starts)
            uid_to_sched[uid]["Finish"] = max(finishes)
            return uid_to_sched[uid]["Start"], uid_to_sched[uid]["Finish"]

        # Call it on every summary
        for uid in list(summary_set):
            rollup_summary(uid)

        # Also roll up the very top project row if you have one (UID of the first row)
        top_uid = min(uid_to_sched.keys())
        if top_uid in summary_set:
            rollup_summary(top_uid)

        # 2) Recompute Duration for ALL tasks from Start/Finish span (business minutes)
        for uid, sched in uid_to_sched.items():
            span_min = business_minutes_between(sched["Start"], sched["Finish"])
            # cache as hours for later; the XML writer will multiply by 60 again
            sched["DurationHours"] = max(sched.get("DurationHours", 0), span_min / 60.0)
            
        # Convert datetime objects back to strings for XML output
        for uid, sched in uid_to_sched.items():
            if isinstance(sched["Start"], datetime.datetime):
                sched["Start"] = sched["Start"].strftime("%Y-%m-%dT%H:%M:%S")
            if isinstance(sched["Finish"], datetime.datetime):
                sched["Finish"] = sched["Finish"].strftime("%Y-%m-%dT%H:%M:%S")

        # Create resource list (filter out nan/empty roles)
        all_roles = set()
        for r in rows:
            all_roles.update(r["RoleList"])
        if allow_unassigned:
            all_roles.add("Unassigned")
        
        # Remove nan, empty, and None values
        all_roles = {role for role in all_roles if role and str(role).lower() not in ['nan', 'none', '']}
        
        resources = []
        res_name_to_uid = {}
        for i, role in enumerate(sorted(all_roles), 1):
            resources.append({"UID": i, "ID": i, "Name": role})
            res_name_to_uid[role] = i

        # Map prealloc from WBS -> UID (after UIDs exist)
        prealloc_by_task_uid: Dict[int, Dict[str, float]] = {}
        if prealloc_by_parent_wbs:
            wbs_to_uid = {r["WBS"]: r["UID"] for r in rows if r["WBS"]}
            for wbs, role_hours in prealloc_by_parent_wbs.items():
                uid = wbs_to_uid.get(wbs)
                if uid:
                    prealloc_by_task_uid[uid] = role_hours

        # Create assignments
        assignments = []
        assign_uid = 1
        for r in rows:
            if r["UID"] in summary_set:
                continue

            task_hours = uid_to_sched[r["UID"]]["PlannedHours"]
            if task_hours <= 0.0001:
                continue

            # Duration basis for Units
            task_dur_h = uid_to_sched[r["UID"]]["DurationHours"] if uid_to_sched[r["UID"]]["DurationHours"] > 0 else task_hours
            if uid_to_sched[r["UID"]]["DurationHours"] <= 0.0001 and task_hours > 0:
                uid_to_sched[r["UID"]]["DurationHours"] = task_hours

            # --- Use precomputed role->hours if merged
            alloc = prealloc_by_task_uid.get(r["UID"])
            if alloc:
                for role, work_h in alloc.items():
                    res_uid = res_name_to_uid.get(role) or res_name_to_uid.get("Unassigned")
                    units = (work_h / task_dur_h) if task_dur_h > 0 else 1.0
                    units = max(0.05, min(units, 2.0))
                    assignments.append({
                        "UID": assign_uid,
                        "TaskUID": r["UID"],
                        "ResourceUID": res_uid,
                        "Start": uid_to_sched[r["UID"]]["Start"],
                        "Finish": uid_to_sched[r["UID"]]["Finish"],
                        "Units": units,
                        "WorkHours": work_h
                    })
                    assign_uid += 1
                continue  # done with this task

            # else: fall back to existing split-by-role behavior
            role_list = r["RoleList"]
            if not role_list:
                role_list = ["Unassigned"]
                
            if roles_split_rule == "even":
                hours_per_role = task_hours / len(role_list)
                for role in role_list:
                    res_uid = res_name_to_uid.get(role) or res_name_to_uid.get("Unassigned")
                    units = (hours_per_role / task_dur_h) if task_dur_h > 0 else 1.0
                    units = max(0.05, min(units, 2.0))
                    assignments.append({
                        "UID": assign_uid,
                        "TaskUID": r["UID"],
                        "ResourceUID": res_uid,
                        "Start": uid_to_sched[r["UID"]]["Start"],
                        "Finish": uid_to_sched[r["UID"]]["Finish"],
                        "Units": units,
                        "WorkHours": hours_per_role
                    })
                    assign_uid += 1
            elif roles_split_rule == "weighted" and role_weights:
                total_weight = sum(role_weights.get(role, 1.0) for role in role_list)
                for role in role_list:
                    weight = role_weights.get(role, 1.0)
                    hours_for_role = task_hours * (weight / total_weight)
                    res_uid = res_name_to_uid.get(role) or res_name_to_uid.get("Unassigned")
                    units = (hours_for_role / task_dur_h) if task_dur_h > 0 else 1.0
                    units = max(0.05, min(units, 2.0))
                    assignments.append({
                        "UID": assign_uid,
                        "TaskUID": r["UID"],
                        "ResourceUID": res_uid,
                        "Start": uid_to_sched[r["UID"]]["Start"],
                        "Finish": uid_to_sched[r["UID"]]["Finish"],
                        "Units": units,
                        "WorkHours": hours_for_role
                    })
                    assign_uid += 1

        # Generate XML
        project = Element("Project", xmlns="http://schemas.microsoft.com/project")
        
        # Project info
        SubElement(project, "Name").text = project_name or f"Project from {sheet_name}"
        SubElement(project, "CreationDate").text = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        SubElement(project, "StartDate").text = project_start.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Project header tuning
        SubElement(project, "DefaultCalendarUID").text = "1"
        SubElement(project, "ScheduleFromStart").text = "1"
        SubElement(project, "MinutesPerDay").text = "480"
        SubElement(project, "MinutesPerWeek").text = "2400"
        SubElement(project, "DaysPerMonth").text = "20"
        SubElement(project, "DurationFormat").text = "7"
        
        # Calendars
        calendars = SubElement(project, "Calendars")
        calendar = SubElement(calendars, "Calendar")
        SubElement(calendar, "UID").text = "1"
        SubElement(calendar, "Name").text = "Standard"
        SubElement(calendar, "IsBaseCalendar").text = "1"
        
        # Working days
        weekdays = SubElement(calendar, "WeekDays")
        for day_num in range(1, 8):  # 1=Sunday, 2=Monday, etc.
            weekday = SubElement(weekdays, "WeekDay")
            SubElement(weekday, "DayType").text = str(day_num)
            if day_num in [1, 7]:  # Sunday, Saturday
                SubElement(weekday, "DayWorking").text = "0"
            else:
                SubElement(weekday, "DayWorking").text = "1"
                working_times = SubElement(weekday, "WorkingTimes")
                for start_time, end_time in calendar_blocks:
                    working_time = SubElement(working_times, "WorkingTime")
                    SubElement(working_time, "FromTime").text = start_time
                    SubElement(working_time, "ToTime").text = end_time

        # Resources
        resources_elem = SubElement(project, "Resources")
        for res in resources:
            resource = SubElement(resources_elem, "Resource")
            SubElement(resource, "UID").text = str(res["UID"])
            SubElement(resource, "ID").text = str(res["ID"])
            SubElement(resource, "Name").text = res["Name"]
            SubElement(resource, "Type").text = "1"  # Work resource

        # Tasks
        tasks_elem = SubElement(project, "Tasks")
        for task_id, r in enumerate(rows, 1):
            task = SubElement(tasks_elem, "Task")
            SubElement(task, "UID").text = str(r["UID"])
            SubElement(task, "ID").text = str(task_id)
            SubElement(task, "Name").text = r["Name"]
            SubElement(task, "WBS").text = r["WBS"]
            SubElement(task, "OutlineNumber").text = r["WBS"] 
            SubElement(task, "Start").text = uid_to_sched[r["UID"]]["Start"]
            SubElement(task, "Finish").text = uid_to_sched[r["UID"]]["Finish"]
            # Summary task flag
            is_summary = r["UID"] in summary_set
            SubElement(task, "Summary").text = "1" if is_summary else "0"
            
            # Work and Duration handling
            if is_summary:
                # Summary tasks: set Work to PT0M (Workfront will compute from children)
                SubElement(task, "Work").text = "PT0M"
                # Duration will be rolled up by Workfront, but we can include the computed value
                dur_hours = uid_to_sched[r['UID']]['DurationHours']
                if round_to_whole_days:
                    # Round to whole days (8 hours per day = 480 minutes)
                    dur_minutes = int(round(dur_hours / 8.0) * 480)
                else:
                    dur_minutes = int(round(dur_hours * 60))
                SubElement(task, "Duration").text = f"PT{dur_minutes}M"
            else:
                # Leaf tasks: set Work and Duration from planned hours
                planned_minutes = max(0, int(uid_to_sched[r['UID']]['PlannedHours'] * 60)) if not pd.isna(uid_to_sched[r['UID']]['PlannedHours']) else 0
                dur_hours = uid_to_sched[r['UID']]['DurationHours']
                
                if round_to_whole_days:
                    # Round to whole days (8 hours per day = 480 minutes)
                    dur_minutes = int(round(dur_hours / 8.0) * 480)
                else:
                    dur_minutes = int(round(dur_hours * 60))
                
                SubElement(task, "Work").text = f"PT{planned_minutes}M"
                SubElement(task, "Duration").text = f"PT{dur_minutes}M"
            
            # Use ASAP constraint (let Workfront schedule based on dependencies)
            SubElement(task, "ConstraintType").text = "0"  # ASAP (As Soon As Possible)
            
            # Outline level (based on WBS hierarchy depth, count('.') + 1)
            outline_level = r["WBS"].count(".") + 1  # 1 for '1', 2 for '1.1', etc.
            SubElement(task, "OutlineLevel").text = str(outline_level)

        # Assignments
        assignments_elem = SubElement(project, "Assignments")
        for assign in assignments:
            assignment = SubElement(assignments_elem, "Assignment")
            SubElement(assignment, "UID").text = str(assign["UID"])
            SubElement(assignment, "TaskUID").text = str(assign["TaskUID"])
            SubElement(assignment, "ResourceUID").text = str(assign["ResourceUID"])
            SubElement(assignment, "Start").text = assign["Start"]
            SubElement(assignment, "Finish").text = assign["Finish"]
            SubElement(assignment, "Units").text = str(assign["Units"])
            SubElement(assignment, "Work").text = f"PT{int(assign['WorkHours'] * 60)}M"

        # Add PredecessorLinks for dependencies
        wbs_to_uid = {r["WBS"]: r["UID"] for r in rows}
        
        # Add PredecessorLink elements to tasks that have dependencies
        for pred_wbs, succ_wbs in normalized_edges:
            pred_uid = wbs_to_uid.get(pred_wbs)
            succ_uid = wbs_to_uid.get(succ_wbs)
            if pred_uid and succ_uid:
                # Find the successor task element and add a PredecessorLink (MSPDI: no wrapper)
                for task_elem in tasks_elem.findall("Task"):
                    task_uid_elem = task_elem.find("UID")
                    if task_uid_elem is not None and task_uid_elem.text == str(succ_uid):
                        pred_link = SubElement(task_elem, "PredecessorLink")
                        SubElement(pred_link, "PredecessorUID").text = str(pred_uid)
                        SubElement(pred_link, "Type").text = "1"          # 1 = Finish-to-Start
                        SubElement(pred_link, "CrossProject").text = "0"
                        # Optional but harmless:
                        SubElement(pred_link, "LinkLag").text = "0"
                        SubElement(pred_link, "LagFormat").text = "7"     # 7 = days
                        break

        # Compute project summary start/finish from children (no more hardcoded dates)
        if tasks_elem is not None:
            all_task_starts = []
            all_task_finishes = []
            project_task_elem = None
            
            for task_elem in tasks_elem.findall("Task"):
                uid_elem = task_elem.find("UID")
                start_elem = task_elem.find("Start")
                finish_elem = task_elem.find("Finish")
                
                if uid_elem is not None and start_elem is not None and finish_elem is not None:
                    if uid_elem.text == "1":  # Project summary task
                        project_task_elem = task_elem
                    else:
                        # Collect all non-project task dates
                        all_task_starts.append(start_elem.text)
                        all_task_finishes.append(finish_elem.text)
            
            # Set project summary dates from children min/max
            if project_task_elem is not None and all_task_starts and all_task_finishes:
                earliest_start = min(all_task_starts)
                latest_finish = max(all_task_finishes)
                
                # Update project summary start/finish
                proj_start_elem = project_task_elem.find("Start")
                proj_finish_elem = project_task_elem.find("Finish")
                
                if proj_start_elem is not None:
                    proj_start_elem.text = earliest_start
                if proj_finish_elem is not None:
                    proj_finish_elem.text = latest_finish
                
                # Ensure project summary is marked as summary
                proj_summary_elem = project_task_elem.find("Summary")
                if proj_summary_elem is not None:
                    proj_summary_elem.text = "1"

        # Write XML file
        xml_string = tostring(project, encoding='unicode')
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        with open(output_xml, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)

        # Return statistics
        return {
            "tasks_total": len(rows),
            "tasks_merged": len(removed_child_wbs),
            "resources_total": len(resources),
            "assignments_total": len(assignments),
            "dependencies_total": len(normalized_edges)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MSPDI conversion failed: {str(e)}")

# ---------- Run locally in Replit ----------
# In Replit, set the "run" command to: uvicorn main:app --host 0.0.0.0 --port 5000 --reload