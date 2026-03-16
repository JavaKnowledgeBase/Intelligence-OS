import { SectionTitle } from "../components/SectionTitle";
import {
  architectureFlows,
  architectureLayers,
  securityPrinciples,
} from "../data/architectureData";

export function ArchitecturePage() {
  return (
    <main className="content architecture-content">
      <section className="glass-card architecture-hero">
        <SectionTitle
          eyebrow="Platform blueprint"
          title="Enterprise architecture built into the template"
          description="This page borrows the polished PolicyMind information style, but all markup and assets now live locally inside Torilaure."
        />
        <div className="architecture-flow-grid">
          {architectureFlows.map((flow) => (
            <div key={flow} className="flow-chip">
              {flow}
            </div>
          ))}
        </div>
      </section>

      <section className="architecture-grid">
        {architectureLayers.map((layer) => (
          <article key={layer.title} className="glass-card architecture-card">
            <span className="panel-label">{layer.title}</span>
            <p className="architecture-copy">{layer.description}</p>
            <ul className="architecture-list">
              {layer.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        ))}
      </section>

      <section className="split-panel">
        <div className="glass-card">
          <SectionTitle
            eyebrow="Security"
            title="Enterprise controls"
            description="The visual system and architecture layer now communicate a real production direction instead of a demo-only landing page."
          />
          <ul className="workflow-list">
            {securityPrinciples.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="glass-card">
          <SectionTitle
            eyebrow="Deployment"
            title="Scalable by design"
            description="Frontend, core APIs, and future intelligence services are already framed as separate but coordinated layers."
          />
          <div className="architecture-stat-stack">
            <div>
              <strong>Gateway-first architecture</strong>
              <p>Supports auth, policy, and service expansion without rewriting the experience layer.</p>
            </div>
            <div>
              <strong>Service-ready UI shell</strong>
              <p>Forecasting, valuation, scoring, and retrieval can plug in as the backend matures.</p>
            </div>
            <div>
              <strong>Shared design language</strong>
              <p>Torilaure now has an enterprise look from the first template, not just after later polish passes.</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

