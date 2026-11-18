# app/utils/file_ops.py

import os
import shutil
import datetime
from pathlib import Path
from backend.config.logging_config import logger
from backend.config.messages import MESSAGES

# ---------------------------
# 1. Directory helpers
# ---------------------------
def ensure_dir(path: str) -> None:
    """Ensure a directory exists, create if missing."""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        logger.debug(MESSAGES["DIR_CREATED"].format(path=path))
    except Exception as e:
        logger.exception(MESSAGES["DIR_CREATE_FAILED"].format(path=path), exc_info=e)


def clear_dir(path: str) -> None:
    """Delete all files in a directory."""
    try:
        if os.path.exists(path):
            for f in os.listdir(path):
                fp = os.path.join(path, f)
                if os.path.isfile(fp):
                    os.remove(fp)
            logger.info(MESSAGES["DIR_CLEARED"].format(path=path))
    except Exception as e:
        logger.exception(MESSAGES["DIR_CLEAR_FAILED"].format(path=path), exc_info=e)


# ---------------------------
# 2. Snapshot management
# ---------------------------
def archive_snapshot(snapshot_path: str, archive_dir: str) -> str:
    """
    Move a snapshot to the archive directory with timestamp.
    Returns new archived path.
    """
    try:
        ensure_dir(archive_dir)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{Path(snapshot_path).stem}_{timestamp}{Path(snapshot_path).suffix}"
        archived_path = os.path.join(archive_dir, filename)
        shutil.move(snapshot_path, archived_path)
        logger.info(MESSAGES["SNAPSHOT_ARCHIVED"].format(path=archived_path))
        return archived_path
    except Exception as e:
        logger.exception(MESSAGES["SNAPSHOT_ARCHIVE_FAILED"].format(path=snapshot_path), exc_info=e)
        return snapshot_path


def delete_snapshot(snapshot_path: str) -> None:
    """Delete a snapshot file safely."""
    try:
        if os.path.exists(snapshot_path):
            os.remove(snapshot_path)
            logger.info(MESSAGES["SNAPSHOT_DELETED"].format(path=snapshot_path))
        else:
            logger.warning(MESSAGES["SNAPSHOT_NOT_FOUND"].format(path=snapshot_path))
    except Exception as e:
        logger.exception(MESSAGES["SNAPSHOT_DELETE_FAILED"].format(path=snapshot_path), exc_info=e)


# ---------------------------
# 3. Zone setup management
# ---------------------------
def save_zone_config(zone_data: dict, zone_dir: str, zone_id: str) -> str:
    """
    Save zone configuration as JSON file.
    """
    import json
    try:
        ensure_dir(zone_dir)
        path = os.path.join(zone_dir, f"{zone_id}.json")
        with open(path, "w") as f:
            json.dump(zone_data, f, indent=4)
        logger.info(MESSAGES["ZONE_CONFIG_SAVED"].format(path=path))
        return path
    except Exception as e:
        logger.exception(MESSAGES["ZONE_CONFIG_SAVE_FAILED"].format(zone=zone_id), exc_info=e)
        return ""


def load_zone_config(zone_dir: str, zone_id: str) -> dict:
    """
    Load zone configuration JSON file.
    """
    import json
    path = os.path.join(zone_dir, f"{zone_id}.json")
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            logger.info(MESSAGES["ZONE_CONFIG_LOADED"].format(path=path))
            return data
        else:
            logger.warning(MESSAGES["ZONE_CONFIG_NOT_FOUND"].format(zone=zone_id))
            return {}
    except Exception as e:
        logger.exception(MESSAGES["ZONE_CONFIG_LOAD_FAILED"].format(zone=zone_id), exc_info=e)
        return {}


# ---------------------------
# 4. Cleanup helpers
# ---------------------------
def cleanup_old_files(directory: str, days: int = 7) -> int:
    """
    Delete files older than N days in a directory.
    Returns number of files deleted.
    """
    deleted = 0
    try:
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        for f in Path(directory).glob("*"):
            if f.is_file():
                mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    f.unlink()
                    deleted += 1
        logger.info(MESSAGES["FILES_CLEANED"].format(count=deleted, dir=directory))
        return deleted
    except Exception as e:
        logger.exception(MESSAGES["FILES_CLEAN_FAILED"].format(dir=directory), exc_info=e)
        return 0
