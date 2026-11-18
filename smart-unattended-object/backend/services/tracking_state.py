"""
tracking_state.py

The only mutable state shared between the camera threads and the API. Small, but
three things about it are load-bearing.

**A frame sequence number travels with the results.**  Boxes are drawn by the
browser over a live video element, so the overlay has to know which frame a set
of boxes belongs to. Without that, a client polling detections while separately
pulling a stream draws boxes from one moment onto pixels from another, and every
object appears slightly displaced whenever anything moves -- indistinguishable
from a detector inaccuracy, and the reason this is here rather than an
afterthought.

**Errors latch.**  The previous version cleared the error on every results
update, so a failure was visible for a few milliseconds at most and the UI
showed a healthy camera producing nothing. An error now stays until the pipeline
has actually recovered, evidenced by a run of successful frames.

**Frames are published, not polled.**  A condition variable lets the MJPEG
endpoint block until a genuinely new frame exists. The old endpoint re-encoded
and re-sent whatever was in the buffer every 50ms, so a 3fps camera sent the
same JPEG twenty times -- pure bandwidth and CPU spent transmitting duplicates.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Consecutive good frames required before a latched error clears. At ~12fps this
# is about a second of healthy operation -- long enough that a camera flapping
# between working and broken stays visibly broken.
RECOVERY_FRAMES = 15


@dataclass
class _Camera:
    """Everything the API can be asked about one camera."""

    processing: bool = False
    # Latched: survives subsequent successful frames until recovery is proven.
    error: Optional[str] = None
    error_at: Optional[float] = None
    consecutive_ok: int = 0
    objects: List[dict] = field(default_factory=list)
    alerts: List[dict] = field(default_factory=list)
    # Sequence number of the frame ``objects`` were computed from.
    seq: int = 0
    frame_width: int = 0
    frame_height: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = 0.0
    started_at: Optional[float] = None


_lock = threading.Lock()
_cameras: Dict[int, _Camera] = {}


def _camera(camera_id: int) -> _Camera:
    """Caller must hold ``_lock``."""
    state = _cameras.get(int(camera_id))
    if state is None:
        state = _Camera()
        _cameras[int(camera_id)] = state
    return state


# -- writers, called from the camera threads ---------------------------------


def set_processing(camera_id: int, processing: bool) -> None:
    with _lock:
        state = _camera(camera_id)
        state.processing = bool(processing)
        if processing:
            state.started_at = time.time()
        state.updated_at = time.time()


def set_error(camera_id: int, error: Optional[str]) -> None:
    """Record a failure, or clear one explicitly (e.g. on restart)."""
    with _lock:
        state = _camera(camera_id)
        if error is None:
            state.error = None
            state.error_at = None
            state.consecutive_ok = 0
            return
        state.error = str(error)
        state.error_at = time.time()
        state.consecutive_ok = 0
        state.updated_at = time.time()


def update_results(
    camera_id: int,
    objects: List[dict],
    alerts: List[dict],
    seq: int,
    frame_size: Optional[Tuple[int, int]] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> None:
    """Publish the analysis of one frame.

    Deliberately does *not* touch ``error``. A successful frame is evidence
    towards recovery, counted here and acted on once there is enough of it.
    """
    with _lock:
        state = _camera(camera_id)
        state.objects = objects
        state.alerts = alerts
        state.seq = int(seq)
        if frame_size:
            state.frame_width, state.frame_height = int(frame_size[0]), int(frame_size[1])
        if metrics:
            state.metrics = metrics
        state.updated_at = time.time()

        if state.error is not None:
            state.consecutive_ok += 1
            if state.consecutive_ok >= RECOVERY_FRAMES:
                state.error = None
                state.error_at = None
                state.consecutive_ok = 0


def set_metrics(camera_id: int, metrics: Dict[str, Any]) -> None:
    with _lock:
        _camera(camera_id).metrics = dict(metrics)


def reset(camera_id: int) -> None:
    """Forget a camera entirely, on stop."""
    with _lock:
        _cameras.pop(int(camera_id), None)
    _frames.drop(camera_id)


# -- readers, called from the API ---------------------------------------------


def snapshot(camera_id: int) -> Dict[str, Any]:
    """A consistent view of one camera: objects, alerts, and the frame they came from."""
    with _lock:
        state = _camera(camera_id)
        return dict(
            camera_id=int(camera_id),
            processing=state.processing,
            error=state.error,
            error_at=state.error_at,
            objects=list(state.objects),
            alerts=list(state.alerts),
            seq=state.seq,
            frame_width=state.frame_width,
            frame_height=state.frame_height,
            metrics=dict(state.metrics),
            updated_at=state.updated_at,
            started_at=state.started_at,
        )


def get_objects(camera_id: int) -> List[dict]:
    with _lock:
        return list(_camera(camera_id).objects)


def get_alerts(camera_id: int) -> List[dict]:
    with _lock:
        return list(_camera(camera_id).alerts)


def get_metrics(camera_id: int) -> Dict[str, Any]:
    with _lock:
        return dict(_camera(camera_id).metrics)


def get_error(camera_id: int) -> Optional[str]:
    with _lock:
        return _camera(camera_id).error


def is_processing(camera_id: int) -> bool:
    with _lock:
        return _camera(camera_id).processing


def active_cameras() -> List[int]:
    with _lock:
        return sorted(cid for cid, state in _cameras.items() if state.processing)


# -- frame bus ----------------------------------------------------------------


class _FrameBus:
    """Latest published item per camera, with a wait-for-new primitive.

    One slot per camera, overwritten: a client that falls behind should see the
    present, not a queue of stale frames it has to catch up through. The
    sequence number is what makes "new" decidable, and it is the same number the
    overlay matches boxes on.

    The payload is deliberately untyped. Two buses use this: one carries preview
    JPEG bytes at acquisition rate, the other carries an analysed frame together
    with the boxes computed from *those* pixels. The second exists because
    perfect overlay alignment cannot be achieved by matching two independent
    streams after the fact -- the frame and its boxes have to be handed over as
    one indivisible item.
    """

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._items: Dict[int, Tuple[Any, int, float]] = {}
        self._subscribers: Dict[int, int] = {}

    def publish(self, camera_id: int, payload: Any, seq: int) -> None:
        with self._condition:
            self._items[int(camera_id)] = (payload, int(seq), time.time())
            self._condition.notify_all()

    def subscribe(self, camera_id: int) -> None:
        with self._condition:
            self._subscribers[int(camera_id)] = self._subscribers.get(int(camera_id), 0) + 1

    def unsubscribe(self, camera_id: int) -> None:
        with self._condition:
            remaining = self._subscribers.get(int(camera_id), 0) - 1
            if remaining > 0:
                self._subscribers[int(camera_id)] = remaining
            else:
                self._subscribers.pop(int(camera_id), None)
                self._items.pop(int(camera_id), None)

    def wanted(self, camera_id: int) -> bool:
        """True when at least one client is consuming this camera.

        JPEG encoding is the second-largest cost in the pipeline after
        inference, and on a headless deployment -- recording alerts with nobody
        watching -- every one of those encodes is thrown away. Asking first turns
        that into nothing.
        """
        with self._condition:
            return self._subscribers.get(int(camera_id), 0) > 0

    def latest(self, camera_id: int) -> Optional[Tuple[Any, int]]:
        with self._condition:
            entry = self._items.get(int(camera_id))
            return (entry[0], entry[1]) if entry else None

    def wait(
        self, camera_id: int, after_seq: int, timeout: float = 1.0
    ) -> Optional[Tuple[Any, int]]:
        """Block until an item newer than ``after_seq`` exists, or time out.

        Returning ``None`` on timeout is not an error: the caller uses it to
        check whether the client is still connected and whether the camera is
        still running, which a blocking wait with no deadline would prevent.
        """
        deadline = time.monotonic() + timeout
        with self._condition:
            while True:
                entry = self._items.get(int(camera_id))
                if entry is not None and entry[1] != after_seq:
                    return (entry[0], entry[1])
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(remaining)

    def drop(self, camera_id: int) -> None:
        with self._condition:
            self._items.pop(int(camera_id), None)
            self._condition.notify_all()


_frames = _FrameBus()
_synced = _FrameBus()


def set_frame(camera_id: int, jpeg: bytes, seq: int) -> None:
    _frames.publish(camera_id, jpeg, seq)


def get_frame(camera_id: int) -> Optional[bytes]:
    entry = _frames.latest(camera_id)
    return entry[0] if entry else None


def get_frame_with_seq(camera_id: int) -> Optional[Tuple[bytes, int]]:
    return _frames.latest(camera_id)


def wait_for_frame(
    camera_id: int, after_seq: int, timeout: float = 1.0
) -> Optional[Tuple[bytes, int]]:
    return _frames.wait(camera_id, after_seq, timeout)


def set_synced(
    camera_id: int,
    jpeg: bytes,
    seq: int,
    objects: List[dict],
    width: int,
    height: int,
) -> None:
    """Publish an analysed frame and its boxes as one item."""
    _synced.publish(
        camera_id,
        {"jpeg": jpeg, "objects": objects, "width": int(width), "height": int(height)},
        seq,
    )


def get_synced(camera_id: int) -> Optional[Tuple[dict, int]]:
    return _synced.latest(camera_id)


def wait_for_synced(
    camera_id: int, after_seq: int, timeout: float = 5.0
) -> Optional[Tuple[dict, int]]:
    return _synced.wait(camera_id, after_seq, timeout)


def preview_subscribe(camera_id: int) -> None:
    _frames.subscribe(camera_id)


def preview_unsubscribe(camera_id: int) -> None:
    _frames.unsubscribe(camera_id)


def preview_wanted(camera_id: int) -> bool:
    return _frames.wanted(camera_id)


def synced_subscribe(camera_id: int) -> None:
    _synced.subscribe(camera_id)


def synced_unsubscribe(camera_id: int) -> None:
    _synced.unsubscribe(camera_id)


def synced_wanted(camera_id: int) -> bool:
    return _synced.wanted(camera_id)


def drop_frames(camera_id: int) -> None:
    _frames.drop(camera_id)
    _synced.drop(camera_id)

