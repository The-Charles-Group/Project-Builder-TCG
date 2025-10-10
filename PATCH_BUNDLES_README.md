# TCG AI Relevance V2 Patch Bundles

## Overview
This directory contains patch bundles for the AI Relevance V2 scoring system that fixes the critical over-scoring issue where everything scored 85-100%.

## Available Bundles

### 1. **TCG_All_In_One_Patch_v2_seeded.zip** (223 KB) ⭐ RECOMMENDED
**Single-bundle containing everything you need.**

**Contents:**
- `server/ai_relevance_v2.py` - Enhanced AI relevance scoring engine (22.5 KB)
- `server/routes_weights_v2_fastapi.py` - FastAPI router for v2 endpoint (1.9 KB)
- `static/static_weights_v2.js` - Frontend rendering for v2 results (4.4 KB)
- `static/static_weights_v2.css` - Styling for v2 UI components (1.2 KB)
- `data/AI_Matching_Rules_full.xlsx` - Pre-seeded AI matching rules (225 KB)
- `README_PATCH_V2.md` - V2 patch documentation
- `README_ALL_IN_ONE.md` - Bundle installation guide

**Use this for:** Complete installation with data + code + UI

---

### 2. **TCG_Relevance_Patch_v2.zip** (11 KB)
**Code-only patch without AI matching rules data.**

**Contents:**
- Server files (ai_relevance_v2.py, routes_weights_v2_fastapi.py)
- Static files (static_weights_v2.js, static_weights_v2.css)
- README_PATCH_V2.md

**Use this for:** Code updates when you already have AI_Matching_Rules_full.xlsx

---

### 3. **TCG_Agency_AI_Matching_Patch_v8_seeded.zip** (213 KB)
**AI matching rules data only.**

**Contents:**
- `data/AI_Matching_Rules_full.xlsx` - Seeded matching rules (1,583 rules)

**Use this for:** Data updates or when you only need the AI rules

---

## Key Features of V2

✅ **Department Gating** - Top 2 departments get 1.10× bonus, others get 0.35× penalty  
✅ **Execution vs Strategy Bias** - Execution keywords 1.15× bonus, strategy 0.60× penalty  
✅ **Sparsity Control** - Max 4 items in "High" band (≥85%)  
✅ **Budget Awareness** - Over-budget items get 0.60× penalty  
✅ **Hybrid Scoring** - Weight_Base (rules) + TF-IDF (lexical)  
✅ **Level Mapping** - L1=Deliverable, L2=Component, L3=Task

## Installation

### Quick Start (All-In-One Bundle)
```bash
# Extract the all-in-one bundle
unzip TCG_All_In_One_Patch_v2_seeded.zip

# Copy files to your project
cp -r server/ static/ data/ /path/to/your/project/

# Add router to main.py
from server.routes_weights_v2_fastapi import router as weights_v2_router
app.include_router(weights_v2_router)

# Add UI components to index.html (see static files)
```

### Testing
```bash
# Test the v2 endpoint
curl -X POST http://localhost:5000/api/step2/ai/weights_v2 \
  -H "Content-Type: application/json" \
  -d '{"rfp_text": "We need paid media campaign with Meta and Google Ads. Budget: $100k"}'
```

## Bundler Script

The `create_all_in_one_patch.py` script can regenerate the all-in-one bundle from source zips:

```python
python create_all_in_one_patch.py
```

This script:
1. Extracts v2 code from TCG_Relevance_Patch_v2.zip
2. Pulls AI rules from TCG_Agency_AI_Matching_Patch_v8_seeded.zip  
3. Bundles everything into TCG_All_In_One_Patch_v2_seeded.zip

---

## Comparison: V1 vs V2

| Feature | V1 (Original) | V2 (Enhanced) |
|---------|---------------|---------------|
| Score Distribution | Everything 85-100% ❌ | Proper High/Mid/Low bands ✅ |
| Department Focus | None | Top-2 gating with bonuses ✅ |
| Execution Bias | None | Execution 1.15×, Strategy 0.60× ✅ |
| Budget Awareness | None | Over-budget penalty 0.60× ✅ |
| Sparsity | No control ❌ | Max 4 in High band ✅ |

## Support

For questions or issues, refer to the main project documentation in `replit.md`.
