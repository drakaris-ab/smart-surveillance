"""HTTP API for the standalone unattended-object worker."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services import pipeline_runner, tracking_state

router = APIRouter(tags=["Unattended object"])


class CameraStart(BaseModel):
    camera_id: int = Field(gt=0)
    name: str = "Camera"
    rtsp_url: str | None = None
    # Frame sharing configuration
    use_frame_sharing: bool = Field(default=False, description="Fetch frames via HTTP from smart-surveillance-app instead of direct camera access")
    frame_sharing_url: str | None = Field(default=None, description="Base URL of smart-surveillance-app (e.g., http://localhost:8000)")
    frame_sharing_camera_id: int | None = Field(default=None, description="Camera ID to fetch from smart-surveillance-app (defaults to local camera_id)")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/cameras/start")
def start_camera(camera: CameraStart):
    started = pipeline_runner.start_camera(
        camera_id=camera.camera_id,
        camera_name=camera.name,
        stream_url=camera.rtsp_url,
        use_frame_sharing=camera.use_frame_sharing,
        frame_sharing_url=camera.frame_sharing_url,
        frame_sharing_camera_id=camera.frame_sharing_camera_id,
    )
    return {"status": "started" if started else "already_running", "camera_id": camera.camera_id}


@router.post("/cameras/{camera_id}/stop")
def stop_camera(camera_id: int):
    if not pipeline_runner.stop_camera(camera_id):
        raise HTTPException(status_code=404, detail="Camera is not processing")
    return {"status": "stopping", "camera_id": camera_id}


@router.get("/track/{camera_id}")
def track(camera_id: int):
    return tracking_state.snapshot(camera_id)
