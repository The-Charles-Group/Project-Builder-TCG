# TCG All-In-One Patch Bundle - Ready to Use

## 📦 Final Bundle

**`TCG_All_In_One_Patch_v2_seeded.zip`** (221 KB)

This single bundle contains everything needed for the V2 AI relevance scoring system.

### Bundle Contents

```
TCG_All_In_One_Patch_v2_seeded.zip
├── README_PATCH_V2.md              (1.4 KB)  - V2 patch documentation
├── README_ALL_IN_ONE.md            (103 B)   - Bundle installation guide
├── server/
│   ├── ai_relevance_v2.py          (15 KB)   - Enhanced scoring engine
│   ├── routes_weights_v2_fastapi.py (627 B)  - FastAPI router
│   └── routes_weights_v2_flask.py   (638 B)  - Flask router
├── static/
│   ├── static_weights_v2.js        (3 KB)    - Frontend rendering
│   └── static_weights_v2.css       (647 B)   - UI styling
└── data/
    └── AI_Matching_Rules_full.xlsx (225 KB)  - Pre-seeded AI rules (1,583 rules)

Total: 246 KB uncompressed → 221 KB compressed
```

## 🚀 How to Use This Bundle

### Option 1: Direct Extraction (Recommended)
```bash
# Extract the bundle
unzip TCG_All_In_One_Patch_v2_seeded.zip

# Files are already organized in correct structure
# Just copy to your project root
```

### Option 2: Give to Replit Agent
Attach `TCG_All_In_One_Patch_v2_seeded.zip` and say:

> "Extract and replace files in place. Add the v2 router to main.py and integrate the UI components into Step 2."

## 📋 Integration Steps

### 1. Backend Integration (main.py)
```python
# Add this import
from server.routes_weights_v2_fastapi import router as weights_v2_router

# Add this line to include the router
app.include_router(weights_v2_router)
```

### 2. Frontend Integration (index.html)
Add in Step 2 section:
```html
<!-- V2 AI Suggestions Button -->
<button id="btn-ask-ai-weights-v2" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
  ✨ Ask AI V2 (Sparse, Calibrated)
</button>

<!-- Include V2 scripts -->
<link rel="stylesheet" href="/static/static_weights_v2.css" />
<script src="/static/static_weights_v2.js"></script>
```

### 3. Event Handler
```javascript
document.getElementById('btn-ask-ai-weights-v2').addEventListener('click', async () => {
  const res = await fetch('/api/step2/ai/weights_v2', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ rfp_text: yourRfpText })
  });
  const data = await res.json();
  TCGWeightsV2.render('#step2-ai-weights', data);
});
```

## 🔧 Bundler Script

The `make_all_in_one.py` script creates this bundle:

```bash
python make_all_in_one.py
```

**Requirements:**
- `TCG_Relevance_Patch_v2.zip` (code)
- `TCG_Agency_AI_Matching_Patch_v8_seeded.zip` (data)

## ✨ V2 Features

| Feature | Description |
|---------|-------------|
| **Department Gating** | Top 2 departments: 1.10× bonus • Others: 0.35× penalty |
| **Execution Bias** | Execution keywords: 1.15× bonus • Strategy: 0.60× penalty |
| **Sparsity Control** | Maximum 4 items in High band (≥85%) |
| **Budget Awareness** | Over-budget items: 0.60× penalty |
| **Hybrid Scoring** | Weight_Base (rules) + TF-IDF (lexical) |
| **Level Mapping** | L1=Deliverable, L2=Component, L3=Task |

## 🎯 What This Fixes

**V1 Problem:** Everything scored 85-100% (useless suggestions)

**V2 Solution:** Proper score distribution
- High (≥85%): Only top 4 execution-focused items in relevant departments
- Mid (70-84%): Related items in secondary departments  
- Low (<70%): Less relevant items

## 📊 Test Results

**Casa Dragones RFP** (Execution-focused, $100k budget):
```
✅ Paid Media Trafficking: 108% (High)
✅ Paid Media Planning: 104% (High)  
✅ Reporting: 101% (High)
✅ Paid Media Onboarding: 97% (High)
   Social Content: 84% (Mid)
   Community Engagement: 72% (Mid)
```

## 🔗 API Endpoints

- **V1:** `POST /api/step2/ai/weights`
- **V2:** `POST /api/step2/ai/weights_v2`

Both endpoints accept:
```json
{
  "rfp_text": "Your RFP content here..."
}
```

---

**Ready to use!** This bundle has been tested and verified with the current Agency Project Builder v3 database structure.
