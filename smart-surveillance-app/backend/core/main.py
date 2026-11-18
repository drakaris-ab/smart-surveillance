from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sys
from pathlib import Path
from sqlalchemy.orm import Session
import threading
import time
import logging
import os
from contextlib import asynccontextmanager
from backend.services.config_service import get_config

from backend.routers import (
    alerts_routes,
    auth_routes,
    cameras_routes,
    config_routes,
    users_routes,
    zones_routes,
    modules_routes,
    #camera_mapping_routes,
    alert_mute_schedule,
    activity_log,
    archive,
    detection, # Used in dash baord and camera view from camera view it is taking snapshots 
    streams, # This is used in zone
    #camera_stream, # Looks like not req
   # webrtc_routes,
   #camera_worker_routes,
)
from backend.config.logging_config import logger
from backend.database.database import SessionLocal, Base, engine
from backend.database.models import User
from backend.auth.jwt_handler import get_password_hash
from backend.config.messages import MESSAGES
from backend.config.settings import settings
from backend.detection.yolo_detector import detector
from backend.services.unidentified_object_sync_service import start_sync_service, stop_sync_service

# ----------------------------
# Logging setup
# ----------------------------
log_dir = Path(os.getenv("LOCALAPPDATA", ".")) / "SmartSurveillance" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=log_dir / "app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/frame" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

# ----------------------------
# Paths (snapshots + frontend + config)
# ----------------------------
if getattr(sys, "frozen", False):
    exe_dir = Path(sys.executable).parent
    bundle_dir = Path(sys._MEIPASS)
    snapshots_dir = exe_dir / "snapshots"
    frontend_dir = bundle_dir / "frontend" / "build"
    config_dir = exe_dir / "app"
else:
    backend_root = Path(__file__).resolve().parent.parent
    snapshots_dir = backend_root / "snapshots"
    frontend_dir = backend_root / "frontend" / "build"
    config_dir = backend_root / "app"

snapshots_dir.mkdir(parents=True, exist_ok=True)

logger.info("Resolved frontend_dir path: %s", frontend_dir)

# ----------------------------
# Database init
# ----------------------------
Base.metadata.create_all(bind=engine)

def create_admin_user():
    db: Session = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            hashed_pw = get_password_hash("pass#")
            new_admin = User(username="admin", password=hashed_pw, role="Admin")
            db.add(new_admin)
            db.commit()
            db.refresh(new_admin)
            logger.info("Admin user created successfully with default password")
        else:
            logger.info("Admin user already exists")
    except Exception as e:
        logger.error("Error creating admin user: %s", str(e))
    finally:
        db.close()

def start_all_cameras():
    from backend.database.models import Camera
    db: Session = SessionLocal()
    try:
        # ✅ Global flag check
        cfg = get_config(db) 
        if not cfg.is_Camera_Detector:
            logger.info("Global detection disabled (is_Camera_Detector=False). Skipping auto-start.")
            return
        cameras_list = db.query(Camera).all()
        logger.info(f"Found {len(cameras_list)} camera(s). Starting automatic detection...")
        for cam in cameras_list:
            stream = cam.rtsp_url or 0
            if stream is not None:
                logger.info(f"[STARTING] Camera {cam.id} ({stream})")
                threading.Thread(
                    target=detector.start_detection,
                    args=(stream, cam.id),
                    daemon=True
                ).start()
                time.sleep(0.5)
            else:
                logger.info(f"[WARN] Camera ID {cam.id} has no valid stream URL.")
    except Exception as e:
        logger.error("Error starting cameras: %s", str(e))
    finally:
        db.close()

# ----------------------------
# Lifespan handler
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Smart Surveillance API starting...")
    create_admin_user()
    threading.Thread(target=start_all_cameras, daemon=True).start()
    # Start unidentified object alert sync service
    start_sync_service()
    logger.info("Smart Surveillance API started")
    yield
    logger.info("Smart Surveillance API stopped")
    try:
        detector.stop_all_detections()
    except Exception as e:
        logger.error(f"[WARN] Error during stop_all_detections: {e}")
    # Stop unidentified object alert sync service
    stop_sync_service()

# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI(title="Smart Surveillance System", lifespan=lifespan)

# Routers
app.include_router(auth_routes.router)
app.include_router(users_routes.router)
app.include_router(cameras_routes.router)
app.include_router(zones_routes.router) 
app.include_router(modules_routes.router) 
#app.include_router(camera_mapping_routes.router)
app.include_router(alerts_routes.router)
app.include_router(alert_mute_schedule.router)
app.include_router(activity_log.router)
app.include_router(archive.router)
app.include_router(config_routes.router)
app.include_router(detection.router)
app.include_router(streams.router)
#app.include_router(camera_stream.router)
#app.include_router(webrtc_routes.router)     # WebRTC streaming
#app.include_router(camera_worker_routes.router)


# Allow frontend React app to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount snapshots
app.mount("/snapshots", StaticFiles(directory=str(snapshots_dir)), name="snapshots")

# ----------------------------
# Serve config.json if present
# ----------------------------
if config_dir.exists():
    app.mount("/app", StaticFiles(directory=str(config_dir)), name="app")
else:
    logger.warning("Config directory not found at %s", config_dir)

# ----------------------------
# Serve React frontend
# ----------------------------
if frontend_dir.exists():
    # Serve /static/* from build/static
    if (frontend_dir / "static").exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir / "static")), name="static")

    # Serve root-level assets (logo.png, manifest.json, config.json, etc.)
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        index_file = frontend_dir / "index.html"
        logger.info("Checking frontend index file: %s (exists=%s, is_file=%s)",
                    index_file, index_file.exists(), index_file.is_file())
        if index_file.is_file():
            return FileResponse(index_file)
        logger.warning("Frontend index.html not found or not a file at %s", index_file)
        return {"error": "Frontend not found"}
else:
    logger.warning("Frontend directory not found at %s", frontend_dir)

# ----------------------------
# API root
# ----------------------------
@app.get("/api")
def root():
    try:
        return {"msg": "Welcome to Smart Surveillance API"}
    except Exception as e:
        logger.error("Error in root endpoint: %s", str(e))
        return {"msg": MESSAGES["SERVER_ERROR"]}

# ----------------------------
# Entry point for PyInstaller exe
# ----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
