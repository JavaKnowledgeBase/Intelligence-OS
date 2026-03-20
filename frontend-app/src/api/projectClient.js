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

export async function fetchProjectMembers(projectId) {
  const response = await authenticatedFetch(`/projects/${projectId}/members`);
  return readJsonOrThrow(response, "Unable to load project members.");
}

export async function fetchProjectRoiSnapshot(projectId) {
  const response = await authenticatedFetch(`/projects/${projectId}/roi-snapshot`);
  return readJsonOrThrow(response, "Unable to load the ROI snapshot.");
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

export async function calculateProjectRoiScenario(projectId, payload) {
  const response = await authenticatedFetch(`/projects/${projectId}/roi-scenarios/calculate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return readJsonOrThrow(response, "Unable to calculate the ROI scenario.");
}

export async function buildProjectRoiSensitivity(projectId, payload) {
  const response = await authenticatedFetch(`/projects/${projectId}/roi-scenarios/sensitivity`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return readJsonOrThrow(response, "Unable to build the ROI sensitivity analysis.");
}

export async function createProjectRoiScenario(projectId, payload) {
  const response = await authenticatedFetch(`/projects/${projectId}/roi-scenarios`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return readJsonOrThrow(response, "Unable to save the ROI scenario.");
}

export async function updateProjectRoiScenario(projectId, scenarioId, payload) {
  const response = await authenticatedFetch(`/projects/${projectId}/roi-scenarios/${scenarioId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return readJsonOrThrow(response, "Unable to update the ROI scenario.");
}

export async function deleteProjectRoiScenario(projectId, scenarioId) {
  const response = await authenticatedFetch(`/projects/${projectId}/roi-scenarios/${scenarioId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to delete the ROI scenario.");
  }
}

export async function createProjectRoiRecommendation(projectId, scenarioId) {
  const response = await authenticatedFetch(`/projects/${projectId}/roi-scenarios/${scenarioId}/recommendations`, {
    method: "POST",
  });

  return readJsonOrThrow(response, "Unable to create the ROI recommendation.");
}

export async function listProjectRoiRecommendations(projectId, scenarioId) {
  const response = await authenticatedFetch(`/projects/${projectId}/roi-scenarios/${scenarioId}/recommendations`);
  return readJsonOrThrow(response, "Unable to load ROI recommendations.");
}

export async function addProjectMember(projectId, email) {
  const response = await authenticatedFetch(`/projects/${projectId}/members`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });

  return readJsonOrThrow(response, "Unable to add the project member.");
}

export async function removeProjectMember(projectId, memberUserId) {
  const response = await authenticatedFetch(`/projects/${projectId}/members/${memberUserId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to remove the project member.");
  }
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

export async function updateProjectNote(projectId, noteId, content) {
  const response = await authenticatedFetch(`/projects/${projectId}/notes/${noteId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content }),
  });

  return readJsonOrThrow(response, "Unable to update the project note.");
}

export async function deleteProjectNote(projectId, noteId) {
  const response = await authenticatedFetch(`/projects/${projectId}/notes/${noteId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to delete the project note.");
  }
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

export async function downloadProjectRoiRecommendationsPDF(projectId, scenarioId) {
  const response = await authenticatedFetch(`/projects/${projectId}/roi-scenarios/${scenarioId}/recommendations/pdf`);

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Unable to download ROI recommendations PDF.");
  }

  return response.blob();
}
