# ai_planner_agencydb.py (v3 - AgencyDB Integration with Granular L2 Selection)
# Resilient AI suggestions connected to real database with specific task selection

import os, json, math, re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
REASONING_MODEL = os.environ.get("AI_REASONING_MODEL", "gpt-4o")  # Changed to gpt-4o (Chat Completions)
EMBEDDING_MODEL = "text-embedding-3-large"

AI_STRICTNESS_DEFAULT = os.environ.get("AI_STRICTNESS_DEFAULT", "balanced")
AI_AUTORELAX = os.environ.get("AI_AUTORELAX", "true").lower() == "true"
AI_MIN_DELIVERABLES = int(os.environ.get("AI_MIN_DELIVERABLES", "3"))
AI_MIN_COMPONENTS_PER_DELIV = int(os.environ.get("AI_MIN_COMPONENTS_PER_DELIV", "2"))
AI_MIN_TASKS_PER_COMPONENT = int(os.environ.get("AI_MIN_TASKS_PER_COMPONENT", "2"))

DEPARTMENTS = [
    "Creative",
    "Strategy",
    "Paid Media",
    "Content",
    "Technology",
    "Integrated Marketing Management",
]

# ──────────────────────────────────────────────────────────────────────────────
# OpenAI client (Chat Completions + Embeddings)
# ──────────────────────────────────────────────────────────────────────────────
if OPENAI_API_KEY:
    from openai import OpenAI
    oai = OpenAI(api_key=OPENAI_API_KEY)
else:
    oai = None

def embed_many(texts: List[str]) -> List[List[float]]:
    if not oai: 
        # Return zero embeddings as fallback
        return [[0.0] * 1536 for _ in texts]
    if not texts: return []
    
    # Filter out empty/invalid strings - OpenAI API rejects them
    valid_texts = [str(t).strip() if t else "unknown" for t in texts]
    valid_texts = [t if t else "unknown" for t in valid_texts]
    
    # Debug: Check for problematic inputs
    print(f"[EMBED DEBUG] Sending {len(valid_texts)} texts to embeddings API")
    for idx, t in enumerate(valid_texts[:3]):  # Show first 3
        print(f"[EMBED DEBUG] Text {idx}: {t[:100] if len(t) > 100 else t}")
    
    try:
        r = oai.embeddings.create(model=EMBEDDING_MODEL, input=valid_texts)
        return [e.embedding for e in r.data]
    except Exception as e:
        print(f"[EMBED ERROR] Failed with {len(valid_texts)} texts")
        print(f"[EMBED ERROR] First text type: {type(valid_texts[0])}")
        print(f"[EMBED ERROR] First text repr: {repr(valid_texts[0][:200])}")
        raise

def chat_json_schema(messages: list, schema: dict, max_tokens: int = 2200) -> dict:
    """Use Chat Completions with JSON schema for GPT-4o"""
    if not oai:
        # Return empty structure matching schema
        return {"summary": "", "goals": [], "channels": [], "markets": [], "complexity": "medium"}
    
    response = oai.chat.completions.create(
        model=REASONING_MODEL,
        messages=messages,
        response_format={"type": "json_schema", "json_schema": {"name": "Response", "schema": schema, "strict": True}},
        max_tokens=max_tokens,
    )
    text = response.choices[0].message.content
    return json.loads(text)

# ──────────────────────────────────────────────────────────────────────────────
# AgencyDB Catalog Builder
# ──────────────────────────────────────────────────────────────────────────────
def build_catalog_from_agencydb(db) -> List[Dict[str, Any]]:
    """Convert AgencyDB all_rows DataFrame into AI-ready catalog"""
    items = []
    
    if db.all_rows is None or db.all_rows.empty:
        return items
    
    # Group by deliverable
    for deliv_code, deliv_group in db.all_rows.groupby('Deliverable_Code'):
        if pd.isna(deliv_code) or not str(deliv_code).strip():
            continue
            
        # Get deliverable info from first row
        first_row = deliv_group.iloc[0]
        deliv_name = str(first_row.get('Deliverable', deliv_code))
        service_dept = str(first_row.get('Service Department', 'Strategy'))
        
        # Normalize department
        dept = _normalize_dept(service_dept)
        if dept not in DEPARTMENTS:
            continue
        
        # Add deliverable to catalog
        deliv_item = {
            "id": str(deliv_code),
            "level": "deliverable",
            "dept": dept,
            "title": deliv_name,
            "desc": "",
            "keywords": _extract_keywords(deliv_name)
        }
        items.append(deliv_item)
        
        # Group by component under this deliverable
        for comp_name, comp_group in deliv_group.groupby('Component'):
            if pd.isna(comp_name) or not str(comp_name).strip() or str(comp_name) == 'nan':
                comp_name = "General"
            
            comp_id = f"{deliv_code}::{comp_name}"
            comp_item = {
                "id": comp_id,
                "parentId": str(deliv_code),
                "level": "component",
                "dept": dept,
                "title": str(comp_name),
                "desc": "",
                "keywords": _extract_keywords(str(comp_name))
            }
            items.append(comp_item)
            
            # Add all L2 tasks under this component
            for idx, row in comp_group.iterrows():
                task_label = str(row.get('Task_Label', row.get('task_group', 'Task')))
                if pd.isna(task_label) or not task_label.strip() or task_label == 'nan':
                    continue
                
                task_id = f"{deliv_code}::{comp_name}::{task_label}"
                task_item = {
                    "id": task_id,
                    "parentId": comp_id,
                    "level": "task",
                    "dept": dept,
                    "title": task_label,
                    "desc": "",
                    "keywords": _extract_keywords(task_label),
                    "base_hours": float(row.get('Hours', 2.0)) if not pd.isna(row.get('Hours')) else 2.0
                }
                items.append(task_item)
    
    return items

def _normalize_dept(s: str) -> str:
    x = (s or "").lower()
    if "paid" in x or "media" in x: return "Paid Media"
    if "integrated" in x or "imm" in x: return "Integrated Marketing Management"
    if "strategy" in x or "strat" in x: return "Strategy"
    if "creative" in x: return "Creative"
    if "content" in x: return "Content"
    if any(k in x for k in ["tech", "dev", "web", "technology"]): return "Technology"
    return "Strategy"

def _extract_keywords(text: str) -> List[str]:
    """Extract keywords from text"""
    words = re.findall(r'\b\w+\b', text.lower())
    # Remove common stop words
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    keywords = [w for w in words if w not in stopwords and len(w) > 2]
    return keywords[:10]  # Limit to 10 keywords

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
_nonword = re.compile(r"[^a-z0-9\s\-\&\/\+]")
def normalize_text(s: str) -> str: return _nonword.sub(" ", (s or "").lower())
def tokenize(s: str) -> List[str]: return [t for t in normalize_text(s).split() if t]
def sentence_split(text: str) -> List[str]:
    return [s.strip() for s in re.split(r'(?<=[\.\?\!])\s+(?=[A-Z0-9])', text) if s.strip()]

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0: return 0.0
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0: return 0.0
    return float(np.dot(a, b) / denom)

def lexical_score(text: str, title: str, desc: str, keywords: List[str], dept: str) -> float:
    tk_r = set(tokenize(text))
    tk_c = set(tokenize(" ".join([title or "", desc or "", " ".join(keywords or [])])))
    overlap = sum(1 for t in tk_c if t in tk_r)
    dept_hit = 0.05 if dept.lower().split(" ")[0] in tk_r else 0
    return min(1.0, (overlap / max(4, len(tk_c))) + dept_hit)

# ──────────────────────────────────────────────────────────────────────────────
# Summarize request
# ──────────────────────────────────────────────────────────────────────────────
def summarize_request(request_text: str) -> Dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "goals": {"type": "array", "items": {"type": "string"}},
            "channels": {"type": "array", "items": {"type": "string"}},
            "markets": {"type": "array", "items": {"type": "string"}},
            "compliance": {"type": "array", "items": {"type": "string"}},
            "languages": {"type": "array", "items": {"type": "string"}},
            "timeline_weeks": {"type": "number"},
            "budget_tier": {"type": "string", "enum": ["unknown", "scrappy", "moderate", "premium"]},
            "complexity": {"type": "string", "enum": ["low", "medium", "high"]},
            "risk_flags": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["summary", "goals", "channels", "markets", "compliance", "languages", "timeline_weeks", "budget_tier", "complexity", "risk_flags"],
        "additionalProperties": False
    }
    messages = [
        {"role": "system", "content": "You are a senior agency PM/strategist in digital/creative/paid media/content/tech. Extract actionable signals."},
        {"role": "user", "content": f"REQUEST TEXT:\n{request_text}\n\nSummarize (<=120 words) and extract: goals, channels, markets, compliance, languages, timeline_weeks, budget_tier, complexity, risk_flags."}
    ]
    return chat_json_schema(messages, schema)

# ──────────────────────────────────────────────────────────────────────────────
# Recall candidates (embeddings + lexical)
# ──────────────────────────────────────────────────────────────────────────────
def recall_candidates(request_text: str, catalog: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not catalog:
        return [], []
    
    texts = [f"{str(i.get('dept',''))} • {str(i.get('level',''))} • {str(i.get('title',''))} :: {str(i.get('desc',''))} :: {', '.join(str(k) for k in i.get('keywords',[]))}" for i in catalog]
    embs = embed_many([request_text] + texts)
    req = np.array(embs[0], dtype=np.float32)
    
    cands = []
    for i, it in enumerate(catalog, start=1):
        v = np.array(embs[i], dtype=np.float32)
        emb = cosine(req, v)
        lex = lexical_score(request_text, it["title"], it.get("desc", ""), it.get("keywords", []), it["dept"])
        recall = 0.70 * emb + 0.30 * lex
        cands.append({**it, "embScore": emb, "lexScore": lex, "recall": recall})
    
    # Generous cuts to feed re-ranker
    topD = sorted([x for x in cands if x["level"] == "deliverable"], key=lambda z: z["recall"], reverse=True)[:60]
    topC = sorted([x for x in cands if x["level"] == "component"], key=lambda z: z["recall"], reverse=True)[:90]
    topT = sorted([x for x in cands if x["level"] == "task"], key=lambda z: z["recall"], reverse=True)[:120]
    
    return topD + topC + topT, cands

# ──────────────────────────────────────────────────────────────────────────────
# Evidence & LLM re-score with GRANULAR TASK SELECTION
# ──────────────────────────────────────────────────────────────────────────────
def best_evidence(request_text: str, candidate: Dict[str, Any], k: int = 3) -> List[str]:
    sents = sentence_split(request_text)
    scored = [(s, lexical_score(s, candidate["title"], candidate.get("desc", ""), candidate.get("keywords", []), candidate["dept"])) for s in sents]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s for s, score in scored[:k] if score > 0]

def rescore_with_llm_granular(summary: Dict[str, Any], candidates: List[Dict[str, Any]], request_text: str) -> List[Dict[str, Any]]:
    """LLM re-scoring with GRANULAR task-level selection - only select relevant tasks, exclude irrelevant ones"""
    if not candidates or not oai:
        return []
    
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "dept": {"type": "string", "enum": DEPARTMENTS},
                        "level": {"type": "string", "enum": ["deliverable", "component", "task"]},
                        "relevance": {"type": "number", "minimum": 0, "maximum": 100},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "why": {"type": "string"},
                        "risks": {"type": "string"},
                        "select": {"type": "boolean"}  # NEW: explicit selection flag for tasks
                    },
                    "required": ["id", "dept", "level", "relevance", "confidence", "why", "select"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["items"],
        "additionalProperties": False
    }
    
    out = []
    chunk = 40  # Smaller chunks for granular analysis
    for i in range(0, len(candidates), chunk):
        block = candidates[i:i + chunk]
        payload = [{"id": c["id"], "dept": c["dept"], "level": c["level"], "title": c["title"],
                    "desc": c.get("desc", ""), "evidence": best_evidence(request_text, c, 3)} for c in block]
        
        messages = [
            {"role": "system", "content": "You are a senior agency PM/strategist. Score how necessary each candidate is. For TASKS, set select=true ONLY if specifically relevant; set select=false for generic/boilerplate tasks that don't match the request. Think holistically about project flow from start to finish."},
            {"role": "user", "content": f"REQUEST SUMMARY:\n{summary.get('summary','')}\n\nGOALS:\n- " + "\n- ".join(summary.get("goals", [])) + f"\n\nCHANNELS: {', '.join(summary.get('channels',[]))} | MARKETS: {', '.join(summary.get('markets',[]))} | COMPLIANCE: {', '.join(summary.get('compliance',[]))}\n\nCANDIDATES:\n{json.dumps(payload, indent=2)}\n\nFor each candidate, especially TASKS, decide if it should be selected (select=true) or excluded (select=false) based on relevance to this specific project."}
        ]
        
        try:
            r = chat_json_schema(messages, schema, max_tokens=1800)
            out.extend(r.get("items", []))
        except Exception as e:
            print(f"[LLM Re-score Error] {e}")
            # Fallback: mark items based on recall score
            for c in block:
                out.append({
                    "id": c["id"],
                    "dept": c["dept"],
                    "level": c["level"],
                    "relevance": min(100, c["recall"] * 100),
                    "confidence": c["recall"],
                    "why": "Recall-based selection (LLM unavailable)",
                    "risks": "",
                    "select": c["recall"] > 0.4  # Threshold for auto-select
                })
    
    return out

# [Continued in next message due to length...]
# ──────────────────────────────────────────────────────────────────────────────
# Fusion, calibration, AUTO-RELAX & RESCUE
# ──────────────────────────────────────────────────────────────────────────────
def fuse_and_calibrate(candidates: List[Dict[str, Any]], llm_scores: List[Dict[str, Any]], strictness: str = "balanced") -> List[Dict[str, Any]]:
    lookup = {x["id"]: x for x in llm_scores}
    W = {"emb": 0.15, "lex": 0.10, "recall": 0.10, "llm": 0.55, "hist": 0.10}
    hist_prior = 0.65
    gates = {"high": 0.70, "balanced": 0.58, "recall": 0.48}
    
    out = []
    for c in candidates:
        l = lookup.get(c["id"])
        llm_val = (l["relevance"] / 100.0) if l else 0.0
        llm_select = l.get("select", True) if l else True  # Respect AI's select flag
        
        raw = W["emb"] * c["embScore"] + W["lex"] * c["lexScore"] + W["recall"] * c["recall"] + W["llm"] * llm_val + W["hist"] * hist_prior
        calibrated = 1.0 / (1.0 + math.exp(-(2.2 * raw - 1.1)))
        
        # For tasks: only pass if AI explicitly selected it
        if c["level"] == "task" and not llm_select:
            pass_gate = False
        else:
            pass_gate = calibrated >= gates.get(strictness, gates["balanced"])
        
        out.append({**c, "llm": l, "fused_score": raw, "calibrated_confidence": calibrated, "pass": pass_gate, "ai_selected": llm_select})
    
    return out

def _auto_rescue_if_empty(fused: List[Dict[str, Any]], all_recall: List[Dict[str, Any]], llm_scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """If no deliverables pass, relax and ensure a non-empty scope"""
    passed_delivs = [x for x in fused if x["level"] == "deliverable" and x["pass"]]
    if passed_delivs:
        return fused
    
    # Build maps
    by_id = {x["id"]: x for x in fused}
    llm_map = {x["id"]: x for x in llm_scores}
    recall_map = {x["id"]: x for x in all_recall}
    
    # Rank deliverables by LLM relevance (if any), else recall
    deliv_cands = [x for x in all_recall if x["level"] == "deliverable"]
    def deliv_key(x):
        l = llm_map.get(x["id"])
        return (l["relevance"] if l else 0.0, x["recall"])
    deliv_cands.sort(key=deliv_key, reverse=True)
    chosen_delivs = deliv_cands[:max(AI_MIN_DELIVERABLES, 3)]
    
    # Mark chosen deliverables as pass
    for d in chosen_delivs:
        if d["id"] not in by_id:
            fused.append({**d, "llm": llm_map.get(d["id"]), "calibrated_confidence": 0.62, "pass": True, "fused_score": d["recall"], "ai_selected": True})
        else:
            by_id[d["id"]]["pass"] = True
            by_id[d["id"]]["calibrated_confidence"] = max(by_id[d["id"]]["calibrated_confidence"], 0.62)
    
    # Pick components/tasks under each chosen deliverable
    comp_cands = [x for x in all_recall if x["level"] == "component"]
    task_cands = [x for x in all_recall if x["level"] == "task"]
    
    for d in chosen_delivs:
        # top components under this deliverable
        comps = [c for c in comp_cands if c.get("parentId") == d["id"]]
        comps.sort(key=lambda z: (llm_map.get(z["id"], {"relevance": 0}).get("relevance", 0), z["recall"]), reverse=True)
        for c in comps[:max(AI_MIN_COMPONENTS_PER_DELIV, 2)]:
            if c["id"] not in by_id:
                fused.append({**c, "llm": llm_map.get(c["id"]), "calibrated_confidence": 0.58, "pass": True, "fused_score": c["recall"], "ai_selected": True})
            else:
                by_id[c["id"]]["pass"] = True
                by_id[c["id"]]["calibrated_confidence"] = max(by_id[c["id"]]["calibrated_confidence"], 0.58)
            # tasks under this component - respect AI selection
            tasks = [t for t in task_cands if t.get("parentId") == c["id"]]
            tasks.sort(key=lambda z: (llm_map.get(z["id"], {"relevance": 0}).get("relevance", 0), z["recall"]), reverse=True)
            # Only include AI-selected tasks
            for t in tasks[:max(AI_MIN_TASKS_PER_COMPONENT * 2, 4)]:  # Get more candidates
                llm_t = llm_map.get(t["id"])
                if llm_t and llm_t.get("select", False):  # Only if AI selected
                    if t["id"] not in by_id:
                        fused.append({**t, "llm": llm_t, "calibrated_confidence": 0.53, "pass": True, "fused_score": t["recall"], "ai_selected": True})
                    else:
                        by_id[t["id"]]["pass"] = True
                        by_id[t["id"]]["calibrated_confidence"] = max(by_id[t["id"]]["calibrated_confidence"], 0.53)
    
    return fused

# ──────────────────────────────────────────────────────────────────────────────
# Composition with AgencyDB structure
# ──────────────────────────────────────────────────────────────────────────────
def multipliers_from_summary(sumdict: Dict[str, Any]) -> Dict[str, float]:
    ch = len(sumdict.get("channels", []))
    mk = len(sumdict.get("markets", []))
    comp = len(sumdict.get("compliance", []))
    complexity = {"low": 1.0, "medium": 1.15, "high": 1.35}.get(sumdict.get("complexity"), 1.0)
    channel_multi = 1.25 if ch > 4 else (1.12 if ch > 2 else 1.0)
    market_multi = 1.18 if mk > 1 else 1.0
    compliance_multi = 1.08 if comp > 0 else 1.0
    return {"complexity": complexity, "channelMulti": channel_multi, "marketMulti": market_multi, "complianceMulti": compliance_multi}

def planned_hours(base: float, m: Dict[str, float]) -> float:
    return round(base * m["complexity"] * m["channelMulti"] * m["marketMulti"] * m["complianceMulti"], 1)

def compose_plan_from_agencydb(fused: List[Dict[str, Any]], summary: Dict[str, Any], catalog: List[Dict[str, Any]], db, all_recall: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compose plan using real AgencyDB deliverable codes and structure"""
    passing = [x for x in fused if x["pass"]]
    dels = [x for x in passing if x["level"] == "deliverable"]
    comps_pass = {x["id"]: x for x in passing if x["level"] == "component"}
    tasks_pass = {x["id"]: x for x in passing if x["level"] == "task" and x.get("ai_selected", True)}  # Only AI-selected tasks
    
    # If still nothing after auto-rescue, hard fallback
    if not dels:
        topD = [x for x in all_recall if x["level"] == "deliverable"]
        topD.sort(key=lambda z: z["recall"], reverse=True)
        dels = topD[:max(AI_MIN_DELIVERABLES, 3)]
    
    by_dept: Dict[str, List[Dict[str, Any]]] = {}
    m = multipliers_from_summary(summary)
    
    # Build deliverable lookup from catalog
    deliv_lookup = {x["id"]: x for x in catalog if x["level"] == "deliverable"}
    
    for d_item in dels:
        deliv_code = d_item["id"]
        deliv_info = deliv_lookup.get(deliv_code, d_item)
        dept = deliv_info["dept"]
        
        if dept not in DEPARTMENTS:
            continue
        
        by_dept.setdefault(dept, [])
        
        # Get deliverable base hours from DB
        deliv_rows = db.all_rows[db.all_rows['Deliverable_Code'] == deliv_code]
        d_hours = deliv_rows['Hours'].sum() if not deliv_rows.empty else 8.0
        d_hours_planned = planned_hours(d_hours, m)
        
        # Components
        comp_out = []
        for comp_item in [x for x in catalog if x["level"] == "component" and x.get("parentId") == deliv_code]:
            comp_id = comp_item["id"]
            sc = comps_pass.get(comp_id)
            
            if sc:  # Component passed
                # Get tasks for this component - ONLY AI-selected ones
                t_out = []
                for task_item in [x for x in catalog if x["level"] == "task" and x.get("parentId") == comp_id]:
                    task_id = task_item["id"]
                    ts = tasks_pass.get(task_id)
                    
                    if ts and ts.get("ai_selected", False):  # Only include AI-selected tasks
                        base_hours = task_item.get("base_hours", 2.0)
                        t_out.append({
                            "id": task_id,
                            "title": task_item["title"],
                            "calibrated_confidence": ts.get("calibrated_confidence", 0.50),
                            "why": (ts.get("llm") or {}).get("why", "Selected by AI as relevant to project."),
                            "planned_hours": planned_hours(base_hours, m),
                            "ai_selected": True
                        })
                
                # Calculate component hours
                comp_rows = deliv_rows[deliv_rows['Component'] == comp_item["title"].split("::")[- 1]]
                c_hours = comp_rows['Hours'].sum() if not comp_rows.empty else 4.0
                
                comp_out.append({
                    "id": comp_id,
                    "title": comp_item["title"].split("::")[- 1],  # Clean component name
                    "calibrated_confidence": sc["calibrated_confidence"],
                    "why": (sc.get("llm") or {}).get("why", ""),
                    "planned_hours": planned_hours(c_hours, m),
                    "tasks": t_out
                })
        
        # Milestones
        milestones = [
            {"name": "Kickoff", "offset_days": 0},
            {"name": "Plan/Strategy Complete", "offset_days": math.ceil((d_hours_planned or 8) / 6)},
            {"name": "Launch/Activations", "offset_days": math.ceil((d_hours_planned or 8) / 6) + 5},
            {"name": "First Report", "offset_days": math.ceil((d_hours_planned or 8) / 6) + 14},
        ]
        
        by_dept[dept].append({
            "deliverable_code": deliv_code,  # Real database code
            "deliverable_title": deliv_info["title"],
            "calibrated_confidence": d_item.get("calibrated_confidence", 0.60),
            "why": (d_item.get("llm") or {}).get("why", ""),
            "risks": (d_item.get("llm") or {}).get("risks", ""),
            "planned_hours": d_hours_planned,
            "components": comp_out,
            "milestones": milestones
        })
    
    total = 0.0
    for dept_items in by_dept.values():
        for deliv in dept_items:
            total += deliv["planned_hours"] or 0.0
            for comp in deliv.get("components", []):
                total += comp["planned_hours"] or 0.0
                for t in comp.get("tasks", []):
                    total += t["planned_hours"] or 0.0
    
    return {
        "summary": summary,
        "strictness": AI_STRICTNESS_DEFAULT,
        "totals": {"planned_hours_total": round(total, 1)},
        "suggestions_by_department": by_dept
    }

# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
def analyze_with_agencydb(request_text: str, db, strictness: str = None) -> Dict[str, Any]:
    """Main analysis function using AgencyDB"""
    strictness = strictness or AI_STRICTNESS_DEFAULT
    
    # Build catalog from AgencyDB
    catalog = build_catalog_from_agencydb(db)
    
    if not catalog:
        return {
            "auto_run": True,
            "message": "No deliverables found in database.",
            "plan": {"summary": {}, "suggestions_by_department": {}},
            "diagnostics": {"candidates_considered": 0, "catalog_items": 0}
        }
    
    print(f"[AI Planner] Built catalog with {len(catalog)} items from AgencyDB")
    
    summary = summarize_request(request_text)
    candidates, all_recall = recall_candidates(request_text, catalog)
    
    if not candidates:
        return {
            "auto_run": True,
            "message": "No candidates matched request.",
            "plan": {"summary": summary, "suggestions_by_department": {}},
            "diagnostics": {"candidates_considered": 0, "catalog_items": len(catalog)}
        }
    
    llm_scores = rescore_with_llm_granular(summary, candidates, request_text)
    fused = fuse_and_calibrate(candidates, llm_scores, strictness)
    
    # AUTO-RELAX & RESCUE
    if AI_AUTORELAX:
        fused = _auto_rescue_if_empty(fused, all_recall, llm_scores)
    
    plan = compose_plan_from_agencydb(fused, summary, catalog, db, all_recall)
    
    return {
        "auto_run": True,
        "message": "AI analysis complete with granular task selection.",
        "plan": plan,
        "diagnostics": {
            "candidates_considered": len(candidates),
            "catalog_items": len(catalog),
            "deliverables_selected": len([x for x in fused if x["level"] == "deliverable" and x["pass"]]),
            "tasks_ai_selected": len([x for x in fused if x["level"] == "task" and x.get("ai_selected", False) and x["pass"]])
        }
    }

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI routes
# ──────────────────────────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    request_text: str
    strictness: Optional[str] = None

def mount_routes_agencydb(app: FastAPI, base: str = "/api/ai"):
    router = APIRouter()
    
    @router.post("/analyze")
    def _analyze(payload: AnalyzeRequest):
        try:
            db = app.state.db
            if not getattr(db, "loaded", False):
                db.load()
            return analyze_with_agencydb(payload.request_text, db, payload.strictness)
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            print(f"[AI PLANNER ERROR] {error_detail}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/health")
    def _health():
        try:
            db = app.state.db
            if not getattr(db, "loaded", False):
                db.load()
            catalog = build_catalog_from_agencydb(db)
            deliverables = len([x for x in catalog if x["level"] == "deliverable"])
            return {
                "ok": True,
                "deliverables": deliverables,
                "catalog_items": len(catalog),
                "strictness_default": AI_STRICTNESS_DEFAULT,
                "autorelax": AI_AUTORELAX,
                "database_loaded": db.loaded,
                "database_source": db.src
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    app.include_router(router, prefix=base)
