# app/routers/modules.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from backend.database.database import get_db
from backend.database.models import User, Modules, UserModules
from backend.auth.auth_dependency import require_role, get_current_user
from backend.config.logging_config import logger
from backend.config.messages import MESSAGES

router = APIRouter(tags=["Modules & User Modules"])

# ---------------------------
# Request Models
# ---------------------------
class ModuleCreate(BaseModel):
    name: str
    enabled: bool = True

class ModuleUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None

# ---------------------------
# List Modules (Admin only)
# ---------------------------
@router.get("/modules", dependencies=[Depends(require_role("Admin"))])
def list_modules(db: Session = Depends(get_db)):
    try:
        modules = db.query(Modules).all()
        logger.info(MESSAGES["MODULE_FETCH_SUCCESS"])
        return {"status": "success", "message": MESSAGES["MODULE_FETCH_SUCCESS"], "data": modules}
    except Exception as e:
        logger.exception(MESSAGES["MODULE_FETCH_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["MODULE_FETCH_FAIL"])

# ---------------------------
# Add Module (Admin only)
# ---------------------------
@router.post("/modules", dependencies=[Depends(require_role("Admin"))])
def add_module(module: ModuleCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        existing = db.query(Modules).filter(Modules.name == module.name).first()
        if existing:
            logger.warning(MESSAGES["MODULE_EXISTS"])
            raise HTTPException(status_code=400, detail=MESSAGES["MODULE_EXISTS"])

        new_module = Modules(
            name=module.name,
            enabled=module.enabled,
            created_by=current_user["sub"],
            created_at=datetime.utcnow()
        )
        db.add(new_module)
        db.commit()
        db.refresh(new_module)
        logger.info(MESSAGES["MODULE_ADD_SUCCESS"].format(id=new_module.id))
        return {"status": "success", "message": MESSAGES["MODULE_ADD_SUCCESS"], "data": new_module}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["MODULE_ADD_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["MODULE_ADD_FAIL"])

# ---------------------------
# Update Module (Admin only)
# ---------------------------
@router.put("/modules/{module_id}", dependencies=[Depends(require_role("Admin"))])
def update_module(module_id: int, module: ModuleUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        db_module = db.query(Modules).filter(Modules.id == module_id).first()
        if not db_module:
            logger.warning(MESSAGES["MODULE_NOT_FOUND"])
            raise HTTPException(status_code=404, detail=MESSAGES["MODULE_NOT_FOUND"])

        if module.name:
            db_module.name = module.name
        if module.enabled is not None:
            db_module.enabled = module.enabled

        db_module.updated_by = current_user["sub"]
        db_module.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(db_module)
        logger.info(MESSAGES["MODULE_UPDATE_SUCCESS"].format(id=module_id))
        return {"status": "success", "message": MESSAGES["MODULE_UPDATE_SUCCESS"], "data": db_module}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["MODULE_UPDATE_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["MODULE_UPDATE_FAIL"])

# ---------------------------
# Delete Module (Admin only)
# ---------------------------
@router.delete("/modules/{module_id}", dependencies=[Depends(require_role("Admin"))])
def delete_module(module_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        db_module = db.query(Modules).filter(Modules.id == module_id).first()
        if not db_module:
            logger.warning(MESSAGES["MODULE_NOT_FOUND"])
            raise HTTPException(status_code=404, detail=MESSAGES["MODULE_NOT_FOUND"])

        db.delete(db_module)
        db.commit()
        logger.info(MESSAGES["MODULE_DELETE_SUCCESS"].format(id=module_id, user=current_user["sub"]))
        return {"status": "success", "message": MESSAGES["MODULE_DELETE_SUCCESS"], "id": module_id}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["MODULE_DELETE_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["MODULE_DELETE_FAIL"])

# ---------------------------
# Get modules assigned to a user
# ---------------------------
@router.get("/users/{user_id}/modules", dependencies=[Depends(get_current_user)])
def get_user_modules(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin" and int(current_user["id"]) != user_id:
        logger.warning(MESSAGES["UNAUTHORIZED_ACCESS"])
        raise HTTPException(status_code=403, detail=MESSAGES["UNAUTHORIZED_ACCESS"])

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(MESSAGES["USER_NOT_FOUND"])
        raise HTTPException(status_code=404, detail=MESSAGES["USER_NOT_FOUND"])

    modules = (
        db.query(Modules)
        .join(UserModules, UserModules.module_id == Modules.id)
        .filter(UserModules.user_id == user_id)
        .all()
    )
    logger.info(MESSAGES["USER_MODULE_FETCH_SUCCESS"].format(user_id=user_id))
    return {"status": "success", "message": MESSAGES["USER_MODULE_FETCH_SUCCESS"], "data": modules}

# ---------------------------
# Grant module access to a user
# ---------------------------
@router.post("/users/{user_id}/modules", dependencies=[Depends(require_role("Admin"))])
def add_user_module(user_id: int, payload: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        module_id = payload.get("module_id")
        if not module_id:
            logger.warning(MESSAGES["MODULE_ID_REQUIRED"])
            raise HTTPException(status_code=400, detail=MESSAGES["MODULE_ID_REQUIRED"])

        existing = db.query(UserModules).filter(UserModules.user_id == user_id, UserModules.module_id == module_id).first()
        if existing:
            logger.warning(MESSAGES["USER_MODULE_EXISTS"])
            raise HTTPException(status_code=400, detail=MESSAGES["USER_MODULE_EXISTS"])

        new_access = UserModules(
            user_id=user_id,
            module_id=module_id,
            created_at=datetime.utcnow()
        )
        db.add(new_access)
        db.commit()
        db.refresh(new_access)
        logger.info(MESSAGES["USER_MODULE_ADD_SUCCESS"].format(user_id=user_id, module_id=module_id))
        return {"status": "success", "message": MESSAGES["USER_MODULE_ADD_SUCCESS"], "data": {"user_id": user_id, "module_id": module_id}}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["USER_MODULE_ADD_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["USER_MODULE_ADD_FAIL"])

# ---------------------------
# Revoke module access from a user
# ---------------------------
@router.delete("/users/{user_id}/modules/{module_id}", dependencies=[Depends(require_role("Admin"))])
def delete_user_module(user_id: int, module_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        access = db.query(UserModules).filter(UserModules.user_id == user_id, UserModules.module_id == module_id).first()
        if not access:
            logger.warning(MESSAGES["USER_MODULE_NOT_FOUND"])
            raise HTTPException(status_code=404, detail=MESSAGES["USER_MODULE_NOT_FOUND"])

        db.delete(access)
        db.commit()
        logger.info(MESSAGES["USER_MODULE_DELETE_SUCCESS"].format(user_id=user_id, module_id=module_id))
        return {"status": "success", "message": MESSAGES["USER_MODULE_DELETE_SUCCESS"], "data": {"user_id": user_id, "module_id": module_id}}
    except Exception as e:
        db.rollback()
        logger.exception(MESSAGES["USER_MODULE_DELETE_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["USER_MODULE_DELETE_FAIL"])
