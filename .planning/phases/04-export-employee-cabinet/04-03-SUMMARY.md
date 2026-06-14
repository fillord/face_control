---
phase: 04-export-employee-cabinet
plan: "03"
subsystem: employee-cabinet
tags: [employee, cabinet, T-13, emp_id, FK, login, stats, tooltips, rbac]
dependency_graph:
  requires:
    - 04-01 (xfail test scaffold for EMP-01..03)
    - 04-02 (export routes, openpyxl install)
  provides:
    - User.emp_id FK column linking login account to Employee record
    - employee-role login admission in ALLOWED_LOGIN_ROLES
    - POST-login redirect to /employee for employee role
    - Rewritten employee_page() route with cabinet logic
    - templates/employee.html (stats cards + month selector + read-only T-13 grid)
    - emp_id plumbing in create_user API and admin.html create-user form
  affects:
    - tests/test_export_employee.py (EMP-01..03 xfail markers removed — all 6 pass)
tech_stack:
  added: []
  patterns:
    - emp_id resolved from session user only (IDOR mitigation pattern)
    - Server-side month clamp to [prev_month, current_month] (client param untrusted)
    - Idempotent ALTER TABLE startup migration guarded by OperationalError
    - times_by_date dict for tooltip data (date -> {check_in, check_out})
    - early_count computed from U/OU symbols (not returned by compute_employee_totals)
key_files:
  created:
    - templates/employee.html
  modified:
    - models.py (User.emp_id column added)
    - app.py (ALLOWED_LOGIN_ROLES, login dispatch, startup migration, employee_page rewrite, create_user emp_id)
    - templates/admin.html (emp_id input + toggleEmpIdField JS in create-user form)
    - tests/conftest.py (seed_users passes emp_id to User constructor)
    - tests/test_export_employee.py (xfail markers removed from 3 EMP-* tests)
decisions:
  - emp_id forced to None for non-employee roles in create_user (T-04-EMP-LINK)
  - USERS tab visibility for org_admin/dept_admin deferred to follow-up RBAC task
  - seed_users updated to pass emp_id= so test fixtures wire User to Employee record
  - early_count computed inline (U + OU) because compute_employee_totals does not expose it (Gap 3)
  - Startup migration uses try/except OperationalError — idempotent and re-run-safe
metrics:
  duration: "~11 minutes"
  completed: "2026-06-14"
  tasks_completed: 4
  files_changed: 5
---

# Phase 04 Plan 03: Employee Cabinet Vertical Slice Summary

**One-liner:** Employee self-service T-13 cabinet with session-scoped data isolation, server-side month clamp, Приход/Уход tooltips, and three attendance stat cards (EMP-01, EMP-02, EMP-03).

## What Was Built

### Task 1: User.emp_id column + employee login (models.py, app.py, tests/conftest.py)

Added `emp_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)` to the `User` class in `models.py` immediately after `dept_id` (D-10).

In `app.py`:
- Added `from sqlalchemy import text` and `from sqlalchemy import exc as sa_exc` to support the startup migration.
- Changed `ALLOWED_LOGIN_ROLES` from `("superadmin", "org_admin", "dept_admin")` to include `"employee"` as a fourth element (Gap 2 — employees previously could not log in).
- Added `elif role == "employee": return redirect(url_for("employee_page"))` in the login dispatch block (before the `else` fallback to `dashboard_page`).
- Added an idempotent `ALTER TABLE user ADD COLUMN emp_id TEXT` immediately after `db.create_all()` in the startup block, guarded by `try/except sa_exc.OperationalError: pass` (Pitfall 4 — create_all does not alter existing tables).

In `tests/conftest.py`: `seed_users()` now passes `emp_id=u.get("emp_id")` to the `User` constructor so test fixtures can link employee-role users to Employee records.

### Task 2: Rewrite employee_page() (app.py)

Replaced the `employee_page()` stub (which rendered `dashboard.html`) with a full cabinet implementation:

- Resolves `emp_id` from `user.emp_id` (session-derived, never from URL) — T-04-EMP-IDOR mitigation.
- Returns empty-state error template when `user.emp_id` is None (account not linked).
- Returns 403 when `Employee.query.get(emp_id)` is None (invalid emp_id IDOR guard).
- Server-side month clamp: `prev_month` computed from `now.replace(day=1) - timedelta(days=1)`; client `month` param rejected outside `[prev_month, current_month]` (D-08, Pitfall 6).
- Loads `AttendanceRecord` ORM rows filtered to `emp_id + date range` and builds both `attendance` dict (for `compute_symbol`) and `times_by_date` dict (for tooltip data, EMP-02).
- Loads `TimesheetOverride` rows for the employee.
- Builds single-row grid using the same inline per-cell loop as `/timesheet`.
- Computes `early_count = sum(1 for s in symbols if s in ("У", "ОУ"))` (EMP-03, Gap 3 — `compute_employee_totals` does not expose early count).
- Passes `stats = {late, absences, early}`, `grid_row`, `times_by_date`, `days`, `month_str`, `current_month`, `prev_month`, `holidays_set` to `render_template("employee.html", ...)`.

### Task 3: Create templates/employee.html (templates/employee.html, tests/test_export_employee.py)

Created `templates/employee.html` (lang="ru") with:

1. **Header**: same as `timesheet.html` pattern — logo "МедКонтроль — Личный кабинет", `{{ username }}` user badge, Выйти link. No back-to-admin link per UI-SPEC note 6.
2. **Error empty-state**: if `error` is set, renders the error message and stops (no grid).
3. **Page title**: h1 "Мой табель".
4. **Stats grid**: `.stats-grid` with 3 `.stat-card` cells — Опоздания (`stats.late`), Отсутствия (`stats.absences`), Ранний уход (`stats.early`); all values use `.stat-val.orange` (#E65100) per UI-SPEC.
5. **Month selector**: form method="GET" action="/employee" with input[type=month] name="month", value="{{ month_str }}", min="{{ prev_month }}", max="{{ current_month }}", and a Показать submit button.
6. **T-13 grid**: read-only single-row. `sym_titles` and `sym_bg` maps copied from `timesheet.html`. Cells carry a `title` attribute: "Приход: HH:MM / Уход: HH:MM" (sliced to `[:5]`, "—" when missing) when `times_by_date.get(cell.date)` exists; "Нет данных" otherwise. No `onclick`, no `tabindex`, no edit dropdown (D-09).
7. **Totals row**: labeled "Итого" with the single-employee totals.

Removed `@pytest.mark.xfail(...)` decorators from `test_employee_cabinet_renders`, `test_employee_tooltip_times`, `test_employee_stats_counts`. All 6 Phase 4 tests now pass.

### Task 4: emp_id link plumbing (app.py, templates/admin.html)

In `app.py` `create_user()`:
- Reads `new_emp_id = (data.get("emp_id") or None) if target_role == "employee" else None` — emp_id applied only when role is employee; forced to None otherwise (T-04-EMP-LINK).
- Passes `emp_id=new_emp_id` to `User(...)` constructor.
- Logs `emp_id={new_emp_id!r}` in the `USER_CREATED` print line.

In `templates/admin.html`:
- Added `<div id="empIdGroup">` with label "ID сотрудника" and `<input id="newEmpId">` after the Роль select; hidden by default (`style="display:none;"`).
- Added `onchange="toggleEmpIdField()"` to `#newRole` select.
- Added `toggleEmpIdField()` JS function that shows/hides `#empIdGroup` based on role value.
- `toggleCreateForm()` calls `toggleEmpIdField()` at the end to initialize state when the panel opens.
- `createUser()` reads `const empId = document.getElementById("newEmpId").value.trim()` and includes `emp_id: empId` in the POST body.

**Deferral:** The `#createUserPanel` / USERS tab is currently gated `{% if session.role == 'superadmin' %}`. Expanding this tab's visibility to `org_admin`/`dept_admin` to let them create employee-role accounts is a RBAC gating change beyond Phase 4's locked decisions. Deferred to a follow-up RBAC task. The `emp_id` field and API plumbing added here make the link reachable wherever the form renders.

## Verification Results

```
tests/test_export_employee.py: 6 passed, 0 xfailed, 0 errors
tests/ (full suite): 40 passed, 9 xfailed, 20 xpassed, 0 failures
```

All success criteria met:
- EMP-01: /employee returns 200 with "Мой табель" heading
- EMP-02: "Приход" and arrival time appear as tooltip text on day cells
- EMP-03: "Опоздания", "Отсутствия", "Ранний уход" stat labels present
- IDOR: emp_id read only from session; URL manipulation cannot expose other employee's data
- Month clamp enforced server-side

## Deviations from Plan

### Auto-added: seed_users emp_id support (Rule 2 — Missing Critical Functionality)

**Found during:** Task 1 preparation

**Issue:** `seed_users()` in `tests/conftest.py` did not pass `emp_id` to the `User` constructor. The EMP-* test fixtures include `"emp_id": "emp-1"` in the seed dict to link the employee-role user to an Employee record. Without this, `user.emp_id` would always be `None` in tests, causing `employee_page()` to return the "not linked" error state instead of the cabinet.

**Fix:** Added `emp_id=u.get("emp_id")` to the `User(...)` constructor in `seed_users()`.

**Files modified:** `tests/conftest.py`

**Commit:** 8f949b5 (included in Task 1 commit)

## Deferred Items

| Item | Reason |
|------|--------|
| USERS tab visibility for org_admin/dept_admin | RBAC gating change beyond Phase 4 locked decisions; deferred to follow-up RBAC task. The emp_id field and API plumbing are already in place. |

## Known Stubs

None. The employee cabinet is fully wired end-to-end: schema, login routing, route logic, template rendering, and test assertions all connect through live code paths.

## Threat Flags

No new threat surface beyond the plan's threat_model:
- T-04-EMP-IDOR mitigated: emp_id read only from `user.emp_id` (session); never from URL
- T-04-EMP-MONTH mitigated: month clamp server-side; client param rejected outside bounds
- T-04-EMP-AUTH mitigated: employee role gated by @require_role("employee") on /employee
- T-04-EMP-LINK mitigated: emp_id forced to None for non-employee roles in create_user
- T-04-MIGRATE accepted: additive nullable column, guarded by OperationalError

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: User.emp_id + employee login + startup migration | 8f949b5 | models.py, app.py, tests/conftest.py |
| Task 2: Rewrite employee_page() | 738a48d | app.py |
| Task 3: employee.html + xfail removal | 97b4d83 | templates/employee.html, tests/test_export_employee.py |
| Task 4: emp_id link plumbing | b979682 | app.py, templates/admin.html |

## Self-Check: PASSED

- FOUND: models.py (User.emp_id column present)
- FOUND: app.py (ALLOWED_LOGIN_ROLES contains employee, elif role == "employee" dispatch, ALTER TABLE migration, rewritten employee_page, emp_id in create_user)
- FOUND: templates/employee.html (contains "Мой табель", "Приход", stats cards)
- FOUND: templates/admin.html (contains newEmpId, toggleEmpIdField)
- FOUND: tests/conftest.py (emp_id=u.get("emp_id") in seed_users)
- FOUND: tests/test_export_employee.py (xfail markers removed from EMP-* tests)
- FOUND commit 8f949b5 (Task 1)
- FOUND commit 738a48d (Task 2)
- FOUND commit 97b4d83 (Task 3)
- FOUND commit b979682 (Task 4)
- Test run: 6 passed (test_export_employee.py), 40 passed full suite, 0 failures
