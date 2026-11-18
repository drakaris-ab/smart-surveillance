"""
logging.py

One logging setup for the whole worker, replacing the per-frame ``print``
calls that used to dominate both the console and the frame budget.

Three ideas carry the design:

*Levels mean something.*  INFO is lifecycle only -- a camera started, a model
loaded, a threat was confirmed. DEBUG carries per-frame detail and is off
unless asked for. WARNING/ERROR are for things a human should act on.

*Nothing repeats unboundedly.*  A camera that cannot connect would otherwise
log identically thirty times a second. :func:`throttled` collapses a repeated
message to one line per interval and reports how many were suppressed.

*Steady state is summarised, not narrated.*  Instead of a block per frame,
:class:`CameraLog` accumulates counters and emits a single line every
``log_summary_seconds`` with FPS, detection counts and where the time went.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Any, Dict, Optional

from backend.core.config import settings

_LOGGER_NAME = "uod"
_configured = False
_configure_lock = threading.Lock()


class _Formatter(logging.Formatter):
    """``12:04:31 INFO  cam=3  message``  -- compact and column-aligned."""

    def format(self, record: logging.LogRecord) -> str:
        stamp = time.strftime("%H:%M:%S", time.localtime(record.created))
        level = record.levelname.ljust(5)
        scope = getattr(record, "scope", "")
        scope = f"{scope} " if scope else ""
        text = record.getMessage()
        if record.exc_info:
            text = f"{text}\n{self.formatException(record.exc_info)}"
        return f"{stamp} {level} {scope}{text}"


def configure() -> logging.Logger:
    """Idempotently attach handlers. Safe to call from any thread."""
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)
    if _configured:
        return logger

    with _configure_lock:
        if _configured:
            return logger

        level = getattr(logging, settings.log_level.upper(), logging.INFO)
        logger.setLevel(level)
        logger.propagate = False
        logger.handlers.clear()

        stream = logging.StreamHandler(sys.stdout)
        stream.setFormatter(_Formatter())
        logger.addHandler(stream)

        if settings.log_file:
            try:
                os.makedirs(os.path.dirname(settings.log_file) or ".", exist_ok=True)
                file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")
                file_handler.setFormatter(_Formatter())
                logger.addHandler(file_handler)
            except OSError as exc:
                logger.warning("could not open log file %s: %s", settings.log_file, exc)

        # Ultralytics is chatty on import and prints a banner per predict call.
        for noisy in ("ultralytics", "torch", "PIL", "urllib3"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

        _configured = True

    return logger


def get_logger(scope: str = "") -> logging.LoggerAdapter:
    """A logger whose lines are prefixed with ``scope`` (e.g. ``cam=3``)."""
    base = configure()
    return logging.LoggerAdapter(base, {"scope": scope})


# ---------------------------------------------------------------------------
# Throttling
# ---------------------------------------------------------------------------

_throttle_state: Dict[str, list] = {}
_throttle_lock = threading.Lock()


def throttled(
    logger: logging.LoggerAdapter,
    key: str,
    level: int,
    message: str,
    *args: Any,
    interval: float = 10.0,
) -> None:
    """Log at most once per ``interval`` per ``key``.

    Suppressed repeats are counted and reported on the next line that does get
    through, so a burst of identical failures reads as
    ``... (repeated 296x in 10.0s)`` rather than scrolling the console.
    """
    now = time.monotonic()
    with _throttle_lock:
        last, suppressed = _throttle_state.get(key, (0.0, 0))
        if now - last < interval:
            _throttle_state[key] = [last, suppressed + 1]
            return
        _throttle_state[key] = [now, 0]

    if suppressed:
        message = f"{message} (repeated {suppressed}x in {interval:.0f}s)"
    logger.log(level, message, *args)


def reset_throttle(key: str) -> None:
    """Forget a key so a recovered-then-failed condition logs again at once."""
    with _throttle_lock:
        _throttle_state.pop(key, None)


# ---------------------------------------------------------------------------
# Per-camera rolling summary
# ---------------------------------------------------------------------------


class CameraLog:
    """Accumulates counters and emits one summary line per interval.

    Call :meth:`frame` once per processed frame with the timings, then
    :meth:`maybe_summarise` -- it only writes when the interval has elapsed.
    """

    def __init__(self, camera_id: int, camera_name: str = "") -> None:
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.log = get_logger(f"cam={camera_id}")
        self._interval = max(1.0, settings.log_summary_seconds)
        self._reset(time.monotonic())
        self._announced_threats: set = set()

    def _reset(self, now: float) -> None:
        self._window_start = now
        self._frames = 0
        self._detect_cycles = 0
        self._infer_ms = 0.0
        self._cycle_ms = 0.0
        self._tiles = 0
        self._objects = 0
        self._people = 0
        self._threats = 0
        self._dropped = 0

    def frame(
        self,
        *,
        cycle_ms: float,
        infer_ms: float = 0.0,
        tiles: int = 0,
        objects: int = 0,
        people: int = 0,
        threats: int = 0,
        ran_detection: bool = True,
        dropped: int = 0,
    ) -> None:
        self._frames += 1
        self._cycle_ms += cycle_ms
        self._dropped += dropped
        if ran_detection:
            self._detect_cycles += 1
            self._infer_ms += infer_ms
            self._tiles += tiles
        self._objects += objects
        self._people += people
        self._threats = max(self._threats, threats)

    def maybe_summarise(self) -> Optional[dict]:
        now = time.monotonic()
        elapsed = now - self._window_start
        if elapsed < self._interval or self._frames == 0:
            return None

        fps = self._frames / elapsed
        avg_cycle = self._cycle_ms / self._frames
        avg_infer = self._infer_ms / self._detect_cycles if self._detect_cycles else 0.0
        # Near 1.0 means the GPU is the wall; near 0.1 means the model is idle
        # waiting on frame acquisition or post-processing, and a faster model
        # would change nothing.
        infer_share = (avg_infer / avg_cycle) if avg_cycle > 0 else 0.0
        avg_tiles = self._tiles / self._detect_cycles if self._detect_cycles else 0.0
        avg_objects = self._objects / self._frames

        self.log.info(
            "%.1f fps | cycle %.0fms (infer %.0fms, %.0f%%) | %.1f tiles | "
            "%.1f obj avg | %d people | %d threat(s)%s",
            fps,
            avg_cycle,
            avg_infer,
            infer_share * 100,
            avg_tiles,
            avg_objects,
            self._people,
            self._threats,
            f" | {self._dropped} frames dropped" if self._dropped else "",
        )

        metrics = {
            "fps": round(fps, 2),
            "avg_cycle_ms": round(avg_cycle, 1),
            "avg_infer_ms": round(avg_infer, 1),
            "inference_share_of_cycle": round(infer_share, 3),
            "avg_tiles": round(avg_tiles, 2),
            "avg_objects": round(avg_objects, 2),
            "frames_dropped": self._dropped,
            "window_seconds": round(elapsed, 1),
        }
        self._reset(now)
        return metrics

    def threat_confirmed(self, track_id: Any, class_name: str, duration: float, severity: str) -> None:
        """Log a threat once per track, not once per frame it stays true."""
        if track_id in self._announced_threats:
            return
        self._announced_threats.add(track_id)
        self.log.warning(
            "THREAT %s #%s unattended for %.0fs (severity %s)",
            class_name, track_id, duration, severity,
        )

    def threat_cleared(self, track_id: Any, class_name: str) -> None:
        if track_id not in self._announced_threats:
            return
        self._announced_threats.discard(track_id)
        self.log.info("cleared: %s #%s is attended again", class_name, track_id)
