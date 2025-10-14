from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from .learning_brain import LearningBrain
from .security import require_admin
from .brain_store import list_episodes

router = APIRouter()
brain = LearningBrain()

class LearnPayload(BaseModel):
    rfp_text: str = ""
    selected_deliverables: List[str] = Field(default_factory=list)
    components_by_deliv: Optional[Dict[str, Any]] = None
    outcome: str = "accepted"
    notes: Optional[str] = None

class TogglePayload(BaseModel):
    mode: str = Field(pattern="^(off|shadow|active)$")

class PreviewPayload(BaseModel):
    rfp_text: str = ""
    base_scores: Dict[str, float] = Field(default_factory=dict)
    which: str = "published"

class ParamsPayload(BaseModel):
    LEARNING_DELTA_CAP: Optional[float] = None
    LEARNING_MIN_SUPPORT: Optional[int] = None
    LEARNING_RATE: Optional[float] = None

@router.get("/status")
def status():
    return brain.status()

@router.post("/toggle")
def toggle(payload: TogglePayload, ok: bool = Depends(require_admin)):
    return brain.set_mode(payload.mode)

@router.post("/params")
def params(payload: ParamsPayload, ok: bool = Depends(require_admin)):
    p = {k:v for k,v in payload.dict().items() if v is not None}
    return brain.set_params({k:str(v) for k,v in p.items()})

@router.post("/learn")
def learn(payload: LearnPayload):
    return brain.learn(
        rfp_text=payload.rfp_text,
        selected_deliverables=payload.selected_deliverables,
        components_by_deliv=payload.components_by_deliv,
        outcome=payload.outcome,
        notes=payload.notes
    )

@router.get("/episodes")
def episodes(limit: int = 50, offset: int = 0, ok: bool = Depends(require_admin)):
    return {"items": list_episodes(limit=limit, offset=offset)}

@router.post("/publish")
def publish(ok: bool = Depends(require_admin)):
    return brain.publish()

@router.post("/reset")
def reset(ok: bool = Depends(require_admin)):
    return brain.reset()

@router.post("/undo")
def undo(ok: bool = Depends(require_admin)):
    return brain.undo()

@router.post("/preview")
def preview(payload: PreviewPayload, ok: bool = Depends(require_admin)):
    return brain.blend_scores(payload.base_scores, payload.rfp_text, which=payload.which)

@router.get("/export")
def export(ok: bool = Depends(require_admin)):
    return brain.status()