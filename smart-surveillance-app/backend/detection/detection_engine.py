# detection_engine.py
import time
import random
import cv2
import numpy as np

class DetectionEngine:
    def __init__(self, model, device="cuda", quantize="fp32", zone_manager=None, alert_manager=None):
        self.model = model
        self.device = device
        self.quantize = quantize   # ✅ use quantize instead of use_half
        self.zone_manager = zone_manager
        self.alert_manager = alert_manager

        # Shared state (wired externally by YOLODetector)
        self.lock = None
        self.batch_stop_event = None
        self.stop_flags = {}
        self.latest_raw_frame = {}
        self.output_frames = {}

        # Config values (refreshed externally)
        self.conf_threshold = 0.5
        self.inference_size = 416
        self.person_class_id = 0
        self.target_infer_fps = 6.0

        # Per-camera state
        self._zone_reload_ts = {}
        self._next_snapshot_at = {}
        self._intrusion_prev = {}

    def run_batch_loop(self):
        print("[BATCH DETECTOR STARTED]")
        while not self.batch_stop_event.is_set():
            loop_start = time.time()
            min_interval = 1.0 / max(self.target_infer_fps, 0.1)

            with self.lock:
                active_ids = [cid for cid, stopped in self.stop_flags.items() if not stopped]

            if not active_ids:
                time.sleep(0.05)
                continue

            batch_frames, batch_meta = [], []
            for cid in active_ids:
                with self.lock:
                    raw = self.latest_raw_frame.get(cid)
                if raw is None:
                    with self.lock:
                        self.output_frames[cid] = self._generate_no_signal_frame()
                    continue

                frame = raw.copy()
                resized = cv2.resize(frame, (self.inference_size, self.inference_size))
                batch_frames.append(resized)
                batch_meta.append((cid, frame))

            if not batch_frames:
                time.sleep(0.05)
                continue

            try:
                results = self.model.predict(
                    batch_frames,
                    imgsz=self.inference_size,
                    conf=self.conf_threshold,
                    classes=[self.person_class_id],
                    device=self.device,
                    quantize=self.quantize,   # ✅ updated
                    verbose=False,
                )
            except Exception as e:
                print(f"[WARN] batch predict error: {e}")
                time.sleep(0.02)
                continue

            for (cid, frame), result in zip(batch_meta, results):
                try:
                    self.process_result(cid, frame, result)
                except Exception as e:
                    print(f"[WARN] error processing result for camera {cid}: {e}")

            elapsed = time.time() - loop_start
            remaining = min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)

        print("[BATCH DETECTOR STOPPED]")

    def process_result(self, camera_id, frame, result):
        """Apply zone/intrusion logic to a single camera's inference result"""
        now = time.time()
        if now - self._zone_reload_ts.get(camera_id, 0.0) > 10:
            zones = self.zone_manager.load_zones(camera_id)
            self._zone_reload_ts[camera_id] = now
        else:
            zones = self.zone_manager.load_zones(camera_id)

        muted_now = self.alert_manager.is_muted(camera_id) if self.alert_manager else False

        detections = []
        try:
            boxes = result.boxes if result is not None and hasattr(result, "boxes") else None
            if boxes is not None and len(boxes):
                detections = boxes.data.cpu().numpy()
        except Exception:
            detections = []

        h_ratio = frame.shape[0] / max(self.inference_size, 1)
        w_ratio = frame.shape[1] / max(self.inference_size, 1)

        intruder_present, intruder_zone = False, None

        for det in detections:
            x1, y1, x2, y2, conf, cls = det[:6]
            if conf < self.conf_threshold:
                continue
            cls_name = str(self.model.names.get(int(cls), str(int(cls)))).lower()
            if cls_name != "person":
                continue

            x1, y1, x2, y2 = (
                int(x1 * w_ratio),
                int(y1 * h_ratio),
                int(x2 * w_ratio),
                int(y2 * h_ratio),
            )

            bbox_area = (x2 - x1) * (y2 - y1)
            threshold = 0.003 if bbox_area < 6000 else 0.01

            crossed = None
            for z in zones:
                overlap_ratio = self.zone_manager.person_zone_overlap_ratio((x1, y1, x2, y2), z["points"])
                if overlap_ratio >= threshold:
                    crossed = z
                    intruder_present = True
                    intruder_zone = z
                    break

            color = (0, 0, 255) if crossed else (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        now_ts = time.time()
        prev_active = self._intrusion_prev.get(camera_id, False)

        if intruder_present and not prev_active:
            self._next_snapshot_at[camera_id] = now_ts

        if intruder_present and now_ts >= self._next_snapshot_at.get(camera_id, 0.0):
            if muted_now:
                print(f"[HARD BLOCK] Muted - skipping alert for camera {camera_id}")
            else:
                self.alert_manager.handle_alert_async(camera_id, frame, intruder_zone)

            self._next_snapshot_at[camera_id] = now_ts + random.uniform(5.0, 10.0)

        if not intruder_present:
            self._next_snapshot_at[camera_id] = 0.0

        self._intrusion_prev[camera_id] = intruder_present

        self.zone_manager.draw_zones(frame, zones, thickness=4)
        if intruder_present:
            self.zone_manager.draw_intrusion_border(frame)

        with self.lock:
            self.output_frames[camera_id] = frame

    def _generate_no_signal_frame(self):
        frame = np.zeros((480, 640, 3), np.uint8)
        cv2.putText(frame, "NO SIGNAL", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        return frame
