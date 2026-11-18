import axios from "axios";
import { getConfig } from "../config";

// ---------------------------
// Base URLs for different nodes
// ---------------------------
const MAIN_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";
const FACE_RECOGNITION_BASE_URL = process.env.REACT_APP_FACE_API_URL || "http://localhost:8001";
const UNWANTED_OBJECT_BASE_URL = process.env.UNWANTED_OBJECT_BASE_URL || "http://localhost:8002";

// ---------------------------
// Main backend instance
// ---------------------------
const api = axios.create({
  baseURL: MAIN_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ---------------------------
// Face Recognition node instance
// ---------------------------
export const faceApi = axios.create({
  baseURL: FACE_RECOGNITION_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ---------------------------
// unwantedObject node instance
// ---------------------------
export const UnwantedobjectApi = axios.create({
  baseURL: UNWANTED_OBJECT_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ✅ Dynamically inject baseURL for main API based on getConfig
api.interceptors.request.use((config) => {
  const dynamicConfig = getConfig();
  if (dynamicConfig && dynamicConfig.apiBaseUrl && dynamicConfig.port) {
    config.baseURL = `${dynamicConfig.apiBaseUrl}:${dynamicConfig.port}`;
  }
  return config;
});

// ✅ Automatically attach JWT token if present
const attachToken = (config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

api.interceptors.request.use(attachToken, (error) => Promise.reject(error));
faceApi.interceptors.request.use(attachToken, (error) => Promise.reject(error));

// ✅ Response interceptor: refresh token on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");

      if (refreshToken) {
        try {
          const res = await axios.post(`${MAIN_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const newAccessToken = res.data.access_token;
          localStorage.setItem("access_token", newAccessToken);

          // Update headers and retry the original request
          api.defaults.headers.common["Authorization"] = `Bearer ${newAccessToken}`;
          originalRequest.headers["Authorization"] = `Bearer ${newAccessToken}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed → force logout
          localStorage.clear();
          window.location.href = "/login";
        }
      }
    }

    return Promise.reject(error);
  }
);

// ✅ Utility to set/remove tokens manually
export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    faceApi.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
    delete faceApi.defaults.headers.common["Authorization"];
  }
};

export default api;
