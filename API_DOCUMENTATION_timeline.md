# Timeline Generation API Documentation

## Endpoint: `/api/ai/generate_timeline`

### Method: `POST`

### Description
Generates an intelligent project timeline with parallel workstreams, dependencies, and CPM (Critical Path Method) analysis. The endpoint uses AI optimization to create realistic project schedules.

## ✅ CONFIRMED: Parameter Names are Correct

After thorough testing, the API endpoint correctly accepts the following parameters:
- ✅ `deliverables` (NOT `scenario_data` or `scenario`)
- ✅ `rfp_text` 
- ✅ `project_start`
- ✅ `optimization_mode`
- ✅ `use_intelligent_scheduler`

## Request Body Schema

```python
class TimelineGenerationRequest(BaseModel):
    """Request model for AI timeline generation"""
    deliverables: List[Dict[str, Any]]  # Selected deliverables with metadata
    rfp_text: Optional[str] = None  # RFP context text
    project_start: Optional[str] = None  # ISO date format YYYY-MM-DD
    optimization_mode: str = "balanced"  # "speed" | "quality" | "balanced" | "cost"
    use_intelligent_scheduler: bool = True  # Use new intelligent scheduler
```

### Deliverable Object Structure
Each deliverable in the `deliverables` array should contain:

```json
{
    "deliverable_code": "DEL-0001",      // Required: Unique deliverable identifier
    "name": "Strategic Planning",         // Optional: Display name
    "department": "Strategy",             // Optional: Department assignment
    "hours": 80,                          // Optional: Total hours (alias: total_hours)
    "components": ["Research", "Analysis"], // Optional: Component list
    "is_retainer": false,                // Optional: Retainer flag
    "retainer_months": 0                 // Optional: Retainer duration
}
```

## Example Request

```json
{
    "deliverables": [
        {
            "deliverable_code": "DEL-0001",
            "name": "Strategic Planning",
            "department": "Strategy",
            "hours": 80,
            "components": ["Market Research", "Competitive Analysis"],
            "is_retainer": false,
            "retainer_months": 0
        },
        {
            "deliverable_code": "DEL-0002",
            "name": "Creative Concepts",
            "department": "Creative",
            "hours": 120,
            "components": ["Visual Design", "Brand Identity"],
            "is_retainer": false,
            "retainer_months": 0
        },
        {
            "deliverable_code": "DEL-0003",
            "name": "Content Strategy",
            "department": "Content",
            "hours": 60,
            "components": ["Editorial Calendar", "Content Guidelines"],
            "is_retainer": false,
            "retainer_months": 0
        }
    ],
    "rfp_text": "We need a comprehensive marketing campaign for our luxury brand launch",
    "project_start": "2025-10-20",
    "optimization_mode": "balanced",
    "use_intelligent_scheduler": true
}
```

## Response Format

### Initial Response (Job Creation)
```json
{
    "job_id": "7adbbd86-1a61-4d5a-9d39-0168d0dcdb45",
    "status": null,
    "message": "Timeline generation started. Connect to SSE stream for progress updates."
}
```

### SSE Stream Endpoint
Connect to `/api/stream/{job_id}` for real-time progress updates.

### Final Timeline Result Structure
```json
{
    "tasks": [
        {
            "id": "task_DEL-0001",
            "name": "Strategic Planning",
            "start": "2025-11-03",
            "end": "2025-11-21",
            "progress": 0,
            "dependencies": "",
            "custom_class": "workstream-strategy",
            "deliverable_code": "DEL-0001",
            "workstream": "Strategy",
            "phase": "Development",
            "hours": 80,
            "is_milestone": false,
            "critical_path": false,
            "slack_days": 15,
            "parallel_tasks": [],
            "is_retainer": false
        }
    ],
    "milestones": [
        {
            "id": "milestone_creative_approval",
            "name": "🎯 Creative Approval",
            "start": "2025-12-06",
            "end": "2025-12-06",
            "is_milestone": true,
            "critical_path": true
        }
    ],
    "metadata": {
        "project_start": "2025-11-03",
        "project_end": "2026-02-17",
        "total_duration_days": 106,
        "total_hours": 610,
        "workstreams": ["Strategy", "Creative", "Content"],
        "phases": ["Development", "Production", "Launch"],
        "critical_tasks": 5,
        "parallel_opportunities": 3
    },
    "reasoning": {
        "ai_strategic_rationale": "Timeline optimized for balanced delivery...",
        "risk_mitigation": [
            "Regular review checkpoints",
            "Buffer time included"
        ],
        "acceleration_opportunities": [
            "Parallel workstreams identified"
        ],
        "resource_optimization": "Resources leveled across departments",
        "client_touchpoints": [
            "Weekly updates",
            "Phase gate reviews"
        ],
        "confidence_level": 75
    },
    "cpm_metrics": {
        "critical_path_length": 85.0,
        "project_duration": 106.0,
        "critical_tasks_count": 5,
        "average_float": 20.5,
        "project_buffer_days": 10.0,
        "feeding_buffers_count": 3,
        "total_buffer_days": 18.0,
        "confidence_level": 75,
        "resource_utilization": {
            "average": 0.65,
            "peak": 0.90,
            "by_department": {
                "Strategy": 0.60,
                "Creative": 0.75,
                "Content": 0.55
            }
        }
    }
}
```

## Optimization Modes

- **`balanced`** (default): Balance between speed and quality
- **`speed`**: Maximize parallelization, minimize duration
- **`quality`**: Emphasize thoroughness and review cycles
- **`cost`**: Optimize for resource efficiency

## Frontend Integration Example

```javascript
async function generateTimeline(selectedDeliverables) {
    const response = await fetch('/api/ai/generate_timeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            deliverables: selectedDeliverables.map(code => ({
                deliverable_code: code,
                name: labelFor(code),
                department: getDepartment(code),
                hours: getHours(code),
                components: getComponents(code),
                is_retainer: isRetainer(code),
                retainer_months: getRetainerMonths(code)
            })),
            rfp_text: document.getElementById('rfpText')?.value || '',
            project_start: document.getElementById('projectStart')?.value,
            optimization_mode: 'balanced',
            use_intelligent_scheduler: true
        })
    });
    
    const job = await response.json();
    
    // Connect to SSE for progress
    const eventSource = new EventSource(`/api/stream/${job.job_id}`);
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.status === 'completed') {
            // Handle completed timeline
            displayTimeline(data.result);
            eventSource.close();
        }
    };
}
```

## Error Handling

### Common Errors and Solutions

1. **Missing Deliverable Codes**
   - Ensure each deliverable has a `deliverable_code` field
   - Codes should match database entries (e.g., "DEL-0001")

2. **Invalid Date Format**
   - Use ISO format: "YYYY-MM-DD"
   - If omitted, defaults to next Monday

3. **Empty Response from AI**
   - The API has fallback mechanisms
   - Default insights will be provided if AI fails

## Testing the Endpoint

Use the provided test scripts:
- `test_timeline_api.py` - Basic functionality test
- `test_timeline_comprehensive.py` - Full CPM analysis test

## Key Fixes Applied

1. ✅ **Parameter naming**: Confirmed `deliverables` is correct (not `scenario_data` or `scenario`)
2. ✅ **JSON parsing**: Added robust error handling for AI responses
3. ✅ **Deliverable enrichment**: Database lookup works with both `hours` and `total_hours` fields
4. ✅ **Department normalization**: Handles various department name formats
5. ✅ **Async processing**: Returns job ID for SSE streaming

## Performance Notes

- Timeline generation typically takes 5-30 seconds depending on complexity
- Uses SSE (Server-Sent Events) for real-time progress updates
- AI reasoning enhancement adds 2-5 seconds but provides strategic insights
- CPM analysis included when using intelligent scheduler