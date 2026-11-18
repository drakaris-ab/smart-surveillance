import React, { useState } from "react";
import CameraSetupTab from "./CameraSetupTab";
import CameraViewTab from "./CameraViewTab";
import { CameraProvider, useCamera } from "../../context/CameraContext";
import "../../styles/global.css";

function CameraCardContent() {
  const [activeTab, setActiveTab] = useState("setup");
  const { cameras } = useCamera();

  return (
    <div className="round-card card-container">
      {/* Modern Tab Header */}
      <div className="tab-buttons">
       <button
          onClick={() => setActiveTab("setup")}
          className={activeTab === "setup" ? "tab-button active" : "tab-button"}
        >
          ⚙️ Setup Cameras
        </button>
        <button
          onClick={() => setActiveTab("view")}
          className={activeTab === "view" ? "tab-button active" : "tab-button"}
        >
          👁️ View Cameras
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === "setup" && <CameraSetupTab />}
        {activeTab === "view" && <CameraViewTab cameras={cameras} />}
      </div>
    </div>
  );
}

function CameraCard() {
  return (
    <CameraProvider>
      <CameraCardContent />
    </CameraProvider>
  );
}

export default CameraCard;
