from sqlalchemy import Column, Integer, String, Boolean, DateTime,ForeignKey,Text,JSON
from sqlalchemy.sql import func
from backend.database.database import Base
from sqlalchemy.orm import relationship
from datetime import datetime


class FaceReUser(Base):
    __tablename__ = "face_re_users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    aadhaar = Column(String, nullable=True)
    criminal_flag = Column(Boolean, default=False)
    embedding = Column(JSON, nullable=False)   # <-- store as JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


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

"""class FaceRecognitionCameraAssignment(Base):
    __tablename__ = "face_recognition_camera_assignments"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    camera_name = Column(String(255), nullable=False)
    location = Column(String(255))
    rtsp_url = Column(Text, nullable=False) 
    assigned_by = Column(String(255), nullable=False)
    updated_by = Column(String(255))
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())"""

class UserCameraAssignment(Base):
    __tablename__ = "user_camera_assignments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("face_re_users.id"))
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    assigned_at = Column(DateTime, default=datetime.utcnow)

    # ✅ New columns
    untagged = Column(Boolean, default=False)          # mark if camera is untagged
    created_by = Column(String, nullable=True)         # who created assignment
    updated_by = Column(String, nullable=True)         # who last updated assignment
    updated_at = Column(DateTime, nullable=True)       # when last updated

    user = relationship("FaceReUser", backref="camera_assignments")
    camera = relationship("Camera", backref="user_assignments")
class Configurations(Base):
    __tablename__ = "configurations"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)   # e.g. "snapshot_archive_path"
    value = Column(Text, nullable=True)                      # e.g. "/data/snapshots/"
    description = Column(Text, nullable=True)

    # Audit fields
    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
class AlertFace(Base):
    __tablename__ = "alert_face"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, nullable=False)
    message = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    consumed = Column(Boolean, default=False)  # ✅ queue flag
    created_at = Column(DateTime, default=datetime.utcnow)   # ✅ add this