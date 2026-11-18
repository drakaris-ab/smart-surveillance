from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database.database import get_db
from backend.database.models import Configurations
from backend.config.logging_config import logger
from backend.util.messages import messages

router = APIRouter(prefix="/configurations", tags=["Configurations"])

@router.post("/toggle-live-tracking")
def toggle_live_tracking(db: Session = Depends(get_db)):
    try:
        config = db.query(Configurations).filter(Configurations.key == "live_tracking_enabled").first()
        if config:
            # flip the value
            new_value = "false" if config.value == "true" else "true"
            config.value = new_value
            config.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"{messages['CONFIG_TOGGLE_SUCCESS']} (new_value={new_value})")
            return {
                "status": "updated",
                "live_tracking_enabled": new_value,
                "message": messages["CONFIG_TOGGLE_SUCCESS"]
            }
        else:
            # create new entry default ON
            config = Configurations(
                key="live_tracking_enabled",
                value="true",
                description="Flag to start/stop background live tracking process",
                created_at=datetime.utcnow(),
            )
            db.add(config)
            db.commit()
            logger.info(messages["CONFIG_CREATED"])
            return {
                "status": "created",
                "live_tracking_enabled": "true",
                "message": messages["CONFIG_CREATED"]
            }
    except Exception as e:
        logger.exception(f"{messages['CONFIG_ERROR']}: {e}")
        raise HTTPException(status_code=500, detail=messages["CONFIG_ERROR"])

@router.get("/live-tracking-status")
def get_live_tracking_status(db: Session = Depends(get_db)):
    try:
        config = db.query(Configurations).filter(Configurations.key == "live_tracking_enabled").first()
        if not config:
            logger.warning(messages["CONFIG_NOT_FOUND"])
            return {"live_tracking_enabled": "false", "message": messages["CONFIG_NOT_FOUND"]}
        logger.info(messages["CONFIG_STATUS_FETCHED"])
        return {"live_tracking_enabled": config.value, "message": messages["CONFIG_STATUS_FETCHED"]}
    except Exception as e:
        logger.exception(f"{messages['CONFIG_ERROR']}: {e}")
        raise HTTPException(status_code=500, detail=messages["CONFIG_ERROR"])
