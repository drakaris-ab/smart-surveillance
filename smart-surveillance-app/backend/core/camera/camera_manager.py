# app/services/camera_service.py
# Handles camera streams (RTSP/WebRTC)

import datetime
from sqlalchemy.orm import Session
from backend.database import models
from backend.utils.log_activity import log_event
from backend.config.logging_config import logger     # ✅ central logging
from backend.config.messages import MESSAGES         # ✅ central messages


class CameraService:
    def __init__(self):
        logger.info(MESSAGES["CAMERA_SERVICE_INIT"])

    def register_camera(self, db: Session, name: str, location: str, stream_url: str,
                        description: str = None, owner_id: int = None) -> models.Camera | None:
        """
        Register a new camera in the system.
        """
        try:
            camera = models.Camera(
                name=name,
                location=location,
                stream_url=stream_url,
                description=description,
                owner_id=owner_id,
                created_at=datetime.datetime.now()
            )
            db.add(camera)
            db.commit()
            db.refresh(camera)

            log_event("CAMERA_REGISTER", MESSAGES["CAMERA_REGISTER"].format(name=name))
            logger.info(MESSAGES["CAMERA_REGISTER"].format(name=name))
            return camera
        except Exception as e:
            db.rollback()
            logger.exception(MESSAGES["CAMERA_REGISTER_FAILED"].format(name=name), exc_info=e)
            return None

    def list_cameras(self, db: Session, limit: int = 50):
        """
        Retrieve all registered cameras.
        """
        try:
            cameras = db.query(models.Camera).order_by(models.Camera.id).limit(limit).all()
            logger.debug(MESSAGES["CAMERA_LIST"].format(count=len(cameras)))
            return cameras
        except Exception as e:
            logger.exception(MESSAGES["CAMERA_LIST_FAILED"], exc_info=e)
            return []

    def get_camera(self, db: Session, camera_id: int) -> models.Camera | None:
        """
        Retrieve a single camera by ID.
        """
        try:
            camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
            if camera:
                logger.debug(MESSAGES["CAMERA_FETCH"].format(id=camera_id))
            else:
                logger.warning(MESSAGES["CAMERA_NOT_FOUND"].format(id=camera_id))
            return camera
        except Exception as e:
            logger.exception(MESSAGES["CAMERA_FETCH_FAILED"].format(id=camera_id), exc_info=e)
            return None

    def update_camera(self, db: Session, camera_id: int, **kwargs) -> models.Camera | None:
        """
        Update camera details (name, location, stream_url, description).
        """
        try:
            camera = self.get_camera(db, camera_id)
            if not camera:
                logger.warning(MESSAGES["CAMERA_NOT_FOUND"].format(id=camera_id))
                return None

            for key, value in kwargs.items():
                if hasattr(camera, key) and value is not None:
                    setattr(camera, key, value)

            db.commit()
            db.refresh(camera)

            log_event("CAMERA_UPDATE", MESSAGES["CAMERA_UPDATE"].format(id=camera_id))
            logger.info(MESSAGES["CAMERA_UPDATE"].format(id=camera_id))
            return camera
        except Exception as e:
            db.rollback()
            logger.exception(MESSAGES["CAMERA_UPDATE_FAILED"].format(id=camera_id), exc_info=e)
            return None

    def delete_camera(self, db: Session, camera_id: int, owner_id: int) -> bool:
        """
        Delete a camera by ID (only if owned by user).
        """
        try:
            camera = db.query(models.Camera).filter(
                models.Camera.id == camera_id,
                models.Camera.owner_id == owner_id
            ).first()

            if camera:
                db.delete(camera)
                db.commit()
                log_event("CAMERA_DELETE", MESSAGES["CAMERA_DELETE"].format(id=camera_id))
                logger.info(MESSAGES["CAMERA_DELETE"].format(id=camera_id))
                return True
            else:
                logger.warning(MESSAGES["CAMERA_NOT_FOUND"].format(id=camera_id))
                return False
        except Exception as e:
            db.rollback()
            logger.exception(MESSAGES["CAMERA_DELETE_FAILED"].format(id=camera_id), exc_info=e)
            return False
