import random
from datetime import datetime
from sqlalchemy.orm import Session
import models


def check_device(db: Session, device: models.Device) -> models.MonitoringLog:
    """
    Simulates checking a single device's availability.
    In a real system, this would ping the device or make an HTTP request.
    Here, we simulate realistic behavior: devices are usually up,
    with occasional random failures and variable response times.
    """
    is_up = random.random() > 0.15   # ~85% chance the device is up

    if is_up:
        response_time = round(random.uniform(10, 300), 2)   # simulate 10-300ms
        status = "up"
    else:
        response_time = None
        status = "down"

    log = models.MonitoringLog(
        device_id=device.id,
        status=status,
        response_time_ms=response_time,
        checked_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # If the device is down, automatically create an incident
    if status == "down":
        create_incident_if_needed(db, device)

    return log


def create_incident_if_needed(db: Session, device: models.Device):
    """
    Creates a new incident for this device, but only if there isn't
    already an OPEN incident for it (avoids duplicate incidents from
    repeated failed checks).
    """
    existing = (
        db.query(models.Incident)
        .filter(models.Incident.device_id == device.id, models.Incident.status != "resolved")
        .first()
    )
    if existing:
        return existing   # already tracking this outage, don't duplicate

    incident = models.Incident(
        device_id=device.id,
        severity="high",
        status="open",
        description=f"{device.name} ({device.hostname}) is not responding.",
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident