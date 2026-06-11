# Architecture

**Mapped:** 2026-06-11
**Pattern:** Monolithic Flask application

---

## Overview

Single-file Flask application serving a face recognition attendance system. All business logic, CV processing, and data I/O live in `app.py`. No service layer or abstraction boundaries — routes call CV functions and JSON helpers directly.

---

## Layers

```
┌─────────────────────────────────────────────┐
│  Presentation Layer                          │
│  templates/kiosk.html   — live kiosk UI      │
│  templates/register.html — employee mgmt     │
│  templates/admin.html   — attendance reports │
│  templates/login.html   — authentication     │
└────────────────┬────────────────────────────┘
                 │ HTTP / fetch()
┌────────────────▼────────────────────────────┐
│  API / Route Layer  (app.py)                 │
│  /api/recognize     /api/employees           │
│  /api/register_face /api/attendance          │
│  /login  /logout    /admin  /                │
└────────────────┬────────────────────────────┘
                 │ direct function calls
┌────────────────▼────────────────────────────┐
│  Business Logic  (app.py)                    │
│  OpenCV LBPH face recognition                │
│  Attendance state machine (in/out)           │
│  Employee CRUD                               │
└────────────────┬────────────────────────────┘
                 │ load_*/save_* helpers
┌────────────────▼────────────────────────────┐
│  Data Layer                                  │
│  data/employees.json  data/attendance.json   │
│  data/logs.json       data/config.json       │
│  data/faces/{emp_id}/face_*.jpg              │
└─────────────────────────────────────────────┘
```

---

## Key Data Flows

### Recognition Flow (Kiosk)
1. `kiosk.html` polls `/api/recognize` every 1.5s with a captured video frame
2. Server calls `extract_face()` — detects face via Haar cascade
3. LBPH predictor (`recognizer.predict()`) returns employee label + confidence
4. Maps label to employee record in `employees.json`
5. Updates attendance state (check-in / check-out) in `attendance.json`
6. Returns JSON result to kiosk UI

### Registration Flow
1. Admin creates employee via `/api/employees` (POST)
2. Frontend captures 10 face sample images → posts each to `/api/register_face`
3. Server saves face images to `data/faces/{emp_id}/`
4. After 10 samples, calls `train_recognizer()` — full LBPH retrain on all employees
5. Employee is now recognizable at kiosk

---

## Entry Points

- **Web server:** `app.py` lines 420–423 (`app.run(...)`)
- **Kiosk UI:** `GET /` → `templates/kiosk.html`
- **Admin panel:** `GET /admin` (requires login) → `templates/admin.html`
- **Registration:** `GET /register` → `templates/register.html`

---

## Global State

- `recognizer` — OpenCV LBPH face recognizer, loaded at startup and after each training
- `face_cascade` — Haar cascade classifier for face detection, loaded at startup

Both are module-level globals. No locking — concurrent requests can produce race conditions.

---

## Abstractions

None beyond thin JSON helpers (`load_employees()`, `save_employees()`, etc.). The codebase is deliberately simple/monolithic.

---
*Last mapped: 2026-06-11*
