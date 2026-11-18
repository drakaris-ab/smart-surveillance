"""
threat_analyzer.py

The analysis chain, in the one order that works, plus the shared per-track
lifecycle the individual analyzers cannot manage on their own.

**Order is not arbitrary.**  Each stage consumes fields the previous one writes,
and the original order (motion, ownership, dwell) was missing both ends:

1. *Class stabilisation* first, because ownership needs ``is_person`` and a
   flickering label means an object is a person on some frames and luggage on
   others. It also produces ``smoothed_confidence``, which the threat decision
   uses.
2. *Box smoothing* second, so every later measurement and the operator's overlay
   use identical coordinates. Measuring jittery boxes and drawing smoothed ones
   would let a visibly stationary object be reported as moving.
3. *Motion*, because ownership releases a binding when the object is being
   carried, and needs to know that before it decides who owns it.
4. *Ownership*, because dwell only counts time an object is ownerless.
5. *Dwell*, which turns that into a duration and a threat flag.
6. *Severity*, which grades a confirmed threat by how long it has stood.

**Shared lifecycle.**  Five analyzers each held their own per-track dictionaries
and each cleaned up independently -- several of them by deleting anything absent
from the current frame, which a single dropped detection triggers. Expiry is now
uniformly time-based, and ``forget`` fans out to every stage so a track that is
genuinely finished leaves no residue anywhere.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from backend.core.config import UNATTENDED_OBJECT_CLASSES, settings
from backend.ai.alerts.severity import SeverityAnalyzer
from backend.ai.analyzer.box_smoother import BoxSmoother
from backend.ai.analyzer.Class_Stabilizer import ClassStabilizer
from backend.ai.analyzer.dwell_time import DwellTimeAnalyzer
from backend.ai.analyzer.motion import MotionAnalyzer
from backend.ai.analyzer.ownership import OwnershipAnalyzer

_CANDIDATE_NAMES = frozenset(name.lower() for name in UNATTENDED_OBJECT_CLASSES)


class ThreatAnalyzer:
    """One instance per camera: all per-track state is scene-specific."""

    def __init__(self, camera_id: int = 0, threat_seconds: Optional[float] = None) -> None:
        self.camera_id = camera_id
        self.stabilizer = ClassStabilizer()
        self.smoother = BoxSmoother()
        self.motion = MotionAnalyzer()
        self.owner = OwnershipAnalyzer()
        self.dwell = DwellTimeAnalyzer(threat_seconds=threat_seconds)
        self.severity = SeverityAnalyzer()

    def apply_tuning(self) -> None:
        """Push changed settings into every stage that captured one.

        ``SeverityAnalyzer`` is absent because it reads what it needs from the
        object it is given; it holds no configuration of its own.
        """
        self.stabilizer.apply_tuning()
        self.smoother.apply_tuning()
        self.motion.apply_tuning()
        self.owner.apply_tuning()
        self.dwell.apply_tuning()

    def analyze(self, detections: List[dict]) -> List[dict]:
        if not detections:
            # Still advance the stages so their timers and expiry run on an
            # empty frame. An object that has just left the scene has to be able
            # to age out, and that can only happen on frames it is absent from.
            self.stabilizer.analyze([])
            self.smoother.smooth([])
            self.motion.analyze([])
            self.owner.analyze([])
            self.dwell.analyze([])
            return detections

        detections = self.stabilizer.analyze(detections)

        for obj in detections:
            # Only these classes can ever raise an abandoned-object alert, so a
            # stationary person or an unrecognised object never accumulates dwell
            # time. Decided here rather than inside dwell so the flag is also
            # available to the API and the overlay.
            obj["is_candidate"] = str(obj.get("class_name", "")).lower() in _CANDIDATE_NAMES

        detections = self.smoother.smooth(detections)
        detections = self.motion.analyze(detections)
        detections = self.owner.analyze(detections)
        detections = self.dwell.analyze(detections)

        for obj in detections:
            # The threshold travels with the detection so both the severity
            # ladder and the frontend progress bar are scaled to whatever this
            # camera is configured for, instead of assuming the default.
            obj["threat_seconds"] = self.dwell.threat_seconds
            obj["severity"] = self.severity.get_severity(obj)

        return detections

    @property
    def threat_seconds(self) -> float:
        return self.dwell.threat_seconds

    def forget(self, track_ids: Iterable[int]) -> None:
        """Drop every trace of the given tracks across all stages."""
        for track_id in track_ids:
            track_id = int(track_id)
            self.stabilizer.forget(track_id)
            self.smoother.forget(track_id)
            self.motion.forget(track_id)
            self.owner.forget(track_id)
            self.dwell.forget(track_id)

    def state_counts(self) -> dict:
        """Sizes of the internal tables, for the metrics endpoint.

        Every one of these is bounded by ``UOD_TRACK_TTL``; watching them is how
        a leak would be noticed rather than inferred from memory growth.
        """
        return {
            "stabilizer": len(self.stabilizer._history),
            "smoother": len(self.smoother._boxes),
            "motion": len(self.motion._history),
            "bindings": len(self.owner._bindings),
            "dwell": len(self.dwell._state),
            "ttl_seconds": settings.track_ttl_seconds,
        }
