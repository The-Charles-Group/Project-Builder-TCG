from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path
from ai_weighted_matcher import score_rfp

router = APIRouter(prefix="/api/step2/ai", tags=["ai-match"])

class WeightsReq(BaseModel):
    rfp_text: str

@router.post("/weights")
def weights(req: WeightsReq):
    ai_xlsx_path = "AI_Matching_Rules_full.xlsx"
    result = score_rfp(req.rfp_text or "", ai_xlsx_path)
    return result
