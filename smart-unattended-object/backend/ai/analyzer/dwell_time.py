"""
dwell_time.py

The clock that turns "ownerless and stationary" into "threat". Everything
upstream exists to make this timer trustworthy.

**Why the old timer rarely reached its threshold.**  It stored a start time and
deleted it the instant any frame reported the object as attended or moving. A
single frame of detector jitter that nudged the centre 50px, or one frame where
a passer-by was momentarily the nearest person, discarded thirty seconds of
accumulated evidence. In a busy scene the timer was reset more often than it was
allowed to run, so a genuinely abandoned bag could sit there indefinitely and
never trigger.

Two changes make it hold:

*Accumulate elapsed time rather than subtract a start time.*  That makes the
timer pausable. A brief interruption freezes it instead of destroying it.

*Interruptions get a grace window.*  The state is only discarded when the object
has been continuously attended or moving for longer than the grace period --
which is what actually distinguishes "the owner came back" from "one bad frame".

The clock is ``time.monotonic``. Wall-clock time can step backwards on an NTP
correction, which with the old code produced negative durations and, worse, a
duration that jumped straight past the threshold.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from backend.core.config import settings


@dataclass
class _Dwell:
    # Seconds this object has been unattended, excluding paused intervals.
    accumulated: float
    # Last frame that counted towards the total.
    last_update: float
    # When the unattended condition was first broken, or None while it holds.
    broken_at: Optional[float] = None
    # Someone other than the owner is standing with the object. The timer is
    # held rather than discarded: see the note on proxy attendance below.
    frozen: bool = False
    # Highest total reached, so a reported duration never appears to shrink.
    peak: float = 0.0


class DwellTimeAnalyzer:
    """Accumulates unattended time per track, with a grace window."""

    def __init__(
        self,
        threat_seconds: Optional[float] = None,
        grace_seconds: Optional[float] = None,
    ) -> None:
        self.threat_seconds = float(
            threat_seconds if threat_seconds is not None else settings.threat_seconds
        )
        self.grace_seconds = float(
            grace_seconds if grace_seconds is not None else settings.dwell_grace_seconds
        )
        # A per-camera threshold passed in by the caller outranks the global one,
        # so runtime tuning must not overwrite it -- otherwise a camera
        # configured for 10s would silently jump to the global 30s the first time
        # any unrelated slider moved.
        self._threat_is_explicit = threat_seconds is not None
        self._state: Dict[int, _Dwell] = {}
        self._last_seen: Dict[int, float] = {}

    def apply_tuning(self) -> None:
        """Adopt changed dwell settings, keeping every accumulated timer.

        Shortening the interval can confirm a threat on the very next frame from
        time already banked, which is the intended behaviour: the object really
        has been sitting there that long.
        """
        if not self._threat_is_explicit:
            self.threat_seconds = float(settings.threat_seconds)
        self.grace_seconds = float(settings.dwell_grace_seconds)

    @staticmethod
    def _is_unattended(obj: dict) -> bool:
        """The object is a candidate for the clock right now.

        ``motion_ready`` matters: before the motion window has elapsed there is
        no evidence the object is stationary, and starting the clock on a bag
        still in someone's hand is how false alerts begin.
        """
        return bool(
            obj.get("ownerless")
            and not obj.get("is_moving")
            and obj.get("motion_ready", True)
        )

    # Every detection leaves this stage with the same keys present, whether or
    # not it is being timed. A payload whose shape depends on state forces every
    # consumer -- the API serialiser and the overlay both -- to guess.
    _IDLE = dict(duration=0, dwell_seconds=0.0, dwell_progress=0.0, dwell_paused=False, is_threat=False)

    def analyze(self, detections: List[dict]) -> List[dict]:
        now = time.monotonic()

        for obj in detections:
            track_id = obj.get("track_id")

            if obj.get("is_person") or track_id is None or not obj.get("is_candidate", True):
                obj.update(self._IDLE)
                continue

            track_id = int(track_id)
            self._last_seen[track_id] = now
            state = self._state.get(track_id)

            if self._is_unattended(obj):
                if state is None:
                    state = _Dwell(accumulated=0.0, last_update=now)
                    self._state[track_id] = state
                else:
                    # Resuming after a brief interruption: the pause itself is
                    # not credited, only real unattended time.
                    state.broken_at = None
                    state.frozen = False
                    # Cap the credited gap. If the object was occluded for a
                    # long stretch the tracker may have held the id through it,
                    # but crediting minutes of unseen time would let a
                    # re-identified object jump straight to threat.
                    elapsed = min(now - state.last_update, self.grace_seconds)
                    state.accumulated += max(0.0, elapsed)
                state.last_update = now
                state.peak = max(state.peak, state.accumulated)

            elif state is not None:
                if obj.get("attendance") == "proxy":
                    # Somebody who is not the owner is standing with the object.
                    # That is enough to suppress an alert, but not enough to
                    # forgive the time already accumulated -- otherwise a bag
                    # could sit abandoned all day in a busy hall, its timer
                    # cleared each time a stranger happened to stop beside it.
                    # Freeze instead: the moment they leave, the alert is due.
                    state.frozen = True
                    state.broken_at = None
                    state.last_update = now
                else:
                    state.frozen = False
                    if state.broken_at is None:
                        state.broken_at = now
                    elif now - state.broken_at > self.grace_seconds:
                        # Sustained attendance by the owner, or sustained
                        # movement: the object genuinely is not abandoned any
                        # more. Discard the timer for real.
                        self._state.pop(track_id, None)
                        state = None

            if state is None:
                obj.update(self._IDLE)
                continue

            duration = state.peak
            # A threat also has to be a detection worth acting on. Tracking runs
            # on a deliberately low confidence bar to keep ids alive through
            # weak frames; confirming an alert uses the stricter one.
            confidence = float(obj.get("smoothed_confidence", obj.get("confidence", 0.0)))
            confident = confidence >= settings.decision_confidence

            obj.update(
                duration=int(duration),
                dwell_seconds=round(duration, 1),
                dwell_progress=round(min(1.0, duration / max(0.1, self.threat_seconds)), 3),
                dwell_paused=bool(state.frozen or state.broken_at is not None),
                # A frozen timer is not a live threat: somebody is with the
                # object right now. A briefly interrupted one still is, which is
                # what stops the alert flickering on one bad frame.
                is_threat=bool(duration >= self.threat_seconds and confident and not state.frozen),
            )

        self._expire(now)
        return detections

    def _expire(self, now: float) -> None:
        """Drop state for tracks that have not been seen for a while.

        Keyed on absence over time, not absence from one frame -- the original
        deleted state for anything missing from the current frame, which is a
        single dropped detection away from losing the timer.
        """
        ttl = settings.track_ttl_seconds
        stale = [tid for tid, seen in self._last_seen.items() if now - seen > ttl]
        for track_id in stale:
            self._state.pop(track_id, None)
            self._last_seen.pop(track_id, None)

    def forget(self, track_id: int) -> None:
        track_id = int(track_id)
        self._state.pop(track_id, None)
        self._last_seen.pop(track_id, None)
