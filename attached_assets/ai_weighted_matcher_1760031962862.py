# (file content abbreviated here for brevity in notebook; same as previous matcher with levels Deliverable/L1/L2)
# To save space in this cell, we reuse the previously generated matcher that computes weighted percent and returns
# deliverables + components + tasks. (Full content inserted now.)
import re, math, json, os
from typing import List, Dict, Any, Tuple
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

def _normalize_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+"," ", (s or "").lower()).strip()

def _contains_phrase(text: str, phrase: str) -> bool:
    p = re.escape((phrase or "").lower())
    return re.search(rf"\b{p}\b", text) is not None

def _tokenize(s: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t]

class AIMatchingEngine:
    def __init__(self, workbook_path: str):
        self.workbook_path = workbook_path
        self.index = pd.read_excel(workbook_path, sheet_name="AI_Index")
        self.rules = pd.read_excel(workbook_path, sheet_name="AI_Matching_Rules")
        try:
            self.cfg = pd.read_excel(workbook_path, sheet_name="AI_Config")
        except Exception:
            self.cfg = pd.DataFrame(columns=["Key","Value"])
        self.cfg_map = {str(k): float(v) for k, v in zip(self.cfg.get("Key",[]), self.cfg.get("Value",[]))}
        self._build_lex_index()

    def cfg_get(self, key: str, default: float) -> float:
        try:
            return float(self.cfg_map.get(key, default))
        except Exception:
            return default

    def _build_lex_index(self):
        texts = []
        for _, r in self.index.iterrows():
            parts = [
                r.get(COL_DELIVERABLE, ""),
                r.get(COL_L1_NAME, ""),
                r.get(COL_L2_NAME, ""),
                r.get(COL_SERVICE_DEPT, ""),
                r.get("Default_Keywords","")
            ]
            texts.append(_normalize_text(" ".join([str(p) for p in parts if p])))

        df_counts = {}
        for t in texts:
            toks = set(_tokenize(t))
            for tok in toks:
                df_counts[tok] = df_counts.get(tok, 0) + 1
        N = max(1, len(texts))
        self.idf = {tok: math.log(N / (df_counts[tok] + 1.0)) for tok in df_counts}
        self.row_vecs = []
        for t in texts:
            tf = {}
            toks = _tokenize(t)
            for tok in toks:
                tf[tok] = tf.get(tok, 0) + 1
            vec = {tok: (tf[tok] * self.idf.get(tok, 0.0)) for tok in tf}
            self.row_vecs.append(vec)

    def _cosine(self, v1: Dict[str,float], v2: Dict[str,float]) -> float:
        dot = 0.0
        for k, w in v1.items():
            if k in v2:
                dot += w * v2[k]
        n1 = math.sqrt(sum(w*w for w in v1.values())) or 1e-9
        n2 = math.sqrt(sum(w*w for w in v2.values())) or 1e-9
        return max(0.0, min(1.0, dot/(n1*n2)))

    def _text_vec(self, text: str) -> Dict[str,float]:
        tf = {}
        toks = _tokenize(_normalize_text(text))
        for tok in toks:
            tf[tok] = tf.get(tok, 0) + 1
        return {tok: (tf[tok] * self.idf.get(tok, 0.0)) for tok in tf}

    def _rule_match_score(self, level: str, row: pd.Series, rfp_text_norm: str) -> float:
        subset = self.rules[self.rules["Level"]==level]
        dcode = str(row.get(COL_DELIV_CODE,"") or "")
        dname = str(row.get(COL_DELIVERABLE,"") or "")
        cname = str(row.get(COL_L1_NAME,"") or "")
        tname = str(row.get(COL_L2_NAME,"") or "")

        cand = subset[(subset["Deliverable_Code"].astype(str)==dcode) | (subset["Deliverable_Name"].astype(str)==dname)]
        if level == LEVEL_L1:
            cand = cand[(cand["L1_Component_Name"].astype(str)==cname)]
        if level == LEVEL_L2:
            cand = cand[(cand["L1_Component_Name"].astype(str)==cname) & (cand["L2_Task_Name"].astype(str)==tname)]
        if cand.empty:
            return 0.0

        best = 0.0
        for _, rr in cand.iterrows():
            prio = float(rr.get("Priority", 5))
            any_phr = [p.strip() for p in str(rr.get("Keywords_Any","")).split(",") if p.strip()]
            all_phr = [p.strip() for p in str(rr.get("Keywords_All","")).split(",") if p.strip()]
            ex_phr  = [p.strip() for p in str(rr.get("Exclude_Keywords","")).split(",") if p.strip()]
            ctx_pat = str(rr.get("Context_Pattern","") or "").strip()

            any_ok = True if not any_phr else any(_contains_phrase(rfp_text_norm, p) for p in any_phr)
            all_ok = True if not all_phr else all(_contains_phrase(rfp_text_norm, p) for p in all_phr)
            ex_ok  = not any(_contains_phrase(rfp_text_norm, p) for p in ex_phr) if ex_phr else True
            ctx_ok = self._eval_ctx(rfp_text_norm, ctx_pat)

            if any_ok and all_ok and ex_ok and ctx_ok:
                richness = 1.0
                if any_phr:
                    m = sum(1 for p in any_phr if _contains_phrase(rfp_text_norm, p))
                    richness = m / max(1, len(any_phr))
                score = min(1.0, (prio/10.0) * (0.6 + 0.4*richness))
                best = max(best, score)
        return best

    def _eval_ctx(self, text: str, pattern: str) -> bool:
        if not pattern: return True
        tokens = re.split(r"\s+(AND|OR|NOT)\s+", pattern, flags=re.IGNORECASE)
        vals, ops = [], []
        for t in tokens:
            tt = t.strip()
            if tt.upper() in ("AND","OR","NOT"):
                ops.append(tt.upper())
            elif tt != "":
                vals.append(_contains_phrase(text, tt))
        j=0
        while j < len(ops):
            if ops[j] == "NOT":
                vals[j+1] = (not vals[j+1]); ops.pop(j)
            else: j += 1
        j=0
        while j < len(ops):
            if ops[j] == "AND":
                vals[j] = vals[j] and vals[j+1]; vals.pop(j+1); ops.pop(j)
            else: j += 1
        out = vals[0] if vals else True
        for k,op in enumerate(ops):
            out = out or vals[k+1]
        return out

    def _sigmoid(self, x: float, mu: float, sigma: float) -> float:
        return 1.0 / (1.0 + math.exp(-(x - mu) / (sigma if sigma else 0.25)))

    def score(self, rfp_text: str, top_k: int = 20) -> Dict[str, Any]:
        rfp_norm = _normalize_text(rfp_text or "")
        q_vec = self._text_vec(rfp_text or "")

        w_rule_d = self.cfg_get("w_rule_deliverable", 0.60)
        w_rule_l1= self.cfg_get("w_rule_l1", 0.65)
        w_rule_l2= self.cfg_get("w_rule_l2", 0.70)
        w_lex_d  = self.cfg_get("w_lex_deliverable", 0.40)
        w_lex_l1 = self.cfg_get("w_lex_l1", 0.35)
        w_lex_l2 = self.cfg_get("w_lex_l2", 0.30)

        agg_w_d  = self.cfg_get("agg_w_deliverable", 1.0)
        agg_w_l1 = self.cfg_get("agg_w_l1", 0.9)
        agg_w_l2 = self.cfg_get("agg_w_l2", 0.8)

        mu = self.cfg_get("sigmoid_mu", 0.6)
        sigma = self.cfg_get("sigmoid_sigma", 0.25)
        thr = self.cfg_get("min_score_threshold", 0.02)

        idx = self.index.reset_index(drop=True).copy()

        # Build lexical vectors for rows
        texts = []
        for _, r in idx.iterrows():
            parts = [
                r.get(COL_DELIVERABLE, ""),
                r.get(COL_L1_NAME, ""),
                r.get(COL_L2_NAME, ""),
                r.get(COL_SERVICE_DEPT, ""),
                r.get("Default_Keywords","")
            ]
            texts.append(_normalize_text(" ".join([str(p) for p in parts if p])))
        # IDF
        df_counts = {}
        for t in texts:
            for tok in set(_tokenize(t)):
                df_counts[tok] = df_counts.get(tok, 0) + 1
        N = max(1, len(texts))
        idf = {tok: math.log(N / (df_counts[tok] + 1.0)) for tok in df_counts}
        def vec_for(text):
            tf = {}
            for tok in _tokenize(_normalize_text(text)):
                tf[tok] = tf.get(tok, 0) + 1
            return {tok: (tf[tok] * idf.get(tok, 0.0)) for tok in tf}
        row_vecs = [vec_for(t) for t in texts]
        def cosine(v1, v2):
            dot = sum(v1.get(k,0.0)*v2.get(k,0.0) for k in v1.keys())
            n1 = (sum(v*v for v in v1.values()) ** 0.5) or 1e-9
            n2 = (sum(v*v for v in v2.values()) ** 0.5) or 1e-9
            return max(0.0, min(1.0, dot/(n1*n2)))
        idx["lex_score"] = [cosine(q_vec, v) for v in row_vecs]

        results = []
        for dcode, grp in idx.groupby(COL_DELIV_CODE):
            d_rows = grp[grp["Level"]==LEVEL_DELIVERABLE]
            if d_rows.empty: continue
            drow = d_rows.iloc[0]

            s0_rule = self._rule_match_score(LEVEL_DELIVERABLE, drow, rfp_norm)
            s0_lex  = float(drow["lex_score"])
            s0 = w_rule_d * s0_rule + w_lex_d * s0_lex

            l1_rows = grp[grp["Level"]==LEVEL_L1]
            best_l1 = 0.0
            for _, r in l1_rows.iterrows():
                s_rule = self._rule_match_score(LEVEL_L1, r, rfp_norm)
                s_lex  = float(r["lex_score"])
                s = w_rule_l1 * s_rule + w_lex_l1 * s_lex
                best_l1 = max(best_l1, s)

            l2_rows = grp[grp["Level"]==LEVEL_L2]
            best_l2 = 0.0
            for _, r in l2_rows.iterrows():
                s_rule = self._rule_match_score(LEVEL_L2, r, rfp_norm)
                s_lex  = float(r["lex_score"])
                s = w_rule_l2 * s_rule + w_lex_l2 * s_lex
                best_l2 = max(best_l2, s)

            score = agg_w_d * s0 + agg_w_l1 * best_l1 + agg_w_l2 * best_l2
            if score < thr: continue
            pct = round(100.0 * self._sigmoid(score, mu, sigma), 1)

            results.append({
                "deliverable_code": drow.get(COL_DELIV_CODE, ""),
                "deliverable": drow.get(COL_DELIVERABLE, ""),
                "service_department": drow.get(COL_SERVICE_DEPT, ""),
                "match_percent": pct,
                "explain": {"s0_rule": round(s0_rule,4), "s0_lex": round(s0_lex,4)}
            })

        results.sort(key=lambda x: x["match_percent"], reverse=True)
        top_deliverables = results[:top_k]

        components_map, tasks_map = {}, {}
        codes = set([r["deliverable_code"] for r in top_deliverables])
        for code in codes:
            grp = idx[idx[COL_DELIV_CODE]==code]
            l1_rows = grp[grp["Level"]==LEVEL_L1]
            l2_rows = grp[grp["Level"]==LEVEL_L2]
            comps = []
            for _, r in l1_rows.iterrows():
                s_rule = self._rule_match_score(LEVEL_L1, r, rfp_norm)
                s_lex  = float(r["lex_score"])
                s = w_rule_l1 * s_rule + w_lex_l1 * s_lex
                pct = round(100.0 * self._sigmoid(s, mu, sigma), 1)
                comps.append({"component": r.get(COL_L1_NAME,""), "percent": pct})
            comps.sort(key=lambda x: x["percent"], reverse=True)
            components_map[str(code)] = comps[:10]
            tlist = []
            for _, r in l2_rows.iterrows():
                s_rule = self._rule_match_score(LEVEL_L2, r, rfp_norm)
                s_lex  = float(r["lex_score"])
                s = w_rule_l2 * s_rule + w_lex_l2 * s_lex
                pct = round(100.0 * self._sigmoid(s, mu, sigma), 1)
                tlist.append({"component": r.get(COL_L1_NAME,""), "task": r.get(COL_L2_NAME,""), "percent": pct})
            tlist.sort(key=lambda x: x["percent"], reverse=True)
            tasks_map[str(code)] = tlist[:25]

        return {"deliverables": top_deliverables, "components": components_map, "tasks": tasks_map}
