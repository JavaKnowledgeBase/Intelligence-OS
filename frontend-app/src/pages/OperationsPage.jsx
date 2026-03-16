import { useEffect, useState } from "react";
import { getSession } from "../auth";
import {
  createAlertRule,
  deleteAlertRule,
  fetchAlerts,
  fetchIngestionRuns,
  fetchIngestionSources,
  triggerIngestionSync,
  updateAlertRule,
} from "../api/operationsClient";
import { SectionTitle } from "../components/SectionTitle";

const emptyAlertForm = {
  name: "",
  channel: "email",
  trigger: "",
  severity: "medium",
};

function formatDateTime(value) {
  if (!value) {
    return "In progress";
  }
  return new Date(value).toLocaleString();
}

function toTitleCase(value) {
  return value
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function OperationsPage() {
  const session = getSession();
  const canManageOperations = ["admin", "analyst"].includes(session?.user?.role ?? "");
  const [alerts, setAlerts] = useState([]);
  const [ingestionRuns, setIngestionRuns] = useState([]);
  const [ingestionSources, setIngestionSources] = useState([]);
  const [alertForm, setAlertForm] = useState(emptyAlertForm);
  const [errorMessage, setErrorMessage] = useState("");
  const [infoMessage, setInfoMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingAlert, setIsCreatingAlert] = useState(false);
  const [activeAlertId, setActiveAlertId] = useState("");
  const [editingAlertId, setEditingAlertId] = useState("");
  const [isSyncing, setIsSyncing] = useState(false);
  const [selectedSourceName, setSelectedSourceName] = useState("starter_feed");
  const [selectedRunId, setSelectedRunId] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadOperations() {
      setIsLoading(true);
      setErrorMessage("");
      try {
        const [alertData, runData, sourceData] = await Promise.all([fetchAlerts(), fetchIngestionRuns(), fetchIngestionSources()]);
        if (!isMounted) {
          return;
        }
        setAlerts(alertData);
        setIngestionRuns(runData);
        setIngestionSources(sourceData);
        setSelectedSourceName(sourceData[0]?.source_name ?? "starter_feed");
        setSelectedRunId(runData[0]?.id ?? "");
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Unable to load operations data.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadOperations();
    return () => {
      isMounted = false;
    };
  }, []);

  async function handleCreateAlert(event) {
    event.preventDefault();
    try {
      setIsCreatingAlert(true);
      setErrorMessage("");
      setInfoMessage("");
      const created = await createAlertRule(alertForm);
      setAlerts((current) => [created, ...current]);
      setAlertForm(emptyAlertForm);
      setInfoMessage(`Alert created: ${created.name}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create the alert rule.");
    } finally {
      setIsCreatingAlert(false);
    }
  }

  function startEditAlert(alert) {
    setEditingAlertId(alert.id);
    setAlertForm({
      name: alert.name,
      channel: alert.channel,
      trigger: alert.trigger,
      severity: alert.severity,
    });
    setInfoMessage("");
    setErrorMessage("");
  }

  function cancelEditAlert() {
    setEditingAlertId("");
    setAlertForm(emptyAlertForm);
  }

  async function handleSaveAlertEdit(event) {
    event.preventDefault();
    if (!editingAlertId) {
      return;
    }
    try {
      setActiveAlertId(editingAlertId);
      setErrorMessage("");
      setInfoMessage("");
      const current = alerts.find((alert) => alert.id === editingAlertId);
      const updated = await updateAlertRule(editingAlertId, {
        ...alertForm,
        enabled: current?.enabled ?? true,
        scope: current?.scope ?? "tenant",
      });
      setAlerts((existing) => existing.map((alert) => (alert.id === editingAlertId ? updated : alert)));
      setEditingAlertId("");
      setAlertForm(emptyAlertForm);
      setInfoMessage(`Alert updated: ${updated.name}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to update the alert rule.");
    } finally {
      setActiveAlertId("");
    }
  }

  async function handleToggleAlert(alert) {
    try {
      setActiveAlertId(alert.id);
      setErrorMessage("");
      setInfoMessage("");
      const updated = await updateAlertRule(alert.id, {
        name: alert.name,
        channel: alert.channel,
        trigger: alert.trigger,
        severity: alert.severity,
        enabled: !alert.enabled,
        scope: alert.scope,
      });
      setAlerts((existing) => existing.map((item) => (item.id === alert.id ? updated : item)));
      setInfoMessage(`Alert ${updated.enabled ? "enabled" : "disabled"}: ${updated.name}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to update the alert rule.");
    } finally {
      setActiveAlertId("");
    }
  }

  async function handleDeleteAlert(alertId) {
    try {
      setActiveAlertId(alertId);
      setErrorMessage("");
      setInfoMessage("");
      await deleteAlertRule(alertId);
      setAlerts((existing) => existing.filter((alert) => alert.id !== alertId));
      if (editingAlertId === alertId) {
        cancelEditAlert();
      }
      setInfoMessage("Alert rule deleted.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to delete the alert rule.");
    } finally {
      setActiveAlertId("");
    }
  }

  async function handleSync() {
    try {
      setIsSyncing(true);
      setErrorMessage("");
      setInfoMessage("");
      const run = await triggerIngestionSync(selectedSourceName);
      setIngestionRuns((current) => [run, ...current]);
      setSelectedRunId(run.id);
      setInfoMessage(`Ingestion sync completed for ${run.source_name}.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to trigger the ingestion sync.");
    } finally {
      setIsSyncing(false);
    }
  }

  const selectedSource =
    ingestionSources.find((source) => source.source_name === selectedSourceName) ??
    ingestionSources[0] ??
    null;
  const selectedRun =
    ingestionRuns.find((run) => run.id === selectedRunId) ??
    ingestionRuns[0] ??
    null;

  return (
    <main className="content about-content">
      <section className="glass-card architecture-hero">
        <SectionTitle
          eyebrow="Operations"
          title="Alerting and ingestion control room"
          description="Manage notification rules, watch ingestion activity, and keep the platform's operational heartbeat visible."
        />
      </section>

      {errorMessage ? <p className="callout-message">{errorMessage}</p> : null}
      {infoMessage ? <p className="hint-text">{infoMessage}</p> : null}

      <section className="split-panel">
        <div className="glass-card">
          <SectionTitle
            eyebrow="Alerts"
            title="Alert rules"
            description="These rules decide what the platform should watch and how the team gets notified."
          />
          {canManageOperations ? (
            <form className="login-form project-form" onSubmit={editingAlertId ? handleSaveAlertEdit : handleCreateAlert}>
              <label>
                Rule name
                <input
                  type="text"
                  value={alertForm.name}
                  onChange={(event) => setAlertForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="High-score deals"
                />
              </label>
              <label>
                Channel
                <input
                  type="text"
                  value={alertForm.channel}
                  onChange={(event) => setAlertForm((current) => ({ ...current, channel: event.target.value }))}
                  placeholder="email"
                />
              </label>
              <label>
                Severity
                <input
                  type="text"
                  value={alertForm.severity}
                  onChange={(event) => setAlertForm((current) => ({ ...current, severity: event.target.value }))}
                  placeholder="medium"
                />
              </label>
              <label>
                Trigger logic
                <textarea
                  className="login-textarea"
                  value={alertForm.trigger}
                  onChange={(event) => setAlertForm((current) => ({ ...current, trigger: event.target.value }))}
                  placeholder="Notify when a listing reaches a deal score above 90."
                  rows={4}
                />
              </label>
              <button type="submit" className="primary-button login-submit" disabled={isCreatingAlert}>
                {editingAlertId
                  ? activeAlertId === editingAlertId
                    ? "Saving alert..."
                    : "Save alert changes"
                  : isCreatingAlert
                    ? "Creating rule..."
                    : "Create alert rule"}
              </button>
              {editingAlertId ? (
                <button type="button" className="ghost-button login-submit" onClick={cancelEditAlert} disabled={activeAlertId === editingAlertId}>
                  Cancel edit
                </button>
              ) : null}
            </form>
          ) : (
            <p className="hint-text">Your current role can view alert rules, but only analysts and admins can create them.</p>
          )}

          <div className="admin-request-list">
            {alerts.map((alert) => (
              <article key={alert.id} className="admin-request-card">
                <div>
                  <strong>{alert.name}</strong>
                  <p>{alert.trigger}</p>
                  <small>
                    {alert.channel} | {alert.severity} | {alert.enabled ? "enabled" : "disabled"}
                  </small>
                </div>
                <div className="admin-request-side">
                  <span className={`status-pill ${alert.enabled ? "status-live" : "status-pending"}`}>
                    {toTitleCase(alert.scope)}
                  </span>
                  {canManageOperations ? (
                    <div className="admin-request-actions">
                      <button
                        type="button"
                        className="ghost-button"
                        disabled={activeAlertId === alert.id}
                        onClick={() => handleToggleAlert(alert)}
                      >
                        {activeAlertId === alert.id ? "Saving..." : alert.enabled ? "Disable" : "Enable"}
                      </button>
                      <button
                        type="button"
                        className="ghost-button"
                        disabled={activeAlertId === alert.id}
                        onClick={() => startEditAlert(alert)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="ghost-button"
                        disabled={activeAlertId === alert.id}
                        onClick={() => handleDeleteAlert(alert.id)}
                      >
                        Delete
                      </button>
                    </div>
                  ) : null}
                </div>
              </article>
            ))}
            {!alerts.length && !isLoading ? <p className="hint-text">No alert rules are configured yet.</p> : null}
          </div>
        </div>

        <div className="glass-card">
          <SectionTitle
            eyebrow="Ingestion"
            title="Sync activity"
            description="Monitor source sync history and trigger the local starter feed when you want fresh demo data loaded."
          />
          {canManageOperations ? (
            <div className="login-form project-form">
              <label>
                Source
                <select
                  className="login-select"
                  value={selectedSourceName}
                  onChange={(event) => setSelectedSourceName(event.target.value)}
                >
                  {ingestionSources.map((source) => (
                    <option key={source.source_name} value={source.source_name}>
                      {source.source_name}
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" className="ghost-button" onClick={handleSync} disabled={isSyncing || !selectedSourceName}>
                {isSyncing ? "Running sync..." : `Run ${selectedSourceName || "source"} sync`}
              </button>
            </div>
          ) : (
            <p className="hint-text">Your current role can view ingestion history, but only analysts and admins can trigger syncs.</p>
          )}

          {selectedSource ? (
            <div className="project-locked-panel">
              <p className="panel-label">Selected source</p>
              <strong>{selectedSource.source_name}</strong>
              <p className="hint-text">
                {selectedSource.listing_count} listings and {selectedSource.market_insight_count} market insights are available in this feed.
              </p>
            </div>
          ) : null}

          <div className="admin-request-list">
            {ingestionRuns.map((run) => (
              <article
                key={run.id}
                className="admin-request-card"
                onClick={() => setSelectedRunId(run.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setSelectedRunId(run.id);
                  }
                }}
              >
                <div>
                  <strong>{run.source_name}</strong>
                  <p>{run.detail}</p>
                  <small>
                    {run.records_processed} processed | {run.records_created} created | {run.records_updated} updated
                  </small>
                </div>
                <div className="admin-request-side">
                  <span className={`status-pill ${run.status === "completed" ? "status-live" : run.status === "running" ? "status-pending" : "status-error"}`}>
                    {run.status}
                  </span>
                  <small>Started {formatDateTime(run.started_at)}</small>
                  <small>Completed {formatDateTime(run.completed_at)}</small>
                </div>
              </article>
            ))}
            {!ingestionRuns.length && !isLoading ? <p className="hint-text">No ingestion runs have been recorded yet.</p> : null}
          </div>
          {selectedRun ? (
            <div className="document-preview-panel">
              <div className="projects-header-row">
                <div>
                  <p className="panel-label">Run detail</p>
                  <h3 className="projects-heading">{selectedRun.source_name}</h3>
                </div>
                <span className={`status-pill ${selectedRun.status === "completed" ? "status-live" : selectedRun.status === "running" ? "status-pending" : "status-error"}`}>
                  {selectedRun.status}
                </span>
              </div>
              <div className="project-summary-grid">
                <div className="project-summary-card">
                  <span>Processed</span>
                  <strong>{selectedRun.records_processed}</strong>
                </div>
                <div className="project-summary-card">
                  <span>Created</span>
                  <strong>{selectedRun.records_created}</strong>
                </div>
                <div className="project-summary-card">
                  <span>Updated</span>
                  <strong>{selectedRun.records_updated}</strong>
                </div>
                <div className="project-summary-card">
                  <span>Started</span>
                  <strong>{formatDateTime(selectedRun.started_at)}</strong>
                </div>
                <div className="project-summary-card project-summary-card-wide">
                  <span>Run detail</span>
                  <strong>{selectedRun.detail}</strong>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
