from backend.database import SessionLocal
from backend.config.logging_config import logger
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime
from backend.database.models import Configurations
# ---------------------------
# Predefined Config Schema
# ---------------------------
class ConfigSchema(BaseModel):
    alertSoundPath: str = Field(default="assets/sounds/alert.wav")
    alertOutputMode: Literal["system", "hooter"] = Field(default="system")
    alertDurationSeconds: int = Field(default=15, ge=1)
    whatsappPhone: str = Field(default="")
    smsPhone: str = Field(default="")
    archiveDays: int = Field(default=30, ge=1)
    confidenceThreshold: float = Field(default=0.5, ge=0.0, le=1.0)
    frameSize: int = Field(default=640, ge=1)
    imageSize: int = Field(default=416, ge=1)
    focalLength: float = Field(default=24.0, ge=0.0)
    inferenceSize: int = Field(default=416, ge=1)
    snapshotCount: int = Field(default=5, ge=1)
    #detectionEnabled: bool = Field(default=True)
    is_Camera_Detector: bool = Field(default=False)
    live_Face_tracking_enabled: bool = Field(default=False)
    unattendedObjectUrl: str = Field(default="http://localhost:8002")
    unidentifiedObjectPollInterval: int = Field(default=30, ge=5)


# ---------------------------
# DB Dependency#
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



# ---------------------------
# Service Function
# ---------------------------
def get_config(db = None) -> ConfigSchema:
    """Load configuration from DB and merge with defaults in ConfigSchema."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        configs = db.query(Configurations).all()
        values = {}
        for cfg in configs:
            try:
                # Convert DB string values into correct types using Pydantic
                values[cfg.key] = cfg.value
            except Exception as e:
                logger.warning(f"Invalid config value for {cfg.key}: {cfg.value} ({e})")

        # Merge DB values over defaults
        merged = ConfigSchema(**values)
        return merged
    finally:
        if close_db:
            db.close()
