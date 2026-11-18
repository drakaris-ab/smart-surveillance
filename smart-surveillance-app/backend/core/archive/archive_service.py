# app/services/archive_service.py

import datetime
from sqlalchemy.orm import Session
from backend.database import models
from backend.utils import file_ops
from backend.utils.log_activity import log_event
from backend.config.logging_config import logger     # ✅ central logging
from backend.config.messages import MESSAGES         # ✅ central messages


class ArchiveService:
    def __init__(self, archive_dir: str = "app/static/archive"):
        self.archive_dir = archive_dir
        try:
            file_ops.ensure_dir(self.archive_dir)
            logger.info(MESSAGES["ARCHIVE_INIT"].format(dir=self.archive_dir))
        except Exception as e:
            logger.exception(MESSAGES["ARCHIVE_INIT_FAILED"], exc_info=e)

    def archive_snapshot(self, db: Session, snapshot_path: str, camera_id: str) -> models.Archive | None:
        """
        Move a snapshot into the archive directory and persist metadata in DB.
        """
        try:
            archived_path = file_ops.archive_snapshot(snapshot_path, self.archive_dir)

            archive_entry = models.Archive(
                camera_id=camera_id,
                file_path=archived_path,
                timestamp=datetime.datetime.now()
            )
            db.add(archive_entry)
            db.commit()
            db.refresh(archive_entry)

            log_event("ARCHIVE", MESSAGES["ARCHIVE_SNAPSHOT"].format(camera=camera_id), archived_path)
            logger.info(MESSAGES["ARCHIVE_SNAPSHOT"].format(camera=camera_id))
            return archive_entry
        except Exception as e:
            db.rollback()
            logger.exception(MESSAGES["ARCHIVE_SNAPSHOT_FAILED"].format(camera=camera_id), exc_info=e)
            return None

    def list_archives(self, db: Session, camera_id: str = None, limit: int = 50):
        """
        Retrieve recent archived snapshots, optionally filtered by camera.
        """
        try:
            query = db.query(models.Archive).order_by(models.Archive.timestamp.desc())
            if camera_id:
                query = query.filter(models.Archive.camera_id == camera_id)
            archives = query.limit(limit).all()
            logger.debug(MESSAGES["ARCHIVE_LIST"].format(count=len(archives)))
            return archives
        except Exception as e:
            logger.exception(MESSAGES["ARCHIVE_LIST_FAILED"], exc_info=e)
            return []

    def delete_archive(self, db: Session, archive_id: int) -> bool:
        """
        Delete an archive entry and remove the file from disk.
        """
        try:
            archive = db.query(models.Archive).filter(models.Archive.id == archive_id).first()
            if archive:
                file_ops.delete_snapshot(archive.file_path)
                db.delete(archive)
                db.commit()
                log_event("ARCHIVE_DELETE", MESSAGES["ARCHIVE_DELETE"].format(id=archive_id), archive.file_path)
                logger.info(MESSAGES["ARCHIVE_DELETE"].format(id=archive_id))
                return True
            else:
                logger.warning(MESSAGES["ARCHIVE_NOT_FOUND"].format(id=archive_id))
                return False
        except Exception as e:
            db.rollback()
            logger.exception(MESSAGES["ARCHIVE_DELETE_FAILED"].format(id=archive_id), exc_info=e)
            return False

    def cleanup_old_archives(self, db: Session, days: int = 30) -> int:
        """
        Delete archives older than N days from DB and filesystem.
        Returns number of archives deleted.
        """
        try:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
            old_archives = db.query(models.Archive).filter(models.Archive.timestamp < cutoff).all()

            deleted_count = 0
            for archive in old_archives:
                try:
                    file_ops.delete_snapshot(archive.file_path)
                    db.delete(archive)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(MESSAGES["ARCHIVE_DELETE_FILE_FAILED"].format(path=archive.file_path), exc_info=e)

            db.commit()
            log_event("ARCHIVE_CLEANUP", MESSAGES["ARCHIVE_CLEANUP"].format(count=deleted_count), self.archive_dir)
            logger.info(MESSAGES["ARCHIVE_CLEANUP"].format(count=deleted_count))
            return deleted_count
        except Exception as e:
            db.rollback()
            logger.exception(MESSAGES["ARCHIVE_CLEANUP_FAILED"], exc_info=e)
            return 0
