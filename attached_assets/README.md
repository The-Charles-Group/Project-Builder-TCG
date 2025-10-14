
# APB Learning Brain (Drop‑in Package)

**What this is:** A small, industry‑agnostic **learning layer** for your Agency Project Builder that:
- lives **separately** from your existing match/scoring
- works in **OFF / SHADOW / ACTIVE** modes (admin‑controlled)
- stores lightweight **token↔deliverable** adjustments with caps + minima (no overfitting to a single RFP)
- provides an **Admin UI** at `/admin/brain` to **see, publish, undo, reset** learning
- returns **explanations** for how learning influences scores

## Install (5 minutes)

1. **Copy** the `learning_brain/` folder into your repo (e.g. repo root).
2. **Mount** in `main.py`:
   ```python
   from learning_brain.routes_brain import router as brain_router
   from fastapi.staticfiles import StaticFiles

   app.include_router(brain_router, prefix="/api/brain", tags=["learning"])
   app.mount("/admin/brain", StaticFiles(directory="learning_brain/static", html=True), name="brain_admin")
   ```
3. **Env vars** (Replit → Secrets):
   ```
   ADMIN_TOKEN=choose-a-long-random-string
   BRAIN_DB_PATH=/tmp/brain.sqlite3     # or ./exports/brain.sqlite3 for persistence
   LEARNING_MODE=off                    # off | shadow | active
   LEARNING_DELTA_CAP=0.30              # max absolute contribution per token
   LEARNING_MIN_SUPPORT=3               # min episodes before a token contributes
   LEARNING_RATE=0.03                   # tiny per-episode draft delta
   ```
4. **Add a LEARN button** (see `PATCH_INSTRUCTIONS.md`) and call `/api/brain/learn` from the UI.
5. **Open Admin**: `/admin/brain` → set mode, inspect episodes, publish/undo/reset.

## API (admin‑guarded where noted)
- `GET  /api/brain/status` → current mode, top draft/published adjustments
- `POST /api/brain/toggle` (admin) `{mode:"off|shadow|active"}`
- `POST /api/brain/learn`  (user) `{rfp_text, selected_deliverables, components_by_deliv?, outcome?, notes?}`
- `GET  /api/brain/episodes` (admin) list history
- `POST /api/brain/publish` (admin) promote **draft → published**
- `POST /api/brain/undo` (admin) revert last episode’s draft updates
- `POST /api/brain/reset` (admin) clear draft/published/episodes
- `POST /api/brain/preview` (admin) blend given base scores with learned deltas
- `GET  /api/brain/export` (admin) export status snapshot

## How it avoids overfitting / keeps broad applicability
- **No model fine‑tuning**; only tiny, bounded **token→deliverable** deltas.
- **Caps** (`LEARNING_DELTA_CAP`) and **min support** (`LEARNING_MIN_SUPPORT`).
- **Shadow mode** collects data but **doesn’t** affect live selections.
- **Human‑in‑the‑loop**: Admin must **Publish** to affect live scoring.

## Uninstall / Disable
- Set `LEARNING_MODE=off` to disable learning & influence.
- Remove the router and admin mounts to fully remove.
