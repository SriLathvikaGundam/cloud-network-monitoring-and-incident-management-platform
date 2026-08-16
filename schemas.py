from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ---------- DEVICE SCHEMAS ----------

class DeviceCreate(BaseModel):
    name: str
    hostname: str
    device_type: Optional[str] = None
    is_active: bool = True


class DeviceResponse(BaseModel):
    id: int
    name: str
    hostname: str
    device_type: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# ---------- MONITORING LOG SCHEMAS ----------

class MonitoringLogResponse(BaseModel):
    id: int
    device_id: int
    status: str
    response_time_ms: Optional[float] = None
    checked_at: datetime

    class Config:
        from_attributes = True


# ---------- INCIDENT SCHEMAS ----------

class IncidentCreate(BaseModel):
    device_id: int
    severity: str = "medium"
    description: Optional[str] = None


class IncidentResponse(BaseModel):
    id: int
    device_id: int
    severity: str
    status: str
    description: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IncidentStatusUpdate(BaseModel):
    status: str