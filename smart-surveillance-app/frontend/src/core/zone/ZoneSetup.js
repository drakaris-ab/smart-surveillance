// src/core/ZoneSetup.js
import React, { useState, useEffect, useRef, useContext } from "react";
import api from "../../services/api";
import { MessageContext } from "../../context/MessageContext";
import ZonesTable from "../../component/ZonesTable";
import "../../styles/global.css";

export default function ZoneSetup({ initialCamera ,cameraName }) {
  const { showMessage } = useContext(MessageContext);
  const SNAPSHOT_BASE = api.defaults.baseURL;

  const [cameras, setCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState(initialCamera || "");
  const [snapshot, setSnapshot] = useState(null);
  const [points, setPoints] = useState([]);
  const [zones, setZones] = useState([]);
  const [editingZone, setEditingZone] = useState(null);

  const canvasRef = useRef(null);
  const imageRef = useRef(null);

  useEffect(() => {
    fetchCameras();
  }, []);

  useEffect(() => {
    if (initialCamera) {
      setSelectedCamera(initialCamera);
      setSnapshot(null);
      setPoints([]);
      setEditingZone(null);
    }
  }, [initialCamera]);

  useEffect(() => {
    if (selectedCamera) fetchZones(selectedCamera);
  }, [selectedCamera]);

  const fetchCameras = async () => {
    try {
      const res = await api.get("/cameras/");
      setCameras(res.data.data || []);
    } catch {
      showMessage("error", "Failed to fetch cameras");
    }
  };

  const fetchZones = async (cameraId) => {
    try {
      const res = await api.get(`/zones/?camera_id=${cameraId}`);
      setZones(res.data.data || []);
    } catch {
      showMessage("error", "Failed to fetch zones");
    }
  };

  const handleCaptureSnapshot = async (preserveEditing = false) => {
    try {
      const res = await api.get(`/zones/capture_snapshot/${selectedCamera}`);
      if (!res.data?.path) throw new Error("No snapshot path returned");
      setSnapshot(res.data.path);
      if (!preserveEditing) {
        setPoints([]);
        setEditingZone(null);
      }
      showMessage("success", "Snapshot captured successfully!");
    } catch {
      showMessage("error", "Failed to capture snapshot!");
    }
  };

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    setPoints((prev) => [...prev, { x: Math.round(x), y: Math.round(y) }]);
  };

  const handleUndoPoint = () => setPoints((prev) => prev.slice(0, -1));

  useEffect(() => {
  if (!snapshot) return;
  const canvas = canvasRef.current;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  const img = new Image();
  img.src = `${SNAPSHOT_BASE}${snapshot}`;
  img.onload = () => {
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    if (points.length > 0) {
      ctx.strokeStyle = "#ff0000";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      points.forEach((p, i) => {
        if (i > 0) ctx.lineTo(p.x, p.y);
      });
      if (points.length > 2) ctx.closePath();
      ctx.stroke();

      points.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, 2 * Math.PI);
        ctx.fillStyle = "#2563eb";
        ctx.fill();
      });
    }
  };
}, [snapshot, points]);


  const saveZone = async (id, zone) => {
    try {
      if (id) {
        await api.put(`/zones/${id}`, zone);
        showMessage("success", "Zone updated successfully!");
      } else {
        if (zones && zones.length > 0) {
          showMessage("error", "Zone setup is already present for this camera.");
          return;
        }
        await api.post(`/zones/`, zone);
        showMessage("success", "Zone created successfully!");
      }
      fetchZones(selectedCamera);
    } catch (err) {
      const errorMsg = err?.response?.data?.detail;
      showMessage("error", errorMsg || (id ? "Failed to update zone!" : "Failed to create zone!"));
    }
  };

  const deleteZone = async (id) => {
    try {
      await api.delete(`/zones/${id}`);
      showMessage("success", "Zone removed!");
      setZones((prev) => prev.filter((z) => z.id !== id));
    } catch {
      showMessage("error", "Failed to remove zone!");
    }
  };

  return (
    <div className="round-card zone-setup-container">
      
      {/* Camera Dropdown */}
      <div className="zone-selector">
        <span className="selected-camera-label">
        Camera : {cameraName }
      </span>
        

        {selectedCamera && (
          <button
            onClick={() => handleCaptureSnapshot(false)}
            className="primary-btn"
          >
            📸 Capture Snapshot
          </button>
        )}
      </div>

      {/* Snapshot Canvas */}
      {snapshot && (
        <div className="snapshot-canvas-wrapper">
          
          <canvas ref={canvasRef} onClick={handleCanvasClick} className="snapshot-canvas" />
        </div>
      )}

      {/* Zone Drawing Controls */}
      {points.length > 0 && (
        <div className="zone-controls">
          <button onClick={handleUndoPoint} className="secondary-btn">↩️ Undo Point</button>
          <button
            onClick={() =>
              saveZone(
                editingZone?.id || null,
                editingZone || {
                  polygon_coords: JSON.stringify(points),
                  camera_id: Number(selectedCamera),
                  snapshot_file: snapshot,
                }
              )
            }
            className="primary-btn"
          >
            💾 {editingZone ? "Update Zone" : "Save Zone"}
          </button>
          <button
            onClick={() => {
              setPoints([]);
              showMessage("info", "Drawing cleared!");
            }}
            className="secondary-btn danger-btn"
          >
            ❌ Clear Zone
          </button>
        </div>
      )}

      {/* Zones Table */}
      {zones.filter((z) => Number(z.camera_id) === Number(selectedCamera)).length > 0 && (
        <ZonesTable
          zones={zones.filter((z) => Number(z.camera_id) === Number(selectedCamera))}
          onEdit={setEditingZone}
          onDelete={(id) => deleteZone(id)}
          saveZone={saveZone}
        />
      )}
    </div>
  );
}
