# app/services/alert_service.py

import os, sys, time, smtplib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor

from backend.database.session import SessionLocal
from backend.database.models import Alert, Camera, User, AlertMuteSchedule
from backend.services.config_service import get_config
from backend.core.speaker.speaker_service import SpeakerService
from backend.config.logging_config import logger
from backend.config.messages import MESSAGES

# Optional dependencies
try:
    import cv2
except Exception:
    cv2 = None
    logger.warning(MESSAGES["OPENCV_NOT_AVAILABLE"])

try:
    import requests
except Exception:
    requests = None
    logger.warning(MESSAGES["REQUESTS_NOT_AVAILABLE"])

try:
    from playsound import playsound
except Exception:
    playsound = None
    logger.warning(MESSAGES["PLAYSOUND_NOT_AVAILABLE"])

try:
    from twilio.rest import Client
except Exception:
    Client = None
    logger.warning(MESSAGES["TWILIO_NOT_AVAILABLE"])

try:
    import pygame  # type: ignore
except Exception:
    pygame = None
    logger.warning(MESSAGES["PYGAME_NOT_AVAILABLE"])


class AlertService:
    # Cache for alert mute schedules to avoid repeated DB queries
    _schedule_cache = None
    _cache_timestamp = 0
    CACHE_TTL = 30  # seconds - refresh cache every 30 seconds

    def __init__(self, config: dict):
        self.config = config
        raw_sound_path = config.get("alertSoundPath", "assets/sounds/alert.wav")

        # ✅ Resolve to absolute path
        backend_root = Path(__file__).resolve().parent.parent.parent.parent
        self.ALERT_SOUND_PATH = (backend_root / raw_sound_path).resolve()

        self.api_alerts = f"{config.get('backendBase')}/alerts/"
        self.twilio_sid = config.get("twilioSid")
        self.twilio_auth = config.get("twilioAuth")
        self.from_whatsapp = config.get("fromWhatsapp")
        self.admin_token = config.get("adminToken")  # ✅ token for API calls
        self.sound_executor = ThreadPoolExecutor(max_workers=2)
        self.speaker_service = SpeakerService(config)

        logger.info(MESSAGES["ALERT_SERVICE_INIT"])

    @classmethod
    def _load_schedules_from_db(cls):
        """Load all active alert mute schedules from the database"""
        db = SessionLocal()
        try:
            schedules = db.query(AlertMuteSchedule).filter(AlertMuteSchedule.is_active == True).all()
            return schedules
        finally:
            db.close()

    @classmethod
    def _get_schedules(cls):
        """Get schedules from cache, refreshing if expired"""
        now = time.time()
        if cls._schedule_cache is None or (now - cls._cache_timestamp) > cls.CACHE_TTL:
            cls._schedule_cache = cls._load_schedules_from_db()
            cls._cache_timestamp = now
        return cls._schedule_cache

    @classmethod
    def clear_schedule_cache(cls):
        """Clear the schedule cache to force refresh on next access"""
        cls._schedule_cache = None
        cls._cache_timestamp = 0


    def _cfg(self):
        db = SessionLocal()
        try:
            return get_config(db)
        except Exception as e:
            logger.exception(MESSAGES["CONFIG_FETCH_FAILED"], exc_info=e)
            return None
        finally:
            db.close()

    def trigger_alert_sound_and_hooter(self, camera_id: int):
        if self.is_muted(camera_id):
            logger.info(MESSAGES.get("MUTE_ACTIVE", f"Alert muted for camera {camera_id}"))
            return

        cfg = self._cfg()
        if not cfg:
            logger.error(MESSAGES["CONFIG_NOT_FOUND"])
            return
        duration = getattr(cfg, "alertDurationSeconds", 15)
        try:
            if cfg.alertOutputMode == "hooter":
                self.speaker_service.trigger_hooter(duration=duration)
                logger.info(MESSAGES["HOOTER_TRIGGERED"].format(camera_id=camera_id))
            else:
                self.play_alert_sound(camera_id, duration=duration, sound_path=cfg.alertSoundPath)
        except Exception as e:
            logger.exception(MESSAGES["ALERT_TRIGGER_FAILED"], exc_info=e)

    def play_alert_sound(self, camera_id=None, duration=None, sound_path=None):
        def _play():
            try:
                if camera_id is None or not self.is_muted(camera_id):
                    active_sound_path = Path(sound_path or self.ALERT_SOUND_PATH)
                    active_duration = duration or 15

                    if not active_sound_path.exists():
                        logger.error(f"Alert sound file not found: {active_sound_path}")
                        return

                    if pygame:
                        pygame.mixer.init()
                        pygame.mixer.music.load(str(active_sound_path))
                        pygame.mixer.music.play()
                        time.sleep(active_duration)
                        pygame.mixer.music.stop()
                        logger.info(MESSAGES["SOUND_PLAYED"])
                    elif playsound:
                        playsound(str(active_sound_path))
                        logger.info(MESSAGES["SOUND_PLAYED"])
                    else:
                        logger.warning(MESSAGES["NO_SOUND_BACKEND"])
            except Exception as e:
                logger.exception(MESSAGES["SOUND_PLAY_FAILED"], exc_info=e)

        try:
            self.sound_executor.submit(_play)
        except Exception as e:
            logger.exception(MESSAGES["THREADPOOL_FAILED"], exc_info=e)
            try:
                _play()
            except Exception as e2:
                logger.error(MESSAGES["DIRECT_PLAY_FAILED"], exc_info=e2)

    def log_alert(self, camera_id, zone_id, message, snapshot_path, alert_type="zone"):
        db = SessionLocal()
        try:
            alert = Alert(camera_id=camera_id, zone_id=zone_id,
                          event_type=message, image=snapshot_path,
                          timestamp=datetime.utcnow(), alert_type=alert_type)
            db.add(alert)
            db.commit()
            logger.info(MESSAGES["ALERT_LOGGED"].format(msg=message))
        except Exception as e:
            logger.exception(MESSAGES["ALERT_DB_FAILED"], exc_info=e)
        finally:
            db.close()

        # ✅ Optional API POST
        try:
            if requests and self.admin_token:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                requests.post(
                    self.api_alerts,
                    json={
                        "camera_id": camera_id,
                        "zone_id": zone_id,
                        "message": message,
                        "snapshot_path": snapshot_path,
                        "alert_type": alert_type,
                    },
                    headers=headers,
                    timeout=10
                )
                logger.debug(MESSAGES["ALERT_POSTED"])
        except Exception as e:
            logger.warning(MESSAGES["ALERT_POST_FAILED"], exc_info=e)

    def send_whatsapp_alert(self, owner_phone, camera_name, zone_name, snapshot_path):
        try:
            cfg = self._cfg()
            owner_phone = owner_phone or getattr(cfg, "whatsappPhone", None)
            if not Client or not owner_phone:
                logger.warning(MESSAGES["WHATSAPP_SKIPPED"])
                return
            client = Client(self.twilio_sid, self.twilio_auth)
            msg = f"🚨 {MESSAGES['ALERT']} Camera: {camera_name}, Zone: {zone_name}, Time: {datetime.now()}, Snapshot: {snapshot_path}"
            client.messages.create(from_=self.from_whatsapp, body=msg, to=f"whatsapp:{owner_phone}")
            logger.info(MESSAGES["WHATSAPP_SENT"].format(phone=owner_phone))
        except Exception as e:
            logger.exception(MESSAGES["WHATSAPP_FAILED"], exc_info=e)

    def save_snapshot(self, frame, camera_id: int) -> str:
        try:
            fn = f"alert_{camera_id}_{int(time.time())}.jpg"
            if getattr(sys, "frozen", False):
                snapshots_base = Path(sys.executable).parent / "snapshots"
            else:
                backend_root = Path(__file__).resolve().parent.parent
                snapshots_base = backend_root / "snapshots"

            alerts_dir = snapshots_base / "alerts"
            alerts_dir.mkdir(parents=True, exist_ok=True)
            file_path = alerts_dir / fn

            if cv2:
                cv2.imwrite(str(file_path), frame)
                logger.info(MESSAGES["SNAPSHOT_SAVED"].format(path=file_path))
            else:
                logger.warning(MESSAGES["SNAPSHOT_NOT_SAVED"])
            return f"/snapshots/alerts/{fn}"
        except Exception as e:
            logger.exception(MESSAGES["SNAPSHOT_FAILED"], exc_info=e)
            return ""

    def handle_alert(self, camera_id, zone, frame):
        snapshot = self.save_snapshot(frame, camera_id)
        msg = MESSAGES["ZONE_INTRUSION"].format(zone=zone['name'])
        self.log_alert(camera_id, zone["id"], msg, snapshot, alert_type="zone")
        self.play_alert_sound(camera_id)

        db = SessionLocal()
        try:
            cam = db.query(Camera).filter(Camera.id == camera_id).first()
            owner_id = cam.owner_id if cam else None
            phone = None
            if owner_id:
                user = db.query(User).filter(User.id == owner_id).first()
                phone = getattr(user, "phone", None)
        except Exception as e:
            logger.exception(MESSAGES["CAMERA_OWNER_FAILED"], exc_info=e)
            phone = None
        finally:
            db.close()

        if phone:
            self.send_whatsapp_alert(phone, cam.name if cam else f"Camera {camera_id}", zone["name"], snapshot)

    def send_email(self, to_email: str, subject: str, body: str):
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = "f@gmail.com"
            msg["To"] = to_email

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login("app26.amit@gmail.com", "gg")  # use Gmail App Password
                server.send_message(msg)
            logger.info(MESSAGES["EMAIL_SENT"].format(email=to_email))
        except Exception as e:
            logger.exception(MESSAGES["EMAIL_FAILED"], exc_info=e)

    def is_muted(self, camera_id: int) -> bool:
        IST_OFFSET = timedelta(hours=5, minutes=30)
        IST = timezone(IST_OFFSET)
        now = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(IST)

        try:
            schedules = self._get_schedules()
        except Exception as e:
            logger.warning(MESSAGES["MUTE_QUERY_FAILED"], exc_info=e)
            return False

        if not schedules:
            return False

        for schedule in schedules:
            date_matches = True
            now_date = now.strftime("%Y-%m-%d")

            # Check specific date
            if schedule.date:
                if schedule.date != now_date:
                    date_matches = False

            # Check date range
            if schedule.start_date and schedule.end_date:
                if not (schedule.start_date <= now_date <= schedule.end_date):
                    date_matches = False

            days_matches = True
            if schedule.days:
                days_lower = [d.strip().lower() for d in schedule.days.split(",") if d.strip()]
                weekday_short = now.strftime("%a").lower()
                weekday_full = now.strftime("%A").lower()
                if not (weekday_short in days_lower or weekday_full in days_lower):
                    days_matches = False

            time_matches = True
            if schedule.start_time and schedule.end_time:
                now_time = now.strftime("%H:%M")
                if not (schedule.start_time <= now_time <= schedule.end_time):
                    time_matches = False

            has_condition = bool(schedule.date or (schedule.start_date and schedule.end_date) or schedule.days or (schedule.start_time and schedule.end_time))
            if has_condition and date_matches and days_matches and time_matches:
                return True

        return False
