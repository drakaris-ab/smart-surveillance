# backend/database/db.py

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config.settings import settings
from backend.config.logging_config import logger
from backend.config.messages import MESSAGES

SQLALCHEMY_DATABASE_URL = settings.DB_URL

# ---------------------------
# Engine Configuration
# ---------------------------
try:
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
            echo=False  # disable SQL echo in dev logs
        )
    else:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            echo=False
        )
    logger.info(MESSAGES["DB_ENGINE_INIT"].format(url=SQLALCHEMY_DATABASE_URL))
except Exception as e:
    logger.exception(MESSAGES["DB_ENGINE_INIT_FAILED"], exc_info=e)
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------------------
# DB Session Dependency
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(MESSAGES["DB_SESSION_ERROR"].format(error=str(e)))
        raise
    finally:
        db.close()
        logger.debug(MESSAGES["DB_SESSION_CLOSED"])

# ---------------------------
# SQLAlchemy Event Logging
# ---------------------------
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.debug(MESSAGES["DB_CONNECT"].format(url=SQLALCHEMY_DATABASE_URL))

@event.listens_for(engine, "close")
def close(dbapi_connection, connection_record):
    logger.debug(MESSAGES["DB_CLOSE"])

@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug(MESSAGES["DB_CHECKOUT"])

@event.listens_for(engine, "checkin")
def checkin(dbapi_connection, connection_record):
    logger.debug(MESSAGES["DB_CHECKIN"])
