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
from typing import Any, Dict, List, Optional, Callable
import time

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
    # GPT-5.1 models for Smart Schedule Optimization
    "gpt-5.1-pro",
    "gpt-5.1-thinking",
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

# Retry configuration
MAX_RETRIES = int(os.environ.get("GPT5_MAX_RETRIES", "3"))  # Number of retries
BASE_DELAY = float(os.environ.get("GPT5_BASE_DELAY", "1.0"))  # Base delay in seconds
MAX_DELAY = float(os.environ.get("GPT5_MAX_DELAY", "4.0"))  # Max delay in seconds

# ---------------------------------------------------------------------------
# Retry Logic with Exponential Backoff
# ---------------------------------------------------------------------------

def retry_with_exponential_backoff(
    func: Callable,
    max_retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    max_delay: float = MAX_DELAY,
    log_prefix: str = "GPT-5",
    raise_on_failure: bool = True
) -> Any:
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to retry (should be callable with no arguments)
        max_retries: Maximum number of retries (default 3)
        base_delay: Initial delay in seconds (default 1.0)
        max_delay: Maximum delay in seconds (default 4.0)
        log_prefix: Prefix for log messages
        raise_on_failure: Whether to raise the last exception or return None

    Returns:
        The function result if successful, None if all retries failed and raise_on_failure=False

    Raises:
        The last exception encountered if raise_on_failure=True
    """
    last_exception = None
    delay = base_delay

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            if attempt > 0:
                print(f"[{log_prefix} Retry] Attempt {attempt}/{max_retries} after {delay:.1f}s delay...")
                time.sleep(delay)

            result = func()

            if attempt > 0:
                print(f"[{log_prefix} Success] Recovered after {attempt} retry(ies)")

            return result

        except Exception as e:
            last_exception = e
            error_msg = str(e)

            # Check for specific error types
            if "rate_limit" in error_msg.lower() or "429" in str(e):
                print(f"[{log_prefix} Rate Limit] Hit rate limit on attempt {attempt + 1}/{max_retries + 1}")
                # Use longer delay for rate limits
                delay = min(delay * 2, max_delay * 2)
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                print(f"[{log_prefix} Timeout] Request timed out on attempt {attempt + 1}/{max_retries + 1}")
                delay = min(delay * 1.5, max_delay)
            else:
                print(f"[{log_prefix} Error] Attempt {attempt + 1}/{max_retries + 1} failed: {error_msg[:200]}")
                delay = min(delay * 2, max_delay)

            if attempt == max_retries:
                print(f"[{log_prefix} FAILED] All {max_retries + 1} attempts exhausted. Last error: {error_msg[:500]}")
                if raise_on_failure:
                    raise last_exception
                return None

    # Should never reach here, but just in case
    if raise_on_failure and last_exception:
        raise last_exception
    return None

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

    # If response is a dict, handle it directly
    if isinstance(resp, dict):
        # PRIORITY 1: Check output field first - this is where the actual response is
        # (The 'text' field appears to contain request format parameters, not the response)
        if "output" in resp and isinstance(resp["output"], list) and resp["output"]:
            # Look for the actual text output (not the reasoning block)
            for item in resp["output"]:
                if isinstance(item, dict):
                    # Skip reasoning blocks, look for message/text blocks
                    if item.get("type") == "reasoning":
                        continue

                    # Check for message blocks (GPT-5 response format)
                    if "content" in item and item["content"]:
                        content = item["content"]

                        # If content is a list, extract text from it
                        if isinstance(content, list) and content:
                            for content_item in content:
                                if isinstance(content_item, dict):
                                    # Look for text field in content item
                                    if "text" in content_item:
                                        text = content_item["text"]
                                        if text and str(text).strip():
                                            return str(text)
                                    # Look for value field (alternative format)
                                    if "value" in content_item:
                                        value = content_item["value"]
                                        if value and str(value).strip():
                                            return str(value)
                                elif isinstance(content_item, str):
                                    if content_item.strip():
                                        return content_item
                        # If content is a string, return it directly
                        elif isinstance(content, str):
                            return content

                    # Check for text type items
                    if item.get("type") == "text" and item.get("content"):
                        return str(item["content"])

        # Check for nested choices structure (Chat Completions format)
        if "choices" in resp and isinstance(resp["choices"], list) and resp["choices"]:
            choice = resp["choices"][0]
            if isinstance(choice, dict) and "message" in choice:
                msg = choice["message"]
                if isinstance(msg, dict) and "content" in msg:
                    return str(msg["content"])

        # Check for incomplete response
        if "incomplete_details" in resp:
            # Still try to return any partial text we might have
            if "text" in resp and resp["text"]:
                return str(resp["text"])

        # If we can't find meaningful content, return empty string to trigger retry
        return ""

    # Check if response has model_dump method (Pydantic v2)
    if hasattr(resp, "model_dump"):
        try:
            resp_dict = resp.model_dump()
            return _extract_output_text(resp_dict)  # Recursive call with dict
        except Exception as e:
            pass  # Fall through to other extraction methods

    # Check if response has to_dict method
    if hasattr(resp, "to_dict"):
        print("[DEBUG GPT-5] Response has to_dict method")
        try:
            resp_dict = resp.to_dict()
            print(f"[DEBUG GPT-5] to_dict result: {json.dumps(resp_dict, default=str)[:500]}")
            return _extract_output_text(resp_dict)  # Recursive call with dict
        except Exception as e:
            print(f"[DEBUG GPT-5] to_dict failed: {e}")

    # First check for direct output_text attribute (new SDK versions)
    txt = getattr(resp, "output_text", None)
    if isinstance(txt, str) and txt.strip():
        print(f"[DEBUG GPT-5] Found output_text attribute: {txt[:200]}")
        return txt
    else:
        print(f"[DEBUG GPT-5] output_text attribute: {txt}")

    # Check for text attribute directly
    txt = getattr(resp, "text", None)
    if isinstance(txt, str) and txt.strip():
        print(f"[DEBUG GPT-5] Found text attribute: {txt[:200]}")
        return txt
    else:
        print(f"[DEBUG GPT-5] text attribute: {txt}")

    # Check for content attribute (GPT-5 Responses API format)
    content = getattr(resp, "content", None)
    if isinstance(content, str) and content.strip():
        print(f"[DEBUG GPT-5] Found content attribute: {content[:200]}")
        return content
    else:
        print(f"[DEBUG GPT-5] content attribute: {content}")

    # Check for output attribute (GPT-5 Responses API format)
    output = getattr(resp, "output", None)
    print(f"[DEBUG GPT-5] output attribute type: {type(output)}, value: {output}")

    # If output is a string, return it
    if isinstance(output, str) and output.strip():
        print(f"[DEBUG GPT-5] Returning output as string: {output[:200]}")
        return output

    # If output is a list, iterate through it
    if isinstance(output, list) and output:
        print(f"[DEBUG GPT-5] Output is list with {len(output)} items")
        for i, item in enumerate(output):
            print(f"[DEBUG GPT-5] Item {i} type: {type(item)}")
            # Check if item has direct content
            if hasattr(item, "content"):
                content = getattr(item, "content", None)
                if isinstance(content, str) and content.strip():
                    print(f"[DEBUG GPT-5] Found content in output[{i}]: {content[:200]}")
                    return content
                # Check for nested content list structure
                if isinstance(content, list):
                    for j, content_item in enumerate(content):
                        # Try to get text from content item
                        if hasattr(content_item, "text"):
                            t = getattr(content_item, "text", None)
                            if isinstance(t, str) and t.strip():
                                print(f"[DEBUG GPT-5] Found text in output[{i}].content[{j}]: {t[:200]}")
                                return t

    # If we still don't have text, check for incomplete status and return empty
    status = getattr(resp, "status", None)
    if status == "incomplete":
        print(f"[DEBUG GPT-5] Response has incomplete status")
        return ""

    # Last resort: return the string representation (but this is likely an error)
    print(f"[DEBUG GPT-5] Last resort - returning str(resp): {str(resp)[:500]}")
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

        # Log optimizer invocations for GPT-5.1 models
        if model in ("gpt-5.1-pro", "gpt-5.1-thinking"):
            input_data = kwargs.get("input", [])
            input_size = len(str(input_data))
            print(f"[OPTIMIZER] ✨ Smart Schedule Optimization using {model}")
            print(f"[OPTIMIZER] 📊 Request payload size: {input_size:,} bytes")
            print(f"[OPTIMIZER] ✅ Routing through Responses API (not Chat Completions)")

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

# Helper function to get the OpenAI client, supporting multiple API key names.
_CLIENT: Optional[OpenAI] = None
def _get_openai_client() -> Optional[OpenAI]:
    """Get or create OpenAI client with proper API key handling."""
    global _CLIENT
    if _CLIENT is None:
        # Support both OPENAI_API_KEY and Open_AI_Key secret names
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("Open_AI_Key")
        if not api_key:
            return None
        _CLIENT = OpenAI(api_key=api_key)
    return _CLIENT


# ---------------------------------------------------------------------------
# Public helper functions (optional to use from your app)
# ---------------------------------------------------------------------------

def gpt5_json_schema(
    client: "openai.OpenAI",
    messages: List[Dict[str, str]],
    json_schema: Dict[str, Any],
    tier: str = "thinking",
    max_output_tokens: int = 2200,
    use_retry: bool = True,
) -> Dict[str, Any]:
    """
    Strict JSON helper for GPT‑5 using the Responses API with retry logic. Returns a Python dict.
    • `tier` in {"mini","thinking","pro"} selects compute depth & model.
    • `use_retry` enables exponential backoff retry logic (default True)
    """
    # Resolve model from tier (supports UI values like fast/balanced/accurate).
    model = _TIER_TO_MODEL.get(tier, "gpt-5")
    if model not in _ALLOWED_MODELS:
        raise RuntimeError(f"[GPT‑5 Guard] Invalid tier→model: {tier} → {model}")

    # Inject strict JSON schema instruction as a system message.
    messages2 = _inject_json_schema_instruction(messages, json_schema)

    def make_request():
        resp = client.responses.create(
            model=model,
            input=messages2,
            reasoning={"effort": _TIER_TO_EFFORT.get(tier, "medium")},
            # We rely on prompt-based strictness for maximum SDK compatibility.
            max_output_tokens=int(max_output_tokens),
        )
        txt = _extract_output_text(resp)

        # Try to parse the JSON
        try:
            parsed_result = json.loads(txt)
        except json.JSONDecodeError as e:
            # Log detailed parsing error for debugging
            print(f"[GPT-5 JSON Parse Error] Failed to parse response as JSON: {e}")
            print(f"[GPT-5 JSON Parse Error] Response text (first 400 chars): {txt[:400]}")
            raise RuntimeError(f"[GPT‑5 JSON] Expected strict JSON, but failed to parse: {e}\nText: {txt[:400]}")

        # Validate result has content (not empty)
        if not parsed_result:
            raise RuntimeError(f"[GPT-5 JSON] Received empty JSON response")

        return parsed_result

    # Use retry logic if enabled
    if use_retry:
        return retry_with_exponential_backoff(
            make_request,
            log_prefix=f"GPT-5 JSON ({tier})",
            raise_on_failure=True
        )
    else:
        return make_request()


def gpt5_text(
    client: "openai.OpenAI",
    messages: List[Dict[str, str]],
    tier: str = "thinking",
    max_output_tokens: int = 1500,
    use_retry: bool = True,
) -> str:
    """
    Simple text helper for GPT‑5 (Responses API) with retry logic. Returns plain text.
    • `tier` in {"mini","thinking","pro"} selects compute depth & model.
    • `use_retry` enables exponential backoff retry logic (default True)
    """
    model = _TIER_TO_MODEL.get(tier, "gpt-5")

    def make_request():
        resp = client.responses.create(
            model=model,
            input=messages,
            reasoning={"effort": _TIER_TO_EFFORT.get(tier, "medium")},
            max_output_tokens=int(max_output_tokens),
        )
        text_result = _extract_output_text(resp)

        # Validate result has content
        if not text_result or not text_result.strip():
            raise RuntimeError(f"[GPT-5 Text] Received empty text response")

        return text_result

    # Use retry logic if enabled
    if use_retry:
        return retry_with_exponential_backoff(
            make_request,
            log_prefix=f"GPT-5 Text ({tier})",
            raise_on_failure=True
        )
    else:
        return make_request()


# Optional: tiny self-test if run directly
if __name__ == "__main__":  # pragma: no cover
    if openai is None:
        print("[sitecustomize] OpenAI SDK not installed; nothing to test.")
    else:
        try:
            # Use the helper function to get the client
            client = _get_openai_client()
            if client:
                ok = gpt5_text(
                    client,
                    messages=[
                        {"role": "system", "content": "You are concise."},
                        {"role": "user", "content": "Reply with the single word: READY"},
                    ],
                    tier=os.getenv("AI_TIER", "mini")
                )
                print(f"[sitecustomize] Self-test output: {ok!r}")
            else:
                print("[sitecustomize] OpenAI client could not be initialized (API key missing?).")
        except Exception as e:
            print(f"[sitecustomize] Self-test error: {e}")