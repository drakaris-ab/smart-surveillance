// src/module/unwantedobject/UnattendedObject.js
import React, {
  useState,
  useContext,
  useMemo,
  useRef,
  useCallback,
  useEffect,
} from "react";
import axios from "axios";
import { MessageContext } from "../../context/MessageContext";
import { getConfig } from "../../config";
import ConfigureCamera from "./ConfigureCamera";
import TuningPanel from "./TuningPanel";
import ObjectTracking from "./ObjectTracking";
import SystemDiagnostics from "./SystemDiagnostics";
import "../../styles/global.css";
import messages from "../../constants/messages";
import { UnwantedobjectApi } from "../../services/api";

const FALLBACK_URL = "http://localhost:8002";

function resolveWorkerUrl() {
  const config = getConfig() || {};
  if (config.unattendedObjectUrl) return config.unattendedObjectUrl;
  if (config.apiBaseUrl && config.unattendedObjectPort) {
    return `${config.apiBaseUrl}:${config.unattendedObjectPort}`;
  }
  return process.env.UNWANTED_OBJECT_BASE_URL || FALLBACK_URL;
}

const objectApi = axios.create({ timeout: 8000 });
objectApi.interceptors.request.use((config) => {
  config.baseURL = resolveWorkerUrl();
  console.log(
    "[Axios] Request:",
    config.method?.toUpperCase(),
    config.baseURL + config.url
  );
  return config;
});

function UnattendedObject() {
  const [activeTab, setActiveTab] = useState("configure");
  const [cameras, setCameras] = useState([]);
  const [status, setStatus] = useState({});
  const [live, setLive] = useState({});
  const { showMessage } = useContext(MessageContext);
  const workerUrl = useMemo(() => resolveWorkerUrl(), []);
  const liveClock = useRef({});

  // --- Load cameras from DB + pipeline state ---
  useEffect(() => {
    loadCameras();
  }, [activeTab]);

  const loadCameras = async () => {
    try {
      // DB cameras
      const dbRes = await UnwantedobjectApi.get("/Unwanted_camera");
      const dbCameras = dbRes.data.data || [];

      // Running cameras from pipeline
      const runRes = await objectApi.get("/unattended-object/cameras");
      const runningIds = (runRes.data.cameras || []).map((c) => c.camera_id);

      const camerasData = dbCameras.map((c) => ({
        id: c.camera_id,
        name: c.name,
        rtsp_url: c.rtsp_url,
        location: c.location,
        is_assigned: c.is_assigned,
        running: runningIds.includes(c.camera_id),
      }));

      console.log("[LoadCameras] Normalized cameras:", camerasData);
      setCameras(camerasData);

      // Stop unassigned cameras or start assigned cameras
      camerasData.forEach(async (c) => {
        if (!c.is_assigned && c.running) {
          try {
            console.log("[LoadCameras] Stopping unassigned camera:", c.id);
            await objectApi.post(`/unattended-object/cameras/${c.id}/stop`);
            setCameras((prev) => prev.map((cam) => cam.id === c.id ? { ...cam, running: false } : cam));
          } catch (err) {
            console.error("[LoadCameras] Failed to stop camera:", c.id, err);
          }
        }
        if (c.is_assigned && !c.running) {
          try {
            console.log("[LoadCameras] Starting assigned camera:", c.id);
            const config = getConfig() || {};
            const mainApiUrl = `${config.apiBaseUrl || "http://localhost"}:${config.port || "8000"}`;
            await objectApi.post("/unattended-object/cameras/start", {
              camera_id: c.id,
              name: c.name,
              rtsp_url: c.rtsp_url,
              use_frame_sharing: true,
              frame_sharing_url: mainApiUrl,
              frame_sharing_camera_id: c.id,
            });
            setCameras((prev) => prev.map((cam) => cam.id === c.id ? { ...cam, running: true } : cam));
          } catch (err) {
            console.error("[LoadCameras] Failed to start camera:", c.id, err);
          }
        }
      });
    } catch (err) {
      console.error("[LoadCameras] Error:", err);
      showMessage("error", messages.CAMERA_FETCH_FAIL);
      setCameras([]);
    }
  };

  // --- Polling and frame handling logic ---
  const pollStatus = useCallback(async () => {
    if (!cameras.length) {
      console.log("[PollStatus] No cameras to poll.");
      return;
    }
    console.log("[PollStatus] Polling cameras:", cameras.map((c) => c.id));
    const results = await Promise.allSettled(
      cameras.map((camera) =>
        objectApi.get(`/unattended-object/track/${camera.id}`)
      )
    );
    const next = {};
    results.forEach((result, index) => {
      const camera = cameras[index];
      if (result.status === "fulfilled") {
        console.log("[PollStatus] Success:", camera.id, result.value.data);
        next[camera.id] = result.value.data;
      } else {
        console.error("[PollStatus] Error:", camera.id, result.reason);
        next[camera.id] = {
          objects: [],
          alerts: [],
          error: "Worker unreachable",
        };
      }
    });
    setStatus(next);
  }, [cameras]);

  useEffect(() => {
    if (!cameras.length) return;
    console.log("[useEffect] Starting poll interval for cameras:", cameras.length);
    pollStatus();
    const interval = setInterval(pollStatus, 3000);
    return () => {
      console.log("[useEffect] Clearing poll interval");
      clearInterval(interval);
    };
  }, [cameras, pollStatus]);

  const handleFrame = useCallback((cameraId, payload) => {
    console.log("[HandleFrame] Camera:", cameraId, "Payload:", payload);
    if (!payload || !payload.changed) return;
    const now = Date.now();
    if (now - (liveClock.current[cameraId] || 0) < 750) return;
    liveClock.current[cameraId] = now;
    const objects = payload.objects || [];
    setLive((prev) => ({
      ...prev,
      [cameraId]: {
        seq: payload.seq,
        objects: objects.length,
        people: objects.filter((o) => o.is_person).length,
        threats: objects.filter((o) => o.is_threat).length,
        unattended: objects.filter((o) => o.ownerless && !o.is_threat).length,
        error: payload.error || null,
      },
    }));
  }, []);

  const startCamera = async (camera) => {
    console.log("[StartCamera] Starting camera:", camera);
    try {
      const config = getConfig() || {};
      const mainApiUrl = `${config.apiBaseUrl || "http://localhost"}:${config.port || "8000"}`;

      await objectApi.post("/unattended-object/cameras/start", {
        camera_id: camera.id,
        name: camera.name,
        rtsp_url: camera.rtsp_url,
        use_frame_sharing: true,
        frame_sharing_url: mainApiUrl,
        frame_sharing_camera_id: camera.id,
      });
      setCameras((prev) =>
        prev.map((c) =>
          c.id === camera.id ? { ...c, running: true } : c
        )
      );
      await pollStatus();
    } catch (err) {
      console.error("[StartCamera] Error:", err);
      showMessage("error", `Could not start ${camera.name}`);
    }
  };

  const stopCamera = async (camera) => {
    console.log("[StopCamera] Stopping camera:", camera);
    try {
      await objectApi.post(`/unattended-object/cameras/${camera.id}/stop`);
      setCameras((prev) =>
        prev.map((c) =>
          c.id === camera.id ? { ...c, running: false } : c
        )
      );
      setLive((prev) => ({ ...prev, [camera.id]: undefined }));
    } catch (err) {
      console.error("[StopCamera] Error:", err);
      showMessage("error", `Could not stop ${camera.name}`);
    }
  };

  const removeCamera = async (camera) => {
    console.log("[RemoveCamera] Removing camera:", camera);
    if (camera.running) await stopCamera(camera);
    setCameras((prev) => prev.filter((c) => c.id !== camera.id));
    setStatus((prev) => {
      const next = { ...prev };
      delete next[camera.id];
      return next;
    });
  };

  console.log(
    "[Render] ActiveTab:",
    activeTab,
    "Cameras:",
    cameras,
    "Status:",
    status,
    "Live:",
    live
  );

  return (
    <div className="round-card full-screen">
      <h2 className="page-title">Unattended Object Module</h2>

      {/* Tab Navigation */}
      <div className="tab-buttons blue-theme">
        <button
          onClick={() => {
            console.log("[TabSwitch] configure");
            setActiveTab("configure");
          }}
          className={activeTab === "configure" ? "tab-button active" : "tab-button"}
        >
          Configure Camera
        </button>
        <button
          onClick={() => {
            console.log("[TabSwitch] tuning");
            setActiveTab("tuning");
          }}
          className={activeTab === "tuning" ? "tab-button active" : "tab-button"}
        >
          Tuning Panel
        </button>
        <button
          onClick={() => {
            console.log("[TabSwitch] object");
            setActiveTab("object");
          }}
          className={activeTab === "object" ? "tab-button active" : "tab-button"}
        >
          Object Tracking
        </button>
        <button
          onClick={() => {
            console.log("[TabSwitch] diagnostics");
            setActiveTab("diagnostics");
          }}
          className={activeTab === "diagnostics" ? "tab-button active" : "tab-button"}
        >
          System Diagnostics
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === "configure" && (
          <ConfigureCamera
            cameras={cameras}
            setCameras={setCameras}
            showMessage={showMessage}
          />
        )}
        {activeTab === "tuning" && (
          <TuningPanel baseUrl={workerUrl} notify={showMessage} />
        )}
        {activeTab === "object" && (
          <ObjectTracking
            cameras={cameras.filter(c => c.is_assigned)}
            status={status}
            live={live}
            workerUrl={workerUrl}
            handleFrame={handleFrame}
            startCamera={startCamera}
            stopCamera={stopCamera}
            removeCamera={removeCamera}
          />
        )}
        {activeTab === "diagnostics" && (
          <SystemDiagnostics workerUrl={workerUrl} />
        )}
      </div>
    </div>
  );
}

export default UnattendedObject;
