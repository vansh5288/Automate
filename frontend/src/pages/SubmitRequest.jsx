import { useState } from "react";
import { api } from "../api.js";
import StatusBadge from "../components/StatusBadge.jsx";

const EMPTY = { employee_name: "", employee_email: "", department: "", request_text: "" };

export default function SubmitRequest() {
  const [form, setForm] = useState(EMPTY);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    setResult(null);
    try {
      const res = await api.submitRequest(form);
      setResult(res);
      setForm(EMPTY);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1>Submit a Purchase Request</h1>
      <p className="subtitle">Describe what you need in plain language — ProcureFlow will classify it and either process it automatically or route it for approval.</p>

      <form className="form-card" onSubmit={submit}>
        <label>Your name</label>
        <input required value={form.employee_name} onChange={set("employee_name")} placeholder="Rahul Sharma" />

        <label>Work email</label>
        <input required type="email" value={form.employee_email} onChange={set("employee_email")} placeholder="rahul@company.com" />

        <label>Department</label>
        <input required value={form.department} onChange={set("department")} placeholder="Engineering" />

        <label>What do you need?</label>
        <textarea required value={form.request_text} onChange={set("request_text")} placeholder="I need 5 keyboards for the engineering team because our new interns are joining next week." />

        <button className="primary" type="submit" disabled={submitting}>
          {submitting ? "Submitting…" : "Submit request"}
        </button>
      </form>

      {error && (
        <div className="result-card" style={{ borderColor: "#a3372f", background: "#fbe8e6" }}>
          {error}
        </div>
      )}

      {result && (
        <div className="result-card">
          <div style={{ marginBottom: 8 }}>
            <strong>{result.request_id}</strong> &nbsp; <StatusBadge status={result.status} />
          </div>
          <div>{result.message}</div>
        </div>
      )}
    </div>
  );
}
