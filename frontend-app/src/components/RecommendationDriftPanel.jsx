import "../styles/roi.css";

function getRecommendationColor(recommendation) {
  switch (recommendation) {
    case "invest":
      return "recommendation-invest";
    case "watch":
      return "recommendation-watch";
    case "reject":
      return "recommendation-reject";
    default:
      return "";
  }
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

function formatPercent(value) {
  if (value == null) {
    return "Not set";
  }

  return `${Number(value).toFixed(1)}%`;
}

export function RecommendationDriftPanel({ scenario, driftData, loading, error, onRefresh }) {
  return (
    <div className="roi-panel drift-panel">
      <div className="roi-panel-header">
        <h3>Recommendation Drift</h3>
        {scenario ? (
          <button type="button" className="btn-icon" onClick={onRefresh} disabled={loading} title="Refresh analysis">
            Refresh
          </button>
        ) : null}
      </div>

      <div className="roi-panel-content">
        {!scenario ? <p className="text-muted">Select a saved scenario to compare original and actuals-adjusted recommendations.</p> : null}
        {error ? <div className="alert alert-error">{error}</div> : null}
        {loading ? <div className="text-muted">Loading recommendation drift...</div> : null}

        {!loading && driftData ? (
          <>
            <div className={`alert ${driftData.recommended_action === "downgrade" ? "alert-warning" : driftData.recommended_action === "upgrade" ? "alert-info" : "alert-info"}`}>
              {driftData.recommended_action === "downgrade"
                ? "Actuals-adjusted reforecast suggests the scenario should be downgraded."
                : driftData.recommended_action === "upgrade"
                  ? "Actuals-adjusted reforecast supports an improved recommendation."
                  : "Actuals-adjusted reforecast keeps the recommendation unchanged."}
            </div>

            <div className="drift-grid">
              <div className="drift-card">
                <span className="drift-label">Original</span>
                <div className={`recommendation-badge ${getRecommendationColor(driftData.original_recommendation.recommendation)}`}>
                  <div className="recommendation-text">{driftData.original_recommendation.recommendation.toUpperCase()}</div>
                  <div className="recommendation-conviction">{driftData.original_recommendation.conviction}</div>
                </div>
                <small>Score {driftData.original_recommendation.score.toFixed(1)}</small>
              </div>
              <div className="drift-card">
                <span className="drift-label">Reforecast</span>
                <div className={`recommendation-badge ${getRecommendationColor(driftData.reforecast_recommendation.recommendation)}`}>
                  <div className="recommendation-text">{driftData.reforecast_recommendation.recommendation.toUpperCase()}</div>
                  <div className="recommendation-conviction">{driftData.reforecast_recommendation.conviction}</div>
                </div>
                <small>Score {driftData.reforecast_recommendation.score.toFixed(1)}</small>
              </div>
            </div>

            <div className="drift-meta">
              <span className="panel-chip">{driftData.actual_months_recorded} months recorded</span>
              <span className="panel-chip">{driftData.confidence} confidence</span>
              <span className="panel-chip">{driftData.drift_status}</span>
            </div>

            <div className="project-summary-grid">
              <div className="project-summary-card">
                <span>Reforecast revenue</span>
                <strong>{formatCurrency(driftData.reforecast_scenario.annual_revenue)}</strong>
              </div>
              <div className="project-summary-card">
                <span>Reforecast expenses</span>
                <strong>{formatCurrency(driftData.reforecast_scenario.annual_operating_expenses)}</strong>
              </div>
              <div className="project-summary-card">
                <span>Reforecast vacancy</span>
                <strong>{formatPercent(driftData.reforecast_scenario.vacancy_rate)}</strong>
              </div>
              <div className="project-summary-card">
                <span>Reforecast hold</span>
                <strong>{Number(driftData.reforecast_scenario.hold_period_years).toFixed(2)} yrs</strong>
              </div>
            </div>

            {driftData.summary?.length ? (
              <div className="recommendation-section">
                <h4>Drift summary</h4>
                <ul className="rationale-list">
                  {driftData.summary.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
