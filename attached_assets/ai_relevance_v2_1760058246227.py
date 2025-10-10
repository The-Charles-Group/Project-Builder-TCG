
import re, math, glob, os
from typing import Dict, Any, List
from pathlib import Path
import pandas as pd

LEVEL_DELIVERABLE = "Deliverable"
LEVEL_L1 = "L1"
LEVEL_L2 = "L2"

COL_SERVICE_DEPT = "Service_Department"
COL_DELIV_CODE   = "Deliverable_Code"
COL_DELIVERABLE  = "Deliverable"
COL_L1_NAME      = "L1_Component_Name"
COL_L2_NAME      = "L2_Task_Name"

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+"," ", (s or "").lower()).strip()

def _tok(s: str):
    return [t for t in re.findall(r"[a-z0-9]+", _norm(s)) if t]

def _contains(text: str, phrase: str) -> bool:
    p = re.escape((phrase or "").lower())
    return re.search(rf"\b{p}\b", text) is not None

def _sigmoid(x: float, mu: float, sigma: float) -> float:
    return 1.0 / (1.0 + math.exp(-(x - mu) / (sigma if sigma else 0.25)))

def _softmax(xs, temp: float = 1.0):
    if not xs: return []
    m = max(xs)
    es = [math.exp((x - m)/max(1e-6, temp)) for x in xs]
    s = sum(es) or 1e-9
    return [e/s for e in es]

class RelevanceEngineV2:
    def __init__(self, workbook_path: str | None = None):
        self.index, self.hours = self._load_or_build_index(workbook_path)
        self.cfg = {
            "w_rule_deliverable": 0.60, "w_lex_deliverable": 0.40,
            "w_rule_l1": 0.65, "w_lex_l1": 0.35,
            "w_rule_l2": 0.70, "w_lex_l2": 0.30,
            "agg_w_deliverable": 1.0, "agg_w_l1": 0.9, "agg_w_l2": 0.8,
            "mu": 0.6, "sigma": 0.25,
            "dept_topK": 2, "dept_penalty": 0.35, "dept_bonus": 1.10,
            "strategy_penalty": 0.6, "execution_bonus": 1.15,
            "high_cap": 4,
            "band_top": (0.87, 1.00),
            "band_mid": (0.70, 0.84),
            "band_low": (0.40, 0.69),
            "blended_rate": 125.0,
            "budget_hard_ceil_multiplier": 1.10,
            "overbudget_penalty": 0.6,
        }
        self._build_lex()

    def _find_db_workbook(self) -> str | None:
        patterns = ["Replit_App_DB_READABLE*.xlsx","*DB_READABLE*.xlsx","*.xlsx"]
        roots = [".","./data","/app/data","/workspace","/home/runner","/mnt/data"]
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

    def _load_or_build_index(self, workbook_path: str | None):
        idx = None
        hours = {}
        if workbook_path and Path(workbook_path).exists():
            try:
                x = pd.ExcelFile(workbook_path)
                if "AI_Index" in x.sheet_names:
                    idx = pd.read_excel(x, "AI_Index")
            except Exception:
                idx = None
        if idx is not None:
            return idx, hours

        db = self._find_db_workbook()
        if not db:
            cols = [COL_SERVICE_DEPT,COL_DELIV_CODE,COL_DELIVERABLE,COL_L1_NAME,COL_L2_NAME,"Level","Default_Keywords"]
            return pd.DataFrame(columns=cols), {}

        xl = pd.ExcelFile(db)
        di = pd.read_excel(xl, "Deliverable_Index")
        atr = pd.read_excel(xl, "All_Task_Rows")

        def nmap(df): return {re.sub(r"[^a-z0-9]+","_", c.lower()): c for c in df.columns}
        di_map = nmap(di); atr_map = nmap(atr)
        def pick(m, *c): 
            for k in c:
                if k in m: return m[k]
            return None

        di_std = pd.DataFrame({
            "Deliverable_Code": di[pick(di_map,"deliverable_code","code","id")] if pick(di_map,"deliverable_code","code","id") else None,
            "Deliverable": di[pick(di_map,"deliverable","deliverable_name","name")] if pick(di_map,"deliverable","deliverable_name","name") else None,
            "Service_Department": di[pick(di_map,"service_department","department","dept")] if pick(di_map,"service_department","department","dept") else ""
        }).dropna(subset=["Deliverable"])

        atr_std = pd.DataFrame({
            "Service_Department": atr[pick(atr_map,"service_department","department","dept")] if pick(atr_map,"service_department","department","dept") else "",
            "Deliverable_Code": atr[pick(atr_map,"deliverable_code","code","id")] if pick(atr_map,"deliverable_code","code","id") else None,
            "Deliverable": atr[pick(atr_map,"deliverable","deliverable_name","name")] if pick(atr_map,"deliverable","deliverable_name","name") else None,
            "Component_Task_L1": atr[pick(atr_map,"component_task_l1","component","task_l1","l1")] if pick(atr_map,"component_task_l1","component","task_l1","l1") else None,
            "Task_Task_L2": atr[pick(atr_map,"task_task_l2","task","l2")] if pick(atr_map,"task_task_l2","task","l2") else None
        }).dropna(subset=["Deliverable"])

        # Estimate relative hours if present
        hrs_cols = [c for c in atr.columns if re.search(r"hour|hrs", c, re.I)]
        if hrs_cols:
            key = pick(atr_map,"deliverable_code","code","id")
            if key:
                agg = atr.groupby(key)[hrs_cols].sum(numeric_only=True)
                for code, row in agg.iterrows():
                    self_sum = float(row.sum())
                    if self_sum > 0:
                        hours[str(code)] = self_sum

        if atr_std["Deliverable_Code"].isna().any():
            name_to_code = {str(r["Deliverable"]).strip(): r["Deliverable_Code"] for _, r in di_std.iterrows()}
            atr_std["Deliverable_Code"] = atr_std.apply(lambda r: r["Deliverable_Code"] if pd.notna(r["Deliverable_Code"]) else name_to_code.get(str(r["Deliverable"]).strip(), None), axis=1)

        rows = []
        for _, r in di_std.drop_duplicates(subset=["Deliverable_Code","Deliverable","Service_Department"]).iterrows():
            rows.append({"Level":LEVEL_DELIVERABLE, COL_SERVICE_DEPT:str(r["Service_Department"] or ""),
                         COL_DELIV_CODE:str(r["Deliverable_Code"] or ""), COL_DELIVERABLE:str(r["Deliverable"] or ""),
                         COL_L1_NAME:"", COL_L2_NAME:"", "Default_Keywords":f"{r['Deliverable']}, {r['Service_Department']}"})
        l1 = atr_std.dropna(subset=["Component_Task_L1"]).drop_duplicates(subset=["Deliverable_Code","Deliverable","Service_Department","Component_Task_L1"])
        for _, r in l1.iterrows():
            rows.append({"Level":LEVEL_L1, COL_SERVICE_DEPT:str(r["Service_Department"] or ""),
                         COL_DELIV_CODE:str(r["Deliverable_Code"] or ""), COL_DELIVERABLE:str(r["Deliverable"] or ""),
                         COL_L1_NAME:str(r["Component_Task_L1"] or ""), COL_L2_NAME:"",
                         "Default_Keywords":f"{r['Deliverable']}, {r['Component_Task_L1']}, {r['Service_Department']}"})
        l2 = atr_std.dropna(subset=["Component_Task_L1","Task_Task_L2"]).drop_duplicates(subset=["Deliverable_Code","Deliverable","Service_Department","Component_Task_L1","Task_Task_L2"])
        for _, r in l2.iterrows():
            rows.append({"Level":LEVEL_L2, COL_SERVICE_DEPT:str(r["Service_Department"] or ""),
                         COL_DELIV_CODE:str(r["Deliverable_Code"] or ""), COL_DELIVERABLE:str(r["Deliverable"] or ""),
                         COL_L1_NAME:str(r["Component_Task_L1"] or ""), COL_L2_NAME:str(r["Task_Task_L2"] or ""),
                         "Default_Keywords":f"{r['Deliverable']}, {r['Component_Task_L1']}, {r['Task_Task_L2']}, {r['Service_Department']}"})
        idx = pd.DataFrame(rows)
        return idx, hours

    def _build_lex(self):
        texts = []
        for _, r in self.index.iterrows():
            parts = [r.get(COL_DELIVERABLE,""), r.get(COL_L1_NAME,""), r.get(COL_L2_NAME,""),
                     r.get(COL_SERVICE_DEPT,""), r.get("Default_Keywords","")]
            texts.append(_norm(" ".join([str(p) for p in parts if p])))
        df_counts = {}
        for t in texts:
            for tok in set(_tok(t)): df_counts[tok] = df_counts.get(tok,0)+1
        N = max(1,len(texts))
        self.idf = {k: math.log(N/(v+1.0)) for k,v in df_counts.items()}
        self.row_vecs = []
        for t in texts:
            tf = {}
            for tok in _tok(t): tf[tok]=tf.get(tok,0)+1
            self.row_vecs.append({k: tf[k]*self.idf.get(k,0.0) for k in tf})

    def _vec(self, text: str):
        tf = {}
        for tok in _tok(_norm(text)): tf[tok]=tf.get(tok,0)+1
        return {k: tf[k]*self.idf.get(k,0.0) for k in tf}

    def _cos(self, v1, v2) -> float:
        dot = sum(v1.get(k,0.0)*v2.get(k,0.0) for k in v1.keys())
        n1 = (sum(v*v for v in v1.values()) ** 0.5) or 1e-9
        n2 = (sum(v*v for v in v2.values()) ** 0.5) or 1e-9
        return max(0.0, min(1.0, dot/(n1*n2)))

    def _dept_intent(self, text: str):
        t = _norm(text)
        table = {
            "Paid Media": ["paid media","media buying","activation","campaign","google","facebook","pinterest","youtube","programmatic","optimize","pacing","placements"],
            "Creative": ["creative asset","ad asset","design","visual","mockup","key visual","storyboard","video","banner"],
            "Content": ["content plan","content pillar","editorial","copywriting","blog","article","production"],
            "Strategy": ["strategy","roadmap","brief","positioning","competitive","research","audience","kpi framework"],
            "Technology": ["web","website","landing page","ga4","tag","tracking","conversion","gcm","gtm","analytics","ecommerce","cross domain","cross-domain"],
            "Integrated Marketing Management": ["social media","community","organic","publishing","creator","influencer","calendar"]
        }
        scores = {k:0.0 for k in table}
        for dept, keys in table.items():
            for kw in keys:
                if _contains(t, kw):
                    scores[dept] += 1.0
        mx = max(1.0, max(scores.values()) if scores else 1.0)
        for k in scores: scores[k] = scores[k]/mx
        return scores

    def _extract_meta(self, text: str):
        t = text
        budget = None
        m = re.search(r"budget[^\\d$]{0,12}(\\$?\\s*[0-9][0-9,\\.]{2,})", t, flags=re.I)
        if m:
            try:
                budget = float(m.group(1).replace(",","").replace("$","").strip())
            except Exception:
                budget = None
        months = re.findall(r"\\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\\w*\\b", t, flags=re.I)
        qtrs = re.findall(r"\\bq[1-4]\\b", t, flags=re.I)
        return {"budget": budget, "months": [m.lower() for m in months], "quarters": [q.lower() for q in qtrs]}

    def score(self, rfp_text: str, top_k: int = 25):
        cfg = self.cfg
        idx = self.index.reset_index(drop=True).copy()
        if idx.empty:
            return {"deliverables": [], "components": {}, "tasks": {}}

        dept_scores = self._dept_intent(rfp_text or "")
        top_depts = [k for k,_ in sorted(dept_scores.items(), key=lambda kv: kv[1], reverse=True)][:max(1,cfg["dept_topK"])]
        meta = self._extract_meta(rfp_text or "")
        budget = meta.get("budget")

        qvec = self._vec(rfp_text or "")
        idx["lex"] = [self._cos(qvec, v) for v in self.row_vecs]

        results = []
        for dcode, grp in idx.groupby(COL_DELIV_CODE):
            drows = grp[grp["Level"]==LEVEL_DELIVERABLE]
            if drows.empty: continue
            drow = drows.iloc[0]
            dept = str(drow.get(COL_SERVICE_DEPT,""))
            s0 = cfg["w_lex_deliverable"]*float(drow["lex"])
            l1rows = grp[grp["Level"]==LEVEL_L1]
            s1 = 0.0
            for _, r in l1rows.iterrows():
                s = cfg["w_lex_l1"]*float(r["lex"]); s1 = max(s1,s)
            l2rows = grp[grp["Level"]==LEVEL_L2]
            s2 = 0.0
            for _, r in l2rows.iterrows():
                s = cfg["w_lex_l2"]*float(r["lex"]); s2 = max(s2,s)
            score = cfg["agg_w_deliverable"]*s0 + cfg["agg_w_l1"]*s1 + cfg["agg_w_l2"]*s2

            # Department gating
            if dept not in top_depts: score *= cfg["dept_penalty"]
            else: score *= cfg["dept_bonus"]

            # Execution vs strategy biasing
            name = str(drow.get(COL_DELIVERABLE,"")).lower()
            if re.search(r"\\b(plan|strategy|deck|guideline|style|positioning)\\b", name): score *= cfg["strategy_penalty"]
            if re.search(r"\\b(buy|activat|traffick|optim|report|onboard|execution)\\b", name): score *= cfg["execution_bonus"]

            # Budget penalty
            h = float(self.hours.get(str(dcode), 0.0))
            if budget and h>0:
                blended = cfg["blended_rate"]
                est_cost = h*blended
                if est_cost > budget*cfg["budget_hard_ceil_multiplier"]:
                    score *= cfg["overbudget_penalty"]

            results.append({"deliverable_code": dcode, "deliverable": drow.get(COL_DELIVERABLE,""),
                            "service_department": dept, "score": score})

        if not results:
            return {"deliverables": [], "components": {}, "tasks": {}}

        base = [r["score"] for r in results]
        probs = _softmax(base, temp=0.6)
        for r,p in zip(results, probs): r["prob"] = p
        results.sort(key=lambda x: x["prob"], reverse=True)

        cap = cfg["high_cap"]; hi = cfg["band_top"]; mid = cfg["band_mid"]; low = cfg["band_low"]
        def map_band(rank, p):
            if rank < cap:
                lo, hi_b = hi; return lo + (hi_b-lo)*(1.0 - rank/max(1,cap-1))*0.85 + 0.10
            elif rank < cap+6:
                lo, hi_b = mid; return lo + (hi_b-lo)*(1.0 - (rank-cap)/6.0)
            else:
                lo, hi_b = low; return lo + (hi_b-lo)*(1.0 - min(1.0, (rank-cap-6)/10.0))
        for i,r in enumerate(results):
            r["match_percent"] = round(100.0*map_band(i, r["prob"]), 1)

        top_codes = [r["deliverable_code"] for r in results[:25]]
        components, tasks = {}, {}
        for code in top_codes:
            grp = idx[idx[COL_DELIV_CODE]==code]
            l1 = grp[grp["Level"]==LEVEL_L1].copy()
            l1["p"] = l1["lex"]; l1.sort_values("p", ascending=False, inplace=True)
            comps = [{"component": rr.get(COL_L1_NAME,""), "percent": round(100*_sigmoid(float(rr["p"]), self.cfg["mu"], self.cfg["sigma"]),1)}
                     for _, rr in l1.head(8).iterrows()]
            components[str(code)] = comps
            l2 = grp[grp["Level"]==LEVEL_L2].copy()
            l2["p"] = l2["lex"]; l2.sort_values("p", ascending=False, inplace=True)
            tlist = [{"component": rr.get(COL_L1_NAME,""), "task": rr.get(COL_L2_NAME,""), "percent": round(100*_sigmoid(float(rr["p"]), self.cfg["mu"], self.cfg["sigma"]),1)}
                     for _, rr in l2.head(20).iterrows()]
            tasks[str(code)] = tlist

        return {"deliverables": results[:top_k], "components": components, "tasks": tasks,
                "meta": {"top_departments": top_depts, "budget": budget}}
