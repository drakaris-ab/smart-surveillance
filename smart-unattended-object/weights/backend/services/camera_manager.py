"""
camera_manager.py

Handles one or multiple surveillance cameras and
passes frames through the detection pipeline.
"""

import cv2

from backend.services.detection_service import DetectionService
from backend.ai.utils.drawing import DrawingUtils


class CameraManager:

    def __init__(self):

        # Webcam / RTSP sources
        self.camera_sources = [
            0,      # Webcam
            # 1,    # Second webcam
            # "rtsp://admin:password@192.168.1.10:554/stream1",
            # "rtsp://admin:password@192.168.1.11:554/stream1",
        ]

        self.cameras = []

        self.detection_services = []

    def initialize(self):

        for i, source in enumerate(self.camera_sources):
            # Try multiple backends to avoid MSMF issues on Windows
            cap = None
            backends = [cv2.CAP_DSHOW, cv2.CAP_FFMPEG, 0]
            if isinstance(source, str) and source.startswith("rtsp://"):
                backends = [cv2.CAP_FFMPEG]
            elif isinstance(source, str) and source.isdigit():
                backends = [cv2.CAP_DSHOW, cv2.CAP_FFMPEG, int(source)]
            else:
                backends = [cv2.CAP_DSHOW, cv2.CAP_FFMPEG, 0]

            for backend in backends:
                try:
                    src = source if not isinstance(source, str) or not source.isdigit() else int(source)
                    c = cv2.VideoCapture(src, backend)
                    if c.isOpened():
                        # Test that we can actually read a frame
                        ret, test_frame = c.read()
                        if ret and test_frame is not None:
                            cap = c
                            print(f"[INFO] Camera {i} opened with backend {backend}")
                            break
                        else:
                            print(f"[WARN] Camera {i} opened with backend {backend} but cannot read frames")
                            c.release()
                    else:
                        c.release()
                except Exception:
                    pass

            if cap is None:
                print(f"[ERROR] Could not open camera: {source}")
                continue

            self.cameras.append(cap)

            # One DetectionService per camera
            self.detection_services.append(
                DetectionService(camera_id=i,
                    camera_name=f"Camera {i}")
            )

        print(f"[INFO] {len(self.cameras)} camera(s) initialized.")

    def run(self):

        self.initialize()

        if len(self.cameras) == 0:

            print("No cameras available.")

            return

        print("Press 'q' to quit.")

        while True:

            for camera_id, cap in enumerate(self.cameras):

                ret, frame = cap.read()

                if not ret:
                    continue

                detections = self.detection_services[camera_id].process(
                    frame
                )

                frame = DrawingUtils.draw_detections(
                    frame,
                    detections
                )

                cv2.imshow(
                    f"Camera {camera_id}",
                    frame
                )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        self.close()

    def close(self):

        for cap in self.cameras:

            cap.release()

        cv2.destroyAllWindows()

        print("[INFO] Cameras released.")
