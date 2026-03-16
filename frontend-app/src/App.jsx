import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { clearSession, getSession, isAuthenticated, setSession, updateSessionUser } from "./auth";
import { fetchCurrentUser, refreshWithToken } from "./api/authClient";
import { logoutSession } from "./api/sessionClient";
import { BrandMark } from "./components/BrandMark";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { ArchitecturePage } from "./pages/ArchitecturePage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";

function AppLayout() {
  const navigate = useNavigate();
  const [session, setSessionState] = useState(() => getSession());
  const [authReady, setAuthReady] = useState(false);
  const signedIn = Boolean(session?.access_token && session?.user) && isAuthenticated();

  useEffect(() => {
    let ignore = false;

    async function bootstrapSession() {
      const currentSession = getSession();
      if (!currentSession?.access_token) {
        if (!ignore) {
          setSessionState(null);
          setAuthReady(true);
        }
        return;
      }

      try {
        const user = await fetchCurrentUser(currentSession.access_token);
        if (ignore) {
          return;
        }
        const nextSession = updateSessionUser(user);
        setSessionState(nextSession);
      } catch {
        try {
          const refreshedSession = await refreshWithToken(currentSession.refresh_token);
          if (ignore) {
            return;
          }
          setSession(refreshedSession);
          const validatedUser = await fetchCurrentUser(refreshedSession.access_token);
          const nextSession = updateSessionUser(validatedUser);
          setSessionState(nextSession ?? refreshedSession);
        } catch {
          if (ignore) {
            return;
          }
          clearSession();
          setSessionState(null);
        }
      } finally {
        if (!ignore) {
          setAuthReady(true);
        }
      }
    }

    bootstrapSession();

    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="app-shell">
      <div className="page-orb page-orb-left" />
      <div className="page-orb page-orb-right" />

      <header className="hero">
        <nav className="topbar">
          <BrandMark />
          <div className="topbar-actions">
            <div className="nav-pills" aria-label="Torilaure application views">
              <NavLink to="/dashboard" className={({ isActive }) => `nav-pill ${isActive ? "nav-pill-active" : ""}`}>
                Dashboard
              </NavLink>
              <NavLink to="/architecture" className={({ isActive }) => `nav-pill ${isActive ? "nav-pill-active" : ""}`}>
                Architecture
              </NavLink>
              <NavLink to="/login" className={({ isActive }) => `nav-pill ${isActive ? "nav-pill-active" : ""}`}>
                Login
              </NavLink>
            </div>
            <a className="ghost-button button-link" href="http://localhost:8000/api/v1/projects/overview" target="_blank" rel="noreferrer">
              Investor API
            </a>
            {signedIn ? (
              <button
                className="primary-button"
                type="button"
                onClick={async () => {
                  await logoutSession();
                  setSessionState(null);
                  navigate("/login");
                }}
              >
                Sign out
              </button>
            ) : (
              <button className="primary-button" type="button" onClick={() => navigate("/login")}>
                Sign in
              </button>
            )}
          </div>
        </nav>
        {signedIn && session?.user ? (
          <div className="session-banner">
            <span>Signed in as {session.user.full_name}</span>
            <strong>{session.user.role}</strong>
          </div>
        ) : null}
      </header>

      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute isReady={authReady} isAuthenticated={signedIn}>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/architecture"
          element={
            <ProtectedRoute isReady={authReady} isAuthenticated={signedIn}>
              <ArchitecturePage />
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<LoginPage onLogin={setSessionState} />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return <AppLayout />;
}
