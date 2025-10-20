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
from gpt5_helpers import gpt5_json_schema, gpt5_text
from embedding_cache import embed_many, get_cache_stats  # Import embedding cache

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
REASONING_MODEL = os.environ.get("AI_REASONING_MODEL", "gpt-5-thinking")  # GPT-5 model
EMBEDDING_MODEL = "text-embedding-3-large"

AI_STRICTNESS_DEFAULT = os.environ.get("AI_STRICTNESS_DEFAULT", "balanced")
AI_AUTORELAX = os.environ.get("AI_AUTORELAX", "true").lower() == "true"
AI_MIN_DELIVERABLES = int(os.environ.get("AI_MIN_DELIVERABLES", "20"))  # Reasonable default for normal RFPs
AI_MIN_COMPONENTS_PER_DELIV = int(os.environ.get("AI_MIN_COMPONENTS_PER_DELIV", "3"))  # Increased for richer expansion
AI_MIN_TASKS_PER_COMPONENT = int(os.environ.get("AI_MIN_TASKS_PER_COMPONENT", "3"))  # Increased for more detail

# Fast vs Deep mode configuration
FAST_TOP_K = int(os.getenv("FAST_TOP_K", "120"))     # Lexical prefilter for Fast mode - increased for comprehensive RFPs
DEEP_TOP_K = int(os.getenv("DEEP_TOP_K", "100"))     # LLM rescoring set for Deep mode - increased to 100 for luxury fashion

DEPARTMENTS = [
    "Creative",
    "Strategy",
    "Paid Media",
    "Content",
    "Technology",
    "Integrated Marketing Management",
]

# ──────────────────────────────────────────────────────────────────────────────
# Service Mapping for Explicit Match Detection
# ──────────────────────────────────────────────────────────────────────────────
SERVICE_MAPPING = {
    # Paid Media Services
    "paid media buying": ["PM.01", "PM.02", "PM.03", "PM.04", "PM.05", "PM.06"],
    "paid media planning": ["PM.01", "PM.02", "PM.03", "PM.04"],
    "media buying": ["PM.01", "PM.02", "PM.03", "PM.04", "PM.05", "PM.06"],
    "media planning": ["PM.01", "PM.02", "PM.03", "PM.04"],
    "performance reporting": ["PM.04", "PM.05", "PM.06", "CS.04"],
    "analytics reporting": ["PM.04", "PM.05", "PM.06", "CS.04"],
    "campaign measurement": ["PM.04", "PM.05", "PM.06", "CS.04"],
    "performance tracking": ["PM.04", "PM.05", "PM.06", "CS.04"],
    
    # Campaign Strategy
    "campaign strategy": ["CS.01", "CS.02", "CS.03", "CS.04"],
    "strategic planning": ["CS.01", "CS.02", "CS.03"],
    "marketing strategy": ["CS.01", "CS.02", "CS.03"],
    "audience strategy": ["CS.01", "CS.02", "CS.03", "PM.01"],
    "audience targeting": ["CS.01", "CS.02", "PM.01", "PM.02"],
    
    # Creative Services
    "creative development": ["CR.01", "CR.02", "CR.03", "CR.04"],
    "creative production": ["CR.01", "CR.02", "CR.03", "CR.04", "CR.05"],
    "content creation": ["CO.01", "CO.02", "CO.03", "CO.04", "CO.05"],
    "social media content": ["CO.01", "CO.02", "CO.03", "CO.04"],
    "video production": ["CR.03", "CR.04", "CR.05", "CO.03"],
    
    # Digital Marketing
    "search engine marketing": ["PM.02", "PM.03", "PM.05"],
    "sem": ["PM.02", "PM.03", "PM.05"],
    "seo": ["CO.01", "CO.02", "CS.03"],
    "search engine optimization": ["CO.01", "CO.02", "CS.03"],
    "social media advertising": ["PM.01", "PM.02", "PM.03", "CO.02"],
    "programmatic advertising": ["PM.01", "PM.02", "PM.03", "PM.06"],
    "display advertising": ["PM.01", "PM.02", "PM.03", "CR.02"],
    
    # Reporting & Analytics
    "reporting": ["PM.04", "PM.05", "PM.06", "CS.04"],
    "analytics": ["PM.04", "PM.05", "PM.06", "CS.04"],
    "insights": ["CS.03", "CS.04", "PM.05", "PM.06"],
    "measurement": ["PM.04", "PM.05", "PM.06", "CS.04"],
    "optimization": ["PM.05", "PM.06", "CS.04"],
    
    # Integrated Services
    "brand strategy": ["CS.01", "CS.02", "CR.01"],
    "integrated marketing": ["IMM.01", "IMM.02", "IMM.03", "CS.01"],
    "channel planning": ["CS.02", "CS.03", "PM.01", "IMM.02"],
    "media optimization": ["PM.05", "PM.06", "CS.04"],
    
    # Technology Services
    "marketing technology": ["TECH.01", "TECH.02", "TECH.03"],
    "martech": ["TECH.01", "TECH.02", "TECH.03"],
    "data integration": ["TECH.02", "TECH.03", "PM.06"],
    "technical implementation": ["TECH.01", "TECH.02", "TECH.03"],
}

# Normalize mapping keys for case-insensitive matching
SERVICE_MAPPING_NORMALIZED = {k.lower(): v for k, v in SERVICE_MAPPING.items()}

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
    current_reasoning: str = ""  # NEW: AI thinking steps visible to user
    reasoning_history: List[str] = field(default_factory=list)  # Track all reasoning steps
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
def sanitize_for_json(text: str, max_length: int = 2000) -> str:
    """
    Sanitize text to prevent JSON parsing errors in LLM responses.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum length for LLM token limits (default 2000 chars for GPT-5 context window)
    
    NOTE: Truncation is REQUIRED to avoid exceeding LLM API token limits (128k context).
    For GPT-5 with many items, we must limit individual text fields.
    """
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
    # API TOKEN LIMIT: Must truncate to prevent exceeding context window
    # With 100+ items in a response, each field must be limited
    if len(text) > max_length:
        # Preserve complete words at boundaries
        truncated = text[:max_length].rsplit(' ', 1)[0] if ' ' in text[:max_length] else text[:max_length]
        return truncated.strip() + "..."
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

# Note: embed_many is imported from embedding_cache at the top of the file
# The embedding_cache module handles caching automatically

def gpt5_json_response(prompt: str, schema: dict, max_output_tokens: int = 16384) -> dict:
    """
    Use GPT-5 helper for JSON responses with schema - with retry logic.
    Only raises exceptions after all retries fail.
    """
    if not OPENAI_API_KEY:
        error_msg = "[GPT-5] No API key available - cannot process request"
        print(error_msg)
        raise Exception(error_msg)
    
    try:
        # Use the helper from gpt5_helpers - it handles model selection and enforcement
        tier = os.environ.get("AI_TIER", "thinking")  # Default to balanced tier
        
        # Create messages format from prompt
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        print(f"[GPT-5] Calling GPT-5 ({tier} tier) with retry logic enabled...")
        
        # gpt5_json_schema now includes retry logic by default
        result = gpt5_json_schema(
            client=oai,  # Use the global OpenAI client
            messages=messages,
            json_schema=schema,
            tier=tier,
            max_output_tokens=max_output_tokens,
            use_retry=True  # Enable retry logic with exponential backoff
        )
        
        # Skip the check for AI_MIN_DELIVERABLES here - this is for individual chunks, not the full response
        # The minimum deliverables check should be done after all chunks are combined
        if "items" in result:
            items = result.get("items", [])
            print(f"[GPT-5 SUCCESS] Received response with {len(items)} items")
        
        return result
    
    except Exception as e:
        # All retries have been exhausted at this point
        error_msg = f"GPT-5 failed after all retry attempts: {str(e)}"
        print(f"[GPT-5 FINAL ERROR] {error_msg}")
        print(f"[GPT-5 FALLBACK] System will now use embedding-based analysis as fallback")
        # Raise exception to trigger embedding fallback
        raise Exception(error_msg)

def chat_json_schema(messages: list, schema: dict, max_completion_tokens: int = 12288) -> dict:
    """Use simplified GPT-5 helper for JSON schema responses"""
    if not OPENAI_API_KEY:
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
    
    # Convert messages to a single prompt for the helper
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
    
    # Use the GPT-5 helper - sitecustomize will enforce GPT-5 automatically
    # FIXED: Use max_output_tokens parameter name to match gpt5_json_response signature
    return gpt5_json_response(prompt, schema, max_output_tokens=max_completion_tokens)

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
        # FIXED: Use correct column name 'Service_Department' with underscore
        service_dept = first_row.get('Service_Department', 'Strategy')
        if pd.isna(service_dept) or str(service_dept) == 'nan':
            service_dept = 'Strategy'
        service_dept = str(service_dept)
        
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
    # FIXED: Better department categorization
    if any(k in x for k in ["paid", "media", "analytics", "sem", "seo", "ppc", "display", "social ads"]): 
        return "Paid Media"
    if "integrated" in x or "imm" in x: 
        return "Integrated Marketing Management"
    if "strategy" in x or "strat" in x or "research" in x or "insights" in x: 
        return "Strategy"
    if any(k in x for k in ["creative", "design", "art", "visual"]): 
        return "Creative"
    if any(k in x for k in ["content", "copy", "editorial", "writing"]): 
        return "Content"
    if any(k in x for k in ["tech", "dev", "web", "technology", "engineering", "code", "software"]): 
        return "Technology"
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
    base_score = min(1.0, (overlap / max(4, len(tk_c))) + dept_hit)
    
    # FIXED: Add media/advertising keyword boosting
    media_keywords = {'media', 'campaign', 'brand', 'strategy', 'creative', 'digital', 
                     'social', 'analytics', 'reporting', 'planning', 'buying', 'activation',
                     'advertising', 'marketing', 'performance', 'programmatic', 'audience'}
    
    # Check if any media keywords are in the title or keywords
    title_words = set(tokenize(title.lower()))
    keyword_set = set([k.lower() for k in keywords]) if keywords else set()
    
    # NEW: Check for exact phrase matches from SERVICE_MAPPING_NORMALIZED
    text_lower = text.lower()
    title_lower = title.lower() if title else ""
    
    # Check for explicit service phrase matches
    exact_phrase_boost = 1.0
    for service_phrase in SERVICE_MAPPING_NORMALIZED.keys():
        # Check if the service phrase appears in the RFP text
        if service_phrase in text_lower:
            # Check if this deliverable title contains related keywords
            phrase_tokens = set(tokenize(service_phrase))
            if phrase_tokens & title_words:
                exact_phrase_boost = 2.0  # 2.0x boost for exact phrase matches
                break
    
    # Special handling for "Required Services" section
    if "required services" in text_lower or "specific services required" in text_lower:
        # If this deliverable is mentioned in required services section, boost it
        section_start = max(
            text_lower.find("required services"),
            text_lower.find("specific services required")
        )
        if section_start != -1:
            section_text = text_lower[section_start:section_start+1000]
            # Check if title keywords appear in this section
            if any(word in section_text for word in title_words):
                exact_phrase_boost = max(exact_phrase_boost, 1.8)  # At least 1.8x boost
    
    # Apply media keyword boost
    media_boost = 1.0
    if title_words & media_keywords or keyword_set & media_keywords:
        media_boost = 1.2  # 1.2x boost for media keywords
    
    # Apply all boosts
    final_score = min(1.0, base_score * media_boost * exact_phrase_boost)
    
    return final_score

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
def recall_candidates(request_text: str, catalog: List[Dict[str, Any]], client=None, mode: str = "deep", session_id: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not catalog:
        return [], []
    
    # FAST MODE: Skip embeddings entirely, use only lexical scoring
    if mode == "fast":
        cands = []
        for it in catalog:
            # Use lexical scoring only for speed
            lex = lexical_score(request_text, it["title"], it.get("desc", ""), it.get("keywords", []), it["dept"])
            # For fast mode, use lexical score as the recall score
            cands.append({**it, "embScore": 0, "lexScore": lex, "recall": lex})
        
        # Select top candidates based on lexical score only
        topD = sorted([x for x in cands if x["level"] == "deliverable"], key=lambda z: z["recall"], reverse=True)[:80]
        topC = sorted([x for x in cands if x["level"] == "component"], key=lambda z: z["recall"], reverse=True)[:120]
        topT = sorted([x for x in cands if x["level"] == "task"], key=lambda z: z["recall"], reverse=True)[:160]
        
        return topD + topC + topT, cands
    
    # DEEP MODE: Use embeddings + lexical for better accuracy
    texts = [f"{str(i.get('dept',''))} • {str(i.get('level',''))} • {str(i.get('title',''))} :: {str(i.get('desc',''))} :: {', '.join(str(k) for k in i.get('keywords',[]))}" for i in catalog]
    
    # Use cached embed_many with client and session_id for isolation
    embs = embed_many([request_text] + texts, client=client, session_id=session_id)
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
# Explicit Requirements Extraction for RFP Matching
# ──────────────────────────────────────────────────────────────────────────────
def extract_explicit_requirements(rfp_text: str) -> Dict[str, List[str]]:
    """
    Extract explicitly requested services from RFP text.
    Looks for sections like "Specific Services Required", "Required Services", 
    "Scope of Work", etc., and maps them to deliverable codes.
    
    Returns:
        Dict mapping deliverable codes to explicit requirement phrases
    """
    explicit_requirements = {}
    
    # Convert to lowercase for matching
    rfp_lower = rfp_text.lower()
    
    # Look for key sections that indicate required services
    required_sections = [
        "specific services required",
        "required services",
        "services required",
        "scope of work",
        "scope of services",
        "services requested",
        "deliverables",
        "key deliverables"
    ]
    
    # Find the section containing required services
    section_text = ""
    for section_marker in required_sections:
        marker_pos = rfp_lower.find(section_marker)
        if marker_pos != -1:
            # Extract text from this section (up to next major section or 1500 chars)
            end_pos = marker_pos + 1500
            next_section_pos = rfp_lower.find("\n\n", marker_pos + len(section_marker))
            if next_section_pos != -1 and next_section_pos < end_pos:
                end_pos = next_section_pos
            section_text = rfp_text[marker_pos:end_pos].lower()
            break
    
    # If we found a required services section, extract bullet points and match to deliverables
    if section_text:
        # Extract bullet points (various formats)
        import re
        bullets = []
        
        # Match different bullet formats
        patterns = [
            r'[•●▪▫◦‣⁃]\s*([^\n•●▪▫◦‣⁃]+)',  # Unicode bullets
            r'\d+\.\s*([^\n]+)',  # Numbered lists
            r'[-*]\s*([^\n]+)',  # Dash or asterisk bullets
            r'[a-z]\)\s*([^\n]+)',  # Letter bullets
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, section_text)
            bullets.extend([m.strip() for m in matches if m.strip()])
        
        # Also check the full RFP for these explicit phrases
        bullets.extend([
            phrase for phrase in SERVICE_MAPPING_NORMALIZED.keys()
            if phrase in rfp_lower
        ])
        
        # Map bullets to deliverable codes
        for bullet in bullets:
            bullet_lower = bullet.lower().strip()
            
            # Check each service mapping
            for service_phrase, deliv_codes in SERVICE_MAPPING_NORMALIZED.items():
                # Check if the service phrase appears in the bullet point
                if service_phrase in bullet_lower:
                    for code in deliv_codes:
                        if code not in explicit_requirements:
                            explicit_requirements[code] = []
                        explicit_requirements[code].append(bullet[:100])  # Store first 100 chars
        
        # Also do a direct phrase search in the entire RFP
        for service_phrase, deliv_codes in SERVICE_MAPPING_NORMALIZED.items():
            if service_phrase in rfp_lower:
                for code in deliv_codes:
                    if code not in explicit_requirements:
                        explicit_requirements[code] = []
                    # Add a note that this was found in the full text
                    explicit_requirements[code].append(f"[Found in RFP: {service_phrase}]")
    
    # Special case: Always check for exact phrase matches in the full RFP
    key_phrases_to_check = [
        "paid media buying", "paid media planning", "media buying", "media planning",
        "performance reporting", "analytics", "campaign measurement", "optimization",
        "campaign strategy", "audience strategy", "creative development", 
        "content creation", "social media", "search engine marketing", "sem", "seo"
    ]
    
    for phrase in key_phrases_to_check:
        if phrase in rfp_lower:
            if phrase in SERVICE_MAPPING_NORMALIZED:
                for code in SERVICE_MAPPING_NORMALIZED[phrase]:
                    if code not in explicit_requirements:
                        explicit_requirements[code] = []
                    explicit_requirements[code].append(f"[Explicit: {phrase}]")
    
    print(f"[EXPLICIT MATCH] Found {len(explicit_requirements)} explicitly requested deliverable codes")
    if explicit_requirements:
        print(f"[EXPLICIT MATCH] Sample matches: {list(explicit_requirements.keys())[:5]}")
    
    return explicit_requirements

# ──────────────────────────────────────────────────────────────────────────────
# Background Batch Analyzer for Job Runner
# ──────────────────────────────────────────────────────────────────────────────
async def analyze_one_batch(batch_data: List[Dict[str, Any]], tier: str = "thinking") -> Dict[str, Any]:
    """
    Analyze a single batch of candidates for the background job runner.
    This is the function that will be called by sitecustomize.py's job runner.
    
    Args:
        batch_data: List containing dicts with keys:
            - candidate: The candidate dict
            - request_text: The RFP text
            - summary: The analysis summary
        tier: Compute tier (mini/thinking/pro)
    
    Returns:
        Dict containing analyzed results for this batch
    """
    if not batch_data:
        return {"items": []}
    
    # Import here to avoid circular dependency
    from sitecustomize import agpt5_json_schema
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI()
    
    # First item contains the shared context
    first_item = batch_data[0]
    request_text = first_item.get("request_text", "")
    summary = first_item.get("summary", {})
    
    # Extract candidates from batch
    candidates = [item["candidate"] for item in batch_data]
    
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
                        "select": {"type": "boolean"}
                    },
                    "required": ["id", "dept", "level", "relevance", "confidence", "why", "risks", "select"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["items"],
        "additionalProperties": False
    }
    
    # Prepare payload with sanitized data
    payload = []
    for c in candidates:
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

IMPORTANT: Pay special attention to services that are EXPLICITLY REQUESTED in the RFP. 
If a service appears directly in a "Required Services" or "Scope of Work" section, it should receive a confidence score of 85-95%.

Score each deliverable/component/task with REALISTIC confidence scores:
- 85-95: Explicitly requested in RFP requirements (e.g., "Paid media buying" if RFP lists "Paid media buying & planning")
- 70-84: Very relevant, strongly recommended, adds significant value
- 50-69: Moderately relevant, nice-to-have, enhances project
- 30-49: Tangentially related, optional, limited value
- 0-29: Not relevant, would not recommend

Look for explicit mentions like:
- "Paid media buying" → Paid Media deliverables should score 85+%
- "Performance reporting" → Reporting deliverables should score 85+%
- "Campaign strategy" → Strategy deliverables should score 85+%
- "Analytics" → Analytics deliverables should score 85+%

For TASKS, set select=true ONLY if specifically needed for THIS project. Exclude generic/boilerplate tasks that don't match the specific request.
Think about the complete project lifecycle, dependencies, and what will actually deliver results for the client."""},
        {"role": "user", "content": f"REQUEST SUMMARY:\n{safe_summary}\n\nGOALS:\n- " + "\n- ".join(safe_goals) + f"\n\nCHANNELS: {', '.join(safe_channels)} | MARKETS: {', '.join(safe_markets)} | COMPLIANCE: {', '.join(safe_compliance)}\n\nCANDIDATES:\n{json.dumps(payload, indent=2)}\n\nIMPORTANT: If the RFP explicitly requests services like 'Paid media buying', 'Performance reporting', 'Campaign measurement', etc., mark those deliverables with confidence 85-95%. Check if the deliverable title contains keywords from the explicit requirements.\n\nProvide realistic confidence scores based on actual relevance. Each item should have a unique, justified confidence level."}
    ]
    
    try:
        # Use sitecustomize's helper for proper GPT-5 JSON response
        result = await agpt5_json_schema(client, messages, schema, tier=tier, max_output_tokens=16384)
        return result
    except Exception as e:
        print(f"[Batch Analysis Error] {e} - Using fallback scoring")
        # FIXED: Enhanced fallback scoring - always provide usable results
        fallback_items = []
        media_keywords = {'media', 'campaign', 'brand', 'strategy', 'creative', 'digital',
                         'social', 'analytics', 'reporting', 'planning', 'buying'}
        
        for c in candidates:
            # Calculate fallback confidence: 40% base + (50% * embedding/recall score)
            base_confidence = 0.4
            embedding_bonus = c.get("recall", 0.5) * 0.5
            fallback_confidence = min(0.9, base_confidence + embedding_bonus)
            
            # Apply media keyword boost
            title_words = set(tokenize(c.get("title", "").lower()))
            if title_words & media_keywords:
                fallback_confidence = min(0.95, fallback_confidence * 1.2)
            
            fallback_items.append({
                "id": c["id"],
                "dept": c["dept"],
                "level": c["level"],
                "relevance": min(100, fallback_confidence * 100),
                "confidence": fallback_confidence,
                "why": f"Embedding-based match (score: {c.get('recall', 0.5):.2f})",
                "risks": "GPT-5 unavailable - using embedding fallback",
                "select": fallback_confidence > 0.45  # Select if confidence > 45%
            })
        return {"items": fallback_items}

# ──────────────────────────────────────────────────────────────────────────────
# Evidence & LLM re-score with GRANULAR TASK SELECTION
# ──────────────────────────────────────────────────────────────────────────────
def best_evidence(request_text: str, candidate: Dict[str, Any], k: int = 3) -> List[str]:
    sents = sentence_split(request_text)
    scored = [(s, lexical_score(s, candidate["title"], candidate.get("desc", ""), candidate.get("keywords", []), candidate["dept"])) for s in sents]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s for s, score in scored[:k] if score > 0]

async def rescore_with_llm_granular_async(summary: Dict[str, Any], candidates: List[Dict[str, Any]], 
                                          request_text: str, tier: str = "thinking") -> List[Dict[str, Any]]:
    """
    New async LLM re-scoring using the sitecustomize job runner.
    This starts a background job and returns the results.
    """
    if not candidates:
        return []
    
    # Get the appropriate batch size based on tier - PERFORMANCE FIX: Reduced to prevent GPT-5 errors
    batch_sizes = {
        "mini": 20,  # Reduced from 50 to prevent insufficient items errors
        "thinking": 15,  # Optimal size for GPT-5 reliability
        "pro": 15,  # Increased from 10 to 15 for better efficiency
        "fast": 20,  # Reduced from 50 to prevent errors
        "balanced": 15,  # Optimal for balanced mode
        "accurate": 15  # Increased from 10 to 15 for better efficiency
    }
    batch_size = batch_sizes.get(tier, 15)
    
    # Prepare candidates for job runner
    batch_data = []
    for candidate in candidates:
        batch_data.append({
            "candidate": candidate,
            "request_text": request_text,
            "summary": summary
        })
    
    # Create batches
    import httpx
    
    # Call the job runner API
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Start the job
        response = await client.post(
            "http://localhost:5000/api/ai/analyze_job",
            json={
                "analyzer": "ai_planner_agencydb.analyze_one_batch",
                "candidates": batch_data,
                "tier": tier,
                "batch_size": batch_size
            }
        )
        response.raise_for_status()
        job_data = response.json()
        job_id = job_data["job_id"]
        
        # Poll for completion
        while True:
            status_resp = await client.get(f"http://localhost:5000/api/ai/jobs/{job_id}")
            status_resp.raise_for_status()
            status = status_resp.json()
            
            if status["status"] in ("done", "error", "timeout", "canceled"):
                if status["status"] == "done" and status["result"]:
                    # Flatten the results from all batches
                    all_items = []
                    for batch_result in status["result"]:
                        if isinstance(batch_result, dict) and "items" in batch_result:
                            all_items.extend(batch_result["items"])
                    return all_items
                else:
                    # Return empty list on error
                    print(f"[Job Runner Error] Job {job_id} failed with status: {status['status']}")
                    return []
            
            # Wait before polling again
            await asyncio.sleep(1.0)

def is_universal_deliverable(title: str) -> bool:
    """Check if a deliverable is universal (required for all projects)"""
    if not title:
        return False
    title_lower = title.lower()
    universal_patterns = [
        'project kickoff',
        'kickoff meeting',
        'status meeting',
        'weekly status',
        'project management',
        'project planning',
        'stakeholder meeting',
        'review meeting',
        'weekly check-in',
        'project setup',
        'team alignment',
        'project close',
        'final presentation'
    ]
    return any(pattern in title_lower for pattern in universal_patterns)

async def _process_single_chunk_async(block: List[Dict[str, Any]], chunk_num: int, total_chunks: int, summary: Dict[str, Any], 
                                      request_text: str, schema: dict, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Process a single chunk asynchronously for parallel processing"""
    # Sanitize all text in payload to prevent JSON parsing errors
    payload = []
    for c in block:
        evidence = best_evidence(request_text, c, 2)
        payload.append({
            "id": sanitize_for_json(c["id"]),
            "dept": c["dept"],
            "level": c["level"],
            "title": sanitize_for_json(c["title"])[:100],
            "desc": sanitize_for_json(c.get("desc", ""))[:100],
            "evidence": [sanitize_for_json(e)[:100] for e in evidence]
        })
    
    # Sanitize summary fields (keep shorter to save tokens)
    safe_summary = sanitize_for_json(summary.get('summary', ''))[:200]
    safe_goals = [sanitize_for_json(g)[:50] for g in summary.get("goals", [])][:3]
    safe_channels = [sanitize_for_json(c) for c in summary.get('channels', [])][:3]
    safe_markets = [sanitize_for_json(m) for m in summary.get('markets', [])][:3]
    safe_compliance = [sanitize_for_json(c) for c in summary.get('compliance', [])][:2]
    
    messages = [
        {"role": "system", "content": """Senior Agency Executive scoring deliverables.
Score 90-100: Essential
Score 70-89: Very relevant
Score 50-69: Moderately relevant
Score 30-49: Optional
Score 0-29: Not relevant
For TASKS, set select=true ONLY if specifically needed."""},
        {"role": "user", "content": f"SUMMARY:\n{safe_summary}\n\nGOALS:\n" + "\n".join(safe_goals) + f"\n\nCANDIDATES:\n{json.dumps(payload, indent=1)}\n\nScore each item."}
    ]
    
    try:
        # Use asyncio.to_thread for synchronous function call - increased tokens to prevent truncation
        r = await asyncio.to_thread(chat_json_schema, messages, schema, max_completion_tokens=8192)
        if r and r.get("items"):
            print(f"[LLM Re-score] Chunk {chunk_num}/{total_chunks} succeeded with {len(r.get('items', []))} items")
            # Boost universal deliverables to ensure they score high
            items = r.get("items", [])
            for item in items:
                for c in block:
                    if c["id"] == item.get("id") and c["level"] == "deliverable":
                        if is_universal_deliverable(c.get("title", "")):
                            # Universal deliverables should score 90-100%
                            item["relevance"] = max(item.get("relevance", 0), 92)
                            item["confidence"] = max(item.get("confidence", 0), 0.95)
                            item["select"] = True
                            item["why"] = "Universal deliverable - required for all projects"
                            print(f"[UNIVERSAL BOOST] {c['title']} boosted to 92% relevance")
            return items
        else:
            raise Exception("Empty response from GPT-5")
    except Exception as e:
        print(f"[LLM Re-score ERROR] Chunk {chunk_num}/{total_chunks} failed: {e} - Using aggressive fallback scoring")
        # Fallback scoring for this chunk
        out = []
        for c in block:
            # Check if this is a universal deliverable
            is_universal = c["level"] == "deliverable" and is_universal_deliverable(c.get("title", ""))
            
            if is_universal:
                # Universal deliverables get high scores automatically
                base_confidence = 0.95
                fallback_confidence = 0.95
                relevance_score = 95
                select_item = True
                why_text = "Universal deliverable - required for all projects"
            else:
                base_confidence = 0.55
                embedding_bonus = c.get("recall", 0.5) * 0.4
                fallback_confidence = min(0.95, base_confidence + embedding_bonus)
                relevance_score = int(fallback_confidence * 100)
                select_item = True if c["level"] == "deliverable" else fallback_confidence > 0.40
                why_text = f"Embedding match (score: {c.get('recall', 0.5):.2f}, boosted for media keywords)"
            
            # Apply media keyword boost only for non-universal items
            if not is_universal:
                media_keywords = {'media', 'campaign', 'brand', 'strategy', 'creative', 'digital',
                                 'social', 'analytics', 'reporting', 'planning', 'buying', 'advertising',
                                 'marketing', 'performance', 'programmatic', 'audience', 'content'}
                title_words = set(tokenize(c.get("title", "").lower()))
                keyword_set = set([k.lower() for k in c.get("keywords", [])]) if c.get("keywords") else set()
                
                if title_words & media_keywords or keyword_set & media_keywords:
                    fallback_confidence = min(0.95, fallback_confidence * 1.3)
                    relevance_score = min(100, fallback_confidence * 100)
            
            out.append({
                "id": c["id"],
                "dept": c["dept"],
                "level": c["level"],
                "relevance": relevance_score,
                "confidence": fallback_confidence,
                "why": why_text,
                "risks": "GPT-5 fallback" if not is_universal else "",
                "select": select_item
            })
        return out

def rescore_with_llm_granular(summary: Dict[str, Any], candidates: List[Dict[str, Any]], request_text: str, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """LLM re-scoring with GRANULAR task-level selection - PERFORMANCE FIX: Now uses PARALLEL processing"""
    if not candidates:
        print("[LLM Re-score] No candidates to score")
        return []
    
    # FIXED: If no OpenAI client, use pure embedding fallback immediately
    if not oai:
        print("[LLM Re-score] No OpenAI client available - using pure embedding fallback for all candidates")
        return _generate_embedding_fallback_scores(candidates, summary)
    
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
                        "select": {"type": "boolean"}
                    },
                    "required": ["id", "dept", "level", "relevance", "confidence", "why", "risks", "select"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["items"],
        "additionalProperties": False
    }
    
    # Use tier-based batch sizing - PERFORMANCE FIX: Reduced to prevent GPT-5 errors
    tier = os.environ.get("AI_TIER", "thinking")
    batch_sizes = {
        "mini": 18,  # Reduced from 40 to prevent insufficient items errors
        "thinking": 15,  # Increased from 8 for better efficiency
        "pro": 15,  # Increased from 5 for better parallel processing
        "fast": 18,  # Reduced from 40 to prevent errors
        "balanced": 15,  # Increased from 8 for better efficiency
        "accurate": 15  # Increased from 5 for better parallel processing
    }
    chunk_size = batch_sizes.get(tier, 15)
    
    # Prepare chunks for parallel processing
    chunks = []
    for i in range(0, len(candidates), chunk_size):
        block = candidates[i:i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        chunks.append((block, chunk_num))
    
    total_chunks = len(chunks)
    
    # Update job with total chunks if job_id provided
    if job_id and job_id in AI_JOB_STORE:
        AI_JOB_STORE[job_id].total_chunks = total_chunks
        AI_JOB_STORE[job_id].current_stage = f"Analyzing with GPT-5 in parallel (0/{total_chunks} chunks)"
    
    print(f"[LLM Re-score] Processing {total_chunks} chunks in PARALLEL with chunk_size={chunk_size}")
    
    # PERFORMANCE FIX: Run async event loop for parallel processing
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Create tasks for parallel processing
    async def run_parallel():
        tasks = []
        for block, chunk_num in chunks:
            # Create async task for each chunk
            task = _process_single_chunk_async(block, chunk_num, total_chunks, summary, request_text, schema, job_id)
            tasks.append(task)
        
        # PERFORMANCE FIX: Process all chunks in parallel
        print(f"[LLM Re-score] Starting parallel processing of {len(tasks)} chunks...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update job progress
        if job_id and job_id in AI_JOB_STORE:
            AI_JOB_STORE[job_id].processed_chunks = total_chunks
            AI_JOB_STORE[job_id].current_stage = f"Completed parallel analysis of {total_chunks} chunks"
        
        return results
    
    # Run the async parallel processing
    chunk_results = loop.run_until_complete(run_parallel())
    
    # Collect all results
    out = []
    failed_chunks = 0
    
    for result in chunk_results:
        if isinstance(result, Exception):
            failed_chunks += 1
            print(f"[LLM Re-score ERROR] Chunk failed with exception: {result}")
        elif isinstance(result, list):
            out.extend(result)
        else:
            failed_chunks += 1
            print(f"[LLM Re-score WARNING] Unexpected result type: {type(result)}")
    
    # FIXED: If too many chunks failed, ensure we have enough results
    if failed_chunks > total_chunks / 2:
        print(f"[LLM Re-score WARNING] {failed_chunks}/{total_chunks} chunks failed - supplementing with embedding fallback")
        # Supplement with pure embedding scores for any missing candidates
        scored_ids = {item["id"] for item in out}
        for c in candidates:
            if c["id"] not in scored_ids:
                base_confidence = 0.60  # Higher base for supplemental items
                embedding_bonus = c.get("recall", 0.5) * 0.35
                fallback_confidence = min(0.90, base_confidence + embedding_bonus)
                
                out.append({
                    "id": c["id"],
                    "dept": c["dept"],
                    "level": c["level"],
                    "relevance": min(100, fallback_confidence * 100),
                    "confidence": fallback_confidence,
                    "why": f"Supplemental embedding match (recall: {c.get('recall', 0.5):.2f})",
                    "risks": "Added via supplemental fallback",
                    "select": True if c["level"] == "deliverable" else fallback_confidence > 0.40
                })
    
    return out

def _generate_embedding_fallback_scores(candidates: List[Dict[str, Any]], summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate pure embedding-based fallback scores when GPT-5 is completely unavailable"""
    print(f"[EMBEDDING FALLBACK] Generating scores for {len(candidates)} candidates using pure embeddings")
    print(f"[USER NOTICE] ⚠️ GPT-5 is currently unavailable after multiple retry attempts.")
    print(f"[USER NOTICE] 📊 Using advanced embedding-based analysis as backup to provide recommendations.")
    print(f"[USER NOTICE] ℹ️ Results may be less contextually aware but still based on semantic similarity.")
    
    out = []
    media_keywords = {'media', 'campaign', 'brand', 'strategy', 'creative', 'digital',
                     'social', 'analytics', 'reporting', 'planning', 'buying', 'advertising',
                     'marketing', 'performance', 'programmatic', 'audience', 'content', 'activation'}
    
    for c in candidates:
        # High base confidence for pure embedding fallback
        base_confidence = 0.60
        embedding_score = c.get("recall", 0.5)
        
        # Combine base + embedding
        fallback_confidence = min(0.95, base_confidence + (embedding_score * 0.4))
        
        # Apply media keyword boost
        title_words = set(tokenize(c.get("title", "").lower()))
        keyword_set = set([k.lower() for k in c.get("keywords", [])]) if c.get("keywords") else set()
        
        boost_applied = False
        if title_words & media_keywords or keyword_set & media_keywords:
            fallback_confidence = min(0.95, fallback_confidence * 1.3)
            boost_applied = True
        
        # Deliverables get higher base confidence
        if c["level"] == "deliverable":
            fallback_confidence = max(0.70, fallback_confidence)
        
        out.append({
            "id": c["id"],
            "dept": c["dept"],
            "level": c["level"],
            "relevance": min(100, fallback_confidence * 100),
            "confidence": fallback_confidence,
            "why": f"Semantic similarity match (score: {embedding_score:.2f}){' with domain-specific boost' if boost_applied else ''}",
            "risks": "⚠️ Using embedding-based fallback (GPT-5 unavailable after retries)",
            "select": True if c["level"] == "deliverable" else fallback_confidence > 0.35  # Very low threshold for tasks
        })
    
    print(f"[EMBEDDING FALLBACK] Completed fallback scoring for {len(out)} candidates")
    return out

# [Continued in next message due to length...]
# ──────────────────────────────────────────────────────────────────────────────
# Fusion, calibration, AUTO-RELAX & RESCUE
# ──────────────────────────────────────────────────────────────────────────────
def fuse_and_calibrate(candidates: List[Dict[str, Any]], llm_scores: List[Dict[str, Any]], strictness: str = "balanced", 
                       explicit_requirements: Dict[str, List[str]] = None) -> List[Dict[str, Any]]:
    # FIXED: Handle case where GPT-5 completely failed
    if not llm_scores:
        print("[FUSION WARNING] No LLM scores available - using pure embedding-based fusion")
    
    lookup = {x["id"]: x for x in llm_scores} if llm_scores else {}
    
    # FIXED: Adjust weights when no LLM scores available
    if llm_scores:
        W = {"emb": 0.15, "lex": 0.10, "recall": 0.10, "llm": 0.55, "hist": 0.10}
    else:
        # No LLM scores - weight embeddings and lexical more heavily
        W = {"emb": 0.40, "lex": 0.25, "recall": 0.25, "llm": 0.0, "hist": 0.10}
    
    hist_prior = 0.65
    # FIXED: Balanced thresholds to filter out low-relevance items while keeping good ones
    gates = {"high": 0.35, "balanced": 0.30, "recall": 0.25}  # Reasonable gates to filter noise
    
    # FIXED: Expanded media agency keywords for better matching
    media_keywords = {'media', 'campaign', 'brand', 'strategy', 'creative', 'digital', 
                     'social', 'analytics', 'reporting', 'planning', 'buying', 'activation',
                     'advertising', 'marketing', 'performance', 'programmatic', 'audience',
                     'content', 'agency', 'production', 'design', 'video', 'paid', 'organic'}
    
    out = []
    for c in candidates:
        l = lookup.get(c["id"])
        llm_val = (l["relevance"] / 100.0) if l else 0.0
        llm_select = l.get("select", True) if l else True  # Default to True if no LLM score
        
        # NEW: Check for explicit match FIRST - this overrides all other scoring
        explicit_match = False
        explicit_reason = ""
        if explicit_requirements and c["level"] == "deliverable":
            # Extract deliverable code from ID (format: "PM.01" or similar)
            deliv_code = c["id"].split("::")[0] if "::" in c["id"] else c["id"]
            
            # Check if this deliverable code is in explicit requirements
            if deliv_code in explicit_requirements:
                explicit_match = True
                explicit_reason = explicit_requirements[deliv_code][0] if explicit_requirements[deliv_code] else "Explicitly requested in RFP"
                print(f"[EXPLICIT MATCH] {c['id']}: {explicit_reason}")
        
        # Check if this is a universal deliverable
        is_universal = c.get("level") == "deliverable" and is_universal_deliverable(c.get("title", ""))
        
        # If explicit match found, set high confidence immediately
        if explicit_match:
            raw = 0.90  # High raw score for explicit matches
            calibrated = 0.88  # 88% confidence for explicitly requested services
            pass_gate = True  # Always pass explicit matches
            llm_select = True  # Override LLM selection
            print(f"[EXPLICIT OVERRIDE] {c['id']}: Setting confidence to 88% (explicitly requested)")
        else:
            # Calculate raw fusion score for non-explicit matches
            if is_universal:
                # Universal deliverables get maximum score
                raw = 0.95
                llm_val = 0.95
                llm_select = True
            else:
                raw = W["emb"] * c.get("embScore", 0.5) + W["lex"] * c.get("lexScore", 0.5) + W["recall"] * c.get("recall", 0.5) + W["llm"] * llm_val + W["hist"] * hist_prior
            
            # FIXED: Apply more aggressive media keyword boost
            boost_factor = 1.0
            if c.get("title"):
                title_words = set(tokenize(c["title"].lower()))
                keyword_set = set([k.lower() for k in c.get("keywords", [])]) if c.get("keywords") else set()
                
                # Count keyword matches
                title_matches = len(title_words & media_keywords)
                keyword_matches = len(keyword_set & media_keywords)
                
                if title_matches > 0 or keyword_matches > 0:
                    # More matches = bigger boost
                    boost_factor = min(1.5, 1.2 + (title_matches + keyword_matches) * 0.05)
                    raw = min(1.0, raw * boost_factor)
                    print(f"[FUSION BOOST] {c['id']}: {title_matches} title matches, {keyword_matches} keyword matches, boost={boost_factor:.2f}")
            
            # FIXED: Even gentler calibration curve for 100+ deliverables
            calibrated = 1.0 / (1.0 + math.exp(-(1.5 * raw - 0.7)))  # Further adjusted to 1.5/0.7 for more permissive scoring
            
            # FIXED: For deliverables with no LLM score, boost confidence
            if c["level"] == "deliverable" and not l:
                calibrated = max(0.50, calibrated)  # Minimum 50% confidence for deliverables
                print(f"[FUSION RESCUE] Deliverable {c['id']} has no LLM score, boosted to {calibrated:.2f}")
            
            # For tasks: only pass if AI explicitly selected it OR if we have no LLM scores at all
            if c["level"] == "task" and llm_scores and not llm_select:
                pass_gate = False
            else:
                # Universal deliverables always pass
                pass_gate = is_universal or calibrated >= gates.get(strictness, gates["balanced"])
        
        # Log pass/fail decisions for debugging
        if c["level"] == "deliverable":
            status = "PASS" if pass_gate else "FAIL"
            match_status = " [EXPLICIT]" if explicit_match else ""
            print(f"[FUSION] {c['id']}: raw={raw:.3f}, calibrated={calibrated:.3f}, gate={gates.get(strictness, gates['balanced']):.3f} => {status}{match_status}")
        
        out.append({
            **c, 
            "llm": l, 
            "fused_score": raw, 
            "calibrated_confidence": calibrated, 
            "pass": pass_gate, 
            "ai_selected": llm_select,
            "boost_applied": boost_factor > 1.0 if not explicit_match else False,
            "explicit_match": explicit_match,
            "explicit_reason": explicit_reason
        })
    
    # Log summary
    passed_delivs = len([x for x in out if x["level"] == "deliverable" and x["pass"]])
    total_delivs = len([x for x in out if x["level"] == "deliverable"])
    print(f"[FUSION COMPLETE] {passed_delivs}/{total_delivs} deliverables passed (gate={gates.get(strictness, gates['balanced'])})")
    
    return out

def _auto_rescue_if_empty(fused: List[Dict[str, Any]], all_recall: List[Dict[str, Any]], llm_scores: List[Dict[str, Any]], rfp_complexity: str = "medium", summary: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """FIXED: Aggressively ensure minimum deliverables based on RFP complexity"""
    passed_delivs = [x for x in fused if x["level"] == "deliverable" and x["pass"]]
    
    # FIXED: Check if this is a comprehensive RFP
    is_comprehensive = False
    if summary:
        request_text = summary.get("summary", "").lower()
        is_comprehensive = (
            rfp_complexity == "high" or
            "luxury" in request_text or
            "fashion" in request_text or
            "comprehensive" in request_text or
            len(summary.get("markets", [])) > 2 or
            len(summary.get("channels", [])) > 3
        )
    
    # FIXED: Dynamic minimum based on RFP complexity - 100+ for comprehensive/luxury fashion RFPs
    complexity_minimums = {
        "low": 50,
        "medium": 75,
        "high": 100,
        "luxury_fashion": 100,  # Special case for luxury fashion RFPs
        "comprehensive": 100     # For comprehensive agency RFPs
    }
    
    # Use reasonable minimum deliverables based on RFP complexity
    # This prevents artificially inflating deliverable count with fake ones
    if is_comprehensive:
        MINIMUM_DELIVERABLES = 35  # Comprehensive RFPs get more deliverables
    elif rfp_complexity == "high":
        MINIMUM_DELIVERABLES = 30  # High complexity
    elif rfp_complexity == "medium":
        MINIMUM_DELIVERABLES = 20  # Medium complexity  
    else:
        MINIMUM_DELIVERABLES = 15  # Low complexity
    
    print(f"[AUTO-RESCUE] Using minimum of {MINIMUM_DELIVERABLES} deliverables for {rfp_complexity} complexity")
    
    # Override with environment variable if set (but cap at reasonable limit)
    env_min = int(os.environ.get("AI_FORCE_MIN_DELIVERABLES", "20"))
    if env_min > 0:
        MINIMUM_DELIVERABLES = min(50, env_min)  # Cap at 50 maximum to prevent bloat
        print(f"[AUTO-RESCUE] Using forced minimum from env: {MINIMUM_DELIVERABLES}")
    
    # FIXED: Always check and ensure minimum deliverables
    if len(passed_delivs) >= MINIMUM_DELIVERABLES:
        print(f"[AUTO-RESCUE] Already have {len(passed_delivs)} deliverables (>= {MINIMUM_DELIVERABLES} for complexity={rfp_complexity})")
        return fused  # Already have enough deliverables
    
    # Build maps
    by_id = {x["id"]: x for x in fused}
    llm_map = {x["id"]: x for x in llm_scores}
    recall_map = {x["id"]: x for x in all_recall}
    
    # FIXED: ALWAYS add deliverables to reach minimum, regardless of scores
    needed = MINIMUM_DELIVERABLES - len(passed_delivs)
    
    print(f"[AUTO-RESCUE TRIGGERED AGGRESSIVELY] Only {len(passed_delivs)} deliverables passed, FORCIBLY adding {needed} more to reach minimum of {MINIMUM_DELIVERABLES}")
    
    # Get ALL deliverables and rank them
    deliv_cands = [x for x in all_recall if x["level"] == "deliverable"]
    
    # Exclude already-passed deliverables
    passed_ids = {d["id"] for d in passed_delivs}
    unpassed_delivs = [d for d in deliv_cands if d["id"] not in passed_ids]
    
    # FIXED: Sort by embedding score (always available)
    # Don't care about LLM scores for rescue - just use embedding scores
    unpassed_delivs.sort(key=lambda x: x.get("recall", 0), reverse=True)
    
    print(f"[AUTO-RESCUE] Have {len(unpassed_delivs)} unpassed deliverables to choose from")
    
    # Take top N deliverables to reach minimum
    chosen_delivs = unpassed_delivs[:needed]
    print(f"[AUTO-RESCUE] Selected {len(chosen_delivs)} additional deliverables based on embedding scores")
    
    # Mark chosen deliverables as pass with BOOSTED SCORES to ensure they pass
    for d in chosen_delivs:
        llm_d = llm_map.get(d["id"])
        # FIXED: Boost confidence to ensure rescue deliverables are included
        # Use actual LLM confidence if available, else use boosted recall score
        if llm_d and llm_d.get("confidence", 0) > 0:
            actual_confidence = max(0.65, llm_d.get("confidence", 0.65))  # Minimum 65% confidence
        else:
            # FIXED: Boost embedding score to ensure it passes gates
            actual_confidence = max(0.65, min(0.95, d["recall"] * 1.5))  # Boost by 1.5x, min 65%, max 95%
        
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

def expand_deliverables_for_comprehensive_rfp(deliverables: List[Dict[str, Any]], summary: Dict[str, Any], target_count: int = 100) -> List[Dict[str, Any]]:
    """Expand deliverables for comprehensive RFPs by creating smart variations based on department and type"""
    
    # Get context from summary
    markets = summary.get("markets", ["US"])
    channels = summary.get("channels", ["Digital"])
    timeline_weeks = summary.get("timeline_weeks", 12)
    request_text = summary.get("summary", "").lower()
    
    # Enhanced detection of comprehensive RFP characteristics
    is_luxury = any(term in request_text for term in ['luxury', 'fashion', 'premium', 'haute', 'high-end', 'exclusive', 'couture', 'designer'])
    is_fashion = any(term in request_text for term in ['fashion', 'apparel', 'collection', 'seasonal', 'runway', 'style'])
    is_retail = any(term in request_text for term in ['retail', 'store', 'e-commerce', 'shop', 'boutique'])
    is_global = len(markets) > 1 or any(m.lower() in ['global', 'international', 'worldwide'] for m in markets) or 'global' in request_text
    is_multichannel = len(channels) > 2
    is_annual = timeline_weeks >= 40  # 10+ months indicates annual engagement
    is_multiyear = timeline_weeks >= 80 or 'multi-year' in request_text or 'annual' in request_text
    is_multiproduct = any(term in request_text for term in ['portfolio', 'multiple products', 'product line', 'collection', 'range'])
    is_comprehensive = summary.get("complexity") == "high" or is_luxury or is_global or is_annual or len(deliverables) < 70
    
    # Force expansion for luxury/comprehensive RFPs
    if not is_comprehensive and len(deliverables) >= target_count:
        return deliverables
        
    print(f"[EXPAND] Comprehensive/Luxury RFP detected - expanding {len(deliverables)} to {target_count}+ deliverables")
    print(f"[EXPAND] Context: luxury={is_luxury}, fashion={is_fashion}, global={is_global}, multichannel={is_multichannel}, annual={is_annual}, multiyear={is_multiyear}")
    
    # Enhanced phases (4 phases for comprehensive coverage)
    phases = ["Discovery", "Launch", "Growth", "Optimization"]
    
    # Enhanced regions - now includes Latin America and more
    if is_global:
        regions = ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East", "Africa"][:5]
    else:
        regions = markets[:3] if markets else ["US"]
    
    # Quarters and seasons for annual/fashion engagements
    quarters = ["Q1", "Q2", "Q3", "Q4"] if is_annual else []
    seasons = ["Spring", "Summer", "Fall", "Winter"] if is_fashion or is_retail else []
    
    # Fashion collections for luxury/fashion
    collections = ["Spring/Summer", "Fall/Winter", "Resort", "Pre-Fall"] if is_fashion or is_luxury else []
    
    # Audience segments for targeted marketing
    audience_segments = ["Gen Z", "Millennials", "Gen X", "Boomers", "Affluent", "Mass Market"] if is_comprehensive else []
    
    # Products for multi-product launches
    products = []
    if is_multiproduct:
        if is_fashion:
            products = ["Menswear", "Womenswear", "Accessories", "Footwear", "Bags"][:4]
        else:
            products = ["Product A", "Product B", "Product C", "Hero Product"][:3]
    
    # Enhanced channels - more specific and aggressive
    all_channels = ["Instagram", "Facebook", "TikTok", "YouTube", "LinkedIn", "Twitter", 
                    "Email", "SMS", "Web", "Mobile App", "Print", "TV", "Radio", "OOH", 
                    "Events", "Influencer", "Podcast", "Streaming"]
    
    if is_multichannel:
        # Aggressively expand channels
        expanded_channels = []
        for ch in channels[:8]:
            ch_lower = ch.lower()
            if 'digital' in ch_lower:
                expanded_channels.extend(["Web", "Mobile App", "Email", "SMS"])
            elif 'social' in ch_lower:
                expanded_channels.extend(["Instagram", "Facebook", "TikTok", "YouTube", "LinkedIn"])
            elif 'traditional' in ch_lower:
                expanded_channels.extend(["Print", "TV", "Radio", "OOH"])
            elif 'influencer' in ch_lower:
                expanded_channels.extend(["Instagram Influencers", "TikTok Creators", "YouTube Partners"])
            else:
                expanded_channels.append(ch)
        channels_to_use = list(set(expanded_channels))[:8]  # Unique channels, max 8 for aggressive expansion
    else:
        channels_to_use = channels[:4]
    
    # Platform variations for technology
    platforms = ["Web", "iOS", "Android", "Salesforce", "Adobe", "Shopify", "AWS", "Azure"][:5]
    
    # Annual/year variations for multi-year engagements
    years = []
    if is_multiyear:
        years = ["Year 1", "Year 2", "Year 3"][:3]
    
    # Track unique IDs to prevent duplicates
    seen_ids = set()
    expanded = []
    
    # Add all original deliverables first
    for d in deliverables:
        if d["id"] not in seen_ids:
            expanded.append(d)
            seen_ids.add(d["id"])
    
    # Sort deliverables by confidence/relevance for prioritization
    deliverables_sorted = sorted(deliverables, key=lambda x: x.get("calibrated_confidence", 0.5), reverse=True)
    
    # SMART EXPANSION RULES based on department
    expansion_count = 0
    max_expansions_per_deliverable = 12  # Increased limit for more aggressive expansion
    
    for d in deliverables_sorted:
        if len(expanded) >= target_count * 1.5:  # Increased to 150% to ensure we hit target
            break
            
        d_dept = d.get("dept", "Strategy")
        d_title = d.get("title", "").lower()
        base_confidence = d.get("calibrated_confidence", 0.6)
        expansions_for_this = 0
        
        # Strategy deliverables → Regional variations + Phases + Audience Segments
        if d_dept == "Strategy":
            # Regional variations if global (now more aggressive)
            if is_global:
                for region in regions[:4]:  # Increased from 3 to 4 regions
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-{region.replace(' ', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{d.get('title', '')} - {region}"
                        variant["calibrated_confidence"] = max(0.65, base_confidence * 0.95)  # Ensure minimum 0.65
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Phase variations for ALL strategy deliverables
            for phase in phases:  # All 4 phases for strategy
                if expansions_for_this >= max_expansions_per_deliverable:
                    break
                variant_id = f"{d['id']}-{phase}"
                if variant_id not in seen_ids:
                    variant = d.copy()
                    variant["id"] = variant_id
                    variant["title"] = f"{phase} Phase: {d.get('title', '')}"
                    variant["calibrated_confidence"] = max(0.62, base_confidence * 0.93)  # Ensure minimum
                    expanded.append(variant)
                    seen_ids.add(variant_id)
                    expansions_for_this += 1
                    expansion_count += 1
            
            # Add audience segment variations for targeted strategies
            if audience_segments and ('audience' in d_title or 'persona' in d_title or 'target' in d_title or 'segment' in d_title):
                for segment in audience_segments[:3]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-{segment.replace(' ', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{d.get('title', '')} - {segment}"
                        variant["calibrated_confidence"] = max(0.60, base_confidence * 0.92)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Add quarterly strategy reviews for annual engagements
            if is_annual and quarters:
                for quarter in quarters[:4]:  # All quarters for annual
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-Strategy-{quarter}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{quarter} Strategic Review: {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.58, base_confidence * 0.91)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Multi-year variations for long-term engagements
            if is_multiyear and years:
                for year in years[:2]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-{year.replace(' ', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{year} {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.56, base_confidence * 0.90)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
        
        # Creative deliverables → Channel-specific versions + Phases + Collections
        elif d_dept == "Creative":
            # Channel-specific versions (more aggressive)
            for channel in channels_to_use[:6]:  # Increased from 4 to 6
                if expansions_for_this >= max_expansions_per_deliverable:
                    break
                variant_id = f"{d['id']}-{channel.replace(' ', '_')}"
                if variant_id not in seen_ids:
                    variant = d.copy()
                    variant["id"] = variant_id
                    variant["title"] = f"{d.get('title', '')} - {channel}"
                    variant["calibrated_confidence"] = max(0.64, base_confidence * 0.94)  # Ensure minimum
                    expanded.append(variant)
                    seen_ids.add(variant_id)
                    expansions_for_this += 1
                    expansion_count += 1
            
            # Collection-specific variations for fashion/luxury
            if (is_fashion or is_luxury) and collections:
                for collection in collections[:3]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-{collection.replace('/', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{collection} Collection: {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.62, base_confidence * 0.93)  # Ensure minimum 0.62
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Seasonal variations for fashion/retail creative
            if (is_fashion or is_retail) and seasons:
                for season in seasons[:2]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-{season}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{season} {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.60, base_confidence * 0.92)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Add phase variations for creative campaigns
            if 'campaign' in d_title or 'concept' in d_title or True:  # Apply to all creative
                for phase in phases[:3]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-Creative-{phase}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{phase}: {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.58, base_confidence * 0.91)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Audience segment variations for creative targeting
            if audience_segments and ('campaign' in d_title or 'creative' in d_title):
                for segment in audience_segments[:2]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-Creative-{segment.replace(' ', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{d.get('title', '')} for {segment}"
                        variant["calibrated_confidence"] = max(0.56, base_confidence * 0.90)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
        
        # Content deliverables → Quarterly/Monthly variations + Channels + Products
        elif d_dept == "Content":
            # Quarterly variations for annual engagements (more aggressive)
            if is_annual and quarters:
                for quarter in quarters:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-{quarter}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{quarter} {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.62, base_confidence * 0.93)  # Ensure minimum 0.62
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Channel variations for content (more aggressive)
            for channel in channels_to_use[:5]:  # Increased from 3 to 5
                if expansions_for_this >= max_expansions_per_deliverable:
                    break
                variant_id = f"{d['id']}-Content-{channel.replace(' ', '_')}"
                if variant_id not in seen_ids:
                    variant = d.copy()
                    variant["id"] = variant_id
                    variant["title"] = f"{d.get('title', '')} for {channel}"
                    variant["calibrated_confidence"] = base_confidence * 0.92
                    expanded.append(variant)
                    seen_ids.add(variant_id)
                    expansions_for_this += 1
                    expansion_count += 1
            
            # Product-specific content for multi-product launches
            if products and is_multiproduct:
                for product in products[:2]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-{product.replace(' ', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{d.get('title', '')} - {product}"
                        variant["calibrated_confidence"] = max(0.58, base_confidence * 0.91)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Seasonal content for fashion/retail
            if (is_fashion or is_retail) and seasons:
                for season in seasons[:2]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-Content-{season}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{season} {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.56, base_confidence * 0.90)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Audience-specific content
            if audience_segments and ('content' in d_title or 'story' in d_title or 'editorial' in d_title):
                for segment in audience_segments[:2]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-Content-{segment.replace(' ', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{d.get('title', '')} for {segment}"
                        variant["calibrated_confidence"] = max(0.54, base_confidence * 0.89)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
        
        # Technology deliverables → Platform-specific versions
        elif d_dept == "Technology":
            # Platform-specific variations
            for platform in platforms[:3]:
                if expansions_for_this >= max_expansions_per_deliverable:
                    break
                variant_id = f"{d['id']}-{platform}"
                if variant_id not in seen_ids:
                    variant = d.copy()
                    variant["id"] = variant_id
                    variant["title"] = f"{d.get('title', '')} - {platform} Platform"
                    variant["calibrated_confidence"] = max(0.58, base_confidence * 0.91)  # Ensure minimum
                    expanded.append(variant)
                    seen_ids.add(variant_id)
                    expansions_for_this += 1
                    expansion_count += 1
            
            # Phase variations for tech development
            for phase in ["Development", "Testing", "Deployment"]:
                if expansions_for_this >= max_expansions_per_deliverable:
                    break
                variant_id = f"{d['id']}-Tech-{phase}"
                if variant_id not in seen_ids:
                    variant = d.copy()
                    variant["id"] = variant_id
                    variant["title"] = f"{phase}: {d.get('title', '')}"
                    variant["calibrated_confidence"] = max(0.56, base_confidence * 0.90)  # Ensure minimum
                    expanded.append(variant)
                    seen_ids.add(variant_id)
                    expansions_for_this += 1
                    expansion_count += 1
        
        # Paid Media deliverables → Channel + Region combinations + Audience segments
        elif d_dept == "Paid Media":
            # Channel-specific media buying (more aggressive)
            media_channels = ["Google Ads", "Facebook Ads", "Instagram Ads", "LinkedIn", 
                            "Programmatic", "YouTube", "TikTok Ads", "Amazon Ads", "Spotify Ads"]
            for channel in media_channels[:5]:  # Increased from 3 to 5
                if expansions_for_this >= max_expansions_per_deliverable:
                    break
                variant_id = f"{d['id']}-{channel.replace(' ', '_')}"
                if variant_id not in seen_ids:
                    variant = d.copy()
                    variant["id"] = variant_id
                    variant["title"] = f"{d.get('title', '')} - {channel}"
                    variant["calibrated_confidence"] = max(0.64, base_confidence * 0.94)  # Ensure minimum
                    expanded.append(variant)
                    seen_ids.add(variant_id)
                    expansions_for_this += 1
                    expansion_count += 1
            
            # Regional media variations if global (more aggressive)
            if is_global:
                for region in regions[:4]:  # Increased from 2 to 4
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-Media-{region.replace(' ', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{d.get('title', '')} - {region}"
                        variant["calibrated_confidence"] = max(0.60, base_confidence * 0.92)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Audience segment targeting for paid media
            if audience_segments:
                for segment in audience_segments[:3]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-Media-{segment.replace(' ', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{d.get('title', '')} targeting {segment}"
                        variant["calibrated_confidence"] = max(0.58, base_confidence * 0.91)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Product-specific media campaigns
            if products and is_multiproduct:
                for product in products[:2]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-Media-{product.replace(' ', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{d.get('title', '')} for {product}"
                        variant["calibrated_confidence"] = max(0.56, base_confidence * 0.90)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Quarterly media plans for annual
            if is_annual and quarters:
                for quarter in quarters[:4]:  # All quarters for annual
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-Media-{quarter}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{quarter} {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.54, base_confidence * 0.89)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
            
            # Seasonal campaigns for fashion/retail
            if (is_fashion or is_retail) and seasons:
                for season in seasons[:2]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-Media-{season}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{season} Media {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.52, base_confidence * 0.88)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
        
        # Integrated Marketing Management → All phases for coordination
        elif d_dept == "Integrated Marketing Management":
            # All 4 phases for IMM deliverables
            for phase in phases:
                if expansions_for_this >= max_expansions_per_deliverable:
                    break
                variant_id = f"{d['id']}-IMM-{phase}"
                if variant_id not in seen_ids:
                    variant = d.copy()
                    variant["id"] = variant_id
                    variant["title"] = f"{phase}: {d.get('title', '')}"
                    variant["calibrated_confidence"] = max(0.62, base_confidence * 0.93)  # Ensure minimum
                    expanded.append(variant)
                    seen_ids.add(variant_id)
                    expansions_for_this += 1
                    expansion_count += 1
            
            # Add quarterly reviews for annual
            if is_annual and quarters:
                for quarter in quarters[:2]:
                    if expansions_for_this >= max_expansions_per_deliverable:
                        break
                    variant_id = f"{d['id']}-IMM-{quarter}-Review"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{quarter} Review: {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.56, base_confidence * 0.90)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansions_for_this += 1
                        expansion_count += 1
    
    # Additional aggressive expansion if still below target
    if len(expanded) < target_count:
        remaining_needed = target_count - len(expanded)
        print(f"[EXPAND] Still need {remaining_needed} more deliverables, adding aggressive variations")
        
        # Add cross-department variations for top deliverables
        for d in deliverables_sorted[:40]:  # Increased from 20 to 40 for more aggressive expansion
            if len(expanded) >= target_count * 1.2:  # Go up to 120 deliverables to ensure we hit 100+
                break
                
            base_confidence = d.get("calibrated_confidence", 0.6)
            d_title = d.get("title", "").lower()
            
            # Add lifecycle variations
            lifecycle = ["Planning", "Execution", "Optimization", "Reporting", "Analysis", "Review"]
            for stage in lifecycle[:4]:
                variant_id = f"{d['id']}-{stage}"
                if variant_id not in seen_ids:
                    variant = d.copy()
                    variant["id"] = variant_id
                    variant["title"] = f"{stage}: {d.get('title', '')}"
                    variant["calibrated_confidence"] = max(0.52, base_confidence * 0.88)  # Ensure minimum
                    expanded.append(variant)
                    seen_ids.add(variant_id)
                    expansion_count += 1
                    if len(expanded) >= target_count * 1.2:
                        break
            
            # Add format variations for deliverables that make sense
            if any(term in d_title for term in ['report', 'analysis', 'audit', 'assessment']):
                formats = ["Executive Summary", "Detailed Report", "Dashboard View", "Presentation"]
                for format_type in formats[:2]:
                    variant_id = f"{d['id']}-{format_type.replace(' ', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{d.get('title', '')} - {format_type}"
                        variant["calibrated_confidence"] = max(0.50, base_confidence * 0.87)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansion_count += 1
                        if len(expanded) >= target_count * 1.2:
                            break
            
            # Add stakeholder variations for strategy/planning deliverables
            if any(term in d_title for term in ['strategy', 'plan', 'roadmap', 'framework']):
                stakeholders = ["Executive", "Board", "Investor", "Partner"]
                for stakeholder in stakeholders[:2]:
                    variant_id = f"{d['id']}-{stakeholder}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{stakeholder} {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.48, base_confidence * 0.86)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansion_count += 1
                        if len(expanded) >= target_count * 1.2:
                            break
            
            # Add testing/validation variations for campaigns and creative
            if any(term in d_title for term in ['campaign', 'creative', 'content', 'ad']):
                testing_types = ["A/B Test", "Pilot", "Beta", "Full Launch"]
                for test_type in testing_types[:2]:
                    variant_id = f"{d['id']}-{test_type.replace(' ', '_').replace('/', '_')}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{test_type}: {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.46, base_confidence * 0.85)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansion_count += 1
                        if len(expanded) >= target_count * 1.2:
                            break
    
    # Final catch-all expansion if STILL below target (rare but possible)
    if len(expanded) < target_count:
        print(f"[EXPAND] Final push: need {target_count - len(expanded)} more")
        # Add department-phase combinations for all departments
        for dept in DEPARTMENTS:
            if len(expanded) >= target_count:
                break
            dept_delivs = [d for d in deliverables_sorted if d.get("dept") == dept][:5]
            for d in dept_delivs:
                for phase in ["Kickoff", "Mid-point", "Final"]:
                    variant_id = f"{d['id']}-{dept}-{phase}"
                    if variant_id not in seen_ids:
                        variant = d.copy()
                        variant["id"] = variant_id
                        variant["title"] = f"{phase} {d.get('title', '')}"
                        variant["calibrated_confidence"] = max(0.44, d.get("calibrated_confidence", 0.6) * 0.84)  # Ensure minimum
                        expanded.append(variant)
                        seen_ids.add(variant_id)
                        expansion_count += 1
                        if len(expanded) >= target_count:
                            break
    
    print(f"[EXPAND] Expansion complete: {len(deliverables)} → {len(expanded)} deliverables")
    print(f"[EXPAND] Added {expansion_count} smart variations based on department rules")
    print(f"[EXPAND] Total unique deliverables: {len(seen_ids)}")
    
    return expanded

def compose_plan_from_agencydb(fused: List[Dict[str, Any]], summary: Dict[str, Any], catalog: List[Dict[str, Any]], db, all_recall: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compose plan using real AgencyDB deliverable codes and structure"""
    passing = [x for x in fused if x["pass"]]
    dels = [x for x in passing if x["level"] == "deliverable"]
    comps_pass = {x["id"]: x for x in passing if x["level"] == "component"}
    tasks_pass = {x["id"]: x for x in passing if x["level"] == "task" and x.get("ai_selected", True)}  # Only AI-selected tasks
    
    # If still nothing after auto-rescue, hard fallback
    if not dels:
        print("[COMPOSE] No deliverables after rescue - using hard fallback")
        topD = [x for x in all_recall if x["level"] == "deliverable"]
        topD.sort(key=lambda z: z["recall"], reverse=True)
        # Take all available deliverables
        dels = topD[:len(topD)]  # Take all available
        print(f"[COMPOSE] Hard fallback: selected {len(dels)} deliverables")
    
    # Expansion now happens in analyze_with_agencydb BEFORE filtering
    # No need to expand here anymore since it's done earlier in the pipeline
    
    by_dept: Dict[str, List[Dict[str, Any]]] = {}
    m = multipliers_from_summary(summary)
    
    # Build deliverable lookup from catalog
    deliv_lookup = {x["id"]: x for x in catalog if x["level"] == "deliverable"}
    
    print(f"[COMPOSE DEBUG] Processing {len(dels)} deliverables")
    print(f"[COMPOSE DEBUG] Deliverable lookup has {len(deliv_lookup)} items")
    
    for d_item in dels:
        deliv_code = d_item["id"]
        deliv_info = deliv_lookup.get(deliv_code, None)
        
        if deliv_info is None:
            # Skip deliverables not in the database catalog (these are fake IDs)
            print(f"[COMPOSE] Skipping unknown deliverable {deliv_code} - not in database catalog")
            continue  # Skip this deliverable entirely instead of creating a fallback
        
        # FIXED: Ensure dept exists with fallback to 'Strategy'
        dept = deliv_info.get("dept", "Strategy")  # Use .get() for safe access
        
        # Validate department and fallback to Strategy if invalid
        if dept not in DEPARTMENTS:
            print(f"[COMPOSE] Deliverable {deliv_code} has invalid/missing dept '{dept}', using Strategy")
            dept = "Strategy"  # Always use Strategy as fallback
        
        by_dept.setdefault(dept, [])
        
        try:
            # Get deliverable base hours from DB
            deliv_rows = db.all_rows[db.all_rows['Deliverable_Code'] == deliv_code]
            d_hours = deliv_rows['Estimated_Hours'].sum() if not deliv_rows.empty else 8.0
            d_hours_planned = planned_hours(d_hours, m)
        except Exception as e:
            print(f"[COMPOSE ERROR] Error getting hours for {deliv_code}: {e}")
            d_hours = 8.0
            d_hours_planned = 8.0
        
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
        
        # FIXED: Ensure title exists with fallback
        deliv_title = deliv_info.get("title", f"Deliverable {deliv_code}")
        
        # Add deliverable to department
        deliverable_entry = {
            "code": deliv_code,  # Real database code (renamed from deliverable_code)
            "name": deliv_title,  # Frontend expects 'name' not 'deliverable_title'
            "title": deliv_title,  # Keep for backward compatibility
            "confidence": d_item.get("calibrated_confidence", 0.60),  # Renamed from calibrated_confidence
            "deliverable_code": deliv_code,  # Keep old field for backward compatibility
            "deliverable_title": deliv_title,  # Keep old field for backward compatibility
            "calibrated_confidence": d_item.get("calibrated_confidence", 0.60),  # Keep old field for backward compatibility
            "why": (d_item.get("llm") or {}).get("why", ""),
            "risks": (d_item.get("llm") or {}).get("risks", ""),
            "planned_hours": d_hours_planned,
            "components": comp_out,
            "milestones": milestones
        }
        by_dept[dept].append(deliverable_entry)
        print(f"[COMPOSE] Added {deliv_code} to {dept} department (total in dept: {len(by_dept[dept])})")
    
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
def _update_job(job_id: str, stage: str, progress_pct: int = None, total_chunks: int = None, processed_chunks: int = None, reasoning: str = ""):
    """Helper to update job progress with granular tracking and AI reasoning visibility"""
    if job_id and job_id in AI_JOB_STORE:
        job = AI_JOB_STORE[job_id]
        job.current_stage = stage
        if total_chunks is not None:
            job.total_chunks = total_chunks
        if processed_chunks is not None:
            job.processed_chunks = processed_chunks
        # Calculate progress from chunks if not explicitly set
        if progress_pct is None and job.total_chunks > 0:
            progress_pct = int((job.processed_chunks / job.total_chunks) * 100)
        
        # NEW: Add reasoning visibility for users
        if reasoning:
            job.current_reasoning = reasoning
            job.reasoning_history.append(f"[{stage}] {reasoning}")
            print(f"[JOB {job_id}] {stage} (progress: {progress_pct}%) - AI Thinking: {reasoning}")
        else:
            print(f"[JOB {job_id}] {stage} (progress: {progress_pct}%)")

def analyze_with_agencydb(request_text: str, db, strictness: str = None, job_id: Optional[str] = None, tier: str = None, mode: str = "deep", client=None, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Main analysis function using AgencyDB with Fast/Deep mode support and session isolation
    
    Args:
        request_text: The RFP or project request text
        db: AgencyDB instance
        strictness: Filter strictness level
        job_id: Background job ID for progress tracking
        tier: GPT-5 tier (mini/thinking/pro)
        mode: 'fast' for lexical-only (no LLM), 'deep' for full LLM re-ranking
        client: HTTP client for API calls (uses app.state.http if available)
        session_id: Optional session ID for cache isolation
    """
    strictness = strictness or AI_STRICTNESS_DEFAULT
    # PERFORMANCE FIX: Fast mode always uses "mini" tier for speed
    if mode == "fast":
        tier = "mini"
    else:
        tier = tier or "thinking"
    mode = mode or "deep"
    
    print(f"[ANALYZE START] Mode: {mode}, Request length: {len(request_text)}, strictness: {strictness}, tier: {tier}")
    
    # Update job status - Stage 1
    _update_job(job_id, "Stage 1/7: Loading database catalog...", 10, 
                reasoning="Accessing AgencyDB with 1,900+ deliverables, components, and tasks across 6 departments")
    
    # Build catalog from AgencyDB
    catalog = build_catalog_from_agencydb(db)
    
    if not catalog:
        error_result = {
            "auto_run": True,
            "message": "No deliverables found in database.",
            "plan": {"summary": {}, "suggestions_by_department": {}},
            "diagnostics": {"candidates_considered": 0, "catalog_items": 0, "error": "empty_catalog", "mode": mode}
        }
        print(f"[ANALYZE ERROR] Empty catalog")
        return error_result
    
    print(f"[ANALYZE] Built catalog with {len(catalog)} items from AgencyDB")
    deliverable_count = len([x for x in catalog if x["level"] == "deliverable"])
    print(f"[ANALYZE] Catalog contains {deliverable_count} deliverables")
    
    _update_job(job_id, "Stage 1/7: Database loaded", 15,
                reasoning=f"Found {deliverable_count} deliverables across Strategy, Creative, Content, Paid Media, Technology, and IMM departments")
    
    # Stage 2: Summarize request (skip for Fast mode to save time)
    if mode == "deep":
        _update_job(job_id, "Stage 2/7: Summarizing request with GPT-5...", 20,
                    reasoning="Using GPT-5 to extract: business goals, target channels, markets, compliance requirements, and project complexity")
        try:
            summary = summarize_request(request_text)
            print(f"[ANALYZE] Summary generated successfully")
            
            # Extract key insights for reasoning
            goals_count = len(summary.get("goals", []))
            channels = summary.get("channels", [])
            markets = summary.get("markets", [])
            complexity = summary.get("complexity", "medium")
            
            _update_job(job_id, "Stage 2/7: RFP analyzed", 25,
                        reasoning=f"Identified {goals_count} business goals, {len(channels)} channels ({', '.join(channels[:3])}{'...' if len(channels) > 3 else ''}), {len(markets)} market(s). Complexity: {complexity}")
        except Exception as e:
            print(f"[ANALYZE WARNING] Summary failed: {e}, using default summary")
            summary = {
                "summary": request_text[:500],
                "goals": ["Provide comprehensive services"],
                "channels": ["Digital", "Social", "Traditional"],
                "markets": ["US"],
                "compliance": [],
                "languages": ["English"],
                "timeline_weeks": 12,
                "budget_tier": "moderate",
                "complexity": "medium",
                "risk_flags": []
            }
            _update_job(job_id, "Stage 2/7: Using fallback summary", 25,
                        reasoning="GPT-5 summarization failed - using keyword extraction for basic analysis")
    else:
        # Fast mode: Skip GPT-5 summarization
        _update_job(job_id, "Stage 2/7: Fast mode - skipping summarization...", 20,
                    reasoning="Fast mode active - using keyword-based analysis instead of full GPT-5 summarization for speed")
        summary = {
            "summary": request_text[:500],
            "goals": ["Fast analysis"],
            "channels": ["Digital"],
            "markets": ["US"],
            "compliance": [],
            "languages": ["English"],
            "timeline_weeks": 8,
            "budget_tier": "moderate",
            "complexity": "medium",
            "risk_flags": []
        }
    
    # Stage 3: Compute embeddings and find candidates (skip embeddings for Fast mode)
    if mode == 'fast':
        _update_job(job_id, f"Stage 3/7: Finding candidates with keywords...", 30,
                    reasoning="Using TF-IDF keyword matching to rapidly identify relevant deliverables without AI embeddings")
    else:
        _update_job(job_id, f"Stage 3/7: Computing embeddings and similarity scores...", 30,
                    reasoning=f"Generating semantic embeddings for RFP and {len(catalog)} catalog items to find deep pattern matches")
    
    # Pass mode to skip embeddings in Fast mode
    candidates, all_recall = recall_candidates(request_text, catalog, client=client or oai, mode=mode, session_id=session_id)
    
    if not candidates:
        # FIXED: If no candidates, use entire catalog as fallback
        print(f"[ANALYZE WARNING] No candidates from recall, using entire catalog")
        candidates = catalog[:270]  # Top 270 items
        all_recall = catalog
    
    print(f"[ANALYZE] Found {len(candidates)} candidates")
    
    deliv_candidates_count = len([c for c in candidates if c["level"] == "deliverable"])
    _update_job(job_id, f"Stage 3/7: Candidate matching complete", 35,
                reasoning=f"Matched {deliv_candidates_count} relevant deliverables from semantic analysis - now filtering to top matches")
    
    # Stage 4: Fast vs Deep mode divergence
    if mode == "fast":
        # FAST MODE: No LLM calls, use TF-IDF/lexical scoring only
        _update_job(job_id, "Stage 4/7: Fast mode - scoring with TF-IDF only...", 50,
                    reasoning=f"Fast Mode: Statistically scoring {deliv_candidates_count} deliverables using keyword frequency analysis (no AI)")
        
        # Filter to top FAST_TOP_K deliverables based on lexical+embedding scores
        deliverable_candidates = [c for c in candidates if c["level"] == "deliverable"]
        deliverable_candidates.sort(key=lambda x: x.get("recall", 0), reverse=True)
        top_deliverables = deliverable_candidates[:FAST_TOP_K]
        
        # Generate fake LLM scores for compatibility with fusion logic
        llm_scores = []
        for c in top_deliverables:
            # Use lexical and embedding scores to generate confidence
            confidence = min(95, int(c.get("recall", 0.5) * 100))
            llm_scores.append({
                "id": c["id"],
                "level": c["level"],
                "confidence": confidence,
                "relevance": confidence,
                "select": True,
                "why": f"Selected based on TF-IDF similarity (score: {c.get('recall', 0):.2f})"
            })
        
        # Add components and tasks for selected deliverables
        for deliv in top_deliverables:
            # Get components for this deliverable
            components = [c for c in candidates if c["level"] == "component" and c.get("parentId") == deliv["id"]]
            components.sort(key=lambda x: x.get("recall", 0), reverse=True)
            
            for comp in components[:3]:  # Top 3 components per deliverable
                llm_scores.append({
                    "id": comp["id"],
                    "level": comp["level"],
                    "confidence": min(90, int(comp.get("recall", 0.4) * 100)),
                    "relevance": min(90, int(comp.get("recall", 0.4) * 100)),
                    "select": True,
                    "why": "Component selected by TF-IDF similarity"
                })
                
                # Get tasks for this component
                tasks = [t for t in candidates if t["level"] == "task" and t.get("parentId") == comp["id"]]
                tasks.sort(key=lambda x: x.get("recall", 0), reverse=True)
                
                for task in tasks[:2]:  # Top 2 tasks per component
                    llm_scores.append({
                        "id": task["id"],
                        "level": task["level"],
                        "confidence": min(85, int(task.get("recall", 0.3) * 100)),
                        "relevance": min(85, int(task.get("recall", 0.3) * 100)),
                        "select": True,
                        "why": "Task selected by TF-IDF similarity"
                    })
        
        print(f"[ANALYZE FAST] Generated {len(llm_scores)} scores without LLM")
        
    else:
        # DEEP MODE: Use LLM for intelligent re-ranking
        _update_job(job_id, "Stage 4/7: Deep mode - pre-filtering candidates...", 40,
                    reasoning=f"Deep Mode: Preparing top {DEEP_TOP_K} deliverables for GPT-5 Thinking analysis with deep reasoning")
        
        # Pre-filter to DEEP_TOP_K candidates for LLM scoring
        deliverable_candidates = [c for c in candidates if c["level"] == "deliverable"]
        deliverable_candidates.sort(key=lambda x: x.get("recall", 0), reverse=True)
        top_deliverables = deliverable_candidates[:DEEP_TOP_K]
        
        # Build focused candidate set for LLM
        llm_candidates = []
        for deliv in top_deliverables:
            llm_candidates.append(deliv)
            # Add components and tasks for this deliverable
            components = [c for c in candidates if c["level"] == "component" and c.get("parentId") == deliv["id"]]
            for comp in components[:5]:  # Up to 5 components per deliverable
                llm_candidates.append(comp)
                tasks = [t for t in candidates if t["level"] == "task" and t.get("parentId") == comp["id"]]
                llm_candidates.extend(tasks[:3])  # Up to 3 tasks per component
        
        _update_job(job_id, "Stage 5/7: Deep mode - scoring with GPT-5...", 50,
                    reasoning=f"Sending {len(llm_candidates)} items to GPT-5 Thinking for advanced context-aware relevance analysis")
        
        # Wrap LLM scoring in try/except with guaranteed fallback
        try:
            llm_scores = rescore_with_llm_granular(summary, llm_candidates, request_text, job_id)
            print(f"[ANALYZE DEEP] LLM scoring completed, {len(llm_scores)} scores generated")
            
            # Check if we got enough deliverables from LLM
            llm_delivs = [s for s in llm_scores if s["level"] == "deliverable"]
            print(f"[ANALYZE DEEP] LLM returned {len(llm_delivs)} deliverable scores")
            
            if len(llm_delivs) < AI_MIN_DELIVERABLES:
                print(f"[ANALYZE WARNING] LLM returned only {len(llm_delivs)} deliverables, less than minimum {AI_MIN_DELIVERABLES}")
                print(f"[ANALYZE] Rescue function WILL be triggered to ensure minimum deliverables")
                
        except Exception as e:
            print(f"[ANALYZE ERROR] LLM scoring failed: {e}")
            print(f"[ANALYZE] Falling back to lexical scores")
            # Generate fallback scores
            llm_scores = _generate_embedding_fallback_scores(llm_candidates, summary)
            print(f"[ANALYZE] Using fallback scores for {len(llm_scores)} candidates")
    
    # Stage 6: Calibrate and fuse scores
    _update_job(job_id, "Stage 6/7: Calibrating scores and selecting deliverables...", 70,
                reasoning="Combining AI reasoning with statistical analysis to calibrate confidence scores and select final deliverables")
    
    # NEW: Extract explicit requirements from RFP before fusion
    explicit_requirements = extract_explicit_requirements(request_text)
    if explicit_requirements:
        print(f"[ANALYZE] Extracted {len(explicit_requirements)} explicitly requested deliverables from RFP")
    else:
        print(f"[ANALYZE] No explicit requirements found in RFP")
    
    # FIXED: Ensure fusion always happens - now with explicit requirements
    try:
        fused = fuse_and_calibrate(candidates, llm_scores, strictness, explicit_requirements)
        print(f"[ANALYZE] Fusion completed, {len(fused)} items fused")
    except Exception as e:
        print(f"[ANALYZE ERROR] Fusion failed: {e}, using candidates directly")
        # Emergency fallback - mark all deliverables as passed
        fused = []
        for c in candidates:
            if c["level"] == "deliverable":
                c["pass"] = True
                c["calibrated_confidence"] = 0.65
                c["ai_selected"] = True
                fused.append(c)
    
    # AUTO-RELAX & RESCUE - ALWAYS run this
    # Detect luxury fashion or comprehensive RFPs  
    request_lower = request_text.lower()
    is_luxury_fashion = any(term in request_lower for term in ['luxury', 'fashion', 'haute couture', 'premium brand', 'designer'])
    is_comprehensive = any(term in request_lower for term in ['comprehensive', 'full-service', 'integrated', 'complete agency', 'all marketing'])
    
    if is_luxury_fashion:
        rfp_complexity = "luxury_fashion"
    elif is_comprehensive or summary.get("complexity") == "high":
        rfp_complexity = "comprehensive"
    else:
        rfp_complexity = summary.get("complexity", "medium")
    
    print(f"[ANALYZE] Running auto-rescue (autorelax={AI_AUTORELAX}, complexity={rfp_complexity})")
    fused = _auto_rescue_if_empty(fused, all_recall, llm_scores, rfp_complexity, summary)
    
    # EXPANSION FOR COMPREHENSIVE RFPs - DISABLED
    # We no longer artificially expand deliverables with fake variations
    # Only use the actual deliverables from the database
    is_comprehensive_rfp = (
        summary.get("complexity") == "high" or
        is_luxury_fashion or
        is_comprehensive or
        len(summary.get("markets", [])) > 2 or
        len(summary.get("channels", [])) > 3
    )
    
    if is_comprehensive_rfp:
        # Get deliverables that passed so far
        passing_delivs = [x for x in fused if x["level"] == "deliverable" and x["pass"]]
        print(f"[ANALYZE] Comprehensive RFP detected with {len(passing_delivs)} deliverables (no artificial expansion)")
    
    # Check final deliverable count
    final_delivs = [x for x in fused if x["level"] == "deliverable" and x["pass"]]
    print(f"[ANALYZE] After rescue and expansion: {len(final_delivs)} deliverables will be included")
    
    # Stage 7: Compose final plan
    _update_job(job_id, "Stage 7/7: Building final project plan...", 90,
                reasoning=f"Assembling final project plan with {len([f for f in fused if f.get('pass')])} approved deliverables and their components")
    
    # FIXED: Ensure plan composition always succeeds
    try:
        plan = compose_plan_from_agencydb(fused, summary, catalog, db, all_recall)
        print(f"[ANALYZE] Plan composed successfully")
    except Exception as e:
        print(f"[ANALYZE ERROR] Plan composition failed: {e}, using emergency plan")
        # Emergency plan - just return top deliverables
        emergency_delivs = [x for x in fused if x["level"] == "deliverable" and x["pass"]][:25]
        plan = {
            "summary": summary,
            "strictness": strictness,
            "totals": {"planned_hours_total": len(emergency_delivs) * 40},
            "suggestions_by_department": {
                "Strategy": [{
                    "code": d["id"],
                    "name": d.get("title", "Deliverable"),
                    "title": d.get("title", "Deliverable"),
                    "confidence": d.get("calibrated_confidence", 0.60),
                    "deliverable_code": d["id"],
                    "deliverable_title": d.get("title", "Deliverable"),
                    "calibrated_confidence": d.get("calibrated_confidence", 0.60),
                    "why": "Selected based on embedding similarity",
                    "risks": "Emergency fallback plan",
                    "planned_hours": 40,
                    "components": [],
                    "milestones": []
                } for d in emergency_delivs]
            }
        }
    
    # Count final results
    delivs_in_plan = sum(len(dept_items) for dept_items in plan.get("suggestions_by_department", {}).values())
    
    # Mark job complete
    _update_job(job_id, "Complete!", 100)
    
    result = {
        "auto_run": True,
        "message": f"AI analysis complete ({mode} mode). Selected {delivs_in_plan} deliverables.",
        "plan": plan,
        "diagnostics": {
            "mode": mode,
            "candidates_considered": len(candidates),
            "catalog_items": len(catalog),
            "deliverables_selected": len(final_delivs),
            "deliverables_in_plan": delivs_in_plan,
            "tasks_ai_selected": len([x for x in fused if x["level"] == "task" and x.get("ai_selected", False) and x["pass"]]),
            "rescue_triggered": len(final_delivs) >= 25,
            "llm_scores_available": len(llm_scores) > 0,
            "fast_top_k": FAST_TOP_K if mode == "fast" else None,
            "deep_top_k": DEEP_TOP_K if mode == "deep" else None
        }
    }
    
    # Log cache stats
    try:
        cache_stats = get_cache_stats()
        print(f"[CACHE STATS] {cache_stats}")
    except Exception:
        pass
    
    print(f"[ANALYZE COMPLETE] Mode: {mode}, Deliverables: {delivs_in_plan}, Time: {datetime.datetime.now().timestamp() - (AI_JOB_STORE[job_id].start_time if job_id and job_id in AI_JOB_STORE else datetime.datetime.now().timestamp()):.1f}s")
    return result

def _run_analysis_background(job_id: str, request_text: str, db, strictness: str = None, tier: str = None, mode: str = "deep", client=None, session_id: Optional[str] = None, pdf_files: List[dict] = None):
    """Background task to run AI analysis with Fast/Deep mode support, session isolation, and PDF processing"""
    try:
        # If we have PDF files and Deep mode, send them to GPT-5 Vision
        if pdf_files and mode == "deep":
            print(f"[ANALYZE] Processing {len(pdf_files)} PDF files with GPT-5 Vision")
            # TODO: Implement GPT-5 Vision API call with PDF files
            # For now, use text fallback
            
        result = analyze_with_agencydb(request_text, db, strictness, job_id, tier, mode, client, session_id)
        
        if job_id in AI_JOB_STORE:
            # FIXED: Save result BEFORE marking as completed
            AI_JOB_STORE[job_id].result = result
            AI_JOB_STORE[job_id].end_time = datetime.datetime.now().timestamp()
            AI_JOB_STORE[job_id].current_stage = "Complete"
            
            # Log deliverables count for debugging
            delivs_count = 0
            if result and "plan" in result:
                delivs_by_dept = result["plan"].get("suggestions_by_department", {})  # FIXED: Use correct key name
                for dept_delivs in delivs_by_dept.values():
                    delivs_count += len(dept_delivs)
            print(f"[AI JOB {job_id}] Saved {delivs_count} deliverables to job result")
            
            # FIXED: Mark as completed ONLY AFTER saving result
            AI_JOB_STORE[job_id].status = AIJobStatus.COMPLETED
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
    tier: Optional[str] = None  # 'mini', 'thinking', 'pro'
    mode: Optional[str] = "deep"  # 'fast' or 'deep'
    session_id: Optional[str] = None  # Session ID for cache isolation
    upload_session_id: Optional[str] = None  # Upload session for PDF files

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
            
            # Handle uploaded PDF files if session provided
            rfp_content = payload.request_text
            pdf_files = []
            
            if payload.upload_session_id:
                # Import here to avoid circular dependencies
                from main import UPLOADED_PDF_FILES
                
                if payload.upload_session_id in UPLOADED_PDF_FILES:
                    pdf_files = UPLOADED_PDF_FILES[payload.upload_session_id]
                    print(f"[ANALYZE] Found {len(pdf_files)} uploaded PDF files for session {payload.upload_session_id}")
                    
                    # For GPT-5 Vision, we'll send the PDFs directly
                    # Use text as fallback if no PDFs or for Fast Mode
                    if not rfp_content or rfp_content == "PDF files uploaded":
                        # Try to use extracted text from PDFs as fallback
                        text_parts = []
                        for f in pdf_files:
                            if 'text' in f:
                                text_parts.append(f['text'])
                        if text_parts:
                            rfp_content = "\n\n".join(text_parts)
                        else:
                            rfp_content = "PDF files uploaded for analysis"
            
            # Create job
            job_id = str(uuid.uuid4())
            AI_JOB_STORE[job_id] = AIAnalysisJob(
                job_id=job_id,
                status=AIJobStatus.PENDING
            )
            
            # Start background task with mode, client, and session_id for isolation
            # FIXED: Pass None instead of app.state.http for embedding client
            # embed_many will create its own OpenAI client
            background_tasks.add_task(
                _run_analysis_background,
                job_id,
                rfp_content,
                db,
                payload.strictness,
                payload.tier,
                payload.mode or "deep",
                None,  # Pass None - embed_many will create its own OpenAI client
                payload.session_id,  # Pass session_id for cache isolation
                pdf_files  # Pass PDF files for GPT-5 Vision processing
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
    
    @router.get("/jobs/{job_id}")
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
        
        # DEBUG: Check if result is actually there
        if job.status == AIJobStatus.COMPLETED:
            print(f"[DEBUG] Job {job_id} is completed, has result: {job.result is not None}")
            if job.result:
                print(f"[DEBUG] Result keys: {list(job.result.keys()) if isinstance(job.result, dict) else 'Not a dict'}")
                response["result"] = job.result
            else:
                print(f"[DEBUG] Job result is None!")
        
        if job.status == AIJobStatus.FAILED and job.error:
            response["error"] = job.error
        
        return response
    
    @router.get("/jobs/{job_id}/result")
    def _result(job_id: str):
        """Get result of completed AI analysis job"""
        if job_id not in AI_JOB_STORE:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = AI_JOB_STORE[job_id]
        if job.status != AIJobStatus.COMPLETED:
            raise HTTPException(status_code=400, detail=f"Job not completed yet, status: {job.status.value}")
        
        return job.result
    
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
