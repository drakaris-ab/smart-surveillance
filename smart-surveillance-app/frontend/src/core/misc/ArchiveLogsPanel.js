import React, { useState, useContext } from "react";
import useAlertService from "../../services/alertService";
import { ApiContext } from "../../context/ApiContext";
import "../../styles/global.css";

export default function ArchiveLogsPanel() {
  const [destination, setDestination] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(false);
  const api = useContext(ApiContext);
  const alertService = useAlertService();

  const startArchiveLogs = async () => {
    if (!destination || !startDate || !endDate) {
      alertService.error("Please fill destination, start date, and end date.");
      return;
    }
    setLoading(true);
    try {
      const res = await api.post("/archive/logs", {
        destination,
        start_date: startDate,
        end_date: endDate,
      });
      const data = res.data;
      alertService.success(
        `Archived ${data.archived_count} log(s) to ${data.destination} (file: ${data.file}).`
      );
    } catch (e) {
      alertService.error(
        e.response?.data?.detail || e.message || "Log archive failed."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="archive-logs-container">
      <h3 className="archive-logs-title">Archive Logs</h3>

      <div className="archive-logs-form">
        <div>
          <label className="archive-logs-label">
            Destination folder (path)
          </label>
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="e.g., C:\\Archives\\Logs"
            className="input-field"
          />
        </div>

        <div className="archive-logs-date-grid">
          <div>
            <label className="archive-logs-label">Start date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="input-field"
            />
          </div>
          <div>
            <label className="archive-logs-label">End date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="input-field"
            />
          </div>
        </div>
      </div>

      <div className="archive-logs-actions">
        <button
          onClick={startArchiveLogs}
          disabled={loading}
          className="primary-btn"
          style={{ opacity: loading ? 0.6 : 1 }}
        >
          {loading ? "Archiving..." : "📦 Start Archive"}
        </button>
      </div>
    </div>
  );
}
