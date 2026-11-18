let CONFIG = {};

export async function loadConfig() {
  const response = await fetch('/config.json');
  CONFIG = await response.json();
  return CONFIG;
}

export function getConfig() {
  if (!CONFIG || Object.keys(CONFIG).length === 0) {
    return {
      apiBaseUrl: process.env.REACT_APP_API_URL || "http://localhost",
      port: process.env.REACT_APP_API_PORT || "8000",
      faceRecognitionBaseUrl: process.env.FACE_RECOGNITION_BASE_URL || "http://localhost:8001",
      unattendedObjectUrl: process.env.UNWANTED_OBJECT_BASE_URL || "http://localhost:8002"
    };
  }
  return CONFIG;
}


