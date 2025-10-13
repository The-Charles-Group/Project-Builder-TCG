# -*- coding: utf-8 -*-
"""
===============================================================================
sitecustomize.py  —  GPT‑5‑ONLY ENFORCER & WRAPPER (single-file drop‑in)
===============================================================================
WHAT THIS DOES (no other changes required):
  • Auto‑loads on Python startup (standard CPython behavior): patches OpenAI SDK
  • Enforces **ONLY GPT‑5** models:
        allowed: gpt-5, gpt-5-pro, gpt-5-mini, gpt-5-thinking, gpt-5-thinking-mini
  • Blocks downgrades (o1/o3/gpt‑4*). If code or an agent tries to swap models,
    execution fails **loudly** with a clear error—no silent “fallbacks”.
  • Converts any GPT‑5 **Chat Completions** calls to **Responses API** on the fly,
    so existing code keeps working while we move to Responses API.
  • Adds a simple **compute tier** knob (mini → low, thinking → medium, pro → high).
  • Provides helper functions for **JSON‑only** calls using Responses API.

HOW TO USE
  • Just drop this file at the project root. Python imports `sitecustomize` on
    startup automatically. If your runtime disables it, add this once:
        import sitecustomize  # noqa: F401
  • Keep this file read‑only; do not let agents edit it.

AGENT / ASSISTANT RULES (must follow)
  1) Do NOT change model ids in code, config, tests, or CI.
  2) Allowed models are: gpt-5, gpt-5-pro, gpt-5-mini, gpt-5-thinking, gpt-5-thinking-mini.
  3) If a call fails, STOP and report. Do not downgrade to o1/o3/gpt‑4.x.
  4) Prefer Responses API. Chat Completions with GPT‑5 will be re‑routed here.
  5) For JSON output, use the helpers in this file or provide a strict JSON schema.

This file deliberately avoids any external dependencies beyond `openai` and stdlib.
===============================================================================
"""

from __future__ import annotations

import json
import os
import re
import types
import warnings
from typing import Any, Dict, List, Optional

try:
    # If the OpenAI SDK is not installed, we keep graceful behavior.
    import openai  # type: ignore
    from openai import OpenAI as _OpenAI  # type: ignore
except Exception as _e:  # pragma: no cover
    openai = None
    _OpenAI = None
    warnings.warn(f"[sitecustomize] OpenAI SDK not available: {_e!r}")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Canonical GPT‑5 ids we allow.
_ALLOWED_MODELS = {
    "gpt-5",
    "gpt-5-pro",
    "gpt-5-mini",
    # Synonyms your code currently uses (kept for compatibility).
    "gpt-5-thinking",
    "gpt-5-thinking-mini",
}

# Map user “tier” to a model id (you can edit these to taste).
_TIER_TO_MODEL = {
    "mini": "gpt-5-mini",
    "thinking": "gpt-5",
    "pro": "gpt-5-pro",
    # Optional UI spellings
    "fast": "gpt-5-mini",
    "balanced": "gpt-5",
    "accurate": "gpt-5-pro",
}

# Map tier to reasoning effort knob (compute depth).
_TIER_TO_EFFORT = {
    "mini": "low",
    "thinking": "medium",
    "pro": "high",
    "fast": "low",
    "balanced": "medium",
    "accurate": "high",
}

# Synonyms → canonical mapping (keeps your legacy ids working)
def _normalize_model_id(model: str) -> str:
    if not isinstance(model, str):
        return model
    m = model.strip()
    # Align legacy “thinking” names to canonical ids if desired.
    if m == "gpt-5-thinking":
        return "gpt-5"
    if m == "gpt-5-thinking-mini":
        return "gpt-5-mini"
    return m


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    """Formats messages into a readable single prompt (for strict JSON prompting)."""
    parts = []
    for msg in messages or []:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"System: {content}")
        elif role == "user":
            parts.append(f"User: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
        else:
            parts.append(content)
    return "\n\n".join(parts)


def _extract_output_text(resp: Any) -> str:
    """Best-effort extraction of text from a Responses API object."""
    # OpenAI Python SDK typically exposes `output_text`.
    txt = getattr(resp, "output_text", None)
    if isinstance(txt, str) and txt.strip():
        return txt
    # Fallbacks for object-like responses
    out = getattr(resp, "output", None)
    if isinstance(out, list) and out:
        # Common nested shapes: output[0].content[0].text
        try:
            content = out[0].content  # type: ignore[attr-defined]
            if isinstance(content, list) and content:
                text_obj = content[0]
                t = getattr(text_obj, "text", None)
                if isinstance(t, str) and t.strip():
                    return t
        except Exception:
            pass
    # Last resort: str()
    return str(resp)


def _coerce_max_output_tokens(kwargs: Dict[str, Any]) -> Optional[int]:
    """Map completion-style token params to Responses API."""
    if "max_output_tokens" in kwargs and isinstance(kwargs["max_output_tokens"], int):
        return kwargs["max_output_tokens"]
    if "max_completion_tokens" in kwargs and isinstance(kwargs["max_completion_tokens"], int):
        return kwargs["max_completion_tokens"]
    if "max_tokens" in kwargs and isinstance(kwargs["max_tokens"], int):
        return kwargs["max_tokens"]
    return None


def _effort_from_context(model: str, kwargs: Dict[str, Any]) -> Optional[str]:
    """Decide reasoning effort based on explicit kwargs, env, or model/tier hints."""
    # 1) Explicit 'reasoning' kwarg wins
    r = kwargs.get("reasoning")
    if isinstance(r, dict):
        effort = r.get("effort")
        if effort in ("low", "medium", "high"):
            return effort

    # 2) Explicit tier kwarg
    tier = kwargs.get("tier") or kwargs.get("compute") or os.getenv("AI_TIER") or os.getenv("MODEL_TIER")
    if isinstance(tier, str):
        effort = _TIER_TO_EFFORT.get(tier)
        if effort:
            return effort

    # 3) Model name hint
    m = _normalize_model_id(model)
    if m == "gpt-5-mini":
        return "low"
    if m == "gpt-5-pro":
        return "high"
    # default
    return "medium"


def _inject_json_schema_instruction(messages: List[Dict[str, str]], json_schema: Dict[str, Any]) -> List[Dict[str, str]]:
    """Append a system message asking for strict JSON per schema (for chat→responses mapping)."""
    sys_msg = {
        "role": "system",
        "content": (
            "Return ONLY a valid JSON object that STRICTLY matches this schema. "
            "Do not include any extra commentary or code fences.\n"
            + json.dumps(json_schema, indent=2, ensure_ascii=False)
        ),
    }
    return (messages or []) + [sys_msg]


# ---------------------------------------------------------------------------
# Minimal adapter so chat-completions-shaped callers keep working
# ---------------------------------------------------------------------------

class _MsgObj:
    def __init__(self, content: str): self.content = content

class _ChoiceObj:
    def __init__(self, message: _MsgObj): self.message = message

class _ChatCompletionAdapter:
    """Looks like a subset of Chat Completions response (choices[0].message.content)."""
    def __init__(self, text: str, model: str):
        self.id = None
        self.model = model
        self.choices = [_ChoiceObj(_MsgObj(text))]
        self.usage = None


# ---------------------------------------------------------------------------
# Guarded OpenAI client
# ---------------------------------------------------------------------------

class _ResponsesProxy:
    """Wraps client.responses to enforce GPT‑5 allowlist and map basic knobs."""
    def __init__(self, client: "_GuardedOpenAI") -> None:
        self._client = client
        # Underlying bound method
        self._create = client._inner.responses.create  # type: ignore[attr-defined]

    def create(self, **kwargs: Any):
        model = kwargs.get("model")
        if not isinstance(model, str):
            raise RuntimeError("[GPT‑5 Guard] Missing 'model' in responses.create()")
        model = _normalize_model_id(model)
        if model not in _ALLOWED_MODELS:
            raise RuntimeError(f"[GPT‑5 Guard] Blocked non‑GPT‑5 model: {model}")

        # Map token knobs
        mot = _coerce_max_output_tokens(kwargs)
        if mot is not None:
            kwargs["max_output_tokens"] = int(mot)

        # Reasoning effort
        effort = _effort_from_context(model, kwargs)
        kwargs.setdefault("reasoning", {"effort": effort})

        # Ensure canonical model id
        kwargs["model"] = model
        return self._create(**kwargs)


class _CompletionsProxy:
    """
    Intercepts chat.completions.create(...).
    If model is GPT‑5*, we reroute to Responses API and return a small adapter
    compatible with response.choices[0].message.content.
    For non‑GPT‑5 models (which are disallowed), we fail loud.
    """
    def __init__(self, outer: "_GuardedOpenAI") -> None:
        self._outer = outer

    def create(self, **kwargs: Any):
        model = kwargs.get("model")
        if not isinstance(model, str):
            raise RuntimeError("[GPT‑5 Guard] Missing 'model' in chat.completions.create()")
        model = _normalize_model_id(model)

        # Disallow any non‑GPT‑5 outright (prevents downgrades).
        if model not in _ALLOWED_MODELS:
            raise RuntimeError(f"[GPT‑5 Guard] Blocked non‑GPT‑5 model in chat.completions: {model}")

        # Convert chat → responses
        messages = kwargs.get("messages") or []
        # Handle response_format=json_schema
        rf = kwargs.get("response_format")
        if isinstance(rf, dict) and rf.get("type") == "json_schema":
            js = rf.get("json_schema")
            if isinstance(js, dict):
                messages = _inject_json_schema_instruction(messages, js)

        # Build Responses API kwargs
        rkwargs: Dict[str, Any] = {
            "model": model,
            "input": messages,  # Responses API accepts message list
        }

        mot = _coerce_max_output_tokens(kwargs)
        if mot is not None:
            rkwargs["max_output_tokens"] = int(mot)

        # Carry reasoning effort via tier/compute/env or model
        rkwargs["reasoning"] = {"effort": _effort_from_context(model, kwargs)}

        # Call through and adapt result
        resp = self._outer.responses.create(**rkwargs)  # goes through our proxy
        text = _extract_output_text(resp)
        return _ChatCompletionAdapter(text=text, model=model)


class _ChatProxy:
    """chat proxy exposing `completions.create`, but guarded."""
    def __init__(self, outer: "_GuardedOpenAI") -> None:
        self.completions = _CompletionsProxy(outer)


class _GuardedOpenAI(_OpenAI):  # type: ignore[misc]
    """
    Drop‑in replacement for openai.OpenAI that:
      • guards model ids
      • exposes responses.create via a proxy
      • intercepts chat.completions.create for GPT‑5 and routes to Responses
    """
    def __init__(self, *a: Any, **k: Any) -> None:
        super().__init__(*a, **k)
        self._inner = super()

    @property
    def responses(self) -> _ResponsesProxy:
        return _ResponsesProxy(self)

    @property
    def chat(self) -> _ChatProxy:
        return _ChatProxy(self)


def patch_openai() -> None:
    """Replace openai.OpenAI with our guarded client, if possible."""
    if openai is None or _OpenAI is None:
        return
    if getattr(openai, "_gpt5_guard_patched", False):
        return
    openai.OpenAI = _GuardedOpenAI  # type: ignore[assignment]
    openai._gpt5_guard_patched = True  # type: ignore[attr-defined]


# Apply the patch at import time so users don't need to call anything.
patch_openai()


# ---------------------------------------------------------------------------
# Public helper functions (optional to use from your app)
# ---------------------------------------------------------------------------

def gpt5_json_schema(
    client: "openai.OpenAI",
    messages: List[Dict[str, str]],
    json_schema: Dict[str, Any],
    tier: str = "thinking",
    max_output_tokens: int = 2200,
) -> Dict[str, Any]:
    """
    Strict JSON helper for GPT‑5 using the Responses API. Returns a Python dict.
    • `tier` in {"mini","thinking","pro"} selects compute depth & model.
    """
    # Resolve model from tier (supports UI values like fast/balanced/accurate).
    model = _TIER_TO_MODEL.get(tier, "gpt-5")
    if model not in _ALLOWED_MODELS:
        raise RuntimeError(f"[GPT‑5 Guard] Invalid tier→model: {tier} → {model}")

    # Inject strict JSON schema instruction as a system message.
    messages2 = _inject_json_schema_instruction(messages, json_schema)

    resp = client.responses.create(
        model=model,
        input=messages2,
        reasoning={"effort": _TIER_TO_EFFORT.get(tier, "medium")},
        # We rely on prompt-based strictness for maximum SDK compatibility.
        max_output_tokens=int(max_output_tokens),
    )
    txt = _extract_output_text(resp)
    try:
        return json.loads(txt)
    except Exception as e:
        raise RuntimeError(f"[GPT‑5 JSON] Expected strict JSON, but failed to parse: {e}\nText: {txt[:400]}")


def gpt5_text(
    client: "openai.OpenAI",
    messages: List[Dict[str, str]],
    tier: str = "thinking",
    max_output_tokens: int = 1500,
) -> str:
    """
    Simple text helper for GPT‑5 (Responses API). Returns plain text.
    """
    model = _TIER_TO_MODEL.get(tier, "gpt-5")
    resp = client.responses.create(
        model=model,
        input=messages,
        reasoning={"effort": _TIER_TO_EFFORT.get(tier, "medium")},
        max_output_tokens=int(max_output_tokens),
    )
    return _extract_output_text(resp)


# Optional: tiny self-test if run directly
if __name__ == "__main__":  # pragma: no cover
    if openai is None:
        print("[sitecustomize] OpenAI SDK not installed; nothing to test.")
    else:
        try:
            client = openai.OpenAI()
            ok = gpt5_text(
                client,
                messages=[
                    {"role": "system", "content": "You are concise."},
                    {"role": "user", "content": "Reply with the single word: READY"},
                ],
                tier=os.getenv("AI_TIER", "mini")
            )
            print(f"[sitecustomize] Self-test output: {ok!r}")
        except Exception as e:
            print(f"[sitecustomize] Self-test error: {e}")
