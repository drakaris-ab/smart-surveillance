"""
pipeline_runner.py

Owns the threads. Two per camera, and the split is the point of the file.

**Why acquisition and analysis must not share a thread.**  The previous loop read
a frame, ran inference, drew an overlay, encoded a JPEG and published results,
all in sequence. RTSP and MJPEG sources are buffered, so while inference ran the
source kept queueing frames; the next read returned the oldest one waiting rather
than the newest available. Every cycle the backlog grew, and the operator watched
a stream drifting further behind reality -- seconds behind after a minute, with no
way to catch up, because the loop could never read faster than it could infer.

The fix is a *latest-frame-wins* slot between the two. The reader runs flat out
and overwrites the slot; the analyser takes whatever is in it when it becomes
free. Frames in between are dropped on purpose and counted, which is the honest
trade: analysis at the rate the hardware allows, on current pixels.

**The stream carries clean video.**  Boxes are drawn by the browser onto a canvas
over the video, so nothing is baked into the JPEG. That decision pays for itself
here: the encoder no longer waits for inference, so the preview runs at source
rate even when analysis is slow, and an MJPEG source can often be republished
without re-encoding at all.

**A sequence number travels with everything.**  Each acquired frame gets one, and
the results published for it carry the same number, so a client can tell how
stale its boxes are instead of assuming they match what it is looking at.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union

import cv2
import numpy as np
import requests

from backend.core.config import settings
from backend.core.logging import get_logger, reset_throttle, throttled
from backend.services import tracking_state
from backend.services.detection_service import DetectionService, serialise
from backend.shared.stream.stream_manager import StreamManager

# Shared stream manager instance for all camera workers
_stream_manager = StreamManager()

log = get_logger("runner")

Source = Union[str, int, None]


def _source(stream_url: Source) -> Union[str, int]:
    """Keep webcam indexes usable while passing RTSP/HTTP URLs through."""
    if isinstance(stream_url, str) and stream_url.isdigit():
        return int(stream_url)
    return stream_url if stream_url else 0


def encode_jpeg(frame: np.ndarray) -> Optional[bytes]:
    """Downscale to the preview width and encode.

    Streaming full 4K frames to a browser that displays them in a 600px panel
    spends most of the bandwidth and most of the encode time on pixels nobody
    sees. Analysis still uses the full-resolution frame -- the downscale applies
    to the preview only, which is why the overlay scales boxes by the frame
    dimensions reported alongside them rather than by the stream's.
    """
    limit = int(settings.stream_max_width)
    height, width = frame.shape[:2]
    if limit and width > limit:
        scale = limit / float(width)
        frame = cv2.resize(
            frame, (limit, max(1, int(round(height * scale)))), interpolation=cv2.INTER_AREA
        )
    ok, buffer = cv2.imencode(
        ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(settings.jpeg_quality)]
    )
    return buffer.tobytes() if ok else None


class _Slot:
    """A one-deep, overwrite-on-write handoff between two threads.

    Not a queue. A queue of frames is a queue of stale work: by the time the
    analyser reaches the third item it is reasoning about the past, and every
    conclusion it draws -- where an object is, whether it moved -- is wrong for
    the present. Dropping is the correct behaviour, so it is the only behaviour.
    """

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._frame: Optional[np.ndarray] = None
        self._seq: int = 0
        self._dropped: int = 0
        self._closed: bool = False

    def publish(self, frame: np.ndarray, seq: int) -> None:
        with self._condition:
            if self._frame is not None:
                self._dropped += 1
            self._frame = frame
            self._seq = int(seq)
            self._condition.notify()

    def take(self, timeout: float = 1.0) -> Optional[Tuple[np.ndarray, int]]:
        """Remove and return the newest frame, or None on timeout/close."""
        deadline = time.monotonic() + timeout
        with self._condition:
            while self._frame is None and not self._closed:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(remaining)
            if self._frame is None:
                return None
            frame, seq, self._frame = self._frame, self._seq, None
            return frame, seq

    def dropped(self) -> int:
        with self._condition:
            count, self._dropped = self._dropped, 0
            return count

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._frame = None
            self._condition.notify_all()


class MjpegFrameReader:
    """Decodes frames from another service's MJPEG stream.

    Returns the original JPEG bytes alongside the decoded frame. The preview can
    then republish them untouched when no downscale is needed, which removes a
    decode-encode round trip that produced a visibly worse image than the one it
    started from.
    """

    MAX_BUFFER = 4_000_000  # a corrupt stream must not grow the buffer forever

    def __init__(self, stream_url: str) -> None:
        self.stream_url = stream_url
        self.response = None
        self.chunks = None
        self.buffer = bytearray()

    def _connect(self) -> None:
        self.close()
        self.response = requests.get(self.stream_url, stream=True, timeout=(3, 10))
        self.response.raise_for_status()
        self.chunks = self.response.iter_content(chunk_size=16384)

    def read(self) -> Tuple[np.ndarray, bytes]:
        if self.chunks is None:
            self._connect()

        while True:
            chunk = next(self.chunks)
            if not chunk:
                continue
            self.buffer.extend(chunk)

            start = self.buffer.find(b"\xff\xd8")
            end = self.buffer.find(b"\xff\xd9", start + 2) if start >= 0 else -1
            if start < 0 or end < 0:
                if len(self.buffer) > self.MAX_BUFFER:
                    # Keep the tail: a frame boundary may straddle the cut.
                    del self.buffer[:-2]
                continue

            jpeg = bytes(self.buffer[start:end + 2])
            del self.buffer[:end + 2]
            frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                return frame, jpeg

    def close(self) -> None:
        if self.response is not None:
            try:
                self.response.close()
            except Exception:
                pass
        self.response = None
        self.chunks = None
        self.buffer.clear()


@dataclass
class _Rate:
    """Exponentially weighted frames-per-second estimate."""

    ema: float = 0.0
    last: float = 0.0
    alpha: float = 0.1

    def tick(self, now: float) -> float:
        if self.last:
            interval = now - self.last
            if interval > 0:
                instant = 1.0 / interval
                self.ema = instant if self.ema == 0 else (1 - self.alpha) * self.ema + self.alpha * instant
        self.last = now
        return self.ema


class CameraWorker:
    """One camera: an acquisition thread, an analysis thread, one stop flag."""

    def __init__(
        self,
        camera_id: int,
        camera_name: str,
        stream_url: Source = None,
        frame_url: Optional[str] = None,
        # Frame sharing configuration
        use_frame_sharing: bool = False,
        frame_sharing_url: Optional[str] = None,
        frame_sharing_camera_id: Optional[int] = None,
    ) -> None:
        self.camera_id = int(camera_id)
        self.camera_name = camera_name or f"camera-{camera_id}"
        self.stream_url = stream_url
        self.frame_url = frame_url

        # Frame sharing configuration
        self.use_frame_sharing = use_frame_sharing
        self.frame_sharing_url = frame_sharing_url or settings.BASE_API_URL
        self.frame_sharing_camera_id = frame_sharing_camera_id

        self.log = get_logger(f"cam={self.camera_id}")
        self._stop = threading.Event()
        self._slot = _Slot()
        self._threads: list[threading.Thread] = []

        self._seq = 0
        self._source_rate = _Rate()
        self._analysis_rate = _Rate()
        # Set by the acquisition thread after a reconnect: the scene may have
        # changed entirely, and stale tracks would be matched against it.
        self._reset_tracks = threading.Event()
        self._service: Optional[DetectionService] = None
        # Frame URL handling for MJPEG streams (separate from main stream)
        self._mjpeg_reader: Optional[MjpegFrameReader] = None
        self._mjpeg_connected = False
        # HTTP frame sharing session
        self._http_session: Optional[requests.Session] = None

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        if self.use_frame_sharing:
            # Initialize HTTP session for frame sharing
            self._http_session = requests.Session()
            # Start with first frame fetch
            self._fetch_and_publish_initial_frame()
        else:
            # Start the stream manager for this camera (handles cv2.VideoCapture)
            _stream_manager.start_camera(self.camera_id, self.stream_url)

        # Start threads as before, but _acquire_loop will now use appropriate method
        for name, target in (("acquire", self._acquire_loop), ("analyse", self._analyse_loop)):
            thread = threading.Thread(
                target=target, daemon=True, name=f"uod-{name}-{self.camera_id}"
            )
            thread.start()
            self._threads.append(thread)

    def _fetch_and_publish_initial_frame(self) -> None:
        """Fetch an initial frame to prime the pipeline."""
        try:
            frame_jpeg = self._fetch_frame_via_http()
            if frame_jpeg is not None:
                frame = cv2.imdecode(np.frombuffer(frame_jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    self._seq += 1
                    self._slot.publish(frame, self._seq)
                    self.log.info("Initial frame fetched and published via HTTP")
        except Exception as e:
            self.log.warning(f"Failed to fetch initial frame via HTTP: {e}")

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._slot.close()
        for thread in self._threads:
            thread.join(timeout=timeout)
        self._threads.clear()
        # Stop the stream manager for this camera (if not using frame sharing)
        if not self.use_frame_sharing:
            _stream_manager.stop_camera(self.camera_id)
        # Close HTTP session
        if self._http_session:
            self._http_session.close()
            self._http_session = None
        tracking_state.set_processing(self.camera_id, False)
        tracking_state.drop_frames(self.camera_id)
        self.log.info("stopped")

    @property
    def alive(self) -> bool:
        return any(thread.is_alive() for thread in self._threads)

    # -- acquisition ---------------------------------------------------------

    def _open_capture(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(_source(self.stream_url))
        # One-frame device buffer. The default is several frames deep, which is
        # latency the analyser can never recover: it would always be reasoning
        # about a moment that has already passed.
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(f"could not open stream {self.stream_url!r}")
        return cap

    def _acquire_loop(self) -> None:
        if self.use_frame_sharing:
            self._acquire_loop_http()
        else:
            reader: Optional[MjpegFrameReader] = None
            connected = False
            last_stream = 0.0
            stream_interval = 1.0 / max(10.0, settings.target_fps)

            while not self._stop.is_set():
                try:
                    if self.frame_url:
                        if reader is None:
                            reader = MjpegFrameReader(self.frame_url)
                            reader._connect()
                            self._on_connected(connected)
                            connected = True
                        frame, jpeg = reader.read()
                    else:
                        # Get frame from shared stream manager
                        frame = _stream_manager.get_latest_raw_frame(self.camera_id)
                        if frame is None:
                            # No frame available yet, generate no signal frame
                            frame = self._generate_no_signal_frame()
                        jpeg = None  # No JPEG data from raw frame
                except Exception as exc:
                    # Handle MJPEG reader failure
                    if self.frame_url and reader is not None:
                        reader, _ = self._on_failure(exc, reader, None)
                    # For main stream, errors are handled by StreamManager internally
                    # Continue loop to retry getting frame
                    pass

                self._seq += 1
                now = time.monotonic()
                self._source_rate.tick(now)
                self._slot.publish(frame, self._seq)

                # The preview is capped independently of analysis: encoding every
                # frame of a 60fps source would burn a core for frames a browser
                # cannot display anyway.
                if now - last_stream >= stream_interval:
                    last_stream = now
                    self._publish_preview(frame, jpeg, self._seq)

            if reader is not None:
                reader.close()
            self._slot.close()

    def _acquire_loop_http(self) -> None:
        """Acquisition loop that fetches frames via HTTP from smart-surveillance-app."""
        frame_interval = 1.0 / max(1.0, settings.target_fps)  # Minimum interval between frames
        last_fetch_time = 0.0

        while not self._stop.is_set():
            try:
                # Rate limiting to match target FPS
                now = time.monotonic()
                if now - last_fetch_time < frame_interval:
                    time.sleep(min(0.01, frame_interval - (now - last_fetch_time)))
                    continue

                # Fetch frame via HTTP
                frame_jpeg = self._fetch_frame_via_http()
                if frame_jpeg is None:
                    # If we fail to fetch, wait a bit and retry
                    time.sleep(0.1)
                    continue

                # Decode JPEG to frame
                frame = cv2.imdecode(np.frombuffer(frame_jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    self.log.warning("Failed to decode JPEG frame from HTTP")
                    time.sleep(0.1)
                    continue

                # Publish frame to slot
                self._seq += 1
                self._slot.publish(frame, self._seq)
                last_fetch_time = time.monotonic()

                # Update source FPS rate
                self._source_rate.tick(last_fetch_time)

            except Exception as exc:
                throttled(
                    self.log, f"acquire-{self.camera_id}", 30,
                    "HTTP frame acquisition failed: %s -- retrying", exc, interval=15.0,
                )
                tracking_state.set_error(self.camera_id, f"HTTP frame acquisition failed: {exc}")
                time.sleep(min(1.0, settings.reconnect_delay))

    def _fetch_frame_via_http(self) -> Optional[bytes]:
        """Fetch a JPEG frame from smart-surveillance-app's HTTP endpoint."""
        if not self._http_session:
            return None

        try:
            # Construct URL for frame endpoint
            camera_id = self.frame_sharing_camera_id or self.camera_id
            url = f"{self.frame_sharing_url.rstrip('/')}/cameras/{camera_id}/frame"

            # Add cache-busting parameter to ensure we get a fresh frame
            params = {'r': int(time.time() * 1000)}  # Millisecond timestamp

            response = self._http_session.get(url, params=params, timeout=5.0)
            response.raise_for_status()

            # Verify we got JPEG data
            content_type = response.headers.get('content-type', '')
            if 'image/jpeg' not in content_type and not url.endswith('.jpg'):
                # Try to verify it's actually JPEG data by checking magic bytes
                if not response.content.startswith(b'\xff\xd8'):
                    self.log.warning(f"Expected JPEG but got content-type: {content_type}")
                    return None

            return response.content

        except requests.exceptions.RequestException as exc:
            throttled(
                self.log, f"acquire-{self.camera_id}", 30,
                "HTTP request failed: %s", exc, interval=15.0,
            )
            return None
        except Exception as exc:
            self.log.error(f"Unexpected error fetching frame via HTTP: {exc}")
            return None

    def _publish_preview(self, frame: np.ndarray, jpeg: Optional[bytes], seq: int) -> None:
        if not tracking_state.preview_wanted(self.camera_id):
            return
        limit = int(settings.stream_max_width)
        if jpeg is not None and (limit == 0 or frame.shape[1] <= limit):
            payload: Optional[bytes] = jpeg  # already encoded upstream
        else:
            payload = encode_jpeg(frame)
        if payload:
            tracking_state.set_frame(self.camera_id, payload, seq)

    def _on_connected(self, reconnecting: bool) -> None:
        tracking_state.set_processing(self.camera_id, True)
        tracking_state.set_error(self.camera_id, None)
        reset_throttle(f"acquire-{self.camera_id}")
        if reconnecting:
            # A reconnect can land on a different scene, or minutes later. Track
            # ids and owner bindings from before mean nothing now, and keeping
            # them would bind objects to people who left long ago.
            self._reset_tracks.set()
            self.log.info("stream reconnected")
        else:
            self.log.info("connected to %s", self.frame_url or self.stream_url)

    def _on_failure(
        self, exc: Exception, reader: Optional[MjpegFrameReader], cap: Optional[cv2.VideoCapture]
    ) -> Tuple[None, None]:
        throttled(
            self.log, f"acquire-{self.camera_id}", 30,
            "camera unavailable: %s -- retrying every %.1fs", exc, settings.reconnect_delay,
            interval=15.0,
        )
        tracking_state.set_error(self.camera_id, f"Camera stream unavailable: {exc}")
        if reader is not None:
            reader.close()
        if cap is not None:
            cap.release()
        # Wait in slices so a stop request is honoured promptly.
        self._stop.wait(max(0.2, settings.reconnect_delay))
        return None, None

    def _generate_no_signal_frame(self, camera_name="No Signal"):
        """Generate a placeholder frame with text when no signal is available."""
        frame = np.zeros((480, 640, 3), np.uint8)
        text = "NO SIGNAL"
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        x = (frame.shape[1] - text_w) // 2
        y = (frame.shape[0] + text_h) // 2
        cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        return frame

    # -- analysis ------------------------------------------------------------

    def _min_interval(self) -> float:
        """Shortest gap allowed between two analysed frames.

        Two independent caps. ``target_fps`` is an absolute ceiling, so a fast
        machine with a fast camera does not run the GPU flat out for no visible
        benefit. ``detect_every`` is relative to the measured source rate, which
        is what makes it mean the same thing on a 5fps camera and a 60fps one --
        as a bare frame count it silently meant twelve times as much work.
        """
        interval = 1.0 / max(0.5, settings.target_fps)
        every = max(1, int(settings.detect_every))
        source = self._source_rate.ema
        if every > 1 and source > 0:
            interval = max(interval, every / source)
        return interval

    def _analyse_loop(self) -> None:
        try:
            self._service = DetectionService(
                camera_id=self.camera_id, camera_name=self.camera_name
            )
        except Exception as exc:
            # Almost always a missing model file or an unusable device. Fatal for
            # this camera, and the message has to survive: the old code cleared
            # it again on the next results update milliseconds later.
            self.log.error("detection worker could not start: %s", exc, exc_info=True)
            tracking_state.set_error(self.camera_id, f"Detection worker could not start: {exc}")
            tracking_state.set_processing(self.camera_id, False)
            self._stop.set()
            self._slot.close()
            return

        last_processed = 0.0
        while not self._stop.is_set():
            item = self._slot.take(timeout=0.5)
            if item is None:
                continue
            frame, seq = item

            if self._reset_tracks.is_set():
                self._reset_tracks.clear()
                self._service.reset()

            wait = self._min_interval() - (time.monotonic() - last_processed)
            if wait > 0:
                if self._stop.wait(wait):
                    break
                # Something newer almost certainly arrived while pacing. Use it:
                # the point of pacing is to analyse less often, not to analyse
                # older pixels.
                newer = self._slot.take(timeout=0.0)
                if newer is not None:
                    frame, seq = newer

            last_processed = time.monotonic()
            dropped = self._slot.dropped()

            # Process frame with timeout detection to prevent hanging
            process_start = time.monotonic()
            try:
                result = self._service.process(frame, seq=seq, dropped=dropped)
                process_time = time.monotonic() - process_start
                if process_time > 5.0:  # 5 second timeout
                    throttled(
                        self.log, f"analyse-{self.camera_id}", 40,
                        f"Frame processing took too long ({process_time:.1f}s), skipping frame",
                        interval=15.0,
                    )
                    tracking_state.set_error(self.camera_id, f"Frame processing timeout ({process_time:.1f}s)")
                    continue  # Skip this frame, don't publish results
            except Exception as exc:
                throttled(
                    self.log, f"analyse-{self.camera_id}", 40,
                    "frame analysis failed: %s", exc, interval=15.0,
                )
                tracking_state.set_error(self.camera_id, f"Frame analysis failed: {exc}")
                continue

            # Validate result object to prevent downstream errors
            if result is None:
                throttled(
                    self.log, f"analyse-{self.camera_id}", 40,
                    "Detection service returned None result",
                    interval=15.0,
                )
                tracking_state.set_error(self.camera_id, "Detection service returned None result")
                continue

            # Check for required attributes
            required_attrs = ['objects', 'alerts', 'seq', 'width', 'height', 'mode']
            missing_attrs = [attr for attr in required_attrs if not hasattr(result, attr)]
            if missing_attrs:
                throttled(
                    self.log, f"analyse-{self.camera_id}", 40,
                    f"Detection result missing attributes: {missing_attrs}",
                    interval=15.0,
                )
                tracking_state.set_error(self.camera_id, f"Detection result missing attributes: {missing_attrs}")
                continue

            try:
                self._publish(frame, result, dropped)
            except Exception as exc:
                self.log.error(f"Failed to publish results for camera {self.camera_id}: {exc}", exc_info=True)
                tracking_state.set_error(self.camera_id, f"Failed to publish results: {exc}")
                # Continue looping to try to recover on next frame

    def _publish(self, frame: np.ndarray, result, dropped: int) -> None:
        fps = self._analysis_rate.tick(time.monotonic())
        if fps > 0:
            # The tracker's Kalman filter and lost-track buffer are both in
            # frames, so they need the rate frames are actually arriving at.
            self._service.set_frame_rate(fps)

        objects = serialise(result.objects)

        tracking_state.update_results(
            self.camera_id,
            objects,
            result.alerts,
            seq=result.seq,
            frame_size=(result.width, result.height),
        )

        # The frame and the boxes measured from it are handed over as one item.
        # Publishing them separately is what makes an overlay look inaccurate:
        # the client ends up drawing boxes from one moment over pixels from
        # another, and every object appears displaced whenever anything moves.
        if tracking_state.synced_wanted(self.camera_id):
            jpeg = encode_jpeg(frame)
            if jpeg:
                tracking_state.set_synced(
                    self.camera_id, jpeg, result.seq, objects, result.width, result.height,
                )

        metrics = self._service.summarise()
        if metrics is not None:
            metrics.update(
                source_fps=round(self._source_rate.ema, 2),
                analysis_fps=round(fps, 2),
                tile_mode=result.mode,
                last_seq=result.seq,
                frame_width=result.width,
                frame_height=result.height,
            )
            tracking_state.set_metrics(self.camera_id, metrics)

    def stats(self) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            "camera_id": self.camera_id,
            "camera_name": self.camera_name,
            "source": self.frame_url or self.stream_url if not self.use_frame_sharing else f"HTTP:{self.frame_sharing_url}/cameras/{self.frame_sharing_camera_id or self.camera_id}/frame",
            "alive": self.alive,
            "source_fps": round(self._source_rate.ema, 2),
            "analysis_fps": round(self._analysis_rate.ema, 2),
            "frames_acquired": self._seq,
            "min_analysis_interval_ms": round(self._min_interval() * 1000, 1),
        }
        if self._service is not None:
            base.update(self._service.stats())
        return base


# ---------------------------------------------------------------------------
# Registry -- what the API calls
# ---------------------------------------------------------------------------

_workers: Dict[int, CameraWorker] = {}
_workers_lock = threading.Lock()


def start_camera(
    camera_id: int,
    camera_name: str,
    stream_url: Source = None,
    frame_url: Optional[str] = None,
    # Frame sharing parameters
    use_frame_sharing: bool = False,
    frame_sharing_url: Optional[str] = None,
    frame_sharing_camera_id: Optional[int] = None,
) -> bool:
    """Start processing a camera. False if it was already running."""
    with _workers_lock:
        existing = _workers.get(int(camera_id))
        if existing is not None and existing.alive:
            return False
        worker = CameraWorker(
            camera_id=camera_id,
            camera_name=camera_name,
            stream_url=stream_url,
            frame_url=frame_url,
            use_frame_sharing=use_frame_sharing,
            frame_sharing_url=frame_sharing_url,
            frame_sharing_camera_id=frame_sharing_camera_id,
        )
        _workers[int(camera_id)] = worker
    worker.start()
    return True


def stop_camera(camera_id: int) -> bool:
    with _workers_lock:
        worker = _workers.pop(int(camera_id), None)
    if worker is None:
        return False
    worker.stop()
    return True


def stop_all() -> None:
    with _workers_lock:
        workers = list(_workers.values())
        _workers.clear()
    for worker in workers:
        worker.stop()


def is_running(camera_id: int) -> bool:
    with _workers_lock:
        worker = _workers.get(int(camera_id))
    return bool(worker and worker.alive)


def running_cameras() -> list:
    with _workers_lock:
        return sorted(cid for cid, worker in _workers.items() if worker.alive)


def worker_stats(camera_id: Optional[int] = None) -> Any:
    """Per-camera pipeline statistics for the performance endpoint."""
    with _workers_lock:
        workers = dict(_workers)
    if camera_id is not None:
        worker = workers.get(int(camera_id))
        return worker.stats() if worker else {}
    return [worker.stats() for worker in workers.values()]