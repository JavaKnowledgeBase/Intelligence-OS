import { authenticatedFetch } from "./sessionClient";

async function readJsonOrThrow(response, fallbackMessage) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail ?? fallbackMessage);
  }
  return payload;
}

export async function fetchProjects() {
  const response = await authenticatedFetch("/projects");
  return readJsonOrThrow(response, "Unable to load projects.");
}

export async function fetchProjectWorkspace(projectId) {
  const response = await authenticatedFetch(`/projects/${projectId}/workspace`);
  return readJsonOrThrow(response, "Unable to load the project workspace.");
}

export async function createProject(payload) {
  const response = await authenticatedFetch("/projects", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return readJsonOrThrow(response, "Unable to create project.");
}

export async function uploadProjectDocument(projectId, file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await authenticatedFetch(`/projects/${projectId}/documents`, {
    method: "POST",
    body: formData,
  });

  return readJsonOrThrow(response, "Unable to upload the project document.");
}

export async function createProjectNote(projectId, content) {
  const response = await authenticatedFetch(`/projects/${projectId}/notes`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content }),
  });

  return readJsonOrThrow(response, "Unable to save the project note.");
}

export async function downloadProjectDocument(projectId, documentId) {
  const response = await authenticatedFetch(`/projects/${projectId}/documents/${documentId}/download`);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to download the project document.");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const fileName = match?.[1] ?? "project-document";
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(objectUrl);
}

export async function fetchProjectDocumentPreview(projectId, documentId) {
  const response = await authenticatedFetch(`/projects/${projectId}/documents/${documentId}/preview`);
  return readJsonOrThrow(response, "Unable to load the project document preview.");
}
