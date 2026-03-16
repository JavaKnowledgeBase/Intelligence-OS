import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getSession } from "../auth";
import { createProject, fetchProjects } from "../api/projectClient";
import { logoutSession } from "../api/sessionClient";
import { FileUploadPanel } from "../components/FileUploadPanel";
import { SectionTitle } from "../components/SectionTitle";

const emptyForm = {
  name: "",
  project_type: "acquisition",
  owner: "Ravi Kafley",
  stage: "screening",
  investment_thesis: "",
  target_irr: "",
  budget_amount: "",
};

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

function toTitleCase(value) {
  return value
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function ProjectsPage() {
  const navigate = useNavigate();
  const session = getSession();
  const canCreateProjects = ["admin", "analyst"].includes(session?.user?.role ?? "");
  const [projects, setProjects] = useState([]);
  const [formState, setFormState] = useState(emptyForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [infoMessage, setInfoMessage] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadProjects() {
      setIsLoading(true);
      setErrorMessage("");

      try {
        const data = await fetchProjects();
        if (!isMounted) {
          return;
        }
        setProjects(data);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        const message = error instanceof Error ? error.message : "Unable to load projects.";
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

    loadProjects();

    return () => {
      isMounted = false;
    };
  }, [navigate]);

  async function handleCreateProject(event) {
    event.preventDefault();
    setErrorMessage("");
    setInfoMessage("");

    try {
      setIsSubmitting(true);
      const createdProject = await createProject({
        ...formState,
        target_irr: formState.target_irr ? Number(formState.target_irr) : null,
        budget_amount: formState.budget_amount ? Number(formState.budget_amount) : null,
      });
      setProjects((current) => [createdProject, ...current]);
      setFormState({
        ...emptyForm,
        owner: session?.user?.full_name ?? "Ravi Kafley",
      });
      setInfoMessage(`Project created: ${createdProject.name}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create project.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="content projects-content">
      <section className="section-block">
        <SectionTitle
          eyebrow="Workspace"
          title="Shared projects"
          description="Manage live investment workspaces, see ownership and stage at a glance, and create new projects from the governed platform model."
        />
      </section>

      <section className="projects-shell">
        <div className="glass-card">
          <div className="projects-header-row">
            <div>
              <p className="panel-label">Project registry</p>
              <h3 className="projects-heading">Active workspace list</h3>
            </div>
            <span className={`status-pill ${isLoading ? "status-pending" : errorMessage ? "status-error" : "status-live"}`}>
              {isLoading ? "Loading" : errorMessage ? "Attention needed" : `${projects.length} loaded`}
            </span>
          </div>

          {errorMessage ? <p className="callout-message">{errorMessage}</p> : null}

          <div className="projects-grid">
            {projects.map((project) => (
              <article key={project.id} className="project-card">
                <div className="project-card-top">
                  <span>{toTitleCase(project.project_type)}</span>
                  <strong>{toTitleCase(project.stage)}</strong>
                </div>
                <h3>{project.name}</h3>
                <p>{project.investment_thesis || "Investment thesis not captured yet for this workspace."}</p>
                <div className="project-meta-grid">
                  <div>
                    <span>Owner</span>
                    <strong>{project.owner}</strong>
                  </div>
                  <div>
                    <span>Target IRR</span>
                    <strong>{formatPercent(project.target_irr)}</strong>
                  </div>
                  <div>
                    <span>Budget</span>
                    <strong>{formatCurrency(project.budget_amount)}</strong>
                  </div>
                  <div>
                    <span>Deal slots</span>
                    <strong>{project.active_deals}</strong>
                  </div>
                </div>
                <div className="project-card-actions">
                  <button className="ghost-button" type="button" onClick={() => navigate(`/projects/${project.id}`)}>
                    Open workspace
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="glass-card">
          <p className="panel-label">Create workspace</p>
          <h3 className="projects-heading">New project intake</h3>
          <p className="hero-text">
            Analysts and admins can open new shared projects so listings, ROI logic, alerts, and future documents stay connected to one tenant-aware workspace.
          </p>

          {canCreateProjects ? (
            <form className="login-form project-form" onSubmit={handleCreateProject}>
              <label>
                Project name
                <input
                  type="text"
                  value={formState.name}
                  onChange={(event) => setFormState((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Sunbelt Retail Rollup"
                />
              </label>
              <label>
                Project type
                <input
                  type="text"
                  value={formState.project_type}
                  onChange={(event) => setFormState((current) => ({ ...current, project_type: event.target.value }))}
                  placeholder="acquisition"
                />
              </label>
              <label>
                Stage
                <input
                  type="text"
                  value={formState.stage}
                  onChange={(event) => setFormState((current) => ({ ...current, stage: event.target.value }))}
                  placeholder="screening"
                />
              </label>
              <label>
                Owner
                <input
                  type="text"
                  value={formState.owner}
                  onChange={(event) => setFormState((current) => ({ ...current, owner: event.target.value }))}
                  placeholder="Ravi Kafley"
                />
              </label>
              <label>
                Target IRR
                <input
                  type="number"
                  step="0.1"
                  value={formState.target_irr}
                  onChange={(event) => setFormState((current) => ({ ...current, target_irr: event.target.value }))}
                  placeholder="18.0"
                />
              </label>
              <label>
                Budget amount
                <input
                  type="number"
                  step="1000"
                  value={formState.budget_amount}
                  onChange={(event) => setFormState((current) => ({ ...current, budget_amount: event.target.value }))}
                  placeholder="2500000"
                />
              </label>
              <label>
                Investment thesis
                <textarea
                  className="login-textarea"
                  value={formState.investment_thesis}
                  onChange={(event) => setFormState((current) => ({ ...current, investment_thesis: event.target.value }))}
                  placeholder="Summarize the operating edge, demand signal, or value-creation thesis."
                  rows={5}
                />
              </label>
              <button type="submit" className="primary-button login-submit" disabled={isSubmitting}>
                {isSubmitting ? "Creating workspace..." : "Create project"}
              </button>
            </form>
          ) : (
            <div className="project-locked-panel">
              <p className="hint-text">
                Your current role is <strong>{session?.user?.role ?? "viewer"}</strong>. Project creation is limited to analysts and admins in the current authorization model.
              </p>
              <button className="ghost-button" type="button" onClick={() => navigate("/login")}>
                Request elevated access
              </button>
            </div>
          )}

          {infoMessage ? <p className="hint-text">{infoMessage}</p> : null}

          <div className="project-side-stack">
            <FileUploadPanel
              title="Project evidence upload"
              description="Use the same upload module for deal memos, underwriting packs, lease schedules, or later ingestion-ready evidence files."
              buttonLabel="Stage evidence file"
              helperText="Project-scoped document uploads are live inside each project workspace."
            />
          </div>
        </div>
      </section>
    </main>
  );
}
