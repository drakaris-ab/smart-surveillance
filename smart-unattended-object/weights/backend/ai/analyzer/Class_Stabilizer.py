"""
Class_Stabilizer.py

Holds a track's class label and confidence steady across frames.

The detector's class decision is not stable frame to frame: a backpack seen at
30 pixels is regularly reported as a handbag, and at the boundary between two
similar classes the label can alternate every frame. That matters here for a
specific reason -- the label decides whether the object is a threat candidate at
all, so a flickering label means an object drops out of consideration on some
frames and the alert text changes on others.

**Why the old cleanup was self-defeating.**  It deleted the history of every
track not present in the current frame. One missed detection -- routine during a
partial occlusion -- wiped the entire rolling window, so the track came back with
no history and took the full window to stabilise again. The very frames where
stabilisation is most needed are the ones that destroyed it. Cleanup is now
keyed on how long a track has been absent.

Votes are weighted by confidence. A run of weak 0.3 detections calling something
a handbag should not outvote two strong 0.9 detections calling it a suitcase,
which unweighted majority voting would let it do.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from backend.core.config import PERSON_CLASSES, settings

_PERSON_NAMES = frozenset(name.lower() for name in PERSON_CLASSES)


class ClassStabilizer:
    """Rolling, confidence-weighted class vote and smoothed confidence."""

    def __init__(self, window: Optional[int] = None) -> None:
        self.window = int(window if window is not None else settings.stabilizer_window)
        # {track_id: deque[(class_id, class_name, confidence)]}
        self._history: Dict[int, Deque[Tuple[int, str, float]]] = {}
        self._last_seen: Dict[int, float] = {}

    def apply_tuning(self) -> None:
        """Adopt a new vote window. Existing history is re-bounded, not dropped,
        by the maxlen check in :meth:`analyze`."""
        self.window = int(settings.stabilizer_window)

    def analyze(self, detections: List[dict]) -> List[dict]:
        now = time.monotonic()

        for obj in detections:
            track_id = obj.get("track_id")
            confidence = float(obj.get("confidence", 0.0))

            if track_id is None:
                # Nothing to key a history on. Report this frame's own values so
                # downstream consumers always find the smoothed fields present.
                obj["smoothed_confidence"] = round(confidence, 3)
                obj["class_votes"] = 1
                continue

            track_id = int(track_id)
            self._last_seen[track_id] = now

            history = self._history.get(track_id)
            if history is None:
                history = deque(maxlen=self.window)
                self._history[track_id] = history
            elif history.maxlen != self.window:
                # Window resized at runtime; carry over what still fits.
                history = deque(history, maxlen=self.window)
                self._history[track_id] = history

            history.append((int(obj.get("class_id", -1)), str(obj.get("class_name", "")), confidence))

            weights: Dict[Tuple[int, str], float] = {}
            for class_id, class_name, conf in history:
                key = (class_id, class_name)
                # A floor keeps a very weak detection from contributing nothing
                # at all, so a class seen only weakly still accumulates evidence.
                weights[key] = weights.get(key, 0.0) + max(0.05, conf)

            (best_id, best_name), _ = max(weights.items(), key=lambda item: item[1])
            obj["class_id"] = best_id
            obj["class_name"] = best_name
            obj["is_person"] = best_name.lower() in _PERSON_NAMES

            # Mean over the window, not an EMA: a plain mean over a bounded
            # window forgets an outlier completely once it falls out, whereas an
            # EMA keeps a decaying trace of it indefinitely.
            confs = [conf for _, _, conf in history]
            obj["smoothed_confidence"] = round(sum(confs) / len(confs), 3)
            obj["class_votes"] = len(history)

        self._expire(now)
        return detections

    def _expire(self, now: float) -> None:
        ttl = settings.track_ttl_seconds
        stale = [tid for tid, seen in self._last_seen.items() if now - seen > ttl]
        for track_id in stale:
            self._history.pop(track_id, None)
            self._last_seen.pop(track_id, None)

    def forget(self, track_id: int) -> None:
        track_id = int(track_id)
        self._history.pop(track_id, None)
        self._last_seen.pop(track_id, None)
