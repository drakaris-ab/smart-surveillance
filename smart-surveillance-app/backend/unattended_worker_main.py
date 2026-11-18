"""
Unattended Object Worker Service - Runs on port 8002
Provides /unattended-object/alerts/{camera_id} endpoint for the main backend to poll
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from pathlib import Path
from contextlib import asynccontextmanager
import threading
import time

# Import your detection logic here
from backend.database.database import SessionLocal, Base, engine
from backend.database.models import Camera
from backend.config.logging_config import logger

# Pydantic models for API responses
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CameraResponse(BaseModel):
    camera_id: int
    name: str
    rtsp_url: str
    location: str
    is_assigned: bool = True  # For frontend compatibility

class StartCameraRequest(BaseModel):
    camera_id: int
    name: str
    rtsp_url: str
    use_frame_sharing: bool = True
    frame_sharing_url: str = ""
    frame_sharing_camera_id: int = 0

class TrackResponse(BaseModel):
    objects: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []
    error: Optional[str] = None

# In-memory state for running cameras (replace with actual detection pipeline)
running_cameras: Dict[int, Dict[str, Any]] = {}
running_cameras_lock = threading.Lock()

# Create tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Unattended Object Worker starting on port 8002...")
    yield
    logger.info("Unattended Object Worker stopped")

app = FastAPI(title="Unattended Object Worker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "unattended-object-worker"}

@app.get("/unattended-object/alerts/{camera_id}")
def get_unattended_alerts(camera_id: int):
    """
    Returns alerts detected by the unattended object detection for a specific camera.
    This is polled by the main backend's sync service.
    """
    # TODO: Implement actual detection logic here
    # For now, return empty alerts - replace with real detection
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            return {"alerts": []}

        # TODO: Replace with actual detection results
        # Example format expected by sync service:
        # return {
        #     "alerts": [
        #         {
        #             "timestamp": "2026-10-30T12:00:00.000Z",
        #             "message": "Unattended bag detected",
        #             "snapshot": "/path/to/snapshot.jpg"
        #         }
        #     ]
        # }
        return {"alerts": []}
    finally:
        db.close()


@app.get("/unattended-object/cameras")
def get_running_cameras():
    """
    Returns list of currently running cameras from the detection pipeline.
    Called by frontend to get running camera state.
    """
    with running_cameras_lock:
        cameras = [
            {
                "camera_id": cam_id,
                "name": data.get("name", f"Camera {cam_id}"),
                "rtsp_url": data.get("rtsp_url", ""),
                "status": "running"
            }
            for cam_id, data in running_cameras.items()
        ]
    return {"cameras": cameras}


@app.post("/unattended-object/cameras/start")
def start_camera(request: StartCameraRequest):
    """
    Start a camera for unattended object tracking.
    Called by frontend when assigning a camera or starting tracking.
    """
    camera_id = request.camera_id
    with running_cameras_lock:
        running_cameras[camera_id] = {
            "name": request.name,
            "rtsp_url": request.rtsp_url,
            "use_frame_sharing": request.use_frame_sharing,
            "frame_sharing_url": request.frame_sharing_url,
            "frame_sharing_camera_id": request.frame_sharing_camera_id,
            "started_at": time.time(),
        }

    # TODO: Actually start the detection pipeline here
    # For now, just mark as running
    logger.info(f"Started camera {camera_id} for unattended object tracking")
    return {"status": "success", "message": f"Camera {camera_id} started"}


@app.post("/unattended-object/cameras/{camera_id}/stop")
def stop_camera(camera_id: int):
    """
    Stop a camera from unattended object tracking.
    Called by frontend when unassigning or stopping tracking.
    """
    with running_cameras_lock:
        if camera_id in running_cameras:
            del running_cameras[camera_id]
            logger.info(f"Stopped camera {camera_id} for unattended object tracking")
            return {"status": "success", "message": f"Camera {camera_id} stopped"}
        else:
            return {"status": "error", "message": f"Camera {camera_id} not running"}


@app.get("/unattended-object/track/{camera_id}")
def get_track_status(camera_id: int):
    """
    Returns tracking status for a specific camera.
    Polled by frontend every 3 seconds for object detection results.
    """
    with running_cameras_lock:
        camera_running = camera_id in running_cameras

    if not camera_running:
        return TrackResponse(
            objects=[],
            alerts=[],
            error="Camera not running"
        ).dict()

    # TODO: Replace with actual detection results from pipeline
    # For now, return mock data structure that frontend expects
    return TrackResponse(
        objects=[],
        alerts=[],
        error=None
    ).dict()


@app.get("/Unwanted_camera")
def get_unwanted_cameras():
    """
    Returns camera configurations for the unattended object module.
    This is called by the frontend to get camera list.
    """
    db = SessionLocal()
    try:
        cameras = db.query(Camera).all()
        return {
            "data": [
                {
                    "camera_id": c.id,
                    "name": c.name,
                    "rtsp_url": c.rtsp_url,
                    "location": c.location,
                    "is_assigned": getattr(c, 'is_assigned', True),  # Default to True if not set
                }
                for c in cameras
            ]
        }
    finally:
        db.close()


@app.post("/Unwanted_camera")
def assign_camera(camera_id: int, user: str):
    """
    Assign a camera to unattended object tracking.
    """
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            return {"status": "error", "message": "Camera not found"}

        # Update camera assignment
        camera.is_assigned = True
        db.commit()
        return {"status": "success", "message": "Camera assigned for unattended object tracking"}
    except Exception as e:
        logger.error(f"Error assigning camera: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@app.delete("/Unwanted_camera/{camera_id}")
def unassign_camera(camera_id: int, user: str):
    """
    Unassign a camera from unattended object tracking.
    """
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            return {"status": "error", "message": "Camera not found"}

        # Update camera assignment
        camera.is_assigned = False
        db.commit()
        return {"status": "success", "message": "Camera unassigned from unattended object tracking"}
    except Exception as e:
        logger.error(f"Error unassigning camera: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")