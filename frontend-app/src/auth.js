// Developer: Ravi Kafley
// Frontend session helpers for the starter login flow.
const SESSION_KEY = "torilaure_auth_session";

export function getSession() {
  const rawValue = localStorage.getItem(SESSION_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue);
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function setSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

export function isAuthenticated() {
  const session = getSession();
  return Boolean(session?.access_token && session?.user);
}

export function updateSessionUser(user) {
  const session = getSession();
  if (!session) {
    return null;
  }
  const nextSession = { ...session, user };
  setSession(nextSession);
  return nextSession;
}
