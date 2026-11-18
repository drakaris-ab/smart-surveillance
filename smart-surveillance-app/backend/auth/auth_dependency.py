from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from backend.auth.auth_utils import decode_token
from backend.config.messages import MESSAGES
from backend.config.logging_config import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Decode JWT and return user payload."""
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        logger.warning(MESSAGES["TOKEN_INVALID"])
        raise HTTPException(status_code=401, detail=MESSAGES["TOKEN_INVALID"])
    logger.debug("Token decoded successfully for user: %s", payload.get("sub"))
    return payload

def require_role(required_role: str):
    """Dependency to enforce role-based access control."""
    def role_checker(user: dict = Depends(get_current_user)):
        try:
            if user.get("role") != required_role:
                logger.warning(
                    "Access denied. Required role: %s, user role: %s",
                    required_role, user.get("role")
                )
                raise HTTPException(status_code=403, detail=MESSAGES["ROLE_FORBIDDEN"])
            logger.debug("Role check passed for user: %s", user.get("sub"))
            return user
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Unexpected error in role_checker: %s", str(e))
            raise HTTPException(status_code=500, detail="Role validation failed")
    return role_checker
