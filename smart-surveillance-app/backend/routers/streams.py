# app/routers/streams.py
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import StreamingResponse
import time

try:
    import cv2
except Exception:  # optional dependency fallback
    cv2 = None

from backend.detection import detector
from backend.database import SessionLocal, models
from backend.config.logging_config import logger
from backend.config.router_message import MESSAGES
from backend.routers.cameras_routes import camera_cache

router = APIRouter(prefix="/streams", tags=["Streams"])
STREAM_FPS = 20
STREAM_FRAME_INTERVAL = 1.0 / STREAM_FPS


def mjpeg_generator(camera_id: int):
    if detector is None or cv2 is None:
        logger.error(MESSAGES["STREAM_INIT_FAIL"])
        return

    # wait for first frame
    t0 = time.time()
    while True:
        frame = detector.get_frame(camera_id)
        if frame is not None:
            break
        if time.time() - t0 > 5:
            logger.warning(MESSAGES["FRAME_TIMEOUT"].format(id=camera_id))
            return
        time.sleep(0.05)

    while True:
        frame = detector.get_frame(camera_id)
        if frame is None:
            time.sleep(0.05)
            continue
        ok, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            logger.warning(MESSAGES["FRAME_ENCODING_FAIL"])
            time.sleep(0.01)
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
        )
        time.sleep(STREAM_FRAME_INTERVAL)

@router.get("/live/{camera_id}")
def stream_camera(camera_id: int):
    db = SessionLocal()
    try:
        # 🔹 Try cache first
        cam = camera_cache.get(f"camera:{camera_id}")
        if not cam:
            db_cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
            if not db_cam:
                logger.warning(MESSAGES["CAMERA_NOT_FOUND"].format(id=camera_id))
                return Response(MESSAGES["CAMERA_NOT_FOUND"], status_code=404)

            cam = {"id": db_cam.id, "rtsp_url": db_cam.rtsp_url, "name": db_cam.name}
            camera_cache.set(f"camera:{camera_id}", cam)

        stream_url = cam["rtsp_url"]
        if not stream_url:
            logger.warning(MESSAGES["STREAM_URL_NOT_CONFIGURED"].format(id=camera_id))
            return Response(MESSAGES["STREAM_URL_NOT_CONFIGURED"], status_code=400)

        # normalize "0" -> int webcam index
        if isinstance(stream_url, str) and stream_url.isdigit():
            stream_url = int(stream_url)

        # start detection if not already running
        running_ids = detector.get_all_cameras()
        if camera_id not in running_ids:
            logger.info(MESSAGES["STREAM_START"].format(id=camera_id, url=stream_url))
            detector.start_detection(stream_url, camera_id)

        logger.info(MESSAGES["STREAM_SUCCESS"].format(id=camera_id))
        return StreamingResponse(
            mjpeg_generator(camera_id),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        logger.exception(MESSAGES["STREAM_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["STREAM_FAIL"])
    finally:
        db.close()
