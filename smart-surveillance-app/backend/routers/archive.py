# app/routers/archive.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime
import shutil
import os, sys

from sqlalchemy.orm import Session
from backend.database import get_db
from backend.database.models import ActivityLog
from backend.config.logging_config import logger
from backend.config.router_message import MESSAGES

router = APIRouter(
    prefix="",
    tags=["archive"]
)

# --- Path setup ---
if getattr(sys, "frozen", False):
    base_path = Path(sys._MEIPASS)
    base_path = Path(sys.executable).parent
else:
    base_path = Path(__file__).resolve().parent.parent
    exe_dir = base_path

SNAPSHOT_SOURCE = base_path / "snapshots/alerts"


# --- Models ---
class ArchiveRequest(BaseModel):
    destination: str = Field(..., description="Absolute or relative path to destination folder")
    start_date: str = Field(..., description="ISO date string, e.g., 2025-11-01")
    end_date: str = Field(..., description="ISO date string, e.g., 2025-11-26")
    extensions: list[str] = Field(default=[".jpg", ".jpeg", ".png"], description="Allowed file extensions")


class ArchiveResponse(BaseModel):
    copied_count: int
    destination: str
    start_date: str
    end_date: str
    files: list[str]


class ArchiveLogsRequest(BaseModel):
    destination: str
    start_date: str
    end_date: str


class ArchiveLogsResponse(BaseModel):
    archived_count: int
    destination: str
    start_date: str
    end_date: str
    file: str


# --- Snapshot Archiving ---
@router.post("/archive/snapshots", response_model=ArchiveResponse)
def archive_snapshots(req: ArchiveRequest):
    if not SNAPSHOT_SOURCE.exists() or not SNAPSHOT_SOURCE.is_dir():
        logger.warning(MESSAGES["snapshot_source_missing"].format(path=SNAPSHOT_SOURCE))
        raise HTTPException(status_code=404, detail=f"Source not found: {SNAPSHOT_SOURCE}")

    try:
        start_dt = datetime.fromisoformat(req.start_date)
        end_dt = datetime.fromisoformat(req.end_date)
        if end_dt < start_dt:
            raise ValueError("end_date must be >= start_date")
    except Exception as e:
        logger.error(MESSAGES["invalid_dates"].format(error=str(e)))
        raise HTTPException(status_code=400, detail=f"Invalid dates: {e}")

    dest_path = Path(req.destination).expanduser()
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(MESSAGES["dest_create_failed"].format(error=str(e)))
        raise HTTPException(status_code=400, detail=f"Cannot create destination: {e}")

    copied = 0
    copied_files: list[str] = []

    for entry in SNAPSHOT_SOURCE.iterdir():
        if not entry.is_file():
            continue
        if req.extensions and entry.suffix.lower() not in [ext.lower() for ext in req.extensions]:
            continue
        try:
            mtime = datetime.fromtimestamp(entry.stat().st_mtime)
        except Exception:
            continue

        if start_dt <= mtime <= end_dt:
            dest_file = dest_path / entry.name
            try:
                shutil.copy2(entry, dest_file)
                entry.unlink()
                copied += 1
                copied_files.append(entry.name)
                logger.info(MESSAGES["snapshot_archived"].format(file=entry.name, dest=dest_file))
            except Exception as e:
                logger.warning(MESSAGES["snapshot_move_failed"].format(file=entry.name, error=str(e)))

    return ArchiveResponse(
        copied_count=copied,
        destination=str(dest_path),
        start_date=req.start_date,
        end_date=req.end_date,
        files=copied_files,
    )


# --- Logs Archiving ---
@router.post("/archive/logs", response_model=ArchiveLogsResponse)
def archive_logs(req: ArchiveLogsRequest, db: Session = Depends(get_db)):
    try:
        start_dt = datetime.fromisoformat(req.start_date)
        end_dt = datetime.fromisoformat(req.end_date)
        if end_dt < start_dt:
            raise ValueError("end_date must be >= start_date")
    except Exception as e:
        logger.error(MESSAGES["invalid_dates"].format(error=str(e)))
        raise HTTPException(status_code=400, detail=f"Invalid dates: {e}")

    dest_path = Path(req.destination).expanduser()
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(MESSAGES["dest_create_failed"].format(error=str(e)))
        raise HTTPException(status_code=400, detail=f"Cannot create destination: {e}")

    file_name = f"logs_{req.start_date}_{req.end_date}.sql"
    file_path = dest_path / file_name

    try:
        logs = (
            db.query(ActivityLog)
            .filter(ActivityLog.timestamp.between(start_dt, end_dt))
            .all()
        )
    except Exception as e:
        logger.exception(MESSAGES["logs_fetch_failed"].format(error=str(e)))
        raise HTTPException(status_code=500, detail="Failed to fetch logs")

    if not logs:
        logger.info(MESSAGES["no_logs_found"].format(start=req.start_date, end=req.end_date))
        return ArchiveLogsResponse(
            archived_count=0,
            destination=str(dest_path),
            start_date=req.start_date,
            end_date=req.end_date,
            file=file_name
        )

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            for log in logs:
                f.write(
                    f"INSERT INTO activity_logs (id, user_id, action, timestamp) "
                    f"VALUES ({log.id}, '{log.user_id}', '{log.action}', '{log.timestamp}');\n"
                )
        archived_count = len(logs)

        db.query(ActivityLog).filter(ActivityLog.timestamp.between(start_dt, end_dt)).delete(synchronize_session=False)
        db.commit()

        logger.info(MESSAGES["logs_archived"].format(count=archived_count, file=file_name))
    except Exception as e:
        logger.exception(MESSAGES["logs_archive_failed"].format(error=str(e)))
        raise HTTPException(status_code=500, detail="Failed to archive logs")

    return ArchiveLogsResponse(
        archived_count=archived_count,
        destination=str(dest_path),
        start_date=req.start_date,
        end_date=req.end_date,
        file=file_name
    )


# --- Today's Snapshots ---
@router.get("/archive/snapshots/today")
def list_today_snapshots():
    if not SNAPSHOT_SOURCE.exists() or not SNAPSHOT_SOURCE.is_dir():
        logger.warning(MESSAGES["snapshot_source_missing"].format(path=SNAPSHOT_SOURCE))
        raise HTTPException(status_code=404, detail=f"Source not found: {SNAPSHOT_SOURCE}")

    today = datetime.now().date()
    results = []

    for entry in SNAPSHOT_SOURCE.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
            continue

        try:
            mtime = datetime.fromtimestamp(entry.stat().st_mtime).date()
        except Exception as e:
            logger.warning(MESSAGES["snapshot_stat_failed"].format(file=entry.name, error=str(e)))
            continue

        if mtime == today:
            rel_path = str(entry.relative_to(SNAPSHOT_SOURCE.parent))
            results.append({"path": f"/{rel_path.replace(os.sep, '/')}"})

    logger.info(MESSAGES["snapshots_today_listed"].format(count=len(results)))
    return results
