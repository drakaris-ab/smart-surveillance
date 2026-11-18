"""
routes.py

The worker's HTTP surface. Four endpoints do the real work and the shape of each
one is a response to something the previous version got wrong.

**``/stream`` no longer re-sends frames it has already sent.**  The old generator
slept 50ms and yielded whatever was in the buffer, so a camera analysed at 4fps
produced a 20fps stream of which three quarters were byte-identical duplicates.
It now blocks until a genuinely new frame exists, which removes the duplicate
traffic and, more usefully, removes the fixed 50ms of latency that a poll loop
adds even when a frame is ready immediately.

**``/frame`` exists so boxes can be drawn accurately.**  An MJPEG stream in an
``<img>`` tag cannot tell the page which frame it is currently showing -- browsers
expose no per-part metadata -- so a canvas overlay fed by separate polling always
draws boxes from one moment over pixels from another. Every object then looks
displaced in the direction it is moving, which reads as detector inaccuracy and
was a large part of the reported "bounding box inaccuracy". This endpoint returns
the analysed frame *and* the boxes measured from it as one object, long-polling
until the next one exists. There is nothing to align because they were never
separated.

**Errors are reported, not implied.**  A camera that is running but failing now
returns its latched error alongside the empty object list, so the UI can say what
is wrong instead of showing a healthy camera that never detects anything.
"""

from __future__ import annotations

import base64
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from backend.core.config import settings
from backend.core.runtime import get_profile, vram_snapshot
from backend.core import tuning
from backend.ai.detector import model_loader
from backend.ai.tracker import tracker_manager
from backend.services import pipeline_runner, tracking_state

router = APIRouter(prefix="/unattended-object",tags=["Unattended object"])

_BOUNDARY = "frame"
# Long-poll ceiling. Long enough that an idle camera does not generate constant
# request churn, short enough to stay well inside any proxy's read timeout.
_POLL_TIMEOUT = 10.0


class CameraStart(BaseModel):
    camera_id: int = Field(..., gt=0, description="Stable identifier for this camera")
    name: str = Field(..., min_length=1, max_length=120)
    # A device index ("0"), a file path, or an rtsp/http URL. Blank means the
    # default local camera, which is what a bare install has to test with.
    rtsp_url: Optional[str] = Field(default=None, max_length=2048)
    # An MJPEG endpoint read frame-by-frame instead of opened by OpenCV. Kept
    # separate because it takes a different read path, not because it is a
    # different kind of URL.
    frame_url: Optional[str] = Field(default=None, max_length=2048)
    # Frame sharing configuration
    use_frame_sharing: bool = Field(default=False, description="Fetch frames via HTTP from smart-surveillance-app instead of direct camera access")
    frame_sharing_url: Optional[str] = Field(default=None, max_length=2048, description="Base URL of smart-surveillance-app (e.g., http://localhost:8000)")
    frame_sharing_camera_id: Optional[int] = Field(default=None, gt=0, description="Camera ID to fetch from smart-surveillance-app (defaults to local camera_id)")

    @field_validator("frame_url")
    @classmethod
    def _http_only(cls, value: Optional[str]) -> Optional[str]:
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("frame_url must be an http(s) URL")
        return value


def _require_running(camera_id: int) -> None:
    """404 rather than an empty stream when a camera was never started.

    A silent empty response here is indistinguishable from a camera that is
    running but seeing nothing, which is exactly the ambiguity the error
    latching elsewhere exists to remove.
    """
    if not pipeline_runner.is_running(camera_id):
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} is not running")


@router.get("/health")
def health() -> dict:
    """Liveness plus the two facts that explain a slow deployment.

    ``device`` and ``torch_cuda_build`` are here deliberately: a CPU-only
    PyTorch wheel is the most common cause of "why is this machine slower", and
    it is invisible from the outside unless something reports it.

    ``reid`` is here for the same reason applied to correctness rather than
    speed. Appearance ReID is what lets an abandoned bag keep its identity --
    and therefore its dwell timer -- while someone walks in front of it, and it
    switches itself off with a single log warning if its runtime is missing.
    ``reid.usable`` false means bags will be missed, so it belongs in the
    endpoint people actually check.
    """
    return {
        "status": "ok",
        "model": settings.model_name,
        "runtime": get_profile().as_dict(),
        "reid": tracker_manager.reid_status(),
        "running_cameras": pipeline_runner.running_cameras(),
    }


# -- camera lifecycle ---------------------------------------------------------


@router.post("/cameras/start")
def start_camera(payload: CameraStart) -> dict:
    started = pipeline_runner.start_camera(
        camera_id=payload.camera_id,
        camera_name=payload.name,
        stream_url=payload.rtsp_url,
        frame_url=payload.frame_url,
        use_frame_sharing=payload.use_frame_sharing,
        frame_sharing_url=payload.frame_sharing_url,
        frame_sharing_camera_id=payload.frame_sharing_camera_id,
    )
    # Starting a camera that is already running is not an error -- a UI that
    # re-sends on reconnect would otherwise show a failure for a healthy camera.
    return {
        "camera_id": payload.camera_id,
        "started": started,
        "already_running": not started,
    }


@router.post("/cameras/{camera_id}/stop")
def stop_camera(camera_id: int) -> dict:
    stopped = pipeline_runner.stop_camera(camera_id)
    return {"camera_id": camera_id, "stopped": stopped}


@router.get("/cameras")
def list_cameras() -> dict:
    """What is running, with just enough state to render a camera list."""
    cameras = []
    for camera_id in pipeline_runner.running_cameras():
        state = tracking_state.snapshot(camera_id)
        cameras.append(
            {
                "camera_id": camera_id,
                "processing": state["processing"],
                "error": state["error"],
                "objects": len(state["objects"]),
                "alerts": len(state["alerts"]),
                "seq": state["seq"],
                "frame_width": state["frame_width"],
                "frame_height": state["frame_height"],
            }
        )
    return {"cameras": cameras, "count": len(cameras)}


# -- results ------------------------------------------------------------------


@router.get("/track/{camera_id}")
def track(camera_id: int) -> dict:
    """Everything known about one camera, from a single consistent snapshot.

    Objects, alerts and the frame they were measured from are read under one
    lock, so the boxes in a response always belong to the ``seq`` in the same
    response. This is the endpoint the existing frontend polls, so its keys are
    kept; ``seq`` and the frame dimensions are additions, not replacements.
    """
    state = tracking_state.snapshot(camera_id)
    state["running"] = pipeline_runner.is_running(camera_id)
    return state


@router.get("/detections/{camera_id}")
def detections(camera_id: int) -> dict:
    """The lean payload an overlay needs, and nothing else.

    Boxes are in source-frame pixels and the frame's own dimensions travel with
    them, because the browser scales to whatever size the video element ended up
    being. Sending normalised coordinates instead would lose precision for no
    benefit, and sending boxes without their reference dimensions is how an
    overlay silently ends up mis-scaled on any non-default layout.
    """
    state = tracking_state.snapshot(camera_id)
    return {
        "camera_id": camera_id,
        "seq": state["seq"],
        "frame_width": state["frame_width"],
        "frame_height": state["frame_height"],
        "objects": state["objects"],
        "alerts": state["alerts"],
        "processing": state["processing"],
        "error": state["error"],
        "updated_at": state["updated_at"],
    }


@router.get("/alerts/{camera_id}")
def alerts(camera_id: int) -> dict:
    return {"camera_id": camera_id, "alerts": tracking_state.get_alerts(camera_id)}


# -- video --------------------------------------------------------------------


def _mjpeg_generator(camera_id: int):
    """Yield each frame exactly once.

    The generator blocks on the frame bus rather than polling it. The old
    version slept 50ms and re-sent whatever was in the buffer, so every frame
    was transmitted several times over -- bandwidth and CPU spent on bytes the
    browser already had, plus up to 50ms of latency added to frames that were
    ready the moment they were asked for.

    Subscribing tells the pipeline somebody is watching. With no subscriber it
    skips JPEG encoding altogether, which on a headless deployment is the second
    largest cost in the pipeline reduced to nothing.
    """
    tracking_state.preview_subscribe(camera_id)
    last_seq = -1
    try:
        while True:
            item = tracking_state.wait_for_frame(camera_id, last_seq, timeout=1.0)
            if item is None:
                # A timeout is the only chance to notice the camera stopped:
                # a wait with no deadline would hang until the client gave up.
                if not pipeline_runner.is_running(camera_id):
                    return
                continue
            jpeg, last_seq = item
            yield (
                b"--" + _BOUNDARY.encode() + b"\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"X-Frame-Seq: " + str(last_seq).encode() + b"\r\n"
                b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                + jpeg + b"\r\n"
            )
    finally:
        # Runs on client disconnect too, since Starlette closes the generator.
        tracking_state.preview_unsubscribe(camera_id)


@router.get("/stream/{camera_id}")
def stream(camera_id: int) -> StreamingResponse:
    _require_running(camera_id)
    return StreamingResponse(
        _mjpeg_generator(camera_id),
        media_type=f"multipart/x-mixed-replace; boundary={_BOUNDARY}",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/frame/{camera_id}")
def frame(
    camera_id: int,
    after: int = Query(default=-1, description="Last frame sequence already rendered"),
) -> dict:
    """One analysed frame together with the boxes measured from *that* frame.

    This is the endpoint that fixes bounding box accuracy as seen by a user.
    Browsers expose no per-part metadata for an MJPEG stream, so a page showing
    ``/stream`` genuinely cannot know which frame is on screen; boxes polled
    separately are therefore always from a different moment than the pixels they
    are drawn over, and every moving object looks offset in its direction of
    travel. Handing the JPEG and its boxes over as one object removes the
    alignment problem rather than reducing it -- there is nothing left to align.

    It long-polls: the response arrives the instant a newer frame exists, and
    after ``_POLL_TIMEOUT`` of nothing it returns ``changed: false`` so the
    client can loop again without a stalled request.
    """
    _require_running(camera_id)
    tracking_state.synced_subscribe(camera_id)
    try:
        item = tracking_state.wait_for_synced(camera_id, after, timeout=_POLL_TIMEOUT)
    finally:
        tracking_state.synced_unsubscribe(camera_id)

    if item is None:
        state = tracking_state.snapshot(camera_id)
        return {
            "camera_id": camera_id,
            "changed": False,
            "seq": after,
            "error": state["error"],
            "processing": state["processing"],
        }

    payload, seq = item
    state = tracking_state.snapshot(camera_id)
    return {
        "camera_id": camera_id,
        "changed": True,
        "seq": seq,
        "frame_width": payload["width"],
        "frame_height": payload["height"],
        # Inline rather than a second request for the image: a separate fetch
        # would reintroduce the very split this endpoint exists to close.
        "image": "data:image/jpeg;base64," + base64.b64encode(payload["jpeg"]).decode("ascii"),
        "objects": payload["objects"],
        "alerts": state["alerts"],
        "error": state["error"],
        "processing": state["processing"],
    }


@router.get("/snapshot/{camera_id}")
def snapshot_image(camera_id: int) -> Response:
    """The most recent preview frame as a plain JPEG.

    Subscribes for the duration of the request so a camera nobody is streaming
    still produces something here, instead of returning 503 because encoding was
    skipped for want of an audience.
    """
    _require_running(camera_id)
    tracking_state.preview_subscribe(camera_id)
    try:
        item = tracking_state.wait_for_frame(camera_id, -1, timeout=2.0)
    finally:
        tracking_state.preview_unsubscribe(camera_id)
    if item is None:
        raise HTTPException(status_code=503, detail="No frame available yet")
    return Response(content=item[0], media_type="image/jpeg",
                    headers={"Cache-Control": "no-store", "X-Frame-Seq": str(item[1])})


# -- diagnostics --------------------------------------------------------------


@router.get("/system/performance")
def performance() -> dict:
    """Where the time goes, per camera.

    ``inference_share_of_cycle`` is the number worth reading first. Near 1.0
    means the cycle is inference and the GPU is the constraint, so a smaller
    model or fewer tiles is the lever. Well below it means most of the cycle is
    spent elsewhere -- decoding, colour conversion, JPEG encoding -- and a faster
    GPU would change nothing. Without it, "slow" is indistinguishable between
    those two cases, and they have opposite fixes.
    """
    cameras = []
    for stats in pipeline_runner.worker_stats():
        camera_id = stats.get("camera_id")
        if camera_id is not None:
            # The rolling window the summary logger already computes, rather
            # than a second set of counters that could disagree with the logs.
            stats = {**stats, "metrics": tracking_state.get_metrics(camera_id)}
        cameras.append(stats)

    return {
        "runtime": get_profile().as_dict(),
        "vram": vram_snapshot(),
        # What is loaded once versus per camera. This is the answer to "does
        # adding a camera cost me another copy of the model": both the detector
        # and the ReID encoder are counted here, and both should stay at one
        # however many cameras are running.
        "shared": {
            "detector_instances": model_loader.loaded_count(),
            "reid_encoders": tracker_manager.encoder_count(),
            "cameras": len(pipeline_runner.running_cameras()),
        },
        "settings": {
            "model": settings.model_name,
            "inference_size": settings.inference_size,
            "target_fps": settings.target_fps,
            "detect_every": settings.detect_every,
            "sahi_enabled": settings.sahi_enabled,
            "sahi_slice": settings.sahi_slice,
            "sahi_motion_gate": settings.sahi_motion_gate,
            "track_with_reid": settings.track_with_reid,
            "stream_max_width": settings.stream_max_width,
            "jpeg_quality": settings.jpeg_quality,
        },
        "cameras": cameras,
    }


@router.get("/system/performance/{camera_id}")
def performance_for(camera_id: int) -> dict:
    stats = pipeline_runner.worker_stats(camera_id)
    if not stats:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} is not running")
    return {"camera": stats, "metrics": tracking_state.get_metrics(camera_id)}


# ---------------------------------------------------------------------------
# Live tuning
# ---------------------------------------------------------------------------
# Deliberately no per-camera variant. These are the parameters that decide what
# the model sees, and tuning one camera differently from another would mean two
# cameras disagreeing about what counts as a detection -- which makes the panel
# useless as a diagnostic, because you could no longer tell whether a change or
# the scene explained the difference.


class TuningPatch(BaseModel):
    """Field name -> new value, for any subset of the advertised parameters.

    Free-form on purpose: the schema lives in one place (``core.tuning``) and is
    served by the GET, so duplicating it as pydantic fields would create a second
    copy to keep in agreement.
    """

    values: dict = Field(default_factory=dict)


@router.get("/tuning")
def get_tuning() -> dict:
    """Schema, current values, defaults and bounds -- everything the panel needs."""
    return tuning.snapshot()


@router.patch("/tuning")
def patch_tuning(payload: TuningPatch) -> dict:
    """Apply a subset of parameters, reporting per-field success or failure.

    200 even when some fields are rejected: the accepted ones did take effect,
    and an error status would tell the panel to discard a response that contains
    the reason. Only a request in which *nothing* was recognised is a 400.
    """
    if not payload.values:
        raise HTTPException(status_code=400, detail="No values supplied")
    result = tuning.apply(payload.values)
    if not result["applied"] and result["rejected"]:
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/tuning/reset")
def reset_tuning() -> dict:
    """Return every adjustable parameter to its startup value."""
    return tuning.reset()
