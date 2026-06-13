---
plan: 06-03
phase: 06-sqlite-migration
status: complete
completed: 2026-06-13
self_check: PASSED
key-files:
  created: []
  modified:
    - app.py
---

# Plan 06-03: ORM Route Rewrite + fcntl Removal

## One-liner
Replaced all user/employee/org/dept/config/log JSON call sites in app.py with SQLAlchemy ORM queries, rewrote append_log to insert LogEntry rows with 10,000-entry cap, and removed all flat-entity JSON helpers, *_FILE constants, and fcntl (DB-01, DB-04).

## What Was Built

### Task 1: Replace require_role + user/employee/org/dept/config call sites with ORM
- `require_role()` now resolves users via `User.query.get(user_id)` with `user.active`/`user.role` attribute access
- Added `_emp_to_dict(e)`, `_org_to_dict(o)`, `_dept_to_dict(d)` helpers that return JSON-compatible dicts (including `schedule` sub-dict from EmployeeSchedule for employees)
- All `load_employees()` / `load_users()` / `load_orgs()` / `load_depts()` / `load_config()` route callers replaced with ORM queries
- Employee create/update routes use `db.session.add(Employee(...))` + `db.session.commit()`
- Config reads use `{s.key: s.value for s in AppSetting.query.all()}`; writes use AppSetting upsert + commit
- ORM shim wrappers (`load_orgs`, `load_depts`, `load_employees`, `load_users`) kept as thin ORM-backed helpers for test compatibility (return same dict shapes as before, no JSON file I/O)

### Task 2: Rewrite append_log to insert LogEntry with 10,000-entry cap
- `append_log(entry)` now constructs `LogEntry(...)`, adds to session, commits
- Enforces 10,000-row cap: queries count, deletes oldest rows by id when exceeded
- `LOGS_FILE` constant and file-based body removed entirely (D-03)

### Task 3: Remove migrated helpers, *_FILE constants, and fcntl
- Deleted function definitions: `load_config`, `save_config`, `load_users` (JSON), `save_users`, `load_employees` (JSON), `save_employees`, `load_orgs` (JSON), `save_orgs`, `load_depts` (JSON), `save_depts`
- Deleted constants: `CONFIG_FILE`, `USERS_FILE`, `EMPLOYEES_FILE`, `ORGS_FILE`, `DEPTS_FILE`, `LOGS_FILE`
- Removed `import fcntl` (line 2) and stripped `fcntl.flock` from `save_timesheet_overrides` body (full helper deleted in plan 04)
- `grep -c "fcntl" app.py` → 0 (D-04, D-15)

## Test Results
- `pytest tests/test_auth.py tests/test_rbac.py tests/test_org_dept.py tests/test_org_settings.py -q` → 10 passed, 6 xfailed, 10 xpassed (exit 0)

## Deviations
- Agent hit session limit before writing SUMMARY.md; all 3 task commits were complete. Orchestrator wrote SUMMARY.md manually and completed cleanup.
- ORM shim wrappers for `load_orgs/depts/employees/users` retained as thin ORM-backed helpers (return same JSON-shape dicts as original, zero file I/O) for test verification compatibility. These are not the same as the original JSON-reading helpers.

## Self-Check: PASSED
- `grep -c "fcntl" app.py` = 0 ✓
- `User.query.get` present in require_role ✓
- `LogEntry(` present in append_log ✓
- `LOGS_FILE` absent ✓
- `CONFIG_FILE`, `USERS_FILE`, `EMPLOYEES_FILE`, `ORGS_FILE`, `DEPTS_FILE` absent ✓
- Auth/RBAC/org/org-settings tests pass against SQLite ✓
