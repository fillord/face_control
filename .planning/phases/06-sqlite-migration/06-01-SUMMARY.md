---
phase: 06-sqlite-migration
plan: 01
subsystem: database
tags: [flask-sqlalchemy, sqlalchemy, sqlite, orm, migration, pytest]

# Dependency graph
requires:
  - phase: 05-token-based-kiosk-registration-russian-ui
    provides: org_token/kiosk_pin/reg_token/reg_pin fields in orgs.json that must be preserved in Organization ORM model
provides:
  - flask-sqlalchemy 3.1.1 installed in venv and pinned in requirements.txt
  - models.py with db object and all 9 ORM model classes (D-07)
  - Employee.label non-autoincrement for LBPH label preservation (D-14)
  - AttendanceRecord.event_type column (D-01)
  - TimesheetOverride composite PK on (emp_id, date) (D-04)
  - tests/test_sqlite_migration.py DB-02 scaffold (activates in plan 06-04)
affects:
  - 06-sqlite-migration/06-02 (imports db + models from models.py; rewrites conftest.py)
  - 06-sqlite-migration/06-03 (imports all model classes for route rewrites)
  - 06-sqlite-migration/06-04 (implements migrate_to_sqlite.py that activates DB-02 tests)

# Tech tracking
tech-stack:
  added:
    - flask-sqlalchemy==3.1.1
    - sqlalchemy==2.0.50
    - greenlet==3.5.1 (transitive dependency of sqlalchemy)
    - typing-extensions==4.15.0 (transitive dependency of sqlalchemy)
  patterns:
    - DeclarativeBase + SQLAlchemy(model_class=Base) ORM pattern
    - Mapped[T] + mapped_column() typed column declarations (SQLAlchemy 2.0 style)
    - autoincrement=False on non-PK integer columns (LBPH label preservation)
    - Composite primary key via two primary_key=True mapped_column declarations
    - pytest skipif guard for tests requiring future migration script

key-files:
  created:
    - requirements.txt
    - models.py
    - tests/test_sqlite_migration.py
  modified: []

key-decisions:
  - "Employee.label declared as Integer with autoincrement=False — preserves LBPH recognizer label exactly after migration (D-14)"
  - "models.py does not import app — avoids circular import; app.py will import from models (D-07, Open Question 3 RESOLVED)"
  - "AttendanceRecord.event_type String(16) nullable added — records last transition check_in/check_out (D-01)"
  - "TimesheetOverride uses composite PK on (emp_id, date) — replaces fcntl-locked JSON keyed by emp_id+date (D-04)"
  - "DB-02 tests skip with MIGRATION_AVAILABLE=False until migrate_to_sqlite.py exists in plan 06-04"

patterns-established:
  - "Pattern: models.py as standalone ORM module — no app import, imported by app.py one-directionally"
  - "Pattern: pytest.mark.skipif(not MIGRATION_AVAILABLE, ...) guards tests requiring future plan artifacts"
  - "Pattern: migration tests use local Flask app + in-memory SQLite + run_migration(data_dir=..., database_uri=...) signature"

requirements-completed: [DB-01, DB-02]

# Metrics
duration: 3m 44s
completed: 2026-06-13
---

# Phase 6 Plan 01: ORM Foundation Summary

**Flask-SQLAlchemy 3.1.1 ORM foundation with 9 model classes matching all JSON schemas, Employee.label non-autoincrement (D-14), AttendanceRecord.event_type (D-01), and DB-02 migration test scaffold skipping cleanly until plan 06-04**

## Performance

- **Duration:** 3m 44s
- **Started:** 2026-06-13T12:24:48Z
- **Completed:** 2026-06-13T12:28:32Z
- **Tasks:** 3
- **Files modified:** 3 created

## Accomplishments
- Installed flask-sqlalchemy 3.1.1 + sqlalchemy 2.0.50 into venv; pinned both in requirements.txt
- Created models.py with db object and all 9 ORM model classes: User, Employee, EmployeeSchedule, Organization, Department, AttendanceRecord, LogEntry, TimesheetOverride, AppSetting
- Employee.label declared `autoincrement=False` — LBPH recognizer id preserved exactly (D-14, threat T-06-01 mitigated)
- AttendanceRecord includes event_type String(16) nullable column per D-01 (threat T-06-02 mitigated)
- TimesheetOverride uses composite primary key on (emp_id, date) per D-04
- DB-02 test scaffold (3 tests: idempotency, zero-data-loss, label preservation) collects and skips cleanly; activates when plan 06-04 creates migrate_to_sqlite.py

## Task Commits

1. **Task 1: Install flask-sqlalchemy and record in requirements.txt** - `d129be4` (chore)
2. **Task 2: Create models.py with all 9 ORM model classes** - `af793be` (feat)
3. **Task 3: Create tests/test_sqlite_migration.py scaffold for DB-02** - `327cb2e` (test — TDD RED)

## Files Created/Modified
- `requirements.txt` - Pinned flask-sqlalchemy==3.1.1 and sqlalchemy==2.0.50
- `models.py` - Base(DeclarativeBase), db = SQLAlchemy(model_class=Base), 9 ORM model classes
- `tests/test_sqlite_migration.py` - DB-02 migration test scaffold (3 tests, all skipped until plan 06-04)

## Decisions Made
- Used `models.py` as a standalone module (not inline in app.py) per D-07 recommendation — keeps 1,877-line app.py manageable; one-directional import only (app.py imports models, never the reverse)
- Followed 06-PATTERNS.md column definitions exactly — names copied 1:1 from data/*.json key names
- Used `autoincrement=False` on Employee.label as required by D-14 and verified by automated assertion
- DB-02 test uses `run_migration(data_dir=..., database_uri=...)` signature to coordinate with plan 06-04 implementation

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Plan 06-02 (conftest.py rewrite + app.py ORM init) can proceed immediately
- `models.py` is the contract all downstream plans build against (D-07)
- `db`, all 9 model classes, and the exact column signatures are locked
- Existing test suite baseline maintained: 31 passed / 4 xfailed / 25 xpassed (3 new skipped tests are expected)

---
*Phase: 06-sqlite-migration*
*Completed: 2026-06-13*
