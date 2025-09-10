import os, re, io, math, json, datetime, urllib.parse, tempfile
from typing import List, Optional, Dict, Any
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
        self.ui_options = None              # UI_Options
        self.rfp_rules = None               # RFP_Matching_Rules

    def _scenario_col(self, complexity: str, tier: str) -> str:
        return f"{complexity}__{tier}_Hours"

    def load(self):
        # Try Excel v4, else CSV bundle, else create mock data
        xlsx_name = "Replit_App_DB_READABLE_FullRows_v4.xlsx"
        csv_dir  = "Replit_App_DB_READABLE_FullRows_v4_csvs"
        if os.path.exists(xlsx_name):
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

        self.loaded = True
        return True

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
    def suggest_deliverables_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Returns a list of suggestions: [{
            deliverable_code, deliverable, category, confidence, matches: [matched_keywords...]
        }]
        Strategy:
          1) Use RFP_Matching_Rules (Regex_Keywords -> Map_To_Deliverable).
          2) If no rule hits and/or rules table empty, fallback: match deliverable names in text.
        """
        if not text:
            return []

        text = str(text)
        suggestions: Dict[str, Dict[str, Any]] = {}

        # (1) Rule-based pass (preferred)
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
            match_df = self.deliverables[self.deliverables["Deliverable"] == target]
            if match_df.empty:
                continue
            for __, r in match_df.iterrows():
                code = str(r["Deliverable_Code"])
                entry = suggestions.setdefault(code, {
                    "deliverable_code": code,
                    "deliverable": str(r["Deliverable"]),
                    "category": str(r.get("Category", "")),
                    "confidence": 0,
                    "matches": []
                })
                entry["confidence"] += len(hits)
                # Store a few unique matched tokens for UX
                uniq = list({str(h).lower() for h in hits if str(h).strip()})
                entry["matches"].extend([m for m in uniq if m not in entry["matches"]])

        # (2) Fallback: check if deliverable names appear in-text (very light heuristic)
        if not suggestions:
            for _, r in self.deliverables.iterrows():
                name = str(r["Deliverable"])
                code = str(r["Deliverable_Code"])
                if not name:
                    continue
                # token containment (case-insensitive)
                if re.search(r"\b" + re.escape(name) + r"\b", text, flags=re.IGNORECASE):
                    suggestions[code] = {
                        "deliverable_code": code,
                        "deliverable": name,
                        "category": str(r.get("Category", "")),
                        "confidence": 1,
                        "matches": [name]
                    }

        # Rank by confidence desc, then by deliverable
        out = list(suggestions.values())
        out.sort(key=lambda x: (-x["confidence"], x["deliverable"]))
        return out

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
        col = self._scenario_col(complexity, tier)
        if col not in self.all_rows.columns:
            raise HTTPException(400, f"Scenario column not found: {col}")
        return col

    def hours_by_role_for_deliverable(
        self, deliverable_code: str, included_task_groups: List[str], scenario_col: str
    ) -> pd.DataFrame:
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str)==str(deliverable_code)) &
            (self.all_rows["task_group"].isin(included_task_groups))
        ]
        if sub.empty:
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
                       project_start: Optional[str]=None) -> List[Dict[str, Any]]:
        # Order task groups by a sensible default from Timeline_Params appearance
        order_map = {tg:i for i, tg in enumerate(self.timeline_params["Task_Group"].tolist())}
        tgs = sorted(included_task_groups, key=lambda x: order_map.get(x, 999))

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

def _safe_sheet_name(s: str) -> str:
    # Excel sheet name rules: max 31 chars, no : \ / ? * [ ]
    s = re.sub(r'[:\\/?*\[\]]+', "-", (s or "Sheet"))
    s = s.strip() or "Sheet"
    return s[:31]

def _wbs_dataframe_from_scenario(scenario: dict, project_name: str) -> pd.DataFrame:
    """Build the same WBS rows you already export to CSV, using provided project_name."""
    rows = []
    for i, d in enumerate(scenario.get("items", []), start=1):
        wbs_id = f"1.{i}"
        rows.append({
            "Project_Name": project_name,
            "WBS_ID": wbs_id, "Parent_WBS_ID": "1",
            "Task_Name": d["deliverable"], "Deliverable": d["deliverable"],
            "Component": "", "Task": "", "Role": "", "Seniority": "",
            "Planned_Hours": d["total_hours"], "Start_Offset_Days": 0,
            "Duration_Days": sum(x["duration_days"] for x in d["schedule"]),
            "Dependencies": "", "Assignee_External_ID": "",
            "Notes": f"{d['complexity']} / {d['tier']}"
        })
        for j, t in enumerate(d["schedule"], start=1):
            rows.append({
                "Project_Name": project_name,
                "WBS_ID": f"{wbs_id}.{j}", "Parent_WBS_ID": wbs_id,
                "Task_Name": t["task_group"], "Deliverable": d["deliverable"],
                "Component": "", "Task": t["task_group"], "Role": "", "Seniority": "",
                "Planned_Hours": "", "Start_Offset_Days": "", "Duration_Days": t["duration_days"],
                "Dependencies": "", "Assignee_External_ID": "", "Notes": ""
            })
    return pd.DataFrame(rows)

# ---------- Pydantic models ----------
class SuggestPayload(BaseModel):
    rfp_text: str

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
    # Extract dropdown lists
    complexities = DB.timeline_scaling[DB.timeline_scaling["Scale_Type"]=="Complexity"]["Key"].tolist()
    tiers        = DB.timeline_scaling[DB.timeline_scaling["Scale_Type"]=="Tier"]["Key"].tolist()
    rate_bands   = DB.rate_bands["Band_Name"].tolist()
    pricing_modes= ["Flat_Blended","Per_Resource"]
    # Bundles per category
    bundles = DB.b_defaults["Bundle"].tolist()
    # Deliverables
    deliverables = DB.deliverables[["Deliverable_Code","Deliverable","Category"]].to_dict(orient="records")
    # Scenario templates
    scenario_templates = DB.scenario_templates.to_dict(orient="records")
    return {
        "complexities": complexities,
        "tiers": tiers,
        "rate_bands": rate_bands,
        "pricing_modes": pricing_modes,
        "bundles": bundles,
        "deliverables": deliverables,
        "scenario_templates": scenario_templates,
        "pricing_settings": DB.pricing_settings.to_dict(orient="records"),
        "slack_settings": DB.slack_settings.to_dict(orient="records"),
    }

@app.post("/api/suggest_by_text")
def api_suggest(payload: SuggestPayload):
    if not DB.loaded:
        DB.load()
    recs = DB.suggest_deliverables_from_text(payload.rfp_text or "")
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
                              project_start: Optional[str]) -> Dict[str, Any]:
    # Which task groups to include?
    if spec["mode"] == "bundle":
        included = DB.included_task_groups(category, spec["bundle"])
    else:
        # Template mode: include all task_groups that exist in data for this deliverable (collapsed to unique)
        sub = DB.all_rows[DB.all_rows["Deliverable_Code"].astype(str)==str(deliv_code)]
        included = sorted(set(sub["task_group"].dropna().astype(str).tolist()))

    complexity, tier = spec["complexity"], spec["tier"]
    scen_col = DB.scenario_hours_col(complexity, tier)
    hrs_by_role = DB.hours_by_role_for_deliverable(deliv_code, included, scen_col)
    total_hours = float(hrs_by_role["Hours"].sum()) if not hrs_by_role.empty else 0.0

    # Price
    if pricing_mode == "Flat_Blended":
        if blended_rate is None:
            # default from Pricing_Settings
            ps = DB.pricing_settings[DB.pricing_settings["Key"]=="Default_Blended_Rate"]
            blended_rate = float(ps["Default"].iloc[0]) if not ps.empty else 185.0
        price = DB.blended_price(total_hours, blended_rate)
    else:
        price = DB.per_resource_price(hrs_by_role, rate_band=rate_band or "Standard_US")

    # Schedule
    schedule = DB.build_schedule(
        deliv_code, included, complexity, tier, use_slack, slack_i, slack_c, slack_pct, project_start
    )

    return {
        "deliverable_code": deliv_code,
        "included_task_groups": included,
        "complexity": complexity,
        "tier": tier,
        "scenario_col": scen_col,
        "hours_by_role": hrs_by_role.to_dict(orient="records"),
        "total_hours": total_hours,
        "price": round(price, 2),
        "schedule": schedule
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

    # Build scenarios
    scenarios = {}
    for letter, spec_in in [("A", payload.scenario_a), ("B", payload.scenario_b)]:
        per_deliv = []
        price_sum = 0.0
        hours_sum = 0.0
        for code in payload.selected_deliverable_codes:
            row = DB.deliverables[DB.deliverables["Deliverable_Code"].astype(str)==str(code)]
            if row.empty: 
                continue
            cat = str(row["Category"].iloc[0])
            spec_resolved = _resolve_scenario(spec_in, cat)
            out = _scenario_for_deliverable(
                code, cat, spec_resolved,
                pricing_mode, blended_rate, rate_band,
                use_slack, slack_i, slack_c, slack_pct, project_start
            )
            # Add names for readability
            out["deliverable"] = str(row["Deliverable"].iloc[0])
            out["category"]    = cat
            per_deliv.append(out)
            price_sum += out["price"]
            hours_sum += out["total_hours"]

        scenarios[letter] = {
            "pricing_mode": pricing_mode,
            "rate_band": rate_band,
            "blended_rate": blended_rate,
            "use_slack": use_slack,
            "slack_after_internal": slack_i,
            "slack_after_client": slack_c,
            "slack_global_pct": slack_pct,
            "project_start": project_start,
            "items": per_deliv,
            "totals": {"hours": round(hours_sum,2), "price": round(price_sum,2)}
        }

    return scenarios

@app.post("/api/auto_build")
def api_auto_build(payload: AutoBuildPayload):
    if not DB.loaded:
        DB.load()

    # 1) Get AI suggestions
    suggestions = DB.suggest_deliverables_from_text(payload.rfp_text or "")
    selected_codes = [s["deliverable_code"] for s in suggestions]

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
            out = _scenario_for_deliverable(
                code, cat, spec_resolved,
                payload.pricing_mode, payload.blended_rate, payload.rate_band or "Standard_US",
                bool(payload.use_slack), int(payload.slack_after_internal), int(payload.slack_after_client),
                float(payload.slack_global_pct or 0), payload.project_start
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

    scenario = payload.scenario or {}
    project_name = payload.project_name or f"Proposal {datetime.date.today().isoformat()}"
    project_name = _safe_filename(project_name)

    # Optional scenario tag used in the download filename (not inside the sheet itself)
    scen_label = _safe_filename(payload.scenario_label or "")

    # Build rows (same as before, but use project_name param)
    rows = []
    for i, d in enumerate(scenario.get("items", []), start=1):
        wbs_id = f"1.{i}"
        rows.append({
            "Project_Name": project_name,
            "WBS_ID": wbs_id,
            "Parent_WBS_ID": "1",
            "Task_Name": d["deliverable"],
            "Deliverable": d["deliverable"],
            "Component": "",
            "Task": "",
            "Role": "",
            "Seniority": "",
            "Planned_Hours": d["total_hours"],
            "Start_Offset_Days": 0,
            "Duration_Days": sum([x["duration_days"] for x in d["schedule"]]),
            "Dependencies": "",
            "Assignee_External_ID": "",
            "Notes": f"{d['complexity']} / {d['tier']}"
        })
        for j, t in enumerate(d["schedule"], start=1):
            rows.append({
                "Project_Name": project_name,
                "WBS_ID": f"{wbs_id}.{j}",
                "Parent_WBS_ID": wbs_id,
                "Task_Name": t["task_group"],
                "Deliverable": d["deliverable"],
                "Component": "",
                "Task": t["task_group"],
                "Role": "",
                "Seniority": "",
                "Planned_Hours": "",
                "Start_Offset_Days": "",
                "Duration_Days": t["duration_days"],
                "Dependencies": "",
                "Assignee_External_ID": "",
                "Notes": ""
            })

    df = pd.DataFrame(rows)

    # File naming
    parts = [p for p in [project_name, scen_label, "Workfront Export"] if p]
    base = " - ".join(parts)
    if payload.add_timestamp:
        base += " - " + datetime.datetime.now().strftime("%Y%m%d-%H%M")

    fmt = (payload.file_format or "csv").lower().strip()
    if fmt not in ("csv", "xlsx"):
        raise HTTPException(400, "file_format must be 'csv' or 'xlsx'.")

    if fmt == "csv":
        out_name = f"{base}.csv"
        df.to_csv(out_name, index=False)
        resp = FileResponse(out_name, filename=out_name, media_type="text/csv")
    else:
        out_name = f"{base}.xlsx"
        try:
            df.to_excel(out_name, index=False, engine="openpyxl")
        except Exception as ex:
            raise HTTPException(400, "XLSX export requires 'openpyxl'. Add it to requirements.txt.") from ex
        resp = FileResponse(
            out_name,
            filename=out_name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Add RFC 5987 filename* for better cross-browser support
    import urllib.parse
    quoted = urllib.parse.quote(out_name)
    resp.headers["Content-Disposition"] = f'attachment; filename="{out_name}"; filename*=UTF-8\'\'{quoted}'
    return resp

@app.post("/api/export_workbook")
def api_export_workbook(payload: ExportWorkbookPayload):
    """
    Export both scenarios in ONE Excel (.xlsx) file with two tabs.
    """
    if not DB.loaded:
        DB.load()

    # Naming (for download filename only, not file path)
    project = _safe_filename(payload.project_name or f"Proposal {datetime.date.today().isoformat()}")
    base = f"{project} - Scenarios A & B - Workfront Export"
    if payload.add_timestamp:
        base += " - " + datetime.datetime.now().strftime("%Y%m%d-%H%M")
    download_name = f"{base}.xlsx"

    # Sheet names
    sA = _safe_sheet_name(payload.sheet_name_a or "Scenario A")
    sB = _safe_sheet_name(payload.sheet_name_b or "Scenario B")

    # Build dataframes
    dfA = _wbs_dataframe_from_scenario(payload.scenario_a or {}, project)
    dfB = _wbs_dataframe_from_scenario(payload.scenario_b or {}, project)

    # Use temporary file for secure file handling
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
        temp_path = tmp_file.name

    try:
        # Write workbook with two sheets
        with pd.ExcelWriter(temp_path, engine="openpyxl") as xw:
            dfA.to_excel(xw, sheet_name=sA, index=False)
            dfB.to_excel(xw, sheet_name=sB, index=False)

        # Return with a robust Content-Disposition (filename + filename*)
        resp = FileResponse(
            temp_path,
            filename=download_name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        quoted = urllib.parse.quote(download_name)
        resp.headers["Content-Disposition"] = f'attachment; filename="{download_name}"; filename*=UTF-8\'\'{quoted}'
        
        # Clean up temporary file after response
        import atexit
        atexit.register(lambda: os.unlink(temp_path) if os.path.exists(temp_path) else None)
        
        return resp
    except Exception as ex:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        if "openpyxl" in str(ex):
            raise HTTPException(400, "Excel export requires 'openpyxl'. Add it to requirements.txt.") from ex
        raise HTTPException(500, f"Error creating Excel workbook: {str(ex)}") from ex

# ---------- Run locally in Replit ----------
# In Replit, set the "run" command to: uvicorn main:app --host 0.0.0.0 --port 5000 --reload