// src/core/ZoneManagement.js
import React, { useState, useEffect, useContext } from "react";
import api from "../../services/api";
import { MessageContext } from "../../context/MessageContext";
import ZoneSetup from "./ZoneSetup";
import ZonesTable from "../../component/ZonesTable";
import "../../styles/global.css";

function ZoneManagement() {
  const { showMessage } = useContext(MessageContext);
  const [cameras, setCameras] = useState([]);
  const [zones, setZones] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState("");
  const [showZoneSetup, setShowZoneSetup] = useState(false);

  useEffect(() => {
    fetchCameras();
  }, []);

  const fetchCameras = async () => {
    try {
      const res = await api.get("/cameras/");
      setCameras(res.data.data || []);
      showMessage("success", "Cameras loaded successfully");
    } catch (err) {
      console.error("Failed to fetch cameras:", err);
      showMessage("error", "Failed to fetch cameras");
    }
  };

  const fetchZones = async (cameraId) => {
    if (!cameraId) return;
    try {
      const res = await api.get(`/zones/?camera_id=${cameraId}`);
      setZones(res.data.data || []);
      showMessage("success", "Zones loaded successfully");
    } catch (err) {
      console.error("Failed to fetch zones:", err);
      showMessage("error", "Failed to fetch zones");
    }
  };

  const saveZone = async (id, zone) => {
    try {
      if (id) {
        await api.put(`/zones/${id}`, zone);
        showMessage("success", "Zone updated successfully!");
      } else {
        await api.post(`/zones/`, zone);
        showMessage("success", "Zone created successfully!");
      }
      fetchZones(selectedCamera);
    } catch {
      showMessage("error", id ? "Failed to update zone!" : "Failed to create zone!");
    }
  };

  const deleteZone = async (id) => {
    try {
      await api.delete(`/zones/${id}`);
      showMessage("success", "Zone removed successfully!");
      fetchZones(selectedCamera);
    } catch (err) {
      console.error("Failed to remove zone:", err);
      showMessage("error", "Failed to remove zone");
    }
  };

  return (
    <div className="round-card zone-management-container">
      <h2 className="zone-management-title">Manage Zones</h2>

      {/* Camera Selector */}
      <div className="zone-selector">
        <select
          value={selectedCamera}
          onChange={(e) => {
            const camId = e.target.value;
            setSelectedCamera(camId);
            fetchZones(camId);
          }}
          className="input-field"
        >
          <option value="">Select Camera</option>
          {cameras.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>

        {selectedCamera && (
          <button
            onClick={() => setShowZoneSetup((prev) => !prev)}
            className="primary-btn"
          >
            {showZoneSetup ? "Close Zone Setup" : "Open Zone Setup"}
          </button>
        )}
      </div>

      {/* Inline Zone Setup */}
      {showZoneSetup && (
        <div className="zone-setup-wrapper">
          <ZoneSetup
            initialCamera={selectedCamera}
            cameraName={cameras.find((c) => c.id === Number(selectedCamera))?.name}
          />
        </div>
      )}

      {/* Zone List only when ZoneSetup is closed */}
      {!showZoneSetup && (
        <div className="zone-table-wrapper">
          {zones.length > 0 ? (
            <ZonesTable
              zones={zones}
              onEdit={() => {}}          // optional, if you want editing
              onDelete={(id) => deleteZone(id)} // ✅ correct prop name
              saveZone={saveZone}
            />
          ) : selectedCamera ? (
            <p className="zone-empty">No zone setup for this camera.</p>
          ) : (
            <p className="zone-empty">Select a camera to view its zones.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default ZoneManagement;
