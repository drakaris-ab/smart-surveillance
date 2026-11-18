// src/core/FaceRecognition.js
import React, { useState, useContext } from "react";
import FaceRecognitionConfigure from "../FaceRecognition/FaceRecognitionConfigure";
import FaceRecognitionMonitor from "../FaceRecognition/FaceRecognitionMonitor";
import VisitorTracking from "../FaceRecognition/VisitorTracking";
import { MessageContext } from "../../context/MessageContext";
import messages from "../../constants/messages";
import "../../styles/global.css";

function FaceRecognition() {
  const [activeTab, setActiveTab] = useState("configure");
  const [selectedCamera, setSelectedCamera] = useState(null);
  const { showMessage } = useContext(MessageContext);

  const handleAlert = (type, key) => {
    showMessage(type, messages[key]);
  };

  return (
    <div className="round-card full-screen">
           {/* Tab Navigation */}
      <div className="tab-buttons blue-theme">
        <button
          onClick={() => setActiveTab("configure")}
          className={activeTab === "configure" ? "tab-button active" : "tab-button"}
        >
          Configure
        </button>
        <button
          onClick={() => setActiveTab("monitor")}
          className={activeTab === "monitor" ? "tab-button active" : "tab-button"}
        >
          Monitor
        </button>
        <button
          onClick={() => setActiveTab("tracking")}
          className={activeTab === "tracking" ? "tab-button active" : "tab-button"}
        >
          Visitor Tracking
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === "configure" && (
          <FaceRecognitionConfigure
            setAlert={handleAlert}
            selectedCamera={selectedCamera}
            setSelectedCamera={setSelectedCamera}
          />
        )}

        {activeTab === "monitor" && (
          <FaceRecognitionMonitor
            setAlert={handleAlert}
            selectedCamera={selectedCamera}
          />
        )}
        {activeTab === "tracking" && (
          <VisitorTracking setAlert={handleAlert} />
        )}
      </div>
    </div>
  );
}

export default FaceRecognition;
