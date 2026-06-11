---
phase: 01-rbac-foundation
plan: 03
subsystem: auth/rbac
tags: [security, rbac, route-protection, nav]
dependency_graph:
  requires: [01-02]
  provides: [protected-api-surface, role-gated-nav]
  affects: [app.py, templates/admin.html]
tech_stack:
  added: []
  patterns: [require_role-decorator, jinja2-session-conditional]
key_files:
  created: []
  modified:
    - app.py
    - templates/admin.html
decisions:
  - "All 10 non-kiosk routes protected with @require_role('superadmin','org_admin','dept_admin') (AUTH-05)"
  - "login_required function deleted entirely per D-04 (zero occurrences in app.py)"
  - "admin_page() now passes username from users.json to render_template for DASH-03"
  - "admin.html nav tabs wrapped in Jinja2 role gate; tabUsers placeholder added for plan 01-04"
metrics:
  duration: "2m 9s"
  completed_date: "2026-06-11"
  tasks_completed: 2
  files_modified: 2
---

# Phase 01 Plan 03: Route Security Hardening and Nav Role-Gating Summary

**One-liner:** Applied @require_role to all 10 non-kiosk routes, retired @login_required, and added Jinja2 role-gated nav with real username to admin.html.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Apply @require_role to all non-kiosk routes and retire @login_required | da8b606 | app.py |
| 2 | Role-gate admin.html navigation and show real username | a035475 | templates/admin.html |

## What Was Built

### Task 1: Route Protection (AUTH-05, D-04)

- Deleted `login_required` function definition from app.py (D-04: fully retired)
- Replaced `@login_required` on `/register` and `/admin` with `@require_role("superadmin", "org_admin", "dept_admin")`
- Added `@require_role("superadmin", "org_admin", "dept_admin")` to all 8 previously-unprotected API routes:
  - `GET /api/employees`
  - `POST /api/employees`
  - `DELETE /api/employees/<emp_id>`
  - `POST /api/employees/<emp_id>/reset`
  - `POST /api/register_face`
  - `GET /api/attendance`
  - `GET /api/attendance/dates`
  - `GET /api/stats`
- Kiosk trio (`GET /`, `POST /api/recognize`, `POST /api/detect`) remain undecorated and public
- `admin_page()` handler now looks up username from users.json and passes to template
- `grep -c "login_required" app.py` returns 0; `grep -c "@require_role" app.py` returns 11

### Task 2: Admin Nav Role-Gating (DASH-03)

- Replaced static `<span class="user-badge">Администратор</span>` with `{{ username }}`
- Wrapped existing Журнал посещаемости and Статистика за месяц tabs in `{% if session.role in ['superadmin', 'org_admin', 'dept_admin'] %}`
- Added `Пользователи` tab trigger (`id="tabUsers"`) inside the same role gate (panel wired in plan 01-04)
- No new CSS added; existing `.tab` classes reused

## Verification Results

```
pytest tests/test_rbac.py::test_unauthenticated_redirect tests/test_rbac.py::test_public_routes -x -q
..
2 passed in 0.23s

pytest tests/ -q
2 passed, 2 xfailed, 6 xpassed in 2.27s
```

Acceptance criteria verified:
- `grep -c "login_required" app.py` = 0
- `grep -c "@require_role" app.py` = 11 (>= 10 required)
- `grep -c "session.role in \['superadmin', 'org_admin', 'dept_admin'\]" templates/admin.html` = 1
- `grep -c "Администратор</span>" templates/admin.html` = 0
- `grep -c "{{ username }}" templates/admin.html` = 1
- `grep -c "tabUsers" templates/admin.html` = 1

## Deviations from Plan

### Auto-added Functionality

**1. [Rule 2 - Missing Critical] admin_page() passes username to render_template**

- **Found during:** Task 1
- **Issue:** Plan Task 2 specified that admin_page() needed updating to look up username and pass to render_template. This was done as part of Task 1 (the app.py touch) since the plan allowed one app.py edit in Task 2.
- **Fix:** Added username lookup and render_template call within admin_page() in the same Task 1 commit to minimize the diff surface and keep both changes coherent.
- **Files modified:** app.py
- **Commit:** da8b606

No other deviations. Plan executed as written.

## Known Stubs

- `Пользователи` tab (tabUsers) in admin.html has no panel — clicking it triggers `switchTab('users')` but `panelUsers` div does not yet exist. This is intentional per plan spec ("panel content is built in plan 01-04"). No data flows to UI from this stub.

## Threat Surface Scan

All mitigations from the plan threat register were applied:

| Threat ID | Status |
|-----------|--------|
| T-01-03-API | Mitigated — all 8 API routes now decorated with @require_role |
| T-01-03-LR | Mitigated — login_required deleted, 0 occurrences confirmed |
| T-01-03-NAV | Accepted — Jinja2 nav gating is supplemental; server @require_role is authoritative |
| T-01-03-KIOSK | Mitigated — kiosk handlers confirmed undecorated; test_public_routes passes |

No new threat surface introduced by this plan.

## Self-Check

- [x] app.py modified and committed at da8b606
- [x] templates/admin.html modified and committed at a035475
- [x] login_required: 0 occurrences
- [x] @require_role: 11 occurrences
- [x] Tests pass: 2 passed, 2 xfailed, 6 xpassed
