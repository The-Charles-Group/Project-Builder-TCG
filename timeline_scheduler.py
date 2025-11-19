"""
Intelligent Timeline Scheduler with Parallel Workstreams and Dependencies
Provides advanced project scheduling with phases, dependencies, and resource optimization
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import math
from collections import defaultdict

# Project phases with typical durations (in business days)
@dataclass
class ProjectPhase:
    """Represents a project phase with timing and deliverables"""
    name: str
    description: str
    start_week: int  # Week number from project start
    duration_weeks: int
    workstreams: List[str]  # Which departments are active
    milestone: Optional[str] = None  # Key approval milestone
    
class PhaseType(Enum):
    """Standard agency project phases"""
    DISCOVERY = "Discovery & Strategy"
    DEVELOPMENT = "Development"  
    PRODUCTION = "Production"
    LAUNCH = "Launch & Optimization"
    ONGOING = "Ongoing Management"

# Standard project phases configuration
PROJECT_PHASES = [
    ProjectPhase(
        name=PhaseType.DISCOVERY.value,
        description="Research, analysis, and strategic planning",
        start_week=1,
        duration_weeks=4,
        workstreams=["Strategy", "Account Management"],
        milestone="Strategy Approval"
    ),
    ProjectPhase(
        name=PhaseType.DEVELOPMENT.value,
        description="Creative concepting, media planning, content strategy",
        start_week=3,  # Overlaps with Discovery
        duration_weeks=6,
        workstreams=["Creative", "Paid Media", "Content", "Strategy"],
        milestone="Creative Approval"
    ),
    ProjectPhase(
        name=PhaseType.PRODUCTION.value,
        description="Asset creation, platform setup, testing",
        start_week=6,  # Overlaps with Development
        duration_weeks=7,
        workstreams=["Creative", "Technology", "Paid Media", "Content"],
        milestone="Pre-Launch Review"
    ),
    ProjectPhase(
        name=PhaseType.LAUNCH.value,
        description="Campaign launch, monitoring, optimization",
        start_week=10,
        duration_weeks=4,
        workstreams=["Paid Media", "Technology", "Account Management"],
        milestone="Launch Complete"
    ),
    ProjectPhase(
        name=PhaseType.ONGOING.value,
        description="Retainer services and continuous optimization",
        start_week=12,
        duration_weeks=52,  # Full year
        workstreams=["All"],
        milestone=None
    )
]

@dataclass
class DependencyRelationship:
    """Represents a dependency between tasks"""
    predecessor: str  # Task ID that must come first
    successor: str    # Task ID that depends on predecessor
    type: str = "FS"  # FS, SS, FF, SF
    lag_days: int = 0  # Lag time in business days
    lag_percentage: float = 0.0  # For SS relationships, what % completion triggers successor
    reason: str = ""  # Explanation for the dependency
    
@dataclass
class WorkstreamTask:
    """Enhanced task with workstream and dependency information"""
    id: str
    name: str
    deliverable_code: str
    workstream: str  # Department/workstream
    phase: PhaseType
    start_date: datetime
    end_date: datetime
    duration_days: int
    hours: float
    dependencies: List[DependencyRelationship] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    is_milestone: bool = False
    is_critical: bool = False
    is_retainer: bool = False
    slack_days: int = 0  # Float/slack time
    earliest_start: Optional[datetime] = None
    latest_start: Optional[datetime] = None
    parallel_tasks: List[str] = field(default_factory=list)  # Tasks that can run in parallel
    
class TimelineScheduler:
    """Advanced scheduler for intelligent timeline generation"""
    
    # Dependency rules between deliverable types
    DEPENDENCY_RULES = {
        # Strategy must complete before creative starts
        ("strategy", "creative"): {
            "type": "FS",
            "lag_days": 2,
            "reason": "Creative needs approved strategy"
        },
        # Strategy can overlap with research
        ("research", "analysis"): {
            "type": "SS", 
            "lag_percentage": 0.25,
            "reason": "Analysis can start once initial research data available"
        },
        # Creative concepting can start before strategy fully complete
        ("strategy", "concepting"): {
            "type": "SS",
            "lag_percentage": 0.6,
            "reason": "Initial concepts can begin with draft strategy"
        },
        # Production can start before all creative approved
        ("creative", "production"): {
            "type": "SS",
            "lag_percentage": 0.4,
            "reason": "Production can begin on approved pieces"
        },
        # Media planning can run parallel to creative
        ("audience_research", "media_planning"): {
            "type": "SS",
            "lag_percentage": 0.5,
            "reason": "Media planning starts once target audience defined"
        },
        # Technology needs design specs
        ("design", "development"): {
            "type": "SS",
            "lag_percentage": 0.7,
            "reason": "Development needs core designs complete"
        },
        # QA starts near end of development
        ("development", "testing"): {
            "type": "SS",
            "lag_percentage": 0.8,
            "reason": "Testing begins on stable builds"
        }
    }
    
    # Workstream assignment rules based on deliverable patterns
    WORKSTREAM_PATTERNS = {
        "Strategy": [
            "research", "analysis", "strategy", "positioning", "brief", 
            "audit", "insights", "planning", "roadmap", "framework"
        ],
        "Creative": [
            "creative", "design", "visual", "art", "copy", "concept",
            "brand", "identity", "campaign", "video", "photography"
        ],
        "Content": [
            "content", "editorial", "blog", "social", "email", "newsletter",
            "article", "writing", "storytelling", "messaging"
        ],
        "Paid Media": [
            "media", "advertising", "ppc", "sem", "display", "programmatic",
            "facebook", "google", "linkedin", "retargeting", "attribution"
        ],
        "Technology": [
            "development", "website", "app", "platform", "integration", "api",
            "database", "analytics", "tracking", "automation", "technical"
        ],
        "Account Management": [
            "project", "management", "reporting", "presentation", "meeting",
            "status", "coordination", "stakeholder", "communication"
        ]
    }
    
    def __init__(self):
        self.tasks = []
        self.dependencies = []
        self.workstreams = defaultdict(list)  # workstream -> list of tasks
        self.phases = defaultdict(list)  # phase -> list of tasks
        self.resource_calendar = defaultdict(set)  # date -> set of busy resources
        
    def identify_workstream(self, deliverable_name: str, department: Optional[str] = None) -> str:
        """Identify which workstream a deliverable belongs to"""
        if department:
            return department
            
        name_lower = deliverable_name.lower()
        
        # Check patterns to assign workstream
        for workstream, patterns in self.WORKSTREAM_PATTERNS.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return workstream
        
        return "Strategy"  # Default fallback
    
    def identify_phase(self, deliverable_name: str, workstream: str) -> PhaseType:
        """Determine which project phase a deliverable belongs to"""
        name_lower = deliverable_name.lower()
        
        # Phase assignment logic based on deliverable type
        if any(word in name_lower for word in ["research", "audit", "discovery", "analysis", "brief"]):
            return PhaseType.DISCOVERY
        elif any(word in name_lower for word in ["concept", "creative", "planning", "strategy doc"]):
            return PhaseType.DEVELOPMENT
        elif any(word in name_lower for word in ["production", "asset", "build", "development", "implementation"]):
            return PhaseType.PRODUCTION
        elif any(word in name_lower for word in ["launch", "campaign", "activation", "go-live"]):
            return PhaseType.LAUNCH
        elif any(word in name_lower for word in ["optimization", "reporting", "management", "ongoing"]):
            return PhaseType.ONGOING
        
        # Workstream-based defaults
        if workstream == "Strategy":
            return PhaseType.DISCOVERY
        elif workstream in ["Creative", "Content"]:
            return PhaseType.DEVELOPMENT
        elif workstream == "Technology":
            return PhaseType.PRODUCTION
        elif workstream == "Paid Media":
            return PhaseType.LAUNCH
        
        return PhaseType.DEVELOPMENT  # Default
    
    def detect_dependencies(self, tasks: List[Dict[str, Any]]) -> List[DependencyRelationship]:
        """Intelligently detect dependencies between tasks"""
        print(f"[Scheduler] detect_dependencies() called with {len(tasks)} tasks")
        dependencies = []
        task_lookup = {t['id']: t for t in tasks}
        
        total_comparisons = len(tasks) * (len(tasks) - 1)
        print(f"[Scheduler] Will check {total_comparisons} task pairs for dependencies")
        
        comparisons_done = 0
        for i, task in enumerate(tasks):
            if i % 3 == 0:  # Log progress every 3 tasks
                print(f"[Scheduler] Dependency check: task {i+1}/{len(tasks)}, {len(dependencies)} dependencies so far")
            
            task_name_lower = task['name'].lower()
            task_workstream = task.get('workstream', 'Strategy')
            
            for j, other_task in enumerate(tasks):
                if i == j:
                    continue
                    
                comparisons_done += 1
                other_name_lower = other_task['name'].lower()
                other_workstream = other_task.get('workstream', 'Strategy')
                
                # Check dependency rules
                for (pattern1, pattern2), rule in self.DEPENDENCY_RULES.items():
                    if pattern1 in other_name_lower and pattern2 in task_name_lower:
                        dep = DependencyRelationship(
                            predecessor=other_task['id'],
                            successor=task['id'],
                            type=rule['type'],
                            lag_days=rule.get('lag_days', 0),
                            lag_percentage=rule.get('lag_percentage', 0),
                            reason=rule['reason']
                        )
                        dependencies.append(dep)
                        break
                
                # Cross-workstream dependencies
                if task_workstream in ["Creative", "Content"] and other_workstream == "Strategy":
                    if "strategy" in other_name_lower or "brief" in other_name_lower:
                        dep = DependencyRelationship(
                            predecessor=other_task['id'],
                            successor=task['id'],
                            type="FS",
                            lag_days=1,
                            reason="Creative work requires strategy approval"
                        )
                        dependencies.append(dep)
                
                # Milestone dependencies
                if other_task.get('is_milestone') and task.get('phase_order', 0) > other_task.get('phase_order', 0):
                    dep = DependencyRelationship(
                        predecessor=other_task['id'],
                        successor=task['id'],
                        type="FS",
                        lag_days=0,
                        reason=f"Requires {other_task['name']} milestone"
                    )
                    dependencies.append(dep)
        
        print(f"[Scheduler] detect_dependencies() COMPLETE: found {len(dependencies)} dependencies")
        return dependencies
    
    def identify_parallel_opportunities(self, tasks: List[WorkstreamTask]) -> Dict[str, List[str]]:
        """Identify tasks that can run in parallel"""
        parallel_groups = defaultdict(list)
        
        # Group by workstream and phase
        workstream_phase_tasks = defaultdict(list)
        for task in tasks:
            key = f"{task.workstream}_{task.phase.value}"
            workstream_phase_tasks[key].append(task)
        
        # Tasks in different workstreams during same phase can often run in parallel
        for phase in PhaseType:
            phase_tasks = [t for t in tasks if t.phase == phase]
            workstreams_in_phase = defaultdict(list)
            
            for task in phase_tasks:
                workstreams_in_phase[task.workstream].append(task.id)
            
            # Different workstreams can run in parallel
            workstream_list = list(workstreams_in_phase.keys())
            for i, ws1 in enumerate(workstream_list):
                for ws2 in workstream_list[i+1:]:
                    # Check if workstreams can run in parallel
                    if self.can_run_parallel(ws1, ws2):
                        for task_id1 in workstreams_in_phase[ws1]:
                            parallel_groups[task_id1].extend(workstreams_in_phase[ws2])
                        for task_id2 in workstreams_in_phase[ws2]:
                            parallel_groups[task_id2].extend(workstreams_in_phase[ws1])
        
        return parallel_groups
    
    def can_run_parallel(self, workstream1: str, workstream2: str) -> bool:
        """Check if two workstreams can run in parallel"""
        # Define workstreams that typically can't run in parallel
        blocking_pairs = [
            ("Strategy", "Creative"),  # Creative needs strategy first
            ("Creative", "Production"),  # Production needs creative assets
            ("Technology", "Testing"),  # Testing needs dev complete
        ]
        
        for ws1, ws2 in blocking_pairs:
            if (workstream1 == ws1 and workstream2 == ws2) or \
               (workstream1 == ws2 and workstream2 == ws1):
                return False
        
        return True
    
    def calculate_slack_time(self, task: WorkstreamTask, all_tasks: List[WorkstreamTask]) -> int:
        """Calculate slack time for a task (float in CPM)"""
        # Find dependent tasks
        dependent_tasks = [
            t for t in all_tasks 
            if any(d.successor == t.id for d in task.dependencies)
        ]
        
        if not dependent_tasks:
            # No dependencies, slack is based on phase end
            return 5  # Default 5 days slack for independent tasks
        
        # Calculate slack based on earliest dependent task
        earliest_starts = [t.earliest_start for t in dependent_tasks if t.earliest_start]
        if not earliest_starts:
            return 5  # Default slack if no valid dependent starts
        
        min_dependent_start = min(earliest_starts)
        if min_dependent_start and task.end_date:
            slack_days = (min_dependent_start - task.end_date).days
            return max(0, slack_days)
        
        return 0
    
    def apply_resource_constraints(self, tasks: List[WorkstreamTask]) -> List[WorkstreamTask]:
        """Apply resource constraints to prevent overallocation"""
        # Track resource allocation by day
        resource_calendar = defaultdict(lambda: defaultdict(float))
        max_hours_per_day = 8.0
        
        # Sort tasks by priority (critical path first, then by start date)
        sorted_tasks = sorted(tasks, key=lambda t: (not t.is_critical, t.start_date))
        
        for task in sorted_tasks:
            if not task.resources:
                continue
                
            # Check resource availability
            current_date = task.start_date
            task_hours_remaining = task.hours
            days_needed = math.ceil(task_hours_remaining / max_hours_per_day)
            
            # Find available slots for resources
            while task_hours_remaining > 0:
                date_str = current_date.strftime('%Y-%m-%d')
                
                # Check if resources are available
                resources_available = all(
                    resource_calendar[date_str][resource] < max_hours_per_day
                    for resource in task.resources
                )
                
                if resources_available and current_date.weekday() < 5:  # Business days only
                    # Allocate hours for this day
                    daily_hours = min(max_hours_per_day, task_hours_remaining)
                    for resource in task.resources:
                        resource_calendar[date_str][resource] += daily_hours
                    task_hours_remaining -= daily_hours
                
                current_date += timedelta(days=1)
            
            # Update task end date if needed
            if current_date > task.end_date:
                task.end_date = current_date
                task.duration_days = (task.end_date - task.start_date).days
        
        return tasks
    
    def calculate_critical_path(self, tasks: List[WorkstreamTask]) -> List[str]:
        """Calculate critical path using CPM algorithm"""
        print(f"[Scheduler] calculate_critical_path() called with {len(tasks)} tasks")
        
        # Build adjacency list for dependencies
        predecessors = defaultdict(list)
        successors = defaultdict(list)
        
        for task in tasks:
            for dep in task.dependencies:
                predecessors[dep.successor].append(dep.predecessor)
                successors[dep.predecessor].append(dep.successor)
        
        print(f"[Scheduler] Built adjacency lists: {len(predecessors)} tasks with predecessors, {len(successors)} tasks with successors")
        
        # Forward pass - calculate earliest start/finish times
        print(f"[Scheduler] Starting forward pass...")
        earliest_start = {}
        earliest_finish = {}
        
        # Start with tasks that have no predecessors
        for task in tasks:
            if task.id not in predecessors or not predecessors[task.id]:
                earliest_start[task.id] = task.start_date
                earliest_finish[task.id] = task.end_date
        
        print(f"[Scheduler] Forward pass: {len(earliest_start)} tasks with no predecessors")
        
        # Process remaining tasks
        processed = set(earliest_start.keys())
        max_iterations = len(tasks) * 2  # Safety limit
        iteration = 0
        
        while len(processed) < len(tasks):
            iteration += 1
            if iteration > max_iterations:
                print(f"[Scheduler] WARNING: Forward pass exceeded max iterations ({max_iterations}), breaking to prevent infinite loop")
                print(f"[Scheduler] Processed {len(processed)}/{len(tasks)} tasks")
                break
            
            progress_made = False
            for task in tasks:
                if task.id in processed:
                    continue
                    
                # Check if all predecessors are processed
                if all(pred in processed for pred in predecessors.get(task.id, [])):
                    # Calculate earliest start based on predecessor finish times
                    if predecessors[task.id]:
                        pred_finishes = [earliest_finish[pred] for pred in predecessors[task.id] if pred in earliest_finish]
                        if pred_finishes:
                            max_pred_finish = max(pred_finishes)
                        else:
                            max_pred_finish = task.start_date
                        earliest_start[task.id] = max(task.start_date, max_pred_finish)
                        earliest_finish[task.id] = earliest_start[task.id] + timedelta(days=task.duration_days)
                    else:
                        earliest_start[task.id] = task.start_date
                        earliest_finish[task.id] = task.end_date
                    
                    processed.add(task.id)
                    progress_made = True
            
            # If we made no progress in this iteration, we have circular dependencies
            if not progress_made:
                print(f"[Scheduler] WARNING: Forward pass stuck with {len(processed)}/{len(tasks)} tasks processed - likely circular dependencies")
                # Add remaining tasks with default values to prevent crash
                for task in tasks:
                    if task.id not in processed:
                        earliest_start[task.id] = task.start_date
                        earliest_finish[task.id] = task.end_date
                        processed.add(task.id)
                break
        
        print(f"[Scheduler] Forward pass complete: processed {len(processed)}/{len(tasks)} tasks in {iteration} iterations")
        
        # Backward pass - calculate latest start/finish times
        # Check if we have any tasks to process
        if not earliest_finish:
            print("[Scheduler] Warning: No tasks with finish times found, returning empty critical path")
            return []
        
        print(f"[Scheduler] Starting backward pass...")
        project_end = max(earliest_finish.values())
        latest_start = {}
        latest_finish = {}
        
        # Start with tasks that have no successors
        for task in tasks:
            if task.id not in successors or not successors[task.id]:
                latest_finish[task.id] = project_end
                latest_start[task.id] = latest_finish[task.id] - timedelta(days=task.duration_days)
        
        print(f"[Scheduler] Backward pass: {len(latest_finish)} tasks with no successors")
        
        # Process remaining tasks in reverse
        processed = set(latest_finish.keys())
        max_iterations = len(tasks) * 2  # Safety limit
        iteration = 0
        
        while len(processed) < len(tasks):
            iteration += 1
            if iteration > max_iterations:
                print(f"[Scheduler] WARNING: Backward pass exceeded max iterations ({max_iterations}), breaking to prevent infinite loop")
                print(f"[Scheduler] Processed {len(processed)}/{len(tasks)} tasks")
                break
            
            progress_made = False
            for task in reversed(tasks):
                if task.id in processed:
                    continue
                    
                # Check if all successors are processed
                if all(succ in processed for succ in successors.get(task.id, [])):
                    if successors[task.id]:
                        succ_starts = [latest_start[succ] for succ in successors[task.id] if succ in latest_start]
                        if succ_starts:
                            min_succ_start = min(succ_starts)
                        else:
                            min_succ_start = project_end
                        latest_finish[task.id] = min_succ_start
                        latest_start[task.id] = latest_finish[task.id] - timedelta(days=task.duration_days)
                    else:
                        latest_finish[task.id] = project_end
                        latest_start[task.id] = latest_finish[task.id] - timedelta(days=task.duration_days)
                    
                    processed.add(task.id)
                    progress_made = True
            
            # If we made no progress in this iteration, we have circular dependencies
            if not progress_made:
                print(f"[Scheduler] WARNING: Backward pass stuck with {len(processed)}/{len(tasks)} tasks processed - likely circular dependencies")
                # Add remaining tasks with default values to prevent crash
                for task in tasks:
                    if task.id not in processed:
                        latest_finish[task.id] = project_end
                        latest_start[task.id] = latest_finish[task.id] - timedelta(days=task.duration_days)
                        processed.add(task.id)
                break
        
        print(f"[Scheduler] Backward pass complete: processed {len(processed)}/{len(tasks)} tasks in {iteration} iterations")
        
        # Identify critical path - tasks with zero slack
        print(f"[Scheduler] Calculating slack and identifying critical path...")
        critical_path = []
        for task in tasks:
            if task.id in earliest_start and task.id in latest_start:
                slack = (latest_start[task.id] - earliest_start[task.id]).days
                if slack <= 0:  # Zero or negative slack means critical path
                    critical_path.append(task.id)
                task.slack_days = slack
                task.earliest_start = earliest_start[task.id]
                task.latest_start = latest_start[task.id]
        
        print(f"[Scheduler] Critical path identified: {len(critical_path)} tasks on critical path")
        print(f"[Scheduler] calculate_critical_path() COMPLETE")
        return critical_path
    
    async def optimize_timeline(
        self,
        deliverables: List[Dict[str, Any]],
        project_start: datetime,
        optimization_mode: str = "balanced"
    ) -> Dict[str, Any]:
        """Generate optimized timeline with parallel workstreams"""
        
        print(f"[Scheduler] optimize_timeline STARTED with {len(deliverables)} deliverables")
        
        tasks = []
        
        # Phase 1: Create tasks and assign to workstreams/phases
        print(f"[Scheduler] Phase 1: Creating tasks...")
        for i, deliv in enumerate(deliverables):
            if i % 5 == 0:  # Log every 5th deliverable
                print(f"[Scheduler] Creating task {i+1}/{len(deliverables)}")
            workstream = self.identify_workstream(
                deliv.get('deliverable_name', ''),
                deliv.get('department')
            )
            
            phase = self.identify_phase(
                deliv.get('deliverable_name', ''),
                workstream
            )
            
            # Calculate duration based on hours
            hours = deliv.get('total_hours', 40)
            duration_days = self.calculate_duration_from_hours(hours, optimization_mode)
            
            # Determine initial start date based on phase
            phase_config = next((p for p in PROJECT_PHASES if p.name == phase.value), None)
            if phase_config:
                phase_start_offset = (phase_config.start_week - 1) * 5  # Business days
                task_start = self.add_business_days(project_start, phase_start_offset)
            else:
                task_start = project_start
            
            task = WorkstreamTask(
                id=f"task_{deliv['deliverable_code']}",
                name=deliv.get('deliverable_name', ''),
                deliverable_code=deliv['deliverable_code'],
                workstream=workstream,
                phase=phase,
                start_date=task_start,
                end_date=self.add_business_days(task_start, duration_days),
                duration_days=duration_days,
                hours=hours,
                resources=self.identify_resources(deliv),
                is_retainer=deliv.get('is_retainer', False)
            )
            
            tasks.append(task)
            self.workstreams[workstream].append(task)
            self.phases[phase].append(task)
        
        print(f"[Scheduler] Phase 1 complete: {len(tasks)} tasks created")
        
        # Phase 2: Detect and apply dependencies
        print(f"[Scheduler] Phase 2: Detecting dependencies...")
        raw_dependencies = self.detect_dependencies(
            [{'id': t.id, 'name': t.name, 'workstream': t.workstream} for t in tasks]
        )
        print(f"[Scheduler] Phase 2 complete: {len(raw_dependencies)} dependencies detected")
        
        # Apply dependencies to tasks
        for dep in raw_dependencies:
            task = next((t for t in tasks if t.id == dep.successor), None)
            if task:
                task.dependencies.append(dep)
        
        # Phase 3: Identify parallel opportunities
        print(f"[Scheduler] Phase 3: Identifying parallel opportunities...")
        parallel_opps = self.identify_parallel_opportunities(tasks)
        print(f"[Scheduler] Phase 3 complete: {len(parallel_opps)} parallel opportunities found")
        for task_id, parallel_ids in parallel_opps.items():
            task = next((t for t in tasks if t.id == task_id), None)
            if task:
                task.parallel_tasks = parallel_ids
        
        # Phase 4: Apply scheduling constraints
        print(f"[Scheduler] Phase 4: Applying scheduling constraints...")
        tasks = await self.apply_scheduling_constraints(tasks, optimization_mode)
        print(f"[Scheduler] Phase 4 complete: Scheduling constraints applied")
        
        # Phase 5: Calculate critical path
        print(f"[Scheduler] Phase 5: Calculating critical path...")
        critical_path_ids = self.calculate_critical_path(tasks)
        print(f"[Scheduler] Phase 5 complete: {len(critical_path_ids)} tasks on critical path")
        for task in tasks:
            task.is_critical = task.id in critical_path_ids
        
        # Phase 6: Apply resource constraints
        print(f"[Scheduler] Phase 6: Applying resource constraints...")
        tasks = self.apply_resource_constraints(tasks)
        print(f"[Scheduler] Phase 6 complete: Resource constraints applied")
        
        # Phase 7: Add milestones
        print(f"[Scheduler] Phase 7: Adding milestones...")
        milestones = self.add_milestones(tasks, project_start)
        tasks.extend(milestones)
        print(f"[Scheduler] Phase 7 complete: {len(milestones)} milestones added")
        
        print(f"[Scheduler] Formatting timeline response...")
        result = self.format_timeline_response(tasks, optimization_mode)
        print(f"[Scheduler] optimize_timeline COMPLETE - returning {len(result.get('tasks', []))} tasks")
        return result
    
    async def apply_scheduling_constraints(
        self,
        tasks: List[WorkstreamTask],
        optimization_mode: str
    ) -> List[WorkstreamTask]:
        """Apply scheduling constraints based on dependencies"""
        
        # Sort tasks topologically based on dependencies
        sorted_tasks = self.topological_sort(tasks)
        
        for task in sorted_tasks:
            if not task.dependencies:
                continue
                
            for dep in task.dependencies:
                pred_task = next((t for t in tasks if t.id == dep.predecessor), None)
                if not pred_task:
                    continue
                
                if dep.type == "FS":  # Finish-to-Start
                    # Task starts after predecessor finishes plus lag
                    min_start = self.add_business_days(pred_task.end_date, dep.lag_days)
                    if task.start_date < min_start:
                        task.start_date = min_start
                        task.end_date = self.add_business_days(task.start_date, task.duration_days)
                        
                elif dep.type == "SS":  # Start-to-Start
                    # Task can start when predecessor reaches certain percentage
                    if dep.lag_percentage > 0:
                        pred_partial_days = int(pred_task.duration_days * dep.lag_percentage)
                        min_start = self.add_business_days(pred_task.start_date, pred_partial_days)
                    else:
                        min_start = self.add_business_days(pred_task.start_date, dep.lag_days)
                    
                    if task.start_date < min_start:
                        task.start_date = min_start
                        task.end_date = self.add_business_days(task.start_date, task.duration_days)
        
        return tasks
    
    def topological_sort(self, tasks: List[WorkstreamTask]) -> List[WorkstreamTask]:
        """Sort tasks topologically based on dependencies"""
        print(f"[Scheduler] topological_sort() called with {len(tasks)} tasks")
        
        # Build adjacency list
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        task_map = {t.id: t for t in tasks}
        
        total_deps = 0
        for task in tasks:
            for dep in task.dependencies:
                graph[dep.predecessor].append(task.id)
                in_degree[task.id] += 1
                total_deps += 1
        
        print(f"[Scheduler] Built dependency graph: {total_deps} total dependencies")
        
        # Start with tasks that have no dependencies
        queue = [t.id for t in tasks if in_degree[t.id] == 0]
        sorted_tasks = []
        
        print(f"[Scheduler] Starting with {len(queue)} tasks that have no dependencies")
        
        iterations = 0
        max_iterations = len(tasks) * 2  # Safety limit
        
        while queue:
            iterations += 1
            if iterations > max_iterations:
                print(f"[Scheduler] WARNING: topological_sort exceeded max iterations ({max_iterations}), breaking to prevent infinite loop")
                break
                
            task_id = queue.pop(0)
            sorted_tasks.append(task_map[task_id])
            
            # Process dependent tasks
            for successor in graph[task_id]:
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    queue.append(successor)
        
        print(f"[Scheduler] Topological sort completed {len(sorted_tasks)}/{len(tasks)} tasks in {iterations} iterations")
        
        # Add any remaining tasks (cycles or disconnected)
        remaining_count = 0
        for task in tasks:
            if task not in sorted_tasks:
                sorted_tasks.append(task)
                remaining_count += 1
        
        if remaining_count > 0:
            print(f"[Scheduler] WARNING: Added {remaining_count} tasks with circular dependencies or disconnected from graph")
        
        print(f"[Scheduler] topological_sort() COMPLETE: returning {len(sorted_tasks)} tasks")
        return sorted_tasks
    
    def add_milestones(self, tasks: List[WorkstreamTask], project_start: datetime) -> List[WorkstreamTask]:
        """Add project milestones"""
        milestones = []
        
        for phase_config in PROJECT_PHASES:
            if not phase_config.milestone:
                continue
                
            # Find tasks in this phase
            phase_tasks = [t for t in tasks if t.phase.value == phase_config.name]
            if not phase_tasks:
                continue
            
            # Milestone occurs at the end of the phase's critical tasks
            critical_in_phase = [t for t in phase_tasks if t.is_critical]
            if critical_in_phase:
                milestone_date = max(t.end_date for t in critical_in_phase)
            elif phase_tasks:
                milestone_date = max(t.end_date for t in phase_tasks)
            else:
                # Skip milestone if no tasks in phase
                continue
            
            milestone = WorkstreamTask(
                id=f"milestone_{phase_config.name.lower().replace(' ', '_')}",
                name=f"🎯 {phase_config.milestone}",
                deliverable_code=f"milestone_{phase_config.name.lower()}",
                workstream="Project Management",
                phase=PhaseType(phase_config.name),
                start_date=milestone_date,
                end_date=milestone_date,
                duration_days=0,
                hours=0,
                is_milestone=True,
                is_critical=True
            )
            
            milestones.append(milestone)
        
        return milestones
    
    def calculate_duration_from_hours(self, hours: float, optimization_mode: str) -> int:
        """
        Calculate duration in business days using Workfront normalization formula.
        This ensures Work ≤ Duration for all tasks and matches XML export expectations.
        
        Formula: required_days = max(1, ceil(hours / 8.0))
        Uses 8-hour workday aligned with MinutesPerDay=480 constant.
        Milestone exemption: 0 hours → 0 days
        """
        # WORKFRONT NORMALIZATION: Milestone exemption (0 hours stays 0 days)
        if hours == 0:
            return 0
        
        # WORKFRONT NORMALIZATION: Use ceil(hours / 8.0) formula
        # This guarantees Work ≤ Duration in all cases
        required_days = max(1, math.ceil(hours / 8.0))
        
        print(f"[Scheduler] Duration calc: {hours}h → {required_days} days (Workfront formula)")
        
        return required_days
    
    def add_business_days(self, start_date: datetime, days: int) -> datetime:
        """Add business days to a date (skip weekends)"""
        current = start_date
        days_added = 0
        
        while days_added < days:
            current += timedelta(days=1)
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                days_added += 1
        
        return current
    
    def identify_resources(self, deliverable: Dict[str, Any]) -> List[str]:
        """Identify required resources for a deliverable"""
        resources = []
        
        # Extract from roles if available
        if 'roles' in deliverable:
            resources.extend(deliverable['roles'])
        
        # Infer from department
        dept = deliverable.get('department', 'Strategy')
        if dept == "Creative":
            resources.extend(["Designer", "Art Director"])
        elif dept == "Strategy":
            resources.extend(["Strategist", "Analyst"])
        elif dept == "Technology":
            resources.extend(["Developer", "Tech Lead"])
        elif dept == "Paid Media":
            resources.extend(["Media Planner", "PPC Specialist"])
        elif dept == "Content":
            resources.extend(["Content Writer", "Editor"])
        
        return list(set(resources))  # Remove duplicates
    
    def format_timeline_response(self, tasks: List[WorkstreamTask], optimization_mode: str) -> Dict[str, Any]:
        """Format timeline for response"""
        
        # Convert tasks to Gantt format
        gantt_tasks = []
        for task in tasks:
            gantt_task = {
                "id": task.id,
                "name": task.name,
                "start": task.start_date.strftime('%Y-%m-%d'),
                "end": task.end_date.strftime('%Y-%m-%d'),
                "progress": 0,
                "dependencies": ",".join([d.predecessor for d in task.dependencies]),
                "custom_class": f"workstream-{task.workstream.lower().replace(' ', '-')}",
                "deliverable_code": task.deliverable_code,
                "workstream": task.workstream,
                "phase": task.phase.value,
                "hours": task.hours,
                "is_milestone": task.is_milestone,
                "critical_path": task.is_critical,
                "slack_days": task.slack_days,
                "parallel_tasks": task.parallel_tasks,
                "is_retainer": task.is_retainer
            }
            gantt_tasks.append(gantt_task)
        
        # Calculate project metrics
        if not tasks:
            print("[TIMELINE] Warning: No tasks provided for timeline optimization")
            return {
                "timeline": [],
                "milestones": [],
                "critical_path": [],
                "duration_days": 0,
                "resource_utilization": {}
            }
        
        project_start = min(t.start_date for t in tasks)
        project_end = max(t.end_date for t in tasks)
        total_days = (project_end - project_start).days
        
        # Build reasoning
        critical_tasks = [t for t in tasks if t.is_critical]
        parallel_groups = {}
        for task in tasks:
            if task.parallel_tasks:
                parallel_groups[task.name] = [
                    next(t.name for t in tasks if t.id == pid)
                    for pid in task.parallel_tasks[:3]  # Limit to 3 for display
                ]
        
        reasoning = {
            "overall_strategy": f"Timeline optimized for {optimization_mode} delivery with {len(self.workstreams)} parallel workstreams",
            "critical_path_explanation": f"{len(critical_tasks)} tasks on critical path driving {total_days}-day timeline",
            "phase_breakdown": {
                phase.value: {
                    "tasks": len(self.phases.get(phase, [])),
                    "workstreams": list(set(t.workstream for t in self.phases.get(phase, [])))
                }
                for phase in PhaseType
            },
            "workstream_allocation": {
                ws: len(tasks_list) for ws, tasks_list in self.workstreams.items()
            },
            "parallel_opportunities": [
                f"{name} can run parallel with: {', '.join(parallel[:3])}"
                for name, parallel in parallel_groups.items()
            ][:10],  # Limit display
            "dependency_insights": [
                f"{dep.successor} depends on {dep.predecessor}: {dep.reason}"
                for task in tasks
                for dep in task.dependencies[:5]  # Sample dependencies
            ][:10],
            "optimization_notes": [
                f"Applied {optimization_mode} optimization strategy",
                f"Identified {len(parallel_groups)} parallel work opportunities",
                f"Added {sum(1 for t in tasks if t.is_milestone)} project milestones",
                f"Average task slack: {sum(t.slack_days for t in tasks) / len(tasks):.1f} days"
            ],
            "risk_factors": self.identify_risks(tasks)
        }
        
        # WORKFRONT NORMALIZATION: Create normalized schedule for single source of truth
        # This schedule will be persisted to SCENARIO_STORE and used by both UI and XML exporter
        normalized_schedule = {}
        for task in tasks:
            # Calculate duration in hours and minutes using Workfront formula
            duration_hours = task.duration_days * 8.0  # 8-hour workdays
            duration_minutes = task.duration_days * 480  # 480 minutes per day
            
            # Store normalized schedule data for this task
            normalized_schedule[task.id] = {
                "Start": task.start_date.strftime('%Y-%m-%dT%H:%M:%S'),
                "Finish": task.end_date.strftime('%Y-%m-%dT%H:%M:%S'),
                "PlannedHours": task.hours,
                "DurationHours": duration_hours,
                "DurationMinutes": duration_minutes,
                "DurationDays": task.duration_days,
                "IsMillestone": task.is_milestone,
                "IsCritical": task.is_critical,
                "Workstream": task.workstream,
                "Phase": task.phase.value,
                "DeliverableCode": task.deliverable_code
            }
            
            print(f"[Scheduler] Normalized schedule for {task.name[:40]}: {task.hours}h work → {task.duration_days} days ({duration_hours}h duration)")
        
        return {
            "tasks": gantt_tasks,
            "reasoning": reasoning,
            "metadata": {
                "total_duration_days": total_days,
                "project_start": project_start.strftime('%Y-%m-%d'),
                "project_end": project_end.strftime('%Y-%m-%d'),
                "total_tasks": len(tasks),
                "critical_tasks": len(critical_tasks),
                "milestones": sum(1 for t in tasks if t.is_milestone),
                "workstreams": list(self.workstreams.keys()),
                "phases": [phase.value for phase in PhaseType if self.phases.get(phase)],
                "optimization_mode": optimization_mode,
                "schedule_version": "workfront_normalized_v1"  # Version for migration tracking
            },
            "normalized_schedule": normalized_schedule  # Single source of truth for UI and XML
        }
    
    def identify_risks(self, tasks: List[WorkstreamTask]) -> List[str]:
        """Identify potential scheduling risks"""
        risks = []
        
        # Check for resource overallocation
        resource_loads = defaultdict(float)
        for task in tasks:
            for resource in task.resources:
                resource_loads[resource] += task.hours
        
        overloaded = [r for r, hours in resource_loads.items() if hours > 200]
        if overloaded:
            risks.append(f"Resource overallocation: {', '.join(overloaded[:3])}")
        
        # Check for tight critical path
        critical_tasks = [t for t in tasks if t.is_critical]
        if len(critical_tasks) > len(tasks) * 0.6:
            risks.append("Over 60% of tasks on critical path - limited flexibility")
        
        # Check for phase overlaps
        phase_overlaps = []
        for i, phase1 in enumerate(PROJECT_PHASES[:-1]):
            phase2 = PROJECT_PHASES[i + 1]
            if phase1.start_week + phase1.duration_weeks > phase2.start_week + 2:
                phase_overlaps.append(f"{phase1.name} and {phase2.name}")
        
        if phase_overlaps:
            risks.append(f"Significant phase overlaps: {', '.join(phase_overlaps)}")
        
        # Check for dependencies across many workstreams
        cross_stream_deps = 0
        for task in tasks:
            for dep in task.dependencies:
                dep_task = next((t for t in tasks if t.id == dep.predecessor), None)
                if dep_task and dep_task.workstream != task.workstream:
                    cross_stream_deps += 1
        
        if cross_stream_deps > len(tasks) * 0.3:
            risks.append("High cross-team dependencies may cause coordination challenges")
        
        return risks[:5]  # Limit to top 5 risks

# Async function to generate timeline using the scheduler
async def generate_intelligent_timeline(
    deliverables: List[Dict[str, Any]],
    project_start: Optional[str] = None,
    optimization_mode: str = "balanced"
) -> Dict[str, Any]:
    """Generate an intelligent timeline with parallel workstreams"""
    
    # Parse start date
    if project_start:
        start_date = datetime.fromisoformat(project_start)
    else:
        # Default to next Monday
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7 or 7
        start_date = today + timedelta(days=days_until_monday)
    
    # Create scheduler instance
    scheduler = TimelineScheduler()
    
    # Generate optimized timeline
    timeline = await scheduler.optimize_timeline(
        deliverables,
        start_date,
        optimization_mode
    )
    
    return timeline