# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from backend.database.database import get_db
from backend.database.models import User
from backend.auth.jwt_handler import get_password_hash
from backend.config.logging_config import logger
from backend.config.router_message import MESSAGES
from backend.auth.auth_dependency import require_role, get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

# ---------------------------
# Request Models
# ---------------------------
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "Monitor"

class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role: str | None = None

# ---------------------------
# List Users (Admin only)
# ---------------------------
@router.get("/", dependencies=[Depends(require_role("Admin"))])
def list_users(db: Session = Depends(get_db)):
    try:
        users = db.query(User).all()
        logger.info(MESSAGES["USER_FETCH_SUCCESS"])
        return {"status": "success", "message": MESSAGES["USER_FETCH_SUCCESS"], "data": users}
    except Exception as e:
        logger.exception(MESSAGES["USER_FETCH_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["USER_FETCH_FAIL"])

# ---------------------------
# Add User (Admin only)
# ---------------------------
@router.post("/", dependencies=[Depends(require_role("Admin"))])
def add_user(user: UserCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        existing = db.query(User).filter(User.username == user.username).first()
        if existing:
            logger.warning(MESSAGES["USER_EXISTS"])
            raise HTTPException(status_code=400, detail=MESSAGES["USER_EXISTS"])

        hashed_pw = get_password_hash(user.password)
        new_user = User(
            username=user.username,
            password=hashed_pw,
            role=user.role,
            created_by=current_user["sub"],
            created_at=datetime.utcnow()
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(MESSAGES["USER_ADD_SUCCESS"].format(id=new_user.id))
        return {"status": "success", "message": MESSAGES["USER_ADD_SUCCESS"], "data": new_user}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["USER_ADD_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["USER_ADD_FAIL"])

# ---------------------------
# Update User (Admin only)
# ---------------------------
@router.put("/{user_id}", dependencies=[Depends(require_role("Admin"))])
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            logger.warning(MESSAGES["USER_NOT_FOUND"])
            raise HTTPException(status_code=404, detail=MESSAGES["USER_NOT_FOUND"])

        if user.username:
            db_user.username = user.username
        if user.password:
            db_user.password = get_password_hash(user.password)
        if user.role:
            db_user.role = user.role

        db_user.updated_by = current_user["sub"]
        db_user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(db_user)
        logger.info(MESSAGES["USER_UPDATE_SUCCESS"].format(id=user_id))
        return {"status": "success", "message": MESSAGES["USER_UPDATE_SUCCESS"], "data": db_user}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["USER_UPDATE_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["USER_UPDATE_FAIL"])

# ---------------------------
# Delete User (Admin only)
# ---------------------------
@router.delete("/{user_id}", dependencies=[Depends(require_role("Admin"))])
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            logger.warning(MESSAGES["USER_NOT_FOUND"])
            raise HTTPException(status_code=404, detail=MESSAGES["USER_NOT_FOUND"])

        db.delete(db_user)
        db.commit()
        logger.info(MESSAGES["USER_DELETE_SUCCESS"].format(id=user_id, user=current_user["sub"]))
        return {"status": "success", "message": MESSAGES["USER_DELETE_SUCCESS"], "id": user_id}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["USER_DELETE_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["USER_DELETE_FAIL"])
