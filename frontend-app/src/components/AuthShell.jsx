import { WisdomTicker } from "./WisdomTicker";

// Reusable auth shell so sign-in, account creation, and future OAuth screens share one enterprise layout.
export function AuthShell({ title, modeAction, children, footer }) {
  return (
    <main className="content login-content">
      <section className="login-shell">
        <div className="login-panel login-panel-brand">
          <p className="eyebrow">Secure enterprise access</p>
          <h2>Welcome back to your investment command center, your return on investment advisor.</h2>
          <div className="highlight-strip">
            <div className="highlight-card">
              <strong>Shared project model</strong>
              <span>Retail, valuation, and ROI packs plug into one governed workspace.</span>
            </div>
            <div className="highlight-card">
              <strong>Evidence-backed insights</strong>
              <span>Deal ranking, market signals, and ROI logic stay aligned under one experience layer.</span>
            </div>
          </div>
          <div className="pill-row">
            <span className="pill">Investor</span>
            <span className="pill">Analyst</span>
            <span className="pill">Operator</span>
            <span className="pill">Admin</span>
          </div>
          <WisdomTicker />
        </div>

        <div className="login-panel login-panel-form">
          <p className="panel-label">Developer: Ravi Kafley</p>
          <div className="login-mode-header">
            <h3>{title}</h3>
            {modeAction}
          </div>
          {children}
          {footer}
        </div>
      </section>
    </main>
  );
}
