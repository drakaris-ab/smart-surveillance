// src/components/CameraSetupTab.js
import React, { useState, useContext } from "react";
import { useCamera } from "../../context/CameraContext";
import { MessageContext } from "../../context/MessageContext";
import NewCameraTable from "../../component/NewCameraTable";
import "../../styles/global.css";

export default function CameraSetupTab() {
  const { cameras, addCamera, removeCamera, updateCamera, setCameras } = useCamera();
  const { showMessage } = useContext(MessageContext);

  const [form, setForm] = useState({ name: "", location: "", stream_url: "" });
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", location: "", stream_url: "" });
  const [isConnecting, setIsConnecting] = useState(false);

  // --- Add Camera ---
  const handleAdd = async (e) => {
    e.preventDefault();
    setIsConnecting(true);

    const startTime = Date.now();
    try {
      const res = await addCamera(form);   // backend POST
      showMessage("success", "Camera added successfully!");
      setCameras((prev) => [...prev, res]); // ✅ refresh list with new camera
      setForm({ name: "", location: "", stream_url: "" });
    } catch (err) {
      showMessage("error", "Failed to add camera");
    } finally {
      const elapsed = Date.now() - startTime;
      const minWait = 2500;
      const remaining = Math.max(0, minWait - elapsed);
      setTimeout(() => setIsConnecting(false), remaining);
    }
  };

  // --- Save Edit ---
  const saveEdit = async (id) => {
    try {
      const res = await updateCamera(id, editForm); // backend PUT
      setCameras((prev) =>
        prev.map((c) => (c.id === id ? res : c)) // ✅ replace updated camera
      );
      setEditingId(null);
      setEditForm({ name: "", location: "", stream_url: "" });
      showMessage("success", "Camera updated successfully!");
    } catch (err) {
      showMessage("error", "Failed to update camera");
    }
  };

  return (
    <div className="round-card card-container">
      {/* Add Camera Form */}
      <form onSubmit={handleAdd} className="form-grid">
        {/* Row 1: Name + Location side by side */}
        <input
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Name of the camera"
          className="input-field"
          required
        />
        <input
          value={form.location}
          onChange={(e) => setForm({ ...form, location: e.target.value })}
          placeholder="Camera Location"
          className="input-field"
        />

        {/* Row 2: Stream URL full width */}
        <input
          value={form.stream_url}
          onChange={(e) => setForm({ ...form, stream_url: e.target.value })}
          placeholder="RTSP stream url"
          className="input-field stream-url-input"
          required
        />

        {/* Row 3: Button full width */}
        <button type="submit" className="primary-btn full-width" disabled={isConnecting}>
          ➕ Add Camera
        </button>
      </form>

      {/* Loader */}
      {isConnecting && (
        <div className="connecting-modal">
          <div className="connecting-modal-content">
            <div className="spinner"></div>
            <p>Connecting to camera...</p>
          </div>
        </div>
      )}

      {/* Camera Table */}
      <NewCameraTable
        cameras={cameras}
        setCameras={setCameras}
        editingId={editingId}
        setEditingId={setEditingId}
        saveCamera={saveEdit}
        removeCamera={removeCamera}
      />
    </div>
  );
}
