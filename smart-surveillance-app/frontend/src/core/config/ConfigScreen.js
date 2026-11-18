import React, { useState, useEffect, useContext } from "react";
import { ApiContext } from "../../context/ApiContext";
import useAlertService from "../../services/alertService";
import "../../styles/global.css";

function ConfigScreen() {
  const api = useContext(ApiContext);
  const alertService = useAlertService();

  const [configs, setConfigs] = useState([]);
  const [editingId, setEditingId] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get("/config/all");
        setConfigs(res.data);
      } catch (err) {
        alertService.error("Failed to load configuration");
      }
    })();
  }, [api]);

  const saveConfig = async (id, cfg) => {
    try {
      await api.put(`/config/update/${cfg.key}`, null, {
        params: { value: cfg.value, updated_by: "frontend" }
      });
      alertService.success(`${cfg.description} updated successfully`);
      setEditingId(null);
    } catch (err) {
      alertService.error("Failed to update configuration");
    }
  };

  const handleFileUpload = async (e, cfg) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      await api.post("/config/upload-sound", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      alertService.success("Sound file uploaded successfully");
      
      // Update local state to reflect change
      setConfigs(configs.map((c) =>
        c.key === cfg.key ? { ...c, value: `assets/sounds/${file.name}` } : c
      ));
    } catch (err) {
      alertService.error("Failed to upload sound file");
    }
  };

  const renderInput = (c, currentConfigs, setConfigsFn) => {
    const handleChange = (val) => {
      setConfigsFn(currentConfigs.map(cfg => cfg.id === c.id ? { ...cfg, value: val } : cfg));
    };

    const desc = (c.description || "").toLowerCase();

    // Booleans / Switches
    if (
      desc.includes("flag to start background") ||
      desc.includes("enable or disable") ||
      c.key === "startLiveTracking" || c.key === "enableLiveDetection" || c.key === "enableCameraDetection" || c.key === "enableFaceDetection" ||
      c.key === "live_tracking_enabled" || c.key === "is_Camera_Detector" || c.key === "live_Face_tracking_enabled" || c.key === "detectionEnabled"
    ) {
      return (
        <select
          className="input-field"
          value={String(c.value).toLowerCase()}
          onChange={(e) => handleChange(e.target.value)}
        >
          <option value="true">True</option>
          <option value="false">False</option>
        </select>
      );
    }

    // Alert Target
    if (desc.includes("where the alert is played") || c.key === "alertPlayTarget" || c.key === "alertOutputMode") {
      return (
        <select
          className="input-field"
          value={c.value}
          onChange={(e) => handleChange(e.target.value)}
        >
          <option value="system">System</option>
          <option value="external">External Hooter</option>
          <option value="both">Both</option>
        </select>
      );
    }

    // File Upload
    if (desc.includes("file path to the alert sound") || c.key === "alertSoundPath") {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <input
            className="input-field"
            type="text"
            value={c.value}
            onChange={(e) => handleChange(e.target.value)}
          />
          <input
            type="file"
            accept=".wav,.mp3,.ogg"
            onChange={(e) => handleFileUpload(e, c)}
          />
        </div>
      );
    }

    // Number Inputs
    if (
      desc.includes("duration") ||
      desc.includes("days to retain") ||
      desc.includes("confidence score") ||
      desc.includes("frame size") ||
      desc.includes("image size") ||
      desc.includes("focal length") ||
      desc.includes("number of snapshots") ||
      ["archiveRetentionDays", "archiveDays", "confidenceThreshold", "frameSize", "imageSize", "focalLength", "inferenceSize", "snapshotCount", "alertDurationSeconds"].includes(c.key)
    ) {
      const isFloat = desc.includes("confidence score") || desc.includes("focal length") || c.key === "confidenceThreshold" || c.key === "focalLength";
      return (
        <input
          className="input-field"
          type="number"
          step={isFloat ? "0.1" : "1"}
          value={c.value}
          onChange={(e) => handleChange(e.target.value)}
        />
      );
    }

    return (
      <input
        className="input-field"
        value={c.value}
        onChange={(e) => handleChange(e.target.value)}
      />
    );
  };

  return (
    <div className="table-container">
      <table className="camera-table bordered">
        <thead>
          <tr>
            <th>DESCRIPTION</th>
            <th>VALUE</th>
            <th>ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          {Array.isArray(configs) &&
            configs
              .filter(c => {
                const d = (c.description || "").toLowerCase();
                const k = (c.key || "").toLowerCase();
                return !(d.includes("whatsapp") || d.includes("sms") || k.includes("whatsapp") || k.includes("sms"));
              })
              .map((c, index) => (
              <tr key={c.id} className={index % 2 === 0 ? "row-even" : "row-odd"}>
                <td>{c.description}</td>
                <td>
                  {renderInput(c, configs, setConfigs)}
                </td>
                <td>
                  <div className="edit-actions">
                    <button className="primary-btn success-btn" onClick={() => saveConfig(c.id, c)}>Save</button>
                  </div>
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

export default ConfigScreen;
