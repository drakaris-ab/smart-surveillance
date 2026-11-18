MESSAGES = {
    # ---------------------------
    # Authentication & Session
    # ---------------------------
    "USER_CREATED": "User created successfully",
    "USER_EXISTS": "Username already exists",
    "LOGIN_SUCCESS": "Login successful",
    "LOGIN_FAIL": "Invalid username or password",
    "LOGOUT_SUCCESS": "Logout successful",
    "TOKEN_REFRESHED": "Token refreshed successfully",
    "TOKEN_EXPIRED": "Token expired or invalid",
    "TOKEN_INVALID": "Invalid Token",
    "PROFILE_FETCH_SUCCESS": "Profile fetched successfully",

    # ---------------------------
    # Authorization & Roles
    # ---------------------------
    "ACCESS_DENIED": "Access denied",
    "ROLE_FORBIDDEN": "You don't have the correct role",

    # ---------------------------
    # User CRUD Operations
    # ---------------------------
    "USER_FETCH_SUCCESS": "Users fetched successfully",
    "USER_FETCH_FAIL": "Failed to fetch users",
    "USER_ADD_SUCCESS": "User created successfully",
    "USER_ADD_FAIL": "Failed to create user",
    "USER_UPDATE_SUCCESS": "User updated successfully",
    "USER_UPDATE_FAIL": "Failed to update user",
    "USER_DELETE_SUCCESS": "User deleted successfully",
    "USER_DELETE_FAIL": "Failed to delete user",
    "USER_NOT_FOUND": "User not found",

    # ---------------------------
    # Server & System
    # ---------------------------
    "SERVER_ERROR": "Internal server error",

    # ---------------------------
    # Camera CRUD
    # ---------------------------
    "CAMERA_FETCH_SUCCESS": "Cameras fetched successfully",
    "CAMERA_FETCH_FAIL": "Failed to fetch cameras",
    "CAMERA_ADD_SUCCESS": "Camera added successfully",
    "CAMERA_ADD_FAIL": "Failed to add camera",
    "CAMERA_UPDATE_SUCCESS": "Camera updated successfully",
    "CAMERA_UPDATE_FAIL": "Failed to update camera",
    "CAMERA_DELETE_SUCCESS": "Camera deleted successfully",
    "CAMERA_DELETE_FAIL": "Failed to delete camera",
    "CAMERA_NOT_FOUNDbhhh": "Camera not found",
    "CAMERA_DELETE_CONFIRM": "Are you sure you want to delete this camera?",
    "MANDATORY_CAMERA_FIELDS": "Camera name, RTSP URL, and location are required",

    # ---------------------------
    # Zone CRUD
    # ---------------------------
    "ZONE_FETCH_SUCCESS": "Zones fetched successfully",
    "ZONE_FETCH_FAIL": "Failed to fetch zones",
    "ZONE_ADD_SUCCESS": "Zone added successfully",
    "ZONE_ADD_FAIL": "Failed to add zone",
    "ZONE_UPDATE_SUCCESS": "Zone updated successfully",
    "ZONE_UPDATE_FAIL": "Failed to update zone",
    "ZONE_DELETE_SUCCESS": "Zone deleted successfully",
    "ZONE_DELETE_FAIL": "Failed to delete zone",
    "ZONE_NOT_FOUND": "Zone not found",
    "ZONE_DELETE_CONFIRM": "Are you sure you want to delete this zone?",
    "MANDATORY_ZONE_FIELDS": "Camera, snapshot and coordinates are required",

    # ---------------------------
    # Modules
    # ---------------------------
    "MODULE_FETCH_SUCCESS": "Modules fetched successfully",
    "MODULE_FETCH_FAIL": "Failed to fetch modules",
    "MODULE_ADD_SUCCESS": "Module added successfully",
    "MODULE_ADD_FAIL": "Failed to add module",
    "MODULE_UPDATE_SUCCESS": "Module updated successfully",
    "MODULE_UPDATE_FAIL": "Failed to update module",
    "MODULE_DELETE_SUCCESS": "Module deleted successfully",
    "MODULE_DELETE_FAIL": "Failed to delete module",
    "MODULE_NOT_FOUND": "Module not found",
    "MODULE_EXISTS": "Module already exists",

    # ---------------------------
    # User Modules
    # ---------------------------
    "USER_MODULE_FETCH_SUCCESS": "User modules fetched successfully",
    "USER_MODULE_FETCH_FAIL": "Failed to fetch user modules",
    "USER_MODULE_ADD_SUCCESS": "Module access granted successfully",
    "USER_MODULE_ADD_FAIL": "Failed to grant module access",
    "USER_MODULE_DELETE_SUCCESS": "Module access revoked successfully",
    "USER_MODULE_DELETE_FAIL": "Failed to revoke module access",
    "USER_MODULE_EXISTS": "User already has this module assigned",
    "USER_MODULE_NOT_FOUND": "Module access not found for this user",

    # ---------------------------
    # Face Recognition & Visitors
    # ---------------------------
    "FACE_MATCH_SUCCESS": "Face match operation completed successfully",
    "FACE_MATCH_FAIL": "Face match operation failed",
    "FACE_NO_DETECT": "No face detected in frame",
    "FACE_UNRECOGNIZED_SAVED": "Unrecognized face saved for future identification",
    "VISITOR_NOT_FOUND": "Visitor not found",
    "VISITOR_REGISTER_SUCCESS": "Visitor registered successfully",
    "VISITOR_REGISTER_FAIL": "Visitor registration failed",
    "VISITOR_VERIFY_SUCCESS": "Visitor verification successful",
    "VISITOR_VERIFY_FAIL": "Visitor verification failed",

    # ---------------------------
    # Camera Assignments & Mapping
    # ---------------------------
    "CAMERA_ASSIGN_SUCCESS": "Camera assigned successfully to user",
    "CAMERA_ASSIGN_UPDATE_SUCCESS": "Camera assignment updated successfully",
    "CAMERA_ASSIGN_FAIL": "Failed to assign camera to user",
    "CAMERA_MAPPING_NOT_FOUND": "Camera mapping not found",
    "CAMERA_MAPPING_UPDATE_SUCCESS": "Camera mapping updated successfully",
    "CAMERA_MAPPING_UPDATE_FAIL": "Failed to update camera mapping",
    "CAMERA_MAPPING_DELETE_SUCCESS": "Camera mapping deleted successfully",
    "CAMERA_MAPPING_DELETE_FAIL": "Failed to delete camera mapping",
    "CAMERA_MAPPING_FETCH_SUCCESS": "User camera fetched successfully",
    "CAMERA_MAPPING_FETCH_FAIL": "Failed to fetch user camera",

    # ---------------------------
    # Camera Streaming & Snapshots
    # ---------------------------
    "CAMERA_STREAM_START": "Camera stream starting",
    "CAMERA_STREAM_FAIL": "Camera stream failed",
    "CAMERA_STREAM_NO_FRAME": "No frame read from camera",
    "CAMERA_STREAM_ENCODING_FAIL": "Frame encoding failed",
    "CAMERA_STREAMING": "Camera streaming in progress",
    "CAMERA_STREAM_REQUEST": "Camera stream request received",
    "CAMERA_SNAPSHOT_REQUEST": "Snapshot request received",
    "CAMERA_SNAPSHOT_FAIL": "Snapshot failed",
    "CAMERA_SNAPSHOT_NO_FRAME": "No frame available for snapshot",
    "CAMERA_SNAPSHOT_ENCODING_FAIL": "Snapshot encoding failed",
    "CAMERA_SNAPSHOT_SUCCESS": "Snapshot captured successfully",

    # ---------------------------
    # Archive Service
    # ---------------------------
    "ARCHIVE_INIT": "Archive directory initialized at {dir}",
    "ARCHIVE_INIT_FAILED": "Failed to initialize archive directory",
    "ARCHIVE_SNAPSHOT": "Snapshot archived for camera {camera}",
    "ARCHIVE_SNAPSHOT_FAILED": "Failed to archive snapshot for camera {camera}",
    "ARCHIVE_LIST": "Retrieved {count} archives",
    "ARCHIVE_LIST_FAILED": "Failed to list archives",
    "ARCHIVE_DELETE": "Deleted archive {id}",
    "ARCHIVE_NOT_FOUND": "Archive {id} not found",
    "ARCHIVE_DELETE_FAILED": "Failed to delete archive {id}",
    "ARCHIVE_DELETE_FILE_FAILED": "Failed to delete archive file {path}",
    "ARCHIVE_CLEANUP": "Cleaned {count} old archives",
    "ARCHIVE_CLEANUP_FAILED": "Failed to cleanup old archives",

    # ---------------------------
    # Camera Service
    # ---------------------------
    "CAMERA_SERVICE_INIT": "Camera service initialized",
    "CAMERA_REGISTER": "Camera {name} registered",
    "CAMERA_REGISTER_FAILED": "Failed to register camera {name}",
    "CAMERA_LIST": "Retrieved {count} cameras",
    "CAMERA_LIST_FAILED": "Failed to list cameras",
    "CAMERA_FETCH": "Fetched camera {id}",
    "CAMERA_FETCH_FAILED": "Failed to fetch camera {id}",
    "CAMERA_UPDATE": "Camera {id} updated",
    "CAMERA_UPDATE_FAILED": "Failed to update camera {id}",
    "CAMERA_DELETE": "Camera {id} deleted",
    "CAMERA_DELETE_FAILED": "Failed to delete camera {id}",

    # ---------------------------
    # Config Service
    # ---------------------------
    "CONFIG_SCHEMA_UPDATED": "Configuration schema verified/updated",
    "CONFIG_SCHEMA_FAILED": "Failed to update configuration schema",
    "CONFIG_CREATED_DEFAULT": "Default configuration created",
    "CONFIG_FETCHED": "Configuration fetched successfully",
    "CONFIG_FETCH_FAILED": "Failed to fetch configuration",
    "CONFIG_UPDATED": "Configuration updated successfully",
    "CONFIG_UPDATE_FAILED": "Failed to update configuration",

    # ---------------------------
    # Speaker Service / Hooter
    # ---------------------------
    "SPEAKER_INIT": "Speaker service initialized",
    "SPEAKER_IP_NOT_CONFIGURED": "Speaker IP address is not configured",
    "SPEAKER_PORT_NOT_CONFIGURED": "Speaker port is not configured",
    "SPEAKER_TRIGGER_ENDPOINT_NOT_CONFIGURED": "Speaker trigger endpoint is not configured",
    "SPEAKER_DISABLED": "Speaker feature is disabled",
    "SPEAKER_CONNECTED": "Speaker {ip}:{port} is connected",
    "SPEAKER_STATUS_FAILED": "Speaker returned status code {code}",
    "SPEAKER_CONNECTION_ERROR": "Cannot connect to speaker at {url}",
    "SPEAKER_TIMEOUT": "Speaker connection timed out at {url}",
    "SPEAKER_UNEXPECTED_ERROR": "Unexpected error checking speaker connection",
    "SPEAKER_TRIGGER_FAILED": "Speaker not configured, cannot trigger hooter",
    "HOOTER_ALREADY_ACTIVE": "Hooter is already active, skipping duplicate trigger",
    "HOOTER_TRIGGER": "Triggering hooter at {url} - {time}",
    "HOOTER_TRIGGER_SUCCESS": "Hooter triggered successfully",
     "HOOTER_TRIGGER_FAILED": "Hooter trigger returned status {code}: {text}",
    "HOOTER_CONNECTION_ERROR": "Failed to trigger hooter - Connection error to {url}",
    "HOOTER_TIMEOUT": "Failed to trigger hooter - Request timed out",
    "HOOTER_UNEXPECTED_ERROR": "Unexpected error triggering hooter",
    "HOOTER_STOP": "Stopping hooter at {url} - {time}",
    "HOOTER_STOP_SUCCESS": "Hooter stopped successfully",
    "HOOTER_STOP_FAILED": "Hooter stop returned status {code}: {text}",
    "HOOTER_AUTO_STOP": "Auto-stop scheduled in {duration} seconds",

    # ---------------------------
    # Email Service
    # ---------------------------
    "EMAIL_SENT": "Email successfully sent to {email}",
    "EMAIL_AUTH_FAILED": "Email authentication failed. Check credentials.",
    "EMAIL_SEND_FAILED": "Failed to send email to {email}",
    "EMAIL_UNEXPECTED_ERROR": "Unexpected error occurred while sending email",

    # ---------------------------
    # Alerts & Notifications
    # ---------------------------
    "ALERT_TRIGGER_FAILED": "Failed to trigger alert output",
    "ALERT_LOGGED": "Alert logged in DB: {msg}",
    "ALERT_DB_FAILED": "Failed to log alert in DB",
    "ALERT_POSTED": "Alert posted to API",
    "ALERT_POST_FAILED": "Failed to post alert to API",
    "ALERT_WHATSAPP_SENT": "WhatsApp alert sent to {phone}",
    "ALERT_WHATSAPP_FAILED": "WhatsApp alert failed",
    "ALERT_WHATSAPP_SKIPPED": "WhatsApp alert skipped (Twilio or phone missing)",
    "ALERT_SNAPSHOT_SAVED": "Snapshot saved: {path}",
    "ALERT_SNAPSHOT_NOT_SAVED": "Snapshot not saved (OpenCV not available)",
    "ALERT_SNAPSHOT_FAILED": "Error saving snapshot",
    "ALERT_MUTE_QUERY_FAILED": "DB query failed in is_muted",
    "ZONE_INTRUSION": "Person detected crossing zone {zone}",
    "CAMERA_OWNER_FAILED": "Error fetching camera owner",
    # ---------------------------
        # Database
        # ---------------------------
    "DB_ENGINE_INIT": "Database engine initialized with URL {url}",
    "DB_ENGINE_INIT_FAILED": "Failed to initialize database engine",
    "DB_SESSION_ERROR": "Database session error: {error}",
    "DB_SESSION_CLOSED": "Database session closed",
    "DB_CONNECT": "Database connection established: {url}",
    "DB_CLOSE": "Database connection closed",
    "DB_CHECKOUT": "Database connection checked out",
    "DB_CHECKIN": "Database connection returned to pool",

        # ---------------------------
        #Util 
        #-------------------------------


    "DIR_CREATED": "Directory ensured at {path}",
    "DIR_CREATE_FAILED": "Failed to create directory {path}",
    "SNAPSHOT_PATH_GENERATED": "Snapshot path generated: {path}",
    "SNAPSHOT_PATH_FAILED": "Failed to generate snapshot path for camera {camera}",
    "FRAME_SAVED": "Frame saved successfully at {path}",
    "FRAME_SAVE_FAILED": "Failed to save frame at {path}",
    "FRAME_SAVE_ERROR": "Error saving frame at {path}",
    "FRAME_RESIZED": "Frame resized to width {width}",
    "FRAME_RESIZE_FAILED": "Failed to resize frame",
    "DETECTIONS_FILTERED": "Detections filtered, count={count}",
    "DETECTIONS_FILTER_FAILED": "Failed to filter detections",
    "BOXES_DRAWN": "Bounding boxes drawn, count={count}",
    "BOXES_DRAW_FAILED": "Failed to draw bounding boxes",
 
    #----------------------------------
    #entries for detector
    #----------------------------------

    "YOLO_MODEL_LOADED": "YOLO model loaded on {device}",
    "YOLO_MODEL_MOVE_FAILED": "Could not move YOLO model to {device}",
    "YOLO_CLASS_RESOLVE_FAILED": "Failed to resolve 'person' class id",
    "YOLO_CONFIG_REFRESH_FAILED": "Could not refresh detector config from DB",
    "YOLO_CONFIG_APPLIED": "Detector config applied -> conf={conf}, frame={frame}, image={image}, focal={focal}, infer={infer}",
    "YOLO_BATCH_STARTED": "Batch detection loop started",
    "YOLO_BATCH_STOPPED": "Batch detection loop stopped",
    "YOLO_BATCH_PREDICT_FAILED": "Batch predict error",
    "YOLO_RESULT_PROCESS_FAILED": "Error processing result for camera {camera}",
    "YOLO_ALERT_TRIGGERED": "Alert triggered for camera {camera}",
    "YOLO_ALERT_TRIGGER_FAILED": "Failed to trigger alert for camera {camera}",
    "YOLO_ALERT_LOGGED": "Alert logged for camera {camera}, zone {zone}",
    "YOLO_ALERT_LOG_FAILED": "Failed to log alert for camera {camera}",
    "YOLO_BATCH_THREAD_STARTED": "Batch detection thread started",
    "YOLO_CAMERA_STARTED": "Camera {camera} started with stream {url}",
    "YOLO_THREAD_JOIN_FAILED": "Failed to join reader thread",
    "YOLO_BATCH_THREAD_STOP_FAILED": "Failed to stop batch thread",
    "YOLO_CAPTURE_RELEASE_FAILED": "Failed to release camera capture",
    "YOLO_SOUND_EXECUTOR_SHUTDOWN_FAILED": "Failed to shutdown sound executor",
    "YOLO_ALL_DETECTIONS_STOPPED": "All detections stopped",
    "YOLO_GET_CAMERAS_FAILED": "Failed to get list of cameras",

    #-------------------------------
    #file_ops
    #-------------------------------

    "DIR_CREATED": "Directory ensured at {path}",
    "DIR_CREATE_FAILED": "Failed to create directory {path}",
    "DIR_CLEARED": "Directory cleared at {path}",
    "DIR_CLEAR_FAILED": "Failed to clear directory {path}",
    "SNAPSHOT_ARCHIVED": "Snapshot archived at {path}",
    "SNAPSHOT_ARCHIVE_FAILED": "Failed to archive snapshot {path}",
    "SNAPSHOT_DELETED": "Snapshot deleted at {path}",
    "SNAPSHOT_NOT_FOUND": "Snapshot not found at {path}",
    "SNAPSHOT_DELETE_FAILED": "Failed to delete snapshot {path}",
    "ZONE_CONFIG_SAVED": "Zone configuration saved at {path}",
    "ZONE_CONFIG_SAVE_FAILED": "Failed to save zone configuration for {zone}",
    "ZONE_CONFIG_LOADED": "Zone configuration loaded from {path}",
    "ZONE_CONFIG_NOT_FOUND": "Zone configuration not found for {zone}",
    "ZONE_CONFIG_LOAD_FAILED": "Failed to load zone configuration for {zone}",
    "FILES_CLEANED": "Cleaned {count} old files from {dir}",
    "FILES_CLEAN_FAILED": "Failed to cleanup files in {dir}",

    # Service init
    "ALERT_SERVICE_INIT": "Alert service initialized",

    # Config
    "CONFIG_FETCH_FAILED": "Failed to fetch configuration from DB",
    "CONFIG_NOT_FOUND": "No configuration found",

    # Sound / hooter
    "HOOTER_TRIGGERED": "Hooter triggered for camera {camera_id}",
    "ALERT_TRIGGER_FAILED": "Failed to trigger alert sound/hooter",
    "SOUND_PLAYED": "Alert sound played successfully",
    "NO_SOUND_BACKEND": "No sound backend available (pygame/playsound missing)",
    "SOUND_PLAY_FAILED": "Failed to play alert sound",
    "THREADPOOL_FAILED": "Failed to submit sound playback to threadpool",
    "DIRECT_PLAY_FAILED": "Direct sound playback failed",

    # WhatsApp
    "WHATSAPP_SKIPPED": "WhatsApp alert skipped (Twilio or phone missing)",
    "WHATSAPP_SENT": "WhatsApp alert sent to {phone}",
    "WHATSAPP_FAILED": "Failed to send WhatsApp alert",

    # Snapshots
    "SNAPSHOT_SAVED": "Snapshot saved at {path}",
    "SNAPSHOT_NOT_SAVED": "Snapshot not saved (OpenCV unavailable)",
    "SNAPSHOT_FAILED": "Failed to save snapshot",

    # Alerts
    "ALERT_LOGGED": "Alert logged: {msg}",
    "ALERT_DB_FAILED": "Failed to log alert in DB",
    "ALERT_POSTED": "Alert posted to API",
    "ALERT_POST_FAILED": "Failed to post alert to API",

    # Intrusion
    "ZONE_INTRUSION": "Person detected crossing zone {zone}",

    # Camera owner
    "CAMERA_OWNER_FAILED": "Failed to fetch camera owner details",

    # Email
    "EMAIL_SENT": "Email sent to {email}",
    "EMAIL_FAILED": "Failed to send email",

    # Mute schedule
    "MUTE_QUERY_FAILED": "Failed to query mute schedule",

    # Optional dependencies
    "OPENCV_NOT_AVAILABLE": "OpenCV not available",
    "REQUESTS_NOT_AVAILABLE": "Requests library not available",
    "PLAYSOUND_NOT_AVAILABLE": "Playsound library not available",
    "TWILIO_NOT_AVAILABLE": "Twilio client not available",
    "PYGAME_NOT_AVAILABLE": "Pygame not available",

    # General
    "ALERT": "Alert",

    "CONFIG_PATH_FAILED": "Failed to resolve config path",
    "CONFIG_FILE_NOT_FOUND": "Config file not found at {path}, using defaults",
    "CONFIG_LOADED": "Configuration loaded from {path}",
    "CONFIG_LOAD_FAILED": "Failed to load configuration file",

    "MUTE_FETCH_ALL": "Fetched {count} mute schedules",
    "MUTE_FETCH_FAILED": "Failed to fetch mute schedules",
    "MUTE_NOT_FOUND": "Mute schedule not found (id={id})",
    "MUTE_CREATED": "Mute schedule created by {user} (id={id})",
    "MUTE_CREATE_FAILED": "Failed to create mute schedule",
    "MUTE_UPDATED": "Mute schedule updated by {user} (id={id})",
    "MUTE_UPDATE_FAILED": "Failed to update mute schedule",
    "MUTE_DELETED": "Mute schedule deleted by {user} (id={id})",
    "MUTE_DELETE_FAILED": "Failed to delete mute schedule",
    "config_missing": "[WARN] Detector config not found in DB, using defaults",

        "config_applied": "[CONFIG] Detector runtime config applied -> confidence={conf}, frame_size={frame_size}, image_size={image_size}, focal_length={focal_length}, inference_size={inference_size}",
    "config_apply_failed": "[ERROR] Failed to apply detector config: {error}",
    "config_refresh_failed": "[WARN] Could not refresh detector config from DB: {error}",
    "camera_started": "[STARTED] Camera {camera_id} ({stream_url})",
    "camera_open_failed": "[ERROR] Failed to open video source for camera {camera_id}: {url}",
    "camera_signal_lost": "[WARN] Camera {camera_id} lost signal, reconnecting...",
    "camera_reader_stopped": "[INFO] Camera {camera_id} reader stopped",
    "camera_reader_error": "[ERROR] Camera {camera_id} reader crashed: {error}",
    "batch_started": "[BATCH DETECTOR STARTED]",
    "batch_stopped": "[BATCH DETECTOR STOPPED]",
    "batch_predict_error": "[WARN] batch predict error: {error}",
    "alert_failed": "[WARN] Could not handle alert: {error}",
    "detections_stopped": "[INFO] All detections stopped",
    
}