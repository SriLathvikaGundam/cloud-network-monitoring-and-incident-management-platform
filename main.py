from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
import models
import schemas
import monitoring
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request, Form
from fastapi.responses import RedirectResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Network Monitoring & Incident Management Platform")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


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

# ---------- UI ROUTES: DASHBOARD ----------

@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    device_count = db.query(models.Device).count()
    open_incidents = db.query(models.Incident).filter(models.Incident.status != "resolved").count()
    resolved_incidents = db.query(models.Incident).filter(models.Incident.status == "resolved").count()

    logs_with_response = db.query(models.MonitoringLog).filter(models.MonitoringLog.response_time_ms.isnot(None)).all()
    avg_response_time = round(sum(l.response_time_ms for l in logs_with_response) / len(logs_with_response), 1) if logs_with_response else 0

    recent_incidents = db.query(models.Incident).order_by(models.Incident.created_at.desc()).limit(5).all()

    return templates.TemplateResponse(request, "dashboard.html", {
        "device_count": device_count,
        "open_incidents": open_incidents,
        "resolved_incidents": resolved_incidents,
        "avg_response_time": avg_response_time,
        "recent_incidents": recent_incidents,
    })


# ---------- UI ROUTES: DEVICES ----------

@app.get("/ui/devices")
def ui_devices(request: Request, db: Session = Depends(get_db)):
    devices = db.query(models.Device).all()
    return templates.TemplateResponse(request, "devices.html", {"devices": devices})


@app.post("/ui/devices/create")
def ui_create_device(
    name: str = Form(...),
    hostname: str = Form(...),
    device_type: str = Form(""),
    db: Session = Depends(get_db),
):
    new_device = models.Device(name=name, hostname=hostname, device_type=device_type or None, is_active=True)
    db.add(new_device)
    db.commit()
    return RedirectResponse(url="/ui/devices", status_code=303)


@app.post("/ui/devices/{device_id}/check")
def ui_check_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device:
        monitoring.check_device(db, device)
    return RedirectResponse(url="/ui/devices", status_code=303)


@app.post("/ui/devices/{device_id}/delete")
def ui_delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device:
        db.delete(device)
        db.commit()
    return RedirectResponse(url="/ui/devices", status_code=303)


# ---------- UI ROUTES: INCIDENTS ----------

@app.get("/ui/incidents")
def ui_incidents(request: Request, db: Session = Depends(get_db)):
    incidents = db.query(models.Incident).order_by(models.Incident.created_at.desc()).all()
    return templates.TemplateResponse(request, "incidents.html", {"incidents": incidents})


@app.post("/ui/incidents/{incident_id}/status")
def ui_update_incident_status(incident_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    incident = db.query(models.Incident).filter(models.Incident.id == incident_id).first()
    if incident:
        incident.status = status
        if status == "resolved":
            from datetime import datetime
            incident.resolved_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/ui/incidents", status_code=303)