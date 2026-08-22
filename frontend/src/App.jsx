import { Routes, Route, NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "./api.js";
import Dashboard from "./pages/Dashboard.jsx";
import SubmitRequest from "./pages/SubmitRequest.jsx";
import RequestDetail from "./pages/RequestDetail.jsx";
import Integrations from "./pages/Integrations.jsx";

export default function App() {
  const [notionUrl, setNotionUrl] = useState(import.meta.env.VITE_NOTION_WORKSPACE_URL || "https://notion.so");
  const [notionLabel, setNotionLabel] = useState("Open Notion Workspace");
  useEffect(() => {
    api.integrationStatus().then((status) => {
      if (status.procureflow_url) {
        setNotionUrl(status.procureflow_url);
        setNotionLabel("Open ProcureFlow in Notion");
      }
    }).catch(() => {});
  }, []);
  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="brand">ProcureFlow <span className="stamp">OPS</span></div>
        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>Dashboard</NavLink>
          <NavLink to="/submit" className={({ isActive }) => (isActive ? "active" : "")}>Submit Request</NavLink>
          <NavLink to="/settings/integrations" className={({ isActive }) => (isActive ? "active" : "")}>Integrations</NavLink>
          <a href={notionUrl} target="_blank" rel="noreferrer" className="notion-link">{notionLabel} ↗</a>
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
