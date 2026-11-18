import React, { createContext, useState, useEffect, useCallback } from "react";

// 1. Create Context
export const AuthContext = createContext();

// 2. Provider Component
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load user from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem("access_token");   // ✅ consistent key
    const username = localStorage.getItem("username");
    const userId = localStorage.getItem("userId");

    if (token) {
      setUser({ token, username, userId });
    }
    setLoading(false);
  }, []);

  // Login function
  const login = useCallback((username, token, userId) => {
    const userData = { username, token, userId };
    setUser(userData);

    // ✅ store consistently
    localStorage.setItem("access_token", token);
    localStorage.setItem("username", username);
    localStorage.setItem("userId", userId);
  }, []);

  // Logout function
  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("userId");
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
