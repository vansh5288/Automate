import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Integrations() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.integrationStatus().then(setStatus).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const validate = async () => {
    setBusy(true);
    setError("");
    try { setStatus(await api.validateNotion()); } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const setup = async () => {
    setBusy(true);
    setError("");
    try { await api.setupNotion(); setStatus(await api.integrationStatus()); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const sync = async () => {
    setBusy(true);
    setError("");
    try { await api.syncNotion(); setStatus(await api.integrationStatus()); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  if (!status) return <div className="empty">Loading integration status...</div>;
  const checks = [
    ["Connection", status.connected ? "Connected" : "Not connected"],
    ["Token", status.token_configured ? "Configured" : "Missing"],
    ["Database access", status.database_access ? "OK" : "Unavailable"],
    ["Schema", status.schema_valid ? "Valid" : "Invalid or unchecked"],
    ["Purchase Requests", status.databases?.purchase_requests?.schema_valid ? "Ready" : "Missing or invalid"],
    ["Approval Queue", status.databases?.approval_queue?.schema_valid ? "Ready" : "Missing or invalid"],
    ["Run Log", status.databases?.run_log?.schema_valid ? "Ready" : "Missing or invalid"],
    ["Poller", status.poller],
  ];

  return (
    <div>
      <h1>Integrations</h1>
      <p className="subtitle">Connection health for the services behind the procurement workflow.</p>
      <div className="integration-banner"><strong>{status.mode} MODE</strong><span>{status.message}</span></div>
      <div className="panel integration-list">
        {checks.map(([label, value]) => <div className="integration-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}
      </div>
      {status.missing_properties?.length > 0 && <div className="result-card" style={{ borderColor: "#a3670f" }}>{status.missing_properties.join("; ")}</div>}
      {error && <div className="result-card" style={{ borderColor: "#a3372f" }}>{error}</div>}
      <div className="integration-actions">
        <button className="primary" onClick={validate} disabled={busy}>{busy ? "Working..." : "Test Connection / Validate Schema"}</button>
        <button className="secondary" onClick={setup} disabled={busy}>Setup ProcureFlow in Notion</button>
        <button className="secondary" onClick={sync} disabled={busy}>Sync Now</button>
        <button className="secondary" onClick={load}>Refresh</button>
      </div>
    </div>
  );
}
