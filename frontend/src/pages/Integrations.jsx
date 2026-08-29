import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Integrations() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.integrationStatus().then(setStatus).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  const validate = async () => {
    setBusy(true);
    setError("");
    try {
      setStatus(await api.validateNotion());
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const setup = async () => {
    setBusy(true);
    setError("");
    try {
      await api.setupNotion();
      setStatus(await api.integrationStatus());
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const sync = async () => {
    setBusy(true);
    setError("");
    try {
      await api.syncNotion();
      setStatus(await api.integrationStatus());
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (!status) return <div className="empty">Loading integration status...</div>;

  const state = status.connection_state || (status.mode === "REAL" ? "connected" : "demo");
  const modeColor = state === "connected" ? "#2ecc71" : state === "error" ? "#e74c3c" : "#f39c12";
  const modeLabel =
    state === "connected" ? "🟢 Notion Connected" : state === "error" ? "🔴 Notion Configuration Error" : "🟡 Demo / Local Mode";

  const checks = [
    ["Mode", status.mode === "REAL" ? "REAL (Notion enabled)" : "DEMO (Notion disabled)"],
    ["DEMO_MODE flag", status.demo_mode ? "true – external actions simulated" : "false"],
    ["Integration Token", status.token_configured ? "✓ Configured" : "✗ Missing"],
    ["Parent Page", status.parent_page_configured ? "✓ Configured" : "✗ Missing"],
    ["Database IDs", status.databases_configured ? "✓ All configured" : "✗ Some missing"],
    ["Connection", status.connected ? "✓ Connected" : "✗ Failed to connect"],
    ["Database Access", status.database_access ? "✓ OK" : "✗ No access"],
    ["Schema", status.schema_valid ? "✓ Valid" : "✗ Invalid or incomplete"],
    ["Approval Polling", status.poller],
  ];

  return (
    <div>
      <h1>Integrations</h1>
      <p className="subtitle">Connection health for the services behind the procurement workflow.</p>

      <div className="integration-banner" style={{ borderLeftColor: modeColor }}>
        <strong>{modeLabel}</strong>
        <span>{status.message}</span>
      </div>

      <div className="panel integration-list">
        {checks.map(([label, value]) => (
          <div className="integration-row" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>

      {status.missing_properties?.length > 0 && (
        <div className="result-card" style={{ borderColor: "#a3670f" }}>
          <strong>Schema / Configuration Issues:</strong>
          <ul style={{ marginTop: 8, marginBottom: 0, paddingLeft: 20 }}>
            {status.missing_properties.map((prop, i) => (
              <li key={i}>{prop}</li>
            ))}
          </ul>
        </div>
      )}

      {error && <div className="result-card" style={{ borderColor: "#a3372f" }}>{error}</div>}

      <div className="integration-actions">
        <button className="primary" onClick={validate} disabled={busy}>
          {busy ? "Working..." : "Test Connection / Validate Schema"}
        </button>
        <button className="secondary" onClick={setup} disabled={busy}>
          Setup ProcureFlow in Notion
        </button>
        <button className="secondary" onClick={sync} disabled={busy || status.mode !== "REAL"}>
          Sync Now
        </button>
        <button className="secondary" onClick={load}>
          Refresh
        </button>
      </div>
    </div>
  );
}
