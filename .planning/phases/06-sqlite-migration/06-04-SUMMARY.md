---
phase: 06-sqlite-migration
plan: "04"
subsystem: data-layer
tags: [orm, attendance, recognition, migration, sqlite]
dependency_graph:
  requires: [06-03]
  provides: [DB-01, DB-02, DB-05]
  affects: [app.py, migrate_to_sqlite.py, .gitignore]
tech_stack:
  added: []
  patterns:
    - "ORM attendance dict adapter: query AttendanceRecord → build {date: {emp_id: {check_in, check_out}}} dict for pure functions"
    - "ORM override dict adapter: query TimesheetOverride → build {emp_id: {date: symbol}} dict"
    - "on_conflict_do_nothing idempotent migration for flat-PK tables"
    - "query-then-skip idempotency for auto-increment tables (AttendanceRecord, LogEntry)"
    - "run_migration() detects active Flask app context and reuses it for test compatibility"
key_files:
  created:
    - migrate_to_sqlite.py
    - .gitignore
  modified:
    - app.py
decisions:
  - "Attendance dict adapter: ORM rows converted to {date:{emp_id:{check_in,check_out}}} for compute_symbol/compute_timesheet_grid (Pitfall 5 preserved)"
  - "event_type set on every check-in (check_in) and check-out (check_out) by recognition route (D-01)"
  - "Migrated AttendanceRecord rows get event_type based on check_out presence (check_out→check_out, else check_in; NULL acceptable for legacy)"
  - "run_migration() uses has_app_context() to reuse active context from test fixtures (no double-init)"
  - "tempfile import removed as save_timesheet_overrides was sole user"
metrics:
  duration: "~40 minutes"
  completed: "2026-06-13T16:46:00Z"
  tasks_completed: 3
  tasks_total: 4
  files_changed: 3
  checkpoint_pending: 1
---

# Phase 06 Plan 04: Finish Migration — ORM Attendance/Recognition + migrate_to_sqlite.py Summary

**One-liner:** Attendance, recognition, and timesheet-override routes fully ORM-backed; `migrate_to_sqlite.py` migrates all JSON sources idempotently with label preservation and `on_conflict_do_nothing`; `event_type` set on every check-in/check-out transition (D-01).

## Tasks Completed

### Task 1: Rewrite attendance, recognition, and timesheet-override routes to ORM

Replaced all remaining `load_attendance()`, `save_attendance()`, `load_timesheet_overrides()`, and `save_timesheet_overrides()` call sites with ORM operations:

**Recognition route (`/api/recognize`):**
- Queries `AttendanceRecord.query.filter_by(emp_id=emp_id, date=today).first()`
- New record: `AttendanceRecord(emp_id, date, check_in_time=now, event_type="check_in")`
- Check-out: `rec.check_out_time = now; rec.event_type = "check_out"`
- Already-done: leaves event_type unchanged
- `db.session.commit()` once per recognition; rollback on error

**Timesheet route (`/timesheet`):**
- Queries `AttendanceRecord` for the requested month's date range
- Builds `{date: {emp_id: {check_in, check_out}}}` dict adapter for `compute_timesheet_grid`
- Queries `TimesheetOverride.query.all()` for `{emp_id: {date: symbol}}` adapter
- `compute_symbol` and `compute_timesheet_grid` pure functions unchanged (Pitfall 5)

**Timesheet override (`/api/timesheet/override`):**
- DELETE: `db.session.get(TimesheetOverride, (emp_id, date_str))` then `db.session.delete()`
- POST: upsert via `db.session.get` then update or `db.session.add`; sets `updated_by`/`updated_at`

**Other routes updated (all now use ORM attendance adapter):**
- `superadmin_stats`: `AttendanceRecord.query.filter(date==today, check_in_time != None).count()`
- `dept_attendance_today`: queries `AttendanceRecord.emp_id.in_(scoped_ids)` for today
- `kiosk_log`: queries `AttendanceRecord` with `emp_id.in_()` filter
- `get_attendance`: `AttendanceRecord.query.filter_by(date=day)`
- `get_dates`: `db.select(AttendanceRecord.date).distinct()`
- `get_stats`: `AttendanceRecord.query` with optional date filters
- `org_admin` DASH-04 summary: ORM-backed attendance and overrides adapters

**Commit:** `4b541ad`

---

### Task 2: Remove final JSON helpers + constants; verify zero JSON I/O in app.py

Deleted from `app.py`:
- `load_attendance()` function
- `save_attendance()` function
- `load_timesheet_overrides()` function
- `save_timesheet_overrides()` function
- `ATTENDANCE_FILE` constant
- `TIMESHEET_OVERRIDES_FILE` constant
- `tempfile` import (was only used by `save_timesheet_overrides`)

Remaining `json.loads`/`json.dumps` calls (5 total) are ALL for `work_days_json` TEXT column serialization — NOT data-store file I/O. This is correct behavior per D-02.

**Verification passed:**
- `grep -Eq "^def (load_attendance|save_attendance|...)"`  → no matches
- `grep -q "ATTENDANCE_FILE|..._FILE"` → no matches
- `grep -c "fcntl"` → 0
- Full suite: 34 passed, 9 xfailed, 20 xpassed (DB-01, DB-03)

**Commit:** `65fe271`

---

### Task 3: Write migrate_to_sqlite.py and add .gitignore

**`migrate_to_sqlite.py`:**
- `run_migration(data_dir=None, database_uri=None)` with sensible defaults (D-13, D-16)
- `_load_json(data_dir, filename)` returns `{}` if file absent (Pitfall 7)
- Idempotency strategies:
  - Flat-PK tables (Employee, User, Organization, Department, AppSetting, TimesheetOverride): `sqlite_insert(...).on_conflict_do_nothing(index_elements=[...])`
  - EmployeeSchedule: `on_conflict_do_nothing(index_elements=["emp_id"])`
  - AttendanceRecord, LogEntry: query-then-skip (auto-increment PK, no natural unique key to target)
- Label preservation: `label=int(emp["label"])` verbatim (D-14, T-06-11)
- event_type on migrated AttendanceRecord: `"check_out"` if check_out present, else `"check_in"` (D-01)
- `has_app_context()` check: reuses active Flask context from test fixtures (D-11 compatibility)
- Per-table printed summary
- `if __name__ == "__main__": run_migration()`

**`.gitignore`:**
- `data/app.db` (DB-05)
- `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`
- Standard Python/virtualenv/editor ignores

**Tests passed:** `tests/test_sqlite_migration.py` — 3 passed (idempotency, zero-data-loss, label preservation)

**Commit:** `218b63c`

---

### Task 4: Human Checkpoint (APPROVED)

Task 4 is a `checkpoint:human-verify` gate. All items verified by operator:
1. ✓ Real-data migration: 2 employees, 7 users, 2 orgs, 3 depts, 6 attendance, 27 logs — counts match JSON sources
2. ✓ Idempotency: second run inserted 0 new rows with no errors
3. ✓ Label preservation: employee labels 1 and 2 match employees.json exactly
4. ✓ App boots with only SECRET_KEY + DATABASE_URL; /login → 200
5. ✓ Migrated data (7 users, 2 employees) survives PM2 restart

**Note:** migrate_to_sqlite.py requires running against a clean DB (before init_users() bootstraps a superadmin) to avoid UNIQUE constraint on username. Documented as a known ordering requirement.

**Status:** APPROVED by operator 2026-06-13.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] migrate_to_sqlite.py used separate Flask app context, causing test queries to see empty database**
- **Found during:** Task 3 test run (`test_migration_zero_data_loss`, `test_migration_label_preservation` both failed)
- **Issue:** `run_migration()` created a new `Flask(__name__)` app and called `db.init_app(new_app)`. The test fixture `_db_context` had already called `db.init_app(test_app)` and was inside `with test_app.app_context()`. The migration inserted into the new app's SQLite but the test queries ran against the fixture's in-memory SQLite — two different databases, both `:memory:`.
- **Fix:** Added `has_app_context()` check; when an active context exists, migration reuses it via `db.session` directly (no new Flask app created). Only creates a new Flask app in standalone/CLI invocations.
- **Files modified:** `migrate_to_sqlite.py`
- **Commit:** `218b63c`

---

## Known Stubs

None — all routes return live ORM data; no placeholder values.

---

## Threat Flags

No new threat surface introduced beyond what was documented in the plan's threat model (T-06-11 through T-06-15). No new network endpoints, auth paths, or schema changes added in this plan.

---

## Self-Check (pre-write)

| Item | Status |
|------|--------|
| `4b541ad` exists | Yes (Task 1 commit) |
| `65fe271` exists | Yes (Task 2 commit) |
| `218b63c` exists | Yes (Task 3 commit) |
| `migrate_to_sqlite.py` exists | Yes |
| `.gitignore` exists | Yes |
| `event_type="check_in"` in app.py | Yes |
| `event_type="check_out"` in app.py | Yes |
| No `load_attendance`/`save_attendance` callers | Yes |
| No `*_FILE` JSON-store constants | Yes |
| No `fcntl` in app.py | Yes |
| `tests/test_sqlite_migration.py` 3 passed | Yes |
| Full suite 34 passed + xfailed/xpassed | Yes |
| `.gitignore` contains `data/app.db` | Yes |
