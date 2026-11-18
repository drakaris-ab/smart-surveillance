# backend/auth/jwt_handler.py


from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from backend.config.settings import settings
from backend.config.messages import MESSAGES
from backend.config.logging_config import logger   # ✅ central logging



# --- Password hashing context ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a plain password using bcrypt."""
    try:
        hashed = pwd_context.hash(password)
        logger.debug("Password hashed successfully.")
        return hashed
    except Exception as e:
        logger.exception("Error hashing password: %s", str(e))
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        logger.debug("Password verification result: %s", result)
        return result
    except Exception as e:
        logger.exception("Error verifying password: %s", str(e))
        return False

def create_access_token(data: dict, expires_delta: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """
    Create a JWT access token.
    :param data: dict payload (e.g., {"sub": user_id})
    :param expires_delta: expiration in minutes (defaults to settings)
    """
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=expires_delta)
        to_encode.update({"exp": expire})

        token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.info("Access token created for subject: %s", data.get("sub"))
        return token
    except Exception as e:
        logger.exception("Error creating token: %s", str(e))
        raise

def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.debug("Token decoded successfully for subject: %s", payload.get("sub"))
        return payload
    except JWTError as e:
        logger.warning("JWT decode failed: %s", str(e))
        return None
    except Exception as e:
        logger.exception("Unexpected error decoding token: %s", str(e))
        return None
