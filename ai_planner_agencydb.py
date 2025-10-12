# ai_planner_agencydb.py (v3 - AgencyDB Integration with Granular L2 Selection)
# Resilient AI suggestions connected to real database with specific task selection

import os, json, math, re, datetime, asyncio, uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
REASONING_MODEL = os.environ.get("AI_REASONING_MODEL", "gpt-5-thinking")  # GPT-5 model
EMBEDDING_MODEL = "text-embedding-3-large"

AI_STRICTNESS_DEFAULT = os.environ.get("AI_STRICTNESS_DEFAULT", "balanced")
AI_AUTORELAX = os.environ.get("AI_AUTORELAX", "true").lower() == "true"
AI_MIN_DELIVERABLES = int(os.environ.get("AI_MIN_DELIVERABLES", "3"))
AI_MIN_COMPONENTS_PER_DELIV = int(os.environ.get("AI_MIN_COMPONENTS_PER_DELIV", "2"))
AI_MIN_TASKS_PER_COMPONENT = int(os.environ.get("AI_MIN_TASKS_PER_COMPONENT", "2"))

DEPARTMENTS = [
    "Creative",
    "Strategy",
    "Paid Media",
    "Content",
    "Technology",
    "Integrated Marketing Management",
]

# ──────────────────────────────────────────────────────────────────────────────
# Background Job Tracking for AI Analysis
# ──────────────────────────────────────────────────────────────────────────────
class AIJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class AIAnalysisJob:
    job_id: str
    status: AIJobStatus
    start_time: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    end_time: Optional[float] = None
    total_chunks: int = 0
    processed_chunks: int = 0
    current_stage: str = "Initializing..."
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Global job store
AI_JOB_STORE: Dict[str, AIAnalysisJob] = {}
AI_JOB_TTL_SECONDS = 300  # Clean up jobs after 5 minutes

def cleanup_ai_jobs():
    """Remove expired completed/failed jobs to prevent memory leaks"""
    now = datetime.datetime.now().timestamp()
    to_remove = []
    
    for job_id, job in AI_JOB_STORE.items():
        if job.end_time and (now - job.end_time > AI_JOB_TTL_SECONDS):
            to_remove.append(job_id)
    
    for job_id in to_remove:
        del AI_JOB_STORE[job_id]
    
    if to_remove:
        print(f"[AI JOB CLEANUP] Removed {len(to_remove)} expired jobs")

# ──────────────────────────────────────────────────────────────────────────────
# Text Sanitization for LLM Safety
# ──────────────────────────────────────────────────────────────────────────────
def sanitize_for_json(text: str) -> str:
    """Sanitize text to prevent JSON parsing errors in LLM responses"""
    if not text:
        return ""
    text = str(text)
    # Replace problematic characters that break JSON
    text = text.replace('\\', '\\\\')  # Escape backslashes first
    text = text.replace('"', '\\"')     # Escape double quotes
    text = text.replace('\n', ' ')      # Replace newlines with spaces
    text = text.replace('\r', ' ')      # Replace carriage returns
    text = text.replace('\t', ' ')      # Replace tabs
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    # Limit length to prevent token overflow
    if len(text) > 500:
        text = text[:500] + "..."
    return text.strip()

def repair_json_response(text: str) -> str:
    """Attempt to repair malformed JSON responses from LLM"""
    if not text:
        return "{}"
    
    # Remove any leading/trailing whitespace
    text = text.strip()
    
    # Fix common issues
    # 1. Remove trailing commas before closing braces/brackets
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # 2. Fix malformed confidence values with spaces (e.g., "confidence":   0" -> "confidence": 0)
    text = re.sub(r'"confidence"\s*:\s*(\s+)(\d+(?:\.\d+)?)', r'"confidence": \2', text)
    text = re.sub(r'"confidence"\s*:\s*([^\d,}\]]+)(?=[,}\]])', r'"confidence": 0', text)
    
    # 3. Fix malformed relevance values
    text = re.sub(r'"relevance"\s*:\s*(\s+)(\d+(?:\.\d+)?)', r'"relevance": \2', text)
    text = re.sub(r'"relevance"\s*:\s*([^\d,}\]]+)(?=[,}\]])', r'"relevance": 0', text)
    
    # 4. Fix missing quotes around string values (common for enum fields)
    text = re.sub(r'("level"\s*:\s*)([^",}\]]+)(?=[,}\]])', r'\1"\2"', text)
    text = re.sub(r'("dept"\s*:\s*)([^",}\]]+)(?=[,}\]])', r'\1"\2"', text)
    text = re.sub(r'("budget_tier"\s*:\s*)([^",}\]]+)(?=[,}\]])', r'\1"\2"', text)
    text = re.sub(r'("complexity"\s*:\s*)([^",}\]]+)(?=[,}\]])', r'\1"\2"', text)
    
    # 5. Attempt to close unclosed strings at end of response
    # Count quotes to see if we have an odd number (unclosed string)
    quote_count = text.count('"') - text.count('\\"')
    if quote_count % 2 != 0:
        # Find last quote and try to close it
        last_quote_pos = text.rfind('"')
        if last_quote_pos > 0:
            # Check if it's a field name or value
            # Look for : after the last quote
            after_quote = text[last_quote_pos+1:].strip()
            if after_quote and after_quote[0] == ':':
                # It's a field name, add a value
                text = text + '""'
            else:
                # It's a value, just close it
                text = text[:last_quote_pos+1] + '"'
    
    # 6. Fix incomplete objects in arrays (add missing fields with defaults)
    # This is a simplistic approach - just ensure proper closure
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    
    # If we have unclosed structures, try to close them properly
    if open_braces > 0 or open_brackets > 0:
        # Add closing braces/brackets
        text += '}' * open_braces + ']' * open_brackets
    
    # 7. Final validation - try to parse and fix any remaining issues
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        # As a last resort, try to extract the largest valid JSON substring
        # Look for the first { and last matching }
        first_brace = text.find('{')
        if first_brace >= 0:
            # Try to find matching closing brace
            brace_count = 0
            last_brace = -1
            for i, char in enumerate(text[first_brace:], first_brace):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        last_brace = i
                        break
            
            if last_brace > first_brace:
                text = text[first_brace:last_brace+1]
            else:
                # Just close it at the end
                text = text[first_brace:] + '}'
        
        # If it's an array, handle similarly
        first_bracket = text.find('[')
        if first_bracket >= 0 and (first_brace < 0 or first_bracket < first_brace):
            bracket_count = 0
            last_bracket = -1
            for i, char in enumerate(text[first_bracket:], first_bracket):
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        last_bracket = i
                        break
            
            if last_bracket > first_bracket:
                text = text[first_bracket:last_bracket+1]
            else:
                text = text[first_bracket:] + ']'
    
    return text

# ──────────────────────────────────────────────────────────────────────────────
# OpenAI client (Chat Completions + Embeddings)
# ──────────────────────────────────────────────────────────────────────────────
if OPENAI_API_KEY:
    from openai import OpenAI
    oai = OpenAI(api_key=OPENAI_API_KEY)
else:
    oai = None

def embed_many(texts: List[str]) -> List[List[float]]:
    if not oai: 
        # Return zero embeddings as fallback
        return [[0.0] * 1536 for _ in texts]
    if not texts: return []
    
    # Filter out empty/invalid strings - OpenAI API rejects them
    valid_texts = [str(t).strip() if t else "unknown" for t in texts]
    valid_texts = [t if t else "unknown" for t in valid_texts]
    
    # Batch process to avoid API limits (max ~2048 inputs per request)
    BATCH_SIZE = 2000
    all_embeddings = []
    
    print(f"[EMBED] Processing {len(valid_texts)} texts in batches of {BATCH_SIZE}")
    
    for i in range(0, len(valid_texts), BATCH_SIZE):
        batch = valid_texts[i:i + BATCH_SIZE]
        print(f"[EMBED] Batch {i//BATCH_SIZE + 1}: {len(batch)} texts")
        r = oai.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        all_embeddings.extend([e.embedding for e in r.data])
    
    print(f"[EMBED] Completed: {len(all_embeddings)} embeddings generated")
    return all_embeddings

def gpt5_json_response(prompt: str, schema: dict, max_output_tokens: int = 2200) -> dict:
    """Use GPT-5 Responses API for reasoning models"""
    if not oai:
        # Return proper error structure based on schema
        if "items" in schema.get("properties", {}):
            return {"items": []}
        # For summarize_request, return all required fields
        return {
            "summary": "",
            "goals": [],
            "channels": [],
            "markets": [],
            "compliance": [],
            "languages": [],
            "timeline_weeks": 0,
            "budget_tier": "unknown",
            "complexity": "medium",
            "risk_flags": []
        }
    
    try:
        print(f"[GPT-5 API] Using Responses API with model: {REASONING_MODEL}")
        
        # Add schema instruction to the prompt
        schema_instruction = f"\n\nReturn a valid JSON object matching this schema: {json.dumps(schema, indent=2)}"
        full_prompt = prompt + schema_instruction
        
        response = oai.responses.create(
            model=REASONING_MODEL,
            input=full_prompt,
            max_output_tokens=max_output_tokens
        )
        
        # GPT-5 Responses API returns content directly
        text = response.content if hasattr(response, 'content') else str(response)
        
        # Handle empty or None content
        if not text or text.strip() == "":
            print(f"[GPT-5 Warning] Response returned empty content")
            if "items" in schema.get("properties", {}):
                return {"items": []}
            # For summarize_request
            return {
                "summary": "",
                "goals": [],
                "channels": [],
                "markets": [],
                "compliance": [],
                "languages": [],
                "timeline_weeks": 0,
                "budget_tier": "unknown",
                "complexity": "medium",
                "risk_flags": []
            }
        
        # Attempt to parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[GPT-5 JSON Repair] Attempting to fix malformed response: {e}")
            print(f"[GPT-5 Debug] Response text (first 200 chars): {text[:200] if text else 'Empty'}")
            repaired = repair_json_response(text)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as e2:
                print(f"[GPT-5 JSON Repair Failed] Could not repair: {e2}")
                # Return proper structure based on schema
                if "items" in schema.get("properties", {}):
                    return {"items": []}
                return {
                    "summary": "",
                    "goals": [],
                    "channels": [],
                    "markets": [],
                    "compliance": [],
                    "languages": [],
                    "timeline_weeks": 0,
                    "budget_tier": "unknown",
                    "complexity": "medium",
                    "risk_flags": []
                }
    
    except Exception as e:
        print(f"[GPT-5 API Error] OpenAI call failed: {e}")
        # Return proper error structure based on schema
        if "items" in schema.get("properties", {}):
            return {"items": []}
        return {
            "summary": "",
            "goals": [],
            "channels": [],
            "markets": [],
            "compliance": [],
            "languages": [],
            "timeline_weeks": 0,
            "budget_tier": "unknown",
            "complexity": "medium",
            "risk_flags": []
        }

def chat_json_schema(messages: list, schema: dict, max_completion_tokens: int = 2200) -> dict:
    """Use Chat Completions or GPT-5 Responses API based on model"""
    if not oai:
        # Return proper error structure based on schema
        if "items" in schema.get("properties", {}):
            return {"items": []}
        # For summarize_request
        return {
            "summary": "",
            "goals": [],
            "channels": [],
            "markets": [],
            "compliance": [],
            "languages": [],
            "timeline_weeks": 0,
            "budget_tier": "unknown",
            "complexity": "medium",
            "risk_flags": []
        }
    
    # Check if using a GPT-5 model (only use Responses API for actual GPT-5 models)
    if REASONING_MODEL.startswith("gpt-5"):
        print(f"[GPT-5 API] Using Responses API with model: {REASONING_MODEL}")
        # Convert messages to a single prompt for GPT-5 Responses API
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt = "\n\n".join(prompt_parts)
        return gpt5_json_response(prompt, schema, max_completion_tokens)
    
    # For non-GPT-5 models, use chat completions (backward compatibility)
    try:
        # For other models (which we don't use), use simpler JSON mode without strict schema validation
        if False:  # We only use GPT-5
            # Enhance messages to explicitly request JSON format matching the schema
            enhanced_messages = messages.copy()
            # Add schema instruction to the last user message
            if enhanced_messages and enhanced_messages[-1]["role"] == "user":
                enhanced_messages[-1]["content"] += f"\n\nIMPORTANT: You MUST return a valid JSON object that exactly matches this schema:\n{json.dumps(schema, indent=2)}\n\nEnsure all required fields are present and properly formatted."
            
            response = oai.chat.completions.create(
                model=REASONING_MODEL,
                messages=enhanced_messages,
                response_format={"type": "json_object"},  # Simpler JSON mode
                max_completion_tokens=max_completion_tokens,
                temperature=0.1  # Lower temperature for more consistent output
            )
        else:
            # For other models that support strict schema
            response = oai.chat.completions.create(
                model=REASONING_MODEL,
                messages=messages,
                response_format={"type": "json_schema", "json_schema": {"name": "Response", "schema": schema, "strict": True}},
                max_completion_tokens=max_completion_tokens,
            )
        
        # Check if response has valid content
        if not response.choices or len(response.choices) == 0:
            print(f"[API Warning] OpenAI returned no choices")
            if "items" in schema.get("properties", {}):
                return {"items": []}
            # For summarize_request
            return {
                "summary": "",
                "goals": [],
                "channels": [],
                "markets": [],
                "compliance": [],
                "languages": [],
                "timeline_weeks": 0,
                "budget_tier": "unknown",
                "complexity": "medium",
                "risk_flags": []
            }
        
        text = response.choices[0].message.content
        
        # Log model used for debugging
        print(f"[API Response] Model: {REASONING_MODEL}, Response length: {len(text) if text else 0} chars")
        
        # Handle empty or None content
        if not text or text.strip() == "":
            print(f"[API Warning] OpenAI returned empty content")
            if "items" in schema.get("properties", {}):
                return {"items": []}
            return {
                "summary": "",
                "goals": [],
                "channels": [],
                "markets": [],
                "compliance": [],
                "languages": [],
                "timeline_weeks": 0,
                "budget_tier": "unknown",
                "complexity": "medium",
                "risk_flags": []
            }
        
        # Attempt to parse JSON
        try:
            result = json.loads(text)
            print(f"[JSON Success] Successfully parsed JSON response")
            return result
        except json.JSONDecodeError as e:
            print(f"[JSON Repair] Attempting to fix malformed response: {e}")
            print(f"[JSON Debug] Model: {REASONING_MODEL}")
            print(f"[JSON Debug] Response text (first 500 chars): {text[:500] if text else 'Empty'}")
            print(f"[JSON Debug] Response text (last 500 chars): {text[-500:] if text and len(text) > 500 else ''}")
            
            repaired = repair_json_response(text)
            try:
                result = json.loads(repaired)
                print(f"[JSON Repair Success] Successfully repaired and parsed JSON")
                return result
            except json.JSONDecodeError as e2:
                print(f"[JSON Repair Failed] Could not repair: {e2}")
                print(f"[JSON Repair Debug] Repaired text (first 500 chars): {repaired[:500] if repaired else 'Empty'}")
                # Return proper structure based on schema
                if "items" in schema.get("properties", {}):
                    return {"items": []}
                return {
                    "summary": "",
                    "goals": [],
                    "channels": [],
                    "markets": [],
                    "compliance": [],
                    "languages": [],
                    "timeline_weeks": 0,
                    "budget_tier": "unknown",
                    "complexity": "medium",
                    "risk_flags": []
                }
    
    except Exception as e:
        print(f"[API Error] OpenAI call failed: {e}")
        if "items" in schema.get("properties", {}):
            return {"items": []}
        return {
            "summary": "",
            "goals": [],
            "channels": [],
            "markets": [],
            "compliance": [],
            "languages": [],
            "timeline_weeks": 0,
            "budget_tier": "unknown",
            "complexity": "medium",
            "risk_flags": []
        }

# ──────────────────────────────────────────────────────────────────────────────
# AgencyDB Catalog Builder
# ──────────────────────────────────────────────────────────────────────────────
def build_catalog_from_agencydb(db) -> List[Dict[str, Any]]:
    """Convert AgencyDB all_rows DataFrame into AI-ready catalog"""
    items = []
    
    if db.all_rows is None or db.all_rows.empty:
        return items
    
    # Group by deliverable
    for deliv_code, deliv_group in db.all_rows.groupby('Deliverable_Code'):
        if pd.isna(deliv_code) or not str(deliv_code).strip():
            continue
            
        # Get deliverable info from first row
        first_row = deliv_group.iloc[0]
        deliv_name = str(first_row.get('Deliverable', deliv_code))
        service_dept = str(first_row.get('Service Department', 'Strategy'))
        
        # Normalize department
        dept = _normalize_dept(service_dept)
        if dept not in DEPARTMENTS:
            continue
        
        # Add deliverable to catalog with sanitized text
        deliv_item = {
            "id": str(deliv_code),
            "level": "deliverable",
            "dept": dept,
            "title": sanitize_for_json(deliv_name),
            "desc": "",
            "keywords": _extract_keywords(deliv_name)
        }
        items.append(deliv_item)
        
        # Group by component under this deliverable (v4 uses Component_Task_L1)
        comp_column = 'Component_Task_L1' if 'Component_Task_L1' in db.all_rows.columns else 'Component'
        for comp_name, comp_group in deliv_group.groupby(comp_column):
            if pd.isna(comp_name) or not str(comp_name).strip() or str(comp_name) == 'nan':
                comp_name = "General"
            
            comp_id = f"{deliv_code}::{comp_name}"
            comp_item = {
                "id": comp_id,
                "parentId": str(deliv_code),
                "level": "component",
                "dept": dept,
                "title": sanitize_for_json(comp_name),
                "desc": "",
                "keywords": _extract_keywords(str(comp_name))
            }
            items.append(comp_item)
            
            # Add all L2 tasks under this component
            for idx, row in comp_group.iterrows():
                # v4 uses Task_Task_L2, fallback to Task_Label or task_group
                task_label = str(row.get('Task_Task_L2', row.get('Task_Label', row.get('task_group', 'Task'))))
                if pd.isna(task_label) or not task_label.strip() or task_label == 'nan':
                    continue
                
                # v4 uses Estimated_Hours instead of Hours
                hours = row.get('Estimated_Hours', row.get('Hours', 2.0))
                base_hours = float(hours) if not pd.isna(hours) else 2.0
                
                task_id = f"{deliv_code}::{comp_name}::{task_label}"
                task_item = {
                    "id": task_id,
                    "parentId": comp_id,
                    "level": "task",
                    "dept": dept,
                    "title": sanitize_for_json(task_label),
                    "desc": "",
                    "keywords": _extract_keywords(task_label),
                    "base_hours": base_hours
                }
                items.append(task_item)
    
    return items

def _normalize_dept(s: str) -> str:
    x = (s or "").lower()
    if "paid" in x or "media" in x: return "Paid Media"
    if "integrated" in x or "imm" in x: return "Integrated Marketing Management"
    if "strategy" in x or "strat" in x: return "Strategy"
    if "creative" in x: return "Creative"
    if "content" in x: return "Content"
    if any(k in x for k in ["tech", "dev", "web", "technology"]): return "Technology"
    return "Strategy"

def _extract_keywords(text: str) -> List[str]:
    """Extract keywords from text"""
    words = re.findall(r'\b\w+\b', text.lower())
    # Remove common stop words
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    keywords = [w for w in words if w not in stopwords and len(w) > 2]
    return keywords[:10]  # Limit to 10 keywords

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
_nonword = re.compile(r"[^a-z0-9\s\-\&\/\+]")
def normalize_text(s: str) -> str: return _nonword.sub(" ", (s or "").lower())
def tokenize(s: str) -> List[str]: return [t for t in normalize_text(s).split() if t]
def sentence_split(text: str) -> List[str]:
    return [s.strip() for s in re.split(r'(?<=[\.\?\!])\s+(?=[A-Z0-9])', text) if s.strip()]

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0: return 0.0
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0: return 0.0
    return float(np.dot(a, b) / denom)

def lexical_score(text: str, title: str, desc: str, keywords: List[str], dept: str) -> float:
    tk_r = set(tokenize(text))
    tk_c = set(tokenize(" ".join([title or "", desc or "", " ".join(keywords or [])])))
    overlap = sum(1 for t in tk_c if t in tk_r)
    dept_hit = 0.05 if dept.lower().split(" ")[0] in tk_r else 0
    return min(1.0, (overlap / max(4, len(tk_c))) + dept_hit)

# ──────────────────────────────────────────────────────────────────────────────
# Summarize request
# ──────────────────────────────────────────────────────────────────────────────
def summarize_request(request_text: str) -> Dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "goals": {"type": "array", "items": {"type": "string"}},
            "channels": {"type": "array", "items": {"type": "string"}},
            "markets": {"type": "array", "items": {"type": "string"}},
            "compliance": {"type": "array", "items": {"type": "string"}},
            "languages": {"type": "array", "items": {"type": "string"}},
            "timeline_weeks": {"type": "number"},
            "budget_tier": {"type": "string", "enum": ["unknown", "scrappy", "moderate", "premium"]},
            "complexity": {"type": "string", "enum": ["low", "medium", "high"]},
            "risk_flags": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["summary", "goals", "channels", "markets", "compliance", "languages", "timeline_weeks", "budget_tier", "complexity", "risk_flags"],
        "additionalProperties": False
    }
    messages = [
        {"role": "system", "content": "You are a senior agency PM/strategist in digital/creative/paid media/content/tech. Extract actionable signals."},
        {"role": "user", "content": f"REQUEST TEXT:\n{request_text}\n\nSummarize (<=120 words) and extract: goals, channels, markets, compliance, languages, timeline_weeks, budget_tier, complexity, risk_flags."}
    ]
    return chat_json_schema(messages, schema)

# ──────────────────────────────────────────────────────────────────────────────
# Recall candidates (embeddings + lexical)
# ──────────────────────────────────────────────────────────────────────────────
def recall_candidates(request_text: str, catalog: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not catalog:
        return [], []
    
    texts = [f"{str(i.get('dept',''))} • {str(i.get('level',''))} • {str(i.get('title',''))} :: {str(i.get('desc',''))} :: {', '.join(str(k) for k in i.get('keywords',[]))}" for i in catalog]
    embs = embed_many([request_text] + texts)
    req = np.array(embs[0], dtype=np.float32)
    
    cands = []
    for i, it in enumerate(catalog, start=1):
        v = np.array(embs[i], dtype=np.float32)
        emb = cosine(req, v)
        lex = lexical_score(request_text, it["title"], it.get("desc", ""), it.get("keywords", []), it["dept"])
        recall = 0.70 * emb + 0.30 * lex
        cands.append({**it, "embScore": emb, "lexScore": lex, "recall": recall})
    
    # Generous cuts to feed re-ranker
    topD = sorted([x for x in cands if x["level"] == "deliverable"], key=lambda z: z["recall"], reverse=True)[:60]
    topC = sorted([x for x in cands if x["level"] == "component"], key=lambda z: z["recall"], reverse=True)[:90]
    topT = sorted([x for x in cands if x["level"] == "task"], key=lambda z: z["recall"], reverse=True)[:120]
    
    return topD + topC + topT, cands

# ──────────────────────────────────────────────────────────────────────────────
# Evidence & LLM re-score with GRANULAR TASK SELECTION
# ──────────────────────────────────────────────────────────────────────────────
def best_evidence(request_text: str, candidate: Dict[str, Any], k: int = 3) -> List[str]:
    sents = sentence_split(request_text)
    scored = [(s, lexical_score(s, candidate["title"], candidate.get("desc", ""), candidate.get("keywords", []), candidate["dept"])) for s in sents]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s for s, score in scored[:k] if score > 0]

def rescore_with_llm_granular(summary: Dict[str, Any], candidates: List[Dict[str, Any]], request_text: str, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """LLM re-scoring with GRANULAR task-level selection - only select relevant tasks, exclude irrelevant ones"""
    if not candidates or not oai:
        return []
    
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "dept": {"type": "string", "enum": DEPARTMENTS},
                        "level": {"type": "string", "enum": ["deliverable", "component", "task"]},
                        "relevance": {"type": "number", "minimum": 0, "maximum": 100},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "why": {"type": "string"},
                        "risks": {"type": "string"},
                        "select": {"type": "boolean"}  # NEW: explicit selection flag for tasks
                    },
                    "required": ["id", "dept", "level", "relevance", "confidence", "why", "risks", "select"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["items"],
        "additionalProperties": False
    }
    
    out = []
    chunk = 35  # Reduced chunk size for better reliability with GPT-5
    total_chunks = math.ceil(len(candidates) / chunk)
    
    # Update job with total chunks if job_id provided
    if job_id and job_id in AI_JOB_STORE:
        AI_JOB_STORE[job_id].total_chunks = total_chunks
        AI_JOB_STORE[job_id].current_stage = f"Analyzing with GPT-5 (0/{total_chunks} chunks)"
    
    for i in range(0, len(candidates), chunk):
        block = candidates[i:i + chunk]
        chunk_num = (i // chunk) + 1
        
        # Update job progress
        if job_id and job_id in AI_JOB_STORE:
            AI_JOB_STORE[job_id].current_stage = f"Analyzing with GPT-5 (chunk {chunk_num}/{total_chunks})"
        
        # Sanitize all text in payload to prevent JSON parsing errors
        payload = []
        for c in block:
            evidence = best_evidence(request_text, c, 3)
            payload.append({
                "id": sanitize_for_json(c["id"]),
                "dept": c["dept"],
                "level": c["level"],
                "title": sanitize_for_json(c["title"]),
                "desc": sanitize_for_json(c.get("desc", "")),
                "evidence": [sanitize_for_json(e) for e in evidence]
            })
        
        # Sanitize summary fields
        safe_summary = sanitize_for_json(summary.get('summary', ''))
        safe_goals = [sanitize_for_json(g) for g in summary.get("goals", [])]
        safe_channels = [sanitize_for_json(c) for c in summary.get('channels', [])]
        safe_markets = [sanitize_for_json(m) for m in summary.get('markets', [])]
        safe_compliance = [sanitize_for_json(c) for c in summary.get('compliance', [])]
        
        messages = [
            {"role": "system", "content": """You are a Senior Agency Executive (CEO/President level) with 20+ years experience running successful marketing/advertising/digital agencies. 
You think strategically about:
- Client value and ROI
- Resource allocation and team capabilities  
- Risk management and quality assurance
- Competitive differentiation and innovation
- Long-term client relationships

Score each deliverable/component/task with REALISTIC confidence scores:
- 90-100: Essential, directly requested, mission-critical
- 70-89: Very relevant, strongly recommended, adds significant value
- 50-69: Moderately relevant, nice-to-have, enhances project
- 30-49: Tangentially related, optional, limited value
- 0-29: Not relevant, would not recommend

For TASKS, set select=true ONLY if specifically needed for THIS project. Exclude generic/boilerplate tasks that don't match the specific request.
Think about the complete project lifecycle, dependencies, and what will actually deliver results for the client."""},
            {"role": "user", "content": f"REQUEST SUMMARY:\n{safe_summary}\n\nGOALS:\n- " + "\n- ".join(safe_goals) + f"\n\nCHANNELS: {', '.join(safe_channels)} | MARKETS: {', '.join(safe_markets)} | COMPLIANCE: {', '.join(safe_compliance)}\n\nCANDIDATES:\n{json.dumps(payload, indent=2)}\n\nProvide realistic confidence scores based on actual relevance. Do NOT default to any specific score like 62%. Each item should have a unique, justified confidence level."}
        ]
        
        try:
            r = chat_json_schema(messages, schema, max_completion_tokens=3500)  # Matched to chunk size (70 items × ~50 tokens/item)
            out.extend(r.get("items", []))
        except Exception as e:
            print(f"[LLM Re-score Error] {e}")
            # Fallback: mark items based on recall score
            for c in block:
                out.append({
                    "id": c["id"],
                    "dept": c["dept"],
                    "level": c["level"],
                    "relevance": min(100, c["recall"] * 100),
                    "confidence": c["recall"],
                    "why": "Recall-based selection (LLM unavailable)",
                    "risks": "",
                    "select": c["recall"] > 0.4  # Threshold for auto-select
                })
        
        # Update chunk completion
        if job_id and job_id in AI_JOB_STORE:
            AI_JOB_STORE[job_id].processed_chunks = chunk_num
    
    return out

# [Continued in next message due to length...]
# ──────────────────────────────────────────────────────────────────────────────
# Fusion, calibration, AUTO-RELAX & RESCUE
# ──────────────────────────────────────────────────────────────────────────────
def fuse_and_calibrate(candidates: List[Dict[str, Any]], llm_scores: List[Dict[str, Any]], strictness: str = "balanced") -> List[Dict[str, Any]]:
    lookup = {x["id"]: x for x in llm_scores}
    W = {"emb": 0.15, "lex": 0.10, "recall": 0.10, "llm": 0.55, "hist": 0.10}
    hist_prior = 0.65
    gates = {"high": 0.70, "balanced": 0.58, "recall": 0.48}
    
    out = []
    for c in candidates:
        l = lookup.get(c["id"])
        llm_val = (l["relevance"] / 100.0) if l else 0.0
        llm_select = l.get("select", True) if l else True  # Respect AI's select flag
        
        raw = W["emb"] * c["embScore"] + W["lex"] * c["lexScore"] + W["recall"] * c["recall"] + W["llm"] * llm_val + W["hist"] * hist_prior
        calibrated = 1.0 / (1.0 + math.exp(-(2.2 * raw - 1.1)))
        
        # For tasks: only pass if AI explicitly selected it
        if c["level"] == "task" and not llm_select:
            pass_gate = False
        else:
            pass_gate = calibrated >= gates.get(strictness, gates["balanced"])
        
        out.append({**c, "llm": l, "fused_score": raw, "calibrated_confidence": calibrated, "pass": pass_gate, "ai_selected": llm_select})
    
    return out

def _auto_rescue_if_empty(fused: List[Dict[str, Any]], all_recall: List[Dict[str, Any]], llm_scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """If no deliverables pass, relax and ensure a non-empty scope"""
    passed_delivs = [x for x in fused if x["level"] == "deliverable" and x["pass"]]
    if passed_delivs:
        return fused
    
    # Build maps
    by_id = {x["id"]: x for x in fused}
    llm_map = {x["id"]: x for x in llm_scores}
    recall_map = {x["id"]: x for x in all_recall}
    
    # Rank deliverables by LLM relevance (if any), else recall
    deliv_cands = [x for x in all_recall if x["level"] == "deliverable"]
    def deliv_key(x):
        l = llm_map.get(x["id"])
        return (l["relevance"] if l else 0.0, x["recall"])
    deliv_cands.sort(key=deliv_key, reverse=True)
    # CHANGED: Remove limit - suggest ALL deliverables that have decent scores
    # Filter by minimum threshold instead of hard limit
    min_threshold = 0.30  # Deliverables with at least 30% recall/relevance
    chosen_delivs = [d for d in deliv_cands if d["recall"] > min_threshold or (llm_map.get(d["id"], {}).get("relevance", 0) > 30)]
    
    # If still no deliverables, take at least the minimum
    if not chosen_delivs:
        chosen_delivs = deliv_cands[:max(AI_MIN_DELIVERABLES, 3)]
    
    # Mark chosen deliverables as pass with REAL SCORES
    for d in chosen_delivs:
        llm_d = llm_map.get(d["id"])
        # Use actual LLM confidence if available, else calculate from recall
        actual_confidence = llm_d.get("confidence", d["recall"]) if llm_d else d["recall"]
        
        if d["id"] not in by_id:
            fused.append({**d, "llm": llm_d, "calibrated_confidence": actual_confidence, "pass": True, "fused_score": d["recall"], "ai_selected": True})
        else:
            by_id[d["id"]]["pass"] = True
            by_id[d["id"]]["calibrated_confidence"] = max(by_id[d["id"]]["calibrated_confidence"], actual_confidence)
    
    # Pick components/tasks under each chosen deliverable
    comp_cands = [x for x in all_recall if x["level"] == "component"]
    task_cands = [x for x in all_recall if x["level"] == "task"]
    
    for d in chosen_delivs:
        # top components under this deliverable
        comps = [c for c in comp_cands if c.get("parentId") == d["id"]]
        comps.sort(key=lambda z: (llm_map.get(z["id"], {"relevance": 0}).get("relevance", 0), z["recall"]), reverse=True)
        # CHANGED: Don't limit components - suggest all relevant ones
        for c in comps:
            llm_c = llm_map.get(c["id"])
            # Skip components with very low relevance
            if c["recall"] < 0.25 and (not llm_c or llm_c.get("relevance", 0) < 25):
                continue
                
            # Use actual LLM confidence if available
            actual_comp_confidence = llm_c.get("confidence", c["recall"]) if llm_c else c["recall"]
            
            if c["id"] not in by_id:
                fused.append({**c, "llm": llm_c, "calibrated_confidence": actual_comp_confidence, "pass": True, "fused_score": c["recall"], "ai_selected": True})
            else:
                by_id[c["id"]]["pass"] = True
                by_id[c["id"]]["calibrated_confidence"] = max(by_id[c["id"]]["calibrated_confidence"], actual_comp_confidence)
            # tasks under this component - respect AI selection
            tasks = [t for t in task_cands if t.get("parentId") == c["id"]]
            tasks.sort(key=lambda z: (llm_map.get(z["id"], {"relevance": 0}).get("relevance", 0), z["recall"]), reverse=True)
            # Only include AI-selected tasks
            for t in tasks:  # CHANGED: No limit on tasks
                llm_t = llm_map.get(t["id"])
                if llm_t and llm_t.get("select", False):  # Only if AI selected
                    # Use actual LLM confidence for tasks
                    actual_task_confidence = llm_t.get("confidence", t["recall"]) if llm_t else t["recall"]
                    
                    if t["id"] not in by_id:
                        fused.append({**t, "llm": llm_t, "calibrated_confidence": actual_task_confidence, "pass": True, "fused_score": t["recall"], "ai_selected": True})
                    else:
                        by_id[t["id"]]["pass"] = True
                        by_id[t["id"]]["calibrated_confidence"] = max(by_id[t["id"]]["calibrated_confidence"], actual_task_confidence)
    
    return fused

# ──────────────────────────────────────────────────────────────────────────────
# Composition with AgencyDB structure
# ──────────────────────────────────────────────────────────────────────────────
def multipliers_from_summary(sumdict: Dict[str, Any]) -> Dict[str, float]:
    ch = len(sumdict.get("channels", []))
    mk = len(sumdict.get("markets", []))
    comp = len(sumdict.get("compliance", []))
    complexity = {"low": 1.0, "medium": 1.15, "high": 1.35}.get(sumdict.get("complexity"), 1.0)
    channel_multi = 1.25 if ch > 4 else (1.12 if ch > 2 else 1.0)
    market_multi = 1.18 if mk > 1 else 1.0
    compliance_multi = 1.08 if comp > 0 else 1.0
    return {"complexity": complexity, "channelMulti": channel_multi, "marketMulti": market_multi, "complianceMulti": compliance_multi}

def planned_hours(base: float, m: Dict[str, float]) -> float:
    return round(base * m["complexity"] * m["channelMulti"] * m["marketMulti"] * m["complianceMulti"], 1)

def compose_plan_from_agencydb(fused: List[Dict[str, Any]], summary: Dict[str, Any], catalog: List[Dict[str, Any]], db, all_recall: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compose plan using real AgencyDB deliverable codes and structure"""
    passing = [x for x in fused if x["pass"]]
    dels = [x for x in passing if x["level"] == "deliverable"]
    comps_pass = {x["id"]: x for x in passing if x["level"] == "component"}
    tasks_pass = {x["id"]: x for x in passing if x["level"] == "task" and x.get("ai_selected", True)}  # Only AI-selected tasks
    
    # If still nothing after auto-rescue, hard fallback
    if not dels:
        topD = [x for x in all_recall if x["level"] == "deliverable"]
        topD.sort(key=lambda z: z["recall"], reverse=True)
        # CHANGED: Take all deliverables with reasonable scores, not just 3
        min_score = 0.20  # Minimum 20% recall to be included
        dels = [d for d in topD if d["recall"] > min_score]
        if not dels:  # If still nothing, take at least minimum
            dels = topD[:max(AI_MIN_DELIVERABLES, 3)]
    
    by_dept: Dict[str, List[Dict[str, Any]]] = {}
    m = multipliers_from_summary(summary)
    
    # Build deliverable lookup from catalog
    deliv_lookup = {x["id"]: x for x in catalog if x["level"] == "deliverable"}
    
    for d_item in dels:
        deliv_code = d_item["id"]
        deliv_info = deliv_lookup.get(deliv_code, d_item)
        dept = deliv_info["dept"]
        
        if dept not in DEPARTMENTS:
            continue
        
        by_dept.setdefault(dept, [])
        
        # Get deliverable base hours from DB
        deliv_rows = db.all_rows[db.all_rows['Deliverable_Code'] == deliv_code]
        d_hours = deliv_rows['Estimated_Hours'].sum() if not deliv_rows.empty else 8.0
        d_hours_planned = planned_hours(d_hours, m)
        
        # Components
        comp_out = []
        for comp_item in [x for x in catalog if x["level"] == "component" and x.get("parentId") == deliv_code]:
            comp_id = comp_item["id"]
            sc = comps_pass.get(comp_id)
            
            if sc:  # Component passed
                # Get tasks for this component - ONLY AI-selected ones
                t_out = []
                for task_item in [x for x in catalog if x["level"] == "task" and x.get("parentId") == comp_id]:
                    task_id = task_item["id"]
                    ts = tasks_pass.get(task_id)
                    
                    if ts and ts.get("ai_selected", False):  # Only include AI-selected tasks
                        base_hours = task_item.get("base_hours", 2.0)
                        t_out.append({
                            "id": task_id,
                            "title": task_item["title"],
                            "calibrated_confidence": ts.get("calibrated_confidence", 0.50),
                            "why": (ts.get("llm") or {}).get("why", "Selected by AI as relevant to project."),
                            "planned_hours": planned_hours(base_hours, m),
                            "ai_selected": True
                        })
                
                # Calculate component hours
                comp_rows = deliv_rows[deliv_rows['Component_Task_L1'] == comp_item["title"].split("::")[- 1]]
                c_hours = comp_rows['Estimated_Hours'].sum() if not comp_rows.empty else 4.0
                
                comp_out.append({
                    "id": comp_id,
                    "title": comp_item["title"].split("::")[- 1],  # Clean component name
                    "calibrated_confidence": sc["calibrated_confidence"],
                    "why": (sc.get("llm") or {}).get("why", ""),
                    "planned_hours": planned_hours(c_hours, m),
                    "tasks": t_out
                })
        
        # Milestones
        milestones = [
            {"name": "Kickoff", "offset_days": 0},
            {"name": "Plan/Strategy Complete", "offset_days": math.ceil((d_hours_planned or 8) / 6)},
            {"name": "Launch/Activations", "offset_days": math.ceil((d_hours_planned or 8) / 6) + 5},
            {"name": "First Report", "offset_days": math.ceil((d_hours_planned or 8) / 6) + 14},
        ]
        
        by_dept[dept].append({
            "code": deliv_code,  # Real database code (renamed from deliverable_code)
            "name": deliv_info["title"],  # Frontend expects 'name' not 'deliverable_title'
            "title": deliv_info["title"],  # Keep for backward compatibility
            "confidence": d_item.get("calibrated_confidence", 0.60),  # Renamed from calibrated_confidence
            "deliverable_code": deliv_code,  # Keep old field for backward compatibility
            "deliverable_title": deliv_info["title"],  # Keep old field for backward compatibility
            "calibrated_confidence": d_item.get("calibrated_confidence", 0.60),  # Keep old field for backward compatibility
            "why": (d_item.get("llm") or {}).get("why", ""),
            "risks": (d_item.get("llm") or {}).get("risks", ""),
            "planned_hours": d_hours_planned,
            "components": comp_out,
            "milestones": milestones
        })
    
    total = 0.0
    for dept_items in by_dept.values():
        for deliv in dept_items:
            total += deliv["planned_hours"] or 0.0
            for comp in deliv.get("components", []):
                total += comp["planned_hours"] or 0.0
                for t in comp.get("tasks", []):
                    total += t["planned_hours"] or 0.0
    
    return {
        "summary": summary,
        "strictness": AI_STRICTNESS_DEFAULT,
        "totals": {"planned_hours_total": round(total, 1)},
        "suggestions_by_department": by_dept
    }

# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
def analyze_with_agencydb(request_text: str, db, strictness: str = None, job_id: Optional[str] = None) -> Dict[str, Any]:
    """Main analysis function using AgencyDB"""
    strictness = strictness or AI_STRICTNESS_DEFAULT
    
    # Update job status
    if job_id and job_id in AI_JOB_STORE:
        AI_JOB_STORE[job_id].status = AIJobStatus.RUNNING
        AI_JOB_STORE[job_id].current_stage = "Building catalog from database..."
    
    # Build catalog from AgencyDB
    catalog = build_catalog_from_agencydb(db)
    
    if not catalog:
        return {
            "auto_run": True,
            "message": "No deliverables found in database.",
            "plan": {"summary": {}, "suggestions_by_department": {}},
            "diagnostics": {"candidates_considered": 0, "catalog_items": 0}
        }
    
    print(f"[AI Planner] Built catalog with {len(catalog)} items from AgencyDB")
    
    # Update job status
    if job_id and job_id in AI_JOB_STORE:
        AI_JOB_STORE[job_id].current_stage = "Summarizing request with GPT-5..."
    
    summary = summarize_request(request_text)
    
    # Update job status
    if job_id and job_id in AI_JOB_STORE:
        AI_JOB_STORE[job_id].current_stage = "Finding candidate deliverables..."
    
    # Process all items - let AI intelligence do the filtering
    candidates, all_recall = recall_candidates(request_text, catalog)
    
    if not candidates:
        return {
            "auto_run": True,
            "message": "No candidates matched request.",
            "plan": {"summary": summary, "suggestions_by_department": {}},
            "diagnostics": {"candidates_considered": 0, "catalog_items": len(catalog)}
        }
    
    llm_scores = rescore_with_llm_granular(summary, candidates, request_text, job_id)
    
    # Update job status
    if job_id and job_id in AI_JOB_STORE:
        AI_JOB_STORE[job_id].current_stage = "Calibrating scores and finalizing plan..."
    
    fused = fuse_and_calibrate(candidates, llm_scores, strictness)
    
    # AUTO-RELAX & RESCUE
    if AI_AUTORELAX:
        fused = _auto_rescue_if_empty(fused, all_recall, llm_scores)
    
    plan = compose_plan_from_agencydb(fused, summary, catalog, db, all_recall)
    
    return {
        "auto_run": True,
        "message": "AI analysis complete with granular task selection.",
        "plan": plan,
        "diagnostics": {
            "candidates_considered": len(candidates),
            "catalog_items": len(catalog),
            "deliverables_selected": len([x for x in fused if x["level"] == "deliverable" and x["pass"]]),
            "tasks_ai_selected": len([x for x in fused if x["level"] == "task" and x.get("ai_selected", False) and x["pass"]])
        }
    }

def _run_analysis_background(job_id: str, request_text: str, db, strictness: str = None):
    """Background task to run AI analysis"""
    try:
        result = analyze_with_agencydb(request_text, db, strictness, job_id)
        
        if job_id in AI_JOB_STORE:
            AI_JOB_STORE[job_id].status = AIJobStatus.COMPLETED
            AI_JOB_STORE[job_id].result = result
            AI_JOB_STORE[job_id].end_time = datetime.datetime.now().timestamp()
            AI_JOB_STORE[job_id].current_stage = "Complete"
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"[AI JOB {job_id} ERROR] {error_detail}")
        
        if job_id in AI_JOB_STORE:
            AI_JOB_STORE[job_id].status = AIJobStatus.FAILED
            AI_JOB_STORE[job_id].error = str(e)
            AI_JOB_STORE[job_id].end_time = datetime.datetime.now().timestamp()

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI routes
# ──────────────────────────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    request_text: str
    strictness: Optional[str] = None

def mount_routes_agencydb(app: FastAPI, base: str = "/api/ai"):
    router = APIRouter()
    
    @router.post("/analyze")
    def _analyze(payload: AnalyzeRequest, background_tasks: BackgroundTasks):
        """Start AI analysis as a background job and return job ID immediately"""
        try:
            db = app.state.db
            if not getattr(db, "loaded", False):
                db.load()
            
            # Clean up old jobs to prevent memory leaks
            cleanup_ai_jobs()
            
            # Create job
            job_id = str(uuid.uuid4())
            AI_JOB_STORE[job_id] = AIAnalysisJob(
                job_id=job_id,
                status=AIJobStatus.PENDING
            )
            
            # Start background task
            background_tasks.add_task(
                _run_analysis_background,
                job_id,
                payload.request_text,
                db,
                payload.strictness
            )
            
            return {
                "job_id": job_id,
                "status": "started",
                "message": "AI analysis started in background"
            }
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            print(f"[AI PLANNER ERROR] {error_detail}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/status/{job_id}")
    def _status(job_id: str):
        """Get status of AI analysis job"""
        if job_id not in AI_JOB_STORE:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = AI_JOB_STORE[job_id]
        now = datetime.datetime.now().timestamp()
        elapsed = now - job.start_time
        
        # Calculate progress percentage
        progress = 0
        eta = None
        if job.total_chunks > 0 and job.processed_chunks > 0:
            progress = int((job.processed_chunks / job.total_chunks) * 100)
            # Estimate remaining time based on average time per chunk
            if job.processed_chunks < job.total_chunks:
                avg_time_per_chunk = elapsed / job.processed_chunks
                remaining_chunks = job.total_chunks - job.processed_chunks
                eta = avg_time_per_chunk * remaining_chunks
        
        response = {
            "job_id": job.job_id,
            "status": job.status.value,
            "progress": progress,
            "current_stage": job.current_stage,
            "elapsed_seconds": round(elapsed, 1),
            "eta_seconds": round(eta, 1) if eta else None
        }
        
        if job.status == AIJobStatus.COMPLETED and job.result:
            response["result"] = job.result
        
        if job.status == AIJobStatus.FAILED and job.error:
            response["error"] = job.error
        
        return response
    
    @router.get("/health")
    def _health():
        try:
            db = app.state.db
            if not getattr(db, "loaded", False):
                db.load()
            catalog = build_catalog_from_agencydb(db)
            deliverables = len([x for x in catalog if x["level"] == "deliverable"])
            return {
                "ok": True,
                "deliverables": deliverables,
                "catalog_items": len(catalog),
                "strictness_default": AI_STRICTNESS_DEFAULT,
                "autorelax": AI_AUTORELAX,
                "database_loaded": db.loaded,
                "database_source": db.src
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    app.include_router(router, prefix=base)
