# app/services/unidentified_object_sync_service.py
"""
Background service to fetch unidentified object alerts from the Unattended Object
worker service (port 8002) and store them in the main Alert table.
"""

import time
import threading
import logging
from datetime import datetime, timezone, timedelta

try:
    import requests
except Exception:
    requests = None

from backend.database.session import SessionLocal
from backend.database.models import Alert, Camera
from backend.services.config_service import get_config
from backend.config.logging_config import logger
from backend.config.messages import MESSAGES

IST = timezone(timedelta(hours=5, minutes=30))

class UnidentifiedObjectSyncService:
    """Service to sync unidentified object alerts from worker service to main database."""

    def __init__(self, config: dict):
        self.config = config
        self.worker_base_url = config.get("unattendedObjectUrl") or config.get("UNWANTED_OBJECT_BASE_URL") or "http://localhost:8002"
        self.poll_interval = config.get("unidentifiedObjectPollInterval", 30)  # seconds
        self.running = False
        self._thread = None
        self._last_fetch_time = {}

        logger.info(f"[UnidentifiedObjectSyncService] Initialized with worker URL: {self.worker_base_url}, poll interval: {self.poll_interval}s")

    def start(self):
        """Start the background sync thread."""
        if self.running:
            logger.warning("[UnidentifiedObjectSyncService] Already running")
            return

        self.running = True
        self._thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._thread.start()
        logger.info("[UnidentifiedObjectSyncService] Started")

    def stop(self):
        """Stop the background sync thread."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[UnidentifiedObjectSyncService] Stopped")

    def _sync_loop(self):
        """Main sync loop - polls worker service for alerts."""
        while self.running:
            try:
                self._fetch_and_store_alerts()
            except Exception as e:
                logger.exception(f"[UnidentifiedObjectSyncService] Error in sync loop: {e}")

            time.sleep(self.poll_interval)

    def _fetch_and_store_alerts(self):
        """Fetch alerts from worker service for all cameras and store in main DB."""
        if not requests:
            logger.warning("[UnidentifiedObjectSyncService] requests library not available")
            return

        db = SessionLocal()
        try:
            # Get all cameras
            cameras = db.query(Camera).all()
            if not cameras:
                return

            for camera in cameras:
                try:
                    self._sync_camera_alerts(db, camera)
                except Exception as e:
                    logger.exception(f"[UnidentifiedObjectSyncService] Error syncing camera {camera.id}: {e}")

        finally:
            db.close()

    def _sync_camera_alerts(self, db, camera: Camera):
        """Fetch alerts for a specific camera from worker service and store new ones."""
        camera_id = camera.id

        try:
            # Fetch alerts from worker service
            url = f"{self.worker_base_url}/unattended-object/alerts/{camera_id}"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                logger.warning(f"[UnidentifiedObjectSyncService] Failed to fetch alerts for camera {camera_id}: {response.status_code}")
                return

            data = response.json()
            alerts = data.get("alerts", [])

            if not alerts:
                return

            # Get the last fetch time for this camera to only process new alerts
            last_fetch = self._last_fetch_time.get(camera_id, datetime.min.replace(tzinfo=timezone.utc))

            new_alerts_count = 0
            for alert_data in alerts:
                try:
                    # Parse timestamp from alert
                    alert_timestamp_str = alert_data.get("timestamp")
                    if not alert_timestamp_str:
                        continue

                    # Parse timestamp - handle various formats
                    alert_timestamp = self._parse_timestamp(alert_timestamp_str)

                    # Skip if already processed
                    if alert_timestamp <= last_fetch:
                        continue

                    # Check if alert already exists in DB (by camera_id, timestamp, and message)
                    existing = db.query(Alert).filter(
                        Alert.camera_id == camera_id,
                        Alert.timestamp == alert_timestamp,
                        Alert.event_type == alert_data.get("message", ""),
                        Alert.alert_type == "unidentified_object"
                    ).first()

                    if existing:
                        continue

                    # Create new alert
                    snapshot_path = alert_data.get("snapshot", "")
                    message = alert_data.get("message", "Unidentified object detected")

                    alert = Alert(
                        camera_id=camera_id,
                        zone_id=None,  # No zone for unidentified object alerts
                        event_type=message,
                        image=snapshot_path,
                        timestamp=alert_timestamp,
                        alert_type="unidentified_object",
                        created_by="system"
                    )
                    db.add(alert)
                    new_alerts_count += 1

                except Exception as e:
                    logger.exception(f"[UnidentifiedObjectSyncService] Error processing alert for camera {camera_id}: {e}")

            if new_alerts_count > 0:
                db.commit()
                logger.info(f"[UnidentifiedObjectSyncService] Stored {new_alerts_count} new unidentified object alerts for camera {camera_id}")

                # Update last fetch time to the latest alert timestamp
                if alerts:
                    latest_timestamp = max(
                        self._parse_timestamp(a.get("timestamp", ""))
                        for a in alerts
                        if a.get("timestamp")
                    )
                    self._last_fetch_time[camera_id] = latest_timestamp

        except requests.exceptions.Timeout:
            logger.warning(f"[UnidentifiedObjectSyncService] Timeout fetching alerts for camera {camera_id}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"[UnidentifiedObjectSyncService] Connection error fetching alerts for camera {camera_id}")
        except Exception as e:
            logger.exception(f"[UnidentifiedObjectSyncService] Error fetching alerts for camera {camera_id}: {e}")

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime object."""
        # Try multiple formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",  # ISO with microseconds
            "%Y-%m-%dT%H:%M:%S",     # ISO without microseconds
            "%Y-%m-%d %H:%M:%S.%f",  # Space separated with microseconds
            "%Y-%m-%d %H:%M:%S",     # Space separated without microseconds
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        # If all formats fail, try ISO format parsing
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

        # Fallback to current time
        logger.warning(f"[UnidentifiedObjectSyncService] Failed to parse timestamp: {timestamp_str}")
        return datetime.utcnow().replace(tzinfo=timezone.utc)


# Global instance
_sync_service = None

def get_sync_service():
    """Get or create the global sync service instance."""
    global _sync_service
    if _sync_service is None:
        config = {}
        try:
            db = SessionLocal()
            try:
                config_obj = get_config(db)
                if config_obj:
                    # Handle both SQLAlchemy model and dict
                    config = {
                        "unattendedObjectUrl": getattr(config_obj, "unattendedObjectUrl", None) or
                                              (config_obj.get("unattendedObjectUrl") if isinstance(config_obj, dict) else None),
                        "UNWANTED_OBJECT_BASE_URL": getattr(config_obj, "UNWANTED_OBJECT_BASE_URL", None) or
                                                   (config_obj.get("UNWANTED_OBJECT_BASE_URL") if isinstance(config_obj, dict) else None),
                        "unidentifiedObjectPollInterval": getattr(config_obj, "unidentifiedObjectPollInterval", 30) or
                                                         (config_obj.get("unidentifiedObjectPollInterval") if isinstance(config_obj, dict) else 30),
                    }
            finally:
                db.close()
        except Exception as e:
            logger.exception(f"[UnidentifiedObjectSyncService] Error loading config: {e}")
            config = {}

        _sync_service = UnidentifiedObjectSyncService(config)

    return _sync_service

def start_sync_service():
    """Start the global sync service."""
    service = get_sync_service()
    service.start()

def stop_sync_service():
    """Stop the global sync service."""
    global _sync_service
    if _sync_service:
        _sync_service.stop()
        _sync_service = None