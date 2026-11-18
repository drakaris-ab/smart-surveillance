# shared/stream/stream_manager.py
import cv2
import numpy as np
import time
import threading
from threading import Lock

class StreamManager:
    """
    Manages video capture streams and allows multiple camera IDs to share the same video source.
    Only opens a single capture per unique stream URL and shares frames among all camera IDs
    pointing to that URL.
    """

    def __init__(self):
        # Map of camera_id -> latest raw frame (copy-on-write for safety)
        self.latest_raw_frame = {}
        # Map of camera_id -> last update timestamp
        self.last_update = {}
        # Map of camera_id -> health status (bool)
        self.camera_health = {}
        # Map of camera_id -> stop flag (bool)
        self.stop_flags = {}
        # Map of camera_id -> reader thread
        self.reader_threads = {}
        # Map of normalized stream URL -> cv2.VideoCapture object (shared capture)
        self.captures = {}
        # Map of camera_id -> normalized stream URL
        self.stream_urls = {}

        # Thread safety locks
        self.lock = Lock()          # protects shared state: latest_raw_frame, last_update, camera_health, captures, stream_urls
        self.init_lock = Lock()     # protects capture initialization and shared reader logic

    def _normalize_stream_url(self, url):
        """Normalize stream URL for comparison (handles webcam index 0)."""
        if url is None:
            return ""
        s = str(url).strip()
        if s in ["0", "0.0"]:
            return "0"
        return s

    def _generate_no_signal_frame(self, camera_name="No Signal"):
        """Generate a placeholder frame with text when no signal is available."""
        frame = np.zeros((480, 640, 3), np.uint8)
        text = "NO SIGNAL"
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        x = (frame.shape[1] - text_w) // 2
        y = (frame.shape[0] + text_h) // 2
        cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        return frame

    def _set_camera_health(self, camera_id, connected):
        """Set the health status for a camera."""
        with self.lock:
            self.camera_health[camera_id] = bool(connected)

    def is_camera_connected(self, camera_id):
        """Check if a camera is connected (healthy and recently updated)."""
        with self.lock:
            connected = self.camera_health.get(camera_id, False)
            last = self.last_update.get(camera_id)
        if not connected or last is None:
            return False
        return (time.time() - last) <= 2.0

    def get_latest_raw_frame(self, camera_id):
        """Get a copy of the latest raw frame for a camera ID."""
        with self.lock:
            frame = self.latest_raw_frame.get(camera_id)
            if frame is None:
                return None
            return frame.copy()

    def start_camera(self, camera_id, stream_url):
        """Start capturing frames for a camera ID from the given stream URL."""
        # Ensure any previous state for this camera is cleaned up
        if camera_id in self.stop_flags:
            self.stop_flags[camera_id] = True
            time.sleep(0.3)  # Allow previous thread to exit

        with self.lock:
            self.stop_flags[camera_id] = False
            self.stream_urls[camera_id] = stream_url
            self.latest_raw_frame[camera_id] = self._generate_no_signal_frame()
            self.camera_health[camera_id] = False
            self.last_update[camera_id] = time.time()

        # Start the reader thread for this camera
        reader = threading.Thread(
            target=self._frame_reader,
            args=(camera_id, stream_url),
            daemon=True,
        )
        self.reader_threads[camera_id] = reader
        reader.start()

    def stop_camera(self, camera_id):
        """Stop capturing frames for a camera ID and clean up resources."""
        # Signal the reader thread to stop
        with self.lock:
            if camera_id in self.stop_flags:
                self.stop_flags[camera_id] = True

        # Wait for the reader thread to finish
        t = self.reader_threads.get(camera_id)
        if t:
            try:
                t.join(timeout=2)
            except Exception:
                pass
            self.reader_threads.pop(camera_id, None)

        # Clean up camera-specific state
        with self.lock:
            self.stream_urls.pop(camera_id, None)
            self.latest_raw_frame[camera_id] = None
            self.last_update.pop(camera_id, None)
            self.camera_health.pop(camera_id, None)
            self.stop_flags.pop(camera_id, None)

        # Note: We do not release the shared capture here; it is released when the last camera using it stops.
        # The capture is released in _frame_reader when the stop flag is set and the loop exits.

    def _frame_reader(self, camera_id, stream_url):
        """Reader thread function for a single camera ID."""
        norm_url = self._normalize_stream_url(stream_url)
        source = 0 if norm_url == "0" else stream_url
        is_webcam = (norm_url == "0" or source == 0)

        while not self.stop_flags.get(camera_id, False):
            # Check if another camera is already capturing this stream URL
            shared_camera_id = None
            with self.lock:
                for cid, url in list(self.stream_urls.items()):
                    if cid != camera_id and self._normalize_stream_url(url) == norm_url:
                        if cid in self.captures and self.captures[cid] is not None:
                            shared_camera_id = cid
                            break

            if shared_camera_id is not None:
                # Share frames from the existing capture
                with self.lock:
                    frame = self.latest_raw_frame.get(shared_camera_id)
                if frame is not None:
                    with self.lock:
                        self.latest_raw_frame[camera_id] = frame.copy()
                        self.last_update[camera_id] = time.time()
                    self._set_camera_health(camera_id, True)
                else:
                    self._set_camera_health(camera_id, False)
                time.sleep(0.03)  # ~30 FPS
                continue

            # No existing capture for this URL; we need to open our own
            self._set_camera_health(camera_id, False)
            cap = None

            def _open_capture():
                nonlocal cap
                backends = []
                if isinstance(source, str) and source.startswith("rtsp://"):
                    backends = [cv2.CAP_FFMPEG]
                elif is_webcam:
                    # Try multiple backends, explicitly avoiding MSMF if possible
                    backends = [cv2.CAP_DSHOW, cv2.CAP_FFMPEG, 0]
                else:
                    backends = [0]

                for backend in backends:
                    try:
                        src = int(source) if str(source).isdigit() else source
                        c = cv2.VideoCapture(src, backend)
                        if c.isOpened():
                            try:
                                c.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            except Exception:
                                pass
                            # Test that we can actually read a frame
                            ret, test_frame = c.read()
                            if ret and test_frame is not None:
                                print(f"[INFO] Camera {camera_id} opened with backend {backend}")
                                cap = c
                                break
                            else:
                                print(f"[WARN] Camera {camera_id} opened with backend {backend} but cannot read frames")
                                c.release()
                        else:
                            c.release()
                    except Exception:
                        pass

            if is_webcam:
                with self.init_lock:
                    # Double-check inside lock if another camera started capturing while we waited
                    already_opened = False
                    shared_camera_id = None
                    with self.lock:
                        for cid, url in list(self.stream_urls.items()):
                            if cid != camera_id and self._normalize_stream_url(url) == norm_url:
                                if cid in self.captures and self.captures[cid] is not None:
                                    already_opened = True
                                    shared_camera_id = cid
                                    break

                    if already_opened:
                        # Shadow mode: copy frames from existing capture
                        while not self.stop_flags.get(camera_id, False):
                            # Check if shared camera is still valid
                            shared_still_valid = False
                            with self.lock:
                                if (shared_camera_id in self.stream_urls and
                                    self.stream_urls[shared_camera_id] is not None and
                                    shared_camera_id in self.captures and
                                    self.captures[shared_camera_id] is not None and
                                    self.camera_health.get(shared_camera_id, False)):
                                    shared_still_valid = True
                            if not shared_still_valid:
                                break  # Shared camera gone; break to try own capture

                            # Copy frame from shared camera
                            with self.lock:
                                frame = self.latest_raw_frame.get(shared_camera_id)
                            if frame is not None:
                                with self.lock:
                                    self.latest_raw_frame[camera_id] = frame.copy()
                                    self.last_update[camera_id] = time.time()
                                self._set_camera_health(camera_id, True)
                            else:
                                self._set_camera_health(camera_id, False)
                            time.sleep(0.03)
                            continue
                        # Exit shadow loop; fall through to try own capture

                    # If not already opened or shared camera lost, try to open our own capture
                    _open_capture()

                    if cap is not None and cap.isOpened():
                        with self.lock:
                            self.captures[camera_id] = cap
                            self.camera_health[camera_id] = True
            else:
                _open_capture()
                if cap is not None and cap.isOpened():
                    with self.lock:
                        self.captures[camera_id] = cap
                        self.camera_health[camera_id] = True

            if cap is None or not cap.isOpened():
                print(f"[ERROR] Failed to open video source for camera {camera_id}: {stream_url}, retrying...")
                with self.lock:
                    self.latest_raw_frame[camera_id] = self._generate_no_signal_frame()
                time.sleep(2)
                continue

            # Main capture loop
            while not self.stop_flags.get(camera_id, False):
                ret, frame = cap.read()
                if not ret or frame is None:
                    print(f"[WARN] Camera {camera_id} lost signal, reconnecting...")
                    with self.lock:
                        self.camera_health[camera_id] = False
                        self.latest_raw_frame[camera_id] = self._generate_no_signal_frame()
                    cap.release()
                    time.sleep(2)
                    break

                with self.lock:
                    self.latest_raw_frame[camera_id] = frame.copy()
                    self.last_update[camera_id] = time.time()

            # Clean up capture for this camera
            with self.lock:
                if camera_id in self.captures:
                    self.captures[camera_id].release()
                    del self.captures[camera_id]

        print(f"[INFO] Camera {camera_id} reader stopped")

    def stop_all(self):
        """Stop all camera readers and release all captures."""
        with self.lock:
            for cid in list(self.stop_flags.keys()):
                self.stop_flags[cid] = True

        # Wait for all reader threads to finish
        for cid, t in list(self.reader_threads.items()):
            try:
                t.join(timeout=2)
            except Exception:
                pass

        # Release all captures
        with self.lock:
            for cap in list(self.captures.values()):
                try:
                    cap.release()
                except Exception:
                    pass
            self.captures.clear()

        # Clear all state
        with self.lock:
            self.reader_threads.clear()
            self.stream_urls.clear()
            self.latest_raw_frame.clear()
            self.last_update.clear()
            self.camera_health.clear()
            self.stop_flags.clear()