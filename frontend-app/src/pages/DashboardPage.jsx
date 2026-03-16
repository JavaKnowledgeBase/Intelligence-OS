import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { logoutSession } from "../api/sessionClient";
import { SectionTitle } from "../components/SectionTitle";
import { workflows } from "../data/dashboardData";
import { authenticatedFetch } from "../api/sessionClient";

const emptyDashboard = {
  overviewCards: [],
  featuredDeals: [],
  marketSignals: [],
  projectCount: 0,
};

function formatCompactNumber(value) {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
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

async function fetchJson(path) {
  const response = await authenticatedFetch(path);
  if (!response.ok) {
    throw new Error(`Request failed for ${path} with status ${response.status}`);
  }
  return response.json();
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(emptyDashboard);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadDashboard() {
      setIsLoading(true);
      setErrorMessage("");

      try {
        const [overview, listings, marketSignals] = await Promise.all([
          fetchJson("/projects/overview"),
          fetchJson("/listings"),
          fetchJson("/market/insights"),
        ]);

        if (!isMounted) {
          return;
        }

        setDashboard({
          overviewCards: buildOverviewCards(overview, listings),
          featuredDeals: mapFeaturedDeals(overview.featured_deals),
          marketSignals: mapMarketSignals(marketSignals),
          projectCount: overview.total_projects,
        });
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
            <button className="ghost-button" type="button" onClick={() => navigate("/architecture")}>
              Review architecture
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
      </main>
    </>
  );
}
