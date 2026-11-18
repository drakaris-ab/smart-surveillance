import React, { useEffect, useState, useContext } from "react";
import useAlertService from "../../services/alertService";
import { ApiContext } from "../../context/ApiContext";
import { getConfig } from "../../config";
import "../../styles/global.css";

export default function NotificationsTab() {
  const api = useContext(ApiContext);
  const [alerts, setAlerts] = useState([]);
  const [filteredAlerts, setFilteredAlerts] = useState([]);
  const [filters, setFilters] = useState({ date: "", time: "", camera: "" });
  const [showFilters, setShowFilters] = useState(false);
  const [activeSubtab, setActiveSubtab] = useState("zone"); // "zone" or "unidentified_object"
  const alertService = useAlertService();

  const getSnapshotUrl = (snapshotPath) => {
    if (!snapshotPath) return "";
    const normalized = String(snapshotPath).trim();
    if (normalized.startsWith("http://") || normalized.startsWith("https://")) {
      return normalized;
    }
    return `${getConfig().apiBaseUrl}:${getConfig().port}${
      normalized.startsWith("/") ? "" : "/"
    }${normalized}`;
  };

  const fetchAlerts = async () => {
    try {
      const res = await api.get("/alerts/", {
        params: { alert_type: activeSubtab === "zone" ? "zone" : "unidentified_object" }
      });
      const data = res.data.data || res.data;
      if (Array.isArray(data)) {
        setAlerts(data);
        setFilteredAlerts(data);
      } else {
        alertService.warning("Unexpected alerts response format");
      }
    } catch (err) {
      alertService.error("Failed to fetch alerts");
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, [activeSubtab]);

  useEffect(() => {
    let filtered = alerts;
    if (filters.date) {
      filtered = filtered.filter((a) => a.timestamp?.startsWith(filters.date));
    }
    if (filters.time) {
      filtered = filtered.filter((a) => a.timestamp?.includes(filters.time));
    }
    if (filters.camera) {
      filtered = filtered.filter(
        (a) => String(a.camera_id) === String(filters.camera)
      );
    }
    setFilteredAlerts(filtered);
  }, [filters, alerts]);

  // Reset filters when subtab changes
  useEffect(() => {
    setFilters({ date: "", time: "", camera: "" });
  }, [activeSubtab]);

  const subtabLabels = {
    zone: "Zone Alerts",
    unidentified_object: "Unidentified Object Alerts"
  };

  return (
    <div className="notifications-container">
      <h2 className="notifications-title">Notifications Feed</h2>

      {/* Subtab Navigation */}
      <div className="notifications-subtabs">
        {Object.entries(subtabLabels).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setActiveSubtab(key)}
            className={`subtab-button ${activeSubtab === key ? "active" : ""}`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="notifications-filter-toggle">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="primary-btn"
        >
          {showFilters ? "❌ Hide Search" : "🔍 Search"}
        </button>
      </div>

      {showFilters && (
        <div className="notifications-filters">
          <div>
            <label className="notifications-label">Date</label>
            <input
              type="date"
              value={filters.date}
              onChange={(e) =>
                setFilters({ ...filters, date: e.target.value })
              }
              className="input-field"
            />
          </div>

          <div>
            <label className="notifications-label">Time (HH:MM)</label>
            <input
              type="time"
              value={filters.time}
              onChange={(e) =>
                setFilters({ ...filters, time: e.target.value })
              }
              className="input-field"
            />
          </div>

          <div>
            <label className="notifications-label">Camera #</label>
            <input
              type="text"
              placeholder="e.g. 1"
              value={filters.camera}
              onChange={(e) =>
                setFilters({ ...filters, camera: e.target.value })
              }
              className="input-field"
            />
          </div>

          <button
            onClick={() => setFilters({ date: "", time: "", camera: "" })}
            className="secondary-btn"
          >
            ❌ Clear
          </button>
        </div>
      )}

      {filteredAlerts.length === 0 ? (
        <p className="notifications-empty">
          {activeSubtab === "zone"
            ? "No zone alerts yet."
            : "No unidentified object alerts yet."
          }
        </p>
      ) : (
        <ul className="notifications-grid">
          {filteredAlerts.map((a, idx) => (
            <li key={a.id || idx} className="notification-card text-only" style={{ display: 'flex', alignItems: 'center', gap: '15px', padding: '16px', background: 'rgba(0,0,0,0.05)', borderRadius: '8px', borderLeft: '4px solid #3b82f6', marginBottom: '10px' }}>
              <div style={{ fontSize: '24px' }}>
                {activeSubtab === "zone" ? "🚨" : "🎒"}
              </div>
              <div className="notification-details" style={{ flex: 1, padding: 0 }}>
                <p style={{ margin: '0 0 8px 0', fontSize: '1.1rem', color: '#000' }}>
                  <strong>{a.message || a.event_type || "Detection alert triggered"}</strong>
                </p>
                <div style={{ display: 'flex', gap: '20px', color: '#333', fontSize: '0.9rem' }}>
                  <span>📸 Camera {a.camera_id || "Unknown"}</span>
                  <span>🕒 {a.timestamp ? new Date(a.timestamp).toLocaleString() : "Not available"}</span>
                  {a.zone_id && <span>📍 Zone {a.zone_id}</span>}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
