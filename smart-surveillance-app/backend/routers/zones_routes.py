# app/routers/zones.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import json, sys, time
from pathlib import Path

try:
    import cv2
except Exception:  # optional dependency fallback
    cv2 = None

from backend.database.database import get_db
from backend.database import models
from backend.config.router_message import MESSAGES
from backend.config.logging_config import logger
from backend.auth.auth_dependency import require_role, get_current_user
from backend.detection.yolo_detector import detector as shared_detector

# ✅ Import shared cache
from backend.routers.cameras_routes import camera_cache

router = APIRouter(prefix="/zones", tags=["Zones"])

# ---------------------------
# Request Models
# ---------------------------
class ZoneCreate(BaseModel):
    camera_id: int
    polygon_coords: str
    sensitivity: str | None = None
    snapshot_file: str | None = None

class ZoneUpdate(BaseModel):
    polygon_coords: str | None = None
    sensitivity: str | None = None
    snapshot_file: str | None = None

# ---------------------------
# Endpoints
# ---------------------------

@router.get("/active-feed")
def active_feed(db: Session = Depends(get_db)):
    try:
        camera = db.query(models.Zone.camera_id).first()
        if not camera:
            logger.warning(MESSAGES["ACTIVE_FEED_EMPTY"])
            return {"stream_url": None}
        logger.info(MESSAGES["ACTIVE_FEED_SUCCESS"].format(camera_id=camera[0]))
        return {"stream_url": f"/cameras/{camera[0]}/stream"}
    except Exception as e:
        logger.exception(MESSAGES["ACTIVE_FEED_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["ACTIVE_FEED_FAIL"])


@router.get("/unidentified_object/track")
def track_unidentified_objects():
    logger.info(MESSAGES["TRACK_UNIDENTIFIED_SUCCESS"])
    return {"objects": [], "alerts": []}


@router.get("/capture_snapshot/{camera_id}", dependencies=[Depends(require_role("Admin"))])
def capture_snapshot(camera_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        # 🔹 Try cache first
        cam = camera_cache.get(f"camera:{camera_id}")
        if not cam:
            db_cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
            if not db_cam:
                logger.warning(MESSAGES["CAMERA_NOT_FOUND"])
                raise HTTPException(status_code=404, detail=MESSAGES["CAMERA_NOT_FOUND"])
            cam = {"id": db_cam.id, "rtsp_url": db_cam.rtsp_url, "name": db_cam.name}
            camera_cache.set(f"camera:{camera_id}", cam)

        frame = None
        if shared_detector.is_camera_connected(camera_id):
            frame = shared_detector.get_latest_raw_frame(camera_id)
        if frame is None:
            stream_url = cam["rtsp_url"].strip()
            stream_source = int(stream_url) if stream_url.isdigit() else stream_url
            cap = cv2.VideoCapture(stream_source)
            if not cap.isOpened():
                logger.error(MESSAGES["CAMERA_STREAM_FAIL"].format(url=stream_url))
                raise HTTPException(status_code=500, detail=MESSAGES["CAMERA_STREAM_FAIL"].format(url=stream_url))

            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                logger.error(MESSAGES["FRAME_CAPTURE_FAIL"])
                raise HTTPException(status_code=500, detail=MESSAGES["FRAME_CAPTURE_FAIL"])

        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            snapshots_base = exe_dir / "snapshots"
        else:
            backend_root = Path(__file__).resolve().parent.parent
            snapshots_base = backend_root / "snapshots"

        snapshot_dir = snapshots_base / "zone_setup"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = snapshot_dir / f"camera_{camera_id}_{timestamp}.jpg"

        success = cv2.imwrite(str(snapshot_path), frame)
        if not success:
            logger.error(MESSAGES["SNAPSHOT_SAVE_FAIL"])
            raise HTTPException(status_code=500, detail=MESSAGES["SNAPSHOT_SAVE_FAIL"])

        snapshot_url = f"/snapshots/zone_setup/{snapshot_path.name}"
        logger.info(MESSAGES["SNAPSHOT_SUCCESS_ZONE"].format(path=snapshot_url))
        return {"path": snapshot_url}
    except Exception as e:
        logger.exception(MESSAGES["SNAPSHOT_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["SNAPSHOT_FAIL"])


@router.get("/", dependencies=[Depends(require_role("Admin"))])
def list_zones(camera_id: int = None, db: Session = Depends(get_db)):
    try:
        query = db.query(models.Zone)
        if camera_id:
            query = query.filter(models.Zone.camera_id == camera_id)
        zones = query.all()
        logger.info(MESSAGES["ZONE_FETCH_SUCCESS"])
        return {"status": "success", "message": MESSAGES["ZONE_FETCH_SUCCESS"], "data": zones}
    except Exception as e:
        logger.exception(MESSAGES["ZONE_FETCH_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["ZONE_FETCH_FAIL"])


@router.post("/", dependencies=[Depends(require_role("Admin"))])
def add_zone(zone: ZoneCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        new_zone = models.Zone(
            camera_id=zone.camera_id,
            polygon_coords=zone.polygon_coords,
            sensitivity=zone.sensitivity,
            snapshot_file=zone.snapshot_file,
            created_by=current_user["sub"],
            created_at=datetime.utcnow()
        )
        db.add(new_zone)
        db.commit()
        db.refresh(new_zone)
        logger.info(MESSAGES["ZONE_ADD_SUCCESS"].format(id=new_zone.id))
        return {"status": "success", "message": MESSAGES["ZONE_ADD_SUCCESS"], "data": new_zone}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["ZONE_ADD_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["ZONE_ADD_FAIL"])


@router.put("/{zone_id}", dependencies=[Depends(require_role("Admin"))])
def update_zone(zone_id: int, zone: ZoneUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        db_zone = db.query(models.Zone).filter(models.Zone.id == zone_id).first()
        if not db_zone:
            logger.warning(MESSAGES["ZONE_NOT_FOUND"])
            raise HTTPException(status_code=404, detail=MESSAGES["ZONE_NOT_FOUND"])

        if zone.polygon_coords is not None:
            db_zone.polygon_coords = zone.polygon_coords
        if zone.sensitivity is not None:
            db_zone.sensitivity = zone.sensitivity
        if zone.snapshot_file is not None:
            db_zone.snapshot_file = zone.snapshot_file

        db_zone.updated_by = current_user["sub"]
        db_zone.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(db_zone)
        logger.info(MESSAGES["ZONE_UPDATE_SUCCESS"].format(id=zone_id))
        return {"status": "success", "message": MESSAGES["ZONE_UPDATE_SUCCESS"], "data": db_zone}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["ZONE_UPDATE_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["ZONE_UPDATE_FAIL"])


@router.delete("/{zone_id}", dependencies=[Depends(require_role("Admin"))])
def delete_zone(zone_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        db_zone = db.query(models.Zone).filter(models.Zone.id == zone_id).first()
        if not db_zone:
            logger.warning(MESSAGES["ZONE_NOT_FOUND"])
            raise HTTPException(status_code=404, detail=MESSAGES["ZONE_NOT_FOUND"])

        db.delete(db_zone)
        db.commit()
        logger.info(MESSAGES["ZONE_DELETE_SUCCESS"].format(id=zone_id, user=current_user["sub"]))
        return {"status": "success", "message": MESSAGES["ZONE_DELETE_SUCCESS"], "id": zone_id}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["ZONE_DELETE_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["ZONE_DELETE_FAIL"])


def get_zones_by_camera_id(camera_id: int):
    """Fetch zones directly from DB for a given camera (used by YOLO detector)."""
    from backend.database.database import SessionLocal
    db = SessionLocal()
    try:
        zones = db.query(models.Zone).filter(models.Zone.camera_id == camera_id).all()
        result = []
        for z in zones:
            result.append({
                "id": z.id,
                "polygon_coords": z.polygon_coords,
                "camera_id": z.camera_id
            })
        return result
    finally:
        db.close()
