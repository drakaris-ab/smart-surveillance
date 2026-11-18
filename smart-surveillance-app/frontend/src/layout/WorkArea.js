// src/layout/WorkArea.js
import React from "react";
import { Outlet, useLocation } from "react-router-dom";
import "../styles/global.css";

function WorkArea() {
  const location = useLocation();

  const sectionLabels = {
    "/dashboard": "Dashboard",
    "/cameras": "Camera Management",
    "/zones": "Zones",
    "/alerts": "Alerts",
    "/users": "User Management",
    "/module-access": "User Module Access",
    "/face-recognition":"Face Recognition",
    "/unidentified-object":"Unidentified Object Tracking"

  };

  const currentLabel = sectionLabels[location.pathname] || "Dashboard";

  return (
    <main className="work-area">
      <div className="work-bar">{currentLabel}</div>
      <Outlet />
    </main>
  );
}

export default WorkArea;
