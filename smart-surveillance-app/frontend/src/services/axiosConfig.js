import axios from "axios";
import { getConfig } from "../config";

export function createApi() {
  const config = getConfig();

  const api = axios.create({
    baseURL: `${config.apiBaseUrl}:${config.port}`,
  });

  // Attach interceptor for auth token
  api.interceptors.request.use((reqConfig) => {
    const token = localStorage.getItem("token");
    if (token) {
      reqConfig.headers.Authorization = `Bearer ${token}`;
    }
    return reqConfig;
  });

  // Attach interceptor for handling 401 Unauthorized
  api.interceptors.response.use(
    (response) => response,
    async (error) => {
      if (error.response?.status === 401) {
        const refreshToken = localStorage.getItem("refreshToken");
        if (refreshToken) {
          try {
            // Call your backend refresh endpoint
            const res = await axios.post(
              `${config.apiBaseUrl}:${config.port}/auth/refresh`,
              { refresh_token: refreshToken }
            );

            // Save new token
            localStorage.setItem("token", res.data.access_token);

            // Retry original request with new token
            error.config.headers.Authorization = `Bearer ${res.data.access_token}`;
            return api.request(error.config);
          } catch (refreshErr) {
            console.error("Token refresh failed:", refreshErr);
            // Optionally force logout
            localStorage.removeItem("token");
            localStorage.removeItem("refreshToken");
            window.location.href = "/login";
          }
        }
      }
      return Promise.reject(error);
    }
  );

  return api;
}
