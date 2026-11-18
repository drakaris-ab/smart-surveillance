# app/routers/config.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import os, shutil

#from backend.database.schemas import AppConfig
from backend.services.config_service import get_config, ConfigSchema
from backend.database import SessionLocal
from backend.database.models import Configurations
from backend.config.logging_config import logger
from backend.config.router_message import MESSAGES

router = APIRouter(prefix="/config", tags=["Config"])

# ---------------------------
# DB Dependency#
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.put("/update/{key}")
def update_config(key: str, value: str, updated_by: str = "frontend"):
    # Ensure key is valid (exists in ConfigSchema)
    if key not in ConfigSchema.__fields__:
        raise HTTPException(status_code=400, detail=f"Invalid configuration key: {key}")

    db = SessionLocal()
    try:
        config = db.query(Configurations).filter(Configurations.key == key).first()
        if not config:
            raise HTTPException(status_code=404, detail="Configuration key not found")

        config.value = value
        config.updated_by = updated_by
        db.commit()
        db.refresh(config)
        return {"message": f"{key} updated", "config": {"key": config.key, "value": config.value}}
    finally:
        db.close()


# ---------------------------
# Upload Alert Sound
# ---------------------------
@router.post("/upload-sound", response_model=ConfigSchema)
def upload_sound(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        if not file.filename.lower().endswith((".wav", ".mp3", ".ogg")):
            logger.warning(MESSAGES["INVALID_FILE_TYPE"].format(filename=file.filename))
            raise HTTPException(status_code=400, detail=MESSAGES["INVALID_FILE_TYPE"])

        sound_dir = os.path.join("assets", "sounds")
        os.makedirs(sound_dir, exist_ok=True)
        dest = os.path.join(sound_dir, file.filename)

        with open(dest, "wb") as out:
            shutil.copyfileobj(file.file, out)

        dest = dest.replace("\\", "/") # Normalize path for DB
        config_entry = db.query(Configurations).filter(Configurations.key == "alertSoundPath").first()
        if config_entry:
            config_entry.value = dest
            config_entry.updated_by = "upload_api"
            db.commit()
            db.refresh(config_entry)

        logger.info(MESSAGES["SOUND_UPLOAD_SUCCESS"].format(path=dest))
        return get_config(db)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(MESSAGES["SOUND_UPLOAD_FAIL"].format(error=str(e)))
        raise HTTPException(status_code=500, detail=MESSAGES["SOUND_UPLOAD_FAIL"])
@router.get("/all")
def list_configs(db: Session = Depends(get_db)):
    configs = db.query(Configurations).all()
    return [
        {
            "id": c.id,
            "key": c.key,
            "value": c.value,
            "description": c.description,
            "updated_by": c.updated_by,
            "updated_at": c.updated_at,
        }
        for c in configs
    ]
