---
phase: 02-org-dept-data-model
plan: "04"
subsystem: api+frontend
tags: [dashboards, schedule, rbac, scope-gates, flask-routes, jinja2, dept-attendance]

dependency_graph:
  requires: [02-01, 02-02, 02-03]
  provides: [/api/superadmin_stats, /api/dept_attendance_today, /api/employees/<id>/schedule, /dept_admin, dept_admin.html, login-redirect-D11]
  affects: [app.py, templates/dept_admin.html]

tech_stack:
  added: []
  patterns: [15-min grace period for late detection, ISO weekday scope gate, whitelist schedule field assignment, session-role scoping for dept/org/superadmin, role-specific login redirect]

key_files:
  created:
    - templates/dept_admin.html
  modified:
    - app.py

decisions:
  - "login_page GET redirect also fixed by role — already-logged-in users sent to role-appropriate page"
  - "dept_attendance_today excludes day-off employees from absent count (A3 per RESEARCH)"
  - "Late threshold: schedule.start + 15 min grace; handles hour rollover correctly"
  - "PATCH /api/employees/<id>/schedule uses regex + range check; rejects '25:00' with 400"
  - "dept_admin_page route serves both dept_admin and viewer roles per D-11"
  - "GET /api/employees/<id> added (needed by test_schedule_update verification path)"

requirements-completed: [T13-06, DASH-01, DASH-02]

metrics:
  duration: "~5 minutes"
  completed: "2026-06-12T09:35:12Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 02 Plan 04: Stats Dashboards + Schedule Endpoints Summary

**Scoped dept dashboard with live attendance stats, per-employee schedule editing, and role-specific login redirects wired end-to-end.**

## What Was Built

### Task 1 — Stats + dept attendance + schedule PATCH endpoints, dept page, login redirect (app.py)

Added to `app.py`:

**`GET /api/superadmin_stats` (require_role superadmin):**
- Returns `{"orgs": int, "employees": int, "checkins_today": int}`
- Reads orgs.json, employees.json, attendance.json — counts records with check_in for today

**`GET /api/dept_attendance_today` (require_role dept_admin/org_admin/superadmin):**
- Scope filter: dept_admin → session dept_id; org_admin → session org_id; superadmin → all
- Skips employees on their day off (not counted as absent per A3)
- Late detection: check_in > schedule.start + 15 min grace (handles minute rollover at :45-:59)
- Returns `{"employees": [{emp_id, name, check_in, check_out, status, schedule}], "stats": {present, absent, late}}`

**`PATCH /api/employees/<emp_id>/schedule` (require_role superadmin/org_admin/dept_admin):**
- 404 guard; dept_admin restricted to own dept employees, else 403
- Validates `start`/`end` match `^\d{2}:\d{2}$` AND hour 0-23 / minute 0-59 (rejects "25:00" with 400)
- Validates `work_days` is a non-empty list of ints each in 1..7 (else 400)
- Stores only `{start, end, work_days}` (whitelist — T-02-T8 mitigation)

**`GET /api/employees/<emp_id>` (require_role superadmin/org_admin/dept_admin):**
- Single employee fetch (needed by test verification path)

**`GET /dept_admin` -> `dept_admin_page` (require_role dept_admin, viewer):**
- Renders `dept_admin.html` with username/role context, following admin_page/org_admin_page pattern

**`login_page` updates (D-11):**
- POST redirect: dept_admin/viewer now redirected to `/dept_admin` instead of `/admin`
- GET already-logged-in redirect: role-specific branching added (was hardcoded to `admin_page`)
- kiosk `is_late = now > "09:00:00"` line left UNCHANGED (Pitfall 4 — Phase 3 scope)

### Task 2 — dept_admin.html dashboard + schedule edit wired to scoped APIs

`templates/dept_admin.html` (331 lines):

- **Header**: МедКонтроль — Отдел; username badge; Киоск link; Выйти button
- **Nav tabs**: [Посещаемость (active)] [Сотрудники] [Отчёты ->]
- **Посещаемость tab**: 3 live stat cards (Пришли green, Отсутствуют orange, Опоздали orange);
  attendance table (Сотрудник, Приход, Уход, Статус, График); absent shows "—" for times;
  semantic badge colors per UI-SPEC; empty state "Сегодня никто ещё не отметился."
- **Сотрудники tab**: employee list with schedule string display ("09:00 – 18:00  Пн–Пт");
  "Изменить график" action opens inline form per employee
- **Schedule edit form**: Начало/Конец рабочего дня time inputs + 7 Cyrillic checkboxes pre-checked Mon-Fri;
  PATCHes `/api/employees/<id>/schedule`; on 400 shows "Заполните все обязательные поля.";
  on success closes form and reloads via `loadAttendance()`
- Single `fetch('/api/dept_attendance_today')` on page load, no polling
- Reuses all CSS classes from superadmin.html/admin.html verbatim; no new color/size tokens

## Verification Results

```
tests/test_org_dept.py::test_superadmin_stats         XPASS (DASH-01 GREEN)
tests/test_org_dept.py::test_dept_attendance_scope    XPASS (DASH-02 GREEN)
tests/test_org_dept.py::test_schedule_update          XPASS (T13-06 GREEN)
```

Full suite: 1 failed (pre-existing `test_public_routes` — kiosk.html absent in worktree), 1 passed, 3 xfailed, 15 xpassed.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 48a0d11 | feat(02-04): add superadmin_stats, dept_attendance_today, schedule PATCH, dept_admin page, login redirect |
| Task 2 | 9f166c8 | feat(02-04): create dept_admin.html dashboard wired to dept_attendance_today and schedule PATCH |

## Deviations from Plan

### Auto-added Missing Functionality

**1. [Rule 2 - Missing Functionality] Added GET /api/employees/<emp_id>**
- **Found during:** Task 1 test verification
- **Issue:** `test_schedule_update` optionally calls `GET /api/employees/<id>` to verify persistence; without this route the test skips verification. Also needed for future phases to pre-populate the schedule editor with current values.
- **Fix:** Added `get_employee(emp_id)` route with 404 guard and require_role protection
- **Files modified:** app.py
- **Commit:** 48a0d11

**2. [Rule 1 - Bug] Fixed login_page GET redirect**
- **Found during:** Task 1 — reviewing existing login_page code
- **Issue:** The GET redirect for already-logged-in users still pointed to `admin_page` unconditionally, defeating the role-specific routing. dept_admin/viewer would see the attendance-report page instead of their dashboard.
- **Fix:** Added role-specific branching to the GET handler, matching the POST handler pattern
- **Files modified:** app.py
- **Commit:** 48a0d11

## Threat Surface Scan

Threat mitigations applied per plan's threat register:

| Threat ID | Mitigation Applied |
|-----------|--------------------|
| T-02-I2 | dept_attendance_today filters scoped by session dept_id for dept_admin — no cross-dept leak |
| T-02-T7 | schedule PATCH validates HH:MM range + work_days ints 1-7; 400 on failure |
| T-02-E2 | schedule PATCH returns 403 if dept_admin targets employee outside their dept |
| T-02-T8 | schedule PATCH whitelists only {start, end, work_days}; label/name never modified |

No new unplanned threat surface introduced.

## Known Stubs

None — all stat cards, attendance rows, and schedule data are wired to live API responses. No hardcoded empty values flow to UI rendering.

## Self-Check: PASSED

- app.py contains `dept_attendance_today`, `superadmin_stats`, `update_employee_schedule`, `dept_admin_page` — FOUND
- templates/dept_admin.html exists and is 331 lines (>= 90) — FOUND
- templates/dept_admin.html references `/api/dept_attendance_today` — FOUND
- templates/dept_admin.html references schedule PATCH path — FOUND
- templates/dept_admin.html contains "Изменить график" — FOUND
- kiosk `is_late = now > "09:00:00"` unchanged — CONFIRMED
- Commits 48a0d11 and 9f166c8 — FOUND
- 3 DASH/T13 tests: all xpassed — CONFIRMED
