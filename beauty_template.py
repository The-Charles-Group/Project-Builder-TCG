"""
Beauty & Cosmetics Industry Template System
============================================
Specialized deliverables, timelines, and pricing for beauty and cosmetics brands.

This module provides:
- Product launch campaign patterns
- Tutorial and educational content workflows
- Influencer and creator partnerships
- Clinical and efficacy messaging
- Sustainability and clean beauty narratives
- Ingredient storytelling and formulation content
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

# ================================================================================
# Beauty Industry Constants
# ================================================================================

class BeautyCategory(str, Enum):
    """Beauty product categories"""
    SKINCARE = "Skincare"
    MAKEUP = "Makeup"
    HAIRCARE = "Haircare"
    FRAGRANCE = "Fragrance"
    BODYCARE = "Body Care"
    WELLNESS = "Wellness & Supplements"
    TOOLS = "Beauty Tools & Devices"

class BeautyCampaignType(str, Enum):
    """Types of beauty campaigns"""
    PRODUCT_LAUNCH = "New Product Launch"
    SEASONAL_COLLECTION = "Seasonal Collection"
    BRAND_COLLAB = "Brand Partnership/Collaboration"
    SAMPLING_PROGRAM = "Sampling & Trial Program"
    EDUCATION_CAMPAIGN = "Education & Tutorial Campaign"
    CLINICAL_CAMPAIGN = "Clinical Efficacy Campaign"
    SUSTAINABILITY = "Sustainability Initiative"
    INGREDIENT_STORY = "Ingredient Storytelling"

class RetailPartner(str, Enum):
    """Major beauty retail partners"""
    SEPHORA = "Sephora"
    ULTA = "Ulta Beauty"
    NORDSTROM = "Nordstrom"
    SAKS = "Saks Fifth Avenue"
    BERGDORF = "Bergdorf Goodman"
    BLUEMERCURY = "Bluemercury"
    AMAZON = "Amazon Beauty"
    DTC = "Direct-to-Consumer"

# Beauty Calendar - Key retail and launch windows
BEAUTY_CALENDAR = {
    "Holiday Season": {
        "launch_month": 9,  # September for holiday collections
        "prep_lead_time_weeks": 16,
        "peak_months": [11, 12],
        "key_dates": ["Black Friday", "Cyber Monday", "Gift Sets Launch"]
    },
    "Spring/Summer": {
        "launch_month": 3,  # March for spring/summer
        "prep_lead_time_weeks": 12,
        "peak_months": [4, 5, 6],
        "key_dates": ["Mother's Day", "Graduation Season", "Summer Vacation"]
    },
    "Back to School": {
        "launch_month": 7,  # July for back-to-school
        "prep_lead_time_weeks": 8,
        "peak_months": [8, 9],
        "key_dates": ["College Move-In", "Fall Refresh"]
    },
    "New Year/Resolution": {
        "launch_month": 12,  # December for January launch
        "prep_lead_time_weeks": 10,
        "peak_months": [1, 2],
        "key_dates": ["New Year New You", "Valentine's Day Prep"]
    }
}

# Regulatory and compliance timelines
REGULATORY_TIMELINES = {
    "FDA_OTC": {
        "min_weeks": 12,
        "typical_weeks": 20,
        "description": "FDA OTC drug registration"
    },
    "Clinical_Testing": {
        "min_weeks": 8,
        "typical_weeks": 12,
        "description": "Clinical efficacy testing and validation"
    },
    "Claims_Substantiation": {
        "min_weeks": 4,
        "typical_weeks": 8,
        "description": "Marketing claims substantiation"
    },
    "EU_Compliance": {
        "min_weeks": 16,
        "typical_weeks": 24,
        "description": "EU cosmetics regulation compliance"
    },
    "Organic_Certification": {
        "min_weeks": 12,
        "typical_weeks": 16,
        "description": "Organic/Natural certification process"
    }
}

# ================================================================================
# Beauty Deliverables
# ================================================================================

@dataclass
class BeautyDeliverable:
    """Beauty-specific deliverable with industry attributes"""
    code: str
    name: str
    category: str
    components: List[str]
    base_hours: float
    complexity_multiplier: float = 1.0
    revision_rounds: int = 2
    requires_clinical: bool = False
    requires_influencer: bool = False
    requires_regulatory: bool = False
    retail_coordination: bool = False
    
def get_beauty_deliverables() -> List[BeautyDeliverable]:
    """Return comprehensive list of beauty industry deliverables"""
    return [
        # ========== PRODUCT LAUNCH CAMPAIGNS ==========
        BeautyDeliverable(
            code="BT-LAUNCH-001",
            name="Hero Product Launch Campaign",
            category="Product Launch",
            components=[
                "Product positioning and messaging",
                "Launch narrative development",
                "Visual identity and key art",
                "Campaign architecture across channels",
                "Launch timeline and rollout strategy",
                "Retail partner coordination",
                "PR and media strategy"
            ],
            base_hours=160,
            complexity_multiplier=1.5,
            retail_coordination=True
        ),
        BeautyDeliverable(
            code="BT-LAUNCH-002",
            name="Product Collection Launch",
            category="Product Launch",
            components=[
                "Collection theme and storytelling",
                "Individual product narratives",
                "Collection packaging strategy",
                "Cross-sell and bundle strategy",
                "Tiered launch approach",
                "Influencer seeding strategy",
                "Retail merchandising plan"
            ],
            base_hours=200,
            complexity_multiplier=1.6,
            requires_influencer=True,
            retail_coordination=True
        ),
        BeautyDeliverable(
            code="BT-LAUNCH-003",
            name="Limited Edition Campaign",
            category="Product Launch",
            components=[
                "Exclusivity narrative",
                "Scarcity marketing strategy",
                "Special packaging design brief",
                "VIP early access program",
                "Countdown campaign mechanics",
                "Waitlist management strategy",
                "Post-launch momentum plan"
            ],
            base_hours=140,
            complexity_multiplier=1.4
        ),
        BeautyDeliverable(
            code="BT-LAUNCH-004",
            name="Product Reformulation Announcement",
            category="Product Launch",
            components=[
                "Reformulation rationale messaging",
                "Comparison content (before/after)",
                "Clinical improvement highlights",
                "Customer transition strategy",
                "FAQ and education materials",
                "Loyalty program integration"
            ],
            base_hours=100,
            complexity_multiplier=1.2,
            requires_regulatory=True
        ),
        
        # ========== TUTORIAL & EDUCATIONAL CONTENT ==========
        BeautyDeliverable(
            code="BT-EDU-001",
            name="Video Tutorial Series",
            category="Educational Content",
            components=[
                "Tutorial concept development",
                "Step-by-step script writing",
                "MUA or expert booking",
                "Video production setup",
                "Multiple technique demonstrations",
                "Post-production and editing",
                "Platform optimization (YouTube, TikTok, IG)",
                "Shoppable video integration"
            ],
            base_hours=180,
            complexity_multiplier=1.5,
            requires_influencer=True
        ),
        BeautyDeliverable(
            code="BT-EDU-002",
            name="How-To Guide Development",
            category="Educational Content",
            components=[
                "Technique research and validation",
                "Step-by-step photography",
                "Written instructions",
                "Tips and tricks inclusion",
                "Common mistakes section",
                "Product recommendations",
                "Printable/downloadable formats"
            ],
            base_hours=80,
            complexity_multiplier=1.1
        ),
        BeautyDeliverable(
            code="BT-EDU-003",
            name="Masterclass Program",
            category="Educational Content",
            components=[
                "Curriculum development",
                "Expert instructor recruitment",
                "Live or recorded session production",
                "Interactive Q&A setup",
                "Certificate program design",
                "Community building elements",
                "Follow-up content series"
            ],
            base_hours=240,
            complexity_multiplier=1.7,
            requires_influencer=True
        ),
        BeautyDeliverable(
            code="BT-EDU-004",
            name="Skin/Hair Type Quiz & Recommendations",
            category="Educational Content",
            components=[
                "Quiz logic development",
                "Question and answer mapping",
                "Results algorithm design",
                "Personalized recommendations",
                "Product matching system",
                "Email capture and nurture flow",
                "Retake and tracking functionality"
            ],
            base_hours=120,
            complexity_multiplier=1.3
        ),
        
        # ========== INFLUENCER & CREATOR PARTNERSHIPS ==========
        BeautyDeliverable(
            code="BT-INF-001",
            name="Beauty Guru Partnership Campaign",
            category="Influencer Marketing",
            components=[
                "Influencer identification and vetting",
                "Partnership negotiation and contracts",
                "Content brief and guidelines",
                "Product seeding coordination",
                "Content calendar alignment",
                "Usage rights negotiation",
                "Performance tracking setup",
                "Amplification strategy"
            ],
            base_hours=160,
            complexity_multiplier=1.5,
            requires_influencer=True
        ),
        BeautyDeliverable(
            code="BT-INF-002",
            name="MUA Professional Program",
            category="Influencer Marketing",
            components=[
                "Professional MUA recruitment",
                "Pro discount program setup",
                "Exclusive product access",
                "Portfolio content creation",
                "Backstage and BTS content",
                "Masterclass opportunities",
                "Certification program"
            ],
            base_hours=200,
            complexity_multiplier=1.6,
            requires_influencer=True
        ),
        BeautyDeliverable(
            code="BT-INF-003",
            name="Micro-Influencer Seeding Campaign",
            category="Influencer Marketing",
            components=[
                "Micro-influencer discovery",
                "Authentic voice curation",
                "Personalized seeding boxes",
                "Unboxing experience design",
                "Content guidelines (flexible)",
                "UGC aggregation system",
                "Rights management",
                "Community building"
            ],
            base_hours=140,
            complexity_multiplier=1.3,
            requires_influencer=True
        ),
        BeautyDeliverable(
            code="BT-INF-004",
            name="Celebrity Spokesperson Campaign",
            category="Influencer Marketing",
            components=[
                "Celebrity talent scouting",
                "Contract negotiation",
                "Campaign creative development",
                "Photo/video shoot production",
                "Media tour coordination",
                "Red carpet appearances",
                "Social media integration",
                "PR amplification"
            ],
            base_hours=320,
            complexity_multiplier=2.0,
            requires_influencer=True
        ),
        
        # ========== CLINICAL & EFFICACY MESSAGING ==========
        BeautyDeliverable(
            code="BT-CLIN-001",
            name="Clinical Study Campaign",
            category="Clinical Marketing",
            components=[
                "Study design consultation",
                "Results visualization",
                "Before/after photography standards",
                "Statistical significance messaging",
                "Consumer-friendly translation",
                "Regulatory compliance review",
                "Healthcare professional outreach",
                "White paper development"
            ],
            base_hours=240,
            complexity_multiplier=1.3,
            requires_clinical=True,
            requires_regulatory=True
        ),
        BeautyDeliverable(
            code="BT-CLIN-002",
            name="Before/After Content Series",
            category="Clinical Marketing",
            components=[
                "Photography protocol development",
                "Participant recruitment",
                "Consent and release management",
                "Standardized capture process",
                "Image processing and validation",
                "Timeline documentation",
                "Testimonial capture",
                "Multi-format distribution"
            ],
            base_hours=180,
            complexity_multiplier=1.3,
            requires_clinical=True,
            requires_regulatory=True
        ),
        BeautyDeliverable(
            code="BT-CLIN-003",
            name="Dermatologist Partnership Program",
            category="Clinical Marketing",
            components=[
                "Dermatologist recruitment",
                "Clinical review process",
                "Professional samples program",
                "Educational materials development",
                "Office display materials",
                "Patient recommendation tools",
                "Professional testimonials",
                "Medical conference presence"
            ],
            base_hours=280,
            complexity_multiplier=1.5,
            requires_clinical=True
        ),
        BeautyDeliverable(
            code="BT-CLIN-004",
            name="Clinical Claims Substantiation",
            category="Clinical Marketing",
            components=[
                "Claims inventory and audit",
                "Testing protocol recommendation",
                "Third-party validation coordination",
                "Documentation package assembly",
                "Legal review facilitation",
                "Marketing claims refinement",
                "Disclaimer development"
            ],
            base_hours=160,
            complexity_multiplier=1.2,
            requires_regulatory=True
        ),
        
        # ========== SUSTAINABILITY & CLEAN BEAUTY ==========
        BeautyDeliverable(
            code="BT-SUS-001",
            name="Clean Beauty Campaign",
            category="Sustainability",
            components=[
                "Ingredient transparency story",
                "Clean beauty certification pursuit",
                "Formulation story development",
                "Safety messaging framework",
                "Comparison charts and tools",
                "Retailer clean programs alignment",
                "Third-party validation",
                "Education content series"
            ],
            base_hours=180,
            complexity_multiplier=1.4,
            requires_regulatory=True
        ),
        BeautyDeliverable(
            code="BT-SUS-002",
            name="Sustainable Packaging Initiative",
            category="Sustainability",
            components=[
                "Packaging audit and assessment",
                "Sustainable alternatives research",
                "Refill program design",
                "Recycling instructions development",
                "Partnership with TerraCycle or similar",
                "Consumer education campaign",
                "Impact reporting dashboard",
                "PR and communications strategy"
            ],
            base_hours=200,
            complexity_multiplier=1.5
        ),
        BeautyDeliverable(
            code="BT-SUS-003",
            name="Cruelty-Free Certification Campaign",
            category="Sustainability",
            components=[
                "Certification process management",
                "Leaping Bunny or PETA coordination",
                "Supply chain verification",
                "Marketing integration strategy",
                "Retailer notification process",
                "Consumer announcement campaign",
                "Website and packaging updates",
                "Advocacy partnership opportunities"
            ],
            base_hours=160,
            complexity_multiplier=1.3,
            requires_regulatory=True
        ),
        BeautyDeliverable(
            code="BT-SUS-004",
            name="Carbon Neutral Beauty Program",
            category="Sustainability",
            components=[
                "Carbon footprint assessment",
                "Reduction strategy development",
                "Offset program selection",
                "Supply chain engagement",
                "Consumer participation mechanics",
                "Transparency reporting",
                "Certification pursuit",
                "Marketing integration"
            ],
            base_hours=240,
            complexity_multiplier=1.6
        ),
        
        # ========== INGREDIENT STORYTELLING ==========
        BeautyDeliverable(
            code="BT-ING-001",
            name="Hero Ingredient Campaign",
            category="Ingredient Marketing",
            components=[
                "Ingredient science story",
                "Sourcing narrative development",
                "Efficacy data visualization",
                "Educational content creation",
                "Formulation story",
                "Competitive differentiation",
                "Cross-product integration",
                "Expert endorsements"
            ],
            base_hours=140,
            complexity_multiplier=1.3
        ),
        BeautyDeliverable(
            code="BT-ING-002",
            name="Ingredient Innovation Launch",
            category="Ingredient Marketing",
            components=[
                "Innovation story development",
                "Patent and proprietary messaging",
                "Scientific backing compilation",
                "Mechanism of action visualization",
                "Clinical proof points",
                "Trade media strategy",
                "B2B partnership opportunities",
                "Consumer translation"
            ],
            base_hours=180,
            complexity_multiplier=1.5,
            requires_clinical=True
        ),
        BeautyDeliverable(
            code="BT-ING-003",
            name="Natural/Botanical Story",
            category="Ingredient Marketing",
            components=[
                "Botanical sourcing story",
                "Traditional use history",
                "Modern science validation",
                "Sustainability angle",
                "Farm/supplier partnerships",
                "Extraction process content",
                "Purity and potency messaging",
                "Sensorial experience focus"
            ],
            base_hours=160,
            complexity_multiplier=1.3
        ),
        BeautyDeliverable(
            code="BT-ING-004",
            name="Technology Platform Campaign",
            category="Ingredient Marketing",
            components=[
                "Technology explanation simplified",
                "Delivery system visualization",
                "Performance data presentation",
                "Competitive advantages",
                "Patent landscape navigation",
                "Clinical validation",
                "Future pipeline preview",
                "B2B licensing opportunities"
            ],
            base_hours=200,
            complexity_multiplier=1.6,
            requires_clinical=True
        ),
        
        # ========== RETAIL & E-COMMERCE ==========
        BeautyDeliverable(
            code="BT-RETAIL-001",
            name="Sephora/Ulta Launch Program",
            category="Retail Marketing",
            components=[
                "Retailer pitch deck development",
                "Merchandising plan creation",
                "Gondola and endcap design",
                "Sales training materials",
                "Gratis program setup",
                "Promotional calendar alignment",
                "Digital shelf optimization",
                "Launch event planning"
            ],
            base_hours=240,
            complexity_multiplier=1.5,
            retail_coordination=True
        ),
        BeautyDeliverable(
            code="BT-RETAIL-002",
            name="DTC E-commerce Experience",
            category="Digital Commerce",
            components=[
                "Website UX/UI optimization",
                "Product page enhancement",
                "Virtual try-on integration",
                "Shade matching tools",
                "Subscription program design",
                "Loyalty program integration",
                "Personalization engine",
                "Chat and consultation features"
            ],
            base_hours=320,
            complexity_multiplier=1.7
        ),
        BeautyDeliverable(
            code="BT-RETAIL-003",
            name="Sampling Program Development",
            category="Retail Marketing",
            components=[
                "Sample size strategy",
                "Distribution channel planning",
                "Subscription box partnerships",
                "In-store sampling events",
                "Online sample requests system",
                "Sample-to-purchase tracking",
                "Follow-up nurture campaigns",
                "ROI measurement framework"
            ],
            base_hours=180,
            complexity_multiplier=1.4,
            retail_coordination=True
        ),
        BeautyDeliverable(
            code="BT-RETAIL-004",
            name="Holiday Gift Set Campaign",
            category="Seasonal Marketing",
            components=[
                "Gift set curation strategy",
                "Limited edition packaging design",
                "Value proposition development",
                "Gift guide placements",
                "Retailer exclusive offerings",
                "Gift with purchase mechanics",
                "Holiday party tie-ins",
                "Post-holiday conversion strategy"
            ],
            base_hours=200,
            complexity_multiplier=1.5,
            retail_coordination=True
        ),
        
        # ========== EVENTS & EXPERIENCES ==========
        BeautyDeliverable(
            code="BT-EVENT-001",
            name="Pop-Up Beauty Bar",
            category="Experiential Marketing",
            components=[
                "Pop-up concept and design",
                "Location scouting and negotiation",
                "Beauty station setup",
                "MUA and staff recruitment",
                "Service menu development",
                "Appointment booking system",
                "Product sampling strategy",
                "Social media integration"
            ],
            base_hours=280,
            complexity_multiplier=1.6,
            requires_influencer=True
        ),
        BeautyDeliverable(
            code="BT-EVENT-002",
            name="Influencer Beauty Event",
            category="Event Marketing",
            components=[
                "Event concept and theme",
                "Influencer guest list curation",
                "Venue selection and design",
                "Beauty stations and activities",
                "Gift bag curation",
                "Content capture setup",
                "Live social coverage",
                "Post-event content distribution"
            ],
            base_hours=200,
            complexity_multiplier=1.5,
            requires_influencer=True
        ),
        BeautyDeliverable(
            code="BT-EVENT-003",
            name="Virtual Beauty Consultation Platform",
            category="Digital Experience",
            components=[
                "Platform selection and setup",
                "Consultant training program",
                "Booking system integration",
                "Consultation flow design",
                "Product recommendation engine",
                "Follow-up automation",
                "Performance tracking",
                "Customer satisfaction system"
            ],
            base_hours=240,
            complexity_multiplier=1.6
        ),
        
        # ========== CONTENT PRODUCTION ==========
        BeautyDeliverable(
            code="BT-CONT-001",
            name="Product Photography Suite",
            category="Content Production",
            components=[
                "Creative direction development",
                "Photographer selection",
                "Props and set design",
                "Product styling",
                "Texture and swatch shots",
                "Lifestyle imagery",
                "Model shots (if applicable)",
                "Post-production and retouching"
            ],
            base_hours=160,
            complexity_multiplier=1.4
        ),
        BeautyDeliverable(
            code="BT-CONT-002",
            name="Social Media Content Calendar",
            category="Social Media",
            components=[
                "Monthly theme development",
                "Content pillar definition",
                "Daily post creation",
                "Stories and Reels planning",
                "UGC curation strategy",
                "Influencer content integration",
                "Community management guidelines",
                "Performance metrics setup"
            ],
            base_hours=120,
            complexity_multiplier=1.2
        ),
        BeautyDeliverable(
            code="BT-CONT-003",
            name="Email Marketing Campaign Series",
            category="Digital Marketing",
            components=[
                "Email strategy development",
                "Segmentation strategy",
                "Template design system",
                "Automated flow creation",
                "A/B testing framework",
                "Personalization tactics",
                "Mobile optimization",
                "Performance tracking"
            ],
            base_hours=140,
            complexity_multiplier=1.3
        )
    ]

# ================================================================================
# Campaign Timeline Templates
# ================================================================================

def get_beauty_campaign_timelines() -> Dict[str, Dict[str, Any]]:
    """Return standard timelines for different beauty campaign types"""
    return {
        "new_product_launch": {
            "name": "New Product Launch (6-12 weeks)",
            "duration_weeks": 12,
            "phases": [
                {
                    "name": "Pre-Launch Tease",
                    "week_start": 1,
                    "week_end": 2,
                    "deliverables": ["Teaser campaign", "Influencer seeding", "Waitlist setup"]
                },
                {
                    "name": "Soft Launch",
                    "week_start": 3,
                    "week_end": 4,
                    "deliverables": ["VIP early access", "Press samples", "First reviews"]
                },
                {
                    "name": "Full Launch",
                    "week_start": 5,
                    "week_end": 8,
                    "deliverables": ["Retail launch", "Paid media", "Content blitz"]
                },
                {
                    "name": "Sustain",
                    "week_start": 9,
                    "week_end": 12,
                    "deliverables": ["User generated content", "Replenishment", "Loyalty integration"]
                }
            ]
        },
        "seasonal_collection": {
            "name": "Seasonal Collection Launch",
            "duration_weeks": 8,
            "phases": [
                {
                    "name": "Collection Reveal",
                    "week_start": 1,
                    "week_end": 2,
                    "deliverables": ["Full collection reveal", "Editorial placements", "Influencer packages"]
                },
                {
                    "name": "Retail Rollout",
                    "week_start": 3,
                    "week_end": 5,
                    "deliverables": ["In-store displays", "Online feature", "Sales training"]
                },
                {
                    "name": "Peak Promotion",
                    "week_start": 6,
                    "week_end": 8,
                    "deliverables": ["Promotional offers", "Gift with purchase", "Bundle deals"]
                }
            ]
        },
        "influencer_collaboration": {
            "name": "Influencer Collaboration Launch",
            "duration_weeks": 10,
            "phases": [
                {
                    "name": "Announcement",
                    "week_start": 1,
                    "week_end": 2,
                    "deliverables": ["Partnership announcement", "BTS content", "Coming soon page"]
                },
                {
                    "name": "Content Creation",
                    "week_start": 3,
                    "week_end": 5,
                    "deliverables": ["Tutorial content", "Get ready with me", "Product stories"]
                },
                {
                    "name": "Launch Week",
                    "week_start": 6,
                    "week_end": 7,
                    "deliverables": ["Live events", "Exclusive access", "Media blitz"]
                },
                {
                    "name": "Extended Campaign",
                    "week_start": 8,
                    "week_end": 10,
                    "deliverables": ["Ongoing content", "Community engagement", "Restock alerts"]
                }
            ]
        },
        "clinical_launch": {
            "name": "Clinical Efficacy Campaign",
            "duration_weeks": 8,
            "phases": [
                {
                    "name": "Study Results Release",
                    "week_start": 1,
                    "week_end": 2,
                    "deliverables": ["Clinical data release", "Expert testimonials", "Media briefing"]
                },
                {
                    "name": "Education Phase",
                    "week_start": 3,
                    "week_end": 5,
                    "deliverables": ["How it works content", "Ingredient deep dive", "Q&A sessions"]
                },
                {
                    "name": "Trial Program",
                    "week_start": 6,
                    "week_end": 8,
                    "deliverables": ["Sample distribution", "Before/after collection", "Review generation"]
                }
            ]
        }
    }

# ================================================================================
# Pricing Structure
# ================================================================================

class BeautyPricingFactors:
    """Pricing multipliers for beauty-specific requirements"""
    
    # Base multipliers
    STANDARD = 1.0
    
    # Clinical and regulatory premiums
    CLINICAL_PHOTOGRAPHY = 1.3  # Medical-grade photography
    CLINICAL_TESTING = 1.4      # Clinical trial coordination
    REGULATORY_COMPLIANCE = 1.2  # Claims work and compliance
    
    # Influencer and talent premiums  
    INFLUENCER_CONTENT_RIGHTS = 1.5  # Usage rights for influencer content
    CELEBRITY_TALENT = 2.0           # Celebrity spokesperson campaigns
    MUA_PROFESSIONALS = 1.3          # Professional makeup artist involvement
    
    # Retail partner premiums
    MAJOR_RETAILER_LAUNCH = 1.4     # Sephora/Ulta launch requirements
    MULTI_RETAILER_COORDINATION = 1.3  # Coordinating multiple retail partners
    
    # Speed premiums
    RUSH_LAUNCH = 1.5  # Less than 4 weeks to launch
    EXPEDITED = 1.3    # Less than 6 weeks to launch
    
    # Complexity premiums
    GLOBAL_CAMPAIGN = 1.4      # Multi-market coordination
    MULTI_LANGUAGE = 1.3       # Localization requirements
    TECHNICAL_INNOVATION = 1.5  # New technology or innovation
    
    @classmethod
    def calculate_total_multiplier(cls, factors: List[str]) -> float:
        """Calculate combined multiplier from list of factor names"""
        multiplier = cls.STANDARD
        for factor in factors:
            if hasattr(cls, factor):
                factor_value = getattr(cls, factor)
                # Compound multipliers but cap at 2.5x
                multiplier *= factor_value
        return min(multiplier, 2.5)

# ================================================================================
# Beauty Industry Template Class
# ================================================================================

class BeautyTemplate:
    """Complete template system for beauty and cosmetics projects"""
    
    def __init__(self):
        self.deliverables = get_beauty_deliverables()
        self.timelines = get_beauty_campaign_timelines()
        self.pricing = BeautyPricingFactors()
        self.calendar = BEAUTY_CALENDAR
        self.regulatory = REGULATORY_TIMELINES
    
    def get_deliverables_for_campaign(self, campaign_type: BeautyCampaignType) -> List[BeautyDeliverable]:
        """Get relevant deliverables for a specific campaign type"""
        campaign_deliverable_map = {
            BeautyCampaignType.PRODUCT_LAUNCH: [
                "BT-LAUNCH-001", "BT-LAUNCH-002", "BT-CONT-001", "BT-RETAIL-001",
                "BT-INF-001", "BT-EDU-001", "BT-ING-001"
            ],
            BeautyCampaignType.SEASONAL_COLLECTION: [
                "BT-LAUNCH-002", "BT-LAUNCH-003", "BT-RETAIL-004", "BT-EVENT-002",
                "BT-CONT-001", "BT-INF-003"
            ],
            BeautyCampaignType.BRAND_COLLAB: [
                "BT-INF-004", "BT-INF-001", "BT-EVENT-002", "BT-LAUNCH-003",
                "BT-CONT-002", "BT-EDU-003"
            ],
            BeautyCampaignType.SAMPLING_PROGRAM: [
                "BT-RETAIL-003", "BT-INF-003", "BT-EDU-001", "BT-EVENT-001"
            ],
            BeautyCampaignType.EDUCATION_CAMPAIGN: [
                "BT-EDU-001", "BT-EDU-002", "BT-EDU-003", "BT-EDU-004",
                "BT-INF-002", "BT-EVENT-003"
            ],
            BeautyCampaignType.CLINICAL_CAMPAIGN: [
                "BT-CLIN-001", "BT-CLIN-002", "BT-CLIN-003", "BT-CLIN-004",
                "BT-ING-002", "BT-EDU-001"
            ],
            BeautyCampaignType.SUSTAINABILITY: [
                "BT-SUS-001", "BT-SUS-002", "BT-SUS-003", "BT-SUS-004",
                "BT-ING-003", "BT-CONT-002"
            ],
            BeautyCampaignType.INGREDIENT_STORY: [
                "BT-ING-001", "BT-ING-002", "BT-ING-003", "BT-ING-004",
                "BT-EDU-002", "BT-CLIN-001"
            ]
        }
        
        relevant_codes = campaign_deliverable_map.get(campaign_type, [])
        return [d for d in self.deliverables if d.code in relevant_codes]
    
    def calculate_timeline(self, deliverable_codes: List[str], start_date: datetime) -> Dict[str, Any]:
        """Calculate beauty-aware timeline with milestones - API compatible"""
        timeline = {
            "phases": [],
            "milestones": [],
            "total_duration_weeks": 0,
            "beauty_calendar_conflicts": [],
            "regulatory_requirements": []
        }
        
        selected_deliverables = [d for d in self.deliverables if d.code in deliverable_codes]
        if not selected_deliverables:
            return timeline
        
        # Calculate total duration based on deliverables
        max_lead_time = 4  # Base minimum
        requires_clinical = False
        requires_regulatory = False
        requires_retail = False
        
        for deliverable in selected_deliverables:
            if deliverable.requires_clinical:
                requires_clinical = True
                max_lead_time = max(max_lead_time, 12)  # Clinical needs 12+ weeks
            if deliverable.requires_regulatory:
                requires_regulatory = True
                max_lead_time = max(max_lead_time, 8)   # Regulatory needs 8+ weeks
            if deliverable.retail_coordination:
                requires_retail = True
                max_lead_time = max(max_lead_time, 6)   # Retail coordination needs 6+ weeks
            elif deliverable.requires_influencer:
                max_lead_time = max(max_lead_time, 6)   # Influencer seeding needs 6 weeks
            elif "LAUNCH" in deliverable.code:
                max_lead_time = max(max_lead_time, 8)   # Product launches need 8 weeks
        
        timeline["total_duration_weeks"] = max_lead_time
        
        # Generate phases based on campaign type
        current_date = start_date
        
        # Determine phase structure based on deliverables
        if requires_clinical:
            phases = [
                {"name": "Clinical Testing & Validation", "duration_pct": 0.3},
                {"name": "Content Development", "duration_pct": 0.2},
                {"name": "Pre-Launch & Seeding", "duration_pct": 0.2},
                {"name": "Launch Activation", "duration_pct": 0.2},
                {"name": "Sustain & Amplify", "duration_pct": 0.1}
            ]
        elif requires_retail:
            phases = [
                {"name": "Retail Planning & Coordination", "duration_pct": 0.2},
                {"name": "Creative Development", "duration_pct": 0.2},
                {"name": "Pre-Launch Activities", "duration_pct": 0.2},
                {"name": "Retail Launch", "duration_pct": 0.3},
                {"name": "Post-Launch Support", "duration_pct": 0.1}
            ]
        else:
            phases = [
                {"name": "Strategy & Planning", "duration_pct": 0.15},
                {"name": "Creative Development", "duration_pct": 0.25},
                {"name": "Production", "duration_pct": 0.25},
                {"name": "Launch", "duration_pct": 0.25},
                {"name": "Optimization", "duration_pct": 0.1}
            ]
        
        for phase in phases:
            phase_duration = int(max_lead_time * phase["duration_pct"])
            if phase_duration == 0:
                phase_duration = 1  # Minimum 1 week per phase
            end_date = current_date + timedelta(weeks=phase_duration)
            
            timeline["phases"].append({
                "name": phase["name"],
                "start": current_date.isoformat(),
                "end": end_date.isoformat(),
                "duration_weeks": phase_duration
            })
            
            current_date = end_date
        
        # Add beauty-specific milestones
        timeline["milestones"] = [
            {"week": 1, "milestone": "Kick-off & Brief Alignment"},
            {"week": int(max_lead_time * 0.2), "milestone": "Concept & Creative Approved"},
            {"week": int(max_lead_time * 0.4), "milestone": "Influencer/Talent Confirmed"},
            {"week": int(max_lead_time * 0.5), "milestone": "Content Production Complete"},
            {"week": int(max_lead_time * 0.7), "milestone": "Retail Partner Alignment"},
            {"week": int(max_lead_time * 0.9), "milestone": "Soft Launch/Seeding"},
            {"week": max_lead_time, "milestone": "Full Market Launch"}
        ]
        
        # Check for beauty calendar conflicts
        launch_month = (start_date + timedelta(weeks=max_lead_time)).month
        
        if launch_month in [11, 12]:  # Holiday season
            timeline["beauty_calendar_conflicts"].append({
                "event": "Holiday Shopping Season",
                "impact": "High competition for shelf space and consumer attention"
            })
        elif launch_month in [3, 4]:  # Spring refresh
            timeline["beauty_calendar_conflicts"].append({
                "event": "Spring Beauty Refresh",
                "impact": "Major retailers launching spring collections"
            })
        elif launch_month in [9, 10]:  # Fall/holiday prep
            timeline["beauty_calendar_conflicts"].append({
                "event": "Fall/Holiday Collection Launches",
                "impact": "Retailers focusing on holiday sets and gift offerings"
            })
        
        # Add regulatory requirements if needed
        if requires_regulatory:
            timeline["regulatory_requirements"].append({
                "requirement": "Claims Substantiation",
                "lead_time_weeks": 4,
                "description": "Marketing claims validation and legal review"
            })
        if requires_clinical:
            timeline["regulatory_requirements"].append({
                "requirement": "Clinical Testing",
                "lead_time_weeks": 8,
                "description": "Clinical efficacy testing and documentation"
            })
        
        return timeline
    
    def calculate_pricing(self, deliverable_codes: List[str], base_rate: float = 150) -> Dict[str, Any]:
        """Calculate beauty-adjusted pricing - API compatible"""
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
            
            # Apply complexity multiplier
            adjusted_cost = base_cost * deliverable.complexity_multiplier
            
            pricing["deliverables"].append({
                "code": deliverable.code,
                "name": deliverable.name,
                "base_hours": deliverable.base_hours,
                "base_cost": base_cost,
                "complexity_multiplier": deliverable.complexity_multiplier,
                "adjusted_cost": adjusted_cost
            })
            
            pricing["subtotal"] += adjusted_cost
        
        # Apply additional adjustments based on requirements
        adjustments_total = 0
        
        # Clinical photography/testing premium
        if any(d.requires_clinical for d in selected_deliverables):
            clinical_adjustment = pricing["subtotal"] * 0.3  # 30% for clinical requirements
            pricing["adjustments"].append({
                "type": "Clinical Testing & Photography",
                "amount": clinical_adjustment
            })
            adjustments_total += clinical_adjustment
        
        # Influencer content rights premium
        if any(d.requires_influencer for d in selected_deliverables):
            influencer_adjustment = pricing["subtotal"] * 0.25  # 25% for influencer rights
            pricing["adjustments"].append({
                "type": "Influencer Content Rights",
                "amount": influencer_adjustment
            })
            adjustments_total += influencer_adjustment
        
        # Regulatory compliance premium
        if any(d.requires_regulatory for d in selected_deliverables):
            regulatory_adjustment = pricing["subtotal"] * 0.2  # 20% for regulatory work
            pricing["adjustments"].append({
                "type": "Regulatory Compliance",
                "amount": regulatory_adjustment
            })
            adjustments_total += regulatory_adjustment
        
        # Retail coordination premium
        if any(d.retail_coordination for d in selected_deliverables):
            retail_adjustment = pricing["subtotal"] * 0.15  # 15% for retail coordination
            pricing["adjustments"].append({
                "type": "Retail Partner Coordination",
                "amount": retail_adjustment
            })
            adjustments_total += retail_adjustment
        
        pricing["total"] = pricing["subtotal"] + adjustments_total
        
        return pricing
    
    def get_suggested_deliverables(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Get suggested deliverables based on keywords - API compatible method"""
        suggested = []
        keywords_lower = [k.lower() for k in keywords] if keywords else []
        
        # If no keywords, use the brief text method
        if not keywords:
            # Return default beauty deliverables
            default_codes = ["BT-LAUNCH-001", "BT-CONT-001", "BT-CONT-002", "BT-INF-001"]
            for deliverable in self.deliverables:
                if deliverable.code in default_codes:
                    suggested.append(self._deliverable_to_dict(deliverable, confidence=0.6))
            return suggested
        
        # Beauty-specific keyword mapping
        keyword_map = {
            # Product related
            "launch": ["BT-LAUNCH-001", "BT-LAUNCH-002"],
            "product": ["BT-LAUNCH-001", "BT-LAUNCH-002"],
            "collection": ["BT-LAUNCH-002", "BT-RETAIL-004"],
            "limited": ["BT-LAUNCH-003"],
            "exclusive": ["BT-LAUNCH-003"],
            "reformulation": ["BT-LAUNCH-004"],
            
            # Education/Tutorial
            "tutorial": ["BT-EDU-001", "BT-EDU-002"],
            "education": ["BT-EDU-001", "BT-EDU-002", "BT-EDU-003"],
            "masterclass": ["BT-EDU-003"],
            "quiz": ["BT-EDU-004"],
            "how-to": ["BT-EDU-001", "BT-EDU-002"],
            
            # Influencer
            "influencer": ["BT-INF-001", "BT-INF-003"],
            "beauty guru": ["BT-INF-001"],
            "mua": ["BT-INF-002"],
            "makeup artist": ["BT-INF-002"],
            "celebrity": ["BT-INF-004"],
            "ambassador": ["BT-INF-004"],
            "seeding": ["BT-INF-003"],
            
            # Clinical
            "clinical": ["BT-CLIN-001", "BT-CLIN-002"],
            "study": ["BT-CLIN-001"],
            "efficacy": ["BT-CLIN-001"],
            "before": ["BT-CLIN-002"],
            "after": ["BT-CLIN-002"],
            "dermatologist": ["BT-CLIN-003"],
            "claims": ["BT-CLIN-004"],
            
            # Sustainability
            "clean": ["BT-SUS-001"],
            "natural": ["BT-SUS-001", "BT-ING-003"],
            "organic": ["BT-SUS-001"],
            "sustainable": ["BT-SUS-002"],
            "packaging": ["BT-SUS-002"],
            "cruelty-free": ["BT-SUS-003"],
            "vegan": ["BT-SUS-003"],
            "carbon": ["BT-SUS-004"],
            
            # Ingredients
            "ingredient": ["BT-ING-001", "BT-ING-003"],
            "formula": ["BT-ING-001"],
            "innovation": ["BT-ING-002"],
            "technology": ["BT-ING-002", "BT-ING-004"],
            "botanical": ["BT-ING-003"],
            
            # Retail
            "sephora": ["BT-RETAIL-001"],
            "ulta": ["BT-RETAIL-001"],
            "retail": ["BT-RETAIL-001"],
            "ecommerce": ["BT-RETAIL-002"],
            "sample": ["BT-RETAIL-003"],
            "sampling": ["BT-RETAIL-003"],
            "holiday": ["BT-RETAIL-004"],
            "gift": ["BT-RETAIL-004"],
            
            # Events
            "popup": ["BT-EVENT-001"],
            "pop-up": ["BT-EVENT-001"],
            "event": ["BT-EVENT-002"],
            "virtual": ["BT-EVENT-003"],
            "consultation": ["BT-EVENT-003"],
            
            # Content
            "photography": ["BT-CONT-001"],
            "photo": ["BT-CONT-001"],
            "social": ["BT-CONT-002"],
            "instagram": ["BT-CONT-002"],
            "tiktok": ["BT-CONT-002"],
            "email": ["BT-CONT-003"]
        }
        
        # Find matching deliverables based on keywords
        matched_codes = set()
        for keyword in keywords_lower:
            for pattern, codes in keyword_map.items():
                if pattern in keyword or keyword in pattern:
                    matched_codes.update(codes)
        
        # Build suggested deliverables list
        for deliverable in self.deliverables:
            if deliverable.code in matched_codes:
                suggested.append(self._deliverable_to_dict(deliverable, confidence=0.9))
        
        # If few matches, add core beauty deliverables
        if len(suggested) < 5:
            core_codes = ["BT-LAUNCH-001", "BT-INF-001", "BT-CONT-001", "BT-EDU-001", "BT-RETAIL-001"]
            for deliverable in self.deliverables:
                if deliverable.code in core_codes and deliverable.code not in matched_codes:
                    suggested.append(self._deliverable_to_dict(deliverable, confidence=0.6))
        
        # Sort by confidence
        suggested.sort(key=lambda x: x["confidence"], reverse=True)
        return suggested
    
    def _deliverable_to_dict(self, deliverable: BeautyDeliverable, confidence: float = 0.8) -> Dict[str, Any]:
        """Convert deliverable to API response format"""
        return {
            "code": deliverable.code,
            "name": deliverable.name,
            "category": deliverable.category,
            "components": deliverable.components,
            "base_hours": deliverable.base_hours,
            "complexity_multiplier": deliverable.complexity_multiplier,
            "revision_rounds": deliverable.revision_rounds,
            "confidence": confidence
        }
    
    def suggest_deliverables_from_brief(self, brief_text: str) -> List[BeautyDeliverable]:
        """Legacy method for direct brief analysis"""
        # Extract keywords from brief
        import re
        words = re.findall(r'\b[a-zA-Z]{3,}\b', brief_text.lower())
        
        # Filter for beauty-relevant keywords
        beauty_keywords = ["beauty", "cosmetic", "skincare", "makeup", "product", "launch",
                          "influencer", "tutorial", "clinical", "ingredient", "sustainable",
                          "sephora", "ulta", "sample", "event", "campaign"]
        keywords = [w for w in words if w in beauty_keywords]
        
        # Use the main suggestion method
        suggestions_dict = self.get_suggested_deliverables(keywords)
        
        # Convert back to deliverable objects
        suggested_codes = [s["code"] for s in suggestions_dict]
        return [d for d in self.deliverables if d.code in suggested_codes]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for API responses"""
        return {
            "industry": "beauty_cosmetics",
            "name": "Beauty & Cosmetics Industry Template",
            "description": "Specialized template for beauty brands including product launches, clinical campaigns, and influencer partnerships",
            "deliverable_count": len(self.deliverables),
            "campaign_types": [ct.value for ct in BeautyCampaignType],
            "categories": list(set(d.category for d in self.deliverables)),
            "features": [
                "Product launch workflows",
                "Clinical efficacy messaging",
                "Influencer partnership management",
                "Regulatory compliance tracking",
                "Sustainability initiatives",
                "Retail partner coordination"
            ]
        }

# ================================================================================
# Export Functions for API Integration
# ================================================================================

def get_beauty_template_instance() -> BeautyTemplate:
    """Factory function to create beauty template instance"""
    return BeautyTemplate()

def get_beauty_deliverable_suggestions(brief_text: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get deliverable suggestions for API endpoint"""
    template = BeautyTemplate()
    suggestions = template.suggest_deliverables_from_brief(brief_text)[:limit]
    
    return [
        {
            "code": d.code,
            "name": d.name,
            "category": d.category,
            "base_hours": d.base_hours,
            "components": d.components,
            "requires_clinical": d.requires_clinical,
            "requires_influencer": d.requires_influencer,
            "requires_regulatory": d.requires_regulatory,
            "retail_coordination": d.retail_coordination
        }
        for d in suggestions
    ]

# Module exports
__all__ = [
    'BeautyTemplate',
    'BeautyDeliverable', 
    'BeautyCampaignType',
    'BeautyCategory',
    'RetailPartner',
    'BeautyPricingFactors',
    'get_beauty_deliverables',
    'get_beauty_campaign_timelines',
    'get_beauty_template_instance',
    'get_beauty_deliverable_suggestions'
]