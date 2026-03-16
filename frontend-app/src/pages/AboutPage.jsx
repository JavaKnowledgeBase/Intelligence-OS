import { SectionTitle } from "../components/SectionTitle";

const documentationCards = [
  {
    title: "Project Setup Reference",
    description: "Snapshot of the current scaffold, created files, frameworks, libraries, and import structure.",
    path: "docs/project-setup-reference.md",
  },
  {
    title: "OAuth Setup Reference",
    description: "Forward plan for Microsoft OAuth, planned files, imports, environment variables, and class diagram.",
    path: "docs/oauth-setup-reference.md",
  },
  {
    title: "Architecture Snapshot",
    description: "Platform direction, service map, data targets, and enterprise platform intent.",
    path: "docs/architecture.md",
  },
  {
    title: "Security Baseline",
    description: "OWASP-aligned baseline, secure development direction, and controls checklist.",
    path: "docs/security-baseline.md",
  },
];

const platformFacts = [
  "React + Vite frontend with routed enterprise UI shell",
  "FastAPI backend with JWT auth, refresh rotation, and protected APIs",
  "PostgreSQL-backed domain models managed through Alembic migrations",
  "Redis-backed rate limiting and shared session persistence",
  "Local ingestion pipeline with durable run history and source-aware upserts",
];

export function AboutPage() {
  return (
    <main className="content about-content">
      <section className="glass-card architecture-hero">
        <SectionTitle
          eyebrow="About"
          title="Torilaure Intelligence OS foundation"
          description="This page gives us a clean place to keep project context, document references, and platform direction visible inside the app while the product keeps growing."
        />
        <div className="architecture-flow-grid">
          <div className="flow-chip">Enterprise UI shell</div>
          <div className="flow-chip">JWT + Redis sessions</div>
          <div className="flow-chip">PostgreSQL domain model</div>
          <div className="flow-chip">Alembic migrations</div>
          <div className="flow-chip">Local ingestion pipeline</div>
        </div>
      </section>

      <section className="split-panel about-panel">
        <div className="glass-card">
          <SectionTitle
            eyebrow="Status"
            title="What is already in place"
            description="The scaffold is past template stage. It already carries the main product shell, security baseline, data model direction, and developer documentation."
          />
          <ul className="workflow-list">
            {platformFacts.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="glass-card">
          <SectionTitle
            eyebrow="Next"
            title="What comes later"
            description="The About page can later host final documentation links, onboarding notes, release summaries, and deeper platform reference material."
          />
          <div className="architecture-stat-stack">
            <div>
              <strong>Docs links</strong>
              <p>We can swap these repo-path references to proper app or GitHub links when the final About experience is ready.</p>
            </div>
            <div>
              <strong>OAuth completion</strong>
              <p>Microsoft sign-in can plug into the existing auth/session layer near the end of the build sequence.</p>
            </div>
            <div>
              <strong>Connector growth</strong>
              <p>Broker feeds, CRM exports, and market providers can extend the ingestion model already in place.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="about-doc-grid">
        {documentationCards.map((card) => (
          <article key={card.title} className="glass-card about-doc-card">
            <span className="panel-label">Documentation</span>
            <h3>{card.title}</h3>
            <p>{card.description}</p>
            <div className="about-doc-path">
              <strong>Repo path</strong>
              <code>{card.path}</code>
            </div>
          </article>
        ))}
      </section>

    </main>
  );
}
