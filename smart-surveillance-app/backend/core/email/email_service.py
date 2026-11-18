# app/services/email_service.py

import smtplib
from email.mime.text import MIMEText
from backend.config.logging_config import logger     # ✅ central logging
from backend.config.messages import MESSAGES         # ✅ central messages


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send an email using Gmail SMTP with App Password.
    Returns True if sent successfully, False otherwise.
    """
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = "aicctvapp@gmail.com"   # sender email
        msg["To"] = to_email                  # recipient email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            # ⚠️ Replace with environment variable or secure secret manager
            server.login("aicctvapp@gmail.com", "your-app-password")
            server.send_message(msg)

        logger.info(MESSAGES["EMAIL_SENT"].format(email=to_email))
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(MESSAGES["EMAIL_AUTH_FAILED"], exc_info=e)
        return False
    except smtplib.SMTPException as e:
        logger.error(MESSAGES["EMAIL_SEND_FAILED"].format(email=to_email), exc_info=e)
        return False
    except Exception as e:
        logger.exception(MESSAGES["EMAIL_UNEXPECTED_ERROR"], exc_info=e)
        return False
