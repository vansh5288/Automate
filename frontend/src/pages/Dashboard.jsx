import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import StatusBadge from "../components/StatusBadge.jsx";

export default function Dashboard() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listRequests().then(setRequests).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  const counts = requests.reduce((acc, r) => {
    acc.total++;
    if (["COMPLETED", "AUTO_PROCESSED"].includes(r.status)) acc.auto++;
    if (r.status === "PENDING_APPROVAL") acc.pending++;
    if (r.status === "COMPLETED") acc.completed++;
    if (r.status === "REJECTED") acc.rejected++;
    if (["FAILED", "ACTION_FAILED"].includes(r.status)) acc.failed++;
    return acc;
  }, { total: 0, auto: 0, pending: 0, completed: 0, rejected: 0, failed: 0 });

  return (
    <div>
      <h1>Operations Dashboard</h1>
      <p className="subtitle">Every purchase request that has entered ProcureFlow, and where it stands right now.</p>

      <div className="stat-grid">
        <Stat value={counts.total} label="Total Requests" />
        <Stat value={counts.auto} label="Auto-Processed" />
        <Stat value={counts.pending} label="Pending Approval" />
        <Stat value={counts.completed} label="Completed" />
        <Stat value={counts.rejected} label="Rejected" />
        <Stat value={counts.failed} label="Failed" />
      </div>

      <div className="panel">
        {loading && <div className="empty">Loading requests…</div>}
        {error && <div className="empty">Couldn't reach the backend: {error}</div>}
        {!loading && !error && requests.length === 0 && (
          <div className="empty">No requests yet. Submit one to see it appear here.</div>
        )}
        {!loading && requests.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Request</th>
                <th>Employee</th>
                <th>Item</th>
                <th>Amount</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.request_id} className="clickable" onClick={() => (window.location.href = `/requests/${r.request_id}`)}>
                  <td style={{ fontFamily: "IBM Plex Mono, monospace" }}>{r.request_id}</td>
                  <td>{r.employee_name} <span style={{ color: "#8b93a1" }}>· {r.department}</span></td>
                  <td>{r.quantity ? `${r.quantity}x ${r.item}` : "—"}</td>
                  <td>{r.estimated_amount ? `₹${r.estimated_amount.toLocaleString("en-IN")}` : "—"}</td>
                  <td><StatusBadge status={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Stat({ value, label }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
