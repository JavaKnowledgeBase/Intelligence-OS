import { clearSession, getSession, setSession } from "../auth";

const API_BASE_URL = "http://localhost:8000/api/v1";

async function refreshSessionOrClear() {
  const session = getSession();
  if (!session?.refresh_token) {
    clearSession();
    return null;
  }

  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: session.refresh_token }),
  });

  if (!response.ok) {
    clearSession();
    return null;
  }

  const nextSession = await response.json();
  setSession(nextSession);
  return nextSession;
}

export async function authenticatedFetch(path, options = {}) {
  let session = getSession();
  const headers = new Headers(options.headers ?? {});

  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }

  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status !== 401) {
    return response;
  }

  session = await refreshSessionOrClear();
  if (!session?.access_token) {
    return response;
  }

  const retryHeaders = new Headers(options.headers ?? {});
  retryHeaders.set("Authorization", `Bearer ${session.access_token}`);
  return fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: retryHeaders,
  });
}

export async function logoutSession() {
  const session = getSession();
  const headers = new Headers();
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }
  await fetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...Object.fromEntries(headers.entries()),
    },
    body: JSON.stringify({
      refresh_token: session?.refresh_token ?? null,
    }),
  });
  clearSession();
}

