import { authenticatedFetch } from "./sessionClient";

async function readJsonOrThrow(response, fallbackMessage) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail ?? fallbackMessage);
  }
  return payload;
}

export async function fetchListings() {
  const response = await authenticatedFetch("/listings");
  return readJsonOrThrow(response, "Unable to load listings.");
}

export async function searchListings(query) {
  const suffix = query?.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  const response = await authenticatedFetch(`/listings/search${suffix}`);
  return readJsonOrThrow(response, "Unable to search listings.");
}

export async function createListing(payload) {
  const response = await authenticatedFetch("/listings", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return readJsonOrThrow(response, "Unable to create listing.");
}
