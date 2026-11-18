import time, threading
import cv2, requests, base64, numpy as np
from sqlalchemy.orm import Session
import insightface
import warnings
from datetime import datetime
import onnxruntime as ort

from backend.config.settings import settings
from backend.database.database import SessionLocal
from backend.database.models import (
    Camera,
    UserCameraAssignment,
    Configurations,
)
from backend.config.logging_config import logger
from backend.util.messages import messages
from backend.services.notifications import NotificationsService
from backend.util.face_cache import face_cache

warnings.filterwarnings("ignore", category=FutureWarning)

# -------------------------
# Load InsightFace model once (GPU if available, else CPU)
# -------------------------
available_providers = ort.get_available_providers()
if "CUDAExecutionProvider" in available_providers:
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    logger.info("[INSIGHTFACE] Using GPU (CUDAExecutionProvider)")
else:
    providers = ["CPUExecutionProvider"]
    logger.info("[INSIGHTFACE] Using CPU (CPUExecutionProvider)")

model = insightface.app.FaceAnalysis(name="buffalo_l", providers=providers)
model.prepare(ctx_id=0, det_size=(640, 640))

# -------------------------
# Utility functions
# -------------------------
def extract_faces(frame):
    return model.get(frame) or [] 

def crop_and_encode_face(frame, bbox):
    x1, y1, x2, y2 = map(int, bbox)
    face_crop = frame[y1:y2, x1:x2]
    _, buffer = cv2.imencode('.jpg', face_crop)
    return base64.b64encode(buffer).decode("utf-8")

def is_live_tracking_enabled(db: Session) -> bool:
    cfg = db.query(Configurations).filter(Configurations.key == "live_tracking_enabled").first()
    if not cfg:
        return False
    return cfg.value.strip().lower() == "true"

def get_similarity_threshold(db: Session) -> float:
    cfg = db.query(Configurations).filter(Configurations.key == "similarity_threshold").first()
    return float(cfg.value) if cfg else 0.6

# -------------------------
# Monitor a single camera
# -------------------------
def monitor_camera(camera_id: int, camera_name: str, rtsp_url: str, stop_event: threading.Event):
    logger.info(f"Started monitoring camera '{camera_name}' (ID={camera_id})")
    
    last_alert_time = 0
    COOLDOWN_SECONDS = 10

    while not stop_event.is_set():
        db: Session = SessionLocal()
        alert_service = NotificationsService(db)

        if not is_live_tracking_enabled(db):
            logger.info(f"{messages['LIVE_TRACKING_DISABLED']} (camera={camera_name})")
            db.close()
            break

        try:
            resp = requests.get(f"{settings.BASE_API_URL}/cameras/{camera_id}/latest_frame")
            if resp.status_code != 200 or not resp.content:
                db.close()
                time.sleep(1)
                continue

            nparr = np.frombuffer(resp.content, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                db.close()
                time.sleep(1)
                continue

            faces = extract_faces(frame)
            if not faces:
                db.close()
                time.sleep(0.5)
                continue

            # Refresh cache and threshold
            face_cache.refresh_if_needed(db)
            threshold = get_similarity_threshold(db)
            db.close()

            for face in faces:
                emb = face.embedding.tolist()
                bbox = face.bbox.astype(int).tolist()
                thumbnail = crop_and_encode_face(frame, bbox)

                matched_user, best_sim = face_cache.find_best_match(emb, threshold=threshold)
                
                if matched_user:
                    logger.debug(f"[SIMILARITY] user={matched_user['name']}, sim={best_sim:.3f}, threshold={threshold}")

                    # Reopen session only when needed for assignments
                    db2: Session = SessionLocal()
                    assignments = db2.query(UserCameraAssignment).filter(
                        UserCameraAssignment.user_id == matched_user["id"],
                        UserCameraAssignment.untagged == False
                    ).all()
                    assigned_ids = [a.camera_id for a in assignments]
                    db2.close()

                    if camera_id not in assigned_ids:
                        current_time = time.time()
                        if current_time - last_alert_time > COOLDOWN_SECONDS:
                            alert_msg = f"{messages['FACE_UNAUTHORIZED']}: User '{matched_user['name']}' in camera '{camera_name}'"
                            logger.error(alert_msg)
                            alert_service.save_alert(camera_id, alert_msg)
                            alert_service.notify("db", {"camera_id": camera_id, "message": alert_msg})
                            last_alert_time = current_time
                    else:
                        logger.info(f"{messages['FACE_RECOGNIZED']} (user={matched_user['name']}, camera={camera_name})")
                else:
                    current_time = time.time()
                    if current_time - last_alert_time > COOLDOWN_SECONDS:
                        alert_msg = f"{messages['FACE_UNAUTHORIZED']}: Unknown face detected in camera '{camera_name}'"
                        logger.error(alert_msg)
                        alert_service.save_alert(camera_id, alert_msg)
                        alert_service.notify("db", {"camera_id": camera_id, "message": alert_msg})
                        last_alert_time = current_time

        except Exception as e:
            logger.exception(f"{messages['MONITOR_ERROR']} (camera={camera_name}, id={camera_id}): {e}")
        finally:
            try:
                db.close()
            except:
                pass

        time.sleep(0.5)
        
    logger.info(f"Stopped monitoring camera '{camera_name}' (ID={camera_id})")

# -------------------------
# Live tracking loop
# -------------------------
def run_live_tracking():
    logger.info(messages["LIVE_TRACKING_STARTED"])
    active_threads = {}

    try:
        while True:
            db: Session = SessionLocal()
            enabled = is_live_tracking_enabled(db)
            db.close()

            if enabled:
                db: Session = SessionLocal()
                cameras = db.query(Camera).filter_by(is_assigned=True).all()
                db.close()

                current_ids = {cam.id for cam in cameras}
                active_ids = set(active_threads.keys())

                # Start monitoring new cameras
                for cam in cameras:
                    if cam.id not in active_ids:
                        logger.info(f"Starting monitor for new camera {cam.name} (ID={cam.id})")
                        stop_event = threading.Event()
                        t = threading.Thread(
                            target=monitor_camera, 
                            args=(cam.id, cam.name, cam.rtsp_url, stop_event),
                            daemon=True
                        )
                        t.start()
                        active_threads[cam.id] = {"thread": t, "stop_event": stop_event}

                # Stop monitoring removed cameras
                for cam_id in active_ids - current_ids:
                    logger.info(f"Stopping monitor for removed camera ID={cam_id}")
                    active_threads[cam_id]["stop_event"].set()
                    active_threads[cam_id]["thread"].join(timeout=1)
                    del active_threads[cam_id]

            else:
                # Stop all tasks if live tracking disabled
                for cam_id, info in list(active_threads.items()):
                    logger.info(f"Stopping monitor for camera ID={cam_id} (live tracking disabled)")
                    info["stop_event"].set()
                    info["thread"].join(timeout=1)
                    del active_threads[cam_id]
                time.sleep(2)

            time.sleep(5)

    except KeyboardInterrupt:
        logger.info(messages["LIVE_TRACKING_STOPPED"])
        for cam_id, info in active_threads.items():
            info["stop_event"].set()
            info["thread"].join(timeout=1)

# -------------------------
# Entry point
# -------------------------
if __name__ == "__main__":
    run_live_tracking()
