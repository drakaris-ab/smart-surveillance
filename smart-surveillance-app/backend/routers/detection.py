# app/routers/detection.py
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import StreamingResponse
import cv2
import time

from backend.database import SessionLocal, Camera
from backend.detection import detector
from backend.config.logging_config import logger
from backend.config.router_message import MESSAGES
from backend.services.config_service import get_config

router = APIRouter(prefix="/detection", tags=["Detection"])
STREAM_FPS = 20
STREAM_FRAME_INTERVAL = 1.0 / STREAM_FPS


# ---------------------------
# Stream Camera  
# ---------------------------
"""@router.get("/stream/{camera_id}")
def stream_camera(camera_id: int):
    if detector is None:
        logger.error(MESSAGES["DETECTOR_NOT_INITIALIZED"])
        return {"error": MESSAGES["DETECTOR_NOT_INITIALIZED"]}

    cfg = get_config()
    if not cfg.is_Camera_Detector:
        logger.info(f"Detection disabled globally (is_Camera_Detector=False)")
        return {"error": "Detection is disabled by configuration"}

    try:
        known = set(detector.get_all_cameras())
        if camera_id not in known:
            db = SessionLocal()
            try:
                cam = db.query(Camera).filter(Camera.id == camera_id).first()
                if not cam:
                    logger.warning(MESSAGES["CAMERA_NOT_FOUND"].format(id=camera_id))
                    return {"error": MESSAGES["CAMERA_NOT_FOUND"].format(id=camera_id)}

                stream_url = getattr(cam, "stream_url", None) or getattr(cam, "rtsp_url", None)
                if isinstance(stream_url, str) and stream_url.isdigit():
                    stream_url = int(stream_url)

                detector.start_detection(stream_url, camera_id)
                logger.info(MESSAGES["CAMERA_STREAM_STARTED"].format(id=camera_id))
            finally:
                db.close()

        def frame_generator():
            while True:
                frame = detector.get_frame(camera_id)
                if frame is None:
                    time.sleep(0.05)
                    continue
                ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if not ok:
                    logger.warning(MESSAGES["FRAME_ENCODING_FAIL"])
                    time.sleep(0.01)
                    continue
                yield ( 
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                )
                time.sleep(STREAM_FRAME_INTERVAL)

        return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")
    except Exception as e:
        logger.exception(MESSAGES["CAMERA_STREAM_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["CAMERA_STREAM_FAIL"])"""


# ---------------------------
# Snapshot
# ---------------------------
"""@router.get("/frame/{camera_id}")
def get_detection_snapshot(camera_id: int):
    if detector is None:
        logger.error(MESSAGES["DETECTOR_NOT_INITIALIZED"])
        return Response(MESSAGES["DETECTOR_NOT_INITIALIZED"], status_code=503)
    cfg = get_config()
    if not cfg.is_Camera_Detector:
        logger.info(f"Detection disabled globally (is_Camera_Detector=False)")
        return {"error": "Detection is disabled by configuration"}
    try:
        known = set(detector.get_all_cameras())
        if camera_id not in known:
            db = SessionLocal()
            try:
                cam = db.query(Camera).filter(Camera.id == camera_id).first()
                if not cam:
                    logger.warning(MESSAGES["CAMERA_NOT_FOUND"].format(id=camera_id))
                    return Response(MESSAGES["CAMERA_NOT_FOUND"], status_code=404)

                stream_url = getattr(cam, "stream_url", None) or getattr(cam, "rtsp_url", None)
                if isinstance(stream_url, str) and stream_url.isdigit():
                    stream_url = int(stream_url)

                detector.start_detection(stream_url, camera_id)
                time.sleep(0.5)
                logger.info(MESSAGES["CAMERA_STREAM_STARTED"].format(id=camera_id))
            finally:
                db.close() 

        frame = detector.get_frame(camera_id)
        if frame is None:
            logger.warning(MESSAGES["FRAME_NOT_AVAILABLE"].format(id=camera_id))
            return Response(MESSAGES["FRAME_NOT_AVAILABLE"], status_code=503)

        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            logger.error(MESSAGES["FRAME_ENCODING_FAIL"])
            return Response(MESSAGES["FRAME_ENCODING_FAIL"], status_code=500)

        logger.info(MESSAGES["SNAPSHOT_SUCCESS"].format(id=camera_id))
        return Response(content=buffer.tobytes(), media_type="image/jpeg")
    except Exception as e:
        logger.exception(MESSAGES["SNAPSHOT_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["SNAPSHOT_FAIL"])"""


# ---------------------------
# Camera Status
# ---------------------------
@router.get("/status/{camera_id}")
def camera_status(camera_id: int):
    if detector is None:
        logger.error(MESSAGES["DETECTOR_NOT_INITIALIZED"])
        return {"camera_id": camera_id, "connected": False}

    connected = bool(detector.is_camera_connected(camera_id))
    logger.info(MESSAGES["CAMERA_STATUS_CHECK"].format(id=camera_id, status=connected))
    return {"camera_id": camera_id, "connected": connected}


# ---------------------------
# Stop All Detections
# ---------------------------
@router.post("/stop_all")
def stop_all_detections():
    try:
        detector.stop_all_detections()
        logger.info(MESSAGES["ALL_DETECTIONS_STOPPED"])
        return {"message": MESSAGES["ALL_DETECTIONS_STOPPED"]}
    except Exception as e:
        logger.exception(MESSAGES["STOP_ALL_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["STOP_ALL_FAIL"])
