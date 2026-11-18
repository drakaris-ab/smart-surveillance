import asyncio
import multiprocessing
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.settings import settings
from backend.config.logging_config import logger
from backend.database.database import Base, engine
from backend.database.models import FaceReUser
from backend.database.models import Camera

import backend.util.cache_events  # <-- important: registers event listeners
from backend.routers import face_routes, assign_camera, User_Camera_Assignments, configurations, alerts_routes
from backend.services.live_tracking_worker import run_live_tracking

# ---------------------------
# DB Migration / Table Creation
# ---------------------------
Base.metadata.create_all(bind=engine)
logger.info("Database tables ensured.")

# ---------------------------
# Worker Process Wrapper
# ---------------------------
def start_worker():
    """Run live tracking worker in its own process"""
    logger.info(">>>>>>>>>>>>>> Live tracking worker process starting======================================")
    try:
        run_live_tracking()
    except KeyboardInterrupt:
        logger.info("Live tracking worker stopped manually.")

# ---------------------------
# Lifespan Context Manager
# ---------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI starting up... launching live tracking worker process")
    worker_proc = multiprocessing.Process(target=start_worker, daemon=True)
    worker_proc.start()

    yield  # <-- app runs here

    logger.info("FastAPI shutting down. Terminating live tracking worker process")
    worker_proc.terminate()
    worker_proc.join()

# ---------------------------
# FastAPI App
# ---------------------------
app = FastAPI(title="Face Recognition API", lifespan=lifespan)

# ---------------------------
# CORS Middleware
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Routers
# ---------------------------
app.include_router(face_routes.router)
app.include_router(assign_camera.router)
app.include_router(User_Camera_Assignments.router)
app.include_router(configurations.router)
app.include_router(alerts_routes.router)   # ✅ new alerts API

# ---------------------------
# Health Check
# ---------------------------
@app.get("/health")
def health_check():
    logger.debug("Health check called.")
    return {"status": "ok", "service": "Face Recognition API"}

if __name__ == "__main__":
    multiprocessing.freeze_support()
    import uvicorn
    from backend.core import main   # import your module
    uvicorn.run(main.app, host="0.0.0.0", port=8001, reload=False)
