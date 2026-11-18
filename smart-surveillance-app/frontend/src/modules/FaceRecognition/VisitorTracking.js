// src/FaceRecognition/VisitorTracking.js
import React, { useEffect, useState, useContext } from "react";
import { faceApi } from "../../services/api";
import { MessageContext } from "../../context/MessageContext";
import messages from "../../constants/messages";

function VisitorTracking({ setAlert }) {
  const [cameras, setCameras] = useState([]);
  const [visitorQuery, setVisitorQuery] = useState("");
  const [selectedVisitor, setSelectedVisitor] = useState(null);
  const { showMessage } = useContext(MessageContext);
  const [liveTrackingEnabled, setLiveTrackingEnabled] = useState(false);
  const userId = localStorage.getItem("userId"); // logged-in user

  useEffect(() => {
    loadCameras();
  }, []);

  const loadCameras = async () => {
    try {
      const res = await faceApi.get("/assign_camera/");
      const camerasData = res.data.data || [];
      setCameras(camerasData); // load all cameras, not just assigned
      showMessage("success", messages.CAMERA_FETCH_SUCCESS);
    } catch {
      showMessage("error", messages.CAMERA_FETCH_FAIL);
    }
  };

  const searchVisitor = async () => {
    if (!visitorQuery.trim()) {
      showMessage("error", messages.MANDATORY_VISITOR_FIELDS);
      return;
    }
    try {
      const res = await faceApi.get(`/assignments/search?q=${visitorQuery}`);
      setSelectedVisitor({
        ...res.data,
        assigned_cameras: res.data.assigned_cameras || [],
      });
      showMessage("success", messages.VISITOR_FETCH_SUCCESS);
    } catch {
      setSelectedVisitor(null);
      showMessage("error", messages.VISITOR_NOT_FOUND);
    }
  };

  // ✅ Toggle only updates local state
  const handleCameraToggle = (cameraId, checked) => {
    let updated;
    if (checked) {
      updated = [...selectedVisitor.assigned_cameras, cameraId];
    } else {
      updated = selectedVisitor.assigned_cameras.filter((id) => id !== cameraId);
    }
    setSelectedVisitor({ ...selectedVisitor, assigned_cameras: updated });
  };

  // ✅ Save pushes the full updated list to backend
  const saveAssignments = async () => {
    try {
      await faceApi.post("/assignments/assign", {
        user_id: selectedVisitor.id,
        camera_ids: selectedVisitor.assigned_cameras, // full array of assigned cameras
        actor: userId,
      });
      showMessage("success", messages.VISITOR_ACCESS_UPDATED);
    } catch {
      showMessage("error", messages.VISITOR_ACCESS_FAIL);
    }
  };

  //Fetch current status once
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await faceApi.get("/configurations/live-tracking-status");
        setLiveTrackingEnabled(res.data.live_tracking_enabled === "true");
      } catch {
        showMessage("error", "Failed to fetch live tracking status");
      }
    };
    fetchStatus();
  }, []);

  const toggleLiveTracking = async () => {
    try {
      const res = await faceApi.post("/configurations/toggle-live-tracking");
      setLiveTrackingEnabled(res.data.live_tracking_enabled === "true");
      showMessage("success", res.data.message);
    } catch {
      showMessage("error", "Failed to toggle live tracking");
    }
  };

  return (
    <div className="tracking-tab">
      <h3>Visitor Tracking</h3>

      {/* Search Visitor */}
      <div className="form-container">
        <input
          className="input-field full-width"
          placeholder="Enter Visitor Name / ID / Phone / Aadhaar"
          value={visitorQuery}
          onChange={(e) => setVisitorQuery(e.target.value)}
        />
        <button className="primary-btn" onClick={searchVisitor}>
          Search Visitor
        </button>
      </div>

      {/* Visitor Details + Camera Assignments */}
      {selectedVisitor && (
        <div className="visitor-row-card" style={{ display: "flex", gap: "20px", marginTop: "20px" }}>
          {/* Visitor Info */}
          <div className="visitor-info" style={{ flex: "1" }}>
            <h4>{selectedVisitor.name}</h4>
            <p><strong>Phone:</strong> {selectedVisitor.phone}</p>
            <p><strong>Aadhaar:</strong> {selectedVisitor.aadhaar}</p>
            <p><strong>Address:</strong> {selectedVisitor.address}</p>
          </div>

          {/* Assigned Cameras */}
          <div className="assigned-cameras" style={{ flex: "1" }}>
            <h5>Assign Cameras</h5>
            <div className="camera-grid">
              {cameras.map((cam) => (
                <div key={cam.camera_id} className="camera-card" style={{ display: "flex", gap: "12px", marginBottom: "6px" }}>
                  <img src="/logo3.png" alt="Camera icon" style={{ width: "75px", height: "75px" }} />
                  <div>
                    <label>
                      <input
                        type="checkbox"
                        checked={selectedVisitor.assigned_cameras.includes(cam.camera_id)}
                        onChange={(e) => handleCameraToggle(cam.camera_id, e.target.checked)}
                      />
                      <strong style={{ marginLeft: "6px" }}>Name: {cam.name}</strong>
                    </label>
                    <p style={{ margin: "2px 0", fontWeight: "bold" }}>Location: {cam.location}</p>
                    <p style={{ margin: "2px 0", fontWeight: "bold" }}>Camera ID: {cam.camera_id}</p>
                  </div>
                </div>
              ))}
            </div>
            {/* ✅ Save button persists changes */}
            <button className="primary-btn" onClick={saveAssignments}>
              Save Assignments
            </button>
          </div>
        </div>
      )}

      {/* Toggle Live Tracking */}
      <div style={{ marginTop: "20px" }}>
        <button className="primary-btn" onClick={toggleLiveTracking}>
          {liveTrackingEnabled ? "Stop Live Tracking" : "Start Live Tracking"}
        </button>
      </div>
    </div>
  );
}

export default VisitorTracking;
