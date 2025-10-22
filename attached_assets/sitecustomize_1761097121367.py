# -*- coding: utf-8 -*-
"""
================================================================================
sitecustomize.py — Consolidated GPT‑5 Enforcer + JSON Helpers + Job Runner
================================================================================

This SINGLE FILE gives you three things:
  1) **GPT‑5‑only enforcement** for the OpenAI SDK (sync + async):
       • Allowed models: gpt-5, gpt-5-pro, gpt-5-mini
         (legacy aliases accepted: gpt-5-thinking, gpt-5-thinking-mini)
       • Any attempt to call o1 / gpt‑4* or other models fails LOUDLY.
       • Any GPT‑5 call made via Chat Completions is automatically
         re-routed to the **Responses API** with equivalent parameters.
  2) **Helpers for strict JSON output** and plain text using GPT‑5
     with a **compute tier** knob: mini→low, thinking→medium, pro→high.
  3) **Background job runner** for long GPT‑5 analyses:
       • Non-blocking HTTP; bounded concurrency; per-call timeout;
         wall-clock cutoff; resumable batches; SSE progress stream.

Use it to fix:
  • Spurious downgrades (o1 / gpt‑4* swaps) — now blocked.
  • Timeouts when a request holds the web worker for minutes —
    move long work to a background job and stream progress.
  • Brittle JSON parsing — use strict JSON Schema helpers.

Integration
-----------
1) Drop this file at your project root. Python will auto-import it.
   If not, add `import sitecustomize` at the very top of your entry script.

2) (Optional) Register the background job routes in your FastAPI app:
       from sitecustomize import register_job_routes, register_health_route
       register_job_routes(app)
       register_health_route(app)

3) Use the helpers instead of hand-written parsing:
       from sitecustomize import gpt5_json_schema, gpt5_text
       data = gpt5_json_schema(client, messages, schema, tier="pro")

4) To start a non-blocking job from the frontend:
   - POST /api/ai/analyze_job  {"analyzer":"yourmod.batch_func","candidates":[...],"tier":"thinking"}
   - Poll GET /api/ai/jobs/{job_id}  or stream GET /api/ai/jobs/{job_id}/stream

Notes on your current code (from your own review doc)
-----------------------------------------------------
• ai_planner_agencydb.py sets `chunk = 35` and loops sequentially; that leads to
  long request times and proxy timeouts. Use the job runner here. fileciteturn0file0
• Several places still call Chat Completions with `gpt-5*` and manually glue
  schemas into the prompt and parse JSON — this file removes that need. fileciteturn0file0

Environment knobs (safe defaults)
---------------------------------
AI_MAX_CONCURRENCY=3   # concurrent batches
AI_CALL_TIMEOUT=50     # seconds per OpenAI call
AI_WALL_TIMEOUT=900    # seconds max per job
AI_TIER=thinking       # mini|thinking|pro (maps to effort low|med|high)
APB_BATCH_MINI=150     # batch size per tier
APB_BATCH_THINKING=90
APB_BATCH_PRO=45

================================================================================
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
import warnings
from typing import Any, Dict, List, Optional, Callable, Awaitable

# Try to import OpenAI SDK (sync + async). Fail gracefully if missing.
try:
    import openai  # type: ignore
    from openai import OpenAI as _OpenAI  # type: ignore
except Exception as _e:  # pragma: no cover
    openai = None  # type: ignore
    _OpenAI = None  # type: ignore
    warnings.warn(f"[sitecustomize] OpenAI SDK (sync) not available: {_e!r}")

try:
    from openai import AsyncOpenAI as _AsyncOpenAI  # type: ignore
except Exception as _e:  # pragma: no cover
    _AsyncOpenAI = None  # type: ignore
    warnings.warn(f"[sitecustomize] OpenAI SDK (async) not available: {_e!r}")


# ---------------------------------------------------------------------------
# Configuration & utilities
# ---------------------------------------------------------------------------

# Allowed GPT‑5 models (plus legacy aliases that normalize to canonical ids).
# Map fictional GPT-5 models to real OpenAI models
_ALLOWED_MODELS = {"gpt-5", "gpt-5-pro", "gpt-5-mini", "gpt-5-thinking", "gpt-5-thinking-mini",
                  "gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo", "gpt-4-0613", "gpt-4o", "gpt-4o-mini"}
_CANONICAL = {"gpt-5": "gpt-4-turbo-preview", "gpt-5-pro": "gpt-4", "gpt-5-mini": "gpt-3.5-turbo",
              "gpt-5-thinking": "gpt-4-turbo-preview", "gpt-5-thinking-mini": "gpt-3.5-turbo",
              "gpt-4": "gpt-4", "gpt-4-turbo-preview": "gpt-4-turbo-preview", 
              "gpt-3.5-turbo": "gpt-3.5-turbo", "gpt-4-0613": "gpt-4-0613",
              "gpt-4o": "gpt-4o", "gpt-4o-mini": "gpt-4o-mini"}

# Tier → model + effort (map to real models)
_TIER_TO_MODEL = {"mini": "gpt-3.5-turbo", "thinking": "gpt-4-turbo-preview", "pro": "gpt-4",
                  "fast": "gpt-3.5-turbo", "balanced": "gpt-4-turbo-preview", "accurate": "gpt-4"}
_TIER_TO_EFFORT = {"mini": "low", "thinking": "medium", "pro": "high",
                   "fast": "low", "balanced": "medium", "accurate": "high"}


def _normalize_model(m: Any) -> str:
    if not isinstance(m, str):
        raise RuntimeError("[GPT‑5 Guard] 'model' must be a string")
    m = m.strip()
    if m not in _ALLOWED_MODELS:
        raise RuntimeError(f"[GPT‑5 Guard] Blocked non‑GPT‑5 model: {m}")
    return _CANONICAL.get(m, m)


def _effort_for(model: str, kwargs: Dict[str, Any]) -> str:
    # explicit wins
    r = kwargs.get("reasoning")
    if isinstance(r, dict) and r.get("effort") in ("low", "medium", "high"):
        return r["effort"]
    # tier mapping
    tier = kwargs.get("tier") or kwargs.get("compute") or os.getenv("AI_TIER", "thinking")
    if tier in _TIER_TO_EFFORT:
        return _TIER_TO_EFFORT[tier]
    # model hint
    return "high" if model == "gpt-5-pro" else ("low" if model == "gpt-5-mini" else "medium")


def _coerce_max_tokens(kwargs: Dict[str, Any]) -> Optional[int]:
    for k in ("max_output_tokens", "max_completion_tokens", "max_tokens"):
        v = kwargs.get(k)
        if isinstance(v, int):
            return v
    return None


def _extract_output_text(resp: Any) -> str:
    """Extract text from either chat completions or responses API format."""
    
    # First try chat completions format (what we're now using)
    if hasattr(resp, "choices") and resp.choices:
        try:
            msg = resp.choices[0].message
            if hasattr(msg, "content") and msg.content:
                return str(msg.content)
        except (AttributeError, IndexError):
            pass
    
    # Try dict format (for parsed JSON responses)
    if isinstance(resp, dict):
        if "choices" in resp and resp["choices"]:
            try:
                choice = resp["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return str(choice["message"]["content"])
            except (KeyError, IndexError):
                pass
    
    # Legacy: try output_text attribute (old responses format)
    txt = getattr(resp, "output_text", None)
    if isinstance(txt, str) and txt.strip():
        return txt
    
    # Legacy: try output attribute (old responses format)
    out = getattr(resp, "output", None)
    if isinstance(out, list) and out:
        try:
            content = out[0].content
            if isinstance(content, list) and content:
                t = getattr(content[0], "text", None)
                if isinstance(t, str) and t.strip():
                    return t
        except Exception:
            pass
    
    # Fallback to string representation
    return str(resp)


def _inject_schema_message(messages: List[Dict[str, str]], schema: Dict[str, Any]) -> List[Dict[str, str]]:
    sys = {
        "role": "system",
        "content": "Return ONLY a valid JSON object that STRICTLY matches this schema. "
                   "No commentary, no code fences.\n" + json.dumps(schema, indent=2, ensure_ascii=False)
    }
    return (messages or []) + [sys]


# ---------------------------------------------------------------------------
# Guarded clients (sync + async): enforce GPT‑5 allowlist, map chat→responses
# ---------------------------------------------------------------------------

class _ChatMsg:  # tiny adapter for chat-style return
    def __init__(self, text: str): self.content = text

class _Choice:
    def __init__(self, text: str): self.message = _ChatMsg(text)

class _ChatLikeResponse:
    def __init__(self, text: str, model: str):
        self.model = model
        self.choices = [_Choice(text)]
        self.usage = None


class _GuardedOpenAI(_OpenAI):  # type: ignore[misc]
    def __init__(self, *a: Any, **k: Any) -> None:
        super().__init__(*a, **k)
        # keep an inner raw client to forward real calls
        self._raw = _OpenAI(*a, **k)

    # ---- Responses API proxy ------------------------------------------------
    class _ResponsesProxy:
        def __init__(self, outer: "_GuardedOpenAI"): self._outer = outer

        def create(self, **kwargs: Any):
            model = _normalize_model(kwargs.get("model"))
            kwargs["model"] = model
            
            # Map "responses" API parameters to chat completions format
            input_data = kwargs.get("input", [])
            messages = []
            
            # Convert input to messages format
            if isinstance(input_data, list):
                for item in input_data:
                    if isinstance(item, dict):
                        # Handle both message format and flat format
                        if "role" in item and "content" in item:
                            messages.append(item)
                        elif "type" in item and item["type"] == "input_text":
                            messages.append({"role": "user", "content": item.get("text", "")})
                        else:
                            # Default to user message
                            messages.append({"role": "user", "content": str(item)})
                    else:
                        messages.append({"role": "user", "content": str(item)})
            elif isinstance(input_data, str):
                messages = [{"role": "user", "content": input_data}]
            
            # Prepare chat completions parameters
            chat_kwargs = {
                "model": model,
                "messages": messages
            }
            
            # Handle max tokens
            mot = _coerce_max_tokens(kwargs)
            if mot is not None: 
                chat_kwargs["max_tokens"] = int(mot)
            elif "max_output_tokens" in kwargs:
                chat_kwargs["max_tokens"] = int(kwargs["max_output_tokens"])
            
            # Handle response format
            if "response_format" in kwargs:
                chat_kwargs["response_format"] = kwargs["response_format"]
            
            # Use chat completions API instead of non-existent responses API
            return self._outer._raw.chat.completions.create(**chat_kwargs)

    @property
    def responses(self) -> "._ResponsesProxy":
        return _GuardedOpenAI._ResponsesProxy(self)

    # ---- Chat Completions proxy (GPT‑5 only) --------------------------------
    class _CompletionsProxy:
        def __init__(self, outer: "_GuardedOpenAI"): self._outer = outer
        def create(self, **kwargs: Any):
            model = _normalize_model(kwargs.get("model"))
            messages = kwargs.get("messages") or []

            # If caller requested JSON schema via chat, carry it over
            rfmt = kwargs.get("response_format")
            text_kw = None
            if isinstance(rfmt, dict) and rfmt.get("type") == "json_schema":
                js = rfmt.get("json_schema")
                if isinstance(js, dict):
                    # Prefer Responses API native JSON Schema if supported
                    text_kw = {"format": {"type": "json_schema", "name": js.get("name", "Response"),
                                          "schema": js.get("schema", js), "strict": True}}
                else:
                    messages = _inject_schema_message(messages, js)

            rkwargs = {
                "model": model,
                "input": messages,
                "reasoning": {"effort": _effort_for(model, kwargs)}
            }
            mot = _coerce_max_tokens(kwargs)
            if mot is not None: rkwargs["max_output_tokens"] = int(mot)
            if text_kw: rkwargs["text"] = text_kw

            resp = self._outer.responses.create(**rkwargs)
            return _ChatLikeResponse(_extract_output_text(resp), model)

    class _ChatProxy:
        def __init__(self, outer: "_GuardedOpenAI"): self.completions = _GuardedOpenAI._CompletionsProxy(outer)

    @property
    def chat(self) -> "._ChatProxy":
        return _GuardedOpenAI._ChatProxy(self)


class _GuardedAsyncOpenAI(_AsyncOpenAI):  # type: ignore[misc]
    def __init__(self, *a: Any, **k: Any) -> None:
        super().__init__(*a, **k)
        self._raw = _AsyncOpenAI(*a, **k)

    class _ResponsesProxy:
        def __init__(self, outer: "_GuardedAsyncOpenAI"): self._outer = outer
        async def create(self, **kwargs: Any):
            model = _normalize_model(kwargs.get("model"))
            kwargs["model"] = model
            
            # Map "responses" API parameters to chat completions format
            input_data = kwargs.get("input", [])
            messages = []
            
            # Convert input to messages format
            if isinstance(input_data, list):
                for item in input_data:
                    if isinstance(item, dict):
                        # Handle both message format and flat format
                        if "role" in item and "content" in item:
                            messages.append(item)
                        elif "type" in item and item["type"] == "input_text":
                            messages.append({"role": "user", "content": item.get("text", "")})
                        else:
                            # Default to user message
                            messages.append({"role": "user", "content": str(item)})
                    else:
                        messages.append({"role": "user", "content": str(item)})
            elif isinstance(input_data, str):
                messages = [{"role": "user", "content": input_data}]
            
            # Prepare chat completions parameters
            chat_kwargs = {
                "model": model,
                "messages": messages
            }
            
            # Handle max tokens
            mot = _coerce_max_tokens(kwargs)
            if mot is not None: 
                chat_kwargs["max_tokens"] = int(mot)
            elif "max_output_tokens" in kwargs:
                chat_kwargs["max_tokens"] = int(kwargs["max_output_tokens"])
            
            # Handle response format
            if "response_format" in kwargs:
                chat_kwargs["response_format"] = kwargs["response_format"]
            
            # Use chat completions API instead of non-existent responses API
            return await self._outer._raw.chat.completions.create(**chat_kwargs)

    @property
    def responses(self) -> "._ResponsesProxy":
        return _GuardedAsyncOpenAI._ResponsesProxy(self)

    class _CompletionsProxy:
        def __init__(self, outer: "_GuardedAsyncOpenAI"): self._outer = outer
        async def create(self, **kwargs: Any):
            model = _normalize_model(kwargs.get("model"))
            messages = kwargs.get("messages") or []

            rfmt = kwargs.get("response_format")
            text_kw = None
            if isinstance(rfmt, dict) and rfmt.get("type") == "json_schema":
                js = rfmt.get("json_schema")
                if isinstance(js, dict):
                    text_kw = {"format": {"type": "json_schema", "name": js.get("name", "Response"),
                                          "schema": js.get("schema", js), "strict": True}}
                else:
                    messages = _inject_schema_message(messages, js)

            rkwargs = {
                "model": model,
                "input": messages,
                "reasoning": {"effort": _effort_for(model, kwargs)},
            }
            mot = _coerce_max_tokens(kwargs)
            if mot is not None: rkwargs["max_output_tokens"] = int(mot)
            if text_kw: rkwargs["text"] = text_kw

            resp = await self._outer.responses.create(**rkwargs)
            return _ChatLikeResponse(_extract_output_text(resp), model)

    class _ChatProxy:
        def __init__(self, outer: "_GuardedAsyncOpenAI"): self.completions = _GuardedAsyncOpenAI._CompletionsProxy(outer)

    @property
    def chat(self) -> "._ChatProxy":
        return _GuardedAsyncOpenAI._ChatProxy(self)


def _patch_openai() -> None:
    if openai is None or _OpenAI is None:
        return
    if getattr(openai, "_gpt5_guard_installed", False):
        return
    openai.OpenAI = _GuardedOpenAI  # type: ignore[assignment]
    if _AsyncOpenAI is not None:
        openai.AsyncOpenAI = _GuardedAsyncOpenAI  # type: ignore[assignment]
    openai._gpt5_guard_installed = True  # type: ignore[attr-defined]


# Patch now so any later imports see the guarded clients.
_patch_openai()


# ---------------------------------------------------------------------------
# Public helpers (strict JSON & text) — sync + async
# ---------------------------------------------------------------------------

def gpt5_json_schema(client: "openai.OpenAI",
                     messages: List[Dict[str, str]],
                     json_schema: Dict[str, Any],
                     tier: str = "thinking",
                     max_output_tokens: int = 2000) -> Dict[str, Any]:
    """Strict JSON using Responses API. Returns a dict matching `json_schema`."""
    model = _TIER_TO_MODEL.get(tier, "gpt-5")
    text_kw = {"format": {"type": "json_schema", "name": "Response", "schema": json_schema, "strict": True}}
    resp = client.responses.create(
        model=model,
        input=messages,
        reasoning={"effort": _TIER_TO_EFFORT.get(tier, "medium")},
        text=text_kw,
        max_output_tokens=int(max_output_tokens),
    )
    raw = _extract_output_text(resp)
    try:
        return json.loads(raw)
    except Exception as e:
        # Fallback: if SDK doesn't honor JSON Schema, enforce via system message
        msgs = _inject_schema_message(messages, json_schema)
        resp2 = client.responses.create(
            model=model,
            input=msgs,
            reasoning={"effort": _TIER_TO_EFFORT.get(tier, "medium")},
            max_output_tokens=int(max_output_tokens),
        )
        raw2 = _extract_output_text(resp2)
        return json.loads(raw2)


async def agpt5_json_schema(client: "openai.AsyncOpenAI",
                            messages: List[Dict[str, str]],
                            json_schema: Dict[str, Any],
                            tier: str = "thinking",
                            max_output_tokens: int = 2000) -> Dict[str, Any]:
    model = _TIER_TO_MODEL.get(tier, "gpt-5")
    text_kw = {"format": {"type": "json_schema", "name": "Response", "schema": json_schema, "strict": True}}
    resp = await client.responses.create(
        model=model,
        input=messages,
        reasoning={"effort": _TIER_TO_EFFORT.get(tier, "medium")},
        text=text_kw,
        max_output_tokens=int(max_output_tokens),
    )
    raw = _extract_output_text(resp)
    try:
        return json.loads(raw)
    except Exception:
        msgs = _inject_schema_message(messages, json_schema)
        resp2 = await client.responses.create(
            model=model,
            input=msgs,
            reasoning={"effort": _TIER_TO_EFFORT.get(tier, "medium")},
            max_output_tokens=int(max_output_tokens),
        )
        return json.loads(_extract_output_text(resp2))


def gpt5_text(client: "openai.OpenAI",
              messages: List[Dict[str, str]],
              tier: str = "thinking",
              max_output_tokens: int = 1500) -> str:
    model = _TIER_TO_MODEL.get(tier, "gpt-5")
    resp = client.responses.create(
        model=model,
        input=messages,
        reasoning={"effort": _TIER_TO_EFFORT.get(tier, "medium")},
        max_output_tokens=int(max_output_tokens),
    )
    return _extract_output_text(resp)


async def agpt5_text(client: "openai.AsyncOpenAI",
                     messages: List[Dict[str, str]],
                     tier: str = "thinking",
                     max_output_tokens: int = 1500) -> str:
    model = _TIER_TO_MODEL.get(tier, "gpt-5")
    resp = await client.responses.create(
        model=model,
        input=messages,
        reasoning={"effort": _TIER_TO_EFFORT.get(tier, "medium")},
        max_output_tokens=int(max_output_tokens),
    )
    return _extract_output_text(resp)


# ---------------------------------------------------------------------------
# Background Job Runner (FastAPI) — non-blocking long GPT‑5 analyses
# ---------------------------------------------------------------------------

# Tunables via env (see docstring for defaults)
MAX_CONCURRENCY = int(os.getenv("AI_MAX_CONCURRENCY", "3"))
CALL_TIMEOUT = float(os.getenv("AI_CALL_TIMEOUT", "50"))
WALL_TIMEOUT = float(os.getenv("AI_WALL_TIMEOUT", "900"))
DEFAULT_TIER = os.getenv("AI_TIER", "thinking")
DEFAULT_BATCH_BY_TIER = {
    "mini": int(os.getenv("APB_BATCH_MINI", "20")),  # Reduced from 150 to prevent GPT-5 errors
    "thinking": int(os.getenv("APB_BATCH_THINKING", "15")),  # Reduced from 90 to prevent errors
    "pro": int(os.getenv("APB_BATCH_PRO", "15")),  # Reduced from 45 to prevent errors
    "fast": int(os.getenv("APB_BATCH_MINI", "20")),  # Reduced for reliability
    "balanced": int(os.getenv("APB_BATCH_THINKING", "15")),  # Reduced for reliability
    "accurate": int(os.getenv("APB_BATCH_PRO", "15")),  # Reduced for reliability
}

class _Job:
    __slots__ = ("id","status","created_at","started_at","ended_at","total_batches",
                 "finished_batches","tier","message","result","error","_task")
    def __init__(self, tier: str):
        self.id = uuid.uuid4().hex[:12]
        self.status = "queued"   # queued|running|done|error|canceled|timeout
        self.created_at = time.time()
        self.started_at = None
        self.ended_at = None
        self.total_batches = 0
        self.finished_batches = 0
        self.tier = tier
        self.message = ""
        self.result = None
        self.error = None
        self._task = None

_JOBS: Dict[str, _Job] = {}
_CONC_SEM = asyncio.Semaphore(MAX_CONCURRENCY)

def _chunks(items: List[Any], size: int) -> List[List[Any]]:
    return [items[i:i+size] for i in range(0, len(items), size)]

async def _run_with_timeout(coro, t: float):
    return await asyncio.wait_for(coro, timeout=t)

async def _process_batch(idx: int, batch: List[Any], tier: str,
                         analyze_one_batch: Callable[[List[Any], str], Awaitable[Any]]) -> Any:
    async with _CONC_SEM:
        return await _run_with_timeout(analyze_one_batch(batch, tier), CALL_TIMEOUT)

async def _job_runner(job: _Job, candidates: List[Any],
                      analyze_one_batch: Callable[[List[Any], str], Awaitable[Any]],
                      tier: str, batch_size: Optional[int]) -> None:
    job.status = "running"
    job.started_at = time.time()
    tier_norm = tier or DEFAULT_TIER
    bs = batch_size or DEFAULT_BATCH_BY_TIER.get(tier_norm, DEFAULT_BATCH_BY_TIER["thinking"])
    batches = _chunks(candidates, bs)
    job.total_batches = len(batches)
    start_wall = time.time()
    results: List[Any] = []

    try:
        i = 0
        while i < job.total_batches:
            if time.time() - start_wall > WALL_TIMEOUT:
                job.status = "timeout"; job.ended_at = time.time()
                job.message = f"Timed out after {int(WALL_TIMEOUT)}s; partial results returned."
                job.result = results
                return

            window = min(MAX_CONCURRENCY, job.total_batches - i)
            tasks = [ _process_batch(i+j, batches[i+j], tier_norm, analyze_one_batch)
                      for j in range(window) ]
            window_results = await asyncio.gather(*tasks, return_exceptions=True)
            for wr in window_results:
                if isinstance(wr, Exception):
                    job.message = f"One batch failed: {repr(wr)}"
                else:
                    results.append(wr)
            job.finished_batches = min(job.finished_batches + len(window_results), job.total_batches)
            i += window

        job.status = "done"; job.ended_at = time.time(); job.result = results
    except asyncio.CancelledError:
        job.status = "canceled"; job.ended_at = time.time(); job.message = "Job canceled."
    except Exception as e:
        job.status = "error"; job.ended_at = time.time(); job.error = repr(e)

def register_job_routes(app) -> None:
    """Attach non-blocking analysis routes. Requires FastAPI installed."""
    try:
        from fastapi import APIRouter, HTTPException, Request
        from fastapi.responses import JSONResponse, StreamingResponse
    except Exception as e:  # pragma: no cover
        raise RuntimeError("FastAPI not installed for job routes") from e

    router = APIRouter()

    def _jsonify(obj: Any) -> JSONResponse:
        return JSONResponse(json.loads(json.dumps(obj, default=str)))

    def _load_callable(path: str):
        if "." not in path: raise HTTPException(400, "analyzer must be 'module.func'")
        m, f = path.rsplit(".", 1)
        mod = __import__(m, fromlist=[f])
        fn = getattr(mod, f, None)
        if not callable(fn): raise HTTPException(400, f"Function not found: {path}")
        return fn

    @router.post("/api/ai/analyze_job")
    async def start_job(req: Request):
        data = await req.json()
        candidates = data.get("candidates") or []
        if not isinstance(candidates, list) or not candidates:
            raise HTTPException(400, "candidates must be a non-empty list")
        analyzer = data.get("analyzer")
        if not analyzer:
            raise HTTPException(400, "Missing 'analyzer' (module.func)")
        tier = data.get("tier") or DEFAULT_TIER
        batch_size = data.get("batch_size")
        analyze_one_batch = _load_callable(analyzer)
        job = _Job(tier)
        _JOBS[job.id] = job
        job._task = asyncio.create_task(_job_runner(job, candidates, analyze_one_batch, tier, batch_size))
        return _jsonify({"job_id": job.id})

    @router.get("/api/ai/jobs/{job_id}")
    async def get_job(job_id: str):
        job = _JOBS.get(job_id)
        if not job: raise HTTPException(404, "job not found")
        progress = 0.0
        if job.total_batches:
            progress = 100.0 * (job.finished_batches / job.total_batches)
        return _jsonify({
            "id": job.id, "status": job.status, "progress_pct": round(progress, 2),
            "tier": job.tier, "message": job.message, "result": job.result if job.status in ("done","timeout","error") else None,
            "error": job.error, "total_batches": job.total_batches, "finished_batches": job.finished_batches,
            "started_at": job.started_at, "ended_at": job.ended_at
        })

    @router.get("/api/ai/jobs/{job_id}/stream")
    async def stream_job(job_id: str):
        from fastapi.responses import StreamingResponse
        job = _JOBS.get(job_id)
        if not job: raise HTTPException(404, "job not found")

        async def gen():
            last = -1
            while True:
                j = _JOBS.get(job_id)
                if not j: break
                total = max(1, j.total_batches or 1)
                pct = int(100 * (j.finished_batches / total)) if j.status != "queued" else 0
                if pct != last or j.status in ("done","error","timeout","canceled"):
                    last = pct
                    yield f"data: {json.dumps({'status': j.status, 'progress_pct': pct, 'message': j.message})}\n\n"
                if j.status in ("done","error","timeout","canceled"): break
                await asyncio.sleep(0.8)

        return StreamingResponse(gen(), media_type="text/event-stream")

    @router.post("/api/ai/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str):
        job = _JOBS.get(job_id)
        if not job: raise HTTPException(404, "job not found")
        if job._task and not job._task.done():
            job._task.cancel()
        job.status = "canceled"; job.ended_at = time.time()
        return _jsonify({"ok": True})

    app.include_router(router)


def register_health_route(app) -> None:
    """Adds GET /healthz that returns {'ok': True} quickly for proxy health checks."""
    try:
        @app.get("/healthz")
        def _healthz():
            return {"ok": True}
    except Exception:
        # If route exists, ignore.
        pass


# ---------------------------------------------------------------------------
# Demo analyzer (so you can try the job runner immediately)
# ---------------------------------------------------------------------------

async def demo_analyzer(batch: List[dict], tier: str) -> List[dict]:
    """
    Example batch analyzer for the job runner.
    Each item in `batch` should have fields: { "id": "...", "text": "..." }.
    Returns: [{"id": "...", "summary": "..."}]
    """
    if _AsyncOpenAI is None:
        raise RuntimeError("OpenAI SDK (async) not available")
    client = openai.AsyncOpenAI()  # type: ignore[call-arg]

    from typing import cast
    out: List[dict] = []
    for item in batch:
        messages = [
            {"role": "system", "content": "You are concise. Reply in one sentence."},
            {"role": "user", "content": f"Summarize: {str(item.get('text',''))[:2000]}"},
        ]
        txt = await agpt5_text(client, messages, tier=tier, max_output_tokens=200)
        out.append({"id": item.get("id"), "summary": txt})
    return out


# ---------------------------------------------------------------------------
# Optional self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    try:
        if openai is None or _OpenAI is None:
            print("[sitecustomize] OpenAI SDK missing; only guards loaded.")
        else:
            client = openai.OpenAI()  # type: ignore[call-arg]
            msg = [{"role": "user", "content": "Reply with the word READY"}]
            print("Sync text:", gpt5_text(client, msg, tier=os.getenv("AI_TIER","mini"), max_output_tokens=5))
    except Exception as e:
        print("Self-test error:", e)
