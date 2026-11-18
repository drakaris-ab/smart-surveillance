# camera_manager.py
import cv2
import numpy as np
import time
import threading

class CameraManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.init_lock = threading.Lock()
        self.captures = {}
        self.camera_health = {}
        self.latest_raw_frame = {}
        self.last_update = {}
        self.output_frames = {}
        self.stop_flags = {}
        self.stream_urls = {}

    def _generate_no_signal_frame(self):
        """Return a red 'NO SIGNAL' frame"""
        frame = np.zeros((480, 640, 3), np.uint8)
        text = "NO SIGNAL"
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        x = (frame.shape[1] - text_w) // 2
        y = (frame.shape[0] + text_h) // 2
        cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        return frame

    def _set_camera_health(self, camera_id, connected):
        with self.lock:
            self.camera_health[camera_id] = bool(connected)

    def is_camera_connected(self, camera_id):
        with self.lock:
            connected = self.camera_health.get(camera_id, False)
            last = self.last_update.get(camera_id)
        if not connected or last is None:
            return False
        return (time.time() - last) <= 2.0

    def get_latest_raw_frame(self, camera_id):
        with self.lock:
            frame = self.latest_raw_frame.get(camera_id)
            if frame is None:
                return None
            return frame.copy()

    def get_frame(self, camera_id):
        """Return processed frame or NO SIGNAL frame"""
        with self.lock:
            frame = self.output_frames.get(camera_id)
        if frame is None:
            return self._generate_no_signal_frame()
        return frame

    def _normalize_stream_url(self, url):
        if url is None:
            return ""
        s = str(url).strip()
        if s in ["0", "0.0"]:
            return "0"
        return s

    def start_reader(self, camera_id, stream_url):
        """Start a thread to read frames from a camera"""
        self.stop_flags[camera_id] = False
        self.stream_urls[camera_id] = stream_url
        self.output_frames[camera_id] = self._generate_no_signal_frame()
        self.camera_health[camera_id] = False

        reader = threading.Thread(
            target=self._frame_reader,
            args=(camera_id, stream_url),
            daemon=True,
        )
        reader.start()
        return reader

    def _frame_reader(self, camera_id, stream_url):
        """Internal loop for reading frames from a camera"""
        norm_url = self._normalize_stream_url(stream_url)
        source = 0 if norm_url == "0" else stream_url
        is_webcam = (norm_url == "0" or source == 0)

        while not self.stop_flags.get(camera_id, False):
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                print(f"[ERROR] Failed to open video source for camera {camera_id}: {stream_url}")
                with self.lock:
                    self.output_frames[camera_id] = self._generate_no_signal_frame()
                time.sleep(2)
                continue

            while not self.stop_flags.get(camera_id, False):
                ret, frame = cap.read()
                if not ret or frame is None:
                    print(f"[WARN] Camera {camera_id} lost signal, reconnecting...")
                    with self.lock:
                        self.camera_health[camera_id] = False
                        self.output_frames[camera_id] = self._generate_no_signal_frame()
                        self.captures.pop(camera_id, None)
                    cap.release()
                    time.sleep(2)
                    break

                with self.lock:
                    self.latest_raw_frame[camera_id] = frame
                    self.last_update[camera_id] = time.time()
                    self.camera_health[camera_id] = True

            with self.lock:
                self.captures.pop(camera_id, None)

        print(f"[INFO] Camera {camera_id} reader stopped")

    def stop_all(self):
        """Stop all camera readers and release resources"""
        with self.lock:
            for cid in list(self.stop_flags.keys()):
                self.stop_flags[cid] = True

        for _, cap in list(self.captures.items()):
            try:
                cap.release()
            except Exception:
                pass

        with self.lock:
            self.captures.clear()
            self.stop_flags.clear()
            self.output_frames.clear()
            self.latest_raw_frame.clear()
            self.camera_health.clear()
            self.stream_urls.clear()

        print("[INFO] All cameras stopped")
