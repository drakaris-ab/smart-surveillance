// src/components/Dashboard.js
import React, { useState, useEffect, useContext, useRef } from "react";
import api from "../../services/api";
import { MessageContext } from "../../context/MessageContext";
import messages from "../../constants/messages";
import "../../styles/global.css";
import Modal from "react-modal";
import { getConfig } from "../../config";
Modal.setAppElement("#root"); // important for accessibility

function Dashboard() {
  const [cameras, setCameras] = useState([]);
  const [aiDetection, setAiDetection] = useState({});
  const { showMessage } = useContext(MessageContext);

  useEffect(() => {
    loadCameras();
  }, []);

  const loadCameras = async () => {
    try {
      const res = await api.get("/cameras/");
      const camerasData = res.data.data || [];
      setCameras(camerasData);
      const initialAiState = {};
      camerasData.forEach((c) => (initialAiState[c.id] = true));
      setAiDetection(initialAiState);
    } catch (err) {
      console.error("Error loading cameras:", err);
      showMessage("error", "Failed to load cameras");
      setCameras([]);
    }
  };

  const handleImageError = (camId) => {
    console.error(`Stream connection failed for camera ${camId}`);
    showMessage("error", `Stream unavailable for camera ${camId}`);
  };

  return (
    <div className="round-card">
      <div className="form-container">
        <main className="work-area">
          <div className="camera-grid">
            {cameras.length === 0 ? (
              <p className="no-data">No cameras added yet.</p>
            ) : (
              cameras.map((cam) => (
                <LazyCameraCard
                  key={cam.id}
                  cam={cam}
                  aiDetection={aiDetection}
                  setAiDetection={setAiDetection}
                  handleImageError={handleImageError}
                />
              ))
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

function LazyCameraCard({ cam, aiDetection, setAiDetection, handleImageError }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const modalCanvasRef = useRef(null);
  const [visible, setVisible] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // Lazy loading
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setVisible(true);
            observer.disconnect();
          }
        });
      },
      { threshold: 0.25 }
    );
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // WebSocket stream
  useEffect(() => {
    if (!visible) return;

    const mode = aiDetection[cam.id] ? "processed" : "raw";
    const dynamicConfig = getConfig();
    const baseHttpUrl = (dynamicConfig && dynamicConfig.apiBaseUrl && dynamicConfig.port)
      ? `${dynamicConfig.apiBaseUrl}:${dynamicConfig.port}`
      : (api.defaults.baseURL || "http://localhost:8000");
    const wsProtocol = baseHttpUrl.startsWith("https") ? "wss://" : "ws://";
    const cleanHost = baseHttpUrl.replace(/^https?:\/\//, "");
    const wsUrl = `${wsProtocol}${cleanHost}/cameras/${cam.id}/stream?mode=${mode}`;
    const ws = new WebSocket(wsUrl);
    ws.binaryType = "blob";

    ws.onmessage = (event) => {
      const blob = event.data;
      const url = URL.createObjectURL(blob);
      const img = new Image();

      img.onload = () => {
        // draw to small canvas
        if (canvasRef.current) {
          const ctx = canvasRef.current.getContext("2d");
          if (
            canvasRef.current.width !== img.width ||
            canvasRef.current.height !== img.height
          ) {
            canvasRef.current.width = img.width;
            canvasRef.current.height = img.height;
          }
          ctx.drawImage(img, 0, 0);
        }
        // draw to modal canvas if open
        if (showModal && modalCanvasRef.current) {
          const ctxModal = modalCanvasRef.current.getContext("2d");
          if (
            modalCanvasRef.current.width !== img.width ||
            modalCanvasRef.current.height !== img.height
          ) {
            modalCanvasRef.current.width = img.width;
            modalCanvasRef.current.height = img.height;
          }
          ctxModal.drawImage(img, 0, 0);
        }
        URL.revokeObjectURL(url);
      };
      img.src = url;
    };

    ws.onerror = () => {
      handleImageError(cam.id);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [visible, aiDetection[cam.id], cam.id, showModal]);

  return (
    <div className="camera-card" ref={containerRef}>
      <div className="camera-header">
        <span className="camera-title">
          {cam.name} <span className="camera-location">({cam.location})</span>
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontSize: "0.85rem", color: "#ddd", userSelect: "none" }}>
            <input
              type="checkbox"
              checked={!!aiDetection[cam.id]}
              onChange={(e) =>
                setAiDetection({
                  ...aiDetection,
                  [cam.id]: e.target.checked,
                })
              }
              style={{ cursor: "pointer" }}
            />
            🤖 AI Detection
          </label>
          <span className="live-indicator">
            <span className="blink-dot"></span> Live
          </span>
        </div>
      </div>
      {visible ? (
        <canvas
          ref={canvasRef}
          className="camera-video"
          style={{
            display: "block",
            width: "100%",
            height: "auto",
            borderRadius: "0 0 8px 8px",
            background: "#000",
            cursor: "pointer",
          }}
          onClick={() => setShowModal(true)}
        />
      ) : (
        <div style={{ width: "100%", height: "200px", background: "#222", borderRadius: "0 0 8px 8px", display: "flex", alignItems: "center", justifyContent: "center", color: "#888" }}>
          Loading camera…
        </div>
      )}

      <Modal
        isOpen={showModal}
        onRequestClose={() => setShowModal(false)}
        style={{
          content: {
            background: "#111",          // darker background for contrast
            display: "flex",
            flexDirection: "column",     // stack header + canvas
            justifyContent: "flex-start",
            alignItems: "center",
            padding: 0,
            width: "60%",                // moderate size
            height: "60%",
            margin: "auto",
            borderRadius: "8px",
            overflow: "hidden",          // no scrollbars
          },
          overlay: {
            backgroundColor: "rgba(0,0,0,0.7)",
          },
        }}
      >
        {/* Header bar */}
        <div
          style={{
            width: "100%",
            background: "#222",
            color: "#fff",
            padding: "10px 16px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: "1rem",
            fontWeight: "500",
          }}
        >
          <span>{cam.name} ({cam.location})</span>
          <button
            onClick={() => setShowModal(false)}
            style={{
              background: "transparent",
              border: "none",
              color: "#fff",
              fontSize: "1.2rem",
              cursor: "pointer",
            }}
          >
            ✖
          </button>
        </div>

        {/* Enlarged video canvas */}
        <canvas
          ref={modalCanvasRef}
          className="camera-video-large"
          style={{
            flex: 1,
            width: "85%",
            height: "85%",
            background: "#000",
          }}
        />
      </Modal>

    </div>
  );
}

export default Dashboard;
