---
phase: 07-org-admin-ux-improvements
plan: "03"
subsystem: org-admin-ui
tags:
  - employee-edit
  - inline-form
  - org-admin
  - rbac
dependency_graph:
  requires:
    - 07-02
  provides:
    - inline-employee-edit-form
    - employee-profile-patch
  affects:
    - app.py
    - templates/org_admin.html
tech_stack:
  added: []
  patterns:
    - inline-edit-panel with hidden/show toggle
    - dual-PATCH save (profile + schedule)
    - org_admin scope gate on PATCH endpoint
key_files:
  created: []
  modified:
    - app.py
    - templates/org_admin.html
decisions:
  - "scope gate placed before allowed_keys filter to fail fast on unauthorized access"
  - "return updated employee dict from PATCH for potential future optimistic UI use"
  - "editEmpPanel placed inside panelEmployees div, hidden by default via .hidden CSS class"
  - "dept select in edit form populated dynamically from allDepts at open time (not pre-rendered)"
metrics:
  duration: "~8 minutes"
  completed: "2026-06-15"
  tasks: 2
  files_modified: 2
---

# Phase 07 Plan 03: Employee Inline Edit Form Summary

**One-liner:** Org_admin can now edit employee name, position, department, and work schedule inline from the Employees tab via a dual-PATCH flow (profile + schedule endpoints).

## What Was Built

### Task 1: Expand PATCH /api/employees/<emp_id> (app.py)

Modified `update_employee_assignment()` to:

- Add org_admin scope gate early in the function (before `allowed_keys`): returns 403 if `emp.org_id != caller_org_id`
- Expand `allowed_keys` whitelist from `{"dept_id"}` to `{"dept_id", "name", "role"}` for org_admin (and `{"dept_id", "org_id", "name", "role"}` for superadmin)
- Apply `name` update with `.strip()` and non-empty validation (400 if blank)
- Apply `role` update (stored as job position string, not RBAC role)
- Return `{"status": "updated", "employee": _emp_to_dict(emp)}` so frontend gets fresh data

### Task 2: Inline edit form in templates/org_admin.html

Added to `panelEmployees`:

- `editEmpPanel` hidden card with: ФИО text input, Должность text input, Отдел select (populated from `allDepts`), Начало/Конец рабочего дня time inputs, Рабочие дни checkboxes (Пн–Вс), error display, and Save/Cancel buttons
- Updated thead to add 6th column `Действия`
- Updated empty-state colspan from 5 to 6
- Each row now has `<button class="btn-edit" onclick="startEditEmp(...)">Изменить</button>` in the Действия column
- Added three JS functions:
  - `startEditEmp(empId)` — pre-fills form from `allEmployees` and `allDepts`, shows panel
  - `cancelEmployeeEdit()` — hides panel
  - `saveEmployeeEdit()` — validates, PATCHes `/api/employees/<id>` then `/api/employees/<id>/schedule`, hides panel, reloads list

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | e9ece7f | feat(07-03): expand PATCH /api/employees/<emp_id> to accept name and role |
| 2    | 9569e4d | feat(07-03): add inline employee edit form and saveEmployeeEdit() to org_admin.html |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all fields (name, role, dept_id, schedule) are wired to real DB persistence via existing PATCH endpoints.

## Threat Surface Scan

No new network endpoints introduced. The expanded PATCH route already existed; the scope gate added in this plan closes an existing gap (T-07-03-A). No new trust boundaries created.

## Self-Check

- [x] `app.py` — `emp.org_id != caller_org_id` scope gate present
- [x] `app.py` — `allowed_keys` includes `"name"` and `"role"` for org_admin
- [x] `app.py` — `emp.name = name` and `emp.role = update_data["role"]` assignments present
- [x] `app.py` — response includes `"employee": _emp_to_dict(emp)`
- [x] `templates/org_admin.html` — `editEmpPanel` div present and hidden by default
- [x] `templates/org_admin.html` — `saveEmployeeEdit`, `startEditEmp`, `cancelEmployeeEdit` functions present
- [x] `templates/org_admin.html` — `Действия` column header added; colspan updated to 6
- [x] Commits e9ece7f and 9569e4d verified in git log
