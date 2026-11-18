const messages = {
  // ---------------------------
  // Auth
  // ---------------------------
  LOGIN_SUCCESS: "Login successful",
  LOGIN_FAILED: "Login failed",
  MANDATORY_USER_PASS: "Username and Password are required",

  // ---------------------------
  // User Management
  // ---------------------------
  USER_CREATED: "User created successfully",
  USER_CREATION_FAILED: "Failed to create user",
  USER_ADD_SUCCESS: "User added successfully",
  USER_ADD_FAIL: "Failed to add user",
  USER_UPDATE_SUCCESS: "User updated successfully",
  USER_UPDATE_FAIL: "Failed to update user",
  USER_DELETE_SUCCESS: "User deleted successfully",
  USER_DELETE_FAIL: "Failed to delete user",
  USER_EXISTS: "User already exists",
  USER_NOT_FOUND: "User not found",
  USER_FETCH_SUCCESS: "Users fetched successfully",
  USER_FETCH_FAIL: "Failed to fetch users",
  USER_DELETE_CONFIRM: "Are you sure you want to delete this user?",
  MANDATORY_USER_FIELDS: "Username, password and role are required",

  // ---------------------------
  // Camera Management
  // ---------------------------
  CAMERA_DASHBOARD_TITLE: "Camera Dashboard",
  CAMERA_ADD_SUCCESS: "Camera added successfully",
  CAMERA_ADD_FAIL: "Failed to add camera",
  CAMERA_UPDATE_SUCCESS: "Camera updated successfully",
  CAMERA_UPDATE_FAIL: "Failed to update camera",
  CAMERA_DELETE_SUCCESS: "Camera deleted successfully",
  CAMERA_DELETE_FAIL: "Failed to delete camera",
  CAMERA_DELETE_CONFIRM: "Are you sure you want to delete this camera?",
  CAMERA_FETCH_SUCCESS: "Cameras fetched successfully",
  CAMERA_FETCH_FAIL: "Failed to fetch cameras",
  CAMERA_NOT_FOUND: "Camera not found",
  MANDATORY_CAMERA_FIELDS: "Camera name, RTSP URL, and location are required",

  // ---------------------------
  // Zone Management
  // ---------------------------
  ZONE_DASHBOARD_TITLE: "Zone Dashboard",
  ZONE_ADD_SUCCESS: "Zone added successfully",
  ZONE_ADD_FAIL: "Failed to add zone",
  ZONE_UPDATE_SUCCESS: "Zone updated successfully",
  ZONE_UPDATE_FAIL: "Failed to update zone",
  ZONE_DELETE_SUCCESS: "Zone deleted successfully",
  ZONE_DELETE_FAIL: "Failed to delete zone",
  ZONE_DELETE_CONFIRM: "Are you sure you want to delete this zone?",
  ZONE_FETCH_SUCCESS: "Zones fetched successfully",
  ZONE_FETCH_FAIL: "Failed to fetch zones",
  ZONE_NOT_FOUND: "Zone not found",

  // Zone Validation
  MANDATORY_ZONE_FIELDS: "Camera, polygon coordinates and snapshot are required",
  MANDATORY_CAMERA_SELECT: "Please select a camera",

  // Zone Dashboard / UI
  SELECT_CAMERA: "Select Camera",
  ZONE_COORDS_PLACEHOLDER: "Polygon Coordinates",
  CAPTURE_SNAPSHOT: "Capture Snapshot",
  SNAPSHOT_ALT: "Snapshot",
  ZONE_ADD_BTN: "+ Add Zone",
  TABLE_CAMERA: "Camera",
  TABLE_COORDS: "Polygon Coordinates",
  TABLE_SNAPSHOT: "Snapshot",
  TABLE_ACTIONS: "Actions",
  SAVE_BTN: "Save",
  CANCEL_BTN: "Cancel",
  YES_BTN: "Yes",
  NO_BTN: "No",
  UPDATE_ZONE_TITLE: "Update Zone",
  DELETE_ZONE_TITLE: "Delete Zone",
  NO_SNAPSHOT: "No snapshot",

  // Snapshot
  SNAPSHOT_CAPTURE_SUCCESS: "Snapshot captured successfully",
  SNAPSHOT_CAPTURE_FAIL: "Failed to capture snapshot",

  // ---------------------------
  // Alerts
  // ---------------------------
  ALERT_TRIGGERED: "Alert triggered",
  ALERT_FAILED: "Failed to trigger alert",

  // ---------------------------
  // General
  // ---------------------------
  ACTION_CANCELLED: "Action cancelled",
   // Modules
  MODULE_FETCH_SUCCESS: "Modules fetched successfully",
  MODULE_FETCH_FAIL: "Failed to fetch modules",
  MODULE_ADD_SUCCESS: "Module added successfully",
  MODULE_ADD_FAIL: "Failed to add module",
  MODULE_UPDATE_SUCCESS: "Module updated successfully",
  MODULE_UPDATE_FAIL: "Failed to update module",
  MODULE_DELETE_SUCCESS: "Module deleted successfully",
  MODULE_DELETE_FAIL: "Failed to delete module",
  MODULE_EXISTS: "Module already exists",
  MODULE_NOT_FOUND: "Module not found",

  // Module Access
  MODULE_ACCESS_GRANTED: "Module access granted successfully",
  MODULE_ACCESS_REVOKED: "Module access revoked successfully",
  MODULE_ACCESS_FAIL: "Failed to update module access",

  // User Modules
  USER_MODULE_FETCH_SUCCESS: "User modules fetched successfully",
  USER_MODULE_FETCH_FAIL: "Failed to fetch user modules",
  USER_MODULE_ADD_SUCCESS: "Module access granted successfully",
  USER_MODULE_ADD_FAIL: "Failed to grant module access",
  USER_MODULE_DELETE_SUCCESS: "Module access revoked successfully",
  USER_MODULE_DELETE_FAIL: "Failed to revoke module access",
  USER_MODULE_EXISTS: "User already has this module assigned",
  USER_MODULE_NOT_FOUND: "Module access not found for this user",
  // ---------------------------
  // Recognition / Visitors
  // ---------------------------
  RECOGNITION_STARTED: "Live recognition started...",
  RECOGNITION_ENDED: "Live recognition ended",
  RECOGNITION_TIMEOUT: "No match found after 20 attempts",
  VISITOR_RECOGNIZED: "Visitor recognized successfully",
  VISITOR_UNRECOGNIZED: "Unrecognized face. Please register",
  NO_MATCH_FOUND: "No match found",
  REGISTERING_VISITOR: "Registering visitor...",
  VISITOR_REGISTER_SUCCESS: "Visitor registered successfully",
  VISITOR_REGISTER_FAIL: "Visitor registration failed",
  VERIFYING_VISITOR: "Verifying visitor...",
  VISITOR_VERIFY_SUCCESS: "Visitor verified successfully",
  VISITOR_VERIFY_FAIL: "Visitor verification failed",
  SNAPSHOT_SAVED: "Snapshot captured successfully",
  SNAPSHOT_FAIL: "Failed to capture snapshot",
  WS_ERROR: "WebSocket error occurred",

  VISITOR_FETCH_SUCCESS: "Visitors loaded successfully",
  VISITOR_FETCH_FAIL: "Failed to load visitors",
  VISITOR_ACCESS_UPDATED: "Visitor access updated successfully",
  VISITOR_ACCESS_FAIL: "Failed to update visitor access",
  MANDATORY_VISITOR_FIELDS: "Visitor name, ID or phone is required",
  VISITOR_NOT_FOUND: "Visitor not found",

  ZONE_FETCH_SUCCESS: "Zone feed loaded successfully",
  ZONE_FETCH_FAIL: "Failed to load zone feed",
  ALERT_TRIGGERED: "Alert triggered",
  ALERT_FAILED: "Failed to fetch alerts",

};

export default messages;
