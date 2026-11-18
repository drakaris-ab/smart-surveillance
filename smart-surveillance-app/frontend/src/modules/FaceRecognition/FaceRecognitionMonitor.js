// src/FaceRecognition/FaceRecognitionMonitor.js
import React, { useEffect, useState, useContext } from "react";
import "../../styles/global.css";
import FaceRecognitionDashboard from "./FaceRecognitionDashboard";
import { MessageContext } from "../../context/MessageContext";

function FaceRecognitionMonitor({ selectedCamera }) {
  const [alerts, setAlerts] = useState({});
  const { showMessage } = useContext(MessageContext);

 

  return (
    <div style={{ position: "relative" }}>
      <FaceRecognitionDashboard selectedCamera={selectedCamera} alerts={alerts} />
    </div>
  );
}

export default FaceRecognitionMonitor;
