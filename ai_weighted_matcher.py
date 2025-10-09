
# ai_weighted_matcher.py
# Self-contained weighted matching engine for Agency Project Builder (L1/L2/L3).
# Drop this file into your server package and import score_rfp().
# No external deps beyond pandas.

from __future__ import annotations
import math, re
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple
import pandas as pd

# -----------------------------
# Tokenization / TF-IDF basics
# -----------------------------

TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")

def tokenize(text: str) -> List[str]:
    if not isinstance(text, str):
        text = str(text or "")
    return TOKEN_RE.findall(text.lower())

def build_tfidf(ai_index_df: pd.DataFrame) -> Dict[str, Any]:
    docs = []
    for _, row in ai_index_df.iterrows():
        parts = []
        for k in ["Default_Keywords","Deliverable","Component_Task_L1","Task_Task_L2","Service_Department","Category"]:
            v = row.get(k, "")
            if pd.isna(v):
                v = ""
            parts.append(str(v))
        text = " ".join(parts)
        tokens = tokenize(text)
        docs.append(tokens)
    N = len(docs)
    df_counts = Counter()
    for tokens in docs:
        df_counts.update(set(tokens))
    idf = {t: math.log((N+1)/(df_counts[t]+1)) + 1 for t in df_counts}
    doc_tfidf = []
    doc_norm = []
    for tokens in docs:
        tf = Counter(tokens)
        vec = {t: tf[t]*idf.get(t,0.0) for t in tf}
        norm = math.sqrt(sum(w*w for w in vec.values())) or 1.0
        doc_tfidf.append(vec)
        doc_norm.append(norm)
    return {"idf":idf, "doc_tfidf":doc_tfidf, "doc_norm":doc_norm}

def compute_lexical_scores(rfp_text: str, tfidf_idx: Dict[str, Any]) -> List[float]:
    idf = tfidf_idx["idf"]
    doc_tfidf = tfidf_idx["doc_tfidf"]
    doc_norm = tfidf_idx["doc_norm"]
    q_tokens = tokenize(rfp_text)
    q_tf = Counter(q_tokens)
    q_vec = {t: q_tf[t]*idf.get(t,0.0) for t in q_tf}
    q_norm = math.sqrt(sum(w*w for w in q_vec.values())) or 1.0
    sims = []
    for vec, dnorm in zip(doc_tfidf, doc_norm):
        dot = 0.0
        for t, w in q_vec.items():
            if t in vec:
                dot += w * vec[t]
        sims.append(dot / (q_norm * dnorm))
    return sims

# -----------------------------
# Rule engine (sheet-driven)
# -----------------------------

def _contains(text: str, phrase: str) -> bool:
    p = re.escape(str(phrase).lower())
    return re.search(rf"\b{p}\b", text) is not None

def _split_csv(v) -> List[str]:
    if pd.isna(v) or v is None:
        return []
    return [s.strip() for s in str(v).split(",") if s.strip()]

def eval_rules(rfp_text: str, ai_rules_df: pd.DataFrame) -> Tuple[List[float], List[dict]]:
    text = (rfp_text or "").lower()
    hits = [0.0]*len(ai_rules_df)
    why = [{} for _ in range(len(ai_rules_df))]
    for i, row in ai_rules_df.iterrows():
        any_list = _split_csv(row.get("Keywords_Any"))
        all_list = _split_csv(row.get("Keywords_All"))
        exc_list = _split_csv(row.get("Exclude_Keywords"))
        any_ok = (not any_list) or any(_contains(text, p) for p in any_list)
        all_ok = (not all_list) or all(_contains(text, p) for p in all_list)
        exc_ok = not any(_contains(text, p) for p in exc_list) if exc_list else True
        if any_ok and all_ok and exc_ok:
            pri = float(row.get("Priority") or 5.0)
            hits[i] = pri/10.0
            why[i] = {
                "rule_id": row.get("Rule_ID"),
                "matched_any": [p for p in any_list if _contains(text, p)],
                "priority": pri,
                "level": row.get("Level")
            }
    return hits, why

# -----------------------------
# Scoring & aggregation
# -----------------------------

def _cfg(config: Dict[str, Any], key: str, default: float) -> float:
    try:
        return float(config.get(key, default))
    except Exception:
        return default

def aggregate_scores(ai_index_df: pd.DataFrame,
                     lex_scores: List[float],
                     ai_rules_df: pd.DataFrame,
                     rule_hits: List[float],
                     config: Dict[str, Any]) -> Dict[str, Any]:
    w_rule_l1 = _cfg(config, "w_rule_l1", 0.6)
    w_rule_l2 = _cfg(config, "w_rule_l2", 0.65)
    w_rule_l3 = _cfg(config, "w_rule_l3", 0.7)
    w_lex_l1  = _cfg(config, "w_lexical_l1", 0.4)
    w_lex_l2  = _cfg(config, "w_lexical_l2", 0.35)
    w_lex_l3  = _cfg(config, "w_lexical_l3", 0.3)
    comp_mult = _cfg(config, "component_weight_multiplier", 0.9)
    task_mult = _cfg(config, "task_weight_multiplier", 0.8)

    # Index rules by (level, dcode, component_name, task_name)
    rule_map = {}
    for i, rr in ai_rules_df.iterrows():
        key = (str(rr.get("Level")).strip(),
               str(rr.get("Deliverable_Code")).strip(),
               str(rr.get("Component_Name") or "").strip().lower(),
               str(rr.get("Task_Name") or "").strip().lower())
        rule_map.setdefault(key, []).append(i)

    l1_scores = defaultdict(lambda: {"lex":0.0, "rule":0.0, "rows":[]})
    l2_details = defaultdict(list)   # code -> list[(row_idx, score)]
    l3_details = defaultdict(list)

    for idx, row in ai_index_df.iterrows():
        code = row["Deliverable_Code"]
        level = row["Level"]
        comp = str(row.get("Component_Task_L1") or "").strip()
        task = str(row.get("Task_Task_L2") or "").strip()
        key = (level, code, comp.lower() if comp else "", task.lower() if task else "")
        # max rule hit for this key
        rhit = 0.0
        for rule_idx in rule_map.get(key, []):
            rhit = max(rhit, rule_hits[rule_idx])
        lex = float(lex_scores[idx])

        if level == "L1":
            l1_scores[code]["lex"] = max(l1_scores[code]["lex"], lex)
            l1_scores[code]["rule"] = max(l1_scores[code]["rule"], rhit)
            l1_scores[code]["rows"].append(idx)
        elif level == "L2":
            sc = w_rule_l2 * rhit + w_lex_l2 * lex
            l2_details[code].append((idx, sc))
        else:
            sc = w_rule_l3 * rhit + w_lex_l3 * lex
            l3_details[code].append((idx, sc))

    final = {}
    for code in ai_index_df["Deliverable_Code"].unique():
        base = l1_scores.get(code, {"lex":0.0, "rule":0.0, "rows":[]})
        sc_l1 = w_rule_l1*base["rule"] + w_lex_l1*base["lex"]
        comp_best = max([sc for (_, sc) in l2_details.get(code, [])] or [0.0])
        task_best = max([sc for (_, sc) in l3_details.get(code, [])] or [0.0])
        sc = sc_l1 + comp_mult*comp_best + task_mult*task_best
        final[code] = {
            "score": sc,
            "l1_parts": base,
            "comp_best": comp_best,
            "task_best": task_best,
            "l2_list": sorted(l2_details.get(code, []), key=lambda x: x[1], reverse=True)[:12],
            "l3_list": sorted(l3_details.get(code, []), key=lambda x: x[1], reverse=True)[:12],
        }
    return final

def normalize_to_percent(scores_dict: Dict[str, Any], min_threshold: float=0.02) -> Dict[str, Any]:
    vals = [v["score"] for v in scores_dict.values()]
    maxv = max(vals) if vals else 1.0
    out = {}
    for code, data in scores_dict.items():
        sc = data["score"]
        pct = 0.0 if sc < min_threshold else (sc / maxv) * 100.0
        out[code] = {**data, "percent": pct}
    return out

# -----------------------------
# Public API
# -----------------------------

def load_ai_package(ai_xlsx_path: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    xls = pd.ExcelFile(ai_xlsx_path)
    rules = pd.read_excel(xls, sheet_name="AI_Matching_Rules")
    index_df = pd.read_excel(xls, sheet_name="AI_Index")
    cfg_df = pd.read_excel(xls, sheet_name="AI_Config")
    config = {row["Param"]: float(row["Value"]) if isinstance(row["Value"], (int,float)) else row["Value"]
              for _, row in cfg_df.iterrows()}
    return rules, index_df, config

def score_rfp(rfp_text: str,
              ai_xlsx_path: str,
              deliverable_index_df: pd.DataFrame | None = None) -> Dict[str, Any]:
    rules, index_df, config = load_ai_package(ai_xlsx_path)
    tfidf_idx = build_tfidf(index_df)
    lex_scores = compute_lexical_scores(rfp_text, tfidf_idx)
    rule_hits, rules_why = eval_rules(rfp_text, rules)
    agg = aggregate_scores(index_df, lex_scores, rules, rule_hits, config)
    final = normalize_to_percent(agg, min_threshold=float(config.get("min_score_threshold", 0.02)))

    # Attach names / service departments for convenience if provided
    delivery = []
    if deliverable_index_df is not None:
        map_name = {str(r["Deliverable_Code"]): (str(r["Deliverable"]), str(r.get("Service_Department", "")))
                    for _, r in deliverable_index_df.iterrows()}
    else:
        map_name = {}

    for code, data in final.items():
        name, dept = map_name.get(str(code), (code, ""))
        delivery.append({
            "deliverable_code": str(code),
            "deliverable": name,
            "service_department": dept,
            "match_percent": round(float(data["percent"]), 2),
            "explain": {
                "l1_rule": round(float(data.get("l1_parts",{}).get("rule", 0.0)),3),
                "l1_lex": round(float(data.get("l1_parts",{}).get("lex", 0.0)),3),
                "comp_best": round(float(data.get("comp_best", 0.0)),3),
                "task_best": round(float(data.get("task_best", 0.0)),3),
            }
        })
    delivery.sort(key=lambda x: x["match_percent"], reverse=True)

    # For the top-N deliverables, also expand top components and L3 tasks with their percent (relative to each L1)
    # This keeps the payload small for the UI
    per_l1_components = {}
    per_l1_tasks = {}
    for code, data in final.items():
        # Normalize component/task score relative to the best for that L1 so it's 0..100
        l2 = []
        best_c = max([s for (_, s) in data.get("l2_list", [])] or [1.0])
        if best_c == 0: best_c = 1.0
        for row_idx, s in data.get("l2_list", [])[:6]:
            row = index_df.iloc[row_idx]
            l2.append({
                "component": str(row.get("Component_Task_L1","")),
                "percent": round((s/best_c)*100.0, 1)
            })
        per_l1_components[code] = l2

        l3 = []
        best_t = max([s for (_, s) in data.get("l3_list", [])] or [1.0])
        if best_t == 0: best_t = 1.0
        for row_idx, s in data.get("l3_list", [])[:8]:
            row = index_df.iloc[row_idx]
            l3.append({
                "component": str(row.get("Component_Task_L1","")),
                "task": str(row.get("Task_Task_L2","")),
                "percent": round((s/best_t)*100.0, 1)
            })
        per_l1_tasks[code] = l3

    return {
        "deliverables": delivery,
        "components": per_l1_components,
        "tasks": per_l1_tasks,
        "config": config
    }
