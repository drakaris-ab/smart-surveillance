# camera_mapping_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from backend.database.database import get_db
from backend.database.models import UserCameraMapping
from backend.config.router_message import MESSAGES
from backend.config.logging_config import logger
from backend.auth.auth_dependency import get_current_user

router = APIRouter(prefix="/camera-mapping", tags=["Camera Mapping"])

# ---------------------------
# Request Models
# ---------------------------
class CameraAssignRequest(BaseModel):
    camera_id: int

class CameraMappingUpdateRequest(BaseModel):
    camera_id: int

# ---------------------------
# Assign Camera to User
# ---------------------------
@router.post("/assign", dependencies=[Depends(get_current_user)])
def assign_camera(req: CameraAssignRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        mapping = db.query(UserCameraMapping).filter(UserCameraMapping.user_id == current_user["id"]).first()
        if mapping:
            mapping.camera_id = req.camera_id
            mapping.updated_at = datetime.utcnow()
            message = MESSAGES["CAMERA_ASSIGN_UPDATE_SUCCESS"]
        else:
            mapping = UserCameraMapping(user_id=current_user["id"], camera_id=req.camera_id)
            db.add(mapping)
            message = MESSAGES["CAMERA_ASSIGN_SUCCESS"]

        db.commit()
        db.refresh(mapping)
        logger.info(f"{message} - User: {current_user['sub']}, Camera ID: {req.camera_id}")
        return {"status": "success", "message": message, "data": mapping}

    except Exception as e:
        db.rollback()
        logger.error(f"{MESSAGES['CAMERA_ASSIGN_FAIL']}: {e}")
        raise HTTPException(status_code=500, detail=MESSAGES["CAMERA_ASSIGN_FAIL"])

# ---------------------------
# Update User–Camera Mapping
# ---------------------------
@router.put("/assign/{mapping_id}", dependencies=[Depends(get_current_user)])
def update_user_camera(mapping_id: int, req: CameraMappingUpdateRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    mapping = db.query(UserCameraMapping).filter(UserCameraMapping.id == mapping_id).first()
    if not mapping:
        logger.warning(MESSAGES["CAMERA_MAPPING_NOT_FOUND"])
        return {"status": "error", "message": MESSAGES["CAMERA_MAPPING_NOT_FOUND"], "id": mapping_id}

    try:
        mapping.camera_id = req.camera_id
        mapping.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(mapping)
        logger.info(f"{MESSAGES['CAMERA_MAPPING_UPDATE_SUCCESS']} - ID {mapping_id} by {current_user['sub']}")
        return {"status": "success", "message": MESSAGES["CAMERA_MAPPING_UPDATE_SUCCESS"], "data": mapping}
    except Exception as e:
        db.rollback()
        logger.error(f"{MESSAGES['CAMERA_MAPPING_UPDATE_FAIL']}: {e}")
        raise HTTPException(status_code=500, detail=MESSAGES["CAMERA_MAPPING_UPDATE_FAIL"])

# ---------------------------
# Delete User–Camera Mapping
# ---------------------------
@router.delete("/assign/{mapping_id}", dependencies=[Depends(get_current_user)])
def delete_user_camera(mapping_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    mapping = db.query(UserCameraMapping).filter(UserCameraMapping.id == mapping_id).first()
    if not mapping:
        logger.warning(MESSAGES["CAMERA_MAPPING_NOT_FOUND"])
        return {"status": "error", "message": MESSAGES["CAMERA_MAPPING_NOT_FOUND"], "id": mapping_id}

    try:
        db.delete(mapping)
        db.commit()
        logger.info(f"{MESSAGES['CAMERA_MAPPING_DELETE_SUCCESS']} - ID {mapping_id} by {current_user['sub']}")
        return {"status": "success", "message": MESSAGES["CAMERA_MAPPING_DELETE_SUCCESS"], "id": mapping_id}
    except Exception as e:
        db.rollback()
        logger.error(f"{MESSAGES['CAMERA_MAPPING_DELETE_FAIL']}: {e}")
        raise HTTPException(status_code=500, detail=MESSAGES["CAMERA_MAPPING_DELETE_FAIL"])

# ---------------------------
# Get User's Assigned Camera
# ---------------------------
@router.get("/user-camera", dependencies=[Depends(get_current_user)])
def get_user_camera(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    mapping = db.query(UserCameraMapping).filter(UserCameraMapping.user_id == current_user["id"]).first()
    if not mapping:
        logger.warning(MESSAGES["CAMERA_MAPPING_NOT_FOUND"])
        return {"status": "error", "message": MESSAGES["CAMERA_MAPPING_NOT_FOUND"], "data": None}

    try:
        logger.info(f"{MESSAGES['CAMERA_MAPPING_FETCH_SUCCESS']} - User: {current_user['sub']}")
        return {"status": "success", "message": MESSAGES["CAMERA_MAPPING_FETCH_SUCCESS"], "data": mapping.camera}
    except Exception as e:
        logger.error(f"{MESSAGES['CAMERA_MAPPING_FETCH_FAIL']}: {e}")
        raise HTTPException(status_code=500, detail=MESSAGES["CAMERA_MAPPING_FETCH_FAIL"])
