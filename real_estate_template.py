"""
Real Estate Industry Template System
=====================================
Specialized deliverables, timelines, and pricing for real estate developers and property managers.

This module provides:
- Property launch campaigns (residential, commercial, mixed-use)
- Virtual tours and 3D visualizations
- Neighborhood lifestyle content and area guides
- Open house and broker event management
- Investment materials and financial analysis tools
- Tenant/buyer personas and journey mapping
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

# ================================================================================
# Real Estate Constants
# ================================================================================

class PropertyType(str, Enum):
    """Types of real estate properties"""
    LUXURY_RESIDENTIAL = "Luxury Residential"
    COMMERCIAL_OFFICE = "Commercial Office"
    RETAIL = "Retail Space"
    INDUSTRIAL = "Industrial"
    MULTI_FAMILY = "Multi-Family"
    MIXED_USE = "Mixed-Use Development"
    MASTER_PLANNED = "Master-Planned Community"
    HOSPITALITY = "Hospitality"
    MEDICAL = "Medical Office"
    STUDENT_HOUSING = "Student Housing"

class ProjectPhase(str, Enum):
    """Real estate project phases"""
    PRE_CONSTRUCTION = "Pre-Construction"
    CONSTRUCTION = "Construction Phase"
    SALES_LAUNCH = "Sales Launch"
    LEASE_UP = "Lease-Up"
    STABILIZATION = "Stabilization"
    REPOSITIONING = "Repositioning"

class MarketingChannel(str, Enum):
    """Real estate marketing channels"""
    MLS = "MLS Syndication"
    PROPERTY_PORTALS = "Property Portals"
    BROKER_NETWORK = "Broker Co-Marketing"
    PRINT_ADVERTISING = "Print Media"
    DIGITAL = "Digital Marketing"
    SIGNAGE = "Signage & Environmental"
    EVENTS = "Events & Activations"

# Real Estate Development Timeline Standards
DEVELOPMENT_PHASES = {
    "Pre-Construction": {
        "duration_months": [12, 18],
        "key_activities": ["Concept development", "Permits", "Pre-sales", "Financing"]
    },
    "Construction": {
        "duration_months": [12, 36],
        "key_activities": ["Monthly updates", "Progress photography", "Broker tours"]
    },
    "Sales Launch": {
        "duration_weeks": [6, 8],
        "key_activities": ["Media blitz", "Broker events", "Model home opening"]
    },
    "Lease-Up": {
        "duration_months": [3, 6],
        "key_activities": ["Tenant acquisition", "Community building", "Grand opening"]
    }
}

# ================================================================================
# Real Estate Deliverables
# ================================================================================

@dataclass
class RealEstateDeliverable:
    """Real estate-specific deliverable with property market attributes"""
    code: str
    name: str
    category: str
    components: List[str]
    base_hours: float
    luxury_multiplier: float = 1.0  # Additional for luxury properties
    commercial_multiplier: float = 1.0  # Additional for commercial complexity
    revision_rounds: int = 2
    requires_site_access: bool = False
    requires_permits: bool = False
    property_types: List[str] = field(default_factory=list)
    
def get_real_estate_deliverables() -> List[RealEstateDeliverable]:
    """Return comprehensive list of real estate deliverables"""
    return [
        # ========== PROPERTY LAUNCH CAMPAIGNS ==========
        RealEstateDeliverable(
            code="RE-LAUNCH-001",
            name="Residential Property Launch Campaign",
            category="Launch Campaigns",
            components=[
                "Market positioning strategy",
                "Brand identity and naming",
                "Marketing collateral suite",
                "Digital presence setup",
                "Sales center design",
                "Launch event planning",
                "Broker outreach program",
                "Initial advertising campaign"
            ],
            base_hours=280,
            luxury_multiplier=1.8,
            property_types=["residential", "condo", "luxury"]
        ),
        RealEstateDeliverable(
            code="RE-LAUNCH-002",
            name="Commercial Property Launch Campaign",
            category="Launch Campaigns",
            components=[
                "Market analysis and positioning",
                "Tenant mix strategy",
                "Broker presentation materials",
                "Property website and portal listings",
                "Marketing suite design",
                "Leasing collateral package",
                "Industry networking events",
                "Trade publication advertising"
            ],
            base_hours=240,
            commercial_multiplier=1.3,
            property_types=["office", "retail", "industrial"]
        ),
        RealEstateDeliverable(
            code="RE-LAUNCH-003",
            name="Mixed-Use Development Campaign",
            category="Launch Campaigns",
            components=[
                "Integrated positioning strategy",
                "Multi-audience messaging",
                "Retail tenant recruitment materials",
                "Residential sales materials",
                "Office leasing package",
                "Community activation plan",
                "Placemaking initiatives",
                "Cross-promotional campaigns"
            ],
            base_hours=360,
            luxury_multiplier=1.5,
            commercial_multiplier=1.3,
            property_types=["mixed-use"]
        ),
        RealEstateDeliverable(
            code="RE-LAUNCH-004",
            name="Master-Planned Community Launch",
            category="Launch Campaigns",
            components=[
                "Community visioning and branding",
                "Master marketing plan",
                "Welcome center development",
                "Model home program",
                "Builder co-op marketing",
                "Lifestyle programming",
                "Community website and app",
                "Long-term marketing roadmap"
            ],
            base_hours=480,
            luxury_multiplier=1.6,
            property_types=["master-planned"]
        ),
        
        # ========== VIRTUAL TOURS & VISUALIZATIONS ==========
        RealEstateDeliverable(
            code="RE-VISUAL-001",
            name="Matterport Virtual Tour Production",
            category="Virtual Tours",
            components=[
                "3D scanning coordination",
                "Virtual staging integration",
                "Interactive hotspot development",
                "Floor plan generation",
                "VR experience optimization",
                "Multi-platform distribution",
                "Analytics setup"
            ],
            base_hours=40,
            requires_site_access=True,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-VISUAL-002",
            name="Drone Photography & Videography",
            category="Visual Content",
            components=[
                "FAA permit coordination",
                "Flight planning",
                "Aerial photography",
                "Cinematic video production",
                "Progress documentation",
                "Neighborhood context shots",
                "Post-production editing"
            ],
            base_hours=60,
            requires_permits=True,
            requires_site_access=True,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-VISUAL-003",
            name="3D Renderings & Animations",
            category="Visual Content",
            components=[
                "Architectural visualization",
                "Interior renderings",
                "Exterior perspectives",
                "Amenity visualizations",
                "Lifestyle vignettes",
                "Flythrough animations",
                "Virtual reality experiences"
            ],
            base_hours=160,
            luxury_multiplier=1.4,
            property_types=["pre-construction", "luxury"]
        ),
        RealEstateDeliverable(
            code="RE-VISUAL-004",
            name="Property Photography Package",
            category="Visual Content",
            components=[
                "Professional photography scheduling",
                "Twilight photography",
                "Interior detail shots",
                "Amenity photography",
                "Lifestyle photography",
                "Virtual staging",
                "Photo retouching and editing",
                "Multiple format delivery"
            ],
            base_hours=80,
            luxury_multiplier=1.5,
            requires_site_access=True,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-VISUAL-005",
            name="Interactive Floor Plans & Site Maps",
            category="Visual Content",
            components=[
                "2D/3D floor plan creation",
                "Interactive unit selector",
                "Availability integration",
                "Amenity mapping",
                "Neighborhood points of interest",
                "Sun/shade studies",
                "View corridor analysis"
            ],
            base_hours=100,
            property_types=["residential", "commercial"]
        ),
        
        # ========== NEIGHBORHOOD & LIFESTYLE CONTENT ==========
        RealEstateDeliverable(
            code="RE-NEIGH-001",
            name="Neighborhood Lifestyle Guide",
            category="Content Marketing",
            components=[
                "Area demographic research",
                "Local amenity curation",
                "Restaurant and retail guides",
                "School and education info",
                "Transportation analysis",
                "Cultural attractions mapping",
                "Digital and print formats",
                "Seasonal updates"
            ],
            base_hours=120,
            property_types=["residential", "mixed-use"]
        ),
        RealEstateDeliverable(
            code="RE-NEIGH-002",
            name="Amenity Highlight Campaign",
            category="Content Marketing",
            components=[
                "Amenity photography and video",
                "Feature benefit messaging",
                "Lifestyle storytelling",
                "User testimonials",
                "Virtual amenity tours",
                "Reservation system integration",
                "Programming calendar"
            ],
            base_hours=100,
            luxury_multiplier=1.3,
            property_types=["luxury", "multi-family"]
        ),
        RealEstateDeliverable(
            code="RE-NEIGH-003",
            name="Community Lifestyle Blog",
            category="Content Marketing",
            components=[
                "Editorial calendar development",
                "Local expert interviews",
                "Resident spotlights",
                "Event coverage",
                "Market updates",
                "Seasonal content",
                "SEO optimization",
                "Email newsletter integration"
            ],
            base_hours=160,
            property_types=["master-planned", "multi-family"]
        ),
        RealEstateDeliverable(
            code="RE-NEIGH-004",
            name="Walk Score & Transit Analysis",
            category="Content Marketing",
            components=[
                "Walkability assessment",
                "Transit accessibility mapping",
                "Commute time analysis",
                "Bike-ability scoring",
                "Car-free living guide",
                "Neighborhood comparison tool",
                "Interactive transportation map"
            ],
            base_hours=60,
            property_types=["urban", "mixed-use"]
        ),
        
        # ========== OPEN HOUSE & EVENTS ==========
        RealEstateDeliverable(
            code="RE-EVENT-001",
            name="Broker Open House Program",
            category="Event Management",
            components=[
                "Broker invitation strategy",
                "Event scheduling and logistics",
                "Property presentation prep",
                "Marketing materials package",
                "Catering coordination",
                "Gift bag assembly",
                "Follow-up campaign",
                "Broker feedback system"
            ],
            base_hours=80,
            requires_site_access=True,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-EVENT-002",
            name="Public Grand Opening Event",
            category="Event Management",
            components=[
                "Event concept and theming",
                "Marketing and promotion",
                "Registration system",
                "Venue setup and staging",
                "Entertainment booking",
                "Food and beverage planning",
                "Model home tours",
                "Sales team coordination",
                "Media coverage"
            ],
            base_hours=140,
            luxury_multiplier=1.5,
            requires_site_access=True,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-EVENT-003",
            name="VIP Preview Event",
            category="Event Management",
            components=[
                "VIP list curation",
                "Exclusive invitation design",
                "Private showing coordination",
                "Luxury catering service",
                "Valet and security",
                "Entertainment and ambiance",
                "Exclusive offers preparation",
                "White-glove follow-up"
            ],
            base_hours=120,
            luxury_multiplier=2.0,
            requires_site_access=True,
            property_types=["luxury"]
        ),
        RealEstateDeliverable(
            code="RE-EVENT-004",
            name="Construction Milestone Celebration",
            category="Event Management",
            components=[
                "Topping off ceremony planning",
                "Groundbreaking event coordination",
                "Stakeholder invitation management",
                "Media relations",
                "Photography and videography",
                "Commemorative materials",
                "Safety coordination",
                "Post-event publicity"
            ],
            base_hours=100,
            requires_site_access=True,
            requires_permits=True,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-EVENT-005",
            name="Virtual Property Showcase",
            category="Event Management",
            components=[
                "Virtual event platform setup",
                "Live streaming coordination",
                "Interactive Q&A sessions",
                "Virtual tour integration",
                "Digital registration system",
                "Follow-up automation",
                "Recording and distribution",
                "Analytics tracking"
            ],
            base_hours=80,
            property_types=["all"]
        ),
        
        # ========== INVESTMENT MATERIALS ==========
        RealEstateDeliverable(
            code="RE-INVEST-001",
            name="Investment Property ROI Calculator",
            category="Investment Materials",
            components=[
                "Financial model development",
                "Interactive calculator design",
                "Market data integration",
                "Sensitivity analysis tools",
                "Comparative analysis features",
                "Tax benefit calculations",
                "Financing scenarios",
                "Professional reporting"
            ],
            base_hours=120,
            commercial_multiplier=1.3,
            property_types=["commercial", "multi-family"]
        ),
        RealEstateDeliverable(
            code="RE-INVEST-002",
            name="Market Analysis Report",
            category="Investment Materials",
            components=[
                "Market research and data collection",
                "Competitive analysis",
                "Demographic studies",
                "Economic indicators analysis",
                "Supply and demand metrics",
                "Pricing recommendations",
                "Investment highlights",
                "Professional presentation design"
            ],
            base_hours=160,
            commercial_multiplier=1.2,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-INVEST-003",
            name="Property Pro Forma Package",
            category="Investment Materials",
            components=[
                "Revenue projections",
                "Operating expense analysis",
                "Capital expenditure planning",
                "Cash flow modeling",
                "IRR and NPV calculations",
                "Debt service coverage",
                "Exit strategy scenarios",
                "Executive summary"
            ],
            base_hours=140,
            commercial_multiplier=1.4,
            property_types=["commercial", "multi-family"]
        ),
        RealEstateDeliverable(
            code="RE-INVEST-004",
            name="Offering Memorandum",
            category="Investment Materials",
            components=[
                "Executive summary writing",
                "Property overview compilation",
                "Market analysis integration",
                "Financial summary preparation",
                "Architectural plans formatting",
                "Photography and visuals",
                "Legal disclaimer coordination",
                "Professional design and binding"
            ],
            base_hours=200,
            luxury_multiplier=1.3,
            commercial_multiplier=1.3,
            property_types=["commercial", "luxury"]
        ),
        RealEstateDeliverable(
            code="RE-INVEST-005",
            name="Investor Presentation Deck",
            category="Investment Materials",
            components=[
                "Investment thesis development",
                "Market opportunity slides",
                "Property highlights",
                "Financial projections",
                "Development timeline",
                "Team credentials",
                "Risk mitigation strategies",
                "Call to action design"
            ],
            base_hours=80,
            property_types=["all"]
        ),
        
        # ========== BUYER/TENANT PERSONAS ==========
        RealEstateDeliverable(
            code="RE-PERSONA-001",
            name="Buyer Persona Development",
            category="Strategy & Research",
            components=[
                "Market research and surveys",
                "Demographic analysis",
                "Psychographic profiling",
                "Lifestyle mapping",
                "Purchase journey mapping",
                "Pain point identification",
                "Messaging matrix creation",
                "Visual persona cards"
            ],
            base_hours=100,
            property_types=["residential", "luxury"]
        ),
        RealEstateDeliverable(
            code="RE-PERSONA-002",
            name="Tenant Profile Analysis",
            category="Strategy & Research",
            components=[
                "Industry sector analysis",
                "Space requirement studies",
                "Location preference mapping",
                "Amenity prioritization research",
                "Budget range analysis",
                "Decision-maker identification",
                "Tenant mix optimization",
                "Retention strategy development"
            ],
            base_hours=120,
            commercial_multiplier=1.2,
            property_types=["commercial", "retail"]
        ),
        RealEstateDeliverable(
            code="RE-PERSONA-003",
            name="Customer Journey Mapping",
            category="Strategy & Research",
            components=[
                "Awareness stage mapping",
                "Consideration touchpoints",
                "Decision factors analysis",
                "Purchase process optimization",
                "Post-purchase experience",
                "Referral program design",
                "Digital journey tracking",
                "Conversion optimization"
            ],
            base_hours=140,
            property_types=["all"]
        ),
        
        # ========== MLS & PORTAL OPTIMIZATION ==========
        RealEstateDeliverable(
            code="RE-MLS-001",
            name="MLS Listing Optimization",
            category="Digital Marketing",
            components=[
                "MLS copywriting and optimization",
                "Photography selection and ordering",
                "Feature highlighting",
                "Keyword optimization",
                "Syndication setup",
                "Performance tracking",
                "A/B testing implementation",
                "Regular updates and refreshing"
            ],
            base_hours=40,
            property_types=["residential"]
        ),
        RealEstateDeliverable(
            code="RE-MLS-002",
            name="Property Portal Campaign",
            category="Digital Marketing",
            components=[
                "Multi-portal strategy",
                "Premium placement negotiation",
                "Listing optimization",
                "Virtual tour integration",
                "Lead capture setup",
                "Response automation",
                "Performance analytics",
                "ROI reporting"
            ],
            base_hours=80,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-MLS-003",
            name="Broker Co-Marketing Program",
            category="Partnership Marketing",
            components=[
                "Broker incentive structure",
                "Co-branded materials",
                "Broker portal development",
                "Training and certification",
                "Commission protection",
                "Performance tracking",
                "Recognition program",
                "Broker appreciation events"
            ],
            base_hours=160,
            property_types=["luxury", "commercial"]
        ),
        
        # ========== PRINT & SIGNAGE ==========
        RealEstateDeliverable(
            code="RE-PRINT-001",
            name="Luxury Print Advertising Campaign",
            category="Print Advertising",
            components=[
                "Publication selection strategy",
                "Creative concept development",
                "Professional copywriting",
                "High-end photography direction",
                "Media planning and buying",
                "WSJ/NYT placement coordination",
                "Luxury magazine placements",
                "Performance tracking"
            ],
            base_hours=120,
            luxury_multiplier=1.8,
            property_types=["luxury"]
        ),
        RealEstateDeliverable(
            code="RE-SIGN-001",
            name="Property Signage Package",
            category="Environmental Graphics",
            components=[
                "Signage strategy and placement",
                "Design and branding consistency",
                "Permit acquisition",
                "Fabrication coordination",
                "Installation management",
                "Directional signage system",
                "Construction fencing graphics",
                "Monument sign design"
            ],
            base_hours=100,
            requires_permits=True,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-SIGN-002",
            name="Sales Center Experience Design",
            category="Environmental Graphics",
            components=[
                "Sales center layout planning",
                "Interactive displays design",
                "Model and material boards",
                "Digital presentation systems",
                "VR/AR experience stations",
                "Wayfinding and graphics",
                "Hospitality area design",
                "Children's activity zone"
            ],
            base_hours=180,
            luxury_multiplier=1.5,
            requires_site_access=True,
            property_types=["residential", "luxury"]
        ),
        
        # ========== DIGITAL MARKETING ==========
        RealEstateDeliverable(
            code="RE-DIGITAL-001",
            name="Property Website Development",
            category="Digital Marketing",
            components=[
                "Website strategy and UX design",
                "Responsive development",
                "Virtual tour integration",
                "Floor plan selector",
                "Availability real-time updates",
                "Lead capture forms",
                "CRM integration",
                "Analytics implementation"
            ],
            base_hours=240,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-DIGITAL-002",
            name="Social Media Property Campaign",
            category="Digital Marketing",
            components=[
                "Platform strategy development",
                "Content calendar creation",
                "Photography and video content",
                "Community management",
                "Paid social campaigns",
                "Influencer partnerships",
                "User-generated content",
                "Performance reporting"
            ],
            base_hours=160,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-DIGITAL-003",
            name="Email Marketing Automation",
            category="Digital Marketing",
            components=[
                "Email strategy development",
                "Template design suite",
                "Automation workflow setup",
                "Lead nurturing sequences",
                "Broker communication system",
                "Event invitation campaigns",
                "Newsletter production",
                "Performance optimization"
            ],
            base_hours=100,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-DIGITAL-004",
            name="PPC & Retargeting Campaign",
            category="Digital Marketing",
            components=[
                "Keyword research and strategy",
                "Google Ads campaign setup",
                "Facebook/Instagram advertising",
                "Retargeting pixel implementation",
                "Landing page optimization",
                "Bid management",
                "A/B testing program",
                "ROI tracking and reporting"
            ],
            base_hours=120,
            property_types=["all"]
        ),
        
        # ========== CONSTRUCTION MARKETING ==========
        RealEstateDeliverable(
            code="RE-CONST-001",
            name="Construction Progress Documentation",
            category="Construction Marketing",
            components=[
                "Monthly progress photography",
                "Time-lapse video setup",
                "Drone progress flights",
                "Construction milestone updates",
                "Safety compliance documentation",
                "Investor update reports",
                "Social media content",
                "Email update campaigns"
            ],
            base_hours=80,
            requires_site_access=True,
            property_types=["all"]
        ),
        RealEstateDeliverable(
            code="RE-CONST-002",
            name="Pre-Construction Sales Program",
            category="Pre-Construction",
            components=[
                "Pre-sale strategy development",
                "Priority registration system",
                "Deposit structure planning",
                "Preview center setup",
                "Rendering and visualization package",
                "Pricing strategy",
                "Incentive programs",
                "Contract coordination"
            ],
            base_hours=200,
            luxury_multiplier=1.4,
            property_types=["residential", "luxury"]
        ),
        
        # ========== SUSTAINABILITY & ESG ==========
        RealEstateDeliverable(
            code="RE-SUSTAIN-001",
            name="Green Building Certification Campaign",
            category="Sustainability Marketing",
            components=[
                "LEED/ENERGY STAR messaging",
                "Sustainability feature highlights",
                "Cost savings calculator",
                "Environmental impact metrics",
                "Wellness amenity promotion",
                "Green lifestyle content",
                "Certification display materials",
                "Tenant education programs"
            ],
            base_hours=120,
            property_types=["all"]
        ),
        
        # ========== LEASING SUPPORT ==========
        RealEstateDeliverable(
            code="RE-LEASE-001",
            name="Leasing Office Support Package",
            category="Leasing Support",
            components=[
                "Leasing team training materials",
                "Objection handling guides",
                "Competitive analysis tools",
                "Tour route optimization",
                "Closing techniques training",
                "Follow-up templates",
                "Performance dashboards",
                "Incentive tracking systems"
            ],
            base_hours=100,
            property_types=["multi-family", "commercial"]
        ),
        RealEstateDeliverable(
            code="RE-LEASE-002",
            name="Tenant Retention Program",
            category="Leasing Support",
            components=[
                "Resident satisfaction surveys",
                "Retention strategy development",
                "Renewal incentive programs",
                "Community event planning",
                "Resident portal setup",
                "Maintenance request system",
                "Loyalty program design",
                "Exit interview process"
            ],
            base_hours=140,
            property_types=["multi-family", "commercial"]
        )
    ]

# ================================================================================
# Real Estate Template Class
# ================================================================================

class RealEstateTemplate:
    """Template system for real estate industry deliverables and pricing"""
    
    def __init__(self):
        self.name = "Real Estate"
        self.code = "RE"
        self.deliverables = get_real_estate_deliverables()
        
        # Timeline adjustments for real estate projects
        self.timeline_adjustments = {
            "pre_construction_months": [12, 18],
            "construction_months": [12, 36],
            "sales_launch_weeks": [6, 8],
            "lease_up_months": [3, 6],
            "milestone_phases": [
                {"name": "Planning & Approvals", "duration_pct": 0.15},
                {"name": "Pre-Development", "duration_pct": 0.20},
                {"name": "Active Development", "duration_pct": 0.40},
                {"name": "Marketing Launch", "duration_pct": 0.15},
                {"name": "Stabilization", "duration_pct": 0.10}
            ]
        }
        
        # Pricing adjustments specific to real estate
        self.pricing_adjustments = {
            "luxury_premium": 1.5,  # 50% premium for luxury properties
            "commercial_complexity": 1.3,  # 30% for commercial complexity
            "multi_phase_multiplier": 1.2,  # 20% per additional phase
            "rush_timeline": 1.4,  # 40% for accelerated timeline
            "seasonal_factors": {
                "spring": 1.1,  # Peak buying season
                "summer": 1.0,
                "fall": 0.95,
                "winter": 0.9
            }
        }
        
    def get_suggested_deliverables(self, keywords: List[str]) -> List[Dict]:
        """Suggest relevant deliverables based on keywords"""
        suggested = []
        keywords_lower = [k.lower() for k in keywords]
        
        # Extract property type from keywords if present
        property_type = None
        property_type_keywords = {
            "luxury": "luxury",
            "commercial": "commercial", 
            "office": "commercial",
            "retail": "commercial",
            "residential": "residential",
            "mixed-use": "mixed-use",
            "mixed use": "mixed-use",
            "multi-family": "multi-family",
            "multi family": "multi-family"
        }
        
        for keyword in keywords_lower:
            for key, ptype in property_type_keywords.items():
                if key in keyword:
                    property_type = ptype
                    break
        
        # Keyword mapping for real estate
        keyword_map = {
            "launch": ["RE-LAUNCH-001", "RE-LAUNCH-002", "RE-LAUNCH-003"],
            "virtual": ["RE-VISUAL-001", "RE-VISUAL-003", "RE-EVENT-005"],
            "drone": ["RE-VISUAL-002"],
            "matterport": ["RE-VISUAL-001"],
            "3d": ["RE-VISUAL-001", "RE-VISUAL-003"],
            "rendering": ["RE-VISUAL-003"],
            "photography": ["RE-VISUAL-002", "RE-VISUAL-004"],
            "neighborhood": ["RE-NEIGH-001", "RE-NEIGH-004"],
            "amenity": ["RE-NEIGH-002"],
            "lifestyle": ["RE-NEIGH-001", "RE-NEIGH-003"],
            "open house": ["RE-EVENT-001", "RE-EVENT-002"],
            "broker": ["RE-EVENT-001", "RE-MLS-003"],
            "vip": ["RE-EVENT-003"],
            "investment": ["RE-INVEST-001", "RE-INVEST-002", "RE-INVEST-003"],
            "roi": ["RE-INVEST-001"],
            "proforma": ["RE-INVEST-003"],
            "pro forma": ["RE-INVEST-003"],
            "offering": ["RE-INVEST-004"],
            "memorandum": ["RE-INVEST-004"],
            "persona": ["RE-PERSONA-001", "RE-PERSONA-002"],
            "journey": ["RE-PERSONA-003"],
            "mls": ["RE-MLS-001", "RE-MLS-002"],
            "portal": ["RE-MLS-002"],
            "zillow": ["RE-MLS-002"],
            "realtor": ["RE-MLS-002"],
            "print": ["RE-PRINT-001"],
            "wsj": ["RE-PRINT-001"],
            "signage": ["RE-SIGN-001"],
            "sales center": ["RE-SIGN-002"],
            "website": ["RE-DIGITAL-001"],
            "social": ["RE-DIGITAL-002"],
            "email": ["RE-DIGITAL-003"],
            "ppc": ["RE-DIGITAL-004"],
            "construction": ["RE-CONST-001", "RE-CONST-002"],
            "pre-construction": ["RE-CONST-002"],
            "green": ["RE-SUSTAIN-001"],
            "leed": ["RE-SUSTAIN-001"],
            "sustainability": ["RE-SUSTAIN-001"],
            "leasing": ["RE-LEASE-001", "RE-LEASE-002"],
            "retention": ["RE-LEASE-002"],
            "residential": ["RE-LAUNCH-001", "RE-VISUAL-004", "RE-NEIGH-001"],
            "commercial": ["RE-LAUNCH-002", "RE-INVEST-001", "RE-PERSONA-002"],
            "luxury": ["RE-LAUNCH-001", "RE-EVENT-003", "RE-PRINT-001"],
            "mixed-use": ["RE-LAUNCH-003"],
            "mixed use": ["RE-LAUNCH-003"],
            "master planned": ["RE-LAUNCH-004"],
            "master-planned": ["RE-LAUNCH-004"],
            "office": ["RE-LAUNCH-002"],
            "retail": ["RE-LAUNCH-002", "RE-PERSONA-002"],
            "industrial": ["RE-LAUNCH-002"],
            "multi-family": ["RE-INVEST-001", "RE-LEASE-001", "RE-LEASE-002"],
            "multi family": ["RE-INVEST-001", "RE-LEASE-001", "RE-LEASE-002"]
        }
        
        # Find matching deliverables
        matched_codes = set()
        for keyword in keywords_lower:
            for pattern, codes in keyword_map.items():
                if pattern in keyword:
                    matched_codes.update(codes)
        
        # Filter by property type if specified
        for deliverable in self.deliverables:
            # Check if deliverable matches property type
            if property_type and deliverable.property_types:
                if "all" not in deliverable.property_types:
                    property_type_lower = property_type.lower()
                    if not any(pt in property_type_lower for pt in deliverable.property_types):
                        continue
                        
            if deliverable.code in matched_codes:
                suggested.append({
                    "code": deliverable.code,
                    "name": deliverable.name,
                    "category": deliverable.category,
                    "components": deliverable.components,
                    "base_hours": deliverable.base_hours,
                    "luxury_multiplier": deliverable.luxury_multiplier,
                    "commercial_multiplier": deliverable.commercial_multiplier,
                    "revision_rounds": deliverable.revision_rounds,
                    "confidence": 0.9  # High confidence for keyword matches
                })
        
        # If few matches, add core real estate deliverables
        if len(suggested) < 5:
            core_codes = ["RE-LAUNCH-001", "RE-VISUAL-001", "RE-DIGITAL-001", "RE-EVENT-001", "RE-INVEST-002"]
            for deliverable in self.deliverables:
                if deliverable.code in core_codes and deliverable.code not in matched_codes:
                    suggested.append({
                        "code": deliverable.code,
                        "name": deliverable.name,
                        "category": deliverable.category,
                        "components": deliverable.components,
                        "base_hours": deliverable.base_hours,
                        "luxury_multiplier": deliverable.luxury_multiplier,
                        "commercial_multiplier": deliverable.commercial_multiplier,
                        "revision_rounds": deliverable.revision_rounds,
                        "confidence": 0.6  # Medium confidence for core suggestions
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
                        "components": deliverable.components,
                        "base_hours": deliverable.base_hours,
                        "luxury_multiplier": deliverable.luxury_multiplier,
                        "commercial_multiplier": deliverable.commercial_multiplier,
                        "revision_rounds": deliverable.revision_rounds,
                        "confidence": 0.5  # Medium confidence for filler deliverables
                    })
                    added_codes.add(deliverable.code)
                    if len(suggested) >= 45:  # Cap at 45 deliverables
                        break
        
        # Sort by confidence and category
        suggested.sort(key=lambda x: (x["confidence"], x["category"]), reverse=True)
        return suggested
        
    def calculate_timeline(self, deliverable_codes: List[str], start_date: datetime, 
                          project_phase: str = "sales_launch") -> Dict[str, Any]:
        """Calculate real estate project timeline with phase considerations"""
        timeline = {
            "phases": [],
            "milestones": [],
            "total_duration_weeks": 0,
            "critical_path": [],
            "market_considerations": []
        }
        
        selected_deliverables = [d for d in self.deliverables if d.code in deliverable_codes]
        if not selected_deliverables:
            # Add duration_weeks alias for compatibility
            timeline["duration_weeks"] = timeline.get("total_duration_weeks", 0)
            return timeline
            
        # Determine timeline based on project phase
        if project_phase == "pre_construction":
            total_weeks = 52  # 12 months minimum
        elif project_phase == "construction":
            total_weeks = 78  # 18 months typical
        elif project_phase == "sales_launch":
            total_weeks = 8   # 6-8 weeks intensive
        elif project_phase == "lease_up":
            total_weeks = 16  # 3-4 months
        else:
            total_weeks = 12  # Default 3 months
            
        timeline["total_duration_weeks"] = total_weeks
        
        # Generate phases based on milestone template
        current_date = start_date
        for phase in self.timeline_adjustments["milestone_phases"]:
            phase_duration = int(total_weeks * phase["duration_pct"])
            end_date = current_date + timedelta(weeks=phase_duration)
            
            timeline["phases"].append({
                "name": phase["name"],
                "start": current_date.isoformat(),
                "end": end_date.isoformat(),
                "duration_weeks": phase_duration,
                "deliverables": []  # Would be populated with actual deliverable assignments
            })
            
            current_date = end_date
            
        # Add real estate specific milestones
        timeline["milestones"] = [
            {"week": 1, "milestone": "Project Kickoff & Site Analysis"},
            {"week": int(total_weeks * 0.1), "milestone": "Marketing Strategy Approval"},
            {"week": int(total_weeks * 0.2), "milestone": "Brand Identity Finalized"},
            {"week": int(total_weeks * 0.3), "milestone": "Sales Center/Model Ready"},
            {"week": int(total_weeks * 0.5), "milestone": "Public Launch Preparation"},
            {"week": int(total_weeks * 0.7), "milestone": "Broker Preview Events"},
            {"week": int(total_weeks * 0.9), "milestone": "Grand Opening Event"},
            {"week": total_weeks, "milestone": "Campaign Assessment"}
        ]
        
        # Market timing considerations
        launch_month = (start_date + timedelta(weeks=total_weeks)).month
        
        if launch_month in [3, 4, 5]:  # Spring market
            timeline["market_considerations"].append({
                "factor": "Spring Buying Season",
                "impact": "Optimal timing - highest buyer activity",
                "recommendation": "Maximize marketing spend and events"
            })
        elif launch_month in [9, 10, 11]:  # Fall market
            timeline["market_considerations"].append({
                "factor": "Fall Market",
                "impact": "Good timing - serious buyers before holidays",
                "recommendation": "Focus on move-in ready messaging"
            })
        elif launch_month in [12, 1, 2]:  # Winter market
            timeline["market_considerations"].append({
                "factor": "Winter Season",
                "impact": "Slower market - less competition",
                "recommendation": "Offer incentives and interior focus"
            })
        else:  # Summer
            timeline["market_considerations"].append({
                "factor": "Summer Market",
                "impact": "Family-focused timing",
                "recommendation": "Emphasize lifestyle and amenities"
            })
        
        # Add duration_weeks alias for compatibility
        timeline["duration_weeks"] = timeline.get("total_duration_weeks", 0)
        return timeline
        
    def calculate_pricing(self, deliverable_codes: List[str], base_rate: float = 150,
                         property_type: str = None, num_phases: int = 1) -> Dict[str, Any]:
        """Calculate real estate project pricing with adjustments"""
        pricing = {
            "deliverables": [],
            "subtotal": 0,
            "adjustments": [],
            "total": 0
        }
        
        selected_deliverables = [d for d in self.deliverables if d.code in deliverable_codes]
        
        for deliverable in selected_deliverables:
            # Calculate base cost
            base_cost = deliverable.base_hours * base_rate
            
            # Apply property type multipliers
            adjusted_cost = base_cost
            
            if property_type:
                if "luxury" in property_type.lower():
                    adjusted_cost *= deliverable.luxury_multiplier
                elif "commercial" in property_type.lower():
                    adjusted_cost *= deliverable.commercial_multiplier
            
            pricing["deliverables"].append({
                "code": deliverable.code,
                "name": deliverable.name,
                "base_hours": deliverable.base_hours,
                "base_cost": base_cost,
                "property_type_multiplier": adjusted_cost / base_cost,
                "adjusted_cost": adjusted_cost
            })
            
            pricing["subtotal"] += adjusted_cost
            
        # Apply additional adjustments
        adjustments_total = 0
        
        # Multi-phase project adjustment
        if num_phases > 1:
            phase_adjustment = pricing["subtotal"] * (self.pricing_adjustments["multi_phase_multiplier"] - 1) * (num_phases - 1)
            pricing["adjustments"].append({
                "type": f"Multi-Phase Project ({num_phases} phases)",
                "amount": phase_adjustment
            })
            adjustments_total += phase_adjustment
            
        # Site access and permit requirements
        if any(d.requires_site_access for d in selected_deliverables):
            site_adjustment = pricing["subtotal"] * 0.1  # 10% for site coordination
            pricing["adjustments"].append({
                "type": "Site Access Coordination",
                "amount": site_adjustment
            })
            adjustments_total += site_adjustment
            
        if any(d.requires_permits for d in selected_deliverables):
            permit_adjustment = pricing["subtotal"] * 0.15  # 15% for permit management
            pricing["adjustments"].append({
                "type": "Permit & Compliance Management",
                "amount": permit_adjustment
            })
            adjustments_total += permit_adjustment
            
        pricing["total"] = pricing["subtotal"] + adjustments_total
        
        return pricing