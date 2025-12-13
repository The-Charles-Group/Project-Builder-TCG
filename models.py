"""
Database Models and Data Schemas

This file contains:
1. SQLAlchemy database models for the application
2. Pydantic models for the nested hierarchy: Deliverable → Component → Task → Assignment
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, computed_field
from dataclasses import dataclass, field
import hashlib


# ============================================================
# NESTED HIERARCHY SCHEMA: Deliverable → Component → Task → Assignment
# ============================================================

class Assignment(BaseModel):
    """
    An assignment represents work allocated to a role/assignee on a task.
    Multiple assignments can exist per task for multi-role scenarios.
    """
    id: str = Field(default="", description="Unique assignment ID (auto-generated if empty)")
    role: str = Field(..., description="Role title (e.g., 'Designer', 'Developer')")
    assignee: Optional[str] = Field(default=None, description="Assigned person name (null if unassigned)")
    seniority: str = Field(default="Mid", description="Seniority level (Junior, Mid, Senior, Director, VP, EVP)")
    allocation_hours: float = Field(default=0.0, description="Hours allocated to this assignment")
    rate: float = Field(default=0.0, description="Hourly rate for this assignment (role-derived or overridden)")
    notes: Optional[str] = Field(default=None, description="Optional notes for this assignment")
    user_edited: bool = Field(default=False, description="True if user has manually edited this assignment")
    
    @computed_field
    @property
    def price(self) -> float:
        """Calculate price from hours and rate."""
        return self.allocation_hours * self.rate
    
    def generate_id(self, task_key: str) -> str:
        """Generate a stable ID based on task key, role, and seniority."""
        if self.id:
            return self.id
        key_str = f"{task_key}|{self.role}|{self.seniority}"
        return f"asgn_{hashlib.md5(key_str.encode()).hexdigest()[:12]}"


class Task(BaseModel):
    """
    A task is the lowest level of work with assigned hours and resources.
    Tasks live within components and contain assignments.
    """
    id: str = Field(default="", description="Unique task ID")
    label: str = Field(..., description="Task label/name")
    description: Optional[str] = Field(default=None, description="Task description")
    
    hours: float = Field(default=0.0, description="Total planned hours (sum of assignments)")
    rate: float = Field(default=0.0, description="Effective hourly rate (weighted average of assignments)")
    
    assignments: List[Assignment] = Field(default_factory=list, description="Role assignments for this task")
    dependencies: List[str] = Field(default_factory=list, description="Task IDs this task depends on")
    
    start_date: Optional[datetime] = Field(default=None, description="Scheduled start date")
    end_date: Optional[datetime] = Field(default=None, description="Scheduled end date")
    
    row_id: Optional[str] = Field(default=None, description="Original database row ID (for traceability)")
    task_code: Optional[str] = Field(default=None, description="Task code from database")
    task_group: Optional[str] = Field(default=None, description="Task group for timeline calculations")
    
    user_edited: bool = Field(default=False, description="True if user has manually edited this task")
    
    @computed_field
    @property
    def price(self) -> float:
        """Calculate price from hours and rate, or sum of assignment prices."""
        if self.assignments:
            return sum(a.price for a in self.assignments)
        return self.hours * self.rate
    
    def canonical_key(self, deliverable_code: str, component_name: str) -> str:
        """Generate a stable canonical key for this task."""
        key_str = f"{deliverable_code}|{component_name}|{self.label}"
        return f"task_{hashlib.md5(key_str.encode()).hexdigest()[:12]}"
    
    def generate_id(self, deliverable_code: str, component_name: str) -> str:
        """Generate a stable ID if not already set."""
        if self.id:
            return self.id
        return self.canonical_key(deliverable_code, component_name)
    
    def recalculate_from_assignments(self) -> None:
        """Recalculate hours and rate from assignments (bottom-up rollup)."""
        if not self.assignments:
            return
        
        total_hours = sum(a.allocation_hours for a in self.assignments)
        total_price = sum(a.price for a in self.assignments)
        
        self.hours = total_hours
        if total_hours > 0:
            self.rate = total_price / total_hours
        else:
            self.rate = 0.0


class Component(BaseModel):
    """
    A component groups related tasks within a deliverable.
    Components roll up task hours/prices to deliverable level.
    """
    id: str = Field(default="", description="Unique component ID")
    name: str = Field(..., description="Component name")
    description: Optional[str] = Field(default=None, description="Component description")
    
    tasks: List[Task] = Field(default_factory=list, description="Tasks within this component")
    
    default_roles: List[str] = Field(default_factory=list, description="Default roles for tasks in this component")
    
    user_edited: bool = Field(default=False, description="True if user has manually edited this component")
    
    @computed_field
    @property
    def hours(self) -> float:
        """Calculate total hours from tasks (bottom-up rollup)."""
        return sum(t.hours for t in self.tasks)
    
    @computed_field
    @property
    def price(self) -> float:
        """Calculate total price from tasks (bottom-up rollup)."""
        return sum(t.price for t in self.tasks)
    
    @computed_field
    @property
    def rate(self) -> float:
        """Calculate effective rate (weighted average)."""
        total_hours = self.hours
        if total_hours > 0:
            return self.price / total_hours
        return 0.0
    
    def canonical_key(self, deliverable_code: str) -> str:
        """Generate a stable canonical key for this component."""
        key_str = f"{deliverable_code}|{self.name}"
        return f"comp_{hashlib.md5(key_str.encode()).hexdigest()[:12]}"
    
    def generate_id(self, deliverable_code: str) -> str:
        """Generate a stable ID if not already set."""
        if self.id:
            return self.id
        return self.canonical_key(deliverable_code)
    
    def recalculate_from_tasks(self) -> None:
        """Recalculate all tasks from their assignments (cascade rollup)."""
        for task in self.tasks:
            task.recalculate_from_assignments()


class Deliverable(BaseModel):
    """
    A deliverable is the top-level grouping containing components and tasks.
    Deliverables roll up component hours/prices to scenario totals.
    """
    id: str = Field(default="", description="Unique deliverable ID")
    code: str = Field(..., description="Deliverable code (e.g., 'DEL-0001')")
    name: str = Field(..., description="Deliverable name")
    department: str = Field(default="", description="Service department")
    description: Optional[str] = Field(default=None, description="Deliverable description")
    
    components: List[Component] = Field(default_factory=list, description="Components within this deliverable")
    
    selected: bool = Field(default=True, description="Whether this deliverable is included in the scenario")
    match_percent: float = Field(default=0.0, description="AI match confidence (0-100)")
    tfidf_similarity: float = Field(default=0.0, description="TF-IDF similarity score (0-1)")
    
    user_edited: bool = Field(default=False, description="True if user has manually edited this deliverable")
    
    @computed_field
    @property
    def hours(self) -> float:
        """Calculate total hours from components (bottom-up rollup)."""
        return sum(c.hours for c in self.components)
    
    @computed_field
    @property
    def price(self) -> float:
        """Calculate total price from components (bottom-up rollup)."""
        return sum(c.price for c in self.components)
    
    @computed_field
    @property
    def rate(self) -> float:
        """Calculate effective rate (weighted average)."""
        total_hours = self.hours
        if total_hours > 0:
            return self.price / total_hours
        return 0.0
    
    def canonical_key(self) -> str:
        """Generate a stable canonical key for this deliverable."""
        return f"deliv_{self.code}"
    
    def generate_id(self) -> str:
        """Generate a stable ID if not already set."""
        if self.id:
            return self.id
        return self.canonical_key()
    
    def recalculate_from_components(self) -> None:
        """Recalculate all components from their tasks (cascade rollup)."""
        for component in self.components:
            component.recalculate_from_tasks()
    
    def get_all_tasks(self) -> List[Task]:
        """Flatten all tasks across components."""
        tasks = []
        for component in self.components:
            tasks.extend(component.tasks)
        return tasks
    
    def get_all_assignments(self) -> List[Assignment]:
        """Flatten all assignments across components and tasks."""
        assignments = []
        for task in self.get_all_tasks():
            assignments.extend(task.assignments)
        return assignments


class NestedScenario(BaseModel):
    """
    A nested scenario contains the full hierarchy of deliverables → components → tasks → assignments.
    This is the primary data structure for project pricing and timeline.
    """
    id: str = Field(default="", description="Scenario ID")
    name: str = Field(default="Scenario", description="Scenario name")
    
    complexity: str = Field(default="Advanced", description="Complexity level")
    tier: str = Field(default="T2_MediumVolume", description="Volume tier")
    rate_band: str = Field(default="Standard", description="Rate band for pricing")
    
    project_start: Optional[datetime] = Field(default=None, description="Project start date")
    project_end: Optional[datetime] = Field(default=None, description="Project end date")
    
    deliverables: List[Deliverable] = Field(default_factory=list, description="All deliverables in this scenario")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    @computed_field
    @property
    def total_hours(self) -> float:
        """Calculate total hours from selected deliverables."""
        return sum(d.hours for d in self.deliverables if d.selected)
    
    @computed_field
    @property
    def total_price(self) -> float:
        """Calculate total price from selected deliverables."""
        return sum(d.price for d in self.deliverables if d.selected)
    
    @computed_field
    @property
    def effective_rate(self) -> float:
        """Calculate effective blended rate."""
        if self.total_hours > 0:
            return self.total_price / self.total_hours
        return 0.0
    
    def recalculate_all(self) -> None:
        """Cascade recalculation from bottom up."""
        for deliverable in self.deliverables:
            deliverable.recalculate_from_components()
    
    def get_selected_deliverables(self) -> List[Deliverable]:
        """Get only selected deliverables."""
        return [d for d in self.deliverables if d.selected]
    
    def find_deliverable_by_code(self, code: str) -> Optional[Deliverable]:
        """Find a deliverable by its code."""
        for d in self.deliverables:
            if d.code == code:
                return d
        return None
    
    def find_task_by_key(self, deliverable_code: str, component_name: str, task_label: str) -> Optional[Task]:
        """Find a task by its canonical key components."""
        deliverable = self.find_deliverable_by_code(deliverable_code)
        if not deliverable:
            return None
        for component in deliverable.components:
            if component.name == component_name:
                for task in component.tasks:
                    if task.label == task_label:
                        return task
        return None


# ============================================================
# ASSIGNMENT ROLLUP MODELS
# ============================================================

class RollupByRole(BaseModel):
    """Aggregated hours and price by role."""
    role: str
    seniority: str
    total_hours: float = 0.0
    total_price: float = 0.0
    assignment_count: int = 0


class RollupByDeliverable(BaseModel):
    """Aggregated hours and price by deliverable."""
    deliverable_code: str
    deliverable_name: str
    total_hours: float = 0.0
    total_price: float = 0.0
    component_count: int = 0
    task_count: int = 0


class RollupByComponent(BaseModel):
    """Aggregated hours and price by component."""
    deliverable_code: str
    component_name: str
    total_hours: float = 0.0
    total_price: float = 0.0
    task_count: int = 0


class RollupByAssignee(BaseModel):
    """Aggregated hours and price by assignee."""
    assignee: Optional[str]
    total_hours: float = 0.0
    total_price: float = 0.0
    task_count: int = 0


class AssignmentRollups(BaseModel):
    """Complete assignment rollup data for a scenario."""
    by_deliverable: List[RollupByDeliverable] = Field(default_factory=list)
    by_component: List[RollupByComponent] = Field(default_factory=list)
    by_role: List[RollupByRole] = Field(default_factory=list)
    by_assignee: List[RollupByAssignee] = Field(default_factory=list)
    
    total_hours: float = 0.0
    total_price: float = 0.0


def calculate_rollups(scenario: NestedScenario) -> AssignmentRollups:
    """Calculate all rollup aggregations for a scenario."""
    rollups = AssignmentRollups()
    
    role_map: Dict[str, RollupByRole] = {}
    assignee_map: Dict[str, RollupByAssignee] = {}
    
    for deliverable in scenario.get_selected_deliverables():
        deliv_rollup = RollupByDeliverable(
            deliverable_code=deliverable.code,
            deliverable_name=deliverable.name,
            total_hours=deliverable.hours,
            total_price=deliverable.price,
            component_count=len(deliverable.components),
            task_count=len(deliverable.get_all_tasks())
        )
        rollups.by_deliverable.append(deliv_rollup)
        
        for component in deliverable.components:
            comp_rollup = RollupByComponent(
                deliverable_code=deliverable.code,
                component_name=component.name,
                total_hours=component.hours,
                total_price=component.price,
                task_count=len(component.tasks)
            )
            rollups.by_component.append(comp_rollup)
            
            for task in component.tasks:
                for assignment in task.assignments:
                    role_key = f"{assignment.role}|{assignment.seniority}"
                    if role_key not in role_map:
                        role_map[role_key] = RollupByRole(
                            role=assignment.role,
                            seniority=assignment.seniority
                        )
                    role_map[role_key].total_hours += assignment.allocation_hours
                    role_map[role_key].total_price += assignment.price
                    role_map[role_key].assignment_count += 1
                    
                    assignee_key = assignment.assignee or "__unassigned__"
                    if assignee_key not in assignee_map:
                        assignee_map[assignee_key] = RollupByAssignee(
                            assignee=assignment.assignee
                        )
                    assignee_map[assignee_key].total_hours += assignment.allocation_hours
                    assignee_map[assignee_key].total_price += assignment.price
                    assignee_map[assignee_key].task_count += 1
    
    rollups.by_role = list(role_map.values())
    rollups.by_assignee = list(assignee_map.values())
    rollups.total_hours = scenario.total_hours
    rollups.total_price = scenario.total_price
    
    return rollups


# ============================================================
# LEGACY TO NESTED CONVERSION UTILITIES
# ============================================================

def legacy_item_to_deliverable(item: Dict[str, Any], all_rows_data: Optional[List[Dict]] = None) -> Deliverable:
    """
    Convert a legacy flat scenario item to a nested Deliverable structure.
    
    Args:
        item: Legacy scenario item dict with flat structure
        all_rows_data: Optional list of database rows for building task details
    
    Returns:
        Deliverable with nested components, tasks, and assignments
    """
    deliverable = Deliverable(
        id=item.get("id", ""),
        code=item.get("deliverable_code", "") or item.get("code", ""),
        name=item.get("name", "") or item.get("deliverable_name", ""),
        department=item.get("department", "") or item.get("service_department", ""),
        description=item.get("description"),
        selected=item.get("selected", True),
        match_percent=float(item.get("match_percent", 0) or 0),
        tfidf_similarity=float(item.get("tfidf_similarity", 0) or 0),
        user_edited=item.get("user_edited", False)
    )
    
    components_data = item.get("components", [])
    if components_data:
        for comp_data in components_data:
            component = Component(
                id=comp_data.get("id", ""),
                name=comp_data.get("name", "") or comp_data.get("component_name", ""),
                description=comp_data.get("description")
            )
            
            tasks_data = comp_data.get("tasks", [])
            for task_data in tasks_data:
                task = Task(
                    id=task_data.get("id", ""),
                    label=task_data.get("label", "") or task_data.get("name", ""),
                    description=task_data.get("description"),
                    hours=float(task_data.get("hours", 0) or 0),
                    rate=float(task_data.get("rate", 0) or 0),
                    row_id=task_data.get("row_id"),
                    task_code=task_data.get("task_code"),
                    task_group=task_data.get("task_group"),
                    user_edited=task_data.get("user_edited", False)
                )
                
                assignments_data = task_data.get("assignments", [])
                for asgn_data in assignments_data:
                    assignment = Assignment(
                        id=asgn_data.get("id", ""),
                        role=asgn_data.get("role", ""),
                        assignee=asgn_data.get("assignee"),
                        seniority=asgn_data.get("seniority", "Mid"),
                        allocation_hours=float(asgn_data.get("allocation_hours", 0) or 0),
                        rate=float(asgn_data.get("rate", 0) or 0),
                        notes=asgn_data.get("notes"),
                        user_edited=asgn_data.get("user_edited", False)
                    )
                    task.assignments.append(assignment)
                
                component.tasks.append(task)
            
            deliverable.components.append(component)
    else:
        component = Component(
            name=item.get("component_name", "General") or "General",
            description=None
        )
        component.id = component.generate_id(deliverable.code)
        
        task = Task(
            label=item.get("task_label", deliverable.name) or deliverable.name,
            hours=float(item.get("total_hours", 0) or item.get("hours", 0) or 0),
            rate=float(item.get("rate", 0) or 0),
            user_edited=item.get("user_edited", False)
        )
        task.id = task.generate_id(deliverable.code, component.name)
        
        role = item.get("role", "") or item.get("resource_title", "") or "General Role"
        seniority = item.get("seniority", "Mid") or "Mid"
        assignment = Assignment(
            role=role,
            seniority=seniority,
            allocation_hours=task.hours,
            rate=task.rate,
            user_edited=item.get("user_edited", False)
        )
        assignment.id = assignment.generate_id(task.id)
        task.assignments.append(assignment)
        
        component.tasks.append(task)
        deliverable.components.append(component)
    
    deliverable.id = deliverable.generate_id()
    return deliverable


def convert_legacy_scenario_to_nested(legacy_scenario: Dict[str, Any]) -> NestedScenario:
    """
    Convert a complete legacy scenario to nested format.
    
    Args:
        legacy_scenario: Dict with "items" list and metadata
    
    Returns:
        NestedScenario with full hierarchy
    """
    nested = NestedScenario(
        id=legacy_scenario.get("id", ""),
        name=legacy_scenario.get("name", "Scenario"),
        complexity=legacy_scenario.get("complexity", "Advanced"),
        tier=legacy_scenario.get("tier", "T2_MediumVolume"),
        rate_band=legacy_scenario.get("rate_band", "Standard"),
        metadata=legacy_scenario.get("metadata", {})
    )
    
    project_start = legacy_scenario.get("project_start")
    if project_start:
        if isinstance(project_start, str):
            try:
                nested.project_start = datetime.fromisoformat(project_start.replace('Z', ''))
            except ValueError:
                pass
        elif isinstance(project_start, datetime):
            nested.project_start = project_start
    
    items = legacy_scenario.get("items", [])
    for item in items:
        deliverable = legacy_item_to_deliverable(item)
        nested.deliverables.append(deliverable)
    
    return nested


def nested_scenario_to_legacy(nested: NestedScenario) -> Dict[str, Any]:
    """
    Convert a nested scenario back to legacy format for backward compatibility.
    
    Args:
        nested: NestedScenario instance
    
    Returns:
        Dict in legacy format with "items" list
    """
    items = []
    
    for deliverable in nested.deliverables:
        item = {
            "id": deliverable.id,
            "deliverable_code": deliverable.code,
            "name": deliverable.name,
            "department": deliverable.department,
            "description": deliverable.description,
            "selected": deliverable.selected,
            "match_percent": deliverable.match_percent,
            "tfidf_similarity": deliverable.tfidf_similarity,
            "user_edited": deliverable.user_edited,
            "total_hours": deliverable.hours,
            "price": deliverable.price,
            "rate": deliverable.rate,
            "components": []
        }
        
        for component in deliverable.components:
            comp_data = {
                "id": component.id,
                "name": component.name,
                "description": component.description,
                "hours": component.hours,
                "price": component.price,
                "tasks": []
            }
            
            for task in component.tasks:
                task_data = {
                    "id": task.id,
                    "label": task.label,
                    "description": task.description,
                    "hours": task.hours,
                    "rate": task.rate,
                    "price": task.price,
                    "row_id": task.row_id,
                    "task_code": task.task_code,
                    "task_group": task.task_group,
                    "user_edited": task.user_edited,
                    "dependencies": task.dependencies,
                    "assignments": []
                }
                
                if task.start_date:
                    task_data["start_date"] = task.start_date.isoformat()
                if task.end_date:
                    task_data["end_date"] = task.end_date.isoformat()
                
                for assignment in task.assignments:
                    asgn_data = {
                        "id": assignment.id,
                        "role": assignment.role,
                        "assignee": assignment.assignee,
                        "seniority": assignment.seniority,
                        "allocation_hours": assignment.allocation_hours,
                        "rate": assignment.rate,
                        "price": assignment.price,
                        "notes": assignment.notes,
                        "user_edited": assignment.user_edited
                    }
                    task_data["assignments"].append(asgn_data)
                
                comp_data["tasks"].append(task_data)
            
            item["components"].append(comp_data)
        
        items.append(item)
    
    legacy = {
        "id": nested.id,
        "name": nested.name,
        "complexity": nested.complexity,
        "tier": nested.tier,
        "rate_band": nested.rate_band,
        "items": items,
        "totals": {
            "hours": nested.total_hours,
            "price": nested.total_price
        },
        "metadata": nested.metadata
    }
    
    if nested.project_start:
        legacy["project_start"] = nested.project_start.isoformat()
    if nested.project_end:
        legacy["project_end"] = nested.project_end.isoformat()
    
    return legacy


# ============================================================
# CANONICAL KEY UTILITIES
# ============================================================

def generate_task_canonical_key(deliverable_code: str, component_name: str, task_label: str) -> str:
    """Generate a stable canonical key for a task."""
    key_str = f"{deliverable_code}|{component_name}|{task_label}"
    return f"task_{hashlib.md5(key_str.encode()).hexdigest()[:12]}"


def generate_component_canonical_key(deliverable_code: str, component_name: str) -> str:
    """Generate a stable canonical key for a component."""
    key_str = f"{deliverable_code}|{component_name}"
    return f"comp_{hashlib.md5(key_str.encode()).hexdigest()[:12]}"


def generate_assignment_canonical_key(task_key: str, role: str, seniority: str) -> str:
    """Generate a stable canonical key for an assignment."""
    key_str = f"{task_key}|{role}|{seniority}"
    return f"asgn_{hashlib.md5(key_str.encode()).hexdigest()[:12]}"


# ============================================================
# SCENARIO FORMAT DETECTION
# ============================================================

def is_nested_format(scenario_data: Dict[str, Any]) -> bool:
    """
    Detect if scenario data is in nested format or legacy flat format.
    
    Returns:
        True if nested format (has deliverables with components/tasks)
        False if legacy format (has flat items list)
    """
    if "deliverables" in scenario_data:
        deliverables = scenario_data["deliverables"]
        if isinstance(deliverables, list) and len(deliverables) > 0:
            first = deliverables[0]
            if isinstance(first, dict) and "components" in first:
                return True
    
    if "items" in scenario_data:
        items = scenario_data["items"]
        if isinstance(items, list) and len(items) > 0:
            first = items[0]
            if isinstance(first, dict) and "components" in first:
                components = first["components"]
                if isinstance(components, list) and len(components) > 0:
                    first_comp = components[0]
                    if isinstance(first_comp, dict) and "tasks" in first_comp:
                        return True
    
    return False


def ensure_nested_format(scenario_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure scenario data is in nested format, converting if necessary.
    
    Args:
        scenario_data: Scenario dict in either format
    
    Returns:
        Scenario dict in nested format
    """
    if is_nested_format(scenario_data):
        return scenario_data
    
    nested = convert_legacy_scenario_to_nested(scenario_data)
    return nested_scenario_to_legacy(nested)
