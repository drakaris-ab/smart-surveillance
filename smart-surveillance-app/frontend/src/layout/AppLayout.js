import React, { useState } from "react";
import { Outlet } from "react-router-dom";   // 👈 import Outlet
import Sidebar from "./Sidebar";
import Header from "./Topbar";
import WorkArea from "./WorkArea";
import "../styles/global.css";

function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="app-container">
      {/* Header always at top */}
      <Header
        collapsed={collapsed}
        toggleSidebar={() => setCollapsed(!collapsed)}
      />

      {/* Body: sidebar left + main content right */}
      <div className="app-body">
        <Sidebar collapsed={collapsed} />
        <div className="main-content">
          <WorkArea>
            {/* 👇 This is where nested routes like /dashboard will render */}
            <Outlet />
          </WorkArea>
        </div>
      </div>
    </div>
  );
}

export default AppLayout;
