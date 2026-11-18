"""
main.py

The worker process. Small, but three things here are deliberate.

**The device is resolved at startup, not on the first frame.**  Model load and
CUDA initialisation take seconds. Doing that inside the first request makes a
healthy system look broken -- the first camera to start appears to hang -- and it
hides the one diagnostic that matters most: whether this machine will run on GPU
or has silently fallen back to CPU. Resolving it during startup means the answer
is in the log before any camera exists, and ``/unattended-object/health`` can
report it immediately.

**Configuration is logged once.**  Nearly every "it behaves differently on this
machine" question is an environment variable someone set months ago. One
resolved-settings line at boot answers it without a debugging session.

**Shutdown joins the camera threads.**  Without it, ``uvicorn`` exits while
acquisition threads still hold capture handles, which on some drivers leaves the
device unusable until the OS cleans up.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.logging import configure, get_logger
from backend.core.runtime import get_profile
from backend.routes import routes,UBcamera


from backend.services import pipeline_runner

log = get_logger("main")


def _origins() -> list:
    """Allowed browser origins.

    Defaults to the dev server but is overridable, because hardcoding
    ``localhost:3000`` means every non-local deployment fails CORS with a message
    that points at the browser rather than at this line.
    """
    raw = os.environ.get("UOD_CORS_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure()
    profile = get_profile()
    log.info("unattended-object worker starting on %s", profile.device)
    log.debug(settings.describe())
    if not profile.is_cuda:
        # Not an error -- CPU is a supported mode -- but it is the single most
        # likely explanation for a deployment that feels slow, so it is said
        # plainly at boot rather than left to be inferred from frame rates.
        log.warning("running on CPU: %s", profile.reason)
    yield
    pipeline_runner.stop_all()
    log.info("unattended-object worker stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Unattended Object Detection Worker",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # The frame sequence number is how a client keeps boxes and pixels
        # together; a browser cannot read it unless it is exposed here.
        expose_headers=["X-Frame-Seq"],
    )
    app.include_router(routes.router)    
    app.include_router(UBcamera.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    import sys
    is_frozen = getattr(sys, "frozen", False)
    run_app = app if is_frozen else "backend.main:app"
    
    uvicorn.run(
        run_app,
        host=os.environ.get("UOD_HOST", "0.0.0.0"),
        port=int(os.environ.get("UOD_PORT", "8002")),
        reload=not is_frozen,
    )
