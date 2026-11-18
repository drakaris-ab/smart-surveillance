import React, { useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { MessageContext } from "../../context/MessageContext";
import { getConfig } from "../../config";
import CameraCanvas from "./CameraCanvas";
import TuningPanel from "./TuningPanel";

const FALLBACK_URL = "http://localhost:8002";


function resolveWorkerUrl() {
  const config = getConfig() || {};
  if (config.unattendedObjectUrl) return config.unattendedObjectUrl;
  if (config.apiBaseUrl && config.unattendedObjectPort) {
    return `${config.apiBaseUrl}:${config.unattendedObjectPort}`;
  }
  return process.env.REACT_APP_UNATTENDED_OBJECT_API_URL || FALLBACK_URL;
}

const objectApi = axios.create({ timeout: 8000 });
objectApi.interceptors.request.use((config) => {
  config.baseURL = resolveWorkerUrl();
  return config;
});

const STATUS_POLL_MS = 3000;

const LIVE_UPDATE_MS = 750;

function UnattendedObject() {
  const [cameras, setCameras] = useState([]);
  const [form, setForm] = useState({ id: "", name: "", rtsp_url: "" });
  const [status, setStatus] = useState({});
  const [live, setLive] = useState({});
  const { showMessage } = useContext(MessageContext);
  const announced = useRef(new Set());
  const liveClock = useRef({});
  const workerUrl = useMemo(() => resolveWorkerUrl(), []);

  const announce = useCallback(
    (alerts) => {
      const present = new Set();
      alerts.forEach((alert) => {
        const key = alert.id || alert.alert_id;
        if (!key) return;
        present.add(key);
        if (!announced.current.has(key)) {
          announced.current.add(key);
          showMessage("warning", alert.message);
        }
      });
      return present;
    },
    [showMessage]
  );

  const pollStatus = useCallback(async () => {
    if (!cameras.length) return;
    const results = await Promise.allSettled(
      cameras.map((camera) => objectApi.get(`/unattended-object/track/${camera.id}`))
    );

    const next = {};
    const seen = new Set();
    results.forEach((result, index) => {
      const camera = cameras[index];
      if (result.status === "fulfilled") {
        next[camera.id] = result.value.data;
        announce(result.value.data.alerts || []).forEach((key) => seen.add(key));
      } else {
        next[camera.id] = {
          objects: [],
          alerts: [],
          processing: false,
          error: "Worker unreachable",
        };
      }
    });


    announced.current.forEach((key) => {
      if (!seen.has(key)) announced.current.delete(key);
    });

    setStatus(next);
  }, [cameras, announce]);

  useEffect(() => {
    if (!cameras.length) return undefined;
    pollStatus();
    const interval = setInterval(pollStatus, STATUS_POLL_MS);
    return () => clearInterval(interval);
  }, [cameras, pollStatus]);

  const handleFrame = useCallback((cameraId, payload) => {
    if (!payload || !payload.changed) return;
    const now = Date.now();
    if (now - (liveClock.current[cameraId] || 0) < LIVE_UPDATE_MS) return;
    liveClock.current[cameraId] = now;

    const objects = payload.objects || [];
    setLive((previous) => ({
      ...previous,
      [cameraId]: {
        seq: payload.seq,
        objects: objects.length,
        people: objects.filter((object) => object.is_person).length,
        threats: objects.filter((object) => object.is_threat).length,
        unattended: objects.filter((object) => object.ownerless && !object.is_threat).length,
        error: payload.error || null,
      },
    }));
  }, []);

  const addCamera = (event) => {
    event.preventDefault();
    if (!form.id || !form.name) {
      showMessage("error", "Camera ID and name are required");
      return;
    }
    if (!/^\d+$/.test(String(form.id).trim()) || Number(form.id) <= 0) {
      showMessage("error", "Camera ID must be a positive whole number");
      return;
    }
    if (cameras.some((camera) => String(camera.id) === String(form.id).trim())) {
      showMessage("error", "That camera ID is already added");
      return;
    }
    setCameras((previous) => [
      ...previous,
      {
        id: Number(form.id),
        name: form.name.trim(),
        rtsp_url: form.rtsp_url.trim() || "0",
        running: false,
      },
    ]);
    setForm({ id: "", name: "", rtsp_url: "" });
  };

  const setRunning = (cameraId, running) =>
    setCameras((previous) =>
      previous.map((camera) => (camera.id === cameraId ? { ...camera, running } : camera))
    );

  const startCamera = async (camera) => {
    try {
      const { data } = await objectApi.post("/unattended-object/cameras/start", {
        camera_id: camera.id,
        name: camera.name,
        rtsp_url: camera.rtsp_url,
        frame_url: null,
      });
      setRunning(camera.id, true);
      if (data.already_running) showMessage("info", `${camera.name} was already running`);
      await pollStatus();
    } catch (error) {

      const detail = error?.response?.data?.detail;
      showMessage("error", `Could not start ${camera.name}${detail ? `: ${detail}` : ""}`);
    }
  };

  const stopCamera = async (camera) => {
    try {
      await objectApi.post(`/unattended-object/cameras/${camera.id}/stop`);
      setRunning(camera.id, false);
      setLive((previous) => ({ ...previous, [camera.id]: undefined }));
    } catch (error) {
      showMessage("error", `Could not stop ${camera.name}`);
    }
  };

  const removeCamera = async (camera) => {
    if (camera.running) await stopCamera(camera);
    setCameras((previous) => previous.filter((entry) => entry.id !== camera.id));
    setStatus((previous) => {
      const next = { ...previous };
      delete next[camera.id];
      return next;
    });
  };

  const allAlerts = Object.values(status)
    .flatMap((entry) => entry?.alerts || [])
    .sort((a, b) => (b.severity_rank || 0) - (a.severity_rank || 0));
  const hasThreat = allAlerts.length > 0;

  const renderTile = (camera) => {
    const state = status[camera.id];
    const counts = live[camera.id];
    const alerts = state?.alerts || [];
    const topAlert = alerts[0];

    const error = counts?.error || state?.error;

    return (
      <div
        key={camera.id}
        className={`camera-tile ${topAlert ? "camera-tile-alert" : ""}`}
      >
        <div className="camera-tile-header">
          <span className="camera-name">{camera.name}</span>
          <span className="camera-tile-header-right">
            {topAlert && <span className="camera-alert-dot" title={topAlert.message} />}
            <button
              type="button"
              className="camera-remove"
              title="Remove camera"
              onClick={() => removeCamera(camera)}
            >
              ×
            </button>
          </span>
        </div>

        <CameraCanvas
          baseUrl={workerUrl}
          cameraId={camera.id}
          running={camera.running}
          onFrame={(payload) => handleFrame(camera.id, payload)}
        />

        <div className="camera-tile-info">
          {error ? (
            <span className="camera-tile-error">{error}</span>
          ) : (
            <span>
              {camera.running
                ? `${counts?.objects ?? 0} object(s) · ${counts?.people ?? 0} person(s)` +
                  (counts?.unattended ? ` · ${counts.unattended} unattended` : "")
                : "Idle"}
            </span>
          )}
          {topAlert && <span className="camera-tile-alert-text">⚠️ {topAlert.message}</span>}
        </div>

        <div className="camera-tile-controls">
          <button disabled={camera.running} onClick={() => startCamera(camera)}>
            Start
          </button>
          <button disabled={!camera.running} onClick={() => stopCamera(camera)}>
            Stop
          </button>
        </div>
      </div>
    );
  };

  const renderGrid = () => (
    <>
      <div className="camera-scroll-container">
        {cameras.map(renderTile)}
        {!cameras.length && <p>Add a camera above to begin.</p>}
      </div>
      {cameras.length > 0 && (
        <div className="uod-legend">
          <span><i style={{ background: "#38bdf8" }} /> person</span>
          <span><i style={{ background: "#22c55e" }} /> attended object</span>
          <span><i style={{ background: "#facc15" }} /> unattended, timing</span>
          <span><i style={{ background: "#f97316" }} /> threat</span>
          <span><i style={{ background: "#dc2626" }} /> high severity</span>
        </div>
      )}
    </>
  );

  return (
    <div className="uts-dashboard round-card full-screen">
      <h2 className="page-title">Unidentified Object Tracking</h2>

      <div className={`threat-summary-banner ${hasThreat ? "active" : ""}`}>
        <span className="threat-summary-title">
          {hasThreat ? "⚠️ Active Threat" : "✅ No Active Threats"}
        </span>
        <span className="threat-summary-subtext">
          {hasThreat
            ? allAlerts[0].message
            : `All zones nominal. Monitoring ${cameras.length} camera${
                cameras.length === 1 ? "" : "s"
              }.`}
        </span>
      </div>

      

      <TuningPanel baseUrl={workerUrl} notify={showMessage} />

      <h3 className="camera-grid-heading">Camera Feeds ({cameras.length})</h3>
      {renderGrid()}
    </div>
  );
}

export default UnattendedObject;
