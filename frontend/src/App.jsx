import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import SubmitRequest from "./pages/SubmitRequest.jsx";
import RequestDetail from "./pages/RequestDetail.jsx";

const NOTION_URL = import.meta.env.VITE_NOTION_WORKSPACE_URL || "https://notion.so";

export default function App() {
  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="brand">ProcureFlow <span className="stamp">OPS</span></div>
        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>Dashboard</NavLink>
          <NavLink to="/submit" className={({ isActive }) => (isActive ? "active" : "")}>Submit Request</NavLink>
          <a href={NOTION_URL} target="_blank" rel="noreferrer" className="notion-link">Open Notion Workspace ↗</a>
        </div>
      </div>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/submit" element={<SubmitRequest />} />
          <Route path="/requests/:id" element={<RequestDetail />} />
        </Routes>
      </main>
    </div>
  );
}
