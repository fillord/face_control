---
phase: 06-sqlite-migration
plan: "02"
subsystem: database-bootstrap
tags: [sqlalchemy, flask, sqlite, orm, testing, conftest]
dependency_graph:
  requires: ["06-01"]
  provides: ["db-wired-app", "in-memory-test-isolation"]
  affects: ["app.py", "tests/conftest.py"]
tech_stack:
  added: ["Flask-SQLAlchemy db.init_app pattern", "in-memory SQLite test isolation", "ORM-backed bootstrap"]
  patterns: ["startup app_context block", "seed helper ORM insert", "db.create_all/drop_all per test"]
key_files:
  modified:
    - app.py
    - tests/conftest.py
decisions:
  - "abspath default for SQLALCHEMY_DATABASE_URI avoids Flask instance-path trap (Pitfall 8 / T-06-05)"
  - "db.create_all() runs before init_config/init_users to prevent no-such-table crash (Pitfall 2 / T-06-06)"
  - "AppSetting.query.get('password_hash') guards init_config() for idempotent bootstrapping"
  - "init_users() reads AppSetting hash verbatim preserving MIG-03 verbatim-hash behavior (T-06-03)"
  - "tmp_data stub keeps (tmp_data, dict) seed-helper signatures intact for all test_*.py call sites (Pitfall 6)"
  - "db.drop_all() in client teardown provides per-test schema isolation (T-06-04)"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-13"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 06 Plan 02: SQLAlchemy Bootstrap and Test Isolation Summary

**One-liner:** Flask-SQLAlchemy wired into app.py with abspath URI default and ORM-backed bootstrap; conftest.py rewritten for in-memory SQLite isolation with db.session seed helpers.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wire SQLAlchemy into app.py (config, init, startup, ORM bootstrap) | fa7b3a8 | app.py |
| 2 | Rewrite tests/conftest.py for in-memory SQLite isolation | b097140 | tests/conftest.py |

## What Was Built

### Task 1: app.py SQLAlchemy Integration

**Imports added** (after existing imports):
```python
from models import db, Employee, User, Organization, Department
from models import AttendanceRecord, EmployeeSchedule, LogEntry, TimesheetOverride, AppSetting
```

**SQLAlchemy config block** (after `app.secret_key`):
- `_db_url` uses `os.path.dirname(os.path.abspath(__file__))` to avoid Flask instance-path trap (T-06-05)
- `app.config["SQLALCHEMY_DATABASE_URI"]` + `SQLALCHEMY_TRACK_MODIFICATIONS = False` + `db.init_app(app)`

**`init_config()` rewritten** to insert AppSetting rows via ORM:
- Guards on `AppSetting.query.get("password_hash")` — idempotent
- Inserts `username=admin`, `password_hash=bcrypt(b"admin123")` on first run

**`init_users()` rewritten** to bootstrap User via ORM:
- Guards on `User.query.count() > 0` — idempotent
- Reads legacy hash from `AppSetting.query.get("password_hash")` verbatim (MIG-03 / T-06-03)
- Falls back to fresh `bcrypt(b"superadmin123")` if no hash stored

**Startup block** replaced module-level calls:
```python
with app.app_context():
    db.create_all()   # T-06-06: must run before init_config/init_users
    init_config()
    init_users()
```

All `load_*/save_*` helpers and JSON file constants remain intact (removed in plan 03).

### Task 2: tests/conftest.py Rewrite

**`tmp_data` fixture**: stub returning `tmp_path` — no monkeypatching, kept for call-site compat.

**`client` fixture**: sets `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"`, calls `db.create_all()` in setup and `db.session.remove(); db.drop_all()` in teardown. Per-test schema isolation (T-06-04).

**5 seed helpers** rewritten to use `db.session.add()` inside `with _app.app.app_context()`:
- `seed_users(tmp_data, users_dict)` → User rows
- `seed_config(tmp_data, config_dict)` → AppSetting rows
- `seed_orgs(tmp_data, orgs_dict)` → Organization rows
- `seed_depts(tmp_data, depts_dict)` → Department rows
- `seed_employees(tmp_data, employees_dict)` → Employee + EmployeeSchedule rows (D-02)

All seed helpers keep `(tmp_data, dict)` signatures — `tmp_data` accepted and ignored (Pitfall 6).

All `monkeypatch.setattr(_app, "*_FILE", ...)` calls removed.

## Verification Results

```
pytest tests/test_auth.py tests/test_rbac.py -q
3 passed, 7 xfailed, 1 xpassed in 16.64s
```

- `test_unauthenticated_redirect` (AUTH-05) — PASSED
- `test_public_routes` (AUTH-05) — PASSED
- `test_viewer_login_rejected` (AUTH-ROLE-01) — PASSED
- 7 xfailed tests remain xfail (route bodies not yet ORM-backed — plans 03/04)
- 1 xpassed: `test_init_users_bootstrap` passes unexpectedly (ORM bootstrap now works)

Import verification:
```
SECRET_KEY=test DATABASE_URL=sqlite:///:memory: python -c "import app; ..." → init OK
```

## Deviations from Plan

None — plan executed exactly as written. All ORM patterns followed the PATTERNS.md spec.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-06-03 | init_users reads AppSetting hash verbatim, not re-hashed |
| T-06-04 | db.drop_all() in teardown; in-memory DB is per-connection |
| T-06-05 | default URI uses os.path.abspath(__file__) join |
| T-06-06 | startup calls db.create_all() before init_config/init_users |

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced. Bootstrap functions are internal startup-only code.

## Self-Check: PASSED

- app.py modified: found
- tests/conftest.py modified: found
- commit fa7b3a8 exists: confirmed
- commit b097140 exists: confirmed
- `import app` with SECRET_KEY exits 0: confirmed
- `pytest tests/test_auth.py tests/test_rbac.py` exits 0: confirmed (3 passed, 7 xfailed, 1 xpassed)
- No `monkeypatch.setattr(_app, "EMPLOYEES_FILE"` in conftest.py: confirmed
- `sqlite:///:memory:` in conftest.py: confirmed
- `db.create_all()` in conftest.py: confirmed
- `db.drop_all()` in conftest.py: confirmed
