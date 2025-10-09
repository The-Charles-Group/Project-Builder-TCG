
from flask import Blueprint, request, jsonify
from pathlib import Path
from .ai_weighted_matcher import AIMatchingEngine

bp = Blueprint('ai_match', __name__, url_prefix='/api/step2/ai')
_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        path = Path(__file__).resolve().parent.parent / "data" / "AI_Matching_Rules_full.xlsx"
        _engine = AIMatchingEngine(str(path))
    return _engine

@bp.route('/weights', methods=['POST'])
def weights():
    data = request.get_json(silent=True) or {}
    eng = _get_engine()
    out = eng.score(data.get('rfp_text','') or '')
    return jsonify(out), 200
