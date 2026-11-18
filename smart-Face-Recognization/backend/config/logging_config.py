import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from backend.config.settings import settings

# --- Ensure logs directory exists ---
log_dir = os.path.dirname(settings.LOG_FILE)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("face_api")
logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

# Prevent duplicate handlers
if not logger.handlers:
    # Console handler
    ch = logging.StreamHandler()
    if settings.LOG_FORMAT == "json":
        try:
            import json_log_formatter
            formatter = json_log_formatter.JSONFormatter()
        except ImportError:
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    else:
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # --- Rotating file handler with timestamp ---
    if settings.ENABLE_FILE_LOG:
        class TimestampedRotatingFileHandler(RotatingFileHandler):
            def doRollover(self):
                if self.stream:
                    self.stream.close()
                    self.stream = None

                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                rollover_filename = f"{self.baseFilename}_{timestamp}.log"

                if os.path.exists(self.baseFilename):
                    os.rename(self.baseFilename, rollover_filename)

                # Enforce backup count
                log_files = sorted(
                    [f for f in os.listdir(log_dir) if f.startswith(os.path.basename(self.baseFilename))],
                    key=lambda f: os.path.getmtime(os.path.join(log_dir, f))
                )
                while len(log_files) > self.backupCount:
                    oldest = log_files.pop(0)
                    os.remove(os.path.join(log_dir, oldest))

                self.mode = "w"
                self.stream = self._open()

        fh = TimestampedRotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5              # keep 5 rotated files
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)
