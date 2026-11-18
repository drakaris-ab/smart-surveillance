from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database.database import get_db
from backend.database.models import FaceReUser, Camera, UserCameraAssignment
from sqlalchemy import or_
from pydantic import BaseModel
from datetime import datetime
from backend.config.logging_config import logger
from backend.util.messages import messages   # ✅ import centralized messages

router = APIRouter(prefix="/assignments", tags=["User-Camera Assignments"])

class AssignmentRequest(BaseModel):
    user_id: int
    camera_ids: list[int]
    actor: str

@router.post("/assign")
def assign_or_update_camera(data: AssignmentRequest, db: Session = Depends(get_db)):
    """
    Reconcile assignments:
    - Any camera in camera_ids → tagged (untagged=False)
    - Any camera not in camera_ids → untagged=True
    """
    try:
        user = db.query(FaceReUser).filter(FaceReUser.id == data.user_id).first()
        if not user:
            logger.error(f"{messages['USER_NOT_FOUND']} (id={data.user_id})")
            raise HTTPException(status_code=404, detail=messages["USER_NOT_FOUND"])

        # Fetch all existing assignments for this user
        existing_assignments = db.query(UserCameraAssignment).filter(
            UserCameraAssignment.user_id == data.user_id
        ).all()

        results = []

        # 1️⃣ Handle cameras in the new list (tagged)
        for cam_id in data.camera_ids:
            camera = db.query(Camera).filter(Camera.id == cam_id).first()
            if not camera:
                logger.warning(f"{messages['CAMERA_NOT_FOUND']} (id={cam_id})")
                continue

            assignment = next((a for a in existing_assignments if a.camera_id == cam_id), None)
            if assignment:
                assignment.untagged = False
                assignment.updated_by = data.actor
                assignment.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(assignment)
                logger.info(f"{messages['ASSIGN_UPDATE_SUCCESS']} (user={data.user_id}, camera={cam_id})")
                results.append({"status": "updated", "camera_id": cam_id})
            else:
                new_assignment = UserCameraAssignment(
                    user_id=data.user_id,
                    camera_id=cam_id,
                    assigned_at=datetime.utcnow(),
                    created_by=data.actor,
                    untagged=False
                )
                db.add(new_assignment)
                db.commit()
                db.refresh(new_assignment)
                logger.info(f"{messages['ASSIGN_SUCCESS']} (user={data.user_id}, camera={cam_id})")
                results.append({"status": "inserted", "camera_id": cam_id})

        # 2️⃣ Handle cameras NOT in the new list (untagged)
        for assignment in existing_assignments:
            if assignment.camera_id not in data.camera_ids and not assignment.untagged:
                assignment.untagged = True
                assignment.updated_by = data.actor
                assignment.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(assignment)
                logger.info(f"{messages['ASSIGN_UNTAG_SUCCESS']} (user={data.user_id}, camera={assignment.camera_id})")
                results.append({"status": "untagged", "camera_id": assignment.camera_id})

        return {"user_id": data.user_id, "assignments": results}
    except Exception as e:
        logger.exception(f"{messages['ASSIGN_FAILED']} (user={data.user_id}): {e}")
        raise HTTPException(status_code=500, detail=messages["INTERNAL_ERROR"])

@router.get("/search")
def search_user(q: str, db: Session = Depends(get_db)):
    try:
        query = db.query(FaceReUser)

        # Build filters for phone, aadhaar, name
        filters = [
            FaceReUser.phone == str(q),
            FaceReUser.aadhaar == str(q),
            FaceReUser.name.ilike(f"%{q}%")
        ]

        # If q looks like an integer, also check id
        try:
            q_int = int(q)
            filters.append(FaceReUser.id == q_int)
        except ValueError:
            logger.debug(f"Search query '{q}' is not an integer, skipping ID filter")

        user = query.filter(or_(*filters)).first()
        if not user:
            logger.warning(f"{messages['VISITOR_NOT_FOUND']} (query={q})")
            raise HTTPException(status_code=404, detail=messages["VISITOR_NOT_FOUND"])

        # ✅ Only return active (tagged) cameras
        assignments = db.query(UserCameraAssignment).filter(
            UserCameraAssignment.user_id == user.id,
            UserCameraAssignment.untagged == False
        ).all()
        assigned_cameras = [a.camera_id for a in assignments]

        logger.info(f"Visitor found: id={user.id}, name={user.name}, assigned_cameras={assigned_cameras}")

        return {
            "id": user.id,
            "name": user.name,
            "phone": user.phone,
            "address": user.address,
            "aadhaar": user.aadhaar,
            "criminal_flag": user.criminal_flag,
            "assigned_cameras": assigned_cameras
        }

    except HTTPException as e:
        # Already logged above, just re-raise
        raise
    except Exception as e:
        logger.exception(f"{messages['SEARCH_FAILED']} (query={q}): {e}")
        raise HTTPException(status_code=500, detail=messages["INTERNAL_ERROR"])


@router.post("/untag/{user_id}/{camera_id}")
def untag_camera(user_id: int, camera_id: int, actor: str = Query(...), db: Session = Depends(get_db)):
    try:
        assignment = (
            db.query(UserCameraAssignment)
            .filter(UserCameraAssignment.user_id == user_id,
                    UserCameraAssignment.camera_id == camera_id)
            .first()
        )
        if not assignment:
            logger.error(f"{messages['ASSIGNMENT_NOT_FOUND']} (user={user_id}, camera={camera_id})")
            raise HTTPException(status_code=404, detail=messages["ASSIGNMENT_NOT_FOUND"])

        assignment.untagged = True
        assignment.updated_by = actor
        assignment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(assignment)
        logger.info(f"{messages['ASSIGN_UNTAG_SUCCESS']} (user={user_id}, camera={camera_id})")
        return {"status": "untagged", "camera_id": camera_id, "user_id": user_id, "message": messages["ASSIGN_UNTAG_SUCCESS"]}
    except Exception as e:
        logger.exception(f"{messages['UNTAG_FAILED']} (user={user_id}, camera={camera_id}): {e}")
        raise HTTPException(status_code=500, detail=messages["INTERNAL_ERROR"])
