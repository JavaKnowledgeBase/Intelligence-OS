import "../styles/roi.css";

function getAssessmentColor(assessment) {
  switch (assessment) {
    case "outperform":
      return "assessment-outperform";
    case "mixed":
      return "assessment-mixed";
    case "underperform":
      return "assessment-underperform";
    default:
      return "";
  }
}

function getStatusIndicator(status) {
  switch (status) {
    case "above":
      return "Above range";
    case "within":
      return "Within range";
    case "below":
      return "Below range";
    case "unavailable":
      return "Not available";
    default:
      return "Unknown";
  }
}

function formatMetricValue(value) {
  if (value === null || value === undefined) {
    return "Not set";
  }

  if (typeof value === "number") {
    return value.toFixed(2);
  }

  return String(value);
}

function formatCompInfluence(influence) {
  switch (influence) {
    case "used":
      return "Used in calibration";
    case "downweighted":
      return "Used with lower weight";
    case "forced":
      return "Forced into calibration";
    case "excluded_outlier":
      return "Excluded as outlier";
    case "excluded_by_analyst":
      return "Excluded by analyst";
    case "not_used":
      return "Not selected for final range";
    default:
      return "Calibration status unavailable";
  }
}

function formatMetricName(metric) {
  return metric.replaceAll("_", " ");
}

export function BenchmarkAssessmentPanel({ scenario, benchmarkAssessment, benchmarkContext, loading, error, onRefresh }) {
  const assessment = benchmarkAssessment?.benchmark_assessment || benchmarkAssessment;

  return (
    <div className="roi-panel benchmark-panel">
      <div className="roi-panel-header">
        <h3>Benchmark Assessment</h3>
        {scenario ? (
          <button type="button" className="btn-icon" onClick={onRefresh} disabled={loading} title="Refresh analysis">
            Refresh
          </button>
        ) : null}
      </div>

      <div className="roi-panel-content">
        {!scenario ? <p className="text-muted">Select a saved scenario to compare it with benchmark ranges.</p> : null}
        {error ? <div className="alert alert-error">{error}</div> : null}
        {loading ? <div className="text-muted">Loading benchmark assessment...</div> : null}
        {!loading && scenario && !assessment ? <div className="alert alert-info">No benchmark assessment is available yet.</div> : null}

        {!loading && assessment ? (
          <>
            <div className="benchmark-header">
              <div className="benchmark-profile">
                <span className="profile-label">Profile</span>
                <span className="profile-value">{assessment.benchmark_profile || "Default market benchmark"}</span>
              </div>
              <div className={`assessment-badge ${getAssessmentColor(assessment.overall_assessment)}`}>
                {(assessment.overall_assessment || "mixed").toUpperCase()}
              </div>
              <div className="confidence-badge">
                Confidence <strong>{(assessment.confidence || "medium").toUpperCase()}</strong>
              </div>
            </div>

            {assessment.metrics?.length ? (
              <div className="benchmark-metrics">
                <h4>Metric comparison</h4>
                <div className="metrics-table-container">
                  <table className="metrics-table">
                    <thead>
                      <tr>
                        <th>Metric</th>
                        <th>Actual</th>
                        <th>Min</th>
                        <th>Max</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {assessment.metrics.map((metric) => (
                        <tr key={metric.metric} className={`metric-row status-${metric.status}`}>
                          <td className="metric-name">{metric.metric}</td>
                          <td className="metric-value">{formatMetricValue(metric.actual)}</td>
                          <td className="metric-value">{formatMetricValue(metric.benchmark_min)}</td>
                          <td className="metric-value">{formatMetricValue(metric.benchmark_max)}</td>
                          <td className="metric-status">{getStatusIndicator(metric.status)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}

            {assessment.notes?.length ? (
              <div className="benchmark-notes">
                <h4>Calibration notes</h4>
                <ul className="notes-list">
                  {assessment.notes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {benchmarkContext ? (
              <div className="benchmark-context">
                <div className="benchmark-context-header">
                  <h4>Comp set behind this view</h4>
                  <div className="benchmark-context-stats">
                    <span>{benchmarkContext.effective_comp_count} active</span>
                    <span>{benchmarkContext.comp_count} included</span>
                    {benchmarkContext.location ? <span>{benchmarkContext.location}</span> : null}
                  </div>
                </div>

                {benchmarkContext.comps?.length ? (
                  <div className="benchmark-comp-list">
                    {benchmarkContext.comps.map((comp) => (
                      <article key={comp.comp_id} className={`benchmark-comp-card influence-${comp.influence}`}>
                        <div className="benchmark-comp-topline">
                          <div>
                            <strong>{comp.source_name}</strong>
                            <p>{comp.location}</p>
                          </div>
                          <span className="benchmark-comp-impact">{formatCompInfluence(comp.influence)}</span>
                        </div>
                        <div className="benchmark-comp-tags">
                          <span>{comp.fit_label}</span>
                          <span>{comp.freshness_label}</span>
                          <span>{comp.override_mode.replaceAll("_", " ")}</span>
                          {typeof comp.weight === "number" ? <span>Weight {comp.weight.toFixed(2)}</span> : null}
                        </div>
                        {comp.contributing_metrics?.length ? (
                          <p className="benchmark-comp-metrics">
                            Influenced: {comp.contributing_metrics.map(formatMetricName).join(", ")}
                          </p>
                        ) : null}
                        {comp.note ? <p className="benchmark-comp-note">{comp.note}</p> : null}
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted">No active comparable records are attached to this benchmark view yet.</p>
                )}
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
