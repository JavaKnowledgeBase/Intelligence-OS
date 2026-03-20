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
  if (value == null || value === "") {
    return "Not set";
  }

  return `${Number(value).toFixed(1)}%`;
}

export function RoiActualsPanel({
  scenario,
  actuals,
  form,
  loading,
  saving,
  error,
  canEdit,
  onChange,
  onSubmit,
}) {
  return (
    <div className="roi-panel roi-actuals-panel">
      <div className="roi-panel-header">
        <h3>Operating Actuals</h3>
        <span className="panel-chip">{actuals.length} recorded</span>
      </div>

      <div className="roi-panel-content">
        {!scenario ? <p className="text-muted">Select a scenario to record actual monthly results.</p> : null}
        {error ? <div className="alert alert-error">{error}</div> : null}

        {scenario && canEdit ? (
          <form className="roi-actuals-form" onSubmit={onSubmit}>
            <div className="roi-actuals-grid">
              <label>
                Period start
                <input type="date" value={form.period_start} onChange={(event) => onChange("period_start", event.target.value)} />
              </label>
              <label>
                Effective revenue
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.effective_revenue}
                  onChange={(event) => onChange("effective_revenue", event.target.value)}
                />
              </label>
              <label>
                Operating expenses
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.operating_expenses}
                  onChange={(event) => onChange("operating_expenses", event.target.value)}
                />
              </label>
              <label>
                Capex
                <input type="number" min="0" step="0.01" value={form.capex} onChange={(event) => onChange("capex", event.target.value)} />
              </label>
              <label>
                Debt service
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.debt_service}
                  onChange={(event) => onChange("debt_service", event.target.value)}
                />
              </label>
              <label>
                Occupancy rate
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={form.occupancy_rate}
                  onChange={(event) => onChange("occupancy_rate", event.target.value)}
                />
              </label>
            </div>

            <label>
              Note
              <textarea
                className="login-textarea"
                rows={3}
                value={form.note}
                onChange={(event) => onChange("note", event.target.value)}
                placeholder="Summarize leasing changes, one-time costs, or collection issues."
              />
            </label>

            <button type="submit" className="ghost-button" disabled={saving || loading}>
              {saving ? "Saving actual..." : "Save actual"}
            </button>
          </form>
        ) : null}

        {scenario && !actuals.length ? (
          <div className="alert alert-info">No actuals recorded yet for this scenario. Add the first month to unlock variance tracking.</div>
        ) : null}

        {actuals.length ? (
          <div className="activity-list roi-actuals-list">
            {actuals.map((actual) => (
              <article key={actual.id} className="activity-card roi-actual-card">
                <div className="roi-actual-card-top">
                  <strong>
                    {new Date(actual.period_start).toLocaleDateString("en-US", {
                      month: "long",
                      year: "numeric",
                      timeZone: "UTC",
                    })}
                  </strong>
                  {actual.created_at ? (
                    <small>
                      Saved{" "}
                      {new Date(actual.created_at).toLocaleString("en-US", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </small>
                  ) : null}
                </div>
                <p>
                  Revenue {formatCurrency(actual.effective_revenue)} | Expenses {formatCurrency(actual.operating_expenses)} | Capex{" "}
                  {formatCurrency(actual.capex)} | Debt service {formatCurrency(actual.debt_service)}
                </p>
                <small>Occupancy {formatPercent(actual.occupancy_rate)}</small>
                {actual.note ? <p className="roi-actual-note">{actual.note}</p> : null}
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
