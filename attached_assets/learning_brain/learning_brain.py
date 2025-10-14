
from __future__ import annotations
import os, re, math
from typing import Dict, Any, List, Tuple, Optional
from .brain_store import (
    init, add_episode, upsert_draft_updates,
    get_weights, publish_draft, reset_all, undo_last_episode,
    get_setting, set_setting
)

TOKEN_RE = re.compile(r"[A-Za-z0-9\-\_]{3,}")

def _get_param_float(name: str, default: float) -> float:
    v = get_setting(name, os.getenv(name, str(default)))
    try:
        return float(v)
    except Exception:
        return float(default)

def _get_param_int(name: str, default: int) -> int:
    v = get_setting(name, os.getenv(name, str(default)))
    try:
        return int(v)
    except Exception:
        return int(default)

def _get_mode_default() -> str:
    m = get_setting("mode", os.getenv("LEARNING_MODE", "off")).strip().lower()
    return m if m in ("off","shadow","active") else "off"

def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "")][:5000]

def detect_industry(text: str) -> Optional[str]:
    mapping = {
        "education": ["school","students","admissions","enrollment","university","college"],
        "beverage": ["spirits","tequila","vodka","drink","bar","liquor","beverage"],
        "nonprofit": ["donor","fundraising","nonprofit","foundation","charity"]
    }
    tl = (text or "").lower()
    for k, kws in mapping.items():
        if any(kw in tl for kw in kws):
            return k
    return None

class LearningBrain:
    def __init__(self):
        init()
        self.mode = _get_mode_default()

    def set_mode(self, mode: str):
        m = (mode or "off").strip().lower()
        if m not in ("off","shadow","active"):
            m = "off"
        set_setting("mode", m)
        self.mode = m
        return {"mode": self.mode}

    def status(self) -> Dict[str,Any]:
        return {
            "mode": self.mode,
            "params": {
                "LEARNING_DELTA_CAP": _get_param_float("LEARNING_DELTA_CAP", 0.30),
                "LEARNING_MIN_SUPPORT": _get_param_int("LEARNING_MIN_SUPPORT", 3),
                "LEARNING_RATE": _get_param_float("LEARNING_RATE", 0.03),
            },
            "top_draft": get_weights("draft", 50),
            "top_published": get_weights("published", 50)
        }

    def set_params(self, params: Dict[str, str]) -> Dict[str,Any]:
        for k, v in (params or {}).items():
            if k not in ("LEARNING_DELTA_CAP","LEARNING_MIN_SUPPORT","LEARNING_RATE"):
                continue
            set_setting(k, str(v))
        return {"message": "params updated", "params": self.status()["params"]}

    def learn(self, rfp_text: str, selected_deliverables: List[str], components_by_deliv: Dict[str, Any] | None, outcome: str, notes: str | None) -> Dict[str,Any]:
        ind = detect_industry(rfp_text)
        selections = {"deliverables": selected_deliverables or [], "components_by_deliv": components_by_deliv or {}}
        meta = {"outcome": outcome or "accepted", "notes": notes or ""}
        eid = add_episode(rfp_text, selections, ind, meta)
        if self.mode == "off":
            return {"message": "learn recorded (mode=off, no updates)", "episode_id": eid}

        lr = _get_param_float("LEARNING_RATE", 0.03)
        toks = tokenize(rfp_text)
        updates: List[Tuple[str,str,float]] = []
        for code in (selected_deliverables or []):
            for t in toks:
                updates.append((code, t, lr))
        upsert_draft_updates(eid, updates, support_inc=1)
        return {"message": f"learn recorded (mode={self.mode})", "episode_id": eid, "updates": len(updates)}

    def publish(self) -> Dict[str,Any]:
        publish_draft()
        return {"message": "draft → published"}

    def reset(self) -> Dict[str,Any]:
        reset_all()
        return {"message": "brain reset"}

    def undo(self) -> Dict[str,Any]:
        ok = undo_last_episode()
        return {"message": "undone last episode" if ok else "nothing to undo"}

    def blend_scores(self, base_scores: Dict[str, float], rfp_text: str, which: str = "published") -> Dict[str,Any]:
        delta_cap = _get_param_float("LEARNING_DELTA_CAP", 0.30)
        min_support = _get_param_int("LEARNING_MIN_SUPPORT", 3)
        tok = set(tokenize(rfp_text))
        weights = get_weights(which=which, limit=50000)
        by_code: Dict[str, Dict[str, float]] = {}
        for w in weights:
            if int(w["support"]) < min_support: 
                continue
            d = float(w["delta"])
            if abs(d) > delta_cap:
                d = math.copysign(delta_cap, d)
            by_code.setdefault(w["deliverable_code"], {})[w["token"]] = d

        scores_out: Dict[str, float] = {}
        explain: Dict[str, Dict[str, float]] = {}
        for code, base in base_scores.items():
            contrib = 0.0
            per_tok: Dict[str, float] = {}
            m = by_code.get(code) or {}
            for t in tok:
                if t in m:
                    per_tok[t] = m[t]
                    contrib += m[t]
            scores_out[code] = float(base) + contrib
            if per_tok:
                topk = dict(sorted(per_tok.items(), key=lambda kv: abs(kv[1]), reverse=True)[:10])
                explain[code] = topk
        return {"scores": scores_out, "explain": explain}
