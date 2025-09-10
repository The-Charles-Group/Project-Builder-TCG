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

    # ---------- Helper methods for task ordering and role detection ----------
    def sorted_task_groups(self, included: List[str]) -> List[str]:
        order_map = {tg: i for i, tg in enumerate(self.timeline_params["Task_Group"].astype(str).tolist())}
        return sorted([str(x) for x in included], key=lambda tg: order_map.get(tg, 999))

    def task_hours_by_task_group(self, deliverable_code: str, included: List[str], scenario_col: str) -> Dict[str, float]:
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].isin(included))
        ]
        if sub.empty:
            return {}
        g = sub.groupby(["task_group"], as_index=False)[scenario_col].sum()
        return {str(r["task_group"]): float(r[scenario_col]) for _, r in g.iterrows()}

    def dominant_role_for_task_group(self, deliverable_code: str, task_group: str, scenario_col: str):
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str) == str(task_group))
        ]
        if sub.empty:
            return ("","")
        g = sub.groupby(["Resource_Title","Seniority"], as_index=False)[scenario_col].sum()
        r = g.sort_values(scenario_col, ascending=False).iloc[0]
        return (str(r["Resource_Title"]), str(r["Seniority"]))

    # ---------- Component-level helper methods ----------
    def components_for_deliverable(self, deliverable_code: str, included_tgs: list[str]) -> list[str]:
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str).isin([str(x) for x in included_tgs]))
        ]
        if "Component" not in sub.columns:
            # Fallback: treat all tasks as one "General" component
            return ["General"]
        comps = [str(x) for x in sub["Component"].dropna().astype(str).unique().tolist()]
        if not comps:
            return ["General"]

        # Order components by the earliest task_group position in Timeline_Params
        order_map = {str(tg): i for i, tg in enumerate(self.timeline_params["Task_Group"].astype(str).tolist())}
        comp_earliest = {}
        for comp in comps:
            tgs = sub[sub["Component"].astype(str) == comp]["task_group"].astype(str).unique().tolist()
            comp_earliest[comp] = min([order_map.get(tg, 999) for tg in tgs]) if tgs else 999
        return sorted(comps, key=lambda c: (comp_earliest.get(c, 999), c))

    def hours_by_component(self, deliverable_code: str, included_tgs: list[str], scenario_col: str) -> dict[str, float]:
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str).isin([str(x) for x in included_tgs]))
        ]
        comp_col = "Component" if "Component" in sub.columns else None
        if comp_col is None:
            return {"General": float(sub[scenario_col].sum()) if not sub.empty else 0.0}
        g = sub.groupby(comp_col, as_index=False)[scenario_col].sum()
        return {str(r[comp_col]): float(r[scenario_col]) for _, r in g.iterrows()}

    def hours_by_taskgroup_for_component(self, deliverable_code: str, component: str,
                                         included_tgs: list[str], scenario_col: str) -> dict[str, float]:
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str).isin([str(x) for x in included_tgs]))
        ]
        if "Component" in sub.columns:
            sub = sub[sub["Component"].astype(str) == str(component)]
        g = sub.groupby("task_group", as_index=False)[scenario_col].sum()
        return {str(r["task_group"]): float(r[scenario_col]) for _, r in g.iterrows()}

    def dominant_role_for_component_task(self, deliverable_code: str, component: str,
                                         task_group: str, scenario_col: str) -> tuple[str, str]:
        sub = self.all_rows[
            (self.all_rows["Deliverable_Code"].astype(str) == str(deliverable_code)) &
            (self.all_rows["task_group"].astype(str) == str(task_group))
        ]
        if "Component" in sub.columns:
            sub = sub[sub["Component"].astype(str) == str(component)]
        if sub.empty:
            return ("", "")
        g = sub.groupby(["Resource_Title", "Seniority"], as_index=False)[scenario_col].sum()
        r = g.sort_values(scenario_col, ascending=False).iloc[0]
        return (str(r["Resource_Title"]), str(r["Seniority"]))

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

def build_wbs_dataframe_from_scenario(scenario: dict, project_name: str) -> pd.DataFrame:
    """Build WBS with a Project row, then Deliverable → Component → Task (task_group).
       Fills: Component, Role, Seniority, Start_Offset_Days, Dependencies. Rounds hours."""
    rows = []
    # Root project row
    rows.append({
        "Project_Name": project_name, "WBS_ID": "1", "Parent_WBS_ID": "",
        "Task_Name": project_name, "Deliverable": "", "Component": "Project",
        "Task": "", "Role": "", "Seniority": "",
        "Planned_Hours": "", "Start_Offset_Days": 0, "Duration_Days": "",
        "Dependencies": "", "Assignee_External_ID": "", "Notes": ""
    })

    items = scenario.get("items", [])
    # Deliverable ordering by earliest task_group index in Timeline_Params
    order_map = {str(tg): i for i, tg in enumerate(DB.timeline_params["Task_Group"].astype(str).tolist())}

    def deliv_key(d):
        tgs = [str(x) for x in d.get("included_task_groups", [])]
        idxs = [order_map.get(tg, 999) for tg in tgs]
        return (min(idxs) if idxs else 999, str(d.get("deliverable","")))

    items_sorted = sorted(items, key=deliv_key)

    day_cursor = 0
    prev_deliv_wbs = ""

    for i, d in enumerate(items_sorted, start=1):
        dcode = str(d["deliverable_code"])
        scen_col = d["scenario_col"]
        included = [str(x) for x in d.get("included_task_groups", [])]

        # Build a per-deliverable schedule + offsets by task_group
        schedule = d.get("schedule", [])
        tg_order = sorted(included, key=lambda tg: order_map.get(tg, 999))
        duration_by_tg = {str(t["task_group"]): int(t["duration_days"]) for t in schedule}
        offset_by_tg = {}
        run = 0
        for tg in tg_order:
            offset_by_tg[tg] = run
            run += int(duration_by_tg.get(tg, 1))
        total_deliv_duration = run

        # Hours: parent (rounded), components (rounded), then tasks (rounded)
        parent_hours_rounded = _round_int(d.get("total_hours", 0.0))
        comp_hours = DB.hours_by_component(dcode, tg_order, scen_col)
        comp_hours_rounded = _largest_remainder(parent_hours_rounded, comp_hours)

        # Deliverable row
        wbs_deliv = f"1.{i}"
        rows.append({
            "Project_Name": project_name, "WBS_ID": wbs_deliv, "Parent_WBS_ID": "1",
            "Task_Name": str(d.get("deliverable","")), "Deliverable": str(d.get("deliverable","")),
            "Component": "", "Task": "", "Role": "", "Seniority": "",
            "Planned_Hours": parent_hours_rounded,
            "Start_Offset_Days": day_cursor,
            "Duration_Days": total_deliv_duration,
            "Dependencies": prev_deliv_wbs,
            "Assignee_External_ID": "",
            "Notes": f'{d.get("complexity","")}/{d.get("tier","")}'
        })

        # Components ordered by earliest child task position
        comps = DB.components_for_deliverable(dcode, tg_order)
        prev_comp_wbs = ""
        for j, comp in enumerate(comps, start=1):
            tg_in_comp_all = DB.hours_by_taskgroup_for_component(dcode, comp, tg_order, scen_col).keys()
            tg_in_comp = [tg for tg in tg_order if tg in tg_in_comp_all]
            if not tg_in_comp:
                continue

            comp_offset = min(offset_by_tg[tg] for tg in tg_in_comp)
            comp_duration = sum(int(duration_by_tg.get(tg, 1)) for tg in tg_in_comp)
            comp_hours_target = int(comp_hours_rounded.get(comp, 0))

            # Task hours under this component
            tg_hours = DB.hours_by_taskgroup_for_component(dcode, comp, tg_in_comp, scen_col)
            tg_hours_rounded = _largest_remainder(comp_hours_target, tg_hours)

            wbs_comp = f"{wbs_deliv}.{j}"
            rows.append({
                "Project_Name": project_name, "WBS_ID": wbs_comp, "Parent_WBS_ID": wbs_deliv,
                "Task_Name": comp, "Deliverable": str(d.get("deliverable","")),
                "Component": comp, "Task": "", "Role": "", "Seniority": "",
                "Planned_Hours": comp_hours_target,
                "Start_Offset_Days": day_cursor + comp_offset,
                "Duration_Days": comp_duration,
                "Dependencies": (wbs_deliv if j == 1 else prev_comp_wbs),
                "Assignee_External_ID": "", "Notes": ""
            })

            prev_task_wbs = ""
            running = 0
            for k, tg in enumerate(tg_in_comp, start=1):
                dur = int(duration_by_tg.get(tg, 1))
                role, sen = DB.dominant_role_for_component_task(dcode, comp, tg, scen_col)
                wbs_task = f"{wbs_comp}.{k}"
                rows.append({
                    "Project_Name": project_name, "WBS_ID": wbs_task, "Parent_WBS_ID": wbs_comp,
                    "Task_Name": tg, "Deliverable": str(d.get("deliverable","")),
                    "Component": comp, "Task": tg, "Role": role, "Seniority": sen,
                    "Planned_Hours": int(tg_hours_rounded.get(tg, 0)),
                    "Start_Offset_Days": day_cursor + offset_by_tg[tg],
                    "Duration_Days": dur,
                    "Dependencies": (wbs_comp if k == 1 else prev_task_wbs),
                    "Assignee_External_ID": "", "Notes": ""
                })
                prev_task_wbs = wbs_task
                running += dur

            prev_comp_wbs = wbs_comp

        day_cursor += total_deliv_duration
        prev_deliv_wbs = wbs_deliv

    return pd.DataFrame(rows)

# For backward compatibility, keep the old function name pointing to the new one
def _wbs_dataframe_from_scenario(scenario: dict, project_name: str) -> pd.DataFrame:
    """Legacy function name - redirects to the new WBS builder."""
    return build_wbs_dataframe_from_scenario(scenario, project_name)

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

    project_name = payload.project_name or f"Proposal {datetime.date.today().isoformat()}"
    df = build_wbs_dataframe_from_scenario(payload.scenario or {}, project_name)

    # Friendly filename
    base_parts = [project_name, (payload.scenario_label or "").strip(), "Workfront Export"]
    base = " - ".join([p for p in base_parts if p])
    if payload.add_timestamp:
        base += " - " + datetime.datetime.now().strftime("%Y%m%d-%H%M")

    fmt = (payload.file_format or "csv").lower()
    if fmt == "csv":
        out_path = f"{base}.csv"
        df.to_csv(out_path, index=False)
        return FileResponse(out_path, filename=out_path, media_type="text/csv")

    # xlsx
    try:
        out_path = f"{base}.xlsx"
        df.to_excel(out_path, index=False, engine="openpyxl")
        return FileResponse(
            out_path, filename=out_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as ex:
        raise HTTPException(400, "XLSX export requires 'openpyxl'.") from ex

@app.post("/api/export_workbook")
def api_export_workbook(payload: ExportWorkbookPayload):
    if not DB.loaded:
        DB.load()
    project = (payload.project_name or f"Proposal {datetime.date.today().isoformat()}").strip()
    dfA = build_wbs_dataframe_from_scenario(payload.scenario_a or {}, project)
    dfB = build_wbs_dataframe_from_scenario(payload.scenario_b or {}, project)
    base = f"{project} - Scenarios A & B - Workfront Export"
    if payload.add_timestamp:
        base += " - " + datetime.datetime.now().strftime("%Y%m%d-%H%M")
    out_name = f"{base}.xlsx"
    with pd.ExcelWriter(out_name, engine="openpyxl") as xw:
        dfA.to_excel(xw, sheet_name=(_safe_sheet_name(payload.sheet_name_a or "Scenario A")), index=False)
        dfB.to_excel(xw, sheet_name=(_safe_sheet_name(payload.sheet_name_b or "Scenario B")), index=False)
    return FileResponse(out_name, filename=out_name,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------- Run locally in Replit ----------
# In Replit, set the "run" command to: uvicorn main:app --host 0.0.0.0 --port 5000 --reload