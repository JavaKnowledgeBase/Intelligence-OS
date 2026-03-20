import { authenticatedFetch } from "./sessionClient";

async function readJsonOrThrow(response, fallbackMessage) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail ?? fallbackMessage);
  }
  return payload;
}

export async function fetchAlerts() {
  const response = await authenticatedFetch("/alerts");
  return readJsonOrThrow(response, "Unable to load alert rules.");
}

export async function createAlertRule(payload) {
  const response = await authenticatedFetch("/alerts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return readJsonOrThrow(response, "Unable to create the alert rule.");
}

export async function updateAlertRule(alertId, payload) {
  const response = await authenticatedFetch(`/alerts/${alertId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return readJsonOrThrow(response, "Unable to update the alert rule.");
}

export async function deleteAlertRule(alertId) {
  const response = await authenticatedFetch(`/alerts/${alertId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to delete the alert rule.");
  }
}

export async function fetchIngestionRuns() {
  const response = await authenticatedFetch("/ingestion/runs");
  return readJsonOrThrow(response, "Unable to load ingestion runs.");
}

export async function fetchIngestionSources() {
  const response = await authenticatedFetch("/ingestion/sources");
  return readJsonOrThrow(response, "Unable to load ingestion sources.");
}

export async function triggerIngestionSync(sourceName = "starter_feed") {
  const response = await authenticatedFetch("/ingestion/sync", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ source_name: sourceName }),
  });
  return readJsonOrThrow(response, "Unable to trigger the ingestion sync.");
}

export async function fetchBenchmarkComps(assetClass) {
  const query = assetClass ? `?asset_class=${encodeURIComponent(assetClass)}` : "";
  const response = await authenticatedFetch(`/market/benchmark-comps${query}`);
  return readJsonOrThrow(response, "Unable to load benchmark comps.");
}

export async function createBenchmarkComp(payload) {
  const response = await authenticatedFetch("/market/benchmark-comps", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return readJsonOrThrow(response, "Unable to create the benchmark comp.");
}

export async function updateBenchmarkComp(compId, payload) {
  const response = await authenticatedFetch(`/market/benchmark-comps/${compId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return readJsonOrThrow(response, "Unable to update the benchmark comp.");
}

export async function fetchBenchmarkCalibration(assetClass, location) {
  const query = location?.trim() ? `?location=${encodeURIComponent(location.trim())}` : "";
  const response = await authenticatedFetch(`/market/benchmark-calibration/${encodeURIComponent(assetClass)}${query}`);
  return readJsonOrThrow(response, "Unable to load the benchmark calibration.");
}
