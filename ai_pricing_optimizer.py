"""
AI Pricing Optimizer - Intelligent hour redistribution and pricing optimization
Uses GPT-5 to redistribute hours among deliverable components based on complexity and dependencies
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math

# OpenAI client initialization
try:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_AVAILABLE = True
except Exception as e:
    print(f"[AI Pricing] OpenAI not available: {e}")
    OPENAI_AVAILABLE = False
    client = None

@dataclass
class ComponentAllocation:
    """Represents hour allocation for a component"""
    name: str
    current_hours: float
    suggested_hours: float
    change: float
    percentage_of_total: float
    reasoning: str
    complexity_factor: float = 1.0
    confidence: float = 0.85

@dataclass 
class RedistributionResult:
    """Result of hour redistribution operation"""
    deliverable_name: str
    total_hours: float
    original_total: float
    components: List[ComponentAllocation]
    reasoning: str
    confidence: float
    methodology: str

class ComplexityLevel(Enum):
    """Component complexity levels for hour distribution"""
    SIMPLE = 1.0
    MODERATE = 1.5
    COMPLEX = 2.0
    CRITICAL = 2.5

# Industry standard effort distribution patterns
EFFORT_PATTERNS = {
    "strategy": {
        "research": 0.30,
        "analysis": 0.25,
        "development": 0.35,
        "documentation": 0.10
    },
    "creative": {
        "concept": 0.25,
        "design": 0.40,
        "refinement": 0.20,
        "production": 0.15
    },
    "technology": {
        "architecture": 0.15,
        "development": 0.50,
        "testing": 0.20,
        "deployment": 0.15
    },
    "paid_media": {
        "strategy": 0.20,
        "setup": 0.25,
        "management": 0.40,
        "optimization": 0.15
    },
    "content": {
        "planning": 0.15,
        "creation": 0.50,
        "editing": 0.20,
        "publishing": 0.15
    }
}

async def redistribute_hours(
    deliverable_name: str,
    deliverable_code: str,
    new_total_hours: float,
    components: List[Dict[str, Any]],
    complexity: str = "Advanced",
    tier: str = "T2_MediumVolume",
    use_ai: bool = True,
    context: Optional[str] = None
) -> RedistributionResult:
    """
    Redistribute hours among components using AI or rule-based logic
    
    Args:
        deliverable_name: Name of the deliverable
        deliverable_code: Code identifier for the deliverable
        new_total_hours: New total hours to distribute
        components: List of component dicts with name, current_hours, etc.
        complexity: Project complexity level
        tier: Project tier/volume
        use_ai: Whether to use GPT for redistribution
        context: Additional context about the project/requirements
        
    Returns:
        RedistributionResult with suggested allocations
    """
    
    # Calculate original total
    original_total = sum(c.get('hours', 0) for c in components)
    
    if original_total == 0:
        # If no original hours, distribute evenly
        return _distribute_evenly(deliverable_name, new_total_hours, components)
    
    # Calculate change ratio
    change_ratio = new_total_hours / original_total if original_total > 0 else 1.0
    
    if use_ai and OPENAI_AVAILABLE:
        return await _redistribute_with_ai(
            deliverable_name, deliverable_code, new_total_hours, 
            components, change_ratio, complexity, tier, context
        )
    else:
        return _redistribute_with_rules(
            deliverable_name, deliverable_code, new_total_hours,
            components, change_ratio, complexity
        )

async def _redistribute_with_ai(
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
    
    # Build prompt
    components_str = "\n".join([
        f"- {c['name']}: {c.get('hours', 0)} hours (current)"
        for c in components
    ])
    
    change_desc = "increase" if change_ratio > 1 else "decrease"
    change_pct = abs((change_ratio - 1) * 100)
    
    system_prompt = """You are an expert project manager specializing in agency work estimation.
Your task is to redistribute project hours among components based on industry best practices,
task dependencies, and complexity factors.

Consider:
1. Task dependencies and critical path items
2. Complexity scaling (complex tasks scale non-linearly)
3. Fixed vs variable effort (some tasks have minimum thresholds)
4. Industry standard ratios for effort distribution
5. Risk buffers for critical components

Provide reasoning for your redistribution decisions."""

    user_prompt = f"""Redistribute {new_total_hours} total hours among these components for "{deliverable_name}":

Current allocation:
{components_str}

This is a {change_pct:.0f}% {change_desc} from the original {sum(c.get('hours', 0) for c in components)} hours.

Project context:
- Complexity: {complexity}
- Tier: {tier}
- Deliverable type: {deliverable_code}
{f'- Additional context: {context}' if context else ''}

Requirements:
1. Allocate exactly {new_total_hours} hours total
2. Consider which components scale linearly vs non-linearly
3. Maintain minimum viable hours for each component
4. Apply extra weight to research/planning if increasing, or protect core work if decreasing

Return a JSON object with:
{{
    "allocations": [
        {{
            "name": "component name",
            "hours": number,
            "reasoning": "brief explanation",
            "complexity_factor": number (1.0-2.5),
            "scaling": "linear|nonlinear|fixed"
        }}
    ],
    "overall_reasoning": "explanation of redistribution strategy",
    "confidence": number (0.0-1.0),
    "key_considerations": ["list of factors considered"]
}}"""

    try:
        # Check if client is available
        if not client:
            raise RuntimeError("OpenAI client not available")
            
        # Model will be auto-enforced by sitecustomize.py based on tier
        tier = os.getenv("AI_TIER", "thinking")
        model = {"mini": "gpt-5-mini", "thinking": "gpt-5", "pro": "gpt-5-pro"}.get(tier, "gpt-5")
        
        response = await client.chat.completions.create(
            model=model,  # sitecustomize.py will enforce GPT-5
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content if response.choices and response.choices[0].message else None
        if not content:
            raise RuntimeError("No response content from GPT-5")
        
        result = json.loads(content)
        
        # Build allocations
        allocations = []
        for i, comp in enumerate(components):
            ai_alloc = next((a for a in result['allocations'] if a['name'].lower() == comp['name'].lower()), None)
            if ai_alloc:
                suggested = float(ai_alloc['hours'])
                current = float(comp.get('hours', 0))
                allocations.append(ComponentAllocation(
                    name=comp['name'],
                    current_hours=current,
                    suggested_hours=suggested,
                    change=suggested - current,
                    percentage_of_total=(suggested / new_total_hours * 100),
                    reasoning=ai_alloc.get('reasoning', ''),
                    complexity_factor=float(ai_alloc.get('complexity_factor', 1.0)),
                    confidence=float(result.get('confidence', 0.85))
                ))
            else:
                # Fallback if AI didn't include this component
                suggested = comp.get('hours', 0) * change_ratio
                allocations.append(ComponentAllocation(
                    name=comp['name'],
                    current_hours=comp.get('hours', 0),
                    suggested_hours=suggested,
                    change=suggested - comp.get('hours', 0),
                    percentage_of_total=(suggested / new_total_hours * 100),
                    reasoning="Proportional adjustment",
                    confidence=0.7
                ))
        
        # Ensure total matches exactly (handle rounding)
        total_suggested = sum(a.suggested_hours for a in allocations)
        if abs(total_suggested - new_total_hours) > 0.1:
            # Adjust largest component to match
            largest = max(allocations, key=lambda a: a.suggested_hours)
            largest.suggested_hours += (new_total_hours - total_suggested)
            largest.change = largest.suggested_hours - largest.current_hours
            largest.percentage_of_total = (largest.suggested_hours / new_total_hours * 100)
        
        return RedistributionResult(
            deliverable_name=deliverable_name,
            total_hours=new_total_hours,
            original_total=sum(c.get('hours', 0) for c in components),
            components=allocations,
            reasoning=result.get('overall_reasoning', 'AI-optimized distribution based on complexity and dependencies'),
            confidence=float(result.get('confidence', 0.85)),
            methodology="AI-powered (GPT-5)"
        )
        
    except Exception as e:
        print(f"[AI Pricing] AI redistribution failed: {e}, falling back to rules")
        return _redistribute_with_rules(deliverable_name, deliverable_code, new_total_hours, components, change_ratio, complexity)

def _redistribute_with_rules(
    deliverable_name: str,
    deliverable_code: str,
    new_total_hours: float,
    components: List[Dict[str, Any]],
    change_ratio: float,
    complexity: str
) -> RedistributionResult:
    """Redistribute using rule-based logic"""
    
    allocations = []
    
    # Determine deliverable category from code
    category = _get_category_from_code(deliverable_code)
    pattern = EFFORT_PATTERNS.get(category, None)
    
    if pattern and change_ratio != 1.0:
        # Use industry patterns with adjustment
        if change_ratio > 1:
            # When increasing, give more weight to planning/strategy
            adjusted_pattern = _adjust_pattern_for_increase(pattern, change_ratio)
        else:
            # When decreasing, protect core work
            adjusted_pattern = _adjust_pattern_for_decrease(pattern, change_ratio)
        
        # Apply pattern
        component_names = [c['name'].lower() for c in components]
        for comp in components:
            comp_key = _match_component_to_pattern_key(comp['name'], pattern.keys())
            if comp_key:
                suggested = new_total_hours * adjusted_pattern.get(comp_key, 1.0 / len(components))
            else:
                # Default to proportional
                suggested = comp.get('hours', 0) * change_ratio
            
            allocations.append(ComponentAllocation(
                name=comp['name'],
                current_hours=comp.get('hours', 0),
                suggested_hours=round(suggested, 1),
                change=round(suggested - comp.get('hours', 0), 1),
                percentage_of_total=round((suggested / new_total_hours * 100), 1),
                reasoning=f"{'Pattern-based' if comp_key else 'Proportional'} adjustment",
                complexity_factor=_get_complexity_factor(comp['name'], complexity),
                confidence=0.75
            ))
    else:
        # Simple proportional redistribution
        for comp in components:
            current = comp.get('hours', 0)
            if current == 0:
                # Equal distribution for zero-hour components
                suggested = new_total_hours / len(components)
            else:
                suggested = current * change_ratio
            
            allocations.append(ComponentAllocation(
                name=comp['name'],
                current_hours=current,
                suggested_hours=round(suggested, 1),
                change=round(suggested - current, 1),
                percentage_of_total=round((suggested / new_total_hours * 100), 1),
                reasoning="Proportional redistribution",
                complexity_factor=_get_complexity_factor(comp['name'], complexity),
                confidence=0.7
            ))
    
    # Normalize to ensure exact total
    total_suggested = sum(a.suggested_hours for a in allocations)
    if total_suggested != new_total_hours:
        factor = new_total_hours / total_suggested
        for a in allocations:
            a.suggested_hours = round(a.suggested_hours * factor, 1)
            a.change = round(a.suggested_hours - a.current_hours, 1)
            a.percentage_of_total = round((a.suggested_hours / new_total_hours * 100), 1)
    
    # Final adjustment for rounding
    total_after = sum(a.suggested_hours for a in allocations)
    if total_after != new_total_hours and allocations:
        diff = new_total_hours - total_after
        allocations[0].suggested_hours += diff
        allocations[0].change += diff
        allocations[0].percentage_of_total = (allocations[0].suggested_hours / new_total_hours * 100)
    
    reasoning = f"{'Increased' if change_ratio > 1 else 'Decreased'} hours by {abs(change_ratio - 1) * 100:.0f}% using "
    if pattern:
        reasoning += f"{category} industry patterns"
    else:
        reasoning += "proportional distribution"
    
    return RedistributionResult(
        deliverable_name=deliverable_name,
        total_hours=new_total_hours,
        original_total=sum(c.get('hours', 0) for c in components),
        components=allocations,
        reasoning=reasoning,
        confidence=0.75,
        methodology="Rule-based patterns"
    )

def _distribute_evenly(deliverable_name: str, new_total_hours: float, components: List[Dict[str, Any]]) -> RedistributionResult:
    """Distribute hours evenly when no baseline exists"""
    per_component = new_total_hours / len(components) if components else 0
    
    allocations = [
        ComponentAllocation(
            name=comp['name'],
            current_hours=0,
            suggested_hours=round(per_component, 1),
            change=round(per_component, 1),
            percentage_of_total=round(100 / len(components), 1),
            reasoning="Even distribution (no baseline)",
            complexity_factor=1.0,
            confidence=0.6
        )
        for comp in components
    ]
    
    return RedistributionResult(
        deliverable_name=deliverable_name,
        total_hours=new_total_hours,
        original_total=0,
        components=allocations,
        reasoning="Evenly distributed hours as no baseline exists",
        confidence=0.6,
        methodology="Even distribution"
    )

def _get_category_from_code(code: str) -> str:
    """Extract category from deliverable code"""
    code_lower = code.lower()
    if 'strategy' in code_lower or 'deck' in code_lower:
        return 'strategy'
    elif 'creative' in code_lower or 'design' in code_lower:
        return 'creative'
    elif 'tech' in code_lower or 'dev' in code_lower or 'site' in code_lower:
        return 'technology'
    elif 'paid' in code_lower or 'media' in code_lower:
        return 'paid_media'
    elif 'content' in code_lower or 'social' in code_lower:
        return 'content'
    return 'strategy'  # default

def _match_component_to_pattern_key(component_name: str, pattern_keys) -> Optional[str]:
    """Match component name to pattern key"""
    comp_lower = component_name.lower()
    for key in pattern_keys:
        if key in comp_lower or comp_lower in key:
            return key
    return None

def _adjust_pattern_for_increase(pattern: Dict[str, float], ratio: float) -> Dict[str, float]:
    """Adjust pattern when increasing hours - emphasize planning/strategy"""
    adjusted = {}
    emphasis_keys = ['research', 'strategy', 'planning', 'architecture', 'concept']
    
    for key, value in pattern.items():
        if any(e in key for e in emphasis_keys):
            # Give extra weight to planning phases
            adjusted[key] = value * (1 + (ratio - 1) * 0.3)
        else:
            adjusted[key] = value
    
    # Normalize
    total = sum(adjusted.values())
    return {k: v / total for k, v in adjusted.items()}

def _adjust_pattern_for_decrease(pattern: Dict[str, float], ratio: float) -> Dict[str, float]:
    """Adjust pattern when decreasing hours - protect core work"""
    adjusted = {}
    core_keys = ['development', 'design', 'creation', 'management']
    
    for key, value in pattern.items():
        if any(c in key for c in core_keys):
            # Protect core work from cuts
            adjusted[key] = value * (1 - (1 - ratio) * 0.3)
        else:
            adjusted[key] = value * ratio
    
    # Normalize
    total = sum(adjusted.values())
    return {k: v / total for k, v in adjusted.items()}

def _get_complexity_factor(component_name: str, project_complexity: str) -> float:
    """Determine complexity factor for a component"""
    comp_lower = component_name.lower()
    
    # Critical/complex components
    if any(term in comp_lower for term in ['strategy', 'architecture', 'integration', 'migration']):
        base = ComplexityLevel.COMPLEX.value
    # Moderate complexity
    elif any(term in comp_lower for term in ['development', 'design', 'analysis', 'optimization']):
        base = ComplexityLevel.MODERATE.value
    # Simple tasks
    elif any(term in comp_lower for term in ['documentation', 'setup', 'reporting']):
        base = ComplexityLevel.SIMPLE.value
    else:
        base = ComplexityLevel.MODERATE.value
    
    # Adjust based on project complexity
    if project_complexity == "Advanced":
        return base * 1.2
    elif project_complexity == "Basic":
        return base * 0.8
    return base

def calculate_retainer_distribution(
    monthly_hours: float,
    duration_months: int = 12,
    ramp_up: bool = True,
    seasonality: Optional[List[float]] = None
) -> Dict[str, float]:
    """
    Calculate monthly hour distribution for retainer engagements
    
    Args:
        monthly_hours: Base monthly hours
        duration_months: Total months of engagement
        ramp_up: Whether to include ramp-up period
        seasonality: Optional list of seasonal multipliers
        
    Returns:
        Dictionary with month names as keys and hours as values
    """
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    distribution = {}
    
    for i in range(duration_months):
        month_name = months[i % 12]
        if i >= 12:
            month_name = f"{month_name} Y{(i // 12) + 1}"
        
        base_hours = monthly_hours
        
        # Apply ramp-up for first 3 months
        if ramp_up and i < 3:
            ramp_factors = [0.7, 0.85, 1.0]
            base_hours *= ramp_factors[i]
        
        # Apply seasonality if provided
        if seasonality and len(seasonality) > (i % 12):
            base_hours *= seasonality[i % 12]
        
        distribution[month_name] = round(base_hours, 1)
    
    return distribution

class PricingOptimizer:
    """AI-powered pricing optimization for agency deliverables"""
    
    def __init__(self):
        self.client = client  # Use the global OpenAI client
        self.available = OPENAI_AVAILABLE
    
    async def should_be_retainer(
        self, 
        deliverable_name: str, 
        rfp_text: str = ""
    ) -> Dict[str, Any]:
        """
        Determine if a deliverable should be a retainer based on AI analysis
        
        Args:
            deliverable_name: Name of the deliverable
            rfp_text: Optional RFP text for context
            
        Returns:
            Dictionary with is_retainer, suggested_months, and reasoning
        """
        
        # If no AI available, fall back to rule-based
        if not self.available or not self.client:
            return self._rule_based_retainer_check(deliverable_name)
        
        try:
            # Build prompt for GPT
            system_prompt = """You are an expert project manager determining if deliverables should be retainer-based or project-based.
            
            Retainers are best for:
            - Ongoing, recurring work (management, maintenance, monitoring)
            - Regular monthly activities (social media, SEO, reporting)
            - Long-term engagements with consistent effort
            
            Projects are best for:
            - One-time deliverables (audits, launches, setups)
            - Fixed-scope work with clear endpoints
            - Discovery/research phases
            
            Analyze the deliverable name and context, then respond with JSON."""
            
            user_prompt = f"""Deliverable: {deliverable_name}
            
            {f'RFP Context: {rfp_text[:1000]}' if rfp_text else ''}
            
            Should this be a retainer or project? If retainer, suggest duration in months (typically 6, 12, or 24).
            
            Respond with JSON:
            {{
                "is_retainer": boolean,
                "suggested_months": number (0 if project, 6/12/24 if retainer),
                "reasoning": "explanation",
                "confidence": 0.0-1.0
            }}"""
            
            # Model will be auto-enforced by sitecustomize.py
            response = await self.client.chat.completions.create(
                model="gpt-5-mini",  # sitecustomize.py will enforce GPT-5
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "is_retainer": result.get("is_retainer", False),
                "suggested_months": result.get("suggested_months", 12) if result.get("is_retainer") else 0,
                "reasoning": result.get("reasoning", "AI analysis"),
                "confidence": result.get("confidence", 0.8)
            }
            
        except Exception as e:
            print(f"[PricingOptimizer] AI analysis failed: {e}")
            return self._rule_based_retainer_check(deliverable_name)
    
    def _rule_based_retainer_check(self, deliverable_name: str) -> Dict[str, Any]:
        """Fallback rule-based retainer detection"""
        name_lower = deliverable_name.lower()
        
        # Keywords strongly suggesting retainer
        retainer_keywords = [
            'management', 'maintenance', 'monitoring', 'optimization',
            'ongoing', 'monthly', 'reporting', 'social media', 'seo', 'ppc',
            'content creation', 'community', 'support', 'analytics'
        ]
        
        # Keywords strongly suggesting project
        project_keywords = [
            'development', 'launch', 'setup', 'migration', 'redesign',
            'implementation', 'integration', 'audit', 'strategy', 'research',
            'discovery', 'assessment', 'blueprint', 'roadmap'
        ]
        
        retainer_score = sum(1 for k in retainer_keywords if k in name_lower)
        project_score = sum(1 for k in project_keywords if k in name_lower)
        
        is_retainer = retainer_score > project_score
        
        if is_retainer:
            # Determine suggested months based on type
            if 'annual' in name_lower or 'yearly' in name_lower:
                months = 12
            elif 'quarter' in name_lower:
                months = 3
            elif 'half-year' in name_lower or 'semi-annual' in name_lower:
                months = 6
            else:
                months = 12  # Default to annual
            
            reasoning = f"Ongoing service indicated by: {', '.join([k for k in retainer_keywords if k in name_lower])}"
        else:
            months = 0
            reasoning = f"One-time project indicated by: {', '.join([k for k in project_keywords if k in name_lower]) if project_score > 0 else 'default classification'}"
        
        return {
            "is_retainer": is_retainer,
            "suggested_months": months,
            "reasoning": reasoning,
            "confidence": min(0.6 + abs(retainer_score - project_score) * 0.1, 0.9)
        }

def analyze_retainer_vs_project(
    deliverable_name: str,
    total_hours: float,
    duration_months: int = 12
) -> Dict[str, Any]:
    """
    Analyze whether deliverable should be retainer vs project-based
    
    Returns recommendation with reasoning
    """
    
    monthly_avg = total_hours / duration_months if duration_months > 0 else total_hours
    
    # Keywords that suggest retainer
    retainer_keywords = [
        'management', 'maintenance', 'monitoring', 'optimization',
        'ongoing', 'monthly', 'reporting', 'social', 'seo', 'ppc',
        'content creation', 'community'
    ]
    
    # Keywords that suggest project
    project_keywords = [
        'development', 'launch', 'setup', 'migration', 'redesign',
        'implementation', 'integration', 'audit', 'strategy', 'research'
    ]
    
    name_lower = deliverable_name.lower()
    
    retainer_score = sum(1 for k in retainer_keywords if k in name_lower)
    project_score = sum(1 for k in project_keywords if k in name_lower)
    
    # Hour-based heuristics
    if monthly_avg < 10:
        project_score += 2  # Too few hours for retainer
    elif monthly_avg > 40:
        retainer_score += 1  # Substantial ongoing work
    
    if total_hours < 40:
        project_score += 2  # Small engagement
    elif total_hours > 480:
        retainer_score += 1  # Large ongoing engagement
    
    recommendation = "retainer" if retainer_score > project_score else "project"
    confidence = abs(retainer_score - project_score) / max(retainer_score + project_score, 1)
    
    reasoning = []
    if recommendation == "retainer":
        reasoning.append(f"Ongoing nature suggested by: {', '.join([k for k in retainer_keywords if k in name_lower])}")
        reasoning.append(f"Average {monthly_avg:.0f} hours/month indicates sustained engagement")
    else:
        reasoning.append(f"Project nature suggested by: {', '.join([k for k in project_keywords if k in name_lower])}")
        if monthly_avg < 10:
            reasoning.append(f"Low monthly hours ({monthly_avg:.0f}) better suited for project approach")
    
    return {
        "recommendation": recommendation,
        "confidence": round(confidence, 2),
        "reasoning": reasoning,
        "monthly_hours": round(monthly_avg, 1),
        "total_hours": total_hours,
        "retainer_score": retainer_score,
        "project_score": project_score
    }