from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import time
import cv2

from backend.database.database import get_db
from backend.database.models import Camera
from backend.config.router_message import MESSAGES
from backend.config.logging_config import logger
from backend.auth.auth_dependency import require_role, get_current_user
from backend.detection.yolo_detector import detector
from backend.services.config_service import get_config
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

router = APIRouter(prefix="/cameras", tags=["Cameras"])


# ---------------------------
# Hybrid Cache
# ---------------------------
class HybridCache:
    def __init__(self, ttl: int = 120):
        self.ttl = ttl
        self.store = {}
        self.pending = set()  # track cameras already starting

    def get(self, key: str):
        entry = self.store.get(key)
        if entry and (time.time() - entry["time"] < self.ttl):
            return entry["value"]
        return None

    def set(self, key: str, value):
        self.store[key] = {"value": value, "time": time.time()}

    def invalidate(self, key: str):
        self.store.pop(key, None)

    def cleanup(self):
        now = time.time()
        expired_keys = [k for k, v in self.store.items() if now - v["time"] >= self.ttl]
        for k in expired_keys:
            self.invalidate(k)


camera_cache = HybridCache(ttl=120)


# ---------------------------
# Request Models
# ---------------------------
class CameraCreate(BaseModel):
    name: str
    rtsp_url: str
    location: str


class CameraUpdate(BaseModel):
    name: str | None = None
    rtsp_url: str | None = None
    location: str | None = None


# ---------------------------
# List Cameras (Admin only)
# ---------------------------
@router.get("/", dependencies=[Depends(require_role("Admin"))])
def list_cameras(db: Session = Depends(get_db)):
    try:
        cached = camera_cache.get("camera_list")
        if cached:
            logger.info("Camera list served from cache")
            return {"status": "success", "message": MESSAGES["CAMERA_FETCH_SUCCESS"], "data": cached}

        cameras = db.query(Camera).all()
        camera_dicts = [{"id": c.id, "name": c.name, "rtsp_url": c.rtsp_url, "location": c.location} for c in cameras]

        camera_cache.set("camera_list", camera_dicts)
        for c in camera_dicts:
            camera_cache.set(f"camera:{c['id']}", c)

        return {"status": "success", "message": MESSAGES["CAMERA_FETCH_SUCCESS"], "data": camera_dicts}
    except Exception as e:
        logger.exception(MESSAGES["CAMERA_FETCH_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["CAMERA_FETCH_FAIL"])
    finally:
        db.close()


# ---------------------------
# Add Camera (Admin only)
# ---------------------------
@router.post("/", dependencies=[Depends(require_role("Admin"))])
def add_camera(camera: CameraCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        new_camera = Camera(
            name=camera.name,
            rtsp_url=camera.rtsp_url,
            location=camera.location,
            is_assigned=False,
            created_by=current_user["sub"],
            created_at=datetime.utcnow()
        )
        db.add(new_camera)
        db.commit()
        db.refresh(new_camera)

        cam_dict = {"id": new_camera.id, "name": new_camera.name, "rtsp_url": new_camera.rtsp_url, "location": new_camera.location}
        camera_cache.set(f"camera:{new_camera.id}", cam_dict)
        camera_cache.invalidate("camera_list")

        return {"status": "success", "message": MESSAGES["CAMERA_ADD_SUCCESS"], "data": cam_dict}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["CAMERA_ADD_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["CAMERA_ADD_FAIL"])
    finally:
        db.close()


# ---------------------------
# Update Camera (Admin only)
# ---------------------------
@router.put("/{camera_id}", dependencies=[Depends(require_role("Admin"))])
def update_camera(camera_id: int, camera: CameraUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not db_camera:
            raise HTTPException(status_code=404, detail=MESSAGES["CAMERA_NOT_FOUND"])

        # Restart detector if RTSP URL changes
        if camera.rtsp_url and camera.rtsp_url != db_camera.rtsp_url:
            try:
                detector.stop_detection(camera_id)
            except Exception as e:
                logger.warning(f"Detector stop failed for camera {camera_id}: {e}")

        if camera.name: db_camera.name = camera.name
        if camera.rtsp_url: db_camera.rtsp_url = camera.rtsp_url
        if camera.location: db_camera.location = camera.location

        db_camera.updated_by = current_user["sub"]
        db_camera.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(db_camera)

        cam_dict = {"id": db_camera.id, "name": db_camera.name, "rtsp_url": db_camera.rtsp_url, "location": db_camera.location}
        camera_cache.set(f"camera:{camera_id}", cam_dict)
        camera_cache.invalidate("camera_list")

        return {"status": "success", "message": MESSAGES["CAMERA_UPDATE_SUCCESS"], "data": cam_dict}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["CAMERA_UPDATE_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["CAMERA_UPDATE_FAIL"])
    finally:
        db.close()


# ---------------------------
# Delete Camera (Admin only)
# ---------------------------
@router.delete("/{camera_id}", dependencies=[Depends(require_role("Admin"))])
def delete_camera(camera_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not db_camera:
            raise HTTPException(status_code=404, detail=MESSAGES["CAMERA_NOT_FOUND"])

        from backend.database import models
        db.query(models.Zone).filter(models.Zone.camera_id == camera_id).delete()
        db.query(models.Alert).filter(models.Alert.camera_id == camera_id).delete()
        db.query(models.EventLogs).filter(models.EventLogs.camera_id == camera_id).delete()
        db.query(models.Snapshot).filter(models.Snapshot.camera_id == camera_id).delete()
        db.query(models.UserCameraMapping).filter(models.UserCameraMapping.camera_id == camera_id).delete()

        try:
            detector.stop_detection(camera_id)
        except Exception as e:
            logger.warning(MESSAGES["CAMERA_STOP_FAIL"].format(id=camera_id, error=str(e)))

        db.delete(db_camera)
        db.commit()

        camera_cache.invalidate(f"camera:{camera_id}")
        camera_cache.invalidate("camera_list")

        return {"status": "success", "message": MESSAGES["CAMERA_DELETE_SUCCESS"], "id": camera_id}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["CAMERA_DELETE_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["CAMERA_DELETE_FAIL"])
    finally:
        db.close()


# ---------------------------
# Stream Camera
# ---------------------------
"""@router.get("/{camera_id}/stream")
def stream_camera(camera_id: int, mode: str = "processed", db: Session = Depends(get_db)):
    try:
        # Get camera info from cache or DB
        camera = camera_cache.get(f"camera:{camera_id}")
        if not camera:
            db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
            if not db_camera:
                return Response(MESSAGES["CAMERA_NOT_FOUND"], status_code=404)
            camera = {"id": db_camera.id, "rtsp_url": db_camera.rtsp_url, "name": db_camera.name}
            camera_cache.set(f"camera:{camera_id}", camera)

        # Check config
        cfg = get_config()
        if not cfg.is_Camera_Detector:
            return Response("Detection is disabled by configuration", status_code=403)

        # Start detector if not already running
        if not detector.is_camera_connected(camera_id) and camera_id not in camera_cache.pending:
            camera_cache.pending.add(camera_id)
            source = int(camera["rtsp_url"]) if camera["rtsp_url"].isdigit() else camera["rtsp_url"]
            detector.start_detection(source, camera_id)

        def frame_generator():
            while True:
                try:
                    # Get frame from detector
                    frame = detector.get_latest_raw_frame(camera_id) if mode == "raw" else detector.get_frame(camera_id)
                    if frame is None:
                        logger.warning(f"[Stream] No frame available for camera {camera_id}")
                        time.sleep(0.05)
                        continue

                    # Encode frame
                    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    if not ok:
                        logger.error(f"[Stream] Failed to encode frame for camera {camera_id}")
                        time.sleep(0.05)
                        continue

                    # Yield MJPEG chunk
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                    time.sleep(0.05)

                except Exception as e:
                    logger.exception(f"[Stream] Error in frame generator for camera {camera_id}: {e}")
                    break

        return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

    finally:
        db.close()"""

@router.websocket("/{camera_id}/stream")
async def stream_camera(websocket: WebSocket, camera_id: int, mode: str = "processed", db: Session = Depends(get_db)):
    # Accept the incoming browser WebSocket connection
    await websocket.accept()
    
    try:
        # Get camera info from cache or DB (Kept identical to your logic)
        camera = camera_cache.get(f"camera:{camera_id}")
        if not camera:
            db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
            if not db_camera:
                await websocket.close(code=4404, reason=MESSAGES["CAMERA_NOT_FOUND"])
                return
            camera = {"id": db_camera.id, "rtsp_url": db_camera.rtsp_url, "name": db_camera.name}
            camera_cache.set(f"camera:{camera_id}", camera)

        # Start detector if not already running (Kept identical to your logic)
        if not detector.is_camera_connected(camera_id) and camera_id not in camera_cache.pending:
            camera_cache.pending.add(camera_id)
            source = int(camera["rtsp_url"]) if camera["rtsp_url"].isdigit() else camera["rtsp_url"]
            detector.start_detection(source, camera_id)
            # Remove from pending after starting so it can be retried later if it fails to connect
            camera_cache.pending.discard(camera_id)

        # Streaming loop over WebSocket
        while True:
            try:
                # Get frame from detector
                frame = detector.get_latest_raw_frame(camera_id) if mode == "raw" else detector.get_frame(camera_id)
                if frame is None:
                    # Generate a placeholder "NO SIGNAL" frame instead of leaving the canvas black
                    frame = detector._generate_no_signal_frame()

                # Encode frame
                ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if not ok:
                    logger.error(f"[Stream] Failed to encode frame for camera {camera_id}")
                    await asyncio.sleep(0.05)
                    continue

                # Send frame as binary data over WebSocket
                await websocket.send_bytes(buffer.tobytes())
                await asyncio.sleep(0.05)

            except WebSocketDisconnect:
                # Triggers automatically when user closes browser tab or changes page
                logger.info(f"[Stream] Browser disconnected from camera {camera_id}")
                break
            except Exception as e:
                logger.exception(f"[Stream] Error in frame loop for camera {camera_id}: {e}")
                break

    finally:
        db.close()

# ---------------------------
# Latest Frame
# ---------------------------
@router.get("/{camera_id}/latest_frame")
def latest_frame(camera_id: int, db: Session = Depends(get_db)):
    try:
        # ✅ Only fetch raw frame, no detection
        frame = detector.get_latest_raw_frame(camera_id)
        if frame is None:
            # If detector has no frame, fallback to direct RTSP capture
            db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
            if not db_camera:
                return Response(MESSAGES["CAMERA_NOT_FOUND"], status_code=404)

            stream_url = db_camera.rtsp_url.strip()
            source = int(stream_url) if stream_url.isdigit() else stream_url
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                return Response(MESSAGES["FRAME_CAPTURE_FAIL"], status_code=500)

            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                return Response(MESSAGES["FRAME_CAPTURE_FAIL"], status_code=500)

        # ✅ Encode raw frame quickly
        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])  
        if not ok:
            return Response(MESSAGES["FRAME_ENCODING_FAIL"], status_code=500)

        return Response(content=buffer.tobytes(), media_type="image/jpeg")
    finally:
        db.close()

# ---------------------------
# Snapshot (optimized)
# ---------------------------
@router.get("/{camera_id}/frame")
def get_camera_snapshot(camera_id: int, db: Session = Depends(get_db)):
    try:
        frame = detector.get_latest_raw_frame(camera_id)
        if frame is None:
            camera = camera_cache.get(f"camera:{camera_id}")
            if not camera:
                db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
                if not db_camera:
                    return Response(MESSAGES["CAMERA_NOT_FOUND"], status_code=404)
                camera = {"id": db_camera.id, "rtsp_url": db_camera.rtsp_url}
                camera_cache.set(f"camera:{camera_id}", camera)

            stream_url = camera["rtsp_url"].strip()
            source = int(stream_url) if stream_url.isdigit() else stream_url
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                return Response(MESSAGES["FRAME_CAPTURE_FAIL"], status_code=500)

            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                return Response(MESSAGES["FRAME_CAPTURE_FAIL"], status_code=500)

        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            return Response(MESSAGES["FRAME_ENCODING_FAIL"], status_code=500)

        logger.info(MESSAGES["SNAPSHOT_SUCCESS"].format(id=camera_id))
        return Response(content=buffer.tobytes(), media_type="image/jpeg")
    except Exception as e:
        logger.exception(MESSAGES["SNAPSHOT_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["SNAPSHOT_FAIL"])
    finally:
        db.close()
    