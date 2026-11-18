 
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config.settings import settings
from backend.config.logging_config import logger

SQLALCHEMY_DATABASE_URL = settings.DB_URL

# Handle SQLite vs Postgres differently
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
        logger.error("Database session error: %s", str(e))
        raise
    finally:
        db.close()

# ---------------------------
# SQLAlchemy Event Logging
# ---------------------------
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.debug("Database connection established: %s", SQLALCHEMY_DATABASE_URL)

@event.listens_for(engine, "close")
def close(dbapi_connection, connection_record):
    logger.debug("Database connection closed")

@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("Database connection checked out")

@event.listens_for(engine, "checkin")
def checkin(dbapi_connection, connection_record):
    logger.debug("Database connection returned to pool")
