from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
import random

from backend.database import models, schemas
from backend.database.session import get_db
from backend.auth.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.core.email.email_service import send_email
from backend.auth.auth_dependency import get_current_user  
from backend.config.logging_config import logger
from backend.config.router_message import MESSAGES

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# In‑memory OTP store (cleared when server restarts)
otp_store = {}

# ---------------------------
# Request schema for refresh
# ---------------------------
class RefreshRequest(BaseModel):
    refresh_token: str

# ---------------------------
# Signup
# ---------------------------
@router.post("/signup")
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        if db.query(models.User).filter(models.User.username == user.username).first():
            logger.warning(MESSAGES["USER_EXISTS"].format(username=user.username))
            raise HTTPException(status_code=400, detail=MESSAGES["USER_EXISTS"])

        new_user = models.User(
            username=user.username,
            email=getattr(user, "email", None),
            phone=getattr(user, "phone", None),
            password=hash_password(user.password),
            role="user"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(MESSAGES["USER_CREATED"].format(username=new_user.username))
        return {"message": MESSAGES["USER_CREATED"].format(username=new_user.username)}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(MESSAGES["SIGNUP_FAILED"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["SIGNUP_FAILED"])

# ---------------------------
# Login
# ---------------------------
@router.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.username == user.username).first()
        if not db_user or not verify_password(user.password, db_user.password):
            logger.warning(MESSAGES["LOGIN_FAIL"].format(username=user.username))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MESSAGES["LOGIN_FAIL"])

        access_token = create_access_token({"sub": db_user.username, "role": db_user.role, "id": str(db_user.id)})
        refresh_token = create_refresh_token({"sub": db_user.username})

        logger.info(MESSAGES["LOGIN_SUCCESS"].format(username=db_user.username))
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "username": db_user.username,
            "role": db_user.role,
            "id": db_user.id
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(MESSAGES["LOGIN_FAILED"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["LOGIN_FAILED"])

# ---------------------------
# Refresh
# ---------------------------
@router.post("/refresh")
def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(request.refresh_token)
        if not payload or payload.get("type") != "refresh":
            logger.warning(MESSAGES["TOKEN_INVALID"])
            raise HTTPException(status_code=401, detail=MESSAGES["TOKEN_INVALID"])

        user = db.query(models.User).filter(models.User.username == payload.get("sub")).first()
        if not user:
            logger.warning(MESSAGES["USER_NOT_FOUND"].format(username=payload.get("sub")))
            raise HTTPException(status_code=401, detail=MESSAGES["USER_NOT_FOUND"])

        new_access_token = create_access_token({"sub": user.username, "role": user.role, "id": str(user.id)})
        logger.info(MESSAGES["TOKEN_REFRESHED"].format(username=user.username))
        return {"access_token": new_access_token, "token_type": "bearer"}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(MESSAGES["TOKEN_REFRESH_FAILED"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["TOKEN_REFRESH_FAILED"])


# ---------------------------
# Dashboard
# ---------------------------
@router.get("/dashboard")
def dashboard(current_user: models.User = Depends(get_current_user)):
    logger.info(MESSAGES["DASHBOARD_ACCESS"].format(username=current_user.username))
    return {
        "message": f"Welcome {current_user.username}!",
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role
    }

# ---------------------------
# User Management
# ---------------------------
@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    try:
        users = db.query(models.User).all()
        logger.info("Fetched all users successfully.")
        return users
    except Exception as e:
        logger.exception("Failed to fetch users: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch users")

@router.put("/users/{user_id}")
def edit_user(user_id: int, user: dict, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if not db_user:
            logger.warning(MESSAGES["USER_NOT_FOUND"].format(username=user_id))
            raise HTTPException(status_code=404, detail=MESSAGES["USER_NOT_FOUND"])
        for key, value in user.items():
            setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
        logger.info(MESSAGES["USER_UPDATED"].format(id=user_id))
        return db_user
    except Exception as e:
        logger.exception("Failed to update user: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to update user")

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if not db_user:
            logger.warning(MESSAGES["USER_NOT_FOUND"].format(username=user_id))
            raise HTTPException(status_code=404, detail=MESSAGES["USER_NOT_FOUND"])
        db.delete(db_user)
        db.commit()
        logger.info(MESSAGES["USER_DELETED"].format(id=user_id))
        return {"detail": MESSAGES["USER_DELETED"].format(id=user_id)}
    except Exception as e:
        logger.exception("Failed to delete user: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to delete user")

# ---------------------------
# Password Reset Flow
# ---------------------------
@router.post("/request-reset")
def request_reset(data: dict, db: Session = Depends(get_db)):
    username = data.get("username")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        logger.warning(MESSAGES["USER_NOT_FOUND"].format(username=username))
        raise HTTPException(status_code=404, detail=MESSAGES["USER_NOT_FOUND"])
    otp = str(random.randint(100000, 999999))
    otp_store[username] = otp
    try:
        send_email(user.email, "Password Reset OTP", f"Your OTP is {otp}")
        logger.info(MESSAGES["OTP_SENT"].format(username=username))
    except Exception as e:
        logger.error(MESSAGES["OTP_SEND_FAILED"].format(username=username), exc_info=e)
        raise HTTPException(status_code=500, detail=MESSAGES["OTP_SEND_FAILED"])
    return {"message": MESSAGES["OTP_SENT"].format(username=username)}

@router.post("/verify-otp")
def verify_otp(data: dict):
    username, otp = data.get("username"), data.get("otp")
    if otp_store.get(username) != otp:
        logger.warning(MESSAGES["OTP_INVALID"].format(username=username))
        raise HTTPException(status_code=400, detail=MESSAGES["OTP_INVALID"])
    logger.info(MESSAGES["OTP_VERIFIED"].format(username=username))
    return {"message": MESSAGES["OTP_VERIFIED"]}

@router.post("/reset-password")
def reset_password(data: dict, db: Session = Depends(get_db)):
    try:
        username, new_password = data.get("username"), data.get("new_password")
        if not username or not new_password:
            logger.warning(MESSAGES["MISSING_FIELDS"])
            raise HTTPException(status_code=400, detail=MESSAGES["MISSING_FIELDS"])

        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            logger.warning(MESSAGES["USER_NOT_FOUND"].format(username=username))
            raise HTTPException(status_code=404, detail=MESSAGES["USER_NOT_FOUND"])

        # Update password securely
        user.password = hash_password(new_password)
        db.commit()
        db.refresh(user)

        # Clear OTP after successful reset
        otp_store.pop(username, None)

        logger.info(MESSAGES["PASSWORD_RESET"].format(username=username))
        return {"message": MESSAGES["PASSWORD_RESET"].format(username=username)}

    except HTTPException as http_exc:
        # Already logged above, just re-raise
        raise http_exc
    except Exception as e:
        logger.exception(MESSAGES["PASSWORD_RESET_FAILED"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["PASSWORD_RESET_FAILED"])
