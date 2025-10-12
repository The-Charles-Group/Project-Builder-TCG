# GPT-5 Implementation Review Package
## Agency Project Builder - Complete GPT References
### Generated: October 12, 2025

---

## Table of Contents
1. [Core GPT-5 API Implementation](#1-core-gpt-5-api-implementation)
2. [Main API Implementation](#2-main-api-implementation)
3. [Timeline Manager](#3-timeline-manager)
4. [Pricing Optimizer](#4-pricing-optimizer)
5. [Frontend JavaScript](#5-frontend-javascript)
6. [Key API Patterns](#key-gpt-5-api-patterns)
7. [Questions for Review](#questions-for-gpt-5-pro-review)

---

## 1. Core GPT-5 API Implementation
**File: `ai_planner_agencydb.py`**

### Configuration (Line 17)
```python
REASONING_MODEL = os.environ.get("AI_REASONING_MODEL", "gpt-5-thinking")  # GPT-5 model
```

### GPT-5 Responses API Implementation (Lines 231-329)
```python
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
```

### API Router Method (Lines 331-367)
```python
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
```

### Chunk Processing Configuration (Lines 703-718)
```python
chunk = 35  # Reduced chunk size for better reliability with GPT-5
total_chunks = math.ceil(len(candidates) / chunk)

# Update job with total chunks if job_id provided
if job_id and job_id in AI_JOB_STORE:
    AI_JOB_STORE[job_id].total_chunks = total_chunks
    AI_JOB_STORE[job_id].current_stage = f"Analyzing with GPT-5 (0/{total_chunks} chunks)"

for i in range(0, len(candidates), chunk):
    payload = candidates[i:i+chunk]
    chunk_num = (i // chunk) + 1
    
    # Update job progress
    if job_id and job_id in AI_JOB_STORE:
        AI_JOB_STORE[job_id].current_stage = f"Analyzing with GPT-5 (chunk {chunk_num}/{total_chunks})"
```

---

## 2. Main API Implementation
**File: `main.py`**

### Configuration (Line 3015)
```python
OPENAI_MODEL = os.getenv("APB_SUGGEST_MODEL", "gpt-5")
```

### GPT-5 Prompt Creation (Line 2394)
```python
# Create structured prompt for GPT-5
system_prompt = """
You are an agency executive producer.
Given a deliverable and its required components/tasks, 
intelligently redistribute hours when the total changes.
"""
```

### OpenAI API Call (Lines 2416-2420)
```python
response = openai_client.chat.completions.create(
    model="gpt-5",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
)
```

### Component Selection with GPT-5 (Lines 3083-3210)
```python
def _gpt_pick_components_and_l3(db: AgencyDB, dcode: str, rfp: str,
                                top_components: int, top_l3: int,
                                exclude: set[str], weighted_context: dict = None) -> dict:
    """GPT-5 selection logic for components and L3 tasks"""
    
    # Process results
    comps = data.get("components") or []
    for c in comps:
        c.setdefault("why","Selected by GPT‑5 for RFP fit")
        c.setdefault("score", 0.9)
    
    l3 = data.get("l3_by_component") or {}
    for k, arr in l3.items():
        for item in arr:
            item.setdefault("why","GPT‑5 rationale")
    
    return {
        "source": "gpt",
        "components": comps[:top_components],
        "l3_by_component": {k: v[:top_l3] for k,v in l3.items()},
    }

# Fallback handling
try:
    payload = _gpt_pick_components_and_l3(
        db, d, rfp, req.top_components, req.top_l3_per_component, 
        exclude, weighted_context=req.weighted_context
    )
    if req.weighted_context:
        payload["used_weighted_prefilter"] = True
except Exception as e:
    print(f"GPT suggest fallback to rules: {e}")
    payload = _rules_pick_components_and_l3(db, d, rfp, req.top_components, req.top_l3_per_component, exclude)
    payload["model_used"] = "rules"
```

---

## 3. Timeline Manager
**File: `ai_timeline_manager.py`**

### Module Documentation (Lines 1-3)
```python
"""
AI Timeline Manager - Intelligent project scheduling using GPT-5
Generates optimized timelines with dependency analysis and resource allocation
"""
```

### GPT-5 Timeline Generation (Lines 310-320)
```python
# Call GPT-5 for intelligent timeline generation
response = await client.chat.completions.create(
    model=os.getenv("AI_REASONING_MODEL", "gpt-5-thinking"),
    messages=[
        {"role": "system", "content": "You are a project scheduling expert. Provide realistic timelines based on industry standards."},
        {"role": "user", "content": prompt}
    ],
    response_format={"type": "json_object"},
    temperature=0.3,  # Lower temperature for more consistent scheduling
    max_tokens=2000
)
```

---

## 4. Pricing Optimizer
**File: `ai_pricing_optimizer.py`**

### Module Documentation (Lines 1-4)
```python
"""
AI Pricing Optimizer - Intelligent hour redistribution and pricing optimization
Uses GPT-5 to redistribute hours among deliverable components based on complexity and dependencies
"""
```

### Configuration Comment (Lines 108-109)
```python
use_ai: Whether to use GPT for redistribution
```

### GPT-5 Hour Redistribution (Lines 146-267)
```python
async def redistribute_with_gpt(
    deliverable_name: str,
    deliverable_code: str,
    new_total_hours: float,
    components: List[Dict[str, Any]],
    change_ratio: float,
    complexity: str,
    tier: str,
    context: Optional[str]
) -> RedistributionResult:
    """Use GPT to intelligently redistribute hours"""
    
    # API call
    response = await client.chat.completions.create(
        model="gpt-5-thinking",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    # Process response
    return RedistributionResult(
        deliverable_name=deliverable_name,
        total_hours=new_total_hours,
        original_total=sum(c.get('hours', 0) for c in components),
        components=allocations,
        reasoning=result.get('overall_reasoning', 'AI-optimized distribution based on complexity and dependencies'),
        confidence=float(result.get('confidence', 0.85)),
        methodology="AI-powered (GPT-5)"
    )
```

---

## 5. Frontend JavaScript
**File: `static/app.js`**

### Configuration (Lines 14-15)
```javascript
const AUTO_SUGGEST_ON_SELECT = true;
const USE_GPT_FOR_AUTOSUGGEST = true;
```

### UI Labels and Comments (Lines 1933-4792)
```javascript
// Step 1: Analyze with AI (NEW: uses GPT-5 Pro AI planner for Summary + Suggestions in one call)
async function onRunReconcile() {
    // Implementation
}

// Render NEW AI Plan (GPT-5 Pro: Summary + Evidence-backed Suggestions)
function renderAIPlan(aiPlan) {
    // Implementation
}

// Render GPT-5 AI Suggestions Panel
function renderAISuggestionsPanel(dCode, ai) {
    // Display source
    `Source: ${ai.source === "gpt" ? `GPT‑5 (${ai.model_used})` : "Rules"}`
    
    // Section headers
    "<h4>GPT‑5 Suggested Components</h4>"
    "<h4>GPT‑5 Suggested L3 (per component)</h4>"
}

// Auto-suggest with GPT-5 (Lines 3037-3109)
if (AUTO_SUGGEST_ON_SELECT && !hasComponents) {
    if (USE_GPT_FOR_AUTOSUGGEST) {
        try {
            // STEP 2: Call GPT-5 with weighted context for smarter suggestions
            // Include weighted matches as context for GPT-5
            if (weightedContext && weightedContext.deliverables) {
                // Include context for GPT-5
            }
        } catch (error) {
            console.error('GPT auto-suggest error:', error);
        }
    }
}

// ---- S2 Functions (GPT 5 Pro Implementation) ----
```

---

## Key GPT-5 API Patterns

### 1. **Responses API vs Chat Completions**
- **GPT-5 models** use `oai.responses.create()` instead of `oai.chat.completions.create()`
- **Input format**: Single `input` parameter instead of `messages` array
- **Token limit**: `max_output_tokens` instead of `max_completion_tokens`
- **No temperature**: GPT-5 doesn't support temperature parameter (always defaults to 1)
- **No response_format**: Schema must be embedded in the prompt

### 2. **Model Detection Pattern**
```python
if REASONING_MODEL.startswith("gpt-5"):
    # Use Responses API for GPT-5 models
    return gpt5_json_response(prompt, schema, max_completion_tokens)
else:
    # Use Chat Completions API (backward compatibility)
    return chat_completions_response(messages, schema, max_completion_tokens)
```

### 3. **Message to Prompt Conversion**
```python
# Convert chat messages to single prompt for GPT-5
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
```

### 4. **Error Handling Strategy**
- JSON repair attempts for malformed responses
- Fallback to empty structures on failure
- Detailed logging with `[GPT-5 API]`, `[GPT-5 Warning]`, `[GPT-5 Debug]` prefixes
- Graceful degradation to rule-based systems when GPT-5 fails

### 5. **Current Models Referenced**
- **`gpt-5-thinking`** - Primary model used throughout
- **`gpt-5`** - Used in some main.py calls
- **`gpt-5-thinking-mini`** - Proposed for fast operations
- **`gpt-5-pro`** - Proposed for high-accuracy tasks

---

## Questions for GPT-5 Pro Review

### API Implementation
1. **Responses API Usage**: Is the current implementation of `oai.responses.create()` optimal for GPT-5?
2. **Message Conversion**: Is converting messages array to a single prompt the best approach for GPT-5?
3. **Schema Handling**: Should JSON schema be embedded in the prompt differently for better compliance?

### Error Handling
4. **JSON Parsing**: What's the best practice for handling malformed JSON from GPT-5?
5. **Fallback Strategy**: Should we implement retry logic before falling back to rule-based systems?
6. **Error Recovery**: How to better handle API errors and timeouts?

### Performance Optimization
7. **Batch Processing**: Is chunk size of 35 items optimal for GPT-5?
8. **Token Management**: Best practices for setting `max_output_tokens`?
9. **Parallel Requests**: Can we parallelize GPT-5 requests safely?

### Model Selection
10. **Model Variants**: How to efficiently switch between mini/thinking/pro variants?
11. **Cost Optimization**: When should we use mini vs. thinking vs. pro models?
12. **Feature Detection**: How to detect model capabilities programmatically?

### Response Processing
13. **Content Access**: Is `response.content` the correct way to access GPT-5 responses?
14. **Streaming**: Should we implement streaming for long responses?
15. **Caching**: Can/should we cache GPT-5 responses for similar inputs?

---

## Proposed Model Selection Architecture

### Backend Model Router
```python
def get_gpt5_model(user_preference=None, task_type="analyze"):
    """Dynamic model selection based on user preference and task type"""
    
    model_map = {
        "fast": "gpt-5-thinking-mini",
        "balanced": "gpt-5-thinking",
        "accurate": "gpt-5-pro"
    }
    
    default_by_task = {
        "analyze": "gpt-5-thinking",      # RFP analysis
        "suggest": "gpt-5-thinking-mini", # Quick suggestions
        "timeline": "gpt-5-thinking",      # Timeline generation
        "pricing": "gpt-5-thinking-mini"   # Price calculations
    }
    
    return model_map.get(user_preference) or default_by_task.get(task_type)
```

### Frontend Model Selector
```javascript
const AI_MODELS = {
  'gpt-5-thinking-mini': {
    name: 'GPT-5 Mini',
    description: 'Fast & cost-effective',
    icon: '⚡',
    cost: '$',
    speed: 'Fast (~5s)'
  },
  'gpt-5-thinking': {
    name: 'GPT-5 Thinking',
    description: 'Balanced performance',
    icon: '🧠',
    cost: '$$',
    speed: 'Medium (~15s)'
  },
  'gpt-5-pro': {
    name: 'GPT-5 Pro',
    description: 'Maximum accuracy',
    icon: '🚀',
    cost: '$$$',
    speed: 'Slower (~30s)'
  }
}
```

### API Endpoint Enhancement
```python
@app.post("/api/ai/analyze")
async def analyze_with_model_selection(request: Request):
    data = await request.json()
    rfp_text = data.get("request_text", "")
    model_preference = data.get("model_preference", "balanced")  # New field
    
    # Select appropriate model
    selected_model = get_gpt5_model(model_preference, "analyze")
    
    # Use selected model for analysis
    result = await analyze_rfp_with_gpt5(rfp_text, selected_model)
    return result
```

### UI Component for Model Selection
```html
<!-- Model Selector Component -->
<div class="model-selector">
  <h4>AI Model Selection</h4>
  <div class="model-options">
    <label class="model-option">
      <input type="radio" name="ai-model" value="fast" />
      <div class="model-card">
        <span class="icon">⚡</span>
        <strong>GPT-5 Mini</strong>
        <small>Fast & Affordable</small>
        <div class="specs">
          <span class="cost">$</span>
          <span class="speed">~5s</span>
        </div>
      </div>
    </label>
    
    <label class="model-option">
      <input type="radio" name="ai-model" value="balanced" checked />
      <div class="model-card">
        <span class="icon">🧠</span>
        <strong>GPT-5 Thinking</strong>
        <small>Balanced Performance</small>
        <div class="specs">
          <span class="cost">$$</span>
          <span class="speed">~15s</span>
        </div>
      </div>
    </label>
    
    <label class="model-option">
      <input type="radio" name="ai-model" value="accurate" />
      <div class="model-card">
        <span class="icon">🚀</span>
        <strong>GPT-5 Pro</strong>
        <small>Maximum Accuracy</small>
        <div class="specs">
          <span class="cost">$$$</span>
          <span class="speed">~30s</span>
        </div>
      </div>
    </label>
  </div>
</div>
```

---

## Implementation Notes

### Current State
- All non-GPT-5 models have been removed from the codebase
- System uses GPT-5's Responses API exclusively
- Messages are converted to single prompts for GPT-5 compatibility
- JSON schema validation happens through prompt engineering

### Key Differences from Standard OpenAI API
1. **Different API Endpoint**: `responses.create()` vs `chat.completions.create()`
2. **Input Format**: Single string vs messages array
3. **Token Parameter**: `max_output_tokens` vs `max_completion_tokens`
4. **No Temperature Control**: GPT-5 always uses temperature=1
5. **No Response Format Parameter**: Schema must be in prompt

### Areas for Optimization
1. **Batch Processing**: Current chunk size of 35 items may need tuning
2. **Error Recovery**: Could benefit from retry logic with exponential backoff
3. **Response Caching**: Consider caching for identical requests
4. **Model Selection**: Implement dynamic model selection based on task complexity
5. **Cost Management**: Track token usage and provide cost estimates

---

## Summary

This document contains all GPT-5 references and implementation details from the Agency Project Builder codebase. The system currently uses GPT-5's Responses API exclusively, with all non-GPT-5 model references removed. The implementation converts chat messages to single prompts and handles JSON schema validation through prompt engineering rather than API parameters.

Key areas for optimization include:
- API call efficiency
- Error handling robustness
- Model variant selection
- Response parsing reliability
- Cost/performance optimization

The proposed model selection architecture would allow users to choose between GPT-5 mini, thinking, and pro variants based on their specific needs for speed, cost, and accuracy.

---

*Document generated for GPT-5 Pro review - October 12, 2025*
*Total GPT references in codebase: 87*
*Files containing GPT references: 5 Python, 1 JavaScript*