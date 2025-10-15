"""
Lifestyle Industry Template System
===================================
Specialized deliverables, timelines, and pricing for lifestyle brands.

This module provides:
- Brand partnership collaborations
- Experience design and activations  
- Community building initiatives
- Content series and editorial calendars
- Wellness and mindfulness campaigns
- Sustainability and social impact stories
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

# ================================================================================
# Lifestyle Category Constants
# ================================================================================

class LifestyleCategory(str, Enum):
    """Major lifestyle industry categories"""
    HEALTH_WELLNESS = "Health & Wellness"
    FOOD_BEVERAGE = "Food & Beverage"
    TRAVEL_HOSPITALITY = "Travel & Hospitality"
    HOME_DESIGN = "Home & Design"
    SPORTS_FITNESS = "Sports & Fitness"
    BEAUTY_PERSONAL_CARE = "Beauty & Personal Care"
    SUSTAINABLE_LIVING = "Sustainable Living"
    MINDFULNESS_MEDITATION = "Mindfulness & Meditation"

class ExperienceType(str, Enum):
    """Types of lifestyle experiences"""
    IMMERSIVE = "Immersive Experience"
    WORKSHOP = "Workshop/Class"
    RETREAT = "Retreat/Getaway"
    POP_UP = "Pop-Up Activation"
    FESTIVAL = "Festival/Event"
    DIGITAL = "Digital Experience"
    COMMUNITY = "Community Gathering"
    EXCLUSIVE = "Exclusive/VIP Experience"

# Lifestyle Event Calendar
LIFESTYLE_CALENDAR = {
    "New Year Wellness": {
        "month": 1,
        "duration_weeks": 4,
        "categories": ["Health & Wellness", "Sports & Fitness"],
        "focus": "Resolution campaigns, fresh starts"
    },
    "Spring Renewal": {
        "month": [3, 4],
        "duration_weeks": 6,
        "categories": ["Home & Design", "Sustainable Living"],
        "focus": "Spring cleaning, renewal, outdoor living"
    },
    "Summer Lifestyle": {
        "month": [6, 7, 8],
        "duration_weeks": 12,
        "categories": ["Travel & Hospitality", "Food & Beverage"],
        "focus": "Travel, outdoor activities, summer entertaining"
    },
    "Back to Routine": {
        "month": 9,
        "duration_weeks": 3,
        "categories": ["Health & Wellness", "Mindfulness & Meditation"],
        "focus": "Routine reset, productivity, balance"
    },
    "Holiday Entertaining": {
        "month": [11, 12],
        "duration_weeks": 8,
        "categories": ["Food & Beverage", "Home & Design"],
        "focus": "Entertaining, gifting, celebration"
    }
}

# ================================================================================
# Lifestyle Deliverables
# ================================================================================

@dataclass
class LifestyleDeliverable:
    """Lifestyle-specific deliverable with experience attributes"""
    code: str
    name: str
    category: str
    components: List[str]
    base_hours: float
    experience_multiplier: float = 1.0
    revision_rounds: int = 2
    requires_venue: bool = False
    requires_permits: bool = False
    requires_talent: bool = False
    community_focused: bool = False
    sustainability_aligned: bool = False
    
def get_lifestyle_deliverables() -> List[LifestyleDeliverable]:
    """Return comprehensive list of lifestyle deliverables"""
    return [
        # ========== BRAND PARTNERSHIPS ==========
        LifestyleDeliverable(
            code="LS-PART-001",
            name="Brand Partnership Strategy",
            category="Brand Collaborations",
            components=[
                "Partner brand identification and vetting",
                "Collaboration framework development",
                "Co-branding guidelines",
                "Revenue sharing model",
                "Joint marketing strategy",
                "Legal framework setup",
                "Performance metrics definition"
            ],
            base_hours=120,
            experience_multiplier=1.5
        ),
        LifestyleDeliverable(
            code="LS-PART-002",
            name="Co-Branded Product Launch",
            category="Brand Collaborations",
            components=[
                "Product concept development",
                "Design collaboration process",
                "Production coordination",
                "Launch strategy planning",
                "PR and media outreach",
                "Distribution channel setup",
                "Launch event execution"
            ],
            base_hours=200,
            experience_multiplier=1.7,
            requires_venue=True
        ),
        LifestyleDeliverable(
            code="LS-PART-003",
            name="Influencer Collaboration Program",
            category="Influencer Marketing",
            components=[
                "Lifestyle influencer identification",
                "Authentic partnership development",
                "Content co-creation framework",
                "Long-term relationship building",
                "Content calendar coordination",
                "Performance tracking system",
                "Community engagement strategy"
            ],
            base_hours=140,
            experience_multiplier=1.4,
            requires_talent=True,
            community_focused=True
        ),
        LifestyleDeliverable(
            code="LS-PART-004",
            name="Celebrity Lifestyle Partnership",
            category="Celebrity Collaborations",
            components=[
                "Celebrity lifestyle alignment audit",
                "Partnership negotiation",
                "Signature product/service development",
                "Content creation schedule",
                "Media appearances coordination",
                "Social amplification strategy",
                "Fan engagement activations"
            ],
            base_hours=280,
            experience_multiplier=2.0,
            requires_talent=True
        ),
        
        # ========== EXPERIENCE DESIGN ==========
        LifestyleDeliverable(
            code="LS-EXP-001",
            name="Immersive Brand Experience",
            category="Experiential Marketing",
            components=[
                "Experience concept development",
                "Multi-sensory design planning",
                "Interactive technology integration",
                "Visitor journey mapping",
                "Staff training and scripting",
                "Data capture strategy",
                "Social sharing moments design",
                "Post-experience follow-up"
            ],
            base_hours=240,
            experience_multiplier=1.8,
            requires_venue=True,
            requires_permits=True
        ),
        LifestyleDeliverable(
            code="LS-EXP-002",
            name="Lifestyle Workshop Series",
            category="Educational Experiences",
            components=[
                "Workshop curriculum development",
                "Expert instructor recruitment",
                "Venue selection and setup",
                "Materials and supplies sourcing",
                "Registration system setup",
                "Attendee experience design",
                "Follow-up content creation",
                "Community building strategy"
            ],
            base_hours=160,
            experience_multiplier=1.5,
            requires_venue=True,
            requires_talent=True,
            community_focused=True
        ),
        LifestyleDeliverable(
            code="LS-EXP-003",
            name="Wellness Retreat Program",
            category="Wellness Experiences",
            components=[
                "Retreat concept and theme",
                "Location scouting and booking",
                "Wellness expert curation",
                "Daily schedule programming",
                "Accommodation coordination",
                "Healthy catering planning",
                "Mindfulness activities design",
                "Take-home resources creation"
            ],
            base_hours=280,
            experience_multiplier=1.9,
            requires_venue=True,
            requires_talent=True
        ),
        LifestyleDeliverable(
            code="LS-EXP-004",
            name="Pop-Up Experience Activation",
            category="Pop-Up Experiences",
            components=[
                "Pop-up concept development",
                "Location strategy and negotiation",
                "Experience design and build-out",
                "Interactive elements planning",
                "Staffing and training",
                "Queue management system",
                "Social media integration",
                "Performance analytics"
            ],
            base_hours=200,
            experience_multiplier=1.6,
            requires_venue=True,
            requires_permits=True
        ),
        LifestyleDeliverable(
            code="LS-EXP-005",
            name="Virtual Lifestyle Experience",
            category="Digital Experiences",
            components=[
                "Virtual platform selection",
                "Digital experience design",
                "Live streaming setup",
                "Interactive features development",
                "At-home kit creation and shipping",
                "Host training and preparation",
                "Community engagement tools",
                "Recording and replay strategy"
            ],
            base_hours=140,
            experience_multiplier=1.4
        ),
        
        # ========== COMMUNITY BUILDING ==========
        LifestyleDeliverable(
            code="LS-COMM-001",
            name="Brand Community Platform",
            category="Community Development",
            components=[
                "Community platform selection",
                "Membership structure design",
                "Content strategy development",
                "Moderation guidelines creation",
                "Ambassador program setup",
                "Engagement tactics planning",
                "Rewards and recognition system",
                "Community growth strategy"
            ],
            base_hours=180,
            experience_multiplier=1.5,
            community_focused=True
        ),
        LifestyleDeliverable(
            code="LS-COMM-002",
            name="Local Community Activation",
            category="Community Engagement",
            components=[
                "Local market research",
                "Community partner identification",
                "Event series planning",
                "Volunteer program development",
                "Local influencer engagement",
                "Neighborhood marketing",
                "Impact measurement framework"
            ],
            base_hours=140,
            experience_multiplier=1.4,
            community_focused=True,
            sustainability_aligned=True
        ),
        LifestyleDeliverable(
            code="LS-COMM-003",
            name="User-Generated Content Campaign",
            category="Community Content",
            components=[
                "UGC campaign concept",
                "Hashtag strategy development",
                "Submission platform setup",
                "Content curation process",
                "Legal and rights management",
                "Amplification strategy",
                "Creator recognition program",
                "Content repurposing plan"
            ],
            base_hours=100,
            experience_multiplier=1.3,
            community_focused=True
        ),
        LifestyleDeliverable(
            code="LS-COMM-004",
            name="Lifestyle Membership Program",
            category="Loyalty & Membership",
            components=[
                "Membership tier structure",
                "Benefits package design",
                "Exclusive access planning",
                "Member portal development",
                "Communication strategy",
                "Event and experience calendar",
                "Retention tactics development"
            ],
            base_hours=160,
            experience_multiplier=1.5,
            community_focused=True
        ),
        
        # ========== CONTENT SERIES ==========
        LifestyleDeliverable(
            code="LS-CONT-001",
            name="Editorial Content Calendar",
            category="Content Marketing",
            components=[
                "Annual content strategy",
                "Monthly theme development",
                "Content pillar definition",
                "Editorial calendar creation",
                "Writer and contributor network",
                "Photography planning",
                "Distribution strategy",
                "Performance metrics setup"
            ],
            base_hours=120,
            experience_multiplier=1.3
        ),
        LifestyleDeliverable(
            code="LS-CONT-002",
            name="Lifestyle Video Series",
            category="Video Content",
            components=[
                "Series concept development",
                "Episode planning and scripting",
                "Production crew assembly",
                "Location scouting",
                "Filming schedule creation",
                "Post-production workflow",
                "Distribution platform strategy",
                "Audience engagement plan"
            ],
            base_hours=240,
            experience_multiplier=1.7,
            requires_talent=True,
            requires_venue=True
        ),
        LifestyleDeliverable(
            code="LS-CONT-003",
            name="Podcast Series Production",
            category="Audio Content",
            components=[
                "Podcast concept and format",
                "Guest curation strategy",
                "Recording setup and equipment",
                "Episode production workflow",
                "Editing and sound design",
                "Distribution platform setup",
                "Promotion strategy",
                "Listener community building"
            ],
            base_hours=160,
            experience_multiplier=1.4,
            requires_talent=True
        ),
        LifestyleDeliverable(
            code="LS-CONT-004",
            name="Coffee Table Book Project",
            category="Premium Content",
            components=[
                "Book concept development",
                "Content curation and creation",
                "Photography direction",
                "Design and layout",
                "Publisher negotiation",
                "Launch strategy planning",
                "Signing events coordination",
                "PR and media outreach"
            ],
            base_hours=320,
            experience_multiplier=1.8,
            requires_talent=True
        ),
        LifestyleDeliverable(
            code="LS-CONT-005",
            name="Digital Magazine Launch",
            category="Digital Publishing",
            components=[
                "Magazine concept and positioning",
                "Digital platform selection",
                "Content strategy development",
                "Contributor network building",
                "Design template creation",
                "Subscription model setup",
                "Launch campaign development",
                "Reader engagement strategy"
            ],
            base_hours=200,
            experience_multiplier=1.5
        ),
        
        # ========== WELLNESS CAMPAIGNS ==========
        LifestyleDeliverable(
            code="LS-WELL-001",
            name="Corporate Wellness Program",
            category="Wellness Initiatives",
            components=[
                "Wellness assessment framework",
                "Program structure design",
                "Activity and challenge calendar",
                "Digital platform integration",
                "Incentive program development",
                "Progress tracking system",
                "Communication strategy",
                "ROI measurement framework"
            ],
            base_hours=180,
            experience_multiplier=1.5
        ),
        LifestyleDeliverable(
            code="LS-WELL-002",
            name="Mindfulness Campaign",
            category="Mental Wellness",
            components=[
                "Campaign theme development",
                "Meditation content creation",
                "App or platform integration",
                "Expert practitioner partnerships",
                "Daily practice guides",
                "Community support system",
                "Progress tracking tools",
                "Success story amplification"
            ],
            base_hours=120,
            experience_multiplier=1.3,
            community_focused=True
        ),
        LifestyleDeliverable(
            code="LS-WELL-003",
            name="Fitness Challenge Program",
            category="Physical Wellness",
            components=[
                "Challenge concept and rules",
                "Registration platform setup",
                "Training plan development",
                "Nutrition guidance creation",
                "Progress tracking app integration",
                "Community support forums",
                "Prize and recognition system",
                "Celebration event planning"
            ],
            base_hours=140,
            experience_multiplier=1.4,
            community_focused=True
        ),
        LifestyleDeliverable(
            code="LS-WELL-004",
            name="Holistic Health Initiative",
            category="Holistic Wellness",
            components=[
                "Holistic health assessment",
                "Multi-dimensional wellness plan",
                "Expert practitioner network",
                "Educational content series",
                "Personal consultation framework",
                "Product recommendation system",
                "Community support groups",
                "Outcome measurement tools"
            ],
            base_hours=200,
            experience_multiplier=1.6,
            requires_talent=True
        ),
        
        # ========== SUSTAINABILITY INITIATIVES ==========
        LifestyleDeliverable(
            code="LS-SUS-001",
            name="Sustainable Living Campaign",
            category="Sustainability",
            components=[
                "Sustainability audit and baseline",
                "Campaign narrative development",
                "Educational content creation",
                "Partner organization collaboration",
                "Challenge and pledge system",
                "Impact tracking dashboard",
                "Success story documentation",
                "Media and PR strategy"
            ],
            base_hours=160,
            experience_multiplier=1.4,
            sustainability_aligned=True,
            community_focused=True
        ),
        LifestyleDeliverable(
            code="LS-SUS-002",
            name="Zero Waste Initiative",
            category="Environmental Impact",
            components=[
                "Waste audit and analysis",
                "Reduction strategy development",
                "Alternative solution sourcing",
                "Staff and customer education",
                "Implementation roadmap",
                "Progress monitoring system",
                "Certification pursuit",
                "Impact communication plan"
            ],
            base_hours=180,
            experience_multiplier=1.5,
            sustainability_aligned=True
        ),
        LifestyleDeliverable(
            code="LS-SUS-003",
            name="Social Impact Partnership",
            category="Social Responsibility",
            components=[
                "Cause alignment assessment",
                "Non-profit partner selection",
                "Partnership framework design",
                "Volunteer program development",
                "Fundraising campaign creation",
                "Impact measurement system",
                "Stakeholder communication",
                "Annual impact report"
            ],
            base_hours=140,
            experience_multiplier=1.4,
            sustainability_aligned=True,
            community_focused=True
        ),
        LifestyleDeliverable(
            code="LS-SUS-004",
            name="Circular Economy Program",
            category="Sustainable Business",
            components=[
                "Product lifecycle assessment",
                "Take-back program design",
                "Refurbishment process setup",
                "Resale platform development",
                "Customer education campaign",
                "Partner network building",
                "Impact tracking system",
                "Marketing and communication"
            ],
            base_hours=200,
            experience_multiplier=1.6,
            sustainability_aligned=True
        ),
        
        # ========== CATEGORY-SPECIFIC: HEALTH & WELLNESS ==========
        LifestyleDeliverable(
            code="LS-HW-001",
            name="Nutrition Program Launch",
            category="Health & Wellness",
            components=[
                "Program framework development",
                "Nutritionist partnership",
                "Meal plan creation",
                "Recipe content development",
                "Shopping guide creation",
                "Progress tracking tools",
                "Community support system",
                "Success metrics framework"
            ],
            base_hours=160,
            experience_multiplier=1.5,
            requires_talent=True
        ),
        LifestyleDeliverable(
            code="LS-HW-002",
            name="Mental Health Awareness Campaign",
            category="Health & Wellness",
            components=[
                "Campaign strategy development",
                "Expert advisory board setup",
                "Educational content creation",
                "Resource hub development",
                "Support group facilitation",
                "Crisis resource integration",
                "Stigma reduction messaging",
                "Impact measurement"
            ],
            base_hours=180,
            experience_multiplier=1.6,
            requires_talent=True,
            community_focused=True
        ),
        
        # ========== CATEGORY-SPECIFIC: FOOD & BEVERAGE ==========
        LifestyleDeliverable(
            code="LS-FB-001",
            name="Culinary Experience Series",
            category="Food & Beverage",
            components=[
                "Chef partnership development",
                "Menu curation and testing",
                "Venue selection and setup",
                "Ticketing system implementation",
                "Wine/beverage pairing",
                "Guest experience design",
                "Photography and content capture",
                "Follow-up engagement"
            ],
            base_hours=200,
            experience_multiplier=1.7,
            requires_venue=True,
            requires_talent=True
        ),
        LifestyleDeliverable(
            code="LS-FB-002",
            name="Food Festival Activation",
            category="Food & Beverage",
            components=[
                "Festival concept development",
                "Vendor curation and coordination",
                "Layout and flow design",
                "Entertainment programming",
                "Ticketing and access control",
                "Marketing and promotion",
                "On-site operations management",
                "Post-event analysis"
            ],
            base_hours=280,
            experience_multiplier=1.8,
            requires_venue=True,
            requires_permits=True
        ),
        LifestyleDeliverable(
            code="LS-FB-003",
            name="Mixology Program Development",
            category="Food & Beverage",
            components=[
                "Cocktail menu development",
                "Bartender training program",
                "Signature drink creation",
                "Glassware and tool sourcing",
                "Recipe standardization",
                "Cost analysis and pricing",
                "Marketing materials creation",
                "Launch event planning"
            ],
            base_hours=120,
            experience_multiplier=1.4,
            requires_talent=True
        ),
        
        # ========== CATEGORY-SPECIFIC: TRAVEL & HOSPITALITY ==========
        LifestyleDeliverable(
            code="LS-TH-001",
            name="Destination Experience Package",
            category="Travel & Hospitality",
            components=[
                "Destination research and selection",
                "Itinerary development",
                "Local partner coordination",
                "Accommodation arrangements",
                "Activity and excursion planning",
                "Cultural experience integration",
                "Travel logistics management",
                "Guest communication system"
            ],
            base_hours=180,
            experience_multiplier=1.6,
            requires_venue=True
        ),
        LifestyleDeliverable(
            code="LS-TH-002",
            name="Boutique Hotel Launch",
            category="Travel & Hospitality",
            components=[
                "Brand positioning strategy",
                "Guest experience design",
                "Amenity and service planning",
                "Staff training program",
                "Soft opening strategy",
                "Influencer hosting program",
                "PR and media strategy",
                "Grand opening event"
            ],
            base_hours=320,
            experience_multiplier=1.9,
            requires_venue=True
        ),
        
        # ========== CATEGORY-SPECIFIC: HOME & DESIGN ==========
        LifestyleDeliverable(
            code="LS-HD-001",
            name="Home Makeover Series",
            category="Home & Design",
            components=[
                "Series concept development",
                "Designer partnerships",
                "Participant selection process",
                "Before documentation",
                "Design planning and execution",
                "Reveal event coordination",
                "Content creation and editing",
                "Sponsor integration"
            ],
            base_hours=240,
            experience_multiplier=1.7,
            requires_talent=True,
            requires_venue=True
        ),
        LifestyleDeliverable(
            code="LS-HD-002",
            name="Sustainable Home Program",
            category="Home & Design",
            components=[
                "Eco-audit framework",
                "Sustainable product sourcing",
                "Energy efficiency planning",
                "Water conservation systems",
                "Indoor air quality improvement",
                "Waste reduction strategies",
                "ROI calculator development",
                "Education and support materials"
            ],
            base_hours=180,
            experience_multiplier=1.5,
            sustainability_aligned=True
        ),
        
        # ========== CATEGORY-SPECIFIC: SPORTS & FITNESS ==========
        LifestyleDeliverable(
            code="LS-SF-001",
            name="Athletic Training Program",
            category="Sports & Fitness",
            components=[
                "Training methodology development",
                "Coach and trainer recruitment",
                "Facility or platform setup",
                "Equipment specification",
                "Progress tracking system",
                "Nutrition integration",
                "Community building",
                "Performance showcase events"
            ],
            base_hours=200,
            experience_multiplier=1.6,
            requires_talent=True,
            requires_venue=True
        ),
        LifestyleDeliverable(
            code="LS-SF-002",
            name="Sports Event Sponsorship",
            category="Sports & Fitness",
            components=[
                "Event selection and negotiation",
                "Activation strategy development",
                "On-site experience design",
                "Athlete partnerships",
                "Fan engagement activities",
                "Content creation plan",
                "Merchandise strategy",
                "ROI measurement framework"
            ],
            base_hours=220,
            experience_multiplier=1.7,
            requires_venue=True
        )
    ]

# ================================================================================
# Timeline Calculation Functions
# ================================================================================

def calculate_lifestyle_timeline(
    deliverables: List[LifestyleDeliverable],
    experience_complexity: str = "moderate",  # simple, moderate, complex
    seasonal_factor: bool = False
) -> Dict[str, Any]:
    """Calculate timeline for lifestyle deliverables"""
    
    # Base calculation
    total_hours = sum(d.base_hours * d.experience_multiplier for d in deliverables)
    
    # Experience complexity adjustments
    complexity_factors = {
        "simple": 0.8,
        "moderate": 1.0,
        "complex": 1.3
    }
    total_hours *= complexity_factors.get(experience_complexity, 1.0)
    
    # Seasonal adjustments (lifestyle events often tied to seasons)
    if seasonal_factor:
        total_hours *= 1.2
    
    # Calculate weeks
    weeks = total_hours / 40
    
    # Add buffers for specific requirements
    if any(d.requires_permits for d in deliverables):
        weeks += 3  # Permit processing time
    if any(d.requires_venue for d in deliverables):
        weeks += 2  # Venue coordination buffer
    if any(d.requires_talent for d in deliverables):
        weeks += 1.5  # Talent booking buffer
    
    return {
        "total_hours": round(total_hours),
        "estimated_weeks": round(weeks, 1),
        "recommended_team_size": max(2, min(10, len(deliverables) // 2)),
        "critical_dependencies": {
            "permits_required": any(d.requires_permits for d in deliverables),
            "venues_required": any(d.requires_venue for d in deliverables),
            "talent_required": any(d.requires_talent for d in deliverables)
        }
    }

# ================================================================================
# Pricing Calculation Functions
# ================================================================================

def calculate_lifestyle_pricing(
    deliverables: List[LifestyleDeliverable],
    brand_tier: str = "premium",  # emerging, established, premium, luxury
    project_scope: str = "campaign"  # campaign, program, transformation
) -> Dict[str, Any]:
    """Calculate pricing for lifestyle deliverables"""
    
    # Base hourly rates by brand tier
    hourly_rates = {
        "emerging": 125,
        "established": 175,
        "premium": 225,
        "luxury": 300
    }
    
    # Scope multipliers
    scope_multipliers = {
        "campaign": 1.0,
        "program": 1.2,  # Ongoing program
        "transformation": 1.5  # Brand transformation
    }
    
    base_rate = hourly_rates.get(brand_tier, 175)
    scope_mult = scope_multipliers.get(project_scope, 1.0)
    
    # Calculate deliverable costs
    deliverable_costs = []
    for d in deliverables:
        hours = d.base_hours * d.experience_multiplier
        
        # Add premiums for special requirements
        venue_premium = 1.15 if d.requires_venue else 1.0
        talent_premium = 1.2 if d.requires_talent else 1.0
        sustainability_premium = 1.1 if d.sustainability_aligned else 1.0
        
        cost = hours * base_rate * scope_mult * venue_premium * talent_premium * sustainability_premium
        
        deliverable_costs.append({
            "deliverable": d.name,
            "hours": round(hours),
            "cost": round(cost, -2),
            "special_requirements": {
                "venue": d.requires_venue,
                "talent": d.requires_talent,
                "permits": d.requires_permits,
                "community": d.community_focused,
                "sustainability": d.sustainability_aligned
            }
        })
    
    total_cost = sum(dc["cost"] for dc in deliverable_costs)
    
    # Volume discounts
    if total_cost > 150000:
        discount = 0.12
    elif total_cost > 75000:
        discount = 0.08
    elif total_cost > 40000:
        discount = 0.05
    else:
        discount = 0
    
    final_cost = total_cost * (1 - discount)
    
    return {
        "deliverable_breakdown": deliverable_costs,
        "subtotal": total_cost,
        "discount_percentage": discount * 100,
        "discount_amount": total_cost * discount,
        "total_cost": round(final_cost, -2),
        "payment_structure": "Milestone-based" if project_scope == "transformation" else "50% upfront, 50% on completion",
        "includes_expenses": False,
        "expense_estimate": round(total_cost * 0.15, -2)  # Typical 15% for production expenses
    }

# ================================================================================
# Template Matching Functions
# ================================================================================

def match_lifestyle_requirements(
    requirements_text: str,
    category_focus: Optional[LifestyleCategory] = None
) -> List[LifestyleDeliverable]:
    """Match requirements to appropriate lifestyle deliverables"""
    
    all_deliverables = get_lifestyle_deliverables()
    requirements_lower = requirements_text.lower()
    matched_deliverables = []
    
    # Category filtering
    if category_focus:
        category_keywords = {
            LifestyleCategory.HEALTH_WELLNESS: ["health", "wellness", "nutrition", "mental"],
            LifestyleCategory.FOOD_BEVERAGE: ["food", "culinary", "restaurant", "beverage"],
            LifestyleCategory.TRAVEL_HOSPITALITY: ["travel", "hotel", "destination", "hospitality"],
            LifestyleCategory.HOME_DESIGN: ["home", "interior", "design", "decor"],
            LifestyleCategory.SPORTS_FITNESS: ["sports", "fitness", "athletic", "training"]
        }
        
        relevant_keywords = category_keywords.get(category_focus, [])
        for keyword in relevant_keywords:
            if keyword in requirements_lower:
                category_deliverables = [d for d in all_deliverables if keyword in d.name.lower()]
                matched_deliverables.extend(category_deliverables)
    
    # Keyword mapping
    keyword_map = {
        "partnership": ["LS-PART-001", "LS-PART-002", "LS-PART-003"],
        "influencer": ["LS-PART-003", "LS-PART-004"],
        "experience": ["LS-EXP-001", "LS-EXP-002", "LS-EXP-003"],
        "workshop": ["LS-EXP-002"],
        "retreat": ["LS-EXP-003"],
        "pop-up": ["LS-EXP-004"],
        "virtual": ["LS-EXP-005"],
        "community": ["LS-COMM-001", "LS-COMM-002", "LS-COMM-003"],
        "membership": ["LS-COMM-004"],
        "content": ["LS-CONT-001", "LS-CONT-002", "LS-CONT-003"],
        "video": ["LS-CONT-002"],
        "podcast": ["LS-CONT-003"],
        "wellness": ["LS-WELL-001", "LS-WELL-002", "LS-WELL-003"],
        "mindfulness": ["LS-WELL-002"],
        "fitness": ["LS-WELL-003", "LS-SF-001"],
        "sustainability": ["LS-SUS-001", "LS-SUS-002"],
        "social impact": ["LS-SUS-003"],
        "circular": ["LS-SUS-004"],
        "nutrition": ["LS-HW-001"],
        "mental health": ["LS-HW-002"],
        "culinary": ["LS-FB-001", "LS-FB-002"],
        "food festival": ["LS-FB-002"],
        "travel": ["LS-TH-001"],
        "hotel": ["LS-TH-002"],
        "home": ["LS-HD-001", "LS-HD-002"],
        "sports": ["LS-SF-001", "LS-SF-002"]
    }
    
    # Check for keyword matches
    for keyword, codes in keyword_map.items():
        if keyword in requirements_lower:
            for code in codes:
                deliverable = next((d for d in all_deliverables if d.code == code), None)
                if deliverable and deliverable not in matched_deliverables:
                    matched_deliverables.append(deliverable)
    
    # If no matches, suggest popular lifestyle deliverables
    if not matched_deliverables:
        popular_codes = ["LS-EXP-001", "LS-COMM-001", "LS-CONT-001", "LS-WELL-001"]
        for code in popular_codes:
            deliverable = next((d for d in all_deliverables if d.code == code), None)
            if deliverable:
                matched_deliverables.append(deliverable)
    
    return matched_deliverables

# ================================================================================
# Main Lifestyle Template Class
# ================================================================================

class LifestyleTemplate:
    """Main class for lifestyle industry template management"""
    
    def __init__(self):
        self.deliverables = get_lifestyle_deliverables()
        self.categories = LifestyleCategory
        self.experience_types = ExperienceType
        self.calendar = LIFESTYLE_CALENDAR
    
    def get_category_deliverables(self, category: LifestyleCategory) -> List[LifestyleDeliverable]:
        """Get deliverables for a specific lifestyle category"""
        category_name = category.value.lower()
        return [
            d for d in self.deliverables 
            if category_name in d.category.lower() or category_name in d.name.lower()
        ]
    
    def get_experience_package(self, experience_type: ExperienceType) -> List[LifestyleDeliverable]:
        """Get deliverables for a specific experience type"""
        experience_codes = {
            ExperienceType.IMMERSIVE: ["LS-EXP-001", "LS-EXP-004"],
            ExperienceType.WORKSHOP: ["LS-EXP-002", "LS-WELL-003"],
            ExperienceType.RETREAT: ["LS-EXP-003", "LS-WELL-001"],
            ExperienceType.POP_UP: ["LS-EXP-004"],
            ExperienceType.FESTIVAL: ["LS-FB-002"],
            ExperienceType.DIGITAL: ["LS-EXP-005", "LS-CONT-001"],
            ExperienceType.COMMUNITY: ["LS-COMM-001", "LS-COMM-002"],
            ExperienceType.EXCLUSIVE: ["LS-COMM-004", "LS-PART-004"]
        }
        
        codes = experience_codes.get(experience_type, [])
        return [d for d in self.deliverables if d.code in codes]
    
    def get_sustainability_focused(self) -> List[LifestyleDeliverable]:
        """Get all sustainability-aligned deliverables"""
        return [d for d in self.deliverables if d.sustainability_aligned]
    
    def get_community_focused(self) -> List[LifestyleDeliverable]:
        """Get all community-focused deliverables"""
        return [d for d in self.deliverables if d.community_focused]
    
    def get_suggested_deliverables(self, rfp_keywords: List[str]) -> List[Dict[str, Any]]:
        """Match deliverables based on RFP keywords - API compatible method"""
        keywords_lower = [kw.lower() for kw in rfp_keywords]
        suggested = []
        
        # Keyword to deliverable mapping
        keyword_map = {
            "partnership": ["LS-PART-001", "LS-PART-002", "LS-PART-003"],
            "brand collab": ["LS-PART-001", "LS-PART-002"],
            "influencer": ["LS-PART-003", "LS-PART-004"],
            "celebrity": ["LS-PART-004"],
            "experience": ["LS-EXP-001", "LS-EXP-002", "LS-EXP-003"],
            "immersive": ["LS-EXP-001"],
            "workshop": ["LS-EXP-002"],
            "retreat": ["LS-EXP-003"],
            "wellness retreat": ["LS-EXP-003"],
            "pop-up": ["LS-EXP-004"],
            "popup": ["LS-EXP-004"],
            "virtual": ["LS-EXP-005"],
            "digital experience": ["LS-EXP-005"],
            "community": ["LS-COMM-001", "LS-COMM-002", "LS-COMM-003"],
            "ugc": ["LS-COMM-003"],
            "user generated": ["LS-COMM-003"],
            "membership": ["LS-COMM-004"],
            "content": ["LS-CONT-001", "LS-CONT-002", "LS-CONT-003"],
            "editorial": ["LS-CONT-001"],
            "video": ["LS-CONT-002"],
            "podcast": ["LS-CONT-003"],
            "book": ["LS-CONT-004"],
            "magazine": ["LS-CONT-005"],
            "wellness": ["LS-WELL-001", "LS-WELL-002", "LS-WELL-003"],
            "mindfulness": ["LS-WELL-002"],
            "meditation": ["LS-WELL-002"],
            "fitness": ["LS-WELL-003", "LS-SF-001"],
            "health": ["LS-WELL-004", "LS-HW-001", "LS-HW-002"],
            "sustainability": ["LS-SUS-001", "LS-SUS-002"],
            "sustainable": ["LS-SUS-001", "LS-SUS-002"],
            "zero waste": ["LS-SUS-002"],
            "social impact": ["LS-SUS-003"],
            "circular": ["LS-SUS-004"],
            "nutrition": ["LS-HW-001"],
            "mental health": ["LS-HW-002"],
            "culinary": ["LS-FB-001", "LS-FB-002"],
            "food": ["LS-FB-001", "LS-FB-002", "LS-FB-003"],
            "festival": ["LS-FB-002"],
            "mixology": ["LS-FB-003"],
            "travel": ["LS-TH-001"],
            "hotel": ["LS-TH-002"],
            "hospitality": ["LS-TH-001", "LS-TH-002"],
            "home": ["LS-HD-001", "LS-HD-002"],
            "design": ["LS-HD-001", "LS-HD-002"],
            "sports": ["LS-SF-001", "LS-SF-002"],
            "athletic": ["LS-SF-001"]
        }
        
        # Search for matches
        for keyword in keywords_lower:
            for key, codes in keyword_map.items():
                if key in keyword:
                    for code in codes:
                        deliverable = next((d for d in self.deliverables if d.code == code), None)
                        if deliverable:
                            # Format for API
                            formatted_deliverable = {
                                "code": deliverable.code,
                                "name": deliverable.name,
                                "category": deliverable.category,
                                "base_hours": deliverable.base_hours,
                                "components": deliverable.components,
                                "match_reason": f"Matched on '{key}'"
                            }
                            # Check if already in suggested (avoid duplicates)
                            if not any(s["code"] == formatted_deliverable["code"] for s in suggested):
                                suggested.append(formatted_deliverable)
        
        # If no matches, return top lifestyle essentials
        if not suggested:
            essential_codes = ["LS-EXP-001", "LS-COMM-001", "LS-CONT-001", "LS-WELL-001"]
            for code in essential_codes:
                deliverable = next((d for d in self.deliverables if d.code == code), None)
                if deliverable:
                    suggested.append({
                        "code": deliverable.code,
                        "name": deliverable.name,
                        "category": deliverable.category,
                        "base_hours": deliverable.base_hours,
                        "components": deliverable.components,
                        "match_reason": "Core lifestyle deliverable"
                    })
        
        # Ensure we return sufficient deliverables (minimum 40 for comprehensive coverage)
        if len(suggested) < 40:
            # Add remaining deliverables with medium confidence
            added_codes = set(s["code"] for s in suggested)
            for deliverable in self.deliverables:
                if deliverable.code not in added_codes:
                    suggested.append({
                        "code": deliverable.code,
                        "name": deliverable.name,
                        "category": deliverable.category,
                        "base_hours": deliverable.base_hours,
                        "components": deliverable.components,
                        "confidence": 0.5,
                        "match_reason": "Full catalog deliverable"
                    })
                    added_codes.add(deliverable.code)
                    if len(suggested) >= 45:  # Cap at 45 deliverables
                        break
        
        return suggested
    
    def calculate_timeline(self, deliverable_codes: List[str], start_date: datetime,
                          experience_complexity: str = "moderate") -> Dict[str, Any]:
        """Calculate timeline for selected deliverables - API compatible method"""
        # Get deliverable objects
        selected_deliverables = []
        for code in deliverable_codes:
            deliverable = next((d for d in self.deliverables if d.code == code), None)
            if deliverable:
                selected_deliverables.append(deliverable)
        
        if not selected_deliverables:
            return {"error": "No valid deliverables found"}
        
        # Use existing timeline calculation
        timeline_info = calculate_lifestyle_timeline(
            selected_deliverables,
            experience_complexity=experience_complexity
        )
        
        # Format for API
        phases = []
        current_date = start_date
        
        for deliverable in selected_deliverables:
            # Calculate duration for this deliverable
            hours = deliverable.base_hours * deliverable.experience_multiplier
            
            # Apply complexity factor
            complexity_factors = {"simple": 0.8, "moderate": 1.0, "complex": 1.3}
            hours *= complexity_factors.get(experience_complexity, 1.0)
            
            weeks = hours / 40
            
            # Add buffer time for special requirements
            if deliverable.requires_permits:
                weeks += 3
            elif deliverable.requires_venue:
                weeks += 2
            elif deliverable.requires_talent:
                weeks += 1.5
            
            end_date = current_date + timedelta(weeks=weeks)
            
            phases.append({
                "deliverable": deliverable.name,
                "start_date": current_date.isoformat(),
                "end_date": end_date.isoformat(),
                "duration_weeks": round(weeks, 1),
                "requires_venue": deliverable.requires_venue,
                "requires_talent": deliverable.requires_talent,
                "requires_permits": deliverable.requires_permits,
                "community_focused": deliverable.community_focused,
                "sustainability_aligned": deliverable.sustainability_aligned
            })
            
            # Next phase starts after this one
            current_date = end_date
        
        return {
            "phases": phases,
            "total_weeks": timeline_info["estimated_weeks"],
            "total_hours": timeline_info["total_hours"],
            "team_size": timeline_info["recommended_team_size"],
            "critical_dependencies": timeline_info.get("critical_dependencies", {})
        }
    
    def calculate_pricing(self, deliverable_codes: List[str], base_rate: float = 175,
                         brand_tier: str = "established") -> Dict[str, Any]:
        """Calculate pricing for selected deliverables - API compatible method"""
        # Get deliverable objects
        selected_deliverables = []
        for code in deliverable_codes:
            deliverable = next((d for d in self.deliverables if d.code == code), None)
            if deliverable:
                selected_deliverables.append(deliverable)
        
        if not selected_deliverables:
            return {"error": "No valid deliverables found"}
        
        # Use existing pricing calculation
        pricing_info = calculate_lifestyle_pricing(
            selected_deliverables,
            brand_tier=brand_tier,
            project_scope="campaign"
        )
        
        return pricing_info
    
    def suggest_deliverables(
        self,
        brand_values: List[str],
        target_audience: str,
        goals: List[str],
        budget_range: Optional[str] = None,
        timeline_weeks: Optional[int] = None
    ) -> Dict[str, Any]:
        """Suggest deliverables based on lifestyle brand needs"""
        
        suggestions = []
        
        # Map brand values to deliverables
        value_mapping = {
            "sustainability": ["LS-SUS-001", "LS-SUS-002", "LS-SUS-004"],
            "community": ["LS-COMM-001", "LS-COMM-002", "LS-COMM-003"],
            "wellness": ["LS-WELL-001", "LS-WELL-002", "LS-WELL-003"],
            "authenticity": ["LS-PART-003", "LS-COMM-003", "LS-CONT-003"],
            "innovation": ["LS-EXP-001", "LS-EXP-005", "LS-CONT-002"],
            "luxury": ["LS-PART-004", "LS-EXP-003", "LS-CONT-004"],
            "accessibility": ["LS-EXP-005", "LS-CONT-001", "LS-COMM-001"]
        }
        
        # Map goals to deliverables
        goal_mapping = {
            "brand awareness": ["LS-PART-001", "LS-EXP-001", "LS-CONT-002"],
            "community building": ["LS-COMM-001", "LS-COMM-002", "LS-EXP-002"],
            "content creation": ["LS-CONT-001", "LS-CONT-002", "LS-CONT-003"],
            "customer loyalty": ["LS-COMM-004", "LS-WELL-001", "LS-EXP-003"],
            "social impact": ["LS-SUS-001", "LS-SUS-003", "LS-COMM-002"],
            "product launch": ["LS-PART-002", "LS-EXP-001", "LS-EXP-004"],
            "thought leadership": ["LS-CONT-003", "LS-CONT-004", "LS-CONT-005"]
        }
        
        # Process brand values
        for value in brand_values:
            value_lower = value.lower()
            for key, codes in value_mapping.items():
                if key in value_lower:
                    for code in codes:
                        d = next((d for d in self.deliverables if d.code == code), None)
                        if d and d not in suggestions:
                            suggestions.append(d)
        
        # Process goals
        for goal in goals:
            goal_lower = goal.lower()
            for key, codes in goal_mapping.items():
                if key in goal_lower:
                    for code in codes:
                        d = next((d for d in self.deliverables if d.code == code), None)
                        if d and d not in suggestions:
                            suggestions.append(d)
        
        # Calculate timeline and pricing
        if suggestions:
            timeline = calculate_lifestyle_timeline(suggestions)
            
            # Determine brand tier from budget
            if budget_range:
                if "50k" in budget_range or "emerging" in budget_range.lower():
                    brand_tier = "emerging"
                elif "100k" in budget_range or "established" in budget_range.lower():
                    brand_tier = "established"
                elif "250k" in budget_range or "premium" in budget_range.lower():
                    brand_tier = "premium"
                else:
                    brand_tier = "luxury"
            else:
                brand_tier = "established"
            
            pricing = calculate_lifestyle_pricing(suggestions, brand_tier)
            
            # Filter by timeline if specified
            if timeline_weeks and timeline["estimated_weeks"] > timeline_weeks:
                # Prioritize based on goals
                suggestions = suggestions[:max(2, len(suggestions) // 2)]
                timeline = calculate_lifestyle_timeline(suggestions)
                pricing = calculate_lifestyle_pricing(suggestions, brand_tier)
            
            return {
                "suggested_deliverables": [d.name for d in suggestions],
                "deliverable_details": [
                    {
                        "code": d.code,
                        "name": d.name,
                        "category": d.category,
                        "hours": d.base_hours,
                        "community_focused": d.community_focused,
                        "sustainability_aligned": d.sustainability_aligned,
                        "requires_venue": d.requires_venue,
                        "requires_talent": d.requires_talent
                    }
                    for d in suggestions
                ],
                "timeline": timeline,
                "pricing": pricing,
                "brand_values": brand_values,
                "target_audience": target_audience,
                "goals": goals
            }
        
        return {
            "suggested_deliverables": [],
            "message": "No specific deliverables matched. Please provide more details about your lifestyle brand."
        }

# ================================================================================
# Export Functions for API Integration
# ================================================================================

def get_lifestyle_template_for_api(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """API endpoint function to get lifestyle template based on requirements"""
    
    template = LifestyleTemplate()
    
    # Extract parameters
    brand_values = requirements.get("brand_values", [])
    target_audience = requirements.get("target_audience", "general")
    goals = requirements.get("goals", [])
    budget_range = requirements.get("budget_range")
    timeline_weeks = requirements.get("timeline_weeks")
    category = requirements.get("category")
    
    # Get suggestions
    result = template.suggest_deliverables(
        brand_values=brand_values,
        target_audience=target_audience,
        goals=goals,
        budget_range=budget_range,
        timeline_weeks=timeline_weeks
    )
    
    # Add category-specific options if requested
    if category:
        try:
            cat_enum = LifestyleCategory(category)
            category_deliverables = template.get_category_deliverables(cat_enum)
            if category_deliverables:
                result["category_options"] = [d.name for d in category_deliverables[:5]]
        except ValueError:
            pass
    
    # Add sustainability and community options
    result["sustainability_options"] = [d.name for d in template.get_sustainability_focused()[:3]]
    result["community_options"] = [d.name for d in template.get_community_focused()[:3]]
    
    return result

def get_lifestyle_deliverable_catalog() -> List[Dict[str, Any]]:
    """Get full catalog of lifestyle deliverables for API"""
    deliverables = get_lifestyle_deliverables()
    return [
        {
            "code": d.code,
            "name": d.name,
            "category": d.category,
            "base_hours": d.base_hours,
            "components": d.components,
            "requires_venue": d.requires_venue,
            "requires_talent": d.requires_talent,
            "requires_permits": d.requires_permits,
            "community_focused": d.community_focused,
            "sustainability_aligned": d.sustainability_aligned
        }
        for d in deliverables
    ]