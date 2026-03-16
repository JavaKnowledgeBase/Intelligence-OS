// Developer: Ravi Kafley
// Structured architecture content for the enterprise design page.
export const architectureLayers = [
  {
    title: "Experience Layer",
    description: "Enterprise user surfaces for investors, analysts, operators, and executives.",
    items: ["Investor dashboard", "Architecture workspace", "Admin console", "Embedded APIs"],
  },
  {
    title: "Identity and Gateway",
    description: "The secure entry point for login, API access, and tenant-aware controls.",
    items: ["JWT authentication", "OAuth integrations", "API gateway", "Role-based access"],
  },
  {
    title: "Platform Core",
    description: "Shared product services that every future solution pack can reuse.",
    items: ["Project service", "Deal ingestion", "ROI analytics", "Search and retrieval", "Alerts"],
  },
  {
    title: "Intelligence Services",
    description: "Deeper pack-specific services for ranking, valuation, retail, and ROI analysis.",
    items: ["AI scoring", "Forecasting", "Valuation service", "Scenario analysis"],
  },
  {
    title: "Data and Infrastructure",
    description: "Production-minded persistence, cache, storage, and deployment layers.",
    items: ["PostgreSQL", "Redis", "Object storage", "Vector store", "Kubernetes"],
  },
];

export const architectureFlows = [
  "External feeds -> ingestion workers -> deal service",
  "Deal service -> ROI engine -> AI scoring service",
  "AI scoring -> search index -> investor dashboard",
  "User query -> embeddings -> vector search -> LLM explanation",
];

export const securityPrinciples = [
  "Zero trust architecture across every service boundary",
  "JWT and OAuth-ready sign-in flow from day one",
  "TLS, audit logging, and rate limiting as platform defaults",
  "Independent scaling across UI, APIs, workers, and intelligence services",
];

