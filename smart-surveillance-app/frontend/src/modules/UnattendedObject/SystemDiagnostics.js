import React, { useEffect, useState } from "react";
import axios from "axios";
import "../../styles/global.css";

const client = axios.create({ timeout: 8000 });

function SystemDiagnostics({ workerUrl }) {
  const [health, setHealth] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchDiagnostics = async () => {
    try {
      const [healthRes, perfRes] = await Promise.all([
        client.get(`${workerUrl}/unattended-object/health`),
        client.get(`${workerUrl}/unattended-object/system/performance`)
      ]);
      setHealth(healthRes.data);
      setPerformance(perfRes.data);
      setError("");
    } catch (err) {
      setError("Could not reach the detection worker to fetch diagnostics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
    const interval = setInterval(fetchDiagnostics, 5000);
    return () => clearInterval(interval);
  }, [workerUrl]);

  if (loading) return <p>Loading diagnostics...</p>;
  if (error) return <p className="tune-error">{error}</p>;

  return (
    <div className="configure-tab" style={{ padding: "1rem" }}>
      <h3>System Diagnostics</h3>
      
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "1rem" }}>
        {/* Health Information */}
        <div className="round-card" style={{ padding: "1rem", background: "var(--card-bg, #1e293b)" }}>
          <h4>Health Status</h4>
          <p><strong>Status:</strong> {health?.status}</p>
          <p><strong>Model:</strong> {health?.model}</p>
          <p><strong>ReID Status:</strong> {health?.reid?.usable ? "Usable" : "Unavailable"}</p>
          <p><strong>Running Cameras:</strong> {health?.running_cameras?.length || 0}</p>
        </div>

        {/* Runtime & VRAM Information */}
        <div className="round-card" style={{ padding: "1rem", background: "var(--card-bg, #1e293b)" }}>
          <h4>Hardware Performance</h4>
          <p><strong>Device:</strong> {performance?.runtime?.device}</p>
          {performance?.vram && (
            <>
              <p><strong>VRAM Total:</strong> {performance.vram.total_mb} MB</p>
              <p><strong>VRAM Used:</strong> {performance.vram.used_mb} MB</p>
              <p><strong>VRAM Free:</strong> {performance.vram.free_mb} MB</p>
            </>
          )}
        </div>
      </div>

      {/* Camera Performances */}
      <h4 style={{ marginTop: "2rem", marginBottom: "1rem" }}>Camera Performances</h4>
      {performance?.cameras?.length > 0 ? (
        <div className="table-wrap">
          <table className="camera-table">
            <thead>
              <tr>
                <th>Camera ID</th>
                <th>Avg FPS</th>
                <th>Inference Share</th>
                <th>JPEG Share</th>
                <th>Objects</th>
              </tr>
            </thead>
            <tbody>
              {performance.cameras.map((cam, idx) => (
                <tr key={cam.camera_id} className={idx % 2 === 0 ? "row-even" : "row-odd"}>
                  <td>{cam.camera_id}</td>
                  <td>{cam.metrics?.avg_fps?.toFixed(1) || "-"}</td>
                  <td>{cam.inference_share_of_cycle ? (cam.inference_share_of_cycle * 100).toFixed(1) + "%" : "-"}</td>
                  <td>{cam.jpeg_share_of_cycle ? (cam.jpeg_share_of_cycle * 100).toFixed(1) + "%" : "-"}</td>
                  <td>{cam.metrics?.objects_count || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>No cameras are currently running to report performance.</p>
      )}
    </div>
  );
}

export default SystemDiagnostics;
