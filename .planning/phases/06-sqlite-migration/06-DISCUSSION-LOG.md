# Phase 6: SQLite Migration — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 06-sqlite-migration
**Areas discussed:** Schema for nested data, Test isolation scope, config.json treatment, ORM model depth

---

## Schema for Nested Data

### Attendance

| Option | Description | Selected |
|--------|-------------|----------|
| Normalize it | attendance_record table (emp_id, date, check_in_time, check_out_time). Enables SQL-level queries for late/absent detection. | ✓ |
| JSON text column | Keep nested structure as TEXT column; serialize/deserialize in Python. Loses SQL-level queryability. | |
| You decide | Leave to Claude's discretion based on existing query patterns. | |

**User's choice:** Normalize it
**Notes:** Enables the existing symbol engine (which already queries attendance by emp_id+date) to use SQL filters.

---

### Employee Schedule

| Option | Description | Selected |
|--------|-------------|----------|
| JSON text column | Store schedule as TEXT on employees table. It's always read as a whole unit. | |
| Separate schedule table | employee_schedule table (emp_id, start_time, end_time, work_days_json). More normalized. | ✓ |
| Flat columns | Individual boolean/time columns per day directly on employees. Fully queryable but verbose. | |

**User's choice:** Separate schedule table
**Notes:** work_days list stored as JSON TEXT within the schedule table row.

---

### Logs

| Option | Description | Selected |
|--------|-------------|----------|
| Normalize it | log_entry table with individual columns. INSERT per event; 10k cap via DELETE. | ✓ |
| Single JSON blob table | One-row table with TEXT column holding the serialized array. | |

**User's choice:** Normalize it
**Notes:** Eliminates the expensive load-whole-array + append + save cycle on every kiosk recognition event.

---

### Timesheet Overrides

| Option | Description | Selected |
|--------|-------------|----------|
| Normalize it | timesheet_override table (emp_id, date, symbol, updated_by, updated_at). Composite PK. fcntl removed. | ✓ |
| JSON text column | Single-row table with nested JSON blob. Preserves existing pattern exactly. | |

**User's choice:** Normalize it
**Notes:** fcntl advisory locking on timesheet_overrides eliminated by SQLAlchemy transactions.

---

## Test Isolation Scope

| Option | Description | Selected |
|--------|-------------|----------|
| test_*.py only (conftest.py can change) | conftest.py is infrastructure — can update to use in-memory SQLite and db.session.add() for seeding. Individual test functions stay unchanged. | ✓ |
| conftest.py also cannot change | Requires a compatibility shim: load/save functions remain as public API internally backed by SQLAlchemy. Much more complex. | |

**User's choice:** test_*.py only — conftest.py can be updated

---

### Test Database

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory SQLite :memory: | Each test gets fresh in-memory DB. Fastest, no disk I/O, auto-torn-down. | ✓ |
| Separate test file (test.db) | Temp file on disk, deleted after session. Identical to production SQLite. | |

**User's choice:** In-memory SQLite :memory:

---

## config.json Treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Out of scope — stays as a file | config.json remains a JSON file; not in the ROADMAP's 7-file list. | |
| Migrate to settings table | app_setting key-value table in SQLite. Cleaner long-term. | ✓ |
| Remove it entirely | config.json has served its purpose (MIG-03 complete); delete it and update references. | |

**User's choice:** Migrate to settings table
**Notes:** Adds config.json to scope (8 files total → SQLite). app_setting table: (key TEXT PK, value TEXT).

---

## ORM Model Depth

### Model approach

| Option | Description | Selected |
|--------|-------------|----------|
| Full ORM with model classes | Employee, User, Organization, Department, AttendanceRecord, etc. model classes with db.Column declarations. Standard Flask-SQLAlchemy pattern. | ✓ |
| Thin ORM — models only, raw queries where complex | Model classes for tables, db.session.execute(text(...)) for complex date-math queries. | |
| SQLAlchemy Core (no ORM classes) | Table() objects, no model classes, no db.session. Unusual for Flask. | |

**User's choice:** Full ORM with model classes

---

### load_*/save_* functions

| Option | Description | Selected |
|--------|-------------|----------|
| Remove load_*/save_* — routes call db.session directly | Clean cut; ~82 functions refactored; no leftover JSON API. | ✓ |
| Keep as ORM-backed wrappers | load_employees() returns list of Employee objects; saves upsert. Adds pointless indirection. | |

**User's choice:** Remove load_*/save_* entirely — routes call db.session directly

---

## Claude's Discretion

- Transaction boundary style: per-request Flask-SQLAlchemy app context with `@app.teardown_appcontext` cleanup
- Exact column types for timestamps (TEXT ISO 8601 vs DATETIME)
- Index design (emp_id+date composite index on attendance_record, log_entry)
- Placement of model classes (new models.py vs top of app.py)
- UPSERT strategy in migrate_to_sqlite.py (INSERT OR IGNORE vs check-first)

## Deferred Ideas

None — discussion stayed within phase scope.
