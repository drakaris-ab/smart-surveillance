from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import jwt, JWTError

from backend.config.settings import settings
from backend.config.logging_config import logger
from backend.config.router_message import MESSAGES

# --- Security settings ---
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = int(getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------
# Password utilities
# ---------------------------
def hash_password(password: str) -> str:
    try:
        hashed = pwd_context.hash(password)
        logger.debug("Password hashed successfully.")
        return hashed
    except Exception as e:
        logger.exception(MESSAGES["PASSWORD_HASH_FAILED"].format(error=str(e)))
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        logger.debug("Password verification result: %s", result)
        return result
    except Exception as e:
        logger.exception(MESSAGES["PASSWORD_VERIFY_FAILED"].format(error=str(e)))
        return False

# ---------------------------
# Token utilities
# ---------------------------
def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    try:
        expire_minutes = expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES
        expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
        to_encode = {**data, "exp": expire, "type": "access"}
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(MESSAGES["ACCESS_TOKEN_CREATED"].format(subject=data.get("sub")))
        return token
    except Exception as e:
        logger.exception(MESSAGES["TOKEN_CREATION_FAILED"].format(error=str(e)))
        raise

def create_refresh_token(data: dict, expires_delta: Optional[int] = None) -> str:
    try:
        expire_days = expires_delta or REFRESH_TOKEN_EXPIRE_DAYS
        expire = datetime.utcnow() + timedelta(days=expire_days)
        to_encode = {**data, "exp": expire, "type": "refresh"}
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(MESSAGES["REFRESH_TOKEN_CREATED"].format(subject=data.get("sub")))
        return token
    except Exception as e:
        logger.exception(MESSAGES["TOKEN_CREATION_FAILED"].format(error=str(e)))
        raise

def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug("Token decoded successfully.")
        return payload
    except JWTError as e:
        logger.warning(MESSAGES["TOKEN_INVALID"].format(error=str(e)))
        return None
    except Exception as e:
        logger.exception(MESSAGES["TOKEN_DECODE_FAILED"].format(error=str(e)))
        return None
