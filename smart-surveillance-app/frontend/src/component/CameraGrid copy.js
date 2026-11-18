import React, { useState } from "react";
import api from "../services/api";

function CameraGrid({ cameras, aiDetection, setAiDetection, timestamp }) {
  const [selectedCam, setSelectedCam] = useState(null);

  const handleImageError = (camId) => {
    console.error(`Stream image failed to load for camera ${camId}`);
  };

  return (
    <>
      <div
        className={`camera-grid grid-${cameras.length}`}
      >
        {cameras.length === 0 ? (
          <p className="no-data">No cameras added yet.</p>
        ) : (
          cameras.map((cam) => (
            <div
              key={cam.id}
              className="camera-card"
              onClick={() => setSelectedCam(cam)}
              style={{ cursor: "pointer" }}
            >
              <div className="camera-header">
                <span className="camera-title">
                  {cam.name} <span className="camera-location">({cam.location})</span>
                </span>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontSize: "0.85rem", color: "#ddd" }}>
                    <input
                      type="checkbox"
                      checked={!!aiDetection[cam.id]}
                      onChange={(e) =>
                        setAiDetection({
                          ...aiDetection,
                          [cam.id]: e.target.checked,
                        })
                      }
                    />
                    🤖 AI Detection
                  </label>
                  <span className="live-indicator">
                    <span className="blink-dot"></span> Live
                  </span>
                </div>
              </div>
              <img
                src={
                  aiDetection[cam.id]
                    ? `${api.defaults.baseURL}/detection/frame/${cam.id}?t=${timestamp}`
                    : `${api.defaults.baseURL}/cameras/${cam.id}/frame?t=${timestamp}`
                }
                alt={`Camera ${cam.name}`}
                className="camera-video"
                onError={() => handleImageError(cam.id)}
              />
            </div>
          ))
        )}
      </div>

      {/* Modal for enlarged camera */}
      {selectedCam && (
        <div className="camera-modal">
          <div className="modal-content">
            <button
              className="modal-close"
              onClick={() => setSelectedCam(null)}
            >
              ✕
            </button>
            <h3>{selectedCam.name} ({selectedCam.location})</h3>
            <img
              src={
                aiDetection[selectedCam.id]
                  ? `${api.defaults.baseURL}/detection/frame/${selectedCam.id}?t=${timestamp}`
                  : `${api.defaults.baseURL}/cameras/${selectedCam.id}/frame?t=${timestamp}`
              }
              alt={`Camera ${selectedCam.name}`}
              style={{ width: "100%", height: "auto", borderRadius: "8px" }}
            />
          </div>
        </div>
      )}
    </>
  );
}

export default CameraGrid;
