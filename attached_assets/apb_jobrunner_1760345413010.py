

# ---------------- Demo analyzer (optional) -----------------

from __future__ import annotations
import asyncio, os, json
from typing import Any, List
try:
    from openai import AsyncOpenAI
    from sitecustomize import gpt5_text  # optional helper if present
except Exception:
    AsyncOpenAI = None

async def demo_analyzer(batch: List[dict], tier: str) -> list[dict]:
    """
    Minimal example analyzer you can call with analyzer="apb_jobrunner.demo_analyzer".
    Each item in `batch` must be a dict with a 'text' field.
    Returns a list of results: [{"id": item.get("id"), "summary": "..."}]
    """
    if AsyncOpenAI is None:
        raise RuntimeError("OpenAI SDK not installed")
    client = AsyncOpenAI()

    async def one(item: dict) -> dict:
        messages = [
            {"role": "system", "content": "You are concise. Reply in one sentence."},
            {"role": "user", "content": f"Summarize: {item.get('text','')[:2000]}"},
        ]
        # Use the helper if available; otherwise call Responses API directly.
        try:
            txt = gpt5_text(client, messages, tier=tier, max_output_tokens=200)  # type: ignore[arg-type]
            if asyncio.iscoroutine(txt):
                txt = await txt
        except Exception:
            # Fallback to direct Responses API
            resp = await client.responses.create(
                model={"mini": "gpt-5-mini", "thinking": "gpt-5", "pro": "gpt-5-pro"}.get(tier, "gpt-5"),
                input=messages,
                reasoning={"effort": {"mini":"low","thinking":"medium","pro":"high"}.get(tier,"medium")},
                max_output_tokens=200
            )
            txt = getattr(resp, "output_text", None) or str(resp)
        return {"id": item.get("id"), "summary": txt}

    # Run items in the batch sequentially to stay within rate limits; the job runner
    # already parallelizes at the batch level.
    out = []
    for it in batch:
        out.append(await one(it))
    return out
