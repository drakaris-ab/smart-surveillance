import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Settings:
    ENV = os.getenv("ENV", "development")

    # ✅ Resolve DB path outside root
    def _resolve_db_url(self):
        import sys, os
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            db_path = os.path.abspath(os.path.join(exe_dir, "..", "SmartSurveillance", "surveillance.db"))
        else:
            base_path = os.path.abspath(".")
            db_path = os.path.abspath(os.path.join(base_path, "..", "smart-surveillance-app", "surveillance.db"))
        return f"sqlite:///{db_path}"

    DB_URL = os.getenv("DB_URL", None) or _resolve_db_url(None)

    FRONTEND_URLS = os.getenv("FRONTEND_URLS", "*").split(",")
    BASE_API_URL = os.getenv("BASE_API_URL", "http://127.0.0.1:8000")

    # Logging configs
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
    LOG_FORMAT = os.getenv("LOG_FORMAT", "plain")
    LOG_FILE = os.getenv("LOG_FILE", os.path.join("logs", "face_api.log"))
    ENABLE_FILE_LOG = os.getenv("ENABLE_FILE_LOG", "true").lower() == "true"

    def __init__(self):
        # Ensure logs directory exists
        log_dir = os.path.dirname(self.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

settings = Settings()
