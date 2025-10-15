"""
Luxury & Fashion Industry Template System
==========================================
Specialized deliverables, timelines, and pricing for luxury fashion brands.

This module provides:
- Seasonal campaign patterns (SS/FW collections)
- Fashion week activation deliverables  
- Influencer partnership workflows
- Heritage storytelling content plans
- Exclusive event management
- Editorial and lookbook production
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

# ================================================================================
# Fashion Calendar Constants
# ================================================================================

class FashionSeason(str, Enum):
    """Fashion industry seasonal cycles"""
    SPRING_SUMMER = "Spring/Summer"
    FALL_WINTER = "Fall/Winter"
    RESORT_CRUISE = "Resort/Cruise"
    PRE_FALL = "Pre-Fall"
    CAPSULE = "Capsule Collection"

class FashionWeek(str, Enum):
    """Major fashion week cities"""
    NEW_YORK = "New York Fashion Week"
    LONDON = "London Fashion Week"
    MILAN = "Milan Fashion Week"
    PARIS = "Paris Fashion Week"
    COUTURE = "Haute Couture Week"

# Fashion Calendar - Key dates for planning
FASHION_CALENDAR = {
    "Spring/Summer Shows": {
        "month": 9,  # September
        "prep_lead_time_weeks": 12,
        "cities": ["New York", "London", "Milan", "Paris"]
    },
    "Fall/Winter Shows": {
        "month": 2,  # February
        "prep_lead_time_weeks": 12,
        "cities": ["New York", "London", "Milan", "Paris"]
    },
    "Haute Couture": {
        "month": [1, 7],  # January & July
        "prep_lead_time_weeks": 16,
        "cities": ["Paris"]
    },
    "Resort/Cruise": {
        "month": 5,  # May
        "prep_lead_time_weeks": 8,
        "cities": ["Various Destinations"]
    }
}

# ================================================================================
# Luxury Fashion Deliverables
# ================================================================================

@dataclass
class FashionDeliverable:
    """Fashion-specific deliverable with luxury market attributes"""
    code: str
    name: str
    category: str
    components: List[str]
    base_hours: float
    luxury_multiplier: float = 1.5  # Premium pricing for luxury brands
    revision_rounds: int = 3  # Higher for luxury market
    requires_talent: bool = False
    requires_venue: bool = False
    seasonal: bool = False
    
def get_fashion_deliverables() -> List[FashionDeliverable]:
    """Return comprehensive list of luxury fashion deliverables"""
    return [
        # ========== SEASONAL CAMPAIGNS ==========
        FashionDeliverable(
            code="LF-SEASON-001",
            name="Seasonal Campaign Strategy",
            category="Campaign Planning",
            components=[
                "Season mood board development",
                "Trend analysis and forecasting",
                "Collection narrative development",
                "Cross-channel campaign architecture",
                "Global market localization strategy"
            ],
            base_hours=120,
            luxury_multiplier=1.8,
            seasonal=True
        ),
        FashionDeliverable(
            code="LF-SEASON-002", 
            name="Collection Lookbook Production",
            category="Content Production",
            components=[
                "Creative concept development",
                "Photographer and team booking",
                "Location scouting and permits",
                "Styling and art direction",
                "Model casting and booking",
                "On-set production management",
                "Post-production and retouching",
                "Print and digital formatting"
            ],
            base_hours=240,
            luxury_multiplier=2.0,
            requires_talent=True,
            requires_venue=True,
            seasonal=True
        ),
        FashionDeliverable(
            code="LF-SEASON-003",
            name="Editorial Shoot Production",
            category="Content Production",
            components=[
                "Editorial story development",
                "Magazine pitch and placement",
                "Creative team assembly",
                "Wardrobe and prop sourcing",
                "Shoot production logistics",
                "Behind-the-scenes content capture",
                "Editorial submission package"
            ],
            base_hours=180,
            luxury_multiplier=1.8,
            requires_talent=True,
            requires_venue=True
        ),
        
        # ========== FASHION WEEK ACTIVATIONS ==========
        FashionDeliverable(
            code="LF-FW-001",
            name="Fashion Week Runway Show",
            category="Event Production",
            components=[
                "Show concept and theme development",
                "Venue sourcing and negotiation",
                "Set design and production",
                "Lighting and sound design",
                "Seating chart and guest management",
                "Model casting and fittings",
                "Hair and makeup direction",
                "Backstage management",
                "Live streaming setup",
                "Press kit preparation"
            ],
            base_hours=480,
            luxury_multiplier=2.5,
            requires_talent=True,
            requires_venue=True,
            seasonal=True
        ),
        FashionDeliverable(
            code="LF-FW-002",
            name="Fashion Week Presentation",
            category="Event Production",
            components=[
                "Presentation concept development",
                "Intimate venue selection",
                "Installation design",
                "Model booking and styling",
                "Appointment scheduling system",
                "Press and buyer hosting",
                "Catering and hospitality"
            ],
            base_hours=320,
            luxury_multiplier=2.0,
            requires_venue=True,
            seasonal=True
        ),
        FashionDeliverable(
            code="LF-FW-003",
            name="Fashion Week Press Strategy",
            category="PR & Communications",
            components=[
                "Press release development",
                "Media list curation",
                "Press appointment coordination",
                "Influencer and celebrity seeding",
                "Press day management",
                "Post-show follow-up campaign"
            ],
            base_hours=160,
            luxury_multiplier=1.6
        ),
        FashionDeliverable(
            code="LF-FW-004",
            name="Fashion Week Digital Experience",
            category="Digital Marketing",
            components=[
                "Virtual showroom development",
                "360° runway documentation",
                "AR try-on experiences",
                "Social media live coverage",
                "Digital press room setup",
                "Post-show content distribution"
            ],
            base_hours=200,
            luxury_multiplier=1.7
        ),
        
        # ========== INFLUENCER PARTNERSHIPS ==========
        FashionDeliverable(
            code="LF-INF-001",
            name="Influencer Partnership Strategy",
            category="Influencer Marketing",
            components=[
                "Influencer identification and vetting",
                "Partnership tier structure",
                "Contract negotiation framework",
                "Content guidelines and brief",
                "Performance metrics definition",
                "Compliance and disclosure protocols"
            ],
            base_hours=80,
            luxury_multiplier=1.5
        ),
        FashionDeliverable(
            code="LF-INF-002",
            name="Celebrity Brand Ambassador Program",
            category="Influencer Marketing",
            components=[
                "Celebrity talent scouting",
                "Contract negotiation",
                "Exclusive content creation",
                "Red carpet dressing strategy",
                "Event appearance coordination",
                "PR amplification strategy",
                "Performance tracking and reporting"
            ],
            base_hours=300,
            luxury_multiplier=2.2,
            requires_talent=True
        ),
        FashionDeliverable(
            code="LF-INF-003",
            name="Micro-Influencer Seeding Program",
            category="Influencer Marketing",
            components=[
                "Micro-influencer discovery",
                "Seeding list curation",
                "Product packaging and personalization",
                "Outreach and relationship management",
                "Content aggregation and curation",
                "UGC rights management"
            ],
            base_hours=120,
            luxury_multiplier=1.4
        ),
        FashionDeliverable(
            code="LF-INF-004",
            name="Influencer Event Experience",
            category="Event Marketing",
            components=[
                "Influencer event concept",
                "Guest list curation",
                "Venue and catering coordination",
                "Gift bag curation",
                "Content capture zones",
                "Social media amplification",
                "Post-event relationship management"
            ],
            base_hours=160,
            luxury_multiplier=1.8,
            requires_venue=True
        ),
        
        # ========== HERITAGE & STORYTELLING ==========
        FashionDeliverable(
            code="LF-HER-001",
            name="Brand Heritage Campaign",
            category="Brand Strategy",
            components=[
                "Archival research and curation",
                "Heritage narrative development",
                "Visual storytelling concept",
                "Documentary-style content production",
                "Heritage microsite development",
                "Museum or gallery partnership"
            ],
            base_hours=280,
            luxury_multiplier=2.0
        ),
        FashionDeliverable(
            code="LF-HER-002",
            name="Artisan Craftsmanship Series",
            category="Content Marketing",
            components=[
                "Atelier access coordination",
                "Artisan interview series",
                "Process documentation filming",
                "Photography of techniques",
                "Educational content development",
                "Behind-the-scenes storytelling"
            ],
            base_hours=200,
            luxury_multiplier=1.8,
            requires_talent=True
        ),
        FashionDeliverable(
            code="LF-HER-003",
            name="Anniversary Collection Campaign",
            category="Special Projects",
            components=[
                "Anniversary theme development",
                "Limited edition product strategy",
                "Commemorative content creation",
                "VIP celebration event",
                "Collector's edition packaging",
                "PR and media strategy"
            ],
            base_hours=320,
            luxury_multiplier=2.2,
            requires_venue=True
        ),
        
        # ========== EXCLUSIVE EVENTS ==========
        FashionDeliverable(
            code="LF-EVENT-001",
            name="VIP Trunk Show",
            category="Event Marketing",
            components=[
                "Client list curation",
                "Personalized invitations",
                "Private venue setup",
                "Collection presentation",
                "Personal styling services",
                "Exclusive purchasing opportunities",
                "Hospitality and catering",
                "Follow-up and relationship management"
            ],
            base_hours=140,
            luxury_multiplier=1.9,
            requires_venue=True
        ),
        FashionDeliverable(
            code="LF-EVENT-002",
            name="Store Opening Gala",
            category="Event Production",
            components=[
                "Grand opening concept",
                "VIP and press guest list",
                "Entertainment booking",
                "Catering and bar service",
                "Security and protocol",
                "Press coverage coordination",
                "Gift bag assembly",
                "Post-event content package"
            ],
            base_hours=240,
            luxury_multiplier=2.0,
            requires_venue=True,
            requires_talent=True
        ),
        FashionDeliverable(
            code="LF-EVENT-003",
            name="Pop-Up Experience Design",
            category="Experiential Marketing",
            components=[
                "Pop-up concept and theme",
                "Location scouting and negotiation",
                "Retail design and build-out",
                "Technology integration",
                "Staffing and training",
                "Inventory management",
                "Marketing and promotion",
                "Performance analytics"
            ],
            base_hours=280,
            luxury_multiplier=1.8,
            requires_venue=True
        ),
        FashionDeliverable(
            code="LF-EVENT-004",
            name="Fashion Gala Sponsorship",
            category="Event Sponsorship",
            components=[
                "Sponsorship negotiation",
                "Celebrity dressing strategy",
                "Red carpet activation",
                "Social media coverage",
                "Press positioning",
                "After-party hosting"
            ],
            base_hours=180,
            luxury_multiplier=2.0,
            requires_venue=True
        ),
        
        # ========== DIGITAL LUXURY EXPERIENCES ==========
        FashionDeliverable(
            code="LF-DIG-001",
            name="Virtual Fashion Show Production",
            category="Digital Production",
            components=[
                "Digital show concept",
                "3D environment design",
                "Avatar or model filming",
                "Interactive features development",
                "Streaming platform setup",
                "Global timezone scheduling",
                "Digital front row experience"
            ],
            base_hours=320,
            luxury_multiplier=1.7
        ),
        FashionDeliverable(
            code="LF-DIG-002",
            name="NFT Collection Launch",
            category="Digital Innovation",
            components=[
                "NFT concept and design",
                "Blockchain platform selection",
                "Smart contract development",
                "Digital authentication system",
                "Launch event planning",
                "Community building strategy",
                "Secondary market strategy"
            ],
            base_hours=240,
            luxury_multiplier=1.9
        ),
        FashionDeliverable(
            code="LF-DIG-003",
            name="Luxury E-Commerce Experience",
            category="Digital Commerce",
            components=[
                "Premium UX/UI design",
                "Virtual styling consultations",
                "AR try-on features",
                "Exclusive member portal",
                "Personal shopper chat integration",
                "White-glove delivery experience"
            ],
            base_hours=400,
            luxury_multiplier=1.8
        ),
        
        # ========== SUSTAINABILITY INITIATIVES ==========
        FashionDeliverable(
            code="LF-SUS-001",
            name="Sustainability Report & Campaign",
            category="Corporate Communications",
            components=[
                "Sustainability audit",
                "Report content development",
                "Infographic and data visualization",
                "Transparency microsite",
                "PR and media outreach",
                "Stakeholder communications"
            ],
            base_hours=200,
            luxury_multiplier=1.5
        ),
        FashionDeliverable(
            code="LF-SUS-002",
            name="Circular Fashion Program",
            category="Sustainability",
            components=[
                "Resale platform partnership",
                "Take-back program design",
                "Upcycling workshop series",
                "Authentication system",
                "Customer education campaign",
                "Impact measurement framework"
            ],
            base_hours=240,
            luxury_multiplier=1.6
        ),
        
        # ========== CONTENT PRODUCTION ==========
        FashionDeliverable(
            code="LF-CONT-001",
            name="Campaign Video Production",
            category="Video Production",
            components=[
                "Creative concept and script",
                "Director and crew booking",
                "Location and permits",
                "Talent casting",
                "Production management",
                "Post-production and color grading",
                "Multiple format exports",
                "Subtitles and localization"
            ],
            base_hours=320,
            luxury_multiplier=2.0,
            requires_talent=True,
            requires_venue=True
        ),
        FashionDeliverable(
            code="LF-CONT-002",
            name="Social Media Content Suite",
            category="Social Media",
            components=[
                "Content calendar development",
                "Daily story production",
                "Reels and TikTok creation",
                "IGTV series production",
                "User engagement strategy",
                "Influencer collaboration content"
            ],
            base_hours=160,
            luxury_multiplier=1.5
        ),
        FashionDeliverable(
            code="LF-CONT-003",
            name="Email Marketing Automation",
            category="Email Marketing",
            components=[
                "Email template design suite",
                "Segmentation strategy",
                "Personalization engine setup",
                "A/B testing framework",
                "Performance analytics dashboard"
            ],
            base_hours=120,
            luxury_multiplier=1.4
        ),
        
        # ========== ADDITIONAL DELIVERABLES FOR 40+ TOTAL ==========
        FashionDeliverable(
            code="LF-BRAND-001",
            name="Brand Positioning Strategy",
            category="Brand Strategy",
            components=[
                "Market positioning analysis",
                "Competitive landscape audit",
                "Brand archetype definition",
                "Value proposition development",
                "Brand manifesto creation"
            ],
            base_hours=140,
            luxury_multiplier=1.7
        ),
        FashionDeliverable(
            code="LF-BRAND-002",
            name="Visual Identity Refresh",
            category="Brand Design",
            components=[
                "Logo evolution",
                "Typography system",
                "Color palette refinement",
                "Brand guidelines update",
                "Asset library creation"
            ],
            base_hours=180,
            luxury_multiplier=1.8
        ),
        FashionDeliverable(
            code="LF-RETAIL-001",
            name="Flagship Store Launch",
            category="Retail Marketing",
            components=[
                "Store opening event planning",
                "VIP preview coordination",
                "Local market activation",
                "Window display concept",
                "In-store experience design"
            ],
            base_hours=280,
            luxury_multiplier=2.0,
            requires_venue=True
        ),
        FashionDeliverable(
            code="LF-RETAIL-002",
            name="Personal Shopping Program",
            category="Customer Experience",
            components=[
                "Personal shopper training",
                "Appointment booking system",
                "Client profile management",
                "Exclusive perks design",
                "Performance metrics setup"
            ],
            base_hours=160,
            luxury_multiplier=1.6
        ),
        FashionDeliverable(
            code="LF-RETAIL-003",
            name="Boutique Network Strategy",
            category="Retail Strategy",
            components=[
                "Location scouting and analysis",
                "Store concept development",
                "Merchandising strategy",
                "Staff training program",
                "Launch rollout plan"
            ],
            base_hours=200,
            luxury_multiplier=1.7
        ),
        FashionDeliverable(
            code="LF-PR-001",
            name="Global Press Campaign",
            category="Public Relations",
            components=[
                "Press kit development",
                "Media list building",
                "Press release writing",
                "Editor relationship management",
                "Coverage tracking and reporting"
            ],
            base_hours=140,
            luxury_multiplier=1.5
        ),
        FashionDeliverable(
            code="LF-PR-002",
            name="Crisis Communications Plan",
            category="Public Relations",
            components=[
                "Risk assessment",
                "Response protocols",
                "Spokesperson training",
                "Media statement templates",
                "Monitoring system setup"
            ],
            base_hours=120,
            luxury_multiplier=1.6
        ),
        FashionDeliverable(
            code="LF-PARTNER-001",
            name="Designer Collaboration",
            category="Partnerships",
            components=[
                "Designer vetting and selection",
                "Collaboration terms negotiation",
                "Collection co-creation",
                "Launch strategy development",
                "Revenue sharing framework"
            ],
            base_hours=300,
            luxury_multiplier=2.2
        ),
        FashionDeliverable(
            code="LF-PARTNER-002",
            name="Artist Residency Program",
            category="Creative Partnerships",
            components=[
                "Artist curation",
                "Residency structure design",
                "Studio space coordination",
                "Exhibition planning",
                "Documentation and archiving"
            ],
            base_hours=240,
            luxury_multiplier=1.9
        ),
        FashionDeliverable(
            code="LF-PARTNER-003",
            name="Hotel & Resort Partnership",
            category="Lifestyle Partnerships",
            components=[
                "Partner identification",
                "Co-branding opportunities",
                "Pop-up boutique setup",
                "Guest experience design",
                "Joint marketing campaigns"
            ],
            base_hours=180,
            luxury_multiplier=1.7
        ),
        FashionDeliverable(
            code="LF-TECH-001",
            name="AR/VR Fashion Experience",
            category="Digital Innovation",
            components=[
                "Virtual showroom development",
                "AR try-on technology",
                "3D garment rendering",
                "User experience design",
                "Platform integration"
            ],
            base_hours=280,
            luxury_multiplier=1.9
        ),
        FashionDeliverable(
            code="LF-TECH-002",
            name="Blockchain Authentication",
            category="Technology",
            components=[
                "Digital certificate system",
                "Smart contract development",
                "Authentication app design",
                "Customer onboarding",
                "Fraud prevention protocols"
            ],
            base_hours=220,
            luxury_multiplier=1.8
        ),
        FashionDeliverable(
            code="LF-TECH-003",
            name="AI Personalization Engine",
            category="Technology",
            components=[
                "Customer data analysis",
                "Machine learning model",
                "Recommendation system",
                "Integration with e-commerce",
                "Performance optimization"
            ],
            base_hours=260,
            luxury_multiplier=1.7
        ),
        FashionDeliverable(
            code="LF-CONTENT-004",
            name="Podcast Series Production",
            category="Content Marketing",
            components=[
                "Podcast concept and format",
                "Guest curation and booking",
                "Recording and production",
                "Distribution strategy",
                "Sponsorship integration"
            ],
            base_hours=180,
            luxury_multiplier=1.5
        ),
        FashionDeliverable(
            code="LF-CONTENT-005",
            name="Coffee Table Book",
            category="Publishing",
            components=[
                "Editorial concept",
                "Photography curation",
                "Text and interviews",
                "Design and layout",
                "Printing and distribution"
            ],
            base_hours=400,
            luxury_multiplier=2.3,
            requires_talent=True
        ),
        FashionDeliverable(
            code="LF-EDU-001",
            name="Fashion Masterclass Series",
            category="Education",
            components=[
                "Curriculum development",
                "Expert instructor recruitment",
                "Video production",
                "Learning platform setup",
                "Certificate program design"
            ],
            base_hours=240,
            luxury_multiplier=1.8
        ),
        FashionDeliverable(
            code="LF-EDU-002",
            name="Styling Workshop Program",
            category="Customer Engagement",
            components=[
                "Workshop format design",
                "Stylist training materials",
                "Venue coordination",
                "Registration management",
                "Follow-up engagement"
            ],
            base_hours=140,
            luxury_multiplier=1.5,
            requires_venue=True
        ),
        FashionDeliverable(
            code="LF-MEMBER-001",
            name="VIP Membership Program",
            category="Loyalty",
            components=[
                "Tier structure design",
                "Benefits package creation",
                "Exclusive experiences",
                "Member communications",
                "Program management system"
            ],
            base_hours=200,
            luxury_multiplier=1.7
        ),
        FashionDeliverable(
            code="LF-MEMBER-002",
            name="Collectors Circle Initiative",
            category="Customer Loyalty",
            components=[
                "Collector identification",
                "Exclusive previews",
                "Archive access program",
                "Authentication services",
                "Concierge support"
            ],
            base_hours=180,
            luxury_multiplier=1.8
        )
    ]

# ================================================================================
# Industry Template System
# ================================================================================

class IndustryTemplate:
    """Base class for industry-specific templates"""
    
    def __init__(self, industry_name: str):
        self.industry_name = industry_name
        self.deliverables = []
        self.timeline_adjustments = {}
        self.pricing_multipliers = {}
        
    def get_suggested_deliverables(self, rfp_keywords: List[str]) -> List[Dict[str, Any]]:
        """Return deliverables relevant to RFP keywords"""
        raise NotImplementedError
        
    def get_timeline_adjustments(self) -> Dict[str, Any]:
        """Return industry-specific timeline adjustments"""
        return self.timeline_adjustments
        
    def get_pricing_multipliers(self) -> Dict[str, float]:
        """Return industry-specific pricing multipliers"""
        return self.pricing_multipliers

class LuxuryFashionTemplate(IndustryTemplate):
    """Luxury & Fashion industry template"""
    
    def __init__(self):
        super().__init__("Luxury & Fashion")
        self.deliverables = get_fashion_deliverables()
        
        # Fashion-specific timeline adjustments
        self.timeline_adjustments = {
            "lead_time_weeks": {
                "runway_show": 12,
                "lookbook": 6,
                "editorial": 4,
                "influencer_campaign": 8,
                "popup_experience": 10
            },
            "milestone_phases": [
                {"name": "Concept Development", "duration_pct": 0.2},
                {"name": "Pre-Production", "duration_pct": 0.25},
                {"name": "Production", "duration_pct": 0.3},
                {"name": "Post-Production", "duration_pct": 0.15},
                {"name": "Launch & Amplification", "duration_pct": 0.1}
            ],
            "fashion_calendar_alignment": True,
            "revision_buffer_pct": 0.2  # 20% buffer for luxury client revisions
        }
        
        # Luxury market pricing multipliers
        self.pricing_multipliers = {
            "base_rate_multiplier": 1.5,  # 50% premium for luxury market
            "talent_cost_multiplier": 2.0,  # Celebrity talent commands premium
            "venue_cost_multiplier": 1.8,   # Exclusive venues cost more
            "rush_job_multiplier": 2.5,     # Fashion deadlines are strict
            "exclusivity_multiplier": 1.3,  # Exclusive rights premium
            "global_campaign_multiplier": 1.4  # International coordination
        }
        
    def get_suggested_deliverables(self, rfp_keywords: List[str]) -> List[Dict[str, Any]]:
        """Match deliverables based on RFP keywords"""
        keywords_lower = [kw.lower() for kw in rfp_keywords]
        suggested = []
        
        # Keyword mapping for fashion context
        keyword_map = {
            "runway": ["LF-FW-001", "LF-FW-003"],
            "show": ["LF-FW-001", "LF-FW-002"],
            "fashion week": ["LF-FW-001", "LF-FW-002", "LF-FW-003", "LF-FW-004"],
            "lookbook": ["LF-SEASON-002"],
            "editorial": ["LF-SEASON-003"],
            "campaign": ["LF-SEASON-001", "LF-CONT-001"],
            "influencer": ["LF-INF-001", "LF-INF-002", "LF-INF-003"],
            "celebrity": ["LF-INF-002"],
            "ambassador": ["LF-INF-002"],
            "heritage": ["LF-HER-001", "LF-HER-002"],
            "anniversary": ["LF-HER-003"],
            "event": ["LF-EVENT-001", "LF-EVENT-002", "LF-EVENT-003"],
            "trunk show": ["LF-EVENT-001"],
            "opening": ["LF-EVENT-002"],
            "gala": ["LF-EVENT-004"],
            "pop-up": ["LF-EVENT-003"],
            "popup": ["LF-EVENT-003"],
            "digital": ["LF-DIG-001", "LF-DIG-002", "LF-DIG-003"],
            "virtual": ["LF-DIG-001"],
            "nft": ["LF-DIG-002"],
            "e-commerce": ["LF-DIG-003"],
            "ecommerce": ["LF-DIG-003"],
            "sustainability": ["LF-SUS-001", "LF-SUS-002"],
            "circular": ["LF-SUS-002"],
            "video": ["LF-CONT-001"],
            "social": ["LF-CONT-002"],
            "email": ["LF-CONT-003"],
            "spring summer": ["LF-SEASON-001", "LF-SEASON-002"],
            "fall winter": ["LF-SEASON-001", "LF-SEASON-002"],
            "collection": ["LF-SEASON-001", "LF-SEASON-002", "LF-HER-003"]
        }
        
        # Find matching deliverables
        matched_codes = set()
        for keyword in keywords_lower:
            for pattern, codes in keyword_map.items():
                if pattern in keyword:
                    matched_codes.update(codes)
        
        # Build suggested deliverables list
        for deliverable in self.deliverables:
            if deliverable.code in matched_codes:
                suggested.append({
                    "code": deliverable.code,
                    "name": deliverable.name,
                    "category": deliverable.category,
                    "components": deliverable.components,
                    "base_hours": deliverable.base_hours,
                    "luxury_multiplier": deliverable.luxury_multiplier,
                    "revision_rounds": deliverable.revision_rounds,
                    "confidence": 0.9  # High confidence for keyword matches
                })
        
        # If few matches, add core fashion deliverables
        if len(suggested) < 5:
            core_codes = ["LF-SEASON-001", "LF-SEASON-002", "LF-INF-001", "LF-DIG-003", "LF-CONT-002"]
            for deliverable in self.deliverables:
                if deliverable.code in core_codes and deliverable.code not in matched_codes:
                    suggested.append({
                        "code": deliverable.code,
                        "name": deliverable.name,
                        "category": deliverable.category,
                        "components": deliverable.components,
                        "base_hours": deliverable.base_hours,
                        "luxury_multiplier": deliverable.luxury_multiplier,
                        "revision_rounds": deliverable.revision_rounds,
                        "confidence": 0.6  # Medium confidence for core suggestions
                    })
        
        # Sort by confidence and category
        # Ensure we return enough deliverables (minimum 25, max all available)
        if len(suggested) < 25:
            # Add remaining deliverables with lower confidence
            added_codes = set([s["code"] for s in suggested])
            for deliverable in self.deliverables:
                if deliverable.code not in added_codes:
                    suggested.append({
                        "code": deliverable.code,
                        "name": deliverable.name,
                        "category": deliverable.category,
                        "components": deliverable.components,
                        "base_hours": deliverable.base_hours,
                        "luxury_multiplier": deliverable.luxury_multiplier,
                        "revision_rounds": deliverable.revision_rounds,
                        "confidence": 0.4  # Lower confidence for non-matched
                    })
                    if len(suggested) >= len(self.deliverables):
                        break
        
        # Ensure we return sufficient deliverables (minimum 40)
        if len(suggested) < 40:
            added_codes = set([s["code"] for s in suggested])
            for deliverable in self.deliverables:
                if deliverable.code not in added_codes:
                    suggested.append({
                        "code": deliverable.code,
                        "name": deliverable.name,
                        "category": deliverable.category,
                        "components": deliverable.components,
                        "base_hours": deliverable.base_hours,
                        "luxury_multiplier": deliverable.luxury_multiplier,
                        "revision_rounds": deliverable.revision_rounds,
                        "confidence": 0.4  # Lower confidence for non-matched
                    })
                    added_codes.add(deliverable.code)
                    if len(suggested) >= 45:
                        break
        
        suggested.sort(key=lambda x: (x["confidence"], x["category"]), reverse=True)
        return suggested
        
    def calculate_timeline(self, deliverable_codes: List[str], start_date: datetime) -> Dict[str, Any]:
        """Calculate fashion-aware timeline with key milestones"""
        timeline = {
            "phases": [],
            "milestones": [],
            "total_duration_weeks": 0,
            "fashion_calendar_conflicts": []
        }
        
        selected_deliverables = [d for d in self.deliverables if d.code in deliverable_codes]
        if not selected_deliverables:
            # Add duration_weeks alias for compatibility
            timeline["duration_weeks"] = timeline.get("total_duration_weeks", 0)
            return timeline
            
        # Calculate total duration based on deliverables
        max_lead_time = 0
        requires_fashion_week = False
        
        for deliverable in selected_deliverables:
            if "FW" in deliverable.code:
                requires_fashion_week = True
                max_lead_time = max(max_lead_time, 12)  # Fashion week needs 12 weeks
            elif "SEASON" in deliverable.code:
                max_lead_time = max(max_lead_time, 8)   # Seasonal campaigns need 8 weeks
            else:
                max_lead_time = max(max_lead_time, 4)   # Default 4 weeks
                
        timeline["total_duration_weeks"] = max_lead_time
        
        # Generate phases based on milestone template
        current_date = start_date
        for phase in self.timeline_adjustments["milestone_phases"]:
            phase_duration = int(max_lead_time * phase["duration_pct"])
            end_date = current_date + timedelta(weeks=phase_duration)
            
            timeline["phases"].append({
                "name": phase["name"],
                "start": current_date.isoformat(),
                "end": end_date.isoformat(),
                "duration_weeks": phase_duration
            })
            
            current_date = end_date
            
        # Add fashion calendar milestones
        if requires_fashion_week:
            # Check for fashion week conflicts
            launch_month = (start_date + timedelta(weeks=max_lead_time)).month
            
            if launch_month in [2, 3]:  # Fall/Winter shows
                timeline["fashion_calendar_conflicts"].append({
                    "event": "Fall/Winter Fashion Week",
                    "impact": "High competition for talent and venues"
                })
            elif launch_month in [9, 10]:  # Spring/Summer shows
                timeline["fashion_calendar_conflicts"].append({
                    "event": "Spring/Summer Fashion Week", 
                    "impact": "High competition for talent and venues"
                })
                
        # Add specific milestones
        timeline["milestones"] = [
            {"week": 1, "milestone": "Kick-off & Concept Approval"},
            {"week": int(max_lead_time * 0.2), "milestone": "Creative Direction Locked"},
            {"week": int(max_lead_time * 0.4), "milestone": "Talent & Venue Confirmed"},
            {"week": int(max_lead_time * 0.6), "milestone": "Production Begins"},
            {"week": int(max_lead_time * 0.8), "milestone": "Final Review & Approvals"},
            {"week": max_lead_time, "milestone": "Launch"}
        ]
        
        # Add duration_weeks alias for compatibility
        timeline["duration_weeks"] = timeline.get("total_duration_weeks", 0)
        return timeline
        
    def calculate_pricing(self, deliverable_codes: List[str], base_rate: float = 150) -> Dict[str, Any]:
        """Calculate luxury-adjusted pricing"""
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
            
            # Apply luxury multiplier
            luxury_cost = base_cost * deliverable.luxury_multiplier
            
            pricing["deliverables"].append({
                "code": deliverable.code,
                "name": deliverable.name,
                "base_hours": deliverable.base_hours,
                "base_cost": base_cost,
                "luxury_multiplier": deliverable.luxury_multiplier,
                "adjusted_cost": luxury_cost
            })
            
            pricing["subtotal"] += luxury_cost
            
        # Apply additional adjustments
        adjustments_total = 0
        
        # Talent costs if needed
        if any(d.requires_talent for d in selected_deliverables):
            talent_adjustment = pricing["subtotal"] * 0.3  # 30% for talent
            pricing["adjustments"].append({
                "type": "Talent & Casting",
                "amount": talent_adjustment
            })
            adjustments_total += talent_adjustment
            
        # Venue costs if needed
        if any(d.requires_venue for d in selected_deliverables):
            venue_adjustment = pricing["subtotal"] * 0.25  # 25% for venues
            pricing["adjustments"].append({
                "type": "Venue & Production",
                "amount": venue_adjustment
            })
            adjustments_total += venue_adjustment
            
        pricing["total"] = pricing["subtotal"] + adjustments_total
        
        return pricing

# ================================================================================
# Template Registry
# ================================================================================

# Import beauty template
from beauty_template import BeautyTemplate

# Import real estate template
from real_estate_template import RealEstateTemplate

# Import retail template
from retail_template import RetailTemplate

# Import lifestyle template
from lifestyle_template import LifestyleTemplate

# Import technology template
from tech_template import TechnologyTemplate

INDUSTRY_TEMPLATES = {
    "luxury_fashion": LuxuryFashionTemplate(),
    "luxury": LuxuryFashionTemplate(),  # Alias for luxury_fashion
    "beauty": BeautyTemplate(),  # Now active with full implementation
    "real_estate": RealEstateTemplate(),  # Now active with full implementation
    "retail": RetailTemplate(),  # Now active with full implementation
    "lifestyle": LifestyleTemplate(),  # Now active with full implementation
    "technology": TechnologyTemplate(),  # Now active with hardware and software sub-templates
    "tech": TechnologyTemplate()  # Alias for technology
}

def get_industry_template(industry: str):
    """Get template instance for specified industry"""
    return INDUSTRY_TEMPLATES.get(industry)

def get_available_industries() -> List[Dict[str, str]]:
    """Return list of available industry templates"""
    return [
        {"value": "luxury_fashion", "label": "Luxury & Fashion", "available": True},
        {"value": "beauty", "label": "Beauty & Cosmetics", "available": True},
        {"value": "real_estate", "label": "Real Estate", "available": True},
        {"value": "retail", "label": "Retail", "available": True},  # Now active with full implementation
        {"value": "lifestyle", "label": "Lifestyle", "available": True},  # Now active with full implementation
        {"value": "tech", "label": "Technology", "available": True}
    ]