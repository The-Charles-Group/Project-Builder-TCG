from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from ai_weighted_matcher import score_rfp
from learning_brain.learning_brain import LearningBrain

router = APIRouter(prefix="/api/step2/ai", tags=["ai-match"])
LB = LearningBrain()

class WeightsReq(BaseModel):
    rfp_text: str

@router.post("/weights")
def weights(req: WeightsReq):
    ai_xlsx_path = "AI_Matching_Rules_full.xlsx"
    # Don't need deliverable_index_df - AI_Index already has the friendly names
    result = score_rfp(req.rfp_text or "", ai_xlsx_path, deliverable_index_df=None)
    
    if LB.mode == "active":
        # Example: assume result["scores"] is a list of dicts with Deliverable_Code and Score fields.
        base_scores = {}
        try:
            for row in result.get("scores", []):
                code = row.get("Deliverable_Code") or row.get("code") or row.get("deliverable_code")
                score = row.get("Score") or row.get("score") or 0.0
                if code is not None:
                    base_scores[str(code)] = float(score)
        except Exception:
            base_scores = {}

        blended = LB.blend_scores(base_scores, req.rfp_text, which="published")
        # merge blended["scores"] back into result
        for row in result.get("scores", []):
            code = row.get("Deliverable_Code") or row.get("code") or row.get("deliverable_code")
            if code in blended["scores"]:
                row["Score"] = float(blended["scores"][code])
        # (Optional) attach explanations
        result["learning_explain"] = blended.get("explain", {})
    
    return result
