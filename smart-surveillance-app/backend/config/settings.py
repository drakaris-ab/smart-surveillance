import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env
load_dotenv()

class Settings:
    def _resolve_db_url(self):
        import sys, os
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            db_path = os.path.join(exe_dir, "surveillance.db")
        else:
            db_path = os.path.abspath("surveillance.db")
        return f"sqlite:///{db_path}"

    DB_URL = os.getenv("DATABASE_URL", None) or _resolve_db_url(None)
    # Auth
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

    # Frontend
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Logging configs
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    ENABLE_LOGS = os.getenv("ENABLE_LOGS", "true").lower() == "true"
    LOG_FORMAT = os.getenv("LOG_FORMAT", "plain")
    LOG_FILE = os.getenv("LOG_FILE", os.path.join("logs", "surveillance.log"))
    ENABLE_FILE_LOG = os.getenv("ENABLE_FILE_LOG", "true").lower() == "true"

    # Rotation configs
    MAX_LOG_SIZE = int(os.getenv("MAX_LOG_SIZE", 5 * 1024 * 1024))  # default 5 MB
    BACKUP_COUNT = int(os.getenv("BACKUP_COUNT", 5))  # default 5 rotated files

    def __init__(self):
        # Validate log level
        if self.LOG_LEVEL not in logging._nameToLevel:
            self.LOG_LEVEL = "INFO"

        # Ensure logs directory exists
        log_dir = os.path.dirname(self.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

settings = Settings()
