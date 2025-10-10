
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path
from .ai_relevance_v2 import RelevanceEngineV2

router = APIRouter(prefix="/api/step2/ai", tags=["ai-match-v2"])

class WeightsReq(BaseModel):
    rfp_text: str

_engine = None
def _eng():
    global _engine
    if _engine is None:
        path = Path(__file__).resolve().parent.parent / "data" / "AI_Matching_Rules_full.xlsx"
        _engine = RelevanceEngineV2(str(path) if path.exists() else None)
    return _engine

@router.post("/weights_v2")
def weights_v2(req: WeightsReq):
    eng = _eng()
    return eng.score(req.rfp_text or "")
