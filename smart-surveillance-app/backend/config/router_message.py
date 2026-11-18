MESSAGES = {
    # ---------------------------
    # Activity Log
    # ---------------------------
    "ACTIVITY_LOG_FETCHED": "Activity logs fetched for user {user}, count={count}",
    "ACTIVITY_LOG_FETCH_FAILED": "Failed to fetch activity logs for user {user}",

    # ---------------------------
    # Alert Mute Schedule
    # ---------------------------
    "MUTE_FETCH_ALL": "Fetched all mute schedules, count={count}",
    "MUTE_FETCH_FAILED": "Failed to fetch mute schedules",
    "MUTE_NOT_FOUND": "Mute schedule with ID {id} not found",
    "MUTE_CREATED": "Mute schedule created (ID {id}) by {user}",
    "MUTE_CREATE_FAILED": "Failed to create mute schedule",
    "MUTE_UPDATED": "Mute schedule updated (ID {id}) by {user}",
    "MUTE_UPDATE_FAILED": "Failed to update mute schedule",
    "MUTE_DELETED": "Mute schedule deleted (ID {id}) by {user}",
    "MUTE_DELETE_FAILED": "Failed to delete mute schedule",

    # ---------------------------
    # Alerts
    # ---------------------------
    "model_import_failed": "Failed to import models: {error}",
    "alert_created": "Alert created for camera {camera_id}, zone {zone_id} by {user}",
    "alert_create_failed": "Failed to create alert: {error}",
    "alerts_fetched": "Fetched alerts successfully, count={count}",
    "alerts_fetch_failed": "Failed to fetch alerts: {error}",
    "timestamp_conversion_failed": "Timestamp conversion failed for alert {alert_id}: {error}",
    "alert_not_found": "Alert with ID {alert_id} not found",
    "alert_deleted": "Alert {alert_id} deleted by {user}",
    "alert_delete_failed": "Failed to delete alert {alert_id}: {error}",

    # ---------------------------
    # Archive
    # ---------------------------
    "snapshot_source_missing": "Snapshot source directory missing: {path}",
    "invalid_dates": "Invalid date range provided: {error}",
    "dest_create_failed": "Failed to create destination directory: {error}",
    "snapshot_archived": "Snapshot {file} archived successfully to {dest}",
    "snapshot_move_failed": "Failed to move snapshot {file}: {error}",
    "logs_fetch_failed": "Failed to fetch activity logs: {error}",
    "no_logs_found": "No logs found between {start} and {end}",
    "logs_archived": "Archived {count} logs to file {file}",
    "logs_archive_failed": "Failed to archive logs: {error}",
    "snapshot_stat_failed": "Failed to read file stats for {file}: {error}",
    "snapshots_today_listed": "Listed today's snapshots, count={count}",

    # ---------------------------
    # Auth
    # ---------------------------
    "TOKEN_CREATION_FAILED": "Failed to create token: {error}",
    "TOKEN_INVALID": "Invalid or expired token",
    "TOKEN_REFRESHED": "Access token refreshed for user {username}",
    "USER_EXISTS": "User {username} already exists",
    "USER_CREATED": "User {username} created successfully",
    "SIGNUP_FAILED": "Failed to sign up user: {error}",
    "LOGIN_FAIL": "Login failed for user {username}",
    "LOGIN_SUCCESS": "User {username} logged in successfully",
    "LOGIN_FAILED": "Failed to process login: {error}",
    "USER_NOT_FOUND": "User {username} not found",
    "USER_UPDATED": "User {id} updated successfully",
    "USER_DELETED": "User {id} deleted successfully",
    "DASHBOARD_ACCESS": "Dashboard accessed by user {username}",
    "OTP_SENT": "OTP sent successfully to user {username}",
    "OTP_SEND_FAILED": "Failed to send OTP to user {username}",
    "OTP_INVALID": "Invalid OTP for user {username}",
    "OTP_VERIFIED": "OTP verified successfully for user {username}",
    "MISSING_FIELDS": "Missing required fields",
    "PASSWORD_RESET": "Password reset successfully for user {username}",
    "PASSWORD_RESET_FAILED": "Failed to reset password: {error}",

    # ---------------------------
    # Camera Mapping
    # ---------------------------
    "CAMERA_ASSIGN_SUCCESS": "Camera assigned successfully",
    "CAMERA_ASSIGN_UPDATE_SUCCESS": "Camera assignment updated successfully",
    "CAMERA_ASSIGN_FAIL": "Failed to assign camera",
    "CAMERA_MAPPING_UPDATE_SUCCESS": "Camera mapping updated successfully",
    "CAMERA_MAPPING_UPDATE_FAIL": "Failed to update camera mapping",
    "CAMERA_MAPPING_DELETE_SUCCESS": "Camera mapping deleted successfully",
    "CAMERA_MAPPING_DELETE_FAIL": "Failed to delete camera mapping",
    "CAMERA_MAPPING_FETCH_SUCCESS": "Camera mapping fetched successfully",
    "CAMERA_MAPPING_FETCH_FAIL": "Failed to fetch camera mapping",
    "CAMERA_MAPPING_NOT_FOUND": "Camera mapping not found",

    # ---------------------------
    # Camera Stream
    # ---------------------------
    "CAMERA_STREAM_START": "Camera stream started",
    "CAMERA_STREAM_FAIL": "Camera stream failed",
    "CAMERA_STREAM_NO_FRAME": "No frame available from camera stream",
    "CAMERA_STREAM_ENCODING_FAIL": "Failed to encode camera stream frame",
    "CAMERA_STREAMING": "Camera streaming in progress",
    "CAMERA_STREAM_REQUEST": "Camera stream request received",
    "CAMERA_SNAPSHOT_REQUEST": "Camera snapshot request received",
    "CAMERA_SNAPSHOT_FAIL": "Camera snapshot failed",
    "CAMERA_SNAPSHOT_NO_FRAME": "No frame available for snapshot",
    "CAMERA_SNAPSHOT_ENCODING_FAIL": "Failed to encode snapshot frame",
    "CAMERA_SNAPSHOT_SUCCESS": "Camera snapshot captured successfully",

    # ---------------------------
    # Cameras
    # ---------------------------
    "CAMERA_FETCH_SUCCESS": "Cameras fetched successfully",
    "CAMERA_FETCH_FAIL": "Failed to fetch cameras: {error}",
    "CAMERA_ADD_SUCCESS": "Camera added successfully (ID {id})",
    "CAMERA_ADD_FAIL": "Failed to add camera: {error}",
    "CAMERA_UPDATE_SUCCESS": "Camera updated successfully (ID {id})",
    "CAMERA_UPDATE_FAIL": "Failed to update camera: {error}",
    "CAMERA_DELETE_SUCCESS": "Camera deleted successfully (ID {id}) by {user}",
    "CAMERA_DELETE_FAIL": "Failed to delete camera: {error}",
    #"CAMERA_NOT_FOUND": "Camera not found",
    "CAMERA_STREAM_STARTED": "Camera stream started (ID {id})",
    "CAMERA_STREAM_FAIL": "Failed to stream camera: {error}",
    "SNAPSHOT_SUCCESS": "Snapshot captured successfully (ID {id})",
    "SNAPSHOT_FAIL": "Failed to capture snapshot: {error}",
    "FRAME_ENCODING_FAIL": "Failed to encode frame",
    "FRAME_NOT_AVAILABLE": "No frame available",
    "CV2_NOT_INSTALLED": "OpenCV is not installed, streaming unavailable",
    "CAMERA_STOP_FAIL": "Failed to stop detection for camera {id}: {error}",

    # ---------------------------
    # Config
    # ---------------------------
    "CONFIG_FETCH_SUCCESS": "Configuration fetched successfully",
    "CONFIG_FETCH_FAIL": "Failed to fetch configuration: {error}",
    "CONFIG_UPDATE_SUCCESS": "Configuration updated successfully",
    "CONFIG_UPDATE_FAIL": "Failed to update configuration: {error}",
    "INVALID_FILE_TYPE": "Invalid file type: {filename}. Only audio files allowed",
    "SOUND_UPLOAD_SUCCESS": "Alert sound uploaded successfully to {path}",
    "SOUND_UPLOAD_FAIL": "Failed to upload alert sound: {error}",

    # ---------------------------
    # Detection
    # ---------------------------
    "DETECTOR_NOT_INITIALIZED": "Detector is not initialized",
    #"CAMERA_NOT_FOUND": "Camera with ID {id} not found",
    "CAMERA_STREAM_STARTED": "Camera stream started (ID {id})",
    "CAMERA_STREAM_FAIL": "Failed to stream camera: {error}",
    "FRAME_ENCODING_FAIL": "Failed to encode frame",
    "FRAME_NOT_AVAILABLE": "No frame available for camera {id}",
   
    "SNAPSHOT_FAIL": "Failed to capture snapshot: {error}",
    "CAMERA_STATUS_CHECK": "Camera status checked (ID {id}), connected={status}",
    "ALL_DETECTIONS_STOPPED": "All detections stopped successfully",
    "STOP_ALL_FAIL": "Failed to stop all detections: {error}",
    "CAMERA_STREAM_FAIL1": "Failed to stream camera: {error}",


    # ---------------------------
    # Modules
    # ---------------------------
    "MODULE_FETCH_SUCCESS": "Modules fetched successfully",
    "MODULE_FETCH_FAIL": "Failed to fetch modules: {error}",
    "MODULE_EXISTS": "Module already exists",
    "MODULE_ADD_SUCCESS": "Module added successfully (ID {id})",
    "MODULE_ADD_FAIL": "Failed to add module: {error}",
    "MODULE_NOT_FOUND": "Module not found",
    "MODULE_UPDATE_SUCCESS": "Module updated successfully (ID {id})",
    "MODULE_UPDATE_FAIL": "Failed to update module: {error}",
    "MODULE_DELETE_SUCCESS": "Module deleted successfully (ID {id}) by {user}",
    "MODULE_DELETE_FAIL": "Failed to delete module: {error}",

    # User Module Fetch
    "USER_MODULE_FETCH_SUCCESS": "User modules fetched successfully for user {user_id}",

    # Grant Module Access
    "MODULE_ID_REQUIRED": "Module ID required",
    "USER_MODULE_EXISTS": "User already has this module assigned",
    "USER_MODULE_ADD_SUCCESS": "Module {module_id} assigned to user {user_id} successfully",
    "USER_MODULE_ADD_FAIL": "Failed to assign module to user: {error}",

    # Revoke Module Access
    "USER_MODULE_NOT_FOUND": "User module not found",
    "USER_MODULE_DELETE_SUCCESS": "Module {module_id} revoked from user {user_id} successfully",
    "USER_MODULE_DELETE_FAIL": "Failed to revoke module from user: {error}",

    # Authorization
    "UNAUTHORIZED_ACCESS": "Not authorized to access these modules",

    # ---------------------------
    # Streams
    # ---------------------------
    "STREAM_INIT_FAIL": "Stream initialization failed (detector or OpenCV not available)",
    "FRAME_TIMEOUT": "Timeout waiting for frame from camera {id}",
    "FRAME_ENCODING_FAIL": "Failed to encode frame",
    "CAMERA_NOT_FOUND": "Camera not found",
    "STREAM_URL_NOT_CONFIGURED": "Camera stream URL not configured (ID {id})",
    "STREAM_START": "Starting stream for camera {id} -> {url}",
    "STREAM_SUCCESS": "Streaming started successfully for camera {id}",
    "STREAM_FAIL": "Failed to stream camera: {error}",

    # ---------------------------
    # Users
    # ---------------------------
    "USER_FETCH_SUCCESS": "Users fetched successfully",
    "USER_FETCH_FAIL": "Failed to fetch users: {error}",
    "USER_EXISTS": "User already exists",
    "USER_ADD_SUCCESS": "User added successfully (ID {id})",
    "USER_ADD_FAIL": "Failed to add user: {error}",
    "USER_NOT_FOUND": "User not found",
    "USER_UPDATE_SUCCESS": "User updated successfully (ID {id})",
    "USER_UPDATE_FAIL": "Failed to update user: {error}",
    "USER_DELETE_SUCCESS": "User deleted successfully (ID {id}) by {user}",
    "USER_DELETE_FAIL": "Failed to delete user: {error}",

    # ---------------------------
    # Zones
    # ---------------------------
    "ACTIVE_FEED_EMPTY": "No active feed available",
    "ACTIVE_FEED_SUCCESS": "Active feed fetched successfully for camera {camera_id}",
    "ACTIVE_FEED_FAIL": "Failed to fetch active feed: {error}",
    "TRACK_UNIDENTIFIED_SUCCESS": "Tracking unidentified objects initialized successfully",
    #"CAMERA_NOT_FOUND": "Camera not found",
    "CAMERA_STREAM_FAIL": "Failed to open camera stream ({url})",
    "FRAME_CAPTURE_FAIL": "Failed to capture frame from camera",
    "SNAPSHOT_SAVE_FAIL": "Failed to save captured snapshot",
    "SNAPSHOT_SUCCESS_ZONE": "Snapshot captured successfully at {path}",
    "SNAPSHOT_FAIL": "Failed to capture snapshot: {error}",
    "ZONE_FETCH_SUCCESS": "Zones fetched successfully",
    "ZONE_FETCH_FAIL": "Failed to fetch zones: {error}",
    "ZONE_ADD_SUCCESS": "Zone added successfully (ID {id})",
    "ZONE_ADD_FAIL": "Failed to add zone: {error}",
    "ZONE_UPDATE_SUCCESS": "Zone updated successfully (ID {id})",
    "ZONE_UPDATE_FAIL": "Failed to update zone: {error}",
    "ZONE_DELETE_SUCCESS": "Zone deleted successfully (ID {id}) by {user}",
    "ZONE_DELETE_FAIL": "Failed to delete zone: {error}",
    "ZONE_NOT_FOUND": "Zone not found",

    # --- User lifecycle ---
    "USER_EXISTS": "User already exists: {username}",
    "USER_CREATED": "User created successfully: {username}",
    "USER_UPDATED": "User updated successfully with ID: {id}",
    "USER_DELETED": "User deleted successfully with ID: {id}",
    "USER_NOT_FOUND": "User not found: {username}",

    # --- Authentication ---
    "LOGIN_SUCCESS": "Login successful for user: {username}",
    "LOGIN_FAIL": "Login failed for user: {username}",
    "LOGIN_FAILED": "Login process failed due to server error: {error}",
    "SIGNUP_FAILED": "Signup process failed due to server error: {error}",

    # --- Tokens ---
    "ACCESS_TOKEN_CREATED": "Access token created for subject: {subject}",
    "REFRESH_TOKEN_CREATED": "Refresh token created for subject: {subject}",
    "TOKEN_INVALID": "Invalid or expired token",
    "TOKEN_REFRESHED": "Access token refreshed for user: {username}",
    "TOKEN_REFRESH_FAILED": "Token refresh failed due to server error: {error}",
    "TOKEN_CREATION_FAILED": "Token creation failed due to server error: {error}",
    "TOKEN_DECODE_FAILED": "Token decode failed due to server error: {error}",

    # --- Roles ---
    "ROLE_FORBIDDEN": "Access denied. User does not have the required role.",

    # --- Dashboard ---
    "DASHBOARD_ACCESS": "Dashboard accessed by user: {username}",

    # --- Password reset / OTP ---
    "OTP_SENT": "Password reset OTP sent to user: {username}",
    "OTP_SEND_FAILED": "Failed to send OTP for user: {username}",
    "OTP_INVALID": "Invalid OTP provided for user: {username}",
    "OTP_VERIFIED": "OTP verified successfully for user: {username}",
    "PASSWORD_RESET": "Password reset successfully for user: {username}",
    "PASSWORD_RESET_FAILED": "Password reset failed due to server error: {error}",

    # --- Validation ---
    "MISSING_FIELDS": "Required fields are missing in request payload.",
    "PASSWORD_HASH_FAILED": "Password hashing failed due to error: {error}",
    "PASSWORD_VERIFY_FAILED": "Password verification failed due to error: {error}",


}