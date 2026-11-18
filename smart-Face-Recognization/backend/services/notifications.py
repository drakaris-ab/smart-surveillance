 
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database.models import AlertFace
from backend.config.logging_config import logger
from backend.util.messages import messages

class NotificationsService:
    def __init__(self, db: Session):
        self.db = db

    def save_alert(self, camera_id: int, message: str):
        try:
            alert = AlertFace(
                camera_id=camera_id,
                message=message,
                consumed=False,
                created_at=datetime.utcnow()
            )
            self.db.add(alert)
            self.db.commit()
            self.db.refresh(alert)
            logger.info(f"{messages['ALERT_SAVED']} (camera_id={camera_id}, message={message})")
            return alert
        except Exception as e:
            logger.exception(f"Failed to save alert: {e}")
            return None

    def notify(self, channel: str, payload: dict):
        """
        Future extension: send notifications via different channels
        e.g., email, SMS, push, webhook.
        """
        logger.info(f"Notification sent via {channel}: {payload}")
