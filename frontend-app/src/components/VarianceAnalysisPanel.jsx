import { useState } from "react";
import "../styles/roi.css";

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

function getVarianceClass(variance) {
  if (variance > 0) return "variance-positive";
  if (variance < 0) return "variance-negative";
  return "variance-neutral";
}

export function VarianceAnalysisPanel({ scenario, varianceData, loading, error, onRefresh }) {
  const [showMonthly, setShowMonthly] = useState(false);

  return (
    <div className="roi-panel variance-panel">
      <div className="roi-panel-header">
        <h3>Actuals Variance</h3>
        {scenario ? (
          <button type="button" className="btn-icon" onClick={onRefresh} disabled={loading} title="Refresh analysis">
            Refresh
          </button>
        ) : null}
      </div>

      <div className="roi-panel-content">
        {!scenario ? <p className="text-muted">Select a saved scenario to review realized versus underwritten performance.</p> : null}
        {error ? <div className="alert alert-error">{error}</div> : null}
        {loading ? <div className="text-muted">Loading variance analysis...</div> : null}
        {!loading && scenario && !varianceData ? <div className="alert alert-info">Variance analysis will appear once actual operating results are loaded.</div> : null}

        {!loading && varianceData ? (
          <>
            <div className="variance-summary">
              <div className="variance-stat">
                <span className="stat-label">Revenue variance</span>
                <span className={`stat-value ${getVarianceClass(varianceData.total_revenue_variance)}`}>
                  {formatCurrency(varianceData.total_revenue_variance)}
                </span>
              </div>
              <div className="variance-stat">
                <span className="stat-label">Expense variance</span>
                <span className={`stat-value ${getVarianceClass(-varianceData.total_expense_variance)}`}>
                  {formatCurrency(-varianceData.total_expense_variance)}
                </span>
              </div>
              <div className="variance-stat">
                <span className="stat-label">NOI variance</span>
                <span className={`stat-value ${getVarianceClass(varianceData.total_noi_variance)}`}>
                  {formatCurrency(varianceData.total_noi_variance)}
                </span>
              </div>
              {varianceData.average_occupancy_variance != null ? (
                <div className="variance-stat">
                  <span className="stat-label">Occupancy variance</span>
                  <span className={`stat-value ${getVarianceClass(varianceData.average_occupancy_variance)}`}>
                    {formatPercent(varianceData.average_occupancy_variance)}
                  </span>
                </div>
              ) : null}
            </div>

            {varianceData.variance_summary?.length ? (
              <div className="variance-summary-notes">
                <h4>Summary</h4>
                <ul className="summary-list">
                  {varianceData.variance_summary.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {varianceData.periods?.length ? (
              <div className="variance-details">
                <div className="variance-toggle">
                  <button type="button" className={`toggle-btn ${!showMonthly ? "active" : ""}`} onClick={() => setShowMonthly(false)}>
                    Highlights
                  </button>
                  <button type="button" className={`toggle-btn ${showMonthly ? "active" : ""}`} onClick={() => setShowMonthly(true)}>
                    Month detail
                  </button>
                </div>

                {!showMonthly ? (
                  <div className="variance-summary-view">
                    <h4>Period highlights</h4>
                    <VariancePeriodRow period={varianceData.periods[0]} label="First period" />
                    {varianceData.periods.length > 2 ? (
                      <VariancePeriodRow
                        period={varianceData.periods[Math.floor(varianceData.periods.length / 2)]}
                        label="Mid period"
                      />
                    ) : null}
                    {varianceData.periods.length > 1 ? (
                      <VariancePeriodRow period={varianceData.periods[varianceData.periods.length - 1]} label="Latest period" />
                    ) : null}
                  </div>
                ) : (
                  <div className="variance-detail-view">
                    <h4>Monthly detail</h4>
                    <div className="periods-table-container">
                      <table className="periods-table">
                        <thead>
                          <tr>
                            <th>Period</th>
                            <th>Revenue var.</th>
                            <th>Expense var.</th>
                            <th>NOI var.</th>
                            <th>Occ. var.</th>
                          </tr>
                        </thead>
                        <tbody>
                          {varianceData.periods.map((period) => (
                            <tr key={period.period_start}>
                              <td className="period-date">
                                {new Date(period.period_start).toLocaleDateString("en-US", {
                                  month: "short",
                                  year: "2-digit",
                                  timeZone: "UTC",
                                })}
                              </td>
                              <td className={`variance-cell ${getVarianceClass(period.revenue_variance)}`}>
                                {formatCurrency(period.revenue_variance)}
                              </td>
                              <td className={`variance-cell ${getVarianceClass(-period.expense_variance)}`}>
                                {formatCurrency(-period.expense_variance)}
                              </td>
                              <td className={`variance-cell ${getVarianceClass(period.noi_variance)}`}>
                                {formatCurrency(period.noi_variance)}
                              </td>
                              <td className={`variance-cell ${period.occupancy_variance != null ? getVarianceClass(period.occupancy_variance) : ""}`}>
                                {period.occupancy_variance != null ? formatPercent(period.occupancy_variance) : "Not set"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-muted">No actual periods have been recorded yet.</div>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}

function VariancePeriodRow({ period, label }) {
  return (
    <div className="variance-period-row">
      <div className="period-label">{label}</div>
      <div className="period-metrics">
        <span className={`metric ${getVarianceClass(period.revenue_variance)}`}>Rev {formatCurrency(period.revenue_variance)}</span>
        <span className={`metric ${getVarianceClass(-period.expense_variance)}`}>Exp {formatCurrency(-period.expense_variance)}</span>
        <span className={`metric ${getVarianceClass(period.noi_variance)}`}>NOI {formatCurrency(period.noi_variance)}</span>
      </div>
    </div>
  );
}
