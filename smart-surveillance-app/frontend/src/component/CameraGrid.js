// src/components/CameraGrid.js
import React, { useState, useEffect, useRef } from "react";
import api from "../services/api";

function CameraGrid({ cameras }) {
  const [selectedCam, setSelectedCam] = useState(null);
  const [aiDetection, setAiDetection] = useState(
    cameras.reduce((acc, cam) => {
      acc[cam.id] = true; // default ON
      return acc;
    }, {})
  );

  // refresh timestamp every 200ms for live frames (optional if you want cache-busting)
  const [timestamp, setTimestamp] = useState(Date.now());
  useEffect(() => {
    const interval = setInterval(() => setTimestamp(Date.now()), 200);
    return () => clearInterval(interval);
  }, []);

  const handleImageError = (camId) => {
    console.error(`Stream failed for camera ${camId}`);
  };

  return (
    <>
      <div className="camera-grid-wrapper">
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
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      cursor: "pointer",
                      fontSize: "0.85rem",
                      color: "#ddd",
                      userSelect: "none",
                    }}
                    onClick={(e) => e.stopPropagation()} // prevent modal open when toggling
                  >
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
                    ? `${api.defaults.baseURL}/cameras/${cam.id}/stream?mode=raw&r=${timestamp}`
                    : `${api.defaults.baseURL}/cameras/${cam.id}/stream?mode=processed&r=${timestamp}`
                }
                alt={`Camera ${cam.name}`}
                className="camera-video"
                onError={() => handleImageError(cam.id)}
              />
            </div>
          ))
        )}
      </div>

      {/* Modal with enlarged feed */}
      {selectedCam && (
        <div className="camera-modal">
          <div className="modal-content">
            <button className="modal-close" onClick={() => setSelectedCam(null)}>✕</button>
            <h3>
              {selectedCam.name} ({selectedCam.location})
            </h3>
            <img
              src={`${api.defaults.baseURL}/cameras/${selectedCam.id}/stream?mode=raw&r=${timestamp}`}
              alt={`Camera ${selectedCam.name}`}
              style={{ width: "100%", borderRadius: "8px" }}
            />
          </div>
        </div>
      )}
    </>
  );
}

export default CameraGrid;
