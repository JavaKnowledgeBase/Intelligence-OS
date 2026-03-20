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

function getConvictionLabel(conviction) {
  switch (conviction) {
    case "high":
      return "High conviction";
    case "medium":
      return "Medium conviction";
    case "low":
      return "Low conviction";
    default:
      return "Conviction pending";
  }
}

export function ROIRecommendationPanel({ scenario, analysisData, loading, error, onRefresh }) {
  const recommendation = analysisData?.recommendation;

  return (
    <div className="roi-panel roi-recommendation-panel">
      <div className="roi-panel-header">
        <h3>ROI Recommendation</h3>
        {scenario ? (
          <button type="button" className="btn-icon" onClick={onRefresh} disabled={loading} title="Refresh analysis">
            Refresh
          </button>
        ) : null}
      </div>

      <div className="roi-panel-content">
        {!scenario ? <p className="text-muted">Select a saved scenario to review its recommendation.</p> : null}
        {error ? <div className="alert alert-error">{error}</div> : null}
        {loading ? <div className="text-muted">Loading recommendation...</div> : null}

        {!loading && scenario && recommendation ? (
          <>
            <div className={`recommendation-badge ${getRecommendationColor(recommendation.recommendation)}`}>
              <div className="recommendation-text">{recommendation.recommendation.toUpperCase()}</div>
              <div className="recommendation-conviction">{getConvictionLabel(recommendation.conviction)}</div>
            </div>

            <div className="recommendation-score">
              <div className="score-label">Score</div>
              <div className="score-value">{recommendation.score.toFixed(1)}</div>
            </div>

            {recommendation.rationale?.length ? (
              <div className="recommendation-section">
                <h4>Rationale</h4>
                <ul className="rationale-list">
                  {recommendation.rationale.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {recommendation.required_assumption_checks?.length ? (
              <div className="recommendation-section">
                <h4>Required assumption checks</h4>
                <ul className="checks-list">
                  {recommendation.required_assumption_checks.map((check) => (
                    <li key={check}>{check}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {recommendation.action_items?.length ? (
              <div className="recommendation-section">
                <h4>Action items</h4>
                <ul className="actions-list">
                  {recommendation.action_items.map((item) => (
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
