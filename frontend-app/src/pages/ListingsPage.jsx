import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getSession } from "../auth";
import { createListing, fetchListings, searchListings } from "../api/listingClient";
import { fetchProjects } from "../api/projectClient";
import { logoutSession } from "../api/sessionClient";
import { SectionTitle } from "../components/SectionTitle";

const emptyForm = {
  title: "",
  project_id: "",
  asset_class: "retail",
  location: "",
  asking_price: "",
  projected_irr: "",
  deal_score: "",
  summary: "",
  risk_level: "medium",
  occupancy_rate: "",
  hold_period_months: "",
  status: "pipeline",
};

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value) {
  return `${Number(value).toFixed(1)}%`;
}

function toTitleCase(value) {
  return value
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function ListingsPage() {
  const navigate = useNavigate();
  const session = getSession();
  const canManageListings = ["admin", "analyst"].includes(session?.user?.role ?? "");
  const [listings, setListings] = useState([]);
  const [projects, setProjects] = useState([]);
  const [searchValue, setSearchValue] = useState("");
  const [formState, setFormState] = useState(emptyForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [infoMessage, setInfoMessage] = useState("");

  const projectNameById = useMemo(
    () => Object.fromEntries(projects.map((project) => [project.id, project.name])),
    [projects],
  );

  useEffect(() => {
    let isMounted = true;

    async function loadPage() {
      setIsLoading(true);
      setErrorMessage("");
      try {
        const [listingData, projectData] = await Promise.all([fetchListings(), fetchProjects()]);
        if (!isMounted) {
          return;
        }
        setListings(listingData);
        setProjects(projectData);
      } catch (error) {
        if (!isMounted) {
          return;
        }
        const message = error instanceof Error ? error.message : "Unable to load listings.";
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

    loadPage();
    return () => {
      isMounted = false;
    };
  }, [navigate]);

  async function handleSearch(event) {
    event.preventDefault();
    try {
      setIsSearching(true);
      setErrorMessage("");
      const payload = await searchListings(searchValue);
      setListings(payload.results);
      setInfoMessage(searchValue.trim() ? `Found ${payload.total} listing matches.` : "");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to search listings.");
    } finally {
      setIsSearching(false);
    }
  }

  async function handleCreateListing(event) {
    event.preventDefault();
    try {
      setIsSubmitting(true);
      setErrorMessage("");
      setInfoMessage("");
      const created = await createListing({
        ...formState,
        project_id: formState.project_id || null,
        asking_price: Number(formState.asking_price),
        projected_irr: Number(formState.projected_irr),
        deal_score: Number(formState.deal_score),
        occupancy_rate: formState.occupancy_rate ? Number(formState.occupancy_rate) : null,
        hold_period_months: formState.hold_period_months ? Number(formState.hold_period_months) : null,
      });
      setListings((current) => [created, ...current]);
      setFormState(emptyForm);
      setInfoMessage(`Listing created: ${created.title}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create listing.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function resetSearch() {
    setSearchValue("");
    setErrorMessage("");
    setInfoMessage("");
    setIsSearching(true);
    try {
      const payload = await fetchListings();
      setListings(payload);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to reload listings.");
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <main className="content projects-content">
      <section className="section-block">
        <SectionTitle
          eyebrow="Catalog"
          title="Investment opportunities"
          description="Search, evaluate, and create opportunities in one place so ranking, diligence, and workspace assignment stay aligned."
        />
      </section>

      {errorMessage ? <p className="callout-message">{errorMessage}</p> : null}
      {infoMessage ? <p className="hint-text">{infoMessage}</p> : null}

      <section className="projects-shell">
        <div className="glass-card">
          <div className="projects-header-row">
            <div>
              <p className="panel-label">Opportunity catalog</p>
              <h3 className="projects-heading">Live listings</h3>
            </div>
            <span className={`status-pill ${isLoading || isSearching ? "status-pending" : errorMessage ? "status-error" : "status-live"}`}>
              {isLoading ? "Loading" : isSearching ? "Searching" : `${listings.length} visible`}
            </span>
          </div>

          <form className="login-form project-form" onSubmit={handleSearch}>
            <label>
              Search listings
              <input
                type="text"
                value={searchValue}
                onChange={(event) => setSearchValue(event.target.value)}
                placeholder="Search by title, location, asset class, or thesis"
              />
            </label>
            <div className="hero-actions">
              <button type="submit" className="primary-button" disabled={isSearching}>
                {isSearching ? "Searching..." : "Search"}
              </button>
              <button type="button" className="ghost-button" onClick={resetSearch} disabled={isSearching}>
                Reset
              </button>
            </div>
          </form>

          <div className="projects-grid">
            {listings.map((listing) => (
              <article key={listing.id} className="project-card">
                <div className="project-card-top">
                  <span>{toTitleCase(listing.asset_class)}</span>
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
                    <span>Asking price</span>
                    <strong>{formatCurrency(listing.asking_price)}</strong>
                  </div>
                  <div>
                    <span>Projected IRR</span>
                    <strong>{formatPercent(listing.projected_irr)}</strong>
                  </div>
                  <div>
                    <span>Status</span>
                    <strong>{toTitleCase(listing.status)}</strong>
                  </div>
                  <div>
                    <span>Risk level</span>
                    <strong>{toTitleCase(listing.risk_level)}</strong>
                  </div>
                  <div>
                    <span>Workspace</span>
                    <strong>{listing.project_id ? projectNameById[listing.project_id] ?? "Linked project" : "Unassigned"}</strong>
                  </div>
                </div>
              </article>
            ))}
            {!listings.length && !isLoading ? <p className="hint-text">No listings match the current view.</p> : null}
          </div>
        </div>

        <div className="glass-card">
          <p className="panel-label">Create listing</p>
          <h3 className="projects-heading">New opportunity intake</h3>
          <p className="hero-text">
            Analysts and admins can add opportunities directly into the catalog, with optional linkage to an existing project workspace.
          </p>

          {canManageListings ? (
            <form className="login-form project-form" onSubmit={handleCreateListing}>
              <label>
                Title
                <input
                  type="text"
                  value={formState.title}
                  onChange={(event) => setFormState((current) => ({ ...current, title: event.target.value }))}
                  placeholder="Nashville neighborhood retail portfolio"
                />
              </label>
              <label>
                Linked project
                <select
                  className="login-select"
                  value={formState.project_id}
                  onChange={(event) => setFormState((current) => ({ ...current, project_id: event.target.value }))}
                >
                  <option value="">No linked project</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Asset class
                <input
                  type="text"
                  value={formState.asset_class}
                  onChange={(event) => setFormState((current) => ({ ...current, asset_class: event.target.value }))}
                  placeholder="retail"
                />
              </label>
              <label>
                Location
                <input
                  type="text"
                  value={formState.location}
                  onChange={(event) => setFormState((current) => ({ ...current, location: event.target.value }))}
                  placeholder="Nashville, TN"
                />
              </label>
              <label>
                Asking price
                <input
                  type="number"
                  step="1000"
                  value={formState.asking_price}
                  onChange={(event) => setFormState((current) => ({ ...current, asking_price: event.target.value }))}
                  placeholder="12500000"
                />
              </label>
              <label>
                Projected IRR
                <input
                  type="number"
                  step="0.1"
                  value={formState.projected_irr}
                  onChange={(event) => setFormState((current) => ({ ...current, projected_irr: event.target.value }))}
                  placeholder="17.5"
                />
              </label>
              <label>
                Deal score
                <input
                  type="number"
                  step="1"
                  min="0"
                  max="100"
                  value={formState.deal_score}
                  onChange={(event) => setFormState((current) => ({ ...current, deal_score: event.target.value }))}
                  placeholder="88"
                />
              </label>
              <label>
                Risk level
                <input
                  type="text"
                  value={formState.risk_level}
                  onChange={(event) => setFormState((current) => ({ ...current, risk_level: event.target.value }))}
                  placeholder="medium"
                />
              </label>
              <label>
                Occupancy rate
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={formState.occupancy_rate}
                  onChange={(event) => setFormState((current) => ({ ...current, occupancy_rate: event.target.value }))}
                  placeholder="93"
                />
              </label>
              <label>
                Hold period months
                <input
                  type="number"
                  step="1"
                  value={formState.hold_period_months}
                  onChange={(event) => setFormState((current) => ({ ...current, hold_period_months: event.target.value }))}
                  placeholder="36"
                />
              </label>
              <label>
                Status
                <input
                  type="text"
                  value={formState.status}
                  onChange={(event) => setFormState((current) => ({ ...current, status: event.target.value }))}
                  placeholder="pipeline"
                />
              </label>
              <label>
                Investment summary
                <textarea
                  className="login-textarea"
                  value={formState.summary}
                  onChange={(event) => setFormState((current) => ({ ...current, summary: event.target.value }))}
                  placeholder="Summarize the demand signal, underwriting edge, and path to value creation."
                  rows={5}
                />
              </label>
              <button type="submit" className="primary-button login-submit" disabled={isSubmitting}>
                {isSubmitting ? "Creating listing..." : "Create listing"}
              </button>
            </form>
          ) : (
            <div className="project-locked-panel">
              <p className="hint-text">
                Your current role is <strong>{session?.user?.role ?? "viewer"}</strong>. Listing creation is limited to analysts and admins in the current authorization model.
              </p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
