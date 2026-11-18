import cv2
import sys
import os

# Add the project root to the path so we can import backend modules
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.append(project_root)
print(f"Python path: {sys.path}")
print(f"Project root: {project_root}")

from backend.services.detection_service import DetectionService


service = DetectionService(
    camera_id=1,
    camera_name="Test Camera"
)

# Try multiple backends to avoid MSMF issues on Windows
cap = None
backends = [cv2.CAP_DSHOW, cv2.CAP_FFMPEG, 0]
for backend in backends:
    try:
        c = cv2.VideoCapture(0, backend)
        if c.isOpened():
            # Test that we can actually read a frame
            ret, test_frame = c.read()
            if ret and test_frame is not None:
                cap = c
                print(f"[INFO] Testing detection: opened webcam with backend {backend}")
                break
            else:
                print(f"[WARN] Testing detection: opened webcam with backend {backend} but cannot read frames")
                c.release()
        else:
            c.release()
    except Exception:
        pass

if cap is None:
    raise RuntimeError("Could not open webcam with any backend.")

while True:

    ret, frame = cap.read()

    if not ret:
        break

    detections, alerts = service.process(frame)

    for obj in detections:

        x1, y1, x2, y2 = obj["bbox"]

        color = (0, 0, 255) if obj.get("is_threat") else (0, 255, 0)

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            2,
        )

        cv2.putText(
            frame,
            f'{obj["class_name"]} {obj["confidence"]:.2f}',
            (x1, y1 - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )

    cv2.imshow("DetectionService Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()