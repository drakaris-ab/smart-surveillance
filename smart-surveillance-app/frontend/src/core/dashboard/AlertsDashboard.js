// src/components/AlertsDashboard.js
import React, { useState } from "react";
import api from "../../services/api";
import useAlerts from "../../hooks/useAlerts";
import useAlertService from "../../services/alertService";
import AlertMuteDashboard from "./AlertMuteDashboard";
import NotificationsTab from "../misc/NotificationsTab";
import SnapshotsTab from "../snapshots/SnapshotsTab";
import TodaySnapshotsTab from "../snapshots/TodaySnapshotsTab";
import ArchiveSnapshotsPanel from "../snapshots/ArchiveSnapshotsPanel";
import { getSnapshotUrl } from "../../utils/helpers";
import "../../styles/global.css";
 
function SystemAlertsTab() {
  const { alerts, setAlerts } = useAlerts(5000);
  const alertService = useAlertService();

  const deleteAlert = async (id) => {
    try {
      await api.delete(`/alerts/${id}`);
      alertService.success("Alert dismissed successfully");
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      alertService.error("Failed to dismiss alert");
    }
  };

  return (
    <div className="alerts-container">
      <h2 className="alerts-title">⚠️ System Alerts</h2>
      <div className="alerts-scroll">
        <table className="styled-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Camera ID</th>
              <th>Event Type</th>
              <th>Timestamp</th>
              <th>Image</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr>
                <td colSpan="6" className="alerts-empty">
                  No alerts found.
                </td>
              </tr>
            ) : (
              alerts.map((alert, index) => (
                <tr key={alert.id}>
                  <td>{index + 1}</td>
                  <td>{alert.camera_id}</td>
                  <td>{alert.event_type}</td>
                  <td>{new Date(alert.timestamp).toLocaleString()}</td>
                  <td>
                    {getSnapshotUrl(alert.image) ? (
                      <a
                        href={getSnapshotUrl(alert.image)}
                        target="_blank"
                        rel="noreferrer"
                        className="primary-btn snapshot-link"
                      >
                        View Snapshot
                      </a>
                    ) : (
                      "N/A"
                    )}
                  </td>
                  <td>
                    <button
                      onClick={() => deleteAlert(alert.id)}
                      className="secondary-btn dismiss-btn"
                    >
                      Dismiss
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AlertsDashboard() {
  const [activeTab, setActiveTab] = useState("system");
 
  return (
    <div className="round-card alerts-dashboard">
      {/* Modern Tab Header */}
      <div className="tab-buttons">
        <button
          onClick={() => setActiveTab("system")}
          className={activeTab === "system" ? "tab-button active" : "tab-button"}
        >
          ⚠️ System Alerts
        </button>
        <button
          onClick={() => setActiveTab("mute")}
          className={activeTab === "mute" ? "tab-button active" : "tab-button"}
        >
          🔇 Alert Mutes
        </button>
        <button
          onClick={() => setActiveTab("notifications")}
          className={activeTab === "notifications" ? "tab-button active" : "tab-button"}
        >
          🔔 Notifications
        </button>
        <button
          onClick={() => setActiveTab("snapshots")}
          className={activeTab === "snapshots" ? "tab-button active" : "tab-button"}
        >
          📸 Snapshots
        </button>
        <button
          onClick={() => setActiveTab("archive-snapshots")}
          className={activeTab === "archive-snapshots" ? "tab-button active" : "tab-button"}
        >
          📦 Archive Snapshots
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === "system" && <SystemAlertsTab />}
        {activeTab === "mute" && <AlertMuteDashboard />}
        {activeTab === "notifications" && <NotificationsTab />}
        {activeTab === "snapshots" && (
          <div className="snapshots-container">
            <TodaySnapshotsTab />
            <SnapshotsTab />
          </div>
        )}
        {activeTab === "archive-snapshots" && <ArchiveSnapshotsPanel />}
      </div>
    </div>
  );
}

export default AlertsDashboard;
