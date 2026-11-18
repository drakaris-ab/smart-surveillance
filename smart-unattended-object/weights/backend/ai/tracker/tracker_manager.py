"""
tracker_manager.py

Persistent object IDs, on Ultralytics' own BoT-SORT.

**Why the previous tracker could never run.**  It imported
``boxmot.trackers.bbox.botsort``. ``boxmot`` is not installed and was never
listed in ``requirements.txt``, so constructing a ``DetectionService`` raised
``ModuleNotFoundError`` and the camera thread reported "Detection worker could
not start". The tracker's own docstring described working around a broken ReID
path in that package -- but the package was not there at all.

Ultralytics 8.4 ships a maintained BoT-SORT with the same two features that
matter for this problem, so the dependency is simply removed:

*Global motion compensation* estimates frame-to-frame camera movement and
subtracts it before association. Without it, a camera nudged by wind produces a
translation the Kalman filter reads as every object accelerating at once, and
IDs scatter.

*Appearance ReID* is what recovers an identity through a full occlusion. It
matters here more than in generic tracking: when someone walks between the
camera and an abandoned bag, motion-only association gives the bag a new ID on
the far side, and a new ID means a fresh dwell timer -- an object could stay
abandoned indefinitely without ever triggering, because the clock keeps
restarting. ReID lets the bag keep its identity and its clock.

**Frames, not seconds, is the unit BoT-SORT thinks in**, and that is a trap here.
``track_buffer`` is how many frames a lost track survives, and the Kalman filter
assumes a constant interval between updates. This pipeline does not run at a
fixed rate -- tiling makes it vary with scene content. So the measured frame
rate is fed back in: ``track_buffer`` is recomputed from a duration in seconds,
which is what an operator actually reasons about ("survive three seconds of
occlusion"), rather than a frame count that silently means different things on
different hardware.

**One tracker per camera, one encoder for all of them.**  Track ids only mean
something within a scene, so each camera needs its own tracker. The ReID encoder
is the opposite: it maps a crop to a feature vector and keeps nothing between
calls, so it is shared. That distinction is worth making explicitly because
BOTSORT loads an encoder in its own constructor, which meant four cameras loaded
four copies of identical weights -- VRAM and startup time growing with camera
count for no benefit at all.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, Optional, Tuple

import numpy as np

from backend.core.config import settings
from backend.core.logging import get_logger, throttled
from backend.core.runtime import get_profile
from backend.ai.detector.model_loader import WEIGHTS_DIR
from backend.ai.detector.yolo_detector import RawDetections

log = get_logger("tracker")


@dataclass
class TrackedDetections:
    """Detections that have been assigned persistent ids."""

    xyxy: np.ndarray        # (N, 4) float32, full-frame
    confidence: np.ndarray  # (N,)   float32
    class_id: np.ndarray    # (N,)   int32
    tracker_id: np.ndarray  # (N,)   int32

    @staticmethod
    def empty() -> "TrackedDetections":
        return TrackedDetections(
            np.zeros((0, 4), np.float32), np.zeros((0,), np.float32),
            np.zeros((0,), np.int32), np.zeros((0,), np.int32),
        )

    def __len__(self) -> int:
        return int(self.xyxy.shape[0])


class _Results:
    """Adapter presenting ``RawDetections`` the way BoT-SORT expects.

    The tracker wants a Results-like object exposing ``xywh``, ``conf`` and
    ``cls``, sliceable by a boolean mask -- it splits detections into high and
    low confidence bands internally. Adapting here is deliberate: it keeps the
    detector free of tracker-specific shapes, so either side can be swapped
    without touching the other.
    """

    __slots__ = ("xywh", "conf", "cls")

    def __init__(self, xywh: np.ndarray, conf: np.ndarray, cls: np.ndarray):
        self.xywh = xywh
        self.conf = conf
        self.cls = cls

    @classmethod
    def from_raw(cls, det: RawDetections) -> "_Results":
        boxes = det.xyxy.astype(np.float32)
        widths = boxes[:, 2] - boxes[:, 0]
        heights = boxes[:, 3] - boxes[:, 1]
        xywh = np.stack([
            boxes[:, 0] + widths / 2.0,
            boxes[:, 1] + heights / 2.0,
            widths,
            heights,
        ], axis=1)
        return cls(xywh, det.confidence.astype(np.float32), det.class_id.astype(np.float32))

    def __len__(self) -> int:
        return int(self.xywh.shape[0])

    def __getitem__(self, mask) -> "_Results":
        return _Results(self.xywh[mask], self.conf[mask], self.cls[mask])


def _resolve_reid_model() -> Optional[str]:
    """Pick a ReID encoder, preferring something already on disk.

    ``model="auto"`` is not usable from here: it expects backbone features
    handed in alongside the detections, which only the built-in ``model.track()``
    path produces. Driving the tracker directly with sliced detections means an
    explicit encoder is required.
    """
    configured = settings.reid_model.strip()
    if configured.lower() in {"", "none", "off"}:
        return None

    candidate = WEIGHTS_DIR / configured
    if candidate.exists():
        return str(candidate)
    # A bare asset name (e.g. yolo26n-reid.onnx) is fetched by ultralytics on
    # first use; a path that does not resolve is a configuration error.
    if "/" in configured or "\\" in configured:
        log.warning("ReID model %s not found; tracking will use motion only", configured)
        return None
    return configured


# One ReID encoder per (weights, device), shared by every camera.
#
# BOTSORT builds its own encoder in its constructor, and there is one BOTSORT per
# camera, so four cameras loaded four copies of the same network: four lots of
# VRAM and four lots of load time for identical weights. Nothing about the
# encoder is per-camera -- it maps a crop to a feature vector and holds no state
# between calls -- so the copies were pure duplication.
_encoders: Dict[Tuple[str, str], "_SharedEncoder"] = {}
_encoders_lock = threading.Lock()


class _SharedEncoder:
    """Serialises calls into one encoder shared by several camera threads.

    The lock is here for the same reason the detector has one: the underlying
    torch or ONNX session keeps per-call buffers, and two threads calling it at
    once corrupt each other's results rather than running twice as fast. Nothing
    is lost by serialising, because the device executes one of these at a time
    regardless.
    """

    def __init__(self, encoder: Any) -> None:
        self._encoder = encoder
        self._lock = threading.Lock()

    def __call__(self, image, boxes):
        with self._lock:
            return self._encoder(image, boxes)


def encoder_count() -> int:
    """How many distinct ReID encoders are loaded, regardless of camera count."""
    with _encoders_lock:
        return len(_encoders)


def reid_status() -> Dict[str, Any]:
    """Whether appearance ReID can actually run, and why not if it cannot.

    This is reported by ``/health`` because the failure is otherwise invisible in
    exactly the way that matters most here. The default encoder is an ``.onnx``
    asset, so it needs an ONNX runtime installed; when that is missing the
    tracker logs one warning at camera start and then runs motion-only
    association for the rest of the process's life. Motion-only association
    gives an abandoned bag a *new id* once someone walks in front of it, and a
    new id starts a fresh dwell timer -- so the bag can sit unattended
    indefinitely and never be reported. A silent warning is too quiet for a
    failure that disables the feature the system exists to provide.

    Answerable before any camera starts, which is the point: it does not depend
    on an encoder having been loaded.
    """
    import importlib.util

    requested = bool(settings.track_with_reid)
    model = _resolve_reid_model() if requested else None
    profile = get_profile()
    device_ok = profile.is_cuda or settings.reid_force_cpu
    # onnxruntime-gpu installs under the same module name, so one check covers
    # both wheels. A .pt encoder needs torch only, which is always present.
    needs_onnx = bool(model) and str(model).lower().endswith(".onnx")
    onnx_ok = importlib.util.find_spec("onnxruntime") is not None

    if not requested:
        reason = "disabled by configuration (UOD_REID=0)"
    elif not device_ok:
        reason = "CPU device -- set UOD_REID_FORCE_CPU=1 to run it anyway"
    elif not model:
        reason = "no encoder resolved from UOD_REID_MODEL"
    elif needs_onnx and not onnx_ok:
        reason = (
            "onnxruntime is not installed, so the .onnx encoder cannot load -- "
            "install requirements-gpu.txt (onnxruntime-gpu) or point "
            "UOD_REID_MODEL at a .pt encoder such as yolo26n.pt"
        )
    else:
        reason = None

    return {
        "requested": requested,
        "model": model,
        "onnxruntime_installed": onnx_ok,
        "encoders_loaded": encoder_count(),
        "usable": reason is None,
        "reason": reason,
    }


def shared_encoder(model: str, device: Optional[str]) -> "_SharedEncoder":
    """Return the shared encoder for these weights, loading it once."""
    key = (str(model), str(device))
    with _encoders_lock:
        existing = _encoders.get(key)
        if existing is not None:
            return existing
    # Built outside the lock: loading weights takes seconds, and holding the lock
    # across it would stall every other camera's startup.
    from ultralytics.trackers.utils.reid import build_encoder

    built = _SharedEncoder(build_encoder(True, model, device))
    with _encoders_lock:
        # Another camera may have won the race; use its instance so there is
        # still exactly one.
        return _encoders.setdefault(key, built)


class TrackerManager:
    """One BoT-SORT instance per camera. Not shared -- IDs are per-scene."""

    def __init__(self, camera_id: int = 0, frame_rate: float = 15.0) -> None:
        self.camera_id = camera_id
        self.frame_rate = max(1.0, float(frame_rate))
        profile = get_profile()

        # ReID runs a second network over every detection crop, every frame.
        # That is affordable on a GPU and ruinous on CPU, where it can cost more
        # than the detector itself, so it is gated on having one.
        wants_reid = settings.track_with_reid and (profile.is_cuda or settings.reid_force_cpu)
        reid_model = _resolve_reid_model() if wants_reid else None
        self.with_reid = bool(reid_model)

        if settings.track_with_reid and not self.with_reid:
            log.info(
                "cam=%d ReID disabled (%s); association is motion + IoU only, so "
                "ids may not survive a long occlusion",
                camera_id,
                "no encoder available" if profile.is_cuda else "CPU device -- set UOD_REID_FORCE_CPU=1 to override",
            )

        self.args = SimpleNamespace(
            tracker_type="botsort",
            track_high_thresh=settings.track_high_thresh,
            track_low_thresh=settings.track_low_thresh,
            new_track_thresh=settings.new_track_thresh,
            track_buffer=self._buffer_frames(),
            match_thresh=settings.match_thresh,
            fuse_score=True,
            gmc_method=settings.gmc_method,
            proximity_thresh=settings.reid_proximity_thresh,
            appearance_thresh=settings.reid_appearance_thresh,
            with_reid=self.with_reid,
            model=reid_model or "auto",
            device=profile.device,
        )

        self.tracker = self._build()
        log.info(
            "cam=%d BoT-SORT ready: gmc=%s, reid=%s, buffer=%d frames (%.1fs at %.1f fps)",
            camera_id, settings.gmc_method,
            reid_model if self.with_reid else "off",
            self.args.track_buffer, settings.track_buffer_seconds, self.frame_rate,
        )

    def _build(self):
        """Construct the tracker, attaching the shared ReID encoder.

        BOTSORT loads an encoder in its own constructor, so it is built here with
        ReID switched off and the shared encoder assigned afterwards. That is
        safe because BOTSORT reads ``args.with_reid`` live on every frame and
        never caches it, so restoring the flag after construction turns ReID on
        for a tracker that never loaded weights of its own.
        """
        from ultralytics.trackers.bot_sort import BOTSORT

        if not self.args.with_reid:
            return BOTSORT(self.args)

        try:
            encoder = shared_encoder(self.args.model, self.args.device)
        except Exception as exc:
            log.warning(
                "cam=%d could not initialise the ReID encoder (%s); "
                "continuing with motion-only association",
                self.camera_id, exc,
            )
            self.args.with_reid = False
            self.args.model = "auto"
            self.with_reid = False
            return BOTSORT(self.args)

        self.args.with_reid = False
        try:
            tracker = BOTSORT(self.args)
        finally:
            self.args.with_reid = True
        tracker.encoder = encoder
        return tracker

    def _buffer_frames(self) -> int:
        return max(5, int(round(settings.track_buffer_seconds * self.frame_rate)))

    def set_frame_rate(self, frame_rate: float) -> None:
        """Re-derive the lost-track buffer from the measured rate.

        Applied to the live tracker rather than by rebuilding it -- rebuilding
        would discard every existing track and reset every dwell timer.
        """
        frame_rate = max(1.0, float(frame_rate))
        if abs(frame_rate - self.frame_rate) / self.frame_rate < 0.2:
            return  # ignore small drift; only react to a real change of regime
        self.frame_rate = frame_rate
        frames = self._buffer_frames()
        self.args.track_buffer = frames
        self.tracker.max_frames_lost = frames
        log.debug(
            "cam=%d frame rate now %.1f fps; lost-track buffer = %d frames",
            self.camera_id, frame_rate, frames,
        )

    def apply_tuning(self) -> None:
        """Adopt changed thresholds without rebuilding the tracker.

        Two kinds of value here. The association thresholds are read out of
        ``self.args`` on every update, and BOTSORT holds the same namespace
        object we do, so writing them is enough. The buffer length and the ReID
        gates were copied onto the tracker in its constructor, so those are set
        on the tracker as well -- writing only ``args`` would look like it worked
        and change nothing.

        Deliberately no rebuild: a new tracker starts its id namespace from
        scratch, which would discard every dwell timer and ownership binding.
        Tuning a threshold to catch a bag must not throw away the evidence about
        the bag.
        """
        self.args.track_high_thresh = settings.track_high_thresh
        self.args.track_low_thresh = settings.track_low_thresh
        self.args.new_track_thresh = settings.new_track_thresh
        self.args.match_thresh = settings.match_thresh
        self.args.proximity_thresh = settings.reid_proximity_thresh
        self.args.appearance_thresh = settings.reid_appearance_thresh

        frames = self._buffer_frames()
        self.args.track_buffer = frames
        tracker = self.tracker
        tracker.max_frames_lost = frames
        # Present only on the ReID path; setattr unconditionally is wrong if the
        # attribute does not exist, so mirror only what the constructor copied.
        if hasattr(tracker, "proximity_thresh"):
            tracker.proximity_thresh = settings.reid_proximity_thresh
        if hasattr(tracker, "appearance_thresh"):
            tracker.appearance_thresh = settings.reid_appearance_thresh

    def update(self, detections: RawDetections, frame: Optional[np.ndarray] = None) -> TrackedDetections:
        """Advance the tracker by exactly one frame.

        Must be called once per processed frame *including frames with nothing
        in them*. Skipping the empty ones would freeze the internal frame
        counter, so lost tracks would never age out and motion prediction would
        extrapolate across a gap it does not know occurred.
        """
        if detections is None:
            detections = RawDetections.empty()

        try:
            rows = self.tracker.update(_Results.from_raw(detections), frame)
        except Exception as exc:
            throttled(
                log, f"track-{self.camera_id}", 40,
                "cam=%d tracker update failed: %s", self.camera_id, exc,
                interval=15.0,
            )
            return TrackedDetections.empty()

        rows = np.asarray(rows, dtype=np.float32)
        if rows.size == 0:
            return TrackedDetections.empty()

        # Rows are [x1, y1, x2, y2, track_id, score, cls, det_index].
        return TrackedDetections(
            xyxy=rows[:, 0:4].astype(np.float32),
            confidence=rows[:, 5].astype(np.float32),
            class_id=rows[:, 6].astype(np.int32),
            tracker_id=rows[:, 4].astype(np.int32),
        )

    def reset(self) -> None:
        self.tracker.reset()
