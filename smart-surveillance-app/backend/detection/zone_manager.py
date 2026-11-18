# zone_manager.py
import time
import json
import numpy as np
import cv2
from backend.database import SessionLocal, BoundaryZone

class ZoneManager:
    def __init__(self):
        self.zones_cache = {}
        self.zones_cache_time = {}

    def load_zones(self, camera_id):
        """Load zones with caching to reduce database hits"""
        now = time.time()
        if camera_id in self.zones_cache:
            cache_time = self.zones_cache_time.get(camera_id, 0)
            if now - cache_time < 10:  # cache valid for 10 seconds
                return self.zones_cache[camera_id]

        db = SessionLocal()
        zones = db.query(BoundaryZone).filter(BoundaryZone.camera_id == camera_id).all()
        db.close()

        loaded = []
        for z in zones:
            try:
                points_field = getattr(z, "points", None) or getattr(z, "polygon_coords", None)
                pts = json.loads(points_field) if isinstance(points_field, str) else points_field

                parsed_pts = []
                for p in pts:
                    if isinstance(p, dict):
                        parsed_pts.append((p["x"], p["y"]))
                    elif isinstance(p, (list, tuple)) and len(p) >= 2:
                        parsed_pts.append((p[0], p[1]))
                pts = np.array(parsed_pts, np.int32)

                name_field = getattr(z, "name", None) or f"Zone {z.id}"
                loaded.append({"id": z.id, "name": name_field, "points": pts})
            except Exception as e:
                print(f"[WARN] Error loading zone {z.id}: {e}")

        self.zones_cache[camera_id] = loaded
        self.zones_cache_time[camera_id] = now
        return loaded

    def person_zone_overlap_ratio(self, bbox, polygon):
        """Calculate overlap ratio between person bbox and zone polygon"""
        x1, y1, x2, y2 = bbox
        x1 = int(max(0, x1))
        y1 = int(max(0, y1))
        x2 = int(max(x1 + 1, x2))
        y2 = int(max(y1 + 1, y2))

        bbox_w = x2 - x1
        bbox_h = y2 - y1
        bbox_area = float(bbox_w * bbox_h)
        if bbox_area <= 0:
            return 0.0

        try:
            roi_poly = polygon.copy()
            roi_poly[:, 0] = roi_poly[:, 0] - x1
            roi_poly[:, 1] = roi_poly[:, 1] - y1
            zone_mask = np.zeros((bbox_h, bbox_w), dtype=np.uint8)
            cv2.fillPoly(zone_mask, [roi_poly], 255)
            overlap_pixels = cv2.countNonZero(zone_mask)
            return overlap_pixels / bbox_area
        except Exception:
            return 0.0

    def draw_zones(self, frame, zones, thickness=4):
        """Draw zone polygons on frame"""
        for z in zones:
            try:
                cv2.polylines(frame, [z["points"]], True, (0, 255, 255), thickness)
            except Exception:
                pass

    def draw_intrusion_border(self, frame):
        """Blink red border during intrusion"""
        import time
        if int(time.time() * 3) % 2 == 0:
            cv2.rectangle(frame, (0, 0), (frame.shape[1] - 1, frame.shape[0] - 1), (0, 0, 255), 6)
