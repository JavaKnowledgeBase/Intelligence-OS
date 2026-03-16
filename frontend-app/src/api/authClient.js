const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function loginWithPassword(credentials) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? "Unable to sign in.");
  }

  return payload;
}

export async function fetchCurrentUser(accessToken) {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? "Unable to validate session.");
  }

  return payload;
}

export async function refreshWithToken(refreshToken) {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? "Unable to refresh session.");
  }

  return payload;
}

export async function registerAccount(payload) {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail ?? "Unable to create account.");
  }

  return data;
}

export async function requestAdminAccess(payload) {
  const response = await fetch(`${API_BASE_URL}/auth/request-admin-access`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail ?? "Unable to submit admin access request.");
  }

  return data;
}

export async function requestPasswordReset(payload) {
  const response = await fetch(`${API_BASE_URL}/auth/password-reset/request`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail ?? "Unable to request a password reset.");
  }

  return data;
}

export async function confirmPasswordReset(payload) {
  const response = await fetch(`${API_BASE_URL}/auth/password-reset/confirm`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail ?? "Unable to reset password.");
  }

  return data;
}
