---
phase: 02-org-dept-data-model
plan: "03"
subsystem: api
tags: [crud, scope-gates, rbac, uuid, flask-routes, jinja2]

dependency_graph:
  requires: [02-01, 02-02]
  provides: [/api/orgs, /api/depts, update_employee_assignment, /superadmin, /org_admin, superadmin.html, org_admin.html]
  affects: [app.py, templates/superadmin.html, templates/org_admin.html]

tech_stack:
  added: []
  patterns: [server-side scope gate (403 on cross-org writes), cascade guard (409 on referenced delete), uuid4 for entity IDs, whitelist field assignment]

key_files:
  created:
    - templates/superadmin.html
    - templates/org_admin.html
  modified:
    - app.py

decisions:
  - "delete_org/delete_dept return 409 (not cascade-delete) when employees reference the entity"
  - "org_admin may only write depts/employees within their own session org_id — verified server-side"
  - "update_employee_assignment whitelists dept_id (and org_id for superadmin) only — never touches label/name"
  - "add_employee accepts org_id/dept_id/schedule from request but never client-supplied label"
  - "Templates reuse admin.html CSS verbatim with no new color/size tokens"

requirements-completed: [ORG-01, ORG-02, ORG-03, ORG-04]

metrics:
  duration: "~15 minutes"
  completed: "2026-06-12T05:55:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 02 Plan 03: Org/Dept CRUD + Admin Pages Summary

**Org/dept CRUD API with server-side scope gates and superadmin/org_admin management pages wired to the live API.**

## What Was Built

### Task 1 — Org/Dept CRUD routes + employee scope/reassign (app.py)

Added to `app.py`:

**Org routes (`# ─── API: Orgs ───`):**
- `list_orgs` (GET `/api/orgs`) — accessible to superadmin/org_admin/dept_admin
- `create_org` (POST, require superadmin) — `uuid.uuid4()` id, validates non-empty name, 400 on blank
- `update_org` (PUT `/api/orgs/<org_id>`) — 404 guard, updates name/description
- `delete_org` (DELETE) — 409 if any employee has that org_id

**Dept routes (`# ─── API: Depts ───`):**
- `list_depts` (GET `/api/depts`) — org_admin filtered to session org_id, dept_admin filtered to session org_id
- `create_dept` (POST, superadmin/org_admin) — 403 when org_admin target org_id ≠ session org_id
- `update_dept` (PUT `/api/depts/<dept_id>`) — same org_admin scope check
- `delete_dept` (DELETE) — 409 if employees reference the dept

**Employee scope/reassign:**
- Modified `add_employee` to gate dept_admin to session dept_id; accepts and stores `org_id`, `dept_id`, `schedule` (whitelisted, never label)
- `update_employee_assignment` (PATCH `/api/employees/<emp_id>`) — whitelists `dept_id` (and `org_id` for superadmin); org_admin validates target dept's org_id == session org_id; dept_admin → 403

**Page routes:**
- `superadmin_page` (`/superadmin`, require_role superadmin)
- `org_admin_page` (`/org_admin`, require_role org_admin)

### Task 2 — superadmin.html and org_admin.html

`templates/superadmin.html`: header, nav-tabs [Организации][Пользователи][Отчёты →], 3 stat cards (Организации/Сотрудников/Сегодня пришли), orgs table-card (Название/Сотрудников/Описание/Действия), inline add-org form (POST /api/orgs), edit (inline prefill → PUT), delete (window.confirm + DELETE with 409 handling "Не удалось удалить. Возможно, запись используется.").

`templates/org_admin.html`: header, nav-tabs [Отделы][Сотрудники][Отчёты →], 3 stat cards, depts table-card (Название/Руководитель/Сотрудников/Действия), inline add-dept form (POST /api/depts), edit/delete with confirm, employees table-card with dept-reassign control (PATCH /api/employees/<id>). Both files reuse admin.html class names (.stat-card, .table-card, .nav-tabs, .badge) — no new CSS tokens.

## Verification Results

```
tests/test_org_dept.py::test_org_crud         XPASS (ORG-01 GREEN)
tests/test_org_dept.py::test_dept_crud_scope  XPASS (ORG-02 GREEN)
tests/test_org_dept.py::test_employee_dept_scope XPASS (ORG-03 GREEN)
tests/test_org_dept.py::test_employee_reassign   XPASS (ORG-04 GREEN)
```

Full suite: 1 failed (pre-existing `test_public_routes` — kiosk.html absent in worktree), 1 passed, 6 xfailed, 12 xpassed.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | a628a57 | feat(02-03): add org/dept CRUD routes, employee scope gates, and role dashboard page routes |
| Task 2 | a9a693f | feat(02-03): create superadmin.html and org_admin.html wired to org/dept/employee APIs |

## Deviations from Plan

None — plan executed exactly as written. The one failing test (`test_public_routes`) is a pre-existing worktree gap that predates this plan's changes.

## Threat Surface Scan

Threat mitigations applied per plan's threat register:

| Threat ID | Mitigation Applied |
|-----------|--------------------|
| T-02-E1 | @require_role("superadmin") on all org write routes; dept_admin scope gate on employee create |
| T-02-T4 | create/update/delete_dept check target org_id == session org_id, else 403 |
| T-02-T5 | update_employee_assignment + add_employee whitelist fields; no wholesale request.json copy |
| T-02-T6 | Write routes verify referenced org/dept exists before acting |
| T-02-D2 | delete_org/delete_dept return 409 when employees reference the entity |

## Self-Check: PASSED

- app.py contains create_org, update_org, delete_org, create_dept, update_dept, delete_dept, update_employee_assignment, superadmin_page, org_admin_page — FOUND
- templates/superadmin.html references /api/orgs, contains "Создать организацию" — FOUND
- templates/org_admin.html references /api/depts, contains "Добавить отдел" — FOUND
- Commits a628a57 and a9a693f — FOUND
- 4 ORG tests: all xpassed
