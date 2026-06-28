---
phase: 10-superadmin-panel-extension
plan: "01"
subsystem: superadmin-panel
tags: [rbac, superadmin, employees, create-user, frontend, backend, api]
dependency_graph:
  requires: []
  provides:
    - superadmin_employees (GET /api/superadmin/employees)
    - _SA_ALLOWED role allowlist in create_user()
    - dept_admin dept_id guard in create_user()
    - panelEmployees tab with lazy-load and client-side filter
    - loadSuperEmployees / renderSuperEmployees / filterEmployees JS functions
    - onRoleChange / populateDeptSelector JS functions for create-user form
    - Сотрудники nav link in base.html superadmin sidebar
    - VALID_TABS extended (employees/devices/logs/calendar/analytics)
  affects:
    - app.py (create_user, superadmin_page, new endpoint)
    - templates/superadmin.html (create-user form, new tab)
    - templates/base.html (nav links)
tech_stack:
  added: []
  patterns:
    - ORM query + dict-map + jsonify for superadmin_employees
    - Lazy-load tab pattern (employeesLoaded flag + switchTab gate)
    - Client-side org filter with re-render
    - Server-side role allowlist (_SA_ALLOWED set)
key_files:
  created:
    - tests/test_sadm07_02.py
  modified:
    - app.py
    - templates/superadmin.html
    - templates/base.html
decisions:
  - Used _SA_ALLOWED set constant inside create_user() body (plan-prescribed pattern) rather than module-level constant to keep it co-located with the guard
  - switchTab extended only to currently-delivered tabs (orgs/users/system/employees); remaining tabs (devices/logs/calendar/analytics) registered in VALID_TABS but panels deferred to later plans
  - newOrgId onchange wired inline to repopulate dept selector when dept_admin is active; avoids extra event listener registration
metrics:
  duration: "~20 minutes"
  completed: "2026-06-28"
  tasks_completed: 3
  files_changed: 4
---

# Phase 10 Plan 01: SADM-07 / SADM-02 — User Creation Allowlist and Employees Tab Summary

Delivered superadmin create-user role allowlist (SADM-07) and system-wide read-only Employees tab (SADM-02) with server-side 403 enforcement, a scoped department selector in the create-user form, and a lazy-loaded employee directory filterable by organization.

## What Was Built

### Task 1: Backend (app.py + tests/test_sadm07_02.py)

**create_user() role fix (SADM-07 / T-10-01):** Replaced the restrictive single-role check (`target_role != "org_admin"`) with an `_SA_ALLOWED = {"org_admin", "dept_admin", "hr_viewer"}` allowlist. Superadmin creating roles outside this set receives 403 with Russian error message.

**dept_admin dept_id guard (T-10-02):** Added server-side guard after `new_dept_id` is resolved: `if target_role == "dept_admin" and not new_dept_id: return 400`. Prevents orphaned dept_admin accounts.

**GET /api/superadmin/employees (SADM-02 / T-10-03):** New endpoint under `# ─── API: Superadmin Extensions ───` section divider. Loads `Employee.query.all()`, builds `org_map` from `Organization.query.all()` and `dept_map` from `Department.query.all()`, returns JSON list with id, name, org_id, org_name (fallback "—"), dept_id, dept_name (fallback "—"), face_enrolled (bool), registered_at. Protected by `@require_role("superadmin")`.

**VALID_TABS extended:** `superadmin_page()` VALID_TABS updated to `{"orgs", "users", "system", "employees", "devices", "logs", "calendar", "analytics"}` for future plan compatibility.

**tests/test_sadm07_02.py:** 6 tests covering all acceptance criteria. All pass.

### Task 2: Frontend create-user form (templates/superadmin.html)

- Extended `newRole` select with `dept_admin` and `hr_viewer` options; added `onchange="onRoleChange()"`.
- Added hidden `deptSelectGroup` form-group with `newDeptId` select, placed after `newOrgId`.
- `newOrgId` select gains `onchange` to repopulate dept selector when `dept_admin` is the active role.
- Added `allDepts` state var (lazy-loaded by `populateDeptSelector`).
- `onRoleChange()`: shows/hides `deptSelectGroup`; triggers `populateDeptSelector` for `dept_admin`.
- `populateDeptSelector()`: lazy-fetches `/api/depts`, filters by selected `newOrgId`, repopulates `newDeptId` options.
- `createUser()` updated: reads `newDeptId` and includes `dept_id` in POST body.

### Task 3: Employees tab panel + nav link (templates/superadmin.html, templates/base.html)

- Added `panelEmployees` div (class `page hidden`) with toolbar/`empOrgFilter` select and table-card with 5 columns (Имя, Организация, Отдел, Лицо, Дата добавления), tbody `employeesTableBody`. Read-only — no edit/delete actions.
- Added JS state `allSuperEmployees = []`, `employeesLoaded = false`.
- `loadSuperEmployees()`: fetches `/api/superadmin/employees`, populates `empOrgFilter` from distinct org pairs, calls `renderSuperEmployees`.
- `renderSuperEmployees(list)`: renders rows with `escapeHtml` on all DB-sourced text (T-10-04), face check/dash symbol, empty-state "Нет данных" row.
- `filterEmployees()`: client-side filter by `org_id`, re-renders.
- `switchTab()` extended to include `panelEmployees` with lazy-load gate.
- `templates/base.html`: added "Сотрудники" nav link (`href=/superadmin/employees`, icon 👤) after "Пользователи" in the superadmin sidebar block.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

All four threats from the plan's STRIDE register were addressed:

| Threat | Mitigation | Location |
|--------|------------|----------|
| T-10-01 Elevation (create_user role) | `_SA_ALLOWED` set rejects employee/superadmin creation with 403 | app.py create_user() |
| T-10-02 Tampering (dept_admin dept_id) | Server-side guard returns 400 when dept_admin + no dept_id | app.py create_user() |
| T-10-03 Info Disclosure (employees endpoint) | `@require_role("superadmin")` returns 403 for all other roles; verified by test (f) | app.py superadmin_employees() |
| T-10-04 Tampering (name rendering) | `escapeHtml()` applied to all DB-sourced text in renderSuperEmployees | templates/superadmin.html |

## Known Stubs

None. All data sources are wired: `loadSuperEmployees` fetches live data from `/api/superadmin/employees` which queries the production database.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 — Backend | 771002e | app.py, tests/test_sadm07_02.py |
| 2 — Frontend create-user form | 524cdaa | templates/superadmin.html |
| 3 — Employees tab + nav link | 4198247 | templates/superadmin.html, templates/base.html |

## Self-Check: PASSED
