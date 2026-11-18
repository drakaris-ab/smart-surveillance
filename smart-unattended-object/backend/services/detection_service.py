"""
detection_service.py

Per-camera orchestration: pixels in, analysed objects and alerts out. It owns no
algorithms of its own -- every decision lives in the detector, the tracker or the
analyzer chain -- and its whole job is to call them in the right order with the
right data.

**What it replaces.**  The previous version was 500 lines that duplicated the
class lists and confidence thresholds from the config, carried its own SAHI
implementation, merged tiles with NMS on IoU, filtered classes *after* tracking
(so all eighty COCO classes were tiled, tracked and label-smoothed before being
thrown away), and printed several blocks of text per frame per camera. At 12fps
on four cameras that is around two hundred lines of console output a second,
which is slow enough to become the bottleneck itself.

**The pacing decision that matters.**  Detection is not skipped on some frames
and run on others inside this class. The tracker's Kalman filter assumes a
constant interval between updates, so every call to :meth:`process` is exactly
one tracker frame, and the caller controls the rate. Frame *dropping* happens in
the acquisition thread instead, where it belongs: the analysis always sees the
newest frame available rather than working through a backlog.

**One inference path.**  ``SlicedDetector`` always runs the full-frame pass and
adds tiles when they are worth it, so there is no separate "standard" and "sahi"
branch to keep in agreement -- the previous split had already drifted, with
different confidence handling on each side.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from backend.core.config import settings
from backend.core.logging import CameraLog, get_logger, throttled
from backend.core.runtime import get_profile
from backend.core import tuning
from backend.ai.alerts.alert_engine import AlertEngine
from backend.ai.analyzer.threat_analyzer import ThreatAnalyzer
from backend.ai.detector.sahi import SlicedDetector
from backend.ai.detector.yolo_detector import YOLODetector
from backend.ai.tracker.tracker_manager import TrackerManager

log = get_logger("service")

# The fields that leave the worker. Everything else an analyzer writes is
# intermediate, and a payload that carries all of it grows the JSON a client
# polls several times a second for no benefit.
PUBLIC_FIELDS: Tuple[str, ...] = (
    "track_id", "class_id", "class_name", "confidence", "smoothed_confidence",
    "bbox", "raw_bbox", "is_person", "is_candidate",
    "is_moving", "movement_ratio", "motion_ready",
    "owner_id", "owner_state", "ownerless", "owner_distance_norm",
    "owner_missing_seconds", "attendance", "attended_by",
    "duration", "dwell_seconds", "dwell_progress", "dwell_paused",
    "threat_seconds", "is_threat", "severity", "severity_rank",
)


def serialise(objects: Sequence[dict]) -> List[dict]:
    """Trim analysed detections down to what the API and overlay consume."""
    payload = []
    for obj in objects:
        item = {key: obj[key] for key in PUBLIC_FIELDS if key in obj}
        bbox = item.get("bbox")
        if bbox is not None:
            # Sub-pixel precision is meaningless on screen and triples the size
            # of the number in JSON.
            item["bbox"] = [round(float(v), 1) for v in bbox]
        if "raw_bbox" in item:
            item["raw_bbox"] = [round(float(v), 1) for v in item["raw_bbox"]]
        payload.append(item)
    return payload


@dataclass
class FrameResult:
    """Everything one processed frame produced."""

    seq: int
    objects: List[dict]
    alerts: List[dict]
    width: int
    height: int
    cycle_ms: float
    infer_ms: float
    tiles: int
    mode: str
    threats: int = 0
    people: int = 0


class DetectionService:
    """Detector, tracker and analyzer chain for one camera.

    One instance per camera. The model itself is shared and loaded once (see
    ``model_loader``), but tracker and analyzer state are per-scene: track ids
    and owner bindings from one camera are meaningless in another.
    """

    def __init__(
        self,
        camera_id: int = 0,
        camera_name: str = "",
        threat_seconds: Optional[float] = None,
    ) -> None:
        self.camera_id = int(camera_id)
        self.camera_name = camera_name or f"camera-{camera_id}"

        self.detector = YOLODetector()
        self.sliced = SlicedDetector(self.detector, camera_id=self.camera_id)
        self.tracker = TrackerManager(camera_id=self.camera_id, frame_rate=settings.target_fps)
        self.analyzer = ThreatAnalyzer(camera_id=self.camera_id, threat_seconds=threat_seconds)
        self.alert_engine = AlertEngine(camera_id=self.camera_id, camera_name=self.camera_name)
        self.camera_log = CameraLog(self.camera_id, self.camera_name)

        # Boxes from the previous frame's tracks. Tiles overlapping them are
        # always inferred: an unattended object is stationary, so motion gating
        # alone would stop looking at exactly the objects that matter.
        self._keepalive: List[List[float]] = []
        self._threat_ids: set = set()
        self._processed = 0
        self._tuning_revision = tuning.revision

        log.info(
            "cam=%d service ready on %s (%s), threat threshold %.0fs",
            self.camera_id, get_profile().device,
            "fp16" if get_profile().half else "fp32",
            self.analyzer.threat_seconds,
        )

    # -- main entry point ----------------------------------------------------

    def process(self, frame: np.ndarray, seq: int = 0, dropped: int = 0) -> FrameResult:
        """Analyse one frame. Exactly one tracker update per call."""
        started = time.perf_counter()
        height, width = frame.shape[:2]

        if tuning.revision != self._tuning_revision:
            self._apply_tuning()

        sliced = self.sliced.detect(frame, keepalive=self._keepalive)
        tracked = self.tracker.update(sliced.detections, frame)
        self._log_dropped(sliced.detections, tracked)

        objects = self._to_objects(tracked, width, height)
        # Called even when empty, so every analyzer's timers advance and expiry
        # runs on frames where an object is absent.
        self.analyzer.analyze(objects)

        self._keepalive = [list(obj["bbox"]) for obj in objects]
        alerts = self.alert_engine.generate_alerts(objects)
        self._announce(objects)

        cycle_ms = (time.perf_counter() - started) * 1000
        people = sum(1 for obj in objects if obj.get("is_person"))
        threats = sum(1 for obj in objects if obj.get("is_threat"))

        self.camera_log.frame(
            cycle_ms=cycle_ms, infer_ms=sliced.infer_ms, tiles=sliced.tiles_run,
            objects=len(objects), people=people, threats=threats, dropped=dropped,
        )
        self._processed += 1

        return FrameResult(
            seq=int(seq), objects=objects, alerts=alerts,
            width=width, height=height,
            cycle_ms=cycle_ms, infer_ms=sliced.infer_ms,
            tiles=sliced.tiles_run, mode=sliced.mode,
            threats=threats, people=people,
        )

    # -- helpers -------------------------------------------------------------

    def _apply_tuning(self) -> None:
        """Re-read settings that were captured when these objects were built.

        Called from :meth:`process` when the tuning revision has moved, so a
        change made from the panel is live within one frame on every camera
        without anything having to know how many cameras there are.

        Nothing is rebuilt. The detector keeps its weights, the tracker keeps
        every track id, and each analyzer keeps its history -- which is the whole
        point, since the state being preserved (dwell timers, owner bindings) is
        the evidence the operator is tuning to see. Failures are logged and
        swallowed: a bad value must not take a camera thread down, and the
        revision is recorded either way so a broken change is not retried on
        every single frame.
        """
        revision = tuning.revision
        try:
            self.sliced.apply_tuning()
            self.tracker.apply_tuning()
            self.analyzer.apply_tuning()
        except Exception as exc:
            log.warning("cam=%d could not apply tuning r%d: %s", self.camera_id, revision, exc)
        else:
            log.info("cam=%d applied tuning r%d", self.camera_id, revision)
        self._tuning_revision = revision

    def _to_objects(self, tracked, width: int, height: int) -> List[dict]:
        """Build the dicts the analyzer chain expects, and nothing more.

        Exactly the fields the first stage reads: the chain fills in the rest, and
        pre-seeding fields it computes (``is_person`` from the raw class, say)
        would silently override the stabilised value with an unstable one.
        """
        objects: List[dict] = []
        for index in range(len(tracked)):
            x1, y1, x2, y2 = (float(v) for v in tracked.xyxy[index])
            class_id = int(tracked.class_id[index])
            objects.append(dict(
                track_id=int(tracked.tracker_id[index]),
                class_id=class_id,
                class_name=self.detector.class_name(class_id),
                confidence=round(float(tracked.confidence[index]), 3),
                bbox=[x1, y1, x2, y2],
                frame_width=width,
                frame_height=height,
                camera_id=self.camera_id,
                camera_name=self.camera_name,
            ))
        return objects

    def _log_dropped(self, raw, tracked) -> None:
        """Report detections the tracker refused to adopt.

        BoT-SORT starts no track for a detection below ``new_track_thresh``; it
        discards it. From outside, that is indistinguishable from the model not
        seeing the object at all -- the box never reaches the analyzer chain, the
        API or the screen, and nothing anywhere says why. This is how a bag
        detected at 0.4 confidence can be simply absent from the UI while every
        log line looks healthy, so the confidences that fell short are named.
        """
        if len(raw) <= len(tracked):
            return
        floor = min(settings.new_track_thresh, settings.track_high_thresh)
        weak = sorted(
            (
                f"{self.detector.class_name(int(cid))}:{float(conf):.2f}"
                for conf, cid in zip(raw.confidence, raw.class_id)
                if float(conf) < floor
            )
        )
        if not weak:
            return
        throttled(
            log, f"weak-detections-{self.camera_id}", 30,
            "cam=%d %d detection(s) below the %.2f tracking floor were dropped, "
            "so they cannot become objects: %s. Lower UOD_NEW_TRACK/UOD_TRACK_HIGH "
            "if these should be tracked.",
            self.camera_id, len(weak), floor, ", ".join(weak[:8]),
            interval=20.0,
        )

    def _announce(self, objects: Sequence[dict]) -> None:
        """Log threats on transition only -- once when raised, once when cleared.

        The original logged the full detection list every frame, so a single
        genuine threat produced thousands of identical lines and the one event
        worth reading was indistinguishable from the noise around it.
        """
        current = {
            int(obj["track_id"]) for obj in objects
            if obj.get("is_threat") and obj.get("track_id") is not None
        }
        for obj in objects:
            track_id = obj.get("track_id")
            if track_id is None or int(track_id) not in current:
                continue
            self.camera_log.threat_confirmed(
                int(track_id), str(obj.get("class_name", "object")),
                float(obj.get("dwell_seconds", 0.0)), str(obj.get("severity", "LOW")),
            )
        for track_id in self._threat_ids - current:
            self.camera_log.threat_cleared(track_id, "object")
        self._threat_ids = current

    def set_frame_rate(self, fps: float) -> None:
        """Tell the tracker how fast frames are actually arriving."""
        self.tracker.set_frame_rate(fps)

    def summarise(self) -> Optional[Dict[str, Any]]:
        """Emit the periodic log line if due, returning its metrics."""
        return self.camera_log.maybe_summarise()

    def stats(self) -> Dict[str, Any]:
        profile = get_profile()
        return {
            "camera_id": self.camera_id,
            "camera_name": self.camera_name,
            "frames_processed": self._processed,
            "device": profile.device,
            "half_precision": profile.half,
            "detector": self.detector.stats(),
            "tracker": {
                "reid": self.tracker.with_reid,
                "gmc": settings.gmc_method,
                "buffer_frames": self.tracker.args.track_buffer,
                "frame_rate": round(self.tracker.frame_rate, 2),
            },
            "analyzer": self.analyzer.state_counts(),
            "threat_seconds": self.analyzer.threat_seconds,
            "active_threats": sorted(self._threat_ids),
        }

    def reset(self) -> None:
        """Forget all tracks -- used when a stream reconnects to a new scene."""
        self.tracker.reset()
        self._keepalive = []
        self._threat_ids = set()

