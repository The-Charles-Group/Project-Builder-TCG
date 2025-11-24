import type { ScopeSummary } from './models';

// ============================================================================
// Seed data matching the screenshot reference
// St. Regis Nashville RFP Scope
// ============================================================================

export const seedData: ScopeSummary = {
  title: "RFP Scope for St. Regis Hotel & Residences Nashville",
  channels: ["Digital"],
  markets: ["US"],
  complexity: "Medium",
  totalPlannedHours: 4012,
  modules: [
    {
      id: "brand-strategy",
      title: "Brand Strategy",
      valueStatement: "Define positioning and masterbrand for hotel & residences.",
      effort: { size: "L", hoursMin: 600, hoursMax: 800 },
      outputs: [
        { id: "pos", label: "Positioning" },
        { id: "masterbrand", label: "Masterbrand system" },
        { id: "messaging", label: "Messaging" },
      ],
      activities: [
        "Define market positioning across hospitality and branded residential.",
        "Create dual masterbrand system reflecting tower architecture/interiors.",
        "Produce content/specs and partner oversight for install/operations.",
      ],
      risks: ["Stakeholder alignment across multiple partners"],
      assumptions: ["Access to architectural plans and interior specs"],
      dependencies: [{ id: "campaign-creative", type: "feeds" }],
      roles: [
        { role: "Strategist", seniority: "Sr", hours: 400 },
        { role: "Account Manager", seniority: "Mid", hours: 200 },
      ],
      phase: "Discovery",
    },
    {
      id: "brand-identity",
      title: "Brand Identity",
      valueStatement: "Design visual system including logo, color, typography.",
      effort: { size: "L", hoursMin: 500, hoursMax: 700 },
      outputs: [
        { id: "logo", label: "Logo System" },
        { id: "color", label: "Color Palette" },
        { id: "typography", label: "Typography" },
        { id: "graphics", label: "Graphic Elements" },
      ],
      activities: [
        "Develop logo explorations (6-8 directions).",
        "Create comprehensive color palette with accessibility guidelines.",
        "Establish typography system for print and digital.",
        "Design supporting graphic elements and patterns.",
      ],
      risks: ["Client creative direction shifts", "Print production timeline"],
      assumptions: ["Two rounds of revisions included"],
      dependencies: [
        { id: "brand-strategy", type: "needs" },
        { id: "collateral", type: "feeds" },
      ],
      roles: [
        { role: "Creative Director", seniority: "Sr", hours: 200 },
        { role: "Designer", seniority: "Mid", hours: 400 },
      ],
      phase: "Concept",
    },
    {
      id: "brand-architecture",
      title: "Brand Architecture & Naming",
      valueStatement: "Develop naming system and brand hierarchy.",
      effort: { size: "M", hoursMin: 200, hoursMax: 300 },
      outputs: [
        { id: "architecture", label: "Brand Architecture" },
        { id: "naming", label: "Naming System" },
      ],
      activities: [
        "Map brand relationship between hotel and residences.",
        "Create naming conventions for sub-brands and offerings.",
        "Conduct trademark screening for key names.",
      ],
      assumptions: ["Legal review handled by client"],
      dependencies: [{ id: "brand-strategy", type: "needs" }],
      roles: [
        { role: "Strategist", seniority: "Sr", hours: 150 },
        { role: "Copywriter", seniority: "Mid", hours: 100 },
      ],
      phase: "Discovery",
    },
    {
      id: "experiential-activation",
      title: "Experiential Activation",
      valueStatement: "Design signature experiences for launch and ongoing.",
      effort: { size: "M", hoursMin: 300, hoursMax: 400 },
      outputs: [
        { id: "launch-event", label: "Launch Event Concept" },
        { id: "resident-events", label: "Resident Event Series" },
      ],
      activities: [
        "Conceptualize grand opening event experience.",
        "Design quarterly resident engagement program.",
        "Develop activation playbook for operations team.",
      ],
      risks: ["Venue availability", "Budget constraints"],
      roles: [
        { role: "Experience Designer", seniority: "Mid", hours: 200 },
        { role: "Project Manager", seniority: "Mid", hours: 100 },
      ],
      phase: "Concept",
    },
    {
      id: "campaign-creative",
      title: "Campaign Creative",
      valueStatement: "Create launch campaign assets across channels.",
      effort: { size: "L", hoursMin: 600, hoursMax: 900 },
      outputs: [
        { id: "digital-ads", label: "Digital Ad Suite" },
        { id: "print-ads", label: "Print Advertising" },
        { id: "ooh", label: "Out-of-Home" },
        { id: "social", label: "Social Media Templates" },
      ],
      activities: [
        "Develop campaign concept and messaging platform.",
        "Design display ads (awareness, consideration, conversion).",
        "Create print ads for luxury publications.",
        "Design billboard and transit advertising.",
        "Build social media template library.",
      ],
      risks: ["Media buy timeline", "Creative approval delays"],
      assumptions: ["Asset specs provided by media agency"],
      dependencies: [
        { id: "brand-identity", type: "needs" },
        { id: "content-production", type: "feeds" },
      ],
      roles: [
        { role: "Art Director", seniority: "Sr", hours: 300 },
        { role: "Copywriter", seniority: "Sr", hours: 200 },
        { role: "Designer", seniority: "Mid", hours: 300 },
      ],
      phase: "Production",
    },
    {
      id: "content-production",
      title: "Content Production (Video/Audio/Stills)",
      valueStatement: "Produce hero content for all marketing touchpoints.",
      effort: { size: "L", hoursMin: 800, hoursMax: 1200 },
      outputs: [
        { id: "hero-video", label: "Hero Brand Film (60s)" },
        { id: "property-photos", label: "Property Photography" },
        { id: "lifestyle-photos", label: "Lifestyle Photography" },
        { id: "audio", label: "Audio Branding" },
      ],
      activities: [
        "Produce cinematic brand film showcasing property and lifestyle.",
        "Conduct professional photography shoot (interiors, amenities, lifestyle).",
        "Create audio signature and sonic branding elements.",
        "Deliver assets in all required formats and specifications.",
      ],
      risks: ["Weather dependencies", "Talent availability", "Production delays"],
      assumptions: ["Location access provided", "Two shoot days"],
      dependencies: [{ id: "campaign-creative", type: "needs" }],
      roles: [
        { role: "Producer", seniority: "Sr", hours: 400 },
        { role: "Creative Director", seniority: "Sr", hours: 200 },
      ],
      phase: "Production",
    },
    {
      id: "collateral",
      title: "Marketing Collateral & Sales Tools",
      valueStatement: "Design sales materials and resident communications.",
      effort: { size: "M", hoursMin: 400, hoursMax: 600 },
      outputs: [
        { id: "brochure", label: "Sales Brochure" },
        { id: "amenity-guide", label: "Amenity Guide" },
        { id: "signage", label: "Wayfinding Signage" },
        { id: "stationery", label: "Branded Stationery" },
      ],
      activities: [
        "Design premium sales brochure (32-40 pages).",
        "Create resident amenity guide and welcome materials.",
        "Develop wayfinding signage system.",
        "Design branded stationery suite (letterhead, cards, envelopes).",
      ],
      risks: ["Print production timeline"],
      assumptions: ["Content provided by client"],
      dependencies: [{ id: "brand-identity", type: "needs" }],
      roles: [
        { role: "Designer", seniority: "Mid", hours: 400 },
        { role: "Production Manager", seniority: "Mid", hours: 100 },
      ],
      phase: "Production",
    },
    {
      id: "program-management",
      title: "Program Management & Timeline",
      valueStatement: "Oversee project delivery and stakeholder coordination.",
      effort: { size: "M", hoursMin: 300, hoursMax: 400 },
      outputs: [
        { id: "project-plan", label: "Master Project Plan" },
        { id: "status-reports", label: "Status Reports" },
      ],
      activities: [
        "Create master timeline with all dependencies.",
        "Coordinate weekly status meetings with stakeholders.",
        "Manage vendor relationships and approvals.",
        "Track budgets and deliverable milestones.",
      ],
      assumptions: ["Weekly touchpoints with client team"],
      roles: [
        { role: "Project Manager", seniority: "Sr", hours: 300 },
      ],
      phase: "Discovery",
    },
  ],
};
