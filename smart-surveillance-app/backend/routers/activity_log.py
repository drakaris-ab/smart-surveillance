from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.database.models import ActivityLog, User
from backend.routers.auth_routes import get_current_user
from backend.config.logging_config import logger
from backend.config.router_message import MESSAGES
from datetime import timezone as dt_timezone
from zoneinfo import ZoneInfo

router = APIRouter(
    prefix="/activity_log",
    tags=["Activity Log"]
)

@router.get("/")
def get_activity_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch all activity logs for the logged-in user.
    Returns a structured list with timestamps, actions, and details.
    """
    try:
        logs = (
            db.query(ActivityLog)
            .filter(ActivityLog.user_id == current_user.id)   # ✅ scoped to user
            .order_by(ActivityLog.timestamp.desc())
            .all()
        )
        logger.info(MESSAGES["ACTIVITY_LOG_FETCHED"].format(user=current_user.username, count=len(logs)))
    except Exception as e:
        logger.exception(MESSAGES["ACTIVITY_LOG_FETCH_FAILED"].format(user=current_user.username), exc_info=e)
        raise HTTPException(status_code=500, detail=MESSAGES["ACTIVITY_LOG_FETCH_FAILED"].format(user=current_user.username))

    formatted_logs = []
    for log in logs:
        ts = log.timestamp
        if ts:
            # ✅ Convert UTC → Asia/Kolkata
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=dt_timezone.utc)
            ts_local = ts.astimezone(ZoneInfo("Asia/Kolkata"))
            ts_str = ts_local.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts_str = None

        formatted_logs.append({
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "description": log.description,
            "status": log.status or "Success",
            "timestamp": ts_str
        })

    return formatted_logs
