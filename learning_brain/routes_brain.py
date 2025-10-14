"""
Enhanced API routes for Learning Brain with confidence adjustment endpoints
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from .learning_brain import LearningBrain
from .security import require_admin
from .brain_store import list_episodes, get_audit_log
from .models import (
    OperatingMode, FeedbackPayload, ModeChangePayload,
    BulkFeedbackPayload, ConfidenceBlendPayload,
    StatusResponse, AdjustmentHistoryResponse
)

router = APIRouter()
brain = LearningBrain()

# ================ Request Models ================

class LearnPayload(BaseModel):
    rfp_text: str = ""
    selected_deliverables: List[str] = Field(default_factory=list)
    components_by_deliv: Optional[Dict[str, Any]] = None
    outcome: str = "accepted"
    notes: Optional[str] = None

class TogglePayload(BaseModel):
    mode: str = Field(pattern="^(off|shadow|active)$")
    reason: Optional[str] = None

class PreviewPayload(BaseModel):
    rfp_text: str = ""
    base_scores: Dict[str, float] = Field(default_factory=dict)
    which: str = "published"

class ParamsPayload(BaseModel):
    LEARNING_DELTA_CAP: Optional[float] = None
    LEARNING_MIN_SUPPORT: Optional[int] = None
    LEARNING_RATE: Optional[float] = None

class OverridePayload(BaseModel):
    deliverable_code: str
    deliverable_name: str
    confidence_adjustment: float = Field(ge=-1.0, le=1.0)
    reason: Optional[str] = None

# ================ Helper to extract admin user ================

def get_admin_user(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract admin user identifier from token (could be enhanced with JWT)"""
    if authorization and authorization.startswith("Bearer "):
        # In a real implementation, decode JWT to get user info
        # For now, we'll use a simple identifier
        return "admin"
    return None

# ================ Status and Configuration Endpoints ================

@router.get("/status")
def status():
    """Get current status and statistics of the Learning Brain"""
    return brain.status()

@router.post("/mode")
def change_mode(payload: ModeChangePayload, 
                ok: bool = Depends(require_admin),
                admin_user: Optional[str] = Depends(get_admin_user)):
    """Change the operating mode of the Learning Brain"""
    brain.set_admin_user(admin_user)
    return brain.set_mode(payload.mode, payload.reason)

@router.post("/toggle")
def toggle(payload: TogglePayload, 
           ok: bool = Depends(require_admin),
           admin_user: Optional[str] = Depends(get_admin_user)):
    """Toggle operating mode (backward compatibility)"""
    brain.set_admin_user(admin_user)
    return brain.set_mode(payload.mode, payload.reason)

@router.post("/params")
def params(payload: ParamsPayload, 
           ok: bool = Depends(require_admin),
           admin_user: Optional[str] = Depends(get_admin_user)):
    """Update learning parameters"""
    brain.set_admin_user(admin_user)
    p = {k:v for k,v in payload.dict().items() if v is not None}
    return brain.set_params({k:str(v) for k,v in p.items()})

# ================ Confidence Adjustment Endpoints ================

@router.post("/feedback")
def submit_feedback(payload: FeedbackPayload, 
                    ok: bool = Depends(require_admin),
                    admin_user: Optional[str] = Depends(get_admin_user)):
    """Submit a confidence adjustment for a deliverable"""
    brain.set_admin_user(admin_user)
    return brain.submit_confidence_adjustment(
        deliverable_code=payload.deliverable_code,
        deliverable_name=payload.deliverable_name,
        original_confidence=payload.original_confidence,
        adjusted_confidence=payload.adjusted_confidence,
        reason=payload.reason,
        notes=payload.notes
    )

@router.post("/feedback/bulk")
def submit_bulk_feedback(payload: BulkFeedbackPayload,
                         ok: bool = Depends(require_admin),
                         admin_user: Optional[str] = Depends(get_admin_user)):
    """Submit multiple confidence adjustments at once"""
    brain.set_admin_user(admin_user)
    results = []
    
    for adjustment in payload.adjustments:
        result = brain.submit_confidence_adjustment(
            deliverable_code=adjustment.deliverable_code,
            deliverable_name=adjustment.deliverable_name,
            original_confidence=adjustment.original_confidence,
            adjusted_confidence=adjustment.adjusted_confidence,
            reason=adjustment.reason,
            notes=adjustment.notes
        )
        results.append(result)
    
    # If apply_immediately is true, publish the changes
    if payload.apply_immediately:
        brain.publish()
    
    return {
        "message": f"Submitted {len(results)} adjustments",
        "apply_immediately": payload.apply_immediately,
        "results": results
    }

@router.post("/override")
def set_override(payload: OverridePayload,
                 ok: bool = Depends(require_admin),
                 admin_user: Optional[str] = Depends(get_admin_user)):
    """Set a direct confidence override for a deliverable"""
    brain.set_admin_user(admin_user)
    return brain.set_override(
        deliverable_code=payload.deliverable_code,
        deliverable_name=payload.deliverable_name,
        confidence_adjustment=payload.confidence_adjustment,
        reason=payload.reason
    )

@router.get("/adjustments")
def get_adjustments(limit: int = 50, 
                    offset: int = 0,
                    deliverable_code: Optional[str] = None,
                    only_pending: bool = False,
                    ok: bool = Depends(require_admin)):
    """Get confidence adjustment history"""
    adjustments = brain.get_adjustments(
        limit=limit,
        offset=offset,
        deliverable_code=deliverable_code,
        only_pending=only_pending
    )
    
    return {
        "adjustments": adjustments,
        "total": len(adjustments),
        "page": offset // limit if limit > 0 else 0,
        "page_size": limit
    }

# ================ Learning and Publishing Endpoints ================

@router.post("/learn")
def learn(payload: LearnPayload, 
          ok: bool = Depends(require_admin),
          admin_user: Optional[str] = Depends(get_admin_user)):
    """Learn from RFP selection (original functionality)"""
    brain.set_admin_user(admin_user)
    return brain.learn(
        rfp_text=payload.rfp_text,
        selected_deliverables=payload.selected_deliverables,
        components_by_deliv=payload.components_by_deliv,
        outcome=payload.outcome,
        notes=payload.notes
    )

@router.get("/episodes")
def episodes(limit: int = 50, 
             offset: int = 0, 
             ok: bool = Depends(require_admin)):
    """Get learning episodes history"""
    return {"items": list_episodes(limit=limit, offset=offset)}

@router.post("/publish")
def publish(ok: bool = Depends(require_admin),
            admin_user: Optional[str] = Depends(get_admin_user)):
    """Publish draft adjustments to production"""
    brain.set_admin_user(admin_user)
    return brain.publish()

@router.post("/reset")
def reset(ok: bool = Depends(require_admin),
          admin_user: Optional[str] = Depends(get_admin_user)):
    """Reset all learning data"""
    brain.set_admin_user(admin_user)
    return brain.reset()

@router.post("/undo")
def undo(ok: bool = Depends(require_admin),
         admin_user: Optional[str] = Depends(get_admin_user)):
    """Undo the last episode/adjustment"""
    brain.set_admin_user(admin_user)
    return brain.undo()

# ================ Preview and Blending Endpoints ================

@router.post("/preview")
def preview(payload: PreviewPayload, 
            ok: bool = Depends(require_admin)):
    """Preview how adjustments would affect scores"""
    return brain.blend_scores(
        payload.base_scores, 
        payload.rfp_text, 
        which=payload.which
    )

@router.post("/blend")
def blend_scores(payload: ConfidenceBlendPayload):
    """
    Blend AI scores with learned adjustments.
    This endpoint can be called by the main AI analysis to apply adjustments.
    No admin auth required as this is for system integration.
    """
    which = "draft" if payload.use_draft else "published"
    return brain.blend_scores(
        payload.base_scores,
        payload.rfp_text or "",
        which=which
    )

# ================ Audit and Export Endpoints ================

@router.get("/audit")
def get_audit(limit: int = 100, 
              offset: int = 0,
              ok: bool = Depends(require_admin)):
    """Get audit log of all admin actions"""
    logs = brain.get_audit_log(limit=limit, offset=offset)
    return {
        "logs": logs,
        "total": len(logs),
        "page": offset // limit if limit > 0 else 0,
        "page_size": limit
    }

@router.get("/export")
def export(ok: bool = Depends(require_admin)):
    """Export complete brain state for backup/analysis"""
    return brain.status()

# ================ Health Check ================

@router.get("/health")
def health():
    """Simple health check endpoint"""
    return {"status": "ok", "mode": brain.mode}