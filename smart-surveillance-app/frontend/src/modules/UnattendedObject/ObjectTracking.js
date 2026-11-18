import React, { useState } from "react";
import CameraCanvas from "./CameraCanvas";

// --- Simple Modal Component ---
function RawDetailsModal({ isOpen, onClose, cameraId, workerUrl }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    Promise.all([
      fetch(`${workerUrl}/unattended-object/detections/${cameraId}`).then(r => r.json()),
      fetch(`${workerUrl}/unattended-object/alerts/${cameraId}`).then(r => r.json())
    ])
      .then(([dets, alts]) => {
        setDetails({ detections: dets, alerts: alts });
        setLoading(false);
      })
      .catch((err) => {
        setDetails({ error: err.message });
        setLoading(false);
      });
  }, [isOpen, cameraId, workerUrl]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="modal-content round-card" style={{ background: '#1e293b', padding: '2rem', maxWidth: '800px', width: '90%', maxHeight: '80vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3>Raw Details for Camera {cameraId}</h3>
          <button onClick={onClose} style={{ padding: '0.5rem 1rem', background: '#dc2626', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Close</button>
        </div>
        {loading ? <p>Loading...</p> : (
          <pre style={{ background: '#0b1220', padding: '1rem', borderRadius: '4px', overflowX: 'auto', color: '#e2e8f0', fontSize: '0.85rem' }}>
            {JSON.stringify(details, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}

function ObjectTracking({ cameras = [], status, live, workerUrl, handleFrame, startCamera, stopCamera, removeCamera }) {
  const [activeModalCamera, setActiveModalCamera] = useState(null);
  const [viewStreamMode, setViewStreamMode] = useState({});

  // --- Auto-start unstarted cameras (like Face Recognition) ---
  React.useEffect(() => {
    cameras.forEach(camera => {
      if (!camera.running) {
        startCamera(camera);
      }
    });
  }, [cameras, startCamera]);

  const toggleStreamMode = (cameraId) => {
    setViewStreamMode(prev => ({ ...prev, [cameraId]: !prev[cameraId] }));
  };

  const downloadSnapshot = async (cameraId) => {
    try {
      const response = await fetch(`${workerUrl}/unattended-object/snapshot/${cameraId}`);
      if (!response.ok) throw new Error("Could not fetch snapshot");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `snapshot_${cameraId}_${Date.now()}.jpg`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Failed to download snapshot: " + err.message);
    }
  };

  const renderTile = (camera) => {
    const state = status[camera.id];
    const counts = live[camera.id];
    const alerts = state?.alerts || [];
    const topAlert = alerts[0];
    const error = counts?.error || state?.error;

    return (
      <div key={camera.id} className={`camera-tile ${topAlert ? "camera-tile-alert" : ""}`}>
        <div className="camera-tile-header">
          <span className="camera-name">{camera.name}</span>
          <span className="camera-tile-header-right">
            {topAlert && <span className="camera-alert-dot" title={topAlert.message} />}
            <button type="button" className="camera-remove" onClick={() => removeCamera(camera)}>×</button>
          </span>
        </div>

        {viewStreamMode[camera.id] ? (
          <div className="camera-tile-video">
            <img
              src={`${workerUrl}/unattended-object/stream/${camera.id}`}
              alt={`Live stream for ${camera.name}`}
              className="video-feed"
              style={{ width: "100%", height: "100%", objectFit: "contain" }}
            />
          </div>
        ) : (
          <CameraCanvas
            baseUrl={workerUrl}
            cameraId={camera.id}
            running={camera.running}
            onFrame={(payload) => handleFrame(camera.id, payload)}
          />
        )}

        <div className="camera-tile-info">
          {error ? (
            <span className="camera-tile-error">{error}</span>
          ) : (
            <span>
              {camera.running
                ? `${counts?.objects ?? 0} object(s) · ${counts?.people ?? 0} person(s)` +
                (counts?.unattended ? ` · ${counts.unattended} unattended` : "")
                : "Idle"}
            </span>
          )}
          {topAlert && <span className="camera-tile-alert-text">⚠️ {topAlert.message}</span>}
        </div>

        <div className="camera-tile-controls" style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          <button disabled={camera.running} onClick={() => startCamera(camera)}>Start</button>
          <button disabled={!camera.running} onClick={() => stopCamera(camera)}>Stop</button>
          {camera.running && (
            <>
              <button onClick={() => downloadSnapshot(camera.id)}>Snapshot</button>
              <button onClick={() => toggleStreamMode(camera.id)}>
                {viewStreamMode[camera.id] ? "View Canvas" : "View Stream"}
              </button>
              <button onClick={() => setActiveModalCamera(camera.id)}>Raw Details</button>
            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="round-card">
      <h3>Object Tracking</h3>
      <div className="camera-scroll-container">
        {cameras.map(renderTile)}
        {!cameras.length && <p>Add a camera above to begin.</p>}
      </div>
      {cameras.length > 0 && (
        <div className="uod-legend">
          <span><i style={{ background: "#38bdf8" }} /> person</span>
          <span><i style={{ background: "#22c55e" }} /> attended object</span>
          <span><i style={{ background: "#facc15" }} /> unattended, timing</span>
          <span><i style={{ background: "#f97316" }} /> threat</span>
          <span><i style={{ background: "#dc2626" }} /> high severity</span>
        </div>
      )}

      <RawDetailsModal
        isOpen={activeModalCamera !== null}
        onClose={() => setActiveModalCamera(null)}
        cameraId={activeModalCamera}
        workerUrl={workerUrl}
      />
    </div>
  );
}

export default ObjectTracking;
