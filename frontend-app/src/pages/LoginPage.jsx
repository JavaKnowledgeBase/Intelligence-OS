import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { setSession } from "../auth";
import { loginWithPassword } from "../api/authClient";
import { WisdomTicker } from "../components/WisdomTicker";

export function LoginPage({ onLogin }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("ravi@torilaure.com");
  const [password, setPassword] = useState("Torilaure123!");
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorMessage("");

    if (!email.trim() || !password.trim()) {
      setErrorMessage("Enter your email and password to continue.");
      return;
    }

    try {
      setIsLoading(true);
      const payload = await loginWithPassword({
        email: email.trim(),
        password,
      });
      setSession(payload);
      onLogin?.(payload);
      navigate(location.state?.from ?? "/dashboard", { replace: true });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to sign in.");
    } finally {
      setIsLoading(false);
    }
  }

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
          <h3>Sign in</h3>
          <form className="login-form" onSubmit={handleSubmit}>
            <label>
              Work email
              <input
                type="email"
                placeholder="ravi@torilaure.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
              />
            </label>
            <div className="login-form-row">
              <label className="checkbox-row">
                <input type="checkbox" defaultChecked />
                <span>Keep me signed in</span>
              </label>
              <button type="button" className="text-button">
                Forgot password?
              </button>
            </div>
            {errorMessage ? <p className="error-message">{errorMessage}</p> : null}
            <button type="submit" className="primary-button login-submit" disabled={isLoading}>
              {isLoading ? "Signing in..." : "Enter platform"}
            </button>
            <button type="button" className="ghost-button login-submit">
              Continue with Microsoft
            </button>
          </form>
          <div className="auth-links auth-links-under-button">
            <button type="button" className="text-button">
              Create account
            </button>
            <button type="button" className="text-button">
              Request admin access
            </button>
          </div>
          <p className="hint-text">Demo account: `ravi@torilaure.com` / `Torilaure123!`</p>
        </div>
      </section>
    </main>
  );
}
