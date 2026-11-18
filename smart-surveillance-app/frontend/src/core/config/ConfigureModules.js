// src/core/ConfigureModules.js
import React, { useState } from "react";
import ConfigScreen from "./ConfigScreen";
import "../../styles/global.css";

function ConfigureModules() {
  const [activeTab, setActiveTab] = useState("modules");

  return (
    <div className="round-card">
      {/* Modern Tab Header */}
      <div className="tab-buttons">
        <button
          onClick={() => setActiveTab("modules")}
          className={activeTab === "modules" ? "tab-button active" : "tab-button"}
        >
          ⚙️ Module Access
        </button>
        <button
          onClick={() => setActiveTab("system")}
          className={activeTab === "system" ? "tab-button active" : "tab-button"}
        >
          🎛️ System Configuration
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === "modules" && (
          <div>
            <h2 style={{ color: "white", marginBottom: "20px", fontSize: "1.25rem" }}>
              ⚙️ Configure Modules
            </h2>
            <p style={{ color: "#d1d5db", fontStyle: "italic" }}>
              Module toggle functionality goes here.
            </p>
          </div>
        )}
        {activeTab === "system" && <ConfigScreen />}
      </div>
    </div>
  );
}

export default ConfigureModules;
