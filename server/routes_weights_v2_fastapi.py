"""
FastAPI Router for AI Relevance V2 Endpoint
"""

from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
from server.ai_relevance_v2 import RelevanceEngineV2

router = APIRouter(prefix="/api/step2/ai", tags=["ai-match-v2"])


class WeightsReqV2(BaseModel):
    rfp_text: str


# Global engine instance (lazy loaded)
_engine: Optional[RelevanceEngineV2] = None


def _get_engine() -> RelevanceEngineV2:
    """Get or create the global RelevanceEngineV2 instance"""
    global _engine
    if _engine is None:
        # Try to find AI_Matching_Rules_full.xlsx in various locations
        possible_paths = [
            Path("AI_Matching_Rules_full.xlsx"),
            Path("data/AI_Matching_Rules_full.xlsx"),
            Path(__file__).resolve().parent.parent / "AI_Matching_Rules_full.xlsx",
            Path(__file__).resolve().parent.parent / "data" / "AI_Matching_Rules_full.xlsx"
        ]
        
        workbook_path = None
        for p in possible_paths:
            if p.exists():
                workbook_path = str(p)
                print(f"[AI V2] Using AI workbook: {workbook_path}")
                break
        
        if not workbook_path:
            print("[AI V2] No AI_Matching_Rules workbook found, will build from DB workbook")
        
        _engine = RelevanceEngineV2(workbook_path)
    
    return _engine


@router.post("/weights_v2")
def weights_v2(req: WeightsReqV2):
    """
    Score deliverables using V2 algorithm with:
    - Department intent gating
    - Execution vs Strategy bias
    - Budget-aware filtering
    - Sparsity shaping (max 4 in High band)
    
    Returns:
        {
            "deliverables": [...],
            "components": {...},
            "tasks": {...},
            "meta": {"top_departments": [...], "budget": ...}
        }
    """
    eng = _get_engine()
    return eng.score(req.rfp_text or "")
