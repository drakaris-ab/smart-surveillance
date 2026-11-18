# import threading
# import time
# import torch
# import cv2
# from ultralytics import YOLO
# import numpy as np

# from backend.utils.config import load_config
# from backend.services.alert_service import AlertService
# from backend.config.logging_config import logger

# from backend.detection.runtime_config_manager import RuntimeConfigManager
# from backend.detection.zone_manager import ZoneManager
# from backend.detection.camera_manager import CameraManager
# from backend.detection.detection_engine import DetectionEngine
# from backend.detection.alert_manager import AlertManager

# # ✅ Import shared caches (no circular import)
# from backend.detection.shared_cache import frame_cache, last_capture_time


# class YOLODetector:
#     def __init__(self, model_path="yolov8s.pt"):
#         self.model = YOLO(model_path) if YOLO is not None else None
#         self.device = "cuda" if torch.cuda.is_available() else "cpu"
#         self.quantize_mode = "fp16" if self.device == "cuda" else "fp32"
#         self.person_class_id = 0   # COCO dataset index for 'person'

#         if self.device == "cuda":
#             logger.info("[YOLO DETECTOR] Running on GPU (CUDA, FP16 enabled)")
#         else:
#             logger.info("[YOLO DETECTOR] Running on CPU (FP32 only)")

#         if self.model is not None:
#             try:
#                 self.model.to(self.device)
#             except Exception as e:
#                 logger.warning(f"[WARN] Could not move model to {self.device}: {e}")

#         self.config_manager = RuntimeConfigManager()
#         self.zone_manager = ZoneManager()
#         self.camera_manager = CameraManager()
#         self.alert_manager = AlertManager(AlertService(load_config()))

#         self.batch_stop_event = threading.Event()
#         self.lock = threading.Lock()
#         self.detection_engine = DetectionEngine(
#             self.model,
#             device=self.device,
#             quantize=self.quantize_mode,
#             zone_manager=self.zone_manager,
#             alert_manager=self.alert_manager,
#         )

#         self.detection_engine.lock = self.lock
#         self.detection_engine.batch_stop_event = self.batch_stop_event
#         self.detection_engine.stop_flags = self.camera_manager.stop_flags
#         self.detection_engine.latest_raw_frame = self.camera_manager.latest_raw_frame
#         self.detection_engine.output_frames = self.camera_manager.output_frames

#         self.batch_thread = None

#     def _ensure_batch_thread_running(self):
#         with self.lock:
#             if self.batch_thread is None or not self.batch_thread.is_alive():
#                 self.batch_stop_event.clear()
#                 self.batch_thread = threading.Thread(
#                     target=self.detection_engine.run_batch_loop,
#                     daemon=True,
#                 )
#                 self.batch_thread.start()

#     def start_detection(self, stream_url, camera_id):
#         self.camera_manager.start_reader(camera_id, stream_url)
#         self._ensure_batch_thread_running()
#         print(f"[STARTED] Camera {camera_id} ({stream_url})")

#     def is_camera_connected(self, camera_id):
#         return self.camera_manager.is_camera_connected(camera_id)

#     def get_latest_raw_frame(self, camera_id):
#         frame = frame_cache.get(camera_id)
#         if frame is not None:
#             age = time.time() - last_capture_time.get(camera_id, 0)
#             if age < 5.0:
#                 return frame
#             else:
#                 logger.warning(f"[Detector] Raw frame for camera {camera_id} is stale ({age:.1f}s old)")
#         return self.camera_manager.get_latest_raw_frame(camera_id)

#     def get_frame(self, camera_id):
#         frame = frame_cache.get(camera_id)
#         if frame is not None:
#             age = time.time() - last_capture_time.get(camera_id, 0)
#             if age < 5.0:
#                 return frame
#             else:
#                 logger.warning(f"[Detector] Processed frame for camera {camera_id} is stale ({age:.1f}s old)")
#         return self.camera_manager.get_frame(camera_id)

#     def stop_all_detections(self):
#         self.camera_manager.stop_all()
#         self.batch_stop_event.set()
#         if self.batch_thread is not None:
#             try:
#                 self.batch_thread.join(timeout=2)
#             except Exception:
#                 pass
#         self.batch_thread = None
#         print("[INFO] All detections stopped")

#     def get_all_cameras(self):
#         return list(self.camera_manager.stream_urls.keys())

#     def render_result(self, result, frame: np.ndarray):
#             """
#             Safely overlay YOLO detection results onto the frame.
#             """
#             if frame is None or not isinstance(frame, np.ndarray):
#                 return frame
    
#             try:
#                 if not hasattr(result, "boxes") or result.boxes is None:
#                     return frame
    
#                 for box in result.boxes:
#                     try:
#                         x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
#                         cls_id = int(box.cls[0].item())
#                         conf = float(box.conf[0].item())
    
#                         if cls_id == self.person_class_id:  # only draw persons
#                             cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
#                             label = f"{self.model.names[cls_id]} {conf:.2f}"
#                             cv2.putText(frame, label, (x1, y1 - 10),
#                                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
#                     except Exception as inner_e:
#                         print(f"[YOLODetector] Failed to draw box: {inner_e}")
#                         continue
    
#                 return frame
#             except Exception as e:
#                 print(f"[YOLODetector] render_result failed: {e}")
#                 return frame


# # Ensure a detector instance is available
# detector = YOLODetector()
