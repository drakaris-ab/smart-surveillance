# app/services/speaker_service.py
"""
IP Speaker/Hooter Service
Handles communication with IP-based speaker/hooter devices for alarm alerts
"""

import requests
import threading
import time
from datetime import datetime
from backend.config.logging_config import logger     # ✅ central logging
from backend.config.messages import MESSAGES         # ✅ central messages


class SpeakerService:
    """
    Service to control IP speaker/hooter devices
    Manages connection, alarm triggering, and stopping
    """

    def __init__(self, config):
        self.config = config
        speaker_cfg = config.get("ipSpeaker", {})

        self.enabled = speaker_cfg.get("enabled", False)
        self.speaker_ip = speaker_cfg.get("ip", "")
        self.speaker_port = speaker_cfg.get("port", "")
        self.protocol = speaker_cfg.get("protocol", "http")
        self.base_url = f"http://{self.speaker_ip}:{self.speaker_port}" if self.speaker_ip and self.speaker_port else ""
        self.trigger_endpoint = speaker_cfg.get("endpoints", {}).get("trigger", "")
        self.stop_endpoint = speaker_cfg.get("endpoints", {}).get("stop", "")
        self.timeout = speaker_cfg.get("timeout", 5)
        self.duration = speaker_cfg.get("duration", 15)

        self.hooter_active = False
        self.hooter_lock = threading.Lock()
        self.hooter_stop_thread = None

        logger.info(MESSAGES["SPEAKER_INIT"])

    def is_configured(self) -> bool:
        if not self.speaker_ip:
            logger.warning(MESSAGES["SPEAKER_IP_NOT_CONFIGURED"])
            return False
        if not self.speaker_port:
            logger.warning(MESSAGES["SPEAKER_PORT_NOT_CONFIGURED"])
            return False
        if not self.trigger_endpoint:
            logger.warning(MESSAGES["SPEAKER_TRIGGER_ENDPOINT_NOT_CONFIGURED"])
            return False
        return True

    def is_connected(self) -> bool:
        if not self.enabled:
            logger.info(MESSAGES["SPEAKER_DISABLED"])
            return False
        if not self.is_configured():
            return False

        try:
            test_url = f"{self.base_url}/status"
            response = requests.get(test_url, timeout=self.timeout)
            if response.status_code in [200, 201]:
                logger.info(MESSAGES["SPEAKER_CONNECTED"].format(ip=self.speaker_ip, port=self.speaker_port))
                return True
            else:
                logger.warning(MESSAGES["SPEAKER_STATUS_FAILED"].format(code=response.status_code))
                return False
        except requests.exceptions.ConnectionError:
            logger.error(MESSAGES["SPEAKER_CONNECTION_ERROR"].format(url=self.base_url))
            return False
        except requests.exceptions.Timeout:
            logger.error(MESSAGES["SPEAKER_TIMEOUT"].format(url=self.base_url))
            return False
        except Exception as e:
            logger.exception(MESSAGES["SPEAKER_UNEXPECTED_ERROR"], exc_info=e)
            return False

    def trigger_hooter(self, duration=None):
        if duration is not None:
            self.duration = duration
        if not self.enabled or not self.is_configured():
            logger.warning(MESSAGES["SPEAKER_TRIGGER_FAILED"])
            return

        with self.hooter_lock:
            if self.hooter_active:
                logger.info(MESSAGES["HOOTER_ALREADY_ACTIVE"])
                return
            self.hooter_active = True

        try:
            trigger_url = f"{self.base_url}{self.trigger_endpoint}"
            logger.info(MESSAGES["HOOTER_TRIGGER"].format(url=trigger_url, time=datetime.now()))
            response = requests.get(trigger_url, timeout=self.timeout)
            if response.status_code in [200, 201]:
                logger.info(MESSAGES["HOOTER_TRIGGER_SUCCESS"])
            else:
                logger.warning(MESSAGES["HOOTER_TRIGGER_FAILED"].format(code=response.status_code, text=response.text))
            self._schedule_hooter_stop()
        except requests.exceptions.ConnectionError:
            logger.error(MESSAGES["HOOTER_CONNECTION_ERROR"].format(url=self.base_url))
            with self.hooter_lock:
                self.hooter_active = False
        except requests.exceptions.Timeout:
            logger.error(MESSAGES["HOOTER_TIMEOUT"])
            with self.hooter_lock:
                self.hooter_active = False
        except Exception as e:
            logger.exception(MESSAGES["HOOTER_UNEXPECTED_ERROR"], exc_info=e)
            with self.hooter_lock:
                self.hooter_active = False

    def stop_hooter(self):
        if not self.enabled or not self.is_configured():
            return

        with self.hooter_lock:
            if not self.hooter_active:
                return
            self.hooter_active = False

        try:
            stop_url = f"{self.base_url}{self.stop_endpoint}"
            logger.info(MESSAGES["HOOTER_STOP"].format(url=stop_url, time=datetime.now()))
            response = requests.get(stop_url, timeout=self.timeout)
            if response.status_code in [200, 201]:
                logger.info(MESSAGES["HOOTER_STOP_SUCCESS"])
            else:
                logger.warning(MESSAGES["HOOTER_STOP_FAILED"].format(code=response.status_code, text=response.text))
        except requests.exceptions.ConnectionError:
            logger.error(MESSAGES["HOOTER_CONNECTION_ERROR"].format(url=self.base_url))
        except requests.exceptions.Timeout:
            logger.error(MESSAGES["HOOTER_TIMEOUT"])
        except Exception as e:
            logger.exception(MESSAGES["HOOTER_UNEXPECTED_ERROR"], exc_info=e)

    def _schedule_hooter_stop(self):
        def auto_stop():
            time.sleep(self.duration)
            self.stop_hooter()

        self.hooter_stop_thread = threading.Thread(target=auto_stop, daemon=True)
        self.hooter_stop_thread.start()
        logger.info(MESSAGES["HOOTER_AUTO_STOP"].format(duration=self.duration))

    def manual_stop(self):
        self.stop_hooter()


# Global instance
speaker_service = None
