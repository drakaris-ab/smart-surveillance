"""
box_smoother.py

Temporal smoothing of box coordinates. This is the last of the three separate
causes of "inaccurate bounding boxes", and the only one that is purely visual.

The other two are fixed upstream: tile-edge fragments are rejected in
``sahi.py`` and duplicate detections are merged on intersection-over-smaller
rather than IoU. What remains after those is jitter -- a stationary object's box
breathing by a few pixels every frame, because the detector re-estimates the
edges independently each time and nothing constrains consecutive estimates to
agree.

A few pixels of jitter is invisible in a still frame and very visible in a live
overlay, where it reads as the system being unsure what it is looking at. It also
feeds the motion analyzer noise it has to work to reject.

An exponential moving average over the corners fixes it, with one necessary
exception: when the new box barely overlaps the previous one, the object has
genuinely jumped -- someone picked the bag up, or the tracker handed this id a
different object. Averaging across that produces a box that glides through empty
space for several frames, which is worse than the jitter. Low overlap therefore
snaps rather than blends.

Smoothing runs before the analyzers, not after, so motion and ownership are
measured on the same coordinates the operator sees. Measuring one thing and
drawing another is how a box that looks stationary ends up flagged as moving.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Sequence, Tuple

from backend.core.config import settings

Box = Tuple[float, float, float, float]

# Longer than this without an update and the previous box is stale: the object
# has been occluded or lost, so wherever it reappears is not a continuation of
# where it was.
RESYNC_SECONDS = 1.0


def iou(a: Sequence[float], b: Sequence[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class BoxSmoother:
    """Per-track exponential smoothing of box corners, with jump detection."""

    def __init__(
        self,
        alpha: Optional[float] = None,
        snap_iou: Optional[float] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        # alpha is the weight given to the new observation. Higher tracks fast
        # movement more closely; lower is steadier but lags. 0.45 keeps a
        # walking person's box attached while removing most of the breathing on
        # a stationary one.
        self.alpha = float(alpha if alpha is not None else settings.smooth_alpha)
        self.snap_iou = float(snap_iou if snap_iou is not None else settings.smooth_snap_iou)
        self.enabled = bool(enabled if enabled is not None else settings.smooth_boxes)

        self._boxes: Dict[int, Box] = {}
        self._last_seen: Dict[int, float] = {}

    def apply_tuning(self) -> None:
        """Adopt changed smoothing settings. Smoothed positions are kept, so
        turning smoothing off shows raw boxes immediately and turning it back on
        resumes from where each box was rather than snapping."""
        self.alpha = float(settings.smooth_alpha)
        self.snap_iou = float(settings.smooth_snap_iou)
        self.enabled = bool(settings.smooth_boxes)

    def smooth(self, detections: List[dict]) -> List[dict]:
        if not self.enabled:
            for obj in detections:
                obj["raw_bbox"] = list(obj["bbox"])
            return detections

        now = time.monotonic()
        alpha = min(1.0, max(0.05, self.alpha))

        for obj in detections:
            raw: Box = tuple(float(v) for v in obj["bbox"])  # type: ignore[assignment]
            obj["raw_bbox"] = [round(v, 1) for v in raw]

            track_id = obj.get("track_id")
            if track_id is None:
                # No identity, so no history to smooth against.
                continue

            track_id = int(track_id)
            previous = self._boxes.get(track_id)
            gap = now - self._last_seen.get(track_id, now)
            self._last_seen[track_id] = now

            if previous is None or gap > RESYNC_SECONDS or iou(previous, raw) < self.snap_iou:
                smoothed = raw
            else:
                smoothed = (
                    previous[0] + alpha * (raw[0] - previous[0]),
                    previous[1] + alpha * (raw[1] - previous[1]),
                    previous[2] + alpha * (raw[2] - previous[2]),
                    previous[3] + alpha * (raw[3] - previous[3]),
                )

            self._boxes[track_id] = smoothed
            obj["bbox"] = [round(v, 1) for v in smoothed]

        self._expire(now)
        return detections

    def _expire(self, now: float) -> None:
        ttl = settings.track_ttl_seconds
        stale = [tid for tid, seen in self._last_seen.items() if now - seen > ttl]
        for track_id in stale:
            self._boxes.pop(track_id, None)
            self._last_seen.pop(track_id, None)

    def forget(self, track_id: int) -> None:
        track_id = int(track_id)
        self._boxes.pop(track_id, None)
        self._last_seen.pop(track_id, None)
