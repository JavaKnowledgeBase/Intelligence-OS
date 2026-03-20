import { authenticatedFetch } from "./sessionClient";

async function readJsonOrThrow(response, fallbackMessage) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail ?? fallbackMessage);
  }
  return payload;
}

export async function fetchPortfolioSavedViews() {
  const response = await authenticatedFetch("/projects/portfolio-saved-views");
  return readJsonOrThrow(response, "Unable to load portfolio saved views.");
}

export async function createPortfolioSavedView(payload) {
  const response = await authenticatedFetch("/projects/portfolio-saved-views", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return readJsonOrThrow(response, "Unable to create portfolio saved view.");
}

export async function deletePortfolioSavedView(viewId) {
  const response = await authenticatedFetch(`/projects/portfolio-saved-views/${viewId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to delete portfolio saved view.");
  }
}

export async function updatePortfolioSavedView(viewId, payload) {
  const response = await authenticatedFetch(`/projects/portfolio-saved-views/${viewId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return readJsonOrThrow(response, "Unable to update portfolio saved view.");
}
