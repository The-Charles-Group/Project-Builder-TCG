# APB — **All‑in‑One Replit Agent Playbook** (Single File)

> **Give this one file to the Replit Agent.** It contains *everything* in one place: a self‑contained “Learning Brain” (admin‑controlled, industry‑agnostic), instructions to mount it, a LEARN button snippet, optional blending patch, performance upgrades (startup lifespan warm‑caches, AsyncClient reuse, optional embeddings cache), and optional tests (Playwright E2E + Locust).  
> Nothing here is over‑fit to any single RFP; it’s broad by design.

---
## ✅ Agent Task List (do these in order)

1. **Create files** from the “Create these files exactly” section.
2. **Patch** `main.py` to mount the brain API + Admin UI.
3. **Add LEARN button** to the UI with the provided snippet.
4. (Optional) **Blend** learned deltas into weights when `LEARNING_MODE=active`.
5. (Optional) Apply **performance upgrades**: startup lifespan cache, global `httpx.AsyncClient`, optional embeddings cache, Uvicorn run flags.
6. (Optional) Add **Playwright E2E** and **Locust** files and run them.
7. **Set env vars** (below) and **verify** endpoints.

---
## 1) Create these files **exactly**

> Create each file *with the exact path and content* below.
### 1.1 `learning_brain/__init__.py`
```python
# empty package marker
```
### 1.2 `learning_brain/security.py`
```python
from fastapi import Header, HTTPException
import os

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

def require_admin(authorization: str | None = Header(None)):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin token not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header (Bearer)")
    token = authorization.split(" ", 1)[1].strip()
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return True
```
### 1.3 `learning_brain/brain_store.py`
```python
from __future__ import annotations
import os, sqlite3, json, time, hashlib, threading
from typing import Any, Dict, List, Tuple

DEFAULT_DB = os.getenv("BRAIN_DB_PATH", "/tmp/brain.sqlite3")
_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS episodes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  rfp_hash TEXT NOT NULL,
  industry TEXT,
  metadata TEXT,
  selections TEXT
);
CREATE TABLE IF NOT EXISTS weights_draft(
  deliverable_code TEXT NOT NULL,
  token TEXT NOT NULL,
  delta REAL NOT NULL,
  support INTEGER NOT NULL DEFAULT 0,
  updated_ts INTEGER NOT NULL,
  PRIMARY KEY(deliverable_code, token)
);
CREATE TABLE IF NOT EXISTS weights_published(
  deliverable_code TEXT NOT NULL,
  token TEXT NOT NULL,
  delta REAL NOT NULL,
  support INTEGER NOT NULL DEFAULT 0,
  updated_ts INTEGER NOT NULL,
  PRIMARY KEY(deliverable_code, token)
);
CREATE TABLE IF NOT EXISTS episode_updates(
  episode_id INTEGER NOT NULL,
  deliverable_code TEXT NOT NULL,
  token TEXT NOT NULL,
  delta_change REAL NOT NULL
);
"""

def _connect(db_path: str = DEFAULT_DB):
    os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init(db_path: str = DEFAULT_DB):
    with _LOCK:
        conn = _connect(db_path)
        try:
            for stmt in SCHEMA.strip().split(';'):
                s = stmt.strip()
                if s:
                    conn.execute(s+';')
            conn.commit()
        finally:
            conn.close()

def _hash_text(text: str) -> str:
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()

def get_setting(key: str, default: str = "", db_path: str = DEFAULT_DB) -> str:
    with _LOCK:
        conn = _connect(db_path)
        try:
            r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return r["value"] if r else default
        finally:
            conn.close()

def set_setting(key: str, value: str, db_path: str = DEFAULT_DB):
    with _LOCK:
        conn = _connect(db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
            conn.commit()
        finally:
            conn.close()

def add_episode(rfp_text: str, selections: Dict[str, Any], industry: str | None, metadata: Dict[str, Any], db_path: str = DEFAULT_DB) -> int:
    with _LOCK:
        conn = _connect(db_path)
        try:
            ts = int(time.time()*1000)
            rfp_hash = _hash_text(rfp_text)
            conn.execute(
                "INSERT INTO episodes(ts,rfp_hash,industry,metadata,selections) VALUES(?,?,?,?,?)",
                (ts, rfp_hash, industry or "", json.dumps(metadata or {}), json.dumps(selections or {}))
            )
            eid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            conn.commit()
            return int(eid)
        finally:
            conn.close()

def list_episodes(limit: int = 50, offset: int = 0, db_path: str = DEFAULT_DB) -> List[Dict[str,Any]]:
    with _LOCK:
        conn = _connect(db_path)
        try:
            rows = conn.execute("SELECT id,ts,rfp_hash,industry,metadata,selections FROM episodes ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
            return [{
                "id": r["id"], "ts": r["ts"], "rfp_hash": r["rfp_hash"],
                "industry": r["industry"],
                "metadata": json.loads(r["metadata"] or "{}"),
                "selections": json.loads(r["selections"] or "{}"),
            } for r in rows]
        finally:
            conn.close()

def upsert_draft_updates(episode_id: int, updates: List[Tuple[str,str,float]], support_inc: int = 1, db_path: str = DEFAULT_DB):
    now = int(time.time()*1000)
    with _LOCK:
        conn = _connect(db_path)
        try:
            for code, token, delta_change in updates:
                row = conn.execute("SELECT delta,support FROM weights_draft WHERE deliverable_code=? AND token=?", (code, token)).fetchone()
                if row:
                    new_delta = float(row["delta"]) + float(delta_change)
                    new_support = int(row["support"]) + int(support_inc)
                    conn.execute("UPDATE weights_draft SET delta=?, support=?, updated_ts=? WHERE deliverable_code=? AND token=?", (new_delta, new_support, now, code, token))
                else:
                    conn.execute("INSERT INTO weights_draft(deliverable_code,token,delta,support,updated_ts) VALUES(?,?,?,?,?)", (code, token, float(delta_change), int(support_inc), now))
                conn.execute("INSERT INTO episode_updates(episode_id,deliverable_code,token,delta_change) VALUES(?,?,?,?)", (episode_id, code, token, float(delta_change)))
            conn.commit()
        finally:
            conn.close()

def publish_draft(db_path: str = DEFAULT_DB):
    with _LOCK:
        conn = _connect(db_path)
        try:
            conn.execute("DELETE FROM weights_published")
            conn.execute("INSERT INTO weights_published(deliverable_code,token,delta,support,updated_ts) SELECT deliverable_code,token,delta,support,updated_ts FROM weights_draft")
            conn.commit()
        finally:
            conn.close()

def reset_all(db_path: str = DEFAULT_DB):
    with _LOCK:
        conn = _connect(db_path)
        try:
            for table in ("weights_draft","weights_published","episodes","episode_updates"):
                conn.execute(f"DELETE FROM {table}")
            conn.commit()
        finally:
            conn.close()

def undo_last_episode(db_path: str = DEFAULT_DB) -> bool:
    with _LOCK:
        conn = _connect(db_path)
        try:
            row = conn.execute("SELECT id FROM episodes ORDER BY id DESC LIMIT 1").fetchone()
            if not row: return False
            eid = int(row["id"])
            upd = conn.execute("SELECT deliverable_code,token,delta_change FROM episode_updates WHERE episode_id=?", (eid,)).fetchall()
            for r in upd:
                code, token, change = r["deliverable_code"], r["token"], float(r["delta_change"])
                row2 = conn.execute("SELECT delta,support FROM weights_draft WHERE deliverable_code=? AND token=?", (code, token)).fetchone()
                if row2:
                    new_delta = float(row2["delta"]) - change
                    new_support = max(0, int(row2["support"]) - 1)
                    conn.execute("UPDATE weights_draft SET delta=?, support=? WHERE deliverable_code=? AND token=?", (new_delta, new_support, code, token))
            conn.execute("DELETE FROM episode_updates WHERE episode_id=?", (eid,))
            conn.execute("DELETE FROM episodes WHERE id=?", (eid,))
            conn.commit()
            return True
        finally:
            conn.close()

def get_weights(which: str = "published", limit: int = 200, db_path: str = DEFAULT_DB) -> List[Dict[str,Any]]:
    table = "weights_published" if which == "published" else "weights_draft"
    with _LOCK:
        conn = _connect(db_path)
        try:
            rows = conn.execute(f"SELECT deliverable_code,token,delta,support,updated_ts FROM {table} ORDER BY ABS(delta) DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

```
### 1.4 `learning_brain/learning_brain.py`
```python
from __future__ import annotations
import os, re, math
from typing import Dict, Any, List, Tuple, Optional
from .brain_store import (
    init, add_episode, upsert_draft_updates,
    get_weights, publish_draft, reset_all, undo_last_episode,
    get_setting, set_setting
)

TOKEN_RE = re.compile(r"[A-Za-z0-9\-\_]{3,}")

def _get_param_float(name: str, default: float) -> float:
    v = get_setting(name, os.getenv(name, str(default)))
    try:
        return float(v)
    except Exception:
        return float(default)

def _get_param_int(name: str, default: int) -> int:
    v = get_setting(name, os.getenv(name, str(default)))
    try:
        return int(v)
    except Exception:
        return int(default)

def _get_mode_default() -> str:
    m = get_setting("mode", os.getenv("LEARNING_MODE", "off")).strip().lower()
    return m if m in ("off","shadow","active") else "off"

def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "")][:5000]

def detect_industry(text: str) -> Optional[str]:
    mapping = {
        "education": ["school","students","admissions","enrollment","university","college"],
        "beverage": ["spirits","tequila","vodka","drink","bar","liquor","beverage"],
        "nonprofit": ["donor","fundraising","nonprofit","foundation","charity"]
    }
    tl = (text or "").lower()
    for k, kws in mapping.items():
        if any(kw in tl for kw in kws):
            return k
    return None

class LearningBrain:
    def __init__(self):
        init()
        self.mode = _get_mode_default()

    def set_mode(self, mode: str):
        m = (mode or "off").strip().lower()
        if m not in ("off","shadow","active"):
            m = "off"
        set_setting("mode", m)
        self.mode = m
        return {"mode": self.mode}

    def status(self) -> Dict[str,Any]:
        return {
            "mode": self.mode,
            "params": {
                "LEARNING_DELTA_CAP": _get_param_float("LEARNING_DELTA_CAP", 0.30),
                "LEARNING_MIN_SUPPORT": _get_param_int("LEARNING_MIN_SUPPORT", 3),
                "LEARNING_RATE": _get_param_float("LEARNING_RATE", 0.03),
            },
            "top_draft": get_weights("draft", 50),
            "top_published": get_weights("published", 50)
        }

    def set_params(self, params: Dict[str, str]) -> Dict[str,Any]:
        for k, v in (params or {}).items():
            if k not in ("LEARNING_DELTA_CAP","LEARNING_MIN_SUPPORT","LEARNING_RATE"):
                continue
            set_setting(k, str(v))
        return {"message": "params updated", "params": self.status()["params"]}

    def learn(self, rfp_text: str, selected_deliverables: List[str], components_by_deliv: Dict[str, Any] | None, outcome: str, notes: str | None) -> Dict[str,Any]:
        ind = detect_industry(rfp_text)
        selections = {"deliverables": selected_deliverables or [], "components_by_deliv": components_by_deliv or {}}
        meta = {"outcome": outcome or "accepted", "notes": notes or ""}
        eid = add_episode(rfp_text, selections, ind, meta)
        if self.mode == "off":
            return {"message": "learn recorded (mode=off, no updates)", "episode_id": eid}

        lr = _get_param_float("LEARNING_RATE", 0.03)
        toks = tokenize(rfp_text)
        updates: List[Tuple[str,str,float]] = []
        for code in (selected_deliverables or []):
            for t in toks:
                updates.append((code, t, lr))
        upsert_draft_updates(eid, updates, support_inc=1)
        return {"message": f"learn recorded (mode={self.mode})", "episode_id": eid, "updates": len(updates)}

    def publish(self) -> Dict[str,Any]:
        publish_draft()
        return {"message": "draft → published"}

    def reset(self) -> Dict[str,Any]:
        reset_all()
        return {"message": "brain reset"}

    def undo(self) -> Dict[str,Any]:
        ok = undo_last_episode()
        return {"message": "undone last episode" if ok else "nothing to undo"}

    def blend_scores(self, base_scores: Dict[str, float], rfp_text: str, which: str = "published") -> Dict[str,Any]:
        delta_cap = _get_param_float("LEARNING_DELTA_CAP", 0.30)
        min_support = _get_param_int("LEARNING_MIN_SUPPORT", 3)
        tok = set(tokenize(rfp_text))
        weights = get_weights(which=which, limit=50000)
        by_code: Dict[str, Dict[str, float]] = {}
        for w in weights:
            if int(w["support"]) < min_support: 
                continue
            d = float(w["delta"])
            if abs(d) > delta_cap:
                d = math.copysign(delta_cap, d)
            by_code.setdefault(w["deliverable_code"], {})[w["token"]] = d

        scores_out: Dict[str, float] = {}
        explain: Dict[str, Dict[str, float]] = {}
        for code, base in base_scores.items():
            contrib = 0.0
            per_tok: Dict[str, float] = {}
            m = by_code.get(code) or {}
            for t in tok:
                if t in m:
                    per_tok[t] = m[t]
                    contrib += m[t]
            scores_out[code] = float(base) + contrib
            if per_tok:
                topk = dict(sorted(per_tok.items(), key=lambda kv: abs(kv[1]), reverse=True)[:10])
                explain[code] = topk
        return {"scores": scores_out, "explain": explain}

```
### 1.5 `learning_brain/routes_brain.py`
```python
from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from .learning_brain import LearningBrain
from .security import require_admin
from .brain_store import list_episodes

router = APIRouter()
brain = LearningBrain()

class LearnPayload(BaseModel):
    rfp_text: str = ""
    selected_deliverables: List[str] = Field(default_factory=list)
    components_by_deliv: Optional[Dict[str, Any]] = None
    outcome: str = "accepted"
    notes: Optional[str] = None

class TogglePayload(BaseModel):
    mode: str = Field(pattern="^(off|shadow|active)$")

class PreviewPayload(BaseModel):
    rfp_text: str = ""
    base_scores: Dict[str, float] = Field(default_factory=dict)
    which: str = "published"

class ParamsPayload(BaseModel):
    LEARNING_DELTA_CAP: Optional[float] = None
    LEARNING_MIN_SUPPORT: Optional[int] = None
    LEARNING_RATE: Optional[float] = None

@router.get("/status")
def status():
    return brain.status()

@router.post("/toggle")
def toggle(payload: TogglePayload, ok: bool = Depends(require_admin)):
    return brain.set_mode(payload.mode)

@router.post("/params")
def params(payload: ParamsPayload, ok: bool = Depends(require_admin)):
    p = {k:v for k,v in payload.dict().items() if v is not None}
    return brain.set_params({k:str(v) for k,v in p.items()})

@router.post("/learn")
def learn(payload: LearnPayload):
    return brain.learn(
        rfp_text=payload.rfp_text,
        selected_deliverables=payload.selected_deliverables,
        components_by_deliv=payload.components_by_deliv,
        outcome=payload.outcome,
        notes=payload.notes
    )

@router.get("/episodes")
def episodes(limit: int = 50, offset: int = 0, ok: bool = Depends(require_admin)):
    return {"items": list_episodes(limit=limit, offset=offset)}

@router.post("/publish")
def publish(ok: bool = Depends(require_admin)):
    return brain.publish()

@router.post("/reset")
def reset(ok: bool = Depends(require_admin)):
    return brain.reset()

@router.post("/undo")
def undo(ok: bool = Depends(require_admin)):
    return brain.undo()

@router.post("/preview")
def preview(payload: PreviewPayload, ok: bool = Depends(require_admin)):
    return brain.blend_scores(payload.base_scores, payload.rfp_text, which=payload.which)

@router.get("/export")
def export(ok: bool = Depends(require_admin)):
    return brain.status()

```
### 1.6 `learning_brain/static/admin_brain.html`
```html
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>Learning Brain Admin</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
    .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
    .card { border: 1px solid #ddd; padding: 16px; border-radius: 8px; margin: 12px 0; }
    pre { background: #f6f8fa; padding: 10px; overflow: auto; }
  </style>
</head>
<body>
  <h1>Learning Brain — Admin</h1>
  <div class=\"row\">
    <input id=\"token\" type=\"password\" placeholder=\"Admin token (Bearer)\" style=\"min-width: 320px;\" />
    <select id=\"mode\">
      <option value=\"off\">OFF</option>
      <option value=\"shadow\">SHADOW</option>
      <option value=\"active\">ACTIVE</option>
    </select>
    <button onclick=\"setMode()\">Set Mode</button>
    <button onclick=\"getStatus()\">Refresh Status</button>
    <button onclick=\"publish()\">Publish Draft</button>
    <button onclick=\"undo()\">Undo Last</button>
    <button onclick=\"resetAll()\">Reset All</button>
  </div>
  <div class=\"card\">
    <h3>Status</h3>
    <pre id=\"status\">...</pre>
  </div>
  <div class=\"card\">
    <h3>Episodes</h3>
    <button onclick=\"loadEpisodes()\">Load Episodes</button>
    <pre id=\"episodes\">...</pre>
  </div>
  <div class=\"card\">
    <h3>Preview</h3>
    <textarea id=\"rfp\" rows=\"6\" style=\"width:100%\" placeholder=\"Sample RFP text\"></textarea>
    <textarea id=\"base\" rows=\"6\" style=\"width:100%\" placeholder='{\"DEL-0036\": 0.42, \"DEL-0029\": 0.35}'></textarea>
    <button onclick=\"preview('published')\">Preview Published</button>
    <button onclick=\"preview('draft')\">Preview Draft</button>
    <pre id=\"preview\">...</pre>
  </div>
<script>
function auth(){ const t=document.getElementById('token').value.trim(); return t?{Authorization:'Bearer '+t}:{ }; }
async function getStatus(){ const r=await fetch('/api/brain/status'); document.getElementById('status').textContent=JSON.stringify(await r.json(),null,2); }
async function setMode(){ const m=document.getElementById('mode').value; const r=await fetch('/api/brain/toggle',{method:'POST',headers:{'Content-Type':'application/json',...auth()},body:JSON.stringify({mode:m})}); alert(JSON.stringify(await r.json())); }
async function publish(){ const r=await fetch('/api/brain/publish',{method:'POST',headers:auth()}); alert((await r.json()).message||r.status); }
async function undo(){ const r=await fetch('/api/brain/undo',{method:'POST',headers:auth()}); alert((await r.json()).message||r.status); }
async function resetAll(){ if(!confirm('Clear all learning?'))return; const r=await fetch('/api/brain/reset',{method:'POST',headers:auth()}); alert((await r.json()).message||r.status); }
async function loadEpisodes(){ const r=await fetch('/api/brain/episodes?limit=50',{headers:auth()}); document.getElementById('episodes').textContent=JSON.stringify(await r.json(),null,2); }
async function preview(which){ const rfp=document.getElementById('rfp').value||''; let base={}; try{ base=JSON.parse(document.getElementById('base').value||'{}'); }catch(e){} const r=await fetch('/api/brain/preview',{method:'POST',headers:{'Content-Type':'application/json',...auth()},body:JSON.stringify({rfp_text:rfp,base_scores:base,which})}); document.getElementById('preview').textContent=JSON.stringify(await r.json(),null,2); }
getStatus();
</script>
</body>
</html>
```
## 2) Patch **`main.py`** to mount learning brain & admin UI

Add these imports near your existing FastAPI imports:
```python
from learning_brain.routes_brain import router as brain_router
from fastapi.staticfiles import StaticFiles
```
Mount the API + Admin UI after `app = FastAPI(...)` is created:
```python
app.include_router(brain_router, prefix="/api/brain", tags=["learning"])
app.mount("/admin/brain", StaticFiles(directory="learning_brain/static", html=True), name="brain_admin")
```
**Env (Replit → Secrets)**
```
ADMIN_TOKEN=choose-a-strong-random-string
BRAIN_DB_PATH=/tmp/brain.sqlite3     # or ./exports/brain.sqlite3 for persistence
LEARNING_MODE=off                    # off | shadow | active
LEARNING_DELTA_CAP=0.30              # cap impact per token
LEARNING_MIN_SUPPORT=3               # min episodes before a token contributes
LEARNING_RATE=0.03                   # tiny per-episode draft bump
```

---
## 3) Add a **LEARN** button (opt‑in; draft‑only)

**In `static/index.html`**, somewhere next to “Analyze with AI”:
```html
<button id="learnBtn" type="button">LEARN (opt‑in)</button>
```
**In `static/app.js`** (or a small file loaded on that page):
```js
(function attachLearn(){
  const btn = document.getElementById('learnBtn');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const rfpText = (window.APB?.step2?.rfpText) || "";
    const selected = Array.from(window.APB?.step2?.selectedCodes || []);
    const components = (window.APB?.selectionStore?.componentsByDeliv)
      ? Object.fromEntries(window.APB.selectionStore.componentsByDeliv) : {};
    try {
      const res = await fetch("/api/brain/learn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rfp_text: rfpText,
          selected_deliverables: selected,
          components_by_deliv: components,
          outcome: "accepted",
          notes: "learn-from-ui"
        })
      });
      const data = await res.json();
      alert("Learning event: " + (data?.message || res.status));
    } catch (e) {
      alert("Learn call failed: " + e);
    }
  });
})();
```
> **Note:** Learning is **draft‑only** until you publish in `/admin/brain`. This ensures no overfitting or surprise changes.

---
## 4) (Optional) Blend learned deltas into live weights

> Keep it separate unless you turn `LEARNING_MODE=active`. This preserves broad, industry‑agnostic behavior.

**In `routes_weights_fastapi.py`**, lightly blend when ACTIVE:
```python
from learning_brain.learning_brain import LearningBrain
LB = LearningBrain()

@router.post("/weights")
def weights(req: WeightsReq):
    result = score_rfp(req.rfp_text or "", "AI_Matching_Rules_full.xlsx", deliverable_index_df=None)

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
```

---
## 5) (Optional) Performance upgrades (kept generic)

### 5.1 Warm caches & reuse **AsyncClient** (FastAPI **lifespan**)
> Load heavy Excel once, cache to pickle, and reuse `httpx.AsyncClient` across requests.
> Official docs recommend **lifespan** for startup/shutdown. HTTPX clients use **connection pooling**.
 citeturn0search0turn0search4

**In `main.py`** add imports:
```python
from contextlib import asynccontextmanager
import httpx, asyncio, pandas as pd, os
from functools import lru_cache
```
**Replace or wrap your `app = FastAPI(...)` with:**
```python
@lru_cache(maxsize=1)
def load_ai_index():
    xlsx = "AI_Matching_Rules_full.xlsx"
    pkl = xlsx + ".pkl"
    try:
        if os.path.exists(pkl) and os.path.getmtime(pkl) >= os.path.getmtime(xlsx):
            return pd.read_pickle(pkl)
    except Exception:
        pass
    df = pd.read_excel(xlsx, sheet_name="AI_Index", engine="openpyxl")
    try:
        df.to_pickle(pkl)
    except Exception:
        pass
    return df

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=30.0)
    try:
        app.state.ai_index_df = load_ai_index()
        print(f"[STARTUP] AI_Index cached: {len(app.state.ai_index_df)} rows")
    except Exception as e:
        print(f"[STARTUP][WARN] preload failed: {e}")
    yield
    try:
        await app.state.http.aclose()
    except Exception:
        pass

app = FastAPI(lifespan=lifespan)
```
### 5.2 Suggested Uvicorn flags
Run with uvloop & httptools (or via Gunicorn worker). citeturn0search2turn0search14
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --loop uvloop --http httptools
```
### 5.3 (Optional) Embeddings memo cache (SQLite)
```python
import sqlite3, hashlib, json, threading, os
_EMBED_DB = os.getenv("EMBED_DB", "/tmp/embed_cache.sqlite3")
_EMBED_LOCK = threading.Lock()

def _embed_db():
    conn = sqlite3.connect(_EMBED_DB, check_same_thread=False, timeout=10)
    with conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS embeds(
            key TEXT PRIMARY KEY, text_hash TEXT, model TEXT, vec BLOB)""")
    return conn

def _h(x: str) -> str: return hashlib.sha256((x or "").encode("utf-8")).hexdigest()

def cached_embed_many(texts: list[str], model: str, embed_callable):
    if not texts: return []
    conn = _embed_db()
    out, pending = [None]*len(texts), []
    for i, t in enumerate(texts):
        key = f"{model}:{_h(t)}"
        row = conn.execute("SELECT vec FROM embeds WHERE key=?", (key,)).fetchone()
        if row: out[i] = json.loads(row[0])
        else:   pending.append((i, t, key))
    if pending:
        vecs = embed_callable([t for _, t, _ in pending])
        for (i, t, key), v in zip(pending, vecs):
            out[i] = v
            with conn: conn.execute("INSERT OR REPLACE INTO embeds(key,text_hash,model,vec) VALUES(?,?,?,?)",
                                    (key, key.split(":",1)[1], model, json.dumps(v)))
    return out
```
### 5.4 (Optional) SSE progress endpoint
```python
from fastapi import Request
from starlette.responses import StreamingResponse

@app.get("/api/ai/stream/{job_id}")
async def stream(job_id: str, request: Request):
    async def gen():
        last = None
        while True:
            if await request.is_disconnected(): break
            s = JOB_STORE.get(job_id)
            if s and s != last:
                yield f"data: {json.dumps({'stage': getattr(s,'current_stage',None), 'progress': getattr(s,'progress',None)})}\n\n"
                last = s
            await asyncio.sleep(0.5)
    return StreamingResponse(gen(), media_type="text/event-stream")
```
SSE + `StreamingResponse` are common for progress updates. citeturn1search2turn1search11

---
## 6) (Optional) Tests in one go

### 6.1 Playwright E2E
Create **`tests/e2e_upload_rfp.spec.ts`**:
```ts
import { test, expect } from "@playwright/test";
const APP = process.env.APP_URL || "https://tcg-agency-project-builder-v2dot8dot1.replit.app/";

test("RFP flows to plan + pricing", async ({ page }) => {
  await page.goto(APP, { waitUntil: "domcontentloaded" });

  // Upload
  const chooserPromise = page.waitForEvent('filechooser');
  await page.getByText(/Upload Your RFP/i).click();
  const chooser = await chooserPromise;
  await chooser.setFiles("./attached_assets/FINAL Uncommon Schools - May 2025 Media Agency RFP.pdf");

  // Analyze
  await page.getByRole('button', { name: /Analyze with AI/i }).click();
  await expect(page.getByText(/Analyzing/i)).toBeVisible({ timeout: 120000 });

  // Key deliverables show up (names may vary slightly)
  for (const text of [
    "Creative Strategy / Campaign Plan Deck",
    "Paid Media Planning",
    "Paid Media Buying & Activation",
    "Reporting",
    "Competitive Landscape Analysis",
    "Qualitative Research",
    "Meetings"
  ]) {
    await expect(page.getByText(text)).toBeVisible({ timeout: 240000 });
  }

  // Pricing present
  await expect(page.locator('[data-testid="pricing-table"]')).toBeVisible();
});
```
Use Playwright’s `setInputFiles()` for uploads. citeturn1search0

```bash
pip install -U playwright && python -m playwright install --with-deps
npx playwright test tests/e2e_upload_rfp.spec.ts
```

### 6.2 Locust smoke test
Create **`locustfile.py`**:
```python
from locust import HttpUser, task, between

RFP_SNIPPET = "media management across markets with paid social, reporting, optimizations..."

class APBUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def weights_fast(self):
        self.client.post("/api/step2/ai/weights", json={"rfp_text": RFP_SNIPPET})

    @task(1)
    def options(self):
        self.client.get("/api/options")
```
```bash
pip install -U locust
locust -f locustfile.py --host http://localhost:8000
```
Docs: citeturn1search4

---
## 7) Env and run command

**Env (Replit → Secrets)**
```
ADMIN_TOKEN=choose-a-strong-random-string
BRAIN_DB_PATH=/tmp/brain.sqlite3
LEARNING_MODE=off
LEARNING_DELTA_CAP=0.30
LEARNING_MIN_SUPPORT=3
LEARNING_RATE=0.03
EMBED_DB=/tmp/embed_cache.sqlite3      # only if you use the embeddings cache
```
**Run Uvicorn** (ASGI, uvloop, httptools): citeturn0search2turn0search14
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --loop uvloop --http httptools
```

---
## 8) Verification steps

- Open **`/admin/brain`** → set **mode** (OFF/SHADOW/ACTIVE), inspect **episodes**, view **params**, **publish/undo/reset**, and try **preview**.
- Click **LEARN** after you accept or revise a plan. In **SHADOW** mode this only records; **ACTIVE** requires **Publish** first.
- Confirm **no over‑narrowing**: the brain only adds tiny, bounded deltas and requires minimum support—industry‑agnostic by construction.
- (Optional) Run Playwright & Locust.

---
## 9) Why this design keeps your app **broad** and **governable**

- Learning is **separate** from core logic; it **never** hard‑codes to a single RFP.
- **Shadow → Preview → Publish** gives you human‑in‑the‑loop control and safe rollout.
  citeturn2search2turn2search14turn2search17
- Startup **lifespan** and **HTTP client reuse** are recommended patterns for robust services.
  citeturn0search0turn0search4
- Playwright `setInputFiles()` and Locust quickstart simplify test setup. citeturn1search0turn1search4
- Aligns with **People + AI Guidebook** and **NIST AI RMF** (governance & monitoring).
  citeturn2search0turn2search18turn2search7

---
**End of single file.**
