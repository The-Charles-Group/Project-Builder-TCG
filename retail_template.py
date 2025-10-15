"""
Retail Industry Template System
================================
Specialized deliverables, timelines, and pricing for retail businesses.

This module provides:
- Omnichannel campaign strategies
- Seasonal promotion management
- Loyalty program development
- Store opening campaigns
- E-commerce optimization
- POS and in-store experiences
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

# ================================================================================
# Retail Calendar Constants
# ================================================================================

class RetailSeason(str, Enum):
    """Major retail shopping seasons and events"""
    BLACK_FRIDAY = "Black Friday/Cyber Monday"
    HOLIDAY = "Holiday Shopping Season"
    BACK_TO_SCHOOL = "Back-to-School"
    SPRING_SALE = "Spring Sale Season"
    SUMMER_SALE = "Summer Sale Season"
    PRIME_DAY = "Prime Day/Mid-Year Sale"
    VALENTINES = "Valentine's Day"
    MOTHERS_DAY = "Mother's Day"
    FATHERS_DAY = "Father's Day"
    END_OF_YEAR = "End of Year Clearance"

class RetailChannel(str, Enum):
    """Retail channel types for omnichannel strategies"""
    IN_STORE = "In-Store"
    ECOMMERCE = "E-Commerce"
    MOBILE_APP = "Mobile App"
    SOCIAL_COMMERCE = "Social Commerce"
    MARKETPLACE = "Marketplace"
    POP_UP = "Pop-Up Store"
    WHOLESALE = "Wholesale"
    DTC = "Direct-to-Consumer"

# Retail Calendar - Key promotional periods
RETAIL_CALENDAR = {
    "Black Friday": {
        "month": 11,
        "duration_weeks": 2,
        "prep_lead_time_weeks": 12,
        "priority": "critical"
    },
    "Holiday Season": {
        "month": [11, 12],
        "duration_weeks": 6,
        "prep_lead_time_weeks": 16,
        "priority": "critical"
    },
    "Back-to-School": {
        "month": [7, 8],
        "duration_weeks": 4,
        "prep_lead_time_weeks": 8,
        "priority": "high"
    },
    "Spring Sale": {
        "month": [3, 4],
        "duration_weeks": 3,
        "prep_lead_time_weeks": 6,
        "priority": "medium"
    },
    "Summer Sale": {
        "month": [6, 7],
        "duration_weeks": 3,
        "prep_lead_time_weeks": 6,
        "priority": "medium"
    }
}

# ================================================================================
# Retail Deliverables
# ================================================================================

@dataclass
class RetailDeliverable:
    """Retail-specific deliverable with commerce attributes"""
    code: str
    name: str
    category: str
    components: List[str]
    base_hours: float
    complexity_multiplier: float = 1.0
    revision_rounds: int = 2
    requires_tech_integration: bool = False
    requires_inventory_sync: bool = False
    omnichannel: bool = False
    seasonal: bool = False
    
def get_retail_deliverables() -> List[RetailDeliverable]:
    """Return comprehensive list of retail deliverables"""
    return [
        # ========== OMNICHANNEL CAMPAIGNS ==========
        RetailDeliverable(
            code="RT-OMNI-001",
            name="Omnichannel Campaign Strategy",
            category="Campaign Strategy",
            components=[
                "Customer journey mapping across channels",
                "Channel integration strategy",
                "Unified messaging framework",
                "Cross-channel promotion calendar",
                "Attribution model development",
                "Budget allocation by channel",
                "Performance KPI framework"
            ],
            base_hours=120,
            complexity_multiplier=1.5,
            omnichannel=True
        ),
        RetailDeliverable(
            code="RT-OMNI-002",
            name="Buy Online Pickup In-Store (BOPIS)",
            category="Omnichannel Operations",
            components=[
                "BOPIS workflow design",
                "Store operations training",
                "Technology integration setup",
                "Customer communication templates",
                "Pickup area design and signage",
                "Staff scheduling optimization",
                "Performance tracking dashboard"
            ],
            base_hours=160,
            complexity_multiplier=1.6,
            requires_tech_integration=True,
            requires_inventory_sync=True,
            omnichannel=True
        ),
        RetailDeliverable(
            code="RT-OMNI-003",
            name="Unified Inventory Management",
            category="Operations",
            components=[
                "Inventory sync system setup",
                "Real-time stock visibility",
                "Channel allocation rules",
                "Safety stock optimization",
                "Cross-channel fulfillment logic",
                "Return processing workflows"
            ],
            base_hours=200,
            complexity_multiplier=1.8,
            requires_tech_integration=True,
            requires_inventory_sync=True,
            omnichannel=True
        ),
        RetailDeliverable(
            code="RT-OMNI-004",
            name="Mobile App Launch Campaign",
            category="Digital Marketing",
            components=[
                "App launch strategy",
                "App store optimization (ASO)",
                "Download incentive program",
                "Push notification strategy",
                "In-app exclusive offers",
                "Mobile-first content creation",
                "App engagement analytics"
            ],
            base_hours=140,
            complexity_multiplier=1.4,
            requires_tech_integration=True,
            omnichannel=True
        ),
        
        # ========== SEASONAL PROMOTIONS ==========
        RetailDeliverable(
            code="RT-SEAS-001",
            name="Black Friday/Cyber Monday Campaign",
            category="Seasonal Campaigns",
            components=[
                "Early bird strategy development",
                "Doorbuster deal selection",
                "Email marketing sequences",
                "Social media countdown campaigns",
                "Website capacity planning",
                "Inventory forecasting",
                "Flash sale coordination",
                "Post-event analysis"
            ],
            base_hours=180,
            complexity_multiplier=1.7,
            seasonal=True,
            requires_inventory_sync=True
        ),
        RetailDeliverable(
            code="RT-SEAS-002",
            name="Holiday Shopping Campaign",
            category="Seasonal Campaigns",
            components=[
                "Holiday theme development",
                "Gift guide creation",
                "Shipping deadline communications",
                "Gift wrapping services setup",
                "Extended hours planning",
                "Holiday email series",
                "Social media advent calendar",
                "Return policy optimization"
            ],
            base_hours=220,
            complexity_multiplier=1.8,
            seasonal=True,
            omnichannel=True
        ),
        RetailDeliverable(
            code="RT-SEAS-003",
            name="Back-to-School Promotion",
            category="Seasonal Campaigns",
            components=[
                "Student segment targeting",
                "School supply bundles",
                "Teacher discount program",
                "Campus ambassador program",
                "Parent-focused messaging",
                "Social media challenges",
                "Influencer partnerships"
            ],
            base_hours=140,
            complexity_multiplier=1.4,
            seasonal=True
        ),
        RetailDeliverable(
            code="RT-SEAS-004",
            name="End-of-Season Clearance",
            category="Inventory Management",
            components=[
                "Markdown strategy",
                "Clearance merchandising",
                "Email blast campaigns",
                "Social media promotion",
                "In-store signage",
                "Online clearance section",
                "Inventory liquidation planning"
            ],
            base_hours=80,
            complexity_multiplier=1.2,
            seasonal=True,
            requires_inventory_sync=True
        ),
        
        # ========== LOYALTY PROGRAMS ==========
        RetailDeliverable(
            code="RT-LOYAL-001",
            name="Loyalty Program Launch",
            category="Customer Retention",
            components=[
                "Program structure design",
                "Tier and benefits framework",
                "Points earning rules",
                "Redemption catalog setup",
                "Technology platform selection",
                "Staff training program",
                "Launch campaign development",
                "Member acquisition strategy"
            ],
            base_hours=240,
            complexity_multiplier=1.8,
            requires_tech_integration=True
        ),
        RetailDeliverable(
            code="RT-LOYAL-002",
            name="VIP Customer Program",
            category="Customer Retention",
            components=[
                "VIP tier criteria definition",
                "Exclusive benefits package",
                "Personal shopper services",
                "Early access campaigns",
                "VIP event planning",
                "Concierge service setup",
                "Recognition and rewards system"
            ],
            base_hours=160,
            complexity_multiplier=1.6
        ),
        RetailDeliverable(
            code="RT-LOYAL-003",
            name="Referral Program Development",
            category="Customer Acquisition",
            components=[
                "Referral mechanics design",
                "Incentive structure",
                "Tracking system setup",
                "Marketing materials creation",
                "Social sharing tools",
                "Program rules and T&Cs",
                "Performance analytics"
            ],
            base_hours=100,
            complexity_multiplier=1.3,
            requires_tech_integration=True
        ),
        RetailDeliverable(
            code="RT-LOYAL-004",
            name="Birthday & Anniversary Programs",
            category="Customer Retention",
            components=[
                "Automated birthday campaigns",
                "Anniversary recognition system",
                "Personalized offer generation",
                "Multi-channel delivery",
                "Celebration messaging",
                "Special packaging options"
            ],
            base_hours=80,
            complexity_multiplier=1.2
        ),
        
        # ========== STORE OPENING CAMPAIGNS ==========
        RetailDeliverable(
            code="RT-STORE-001",
            name="Grand Opening Campaign",
            category="Store Launch",
            components=[
                "Pre-opening buzz campaign",
                "VIP preview event",
                "Grand opening day activities",
                "Local media outreach",
                "Influencer partnerships",
                "Opening week promotions",
                "Community partnerships",
                "Post-opening follow-up"
            ],
            base_hours=200,
            complexity_multiplier=1.7
        ),
        RetailDeliverable(
            code="RT-STORE-002",
            name="Store Remodel Launch",
            category="Store Marketing",
            components=[
                "Remodel announcement strategy",
                "Construction phase communications",
                "Soft reopening plan",
                "Reveal event planning",
                "New feature highlights",
                "Customer reengagement campaign"
            ],
            base_hours=120,
            complexity_multiplier=1.4
        ),
        RetailDeliverable(
            code="RT-STORE-003",
            name="Pop-Up Store Campaign",
            category="Experiential Retail",
            components=[
                "Pop-up concept development",
                "Location scouting and negotiation",
                "Temporary store design",
                "Limited edition product strategy",
                "Social media activation",
                "Event programming",
                "Performance measurement"
            ],
            base_hours=160,
            complexity_multiplier=1.5
        ),
        RetailDeliverable(
            code="RT-STORE-004",
            name="Local Store Marketing",
            category="Store Marketing",
            components=[
                "Local market analysis",
                "Community partnership development",
                "Local event sponsorships",
                "Neighborhood marketing tactics",
                "Local influencer engagement",
                "Geo-targeted digital ads"
            ],
            base_hours=100,
            complexity_multiplier=1.2
        ),
        
        # ========== E-COMMERCE OPTIMIZATION ==========
        RetailDeliverable(
            code="RT-ECOM-001",
            name="Conversion Rate Optimization",
            category="E-Commerce",
            components=[
                "Conversion funnel analysis",
                "A/B testing framework",
                "Cart abandonment recovery",
                "Checkout optimization",
                "Product page enhancement",
                "Search functionality improvement",
                "Performance tracking setup"
            ],
            base_hours=140,
            complexity_multiplier=1.5,
            requires_tech_integration=True
        ),
        RetailDeliverable(
            code="RT-ECOM-002",
            name="Personalization Engine Setup",
            category="E-Commerce",
            components=[
                "Customer segmentation strategy",
                "Product recommendation engine",
                "Personalized email flows",
                "Dynamic content rules",
                "Behavioral trigger setup",
                "Testing and optimization plan"
            ],
            base_hours=180,
            complexity_multiplier=1.6,
            requires_tech_integration=True
        ),
        RetailDeliverable(
            code="RT-ECOM-003",
            name="Mobile Commerce Optimization",
            category="E-Commerce",
            components=[
                "Mobile UX audit and redesign",
                "Mobile payment integration",
                "App-exclusive features",
                "Mobile-first checkout",
                "Push notification strategy",
                "Mobile performance optimization"
            ],
            base_hours=160,
            complexity_multiplier=1.5,
            requires_tech_integration=True
        ),
        RetailDeliverable(
            code="RT-ECOM-004",
            name="Product Launch Campaign",
            category="Product Marketing",
            components=[
                "Launch strategy development",
                "Pre-launch tease campaign",
                "Launch day activation",
                "Influencer seeding program",
                "User-generated content campaign",
                "Post-launch momentum plan"
            ],
            base_hours=140,
            complexity_multiplier=1.4
        ),
        
        # ========== POS & IN-STORE EXPERIENCES ==========
        RetailDeliverable(
            code="RT-POS-001",
            name="POS Material Package",
            category="In-Store Marketing",
            components=[
                "Window display design",
                "In-store signage system",
                "Shelf talkers and wobblers",
                "End cap displays",
                "Counter cards",
                "Digital screen content",
                "Installation guidelines"
            ],
            base_hours=100,
            complexity_multiplier=1.3
        ),
        RetailDeliverable(
            code="RT-POS-002",
            name="Interactive In-Store Experience",
            category="Experiential Retail",
            components=[
                "Experience concept design",
                "Technology integration",
                "Staff training program",
                "Customer journey mapping",
                "Data capture strategy",
                "ROI measurement framework"
            ],
            base_hours=180,
            complexity_multiplier=1.6,
            requires_tech_integration=True
        ),
        RetailDeliverable(
            code="RT-POS-003",
            name="Visual Merchandising Program",
            category="In-Store Marketing",
            components=[
                "Seasonal display calendar",
                "Planogram development",
                "Window display rotation",
                "Product storytelling displays",
                "Cross-merchandising strategy",
                "VM guidelines and training"
            ],
            base_hours=120,
            complexity_multiplier=1.3
        ),
        RetailDeliverable(
            code="RT-POS-004",
            name="Clienteling Program",
            category="Customer Experience",
            components=[
                "Clienteling app setup",
                "Customer profile system",
                "Personal shopping services",
                "Appointment booking system",
                "Follow-up communication templates",
                "Performance tracking metrics"
            ],
            base_hours=140,
            complexity_multiplier=1.5,
            requires_tech_integration=True
        ),
        
        # ========== INVENTORY PROMOTIONS ==========
        RetailDeliverable(
            code="RT-INV-001",
            name="Flash Sale Campaign",
            category="Promotional Marketing",
            components=[
                "Flash sale strategy",
                "Inventory selection",
                "Countdown timer setup",
                "Email blast preparation",
                "Social media teasers",
                "Website banner updates",
                "Post-sale analysis"
            ],
            base_hours=60,
            complexity_multiplier=1.2,
            requires_inventory_sync=True
        ),
        RetailDeliverable(
            code="RT-INV-002",
            name="Bundle & Save Promotions",
            category="Promotional Marketing",
            components=[
                "Bundle strategy development",
                "Product pairing analysis",
                "Pricing optimization",
                "Bundle merchandising",
                "Marketing creative development",
                "Performance tracking"
            ],
            base_hours=80,
            complexity_multiplier=1.2,
            requires_inventory_sync=True
        ),
        RetailDeliverable(
            code="RT-INV-003",
            name="Limited Edition Launch",
            category="Product Marketing",
            components=[
                "Exclusivity strategy",
                "Scarcity messaging",
                "Pre-order campaign",
                "Waitlist management",
                "Allocation strategy",
                "Collector marketing"
            ],
            base_hours=120,
            complexity_multiplier=1.4
        ),
        
        # ========== CUSTOMER ACQUISITION ==========
        RetailDeliverable(
            code="RT-ACQ-001",
            name="New Customer Welcome Series",
            category="Customer Acquisition",
            components=[
                "Welcome journey design",
                "First purchase incentive",
                "Product education content",
                "Cross-sell recommendations",
                "Feedback collection",
                "Retention hooks"
            ],
            base_hours=100,
            complexity_multiplier=1.3
        ),
        RetailDeliverable(
            code="RT-ACQ-002",
            name="Win-Back Campaign",
            category="Customer Retention",
            components=[
                "Lapsed customer segmentation",
                "Win-back offer strategy",
                "Multi-touch campaign design",
                "Personalization tactics",
                "Re-engagement tracking",
                "ROI analysis"
            ],
            base_hours=120,
            complexity_multiplier=1.3
        ),
        
        # ========== MARKETPLACE INTEGRATION ==========
        RetailDeliverable(
            code="RT-MRKT-001",
            name="Marketplace Launch Strategy",
            category="Channel Expansion",
            components=[
                "Marketplace selection analysis",
                "Product catalog optimization",
                "Competitive pricing strategy",
                "Listing optimization",
                "Review management system",
                "Fulfillment setup",
                "Performance monitoring"
            ],
            base_hours=160,
            complexity_multiplier=1.5,
            requires_tech_integration=True
        ),
        RetailDeliverable(
            code="RT-MRKT-002",
            name="Amazon Store Optimization",
            category="Marketplace Marketing",
            components=[
                "Amazon storefront design",
                "A+ content creation",
                "Product listing optimization",
                "Amazon advertising strategy",
                "Review generation program",
                "FBA setup and optimization"
            ],
            base_hours=140,
            complexity_multiplier=1.4,
            requires_tech_integration=True
        ),
        
        # ========== ANALYTICS & ATTRIBUTION ==========
        RetailDeliverable(
            code="RT-DATA-001",
            name="Cross-Channel Attribution Setup",
            category="Analytics",
            components=[
                "Attribution model selection",
                "Tracking implementation",
                "Data integration setup",
                "Dashboard creation",
                "Reporting framework",
                "Team training"
            ],
            base_hours=120,
            complexity_multiplier=1.5,
            requires_tech_integration=True
        ),
        RetailDeliverable(
            code="RT-DATA-002",
            name="Customer Data Platform (CDP) Setup",
            category="Marketing Technology",
            components=[
                "CDP platform selection",
                "Data source integration",
                "Customer profile unification",
                "Segmentation strategy",
                "Activation workflow setup",
                "Privacy compliance"
            ],
            base_hours=200,
            complexity_multiplier=1.8,
            requires_tech_integration=True
        )
    ]

# ================================================================================
# Timeline Calculation Functions
# ================================================================================

def calculate_retail_timeline(
    deliverables: List[RetailDeliverable],
    season: Optional[RetailSeason] = None,
    rush_delivery: bool = False
) -> Dict[str, Any]:
    """Calculate timeline for retail deliverables considering seasonal factors"""
    
    # Base calculation
    total_hours = sum(d.base_hours * d.complexity_multiplier for d in deliverables)
    
    # Seasonal adjustments
    if season:
        seasonal_factor = 1.0
        if season in [RetailSeason.BLACK_FRIDAY, RetailSeason.HOLIDAY]:
            seasonal_factor = 1.3  # More complexity during peak seasons
        elif season in [RetailSeason.BACK_TO_SCHOOL]:
            seasonal_factor = 1.2
        total_hours *= seasonal_factor
    
    # Rush delivery adjustment
    if rush_delivery:
        total_hours *= 0.8  # Compress timeline but may need more resources
    
    # Calculate weeks (assuming 40 hours per week per resource)
    weeks = total_hours / 40
    
    # Add buffer for retail-specific requirements
    if any(d.requires_tech_integration for d in deliverables):
        weeks += 2  # Tech integration buffer
    if any(d.requires_inventory_sync for d in deliverables):
        weeks += 1  # Inventory sync buffer
    
    return {
        "total_hours": round(total_hours),
        "estimated_weeks": round(weeks, 1),
        "recommended_team_size": max(2, min(8, len(deliverables) // 2)),
        "critical_path_items": [
            d.name for d in deliverables 
            if d.requires_tech_integration or d.requires_inventory_sync
        ]
    }

# ================================================================================
# Pricing Calculation Functions
# ================================================================================

def calculate_retail_pricing(
    deliverables: List[RetailDeliverable],
    business_size: str = "medium",  # small, medium, large, enterprise
    urgency: str = "standard"  # standard, urgent, critical
) -> Dict[str, Any]:
    """Calculate pricing for retail deliverables"""
    
    # Base hourly rates by business size
    hourly_rates = {
        "small": 150,
        "medium": 200,
        "large": 250,
        "enterprise": 300
    }
    
    # Urgency multipliers
    urgency_multipliers = {
        "standard": 1.0,
        "urgent": 1.25,
        "critical": 1.5
    }
    
    base_rate = hourly_rates.get(business_size, 200)
    urgency_mult = urgency_multipliers.get(urgency, 1.0)
    
    # Calculate deliverable costs
    deliverable_costs = []
    for d in deliverables:
        hours = d.base_hours * d.complexity_multiplier
        
        # Add premium for technical requirements
        tech_premium = 1.2 if d.requires_tech_integration else 1.0
        inventory_premium = 1.1 if d.requires_inventory_sync else 1.0
        
        cost = hours * base_rate * urgency_mult * tech_premium * inventory_premium
        
        deliverable_costs.append({
            "deliverable": d.name,
            "hours": round(hours),
            "cost": round(cost, -2),  # Round to nearest 100
            "requires_tech": d.requires_tech_integration,
            "requires_inventory": d.requires_inventory_sync
        })
    
    total_cost = sum(dc["cost"] for dc in deliverable_costs)
    
    # Volume discounts for larger projects
    if total_cost > 100000:
        discount = 0.1
    elif total_cost > 50000:
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
        "payment_terms": "Net 30" if business_size in ["large", "enterprise"] else "50% upfront, 50% on delivery",
        "includes_revisions": True,
        "revision_rounds": 2
    }

# ================================================================================
# Template Matching Functions
# ================================================================================

def match_retail_requirements(
    requirements_text: str,
    available_deliverables: List[RetailDeliverable]
) -> List[RetailDeliverable]:
    """Match requirements text to appropriate retail deliverables"""
    
    requirements_lower = requirements_text.lower()
    matched_deliverables = []
    
    # Keywords to deliverable mapping
    keyword_map = {
        "omnichannel": ["RT-OMNI-001", "RT-OMNI-002", "RT-OMNI-003"],
        "mobile app": ["RT-OMNI-004", "RT-ECOM-003"],
        "black friday": ["RT-SEAS-001"],
        "holiday": ["RT-SEAS-002"],
        "back to school": ["RT-SEAS-003"],
        "loyalty": ["RT-LOYAL-001", "RT-LOYAL-002"],
        "referral": ["RT-LOYAL-003"],
        "grand opening": ["RT-STORE-001"],
        "store opening": ["RT-STORE-001"],
        "pop-up": ["RT-STORE-003"],
        "conversion": ["RT-ECOM-001"],
        "personalization": ["RT-ECOM-002"],
        "flash sale": ["RT-INV-001"],
        "pos": ["RT-POS-001", "RT-POS-003"],
        "visual merchandising": ["RT-POS-003"],
        "amazon": ["RT-MRKT-002"],
        "marketplace": ["RT-MRKT-001"],
        "attribution": ["RT-DATA-001"],
        "cdp": ["RT-DATA-002"],
        "bopis": ["RT-OMNI-002"],
        "pickup": ["RT-OMNI-002"]
    }
    
    # Check for keyword matches
    for keyword, codes in keyword_map.items():
        if keyword in requirements_lower:
            for code in codes:
                deliverable = next((d for d in available_deliverables if d.code == code), None)
                if deliverable and deliverable not in matched_deliverables:
                    matched_deliverables.append(deliverable)
    
    # If no specific matches, suggest core retail deliverables
    if not matched_deliverables:
        core_codes = ["RT-OMNI-001", "RT-LOYAL-001", "RT-ECOM-001", "RT-POS-001"]
        for code in core_codes:
            deliverable = next((d for d in available_deliverables if d.code == code), None)
            if deliverable:
                matched_deliverables.append(deliverable)
    
    return matched_deliverables

# ================================================================================
# Main Retail Template Class
# ================================================================================

class RetailTemplate:
    """Main class for retail industry template management"""
    
    def __init__(self):
        self.deliverables = get_retail_deliverables()
        self.calendar = RETAIL_CALENDAR
        self.seasons = RetailSeason
        self.channels = RetailChannel
    
    def get_seasonal_campaigns(self, month: int) -> List[RetailDeliverable]:
        """Get relevant seasonal campaigns for a given month"""
        seasonal_deliverables = []
        
        for season_name, season_info in self.calendar.items():
            season_months = season_info.get("month", [])
            if not isinstance(season_months, list):
                season_months = [season_months]
            
            if month in season_months:
                # Find deliverables related to this season
                for d in self.deliverables:
                    if d.seasonal and season_name.lower() in d.name.lower():
                        seasonal_deliverables.append(d)
        
        return seasonal_deliverables
    
    def get_omnichannel_suite(self) -> List[RetailDeliverable]:
        """Get complete omnichannel deliverables package"""
        return [d for d in self.deliverables if d.omnichannel]
    
    def get_store_launch_package(self, store_type: str = "new") -> List[RetailDeliverable]:
        """Get deliverables for store launch (new, remodel, or pop-up)"""
        if store_type == "new":
            codes = ["RT-STORE-001", "RT-STORE-004", "RT-POS-001", "RT-POS-003"]
        elif store_type == "remodel":
            codes = ["RT-STORE-002", "RT-POS-001", "RT-POS-003"]
        elif store_type == "popup":
            codes = ["RT-STORE-003", "RT-INV-003"]
        else:
            codes = ["RT-STORE-001"]
        
        return [d for d in self.deliverables if d.code in codes]
    
    def get_ecommerce_optimization_package(self) -> List[RetailDeliverable]:
        """Get complete e-commerce optimization package"""
        codes = ["RT-ECOM-001", "RT-ECOM-002", "RT-ECOM-003", "RT-DATA-001"]
        return [d for d in self.deliverables if d.code in codes]
    
    def get_suggested_deliverables(self, rfp_keywords: List[str]) -> List[Dict[str, Any]]:
        """Match deliverables based on RFP keywords - API compatible method"""
        keywords_lower = [kw.lower() for kw in rfp_keywords]
        suggested = []
        
        # Keyword to deliverable mapping
        keyword_map = {
            "omnichannel": ["RT-OMNI-001", "RT-OMNI-002", "RT-OMNI-003"],
            "mobile": ["RT-OMNI-004", "RT-ECOM-003"],
            "app": ["RT-OMNI-004", "RT-ECOM-003"],
            "black friday": ["RT-SEAS-001"],
            "cyber monday": ["RT-SEAS-001"],
            "holiday": ["RT-SEAS-002"],
            "christmas": ["RT-SEAS-002"],
            "back to school": ["RT-SEAS-003"],
            "loyalty": ["RT-LOYAL-001", "RT-LOYAL-002"],
            "vip": ["RT-LOYAL-002"],
            "referral": ["RT-LOYAL-003"],
            "store opening": ["RT-STORE-001"],
            "grand opening": ["RT-STORE-001"],
            "remodel": ["RT-STORE-002"],
            "pop-up": ["RT-STORE-003"],
            "popup": ["RT-STORE-003"],
            "conversion": ["RT-ECOM-001"],
            "personalization": ["RT-ECOM-002"],
            "flash sale": ["RT-INV-001"],
            "sale": ["RT-INV-001", "RT-SEAS-004"],
            "pos": ["RT-POS-001"],
            "in-store": ["RT-POS-001", "RT-POS-002"],
            "merchandising": ["RT-POS-003"],
            "amazon": ["RT-MRKT-002"],
            "marketplace": ["RT-MRKT-001"],
            "attribution": ["RT-DATA-001"],
            "analytics": ["RT-DATA-001"],
            "cdp": ["RT-DATA-002"],
            "bopis": ["RT-OMNI-002"],
            "pickup": ["RT-OMNI-002"],
            "inventory": ["RT-OMNI-003", "RT-INV-001", "RT-INV-002"],
            "bundle": ["RT-INV-002"],
            "limited edition": ["RT-INV-003"],
            "exclusive": ["RT-INV-003"],
            "welcome": ["RT-ACQ-001"],
            "win back": ["RT-ACQ-002"],
            "retention": ["RT-LOYAL-001", "RT-ACQ-002"]
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
                            if formatted_deliverable not in suggested:
                                suggested.append(formatted_deliverable)
        
        # If no matches, return top retail essentials
        if not suggested:
            essential_codes = ["RT-OMNI-001", "RT-LOYAL-001", "RT-ECOM-001", "RT-SEAS-002"]
            for code in essential_codes:
                deliverable = next((d for d in self.deliverables if d.code == code), None)
                if deliverable:
                    suggested.append({
                        "code": deliverable.code,
                        "name": deliverable.name,
                        "category": deliverable.category,
                        "base_hours": deliverable.base_hours,
                        "components": deliverable.components,
                        "match_reason": "Core retail deliverable"
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
                          rush_delivery: bool = False) -> Dict[str, Any]:
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
        timeline_info = calculate_retail_timeline(
            selected_deliverables,
            rush_delivery=rush_delivery
        )
        
        # Format for API
        phases = []
        current_date = start_date
        
        for deliverable in selected_deliverables:
            # Calculate duration for this deliverable
            hours = deliverable.base_hours * deliverable.complexity_multiplier
            weeks = hours / 40
            if rush_delivery:
                weeks *= 0.8
            
            end_date = current_date + timedelta(weeks=weeks)
            
            phases.append({
                "deliverable": deliverable.name,
                "start_date": current_date.isoformat(),
                "end_date": end_date.isoformat(),
                "duration_weeks": round(weeks, 1),
                "requires_tech": deliverable.requires_tech_integration,
                "requires_inventory": deliverable.requires_inventory_sync
            })
            
            # Next phase starts after this one
            current_date = end_date
        
        return {
            "phases": phases,
            "total_weeks": timeline_info["estimated_weeks"],
            "total_hours": timeline_info["total_hours"],
            "team_size": timeline_info["recommended_team_size"],
            "critical_path": timeline_info.get("critical_path_items", [])
        }
    
    def calculate_pricing(self, deliverable_codes: List[str], base_rate: float = 200,
                         business_size: str = "medium") -> Dict[str, Any]:
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
        pricing_info = calculate_retail_pricing(
            selected_deliverables,
            business_size=business_size,
            urgency="standard"
        )
        
        return pricing_info
    
    def suggest_deliverables(
        self,
        business_type: str,
        goals: List[str],
        budget_range: Optional[str] = None,
        timeline_weeks: Optional[int] = None
    ) -> Dict[str, Any]:
        """Suggest deliverables based on business needs"""
        
        suggestions = []
        
        # Map goals to deliverable categories
        goal_mapping = {
            "increase sales": ["RT-SEAS-001", "RT-INV-001", "RT-ECOM-001"],
            "customer retention": ["RT-LOYAL-001", "RT-LOYAL-002", "RT-ACQ-002"],
            "new customers": ["RT-ACQ-001", "RT-LOYAL-003", "RT-STORE-001"],
            "digital growth": ["RT-ECOM-001", "RT-ECOM-002", "RT-OMNI-004"],
            "store traffic": ["RT-STORE-004", "RT-POS-002", "RT-OMNI-002"],
            "brand awareness": ["RT-STORE-001", "RT-STORE-003", "RT-SEAS-002"]
        }
        
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
            timeline = calculate_retail_timeline(suggestions)
            
            # Determine business size from budget
            if budget_range:
                if "50k" in budget_range or "small" in budget_range.lower():
                    business_size = "small"
                elif "100k" in budget_range or "medium" in budget_range.lower():
                    business_size = "medium"
                elif "250k" in budget_range or "large" in budget_range.lower():
                    business_size = "large"
                else:
                    business_size = "enterprise"
            else:
                business_size = "medium"
            
            pricing = calculate_retail_pricing(suggestions, business_size)
            
            # Filter by timeline if specified
            if timeline_weeks and timeline["estimated_weeks"] > timeline_weeks:
                # Prioritize most important deliverables
                suggestions = suggestions[:max(2, len(suggestions) // 2)]
                timeline = calculate_retail_timeline(suggestions)
                pricing = calculate_retail_pricing(suggestions, business_size)
            
            return {
                "suggested_deliverables": [d.name for d in suggestions],
                "deliverable_details": [
                    {
                        "code": d.code,
                        "name": d.name,
                        "category": d.category,
                        "hours": d.base_hours,
                        "requires_tech": d.requires_tech_integration,
                        "omnichannel": d.omnichannel
                    }
                    for d in suggestions
                ],
                "timeline": timeline,
                "pricing": pricing,
                "business_type": business_type,
                "goals": goals
            }
        
        return {
            "suggested_deliverables": [],
            "message": "No specific deliverables matched your requirements. Please provide more details."
        }

# ================================================================================
# Export Functions for API Integration
# ================================================================================

def get_retail_template_for_api(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """API endpoint function to get retail template based on requirements"""
    
    template = RetailTemplate()
    
    # Extract parameters
    business_type = requirements.get("business_type", "retail")
    goals = requirements.get("goals", [])
    budget_range = requirements.get("budget_range")
    timeline_weeks = requirements.get("timeline_weeks")
    season = requirements.get("season")
    
    # Get suggestions
    result = template.suggest_deliverables(
        business_type=business_type,
        goals=goals,
        budget_range=budget_range,
        timeline_weeks=timeline_weeks
    )
    
    # Add seasonal considerations if applicable
    if season:
        current_month = datetime.now().month
        seasonal_campaigns = template.get_seasonal_campaigns(current_month)
        if seasonal_campaigns:
            result["seasonal_opportunities"] = [d.name for d in seasonal_campaigns]
    
    return result

def get_retail_deliverable_catalog() -> List[Dict[str, Any]]:
    """Get full catalog of retail deliverables for API"""
    deliverables = get_retail_deliverables()
    return [
        {
            "code": d.code,
            "name": d.name,
            "category": d.category,
            "base_hours": d.base_hours,
            "components": d.components,
            "requires_tech": d.requires_tech_integration,
            "requires_inventory": d.requires_inventory_sync,
            "omnichannel": d.omnichannel,
            "seasonal": d.seasonal
        }
        for d in deliverables
    ]