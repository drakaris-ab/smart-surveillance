// src/layout/Header.js
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/global.css";

function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [username, setUsername] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const storedUser = localStorage.getItem("username");
    if (storedUser) setUsername(storedUser);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("username");
    localStorage.removeItem("userId");
    sessionStorage.clear();
    navigate("/login");
  };

  return (
    <header className="app-header">
      {/* Left Section: Logo + Styled Title */}
      <div className="left-section">
        <div className="logo-section">
          <img
            src="/logo3.png"
            alt="AI CCTV Surveillance Logo"
            className="logo-img"
          />
             {/* Bottom Title */}
      
        <h1 className="app-title">
          <span className="big-letter">S</span>mart CCTV System
        </h1>
      
        </div>
      </div>

      {/* Right Section: User Menu */}
      <div className="user-menu">
        <div
          className="user-avatar"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          <div className="avatar-circle">
            {username ? username.charAt(0).toUpperCase() : "U"}
          </div>
          <span className="username">{username || "User"}</span>
        </div>

        {menuOpen && (
          <div className="dropdown-menu">
            <button onClick={() => navigate("/profile")}>Profile</button>
            <button onClick={handleLogout}>Logout</button>
          </div>
        )}
      </div>
    </header>
  );
}

export default Header;
