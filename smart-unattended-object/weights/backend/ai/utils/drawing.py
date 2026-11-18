"""
drawing.py

Utility functions for drawing detections on frames.
"""

import cv2
from typing import List, Dict


class DrawingUtils:

    @staticmethod
    def draw_detections(frame, detections: List[Dict]):

        frame_h, frame_w = frame.shape[:2]

        for obj in detections:

            x1, y1, x2, y2 = map(int, obj["bbox"])

            confidence = obj.get("confidence", 0)
            track_id = obj.get("track_id", "-")
            duration = obj.get("duration", 0)
            severity = obj.get("severity", "NONE")
            is_threat = obj.get("is_threat", False)

            if is_threat:
                color = (0, 0, 255)
                label = (
                    f"THREAT | "
                    f"ID:{track_id} | "
                    f"{duration:.1f}s | "
                    f"{severity}"
                )
            else:
                color = (0, 255, 0)
                label = (
                    f"ID:{track_id} | "
                    f"{confidence:.2f}"
                )

            # Bounding Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Measure actual text size instead of guessing via len(label)*9
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.55
            font_thickness = 2
            (text_w, text_h), baseline = cv2.getTextSize(
                label, font, font_scale, font_thickness
            )

            padding_x = 10
            box_h = text_h + baseline + 12
            box_w = text_w + padding_x

            # Default: label above the box
            label_y2 = y1
            label_y1 = y1 - box_h

            # If it would go off the top of the frame, draw it below instead
            if label_y1 < 0:
                label_y1 = y2
                label_y2 = y2 + box_h

            # Clamp horizontally so it doesn't run off the frame edges
            label_x1 = max(0, min(x1, frame_w - box_w))
            label_x2 = label_x1 + box_w

            # Background
            cv2.rectangle(
                frame,
                (label_x1, label_y1),
                (label_x2, label_y2),
                color,
                -1
            )

            # Text
            text_y = label_y2 - baseline - 6
            cv2.putText(
                frame,
                label,
                (label_x1 + padding_x // 2, text_y),
                font,
                font_scale,
                (255, 255, 255),
                font_thickness,
                cv2.LINE_AA
            )

        return frame