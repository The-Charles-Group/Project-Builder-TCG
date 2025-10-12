"""
AI Timeline Manager - Intelligent project scheduling using GPT-5
Generates optimized timelines with dependency analysis and resource allocation
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import random

# OpenAI client initialization
try:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_AVAILABLE = True
except Exception as e:
    print(f"[AI Timeline] OpenAI not available: {e}")
    OPENAI_AVAILABLE = False
    client = None

# Department colors for Gantt chart
DEPARTMENT_COLORS = {
    "Strategy": "#667eea",      # Purple
    "Creative": "#f56565",      # Red  
    "Paid Media": "#48bb78",    # Green
    "Content": "#ed8936",       # Orange
    "Technology": "#4299e1",    # Blue
    "Integrated Marketing Management": "#9f7aea",  # Violet
    "Project Management": "#718096",  # Gray
    "Quality Assurance": "#38b2ac",   # Teal
    "Account Management": "#d69e2e",  # Gold
}

@dataclass
class TimelineTask:
    """Represents a task in the timeline with all scheduling metadata"""
    id: str
    name: str
    deliverable_code: str
    deliverable_name: str
    component: Optional[str] = None
    department: str = "Strategy"
    start_date: str = ""  # ISO format YYYY-MM-DD
    end_date: str = ""    # ISO format YYYY-MM-DD
    progress: int = 0
    dependencies: List[str] = field(default_factory=list)
    hours: float = 0
    resources: List[str] = field(default_factory=list)
    color: str = ""
    is_milestone: bool = False
    critical_path: bool = False
    is_retainer: bool = False  # NEW: Flag for retainer tasks
    retainer_month: Optional[int] = None  # NEW: Month number for retainer tasks
    monthly_hours: Optional[float] = None  # NEW: Monthly hours for retainer
    
    def to_gantt_format(self) -> Dict[str, Any]:
        """Convert to Frappe Gantt format"""
        result = {
            "id": self.id,
            "name": self.name,
            "start": self.start_date,
            "end": self.end_date,
            "progress": self.progress,
            "dependencies": ",".join(self.dependencies) if self.dependencies else "",
            "custom_class": f"dept-{self.department.lower().replace(' ', '-')}",
            "deliverable_code": self.deliverable_code,
            "component": self.component,
            "department": self.department,
            "hours": self.hours,
            "is_milestone": self.is_milestone,
            "critical_path": self.critical_path
        }
        
        # Add retainer-specific fields
        if self.is_retainer:
            result["is_retainer"] = True
            result["retainer_month"] = self.retainer_month
            result["monthly_hours"] = self.monthly_hours
            result["custom_class"] += " retainer-task"  # Add visual indicator
        
        return result

@dataclass 
class TimelineReasoning:
    """AI's reasoning for timeline decisions"""
    overall_strategy: str
    critical_path_explanation: str
    dependency_rationale: Dict[str, str]  # task_id -> reasoning
    optimization_notes: List[str]
    confidence_score: float  # 0.0 to 1.0
    parallel_opportunities: List[str]
    risk_factors: List[str]
    
class DependencyType(Enum):
    """Types of task dependencies"""
    FINISH_TO_START = "FS"  # Most common: Task B starts after Task A finishes
    START_TO_START = "SS"   # Tasks start together
    FINISH_TO_FINISH = "FF" # Tasks finish together
    START_TO_FINISH = "SF"  # Rare: Task B finishes after Task A starts
    
class TimelineOptimizer:
    """Optimizes project timelines using business rules and AI insights"""
    
    # Standard task sequences by department
    LOGICAL_SEQUENCES = {
        "Strategy": ["Research", "Analysis", "Strategy Development", "Documentation"],
        "Creative": ["Concepting", "Design", "Production", "Review"],
        "Paid Media": ["Planning", "Setup", "Launch", "Optimization"],
        "Content": ["Planning", "Creation", "Review", "Publishing"],
        "Technology": ["Architecture", "Development", "Testing", "Deployment"]
    }
    
    # Cross-department dependencies
    DEPT_DEPENDENCIES = {
        "Creative": ["Strategy"],  # Creative depends on Strategy
        "Paid Media": ["Creative", "Strategy"],
        "Technology": ["Strategy"],
        "Content": ["Strategy", "Creative"]
    }
    
    def calculate_business_days(self, start_date: datetime, duration_days: int) -> datetime:
        """Calculate end date considering only business days (Mon-Fri)"""
        current = start_date
        days_added = 0
        
        while days_added < duration_days:
            current += timedelta(days=1)
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                days_added += 1
                
        return current
    
    def identify_dependencies(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Identify logical dependencies between tasks based on business rules"""
        dependencies = {}
        task_by_dept_comp = {}
        
        # Group tasks by department and component
        for task in tasks:
            dept = task.get('department', 'Strategy')
            comp = task.get('component', '')
            key = f"{dept}:{comp}"
            if key not in task_by_dept_comp:
                task_by_dept_comp[key] = []
            task_by_dept_comp[key].append(task)
        
        # Apply dependency rules
        for i, task in enumerate(tasks):
            task_id = task['id']
            dependencies[task_id] = []
            
            # Same deliverable, earlier components
            for j, other in enumerate(tasks[:i]):
                if task['deliverable_code'] == other['deliverable_code']:
                    # Check if departments have dependency
                    task_dept = task.get('department', 'Strategy')
                    other_dept = other.get('department', 'Strategy')
                    
                    if task_dept in self.DEPT_DEPENDENCIES:
                        if other_dept in self.DEPT_DEPENDENCIES[task_dept]:
                            dependencies[task_id].append(other['id'])
        
        return dependencies
    
    def calculate_critical_path(self, tasks: List[TimelineTask]) -> Set[str]:
        """Identify tasks on the critical path using CPM algorithm"""
        # Build task lookup
        task_map = {t.id: t for t in tasks}
        
        # Calculate earliest start times (forward pass)
        earliest_start = {}
        earliest_finish = {}
        
        for task in tasks:
            if not task.dependencies:
                earliest_start[task.id] = 0
            else:
                max_finish = 0
                for dep_id in task.dependencies:
                    if dep_id in earliest_finish:
                        max_finish = max(max_finish, earliest_finish[dep_id])
                earliest_start[task.id] = max_finish
            
            duration = (datetime.fromisoformat(task.end_date) - datetime.fromisoformat(task.start_date)).days
            earliest_finish[task.id] = earliest_start[task.id] + duration
        
        # Calculate latest start times (backward pass)
        project_end = max(earliest_finish.values())
        latest_start = {}
        latest_finish = {}
        
        for task in reversed(tasks):
            # Find tasks that depend on this one
            dependents = [t for t in tasks if task.id in t.dependencies]
            
            if not dependents:
                latest_finish[task.id] = project_end
            else:
                min_start = project_end
                for dep in dependents:
                    if dep.id in latest_start:
                        min_start = min(min_start, latest_start[dep.id])
                latest_finish[task.id] = min_start
            
            duration = (datetime.fromisoformat(task.end_date) - datetime.fromisoformat(task.start_date)).days
            latest_start[task.id] = latest_finish[task.id] - duration
        
        # Tasks with zero slack are on critical path
        critical_path = set()
        for task_id in earliest_start:
            slack = latest_start.get(task_id, 0) - earliest_start.get(task_id, 0)
            if abs(slack) < 0.01:  # Allow for floating point errors
                critical_path.add(task_id)
        
        return critical_path

async def generate_ai_timeline(
    deliverables: List[Dict[str, Any]], 
    rfp_text: str = "",
    project_start: Optional[str] = None,
    optimization_mode: str = "balanced"
) -> Dict[str, Any]:
    """
    Generate an AI-optimized project timeline
    
    Args:
        deliverables: List of selected deliverables with components and tasks
        rfp_text: Original RFP text for context
        project_start: ISO date string for project start (defaults to next Monday)
        optimization_mode: "speed" | "quality" | "balanced" | "cost"
    
    Returns:
        Dictionary with timeline tasks, reasoning, and metadata
    """
    
    if not OPENAI_AVAILABLE or not client:
        return generate_fallback_timeline(deliverables, project_start)
    
    try:
        # Build context for AI
        deliverable_summary = []
        for d in deliverables:
            components = d.get('components', [])
            hours = d.get('total_hours', 0)
            deliverable_summary.append({
                'name': d.get('deliverable_name', ''),
                'code': d.get('deliverable_code', ''),
                'components': len(components),
                'hours': hours,
                'department': d.get('department', 'Strategy')
            })
        
        # Create the prompt for timeline generation
        prompt = f"""You are an expert project manager specializing in agency work and marketing campaigns.

CONTEXT:
- Project brief: {rfp_text[:2000] if rfp_text else 'Standard agency project'}
- Optimization goal: {optimization_mode}
- Project start: {project_start or 'Next Monday'}

DELIVERABLES TO SCHEDULE:
{json.dumps(deliverable_summary, indent=2)}

REQUIREMENTS:
1. Create a realistic project timeline considering:
   - Logical task sequences (research → strategy → creative → execution)
   - Department dependencies (Creative needs Strategy complete first)
   - Resource constraints (same team can't do parallel work)
   - Client review cycles (add buffer time)
   - Industry best practices

2. For each deliverable, determine:
   - Optimal start date
   - Required duration in business days
   - Dependencies on other deliverables
   - Whether it's on the critical path
   
3. Identify opportunities for:
   - Parallel work across different teams
   - Time savings through smart sequencing
   - Risk mitigation through buffers

Return a JSON object with this structure:
{{
  "timeline_strategy": "Overall approach to scheduling this project",
  "tasks": [
    {{
      "deliverable_code": "code",
      "deliverable_name": "name", 
      "suggested_start_offset_days": 0,  // Business days from project start
      "suggested_duration_days": 10,     // Business days
      "dependencies": ["other_deliverable_codes"],
      "reasoning": "Why scheduled this way",
      "critical_path": true/false,
      "parallel_with": ["deliverable_codes that can run in parallel"],
      "risk_level": "low/medium/high"
    }}
  ],
  "critical_path_explanation": "Which tasks drive the project end date",
  "optimization_notes": ["Key scheduling decisions made"],
  "total_duration_days": 45,
  "confidence_score": 0.85,
  "risks": ["Potential scheduling risks to watch"]
}}"""

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
        
        ai_timeline = json.loads(response.choices[0].message.content)
        
        # Convert AI suggestions to Gantt format
        return process_ai_timeline(ai_timeline, deliverables, project_start)
        
    except Exception as e:
        print(f"[AI Timeline] Error generating timeline: {e}")
        return generate_fallback_timeline(deliverables, project_start)

def process_ai_timeline(
    ai_response: Dict[str, Any], 
    deliverables: List[Dict[str, Any]], 
    project_start: Optional[str]
) -> Dict[str, Any]:
    """Process AI timeline response into Gantt-compatible format"""
    
    # Parse project start date
    if project_start:
        start_date = datetime.fromisoformat(project_start)
    else:
        # Default to next Monday
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7 or 7
        start_date = today + timedelta(days=days_until_monday)
    
    optimizer = TimelineOptimizer()
    tasks = []
    deliverable_lookup = {d['deliverable_code']: d for d in deliverables}
    
    # Process each task from AI response
    for ai_task in ai_response.get('tasks', []):
        code = ai_task['deliverable_code']
        if code not in deliverable_lookup:
            continue
            
        deliverable = deliverable_lookup[code]
        
        # Calculate dates based on AI suggestions
        offset_days = ai_task.get('suggested_start_offset_days', 0)
        duration_days = ai_task.get('suggested_duration_days', 5)
        
        task_start = optimizer.calculate_business_days(start_date, offset_days)
        task_end = optimizer.calculate_business_days(task_start, duration_days)
        
        # Determine department and color
        dept = deliverable.get('department', 'Strategy')
        color = DEPARTMENT_COLORS.get(dept, '#718096')
        
        # Create main deliverable task
        main_task = TimelineTask(
            id=f"task_{code}",
            name=deliverable.get('deliverable_name', code),
            deliverable_code=code,
            deliverable_name=deliverable.get('deliverable_name', ''),
            department=dept,
            start_date=task_start.strftime('%Y-%m-%d'),
            end_date=task_end.strftime('%Y-%m-%d'),
            dependencies=[f"task_{dep}" for dep in ai_task.get('dependencies', [])],
            hours=deliverable.get('total_hours', 0),
            color=color,
            critical_path=ai_task.get('critical_path', False)
        )
        tasks.append(main_task)
        
        # Add component subtasks if they exist
        components = deliverable.get('components', [])
        if components:
            comp_duration = duration_days / len(components) if components else duration_days
            comp_start = task_start
            
            for i, comp in enumerate(components):
                comp_end = optimizer.calculate_business_days(comp_start, max(1, int(comp_duration)))
                
                comp_task = TimelineTask(
                    id=f"task_{code}_comp_{i}",
                    name=f"  └─ {comp.get('name', f'Component {i+1}')}",
                    deliverable_code=code,
                    deliverable_name=deliverable.get('deliverable_name', ''),
                    component=comp.get('name', ''),
                    department=dept,
                    start_date=comp_start.strftime('%Y-%m-%d'),
                    end_date=comp_end.strftime('%Y-%m-%d'),
                    dependencies=[f"task_{code}"] if i == 0 else [f"task_{code}_comp_{i-1}"],
                    hours=comp.get('hours', 0),
                    color=color
                )
                tasks.append(comp_task)
                comp_start = comp_end
    
    # Calculate critical path
    critical_path_ids = optimizer.calculate_critical_path(tasks)
    for task in tasks:
        task.critical_path = task.id in critical_path_ids
    
    # Build reasoning explanation
    reasoning = TimelineReasoning(
        overall_strategy=ai_response.get('timeline_strategy', 'Optimized for efficient delivery'),
        critical_path_explanation=ai_response.get('critical_path_explanation', ''),
        dependency_rationale={
            f"task_{t['deliverable_code']}": t.get('reasoning', '')
            for t in ai_response.get('tasks', [])
        },
        optimization_notes=ai_response.get('optimization_notes', []),
        confidence_score=ai_response.get('confidence_score', 0.75),
        parallel_opportunities=[
            f"{t['deliverable_name']} can run parallel with: {', '.join(t.get('parallel_with', []))}"
            for t in ai_response.get('tasks', [])
            if t.get('parallel_with')
        ],
        risk_factors=ai_response.get('risks', [])
    )
    
    return {
        "tasks": [t.to_gantt_format() for t in tasks],
        "reasoning": {
            "overall_strategy": reasoning.overall_strategy,
            "critical_path_explanation": reasoning.critical_path_explanation,
            "dependency_rationale": reasoning.dependency_rationale,
            "optimization_notes": reasoning.optimization_notes,
            "confidence_score": reasoning.confidence_score,
            "parallel_opportunities": reasoning.parallel_opportunities,
            "risk_factors": reasoning.risk_factors
        },
        "metadata": {
            "total_duration_days": ai_response.get('total_duration_days', 30),
            "project_start": start_date.strftime('%Y-%m-%d'),
            "project_end": max(tasks, key=lambda t: t.end_date).end_date if tasks else start_date.strftime('%Y-%m-%d'),
            "total_tasks": len(tasks),
            "critical_tasks": len(critical_path_ids),
            "departments_involved": list(set(t.department for t in tasks))
        }
    }

def generate_fallback_timeline(
    deliverables: List[Dict[str, Any]], 
    project_start: Optional[str]
) -> Dict[str, Any]:
    """Generate a basic timeline when AI is not available"""
    
    # Parse project start date  
    if project_start:
        start_date = datetime.fromisoformat(project_start)
    else:
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7 or 7
        start_date = today + timedelta(days=days_until_monday)
    
    optimizer = TimelineOptimizer()
    tasks = []
    current_date = start_date
    
    # Simple sequential scheduling with department-based ordering
    dept_order = ["Strategy", "Creative", "Content", "Paid Media", "Technology", "Integrated Marketing Management"]
    
    # Sort deliverables by department priority
    sorted_deliverables = sorted(deliverables, 
                                  key=lambda d: (
                                      dept_order.index(d.get('department', 'Strategy')) 
                                      if d.get('department', 'Strategy') in dept_order 
                                      else 99,
                                      d.get('deliverable_name', '')
                                  ))
    
    for i, deliverable in enumerate(sorted_deliverables):
        code = deliverable.get('deliverable_code', f'deliv_{i}')
        hours = deliverable.get('total_hours', 40)
        
        # Estimate duration based on hours (8 hours per day)
        duration_days = max(1, int(hours / 8))
        
        # Add some buffer between tasks
        if i > 0:
            current_date = optimizer.calculate_business_days(current_date, 1)
        
        task_end = optimizer.calculate_business_days(current_date, duration_days)
        dept = deliverable.get('department', 'Strategy')
        
        task = TimelineTask(
            id=f"task_{code}",
            name=deliverable.get('deliverable_name', code),
            deliverable_code=code,
            deliverable_name=deliverable.get('deliverable_name', ''),
            department=dept,
            start_date=current_date.strftime('%Y-%m-%d'),
            end_date=task_end.strftime('%Y-%m-%d'),
            dependencies=[f"task_{sorted_deliverables[i-1]['deliverable_code']}" ] if i > 0 else [],
            hours=hours,
            color=DEPARTMENT_COLORS.get(dept, '#718096'),
            critical_path=True  # All sequential tasks are critical in fallback
        )
        tasks.append(task)
        current_date = task_end
    
    return {
        "tasks": [t.to_gantt_format() for t in tasks],
        "reasoning": {
            "overall_strategy": "Sequential scheduling based on department dependencies (fallback mode)",
            "critical_path_explanation": "All tasks are on critical path in sequential scheduling",
            "dependency_rationale": {},
            "optimization_notes": ["AI optimization not available - using sequential scheduling"],
            "confidence_score": 0.5,
            "parallel_opportunities": [],
            "risk_factors": ["Manual review recommended for optimization opportunities"]
        },
        "metadata": {
            "total_duration_days": (current_date - start_date).days,
            "project_start": start_date.strftime('%Y-%m-%d'),
            "project_end": current_date.strftime('%Y-%m-%d'),
            "total_tasks": len(tasks),
            "critical_tasks": len(tasks),
            "departments_involved": list(set(t.department for t in tasks))
        }
    }

def generate_retainer_tasks(
    deliverable: Dict[str, Any],
    start_date: datetime,
    months: int = 12,
    monthly_hours: Optional[Dict[str, float]] = None
) -> List[TimelineTask]:
    """
    Generate recurring monthly tasks for retainer deliverables
    
    Args:
        deliverable: Deliverable data including name, code, department
        start_date: Project start date
        months: Number of months for retainer
        monthly_hours: Optional dict of monthly hour allocations
        
    Returns:
        List of monthly timeline tasks
    """
    tasks = []
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    current_date = start_date
    code = deliverable.get('deliverable_code', 'retainer')
    name = deliverable.get('deliverable_name', 'Retainer Service')
    dept = deliverable.get('department', 'Strategy')
    base_hours = deliverable.get('total_hours', 0) / months if months > 0 else 0
    
    for i in range(months):
        month_idx = current_date.month - 1
        month_name = month_names[month_idx]
        year = current_date.year
        
        # Calculate month boundaries (first and last business day of month)
        first_day = current_date.replace(day=1)
        if first_day.weekday() >= 5:  # Skip weekend
            days_until_monday = 7 - first_day.weekday() + 1
            first_day = first_day + timedelta(days=days_until_monday % 7)
        
        # Get last day of month
        if current_date.month == 12:
            last_day = current_date.replace(day=31)
        else:
            last_day = (current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1))
        
        # Skip weekend for last day
        while last_day.weekday() >= 5:
            last_day = last_day - timedelta(days=1)
        
        # Get hours for this month
        if monthly_hours and f"{month_name}" in monthly_hours:
            hours = monthly_hours[f"{month_name}"]
        elif monthly_hours and f"{month_name} Y{(i // 12) + 1}" in monthly_hours:
            hours = monthly_hours[f"{month_name} Y{(i // 12) + 1}"]
        else:
            hours = base_hours
        
        task_id = f"{code}_month_{i+1}"
        task_name = f"{name} - {month_name} {year}"
        
        task = TimelineTask(
            id=task_id,
            name=task_name,
            deliverable_code=code,
            deliverable_name=name,
            department=dept,
            start_date=first_day.strftime('%Y-%m-%d'),
            end_date=last_day.strftime('%Y-%m-%d'),
            dependencies=[f"{code}_month_{i}"] if i > 0 else [],
            hours=hours,
            color=DEPARTMENT_COLORS.get(dept, '#718096'),
            is_retainer=True,
            retainer_month=i + 1,
            monthly_hours=hours
        )
        tasks.append(task)
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    return tasks

async def suggest_timeline_from_selection(
    selected_codes: List[str],
    deliverables_db: List[Dict[str, Any]],
    rfp_text: str = "",
    project_start: Optional[str] = None,
    optimization_mode: str = "balanced"
) -> Dict[str, Any]:
    """
    Main entry point for timeline suggestion from Step 2 selection
    
    Args:
        selected_codes: List of selected deliverable codes from Step 2
        deliverables_db: Full deliverables database for lookup
        rfp_text: Original RFP text for context
        project_start: ISO date string for project start
        optimization_mode: Optimization strategy
    
    Returns:
        Complete timeline with tasks, reasoning, and metadata
    """
    
    # Filter deliverables to only selected ones
    selected_deliverables = [
        d for d in deliverables_db 
        if d.get('deliverable_code') in selected_codes
    ]
    
    if not selected_deliverables:
        return {
            "error": "No valid deliverables selected",
            "tasks": [],
            "reasoning": {},
            "metadata": {}
        }
    
    # Separate retainer and project deliverables
    retainer_deliverables = []
    project_deliverables = []
    
    for deliv in selected_deliverables:
        if deliv.get('is_retainer') or deliv.get('retainer_months'):
            retainer_deliverables.append(deliv)
        else:
            project_deliverables.append(deliv)
    
    # Generate timeline for project deliverables using AI or fallback
    result = await generate_ai_timeline(
        project_deliverables,
        rfp_text,
        project_start,
        optimization_mode
    )
    
    # Add retainer tasks if any
    if retainer_deliverables:
        start_date = datetime.fromisoformat(project_start) if project_start else datetime.now()
        
        for retainer_deliv in retainer_deliverables:
            retainer_months = retainer_deliv.get('retainer_months', 12)
            monthly_hours = retainer_deliv.get('monthly_hours')
            
            retainer_tasks = generate_retainer_tasks(
                retainer_deliv,
                start_date,
                retainer_months,
                monthly_hours
            )
            
            # Add retainer tasks to result
            result['tasks'].extend([t.to_gantt_format() for t in retainer_tasks])
        
        # Update metadata
        result['metadata']['total_tasks'] = len(result['tasks'])
        result['metadata']['retainer_tasks'] = len(retainer_deliverables)
        result['reasoning']['optimization_notes'].append(
            f"Added {len(retainer_deliverables)} retainer deliverables as recurring monthly tasks"
        )
    
    return result