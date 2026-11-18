import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from backend.config.logging_config import logger
from backend.config.messages import MESSAGES

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()

DEFAULT_CONFIG = {
    "logging": {
        "level": os.getenv("LOG_LEVEL", "INFO").upper(),
        "labels": {},
        "output": os.getenv("LOG_OUTPUT", "console").lower(),
    },
    "alertSoundPath": os.getenv("ALERT_SOUND_PATH", "assets/sounds/alert.wav"),
    "backendBase": os.getenv("BACKEND_BASE", "http://localhost:8000"),
    "twilioSid": os.getenv("TWILIO_SID", ""),
    "twilioAuth": os.getenv("TWILIO_AUTH", ""),
    "fromWhatsapp": os.getenv("FROM_WHATSAPP", ""),
}


def resolve_config_path() -> Path:
    """Resolve path to config.json (used only for packaged executables)."""
    try:
        if getattr(sys, "frozen", False):  # running from PyInstaller exe
            base_path = Path(sys.executable).parent
            config_file = base_path / "app" / "config.json"
        else:
            base_path = Path(__file__).resolve().parent.parent
            config_file = base_path / "config.json"
        return config_file
    except Exception as e:
        logger.exception(MESSAGES["CONFIG_PATH_FAILED"], exc_info=e)
        return Path("config.json")


CONFIG_PATH = resolve_config_path()


def load_config() -> dict:
    """Load config.json if present, merge with defaults + env vars."""
    try:
        if not CONFIG_PATH.exists():
            logger.warning(MESSAGES["CONFIG_FILE_NOT_FOUND"].format(path=CONFIG_PATH))
            return DEFAULT_CONFIG.copy()

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            file_config = json.load(f)
            merged = {**DEFAULT_CONFIG, **file_config}
            logger.info(MESSAGES["CONFIG_LOADED"].format(path=CONFIG_PATH))
            return merged
    except Exception as e:
        logger.exception(MESSAGES["CONFIG_LOAD_FAILED"], exc_info=e)
        return DEFAULT_CONFIG.copy()


config = load_config()


def get_config(key: str, default=None):
    """Get a single config value."""
    return config.get(key, default)


def get_logging_config() -> dict:
    """Get logging configuration block."""
    return config.get("logging", {})
