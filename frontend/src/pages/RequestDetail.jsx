import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api.js";
import StatusBadge from "../components/StatusBadge.jsx";

export default function RequestDetail() {
  const { id } = useParams();
  const [req, setReq] = useState(null);
  const [runs, setRuns] = useState([]);
  const [error, setError] = useState("");

  const load = () => {
    Promise.all([api.getRequest(id), api.getRuns(id)])
      .then(([r, l]) => { setReq(r); setRuns(l); })
      .catch((e) => setError(e.message));
  };

  useEffect(load, [id]);

  const retry = async () => {
    try {
      await api.retryRequest(id);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const sync = async () => {
    try {
      await api.syncRequest(id);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  if (error) return <div className="empty">{error}</div>;
  if (!req) return <div className="empty">Loading…</div>;

  const retryable = ["FAILED", "NEEDS_REVIEW", "ACTION_FAILED"].includes(req.status);

  return (
    <div>
      <Link to="/" className="back-link">← Back to dashboard</Link>
      <h1>{req.request_id}</h1>
      <p className="subtitle"><StatusBadge status={req.status} /> {req.notion_url && (
        <a className="secondary" href={req.notion_url} target="_blank" rel="noreferrer">Open in Notion</a>
      )} {req.status === "PENDING_APPROVAL" && (
        <button className="secondary" onClick={sync}>Sync Now</button>
      )} {retryable && (
        <button className="primary" style={{ marginLeft: 12, padding: "4px 12px", fontSize: 12, marginTop: 0 }} onClick={retry}>
          Retry
        </button>
      )}</p>

      <div className="detail-grid">
        <Field k="Employee" v={`${req.employee_name} (${req.employee_email})`} />
        <Field k="Department" v={req.department} />
        <Field k="Item" v={req.item ? `${req.quantity}x ${req.item}` : "—"} />
        <Field k="Category" v={req.category || "—"} />
        <Field k="Estimated Amount" v={req.estimated_amount ? `${req.currency} ${req.estimated_amount.toLocaleString("en-IN")}` : "—"} />
        <Field k="Priority" v={req.priority || "—"} />
        <Field k="Risk Level" v={req.risk_level || "—"} />
        <Field k="AI Confidence" v={req.confidence ? `${Math.round(req.confidence * 100)}%` : "—"} />
        <Field k="Approval Required" v={req.approval_required ? "Yes" : "No"} />
        <Field k="Approver" v={req.approver || "—"} />
      </div>

      <div className="panel" style={{ marginBottom: 24, padding: 20 }}>
        <div className="field"><div className="k">Original Request</div><div>{req.request_text}</div></div>
      </div>

      <div className="panel timeline">
        <div className="field k" style={{ marginBottom: 12 }}>Run History</div>
        {runs.length === 0 && <div style={{ color: "#8b93a1", fontSize: 14 }}>No run log entries yet.</div>}
        {runs.map((r) => (
          <div className="run-row" key={r.run_id}>
            <div className="run-time">{new Date(r.timestamp).toLocaleString()}</div>
            <div className="run-event">{r.event}</div>
            <div>
              <StatusBadge status={r.status === "SUCCESS" ? "COMPLETED" : r.status === "FAILURE" ? "FAILED" : "PROCESSING"} />
              {r.reason && <span style={{ marginLeft: 8, color: "#3d4552" }}>{r.reason}</span>}
              {r.error && <span style={{ marginLeft: 8, color: "#a3372f" }}>{r.error}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Field({ k, v }) {
  return (
    <div className="field">
      <div className="k">{k}</div>
      <div className="v">{v}</div>
    </div>
  );
}
