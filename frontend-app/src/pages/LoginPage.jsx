import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { setSession } from "../auth";
import {
  confirmPasswordReset,
  loginWithPassword,
  registerAccount,
  requestAdminAccess,
  requestPasswordReset,
} from "../api/authClient";
import { AuthShell } from "../components/AuthShell";

const authModes = {
  signIn: "signIn",
  createAccount: "createAccount",
  forgotPassword: "forgotPassword",
  requestAdmin: "requestAdmin",
};

export function LoginPage({ onLogin }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [mode, setMode] = useState(authModes.signIn);
  const [signInForm, setSignInForm] = useState({
    email: "ravi@torilaure.com",
    password: "Torilaure123!",
  });
  const [createAccountForm, setCreateAccountForm] = useState({
    full_name: "",
    company_name: "",
    email: "",
    password: "",
  });
  const [accessRequestForm, setAccessRequestForm] = useState({
    full_name: "",
    company_name: "",
    email: "",
    requested_role: "admin",
    reason: "",
  });
  const [resetRequestEmail, setResetRequestEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [infoMessage, setInfoMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  function switchMode(nextMode) {
    setMode(nextMode);
    setErrorMessage("");
    setInfoMessage("");
  }

  async function handleSignIn(event) {
    event.preventDefault();
    setErrorMessage("");
    setInfoMessage("");

    if (!signInForm.email.trim() || !signInForm.password.trim()) {
      setErrorMessage("Enter your email and password to continue.");
      return;
    }

    try {
      setIsLoading(true);
      const payload = await loginWithPassword({
        email: signInForm.email.trim(),
        password: signInForm.password,
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

  async function handleCreateAccount(event) {
    event.preventDefault();
    setErrorMessage("");
    setInfoMessage("");

    try {
      setIsLoading(true);
      const payload = await registerAccount(createAccountForm);
      setSession(payload);
      onLogin?.(payload);
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create account.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRequestAdminAccess(event) {
    event.preventDefault();
    setErrorMessage("");
    setInfoMessage("");

    try {
      setIsLoading(true);
      const payload = await requestAdminAccess(accessRequestForm);
      setInfoMessage(`${payload.message} Reference: ${payload.request_id}`);
      setAccessRequestForm({
        full_name: "",
        company_name: "",
        email: "",
        requested_role: "admin",
        reason: "",
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to submit access request.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRequestPasswordReset(event) {
    event.preventDefault();
    setErrorMessage("");
    setInfoMessage("");

    try {
      setIsLoading(true);
      const payload = await requestPasswordReset({ email: resetRequestEmail });
      setResetToken(payload.reset_token ?? "");
      setInfoMessage(
        payload.reset_token
          ? `Reset token generated for testing: ${payload.reset_token}`
          : payload.message,
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to request password reset.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleConfirmPasswordReset(event) {
    event.preventDefault();
    setErrorMessage("");
    setInfoMessage("");

    try {
      setIsLoading(true);
      const payload = await confirmPasswordReset({
        email: resetRequestEmail,
        reset_token: resetToken,
        new_password: newPassword,
      });
      setInfoMessage(payload.message);
      setSignInForm({
        email: resetRequestEmail,
        password: newPassword,
      });
      setResetToken("");
      setNewPassword("");
      setMode(authModes.signIn);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to reset password.");
    } finally {
      setIsLoading(false);
    }
  }

  function renderModeContent() {
    if (mode === authModes.createAccount) {
      return (
        <form className="login-form" onSubmit={handleCreateAccount}>
          <label>
            Full name
            <input
              type="text"
              value={createAccountForm.full_name}
              onChange={(event) => setCreateAccountForm((current) => ({ ...current, full_name: event.target.value }))}
              placeholder="Ravi Kafley"
            />
          </label>
          <label>
            Company name
            <input
              type="text"
              value={createAccountForm.company_name}
              onChange={(event) => setCreateAccountForm((current) => ({ ...current, company_name: event.target.value }))}
              placeholder="Torilaure"
            />
          </label>
          <label>
            Work email
            <input
              type="email"
              value={createAccountForm.email}
              onChange={(event) => setCreateAccountForm((current) => ({ ...current, email: event.target.value }))}
              placeholder="name@company.com"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={createAccountForm.password}
              onChange={(event) => setCreateAccountForm((current) => ({ ...current, password: event.target.value }))}
              placeholder="At least 10 chars, mixed case, number"
            />
          </label>
          <button type="submit" className="primary-button login-submit" disabled={isLoading}>
            {isLoading ? "Creating account..." : "Create account"}
          </button>
        </form>
      );
    }

    if (mode === authModes.requestAdmin) {
      return (
        <form className="login-form" onSubmit={handleRequestAdminAccess}>
          <label>
            Full name
            <input
              type="text"
              value={accessRequestForm.full_name}
              onChange={(event) => setAccessRequestForm((current) => ({ ...current, full_name: event.target.value }))}
              placeholder="Ravi Kafley"
            />
          </label>
          <label>
            Company name
            <input
              type="text"
              value={accessRequestForm.company_name}
              onChange={(event) => setAccessRequestForm((current) => ({ ...current, company_name: event.target.value }))}
              placeholder="Torilaure"
            />
          </label>
          <label>
            Work email
            <input
              type="email"
              value={accessRequestForm.email}
              onChange={(event) => setAccessRequestForm((current) => ({ ...current, email: event.target.value }))}
              placeholder="name@company.com"
            />
          </label>
          <label>
            Why do you need admin access?
            <textarea
              className="login-textarea"
              value={accessRequestForm.reason}
              onChange={(event) => setAccessRequestForm((current) => ({ ...current, reason: event.target.value }))}
              placeholder="Describe your use case and level of access needed."
              rows={4}
            />
          </label>
          <button type="submit" className="primary-button login-submit" disabled={isLoading}>
            {isLoading ? "Submitting..." : "Request admin access"}
          </button>
        </form>
      );
    }

    if (mode === authModes.forgotPassword) {
      return (
        <div className="login-form-stack">
          <form className="login-form" onSubmit={handleRequestPasswordReset}>
            <label>
              Work email
              <input
                type="email"
                value={resetRequestEmail}
                onChange={(event) => setResetRequestEmail(event.target.value)}
                placeholder="name@company.com"
              />
            </label>
            <button type="submit" className="primary-button login-submit" disabled={isLoading}>
              {isLoading ? "Generating token..." : "Get reset token"}
            </button>
          </form>

          <form className="login-form" onSubmit={handleConfirmPasswordReset}>
            <label>
              Reset token
              <input
                type="text"
                value={resetToken}
                onChange={(event) => setResetToken(event.target.value)}
                placeholder="Paste the one-time reset token"
              />
            </label>
            <label>
              New password
              <input
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                placeholder="At least 10 chars, mixed case, number"
              />
            </label>
            <button type="submit" className="ghost-button login-submit" disabled={isLoading}>
              {isLoading ? "Resetting..." : "Reset password"}
            </button>
          </form>
        </div>
      );
    }

    return (
      <form className="login-form" onSubmit={handleSignIn}>
        <label>
          Work email
          <input
            type="email"
            placeholder="ravi@torilaure.com"
            value={signInForm.email}
            onChange={(event) => setSignInForm((current) => ({ ...current, email: event.target.value }))}
            autoComplete="email"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            placeholder="Enter your password"
            value={signInForm.password}
            onChange={(event) => setSignInForm((current) => ({ ...current, password: event.target.value }))}
            autoComplete="current-password"
          />
        </label>
        <div className="login-form-row">
          <label className="checkbox-row">
            <input type="checkbox" defaultChecked />
            <span>Keep me signed in</span>
          </label>
          <button type="button" className="text-button" onClick={() => switchMode(authModes.forgotPassword)}>
            Forgot password?
          </button>
        </div>
        <button type="submit" className="primary-button login-submit" disabled={isLoading}>
          {isLoading ? "Signing in..." : "Enter platform"}
        </button>
        <button
          type="button"
          className="ghost-button login-submit"
          onClick={() =>
            setInfoMessage("Microsoft sign-in is not enabled yet in this template. Email/password flows are ready today.")
          }
        >
          Continue with Microsoft
        </button>
      </form>
    );
  }

  return (
    <AuthShell
      title={
        mode === authModes.signIn
          ? "Sign in"
          : mode === authModes.createAccount
            ? "Create account"
            : mode === authModes.forgotPassword
              ? "Reset password"
              : "Request admin access"
      }
      modeAction={
        mode !== authModes.signIn ? (
          <button type="button" className="text-button" onClick={() => switchMode(authModes.signIn)}>
            Back to sign in
          </button>
        ) : null
      }
      footer={<p className="hint-text">Demo account: `ravi@torilaure.com` / `Torilaure123!`</p>}
    >
      {renderModeContent()}

      {errorMessage ? <p className="error-message">{errorMessage}</p> : null}
      {infoMessage ? <p className="hint-text">{infoMessage}</p> : null}

      <div className="auth-links auth-links-under-button">
        <button type="button" className="text-button" onClick={() => switchMode(authModes.signIn)}>
          Sign in
        </button>
        <button type="button" className="text-button" onClick={() => switchMode(authModes.createAccount)}>
          Create account
        </button>
        <button type="button" className="text-button" onClick={() => switchMode(authModes.requestAdmin)}>
          Request admin access
        </button>
      </div>
    </AuthShell>
  );
}
