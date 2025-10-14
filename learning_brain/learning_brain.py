"""
Enhanced Learning Brain with Confidence Adjustment System
"""
from __future__ import annotations
import os, re, math
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from .brain_store import (
    init, add_episode, upsert_draft_updates,
    get_weights, publish_draft, reset_all, undo_last_episode,
    get_setting, set_setting,
    # New confidence adjustment functions
    add_confidence_adjustment, get_confidence_adjustments,
    set_confidence_override, get_confidence_overrides,
    log_mode_change, get_mode_history,
    audit_log_action, get_audit_log, get_statistics
)
from .models import OperatingMode

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
        "nonprofit": ["donor","fundraising","nonprofit","foundation","charity"],
        "retail": ["store","shop","retail","ecommerce","product","merchandise"],
        "technology": ["software","app","tech","digital","platform","api","cloud"],
        "healthcare": ["health","medical","patient","hospital","clinic","doctor"],
    }
    tl = (text or "").lower()
    for k, kws in mapping.items():
        if any(kw in tl for kw in kws):
            return k
    return None

class LearningBrain:
    """
    Enhanced Learning Brain with confidence adjustment capabilities
    """
    def __init__(self):
        init()
        self.mode = _get_mode_default()
        self._admin_user = None  # Current admin user for audit trail

    def set_admin_user(self, user: Optional[str]):
        """Set the current admin user for audit logging"""
        self._admin_user = user

    def set_mode(self, mode: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Change the operating mode"""
        m = (mode or "off").strip().lower()
        if m not in ("off","shadow","active"):
            m = "off"
        
        old_mode = self.mode
        set_setting("mode", m)
        self.mode = m
        
        # Log mode change
        if old_mode != m:
            log_mode_change(old_mode, m, self._admin_user, reason)
        
        return {"mode": self.mode, "previous_mode": old_mode}

    def status(self) -> Dict[str,Any]:
        """Get comprehensive status of the Learning Brain"""
        stats = get_statistics()
        mode_history = get_mode_history(limit=5)
        
        return {
            "mode": self.mode,
            "params": {
                "LEARNING_DELTA_CAP": _get_param_float("LEARNING_DELTA_CAP", 0.30),
                "LEARNING_MIN_SUPPORT": _get_param_int("LEARNING_MIN_SUPPORT", 3),
                "LEARNING_RATE": _get_param_float("LEARNING_RATE", 0.03),
            },
            "statistics": stats,
            "mode_history": mode_history,
            "top_draft": get_weights("draft", 50),
            "top_published": get_weights("published", 50),
            "active_overrides": get_confidence_overrides()
        }

    def set_params(self, params: Dict[str, str]) -> Dict[str,Any]:
        """Update learning parameters"""
        for k, v in (params or {}).items():
            if k not in ("LEARNING_DELTA_CAP","LEARNING_MIN_SUPPORT","LEARNING_RATE"):
                continue
            set_setting(k, str(v))
        
        audit_log_action("update_params", f"Updated parameters: {params}", self._admin_user)
        
        return {"message": "params updated", "params": self.status()["params"]}

    def submit_confidence_adjustment(
        self,
        deliverable_code: str,
        deliverable_name: str,
        original_confidence: float,
        adjusted_confidence: float,
        reason: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a confidence adjustment for a deliverable"""
        
        # Store the adjustment
        adj_id = add_confidence_adjustment(
            deliverable_code=deliverable_code,
            deliverable_name=deliverable_name,
            original_confidence=original_confidence,
            adjusted_confidence=adjusted_confidence,
            reason=reason,
            notes=notes,
            admin_user=self._admin_user
        )
        
        # If in SHADOW or ACTIVE mode, also update the learning weights
        if self.mode in ("shadow", "active"):
            # Calculate the delta for learning
            delta = adjusted_confidence - original_confidence
            
            # Create a simple episode for tracking
            episode_id = add_episode(
                rfp_text="",
                selections={"deliverables": [deliverable_code]},
                industry=None,
                metadata={"type": "confidence_adjustment", "adjustment_id": adj_id, "delta": delta}
            )
            
            # Update draft weights with the adjustment
            lr = _get_param_float("LEARNING_RATE", 0.03)
            updates = [(deliverable_code, f"_confidence_override_{deliverable_code}", delta * lr)]
            upsert_draft_updates(episode_id, updates, support_inc=1)
        
        return {
            "message": f"Confidence adjustment recorded (mode={self.mode})",
            "adjustment_id": adj_id,
            "mode": self.mode
        }

    def learn(self, rfp_text: str, selected_deliverables: List[str], components_by_deliv: Dict[str, Any] | None, outcome: str, notes: str | None) -> Dict[str,Any]:
        """Learn from RFP selection (original functionality)"""
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
        """Publish draft adjustments to production"""
        publish_draft()
        return {"message": "draft → published", "mode": self.mode}

    def reset(self) -> Dict[str,Any]:
        """Reset all learning data"""
        reset_all()
        return {"message": "brain reset", "mode": self.mode}

    def undo(self) -> Dict[str,Any]:
        """Undo the last episode/adjustment"""
        ok = undo_last_episode()
        return {"message": "undone last episode" if ok else "nothing to undo", "mode": self.mode}

    def blend_scores(self, base_scores: Dict[str, float], rfp_text: str = "", which: str = "published") -> Dict[str,Any]:
        """
        Blend base AI scores with learned adjustments.
        This is the main integration point with the AI analysis.
        """
        # If mode is OFF, return base scores unchanged
        if self.mode == "off":
            return {"scores": base_scores, "explain": {}, "mode": "off"}
        
        # Use draft weights in SHADOW mode, published in ACTIVE mode
        if self.mode == "shadow":
            which = "draft"
        elif self.mode == "active":
            which = "published"
        
        delta_cap = _get_param_float("LEARNING_DELTA_CAP", 0.30)
        min_support = _get_param_int("LEARNING_MIN_SUPPORT", 3)
        
        # Apply confidence overrides first (direct admin overrides)
        overrides = get_confidence_overrides() if self.mode == "active" else {}
        
        # Token-based adjustments from RFP text
        tok = set(tokenize(rfp_text)) if rfp_text else set()
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
            # Start with base score
            adjusted = float(base)
            per_tok: Dict[str, float] = {}
            
            # Apply token-based adjustments if RFP text provided
            if rfp_text and code in by_code:
                m = by_code[code]
                contrib = 0.0
                for t in tok:
                    if t in m:
                        per_tok[t] = m[t]
                        contrib += m[t]
                adjusted += contrib
            
            # Apply direct confidence override if exists
            if code in overrides:
                override_delta = overrides[code]
                adjusted += override_delta
                per_tok["_manual_override"] = override_delta
            
            # Ensure score stays within [0, 1] bounds
            adjusted = max(0.0, min(1.0, adjusted))
            scores_out[code] = adjusted
            
            if per_tok:
                # Sort by impact magnitude and take top 10
                topk = dict(sorted(per_tok.items(), key=lambda kv: abs(kv[1]), reverse=True)[:10])
                explain[code] = topk
        
        return {"scores": scores_out, "explain": explain, "mode": self.mode}

    def get_adjustments(
        self, 
        limit: int = 50, 
        offset: int = 0,
        deliverable_code: Optional[str] = None,
        only_pending: bool = False
    ) -> List[Dict[str, Any]]:
        """Get confidence adjustment history"""
        return get_confidence_adjustments(
            limit=limit,
            offset=offset,
            deliverable_code=deliverable_code,
            only_pending=only_pending
        )

    def set_override(
        self,
        deliverable_code: str,
        deliverable_name: str,
        confidence_adjustment: float,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Set a direct confidence override for immediate effect"""
        set_confidence_override(
            deliverable_code=deliverable_code,
            deliverable_name=deliverable_name,
            confidence_adjustment=confidence_adjustment,
            reason=reason,
            admin_user=self._admin_user
        )
        
        return {
            "message": f"Override set for {deliverable_code}",
            "adjustment": confidence_adjustment,
            "mode": self.mode
        }

    def get_audit_log(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get audit log for admin review"""
        return get_audit_log(limit=limit, offset=offset)