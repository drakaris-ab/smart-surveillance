// src/layout/Sidebar.js
import React, { useState, useEffect, useContext } from "react";
import { NavLink } from "react-router-dom";
import api from "../services/api";
import { MessageContext } from "../context/MessageContext";
import "../styles/global.css";

function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [modules, setModules] = useState([]);
  const { showMessage } = useContext(MessageContext);

  useEffect(() => {
    loadUserModules();
  }, []);

  const loadUserModules = async () => {
    try {
      const userId = localStorage.getItem("userId");
      if (!userId) return;

      const res = await api.get(`/users/${userId}/modules`);
      setModules(res.data.data || []);
    } catch {
      showMessage("error", "Failed to load user modules");
      setModules([]);
    }
  };

  return (
    <div className={`sidebar-container ${collapsed ? "collapsed" : ""}`}>
      <nav className="sidebar">
        <ul>
          {modules.map((m) => (
            <li key={m.id}>
              <NavLink
                to={`/${m.name.toLowerCase().replace(/\s+/g, "-")}`}
                className={({ isActive }) => (isActive ? "active-link" : "")}
                title={m.name}
              >
                <span className="menu-icon">{getIcon(m.name)}</span>
                {!collapsed && <span className="menu-text">{m.name}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Collapse Handle with 3 dots */}
      <div
        className="collapse-handle"
        onClick={() => setCollapsed(!collapsed)}
      >
        <span className="dot"></span>
        <span className="dot"></span>
        <span className="dot"></span>
      </div>
    </div>
  );
}

function getIcon(name) {
  switch (name.toLowerCase()) {
    case "dashboard": return "🏠";
    case "cameras": return "📷";
    case "zones": return "🗺️";
    case "alerts": return "⚠️";
    case "users": return "👤";
    case "configure modules": return "⚙️";
    case "face recognition": return "🧑‍💻";
    case "unidentified object": return "🎒";
    case "safety check": return "🛡️";
    case "suspicious activity": return "👀";
    case "module access": return "🔑";
    default: return "📌";
  }
}

export default Sidebar;
