"""
Technology Industry Template System
====================================
Specialized deliverables, timelines, and pricing for technology companies.

This module provides two distinct sub-templates:
- Hardware Technology (HP/Dell/Apple style): Product launches, trade shows, technical content
- Software Technology (Microsoft/Adobe/Salesforce style): SaaS launches, developer programs, cloud solutions

Features:
- B2B enterprise focus
- Technical audience considerations
- Product launch cycles
- Developer ecosystem management
- Channel partner programs
- Technical documentation and training
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

# ================================================================================
# Technology Industry Constants
# ================================================================================

class TechEventType(str, Enum):
    """Major technology industry events"""
    CES = "Consumer Electronics Show"
    COMPUTEX = "Computex Taipei"
    MWC = "Mobile World Congress"
    BUILD = "Microsoft Build"
    WWDC = "Apple WWDC"
    GOOGLE_IO = "Google I/O"
    REINVENT = "AWS re:Invent"
    DREAMFORCE = "Salesforce Dreamforce"
    IGNITE = "Microsoft Ignite"

class ProductLifecycle(str, Enum):
    """Product lifecycle stages"""
    ALPHA = "Alpha"
    BETA = "Beta"
    PREVIEW = "Preview"
    GA = "General Availability"
    LTS = "Long Term Support"
    EOL = "End of Life"

# Tech Event Calendar
TECH_CALENDAR = {
    "CES": {
        "month": 1,
        "location": "Las Vegas",
        "prep_lead_weeks": 16,
        "focus": "Consumer Electronics"
    },
    "Mobile World Congress": {
        "month": 2,
        "location": "Barcelona",
        "prep_lead_weeks": 12,
        "focus": "Mobile & Telecom"
    },
    "Build": {
        "month": 5,
        "location": "Seattle",
        "prep_lead_weeks": 10,
        "focus": "Developer Tools"
    },
    "Computex": {
        "month": 6,
        "location": "Taipei",
        "prep_lead_weeks": 14,
        "focus": "PC & Components"
    },
    "re:Invent": {
        "month": 11,
        "location": "Las Vegas",
        "prep_lead_weeks": 12,
        "focus": "Cloud & AWS"
    }
}

# ================================================================================
# Base Technology Deliverable
# ================================================================================

@dataclass
class TechDeliverable:
    """Technology-specific deliverable with enterprise attributes"""
    code: str
    name: str
    category: str
    components: List[str]
    base_hours: float
    enterprise_multiplier: float = 1.3  # B2B enterprise pricing
    technical_complexity: float = 1.0  # Technical audience factor
    revision_rounds: int = 2
    requires_engineering: bool = False
    requires_certification: bool = False
    requires_compliance: bool = False

# ================================================================================
# Hardware Technology Template (HP/Dell/Apple style)
# ================================================================================

class HardwareTechTemplate:
    """Template for hardware technology companies"""
    
    def __init__(self):
        self.name = "Hardware Technology"
        self.description = "Product launches, trade shows, technical specifications for hardware companies"
        self.deliverables = self._get_hardware_deliverables()
        
        # Hardware-specific timeline adjustments
        self.timeline_adjustments = {
            "product_launch_phases": [
                {"name": "Pre-Announcement", "duration_pct": 0.2},
                {"name": "Manufacturing Ramp", "duration_pct": 0.25},
                {"name": "Channel Preparation", "duration_pct": 0.2},
                {"name": "Launch Campaign", "duration_pct": 0.2},
                {"name": "Post-Launch Support", "duration_pct": 0.15}
            ],
            "regulatory_buffer_weeks": 6,  # FCC/CE approvals
            "supply_chain_buffer_weeks": 4
        }
        
        # Hardware pricing multipliers
        self.pricing_multipliers = {
            "base_rate_multiplier": 1.4,
            "trade_show_multiplier": 2.0,
            "global_launch_multiplier": 1.6,
            "channel_program_multiplier": 1.5,
            "technical_documentation_multiplier": 1.3
        }
    
    def _get_hardware_deliverables(self) -> List[TechDeliverable]:
        """Return comprehensive list of hardware tech deliverables"""
        return [
            # ========== PRODUCT LAUNCH DELIVERABLES ==========
            TechDeliverable(
                code="HW-LAUNCH-001",
                name="Product Announcement Campaign",
                category="Product Launch",
                components=[
                    "Keynote presentation design",
                    "Press event planning and execution",
                    "Product messaging framework",
                    "Executive spokesperson training",
                    "Press kit development",
                    "Media embargo management",
                    "Launch day war room coordination",
                    "Social media countdown campaign"
                ],
                base_hours=280,
                enterprise_multiplier=1.8,
                technical_complexity=1.4
            ),
            TechDeliverable(
                code="HW-LAUNCH-002",
                name="Technical Specifications Content",
                category="Technical Content",
                components=[
                    "Spec sheet development",
                    "Benchmark methodology design",
                    "Performance comparison charts",
                    "Technical white papers",
                    "Architecture diagrams",
                    "Compatibility matrices",
                    "Environmental certifications",
                    "Regulatory compliance documentation"
                ],
                base_hours=160,
                enterprise_multiplier=1.5,
                technical_complexity=1.8,
                requires_engineering=True,
                requires_compliance=True
            ),
            TechDeliverable(
                code="HW-LAUNCH-003",
                name="Unboxing & First Impressions Campaign",
                category="Content Marketing",
                components=[
                    "Unboxing video production",
                    "Product photography suite",
                    "Reviewer guide creation",
                    "Media sample distribution",
                    "Influencer seeding strategy",
                    "First 48-hour coverage tracking",
                    "Quick start guide design",
                    "Product registration flow"
                ],
                base_hours=140,
                enterprise_multiplier=1.3,
                technical_complexity=1.1
            ),
            TechDeliverable(
                code="HW-LAUNCH-004",
                name="Comparison Guides & Benchmarks",
                category="Competitive Marketing",
                components=[
                    "Competitive analysis framework",
                    "Benchmark test suite design",
                    "Performance comparison tools",
                    "TCO calculators",
                    "Migration guides from competitors",
                    "Battle card creation",
                    "Third-party validation coordination",
                    "Industry analyst briefings"
                ],
                base_hours=180,
                enterprise_multiplier=1.6,
                technical_complexity=1.7,
                requires_engineering=True
            ),
            
            # ========== TRADE SHOW & EVENTS ==========
            TechDeliverable(
                code="HW-TRADE-001",
                name="Trade Show Booth Design (CES/Computex)",
                category="Event Marketing",
                components=[
                    "Booth concept and design",
                    "Interactive demo stations",
                    "Product display systems",
                    "AV system integration",
                    "Staff training materials",
                    "Lead capture system setup",
                    "Giveaway and swag design",
                    "Post-show follow-up campaign"
                ],
                base_hours=320,
                enterprise_multiplier=2.0,
                technical_complexity=1.3
            ),
            TechDeliverable(
                code="HW-TRADE-002",
                name="Product Demo Experience",
                category="Event Marketing",
                components=[
                    "Demo script development",
                    "Hands-on experience zones",
                    "AR/VR product demonstrations",
                    "Live benchmark demonstrations",
                    "Technical Q&A preparation",
                    "Demo failure contingencies",
                    "Remote demo capabilities",
                    "Demo analytics tracking"
                ],
                base_hours=200,
                enterprise_multiplier=1.7,
                technical_complexity=1.6,
                requires_engineering=True
            ),
            
            # ========== B2B SALES ENABLEMENT ==========
            TechDeliverable(
                code="HW-B2B-001",
                name="Enterprise Sales Enablement Kit",
                category="Sales Enablement",
                components=[
                    "Sales presentation decks",
                    "ROI calculation tools",
                    "Proof of concept frameworks",
                    "RFP response templates",
                    "Customer reference stories",
                    "Vertical market positioning",
                    "Objection handling guides",
                    "Pricing and discount matrices"
                ],
                base_hours=220,
                enterprise_multiplier=1.8,
                technical_complexity=1.5
            ),
            TechDeliverable(
                code="HW-B2B-002",
                name="Channel Partner Program",
                category="Channel Marketing",
                components=[
                    "Partner recruitment materials",
                    "Tiering and benefits structure",
                    "Partner portal development",
                    "Co-marketing templates",
                    "Deal registration system",
                    "Partner training curriculum",
                    "MDF program guidelines",
                    "Partner certification tracks"
                ],
                base_hours=280,
                enterprise_multiplier=1.9,
                technical_complexity=1.4,
                requires_certification=True
            ),
            TechDeliverable(
                code="HW-B2B-003",
                name="Technical Training & Certification",
                category="Training & Education",
                components=[
                    "Training curriculum design",
                    "Hands-on lab environments",
                    "Certification exam development",
                    "Online learning platform setup",
                    "Instructor-led training materials",
                    "Technical documentation library",
                    "Troubleshooting guides",
                    "Community forum moderation"
                ],
                base_hours=360,
                enterprise_multiplier=1.7,
                technical_complexity=1.8,
                requires_certification=True,
                requires_engineering=True
            ),
            
            # ========== HARDWARE-SPECIFIC FEATURES ==========
            TechDeliverable(
                code="HW-SUPPLY-001",
                name="Supply Chain Communications",
                category="Operations Marketing",
                components=[
                    "Availability messaging strategy",
                    "Allocation communications",
                    "Backorder management messaging",
                    "Component shortage mitigation",
                    "Lead time communications",
                    "Regional availability maps",
                    "Distributor communications",
                    "Inventory status dashboards"
                ],
                base_hours=140,
                enterprise_multiplier=1.4,
                technical_complexity=1.2
            ),
            TechDeliverable(
                code="HW-REG-001",
                name="Regulatory Approval Campaign",
                category="Compliance Marketing",
                components=[
                    "FCC/CE approval announcements",
                    "Safety certification highlights",
                    "Environmental compliance messaging",
                    "Energy efficiency ratings",
                    "Accessibility features promotion",
                    "Security certification badges",
                    "Industry standard compliance",
                    "Regional certification tracking"
                ],
                base_hours=120,
                enterprise_multiplier=1.5,
                technical_complexity=1.3,
                requires_compliance=True
            ),
            TechDeliverable(
                code="HW-GLOBAL-001",
                name="Global Market Rollout Strategy",
                category="International Marketing",
                components=[
                    "Regional launch sequencing",
                    "Localization strategy",
                    "Regional pricing models",
                    "Local partner identification",
                    "Import/export documentation",
                    "Regional PR strategy",
                    "Cultural adaptation guidelines",
                    "Multi-language support materials"
                ],
                base_hours=240,
                enterprise_multiplier=1.8,
                technical_complexity=1.4
            )
        ]
    
    def get_suggested_deliverables(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Match hardware deliverables based on keywords"""
        keywords_lower = [kw.lower() for kw in keywords]
        suggested = []
        
        keyword_map = {
            "product launch": ["HW-LAUNCH-001", "HW-LAUNCH-002", "HW-LAUNCH-003"],
            "announcement": ["HW-LAUNCH-001"],
            "keynote": ["HW-LAUNCH-001"],
            "specifications": ["HW-LAUNCH-002"],
            "specs": ["HW-LAUNCH-002"],
            "unboxing": ["HW-LAUNCH-003"],
            "benchmark": ["HW-LAUNCH-004"],
            "comparison": ["HW-LAUNCH-004"],
            "trade show": ["HW-TRADE-001", "HW-TRADE-002"],
            "ces": ["HW-TRADE-001"],
            "computex": ["HW-TRADE-001"],
            "booth": ["HW-TRADE-001"],
            "demo": ["HW-TRADE-002"],
            "b2b": ["HW-B2B-001", "HW-B2B-002"],
            "enterprise": ["HW-B2B-001"],
            "sales enablement": ["HW-B2B-001"],
            "channel": ["HW-B2B-002"],
            "partner": ["HW-B2B-002"],
            "training": ["HW-B2B-003"],
            "certification": ["HW-B2B-003"],
            "supply chain": ["HW-SUPPLY-001"],
            "regulatory": ["HW-REG-001"],
            "fcc": ["HW-REG-001"],
            "global": ["HW-GLOBAL-001"],
            "international": ["HW-GLOBAL-001"]
        }
        
        matched_codes = set()
        for keyword in keywords_lower:
            for pattern, codes in keyword_map.items():
                if pattern in keyword:
                    matched_codes.update(codes)
        
        for deliverable in self.deliverables:
            if deliverable.code in matched_codes:
                suggested.append({
                    "code": deliverable.code,
                    "name": deliverable.name,
                    "category": deliverable.category,
                    "components": deliverable.components,
                    "base_hours": deliverable.base_hours,
                    "confidence": 0.9
                })
        
        # Add core hardware deliverables if few matches
        if len(suggested) < 3:
            core_codes = ["HW-LAUNCH-001", "HW-B2B-001", "HW-TRADE-001"]
            for deliverable in self.deliverables:
                if deliverable.code in core_codes and deliverable.code not in matched_codes:
                    suggested.append({
                        "code": deliverable.code,
                        "name": deliverable.name,
                        "category": deliverable.category,
                        "components": deliverable.components,
                        "base_hours": deliverable.base_hours,
                        "confidence": 0.6
                    })
        
        return suggested[:10]  # Return top 10 matches
    
    def calculate_timeline(self, deliverable_codes: List[str], start_date: datetime) -> Dict[str, Any]:
        """Calculate hardware product launch timeline"""
        timeline = {
            "phases": [],
            "milestones": [],
            "total_duration_weeks": 0,
            "critical_dependencies": []
        }
        
        selected_deliverables = [d for d in self.deliverables if d.code in deliverable_codes]
        if not selected_deliverables:
            return timeline
        
        # Calculate duration based on complexity
        base_duration = 8  # Base 8 weeks for hardware
        
        if any("TRADE" in d.code for d in selected_deliverables):
            base_duration = max(base_duration, 16)  # Trade shows need 16 weeks
        if any("GLOBAL" in d.code for d in selected_deliverables):
            base_duration = max(base_duration, 12)  # Global rollout needs 12 weeks
        if any(d.requires_compliance for d in selected_deliverables):
            base_duration += self.timeline_adjustments["regulatory_buffer_weeks"]
        
        timeline["total_duration_weeks"] = base_duration
        
        # Generate phases
        current_date = start_date
        for phase in self.timeline_adjustments["product_launch_phases"]:
            phase_duration = int(base_duration * phase["duration_pct"])
            end_date = current_date + timedelta(weeks=phase_duration)
            
            timeline["phases"].append({
                "name": phase["name"],
                "start": current_date.isoformat(),
                "end": end_date.isoformat(),
                "duration_weeks": phase_duration
            })
            
            current_date = end_date
        
        # Add milestones
        timeline["milestones"] = [
            {"week": 1, "milestone": "Product Brief Finalization"},
            {"week": int(base_duration * 0.2), "milestone": "Regulatory Submission"},
            {"week": int(base_duration * 0.4), "milestone": "Manufacturing Start"},
            {"week": int(base_duration * 0.6), "milestone": "Channel Readiness"},
            {"week": int(base_duration * 0.8), "milestone": "Media Embargo"},
            {"week": base_duration, "milestone": "Product Launch"}
        ]
        
        # Add critical dependencies
        if any(d.requires_compliance for d in selected_deliverables):
            timeline["critical_dependencies"].append({
                "type": "Regulatory Approval",
                "lead_time_weeks": 6,
                "impact": "Cannot ship without FCC/CE approval"
            })
        
        if any("SUPPLY" in d.code for d in selected_deliverables):
            timeline["critical_dependencies"].append({
                "type": "Supply Chain",
                "lead_time_weeks": 4,
                "impact": "Component availability affects launch date"
            })
        
        return timeline
    
    def calculate_pricing(self, deliverable_codes: List[str], base_rate: float = 150) -> Dict[str, Any]:
        """Calculate hardware project pricing"""
        pricing = {
            "deliverables": [],
            "subtotal": 0,
            "adjustments": [],
            "total": 0
        }
        
        selected_deliverables = [d for d in self.deliverables if d.code in deliverable_codes]
        
        for deliverable in selected_deliverables:
            # Apply enterprise and technical complexity multipliers
            adjusted_rate = base_rate * deliverable.enterprise_multiplier * deliverable.technical_complexity
            deliverable_cost = deliverable.base_hours * adjusted_rate
            
            pricing["deliverables"].append({
                "code": deliverable.code,
                "name": deliverable.name,
                "base_hours": deliverable.base_hours,
                "rate": adjusted_rate,
                "cost": deliverable_cost
            })
            
            pricing["subtotal"] += deliverable_cost
        
        # Apply adjustments
        if any("TRADE" in d.code for d in selected_deliverables):
            trade_show_adjustment = pricing["subtotal"] * 0.3  # 30% for trade show expenses
            pricing["adjustments"].append({
                "type": "Trade Show Expenses",
                "amount": trade_show_adjustment
            })
            pricing["total"] = pricing["subtotal"] + trade_show_adjustment
        else:
            pricing["total"] = pricing["subtotal"]
        
        return pricing

# ================================================================================
# Software Technology Template (Microsoft/Adobe/Salesforce style)
# ================================================================================

class SoftwareTechTemplate:
    """Template for software technology companies"""
    
    def __init__(self):
        self.name = "Software Technology"
        self.description = "SaaS launches, developer programs, cloud solutions for software companies"
        self.deliverables = self._get_software_deliverables()
        
        # Software-specific timeline adjustments
        self.timeline_adjustments = {
            "agile_sprint_weeks": 2,
            "release_phases": [
                {"name": "Alpha/Private Preview", "duration_pct": 0.2},
                {"name": "Beta/Public Preview", "duration_pct": 0.25},
                {"name": "Release Candidate", "duration_pct": 0.15},
                {"name": "General Availability", "duration_pct": 0.2},
                {"name": "Post-Launch Adoption", "duration_pct": 0.2}
            ],
            "continuous_deployment": True
        }
        
        # Software pricing multipliers
        self.pricing_multipliers = {
            "base_rate_multiplier": 1.5,
            "enterprise_saas_multiplier": 1.8,
            "developer_program_multiplier": 1.6,
            "security_compliance_multiplier": 1.7,
            "api_documentation_multiplier": 1.4
        }
    
    def _get_software_deliverables(self) -> List[TechDeliverable]:
        """Return comprehensive list of software tech deliverables"""
        return [
            # ========== SOFTWARE LAUNCH DELIVERABLES ==========
            TechDeliverable(
                code="SW-LAUNCH-001",
                name="Feature Release Campaign",
                category="Product Launch",
                components=[
                    "Release notes and changelog",
                    "Feature announcement blog posts",
                    "Product demo videos",
                    "What's new documentation",
                    "Email announcement sequence",
                    "In-app notification design",
                    "Social media rollout",
                    "Press release and media kit"
                ],
                base_hours=160,
                enterprise_multiplier=1.5,
                technical_complexity=1.3
            ),
            TechDeliverable(
                code="SW-LAUNCH-002",
                name="Developer Documentation & APIs",
                category="Developer Resources",
                components=[
                    "API reference documentation",
                    "SDK development and packaging",
                    "Code samples and tutorials",
                    "Interactive API explorer",
                    "Integration guides",
                    "Postman collections",
                    "OpenAPI specifications",
                    "Developer changelog"
                ],
                base_hours=280,
                enterprise_multiplier=1.7,
                technical_complexity=1.9,
                requires_engineering=True
            ),
            TechDeliverable(
                code="SW-LAUNCH-003",
                name="SaaS Onboarding Flow",
                category="User Experience",
                components=[
                    "Signup flow optimization",
                    "Interactive product tour",
                    "Onboarding email sequence",
                    "Setup wizard design",
                    "Sample data provisioning",
                    "Quick start guides",
                    "Video walkthroughs",
                    "Success metrics dashboard"
                ],
                base_hours=200,
                enterprise_multiplier=1.6,
                technical_complexity=1.4
            ),
            TechDeliverable(
                code="SW-LAUNCH-004",
                name="Free Trial Campaign",
                category="Growth Marketing",
                components=[
                    "Trial landing page design",
                    "Trial-to-paid conversion flow",
                    "Feature limitation strategy",
                    "Trial extension workflows",
                    "Nurture email campaigns",
                    "In-trial engagement tracking",
                    "Upgrade prompts and CTAs",
                    "Trial success metrics"
                ],
                base_hours=180,
                enterprise_multiplier=1.5,
                technical_complexity=1.2
            ),
            
            # ========== DEVELOPER ECOSYSTEM ==========
            TechDeliverable(
                code="SW-DEV-001",
                name="Developer Community Building",
                category="Developer Relations",
                components=[
                    "Developer portal creation",
                    "Community forum setup",
                    "Discord/Slack community management",
                    "Developer newsletter",
                    "Code contribution guidelines",
                    "Open source strategy",
                    "Hackathon organization",
                    "Developer recognition program"
                ],
                base_hours=240,
                enterprise_multiplier=1.6,
                technical_complexity=1.3
            ),
            TechDeliverable(
                code="SW-DEV-002",
                name="Beta Testing Program",
                category="Product Development",
                components=[
                    "Beta recruitment campaign",
                    "NDA and legal framework",
                    "Beta feedback portal",
                    "Testing scenarios and scripts",
                    "Bug reporting workflows",
                    "Beta community management",
                    "Feature voting system",
                    "Beta-to-GA transition plan"
                ],
                base_hours=200,
                enterprise_multiplier=1.4,
                technical_complexity=1.5,
                requires_engineering=True
            ),
            TechDeliverable(
                code="SW-DEV-003",
                name="Developer Evangelism Program",
                category="Developer Relations",
                components=[
                    "Technical blog content calendar",
                    "Conference speaking proposals",
                    "Workshop and training materials",
                    "YouTube channel content",
                    "Twitch streaming setup",
                    "Developer advocate toolkit",
                    "Community meetup sponsorship",
                    "Developer survey and insights"
                ],
                base_hours=320,
                enterprise_multiplier=1.7,
                technical_complexity=1.4
            ),
            
            # ========== WEBINARS & DEMOS ==========
            TechDeliverable(
                code="SW-DEMO-001",
                name="Webinar Series Program",
                category="Demand Generation",
                components=[
                    "Webinar topic calendar",
                    "Registration landing pages",
                    "Webinar platform setup",
                    "Presentation deck templates",
                    "Demo environment preparation",
                    "Q&A moderation guidelines",
                    "Follow-up email sequences",
                    "Recording distribution strategy"
                ],
                base_hours=160,
                enterprise_multiplier=1.4,
                technical_complexity=1.2
            ),
            TechDeliverable(
                code="SW-DEMO-002",
                name="Interactive Demo Experience",
                category="Sales Enablement",
                components=[
                    "Sandbox environment setup",
                    "Guided demo scenarios",
                    "Self-service demo portal",
                    "Demo data management",
                    "Feature tour creation",
                    "ROI calculator integration",
                    "Demo analytics tracking",
                    "Lead scoring integration"
                ],
                base_hours=220,
                enterprise_multiplier=1.6,
                technical_complexity=1.6,
                requires_engineering=True
            ),
            
            # ========== PARTNER ECOSYSTEM ==========
            TechDeliverable(
                code="SW-PARTNER-001",
                name="Integration Partner Program",
                category="Partner Marketing",
                components=[
                    "Partner API documentation",
                    "Integration marketplace listing",
                    "Co-marketing agreements",
                    "Partner certification program",
                    "Joint solution briefs",
                    "Partner portal development",
                    "Revenue sharing models",
                    "Partner success metrics"
                ],
                base_hours=260,
                enterprise_multiplier=1.8,
                technical_complexity=1.5,
                requires_certification=True
            ),
            TechDeliverable(
                code="SW-PARTNER-002",
                name="Technology Alliance Program",
                category="Strategic Partnerships",
                components=[
                    "Strategic partner identification",
                    "Joint value proposition",
                    "Reference architecture design",
                    "Co-innovation roadmap",
                    "Joint customer success stories",
                    "Partner summit planning",
                    "Executive briefing materials",
                    "Partnership announcements"
                ],
                base_hours=280,
                enterprise_multiplier=1.9,
                technical_complexity=1.4
            ),
            
            # ========== CUSTOMER SUCCESS ==========
            TechDeliverable(
                code="SW-SUCCESS-001",
                name="Customer Success Story Campaign",
                category="Content Marketing",
                components=[
                    "Customer interview process",
                    "Case study development",
                    "Video testimonial production",
                    "ROI analysis documentation",
                    "Success metrics visualization",
                    "Industry-specific versions",
                    "Sales enablement packaging",
                    "Website showcase section"
                ],
                base_hours=180,
                enterprise_multiplier=1.5,
                technical_complexity=1.1
            ),
            TechDeliverable(
                code="SW-SUCCESS-002",
                name="User Conference Planning",
                category="Event Marketing",
                components=[
                    "Conference theme and agenda",
                    "Keynote content development",
                    "Breakout session planning",
                    "Hands-on lab design",
                    "Certification programs",
                    "Partner expo coordination",
                    "Virtual attendance options",
                    "Post-event content package"
                ],
                base_hours=400,
                enterprise_multiplier=2.0,
                technical_complexity=1.3
            ),
            
            # ========== SOFTWARE-SPECIFIC FEATURES ==========
            TechDeliverable(
                code="SW-AGILE-001",
                name="Agile Release Communications",
                category="Product Marketing",
                components=[
                    "Sprint release notes",
                    "Feature flag documentation",
                    "Continuous deployment updates",
                    "Breaking change notifications",
                    "Deprecation timelines",
                    "Version migration guides",
                    "Rollback procedures",
                    "Release calendar maintenance"
                ],
                base_hours=140,
                enterprise_multiplier=1.4,
                technical_complexity=1.5,
                requires_engineering=True
            ),
            TechDeliverable(
                code="SW-CLOUD-001",
                name="Cloud Migration Campaign",
                category="Cloud Solutions",
                components=[
                    "Migration assessment tools",
                    "TCO analysis calculators",
                    "Migration playbooks",
                    "Architecture blueprints",
                    "Security compliance guides",
                    "Performance benchmarks",
                    "Disaster recovery planning",
                    "Multi-cloud strategy content"
                ],
                base_hours=240,
                enterprise_multiplier=1.8,
                technical_complexity=1.7,
                requires_compliance=True
            ),
            TechDeliverable(
                code="SW-SECURITY-001",
                name="Security & Compliance Messaging",
                category="Trust & Security",
                components=[
                    "Security white papers",
                    "Compliance certifications display",
                    "Vulnerability disclosure program",
                    "Security incident communications",
                    "Data privacy documentation",
                    "GDPR/CCPA compliance guides",
                    "SOC2/ISO certification materials",
                    "Security best practices content"
                ],
                base_hours=200,
                enterprise_multiplier=1.7,
                technical_complexity=1.6,
                requires_compliance=True
            ),
            TechDeliverable(
                code="SW-AI-001",
                name="AI/ML Feature Launch",
                category="Innovation Marketing",
                components=[
                    "AI capability demonstrations",
                    "Model transparency documentation",
                    "Ethical AI guidelines",
                    "Use case galleries",
                    "Performance metrics dashboards",
                    "API documentation for AI features",
                    "Training data specifications",
                    "Bias mitigation strategies"
                ],
                base_hours=260,
                enterprise_multiplier=1.9,
                technical_complexity=1.8,
                requires_engineering=True
            )
        ]
    
    def get_suggested_deliverables(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Match software deliverables based on keywords"""
        keywords_lower = [kw.lower() for kw in keywords]
        suggested = []
        
        keyword_map = {
            "feature": ["SW-LAUNCH-001", "SW-AGILE-001"],
            "release": ["SW-LAUNCH-001", "SW-AGILE-001"],
            "api": ["SW-LAUNCH-002", "SW-AI-001"],
            "developer": ["SW-LAUNCH-002", "SW-DEV-001", "SW-DEV-003"],
            "documentation": ["SW-LAUNCH-002"],
            "onboarding": ["SW-LAUNCH-003"],
            "saas": ["SW-LAUNCH-003", "SW-LAUNCH-004"],
            "trial": ["SW-LAUNCH-004"],
            "free": ["SW-LAUNCH-004"],
            "community": ["SW-DEV-001"],
            "beta": ["SW-DEV-002"],
            "testing": ["SW-DEV-002"],
            "evangelism": ["SW-DEV-003"],
            "webinar": ["SW-DEMO-001"],
            "demo": ["SW-DEMO-002"],
            "integration": ["SW-PARTNER-001"],
            "partner": ["SW-PARTNER-001", "SW-PARTNER-002"],
            "alliance": ["SW-PARTNER-002"],
            "customer success": ["SW-SUCCESS-001"],
            "case study": ["SW-SUCCESS-001"],
            "conference": ["SW-SUCCESS-002"],
            "agile": ["SW-AGILE-001"],
            "cloud": ["SW-CLOUD-001"],
            "migration": ["SW-CLOUD-001"],
            "security": ["SW-SECURITY-001"],
            "compliance": ["SW-SECURITY-001"],
            "ai": ["SW-AI-001"],
            "ml": ["SW-AI-001"],
            "machine learning": ["SW-AI-001"]
        }
        
        matched_codes = set()
        for keyword in keywords_lower:
            for pattern, codes in keyword_map.items():
                if pattern in keyword:
                    matched_codes.update(codes)
        
        for deliverable in self.deliverables:
            if deliverable.code in matched_codes:
                suggested.append({
                    "code": deliverable.code,
                    "name": deliverable.name,
                    "category": deliverable.category,
                    "components": deliverable.components,
                    "base_hours": deliverable.base_hours,
                    "confidence": 0.9
                })
        
        # Add core software deliverables if few matches
        if len(suggested) < 3:
            core_codes = ["SW-LAUNCH-001", "SW-LAUNCH-003", "SW-DEV-001"]
            for deliverable in self.deliverables:
                if deliverable.code in core_codes and deliverable.code not in matched_codes:
                    suggested.append({
                        "code": deliverable.code,
                        "name": deliverable.name,
                        "category": deliverable.category,
                        "components": deliverable.components,
                        "base_hours": deliverable.base_hours,
                        "confidence": 0.6
                    })
        
        return suggested[:10]
    
    def calculate_timeline(self, deliverable_codes: List[str], start_date: datetime) -> Dict[str, Any]:
        """Calculate software release timeline"""
        timeline = {
            "phases": [],
            "milestones": [],
            "total_duration_weeks": 0,
            "sprint_schedule": []
        }
        
        selected_deliverables = [d for d in self.deliverables if d.code in deliverable_codes]
        if not selected_deliverables:
            return timeline
        
        # Calculate duration based on agile sprints
        base_sprints = 3  # Minimum 3 sprints
        
        if any("CLOUD" in d.code for d in selected_deliverables):
            base_sprints = max(base_sprints, 6)  # Cloud migration needs 6 sprints
        if any("CONFERENCE" in d.code or "SUCCESS-002" in d.code for d in selected_deliverables):
            base_sprints = max(base_sprints, 8)  # Conference needs 8 sprints
        if any(d.requires_compliance for d in selected_deliverables):
            base_sprints += 2  # Add 2 sprints for compliance
        
        sprint_weeks = self.timeline_adjustments["agile_sprint_weeks"]
        total_weeks = base_sprints * sprint_weeks
        timeline["total_duration_weeks"] = total_weeks
        
        # Generate phases
        current_date = start_date
        for phase in self.timeline_adjustments["release_phases"]:
            phase_duration = int(total_weeks * phase["duration_pct"])
            end_date = current_date + timedelta(weeks=phase_duration)
            
            timeline["phases"].append({
                "name": phase["name"],
                "start": current_date.isoformat(),
                "end": end_date.isoformat(),
                "duration_weeks": phase_duration
            })
            
            current_date = end_date
        
        # Add sprint schedule
        for sprint_num in range(1, base_sprints + 1):
            sprint_start = start_date + timedelta(weeks=(sprint_num - 1) * sprint_weeks)
            sprint_end = sprint_start + timedelta(weeks=sprint_weeks)
            
            timeline["sprint_schedule"].append({
                "sprint": sprint_num,
                "start": sprint_start.isoformat(),
                "end": sprint_end.isoformat()
            })
        
        # Add milestones
        timeline["milestones"] = [
            {"week": 1, "milestone": "Kickoff & Requirements"},
            {"week": sprint_weeks, "milestone": "Alpha Release"},
            {"week": sprint_weeks * 2, "milestone": "Beta Launch"},
            {"week": int(total_weeks * 0.6), "milestone": "Release Candidate"},
            {"week": int(total_weeks * 0.8), "milestone": "Documentation Complete"},
            {"week": total_weeks, "milestone": "General Availability"}
        ]
        
        return timeline
    
    def calculate_pricing(self, deliverable_codes: List[str], base_rate: float = 150) -> Dict[str, Any]:
        """Calculate software project pricing"""
        pricing = {
            "deliverables": [],
            "subtotal": 0,
            "adjustments": [],
            "total": 0
        }
        
        selected_deliverables = [d for d in self.deliverables if d.code in deliverable_codes]
        
        for deliverable in selected_deliverables:
            # Apply enterprise and technical complexity multipliers
            adjusted_rate = base_rate * deliverable.enterprise_multiplier * deliverable.technical_complexity
            deliverable_cost = deliverable.base_hours * adjusted_rate
            
            pricing["deliverables"].append({
                "code": deliverable.code,
                "name": deliverable.name,
                "base_hours": deliverable.base_hours,
                "rate": adjusted_rate,
                "cost": deliverable_cost
            })
            
            pricing["subtotal"] += deliverable_cost
        
        # Apply adjustments
        adjustments_total = 0
        
        # Cloud infrastructure costs
        if any("CLOUD" in d.code for d in selected_deliverables):
            cloud_adjustment = pricing["subtotal"] * 0.2  # 20% for cloud infrastructure
            pricing["adjustments"].append({
                "type": "Cloud Infrastructure",
                "amount": cloud_adjustment
            })
            adjustments_total += cloud_adjustment
        
        # Developer tools and platforms
        if any(d.requires_engineering for d in selected_deliverables):
            tools_adjustment = pricing["subtotal"] * 0.15  # 15% for dev tools
            pricing["adjustments"].append({
                "type": "Developer Tools & Platforms",
                "amount": tools_adjustment
            })
            adjustments_total += tools_adjustment
        
        pricing["total"] = pricing["subtotal"] + adjustments_total
        
        return pricing

# ================================================================================
# Technology Template Wrapper Class
# ================================================================================

class TechnologyTemplate:
    """Main technology template that provides access to both hardware and software sub-templates"""
    
    def __init__(self):
        self.hardware = HardwareTechTemplate()
        self.software = SoftwareTechTemplate()
        self.name = "Technology"
        self.description = "Comprehensive technology industry templates for hardware and software companies"
    
    def get_suggested_deliverables(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Get suggested deliverables from both hardware and software templates"""
        keywords_lower = [kw.lower() for kw in keywords]
        
        # Determine which sub-template to use based on keywords
        hardware_indicators = ["hardware", "device", "product", "manufacturing", "supply chain", 
                               "trade show", "ces", "computex", "benchmark", "specs"]
        software_indicators = ["software", "saas", "cloud", "api", "developer", "agile", 
                               "beta", "subscription", "webinar", "integration"]
        
        hardware_score = sum(1 for kw in keywords_lower for indicator in hardware_indicators if indicator in kw)
        software_score = sum(1 for kw in keywords_lower for indicator in software_indicators if indicator in kw)
        
        # Get suggestions from appropriate template(s)
        if hardware_score > software_score:
            return self.hardware.get_suggested_deliverables(keywords)
        elif software_score > hardware_score:
            return self.software.get_suggested_deliverables(keywords)
        else:
            # Combine suggestions from both if unclear
            hw_suggestions = self.hardware.get_suggested_deliverables(keywords)
            sw_suggestions = self.software.get_suggested_deliverables(keywords)
            
            # Merge and deduplicate
            combined = hw_suggestions + sw_suggestions
            seen = set()
            unique = []
            for item in combined:
                if item["code"] not in seen:
                    seen.add(item["code"])
                    unique.append(item)
            
            # Sort by confidence and return top results
            unique.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
            return unique[:10]
    
    def calculate_timeline(self, deliverable_codes: List[str], start_date: datetime) -> Dict[str, Any]:
        """Calculate timeline based on deliverable types"""
        # Determine which template to use based on deliverable codes
        hardware_codes = [code for code in deliverable_codes if code.startswith("HW-")]
        software_codes = [code for code in deliverable_codes if code.startswith("SW-")]
        
        if hardware_codes and not software_codes:
            return self.hardware.calculate_timeline(hardware_codes, start_date)
        elif software_codes and not hardware_codes:
            return self.software.calculate_timeline(software_codes, start_date)
        else:
            # Mixed project - use longer timeline
            hw_timeline = self.hardware.calculate_timeline(hardware_codes, start_date) if hardware_codes else {"total_duration_weeks": 0}
            sw_timeline = self.software.calculate_timeline(software_codes, start_date) if software_codes else {"total_duration_weeks": 0}
            
            # Return the longer timeline
            if hw_timeline["total_duration_weeks"] >= sw_timeline["total_duration_weeks"]:
                return hw_timeline
            else:
                return sw_timeline
    
    def calculate_pricing(self, deliverable_codes: List[str], base_rate: float = 150) -> Dict[str, Any]:
        """Calculate combined pricing for mixed projects"""
        hardware_codes = [code for code in deliverable_codes if code.startswith("HW-")]
        software_codes = [code for code in deliverable_codes if code.startswith("SW-")]
        
        if hardware_codes and not software_codes:
            return self.hardware.calculate_pricing(hardware_codes, base_rate)
        elif software_codes and not hardware_codes:
            return self.software.calculate_pricing(software_codes, base_rate)
        else:
            # Mixed project - combine pricing
            hw_pricing = self.hardware.calculate_pricing(hardware_codes, base_rate) if hardware_codes else {"total": 0, "deliverables": []}
            sw_pricing = self.software.calculate_pricing(software_codes, base_rate) if software_codes else {"total": 0, "deliverables": []}
            
            combined = {
                "deliverables": hw_pricing["deliverables"] + sw_pricing["deliverables"],
                "subtotal": hw_pricing.get("subtotal", 0) + sw_pricing.get("subtotal", 0),
                "adjustments": hw_pricing.get("adjustments", []) + sw_pricing.get("adjustments", []),
                "total": hw_pricing["total"] + sw_pricing["total"]
            }
            
            return combined

# ================================================================================
# Export Functions for API Integration
# ================================================================================

def get_tech_template():
    """Get the technology template instance"""
    return TechnologyTemplate()

# For backward compatibility with existing template system
def get_industry_template(industry: str):
    """Get template by industry name"""
    if industry.lower() in ["technology", "tech"]:
        return TechnologyTemplate()
    return None

def get_available_industries():
    """Get list of available industries"""
    return ["technology"]