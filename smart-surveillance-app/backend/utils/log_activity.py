import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from sqlalchemy.orm import Session
from backend.database import ActivityLog
from backend.utils.config import load_config

# ----------------------------
# Load config
# ----------------------------
config = load_config()
log_level = config.get("logging", {}).get("level", "INFO").upper()
labels = config.get("logging", {}).get("labels", {})
output_mode = config.get("logging", {}).get("output", "console").lower()

# ----------------------------
# Ensure logs directory exists
# ----------------------------
os.makedirs("logs", exist_ok=True)

# ----------------------------
# Configure logger
# ----------------------------
logger = logging.getLogger("activity_logger")
logger.setLevel(getattr(logging, log_level, logging.INFO))

formatter = logging.Formatter(
    f"[{labels.get('activity_logger','ACTIVITY')}] %(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Clear existing handlers to avoid duplicates
logger.handlers.clear()

# Console handler
if output_mode in ("console", "both"):
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# File handler (rotating to avoid huge files)
if output_mode in ("file", "both"):
    file_handler = RotatingFileHandler(
        "logs/activity.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# ----------------------------
# Activity logging functions
# ----------------------------
def log_activity(user_id: int, action: str, description: str = None) -> bool:
    """
    Record user activity in the ActivityLog table.
    """
    logger.debug(f"Called log_activity() → user_id={user_id}, action='{action}'")

    db: Session = SessionLocal()
    try:
        log_entry = ActivityLog(
            owner_id=user_id,
            action=action,
            description=description,
            timestamp=datetime.utcnow(),
            user_id=user_id
        )

        db.add(log_entry)
        db.commit()
        logger.info(f"✅ Activity logged successfully: action='{action}', user_id={user_id}")
        return True

    except Exception as e:
        logger.error(f"[ActivityLog Error] {e}")
        db.rollback()
        return False

    finally:
        db.close()


def log_event(event_type: str, description: str) -> bool:
    """
    Record a system event (not tied to a specific user).
    Useful for camera register/update/delete, background jobs, etc.
    """
    logger.debug(f"Called log_event() → event_type={event_type}")

    db: Session = SessionLocal()
    try:
        log_entry = ActivityLog(
            owner_id=None,  # system event, no user
            action=event_type,
            description=description,
            timestamp=datetime.utcnow()
        )

        db.add(log_entry)
        db.commit()
        logger.info(f"✅ Event logged successfully: type='{event_type}'")
        return True

    except Exception as e:
        logger.error(f"[EventLog Error] {e}")
        db.rollback()
        return False

    finally:
        db.close()
