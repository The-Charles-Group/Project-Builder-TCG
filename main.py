import os, re, io, math, json, datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
import numpy as np

# ---------- App & CORS ----------
app = FastAPI(title="Agency Project Builder", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
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
        if not text:
            return []
        suggestions = {}
        for _, row in self.rfp_rules.iterrows():
            patt = str(row["Regex_Keywords"])
            deliverable = str(row["Map_To_Deliverable"])
            try:
                if re.search(patt, text, flags=re.IGNORECASE):
                    suggestions[deliverable] = suggestions.get(deliverable, 0) + 1
            except re.error:
                # Skip malformed regex
                continue
        # Map suggestions to Deliverable_Code if present
        out = []
        for dname, hits in sorted(suggestions.items(), key=lambda x: -x[1]):
            match = self.deliverables[self.deliverables["Deliverable"]==dname]
            if not match.empty:
                for _, r in match.iterrows():
                    out.append({
                        "deliverable_code": r["Deliverable_Code"],
                        "deliverable": r["Deliverable"],
                        "category": r.get("Category",""),
                        "confidence": hits
                    })
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

class ExportPayload(BaseModel):
    scenario: Dict[str, Any]                # a scenario dict returned from /api/build

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

@app.post("/api/export")
def api_export(payload: ExportPayload):
    """
    Export a Workfront Fusion CSV from a single scenario payload.
    Each row: Deliverable → Task_Group lines with rolled-up planned hours (per role not required by Workfront WBS).
    """
    if not DB.loaded:
        DB.load()
    scenario = payload.scenario
    rows = []
    # Create a simple WBS: 1.x for deliverables, 1.x.y for tasks
    project_name = f"Proposal {datetime.date.today().isoformat()}"
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
        # children by task_group
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
                "Planned_Hours": "",     # (optional: prorate hours by task_group if needed)
                "Start_Offset_Days": "", # handled by Fusion or further logic
                "Duration_Days": t["duration_days"],
                "Dependencies": "",
                "Assignee_External_ID": "",
                "Notes": ""
            })
    df = pd.DataFrame(rows)
    out_path = "workfront_export.csv"
    df.to_csv(out_path, index=False)
    return FileResponse(out_path, filename=out_path, media_type="text/csv")

# ---------- Run locally in Replit ----------
# In Replit, set the "run" command to: uvicorn main:app --host 0.0.0.0 --port 5000 --reload