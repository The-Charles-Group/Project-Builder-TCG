
from flask import Blueprint, request, jsonify
from pathlib import Path
from .ai_relevance_v2 import RelevanceEngineV2

bp = Blueprint('ai_match_v2', __name__, url_prefix='/api/step2/ai')
_engine = None
def _eng():
    global _engine
    if _engine is None:
        path = Path(__file__).resolve().parent.parent / "data" / "AI_Matching_Rules_full.xlsx"
        _engine = RelevanceEngineV2(str(path) if path.exists() else None)
    return _engine

@bp.route('/weights_v2', methods=['POST'])
def weights_v2():
    data = request.get_json(silent=True) or {}
    eng = _eng()
    return jsonify(eng.score(data.get('rfp_text','') or '')), 200
