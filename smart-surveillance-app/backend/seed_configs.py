from backend.database.database import SessionLocal
from backend.database.models import Configurations

def seed_configurations():
    db = SessionLocal()
    
    configs = [
        {"key": "alertSoundPath", "value": "assets/sounds/alert.wav", "description": "File path to the alert sound (wav/mp3/ogg)."},
        {"key": "alertOutputMode", "value": "system", "description": "Where the alert is played: system speakers or external hooter."},
        {"key": "alertDurationSeconds", "value": "15", "description": "Duration of alert sound in seconds."},
        {"key": "archiveDays", "value": "30", "description": "Number of days to retain archived footage."},
        {"key": "confidenceThreshold", "value": "0.5", "description": "Minimum confidence score for detection (0-1)."},
        {"key": "frameSize", "value": "640", "description": "Frame size used for video processing."},
        {"key": "imageSize", "value": "416", "description": "Image size used for detection model input."},
        {"key": "focalLength", "value": "24.0", "description": "Camera focal length in millimeters."},
        {"key": "inferenceSize", "value": "416", "description": "Inference image size for AI model."},
        {"key": "snapshotCount", "value": "5", "description": "Number of snapshots to capture when motion is detected."},
        {"key": "is_Camera_Detector", "value": "false", "description": "Enable or disable live Camera Detection switch."},
        {"key": "live_Face_tracking_enabled", "value": "false", "description": "Enable or disable live Face Detection switch."},
        {"key": "live_tracking_enabled", "value": "true", "description": "Flag to start background live tracking process."},
        {"key": "unattendedObjectUrl", "value": "http://localhost:8002", "description": "Base URL for the Unattended Object worker service."},
        {"key": "unidentifiedObjectPollInterval", "value": "30", "description": "Poll interval in seconds for fetching unidentified object alerts."}
    ]

    for c in configs:
        existing = db.query(Configurations).filter(Configurations.key == c["key"]).first()
        if not existing:
            new_config = Configurations(key=c["key"], value=c["value"], description=c["description"], updated_by="system")
            db.add(new_config)
        else:
            existing.description = c["description"]

    db.commit()
    db.close()
    print("Configurations seeded successfully.")

if __name__ == "__main__":
    seed_configurations()
