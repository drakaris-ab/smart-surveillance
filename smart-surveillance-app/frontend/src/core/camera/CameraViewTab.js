// src/components/CameraViewTab.js
import React, { useContext } from "react";
import { MessageContext } from "../../context/MessageContext";
import CameraFeed from "./CameraFeed";
import api from "../../services/api";

export default function CameraViewTab({ cameras = [] }) {
  const { showMessage } = useContext(MessageContext);

  if (!cameras.length) {
    return (
      <div className="no-cameras">No cameras available.</div>
    );
  }

  return (
    <div style={{ position: 'relative' }}>
      <div className="camera-grid-wrapper">
        {cameras.map((cam) => (
          <CameraFeed
            key={cam.id}
            cameraId={cam.id}
            name={cam.name}
            location={cam.location}
            // ✅ Directly call snapshot or stream endpoint
            streamUrl={`${api.defaults.baseURL}/cameras/${cam.id}/stream?mode=raw`}
            isConnected={true}   // always true since we’re not checking status
          />
        ))}
      </div>
    </div>
  );
}
