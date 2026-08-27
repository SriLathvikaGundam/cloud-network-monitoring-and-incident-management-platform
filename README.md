# Cloud Network Monitoring & Incident Management Platform

A platform that simulates monitoring network devices, tracking availability and response times, and managing incidents through a full identify → prioritize → resolve workflow. Built with FastAPI and SQLAlchemy, deployed on Microsoft Azure.

**Live Demo:** [monitoring-lathvika-2026.azurewebsites.net](https://monitoring-lathvika-2026.azurewebsites.net)

## Overview

This platform tracks the availability and response times of registered devices (servers, routers, websites, etc.) through simulated monitoring checks, automatically creating incidents when a device is detected as down, and providing a dashboard to track incident resolution over time.

## Tech Stack

- **Language:** Python
- **Framework:** FastAPI
- **Database:** SQLite (deployed on Azure App Service free tier — see "Architecture Decisions")
- **ORM:** SQLAlchemy
- **Validation:** Pydantic
- **Templating:** Jinja2 (server-rendered HTML UI)
- **Server:** Uvicorn
- **Cloud:** Microsoft Azure App Service (Linux, F1 free tier)

## Features

- Device registry with CRUD management
- Simulated monitoring checks (randomized up/down status and response time, mirroring real network check behavior)
- Automatic incident creation when a device fails a check, with duplicate-incident prevention for ongoing outages
- Incident workflow: open → investigating → resolved, with resolution timestamps for reporting
- Full monitoring history log per device
- Server-rendered dashboard showing device count, open/resolved incidents, and average response time

## Data Model

```
Device ──< MonitoringLog
Device ──< Incident
```

- **Device** — name, hostname, device type, active status
- **MonitoringLog** — a record of one check: device, status (up/down), response time, timestamp
- **Incident** — created when a device fails a check; tracks severity, status, description, creation and resolution timestamps

## API Endpoints

| Resource | Endpoints |
|---|---|
| Devices | `GET/POST /devices`, `GET/PUT/DELETE /devices/{id}` |
| Monitoring | `POST /devices/{id}/check`, `POST /devices/check-all`, `GET /devices/{id}/logs` |
| Incidents | `GET /incidents`, `GET /incidents/{id}`, `PUT /incidents/{id}/status`, `DELETE /incidents/{id}` |

Full interactive documentation is available at `/docs`. A browsable HTML UI is available at `/`, `/ui/devices`, and `/ui/incidents`.

## Architecture Decisions

**Why simulated checks instead of real network pings?** This lets the platform demonstrate a complete monitoring and incident workflow without requiring real infrastructure to monitor. The simulation logic (`monitoring.py`) is isolated from the API routes, so it could be swapped for real checks (e.g. via `socket` or `requests`) without changing the rest of the system.

**Why prevent duplicate incidents?** A device that's down for an extended period would otherwise generate a new incident on every failed check. The system checks for an existing unresolved incident before creating a new one — a pattern used by real monitoring tools to avoid alert fatigue.

**Why SQLite instead of a managed cloud database?** Same reasoning as the companion Inventory project — evaluated Azure SQL/PostgreSQL for production-grade concurrency, but chose SQLite on Azure App Service's free tier to avoid cost as a student, with a clear migration path for production use.

## Getting Started

### Prerequisites
- Python 3.10+

### Setup

```bash
git clone https://github.com/SriLathvikaGundam/network-monitoring-platform.git
cd network-monitoring-platform

python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`, with interactive docs at `http://127.0.0.1:8000/docs`.

## Project Structure

```
├── main.py            # API routes and application entry point
├── models.py           # SQLAlchemy database models (tables)
├── schemas.py           # Pydantic schemas (request/response validation)
├── database.py            # Database connection and session setup
├── monitoring.py            # Device check simulation and incident creation logic
├── templates/                 # Jinja2 HTML templates for the UI
├── static/style.css              # UI styling
├── requirements.txt                # Python dependencies
└── README.md
```

## Deployment

Deployed to Azure App Service (Linux, Python 3.12 runtime, F1 free tier) via local Git deployment.

## Future Improvements

- Real network checks (TCP/HTTP) instead of simulation
- Scheduled/automatic periodic checks (e.g. via APScheduler or Azure Functions timer trigger)
- Severity auto-calculation based on device criticality
- Mean Time To Resolution (MTTR) reporting dashboard
- Authentication and role-based access control
