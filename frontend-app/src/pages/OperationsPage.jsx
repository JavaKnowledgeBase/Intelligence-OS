import { useEffect, useState } from "react";
import { getSession } from "../auth";
import {
  createBenchmarkComp,
  createAlertRule,
  deleteAlertRule,
  fetchAlerts,
  fetchBenchmarkCalibration,
  fetchBenchmarkComps,
  fetchIngestionRuns,
  fetchIngestionSources,
  triggerIngestionSync,
  updateBenchmarkComp,
  updateAlertRule,
} from "../api/operationsClient";
import { FileUploadPanel } from "../components/FileUploadPanel";
import { SectionTitle } from "../components/SectionTitle";

const emptyAlertForm = {
  name: "",
  channel: "email",
  trigger: "",
  severity: "medium",
};

const emptyBenchmarkCompForm = {
  asset_class: "real-estate",
  location: "",
  source_name: "",
  closed_on: "",
  sale_price: "",
  net_operating_income: "",
  cap_rate: "",
  projected_irr: "",
  equity_multiple: "",
  average_dscr: "",
  occupancy_rate: "",
  leverage_ratio: "",
  note: "",
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

function normalizeLocation(value) {
  return (value ?? "").trim().toLowerCase();
}

function extractState(value) {
  const normalized = normalizeLocation(value);
  if (!normalized.includes(",")) {
    return "";
  }
  return normalized.split(",").pop()?.trim() ?? "";
}

function getCompFitSummary(comp, locationFocus) {
  if (!comp.included) {
    return {
      label: "Excluded by analyst",
      detail: "This comp is manually excluded and does not influence calibration.",
    };
  }

  const target = normalizeLocation(locationFocus);
  const compLocation = normalizeLocation(comp.location);
  if (!target) {
    return {
      label: "Asset-class match",
      detail: "This comp contributes based on asset class with no explicit geography focus.",
    };
  }
  if (target === compLocation) {
    return {
      label: "Exact market match",
      detail: "This comp receives the strongest geography weighting for calibration.",
    };
  }
  if (extractState(target) && extractState(target) === extractState(compLocation)) {
    return {
      label: "Same-state match",
      detail: "This comp is still relevant but weighted below an exact market match.",
    };
  }
  return {
    label: "Out-of-market reference",
    detail: "This comp is used as a weaker geography reference because it is outside the focused market.",
  };
}

function getCompFreshnessSummary(comp) {
  if (!comp.closed_on) {
    return {
      label: "Undated comp",
      detail: "This comp stays usable but is down-weighted because no close date was provided.",
    };
  }

  const closedOn = new Date(`${comp.closed_on}T00:00:00`);
  const now = new Date();
  const ageDays = Math.max(Math.floor((now.getTime() - closedOn.getTime()) / (1000 * 60 * 60 * 24)), 0);
  if (ageDays <= 365) {
    return {
      label: "Fresh comp",
      detail: "Closed within the last year, so it receives full freshness weight.",
    };
  }
  if (ageDays <= 730) {
    return {
      label: "Aging comp",
      detail: "Older than one year, so it is moderately down-weighted for staleness.",
    };
  }
  if (ageDays <= 1095) {
    return {
      label: "Stale comp",
      detail: "Older than two years, so it is meaningfully down-weighted.",
    };
  }
  return {
    label: "Very stale comp",
    detail: "Older than three years, so it only serves as a weak calibration reference.",
  };
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
  const [benchmarkCompForm, setBenchmarkCompForm] = useState(emptyBenchmarkCompForm);
  const [benchmarkComps, setBenchmarkComps] = useState([]);
  const [benchmarkCalibration, setBenchmarkCalibration] = useState(null);
  const [benchmarkAssetClass, setBenchmarkAssetClass] = useState("real-estate");
  const [benchmarkLocationFilter, setBenchmarkLocationFilter] = useState("");
  const [benchmarkInclusionFilter, setBenchmarkInclusionFilter] = useState("all");
  const [benchmarkOverrideFilter, setBenchmarkOverrideFilter] = useState("all");
  const [isCreatingBenchmarkComp, setIsCreatingBenchmarkComp] = useState(false);
  const [activeBenchmarkCompId, setActiveBenchmarkCompId] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadOperations() {
      setIsLoading(true);
      setErrorMessage("");
      try {
        const [alertData, runData, sourceData, compData, calibrationData] = await Promise.all([
          fetchAlerts(),
          fetchIngestionRuns(),
          fetchIngestionSources(),
          fetchBenchmarkComps(benchmarkAssetClass),
          fetchBenchmarkCalibration(benchmarkAssetClass, benchmarkLocationFilter),
        ]);
        if (!isMounted) {
          return;
        }
        setAlerts(alertData);
        setIngestionRuns(runData);
        setIngestionSources(sourceData);
        setBenchmarkComps(compData);
        setBenchmarkCalibration(calibrationData);
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
  }, [benchmarkAssetClass, benchmarkLocationFilter]);

  function toOptionalNumber(value) {
    return value === "" ? null : Number(value);
  }

  function buildBenchmarkCompPayload(form) {
    return {
      asset_class: form.asset_class.trim(),
      location: form.location.trim(),
      source_name: form.source_name.trim(),
      closed_on: form.closed_on || null,
      sale_price: Number(form.sale_price),
      net_operating_income: toOptionalNumber(form.net_operating_income),
      cap_rate: toOptionalNumber(form.cap_rate),
      projected_irr: toOptionalNumber(form.projected_irr),
      equity_multiple: toOptionalNumber(form.equity_multiple),
      average_dscr: toOptionalNumber(form.average_dscr),
      occupancy_rate: toOptionalNumber(form.occupancy_rate),
      leverage_ratio: toOptionalNumber(form.leverage_ratio),
      note: form.note.trim(),
    };
  }

  async function refreshBenchmarkData(assetClass = benchmarkAssetClass) {
    const [compData, calibrationData] = await Promise.all([
      fetchBenchmarkComps(assetClass),
      fetchBenchmarkCalibration(assetClass, benchmarkLocationFilter),
    ]);
    setBenchmarkComps(compData);
    setBenchmarkCalibration(calibrationData);
  }

  function parseCsvLine(line) {
    const values = [];
    let current = "";
    let inQuotes = false;

    for (let index = 0; index < line.length; index += 1) {
      const char = line[index];
      const next = line[index + 1];

      if (char === '"' && inQuotes && next === '"') {
        current += '"';
        index += 1;
      } else if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === "," && !inQuotes) {
        values.push(current.trim());
        current = "";
      } else {
        current += char;
      }
    }

    values.push(current.trim());
    return values;
  }

  function parseBenchmarkCompUpload(text, fileName) {
    if (fileName.toLowerCase().endsWith(".json")) {
      const parsed = JSON.parse(text);
      if (!Array.isArray(parsed)) {
        throw new Error("JSON upload must be an array of benchmark comp records.");
      }
      return parsed;
    }

    const lines = text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);

    if (lines.length < 2) {
      throw new Error("CSV upload must include a header row and at least one record.");
    }

    const headers = parseCsvLine(lines[0]).map((header) => header.toLowerCase());
    return lines.slice(1).map((line) => {
      const values = parseCsvLine(line);
      return headers.reduce((record, header, index) => {
        record[header] = values[index] ?? "";
        return record;
      }, {});
    });
  }

  async function handleUploadBenchmarkCompFile(file) {
    const text = await file.text();
    const records = parseBenchmarkCompUpload(text, file.name);
    if (!records.length) {
      throw new Error("No benchmark comp records were found in the uploaded file.");
    }

    setIsCreatingBenchmarkComp(true);
    setErrorMessage("");
    setInfoMessage("");

    try {
      for (const record of records) {
        const normalized = {
          asset_class: record.asset_class ?? record["asset class"] ?? benchmarkAssetClass,
          location: record.location ?? "",
          source_name: record.source_name ?? record["source name"] ?? file.name,
          closed_on: record.closed_on ?? record["closed on"] ?? "",
          sale_price: record.sale_price ?? record["sale price"] ?? "",
          net_operating_income: record.net_operating_income ?? record["net operating income"] ?? "",
          cap_rate: record.cap_rate ?? record["cap rate"] ?? "",
          projected_irr: record.projected_irr ?? record["projected irr"] ?? "",
          equity_multiple: record.equity_multiple ?? record["equity multiple"] ?? "",
          average_dscr: record.average_dscr ?? record["average dscr"] ?? "",
          occupancy_rate: record.occupancy_rate ?? record["occupancy rate"] ?? "",
          leverage_ratio: record.leverage_ratio ?? record["leverage ratio"] ?? "",
          note: record.note ?? "",
        };
        await createBenchmarkComp(buildBenchmarkCompPayload(normalized));
      }

      await refreshBenchmarkData(benchmarkAssetClass);
      setInfoMessage(`${records.length} benchmark comp ${records.length === 1 ? "record" : "records"} imported.`);
      return `${records.length} benchmark comp ${records.length === 1 ? "record was" : "records were"} imported.`;
    } finally {
      setIsCreatingBenchmarkComp(false);
    }
  }

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

  async function handleCreateBenchmarkComp(event) {
    event.preventDefault();
    try {
      setIsCreatingBenchmarkComp(true);
      setErrorMessage("");
      setInfoMessage("");
      await createBenchmarkComp(buildBenchmarkCompPayload(benchmarkCompForm));
      setBenchmarkCompForm((current) => ({ ...emptyBenchmarkCompForm, asset_class: current.asset_class }));
      await refreshBenchmarkData(benchmarkCompForm.asset_class);
      setBenchmarkAssetClass(benchmarkCompForm.asset_class);
      setInfoMessage("Benchmark comp saved.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to save the benchmark comp.");
    } finally {
      setIsCreatingBenchmarkComp(false);
    }
  }

  async function handleToggleBenchmarkComp(comp) {
    try {
      setActiveBenchmarkCompId(comp.id);
      setErrorMessage("");
      setInfoMessage("");
      await updateBenchmarkComp(comp.id, {
        included: !comp.included,
        override_mode: comp.override_mode ?? "normal",
        note: comp.note,
      });
      await refreshBenchmarkData(comp.asset_class);
      setInfoMessage(`Benchmark comp ${!comp.included ? "included" : "excluded"}: ${comp.location}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to update the benchmark comp.");
    } finally {
      setActiveBenchmarkCompId("");
    }
  }

  async function handleUpdateBenchmarkOverride(comp, overrideMode) {
    try {
      setActiveBenchmarkCompId(comp.id);
      setErrorMessage("");
      setInfoMessage("");
      await updateBenchmarkComp(comp.id, {
        included: comp.included,
        override_mode: overrideMode,
        note: comp.note,
      });
      await refreshBenchmarkData(comp.asset_class);
      setInfoMessage(`Benchmark comp override updated for ${comp.location}.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to update the benchmark override.");
    } finally {
      setActiveBenchmarkCompId("");
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
  const visibleBenchmarkComps = benchmarkComps.filter((comp) => {
    if (benchmarkInclusionFilter === "included" && !comp.included) {
      return false;
    }
    if (benchmarkInclusionFilter === "excluded" && comp.included) {
      return false;
    }
    if (benchmarkOverrideFilter !== "all" && (comp.override_mode ?? "normal") !== benchmarkOverrideFilter) {
      return false;
    }
    return true;
  });

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
            eyebrow="Benchmarking"
            title="Comparable calibration"
            description="Manage benchmark comps that calibrate ROI expectations, coverage ranges, and scenario quality signals."
          />
          <div className="login-form project-form">
            <label>
              Asset class view
              <select className="login-select" value={benchmarkAssetClass} onChange={(event) => setBenchmarkAssetClass(event.target.value)}>
                <option value="real-estate">real-estate</option>
                <option value="retail">retail</option>
                <option value="industrial">industrial</option>
                <option value="multifamily">multifamily</option>
                <option value="office">office</option>
                <option value="hospitality">hospitality</option>
                </select>
              </label>
            <label>
              Location focus
              <input
                type="text"
                value={benchmarkLocationFilter}
                onChange={(event) => setBenchmarkLocationFilter(event.target.value)}
                placeholder="Charlotte, NC"
              />
            </label>
            <label>
              Inclusion filter
              <select className="login-select" value={benchmarkInclusionFilter} onChange={(event) => setBenchmarkInclusionFilter(event.target.value)}>
                <option value="all">all</option>
                <option value="included">included</option>
                <option value="excluded">excluded</option>
              </select>
            </label>
            <label>
              Override filter
              <select className="login-select" value={benchmarkOverrideFilter} onChange={(event) => setBenchmarkOverrideFilter(event.target.value)}>
                <option value="all">all</option>
                <option value="normal">normal</option>
                <option value="force_include">force include</option>
                <option value="exclude_outlier">exclude outlier</option>
              </select>
            </label>
          </div>

          {benchmarkCalibration ? (
            <div className="document-preview-panel">
              <div className="projects-header-row">
                <div>
                  <p className="panel-label">Calibration status</p>
                  <h3 className="projects-heading">{benchmarkCalibration.benchmark_profile}</h3>
                </div>
                <span className={`status-pill ${benchmarkCalibration.source_mode === "external_comps" ? "status-live" : "status-pending"}`}>
                  {benchmarkCalibration.source_mode}
                </span>
              </div>
              <div className="project-summary-grid">
                <div className="project-summary-card">
                  <span>Comp count</span>
                  <strong>{benchmarkCalibration.comp_count}</strong>
                </div>
                <div className="project-summary-card">
                  <span>Effective comps</span>
                  <strong>{benchmarkCalibration.effective_comp_count}</strong>
                </div>
                <div className="project-summary-card">
                  <span>Stale comps</span>
                  <strong>{benchmarkCalibration.stale_comp_count}</strong>
                </div>
                <div className="project-summary-card">
                  <span>Outliers excluded</span>
                  <strong>{benchmarkCalibration.excluded_outlier_count}</strong>
                </div>
                <div className="project-summary-card project-summary-card-wide">
                  <span>Notes</span>
                  <strong>{benchmarkCalibration.notes?.join(" ") || "No calibration notes yet."}</strong>
                </div>
              </div>
            </div>
          ) : null}

          {canManageOperations ? (
            <>
              <form className="login-form project-form" onSubmit={handleCreateBenchmarkComp}>
                <div className="project-summary-grid">
                  <label>
                    Asset class
                    <input
                      type="text"
                      value={benchmarkCompForm.asset_class}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, asset_class: event.target.value }))}
                      placeholder="real-estate"
                    />
                  </label>
                  <label>
                    Location
                    <input
                      type="text"
                      value={benchmarkCompForm.location}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, location: event.target.value }))}
                      placeholder="Charlotte, NC"
                    />
                  </label>
                  <label>
                    Source name
                    <input
                      type="text"
                      value={benchmarkCompForm.source_name}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, source_name: event.target.value }))}
                      placeholder="manual-comp-set"
                    />
                  </label>
                  <label>
                    Closed on
                    <input
                      type="date"
                      value={benchmarkCompForm.closed_on}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, closed_on: event.target.value }))}
                    />
                  </label>
                  <label>
                    Sale price
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={benchmarkCompForm.sale_price}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, sale_price: event.target.value }))}
                      placeholder="6100000"
                    />
                  </label>
                  <label>
                    NOI
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={benchmarkCompForm.net_operating_income}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, net_operating_income: event.target.value }))}
                      placeholder="590000"
                    />
                  </label>
                  <label>
                    Cap rate
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      value={benchmarkCompForm.cap_rate}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, cap_rate: event.target.value }))}
                      placeholder="9.67"
                    />
                  </label>
                  <label>
                    Projected IRR
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      value={benchmarkCompForm.projected_irr}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, projected_irr: event.target.value }))}
                      placeholder="19.4"
                    />
                  </label>
                  <label>
                    Equity multiple
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={benchmarkCompForm.equity_multiple}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, equity_multiple: event.target.value }))}
                      placeholder="2.15"
                    />
                  </label>
                  <label>
                    Average DSCR
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={benchmarkCompForm.average_dscr}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, average_dscr: event.target.value }))}
                      placeholder="1.42"
                    />
                  </label>
                  <label>
                    Occupancy rate
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      value={benchmarkCompForm.occupancy_rate}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, occupancy_rate: event.target.value }))}
                      placeholder="95"
                    />
                  </label>
                  <label>
                    Leverage ratio
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      value={benchmarkCompForm.leverage_ratio}
                      onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, leverage_ratio: event.target.value }))}
                      placeholder="58"
                    />
                  </label>
                </div>
                <label>
                  Note
                  <textarea
                    className="login-textarea"
                    value={benchmarkCompForm.note}
                    onChange={(event) => setBenchmarkCompForm((current) => ({ ...current, note: event.target.value }))}
                    placeholder="Recent local comp with strong occupancy and stable leverage."
                    rows={3}
                  />
                </label>
                <button type="submit" className="primary-button login-submit" disabled={isCreatingBenchmarkComp}>
                  {isCreatingBenchmarkComp ? "Saving comp..." : "Save benchmark comp"}
                </button>
              </form>

              <FileUploadPanel
                title="Import benchmark comps"
                description="Upload a CSV or JSON file of comparable records to seed benchmark calibration faster."
                accept=".csv,.json"
                buttonLabel={isCreatingBenchmarkComp ? "Importing..." : "Import comp file"}
                helperText="Supported columns: asset_class, location, source_name, closed_on, sale_price, net_operating_income, cap_rate, projected_irr, equity_multiple, average_dscr, occupancy_rate, leverage_ratio, note."
                onUpload={handleUploadBenchmarkCompFile}
              />
            </>
          ) : (
            <p className="hint-text">Your current role can view benchmark calibration, but only analysts and admins can add comparable records.</p>
          )}

          <div className="admin-request-list">
            {visibleBenchmarkComps.map((comp) => (
              <article
                key={comp.id}
                className="admin-request-card"
                style={{
                  borderLeft:
                    comp.included && (comp.override_mode ?? "normal") !== "exclude_outlier"
                      ? "4px solid #1f7a4d"
                      : "4px solid #d0d7de",
                }}
              >
                <div>
                  <strong>{comp.location}</strong>
                  <p>
                    {comp.asset_class} | {comp.source_name}
                    {comp.closed_on ? ` | Closed ${comp.closed_on}` : ""}
                  </p>
                  <small>
                    Sale {Number(comp.sale_price).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })}
                    {comp.cap_rate != null ? ` | Cap ${Number(comp.cap_rate).toFixed(2)}%` : ""}
                    {comp.projected_irr != null ? ` | IRR ${Number(comp.projected_irr).toFixed(2)}%` : ""}
                    {comp.average_dscr != null ? ` | DSCR ${Number(comp.average_dscr).toFixed(2)}` : ""}
                  </small>
                  {comp.note ? <p>{comp.note}</p> : null}
                  <div className="project-summary-grid" style={{ marginTop: "0.75rem" }}>
                    <div className="project-summary-card">
                      <span>{getCompFitSummary(comp, benchmarkLocationFilter).label}</span>
                      <strong>{getCompFitSummary(comp, benchmarkLocationFilter).detail}</strong>
                    </div>
                    <div className="project-summary-card">
                      <span>{getCompFreshnessSummary(comp).label}</span>
                      <strong>{getCompFreshnessSummary(comp).detail}</strong>
                    </div>
                    <div className="project-summary-card">
                      <span>Override mode</span>
                      <strong>{toTitleCase((comp.override_mode ?? "normal").replace("_", " "))}</strong>
                    </div>
                    <div className="project-summary-card">
                      <span>Calibration impact</span>
                      <strong>
                        {!comp.included
                          ? "Ignored by calibration"
                          : (comp.override_mode ?? "normal") === "exclude_outlier"
                            ? "Excluded as outlier"
                            : (comp.override_mode ?? "normal") === "force_include"
                              ? "Forced into calibration"
                              : "Auto-selected by calibration rules"}
                      </strong>
                    </div>
                  </div>
                </div>
                <div className="admin-request-side">
                  <span className={`status-pill ${comp.included ? "status-live" : "status-pending"}`}>
                    {comp.included ? "included" : "excluded"}
                  </span>
                  <span className="status-pill status-live">{toTitleCase(comp.asset_class)}</span>
                  {canManageOperations ? (
                    <>
                      <button
                        type="button"
                        className="ghost-button"
                        disabled={activeBenchmarkCompId === comp.id}
                        onClick={() => handleToggleBenchmarkComp(comp)}
                      >
                        {activeBenchmarkCompId === comp.id ? "Saving..." : comp.included ? "Exclude" : "Include"}
                      </button>
                      <select
                        className="login-select"
                        value={comp.override_mode ?? "normal"}
                        disabled={activeBenchmarkCompId === comp.id}
                        onChange={(event) => handleUpdateBenchmarkOverride(comp, event.target.value)}
                      >
                        <option value="normal">Normal</option>
                        <option value="force_include">Force include</option>
                        <option value="exclude_outlier">Exclude outlier</option>
                      </select>
                    </>
                  ) : null}
                </div>
              </article>
            ))}
            {!visibleBenchmarkComps.length && !isLoading ? (
              <p className="hint-text">No benchmark comps match the current asset-class, inclusion, and override filters.</p>
            ) : null}
          </div>
        </div>

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
