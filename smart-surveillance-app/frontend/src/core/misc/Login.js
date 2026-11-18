import React, { useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../services/api";
import { MessageContext } from "../../context/MessageContext";
import messages from "../../constants/messages";
import "../../styles/global.css";

function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const { showMessage } = useContext(MessageContext);
  const navigate = useNavigate();

  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) {
      showMessage("error", messages.MANDATORY_USER_PASS);
      return;
    }

    try {
      const res = await api.post("/auth/login", { username, password });

      const accessToken = res.data.access_token;
      const refreshToken = res.data.refresh_token;
      const userId = res.data.id;

      if (res.status === 200 && accessToken && refreshToken) {
        // ✅ Store tokens and user info
        localStorage.setItem("access_token", accessToken);
        localStorage.setItem("refresh_token", refreshToken);
        localStorage.setItem("username", username);
        localStorage.setItem("userId", userId);

        showMessage("success", messages.LOGIN_SUCCESS);

        // Call parent onLogin if provided
        if (onLogin) onLogin();

        // Redirect to dashboard
        navigate("/dashboard");
      } else {
        showMessage("error", messages.LOGIN_FAILED);
      }
    } catch (err) {
      console.error("Login error:", err);
      showMessage("error", messages.LOGIN_FAILED);
    }
  };

  return (
    <div className="login-container">
      {/* Left side: Login form */}
      <div className="login-form-section">
        <div className="login-card">
          <h2 className="login-title">Smart Surveillance Login</h2>
          <input
            className="input-field"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <input
            className="input-field"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button className="primary-btn" onClick={handleLogin}>
            Login
          </button>
        </div>
      </div>

      {/* Right side: Big logo */}
      <div className="login-logo-section">
        <img
          src="/logo.png"   // place logo in public folder
          alt="AI CCTV Surveillance Logo"
          className="login-logo-img"
        />
        <h1 className="login-logo-text">AI CCTV Surveillance</h1>
      </div>
    </div>
  );
}

export default Login;
