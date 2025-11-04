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
    # Support both OPENAI_API_KEY and Open_AI_Key secret names
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("Open_AI_Key")
    if api_key:
        client = AsyncOpenAI(api_key=api_key)
        OPENAI_AVAILABLE = True
    else:
        print(f"[AI Timeline] No OpenAI API key found, AI features will be disabled")
        OPENAI_AVAILABLE = False
        client = None
except (ImportError, ModuleNotFoundError) as e:
    print(f"[AI Timeline] OpenAI module not installed: {e}")
    OPENAI_AVAILABLE = False
    client = None
except (ValueError, TypeError) as e:
    print(f"[AI Timeline] OpenAI configuration error: {e}")
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
    is_retainer: bool = False  # Flag for retainer tasks
    retainer_month: Optional[int] = None  # Month number for retainer tasks
    monthly_hours: Optional[float] = None  # Monthly hours for retainer

    # CPM Enhanced Fields
    early_start: Optional[float] = None  # Days from project start
    early_finish: Optional[float] = None  
    late_start: Optional[float] = None
    late_finish: Optional[float] = None
    total_float: float = 0  # Total slack (Late Start - Early Start)
    free_float: float = 0  # Float without delaying successors
    is_critical: bool = False  # True if on critical path (total_float = 0)
    buffer_days: float = 0  # Project or feeding buffer in days
    buffer_type: Optional[str] = None  # "project", "feeding", or None
    resource_level: float = 1.0  # Resource allocation level (0-1.0)
    leveled_start: Optional[str] = None  # Start after resource leveling
    leveled_end: Optional[str] = None  # End after resource leveling

    def to_gantt_format(self) -> Dict[str, Any]:
        """Convert to Frappe Gantt format with enhanced CPM data and governance marking"""
        result = {
            "id": self.id,
            "name": self.name,
            "start": self.leveled_start or self.start_date,  # Use leveled dates if available
            "end": self.leveled_end or self.end_date,
            "progress": self.progress,
            "dependencies": ",".join(self.dependencies) if self.dependencies else "",
            "custom_class": f"dept-{self.department.lower().replace(' ', '-')}",
            "deliverable_code": self.deliverable_code,
            "component": self.component,
            "department": self.department,
            "hours": self.hours,
            "is_milestone": self.is_milestone,
            "critical_path": self.is_critical,  # Use enhanced critical flag

            # CPM Enhanced Fields
            "is_critical": self.is_critical,
            "total_float": self.total_float,
            "free_float": self.free_float,
            "early_start": self.early_start,
            "early_finish": self.early_finish,
            "late_start": self.late_start,
            "late_finish": self.late_finish,
            "resource_level": self.resource_level
        }

        # Add governance information if present
        if hasattr(self, 'is_governance') and self.is_governance:
            result["is_governance"] = True
            result["governance_type"] = getattr(self, 'governance_type', 'governance')
            result["custom_class"] += " governance-milestone"

            # Add specific governance metadata
            if hasattr(self, 'governance_percentage'):
                result["governance_percentage"] = self.governance_percentage

        # Add buffer information if present
        if self.buffer_days > 0:
            result["buffer_days"] = self.buffer_days
            result["buffer_type"] = self.buffer_type

        # Add retainer-specific fields
        if self.is_retainer:
            result["is_retainer"] = True
            result["retainer_month"] = self.retainer_month
            result["monthly_hours"] = self.monthly_hours
            result["custom_class"] += " retainer-task"

        # Add visual indicator for critical tasks
        if self.is_critical:
            result["custom_class"] += " critical-task"

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

class CPMCalculator:
    """Enhanced Critical Path Method calculator with CCPM and resource leveling"""

    def __init__(self, tasks: List[TimelineTask]):
        self.tasks = tasks
        self.task_map = {t.id: t for t in tasks}
        self.successors = self._build_successor_map()

    def _build_successor_map(self) -> Dict[str, List[str]]:
        """Build a map of task successors for free float calculation"""
        successors = {task.id: [] for task in self.tasks}
        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id in successors:
                    successors[dep_id].append(task.id)
        return successors

    def calculate_cpm(self) -> Tuple[Set[str], Dict[str, Any]]:
        """
        Perform complete CPM analysis with float calculations
        Returns: (critical_path_ids, cpm_metrics)
        """
        # Forward pass: Calculate Early Start and Early Finish
        self._forward_pass()

        # Backward pass: Calculate Late Start and Late Finish
        project_duration = self._backward_pass()

        # Calculate floats and identify critical path
        critical_path_ids = self._calculate_floats()

        # Calculate free float for each task
        self._calculate_free_float()

        # Generate CPM metrics
        metrics = self._generate_cpm_metrics(critical_path_ids, project_duration)

        return critical_path_ids, metrics

    def _forward_pass(self):
        """Calculate Early Start and Early Finish for all tasks"""
        # Sort tasks topologically to process in dependency order
        sorted_tasks = self._topological_sort()

        for task in sorted_tasks:
            if not task.dependencies:
                # No dependencies: can start at project start
                task.early_start = 0
            else:
                # Start after all dependencies finish
                max_finish = 0
                for dep_id in task.dependencies:
                    if dep_id in self.task_map:
                        dep_task = self.task_map[dep_id]
                        if dep_task.early_finish is not None:
                            max_finish = max(max_finish, dep_task.early_finish)
                task.early_start = max_finish

            # Calculate duration and early finish
            if task.start_date and task.end_date:
                duration = self._calculate_duration(task.start_date, task.end_date)
                task.early_finish = task.early_start + duration
            else:
                task.early_finish = task.early_start

    def _backward_pass(self) -> float:
        """Calculate Late Start and Late Finish for all tasks"""
        # Find project end date (maximum early finish)
        project_end = max((t.early_finish for t in self.tasks if t.early_finish is not None), default=0)

        # Process tasks in reverse topological order
        for task in reversed(self._topological_sort()):
            # Find successors
            successor_ids = self.successors.get(task.id, [])

            if not successor_ids:
                # No successors: can finish at project end
                task.late_finish = project_end
            else:
                # Must finish before earliest successor starts
                min_start = project_end
                for succ_id in successor_ids:
                    if succ_id in self.task_map:
                        succ_task = self.task_map[succ_id]
                        if succ_task.late_start is not None:
                            min_start = min(min_start, succ_task.late_start)
                task.late_finish = min_start

            # Calculate late start
            duration = self._calculate_duration(task.start_date, task.end_date)
            task.late_start = task.late_finish - duration

        return project_end

    def _calculate_floats(self) -> Set[str]:
        """Calculate Total Float and identify critical tasks"""
        critical_path_ids = set()

        for task in self.tasks:
            if task.early_start is not None and task.late_start is not None:
                # Total Float = Late Start - Early Start
                task.total_float = task.late_start - task.early_start

                # Task is critical if total float is zero (or very close)
                if abs(task.total_float) < 0.01:  # Allow for floating point errors
                    task.is_critical = True
                    critical_path_ids.add(task.id)
                else:
                    task.is_critical = False
            else:
                task.total_float = 0
                task.is_critical = False

        return critical_path_ids

    def _calculate_free_float(self):
        """Calculate Free Float for each task"""
        for task in self.tasks:
            if task.early_finish is None:
                task.free_float = 0
                continue

            successor_ids = self.successors.get(task.id, [])
            if not successor_ids:
                # No successors: free float equals total float
                task.free_float = task.total_float
            else:
                # Free float = minimum (successor ES - task EF)
                min_slack = float('inf')
                for succ_id in successor_ids:
                    if succ_id in self.task_map:
                        succ_task = self.task_map[succ_id]
                        if succ_task.early_start is not None:
                            slack = succ_task.early_start - task.early_finish
                            min_slack = min(min_slack, slack)
                task.free_float = max(0, min_slack)

    def _topological_sort(self) -> List[TimelineTask]:
        """Sort tasks in topological order (dependencies first)"""
        visited = set()
        stack = []

        def dfs(task_id):
            if task_id in visited:
                return
            visited.add(task_id)
            task = self.task_map.get(task_id)
            if task:
                for dep_id in task.dependencies:
                    if dep_id in self.task_map:
                        dfs(dep_id)
                stack.append(task)

        for task in self.tasks:
            dfs(task.id)

        return stack

    def _calculate_duration(self, start_date: str, end_date: str) -> float:
        """Calculate duration in business days"""
        if not start_date or not end_date:
            return 0
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)

            # Count only business days
            business_days = 0
            current = start
            while current <= end:
                if current.weekday() < 5:  # Monday = 0, Friday = 4
                    business_days += 1
                current += timedelta(days=1)

            return max(1, business_days)  # Minimum 1 day
        except (ValueError, TypeError) as e:
            # Log the specific error for debugging
            print(f"[CPM] Error calculating duration between {start_date} and {end_date}: {e}")
            return 1  # Default to 1 day if dates are invalid

    def _generate_cpm_metrics(self, critical_path_ids: Set[str], project_duration: float) -> Dict[str, Any]:
        """Generate comprehensive CPM metrics"""
        critical_tasks = [t for t in self.tasks if t.id in critical_path_ids]
        non_critical_tasks = [t for t in self.tasks if t.id not in critical_path_ids]

        return {
            "project_duration": project_duration,
            "critical_path_count": len(critical_path_ids),
            "total_tasks": len(self.tasks),
            "critical_percentage": (len(critical_path_ids) / len(self.tasks) * 100) if self.tasks else 0,
            "average_total_float": sum(t.total_float for t in non_critical_tasks) / len(non_critical_tasks) if non_critical_tasks else 0,
            "max_total_float": max((t.total_float for t in self.tasks), default=0),
            "critical_path_ids": list(critical_path_ids)
        }


class CCPMBufferManager:
    """Critical Chain Project Management buffer calculator"""

    BUFFER_PERCENTAGE = 0.15  # 15% buffer by default
    FEEDING_BUFFER_PERCENTAGE = 0.10  # 10% feeding buffer

    def add_project_buffer(self, tasks: List[TimelineTask], critical_path_ids: Set[str]) -> TimelineTask:
        """Add project buffer at the end of critical path"""
        # Find the last critical task
        critical_tasks = [t for t in tasks if t.id in critical_path_ids]
        if not critical_tasks:
            return None

        last_critical = max(critical_tasks, key=lambda t: t.early_finish or 0)

        # Calculate buffer duration (percentage of critical path length)
        critical_duration = last_critical.early_finish or 0
        buffer_duration = max(1, int(critical_duration * self.BUFFER_PERCENTAGE))

        # Create buffer task
        buffer_start = datetime.fromisoformat(last_critical.end_date)
        buffer_end = buffer_start + timedelta(days=buffer_duration)

        buffer_task = TimelineTask(
            id=f"buffer_project_{last_critical.id}",
            name="🛡️ Project Buffer",
            deliverable_code="BUFFER",
            deliverable_name="Project Buffer",
            department="Project Management",
            start_date=buffer_start.strftime('%Y-%m-%d'),
            end_date=buffer_end.strftime('%Y-%m-%d'),
            dependencies=[last_critical.id],
            is_milestone=True,
            buffer_days=buffer_duration,
            buffer_type="project",
            color="#FF6B6B"
        )

        return buffer_task

    def add_feeding_buffers(self, tasks: List[TimelineTask], critical_path_ids: Set[str]) -> List[TimelineTask]:
        """Add feeding buffers where non-critical paths join critical path"""
        feeding_buffers = []

        for task in tasks:
            if task.id in critical_path_ids:
                # Check predecessors
                for dep_id in task.dependencies:
                    dep_task = next((t for t in tasks if t.id == dep_id), None)
                    if dep_task and dep_task.id not in critical_path_ids:
                        # Non-critical task feeding into critical path
                        if dep_task.total_float > 2:  # Only add buffer if significant float
                            buffer_duration = max(1, int(dep_task.total_float * self.FEEDING_BUFFER_PERCENTAGE))

                            buffer_task = TimelineTask(
                                id=f"buffer_feeding_{dep_task.id}_{task.id}",
                                name=f"⏱️ Feeding Buffer",
                                deliverable_code="BUFFER",
                                deliverable_name="Feeding Buffer",
                                department=dep_task.department,
                                start_date=dep_task.end_date,
                                end_date=dep_task.end_date,  # Will be adjusted
                                dependencies=[dep_task.id],
                                buffer_days=buffer_duration,
                                buffer_type="feeding",
                                color="#FFA500"
                            )

                            # Adjust end date
                            start = datetime.fromisoformat(buffer_task.start_date)
                            end = start + timedelta(days=buffer_duration)
                            buffer_task.end_date = end.strftime('%Y-%m-%d')

                            feeding_buffers.append(buffer_task)

        return feeding_buffers

    def calculate_confidence_level(self, tasks: List[TimelineTask]) -> float:
        """Calculate project confidence level based on buffer consumption"""
        # This is a simplified confidence calculation
        # In practice, would track actual buffer consumption over time

        total_buffer = sum(t.buffer_days for t in tasks if t.buffer_type)
        critical_tasks = [t for t in tasks if t.is_critical]

        if not critical_tasks:
            return 0.5

        # Base confidence on buffer size relative to critical path
        critical_duration = max((t.early_finish or 0 for t in critical_tasks), default=0)

        if critical_duration > 0:
            buffer_ratio = total_buffer / critical_duration
            # More buffer = higher confidence (up to a point)
            confidence = min(0.95, 0.5 + (buffer_ratio * 2))
        else:
            confidence = 0.5

        return confidence


class ResourceLeveler:
    """Resource leveling to smooth resource allocation"""

    def __init__(self, tasks: List[TimelineTask]):
        self.tasks = tasks
        self.resources = self._extract_resources()

    def _extract_resources(self) -> Dict[str, List[TimelineTask]]:
        """Group tasks by resource/department"""
        resources = {}
        for task in self.tasks:
            resource = task.department
            if resource not in resources:
                resources[resource] = []
            resources[resource].append(task)
        return resources

    def level_resources(self, critical_path_ids: Set[str]) -> None:
        """Level resources by adjusting non-critical task timing"""
        for resource, resource_tasks in self.resources.items():
            # Sort tasks by early start
            resource_tasks.sort(key=lambda t: t.early_start or 0)

            # Check for overallocation
            self._smooth_resource_usage(resource_tasks, critical_path_ids)

    def _smooth_resource_usage(self, resource_tasks: List[TimelineTask], critical_path_ids: Set[str]):
        """Smooth resource usage by delaying non-critical tasks"""
        for i in range(len(resource_tasks) - 1):
            current_task = resource_tasks[i]
            next_task = resource_tasks[i + 1]

            # Don't adjust critical tasks
            if current_task.id in critical_path_ids or next_task.id in critical_path_ids:
                continue

            # Check for overlap
            if current_task.early_finish and next_task.early_start:
                if current_task.early_finish > next_task.early_start:
                    # Overlap detected - delay the non-critical task
                    if next_task.total_float > 0:
                        # Calculate delay needed
                        delay = min(
                            current_task.early_finish - next_task.early_start,
                            next_task.total_float
                        )

                        # Adjust dates
                        if next_task.start_date and next_task.end_date:
                            start = datetime.fromisoformat(next_task.start_date)
                            end = datetime.fromisoformat(next_task.end_date)

                            new_start = start + timedelta(days=int(delay))
                            new_end = end + timedelta(days=int(delay))

                            next_task.leveled_start = new_start.strftime('%Y-%m-%d')
                            next_task.leveled_end = new_end.strftime('%Y-%m-%d')
                            next_task.resource_level = 0.8  # Indicate resource adjustment

    def calculate_resource_utilization(self) -> Dict[str, float]:
        """Calculate resource utilization percentage"""
        utilization = {}

        for resource, resource_tasks in self.resources.items():
            if not resource_tasks:
                utilization[resource] = 0
                continue

            # Calculate total available time
            project_start = min((t.early_start or 0 for t in resource_tasks), default=0)
            project_end = max((t.early_finish or 0 for t in resource_tasks), default=0)
            available_days = project_end - project_start

            # Calculate utilized time
            utilized_days = sum(
                (t.early_finish or 0) - (t.early_start or 0)
                for t in resource_tasks
            )

            if available_days > 0:
                utilization[resource] = min(1.0, utilized_days / available_days)
            else:
                utilization[resource] = 0

        return utilization


class GovernanceFramework:
    """Comprehensive governance framework for project management milestones"""

    def __init__(self, project_start: datetime, project_end: datetime, tasks: List[TimelineTask], project_complexity: str = "medium"):
        """
        Initialize governance framework

        Args:
            project_start: Project start date
            project_end: Project end date
            tasks: List of timeline tasks
            project_complexity: "low", "medium", or "high"
        """
        self.project_start = project_start
        self.project_end = project_end
        self.tasks = tasks
        self.project_complexity = project_complexity
        self.project_duration_days = (project_end - project_start).days
        self.project_duration_weeks = self.project_duration_days / 7
        self.project_duration_months = self.project_duration_days / 30

    def generate_governance_milestones(self) -> List[TimelineTask]:
        """Generate all governance milestones based on project characteristics"""
        milestones = []

        # Add steering committee reviews
        milestones.extend(self._generate_steering_committee_reviews())

        # Add executive briefings
        milestones.extend(self._generate_executive_briefings())

        # Add risk review meetings
        milestones.extend(self._generate_risk_reviews())

        # Add quality gates
        milestones.extend(self._generate_quality_gates())

        # Add change control checkpoints
        milestones.extend(self._generate_change_control_checkpoints())

        return milestones

    def generate_communication_cadence(self) -> List[TimelineTask]:
        """Generate communication cadence milestones"""
        cadence_tasks = []

        # Weekly status meetings (every Monday)
        cadence_tasks.extend(self._generate_weekly_status_meetings())

        # Monthly steering committee updates
        cadence_tasks.extend(self._generate_monthly_steering_updates())

        # Quarterly business reviews for long projects
        if self.project_duration_months >= 3:
            cadence_tasks.extend(self._generate_quarterly_reviews())

        # Daily standups during critical phases
        cadence_tasks.extend(self._generate_critical_phase_standups())

        # Stakeholder touchpoints at key decisions
        cadence_tasks.extend(self._generate_stakeholder_touchpoints())

        return cadence_tasks

    def generate_quality_assurance_milestones(self) -> List[TimelineTask]:
        """Generate quality assurance framework milestones"""
        qa_milestones = []

        # Peer review cycles for deliverables
        qa_milestones.extend(self._generate_peer_reviews())

        # UAT phases for digital products
        qa_milestones.extend(self._generate_uat_phases())

        # Legal/compliance reviews
        if self.project_complexity in ["medium", "high"]:
            qa_milestones.extend(self._generate_compliance_reviews())

        # Accessibility testing for digital experiences
        qa_milestones.extend(self._generate_accessibility_testing())

        # Performance testing milestones
        qa_milestones.extend(self._generate_performance_testing())

        return qa_milestones

    def generate_risk_management_milestones(self) -> List[TimelineTask]:
        """Generate risk management integration milestones"""
        risk_milestones = []

        # Risk assessment at phase starts
        risk_milestones.extend(self._generate_risk_assessments())

        # Contingency plan reviews
        risk_milestones.extend(self._generate_contingency_reviews())

        # Issue escalation points
        risk_milestones.extend(self._generate_escalation_points())

        # Mitigation strategy checkpoints
        risk_milestones.extend(self._generate_mitigation_checkpoints())

        return risk_milestones

    def _generate_steering_committee_reviews(self) -> List[TimelineTask]:
        """Generate steering committee review milestones at 25%, 50%, 75% completion"""
        milestones = []
        percentages = [0.25, 0.50, 0.75]

        for pct in percentages:
            review_date = self.project_start + timedelta(days=int(self.project_duration_days * pct))

            # Skip weekends
            while review_date.weekday() >= 5:
                review_date += timedelta(days=1)

            milestone = TimelineTask(
                id=f"gov_steering_{int(pct*100)}",
                name=f"🎯 Steering Committee Review - {int(pct*100)}% Completion",
                deliverable_code="GOV_STEERING",
                deliverable_name=f"Steering Committee {int(pct*100)}% Review",
                department="Project Management",
                start_date=review_date.strftime('%Y-%m-%d'),
                end_date=review_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=2,
                color="#FFD700"  # Gold for governance
            )
            milestone.governance_type = "steering_review"
            milestone.governance_percentage = pct
            milestones.append(milestone)

        return milestones

    def _generate_executive_briefings(self) -> List[TimelineTask]:
        """Generate executive briefings at major phase transitions"""
        milestones = []

        # Identify major phases (strategy -> creative -> implementation)
        # Get tasks sorted by department and then by date
        sorted_tasks = sorted(self.tasks, key=lambda t: (
            t.department,
            datetime.fromisoformat(t.start_date) if t.start_date else datetime.max
        ))

        # Group tasks by department and find the earliest start date for each
        phase_transitions = {}
        for task in sorted_tasks:
            dept = task.department
            if dept not in phase_transitions:
                phase_transitions[dept] = datetime.fromisoformat(task.start_date) if task.start_date else datetime.max

        # Convert to a sorted list of (department, date) tuples
        sorted_phases = sorted(phase_transitions.items(), key=lambda item: item[1])

        # Determine transitions between sorted phases
        for i in range(len(sorted_phases) - 1):
            from_dept, from_date = sorted_phases[i]
            to_dept, to_date = sorted_phases[i+1]
            # Schedule briefing 1 day before transition
            briefing_date = to_date - timedelta(days=1)
            while briefing_date.weekday() >= 5:
                briefing_date -= timedelta(days=1)

            milestone = TimelineTask(
                id=f"gov_exec_briefing_{from_dept.lower()}_{to_dept.lower()}",
                name=f"📊 Executive Briefing: {from_dept} → {to_dept} Transition",
                deliverable_code="GOV_EXEC",
                deliverable_name="Executive Briefing",
                department="Project Management",
                start_date=briefing_date.strftime('%Y-%m-%d'),
                end_date=briefing_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=1,
                color="#FF69B4"  # Hot pink for executive
            )
            milestone.governance_type = "executive_briefing"
            milestones.append(milestone)

        return milestones

    def _generate_risk_reviews(self) -> List[TimelineTask]:
        """Generate risk review meetings before high-risk phases"""
        milestones = []

        # Identify high-risk phases (Technology deployment, Paid Media launch, etc.)
        high_risk_departments = ["Technology", "Paid Media"]

        for task in self.tasks:
            if task.department in high_risk_departments and task.hours > 20:
                # Schedule risk review 2 days before task starts
                review_date = datetime.fromisoformat(task.start_date) - timedelta(days=2)
                while review_date.weekday() >= 5:
                    review_date -= timedelta(days=1)

                # Don't create if before project start
                if review_date < self.project_start:
                    continue

                milestone = TimelineTask(
                    id=f"gov_risk_review_{task.id}",
                    name=f"⚠️ Risk Review: {task.name[:30]}",
                    deliverable_code="GOV_RISK",
                    deliverable_name="Risk Review Meeting",
                    department="Project Management",
                    start_date=review_date.strftime('%Y-%m-%d'),
                    end_date=review_date.strftime('%Y-%m-%d'),
                    is_milestone=True,
                    hours=1.5,
                    color="#FF4500"  # Orange red for risk
                )
                milestone.governance_type = "risk_review"
                milestones.append(milestone)

                # Limit to 5 risk reviews
                if len(milestones) >= 5:
                    break

        return milestones

    def _generate_quality_gates(self) -> List[TimelineTask]:
        """Generate quality gates before major deliverable releases"""
        milestones = []

        # Find major deliverables (those with high hours or critical path)
        major_deliverables = [t for t in self.tasks if t.hours > 30 or t.is_critical]

        # Create quality gates for all major deliverables
        for task in major_deliverables:
            # Schedule quality gate at task completion
            gate_date = datetime.fromisoformat(task.end_date)

            milestone = TimelineTask(
                id=f"gov_quality_gate_{task.id}",
                name=f"✅ Quality Gate: {task.name[:30]}",
                deliverable_code="GOV_QUALITY",
                deliverable_name="Quality Gate Review",
                department="Quality Assurance",
                start_date=gate_date.strftime('%Y-%m-%d'),
                end_date=gate_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=2,
                dependencies=[task.id],
                color="#32CD32"  # Lime green for quality
            )
            milestone.governance_type = "quality_gate"
            milestones.append(milestone)

        return milestones

    def _generate_change_control_checkpoints(self) -> List[TimelineTask]:
        """Generate change control checkpoints at regular intervals"""
        milestones = []

        # Add change control checkpoints monthly for projects > 2 months
        if self.project_duration_months >= 2:
            num_checkpoints = min(int(self.project_duration_months), 6)  # Max 6 checkpoints

            for i in range(num_checkpoints):
                checkpoint_date = self.project_start + timedelta(days=30 * (i + 1))

                # Skip weekends
                while checkpoint_date.weekday() >= 5:
                    checkpoint_date += timedelta(days=1)

                # Don't exceed project end
                if checkpoint_date > self.project_end:
                    break

                milestone = TimelineTask(
                    id=f"gov_change_control_{i+1}",
                    name=f"🔄 Change Control Checkpoint #{i+1}",
                    deliverable_code="GOV_CHANGE",
                    deliverable_name="Change Control Review",
                    department="Project Management",
                    start_date=checkpoint_date.strftime('%Y-%m-%d'),
                    end_date=checkpoint_date.strftime('%Y-%m-%d'),
                    is_milestone=True,
                    hours=1,
                    color="#9370DB"  # Medium purple for change control
                )
                milestone.governance_type = "change_control"
                milestones.append(milestone)

        return milestones

    def _generate_weekly_status_meetings(self) -> List[TimelineTask]:
        """Generate weekly status meetings (every Monday)"""
        meetings = []

        # Only add weekly meetings for first 2 months to avoid clutter
        max_weeks = min(8, int(self.project_duration_weeks))

        current_date = self.project_start
        # Find first Monday
        days_until_monday = (7 - current_date.weekday()) % 7
        if days_until_monday == 0 and current_date.weekday() != 0:
            days_until_monday = 7
        current_date = current_date + timedelta(days=days_until_monday)

        for week in range(max_weeks):
            meeting_date = current_date + timedelta(weeks=week)

            if meeting_date > self.project_end:
                break

            meeting = TimelineTask(
                id=f"comm_weekly_status_{week+1}",
                name=f"📅 Weekly Status Meeting - Week {week+1}",
                deliverable_code="COMM_WEEKLY",
                deliverable_name="Weekly Status Meeting",
                department="Project Management",
                start_date=meeting_date.strftime('%Y-%m-%d'),
                end_date=meeting_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=1,
                color="#87CEEB"  # Sky blue for communication
            )
            meeting.governance_type = "communication_weekly"
            meetings.append(meeting)

        return meetings

    def _generate_monthly_steering_updates(self) -> List[TimelineTask]:
        """Generate monthly steering committee updates"""
        updates = []

        for month in range(int(self.project_duration_months)):
            update_date = self.project_start + timedelta(days=30 * (month + 1))

            # Schedule for last Friday of the month
            while update_date.weekday() != 4:  # Friday
                update_date -= timedelta(days=1)

            if update_date > self.project_end:
                break

            update = TimelineTask(
                id=f"comm_monthly_steering_{month+1}",
                name=f"📈 Monthly Steering Update - Month {month+1}",
                deliverable_code="COMM_MONTHLY",
                deliverable_name="Monthly Steering Committee Update",
                department="Project Management",
                start_date=update_date.strftime('%Y-%m-%d'),
                end_date=update_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=2,
                color="#4682B4"  # Steel blue for monthly updates
            )
            update.governance_type = "communication_monthly"
            updates.append(update)

        return updates

    def _generate_quarterly_reviews(self) -> List[TimelineTask]:
        """Generate quarterly business reviews for long projects"""
        reviews = []
        quarters = int(self.project_duration_months / 3)

        for q in range(min(quarters, 4)):  # Max 4 quarterly reviews
            review_date = self.project_start + timedelta(days=90 * (q + 1))

            # Schedule for mid-month
            review_date = review_date.replace(day=15)
            while review_date.weekday() >= 5:
                review_date += timedelta(days=1)

            if review_date > self.project_end:
                break

            review = TimelineTask(
                id=f"comm_quarterly_review_{q+1}",
                name=f"📊 Quarterly Business Review - Q{q+1}",
                deliverable_code="COMM_QUARTERLY",
                deliverable_name="Quarterly Business Review",
                department="Project Management",
                start_date=review_date.strftime('%Y-%m-%d'),
                end_date=review_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=3,
                color="#191970"  # Midnight blue for quarterly
            )
            review.governance_type = "communication_quarterly"
            reviews.append(review)

        return reviews

    def _generate_critical_phase_standups(self) -> List[TimelineTask]:
        """Generate daily standups during critical phases"""
        standups = []

        # Find critical phases (high-hour tasks on critical path)
        critical_phases = [t for t in self.tasks if t.is_critical and t.hours > 40]

        for phase in critical_phases[:2]:  # Limit to 2 critical phases
            phase_start = datetime.fromisoformat(phase.start_date)
            phase_end = datetime.fromisoformat(phase.end_date)
            phase_duration_days = (phase_end - phase_start).days

            # Add daily standups for first week of critical phase
            for day in range(min(5, phase_duration_days)):  # Max 5 days
                standup_date = phase_start + timedelta(days=day)

                # Skip weekends
                if standup_date.weekday() >= 5:
                    continue

                standup = TimelineTask(
                    id=f"comm_daily_standup_{phase.id}_{day+1}",
                    name=f"🏃 Daily Standup - {phase.name[:20]} Day {day+1}",
                    deliverable_code="COMM_DAILY",
                    deliverable_name="Daily Standup",
                    department="Project Management",
                    start_date=standup_date.strftime('%Y-%m-%d'),
                    end_date=standup_date.strftime('%Y-%m-%d'),
                    is_milestone=True,
                    hours=0.25,
                    color="#00CED1"  # Dark turquoise for daily
                )
                standup.governance_type = "communication_daily"
                standups.append(standup)

        return standups

    def _generate_stakeholder_touchpoints(self) -> List[TimelineTask]:
        """Generate stakeholder touchpoints at key decision points"""
        touchpoints = []

        # Add touchpoints at 30%, 60%, 90% completion
        percentages = [0.30, 0.60, 0.90]

        for pct in percentages:
            touchpoint_date = self.project_start + timedelta(days=int(self.project_duration_days * pct))

            # Schedule for Tuesday/Thursday
            while touchpoint_date.weekday() not in [1, 3]:  # Tuesday or Thursday
                touchpoint_date += timedelta(days=1)

            if touchpoint_date > self.project_end:
                continue

            touchpoint = TimelineTask(
                id=f"comm_stakeholder_{int(pct*100)}",
                name=f"🤝 Stakeholder Touchpoint - {int(pct*100)}% Milestone",
                deliverable_code="COMM_STAKEHOLDER",
                deliverable_name="Stakeholder Touchpoint",
                department="Account Management",
                start_date=touchpoint_date.strftime('%Y-%m-%d'),
                end_date=touchpoint_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=1.5,
                color="#DAA520"  # Goldenrod for stakeholder
            )
            touchpoint.governance_type = "communication_stakeholder"
            touchpoints.append(touchpoint)

        return touchpoints

    def _generate_peer_reviews(self) -> List[TimelineTask]:
        """Generate peer review cycles for deliverables"""
        reviews = []

        # Add peer reviews for major deliverables
        major_deliverables = [t for t in self.tasks if t.hours > 20 and t.department in ["Creative", "Content", "Technology"]]

        for task in major_deliverables[:5]:  # Limit to 5 peer reviews
            # Schedule peer review 1 day before task ends
            review_date = datetime.fromisoformat(task.end_date) - timedelta(days=1)

            while review_date.weekday() >= 5:
                review_date -= timedelta(days=1)

            review = TimelineTask(
                id=f"qa_peer_review_{task.id}",
                name=f"👥 Peer Review: {task.name[:30]}",
                deliverable_code="QA_PEER",
                deliverable_name="Peer Review",
                department="Quality Assurance",
                start_date=review_date.strftime('%Y-%m-%d'),
                end_date=review_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=2,
                dependencies=[task.id],
                color="#20B2AA"  # Light sea green for QA
            )
            review.governance_type = "qa_peer_review"
            reviews.append(review)

        return reviews

    def _generate_uat_phases(self) -> List[TimelineTask]:
        """Generate UAT phases for digital products"""
        uat_phases = []

        # Find technology/digital deliverables
        digital_tasks = [t for t in self.tasks if t.department == "Technology" and t.hours > 30]

        for task in digital_tasks[:3]:  # Limit to 3 UAT phases
            # Schedule UAT after task completion
            uat_start = datetime.fromisoformat(task.end_date) + timedelta(days=1)
            uat_end = uat_start + timedelta(days=5)  # 5-day UAT period

            # Skip weekends
            while uat_start.weekday() >= 5:
                uat_start += timedelta(days=1)
            while uat_end.weekday() >= 5:
                uat_end += timedelta(days=1)

            uat_phase = TimelineTask(
                id=f"qa_uat_{task.id}",
                name=f"🧪 UAT: {task.name[:30]}",
                deliverable_code="QA_UAT",
                deliverable_name="User Acceptance Testing",
                department="Quality Assurance",
                start_date=uat_start.strftime('%Y-%m-%d'),
                end_date=uat_end.strftime('%Y-%m-%d'),
                is_milestone=False,  # UAT is a phase, not a milestone
                hours=10,
                dependencies=[task.id],
                color="#3CB371"  # Medium sea green for UAT
            )
            uat_phase.governance_type = "qa_uat"
            uat_phases.append(uat_phase)

        return uat_phases

    def _generate_compliance_reviews(self) -> List[TimelineTask]:
        """Generate legal/compliance reviews for regulated industries"""
        reviews = []

        # Add compliance reviews at key milestones
        if self.project_complexity in ["medium", "high"]:
            # Initial compliance review at 20% completion
            review_date = self.project_start + timedelta(days=int(self.project_duration_days * 0.20))

            while review_date.weekday() >= 5:
                review_date += timedelta(days=1)

            initial_review = TimelineTask(
                id="qa_compliance_initial",
                name="⚖️ Initial Compliance Review",
                deliverable_code="QA_COMPLIANCE",
                deliverable_name="Legal/Compliance Review",
                department="Quality Assurance",
                start_date=review_date.strftime('%Y-%m-%d'),
                end_date=review_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=3,
                color="#4B0082"  # Indigo for compliance
            )
            initial_review.governance_type = "qa_compliance"
            reviews.append(initial_review)

            # Final compliance review at 80% completion
            final_review_date = self.project_start + timedelta(days=int(self.project_duration_days * 0.80))

            while final_review_date.weekday() >= 5:
                final_review_date += timedelta(days=1)

            final_review = TimelineTask(
                id="qa_compliance_final",
                name="⚖️ Final Compliance Review",
                deliverable_code="QA_COMPLIANCE",
                deliverable_name="Final Legal/Compliance Review",
                department="Quality Assurance",
                start_date=final_review_date.strftime('%Y-%m-%d'),
                end_date=final_review_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=4,
                color="#4B0082"  # Indigo for compliance
            )
            final_review.governance_type = "qa_compliance"
            reviews.append(final_review)

        return reviews

    def _generate_accessibility_testing(self) -> List[TimelineTask]:
        """Generate accessibility testing for digital experiences"""
        testing = []

        # Find digital/web deliverables
        digital_tasks = [t for t in self.tasks if t.department in ["Technology", "Creative"] and "digital" in t.name.lower()]

        for task in digital_tasks[:2]:  # Limit to 2 accessibility tests
            # Schedule accessibility testing after task completion
            test_date = datetime.fromisoformat(task.end_date)

            test = TimelineTask(
                id=f"qa_accessibility_{task.id}",
                name=f"♿ Accessibility Testing: {task.name[:25]}",
                deliverable_code="QA_ACCESSIBILITY",
                deliverable_name="Accessibility Testing",
                department="Quality Assurance",
                start_date=test_date.strftime('%Y-%m-%d'),
                end_date=test_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=3,
                dependencies=[task.id],
                color="#FF8C00"  # Dark orange for accessibility
            )
            test.governance_type = "qa_accessibility"
            testing.append(test)

        return testing

    def _generate_performance_testing(self) -> List[TimelineTask]:
        """Generate performance testing milestones"""
        testing = []

        # Find technology deliverables that need performance testing
        tech_tasks = [t for t in self.tasks if t.department == "Technology" and t.hours > 25]

        for task in tech_tasks[:3]:  # Limit to 3 performance tests
            # Schedule performance testing before task ends
            test_date = datetime.fromisoformat(task.end_date) - timedelta(days=2)

            while test_date.weekday() >= 5:
                test_date -= timedelta(days=1)

            test = TimelineTask(
                id=f"qa_performance_{task.id}",
                name=f"⚡ Performance Testing: {task.name[:25]}",
                deliverable_code="QA_PERFORMANCE",
                deliverable_name="Performance Testing",
                department="Quality Assurance",
                start_date=test_date.strftime('%Y-%m-%d'),
                end_date=test_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=4,
                color="#DC143C"  # Crimson for performance
            )
            test.governance_type = "qa_performance"
            testing.append(test)

        return testing

    def _generate_risk_assessments(self) -> List[TimelineTask]:
        """Generate risk assessment milestones at phase starts"""
        assessments = []

        # Add risk assessments at the start of major phases
        phase_departments = ["Strategy", "Creative", "Technology", "Paid Media"]
        phase_starts = {}

        for task in self.tasks:
            if task.department in phase_departments and task.department not in phase_starts:
                phase_starts[task.department] = datetime.fromisoformat(task.start_date)

        for dept, start_date in phase_starts.items():
            # Schedule risk assessment at phase start
            assessment_date = start_date

            while assessment_date.weekday() >= 5:
                assessment_date += timedelta(days=1)

            assessment = TimelineTask(
                id=f"risk_assessment_{dept.lower()}",
                name=f"🎲 Risk Assessment: {dept} Phase",
                deliverable_code="RISK_ASSESS",
                deliverable_name="Risk Assessment",
                department="Project Management",
                start_date=assessment_date.strftime('%Y-%m-%d'),
                end_date=assessment_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=2,
                color="#B22222"  # Fire brick for risk
            )
            assessment.governance_type = "risk_assessment"
            assessments.append(assessment)

        return assessments

    def _generate_contingency_reviews(self) -> List[TimelineTask]:
        """Generate contingency plan reviews"""
        reviews = []

        # Add contingency reviews for high-complexity projects
        if self.project_complexity == "high":
            # Add contingency reviews at 33% and 66% completion
            for pct in [0.33, 0.66]:
                review_date = self.project_start + timedelta(days=int(self.project_duration_days * pct))

                while review_date.weekday() >= 5:
                    review_date += timedelta(days=1)

                review = TimelineTask(
                    id=f"risk_contingency_{int(pct*100)}",
                    name=f"🛠️ Contingency Plan Review - {int(pct*100)}%",
                    deliverable_code="RISK_CONTINGENCY",
                    deliverable_name="Contingency Plan Review",
                    department="Project Management",
                    start_date=review_date.strftime('%Y-%m-%d'),
                    end_date=review_date.strftime('%Y-%m-%d'),
                    is_milestone=True,
                    hours=1.5,
                    color="#CD5C5C"  # Indian red for contingency
                )
                review.governance_type = "risk_contingency"
                reviews.append(review)

        return reviews

    def _generate_escalation_points(self) -> List[TimelineTask]:
        """Generate issue escalation points"""
        points = []

        # Add escalation points before critical milestones
        critical_tasks = [t for t in self.tasks if t.is_critical and t.hours > 35]

        for task in critical_tasks[:3]:  # Limit to 3 escalation points
            # Schedule escalation point 3 days before critical task
            escalation_date = datetime.fromisoformat(task.start_date) - timedelta(days=3)

            while escalation_date.weekday() >= 5:
                escalation_date -= timedelta(days=1)

            # Don't create if before project start
            if escalation_date < self.project_start:
                continue

            point = TimelineTask(
                id=f"risk_escalation_{task.id}",
                name=f"🚨 Issue Escalation Point: {task.name[:25]}",
                deliverable_code="RISK_ESCALATION",
                deliverable_name="Issue Escalation Point",
                department="Project Management",
                start_date=escalation_date.strftime('%Y-%m-%d'),
                end_date=escalation_date.strftime('%Y-%m-%d'),
                is_milestone=True,
                hours=1,
                color="#8B0000"  # Dark red for escalation
            )
            point.governance_type = "risk_escalation"
            points.append(point)

        return points

    def _generate_mitigation_checkpoints(self) -> List[TimelineTask]:
        """Generate mitigation strategy checkpoints"""
        checkpoints = []

        # Add mitigation checkpoints bi-weekly for medium/high complexity projects
        if self.project_complexity in ["medium", "high"]:
            num_checkpoints = min(int(self.project_duration_weeks / 2), 8)  # Max 8 checkpoints

            for i in range(num_checkpoints):
                checkpoint_date = self.project_start + timedelta(weeks=2 * (i + 1))

                # Schedule for Wednesday
                while checkpoint_date.weekday() != 2:  # Wednesday
                    checkpoint_date += timedelta(days=1)

                if checkpoint_date > self.project_end:
                    break

                checkpoint = TimelineTask(
                    id=f"risk_mitigation_{i+1}",
                    name=f"🛡️ Mitigation Strategy Checkpoint #{i+1}",
                    deliverable_code="RISK_MITIGATION",
                    deliverable_name="Mitigation Strategy Review",
                    department="Project Management",
                    start_date=checkpoint_date.strftime('%Y-%m-%d'),
                    end_date=checkpoint_date.strftime('%Y-%m-%d'),
                    is_milestone=True,
                    hours=1,
                    color="#A52A2A"  # Brown for mitigation
                )
                checkpoint.governance_type = "risk_mitigation"
                checkpoints.append(checkpoint)

        return checkpoints


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

    # Enhanced deliverable category dependencies (based on naming patterns)
    CATEGORY_DEPENDENCIES = {
        # Strategy/Planning categories (must come first)
        "deck_strategy": [],  # No predecessors
        "deck_brief": [],
        "deck_planning": [],
        "deck_kickoff": [],
        "research": [],
        "audit": [],

        # Brand/Identity (depends on strategy)
        "guidelines": ["deck_strategy", "deck_brief"],
        "brand": ["deck_strategy"],
        "identity": ["deck_strategy", "brand"],

        # Creative Development (depends on brand/guidelines)
        "concept": ["guidelines", "brand", "deck_strategy"],
        "design": ["concept", "guidelines"],
        "creative": ["concept", "brand"],

        # Content Creation (depends on creative)
        "content": ["creative", "guidelines"],
        "copy": ["creative", "brand"],
        "social": ["creative", "content"],

        # Production/Assets (depends on design/creative)
        "assets": ["design", "creative"],
        "production": ["design", "creative"],
        "video": ["creative", "concept"],
        "photo": ["creative", "concept"],

        # Campaign Execution (depends on assets)
        "campaign": ["assets", "creative", "content"],
        "media": ["campaign", "assets"],
        "paid": ["campaign", "media"],

        # Implementation/Launch (depends on campaign)
        "implementation": ["campaign", "assets"],
        "launch": ["implementation", "campaign"],
        "execution": ["campaign", "implementation"],

        # Reporting/Analytics (depends on execution)
        "report": ["execution", "launch", "campaign"],
        "analytics": ["execution", "campaign"],
        "dashboard": ["analytics", "report"],
        "metrics": ["execution", "analytics"],

        # Ongoing/Support (can run parallel)
        "management": [],  # Can run parallel
        "support": ["launch"],
        "optimization": ["launch", "analytics"],
        "retainer": []  # Special handling for retainers
    }

    # Phase definitions with percentage allocations
    PHASE_ALLOCATIONS = {
        "Discovery": {
            "percentage": 0.25,  # 25% of timeline
            "categories": ["deck_strategy", "research", "audit", "deck_brief", "deck_planning"],
            "departments": ["Strategy", "Account Management"]
        },
        "Development": {
            "percentage": 0.45,  # 45% of timeline
            "categories": ["guidelines", "brand", "concept", "design", "creative", "content", "assets"],
            "departments": ["Creative", "Content", "Technology"]
        },
        "Execution": {
            "percentage": 0.30,  # 30% of timeline
            "categories": ["campaign", "media", "implementation", "launch", "report"],
            "departments": ["Paid Media", "Integrated Marketing Management"]
        }
    }

    # Task relationship types with lag times
    RELATIONSHIP_TYPES = {
        "strategy_to_creative": {
            "type": DependencyType.FINISH_TO_START,
            "lag_days": 2  # 2 day buffer between strategy and creative
        },
        "parallel_creative": {
            "type": DependencyType.START_TO_START,
            "lag_days": 1  # Can start 1 day after predecessor starts
        },
        "milestone_gate": {
            "type": DependencyType.FINISH_TO_START,
            "lag_days": 0  # No lag for milestone gates
        },
        "review_buffer": {
            "type": DependencyType.FINISH_TO_START,
            "lag_days": 3  # 3 days for review and feedback
        }
    }

    # Intelligent duration calculations based on complexity
    COMPLEXITY_MULTIPLIERS = {
        "simple": 1.0,    # Base duration
        "moderate": 1.3,  # 30% more time
        "complex": 1.6,   # 60% more time
        "strategic": 2.0  # Double time for strategic work
    }

    # Minimum durations by category (in business days)
    MIN_DURATIONS = {
        "deck_strategy": 5,    # Strategic decks need at least 5 days
        "research": 5,
        "guidelines": 7,
        "brand": 10,
        "creative": 7,
        "campaign": 10,
        "report": 3,
        "default": 2  # Default minimum duration
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

    def get_deliverable_category(self, deliverable_name: str) -> str:
        """Extract category from deliverable name for dependency matching"""
        name_lower = deliverable_name.lower()

        # Check each category pattern
        for category in self.CATEGORY_DEPENDENCIES.keys():
            # Replace underscores with spaces for matching
            pattern = category.replace('_', ' ')
            if pattern in name_lower:
                return category

        # Additional pattern matching
        if 'strategy' in name_lower or 'strategic' in name_lower:
            return 'deck_strategy'
        elif 'brief' in name_lower:
            return 'deck_brief'
        elif 'guideline' in name_lower or 'style' in name_lower:
            return 'guidelines'
        elif 'brand' in name_lower or 'identity' in name_lower:
            return 'brand'
        elif 'concept' in name_lower:
            return 'concept'
        elif 'design' in name_lower:
            return 'design'
        elif 'creative' in name_lower:
            return 'creative'
        elif 'content' in name_lower or 'copy' in name_lower:
            return 'content'
        elif 'asset' in name_lower or 'production' in name_lower:
            return 'assets'
        elif 'campaign' in name_lower:
            return 'campaign'
        elif 'media' in name_lower or 'paid' in name_lower:
            return 'media'
        elif 'launch' in name_lower or 'implement' in name_lower:
            return 'launch'
        elif 'report' in name_lower or 'analytic' in name_lower:
            return 'report'
        elif 'dashboard' in name_lower or 'metric' in name_lower:
            return 'dashboard'
        elif 'management' in name_lower or 'support' in name_lower:
            return 'management'

        return 'default'

    def calculate_intelligent_duration(self, hours: float, category: str, complexity: str = "moderate") -> int:
        """Calculate realistic task duration based on hours, category, and complexity"""
        # Base calculation: assume 6 productive hours per day
        base_days = max(1, int(hours / 6))

        # Apply complexity multiplier
        multiplier = self.COMPLEXITY_MULTIPLIERS.get(complexity, 1.3)
        adjusted_days = int(base_days * multiplier)

        # Apply minimum duration for category
        min_duration = self.MIN_DURATIONS.get(category, self.MIN_DURATIONS['default'])
        final_duration = max(min_duration, adjusted_days)

        # Add buffer for large tasks
        if hours > 40:  # More than a week of work
            final_duration += 2  # Add 2 days buffer
        elif hours > 80:  # More than two weeks
            final_duration += 4  # Add 4 days buffer

        return final_duration

    def generate_wbs_id(self, phase_num: int, deliverable_num: int, component_num: Optional[int] = None) -> str:
        """Generate hierarchical WBS ID"""
        if component_num is not None:
            return f"{phase_num}.{deliverable_num}.{component_num}"
        return f"{phase_num}.{deliverable_num}"

    def identify_dependencies(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Identify intelligent dependencies between tasks based on PM best practices"""
        dependencies = {}

        # Create lookup structures
        tasks_by_category = {}
        tasks_by_dept = {}
        tasks_by_deliverable = {}
        task_map = {t['id']: t for t in tasks}

        # Categorize all tasks
        for task in tasks:
            task_id = task['id']
            dependencies[task_id] = []

            # Get task category
            category = self.get_deliverable_category(task.get('deliverable_name', ''))
            task['category'] = category

            # Group by category
            if category not in tasks_by_category:
                tasks_by_category[category] = []
            tasks_by_category[category].append(task)

            # Group by department
            dept = task.get('department', 'Strategy')
            if dept not in tasks_by_dept:
                tasks_by_dept[dept] = []
            tasks_by_dept[dept].append(task)

            # Group by deliverable
            deliv_code = task.get('deliverable_code', '')
            if deliv_code not in tasks_by_deliverable:
                tasks_by_deliverable[deliv_code] = []
            tasks_by_deliverable[deliv_code].append(task)

        # Apply category-based dependencies
        for task in tasks:
            task_id = task['id']
            category = task['category']

            # Get required predecessor categories
            required_categories = self.CATEGORY_DEPENDENCIES.get(category, [])

            for req_cat in required_categories:
                if req_cat in tasks_by_category:
                    # Find the latest task from required category
                    predecessor_tasks = tasks_by_category[req_cat]
                    for pred_task in predecessor_tasks:
                        # Don't create self-dependencies
                        if pred_task['id'] != task_id:
                            # Check if predecessor should actually come before (by planned dates)
                            if tasks.index(pred_task) < tasks.index(task):
                                dependencies[task_id].append(pred_task['id'])

        # Apply department-based dependencies
        task_dept = task.get('department', 'Strategy')
        if task_dept in self.DEPT_DEPENDENCIES:
            for dep_dept in self.DEPT_DEPENDENCIES[task_dept]:
                if dep_dept in tasks_by_dept:
                    # Find tasks from dependent department that should complete first
                    for dep_task in tasks_by_dept[dep_dept]:
                        # Only add if it's a different deliverable and comes before
                        if (dep_task['deliverable_code'] != task['deliverable_code'] and 
                            tasks.index(dep_task) < tasks.index(task)):
                            if dep_task['id'] not in dependencies[task_id]:
                                dependencies[task_id].append(dep_task['id'])

        # Apply component-level dependencies within same deliverable
        for deliv_code, deliv_tasks in tasks_by_deliverable.items():
            if len(deliv_tasks) > 1:
                # Sort by component order if available
                sorted_tasks = sorted(deliv_tasks, key=lambda x: (
                    x.get('component_order', 999),
                    tasks.index(x)
                ))

                # Create sequential dependencies within deliverable
                for i in range(1, len(sorted_tasks)):
                    curr_task = sorted_tasks[i]
                    prev_task = sorted_tasks[i-1]

                    # Add dependency if not already present
                    if prev_task['id'] not in dependencies[curr_task['id']]:
                        dependencies[curr_task['id']].append(prev_task['id'])

        # Limit dependencies to avoid over-complexity (max 3 direct predecessors)
        for task_id in dependencies:
            if len(dependencies[task_id]) > 3:
                # Keep only the most recent/relevant predecessors
                dependencies[task_id] = dependencies[task_id][-3:]

        return dependencies

    def apply_cpm_analysis(self, tasks: List[TimelineTask]) -> Tuple[Set[str], Dict[str, Any], List[TimelineTask]]:
        """
        Apply comprehensive CPM analysis with buffers and resource leveling
        Returns: (critical_path_ids, cpm_metrics, enhanced_tasks_with_buffers)
        """
        if not tasks:
            return set(), {}, []

        # 1. Perform CPM analysis
        cpm_calc = CPMCalculator(tasks)
        critical_path_ids, cpm_metrics = cpm_calc.calculate_cpm()

        # 2. Add CCPM buffers
        buffer_mgr = CCPMBufferManager()

        # Add project buffer at end of critical path
        project_buffer = buffer_mgr.add_project_buffer(tasks, critical_path_ids)
        if project_buffer:
            tasks.append(project_buffer)

        # Add feeding buffers at critical path junctions
        feeding_buffers = buffer_mgr.add_feeding_buffers(tasks, critical_path_ids)
        tasks.extend(feeding_buffers)

        # 3. Level resources
        leveler = ResourceLeveler(tasks)
        leveler.level_resources(critical_path_ids)
        resource_utilization = leveler.calculate_resource_utilization()

        # 4. Calculate confidence level
        confidence = buffer_mgr.calculate_confidence_level(tasks)

        # 5. Enhance metrics with additional data
        cpm_metrics.update({
            "project_buffer_days": project_buffer.buffer_days if project_buffer else 0,
            "feeding_buffers_count": len(feeding_buffers),
            "total_buffer_days": sum(t.buffer_days for t in tasks if t.buffer_type),
            "confidence_level": confidence,
            "resource_utilization": resource_utilization,
            "critical_milestones": [
                t.id for t in tasks 
                if t.is_critical and (t.is_milestone or "milestone" in t.name.lower())
            ]
        })

        return critical_path_ids, cpm_metrics, tasks

async def enhance_with_ai_reasoning(
    timeline_result: Dict[str, Any],
    rfp_text: str,
    deliverables: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Enhance timeline with AI-generated strategic reasoning"""

    if not OPENAI_AVAILABLE or not client:
        return timeline_result

    try:
        # Extract key metrics from timeline
        total_days = timeline_result['metadata'].get('total_duration_days', 0)
        workstreams = timeline_result['metadata'].get('workstreams', [])
        phases = timeline_result['metadata'].get('phases', [])
        critical_tasks = timeline_result['metadata'].get('critical_tasks', 0)

        # NOTE: Truncation required for GPT-5 API token limits (128k context window)
        # With prompt and response format, we need to limit input text
        # Use larger context for GPT-5 (supports 128k tokens)
        max_context_chars = 8000  # Sufficient for comprehensive RFPs
        max_reasoning_chars = 4000  # More reasoning context

        rfp_context = rfp_text[:max_context_chars] if rfp_text else 'Standard agency project'
        if rfp_text and len(rfp_text) > max_context_chars:
            rfp_context += f"... [truncated from {len(rfp_text)} chars for API limits]"

        reasoning_text = json.dumps(timeline_result.get('reasoning', {}), indent=2)
        reasoning_context = reasoning_text[:max_reasoning_chars]
        if len(reasoning_text) > max_reasoning_chars:
            reasoning_context += f"... [truncated from {len(reasoning_text)} chars for API limits]"

        prompt = f"""As an expert project manager, analyze this project timeline and provide strategic insights.

PROJECT CONTEXT:
{rfp_context}

TIMELINE METRICS:
- Duration: {total_days} days
- Workstreams: {', '.join(workstreams)}
- Phases: {', '.join(phases)}
- Critical tasks: {critical_tasks}
- Total deliverables: {len(deliverables)}

CURRENT REASONING:
{reasoning_context}

Provide strategic insights on:
1. Why this timeline structure makes sense for this specific project
2. Key risks and how the timeline mitigates them
3. Opportunities for acceleration if needed
4. Resource optimization strategies
5. Client communication checkpoints

Return as JSON with keys:
- strategic_rationale: Overall timeline strategy explanation
- risk_mitigation: How timeline addresses project risks
- acceleration_opportunities: Ways to speed up if needed
- resource_optimization: How to best utilize team resources
- client_touchpoints: Key review and approval milestones
- confidence_level: 0-100 score
"""

        response = await client.chat.completions.create(
            model="gpt-5-mini",  # Use GPT-5 model (system enforces GPT-5 only)
            messages=[
                {"role": "system", "content": "You are a senior project management consultant."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            # temperature=1.0 is default for GPT-5, do not specify
            max_completion_tokens=1000  # Use max_completion_tokens for GPT-5
        )

        # Safely parse JSON response with validation
        response_content = response.choices[0].message.content if response.choices else ""

        if not response_content:
            print("[AI Timeline] Empty response from GPT-5, using default insights")
            ai_insights = {
                'strategic_rationale': 'Timeline optimized for balanced delivery',
                'risk_mitigation': ['Regular review checkpoints', 'Buffer time included'],
                'acceleration_opportunities': ['Parallel workstreams identified'],
                'resource_optimization': 'Resources leveled across departments',
                'client_touchpoints': ['Weekly updates', 'Phase gate reviews'],
                'confidence_level': 75
            }
        else:
            try:
                ai_insights = json.loads(response_content)
            except json.JSONDecodeError as e:
                print(f"[AI Timeline] Failed to parse JSON response: {e}")
                # Try to fix common issues in response
                try:
                    # Remove any leading/trailing non-JSON characters
                    cleaned_content = response_content.strip()
                    if cleaned_content.startswith('```json'):
                        cleaned_content = cleaned_content[7:]
                    if cleaned_content.endswith('```'):
                        cleaned_content = cleaned_content[:-3]
                    ai_insights = json.loads(cleaned_content.strip())
                except:
                    # If all parsing fails, use defaults
                    print(f"[AI Timeline] Using default insights due to parsing error")
                    ai_insights = {
                        'strategic_rationale': 'Timeline structured for optimal project flow',
                        'risk_mitigation': ['Risk buffers included in critical path'],
                        'acceleration_opportunities': ['Identified parallel work opportunities'],
                        'resource_optimization': 'Resource allocation balanced across phases',
                        'client_touchpoints': ['Regular status updates scheduled'],
                        'confidence_level': 70
                    }

        # Merge AI insights with existing reasoning
        if 'reasoning' not in timeline_result:
            timeline_result['reasoning'] = {}

        timeline_result['reasoning'].update({
            'ai_strategic_rationale': ai_insights.get('strategic_rationale', ''),
            'risk_mitigation': ai_insights.get('risk_mitigation', []),
            'acceleration_opportunities': ai_insights.get('acceleration_opportunities', []),
            'resource_optimization': ai_insights.get('resource_optimization', ''),
            'client_touchpoints': ai_insights.get('client_touchpoints', []),
            'confidence_level': ai_insights.get('confidence_level', 75)
        })

    except Exception as e:
        print(f"[AI Timeline] Error enhancing with AI reasoning: {e}")

    return timeline_result

async def generate_ai_timeline(
    deliverables: List[Dict[str, Any]], 
    rfp_text: str = "",
    project_start: Optional[str] = None,
    optimization_mode: str = "balanced",
    use_intelligent_scheduler: bool = True,
    include_governance: bool = True,
    project_complexity: str = "medium"
) -> Dict[str, Any]:
    """
    Generate an AI-optimized project timeline with governance framework

    Args:
        deliverables: List of selected deliverables with components and tasks
        rfp_text: Original RFP text for context
        project_start: ISO date string for project start (defaults to next Monday)
        optimization_mode: "speed" | "quality" | "balanced" | "cost"
        use_intelligent_scheduler: Use new intelligent scheduler with workstreams
        include_governance: Whether to include governance milestones
        project_complexity: "low", "medium", or "high" - affects governance milestone density

    Returns:
        Dictionary with timeline tasks, reasoning, metadata, and governance milestones
    """

    # Use the new intelligent scheduler if available
    if use_intelligent_scheduler:
        try:
            from timeline_scheduler import generate_intelligent_timeline
            result = await generate_intelligent_timeline(
                deliverables,
                project_start,
                optimization_mode
            )
            # Enhance with AI reasoning if available
            if OPENAI_AVAILABLE and client and rfp_text:
                result = await enhance_with_ai_reasoning(result, rfp_text, deliverables)
            return result
        except ImportError:
            print("[AI Timeline] Intelligent scheduler not available, falling back to standard")

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
        # Model will be auto-enforced by sitecustomize.py based on tier
        tier = os.getenv("AI_TIER", "thinking")
        model = {"mini": "gpt-5-mini", "thinking": "gpt-5", "pro": "gpt-5-pro"}.get(tier, "gpt-5")

        # Check if client is available
        if not client:
            raise RuntimeError("OpenAI client not available")

        # Use GPT-5 models directly - sitecustomize.py handles the mapping automatically
        # No manual mapping needed - the enforcer will convert to appropriate models

        response = await client.chat.completions.create(
            model=model,  # Use GPT-5 model directly (enforcer handles mapping)
            messages=[
                {"role": "system", "content": "You are a project scheduling expert. Provide realistic timelines based on industry standards."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            # temperature=1.0 is default for GPT-5, do not specify
            max_completion_tokens=2000  # Use max_completion_tokens for GPT-5 models
        )

        content = response.choices[0].message.content if response.choices and response.choices[0].message else None
        if not content:
            raise RuntimeError("No response content from GPT-5")

        ai_timeline = json.loads(content)

        # Convert AI suggestions to Gantt format
        return process_ai_timeline(ai_timeline, deliverables, project_start)

    except Exception as e:
        print(f"[AI Timeline] Error generating timeline: {e}")
        return generate_fallback_timeline(deliverables, project_start)

def generate_phase_based_schedule(
    deliverables: List[Dict[str, Any]],
    start_date: datetime,
    total_duration_days: int
) -> Dict[str, Dict[str, Any]]:
    """
    Create phase-based schedule with proper allocations
    """
    optimizer = TimelineOptimizer()

    # Calculate phase boundaries
    phases = {
        "Discovery": {
            "start": start_date,
            "end": optimizer.calculate_business_days(start_date, int(total_duration_days * 0.25)),
            "tasks": [],
            "departments": ["Strategy", "Account Management"]
        },
        "Development": {
            "start": optimizer.calculate_business_days(start_date, int(total_duration_days * 0.20)),
            "end": optimizer.calculate_business_days(start_date, int(total_duration_days * 0.70)),
            "tasks": [],
            "departments": ["Creative", "Content", "Technology"]
        },
        "Execution": {
            "start": optimizer.calculate_business_days(start_date, int(total_duration_days * 0.60)),
            "end": optimizer.calculate_business_days(start_date, total_duration_days),
            "tasks": [],
            "departments": ["Paid Media", "Integrated Marketing Management"]
        }
    }

    # Categorize deliverables into phases
    for deliv in deliverables:
        category = optimizer.get_deliverable_category(deliv.get('deliverable_name', ''))
        deliv['category'] = category

        # Determine phase
        assigned = False
        for phase_name, phase_config in optimizer.PHASE_ALLOCATIONS.items():
            if category in phase_config['categories']:
                phases[phase_name]['tasks'].append(deliv)
                assigned = True
                break

        # Default by department if not assigned
        if not assigned:
            dept = deliv.get('department', '')
            for phase_name, phase_info in phases.items():
                if dept in phase_info['departments']:
                    phase_info['tasks'].append(deliv)
                    break

    return phases

def process_ai_timeline(
    ai_response: Dict[str, Any], 
    deliverables: List[Dict[str, Any]], 
    project_start: Optional[str],
    include_governance: bool = True,
    project_complexity: str = "medium"
) -> Dict[str, Any]:
    """Process AI timeline response into Gantt-compatible format with enhanced dependencies"""

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

    # Get total project duration from AI response
    total_duration = ai_response.get('total_duration_days', 90)

    # Generate phase-based schedule
    phases = generate_phase_based_schedule(deliverables, start_date, total_duration)

    # WBS counters for hierarchical IDs
    wbs_counters = {"Discovery": 1, "Development": 2, "Execution": 3}
    deliverable_counter = {phase: 0 for phase in phases.keys()}

    # Process each task from AI response with enhanced logic
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

    # Apply comprehensive CPM analysis with buffers and resource leveling
    critical_path_ids, cpm_metrics, enhanced_tasks = optimizer.apply_cpm_analysis(tasks)
    tasks = enhanced_tasks  # Use enhanced tasks with buffers

    # Add governance framework milestones if enabled
    if include_governance and tasks:
        # Calculate project end date
        project_end_date = max(datetime.fromisoformat(t.end_date) for t in tasks)

        # Initialize governance framework
        governance = GovernanceFramework(
            project_start=start_date,
            project_end=project_end_date,
            tasks=tasks,
            project_complexity=project_complexity
        )

        # Generate governance milestones
        governance_tasks = []

        # Add governance milestones
        governance_tasks.extend(governance.generate_governance_milestones())

        # Add communication cadence (limit to avoid clutter)
        comm_tasks = governance.generate_communication_cadence()
        # Only add essential communication milestones to avoid overwhelming the timeline
        essential_comm = [t for t in comm_tasks if 'steering' in t.id.lower() or 'quarterly' in t.id.lower()][:10]
        governance_tasks.extend(essential_comm)

        # Add quality assurance milestones
        qa_tasks = governance.generate_quality_assurance_milestones()
        governance_tasks.extend(qa_tasks[:8])  # Limit to 8 QA milestones

        # Add risk management milestones
        risk_tasks = governance.generate_risk_management_milestones()
        governance_tasks.extend(risk_tasks[:8])  # Limit to 8 risk milestones

        # Mark all governance tasks clearly
        for task in governance_tasks:
            if not hasattr(task, 'governance_type'):
                task.governance_type = "governance"
            task.is_governance = True

        # Add governance tasks to main task list
        tasks.extend(governance_tasks)

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
        },
        "cpm_analysis": {
            "critical_path": {
                "task_ids": list(critical_path_ids),
                "count": cpm_metrics.get("critical_path_count", 0),
                "percentage": cpm_metrics.get("critical_percentage", 0),
                "milestones": cpm_metrics.get("critical_milestones", [])
            },
            "float_analysis": {
                "average_total_float": cpm_metrics.get("average_total_float", 0),
                "max_total_float": cpm_metrics.get("max_total_float", 0),
                "tasks_with_float": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "total_float": t.total_float,
                        "free_float": t.free_float
                    }
                    for t in tasks if t.total_float > 0
                ]
            },
            "buffers": {
                "project_buffer_days": cpm_metrics.get("project_buffer_days", 0),
                "feeding_buffers_count": cpm_metrics.get("feeding_buffers_count", 0),
                "total_buffer_days": cpm_metrics.get("total_buffer_days", 0),
                "buffer_tasks": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "type": t.buffer_type,
                        "days": t.buffer_days
                    }
                    for t in tasks if t.buffer_type
                ]
            },
            "resource_optimization": {
                "utilization": cpm_metrics.get("resource_utilization", {}),
                "leveled_tasks": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "original_start": t.start_date,
                        "leveled_start": t.leveled_start,
                        "resource_level": t.resource_level
                    }
                    for t in tasks if t.leveled_start
                ]
            },
            "project_metrics": {
                "confidence_level": cpm_metrics.get("confidence_level", 0.75),
                "project_duration": cpm_metrics.get("project_duration", 0),
                "optimization_mode": ai_response.get("optimization_mode", "balanced"),
                "risk_assessment": {
                    "high_risk_tasks": [t.id for t in tasks if t.is_critical and t.hours > 40],
                    "buffer_consumption": 0,  # Would be tracked over time
                    "schedule_risk": "low" if cpm_metrics.get("confidence_level", 0) > 0.8 else "medium"
                }
            }
        }
    }

def generate_fallback_timeline(
    deliverables: List[Dict[str, Any]], 
    project_start: Optional[str]
) -> Dict[str, Any]:
    """Generate a comprehensive timeline with CPM analysis when AI is not available"""

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