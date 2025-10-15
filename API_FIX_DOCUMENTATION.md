# API Endpoints - Correct Usage Documentation

## Issue Summary and Resolution

All three API endpoints that were failing have been successfully fixed and tested. The issues were related to incorrect parameter names and missing required fields.

## 1. RFP Analysis Endpoint

**Endpoint:** `POST /api/ai/analyze`

### ❌ Incorrect Usage (Causes 422 Error):
```json
{
  "text": "RFP content here"  // WRONG field name
}
```

### ✅ Correct Usage:
```json
{
  "request_text": "We need a comprehensive digital marketing campaign including social media strategy, content creation, and SEO optimization.",
  "mode": "fast",           // Optional: "fast" or "deep"
  "tier": "mini",           // Optional: "mini", "thinking", or "pro"
  "strictness": "balanced", // Optional
  "session_id": "abc123"    // Optional: for cache isolation
}
```

**Required Fields:**
- `request_text` (string) - The RFP or project request text

**Response:** Returns a job ID for asynchronous processing. Poll `/api/ai/jobs/{job_id}` for results.

---

## 2. L3 For Endpoint

**Endpoint:** `GET /api/l3_for`

### ❌ Incorrect Usage (Causes 422 Error):
```
GET /api/l3_for?deliverable=website&component=design  // WRONG parameter names
```

### ✅ Correct Usage:
```
GET /api/l3_for?deliverable_code=website&component_name=design
```

**Required Query Parameters:**
- `deliverable_code` (string) - The deliverable code
- `component_name` (string) - The component name

**Response:**
```json
{
  "items": [
    {"Task_Label": "wireframes"},
    {"Task_Label": "mockups"},
    {"Task_Label": "prototypes"}
  ]
}
```

---

## 3. Pricing Optimization Endpoint

**Endpoint:** `POST /api/ai/optimize_pricing`

### ❌ Incorrect Usage (Causes 400 Error):
```json
{
  "budget": 20000,          // WRONG field name
  "scenario": {
    "items": [...]          // Missing 'wbs' field
  }
}
```

### ✅ Correct Usage:
```json
{
  "target_budget": 20000,   // or "client_budget" for backward compatibility
  "scenario": {
    "wbs": [                // Required: WBS items array
      {
        "Task": "Strategy Development",
        "Hours": 40,
        "Price": 6000,
        "Rate": 150,
        "Seniority": "Senior",
        "Role": "Strategist"
      }
    ],
    "total_price": 21200,   // Optional
    "total_hours": 180      // Optional
  },
  "company_size": "mid_market",      // Optional: "startup", "mid_market", "enterprise"
  "urgency": "standard",              // Optional: "rush", "standard", "flexible"
  "industry_multiplier": 1.0,        // Optional: e.g., 1.5 for luxury
  "maintain_quality_tiers": true      // Optional: default true
}
```

**Required Fields:**
- `target_budget` or `client_budget` (number) - The target budget
- `scenario` (object) with `wbs` (array) - The scenario with WBS items

**Common Error Responses:**
- **400: "Budget too low for minimum viable delivery"** - The requested budget is below the calculated minimum viable price
- **400: "Valid scenario with WBS is required"** - The scenario object is missing or doesn't have a 'wbs' field
- **400: "Current scenario has no pricing"** - The WBS items don't have Price values

---

## Test Results

All endpoints have been tested and are working correctly:

```
✓ RFP Analysis: PASSED (Status 200)
✓ L3_for: PASSED (Status 200)
✓ Pricing Optimization: PASSED (Status 200)
```

## Quick Test Script

A test script has been created at `test_api_fixes.py` that verifies all three endpoints with the correct parameters. Run it with:

```bash
python test_api_fixes.py
```

## Key Takeaways

1. **Parameter Names Matter**: Always use the exact parameter names expected by the API
2. **Check Required Fields**: Ensure all required fields are present in your requests
3. **Review Error Messages**: The API returns helpful error messages that indicate what's missing
4. **Use Type-Safe Clients**: Consider using generated API clients that enforce correct parameter types and names