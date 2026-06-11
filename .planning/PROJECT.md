# Face Recognition Attendance System — Role & Timesheet Extension

## What This Is

A brownfield extension of an existing Flask + OpenCV face recognition attendance system. The extension adds multi-level role-based access control, organizational/departmental data isolation, and a T-13 timesheet with Excel/CSV export. The kiosk (public face check-in) remains unchanged; the new system layers HR management, reporting, and employee self-service on top.

## Core Value

Department heads and HR staff can view, manage, and export attendance data for exactly the employees they are authorized to see — no more, no less.

## Requirements

### Validated

- ✓ Face recognition check-in kiosk at / — existing
- ✓ Employee registration with face photos — existing
- ✓ Attendance logging (in/out, JSON storage) — existing
- ✓ Admin attendance report view — existing
- ✓ Flask session-based login (basic) — existing

### Active

- [ ] 5-role system: superadmin, org_admin, dept_admin, viewer, employee
- [ ] Organizations: superadmin creates/manages 2–5 orgs; each org is isolated
- [ ] Departments: linked to org; dept_admin sees only their dept
- [ ] Data isolation enforced at query layer (not just UI)
- [ ] T-13 timesheet grid (employees × days, symbols Я/О/У/П/В)
- [ ] Per-employee work schedule (standard 8h/5-day or custom days+hours)
- [ ] Timesheet totals: days worked, hours worked, absences, late arrivals
- [ ] Export T-13 to Excel (openpyxl) and CSV UTF-8 BOM
- [ ] bcrypt password hashing for all user accounts
- [ ] Default superadmin / superadmin123 on first run
- [ ] Each role can create roles one level below itself
- [ ] Employee cabinet: own T-13, exact arrival/departure times, late/absence summary
- [ ] Viewer role: read-only dept attendance view, no editing
- [ ] Migration script: existing employees → default org + dept

### Out of Scope

- Self-service org registration — orgs created by superadmin only
- Shift/rotating schedules (2/2, 1/3) — standard + custom only for v1
- Face re-registration from employee cabinet — admin-only for now
- Mobile app — web-first
- Real-time notifications — out of scope for v1
- OAuth / SSO — bcrypt local auth only

## Context

- **Existing codebase**: Single-file Flask app (`app.py`, ~16k), 4 HTML templates, JSON file storage (`data/`)
- **Existing auth**: Basic login at `/login` with Flask sessions already present — needs bcrypt upgrade
- **Existing employees**: Stored in `data/employees.json` (flat, no org/dept) — migration required
- **Server**: Ubuntu 25.04, PM2 process name `face-recognition`, port 5051, domain `face.almgp33.kz`
- **Domain context**: Kazakh clinic system; department names like ВОП-1, ВОП-2 (family medicine units)
- **Kiosk constraint**: `GET /` must remain public (no auth required) — face check-in is the primary device use case

## Constraints

- **Tech stack**: Flask + Python, no framework migration — extend in place
- **Storage**: JSON files in `data/` — no DB migration for v1
- **Python**: 3.14.4 on venv, openpyxl available via pip
- **Deployment**: PM2 manages the process; final step is `pm2 restart face-recognition`
- **Isolation**: Data isolation must be enforced server-side, not just hidden in UI

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| JSON file storage (no DB) | Existing pattern; low infra complexity for clinic scale | — Pending |
| Extend existing app.py vs split | Single-file works at this scale; splitting adds overhead | — Pending |
| bcrypt upgrade to existing login | Existing auth has no password hashing; security requirement | — Pending |
| Migration assigns all to default org+dept | Avoids blocking first-run on manual assignment | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-11 after initialization*
