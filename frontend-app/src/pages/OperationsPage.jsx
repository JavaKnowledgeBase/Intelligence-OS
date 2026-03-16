import { useEffect, useState } from "react";
import { getSession } from "../auth";
import { createAlertRule, fetchAlerts, fetchIngestionRuns, triggerIngestionSync } from "../api/operationsClient";
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
  const [alertForm, setAlertForm] = useState(emptyAlertForm);
  const [errorMessage, setErrorMessage] = useState("");
  const [infoMessage, setInfoMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingAlert, setIsCreatingAlert] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadOperations() {
      setIsLoading(true);
      setErrorMessage("");
      try {
        const [alertData, runData] = await Promise.all([fetchAlerts(), fetchIngestionRuns()]);
        if (!isMounted) {
          return;
        }
        setAlerts(alertData);
        setIngestionRuns(runData);
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

  async function handleSync() {
    try {
      setIsSyncing(true);
      setErrorMessage("");
      setInfoMessage("");
      const run = await triggerIngestionSync();
      setIngestionRuns((current) => [run, ...current]);
      setInfoMessage(`Ingestion sync completed for ${run.source_name}.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to trigger the ingestion sync.");
    } finally {
      setIsSyncing(false);
    }
  }

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
            <form className="login-form project-form" onSubmit={handleCreateAlert}>
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
                {isCreatingAlert ? "Creating rule..." : "Create alert rule"}
              </button>
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
                <span className={`status-pill ${alert.enabled ? "status-live" : "status-pending"}`}>
                  {toTitleCase(alert.scope)}
                </span>
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
            <button type="button" className="ghost-button" onClick={handleSync} disabled={isSyncing}>
              {isSyncing ? "Running sync..." : "Run starter feed sync"}
            </button>
          ) : (
            <p className="hint-text">Your current role can view ingestion history, but only analysts and admins can trigger syncs.</p>
          )}

          <div className="admin-request-list">
            {ingestionRuns.map((run) => (
              <article key={run.id} className="admin-request-card">
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
        </div>
      </section>
    </main>
  );
}
