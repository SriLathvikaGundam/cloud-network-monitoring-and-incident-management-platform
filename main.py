from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
import models
import schemas
import monitoring

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Network Monitoring & Incident Management Platform")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ---------- DEVICE ENDPOINTS ----------

@app.post("/devices", response_model=schemas.DeviceResponse)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    new_device = models.Device(
        name=device.name,
        hostname=device.hostname,
        device_type=device.device_type,
        is_active=device.is_active,
    )
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return new_device


@app.get("/devices", response_model=list[schemas.DeviceResponse])
def get_devices(db: Session = Depends(get_db)):
    return db.query(models.Device).all()


@app.get("/devices/{device_id}", response_model=schemas.DeviceResponse)
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@app.put("/devices/{device_id}", response_model=schemas.DeviceResponse)
def update_device(device_id: int, updated: schemas.DeviceCreate, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.name = updated.name
    device.hostname = updated.hostname
    device.device_type = updated.device_type
    device.is_active = updated.is_active

    db.commit()
    db.refresh(device)
    return device


@app.delete("/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    db.delete(device)
    db.commit()
    return {"message": f"Device {device_id} deleted successfully"}


# ---------- MONITORING ENDPOINTS ----------

# Trigger a single simulated check for one device
@app.post("/devices/{device_id}/check", response_model=schemas.MonitoringLogResponse)
def check_device_now(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return monitoring.check_device(db, device)


# Trigger a check for ALL active devices at once
@app.post("/devices/check-all")
def check_all_devices(db: Session = Depends(get_db)):
    devices = db.query(models.Device).filter(models.Device.is_active == True).all()
    results = [monitoring.check_device(db, d) for d in devices]
    return {"checked": len(results), "results": [schemas.MonitoringLogResponse.model_validate(r) for r in results]}


# Get monitoring history for a device
@app.get("/devices/{device_id}/logs", response_model=list[schemas.MonitoringLogResponse])
def get_device_logs(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return db.query(models.MonitoringLog).filter(models.MonitoringLog.device_id == device_id).order_by(models.MonitoringLog.checked_at.desc()).all()

# ---------- INCIDENT ENDPOINTS ----------

@app.get("/incidents", response_model=list[schemas.IncidentResponse])
def get_incidents(db: Session = Depends(get_db)):
    return db.query(models.Incident).order_by(models.Incident.created_at.desc()).all()


@app.get("/incidents/{incident_id}", response_model=schemas.IncidentResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(models.Incident).filter(models.Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.put("/incidents/{incident_id}/status", response_model=schemas.IncidentResponse)
def update_incident_status(incident_id: int, update: schemas.IncidentStatusUpdate, db: Session = Depends(get_db)):
    incident = db.query(models.Incident).filter(models.Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident.status = update.status

    # If marking as resolved, record when
    if update.status == "resolved":
        from datetime import datetime
        incident.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(incident)
    return incident


@app.delete("/incidents/{incident_id}")
def delete_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(models.Incident).filter(models.Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    db.delete(incident)
    db.commit()
    return {"message": f"Incident {incident_id} deleted successfully"}