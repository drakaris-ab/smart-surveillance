import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from backend.config.settings import settings

logger = logging.getLogger("surveillance_app")
log_level = logging._nameToLevel.get(settings.LOG_LEVEL, logging.INFO)
logger.setLevel(log_level)

# Clear duplicate handlers
if logger.hasHandlers():
    logger.handlers.clear()

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

if settings.ENABLE_FILE_LOG:
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    fh = RotatingFileHandler(settings.LOG_FILE,
                             maxBytes=settings.MAX_LOG_SIZE,
                             backupCount=settings.BACKUP_COUNT)
    fh.setLevel(log_level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler()
ch.setLevel(log_level)
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.info("Logger initialized. Writing to %s", settings.LOG_FILE)
