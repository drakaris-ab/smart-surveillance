from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database.database import get_db
from backend.database.models import Camera
from backend.config.logging_config import logger
from backend.util.messages import messages
from backend.util.camera_cache import global_cache

router = APIRouter(prefix="/Unwanted_camera", tags=["Unwanted Camera"])

# -------------------------
# Helper: refresh all cameras in cache
# -------------------------
def refresh_camera_cache(db: Session):
    cameras = db.query(Camera).all()
    result = []
    for cam in cameras:
        # cam.is_assigned is now a Boolean (True/False/None)
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
        logger.info(f"[CACHE REFRESH] Camera {cam.id} ({cam.name}) raw={cam.is_assigned} -> normalized={assigned}")
    global_cache.set("all_cameras", result)
    return result

# -------------------------
# GET all cameras (cache-first)
# -------------------------
@router.get("")
def get_cameras_with_assignment(db: Session = Depends(get_db)):
    try:
        data = global_cache.get("all_cameras")
        if not data:  # if cache empty or expired, refresh from DB
            logger.info("[CACHE MISS] Fetching cameras from DB")
            data = refresh_camera_cache(db)
        else:
            logger.info("[CACHE HIT] Returning cameras from cache")

        # Log what’s being returned
        for cam in data:
            logger.info(f"[CACHE RETURN] Camera {cam['camera_id']} ({cam['name']}) is_assigned={cam['is_assigned']}")

        logger.info(messages["ASSIGNMENT_FETCHED"])
        return {"status": "success", "message": messages["ASSIGNMENT_FETCHED"], "data": data}
    except Exception as e:
        logger.exception(f"{messages['ASSIGNMENT_ERROR']}: {e}")
        raise HTTPException(status_code=500, detail=messages["ASSIGNMENT_ERROR"])

# -------------------------
# ASSIGN a camera
# -------------------------
@router.post("")
def assign_camera(camera_id: int, user: str, db: Session = Depends(get_db)):
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise HTTPException(status_code=404, detail=messages["CAMERA_NOT_FOUND"])
        if camera.is_assigned:  # already True
            raise HTTPException(status_code=400, detail=messages["CAMERA_ALREADY_ASSIGNED"])

        camera.is_assigned = True
        camera.updated_by = user
        camera.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(camera)

        data = refresh_camera_cache(db)
        logger.info(f"{messages['ASSIGNMENT_CREATED']} (camera_id={camera_id}, user={user})")
        return {"status": "success", "message": messages["ASSIGNMENT_CREATED"], "data": data}
    except Exception as e:
        logger.exception(f"{messages['ASSIGNMENT_ERROR']}: {e}")
        raise HTTPException(status_code=500, detail=messages["ASSIGNMENT_ERROR"])

# -------------------------
# UNASSIGN a camera
# -------------------------
@router.delete("/{camera_id}")
def unassign_camera(camera_id: int, user: str, db: Session = Depends(get_db)):
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise HTTPException(status_code=404, detail=messages["CAMERA_NOT_FOUND"])
        if not camera.is_assigned:  # already False
            raise HTTPException(status_code=404, detail=messages["ASSIGNMENT_NOT_FOUND"])

        camera.is_assigned = False
        camera.updated_by = user
        camera.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(camera)

        data = refresh_camera_cache(db)
        logger.info(f"{messages['ASSIGNMENT_DELETED']} (id={camera_id}, user={user})")
        return {"status": "success", "message": messages["ASSIGNMENT_DELETED"], "data": data}
    except Exception as e:
        logger.exception(f"{messages['ASSIGNMENT_ERROR']}: {e}")
        raise HTTPException(status_code=500, detail=messages["ASSIGNMENT_ERROR"])
