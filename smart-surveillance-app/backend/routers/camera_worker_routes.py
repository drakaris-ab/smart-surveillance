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

# Cache and queues
frame_cache = TTLCache(maxsize=100, ttl=30)
camera_queues: dict[int, asyncio.Queue] = {}
last_capture_time: dict[int, float] = {}

def encode_frame(frame: np.ndarray, quality: int = 65) -> bytes | None:
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    return buffer.tobytes() if ok else None

async def camera_worker(camera_id: int, rtsp_url: str):
    logger.info(f"[CameraWorker] Opening stream for camera {camera_id}: {rtsp_url}")
    gpu_enabled = hasattr(cv2, "cudacodec")
    reader = None
    cap = None
    frame_count = 0

    try:
        # Try GPU decode first
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
            cap = await asyncio.to_thread(cv2.VideoCapture, rtsp_url, cv2.CAP_FFMPEG)
            await asyncio.to_thread(cap.set, cv2.CAP_PROP_BUFFERSIZE, 1)
            if not await asyncio.to_thread(cap.isOpened):
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
                ret, raw = await asyncio.to_thread(cap.read)
                if ret and raw is not None:
                    frame = cv2.resize(raw, (640, 360))

            if frame is None:
                await asyncio.sleep(0.01)
                continue

            frame_cache[camera_id] = frame
            last_capture_time[camera_id] = time.time()

            if camera_queues[camera_id].full():
                try:
                    camera_queues[camera_id].get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await camera_queues[camera_id].put(frame)

            frame_count += 1
            # 🔹 Run garbage collection every 200 frames
            if frame_count % 200 == 0:
                gc.collect()
                try:
                    import torch
                    torch.cuda.empty_cache()
                except Exception:
                    pass
                logger.info(f"[GC] Triggered garbage collection (camera={camera_id})")

            await asyncio.sleep(0)  # yield control

    except Exception as e:
        logger.exception(f"[CameraWorker] Fatal error initializing camera {camera_id}: {e}")
    finally:
        if cap:
            await asyncio.to_thread(cap.release)
        if reader:
            del reader
            try:
                cv2.cuda.resetDevice()
            except Exception:
                pass
        logger.info(f"[CameraWorker] Camera {camera_id} closed")


@router.get("/{camera_id}/stream")
async def stream_camera(camera_id: int, mode: str = "processed"):
    async def frame_generator():
        while True:
            try:
                if mode == "processed":
                    frame = await asyncio.to_thread(detector.get_frame, camera_id)
                else:
                    if camera_id in camera_queues:
                        frame = await camera_queues[camera_id].get()
                    else:
                        frame = frame_cache.get(camera_id)

                if frame is None or not isinstance(frame, np.ndarray):
                    await asyncio.sleep(0.01)
                    continue

                age = time.time() - last_capture_time.get(camera_id, time.time())
                if age > 1.0:
                    logger.warning(f"[Latency-Warning] Camera {camera_id} processing delayed: {age:.2f}s")

                encoded = await asyncio.to_thread(encode_frame, frame)
                if not encoded:
                    await asyncio.sleep(0.01)
                    continue

                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded + b"\r\n"
                await asyncio.sleep(0)

            except Exception as e:
                logger.exception(f"[Stream] Error streaming camera {camera_id}: {e}")
                break

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


"""@router.get("/{camera_id}/latest_frame")
async def latest_frame(camera_id: int, mode: str = "processed"):
    try:
        frame = await asyncio.to_thread(detector.get_frame, camera_id) if mode == "processed" else frame_cache.get(camera_id)
        if frame is None or not isinstance(frame, np.ndarray):
            return Response(MESSAGES["FRAME_NOT_AVAILABLE"], status_code=500)

        encoded = await asyncio.to_thread(encode_frame, frame)
        if not encoded:
            return Response(MESSAGES["FRAME_ENCODING_FAIL"], status_code=500)

        return Response(content=encoded, media_type="image/jpeg")
    except Exception as e:
        logger.exception(f"[LatestFrame] Unexpected error (camera={camera_id}): {e}")
        raise HTTPException(status_code=500, detail=MESSAGES["FRAME_NOT_AVAILABLE"])"""


@router.get("/{camera_id}/frame")
async def get_camera_snapshot(camera_id: int):
    try:
        frame = frame_cache.get(camera_id)
        if frame is None or not isinstance(frame, np.ndarray):
            # fallback to detector
            frame = await asyncio.to_thread(detector.get_frame, camera_id)
            if frame is None:
                return Response(MESSAGES["FRAME_NOT_AVAILABLE"], status_code=500)

        encoded = await asyncio.to_thread(encode_frame, frame)
        if not encoded:
            return Response(MESSAGES["FRAME_ENCODING_FAIL"], status_code=500)

        return Response(content=encoded, media_type="image/jpeg")
    except Exception as e:
        logger.exception(f"[Snapshot] Unexpected error (camera={camera_id}): {e}")
        raise HTTPException(status_code=500, detail=MESSAGES["SNAPSHOT_FAIL"])
