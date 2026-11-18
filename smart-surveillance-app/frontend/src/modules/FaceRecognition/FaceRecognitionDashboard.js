import React, { useEffect, useState, useContext } from "react";
import api, { faceApi } from "../../services/api";
import CameraFeed from "../../core/camera/CameraFeed";
import { MessageContext } from "../../context/MessageContext";
import "../../styles/global.css";
import cameraIcon from "../../assets/logo.png";

function FaceRecognitionDashboard() {
  const [cameras, setCameras] = useState([]);
  const [faces, setFaces] = useState([]);
  const [alerts, setAlerts] = useState({});
  const [loadingCamera, setLoadingCamera] = useState(null); // ✅ spinner state
  const [formData, setFormData] = useState({
    name: "",
    phone: "",
    address: "",
    aadhaar: "",
    criminal_flag: false,
  });

  const { showMessage } = useContext(MessageContext);
  console.log("Face API Base URL:", faceApi.defaults.baseURL);

  useEffect(() => {
    loadCameras();
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadCameras = async () => {
    try {
      const res = await faceApi.get("/assign_camera/");
      const camerasData = res.data.data || [];
      const assignedCameras = camerasData.filter(cam => cam.is_assigned === true);
      setCameras(assignedCameras);
    } catch (err) {
      console.error("Error loading cameras:", err);
      showMessage("error", "Failed to load cameras");
      setCameras([]);
    }
  };

  const fetchAlerts = async () => {
    try {
      const res = await faceApi.get("/alerts/active");
      const activeAlerts = res.data || [];

      const alertsMap = {};
      for (const alert of activeAlerts) {
        alertsMap[alert.camera_id] = alert.message;
        try {
          await faceApi.post(`/alerts/consume/${alert.id}`);
        } catch (consumeErr) {
          console.error("Failed to consume alert:", consumeErr);
        }
      }
      setAlerts(alertsMap);
    } catch (err) {
      console.error("Error fetching alerts:", err);
    }
  };

  const handleSnapshot = async (cameraId) => {
    setLoadingCamera(cameraId); // ✅ show spinner
    try {
      const res = await faceApi.get(`/face-re-users/recognize/${cameraId}`);
      if (res.data.faces) {
        setFaces(res.data.faces);
        res.data.faces.forEach((face, idx) => {
          if (face.status === "recognized") {
            showMessage("success", `Face ${idx + 1} recognized: ${face.details.name}`);
          } else {
            showMessage("warning", `Face ${idx + 1} unrecognized`);
          }
        });
      } else if (res.data.status === "no_faces") {
        setFaces([]);
        showMessage("info", "No face detected in the snapshot");
      }
    } catch (err) {
      console.error("Recognition error:", err);
      showMessage("error", "Recognition failed");
    } finally {
      setLoadingCamera(null); // ✅ hide spinner
    }
  };

  const handleFormChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleEnroll = async (embedding) => {
    try {
      const payload = { ...formData, embedding };
      const res = await faceApi.post("/face-re-users/enroll", payload);
      if (res.data) {
        showMessage("success", `User ${res.data.name} enrolled successfully`);
        setFaces([]);
        setFormData({
          name: "",
          phone: "",
          address: "",
          aadhaar: "",
          criminal_flag: false,
        });
      }
    } catch (err) {
      console.error("Enroll error:", err);
      showMessage("error", "Failed to enroll user");
    }
  };

  return (
    <div style={{ padding: "24px", background: "rgba(255,255,255,0.05)", borderRadius: "12px" }}>
      <h2 style={{ color: "white", marginBottom: "20px" }}>Face Recognition Dashboard</h2>

      {/* Camera Grid */}
      <div
        style={{
          display: "grid",
          gap: "20px",
          gridTemplateColumns: cameras.length === 1 ? "320px 1fr" : "repeat(auto-fit, minmax(320px, 1fr))",
          alignItems: "start",
        }}
      >
        {cameras.length === 0 ? (
          <p className="no-data">No cameras assigned for face recognition.</p>
        ) : (
          cameras.map((cam) => (
            <div
              key={cam.camera_id}
              style={{
                border: alerts[cam.camera_id] ? "3px solid red" : "1px solid gray",
                borderRadius: "8px",
                padding: "8px",
                position: "relative",
              }}
            >
              <CameraFeed
                cameraId={cam.camera_id}
                name={cam.name}
                location={cam.location}
                streamUrl={`${api.defaults.baseURL}/cameras/${cam.camera_id}/stream`}
                isConnected={true}
                onSnapshot={handleSnapshot}
                style={{ width: cameras.length === 1 ? "320px" : "100%" }}
              />

              {/* ✅ Spinner overlay */}
              {loadingCamera === cam.camera_id && (
                <div className="spinner-overlay">
                  <div className="spinner">
                    <img
                      src={cameraIcon}
                      alt="AI CCTV Logo"
                      className="spinner-logo"
                    />
                  </div>
                </div>
              )}

              {alerts[cam.camera_id] && (
                <p style={{ color: "red", marginTop: "8px" }}>{alerts[cam.camera_id]}</p>
              )}
            </div>
          ))
        )}
      </div>

      {/* Faces Result Grid */}
      <div style={{ display: "grid", gap: "20px", marginTop: "20px", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
        {faces.map((face, idx) => (
          <div
            key={idx}
            className="card"
            style={{
              border: face.status === "recognized" ? "2px solid green" : "2px solid red",
              padding: "16px",
              borderRadius: "8px",
              background: "rgba(255,255,255,0.1)",
            }}
          >
            {face.thumbnail && (
              <img
                src={`data:image/jpeg;base64,${face.thumbnail}`}
                alt="Face thumbnail"
                style={{
                  width: "100px",
                  height: "100px",
                  objectFit: "cover",
                  borderRadius: "6px",
                  marginBottom: "10px",
                }}
              />
            )}

            {face.status === "recognized" ? (
              <>
                <h3>Recognized User</h3>
                <p><strong>Name:</strong> {face.details.name}</p>
                <p><strong>Phone:</strong> {face.details.phone}</p>
                <p><strong>Address:</strong> {face.details.address}</p>
                <p><strong>Aadhaar:</strong> {face.details.aadhaar}</p>
                <p><strong>Authorized:</strong> {face.details.criminal_flag ? "Yes" : "No"}</p>
              </>
            ) : (
              <>
                <h3>Unrecognized Face</h3>
                <form
                  onSubmit={(e) => { e.preventDefault(); handleEnroll(face.embedding); }}
                  style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}
                >
                  {["name", "phone", "address", "aadhaar"].map((field) => (
                    <input
                      key={field}
                      type="text"
                      name={field}
                      value={formData[field]}
                      onChange={handleFormChange}
                      placeholder={field.toUpperCase()}
                      className="input-field"
                      style={{ margin: 0 }}
                      required={field === "name"}
                    />
                  ))}
                  <label className="checkbox-label" style={{ gridColumn: "span 2" }}>
                    <input
                      type="checkbox"
                      name="criminal_flag"
                      checked={formData.criminal_flag}
                      onChange={handleFormChange}
                    />
                    Criminal Flag
                  </label>
                  <button
                    type="submit"
                    className="primary-btn"
                    style={{ gridColumn: "span 2" }}
                  >
                    Enroll User
                  </button>
                </form>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default FaceRecognitionDashboard;
