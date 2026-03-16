import { authenticatedFetch } from "./sessionClient";

async function readJsonOrThrow(response, fallbackMessage) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail ?? fallbackMessage);
  }
  return payload;
}

export async function fetchAccessRequests(status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const response = await authenticatedFetch(`/auth/access-requests${query}`);
  return readJsonOrThrow(response, "Unable to load access requests.");
}

export async function reviewAccessRequest(requestId, status) {
  const response = await authenticatedFetch(`/auth/access-requests/${requestId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
  });
  return readJsonOrThrow(response, "Unable to review the access request.");
}
