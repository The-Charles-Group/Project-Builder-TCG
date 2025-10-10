"""
AI Relevance Engine V2 - Sparse, Department-Gated, Budget-Aware Scoring

Features:
- Department intent gating (top 1-2 departments get bonus, others penalized)
- Execution vs Strategy bias (tactical work boosted, decks penalized)
- Budget-aware filtering (expensive deliverables downweighted)
- Sparsity shaping (max 4 items in "High" band ≥85%)
- Transparent metadata (returns detected departments and budget)
"""

import re
import math
import glob
import os
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import pandas as pd

# Level constants (mapped to AI_Index structure: L1=Deliverable, L2=Component, L3=Task)
LEVEL_DELIVERABLE = "L1"  # Deliverable level in AI_Index
LEVEL_L1 = "L2"  # Component level in AI_Index  
LEVEL_L2 = "L3"  # Task level in AI_Index

# Column name constants
COL_SERVICE_DEPT = "Service_Department"
COL_DELIV_CODE = "Deliverable_Code"
COL_DELIVERABLE = "Deliverable"
COL_L1_NAME = "L1_Component_Name"
COL_L2_NAME = "L2_Task_Name"


def _norm(s: str) -> str:
    """Normalize text for matching"""
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _tok(s: str) -> List[str]:
    """Tokenize normalized text"""
    return [t for t in re.findall(r"[a-z0-9]+", _norm(s)) if t]


def _contains(text: str, phrase: str) -> bool:
    """Check if phrase exists as whole word in text"""
    p = re.escape((phrase or "").lower())
    return re.search(rf"\b{p}\b", text) is not None


def _sigmoid(x: float, mu: float, sigma: float) -> float:
    """Sigmoid function for score normalization"""
    return 1.0 / (1.0 + math.exp(-(x - mu) / (sigma if sigma else 0.25)))


def _softmax(xs: List[float], temp: float = 1.0) -> List[float]:
    """Softmax with temperature for score distribution"""
    if not xs:
        return []
    m = max(xs)
    es = [math.exp((x - m) / max(1e-6, temp)) for x in xs]
    s = sum(es) or 1e-9
    return [e / s for e in es]


class RelevanceEngineV2:
    """
    V2 Relevance Engine with department gating, budget awareness, and sparsity control
    """
    
    def __init__(self, workbook_path: Optional[str] = None):
        """Initialize engine with optional AI_Matching_Rules workbook"""
        self.index, self.hours = self._load_or_build_index(workbook_path)
        
        # Configuration parameters (tunable)
        self.cfg = {
            # Lexical/Rule weighting by level
            "w_rule_deliverable": 0.60,
            "w_lex_deliverable": 0.40,
            "w_rule_l1": 0.65,
            "w_lex_l1": 0.35,
            "w_rule_l2": 0.70,
            "w_lex_l2": 0.30,
            
            # Aggregation weights
            "agg_w_deliverable": 1.0,
            "agg_w_l1": 0.9,
            "agg_w_l2": 0.8,
            
            # Sigmoid normalization
            "mu": 0.6,
            "sigma": 0.25,
            
            # Department gating
            "dept_topK": 2,  # Consider top 2 departments
            "dept_penalty": 0.35,  # Penalty for non-top departments
            "dept_bonus": 1.10,  # Bonus for top departments
            
            # Execution vs Strategy bias
            "strategy_penalty": 0.6,  # Penalty for strategy deliverables
            "execution_bonus": 1.15,  # Bonus for execution deliverables
            
            # Sparsity control
            "high_cap": 4,  # Max items allowed in High band (≥85%)
            "band_top": (0.87, 1.00),  # High band range
            "band_mid": (0.70, 0.84),  # Mid band range
            "band_low": (0.40, 0.69),  # Low band range
            
            # Budget awareness
            "blended_rate": 125.0,  # Default blended hourly rate
            "budget_hard_ceil_multiplier": 1.10,  # 10% over budget threshold
            "overbudget_penalty": 0.6,  # Penalty for over-budget deliverables
        }
        
        self._build_lex()
    
    def _find_db_workbook(self) -> Optional[str]:
        """Find the database workbook automatically"""
        patterns = [
            "Replit_App_DB_READABLE*.xlsx",
            "*DB_READABLE*.xlsx",
            "*.xlsx"
        ]
        roots = [".", "./data", "/app/data", "/workspace", "/home/runner", "/mnt/data"]
        
        for r in roots:
            for pat in patterns:
                for path in glob.glob(os.path.join(r, pat)):
                    try:
                        xl = pd.ExcelFile(path)
                        if ("Deliverable_Index" in xl.sheet_names) and ("All_Task_Rows" in xl.sheet_names):
                            return path
                    except Exception:
                        continue
        return None
    
    def _load_or_build_index(self, workbook_path: Optional[str]) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """Load AI_Index from workbook or build from Deliverable_Index + All_Task_Rows"""
        idx = None
        hours: Dict[str, float] = {}
        
        # Try to load from AI_Matching_Rules workbook if provided
        if workbook_path and Path(workbook_path).exists():
            try:
                x = pd.ExcelFile(workbook_path)
                if "AI_Index" in x.sheet_names:
                    idx = pd.read_excel(x, "AI_Index")
            except Exception:
                idx = None
        
        if idx is not None:
            return idx, hours
        
        # Build from DB workbook
        db = self._find_db_workbook()
        if not db:
            # Return empty DataFrame with correct columns
            cols = [
                COL_SERVICE_DEPT, COL_DELIV_CODE, COL_DELIVERABLE,
                COL_L1_NAME, COL_L2_NAME, "Level", "Default_Keywords"
            ]
            return pd.DataFrame(columns=cols), {}
        
        xl = pd.ExcelFile(db)
        di = pd.read_excel(xl, "Deliverable_Index")
        atr = pd.read_excel(xl, "All_Task_Rows")
        
        # Normalize column names for flexible matching
        def nmap(df):
            return {re.sub(r"[^a-z0-9]+", "_", c.lower()): c for c in df.columns}
        
        di_map = nmap(di)
        atr_map = nmap(atr)
        
        def pick(m, *c):
            for k in c:
                if k in m:
                    return m[k]
            return None
        
        # Standardize Deliverable_Index
        di_code_col = pick(di_map, "deliverable_code", "code", "id")
        di_name_col = pick(di_map, "deliverable", "deliverable_name", "name")
        di_dept_col = pick(di_map, "service_department", "department", "dept")
        
        di_std = pd.DataFrame({
            "Deliverable_Code": di[di_code_col] if di_code_col else None,
            "Deliverable": di[di_name_col] if di_name_col else None,
            "Service_Department": di[di_dept_col] if di_dept_col else ""
        }).dropna(subset=["Deliverable"])
        
        # Standardize All_Task_Rows
        atr_dept_col = pick(atr_map, "service_department", "department", "dept")
        atr_code_col = pick(atr_map, "deliverable_code", "code", "id")
        atr_name_col = pick(atr_map, "deliverable", "deliverable_name", "name")
        atr_l1_col = pick(atr_map, "component_task_l1", "component", "task_l1", "l1")
        atr_l2_col = pick(atr_map, "task_task_l2", "task", "l2")
        
        atr_std = pd.DataFrame({
            "Service_Department": atr[atr_dept_col] if atr_dept_col else "",
            "Deliverable_Code": atr[atr_code_col] if atr_code_col else None,
            "Deliverable": atr[atr_name_col] if atr_name_col else None,
            "Component_Task_L1": atr[atr_l1_col] if atr_l1_col else None,
            "Task_Task_L2": atr[atr_l2_col] if atr_l2_col else None
        }).dropna(subset=["Deliverable"])
        
        # Estimate hours if hour columns exist
        hrs_cols = [c for c in atr.columns if re.search(r"hour|hrs", c, re.I)]
        if hrs_cols and atr_code_col:
            agg = atr.groupby(atr_code_col)[hrs_cols].sum(numeric_only=True)
            for code, row in agg.iterrows():
                self_sum = float(row.sum())
                if self_sum > 0:
                    hours[str(code)] = self_sum
        
        # Fill missing deliverable codes by matching names
        if atr_std["Deliverable_Code"].isna().any():
            name_to_code = {
                str(r["Deliverable"]).strip(): r["Deliverable_Code"]
                for _, r in di_std.iterrows()
            }
            atr_std["Deliverable_Code"] = atr_std.apply(
                lambda r: r["Deliverable_Code"] if pd.notna(r["Deliverable_Code"]) 
                else name_to_code.get(str(r["Deliverable"]).strip(), None),
                axis=1
            )
        
        # Build index with Deliverable, L1, and L2 rows
        rows = []
        
        # Deliverable level rows
        for _, r in di_std.drop_duplicates(subset=["Deliverable_Code", "Deliverable", "Service_Department"]).iterrows():
            rows.append({
                "Level": LEVEL_DELIVERABLE,
                COL_SERVICE_DEPT: str(r["Service_Department"] or ""),
                COL_DELIV_CODE: str(r["Deliverable_Code"] or ""),
                COL_DELIVERABLE: str(r["Deliverable"] or ""),
                COL_L1_NAME: "",
                COL_L2_NAME: "",
                "Default_Keywords": f"{r['Deliverable']}, {r['Service_Department']}"
            })
        
        # L1 (Component) rows
        l1 = atr_std.dropna(subset=["Component_Task_L1"]).drop_duplicates(
            subset=["Deliverable_Code", "Deliverable", "Service_Department", "Component_Task_L1"]
        )
        for _, r in l1.iterrows():
            rows.append({
                "Level": LEVEL_L1,
                COL_SERVICE_DEPT: str(r["Service_Department"] or ""),
                COL_DELIV_CODE: str(r["Deliverable_Code"] or ""),
                COL_DELIVERABLE: str(r["Deliverable"] or ""),
                COL_L1_NAME: str(r["Component_Task_L1"] or ""),
                COL_L2_NAME: "",
                "Default_Keywords": f"{r['Deliverable']}, {r['Component_Task_L1']}, {r['Service_Department']}"
            })
        
        # L2 (Task) rows
        l2 = atr_std.dropna(subset=["Component_Task_L1", "Task_Task_L2"]).drop_duplicates(
            subset=["Deliverable_Code", "Deliverable", "Service_Department", "Component_Task_L1", "Task_Task_L2"]
        )
        for _, r in l2.iterrows():
            rows.append({
                "Level": LEVEL_L2,
                COL_SERVICE_DEPT: str(r["Service_Department"] or ""),
                COL_DELIV_CODE: str(r["Deliverable_Code"] or ""),
                COL_DELIVERABLE: str(r["Deliverable"] or ""),
                COL_L1_NAME: str(r["Component_Task_L1"] or ""),
                COL_L2_NAME: str(r["Task_Task_L2"] or ""),
                "Default_Keywords": f"{r['Deliverable']}, {r['Component_Task_L1']}, {r['Task_Task_L2']}, {r['Service_Department']}"
            })
        
        idx = pd.DataFrame(rows)
        return idx, hours
    
    def _build_lex(self):
        """Build TF-IDF lexical index"""
        texts = []
        for _, r in self.index.iterrows():
            parts = [
                r.get(COL_DELIVERABLE, ""),
                r.get(COL_L1_NAME, ""),
                r.get(COL_L2_NAME, ""),
                r.get(COL_SERVICE_DEPT, ""),
                r.get("Default_Keywords", "")
            ]
            texts.append(_norm(" ".join([str(p) for p in parts if p])))
        
        # Build IDF
        df_counts: Dict[str, int] = {}
        for t in texts:
            for tok in set(_tok(t)):
                df_counts[tok] = df_counts.get(tok, 0) + 1
        
        N = max(1, len(texts))
        self.idf = {k: math.log(N / (v + 1.0)) for k, v in df_counts.items()}
        
        # Build TF-IDF vectors for each row
        self.row_vecs = []
        for t in texts:
            tf: Dict[str, int] = {}
            for tok in _tok(t):
                tf[tok] = tf.get(tok, 0) + 1
            self.row_vecs.append({k: tf[k] * self.idf.get(k, 0.0) for k in tf})
    
    def _vec(self, text: str) -> Dict[str, float]:
        """Convert text to TF-IDF vector"""
        tf: Dict[str, int] = {}
        for tok in _tok(_norm(text)):
            tf[tok] = tf.get(tok, 0) + 1
        return {k: tf[k] * self.idf.get(k, 0.0) for k in tf}
    
    def _cos(self, v1: Dict[str, float], v2: Dict[str, float]) -> float:
        """Cosine similarity between two vectors"""
        dot = sum(v1.get(k, 0.0) * v2.get(k, 0.0) for k in v1.keys())
        n1 = (sum(v * v for v in v1.values()) ** 0.5) or 1e-9
        n2 = (sum(v * v for v in v2.values()) ** 0.5) or 1e-9
        return max(0.0, min(1.0, dot / (n1 * n2)))
    
    def _dept_intent(self, text: str) -> Dict[str, float]:
        """Detect department intent from RFP text"""
        t = _norm(text)
        
        # Department keyword mapping (matches your 6 departments)
        table = {
            "Paid Media": [
                "paid media", "media buying", "activation", "campaign",
                "google", "facebook", "pinterest", "youtube", "programmatic",
                "optimize", "pacing", "placements"
            ],
            "Creative": [
                "creative asset", "ad asset", "design", "visual", "mockup",
                "key visual", "storyboard", "video", "banner"
            ],
            "Content": [
                "content plan", "content pillar", "editorial", "copywriting",
                "blog", "article", "production"
            ],
            "Strategy": [
                "strategy", "roadmap", "brief", "positioning", "competitive",
                "research", "audience", "kpi framework"
            ],
            "Technology": [
                "web", "website", "landing page", "ga4", "tag", "tracking",
                "conversion", "gcm", "gtm", "analytics", "ecommerce",
                "cross domain", "cross-domain"
            ],
            "Integrated Marketing Management": [
                "social media", "community", "organic", "publishing",
                "creator", "influencer", "calendar"
            ]
        }
        
        scores = {k: 0.0 for k in table}
        for dept, keys in table.items():
            for kw in keys:
                if _contains(t, kw):
                    scores[dept] += 1.0
        
        # Normalize
        mx = max(1.0, max(scores.values()) if scores else 1.0)
        for k in scores:
            scores[k] = scores[k] / mx
        
        return scores
    
    def _extract_meta(self, text: str) -> Dict[str, Any]:
        """Extract budget, timeline, and other metadata from RFP"""
        t = text
        budget = None
        
        # Extract budget (various formats)
        m = re.search(r"budget[^\d$]{0,12}(\$?\s*[0-9][0-9,\.]{2,})", t, flags=re.I)
        if m:
            try:
                budget = float(m.group(1).replace(",", "").replace("$", "").strip())
            except Exception:
                budget = None
        
        # Extract months and quarters
        months = re.findall(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\b", t, flags=re.I)
        qtrs = re.findall(r"\bq[1-4]\b", t, flags=re.I)
        
        return {
            "budget": budget,
            "months": [m.lower() for m in months],
            "quarters": [q.lower() for q in qtrs]
        }
    
    def score(self, rfp_text: str, top_k: int = 25) -> Dict[str, Any]:
        """
        Score deliverables against RFP with department gating, budget awareness, and sparsity
        
        Returns:
            {
                "deliverables": [...],  # Top scored deliverables
                "components": {...},    # Component breakdown by deliverable
                "tasks": {...},         # Task breakdown by deliverable
                "meta": {...}           # Detected departments and budget
            }
        """
        cfg = self.cfg
        idx = self.index.reset_index(drop=True).copy()
        
        if idx.empty:
            return {"deliverables": [], "components": {}, "tasks": {}, "meta": {}}
        
        # Detect department intent
        dept_scores = self._dept_intent(rfp_text or "")
        top_depts = [
            k for k, _ in sorted(dept_scores.items(), key=lambda kv: kv[1], reverse=True)
        ][:max(1, cfg["dept_topK"])]
        
        # Extract metadata (budget, timeline)
        meta = self._extract_meta(rfp_text or "")
        budget = meta.get("budget")
        
        # Compute lexical scores for all rows
        qvec = self._vec(rfp_text or "")
        idx["lex"] = [self._cos(qvec, v) for v in self.row_vecs]
        
        # Score each deliverable
        results = []
        for dcode, grp in idx.groupby(COL_DELIV_CODE):
            # Get deliverable-level row
            drows = grp[grp["Level"] == LEVEL_DELIVERABLE]
            if drows.empty:
                continue
            
            drow = drows.iloc[0]
            dept = str(drow.get(COL_SERVICE_DEPT, ""))
            
            # Deliverable score (combine rule and lexical)
            rule_score_d = float(drow.get("Weight_Base", 0.0)) if "Weight_Base" in drow else 0.0
            s0 = (cfg["w_rule_deliverable"] * rule_score_d + 
                  cfg["w_lex_deliverable"] * float(drow["lex"]))
            
            # L1 component scores (max of rule + lexical)
            l1rows = grp[grp["Level"] == LEVEL_L1]
            s1 = 0.0
            for _, r in l1rows.iterrows():
                rule_score_l1 = float(r.get("Weight_Base", 0.0)) if "Weight_Base" in r else 0.0
                s = (cfg["w_rule_l1"] * rule_score_l1 + 
                     cfg["w_lex_l1"] * float(r["lex"]))
                s1 = max(s1, s)
            
            # L2 task scores (max of rule + lexical)
            l2rows = grp[grp["Level"] == LEVEL_L2]
            s2 = 0.0
            for _, r in l2rows.iterrows():
                rule_score_l2 = float(r.get("Weight_Base", 0.0)) if "Weight_Base" in r else 0.0
                s = (cfg["w_rule_l2"] * rule_score_l2 + 
                     cfg["w_lex_l2"] * float(r["lex"]))
                s2 = max(s2, s)
            
            # Aggregate score
            score = cfg["agg_w_deliverable"] * s0 + cfg["agg_w_l1"] * s1 + cfg["agg_w_l2"] * s2
            
            # Department gating
            if dept not in top_depts:
                score *= cfg["dept_penalty"]
            else:
                score *= cfg["dept_bonus"]
            
            # Execution vs Strategy biasing
            name = str(drow.get(COL_DELIVERABLE, "")).lower()
            if re.search(r"\b(plan|strategy|deck|guideline|style|positioning)\b", name):
                score *= cfg["strategy_penalty"]
            if re.search(r"\b(buy|activat|traffick|optim|report|onboard|execution)\b", name):
                score *= cfg["execution_bonus"]
            
            # Budget penalty
            h = float(self.hours.get(str(dcode), 0.0))
            if budget and h > 0:
                blended = cfg["blended_rate"]
                est_cost = h * blended
                if est_cost > budget * cfg["budget_hard_ceil_multiplier"]:
                    score *= cfg["overbudget_penalty"]
            
            results.append({
                "deliverable_code": dcode,
                "deliverable": drow.get(COL_DELIVERABLE, ""),
                "service_department": dept,
                "score": score
            })
        
        if not results:
            return {"deliverables": [], "components": {}, "tasks": {}, "meta": {}}
        
        # Apply softmax for probability distribution
        base = [r["score"] for r in results]
        probs = _softmax(base, temp=0.6)
        for r, p in zip(results, probs):
            r["prob"] = p
        
        # Sort by probability
        results.sort(key=lambda x: x["prob"], reverse=True)
        
        # Map to percentage bands with sparsity control
        cap = cfg["high_cap"]
        hi = cfg["band_top"]
        mid = cfg["band_mid"]
        low = cfg["band_low"]
        
        def map_band(rank: int, p: float) -> float:
            """Map rank to percentage band"""
            if rank < cap:
                # High band (≥85%) - linear interpolation
                lo, hi_b = hi
                return lo + (hi_b - lo) * (1.0 - rank / max(1, cap - 1)) * 0.85 + 0.10
            elif rank < cap + 6:
                # Mid band (70-84%)
                lo, hi_b = mid
                return lo + (hi_b - lo) * (1.0 - (rank - cap) / 6.0)
            else:
                # Low band (<70%)
                lo, hi_b = low
                return lo + (hi_b - lo) * (1.0 - min(1.0, (rank - cap - 6) / 10.0))
        
        for i, r in enumerate(results):
            r["match_percent"] = round(100.0 * map_band(i, r["prob"]), 1)
        
        # Get component and task details for top deliverables
        top_codes = [r["deliverable_code"] for r in results[:25]]
        components: Dict[str, List[Dict[str, Any]]] = {}
        tasks: Dict[str, List[Dict[str, Any]]] = {}
        
        for code in top_codes:
            grp = idx[idx[COL_DELIV_CODE] == code]
            
            # L1 components
            l1 = grp[grp["Level"] == LEVEL_L1].copy()
            if not l1.empty:
                l1["p"] = l1["lex"]
                l1 = l1.sort_values("p", ascending=False)
                comps = [
                    {
                        "component": rr.get(COL_L1_NAME, ""),
                        "percent": round(100 * _sigmoid(float(rr["p"]), cfg["mu"], cfg["sigma"]), 1)
                    }
                    for _, rr in l1.head(8).iterrows()
                ]
                components[str(code)] = comps
            
            # L2 tasks
            l2 = grp[grp["Level"] == LEVEL_L2].copy()
            if not l2.empty:
                l2["p"] = l2["lex"]
                l2 = l2.sort_values("p", ascending=False)
                tlist = [
                    {
                        "component": rr.get(COL_L1_NAME, ""),
                        "task": rr.get(COL_L2_NAME, ""),
                        "percent": round(100 * _sigmoid(float(rr["p"]), cfg["mu"], cfg["sigma"]), 1)
                    }
                    for _, rr in l2.head(20).iterrows()
                ]
                tasks[str(code)] = tlist
        
        return {
            "deliverables": results[:top_k],
            "components": components,
            "tasks": tasks,
            "meta": {
                "top_departments": top_depts,
                "budget": budget
            }
        }
