from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from pydantic import BaseModel

from backend.database.session import get_db
from backend.database.models import AlertMuteSchedule, User
from backend.routers.auth_routes import get_current_user
from backend.utils.log_activity import log_activity
from backend.config.logging_config import logger
from backend.config.router_message import MESSAGES
from backend.services.alert_service import AlertService

router = APIRouter(
    prefix="/alert-mute",
    tags=["Alert Mute Schedule"]
)

# -------------------------
# Pydantic Schemas
# -------------------------
class AlertMuteScheduleCreate(BaseModel):
    date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    days: str | None = None  # e.g., "Mon,Tue,Wed"
    is_active: bool = True

class AlertMuteScheduleResponse(AlertMuteScheduleCreate):
    id: int

    class Config:
        from_attributes = True

# -------------------------
# Routes
# -------------------------

@router.get("/", response_model=List[AlertMuteScheduleResponse])
def get_all_schedules(db: Session = Depends(get_db)):
    try:
        schedules = db.query(AlertMuteSchedule).all()
        logger.info(MESSAGES["MUTE_FETCH_ALL"].format(count=len(schedules)))
        return schedules
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(MESSAGES["MUTE_FETCH_FAILED"], exc_info=e)
        raise HTTPException(status_code=500, detail=MESSAGES["MUTE_FETCH_FAILED"])


@router.get("/{schedule_id}", response_model=AlertMuteScheduleResponse)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    try:
        schedule = db.query(AlertMuteSchedule).filter(AlertMuteSchedule.id == schedule_id).first()
        if not schedule:
            logger.warning(MESSAGES["MUTE_NOT_FOUND"].format(id=schedule_id))
            raise HTTPException(status_code=404, detail=MESSAGES["MUTE_NOT_FOUND"].format(id=schedule_id))
        return schedule
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(MESSAGES["MUTE_FETCH_FAILED"], exc_info=e)
        raise HTTPException(status_code=500, detail=MESSAGES["MUTE_FETCH_FAILED"])


@router.post("", response_model=AlertMuteScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    data: AlertMuteScheduleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        schedule = AlertMuteSchedule(
            date=data.date,
            start_time=data.start_time,
            end_time=data.end_time,
            days=data.days,
            is_active=data.is_active
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        # Clear the alert mute schedule cache to reflect changes
        AlertService.clear_schedule_cache()

        log_activity(
            user_id=current_user.get("id"),
            action="MUTE_SCHEDULE_CREATED",
            description=MESSAGES["MUTE_CREATED"].format(user=current_user.get("sub"), id=schedule.id)
        )
        logger.info(MESSAGES["MUTE_CREATED"].format(user=current_user.get("sub"), id=schedule.id))
        return schedule
    except HTTPException as http_exc:
        db.rollback()
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["MUTE_CREATE_FAILED"], exc_info=e)
        raise HTTPException(status_code=500, detail=MESSAGES["MUTE_CREATE_FAILED"])


@router.put("/{schedule_id}", response_model=AlertMuteScheduleResponse)
def update_schedule(
    schedule_id: int,
    data: AlertMuteScheduleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        schedule = db.query(AlertMuteSchedule).filter(AlertMuteSchedule.id == schedule_id).first()
        if not schedule:
            logger.warning(MESSAGES["MUTE_NOT_FOUND"].format(id=schedule_id))
            raise HTTPException(status_code=404, detail=MESSAGES["MUTE_NOT_FOUND"].format(id=schedule_id))

        schedule.date = data.date
        schedule.start_time = data.start_time
        schedule.end_time = data.end_time
        schedule.days = data.days
        schedule.is_active = data.is_active

        db.commit()
        db.refresh(schedule)
        # Clear the alert mute schedule cache to reflect changes
        AlertService.clear_schedule_cache()

        log_activity(
            user_id=current_user.get("id"),
            action="MUTE_SCHEDULE_UPDATED",
            description=MESSAGES["MUTE_UPDATED"].format(user=current_user.get("sub"), id=schedule.id)
        )
        logger.info(MESSAGES["MUTE_UPDATED"].format(user=current_user.get("sub"), id=schedule.id))
        return schedule
    except HTTPException as http_exc:
        db.rollback()
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["MUTE_UPDATE_FAILED"], exc_info=e)
        raise HTTPException(status_code=500, detail=MESSAGES["MUTE_UPDATE_FAILED"])


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        schedule = db.query(AlertMuteSchedule).filter(AlertMuteSchedule.id == schedule_id).first()
        if not schedule:
            logger.warning(MESSAGES["MUTE_NOT_FOUND"].format(id=schedule_id))
            raise HTTPException(status_code=404, detail=MESSAGES["MUTE_NOT_FOUND"].format(id=schedule_id))

        db.delete(schedule)
        db.commit()
        # Clear the alert mute schedule cache to reflect changes
        AlertService.clear_schedule_cache()

        log_activity(
            user_id=current_user.get("id"),
            action="MUTE_SCHEDULE_DELETED",
            description=MESSAGES["MUTE_DELETED"].format(user=current_user.get("sub"), id=schedule_id)
        )
        logger.info(MESSAGES["MUTE_DELETED"].format(user=current_user.get("sub"), id=schedule_id))
        return {"detail": MESSAGES["MUTE_DELETED"].format(user=current_user.get("sub"), id=schedule_id)}
    except HTTPException as http_exc:
        db.rollback()
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["MUTE_DELETE_FAILED"], exc_info=e)
        raise HTTPException(status_code=500, detail=MESSAGES["MUTE_DELETE_FAILED"])
