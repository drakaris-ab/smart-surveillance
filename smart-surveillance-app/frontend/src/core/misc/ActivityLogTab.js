import React, { useEffect, useState, useContext } from "react";
import { ApiContext } from "../../context/ApiContext";
import "../../styles/global.css";

export default function ActivityLogTab() {
  const api = useContext(ApiContext); 
  const [activityLogs, setActivityLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(true);

  // Session info
  const loginTime = localStorage.getItem("login_time") || new Date().toLocaleString();

  useEffect(() => {
    const fetchActivityLogs = async () => {
      try {
        const res = await api.get("/activity_log/");
        setActivityLogs(res.data.data || res.data || []);
      } catch (error) {
        console.error("Error fetching activity logs:", error);
      } finally {
        setLoadingLogs(false);
      }
    };

    fetchActivityLogs();
  }, [api]);

  const formatAction = (action) => {
    if (!action) return "-";
    const lower = action.toLowerCase();
    if (lower.includes("login")) return "Logged In";
    if (lower.includes("logout")) return "Logged Out";
    return action;
  };

  const formatStatus = (action) => {
    if (!action) return "-";
    const lower = action.toLowerCase();
    if (lower.includes("login")) return "Active";
    if (lower.includes("logout")) return "Inactive";
    return "-";
  };

  return (
    <div className="activity-log-container">
      <h2 className="activity-log-title">Activity Log Stream</h2>

      {/* Session Info */}
      <ul className="session-info">
        <li>
          <strong>Last Login:</strong> {loginTime}
        </li>
        <li>
          <strong>Session Active:</strong> ✅
        </li>
      </ul>

      {/* Activity Logs Table */}
      <div className="activity-log-table">
        {loadingLogs ? (
          <p className="activity-log-loading">Loading activity logs...</p>
        ) : (
          <table className="styled-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Description</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {activityLogs.length > 0 ? (
                activityLogs.map((log) => {
                  const status = formatStatus(log.action);
                  return (
                    <tr key={log.id}>
                      <td>{log.timestamp ? new Date(log.timestamp).toLocaleString() : "-"}</td>
                      <td className="activity-log-action">{formatAction(log.action)}</td>
                      <td>{log.description || "-"}</td>
                      <td>
                        <span className={`activity-status ${status.toLowerCase()}`}>
                          {status}
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="4" className="activity-log-empty">
                    No activity logs yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
