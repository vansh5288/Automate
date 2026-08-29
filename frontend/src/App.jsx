import { Routes, Route, NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "./api.js";
import Dashboard from "./pages/Dashboard.jsx";
import SubmitRequest from "./pages/SubmitRequest.jsx";
import RequestDetail from "./pages/RequestDetail.jsx";
import Integrations from "./pages/Integrations.jsx";

export default function App() {
  const [notionUrl, setNotionUrl] = useState("");
  const [notionLabel, setNotionLabel] = useState("Notion");
  const [connectionState, setConnectionState] = useState("loading");

  useEffect(() => {
    api
      .integrationStatus()
      .then((status) => {
        const state = status.connection_state || (status.mode === "REAL" ? "connected" : "demo");
        setConnectionState(state);
        if (status.procureflow_url && state === "connected") {
          setNotionUrl(status.procureflow_url);
          setNotionLabel("Open ProcureFlow in Notion ↗");
        } else if (state === "demo") {
          setNotionLabel("Demo Mode (No Notion)");
        } else if (state === "error") {
          setNotionLabel("Notion Configuration Error");
        } else {
          setNotionLabel("Notion Not Connected");
        }
      })
      .catch(() => {
        setConnectionState("error");
        setNotionLabel("Backend Unreachable");
      });
  }, []);

  const notionLinkEnabled = connectionState === "connected" && notionUrl;

  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="brand">
          ProcureFlow <span className="stamp">OPS</span>
        </div>
        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Dashboard
          </NavLink>
          <NavLink to="/submit" className={({ isActive }) => (isActive ? "active" : "")}>
            Submit Request
          </NavLink>
          <NavLink to="/settings/integrations" className={({ isActive }) => (isActive ? "active" : "")}>
            Integrations
          </NavLink>
          {notionLinkEnabled ? (
            <a href={notionUrl} target="_blank" rel="noreferrer" className="notion-link">
              {notionLabel}
            </a>
          ) : (
            <span style={{ color: "#8b93a1", fontSize: 13 }}>{notionLabel}</span>
          )}
        </div>
      </div>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/submit" element={<SubmitRequest />} />
          <Route path="/requests/:id" element={<RequestDetail />} />
          <Route path="/settings/integrations" element={<Integrations />} />
        </Routes>
      </main>
    </div>
  );
}
