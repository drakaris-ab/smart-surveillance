from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import numpy as np, cv2, requests, base64
# pyrefly: ignore [missing-import]
import insightface
from datetime import datetime
from typing import List
from pydantic import BaseModel
from backend.config.settings import settings

from backend.database.database import get_db
from backend.database.models import FaceReUser
from backend.config.logging_config import logger
from backend.util.messages import messages   # ✅ centralized messages
from backend.util.face_cache import face_cache

router = APIRouter(prefix="/face-re-users", tags=["Face Recognition Users"])

# -------------------------
# Load InsightFace model once
# -------------------------
model = insightface.app.FaceAnalysis(name="buffalo_l", providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
model.prepare(ctx_id=0, det_size=(640, 640))

def extract_faces(frame):
    faces = model.get(frame)
    return faces if faces else []

def crop_and_encode_face(frame, bbox):
    x1, y1, x2, y2 = map(int, bbox)
    face_crop = frame[y1:y2, x1:x2]
    _, buffer = cv2.imencode('.jpg', face_crop)
    return base64.b64encode(buffer).decode('utf-8')

# -------------------------
# Pydantic Schemas
# -------------------------
class FaceReUserCreate(BaseModel):
    name: str
    phone: str | None = None
    address: str | None = None
    aadhaar: str | None = None
    criminal_flag: bool = False
    embedding: List[float]

class FaceReUserResponse(FaceReUserCreate):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True

# -------------------------
# CRUD Routes
# -------------------------
@router.post("/enroll", response_model=FaceReUserResponse)
def enroll_face_user(data: FaceReUserCreate, db: Session = Depends(get_db)):
    try:
        user = FaceReUser(
            name=data.name,
            phone=data.phone,
            address=data.address,
            aadhaar=data.aadhaar,
            criminal_flag=data.criminal_flag,
            embedding=data.embedding,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"{messages['FACE_USER_CREATED']} (id={user.id}, name={user.name})")
        return user
    except Exception as e:
        logger.exception(f"Enroll failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to enroll user")

@router.get("", response_model=List[FaceReUserResponse])
def get_all_face_users(db: Session = Depends(get_db)):
    try:
        users = db.query(FaceReUser).all()
        logger.info(f"Retrieved {len(users)} face users")
        return users
    except Exception as e:
        logger.exception(f"{messages['FACE_USER_ERROR']}: {e}")
        raise HTTPException(status_code=500, detail=messages["FACE_USER_ERROR"])

@router.get("/{user_id}", response_model=FaceReUserResponse)
def get_face_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(FaceReUser).filter(FaceReUser.id == user_id).first()
    if not user:
        logger.warning(f"{messages['FACE_USER_NOT_FOUND']} (id={user_id})")
        raise HTTPException(status_code=404, detail=messages["FACE_USER_NOT_FOUND"])
    logger.info(f"Retrieved face user {user_id}")
    return user

@router.put("/{user_id}", response_model=FaceReUserResponse)
def update_face_user(user_id: int, data: FaceReUserCreate, db: Session = Depends(get_db)):
    user = db.query(FaceReUser).filter(FaceReUser.id == user_id).first()
    if not user:
        logger.warning(f"{messages['FACE_USER_NOT_FOUND']} (id={user_id})")
        raise HTTPException(status_code=404, detail=messages["FACE_USER_NOT_FOUND"])

    for key, value in data.dict().items():
        setattr(user, key, value)
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    logger.info(f"{messages['FACE_USER_UPDATED']} (id={user.id})")
    return user

@router.delete("/{user_id}")
def delete_face_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(FaceReUser).filter(FaceReUser.id == user_id).first()
    if not user:
        logger.warning(f"{messages['FACE_USER_NOT_FOUND']} (id={user_id})")
        raise HTTPException(status_code=404, detail=messages["FACE_USER_NOT_FOUND"])
    db.delete(user)
    db.commit()
    logger.info(f"{messages['FACE_USER_DELETED']} (id={user_id})")
    return {"status": "deleted", "user_id": user_id, "message": messages["FACE_USER_DELETED"]}

# -------------------------
# Recognition Routes
# -------------------------
@router.post("/recognize/upload")
async def recognize_face(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        np_arr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        faces = extract_faces(frame)
        if not faces:
            logger.info(messages["NO_FACES"])
            return {"status": "no_faces", "message": messages["NO_FACES"]}

        face_cache.refresh_if_needed(db)
        results = []
        
        for face in faces:
            emb = face.embedding.tolist()
            bbox = face.bbox.astype(int).tolist()
            thumbnail = crop_and_encode_face(frame, bbox)

            matched_user, best_sim = face_cache.find_best_match(emb, threshold=0.6)
            
            if matched_user:
                matched = {
                    "status": "recognized",
                    "details": {
                        "id": matched_user["id"],
                        "name": matched_user["name"],
                    },
                    "similarity": best_sim,
                    "thumbnail": thumbnail
                }
                results.append(matched)
            else:
                results.append({"status": "unrecognized", "embedding": emb, "thumbnail": thumbnail})

        logger.info(messages["RECOGNITION_SUCCESS"])
        return {"faces": results, "message": messages["RECOGNITION_SUCCESS"]}
    except Exception as e:
        logger.exception(f"{messages['RECOGNITION_FAILED']}: {e}")
        raise HTTPException(status_code=500, detail=messages["RECOGNITION_FAILED"])

@router.get("/recognize/{camera_id}")
def recognize_live(camera_id: int, db: Session = Depends(get_db)):
    try:
        from backend.database.models import Camera
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")

        resp = requests.get(f"{settings.BASE_API_URL}/cameras/{camera_id}/latest_frame", timeout=10)
        if resp.status_code != 200 or not resp.content:
            raise HTTPException(status_code=503, detail=messages["CAMERA_UNAVAILABLE"])

        nparr = np.frombuffer(resp.content, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(status_code=503, detail=messages["FRAME_NOT_AVAILABLE"])

        faces = extract_faces(frame)
        if not faces:
            return {"status": "no_faces", "message": messages["NO_FACES"]}

        face_cache.refresh_if_needed(db)
        results = []
        
        for face in faces:
            emb = face.embedding.tolist()
            bbox = face.bbox.astype(int).tolist()
            thumbnail = crop_and_encode_face(frame, bbox)

            matched_user, best_sim = face_cache.find_best_match(emb, threshold=0.6)
            
            if matched_user:
                matched = {
                    "status": "recognized",
                    "details": {
                        "id": matched_user["id"],
                        "name": matched_user["name"],
                    },
                    "similarity": best_sim,
                    "thumbnail": thumbnail
                }
                results.append(matched)
            else:
                results.append({"status": "unrecognized", "embedding": emb, "thumbnail": thumbnail})

        return {"faces": results, "message": messages["RECOGNITION_SUCCESS"]}
    except Exception as e:
        logger.exception(f"{messages['RECOGNITION_FAILED']}: {e}")
        raise HTTPException(status_code=500, detail=messages["RECOGNITION_FAILED"])
