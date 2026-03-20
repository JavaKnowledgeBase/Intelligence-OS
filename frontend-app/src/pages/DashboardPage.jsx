import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getSession } from "../auth";
import { logoutSession } from "../api/sessionClient";
import {
  createPortfolioSavedView,
  deletePortfolioSavedView,
  fetchPortfolioSavedViews,
  updatePortfolioSavedView,
} from "../api/portfolioSavedViewClient";
import { SectionTitle } from "../components/SectionTitle";
import { workflows } from "../data/dashboardData";
import { authenticatedFetch } from "../api/sessionClient";

const emptyDashboard = {
  overviewCards: [],
  featuredDeals: [],
  marketSignals: [],
  projectCount: 0,
  roiPortfolio: null,
};

const portfolioViews = [
  {
    key: "all",
    label: "All portfolio",
    description: "Show the full ranking, allocation, and stress picture.",
  },
  {
    key: "high_fragility",
    label: "High fragility",
    description: "Focus on scenarios that break hardest in downside stress.",
  },
  {
    key: "watchlist",
    label: "Watch recommendations",
    description: "Surface scenarios leaning toward watch instead of invest.",
  },
  {
    key: "retail_only",
    label: "Retail only",
    description: "Limit the portfolio view to retail or retail-adjacent projects.",
  },
];

function formatCompactNumber(value) {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
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

function buildOverviewCards(overview, listings) {
  const highScoreDeals = listings.filter((listing) => listing.deal_score >= 85).length;
  const averageIrr =
    listings.length > 0
      ? listings.reduce((total, listing) => total + listing.projected_irr, 0) / listings.length
      : 0;

  return [
    {
      label: "Tracked deals",
      value: formatCompactNumber(overview.total_listings),
      change: `${overview.total_projects} active projects`,
    },
    {
      label: "Average modeled IRR",
      value: formatPercent(averageIrr),
      change: `${formatPercent(overview.average_deal_score / 5)} score-weighted confidence`,
    },
    {
      label: "AI-ranked opportunities",
      value: formatCompactNumber(highScoreDeals),
      change: `${listings.length - highScoreDeals} need review`,
    },
    {
      label: "Active projects",
      value: formatCompactNumber(overview.total_projects),
      change: `${overview.market_insights.length} live market signals`,
    },
  ];
}

function mapFeaturedDeals(listings) {
  return listings.map((listing) => ({
    id: listing.id,
    projectId: listing.project_id,
    title: listing.title,
    type: toTitleCase(listing.asset_class),
    score: listing.deal_score,
    irr: formatPercent(listing.projected_irr),
    thesis: listing.summary,
  }));
}

function mapMarketSignals(signals) {
  return signals.map((signal) => ({
    region: signal.region,
    trend: toTitleCase(signal.trend),
    detail: signal.signal,
    confidence: `${Math.round(signal.confidence * 100)}% confidence`,
  }));
}

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

function getFragilityLabel(value) {
  return toTitleCase(value || "unknown");
}

async function fetchJson(path) {
  const response = await authenticatedFetch(path);
  if (!response.ok) {
    throw new Error(`Request failed for ${path} with status ${response.status}`);
  }
  return response.json();
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const session = getSession();
  const currentUserId = session?.user?.id || "";
  const [dashboard, setDashboard] = useState(emptyDashboard);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [savedViews, setSavedViews] = useState([]);
  const [newSavedViewName, setNewSavedViewName] = useState("");
  const [newSavedViewShared, setNewSavedViewShared] = useState(false);
  const [editingSavedViewId, setEditingSavedViewId] = useState("");
  const [editingSavedViewName, setEditingSavedViewName] = useState("");
  const [editingSavedViewPortfolio, setEditingSavedViewPortfolio] = useState("all");
  const [editingSavedViewShared, setEditingSavedViewShared] = useState(false);
  const activePortfolioView = searchParams.get("portfolio") || "all";

  useEffect(() => {
    let isMounted = true;

    async function loadDashboard() {
      setIsLoading(true);
      setErrorMessage("");

      try {
        const [overview, listings, marketSignals, savedPortfolioViews] = await Promise.all([
          fetchJson("/projects/overview"),
          fetchJson("/listings"),
          fetchJson("/market/insights"),
          fetchPortfolioSavedViews(),
        ]);

        if (!isMounted) {
          return;
        }

        setDashboard({
          overviewCards: buildOverviewCards(overview, listings),
          featuredDeals: mapFeaturedDeals(overview.featured_deals),
          marketSignals: mapMarketSignals(marketSignals),
          projectCount: overview.total_projects,
          roiPortfolio: overview.roi_portfolio,
        });
        setSavedViews(savedPortfolioViews);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setErrorMessage(
          error instanceof Error
            ? `${error.message}. Make sure the backend is running on http://localhost:8000.`
            : "Unable to load dashboard data.",
        );
        if (error instanceof Error && error.message.includes("401")) {
          await logoutSession();
          navigate("/login", { replace: true });
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    const view = searchParams.get("view");
    if (!view) {
      return;
    }
    const target = document.getElementById(`dashboard-${view}`);
    if (!target) {
      return;
    }
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [searchParams, dashboard.roiPortfolio]);

  function openProjectWorkspace(projectId, scenarioId = "", source = "") {
    const nextParams = new URLSearchParams();
    if (scenarioId) {
      nextParams.set("scenario", scenarioId);
    }
    if (source) {
      nextParams.set("from", source);
    }
    if (activePortfolioView && activePortfolioView !== "all") {
      nextParams.set("portfolio", activePortfolioView);
    }
    const search = nextParams.toString() ? `?${nextParams.toString()}` : "";
    navigate(`/projects/${projectId}${search}`);
  }

  function setPortfolioView(viewKey) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (viewKey === "all") {
        next.delete("portfolio");
      } else {
        next.set("portfolio", viewKey);
      }
      return next;
    }, { replace: true });
  }

  async function saveCurrentPortfolioView() {
    const trimmedName = newSavedViewName.trim();
    if (!trimmedName) {
      setErrorMessage("Enter a short name before saving a portfolio view.");
      return;
    }
    try {
      setErrorMessage("");
      const created = await createPortfolioSavedView({
        name: trimmedName,
        portfolio_view: activePortfolioView,
        is_shared: newSavedViewShared,
      });
      setSavedViews((current) => [created, ...current.filter((item) => item.id !== created.id)].slice(0, 12));
      setNewSavedViewName("");
      setNewSavedViewShared(false);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to save the current portfolio view.");
    }
  }

  function openSavedPortfolioView(savedView) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (savedView.portfolio_view && savedView.portfolio_view !== "all") {
        next.set("portfolio", savedView.portfolio_view);
      } else {
        next.delete("portfolio");
      }
      return next;
    }, { replace: true });
  }

  async function handleDeleteSavedPortfolioView(savedViewId) {
    try {
      setErrorMessage("");
      await deletePortfolioSavedView(savedViewId);
      setSavedViews((current) => current.filter((item) => item.id !== savedViewId));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to delete the saved portfolio view.");
    }
  }

  function beginSavedViewEdit(savedView) {
    setEditingSavedViewId(savedView.id);
    setEditingSavedViewName(savedView.name);
    setEditingSavedViewPortfolio(savedView.portfolio_view);
    setEditingSavedViewShared(savedView.is_shared);
  }

  function cancelSavedViewEdit() {
    setEditingSavedViewId("");
    setEditingSavedViewName("");
    setEditingSavedViewPortfolio("all");
    setEditingSavedViewShared(false);
  }

  async function saveSavedViewEdit() {
    if (!editingSavedViewId) {
      return;
    }
    const trimmedName = editingSavedViewName.trim();
    if (!trimmedName) {
      setErrorMessage("Enter a short name before updating a saved view.");
      return;
    }
    try {
      setErrorMessage("");
      const updated = await updatePortfolioSavedView(editingSavedViewId, {
        name: trimmedName,
        portfolio_view: editingSavedViewPortfolio,
        is_shared: editingSavedViewShared,
      });
      setSavedViews((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      cancelSavedViewEdit();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to update the saved portfolio view.");
    }
  }

  const filteredPortfolio = useMemo(() => {
    if (!dashboard.roiPortfolio) {
      return null;
    }

    const matchesView = (item) => {
      if (activePortfolioView === "high_fragility") {
        return item.fragility === "high" || item.ranking?.recommendation === "reject";
      }
      if (activePortfolioView === "watchlist") {
        return item.ranking?.recommendation === "watch" || item.recommendation === "watch";
      }
      if (activePortfolioView === "retail_only") {
        return String(item.project_type || "").toLowerCase().includes("retail");
      }
      return true;
    };

    const topScenarios = dashboard.roiPortfolio.top_scenarios.filter(matchesView);
    const capitalAllocation = dashboard.roiPortfolio.capital_allocation.filter(matchesView);
    const downsideStressViews = dashboard.roiPortfolio.downside_stress_views.filter(matchesView);

    return {
      ...dashboard.roiPortfolio,
      top_scenarios: topScenarios,
      capital_allocation: capitalAllocation,
      downside_stress_views: downsideStressViews,
    };
  }, [activePortfolioView, dashboard.roiPortfolio]);

  return (
    <>
      <div className="hero-grid">
        <div className="hero-copy">
          <p className="eyebrow">Investment intelligence platform</p>
          <h2>Rank deals, model ROI, and turn market noise into investment decisions.</h2>
          <p className="hero-text">
            A React control room for investors, analysts, and operators, backed by Python services for
            deal analytics, scoring, market intelligence, and alerts.
          </p>
          <div className="hero-actions">
            <button className="primary-button" type="button" onClick={() => navigate("/projects")}>
              Open workspace
            </button>
            <button className="ghost-button" type="button" onClick={() => navigate("/listings")}>
              Browse listings
            </button>
          </div>
        </div>

        <div className="hero-panel">
          <div className="status-row">
            <p className="panel-label">Live pipeline</p>
            <span className={`status-pill ${isLoading ? "status-pending" : errorMessage ? "status-error" : "status-live"}`}>
              {isLoading ? "Loading" : errorMessage ? "Backend offline" : "Live"}
            </span>
          </div>
          {errorMessage ? (
            <p className="callout-message">{errorMessage}</p>
          ) : (
            <div className="pipeline-list">
              <div>
                <strong>1. Ingestion</strong>
                <span>{dashboard.projectCount} shared projects feeding the active workspace</span>
              </div>
              <div>
                <strong>2. ROI Engine</strong>
                <span>Live projected IRR metrics are being pulled from the platform core API.</span>
              </div>
              <div>
                <strong>3. AI Ranking</strong>
                <span>Featured listings are coming from the ranked deal payload served by FastAPI.</span>
              </div>
              <div>
                <strong>4. Delivery</strong>
                <span>Market insight cards update from backend signals instead of static frontend data.</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <main className="content">
        <section className="overview-grid">
          {dashboard.overviewCards.map((card) => (
            <article key={card.label} className="metric-card">
              <span>{card.label}</span>
              <strong>{card.value}</strong>
              <p>{card.change}</p>
            </article>
          ))}
        </section>

        {filteredPortfolio ? (
          <section className="section-block">
            <SectionTitle
              eyebrow="Saved views"
              title="Portfolio filters"
              description="Jump directly into the slice of the portfolio you want to review without leaving the dashboard."
            />
            <div className="hero-actions">
              {portfolioViews.map((view) => (
                <button
                  key={view.key}
                  type="button"
                  className={activePortfolioView === view.key ? "primary-button" : "ghost-button"}
                  onClick={() => setPortfolioView(view.key)}
                  title={view.description}
                >
                  {view.label}
                </button>
              ))}
            </div>
            <div className="glass-card" style={{ marginTop: "1rem" }}>
              <div className="projects-header-row">
                <div>
                  <p className="panel-label">My saved views</p>
                  <h3 className="projects-heading">Personal portfolio lenses</h3>
                </div>
              </div>
              <div className="hero-actions">
                <input
                  type="text"
                  value={newSavedViewName}
                  onChange={(event) => setNewSavedViewName(event.target.value)}
                  placeholder="Name this current filter"
                />
                <label>
                  <input
                    type="checkbox"
                    checked={newSavedViewShared}
                    onChange={(event) => setNewSavedViewShared(event.target.checked)}
                  />
                  Share with team
                </label>
                <button type="button" className="ghost-button" onClick={saveCurrentPortfolioView}>
                  Save current view
                </button>
              </div>
              <div className="activity-list">
                {savedViews.map((item) => (
                  <article key={item.id} className="activity-card">
                    {editingSavedViewId === item.id ? (
                      <>
                        <input
                          type="text"
                          value={editingSavedViewName}
                          onChange={(event) => setEditingSavedViewName(event.target.value)}
                        />
                        <select
                          className="login-select"
                          value={editingSavedViewPortfolio}
                          onChange={(event) => setEditingSavedViewPortfolio(event.target.value)}
                        >
                          {portfolioViews.map((view) => (
                            <option key={view.key} value={view.key}>
                              {view.label}
                            </option>
                          ))}
                        </select>
                        <label>
                          <input
                            type="checkbox"
                            checked={editingSavedViewShared}
                            onChange={(event) => setEditingSavedViewShared(event.target.checked)}
                          />
                          Share with team
                        </label>
                        <div className="note-card-actions">
                          <button type="button" className="text-button" onClick={saveSavedViewEdit}>
                            Save
                          </button>
                          <button type="button" className="text-button" onClick={cancelSavedViewEdit}>
                            Cancel
                          </button>
                        </div>
                      </>
                    ) : (
                      <>
                        <strong>{item.name}</strong>
                        <p>{portfolioViews.find((view) => view.key === item.portfolio_view)?.label ?? "All portfolio"}</p>
                        <small>{new Date(item.created_at).toLocaleString()}</small>
                        <small>{item.is_shared ? `Shared by ${item.created_by_name}` : `Personal view by ${item.created_by_name}`}</small>
                        <div className="note-card-actions">
                          <button type="button" className="text-button" onClick={() => openSavedPortfolioView(item)}>
                            Open
                          </button>
                          {item.created_by === currentUserId ? (
                            <>
                              <button type="button" className="text-button" onClick={() => beginSavedViewEdit(item)}>
                                Edit
                              </button>
                              <button type="button" className="text-button text-button-danger" onClick={() => handleDeleteSavedPortfolioView(item.id)}>
                                Delete
                              </button>
                            </>
                          ) : null}
                        </div>
                      </>
                    )}
                  </article>
                ))}
                {!savedViews.length ? <p className="hint-text">No personal saved views yet. Pick a portfolio slice and save it here.</p> : null}
              </div>
            </div>
          </section>
        ) : null}

        <section className="section-block">
          <SectionTitle
            eyebrow="Featured"
            title="AI-ranked opportunities"
            description="The first release now reads its featured opportunities from the FastAPI platform core."
          />
          <div className="deal-grid">
            {dashboard.featuredDeals.map((deal) => (
              <article key={deal.id} className="deal-card">
                <div className="deal-card-top">
                  <span>{deal.type}</span>
                  <strong>{deal.score}</strong>
                </div>
                <h3>{deal.title}</h3>
                <p>{deal.thesis}</p>
                <div className="deal-footer">
                  <span>Modeled IRR</span>
                  <strong>{deal.irr}</strong>
                </div>
                <div className="hero-actions" style={{ marginTop: "0.85rem" }}>
                  <button className="text-button" type="button" onClick={() => navigate("/listings")}>
                    Open listings
                  </button>
                  {deal.projectId ? (
                    <button
                      className="text-button"
                      type="button"
                      onClick={() => openProjectWorkspace(deal.projectId, "", "allocation")}
                    >
                      Open workspace
                    </button>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="split-panel">
          <div className="glass-card">
            <SectionTitle
              eyebrow="Signals"
              title="Market intelligence"
              description="Regional demand, pricing, and operational pressure indicators help the scoring model explain why a deal is moving."
            />
            <div className="signal-list">
              {dashboard.marketSignals.map((signal) => (
                <div key={signal.region} className="signal-row">
                  <div>
                    <strong>{signal.region}</strong>
                    <p>{signal.detail}</p>
                  </div>
                  <div className="signal-meta">
                    <span>{signal.trend}</span>
                    <small>{signal.confidence}</small>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card">
            <SectionTitle
              eyebrow="Foundation"
              title="Shared platform workflows"
              description="The project model stays shared so retail, valuation, and ROI packs can plug into the same platform core."
            />
            <ul className="workflow-list">
              {workflows.map((workflow) => (
                <li key={workflow}>{workflow}</li>
              ))}
            </ul>
          </div>
        </section>

        {filteredPortfolio ? (
          <section className="split-panel">
            <div className="glass-card" id="dashboard-ranking">
              <SectionTitle
                eyebrow="Portfolio ROI"
                title="Risk-adjusted scenario rankings"
                description="Compare modeled scenarios across the tenant portfolio and surface the strongest and weakest positions first."
              />
              <div className="project-summary-grid">
                <div className="project-summary-card">
                  <span>ROI projects</span>
                  <strong>{filteredPortfolio.total_roi_projects}</strong>
                </div>
                <div className="project-summary-card">
                  <span>ROI scenarios</span>
                  <strong>{filteredPortfolio.total_roi_scenarios}</strong>
                </div>
                <div className="project-summary-card">
                  <span>Avg risk-adjusted score</span>
                  <strong>{filteredPortfolio.average_risk_adjusted_score?.toFixed(1) ?? "Not set"}</strong>
                </div>
                <div className="project-summary-card">
                  <span>Downside exposure</span>
                  <strong>{filteredPortfolio.downside_exposure_count}</strong>
                </div>
              </div>
              <div className="activity-list">
                {filteredPortfolio.top_scenarios.map((item) => (
                  <article key={`${item.project_id}-${item.ranking.scenario_id}`} className="activity-card">
                    <strong>
                      {item.project_name} - {item.ranking.scenario_name}
                    </strong>
                    <p>
                      {item.project_type} | {toTitleCase(item.ranking.scenario_type)} | Recommendation {item.ranking.recommendation?.toUpperCase() ?? "N/A"}
                    </p>
                    <small>
                      Risk-adjusted score {item.ranking.risk_adjusted_score.toFixed(1)}
                      {item.ranking.projected_irr != null ? ` | IRR ${formatPercent(item.ranking.projected_irr)}` : ""}
                      {item.ranking.projected_npv != null ? ` | NPV ${formatCurrency(item.ranking.projected_npv)}` : ""}
                    </small>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => openProjectWorkspace(item.project_id, item.ranking.scenario_id, "ranking")}
                    >
                      Open scenario
                    </button>
                  </article>
                ))}
                {!filteredPortfolio.top_scenarios.length ? <p className="hint-text">No scenario rankings match this saved view.</p> : null}
              </div>
            </div>

            <div className="glass-card" id="dashboard-allocation">
              <SectionTitle
                eyebrow="Allocation"
                title="Capital concentration view"
                description="See where modeled budget and scenario density are clustering so the team can judge concentration before allocating more capital."
              />
              <div className="activity-list">
                {filteredPortfolio.capital_allocation.map((item) => (
                  <article key={item.project_id} className="activity-card">
                    <strong>{item.project_name}</strong>
                    <p>
                      {item.project_type} | Budget {formatCurrency(item.budget_amount)} | Weight{" "}
                      {item.budget_weight_percent != null ? `${item.budget_weight_percent.toFixed(1)}%` : "Not set"}
                    </p>
                    <small>
                      {item.scenario_count} scenarios | Best risk-adjusted score{" "}
                      {item.best_risk_adjusted_score != null ? item.best_risk_adjusted_score.toFixed(1) : "Not set"}
                    </small>
                    <button type="button" className="text-button" onClick={() => openProjectWorkspace(item.project_id, "", "allocation")}>
                      Open project
                    </button>
                  </article>
                ))}
                {!filteredPortfolio.capital_allocation.length ? <p className="hint-text">No capital-allocation rows match this saved view.</p> : null}
              </div>
              <div className="project-summary-grid">
                <div className="project-summary-card">
                  <span>Invest</span>
                  <strong>{filteredPortfolio.invest_count}</strong>
                </div>
                <div className="project-summary-card">
                  <span>Watch</span>
                  <strong>{filteredPortfolio.watch_count}</strong>
                </div>
                <div className="project-summary-card">
                  <span>Reject</span>
                  <strong>{filteredPortfolio.reject_count}</strong>
                </div>
              </div>
            </div>
          </section>
        ) : null}

        {filteredPortfolio ? (
          <section className="section-block" id="dashboard-stress">
            <SectionTitle
              eyebrow="Stress"
              title="Downside fragility watchlist"
              description="See which scenarios lose the most value under the combined downside case so the team can focus diligence and mitigation where it matters most."
            />
            <div className="activity-list">
              {filteredPortfolio.downside_stress_views.map((item) => (
                <article key={`${item.project_id}-${item.scenario_id}`} className="activity-card">
                  <strong>
                    {item.project_name} - {item.scenario_name}
                  </strong>
                  <p>
                    {item.project_type} | {toTitleCase(item.scenario_type)} | Fragility {getFragilityLabel(item.fragility)}
                  </p>
                  <small>
                    Base IRR {formatPercent(item.base_irr)} | Downside IRR {formatPercent(item.stressed_irr)} | Compression {formatPercent(item.irr_compression)}
                  </small>
                  <small>
                    Base NPV {formatCurrency(item.base_npv)} | Downside NPV {formatCurrency(item.stressed_npv)} | Drawdown {formatCurrency(item.npv_drawdown)}
                  </small>
                  <small>Downside min DSCR {item.minimum_dscr != null ? item.minimum_dscr.toFixed(2) : "Not set"}</small>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => openProjectWorkspace(item.project_id, item.scenario_id, "stress")}
                    >
                      Review in workspace
                    </button>
                </article>
              ))}
              {!filteredPortfolio.downside_stress_views.length ? <p className="hint-text">No downside stress rows match this saved view.</p> : null}
            </div>
          </section>
        ) : null}
      </main>
    </>
  );
}
