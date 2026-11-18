# # app/detection/yolo_detector.py
# import cv2
# import numpy as np
# import time
# import json
# import random
# import threading
# from concurrent.futures import ThreadPoolExecutor

# import torch
# from ultralytics import YOLO

# from backend.database import SessionLocal, BoundaryZone
# from backend.utils.config import load_config
# from backend.services.alert_service import AlertService
# from backend.services.config_service import get_config
# from backend.config.logging_config import logger
# from backend.config.messages import MESSAGES

# config = load_config()


# class YOLODetector:
   
#     def __init__(self, model_path="yolov8s.pt", conf_threshold=0.5, alert_cooldown=3.0):
#         self.model = YOLO(model_path) if YOLO is not None else None
#         self.MIN_CONF = conf_threshold
#         self.ALERT_COOLDOWN = alert_cooldown
#         self.FRAME_SIZE = 640
#         self.IMAGE_SIZE = 416
#         self.FOCAL_LENGTH = 24.0
#         self.INFERENCE_SIZE = 416
#         self.TARGET_INFER_FPS = 6.0
#         self._last_config_refresh = 0.0
#         self._last_config_signature = None

#         # GPU / precision setup - run on GPU with FP16 if available, since
#         # this is the single biggest lever for throughput on constrained
#         # hardware. Falls back cleanly to CPU/FP32 if no CUDA device exists.
#         self.device = "cuda" if torch.cuda.is_available() else "cpu"
#         self.use_half = self.device == "cuda"

#         if self.device == "cuda":
#             logger.info("[YOLO DETECTOR] Running on GPU (CUDA, FP16 enabled)")
#         else:
#             logger.info("[YOLO DETECTOR] Running on CPU (FP32 only)")
#         if self.model is not None:
#             try:
#                 self.model.to(self.device)
#             except Exception as e:
#                 print(f"[WARN] Could not move model to {self.device}: {e}")

#         # Resolve the "person" class id dynamically instead of hardcoding 0,
#         # so custom-trained models with a different class ordering still work.
#         self.person_class_id = 0
#         if self.model is not None:
#             try:
#                 for idx, name in self.model.names.items():
#                     if str(name).lower() == "person":
#                         self.person_class_id = int(idx)
#                         break
#             except Exception:
#                 pass

#         # Increase worker threads for better multi-camera support
#         self.sound_executor = ThreadPoolExecutor(max_workers=8)

#         # Reader threads: one lightweight I/O thread per camera (unchanged).
#         self.reader_threads = {}
#         # Detection is now a SINGLE shared batch thread across all cameras.
#         self.batch_thread = None
#         self.batch_stop_event = threading.Event()
#         # Kept for backward compatibility with any external code that
#         # inspects detector.detection_threads[camera_id] (e.g. liveness
#         # checks) - all camera ids point at the same shared batch thread.
#         self.detection_threads = {}

#         self.stop_flags = {}
#         self.output_frames = {}
#         self.latest_raw_frame = {}
#         self.lock = threading.Lock()
#         self.init_lock = threading.Lock()
#         self.captures = {}

#         self._mute_cache = {}
#         self._mute_cache_ts = {}
#         self.alert_service = AlertService(config)
#         self.stream_urls = {}
#         self.last_update = {}
#         self.camera_health = {}
#         self.zones_cache = {}  # Cache zones to reduce DB hits
#         self.zones_cache_time = {}  # Track when zones were cached

#         # Per-camera state for the shared batch loop (previously local
#         # variables inside detect_camera(), now keyed by camera_id).
#         self._zone_reload_ts = {}
#         self._next_snapshot_at = {}
#         self._intrusion_prev = {}

#     def _refresh_runtime_config(self):
#         now = time.time()
#         if now - self._last_config_refresh < 5.0 and self._last_config_signature is not None:
#             return

#         try:
#             db = SessionLocal()
#             try:
#                 cfg = get_config(db)
#             finally:
#                 db.close()
#         except Exception as exc:
#             logger.warning(MESSAGES["config_refresh_failed"].format(error=str(exc)))
#             return

#         if cfg is None:
#             logger.warning(MESSAGES["config_missing"])
#             return

#         try:
#             # handle both SQLAlchemy model and dict cases
#             conf = getattr(cfg, "confidenceThreshold", None) or (cfg.get("confidenceThreshold") if isinstance(cfg, dict) else self.MIN_CONF)
#             frame_size = getattr(cfg, "frameSize", None) or (cfg.get("frameSize") if isinstance(cfg, dict) else self.FRAME_SIZE)
#             image_size = getattr(cfg, "imageSize", None) or (cfg.get("imageSize") if isinstance(cfg, dict) else self.IMAGE_SIZE)
#             focal_length = getattr(cfg, "focalLength", None) or (cfg.get("focalLength") if isinstance(cfg, dict) else self.FOCAL_LENGTH)
#             inference_size = getattr(cfg, "inferenceSize", None) or (cfg.get("inferenceSize") if isinstance(cfg, dict) else self.INFERENCE_SIZE)

#             signature = {
#                 "confidenceThreshold": conf,
#                 "frameSize": frame_size,
#                 "imageSize": image_size,
#                 "focalLength": focal_length,
#                 "inferenceSize": inference_size,
#             }

#             if signature == self._last_config_signature:
#                 self._last_config_refresh = now
#                 return

#             self.MIN_CONF = float(conf)
#             self.FRAME_SIZE = int(frame_size)
#             self.IMAGE_SIZE = int(image_size)
#             self.FOCAL_LENGTH = float(focal_length)
#             self.INFERENCE_SIZE = int(inference_size)
#             self._last_config_refresh = now
#             self._last_config_signature = signature

#             logger.info(MESSAGES["config_applied"].format(
#                 conf=self.MIN_CONF,
#                 frame_size=self.FRAME_SIZE,
#                 image_size=self.IMAGE_SIZE,
#                 focal_length=self.FOCAL_LENGTH,
#                 inference_size=self.INFERENCE_SIZE
#             ))
#         except Exception as e:
#             logger.exception(MESSAGES["config_apply_failed"].format(error=str(e)))


#     def _generate_no_signal_frame(self, camera_name="No Signal"):
#         frame = np.zeros((480, 640, 3), np.uint8)
#         text = "NO SIGNAL"
#         (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
#         x = (frame.shape[1] - text_w) // 2
#         y = (frame.shape[0] + text_h) // 2
#         cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
#         return frame

#     def _set_camera_health(self, camera_id, connected):
#         with self.lock:
#             self.camera_health[camera_id] = bool(connected)

#     def is_camera_connected(self, camera_id):
#         with self.lock:
#             connected = self.camera_health.get(camera_id, False)
#             last = self.last_update.get(camera_id)
#         if not connected or last is None:
#             return False
#         return (time.time() - last) <= 2.0

#     def get_latest_raw_frame(self, camera_id):
#         with self.lock:
#             frame = self.latest_raw_frame.get(camera_id)
#             if frame is None:
#                 return None
#             return frame.copy() 

#     def load_zones(self, camera_id):
#         """Load zones with caching to reduce database hits"""
#         now = time.time()
#         # Use cached zones if available and less than 10 seconds old
#         if camera_id in self.zones_cache:
#             cache_time = self.zones_cache_time.get(camera_id, 0)
#             if now - cache_time < 10:
#                 return self.zones_cache[camera_id]

#         db = SessionLocal()
#         zones = db.query(BoundaryZone).filter(BoundaryZone.camera_id == camera_id).all()
#         db.close()
#         loaded = []
#         for z in zones:
#             try:
#                 # Support both z.points and z.polygon_coords database schemas
#                 points_field = getattr(z, "points", None) or getattr(z, "polygon_coords", None)
#                 pts = json.loads(points_field) if isinstance(points_field, str) else points_field

#                 parsed_pts = []
#                 for p in pts:
#                     if isinstance(p, dict):
#                         parsed_pts.append((p["x"], p["y"]))
#                     elif isinstance(p, (list, tuple)) and len(p) >= 2:
#                         parsed_pts.append((p[0], p[1]))
#                 pts = np.array(parsed_pts, np.int32)

#                 # Support both z.name and default f"Zone {z.id}"
#                 name_field = getattr(z, "name", None) or f"Zone {z.id}"

#                 loaded.append({"id": z.id, "name": name_field, "points": pts})
#             except Exception as e:
#                 print(f"[WARN] Error loading zone {z.id}: {e}")

#         # Cache the zones
#         self.zones_cache[camera_id] = loaded
#         self.zones_cache_time[camera_id] = now
#         return loaded

#     def _person_zone_overlap_ratio(self, bbox, polygon):
#         x1, y1, x2, y2 = bbox
#         x1 = int(max(0, x1))
#         y1 = int(max(0, y1))
#         x2 = int(max(x1 + 1, x2))
#         y2 = int(max(y1 + 1, y2))

#         bbox_w = x2 - x1
#         bbox_h = y2 - y1
#         bbox_area = float(bbox_w * bbox_h)
#         if bbox_area <= 0:
#             return 0.0

#         try:
#             roi_poly = polygon.copy()
#             roi_poly[:, 0] = roi_poly[:, 0] - x1
#             roi_poly[:, 1] = roi_poly[:, 1] - y1
#             zone_mask = np.zeros((bbox_h, bbox_w), dtype=np.uint8)
#             cv2.fillPoly(zone_mask, [roi_poly], 255)
#             overlap_pixels = cv2.countNonZero(zone_mask)
#             return overlap_pixels / bbox_area
#         except Exception:
#             return 0.0

#     def _draw_zones(self, frame, zones, thickness=4):
#         for z in zones:
#             try:
#                 cv2.polylines(frame, [z["points"]], True, (0, 255, 255), thickness)
#             except Exception:
#                 pass

#     def _draw_intrusion_border(self, frame):
#         # Blink red border only during intrusion.
#         if int(time.time() * 3) % 2 == 0:
#             cv2.rectangle(frame, (0, 0), (frame.shape[1] - 1, frame.shape[0] - 1), (0, 0, 255), 6)

#     def _normalize_stream_url(self, url):
#         if url is None:
#             return ""
#         s = str(url).strip()
#         if s in ["0", "0.0"]:
#             return "0"
#         return s

#     def _frame_reader(self, camera_id, stream_url):
#         norm_url = self._normalize_stream_url(stream_url)
#         source = 0 if norm_url == "0" else stream_url
#         is_webcam = (norm_url == "0" or source == 0)

#         while not self.stop_flags.get(camera_id, False):
#             # Check if another camera is physically capturing this exact stream_url
#             shared_camera_id = None
#             with self.lock:
#                 for cid, url in list(self.stream_urls.items()):
#                     if cid != camera_id and self._normalize_stream_url(url) == norm_url and self.camera_health.get(cid, False):
#                         if cid in self.captures and self.captures[cid] is not None:
#                             shared_camera_id = cid
#                             break

#             if shared_camera_id is not None:
#                 with self.lock:
#                     frame = self.latest_raw_frame.get(shared_camera_id)
#                 if frame is not None:
#                     with self.lock:
#                         self.latest_raw_frame[camera_id] = frame
#                         self.last_update[camera_id] = time.time()
#                     self._set_camera_health(camera_id, True)
#                 else:
#                     self._set_camera_health(camera_id, False)
#                 time.sleep(0.03)  # roughly 30 fps
#                 continue

#             self._set_camera_health(camera_id, False)
#             cap = None

#             def _open_capture():
#                 nonlocal cap
#                 backends = []
#                 if isinstance(source, str) and source.startswith("rtsp://"):
#                     backends = [cv2.CAP_FFMPEG]
#                 elif is_webcam:
#                     backends = [0, cv2.CAP_DSHOW, cv2.CAP_MSMF]
#                 else:
#                     backends = [0]

#                 for backend in backends:
#                     try:
#                         src = int(source) if str(source).isdigit() else source
#                         c = cv2.VideoCapture(src, backend)
#                         if c.isOpened():
#                             try:
#                                 c.set(cv2.CAP_PROP_BUFFERSIZE, 1)
#                             except Exception:
#                                 pass
#                             print(f"[INFO] Camera {camera_id} opened with backend {backend}")
#                             cap = c
#                             break
#                         c.release()
#                     except Exception:
#                         pass

#             if is_webcam:
#                 with self.init_lock:
#                     # Double check inside lock
#                     already_opened = False
#                     with self.lock:
#                         for cid, url in list(self.stream_urls.items()):
#                             if cid != camera_id and self._normalize_stream_url(url) == norm_url and self.camera_health.get(cid, False):
#                                 if cid in self.captures and self.captures[cid] is not None:
#                                     already_opened = True
#                                     break

#                     if already_opened:
#                         continue

#                     _open_capture()

#                     if cap is not None and cap.isOpened():
#                         with self.lock:
#                             self.captures[camera_id] = cap
#                             self.camera_health[camera_id] = True
#             else:
#                 _open_capture()
#                 if cap is not None and cap.isOpened():
#                     with self.lock:
#                         self.captures[camera_id] = cap
#                         self.camera_health[camera_id] = True

#             if cap is None or not cap.isOpened():
#                 print(f"[ERROR] Failed to open video source for camera {camera_id}: {stream_url}, retrying...")
#                 with self.lock:
#                     self.output_frames[camera_id] = self._generate_no_signal_frame()
#                 time.sleep(2)
#                 continue

#             while not self.stop_flags.get(camera_id, False):
#                 ret, frame = cap.read()
#                 if not ret or frame is None:
#                     print(f"[WARN] Camera {camera_id} lost signal, reconnecting...")
#                     with self.lock:
#                         self.camera_health[camera_id] = False
#                         self.output_frames[camera_id] = self._generate_no_signal_frame()
#                         self.captures.pop(camera_id, None)
#                     cap.release()
#                     time.sleep(2)
#                     break

#                 with self.lock:
#                     self.latest_raw_frame[camera_id] = frame
#                     self.last_update[camera_id] = time.time()

#             with self.lock:
#                 self.captures.pop(camera_id, None)

#         print(f"[INFO] Camera {camera_id} reader stopped")

#     # ------------------------------------------------------------------
#     # Shared batched detection loop (replaces the old per-camera
#     # detect_camera() thread). One pass = one GPU forward call covering
#     # every active camera's latest frame.
#     # ------------------------------------------------------------------
#     def _batch_detect_loop(self):
#         print("[BATCH DETECTOR STARTED]")

#         while not self.batch_stop_event.is_set():
#             loop_start = time.time()
#             self._refresh_runtime_config()
#             min_interval = 1.0 / max(self.TARGET_INFER_FPS, 0.1)

#             with self.lock:
#                 active_ids = [cid for cid, stopped in self.stop_flags.items() if not stopped]

#             if not active_ids:
#                 time.sleep(0.05)
#                 continue

#             batch_frames = []
#             batch_meta = []  # (camera_id, original_resolution_frame)

#             for cid in active_ids:
#                 with self.lock:
#                     raw = self.latest_raw_frame.get(cid)
#                 if raw is None:
#                     with self.lock:
#                         self.output_frames[cid] = self._generate_no_signal_frame()
#                     continue

#                 frame = raw.copy()
#                 # Single resize, straight to inference size (previously this
#                 # was resized twice in Python plus once more internally).
#                 resized = cv2.resize(frame, (self.INFERENCE_SIZE, self.INFERENCE_SIZE))
#                 batch_frames.append(resized)
#                 batch_meta.append((cid, frame))

#             if not batch_frames:
#                 time.sleep(0.05)
#                 continue

#             try:
#                 results = self.model.predict(
#                     batch_frames,
#                     imgsz=self.INFERENCE_SIZE,
#                     conf=self.MIN_CONF,
#                     classes=[self.person_class_id],
#                     quantize="fp16" if self.use_half else "fp32", 
#                     verbose=False,
#                 )
#             except Exception as e:
#                 print(f"[WARN] batch predict error: {e}")
#                 time.sleep(0.02)
#                 continue

#             for (cid, frame), result in zip(batch_meta, results):
#                 try:
#                     self._process_camera_result(cid, frame, result)
#                 except Exception as e:
#                     print(f"[WARN] error processing result for camera {cid}: {e}")

#             elapsed = time.time() - loop_start
#             remaining = min_interval - elapsed
#             if remaining > 0:
#                 time.sleep(remaining)

#         print("[BATCH DETECTOR STOPPED]")

#     def _process_camera_result(self, camera_id, frame, result):
#         """Apply zone/intrusion logic to a single camera's inference result
#         and publish the annotated frame. `frame` is already an owned copy,
#         so it's safe to draw on directly (no extra copy needed)."""
#         now = time.time()
#         if now - self._zone_reload_ts.get(camera_id, 0.0) > 10:
#             zones = self.load_zones(camera_id)
#             self._zone_reload_ts[camera_id] = now
#         else:
#             zones = self.load_zones(camera_id)

#         muted_now = self.alert_service.is_muted(camera_id)

#         detections = []
#         try:
#             boxes = result.boxes if result is not None and hasattr(result, "boxes") else None
#             if boxes is not None and len(boxes):
#                 detections = boxes.data.cpu().numpy()
#         except Exception:
#             detections = []

#         h_ratio = frame.shape[0] / max(self.INFERENCE_SIZE, 1)
#         w_ratio = frame.shape[1] / max(self.INFERENCE_SIZE, 1)

#         intruder_present = False
#         intruder_zone = None

#         for det in detections:
#             x1, y1, x2, y2, conf, cls = det[:6]
#             if conf < self.MIN_CONF:
#                 continue
#             cls_name = str(self.model.names.get(int(cls), str(int(cls)))).lower()
#             if cls_name != "person":
#                 continue

#             x1, y1, x2, y2 = (
#                 int(x1 * w_ratio),
#                 int(y1 * h_ratio),
#                 int(x2 * w_ratio),
#                 int(y2 * h_ratio),
#             )

#             # Calculate bounding box area for adaptive threshold (kids vs adults)
#             bbox_area = (x2 - x1) * (y2 - y1)
#             # Small boxes (kids): < 6000 pixels, use 0.3% threshold; Larger (adults): use 1% threshold
#             threshold = 0.003 if bbox_area < 6000 else 0.01

#             crossed = None
#             for z in zones:
#                 overlap_ratio = self._person_zone_overlap_ratio((x1, y1, x2, y2), z["points"])
#                 if overlap_ratio >= threshold:
#                     crossed = z
#                     intruder_present = True
#                     intruder_zone = z
#                     break

#             color = (0, 0, 255) if crossed else (0, 255, 0)
#             cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

#         now_ts = time.time()
#         prev_active = self._intrusion_prev.get(camera_id, False)

#         if intruder_present and not prev_active:
#             self._next_snapshot_at[camera_id] = now_ts

#         if intruder_present and now_ts >= self._next_snapshot_at.get(camera_id, 0.0):
#             if muted_now:
#                 print(f"[HARD BLOCK] Muted - skipping sound, snapshot, and log for camera {camera_id}")
#             else:
#                 # Run alert operations asynchronously to not block frame display
#                 self.sound_executor.submit(self._handle_alert_async, camera_id, frame, intruder_zone)

#             # Next snapshot in 5-10 seconds while intrusion persists
#             self._next_snapshot_at[camera_id] = now_ts + random.uniform(5.0, 10.0)

#         if not intruder_present:
#             self._next_snapshot_at[camera_id] = 0.0

#         self._intrusion_prev[camera_id] = intruder_present

#         self._draw_zones(frame, zones, thickness=4)
#         if intruder_present:
#             self._draw_intrusion_border(frame)

#         with self.lock:
#             self.output_frames[camera_id] = frame

#     def _handle_alert_async(self, camera_id, frame, intruder_zone):
#         """Handle alert operations asynchronously to not block detection/display threads"""
#         try:
#             # Trigger both the alert sound and IP speaker hooter
#             self.alert_service.trigger_alert_sound_and_hooter(camera_id)
#         except Exception as e:
#             print(f"[WARN] Could not trigger alert sound and hooter: {e}")

#         try:
#             snapshot = self.alert_service.save_snapshot(frame, camera_id)
#             zone_name = intruder_zone["name"] if intruder_zone else "zone"
#             zone_id = intruder_zone["id"] if intruder_zone else None
#             msg = f"Person detected crossing the zone {zone_name}"
#             self.alert_service.log_alert(camera_id, zone_id, msg, snapshot)
#         except Exception as e:
#             print(f"[WARN] Could not handle alert: {e}")

#     def _ensure_batch_thread_running(self):
#         with self.init_lock:
#             if self.batch_thread is None or not self.batch_thread.is_alive():
#                 self.batch_stop_event.clear()
#                 self.batch_thread = threading.Thread(target=self._batch_detect_loop, daemon=True)
#                 self.batch_thread.start()

#     def start_detection(self, stream_url, camera_id):
#         if camera_id in self.stop_flags:
#             self.stop_flags[camera_id] = True
#             time.sleep(0.3)

#         with self.lock:
#             self.stop_flags[camera_id] = False
#             self.stream_urls[camera_id] = stream_url
#             self.output_frames[camera_id] = self._generate_no_signal_frame()
#             self.camera_health[camera_id] = False

#         self._zone_reload_ts[camera_id] = 0.0
#         self._next_snapshot_at[camera_id] = 0.0
#         self._intrusion_prev[camera_id] = False

#         reader = threading.Thread(
#             target=self._frame_reader,
#             args=(camera_id, stream_url),
#             daemon=True,
#         )
#         self.reader_threads[camera_id] = reader
#         reader.start()

#         # Detection itself is handled by the single shared batch thread,
#         # started lazily and reused across all cameras.
#         self._ensure_batch_thread_running()
#         self.detection_threads[camera_id] = self.batch_thread

#         print(f"[STARTED] Camera {camera_id} ({stream_url})")

#     def get_frame(self, camera_id):
#         with self.lock:
#             frame = self.output_frames.get(camera_id)
#         if frame is None:
#             return self._generate_no_signal_frame()
#         # Return without extra copy since frame is already a copy from detection thread
#         return frame

#     def stop_all_detections(self):
#         with self.lock:
#             for cid in list(self.stop_flags.keys()):
#                 self.stop_flags[cid] = True

#         self.batch_stop_event.set()

#         for _, t in list(self.reader_threads.items()):
#             try:
#                 t.join(timeout=2)
#             except Exception:
#                 pass

#         if self.batch_thread is not None:
#             try:
#                 self.batch_thread.join(timeout=2)
#             except Exception:
#                 pass

#         for _, cap in list(self.captures.items()):
#             try:
#                 cap.release()
#             except Exception:
#                 pass

#         with self.lock:
#             self.reader_threads.clear()
#             self.detection_threads.clear()
#             self.stop_flags.clear()
#             self.output_frames.clear()
#             self.latest_raw_frame.clear()
#             self.camera_health.clear()

#         self._zone_reload_ts.clear()
#         self._next_snapshot_at.clear()
#         self._intrusion_prev.clear()
#         self.batch_thread = None

#         try:
#             self.sound_executor.shutdown(wait=False)
#         except Exception:
#             pass

#         print("[INFO] All detections stopped")

#     def get_all_cameras(self):
#         try:
#             return list(self.stream_urls.keys())
#         except Exception:
#             return []


# # ensure a detector instance is available
# detector = YOLODetector()