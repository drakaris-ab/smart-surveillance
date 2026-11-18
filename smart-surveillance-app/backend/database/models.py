from sqlalchemy import Column, Float, Integer, String, Text, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

# -------------------------
# User Model
# -------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(String(20), default="Monitor")

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    audit_logs = relationship("AuditLogs", back_populates="user")
    user_modules = relationship("UserModules", back_populates="user", cascade="all, delete-orphan")
    snapshots = relationship("Snapshot", back_populates="owner", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="owner", cascade="all, delete-orphan")


# -------------------------
# Camera Model
# -------------------------
class Camera(Base):
    __tablename__ = "cameras"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    rtsp_url = Column(Text, nullable=False)
    location = Column(String(100), nullable=True)
    is_assigned= Column(Boolean, default=False)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    zones = relationship("Zone", back_populates="camera")
    alerts = relationship("Alert", back_populates="camera")
    event_logs = relationship("EventLogs", back_populates="camera")


# -------------------------
# Zone Model
# -------------------------
class Zone(Base):
    __tablename__ = "zones"
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    polygon_coords = Column(Text, nullable=False)
    sensitivity = Column(String(20), nullable=True)
    snapshot_file = Column(String, nullable=True)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    camera = relationship("Camera", back_populates="zones")
    alerts = relationship("Alert", back_populates="zone")
    notifications = relationship("Notifications", backref="zone")


BoundaryZone = Zone


# -------------------------
# Alert Model
# -------------------------
class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    event_type = Column(String(50), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    image = Column(Text)
    alert_type = Column(String(50), default="zone", index=True)  # "zone" or "unidentified_object"

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    camera = relationship("Camera", back_populates="alerts")
    zone = relationship("Zone", back_populates="alerts")


# -------------------------
# Notifications Model
# -------------------------
class Notifications(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String(50))
    message = Column(Text)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# -------------------------
# NotificationRecipients Model
# -------------------------
class NotificationRecipients(Base):
    __tablename__ = "notification_recipients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    channel = Column(String(50), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# -------------------------
# AuditLogs Model
# -------------------------
class AuditLogs(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100))
    target = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")


# -------------------------
# EventLogs Model
# -------------------------
class EventLogs(Base):
    __tablename__ = "event_logs"
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    event_type = Column(String(100))
    details = Column(Text, nullable=True)
    image = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    camera = relationship("Camera", back_populates="event_logs")


# -------------------------
# Modules Model
# -------------------------
class Modules(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    enabled = Column(Boolean, default=True)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_modules = relationship("UserModules", back_populates="module", cascade="all, delete-orphan")


# -------------------------
# UserModules Model
# -------------------------
class UserModules(Base):
    __tablename__ = "user_modules"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="user_modules")
    module = relationship("Modules", back_populates="user_modules")


# -------------------------
# Configurations Model
# -------------------------
class Configurations(Base):
    __tablename__ = "configurations"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserCameraMapping(Base):
    __tablename__ = "user_camera_mapping"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="camera_mapping")
    camera = relationship("Camera", backref="user_mapping")

# -------------------------
# Snapshot Model
# -------------------------
class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    owner_id = Column(Integer, ForeignKey("users.id"))
    file_path = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="snapshots")


# -------------------------
# ActivityLog Model
# -------------------------
class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False)
    status = Column(String(50), default="-")
    timestamp = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, nullable=True)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="activity_logs")


# -------------------------
# AlertMuteSchedule Model
# -------------------------
class AlertMuteSchedule(Base):
    __tablename__ = "alert_mute_schedules"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=True)  # e.g., "2023-10-25"
    start_date = Column(String, nullable=True) # e.g., "2023-10-25"
    end_date = Column(String, nullable=True) # e.g., "2023-10-31"
    start_time = Column(String, nullable=True)  # e.g., "14:30"
    end_time = Column(String, nullable=True)  # e.g., "16:30"
    days = Column(String, nullable=True)  # e.g., "Mon,Tue,Wed"
    is_active = Column(Boolean, default=True)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# -------------------------
# AppConfigModel
# -------------------------
"""
class AppConfigModel(Base):
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, index=True)
    alert_sound_path = Column(String(255), nullable=False, default="assets/sounds/alert.wav")
    alert_output_mode = Column(String(20), nullable=False, default="system")
    alert_duration_seconds = Column(Integer, nullable=False, default=15)
    whatsapp_phone = Column(String(32), nullable=True, default="")
    sms_phone = Column(String(32), nullable=True, default="")
    archive_days = Column(Integer, nullable=False, default=30)
    confidence_threshold = Column(Float, nullable=False, default=0.5)
    frame_size = Column(Integer, nullable=False, default=640)
    image_size = Column(Integer, nullable=False, default=416)
    focal_length = Column(Float, nullable=False, default=24.0)
    inference_size = Column(Integer, nullable=False, default=416)

    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
"""