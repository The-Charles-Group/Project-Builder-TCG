
# ai_weighted_matcher.py
# Self-contained weighted matching engine for Agency Project Builder (L1/L2/L3).
# Drop this file into your server package and import score_rfp().
# No external deps beyond pandas.

from __future__ import annotations
import math, re
import logging
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

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
    except (ValueError, TypeError) as e:
        value = config.get(key, default)
        logger.error(
            f"Failed to convert config key '{key}' to float. "
            f"Value found: {value!r} (type: {type(value).__name__}). "
            f"Returning default: {default}. "
            f"Error: {e}"
        )
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

def check_direct_matches(rfp_text: str, deliverable_name: str) -> Tuple[float, List[str]]:
    """
    Check for direct keyword matches between RFP text and deliverable name.
    Returns boost percentage and matched keywords.
    """
    rfp_lower = rfp_text.lower()
    deliv_lower = deliverable_name.lower()
    
    # Extract key phrases from deliverable name (2-3 word phrases)
    words = re.findall(r'\b\w+\b', deliv_lower)
    
    matched_keywords = []
    max_boost = 0.0
    
    # Check for exact phrase matches (2-3 word combinations)
    key_phrases = []
    
    # Add 3-word phrases
    for i in range(len(words) - 2):
        phrase = ' '.join(words[i:i+3])
        key_phrases.append((phrase, 95.0))  # Highest confidence for 3-word matches
    
    # Add 2-word phrases
    for i in range(len(words) - 1):
        phrase = ' '.join(words[i:i+2])
        key_phrases.append((phrase, 92.0))  # High confidence for 2-word matches
    
    # Also check single important words (excluding common words)
    stop_words = {'the', 'and', 'or', 'for', 'in', 'on', 'at', 'to', 'a', 'an', 'of', 'with', 'by', 'as'}
    important_words = [(w, 90.0) for w in words if w not in stop_words and len(w) > 3]
    key_phrases.extend(important_words)
    
    # Check if any key phrases appear in the RFP text
    for phrase, boost in key_phrases:
        if phrase and phrase in rfp_lower:
            matched_keywords.append(phrase)
            max_boost = max(max_boost, boost)
    
    # Special handling for common marketing/media terms with variations
    special_mappings = {
        'media planning': ['media plan', 'media strategy', 'paid media planning'],
        'media buying': ['media buy', 'media purchase', 'paid media buying'],
        'brand strategy': ['branding strategy', 'brand development', 'brand positioning'],
        'creative development': ['creative concept', 'creative production', 'creative design'],
        'social media': ['social marketing', 'social channels', 'social platforms'],
        'influencer marketing': ['influencer campaign', 'influencer outreach', 'influencer partnerships'],
        'content creation': ['content development', 'content production', 'content marketing'],
    }
    
    # Check if deliverable name contains any special term
    for key_term, variations in special_mappings.items():
        if key_term in deliv_lower:
            # Check if RFP mentions this term or its variations
            if key_term in rfp_lower:
                matched_keywords.append(key_term)
                max_boost = max(max_boost, 95.0)
            else:
                for variation in variations:
                    if variation in rfp_lower:
                        matched_keywords.append(f"{key_term} (via {variation})")
                        max_boost = max(max_boost, 93.0)
                        break
    
    return max_boost, list(set(matched_keywords))

def normalize_to_percent(scores_dict: Dict[str, Any], min_threshold: float=0.02, rfp_text: str="", deliverable_names: Dict[str, str]=None) -> Dict[str, Any]:
    """
    Normalize scores to percentages with boost for direct keyword matches.
    
    Args:
        scores_dict: Dictionary of deliverable codes to score data
        min_threshold: Minimum score threshold
        rfp_text: The original RFP text for keyword matching
        deliverable_names: Map of deliverable_code -> deliverable_name
    """
    vals = [v["score"] for v in scores_dict.values()]
    maxv = max(vals) if vals else 1.0
    out = {}
    
    for code, data in scores_dict.items():
        sc = data["score"]
        base_pct = 0.0 if sc < min_threshold else (sc / maxv) * 100.0
        
        # Check for direct keyword matches if we have deliverable names
        direct_match_boost = 0.0
        matched_keywords = []
        
        if rfp_text and deliverable_names and code in deliverable_names:
            direct_match_boost, matched_keywords = check_direct_matches(
                rfp_text, deliverable_names[code]
            )
        
        # Apply boost: if there's a direct match and some base relevance
        if direct_match_boost > 0 and base_pct > 15:  # Lower threshold for boosting
            final_pct = max(base_pct, direct_match_boost)
            # If already high scoring, ensure it's at least 90%
            if base_pct > 50:
                final_pct = max(90.0, final_pct)
        else:
            final_pct = base_pct
        
        # Calculate raw TF-IDF score (0-1 scale) from lexical score
        tfidf_score = data.get("l1_parts", {}).get("lex", 0.0)
        
        out[code] = {
            **data, 
            "percent": round(final_pct, 1),
            "base_percent": round(base_pct, 1),  # Original score for transparency
            "tfidf_similarity": round(tfidf_score, 3),  # Raw TF-IDF score (0-1)
            "direct_match": direct_match_boost > 0,
            "matched_keywords": matched_keywords
        }
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
    
    # Build mapping from AI_Index (which has deliverable names and service departments)
    # Get L1 rows only for the mapping
    l1_rows = index_df[index_df["Level"] == "L1"].copy()
    map_name = {}
    deliverable_names = {}  # For passing to normalize_to_percent
    for _, r in l1_rows.iterrows():
        code = str(r["Deliverable_Code"])
        name = str(r.get("Deliverable", code))
        dept = str(r.get("Service_Department", ""))
        map_name[code] = (name, dept)
        deliverable_names[code] = name
    
    # If external deliverable_index_df provided, prefer those names (for consistency with main app)
    if deliverable_index_df is not None:
        for _, r in deliverable_index_df.iterrows():
            code = str(r["Deliverable_Code"])
            name = str(r.get("Deliverable", code))
            dept = str(r.get("Service_Department", ""))
            map_name[code] = (name, dept)
            deliverable_names[code] = name
    
    # Pass rfp_text and deliverable names for direct match detection
    final = normalize_to_percent(
        agg, 
        min_threshold=float(config.get("min_score_threshold", 0.02)),
        rfp_text=rfp_text,
        deliverable_names=deliverable_names
    )

    delivery = []
    for code, data in final.items():
        name, dept = map_name.get(str(code), (code, ""))
        delivery.append({
            "deliverable_code": str(code),
            "deliverable": name,
            "service_department": dept,
            "match_percent": round(float(data["percent"]), 2),
            "tfidf_similarity": data.get("tfidf_similarity", 0.0),  # Raw TF-IDF score (0-1)
            "base_percent": data.get("base_percent", 0.0),  # Original score before boost
            "direct_match": data.get("direct_match", False),  # Whether direct keyword match was found
            "matched_keywords": data.get("matched_keywords", []),  # Which keywords matched
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
