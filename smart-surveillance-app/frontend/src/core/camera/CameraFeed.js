import React, { useEffect, useRef, useState } from "react";
import "../../styles/global.css";

export default function CameraFeed({ cameraId, name, location, streamUrl, isConnected, onSnapshot, style }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const [visible, setVisible] = useState(false);
  const [hasError, setHasError] = useState(false);

  // Lazy loading observer
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

  useEffect(() => {
    if (!visible || !isConnected || !streamUrl) return;

    // Convert http/https to ws/wss
    const wsUrl = streamUrl.replace(/^http/, "ws");
    const ws = new WebSocket(wsUrl);
    ws.binaryType = "blob";

    ws.onmessage = (event) => {
      setHasError(false);
      const blob = event.data;
      const url = URL.createObjectURL(blob);
      const img = new Image();

      img.onload = () => {
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
        URL.revokeObjectURL(url);
      };
      img.src = url;
    };

    ws.onerror = () => {
      console.error(`Stream connection failed for camera ${cameraId}`);
      setHasError(true);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [visible, isConnected, streamUrl, cameraId]);

  return (
    <div className="camera-card" ref={containerRef} style={{ ...style, display: "flex", flexDirection: "column" }}>
      <div className="camera-header" style={{ display: "flex", justifyContent: "space-between", padding: "10px", background: "#1e293b", color: "#fff", borderRadius: "8px 8px 0 0" }}>
        <span className="camera-title" style={{ fontWeight: "bold" }}>
          {name} <span className="camera-location" style={{ fontWeight: "normal", color: "#94a3b8" }}>({location})</span>
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {onSnapshot && (
            <button 
              className="primary-btn" 
              onClick={() => onSnapshot(cameraId)}
              style={{ padding: "4px 8px", fontSize: "0.8rem", borderRadius: "4px" }}
            >
              📸 Snapshot
            </button>
          )}
          <span className="live-indicator" style={{ color: hasError ? "#dc2626" : "#22c55e", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "4px" }}>
            <span className="blink-dot" style={{ width: "8px", height: "8px", background: hasError ? "#dc2626" : "#22c55e", borderRadius: "50%", display: "inline-block" }}></span> 
            {hasError ? "Offline" : "Live"}
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
            minHeight: "200px"
          }}
        />
      ) : (
        <div style={{ width: "100%", height: "200px", background: "#0f172a", borderRadius: "0 0 8px 8px", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b" }}>
          Loading camera...
        </div>
      )}
    </div>
  );
}
