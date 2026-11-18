# alert_manager.py
import threading

class AlertManager:
    def __init__(self, alert_service):
        self.alert_service = alert_service
        # Use a thread pool for async alert handling
        self.sound_executor = threading.Thread

    def is_muted(self, camera_id):
        """Check if alerts are muted for a camera"""
        try:
            return self.alert_service.is_muted(camera_id)
        except Exception:
            return False

    def handle_alert_async(self, camera_id, frame, intruder_zone):
        """Handle alert operations asynchronously"""
        thread = threading.Thread(
            target=self._handle_alert,
            args=(camera_id, frame, intruder_zone),
            daemon=True,
        )
        thread.start()

    def _handle_alert(self, camera_id, frame, intruder_zone):
        """Trigger sound, save snapshot, and log alert"""
        try:
            # Trigger both the alert sound and IP speaker hooter
            self.alert_service.trigger_alert_sound_and_hooter(camera_id)
        except Exception as e:
            print(f"[WARN] Could not trigger alert sound and hooter: {e}")

        try:
            snapshot = self.alert_service.save_snapshot(frame, camera_id)
            zone_name = intruder_zone["name"] if intruder_zone else "zone"
            zone_id = intruder_zone["id"] if intruder_zone else None
            msg = f"Person detected crossing the zone {zone_name}"
            self.alert_service.log_alert(camera_id, zone_id, msg, snapshot)
        except Exception as e:
            print(f"[WARN] Could not handle alert: {e}")
