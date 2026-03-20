import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getSession } from "../auth";
import {
  addProjectMember,
  buildProjectRoiSensitivity,
  calculateProjectRoiScenario,
  createProjectNote,
  createProjectRoiRecommendation,
  createProjectRoiScenario,
  deleteProjectNote,
  deleteProjectRoiScenario,
  downloadProjectDocument,
  fetchProjectDocumentPreview,
  listProjectRoiRecommendations,
  fetchProjectMembers,
  fetchProjectRoiSnapshot,
  downloadProjectRoiRecommendationsPDF,
  fetchProjectWorkspace,
  removeProjectMember,
  updateProjectRoiScenario,
  updateProjectNote,
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

function formatDecimal(value, digits = 2) {
  if (value == null) {
    return "Not set";
  }
  return Number(value).toFixed(digits);
}

const emptyRoiForm = {
  name: "",
  scenario_type: "custom",
  listing_id: "",
  purchase_price: "",
  upfront_capex: "",
  annual_revenue: "",
  vacancy_rate: "5",
  annual_operating_expenses: "",
  annual_capex_reserve: "0",
  annual_revenue_growth_rate: "3",
  annual_expense_growth_rate: "2",
  exit_cap_rate: "6.5",
  exit_cost_rate: "2",
  hold_period_years: "5",
  discount_rate: "12",
  leverage_ratio: "55",
  interest_rate: "6",
  interest_only_years: "0",
  amortization_period_years: "30",
};

const defaultLeaseAssumptions = [
  {
    tenant_name: "Anchor Tenant",
    monthly_rent: 12000,
    start_month: 1,
    end_month: 24,
    annual_rent_growth_rate: 3,
    reimbursement_monthly: 500,
    downtime_months_after_expiry: 1,
    renewal_rent_change_rate: 4,
  },
];

function canManageNote(note, project, sessionUser) {
  if (!note || !project || !sessionUser) {
    return false;
  }
  if (sessionUser.role === "admin" || sessionUser.role === "analyst") {
    return true;
  }
  if (project.owner_id === sessionUser.id) {
    return true;
  }
  return note.author_id === sessionUser.id;
}

export function ProjectDetailPage() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const session = getSession();
  const currentUserId = session?.user?.id;
  const [workspace, setWorkspace] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [activeNoteId, setActiveNoteId] = useState("");
  const [isSavingMember, setIsSavingMember] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [editingNoteId, setEditingNoteId] = useState("");
  const [editingNoteContent, setEditingNoteContent] = useState("");
  const [roiForm, setRoiForm] = useState(emptyRoiForm);
  const [leaseAssumptionsText, setLeaseAssumptionsText] = useState(JSON.stringify(defaultLeaseAssumptions, null, 2));
  const [editingRoiId, setEditingRoiId] = useState("");
  const [isSavingRoi, setIsSavingRoi] = useState(false);
  const [roiPreview, setRoiPreview] = useState(null);
  const [roiSensitivity, setRoiSensitivity] = useState(null);
  const [roiRecommendations, setRoiRecommendations] = useState([]);
  const [selectedRoiScenarioId, setSelectedRoiScenarioId] = useState("");
  const [isSavingRoiRecommendation, setIsSavingRoiRecommendation] = useState(false);
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
        const roiSnapshot = await fetchProjectRoiSnapshot(projectId);
        if (!isMounted) {
          return;
        }
        setWorkspace((current) => ({ ...(current ?? data), members, roi_snapshot: roiSnapshot }));

        const firstScenarioId = (data.roi_scenarios && data.roi_scenarios[0]?.id) || "";
        setSelectedRoiScenarioId(firstScenarioId);
        if (firstScenarioId) {
          await loadRoiRecommendationsForScenario(firstScenarioId);
        }
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
      setActiveNoteId("create");
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
      setActiveNoteId("");
      setIsSavingNote(false);
    }
  }

  function beginNoteEdit(note) {
    setEditingNoteId(note.id);
    setEditingNoteContent(note.content);
    setErrorMessage("");
  }

  function cancelNoteEdit() {
    setEditingNoteId("");
    setEditingNoteContent("");
  }

  async function handleUpdateNote(event, noteId) {
    event.preventDefault();
    if (!editingNoteContent.trim()) {
      setErrorMessage("Enter a note before saving it.");
      return;
    }

    try {
      setIsSavingNote(true);
      setActiveNoteId(noteId);
      setErrorMessage("");
      const updatedNote = await updateProjectNote(projectId, noteId, editingNoteContent.trim());
      setWorkspace((current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          notes: current.notes.map((note) => (note.id === noteId ? updatedNote : note)),
          activity: current.activity.map((item) =>
            item.id === `activity-note-${noteId}` ? { ...item, detail: updatedNote.content } : item,
          ),
        };
      });
      cancelNoteEdit();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to update the project note.");
    } finally {
      setActiveNoteId("");
      setIsSavingNote(false);
    }
  }

  async function handleDeleteNote(noteId) {
    try {
      setIsSavingNote(true);
      setActiveNoteId(noteId);
      setErrorMessage("");
      await deleteProjectNote(projectId, noteId);
      setWorkspace((current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          notes: current.notes.filter((note) => note.id !== noteId),
          activity: current.activity.filter((item) => item.id !== `activity-note-${noteId}`),
        };
      });
      if (editingNoteId === noteId) {
        cancelNoteEdit();
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to delete the project note.");
    } finally {
      setActiveNoteId("");
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
  const canManageProject = canManageMembers;

  function syncRoiWorkspace(nextScenarios) {
    setWorkspace((current) => {
      if (!current) {
        return current;
      }
      const base = nextScenarios.find((item) => item.scenario_type === "base");
      const upside = nextScenarios.find((item) => item.scenario_type === "upside");
      const downside = nextScenarios.find((item) => item.scenario_type === "downside");
      const irrValues = nextScenarios.map((item) => item.projected_irr).filter((value) => typeof value === "number");
      const averageNpv =
        nextScenarios.length > 0
          ? nextScenarios.reduce((total, item) => total + item.projected_npv, 0) / nextScenarios.length
          : null;
      const dscrValues = nextScenarios.map((item) => item.average_dscr).filter((value) => value != null);
      return {
        ...current,
        roi_scenarios: nextScenarios,
        roi_snapshot: {
          scenario_count: nextScenarios.length,
          base_case_irr: base?.projected_irr ?? null,
          upside_case_irr: upside?.projected_irr ?? null,
          downside_case_irr: downside?.projected_irr ?? null,
          best_case_irr: irrValues.length ? Math.max(...irrValues) : null,
          average_npv: averageNpv == null ? null : Number(averageNpv.toFixed(2)),
          best_equity_multiple: nextScenarios.length
            ? Math.max(...nextScenarios.map((item) => item.equity_multiple ?? 0))
            : null,
          average_dscr: dscrValues.length
            ? Number((dscrValues.reduce((total, value) => total + value, 0) / dscrValues.length).toFixed(3))
            : null,
        },
      };
    });
  }

  function getRoiPayload() {
    let leaseAssumptions = [];
    try {
      leaseAssumptions = JSON.parse(leaseAssumptionsText || "[]");
    } catch {
      throw new Error("Lease assumptions must be valid JSON.");
    }
    return {
      ...roiForm,
      lease_assumptions: leaseAssumptions,
      listing_id: roiForm.listing_id || null,
      purchase_price: Number(roiForm.purchase_price),
      upfront_capex: Number(roiForm.upfront_capex || 0),
      annual_revenue: Number(roiForm.annual_revenue),
      vacancy_rate: Number(roiForm.vacancy_rate || 0),
      annual_operating_expenses: Number(roiForm.annual_operating_expenses),
      annual_capex_reserve: Number(roiForm.annual_capex_reserve || 0),
      annual_revenue_growth_rate: Number(roiForm.annual_revenue_growth_rate),
      annual_expense_growth_rate: Number(roiForm.annual_expense_growth_rate),
      exit_cap_rate: Number(roiForm.exit_cap_rate),
      exit_cost_rate: Number(roiForm.exit_cost_rate),
      hold_period_years: Number(roiForm.hold_period_years),
      discount_rate: Number(roiForm.discount_rate),
      leverage_ratio: Number(roiForm.leverage_ratio),
      interest_rate: Number(roiForm.interest_rate),
      interest_only_years: Number(roiForm.interest_only_years || 0),
      amortization_period_years: Number(roiForm.amortization_period_years || 0) || null,
    };
  }

  function resetRoiForm() {
    setRoiForm(emptyRoiForm);
    setLeaseAssumptionsText(JSON.stringify(defaultLeaseAssumptions, null, 2));
    setEditingRoiId("");
    setRoiPreview(null);
    setRoiSensitivity(null);
  }

  function startEditingRoi(scenario) {
    setEditingRoiId(scenario.id);
    setRoiPreview(null);
    setRoiForm({
      name: scenario.name,
      scenario_type: scenario.scenario_type,
      listing_id: scenario.listing_id ?? "",
      purchase_price: String(scenario.purchase_price),
      upfront_capex: String(scenario.upfront_capex),
      annual_revenue: String(scenario.annual_revenue),
      vacancy_rate: String(scenario.vacancy_rate ?? 0),
      annual_operating_expenses: String(scenario.annual_operating_expenses),
      annual_capex_reserve: String(scenario.annual_capex_reserve ?? 0),
      annual_revenue_growth_rate: String(scenario.annual_revenue_growth_rate),
      annual_expense_growth_rate: String(scenario.annual_expense_growth_rate),
      exit_cap_rate: String(scenario.exit_cap_rate),
      exit_cost_rate: String(scenario.exit_cost_rate),
      hold_period_years: String(scenario.hold_period_years),
      discount_rate: String(scenario.discount_rate),
      leverage_ratio: String(scenario.leverage_ratio),
      interest_rate: String(scenario.interest_rate),
      interest_only_years: String(scenario.interest_only_years ?? 0),
      amortization_period_years: String(scenario.amortization_period_years ?? 30),
    });
    setLeaseAssumptionsText(JSON.stringify(scenario.lease_assumptions ?? [], null, 2));
  }

  async function handlePreviewRoiScenario() {
    try {
      setIsSavingRoi(true);
      setErrorMessage("");
      const payload = await calculateProjectRoiScenario(projectId, getRoiPayload());
      setRoiPreview(payload);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to calculate the ROI scenario.");
    } finally {
      setIsSavingRoi(false);
    }
  }

  async function handleBuildRoiSensitivity() {
    try {
      setIsSavingRoi(true);
      setErrorMessage("");
      const payload = await buildProjectRoiSensitivity(projectId, getRoiPayload());
      setRoiSensitivity(payload);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to build the ROI sensitivity analysis.");
    } finally {
      setIsSavingRoi(false);
    }
  }

  async function loadRoiRecommendationsForScenario(scenarioId) {
    if (!scenarioId) {
      setRoiRecommendations([]);
      return;
    }
    try {
      setErrorMessage("");
      const items = await listProjectRoiRecommendations(projectId, scenarioId);
      setRoiRecommendations(items);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to load ROI recommendations.");
    }
  }

  async function handleCreateRoiRecommendation(scenarioId) {
    if (!scenarioId) {
      setErrorMessage("Pick a scenario first.");
      return;
    }

    try {
      setIsSavingRoiRecommendation(true);
      setErrorMessage("");
      await createProjectRoiRecommendation(projectId, scenarioId);
      await loadRoiRecommendationsForScenario(scenarioId);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create the ROI recommendation.");
    } finally {
      setIsSavingRoiRecommendation(false);
    }
  }

  async function handleSaveRoiScenario(event) {
    event.preventDefault();
    try {
      setIsSavingRoi(true);
      setErrorMessage("");
      const payload = getRoiPayload();
      const saved = editingRoiId
        ? await updateProjectRoiScenario(projectId, editingRoiId, payload)
        : await createProjectRoiScenario(projectId, payload);
      const currentScenarios = workspace?.roi_scenarios ?? [];
      const nextScenarios = editingRoiId
        ? currentScenarios.map((item) => (item.id === editingRoiId ? saved : item))
        : [...currentScenarios, saved];
      syncRoiWorkspace(nextScenarios);
      resetRoiForm();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to save the ROI scenario.");
    } finally {
      setIsSavingRoi(false);
    }
  }

  async function handleDeleteRoiScenario(scenarioId) {
    try {
      setIsSavingRoi(true);
      setErrorMessage("");
      await deleteProjectRoiScenario(projectId, scenarioId);
      syncRoiWorkspace((workspace?.roi_scenarios ?? []).filter((item) => item.id !== scenarioId));
      if (editingRoiId === scenarioId) {
        resetRoiForm();
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to delete the ROI scenario.");
    } finally {
      setIsSavingRoi(false);
    }
  }

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
            eyebrow="ROI Core"
            title="Scenario engine"
            description="Persist assumptions, preview outcomes, and compare base, upside, and downside cases at the project level."
          />
          <div className="project-summary-grid roi-summary-grid">
            <div className="project-summary-card">
              <span>Base IRR</span>
              <strong>{formatPercent(workspace?.roi_snapshot?.base_case_irr)}</strong>
            </div>
            <div className="project-summary-card">
              <span>Upside IRR</span>
              <strong>{formatPercent(workspace?.roi_snapshot?.upside_case_irr)}</strong>
            </div>
            <div className="project-summary-card">
              <span>Downside IRR</span>
              <strong>{formatPercent(workspace?.roi_snapshot?.downside_case_irr)}</strong>
            </div>
            <div className="project-summary-card">
              <span>Average NPV</span>
              <strong>{formatCurrency(workspace?.roi_snapshot?.average_npv)}</strong>
            </div>
            <div className="project-summary-card">
              <span>Best equity multiple</span>
              <strong>{formatDecimal(workspace?.roi_snapshot?.best_equity_multiple, 2)}x</strong>
            </div>
            <div className="project-summary-card">
              <span>Average DSCR</span>
              <strong>{formatDecimal(workspace?.roi_snapshot?.average_dscr, 2)}</strong>
            </div>
          </div>
          {canManageProject ? (
            <form className="login-form project-form" onSubmit={handleSaveRoiScenario}>
              <div className="project-summary-grid">
                <label>
                  Scenario name
                  <input
                    type="text"
                    value={roiForm.name}
                    onChange={(event) => setRoiForm((current) => ({ ...current, name: event.target.value }))}
                    placeholder="Base case"
                  />
                </label>
                <label>
                  Scenario type
                  <select
                    className="login-select"
                    value={roiForm.scenario_type}
                    onChange={(event) => setRoiForm((current) => ({ ...current, scenario_type: event.target.value }))}
                  >
                    <option value="base">Base</option>
                    <option value="upside">Upside</option>
                    <option value="downside">Downside</option>
                    <option value="custom">Custom</option>
                  </select>
                </label>
                <label>
                  Linked listing
                  <select
                    className="login-select"
                    value={roiForm.listing_id}
                    onChange={(event) => setRoiForm((current) => ({ ...current, listing_id: event.target.value }))}
                  >
                    <option value="">Project level</option>
                    {(workspace?.listings ?? []).map((listing) => (
                      <option key={listing.id} value={listing.id}>
                        {listing.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Purchase price
                  <input type="number" value={roiForm.purchase_price} onChange={(event) => setRoiForm((current) => ({ ...current, purchase_price: event.target.value }))} />
                </label>
                <label>
                  Upfront capex
                  <input type="number" value={roiForm.upfront_capex} onChange={(event) => setRoiForm((current) => ({ ...current, upfront_capex: event.target.value }))} />
                </label>
                <label>
                  Annual revenue
                  <input type="number" value={roiForm.annual_revenue} onChange={(event) => setRoiForm((current) => ({ ...current, annual_revenue: event.target.value }))} />
                </label>
                <label>
                  Vacancy %
                  <input type="number" step="0.1" value={roiForm.vacancy_rate} onChange={(event) => setRoiForm((current) => ({ ...current, vacancy_rate: event.target.value }))} />
                </label>
                <label>
                  Annual operating expenses
                  <input
                    type="number"
                    value={roiForm.annual_operating_expenses}
                    onChange={(event) => setRoiForm((current) => ({ ...current, annual_operating_expenses: event.target.value }))}
                  />
                </label>
                <label>
                  Capex reserve
                  <input type="number" value={roiForm.annual_capex_reserve} onChange={(event) => setRoiForm((current) => ({ ...current, annual_capex_reserve: event.target.value }))} />
                </label>
                <label>
                  Revenue growth %
                  <input type="number" step="0.1" value={roiForm.annual_revenue_growth_rate} onChange={(event) => setRoiForm((current) => ({ ...current, annual_revenue_growth_rate: event.target.value }))} />
                </label>
                <label>
                  Expense growth %
                  <input type="number" step="0.1" value={roiForm.annual_expense_growth_rate} onChange={(event) => setRoiForm((current) => ({ ...current, annual_expense_growth_rate: event.target.value }))} />
                </label>
                <label>
                  Exit cap %
                  <input type="number" step="0.1" value={roiForm.exit_cap_rate} onChange={(event) => setRoiForm((current) => ({ ...current, exit_cap_rate: event.target.value }))} />
                </label>
                <label>
                  Exit costs %
                  <input type="number" step="0.1" value={roiForm.exit_cost_rate} onChange={(event) => setRoiForm((current) => ({ ...current, exit_cost_rate: event.target.value }))} />
                </label>
                <label>
                  Hold period years
                  <input type="number" value={roiForm.hold_period_years} onChange={(event) => setRoiForm((current) => ({ ...current, hold_period_years: event.target.value }))} />
                </label>
                <label>
                  Discount rate %
                  <input type="number" step="0.1" value={roiForm.discount_rate} onChange={(event) => setRoiForm((current) => ({ ...current, discount_rate: event.target.value }))} />
                </label>
                <label>
                  Leverage %
                  <input type="number" step="0.1" value={roiForm.leverage_ratio} onChange={(event) => setRoiForm((current) => ({ ...current, leverage_ratio: event.target.value }))} />
                </label>
                <label>
                  Interest rate %
                  <input type="number" step="0.1" value={roiForm.interest_rate} onChange={(event) => setRoiForm((current) => ({ ...current, interest_rate: event.target.value }))} />
                </label>
                <label>
                  Interest-only years
                  <input type="number" value={roiForm.interest_only_years} onChange={(event) => setRoiForm((current) => ({ ...current, interest_only_years: event.target.value }))} />
                </label>
                <label>
                  Amortization years
                  <input type="number" value={roiForm.amortization_period_years} onChange={(event) => setRoiForm((current) => ({ ...current, amortization_period_years: event.target.value }))} />
                </label>
                <label className="project-summary-card-wide">
                  Rent roll / lease assumptions JSON
                  <textarea
                    className="login-textarea"
                    rows={10}
                    value={leaseAssumptionsText}
                    onChange={(event) => setLeaseAssumptionsText(event.target.value)}
                    placeholder='[{"tenant_name":"Anchor Tenant","monthly_rent":12000,"start_month":1,"end_month":24}]'
                  />
                </label>
              </div>
              <div className="note-edit-actions">
                <button type="button" className="ghost-button" onClick={handlePreviewRoiScenario} disabled={isSavingRoi}>
                  {isSavingRoi ? "Calculating..." : "Preview ROI"}
                </button>
                <button type="button" className="ghost-button" onClick={handleBuildRoiSensitivity} disabled={isSavingRoi}>
                  {isSavingRoi ? "Calculating..." : "Sensitivity"}
                </button>
                <button type="submit" className="primary-button" disabled={isSavingRoi}>
                  {isSavingRoi ? "Saving..." : editingRoiId ? "Update scenario" : "Save scenario"}
                </button>
                {(editingRoiId || roiPreview) ? (
                  <button type="button" className="text-button" onClick={resetRoiForm} disabled={isSavingRoi}>
                    Cancel
                  </button>
                ) : null}
              </div>
            </form>
          ) : null}
          {roiPreview ? (
            <div className="document-preview-panel">
              <div className="projects-header-row">
                <div>
                  <p className="panel-label">Preview</p>
                  <h3 className="projects-heading">{roiPreview.scenario.name}</h3>
                </div>
                <span className="status-pill status-live">{formatPercent(roiPreview.scenario.projected_irr)}</span>
              </div>
              <div className="project-summary-grid">
                <div className="project-summary-card"><span>NPV</span><strong>{formatCurrency(roiPreview.scenario.projected_npv)}</strong></div>
                <div className="project-summary-card"><span>Unlevered NPV</span><strong>{formatCurrency(roiPreview.scenario.unlevered_npv)}</strong></div>
                <div className="project-summary-card"><span>Total profit</span><strong>{formatCurrency(roiPreview.scenario.total_profit)}</strong></div>
                <div className="project-summary-card"><span>Equity invested</span><strong>{formatCurrency(roiPreview.scenario.equity_invested)}</strong></div>
                <div className="project-summary-card"><span>Equity multiple</span><strong>{formatDecimal(roiPreview.scenario.equity_multiple, 2)}x</strong></div>
                <div className="project-summary-card"><span>Unlevered IRR</span><strong>{formatPercent(roiPreview.scenario.unlevered_irr)}</strong></div>
                <div className="project-summary-card"><span>Unlevered multiple</span><strong>{formatDecimal(roiPreview.scenario.unlevered_equity_multiple, 2)}x</strong></div>
                <div className="project-summary-card"><span>Avg cash-on-cash</span><strong>{formatPercent(roiPreview.scenario.average_cash_on_cash_return)}</strong></div>
                <div className="project-summary-card"><span>Min DSCR</span><strong>{formatDecimal(roiPreview.scenario.minimum_dscr, 2)}</strong></div>
                <div className="project-summary-card"><span>Exit proceeds</span><strong>{formatCurrency(roiPreview.scenario.sale_proceeds_after_debt)}</strong></div>
                <div className="project-summary-card"><span>Lease lines</span><strong>{roiPreview.scenario.lease_assumptions?.length ?? 0}</strong></div>
              </div>
            </div>
          ) : null}
          {Array.isArray(roiPreview?.annual_cash_flows) ? (
            <div className="document-preview-panel">
              <div className="projects-header-row">
                <div>
                  <p className="panel-label">Cash flow path</p>
                  <h3 className="projects-heading">Annual breakdown</h3>
                </div>
              </div>
              <div className="activity-list">
                {roiPreview.annual_cash_flows.map((year) => (
                  <article key={year.year} className="activity-card">
                    <strong>Year {year.year}</strong>
                    <p>
                      NOI {formatCurrency(year.net_operating_income)} | Debt service {formatCurrency(year.debt_service)} | Total cash flow {formatCurrency(year.total_cash_flow)}
                    </p>
                    <small>
                      DSCR {formatDecimal(year.dscr, 2)} | Loan balance {formatCurrency(year.ending_loan_balance)}
                    </small>
                  </article>
                ))}
              </div>
            </div>
          ) : null}
          {Array.isArray(roiPreview?.monthly_cash_flows) ? (
            <div className="document-preview-panel">
              <div className="projects-header-row">
                <div>
                  <p className="panel-label">Monthly underwriting</p>
                  <h3 className="projects-heading">First 12 months</h3>
                </div>
              </div>
              <div className="activity-list">
                {roiPreview.monthly_cash_flows.slice(0, 12).map((month) => (
                  <article key={month.month} className="activity-card">
                    <strong>Month {month.month}</strong>
                    <p>
                      NOI {formatCurrency(month.net_operating_income)} | Levered {formatCurrency(month.total_cash_flow)} | Unlevered {formatCurrency(month.unlevered_cash_flow)}
                    </p>
                    <small>
                      DSCR {formatDecimal(month.dscr, 2)} | Balance {formatCurrency(month.ending_loan_balance)}
                    </small>
                  </article>
                ))}
              </div>
            </div>
          ) : null}
          {roiSensitivity?.points?.length ? (
            <div className="document-preview-panel">
              <div className="projects-header-row">
                <div>
                  <p className="panel-label">Sensitivity matrix</p>
                  <h3 className="projects-heading">Exit cap vs revenue growth</h3>
                </div>
              </div>
              <div className="activity-list">
                {roiSensitivity.points.map((point) => (
                  <article key={`${point.exit_cap_rate}-${point.annual_revenue_growth_rate}`} className="activity-card">
                    <strong>
                      Exit {formatDecimal(point.exit_cap_rate, 2)}% | Growth {formatDecimal(point.annual_revenue_growth_rate, 2)}%
                    </strong>
                    <p>
                      IRR {formatPercent(point.projected_irr)} | NPV {formatCurrency(point.projected_npv)}
                    </p>
                    <small>Equity multiple {formatDecimal(point.equity_multiple, 2)}x</small>
                  </article>
                ))}
              </div>
            </div>
          ) : null}
          <div className="project-summary-grid" style={{ marginBottom: "1rem" }}>
            <label>
              Recommendation scenario
              <select
                className="login-select"
                value={selectedRoiScenarioId}
                onChange={(event) => {
                  setSelectedRoiScenarioId(event.target.value);
                  loadRoiRecommendationsForScenario(event.target.value);
                }}
              >
                <option value="">Select scenario</option>
                {(workspace?.roi_scenarios ?? []).map((scenario) => (
                  <option key={scenario.id} value={scenario.id}>
                    {scenario.name} ({scenario.scenario_type})
                  </option>
                ))}
              </select>
            </label>
            <div>
              <button
                type="button"
                className="ghost-button"
                onClick={() => handleCreateRoiRecommendation(selectedRoiScenarioId)}
                disabled={isSavingRoiRecommendation || !selectedRoiScenarioId}
              >
                {isSavingRoiRecommendation ? "Saving..." : "Capture recommendation"}
              </button>
              <button
                type="button"
                className="ghost-button"
                onClick={async () => {
                  try {
                    setErrorMessage("");
                    const blob = await downloadProjectRoiRecommendationsPDF(projectId, selectedRoiScenarioId);
                    const url = window.URL.createObjectURL(blob);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = `roi-recommendations-${projectId}-${selectedRoiScenarioId}.pdf`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);
                  } catch (err) {
                    setErrorMessage(err instanceof Error ? err.message : "Unable to download ROI recommendations PDF.");
                  }
                }}
                disabled={!selectedRoiScenarioId}
              >
                Download PDF
              </button>
            </div>
          </div>

          <div className="note-list">
            <h4>ROI Recommendations</h4>
            {roiRecommendations && roiRecommendations.length > 0 ? (
              roiRecommendations.map((recommendation) => (
                <article key={recommendation.created_at} className="note-card">
                  <div className="note-card-header">
                    <div>
                      <strong>{recommendation.recommendation.recommendation.toUpperCase()}</strong>
                      <small>{new Date(recommendation.created_at).toLocaleString()}</small>
                    </div>
                  </div>
                  <p>
                    Conviction: {recommendation.recommendation.conviction} | Score: {recommendation.recommendation.score.toFixed(1)}
                  </p>
                  <p>{recommendation.recommendation.rationale.join(" ")}</p>
                  {recommendation.recommendation.action_items?.length ? (
                    <ul>
                      {recommendation.recommendation.action_items.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  ) : null}
                </article>
              ))
            ) : (
              <p className="hint-text">No recommendations for the selected scenario yet.</p>
            )}
          </div>

          <div className="note-list">
            {(workspace?.roi_scenarios ?? []).map((scenario) => (
              <article key={scenario.id} className="note-card">
                <div className="note-card-header">
                  <div>
                    <strong>{scenario.name}</strong>
                    <small>{scenario.scenario_type}</small>
                  </div>
                  {canManageProject ? (
                    <div className="note-card-actions">
                      <button type="button" className="text-button" onClick={() => startEditingRoi(scenario)} disabled={isSavingRoi}>
                        Edit
                      </button>
                      <button type="button" className="text-button text-button-danger" onClick={() => handleDeleteRoiScenario(scenario.id)} disabled={isSavingRoi}>
                        Delete
                      </button>
                    </div>
                  ) : null}
                </div>
                <div className="project-summary-grid roi-scenario-grid">
                  <div className="project-summary-card"><span>IRR</span><strong>{formatPercent(scenario.projected_irr)}</strong></div>
                  <div className="project-summary-card"><span>NPV</span><strong>{formatCurrency(scenario.projected_npv)}</strong></div>
                  <div className="project-summary-card"><span>Unlevered IRR</span><strong>{formatPercent(scenario.unlevered_irr)}</strong></div>
                  <div className="project-summary-card"><span>Unlevered NPV</span><strong>{formatCurrency(scenario.unlevered_npv)}</strong></div>
                  <div className="project-summary-card"><span>Equity multiple</span><strong>{formatDecimal(scenario.equity_multiple ?? scenario.cash_on_cash_multiple, 2)}x</strong></div>
                  <div className="project-summary-card"><span>Unlevered multiple</span><strong>{formatDecimal(scenario.unlevered_equity_multiple, 2)}x</strong></div>
                  <div className="project-summary-card"><span>Payback</span><strong>{formatDecimal(scenario.payback_period_years, 2)} yrs</strong></div>
                  <div className="project-summary-card"><span>Avg CoC</span><strong>{formatPercent(scenario.average_cash_on_cash_return)}</strong></div>
                  <div className="project-summary-card"><span>Min DSCR</span><strong>{formatDecimal(scenario.minimum_dscr, 2)}</strong></div>
                  <div className="project-summary-card"><span>Exit proceeds</span><strong>{formatCurrency(scenario.sale_proceeds_after_debt)}</strong></div>
                  <div className="project-summary-card"><span>Cap rate on cost</span><strong>{formatPercent(scenario.cap_rate_on_cost)}</strong></div>
                </div>
                <p>
                  Purchase {formatCurrency(scenario.purchase_price)} | Revenue {formatCurrency(scenario.annual_revenue)} | Leases {scenario.lease_assumptions?.length ?? 0} | Vacancy {formatPercent(scenario.vacancy_rate)} | Hold {scenario.hold_period_years} years
                </p>
              </article>
            ))}
            {!workspace?.roi_scenarios?.length && !isLoading ? <p className="hint-text">No ROI scenarios have been saved for this project yet.</p> : null}
          </div>
        </div>

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
                <div className="note-card-header">
                  <div>
                    <strong>{note.author_name}</strong>
                    {note.created_at ? <small>{new Date(note.created_at).toLocaleString()}</small> : null}
                  </div>
                  {canManageNote(note, workspace?.project, session?.user) ? (
                    <div className="note-card-actions">
                      <button type="button" className="text-button" onClick={() => beginNoteEdit(note)} disabled={isSavingNote}>
                        Edit
                      </button>
                      <button
                        type="button"
                        className="text-button text-button-danger"
                        onClick={() => handleDeleteNote(note.id)}
                        disabled={isSavingNote}
                      >
                        {activeNoteId === note.id ? "Removing..." : "Delete"}
                      </button>
                    </div>
                  ) : null}
                </div>
                {editingNoteId === note.id ? (
                  <form className="note-edit-form" onSubmit={(event) => handleUpdateNote(event, note.id)}>
                    <textarea
                      className="login-textarea"
                      value={editingNoteContent}
                      onChange={(event) => setEditingNoteContent(event.target.value)}
                      rows={4}
                    />
                    <div className="note-edit-actions">
                      <button type="submit" className="ghost-button" disabled={isSavingNote}>
                        {activeNoteId === note.id ? "Saving..." : "Save changes"}
                      </button>
                      <button type="button" className="text-button" onClick={cancelNoteEdit} disabled={isSavingNote}>
                        Cancel
                      </button>
                    </div>
                  </form>
                ) : (
                  <p>{note.content}</p>
                )}
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
