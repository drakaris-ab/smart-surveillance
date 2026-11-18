"""
alert_engine.py

Turns confirmed threats into alerts, once each.

**Why this needed changing.**  The previous version built a fresh alert dict for
every threatening detection on every frame. A single abandoned bag at 12fps
generated 720 alerts a minute, all identical apart from the timestamp, and the
API returned whatever the last frame happened to produce -- so an alert that had
been standing for five minutes looked exactly as new as one raised a moment ago,
and any consumer that appended to a list rather than replacing it grew without
bound.

An alert here has an identity: it is raised once per track, updated in place
while the threat persists, and retired when it stops. That makes ``raised_at``
meaningful, lets a client de-duplicate on ``alert_id``, and keeps the payload
proportional to the number of actual problems rather than to uptime.

Retirement is deliberately not instant. The dwell stage already refuses to drop a
threat on a single frame, but a track can vanish for a frame or two while the
tracker holds it; a short linger keeps the alert on screen across that instead of
flickering.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

# How long an alert stays after its track stops reporting a threat.
LINGER_SECONDS = 3.0


@dataclass
class _Alert:
    alert_id: str
    track_id: int
    object_class: str
    raised_at: float          # wall clock, for display
    raised_monotonic: float   # for arithmetic, immune to clock steps
    duration: int = 0
    severity: str = "LOW"
    severity_rank: int = 1
    last_seen: float = 0.0
    active: bool = True

    def payload(self, camera_id: int, camera_name: str) -> dict:
        return {
            "alert_id": self.alert_id,
            # Same value under the key the existing frontend de-duplicates on.
            "id": self.alert_id,
            "camera_id": camera_id,
            "camera_name": camera_name,
            "track_id": self.track_id,
            "object": self.object_class,
            "duration": self.duration,
            "severity": self.severity,
            "severity_rank": self.severity_rank,
            "active": self.active,
            "raised_at": datetime.fromtimestamp(self.raised_at).strftime("%Y-%m-%d %H:%M:%S"),
            # Kept under its old name so existing clients keep working.
            "time": datetime.fromtimestamp(self.raised_at).strftime("%Y-%m-%d %H:%M:%S"),
            "message": (
                f"[{camera_name}] Unattended {self.object_class} "
                f"left for {self.duration}s"
            ),
        }


class AlertEngine:
    """Live alerts for one camera, keyed on track id.

    Camera identity is held here rather than read from each detection: the
    analyzer chain's contract is that detections carry only what the analyzers
    need, and requiring every one of them to also carry the camera's name meant a
    ``KeyError`` deep in alert generation if any stage rebuilt a dict.
    """

    def __init__(self, camera_id: int = 0, camera_name: str = "") -> None:
        self.camera_id = int(camera_id)
        self.camera_name = camera_name or f"camera-{camera_id}"
        self._alerts: Dict[int, _Alert] = {}
        self._counter = 0

    def generate_alerts(self, detections: List[dict]) -> List[dict]:
        """Update the live set from one frame's analysis and return it.

        Returns the current alerts, highest severity first, so a UI showing only
        the top few shows the worst few.
        """
        now = time.monotonic()

        for obj in detections:
            track_id = obj.get("track_id")
            if not obj.get("is_threat") or track_id is None:
                continue
            track_id = int(track_id)
            duration = int(obj.get("dwell_seconds", obj.get("duration", 0)) or 0)
            severity = str(obj.get("severity", "LOW"))
            rank = int(obj.get("severity_rank", 1))

            alert = self._alerts.get(track_id)
            if alert is None:
                self._counter += 1
                alert = _Alert(
                    alert_id=f"c{self.camera_id}-t{track_id}-{self._counter}",
                    track_id=track_id,
                    object_class=str(obj.get("class_name", "object")),
                    raised_at=time.time(),
                    raised_monotonic=now,
                )
                self._alerts[track_id] = alert

            # Duration only ever climbs. The dwell stage reports its peak, but
            # guarding here too means a re-identified track cannot make an alert
            # appear to go backwards.
            alert.duration = max(alert.duration, duration)
            alert.severity = severity
            alert.severity_rank = rank
            alert.last_seen = now
            alert.active = True

        for track_id, alert in list(self._alerts.items()):
            if alert.last_seen == now:
                continue
            if now - alert.last_seen > LINGER_SECONDS:
                self._alerts.pop(track_id, None)
            else:
                # Still shown, but marked so the UI can grey it out rather than
                # having it disappear during a momentary detection gap.
                alert.active = False

        return [
            alert.payload(self.camera_id, self.camera_name)
            for alert in sorted(
                self._alerts.values(),
                key=lambda a: (-a.severity_rank, -a.duration),
            )
        ]

    def active(self) -> List[dict]:
        return [a.payload(self.camera_id, self.camera_name) for a in self._alerts.values() if a.active]

    def clear(self) -> None:
        self._alerts.clear()
