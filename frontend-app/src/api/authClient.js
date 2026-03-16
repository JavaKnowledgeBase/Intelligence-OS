const API_BASE_URL = "http://localhost:8000/api/v1";

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
