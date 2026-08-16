from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    hostname = Column(String, nullable=False)      # e.g. IP address or domain
    device_type = Column(String, nullable=True)     # server, router, website, etc.
    is_active = Column(Boolean, default=True)        # whether monitoring is enabled for this device

    logs = relationship("MonitoringLog", back_populates="device")
    incidents = relationship("Incident", back_populates="device")


class MonitoringLog(Base):
    __tablename__ = "monitoring_logs"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    status = Column(String, nullable=False)          # "up" or "down"
    response_time_ms = Column(Float, nullable=True)   # null if device was down
    checked_at = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="logs")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    severity = Column(String, nullable=False, default="medium")   # low, medium, high, critical
    status = Column(String, nullable=False, default="open")        # open, investigating, resolved
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    device = relationship("Device", back_populates="incidents")