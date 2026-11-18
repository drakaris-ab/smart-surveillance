# app/routers/alerts_routes.py

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional
from backend.database import models, schemas, session
from backend.auth.auth_dependency import get_current_user
from backend.utils.log_activity import log_activity
from backend.config.logging_config import logger
from backend.config.router_message import MESSAGES

try:
    from backend.database import models as app_models
except Exception as e:
    logger.warning(MESSAGES["model_import_failed"].format(error=str(e)))
    app_models = None

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)

get_db = session.get_db
IST = timezone(timedelta(hours=5, minutes=30))


# -------------------------
# Create Alert (POST) - Auth required
# -------------------------
@router.post("/", response_model=schemas.AlertOut, status_code=status.HTTP_201_CREATED)
def create_alert(
    alert: schemas.AlertCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new alert (requires authentication)."""
    try:
        new_alert = models.Alert(
            camera_id=alert.camera_id,
            zone_id=alert.zone_id,
            event_type=alert.message,
            image=alert.snapshot_path,
            timestamp=datetime.utcnow(),
            created_by=getattr(current_user, "username", None)
        )
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)

        # Convert UTC → IST for frontend display
        ist_time = new_alert.timestamp.replace(tzinfo=timezone.utc).astimezone(IST)
        new_alert.timestamp = ist_time.replace(tzinfo=None)

        logger.info(MESSAGES["alert_created"].format(
            camera_id=new_alert.camera_id,
            zone_id=new_alert.zone_id,
            user=getattr(current_user, "username", "unknown")
        ))
        return new_alert
    except Exception as e:
        logger.exception(MESSAGES["alert_create_failed"].format(error=str(e)))
        raise HTTPException(status_code=500, detail="Failed to create alert")


# -------------------------
# Create Alert (POST) - Internal (no auth)
# -------------------------
@router.post("/internal", response_model=schemas.AlertOut, status_code=status.HTTP_201_CREATED)
def create_alert_internal(
    alert: schemas.AlertCreate,
    db: Session = Depends(get_db)
):
    """Create a new alert (internal use, no authentication)."""
    try:
        new_alert = models.Alert(
            camera_id=alert.camera_id,
            zone_id=alert.zone_id,
            event_type=alert.message,
            image=alert.snapshot_path,
            timestamp=datetime.utcnow(),
            created_by="system"
        )
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)

        ist_time = new_alert.timestamp.replace(tzinfo=timezone.utc).astimezone(IST)
        new_alert.timestamp = ist_time.replace(tzinfo=None)

        logger.info(MESSAGES["alert_created"].format(
            camera_id=new_alert.camera_id,
            zone_id=new_alert.zone_id,
            user="system"
        ))
        return new_alert
    except Exception as e:
        logger.exception(MESSAGES["alert_create_failed"].format(error=str(e)))
        raise HTTPException(status_code=500, detail="Failed to create alert")


# -------------------------
# Get All Alerts (GET)
# -------------------------
@router.get("/", response_model=list[schemas.AlertOut])
def get_alerts(
    alert_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Return all alerts (requires authentication). Optional filter by alert_type: 'zone' or 'unidentified_object'."""
    try:
        query = db.query(models.Alert)
        if alert_type:
            query = query.filter(models.Alert.alert_type == alert_type)

        alerts = (
            query.order_by(models.Alert.timestamp.desc())
            .all()
        )

        for a in alerts:
            if a.timestamp:
                try:
                    ist_time = a.timestamp.replace(tzinfo=timezone.utc).astimezone(IST)
                    a.timestamp = ist_time.replace(tzinfo=None)
                except Exception as e:
                    logger.warning(MESSAGES["timestamp_conversion_failed"].format(alert_id=a.id, error=str(e)))

        logger.info(MESSAGES["alerts_fetched"].format(count=len(alerts)))
        return alerts
    except Exception as e:
        logger.exception(MESSAGES["alerts_fetch_failed"].format(error=str(e)))
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")


# -------------------------
# Delete Alert (DELETE)
# -------------------------
@router.delete("/{alert_id}", status_code=status.HTTP_200_OK)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Dismiss/delete an alert (requires authentication)."""
    try:
        alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
        if not alert:
            logger.warning(MESSAGES["alert_not_found"].format(alert_id=alert_id))
            raise HTTPException(status_code=404, detail="Alert not found")

        db.delete(alert)
        db.commit()
        logger.info(MESSAGES["alert_deleted"].format(alert_id=alert_id, user=getattr(current_user, "username", "unknown")))
        return {"message": "Alert dismissed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(MESSAGES["alert_delete_failed"].format(alert_id=alert_id, error=str(e)))
        raise HTTPException(status_code=500, detail="Failed to delete alert")
