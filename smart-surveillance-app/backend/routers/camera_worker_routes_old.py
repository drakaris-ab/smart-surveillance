import cv2
import numpy as np
import asyncio
import time
import gc
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import StreamingResponse
from cachetools import TTLCache

from backend.config.router_message import MESSAGES
from backend.config.logging_config import logger
from backend.detection.yolo_detector import detector

router = APIRouter(prefix="/camservice", tags=["CamService"])

frame_cache = TTLCache(maxsize=100, ttl=30)
camera_queues: dict[int, asyncio.Queue] = {}
last_capture_time: dict[int, float] = {}


def encode_frame(frame, quality: int = 65) -> bytes | None:
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    return buffer.tobytes() if ok else None


async def camera_worker(camera_id: int, rtsp_url: str):
    logger.info(f"[CameraWorker] Opening stream for camera {camera_id}: {rtsp_url}")
    gpu_enabled = hasattr(cv2, "cudacodec")
    reader = None
    cap = None
    frame_count = 0

    try:
        # Try GPU decode
        if gpu_enabled:
            try:
                reader = cv2.cudacodec.createVideoReader(rtsp_url)
                logger.info(f"[CameraWorker] Camera {camera_id} using GPU decode")
            except Exception as e:
                logger.warning(f"[CameraWorker] GPU decode failed, falling back to CPU: {e}")
                gpu_enabled = False

        # CPU fallback
        if not gpu_enabled:
            if "?" not in rtsp_url:
                rtsp_url += "?fflags=nobuffer&flags=low_delay&stimeout=5000000"
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not cap.isOpened():
                logger.error(f"[CameraWorker] Camera {camera_id} failed to open")
                return
            logger.info(f"[CameraWorker] Camera {camera_id} using CPU decode")

        camera_queues[camera_id] = asyncio.Queue(maxsize=1)

        while True:
            frame = None
            if gpu_enabled and reader is not None:
                ok, gpu_frame = reader.nextFrame()
                if ok:
                    gpu_resized = cv2.cuda.resize(gpu_frame, (640, 360))
                    frame = gpu_resized.download()
            else:
                ret, raw = cap.read()
                if ret and raw is not None:
                    frame = cv2.resize(raw, (640, 360))

            if frame is None:
                await asyncio.sleep(0.01)
                continue

            frame_cache[camera_id] = frame
            last_capture_time[camera_id] = time.time()

            if camera_queues[camera_id].full():
                camera_queues[camera_id].get_nowait()
            await camera_queues[camera_id].put(frame)

            frame_count += 1
            # 🔹 Run garbage collection every 200 frames
            if frame_count % 200 == 0:
                gc.collect()
                logger.info(f"[GC] Triggered garbage collection (camera={camera_id})")

            await asyncio.sleep(0)  # yield control

    except Exception as e:
        logger.exception(f"[CameraWorker] Fatal error initializing camera {camera_id}: {e}")
    finally:
        if cap:
            cap.release()
        logger.info(f"[CameraWorker] Camera {camera_id} closed")


@router.get("/{camera_id}/stream")
def stream_camera(camera_id: int, mode: str = "processed"):
    async def frame_generator():
        while True:
            try:
                frame = (
                    detector.get_frame(camera_id)
                    if mode == "processed"
                    else (await camera_queues[camera_id].get() if camera_id in camera_queues else frame_cache.get(camera_id))
                )

                if frame is None or not isinstance(frame, np.ndarray):
                    await asyncio.sleep(0.01)
                    continue

                age = time.time() - last_capture_time.get(camera_id, time.time())
                logger.info(f"[Latency] Camera {camera_id} frame age={age:.3f}s")

                encoded = encode_frame(frame)
                if not encoded:
                    await asyncio.sleep(0.01)
                    continue

                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded + b"\r\n"

            except Exception as e:
                logger.exception(f"[Stream] Error streaming camera {camera_id}: {e}")
                break

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")




# -----------------------------------------
# Latest Frame (detector or raw)
# -----------------------------------------
@router.get("/{camera_id}/latest_frame")
def latest_frame(camera_id: int, mode: str = "processed"):
    try:
        frame = (
            detector.get_frame(camera_id)
            if mode == "processed"
            else frame_cache.get(camera_id)
        )
        if frame is None or not isinstance(frame, np.ndarray):
            logger.warning(f"[LatestFrame] No frame available (camera={camera_id}, mode={mode})")
            return Response(MESSAGES["FRAME_NOT_AVAILABLE"], status_code=500)

        encoded = encode_frame(frame)
        if not encoded:
            logger.error(f"[LatestFrame] Encoding failed (camera={camera_id})")
            return Response(MESSAGES["FRAME_ENCODING_FAIL"], status_code=500)

        return Response(content=encoded, media_type="image/jpeg")

    except Exception as e:
        logger.exception(f"[LatestFrame] Unexpected error (camera={camera_id}): {e}")
        raise HTTPException(status_code=500, detail=MESSAGES["FRAME_NOT_AVAILABLE"])


# -----------------------------------------
# Snapshot (raw only)
# -----------------------------------------
@router.get("/{camera_id}/frame")
def get_camera_snapshot(camera_id: int):
    try:
        frame = frame_cache.get(camera_id)
        if frame is None or not isinstance(frame, np.ndarray):
            logger.warning(f"[Snapshot] No raw frame available (camera={camera_id})")
            return Response(MESSAGES["FRAME_NOT_AVAILABLE"], status_code=500)

        encoded = encode_frame(frame)
        if not encoded:
            logger.error(f"[Snapshot] Encoding failed (camera={camera_id})")
            return Response(MESSAGES["FRAME_ENCODING_FAIL"], status_code=500)

        logger.info(f"[Snapshot] Success (camera={camera_id})")
        return Response(content=encoded, media_type="image/jpeg")

    except Exception as e:
        logger.exception(f"[Snapshot] Unexpected error (camera={camera_id}): {e}")
        raise HTTPException(status_code=500, detail=MESSAGES["SNAPSHOT_FAIL"])
