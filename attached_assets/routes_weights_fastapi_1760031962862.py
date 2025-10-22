
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path
from .ai_weighted_matcher import AIMatchingEngine

router = APIRouter(prefix="/api/step2/ai", tags=["ai-match"])

class WeightsReq(BaseModel):
    rfp_text: str

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        path = Path(__file__).resolve().parent.parent / "data" / "AI_Matching_Rules_full.xlsx"
        _engine = AIMatchingEngine(str(path))
    return _engine

@router.post("/weights")
def weights(req: WeightsReq):
    eng = _get_engine()
    return eng.score(req.rfp_text or "")
