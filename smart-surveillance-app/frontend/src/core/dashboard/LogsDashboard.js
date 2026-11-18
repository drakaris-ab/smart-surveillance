import React, { useState, useEffect, useContext } from "react";
import api from "../../services/api";
import { MessageContext } from "../../context/MessageContext";
import ActivityLogTab from "../misc/ActivityLogTab";
import ArchiveLogsPanel from "../misc/ArchiveLogsPanel";
import "../../styles/global.css";

function SystemLogsTab({ logs }) {
  return (
    <div style={{ maxWidth: "100%", margin: "0 auto" }}>
      <h2 style={{ color: "white", marginBottom: "20px" }}>📝 System Activity Logs</h2>
      <div style={{ overflowX: "auto" }}>
        <table className="styled-table" style={{ minWidth: "100%" }}>
          <thead>
            <tr>
              <th>ID</th>
              <th>User ID</th>
              <th>Action</th>
              <th>Description</th>
              <th>Status</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: "center", color: "#d1d5db", fontStyle: "italic" }}>No activity logs found.</td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id}>
                  <td>{log.id}</td>
                  <td>{log.user_id || "System"}</td>
                  <td>{log.action}</td>
                  <td>{log.description}</td>
                  <td>
                    <span className={`status-badge ${(log.status || "Success").toLowerCase()}`}>
                      {log.status || "Success"}
                    </span>
                  </td>
                  <td>{log.timestamp ? new Date(log.timestamp).toLocaleString() : "N/A"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LogsDashboard() {
  const [logs, setLogs] = useState([]);
  const { showMessage } = useContext(MessageContext);
  const [activeTab, setActiveTab] = useState("system");

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    try {
      const res = await api.get("/activity_log/");
      setLogs(res.data.data || res.data || []);
    } catch (err) {
      showMessage("error", "Failed to load activity logs");
      setLogs([]);
    }
  };

  return (
    <div className="round-card" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', gap: '15px', marginBottom: '24px', borderBottom: '1px solid rgba(255,255,255,0.2)', paddingBottom: '15px' }}>
        <button 
          onClick={() => setActiveTab("system")} 
          className={activeTab === "system" ? "primary-btn" : "secondary-btn"}
          style={activeTab === "system" ? { margin: 0 } : { margin: 0, background: 'transparent', color: '#d1d5db' }}
        >
          📝 System Logs
        </button>
        <button 
          onClick={() => setActiveTab("stream")} 
          className={activeTab === "stream" ? "primary-btn" : "secondary-btn"}
          style={activeTab === "stream" ? { margin: 0 } : { margin: 0, background: 'transparent', color: '#d1d5db' }}
        >
          📊 Activity Stream
        </button>
        <button 
          onClick={() => setActiveTab("archive")} 
          className={activeTab === "archive" ? "primary-btn" : "secondary-btn"}
          style={activeTab === "archive" ? { margin: 0 } : { margin: 0, background: 'transparent', color: '#d1d5db' }}
        >
          📦 Archive Logs
        </button>
      </div>

      {activeTab === "system" && <SystemLogsTab logs={logs} />}
      {activeTab === "stream" && <ActivityLogTab />}
      {activeTab === "archive" && <ArchiveLogsPanel />}
    </div>
  );
}

export default LogsDashboard;
