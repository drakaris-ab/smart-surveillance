from sqlalchemy import event
from sqlalchemy.orm import Session
from backend.database.database import SessionLocal
from backend.database.models import Camera
from backend.util.camera_cache import global_cache
from backend.config.logging_config import logger

# -------------------------
# Refresh function
# -------------------------
def refresh_camera_cache(db: Session):
    cameras = db.query(Camera).all()
    result = []
    for cam in cameras:
        # cam.is_assigned is now Boolean (True/False/None)
        assigned = bool(cam.is_assigned)  # None → False
        result.append({
            "camera_id": cam.id,
            "name": cam.name,
            "location": cam.location,
            "rtsp_url": cam.rtsp_url,
            "is_assigned": assigned,  # return as boolean
            "created_by": cam.created_by,
            "updated_by": cam.updated_by,
            "created_at": cam.created_at,
            "updated_at": cam.updated_at,
        })
        logger.info(
            f"[CACHE REFRESH] Camera {cam.id} ({cam.name}) raw={cam.is_assigned} → normalized={assigned}"
        )
    global_cache.set("all_cameras", result)
    logger.info("[CACHE REFRESH] Camera cache updated automatically")
    return result

# -------------------------
# SQLAlchemy Event Listeners
# -------------------------
@event.listens_for(Camera, "after_insert")
@event.listens_for(Camera, "after_update")
@event.listens_for(Camera, "after_delete")
def camera_changed(mapper, connection, target):
    db = SessionLocal()
    try:
        refresh_camera_cache(db)
    finally:
        db.close()
