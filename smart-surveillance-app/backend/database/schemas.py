from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union, Literal
from datetime import datetime

# -------------------------
# User Schemas
# -------------------------
class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# Camera Schemas
# -------------------------
class CameraCreate(BaseModel):
    name: str
    location: Optional[str] = None
    stream_url: str
    description: Optional[str] = None

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    stream_url: Optional[str] = None
    description: Optional[str] = None

class CameraOut(BaseModel):
    id: int
    name: str
    location: Optional[str] = None
    stream_url: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# Zone Schemas
# -------------------------
class ZoneCreate(BaseModel):
    camera_id: int
    polygon_coords: str
    sensitivity: Optional[str] = None
    snapshot_file: Optional[str] = None

class ZoneUpdate(BaseModel):
    polygon_coords: Optional[str] = None
    sensitivity: Optional[str] = None
    snapshot_file: Optional[str] = None

class ZoneOut(BaseModel):
    id: int
    camera_id: int
    polygon_coords: str
    sensitivity: Optional[str] = None
    snapshot_file: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# Config Schemas
# -------------------------
#class ConfigSchema(BaseModel):
    #alertSoundPath: str = Field(default="app/alert.wav")
    #alertOutputMode: Literal["system", "hooter"] = Field(default="system")
    #alertDurationSeconds: int = Field(default=15, ge=1)
    #whatsappPhone: str = Field(default="")
    #smsPhone: str = Field(default="")
    #archiveDays: int = Field(default=30, ge=1)
    #confidenceThreshold: float = Field(default=0.5, ge=0.0, le=1.0)
    #frameSize: int = Field(default=640, ge=1)
    #imageSize: int = Field(default=416, ge=1)
    #focalLength: float = Field(default=24.0, ge=0.0)
    #inferenceSize: int = Field(default=416, ge=1)


# -------------------------
# Alert Schemas
# -------------------------
class AlertBase(BaseModel):
    camera_id: int
    zone_id: Optional[int] = None
    message: Optional[str] = None
    snapshot_path: Optional[str] = None
    alert_type: Optional[str] = "zone"

class AlertCreate(AlertBase):
    pass

class AlertOut(BaseModel):
    id: int
    camera_id: int
    zone_id: Optional[int] = None
    event_type: Optional[str] = None
    image: Optional[str] = None
    timestamp: datetime
    alert_type: Optional[str] = "zone"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# Notifications Schemas
# -------------------------
class NotificationCreate(BaseModel):
    channel: str
    message: str
    zone_id: Optional[int] = None

class NotificationOut(BaseModel):
    id: int
    channel: str
    message: str
    zone_id: Optional[int] = None
    timestamp: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# NotificationRecipients Schemas
# -------------------------
class NotificationRecipientCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    channel: str
    zone_id: Optional[int] = None
    camera_id: Optional[int] = None

class NotificationRecipientOut(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    channel: str
    zone_id: Optional[int] = None
    camera_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# AuditLogs Schemas
# -------------------------
class AuditLogOut(BaseModel):
    id: int
    user_id: int
    action: str
    target: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# EventLogs Schemas
# -------------------------
class EventLogOut(BaseModel):
    id: int
    camera_id: int
    event_type: str
    details: Optional[str] = None
    image: Optional[str] = None
    timestamp: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# Modules Schemas
# -------------------------
class ModuleCreate(BaseModel):
    name: str
    enabled: bool = True

class ModuleOut(BaseModel):
    id: int
    name: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# UserModules Schemas
# -------------------------
class UserModuleCreate(BaseModel):
    user_id: int
    module_id: int

class UserModuleOut(BaseModel):
    id: int
    user_id: int
    module_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# Configurations Schemas
# -------------------------
class ConfigurationCreate(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None

class ConfigurationOut(BaseModel):
    id: int
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# Snapshot Schemas
# -------------------------
class SnapshotOut(BaseModel):
    id: int
    camera_id: int
    owner_id: int
    file_path: str
    timestamp: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# ActivityLog Schemas
# -------------------------
class ActivityLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    description: str
    status: str
    timestamp: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# AlertMuteSchedule Schemas
# -------------------------
class AlertMuteScheduleCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    days: Optional[str] = None
    is_active: bool = True

class AlertMuteScheduleOut(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime
    days: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
