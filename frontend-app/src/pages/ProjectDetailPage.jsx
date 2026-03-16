import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getSession } from "../auth";
import {
  addProjectMember,
  createProjectNote,
  downloadProjectDocument,
  fetchProjectDocumentPreview,
  fetchProjectMembers,
  fetchProjectWorkspace,
  removeProjectMember,
  uploadProjectDocument,
} from "../api/projectClient";
import { logoutSession } from "../api/sessionClient";
import { FileUploadPanel } from "../components/FileUploadPanel";
import { SectionTitle } from "../components/SectionTitle";

function formatCurrency(value) {
  if (value == null) {
    return "Not set";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value) {
  if (value == null) {
    return "Not set";
  }

  return `${Number(value).toFixed(1)}%`;
}

function formatFileSize(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ProjectDetailPage() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const session = getSession();
  const currentUserId = session?.user?.id;
  const [workspace, setWorkspace] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [isSavingMember, setIsSavingMember] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [memberEmail, setMemberEmail] = useState("");
  const [previewState, setPreviewState] = useState({ title: "", text: "", isLoading: false, isOpen: false });

  useEffect(() => {
    let isMounted = true;

    async function loadWorkspace() {
      setIsLoading(true);
      setErrorMessage("");

      try {
        const data = await fetchProjectWorkspace(projectId);
        if (!isMounted) {
          return;
        }
        setWorkspace(data);
        const members = await fetchProjectMembers(projectId);
        if (!isMounted) {
          return;
        }
        setWorkspace((current) => ({ ...(current ?? data), members }));
      } catch (error) {
        if (!isMounted) {
          return;
        }
        const message = error instanceof Error ? error.message : "Unable to load the project workspace.";
        setErrorMessage(message);
        if (message.includes("401")) {
          await logoutSession();
          navigate("/login", { replace: true });
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadWorkspace();

    return () => {
      isMounted = false;
    };
  }, [navigate, projectId]);

  async function handleDocumentUpload(file) {
    const payload = await uploadProjectDocument(projectId, file);
    setWorkspace((current) => {
      if (!current) {
        return current;
      }
      const activityItem = {
        id: `activity-document-${payload.document.id}`,
        activity_type: "document_uploaded",
        title: "Evidence uploaded",
        detail: `${payload.document.file_name} was added to the project workspace.`,
        actor: payload.document.uploaded_by,
        occurred_at: payload.document.uploaded_at,
      };
      return {
        ...current,
        documents: [payload.document, ...current.documents],
        activity: [activityItem, ...current.activity],
      };
    });
    return `${payload.document.file_name} uploaded into ${workspace?.project?.name ?? "the workspace"}.`;
  }

  async function handleCreateNote(event) {
    event.preventDefault();
    if (!noteContent.trim()) {
      setErrorMessage("Enter a note before saving it.");
      return;
    }

    try {
      setIsSavingNote(true);
      setErrorMessage("");
      const note = await createProjectNote(projectId, noteContent.trim());
      setWorkspace((current) => {
        if (!current) {
          return current;
        }
        const activityItem = {
          id: `activity-note-${note.id}`,
          activity_type: "note_added",
          title: "Project note added",
          detail: note.content,
          actor: note.author_name,
          occurred_at: note.created_at,
        };
        return {
          ...current,
          notes: [note, ...current.notes],
          activity: [activityItem, ...current.activity],
        };
      });
      setNoteContent("");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to save the project note.");
    } finally {
      setIsSavingNote(false);
    }
  }

  async function handleAddMember(event) {
    event.preventDefault();
    if (!memberEmail.trim()) {
      setErrorMessage("Enter an email to add a collaborator.");
      return;
    }

    try {
      setIsSavingMember(true);
      setErrorMessage("");
      const member = await addProjectMember(projectId, memberEmail.trim());
      setWorkspace((current) => {
        if (!current) {
          return current;
        }
        const existing = current.members?.some((item) => item.id === member.id);
        return {
          ...current,
          members: existing ? current.members : [...(current.members ?? []), member],
        };
      });
      setMemberEmail("");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to add the project member.");
    } finally {
      setIsSavingMember(false);
    }
  }

  async function handleRemoveMember(memberUserId) {
    try {
      setErrorMessage("");
      await removeProjectMember(projectId, memberUserId);
      setWorkspace((current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          members: (current.members ?? []).filter((item) => item.id !== memberUserId),
        };
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to remove the project member.");
    }
  }

  const canManageMembers = Boolean(
    workspace?.project &&
      session?.user &&
      (session.user.role === "admin" || session.user.role === "analyst" || workspace.project.owner_id === currentUserId),
  );

  async function handlePreviewDocument(document) {
    try {
      setErrorMessage("");
      setPreviewState({
        title: document.file_name,
        text: "",
        isLoading: true,
        isOpen: true,
      });
      const payload = await fetchProjectDocumentPreview(projectId, document.id);
      setPreviewState({
        title: payload.document.file_name,
        text: payload.preview_text,
        isLoading: false,
        isOpen: true,
      });
    } catch (error) {
      setPreviewState({ title: "", text: "", isLoading: false, isOpen: false });
      setErrorMessage(error instanceof Error ? error.message : "Unable to preview the selected document.");
    }
  }

  return (
    <main className="content projects-content">
      <section className="section-block">
        <SectionTitle
          eyebrow="Project workspace"
          title={workspace?.project?.name ?? "Project workspace"}
          description="Review the investment thesis, associated opportunities, alerts, market signals, and evidence files connected to this project."
        />
      </section>

      {errorMessage ? <p className="callout-message">{errorMessage}</p> : null}

      <section className="project-detail-grid">
        <div className="glass-card">
          <div className="projects-header-row">
            <div>
              <p className="panel-label">Workspace summary</p>
              <h3 className="projects-heading">{workspace?.project?.project_type ?? "Loading project"}</h3>
            </div>
            <span className={`status-pill ${isLoading ? "status-pending" : errorMessage ? "status-error" : "status-live"}`}>
              {isLoading ? "Loading" : workspace?.project?.stage ?? "Ready"}
            </span>
          </div>

          {workspace?.project ? (
            <div className="project-summary-grid">
              <div className="project-summary-card">
                <span>Owner</span>
                <strong>{workspace.project.owner}</strong>
              </div>
              <div className="project-summary-card">
                <span>Target IRR</span>
                <strong>{formatPercent(workspace.project.target_irr)}</strong>
              </div>
              <div className="project-summary-card">
                <span>Budget</span>
                <strong>{formatCurrency(workspace.project.budget_amount)}</strong>
              </div>
              <div className="project-summary-card">
                <span>Status</span>
                <strong>{workspace.project.status}</strong>
              </div>
              <div className="project-summary-card project-summary-card-wide">
                <span>Investment thesis</span>
                <strong>{workspace.project.investment_thesis || "No investment thesis has been captured yet."}</strong>
              </div>
            </div>
          ) : null}
        </div>

        <div className="glass-card">
          <FileUploadPanel
            title="Project evidence upload"
            description="Add acquisition memos, diligence files, lease schedules, and investment evidence into this project-scoped workspace."
            buttonLabel="Upload project document"
            helperText="Files are stored per tenant and project, with metadata tracked in PostgreSQL."
            onUpload={handleDocumentUpload}
          />
        </div>
      </section>

      <section className="split-panel">
        <div className="glass-card">
          <SectionTitle
            eyebrow="Opportunities"
            title="Project listings"
            description="Listings linked to this project stay visible in one place so ROI and diligence can evolve together."
          />
          <div className="projects-grid">
            {(workspace?.listings ?? []).map((listing) => (
              <article key={listing.id} className="project-card">
                <div className="project-card-top">
                  <span>{listing.asset_class}</span>
                  <strong>{listing.deal_score}</strong>
                </div>
                <h3>{listing.title}</h3>
                <p>{listing.summary}</p>
                <div className="project-meta-grid">
                  <div>
                    <span>Location</span>
                    <strong>{listing.location}</strong>
                  </div>
                  <div>
                    <span>IRR</span>
                    <strong>{formatPercent(listing.projected_irr)}</strong>
                  </div>
                </div>
              </article>
            ))}
            {!workspace?.listings?.length && !isLoading ? <p className="hint-text">No listings are attached to this project yet.</p> : null}
          </div>
        </div>

        <div className="glass-card">
          <SectionTitle
            eyebrow="Evidence"
            title="Project documents"
            description="These files are the foundation for later ingestion, extraction, and evidence-backed analysis."
          />
          <div className="document-list">
            {(workspace?.documents ?? []).map((document) => (
              <article key={document.id} className="document-card">
                <div>
                  <strong>{document.file_name}</strong>
                  <p>{document.content_type}</p>
                  {document.extracted_text_excerpt ? <p className="document-excerpt">{document.extracted_text_excerpt}</p> : null}
                </div>
                <div className="document-meta">
                  <span>{formatFileSize(document.file_size_bytes)}</span>
                  <span className={`status-pill status-${document.processing_status === "ready" ? "live" : document.processing_status === "failed" ? "error" : "pending"}`}>
                    {document.processing_status}
                  </span>
                  <small>Uploaded by {document.uploaded_by}</small>
                  {document.preview_available ? (
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => handlePreviewDocument(document)}
                    >
                      Preview
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => downloadProjectDocument(projectId, document.id).catch((error) => setErrorMessage(error.message))}
                  >
                    Download
                  </button>
                </div>
              </article>
            ))}
            {!workspace?.documents?.length && !isLoading ? <p className="hint-text">No documents uploaded yet for this project.</p> : null}
          </div>
          {previewState.isOpen ? (
            <div className="document-preview-panel">
              <div className="projects-header-row">
                <div>
                  <p className="panel-label">Document preview</p>
                  <h3 className="projects-heading">{previewState.title}</h3>
                </div>
                <button type="button" className="text-button" onClick={() => setPreviewState({ title: "", text: "", isLoading: false, isOpen: false })}>
                  Close
                </button>
              </div>
              <pre className="document-preview-text">
                {previewState.isLoading ? "Loading preview..." : previewState.text}
              </pre>
            </div>
          ) : null}
        </div>
      </section>

      <section className="split-panel">
        <div className="glass-card">
          <SectionTitle
            eyebrow="Collaboration"
            title="Project members"
            description="Keep the working team visible so project access, context, and accountability stay clear."
          />
          {canManageMembers ? (
            <form className="login-form project-form" onSubmit={handleAddMember}>
              <label>
                Add teammate by email
                <input
                  type="email"
                  value={memberEmail}
                  onChange={(event) => setMemberEmail(event.target.value)}
                  placeholder="name@company.com"
                />
              </label>
              <button type="submit" className="ghost-button login-submit" disabled={isSavingMember}>
                {isSavingMember ? "Adding member..." : "Add member"}
              </button>
            </form>
          ) : null}
          <div className="member-list">
            {(workspace?.members ?? []).map((member) => (
              <article key={member.id} className="member-card">
                <div>
                  <strong>{member.full_name}</strong>
                  <p>{member.email}</p>
                  <small>{member.role}</small>
                </div>
                {canManageMembers && member.id !== workspace?.project?.owner_id ? (
                  <button type="button" className="text-button" onClick={() => handleRemoveMember(member.id)}>
                    Remove
                  </button>
                ) : null}
              </article>
            ))}
            {!workspace?.members?.length && !isLoading ? <p className="hint-text">No project members are attached yet.</p> : null}
          </div>
        </div>

        <div className="glass-card">
          <SectionTitle
            eyebrow="Signals"
            title="Market insights"
            description="Keep the regional demand and pricing backdrop visible while diligence moves forward."
          />
          <div className="activity-list">
            {(workspace?.market_insights ?? []).map((insight) => (
              <article key={insight.id} className="activity-card">
                <strong>{insight.region}</strong>
                <p>{insight.signal}</p>
                <small>
                  {insight.trend}
                  {typeof insight.confidence === "number" ? ` | ${Math.round(insight.confidence * 100)}% confidence` : ""}
                </small>
              </article>
            ))}
            {!workspace?.market_insights?.length && !isLoading ? <p className="hint-text">No market insights are available yet.</p> : null}
          </div>
        </div>

        <div className="glass-card">
          <SectionTitle
            eyebrow="Governance"
            title="Alert rules"
            description="Notification preferences stay in view so investors and analysts know what the platform is watching."
          />
          <div className="activity-list">
            {(workspace?.alerts ?? []).map((alert) => (
              <article key={alert.id} className="activity-card">
                <strong>{alert.name}</strong>
                <p>{alert.trigger}</p>
                <small>
                  {alert.channel} | {alert.severity} | {alert.enabled ? "enabled" : "disabled"}
                </small>
              </article>
            ))}
            {!workspace?.alerts?.length && !isLoading ? <p className="hint-text">No alert rules are configured yet.</p> : null}
          </div>
        </div>
      </section>

      <section className="split-panel">
        <div className="glass-card">
          <SectionTitle
            eyebrow="Notes"
            title="Project notes"
            description="Capture diligence findings, working assumptions, and coordination context directly inside the workspace."
          />
          <form className="login-form project-form" onSubmit={handleCreateNote}>
            <label>
              Add note
              <textarea
                className="login-textarea"
                value={noteContent}
                onChange={(event) => setNoteContent(event.target.value)}
                placeholder="Record key diligence findings, valuation assumptions, or team follow-ups."
                rows={4}
              />
            </label>
            <button type="submit" className="ghost-button login-submit" disabled={isSavingNote}>
              {isSavingNote ? "Saving note..." : "Save note"}
            </button>
          </form>
          <div className="note-list">
            {(workspace?.notes ?? []).map((note) => (
              <article key={note.id} className="note-card">
                <strong>{note.author_name}</strong>
                <p>{note.content}</p>
              </article>
            ))}
            {!workspace?.notes?.length && !isLoading ? <p className="hint-text">No notes have been added to this project yet.</p> : null}
          </div>
        </div>

        <div className="glass-card">
          <SectionTitle
            eyebrow="Activity"
            title="Recent workspace activity"
            description="See a running history of project setup, uploaded evidence, and notes as the diligence story develops."
          />
          <div className="activity-list">
            {(workspace?.activity ?? []).map((item) => (
              <article key={item.id} className="activity-card">
                <strong>{item.title}</strong>
                <p>{item.detail}</p>
                <small>
                  {item.actor}
                  {item.occurred_at ? ` | ${new Date(item.occurred_at).toLocaleString()}` : ""}
                </small>
              </article>
            ))}
            {!workspace?.activity?.length && !isLoading ? <p className="hint-text">No workspace activity has been recorded yet.</p> : null}
          </div>
        </div>
      </section>
    </main>
  );
}
