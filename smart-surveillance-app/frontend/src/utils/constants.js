// Camera statuses
export const CAMERA_STATUS = {
  IDLE: 'idle',
  CONNECTING: 'connecting',
  ONLINE: 'online',
  OFFLINE: 'offline',
  ERROR: 'error',
};

// Alert types
export const ALERT_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
};

// Default alert duration (ms)
export const ALERT_DURATION = 4000;

// App routes
export const ROUTES = {
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  CAMERAS: '/cameras',
  ARCHIVE: '/archive',
  ALERTS: '/alerts',
  ZONES: '/zones',
};

// API endpoints (relative to baseURL in apiClient.js)
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    SIGNUP: '/auth/signup',
  },
  CAMERAS: '/cameras',
  ARCHIVES: '/archives',
  ZONES: '/zones',
};

// UI constants
export const UI = {
  MAX_CAMERAS: 16, // maximum feeds in grid
  SNAPSHOT_FORMAT: 'image/png',
  THEME: {
    PRIMARY: '#00c6ff',
    SECONDARY: '#2c5364',
  },
};
