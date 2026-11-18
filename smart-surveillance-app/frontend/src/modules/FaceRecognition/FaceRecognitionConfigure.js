import React, { useEffect, useState, useContext } from "react";
import { faceApi } from "../../services/api";
import { MessageContext } from "../../context/MessageContext";
import messages from "../../constants/messages";
import "../../styles/global.css";

function FaceRecognitionConfigure() {
  const [cameras, setCameras] = useState([]);
  const { showMessage } = useContext(MessageContext);
  const userId = localStorage.getItem("userId"); // logged-in user

  useEffect(() => {
    loadCameras();
  }, []);

  const loadCameras = async () => {
    try {
      const res = await faceApi.get("/assign_camera/");
      const camerasData = res.data.data || [];
      setCameras(camerasData);
    } catch {
      showMessage("error", messages.CAMERA_FETCH_FAIL);
      setCameras([]);
    }
  };

  const handleAssign = async (cameraId) => {
    try {
      const res = await faceApi.post(`/assign_camera/?camera_id=${cameraId}&user=${userId}`);
      if (res.data.status === "success") {
        showMessage("success", "Camera assigned for face recognition");
        loadCameras();
      }
    } catch {
      showMessage("error", "Failed to assign camera");
    }
  };

  const handleUnassign = async (cameraId) => {
    try {
      const res = await faceApi.delete(`/assign_camera/${cameraId}?user=${userId}`);
      if (res.data.status === "success") {
        showMessage("success", "Camera unassigned from face recognition");
        loadCameras();
      }
    } catch {
      showMessage("error", "Failed to unassign camera");
    }
  };

  return (
    <div className="configure-tab">
      <h3>Face Recognition Camera Configuration</h3>
      <div className="table-wrap">
        <table className="camera-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Camera Name</th>
              <th>Location</th>
              <th>Assigned</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {cameras.map((cam, idx) => (
              <tr
                key={cam.camera_id}
                className={idx % 2 === 0 ? "row-even" : "row-odd"}
              >
                <td>{cam.camera_id}</td>
                <td>{cam.name}</td>
                <td>{cam.location}</td>
                <td>{cam.is_assigned ? "Yes" : "No"}</td>
                <td>
                  {cam.is_assigned ? (
                    <button
                      className="secondary-btn danger-btn"
                      onClick={() => handleUnassign(cam.camera_id)}
                    >
                      Unassign
                    </button>
                  ) : (
                    <button
                      className="primary-btn"
                      onClick={() => handleAssign(cam.camera_id)}
                    >
                      Assign
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {cameras.length === 0 && (
              <tr>
                <td colSpan="5" style={{ textAlign: "center", color: "#888" }}>
                  No cameras configured yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default FaceRecognitionConfigure;
