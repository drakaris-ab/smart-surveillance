"""
motion.py

Separates "this object is being carried" from "this object is sitting still",
which is the input the dwell timer depends on.

**Why the old test misfired both ways.**  It flagged movement when the centre
travelled more than 50 pixels over 20 frames. Fixed pixels have the same
resolution and perspective problems as the old ownership test: 50px is a
suitcase's width close to the camera and half a concourse at the far end, so a
distant bag being carried away registered as stationary while a nearby one
registered as moving on detector jitter alone.

Fixed *frames* was the second problem. Twenty frames is 0.7 seconds at 30fps and
seven seconds when tiling drops the rate to 3fps -- so the same code answered a
completely different question depending on scene content.

So displacement is measured against the object's own size, over a window
measured in seconds, and the decision has hysteresis. Hysteresis is what stops
an object hovering at the threshold from alternating between states, because
every alternation would reset the dwell timer and an object could sit abandoned
forever without ever accumulating time.
"""

from __future__ import annotations

import math
import time
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from backend.core.config import settings

# Below this, an object's own dimensions are too small to be a meaningful ruler:
# a 15px bottle would get a 5px movement threshold, which is inside the
# detector's own coordinate noise.
MIN_REFERENCE_PX = 40.0


class MotionAnalyzer:
    """Per-track movement state with hysteresis, in object-relative units."""

    def __init__(
        self,
        threshold_factor: Optional[float] = None,
        release_factor: Optional[float] = None,
        window_seconds: Optional[float] = None,
    ) -> None:
        self.threshold_factor = float(
            threshold_factor if threshold_factor is not None else settings.motion_threshold_factor
        )
        self.release_factor = float(
            release_factor if release_factor is not None else settings.motion_release_factor
        )
        self.window_seconds = float(
            window_seconds if window_seconds is not None else settings.motion_window_seconds
        )

        # {track_id: deque[(timestamp, cx, cy)]}
        self._history: Dict[int, Deque[Tuple[float, float, float]]] = {}
        self._moving: Dict[int, bool] = {}
        self._last_seen: Dict[int, float] = {}

    def apply_tuning(self) -> None:
        """Adopt changed motion settings, keeping position history.

        History matters here: discarding it would make every object briefly
        ``motion_ready = False``, which pauses the dwell clock on exactly the
        objects being investigated.
        """
        self.threshold_factor = float(settings.motion_threshold_factor)
        self.release_factor = float(settings.motion_release_factor)
        self.window_seconds = float(settings.motion_window_seconds)

    @staticmethod
    def _centre(bbox) -> Tuple[float, float, float]:
        x1, y1, x2, y2 = (float(v) for v in bbox)
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0, math.hypot(x2 - x1, y2 - y1)

    def analyze(self, detections: List[dict]) -> List[dict]:
        now = time.monotonic()

        for obj in detections:
            track_id = obj.get("track_id")
            if track_id is None:
                obj.update(is_moving=False, movement=0.0, movement_ratio=0.0, motion_ready=False)
                continue

            track_id = int(track_id)
            cx, cy, diagonal = self._centre(obj["bbox"])
            self._last_seen[track_id] = now

            history = self._history.setdefault(track_id, deque())
            history.append((now, cx, cy))

            # Discard samples older than the window, but always keep at least
            # two so a comparison remains possible after a long detection gap.
            while len(history) > 2 and now - history[0][0] > self.window_seconds:
                history.popleft()

            oldest_time, oldest_x, oldest_y = history[0]
            span = now - oldest_time
            displacement = math.hypot(cx - oldest_x, cy - oldest_y)
            reference = max(diagonal, MIN_REFERENCE_PX)
            ratio = displacement / reference

            # Until the window has actually elapsed there is no evidence either
            # way. Reporting "moving" here would be a guess, and reporting
            # "stationary" would start the dwell clock on a bag still in transit,
            # so the state is held and flagged as not yet ready.
            ready = span >= self.window_seconds * 0.6
            was_moving = self._moving.get(track_id, False)

            if not ready:
                moving = was_moving
            elif was_moving:
                moving = ratio > self.release_factor
            else:
                moving = ratio > self.threshold_factor

            self._moving[track_id] = moving
            obj.update(
                is_moving=bool(moving),
                movement=round(displacement, 1),
                movement_ratio=round(ratio, 3),
                motion_ready=bool(ready),
            )

        self._expire(now)
        return detections

    def _expire(self, now: float) -> None:
        ttl = settings.track_ttl_seconds
        stale = [tid for tid, seen in self._last_seen.items() if now - seen > ttl]
        for track_id in stale:
            self._history.pop(track_id, None)
            self._moving.pop(track_id, None)
            self._last_seen.pop(track_id, None)

    def forget(self, track_id: int) -> None:
        track_id = int(track_id)
        self._history.pop(track_id, None)
        self._moving.pop(track_id, None)
        self._last_seen.pop(track_id, None)
