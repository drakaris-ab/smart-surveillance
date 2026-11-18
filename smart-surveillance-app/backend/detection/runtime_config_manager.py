# runtime_config_manager.py
import time
from backend.database import SessionLocal
from backend.services.config_service import get_config
from backend.config.logging_config import logger
from backend.config.messages import MESSAGES

class RuntimeConfigManager:
    def __init__(self):
        self._last_refresh = 0.0
        self._last_signature = None
        # Default values
        self.conf_threshold = 0.5
        self.frame_size = 640
        self.image_size = 416
        self.focal_length = 24.0
        self.inference_size = 416

    def refresh(self):
        now = time.time()
        if now - self._last_refresh < 5.0 and self._last_signature is not None:
            return

        try:
            db = SessionLocal()
            try:
                cfg = get_config(db)
            finally:
                db.close()
        except Exception as exc:
            logger.warning(MESSAGES["config_refresh_failed"].format(error=str(exc)))
            return

        if cfg is None:
            logger.warning(MESSAGES["config_missing"])
            return

        try:
            conf = getattr(cfg, "confidenceThreshold", None) or (cfg.get("confidenceThreshold") if isinstance(cfg, dict) else self.conf_threshold)
            frame_size = getattr(cfg, "frameSize", None) or (cfg.get("frameSize") if isinstance(cfg, dict) else self.frame_size)
            image_size = getattr(cfg, "imageSize", None) or (cfg.get("imageSize") if isinstance(cfg, dict) else self.image_size)
            focal_length = getattr(cfg, "focalLength", None) or (cfg.get("focalLength") if isinstance(cfg, dict) else self.focal_length)
            inference_size = getattr(cfg, "inferenceSize", None) or (cfg.get("inferenceSize") if isinstance(cfg, dict) else self.inference_size)

            signature = {
                "confidenceThreshold": conf,
                "frameSize": frame_size,
                "imageSize": image_size,
                "focalLength": focal_length,
                "inferenceSize": inference_size,
            }

            if signature == self._last_signature:
                self._last_refresh = now
                return

            # Apply new values
            self.conf_threshold = float(conf)
            self.frame_size = int(frame_size)
            self.image_size = int(image_size)
            self.focal_length = float(focal_length)
            self.inference_size = int(inference_size)
            self._last_refresh = now
            self._last_signature = signature

            logger.info(MESSAGES["config_applied"].format(
                conf=self.conf_threshold,
                frame_size=self.frame_size,
                image_size=self.image_size,
                focal_length=self.focal_length,
                inference_size=self.inference_size
            ))
        except Exception as e:
            logger.exception(MESSAGES["config_apply_failed"].format(error=str(e)))
