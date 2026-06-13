# Phase 6: SQLite Migration — Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace all JSON file I/O (7 data files + config.json) with SQLite + Flask-SQLAlchemy. Every `load_*/save_*` function is removed and replaced with direct `db.session` ORM calls across all ~82 functions in `app.py`. A `migrate_to_sqlite.py` script migrates existing data with zero data loss. No API route signatures change, no frontend templates change. All existing `test_*.py` tests pass against the SQLite backend; `conftest.py` is updated to use in-memory SQLite.

</domain>

<decisions>
## Implementation Decisions

### Schema — Attendance Data
- **D-01:** `attendance.json` normalizes into an `attendance_record` table with columns: `(id, emp_id, date, check_in_time, check_out_time, event_type)`. Primary key on `(emp_id, date, check_in_time)` or auto-increment `id`. Enables SQL-level late/absent detection already performed by the symbol engine.

### Schema — Employee Schedule
- **D-02:** `schedule` sub-dict on each employee moves to a separate `employee_schedule` table: `(id, emp_id, start_time, end_time, work_days_json)`. `work_days_json` stores the list of work days (e.g. `["Mon","Tue","Wed","Thu","Fri"]`) as a JSON TEXT column — queried as a whole unit, never by individual day in SQL.

### Schema — Logs
- **D-03:** `logs.json` normalizes into a `log_entry` table: `(id, ts, event, emp_id, name, confidence_raw, confidence_pct)`. INSERT per event replaces the load-array → append → save cycle. The 10,000-entry cap becomes `DELETE FROM log_entry WHERE id IN (SELECT id FROM log_entry ORDER BY ts ASC LIMIT N)` when count exceeds 10,000.

### Schema — Timesheet Overrides
- **D-04:** `timesheet_overrides.json` normalizes into a `timesheet_override` table: `(emp_id, date, symbol, updated_by, updated_at)`. Composite primary key on `(emp_id, date)`. `fcntl` advisory locking removed — SQLAlchemy transactions provide write safety.

### Schema — config.json
- **D-05:** `config.json` (legacy admin password hash, startup config) migrates into an `app_setting` table: `(key TEXT PRIMARY KEY, value TEXT)`. `migrate_to_sqlite.py` reads all keys from config.json and inserts them as rows. `config.json` file is deleted after migration.

### Schema — Remaining Flat Tables
- **D-06:** `employees.json`, `users.json`, `orgs.json`, `depts.json` all map to flat ORM model tables with individual scalar columns. Existing fields (including `label`, `face_count`, `org_token`, `kiosk_pin`, `reg_token`, `reg_pin`, `reg_token_expires`, `kiosk_display_name`) become proper typed columns. No JSON blobs for these tables.

### ORM Model Classes
- **D-07:** Full Flask-SQLAlchemy ORM with model classes: `Employee`, `User`, `Organization`, `Department`, `AttendanceRecord`, `EmployeeSchedule`, `LogEntry`, `TimesheetOverride`, `AppSetting`. All defined in a new `models.py` module (or at the top of `app.py` — researcher to decide placement).
- **D-08:** All `load_*/save_*` helper functions are removed entirely. Routes call `db.session` directly — no backward-compat wrappers. `fcntl` import removed.

### Transaction Boundaries
- **D-09:** Use Flask-SQLAlchemy's per-request app context: `db.session` is automatically scoped to the request; commit at end of write routes, rollback on exception. `@app.teardown_appcontext` handles session cleanup. No manual `db.session.remove()` calls in routes.

### Test Isolation
- **D-10:** "No modification to test code" means `test_*.py` files only. `conftest.py` IS updated to redirect the database to in-memory SQLite.
- **D-11:** Tests use `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"` injected via app config in the `client` fixture. Each test gets a fresh schema via `db.create_all()` / `db.drop_all()`.
- **D-12:** Seed fixture helpers in `conftest.py` (e.g., `write_users_fixture`, `write_orgs_fixture`) migrate from JSON file writes to `db.session.add()` calls. The `monkeypatch.setattr(_app, "EMPLOYEES_FILE", ...)` pattern is replaced with the new DB-URL override.

### Migration Script
- **D-13:** `migrate_to_sqlite.py` reads all 7 JSON files + config.json, creates `data/app.db` with all tables via `db.create_all()`, and inserts all records. Script is idempotent: checks for existing rows before INSERT (UPSERT or skip-if-exists). Print summary of records migrated per table.
- **D-14:** `data/faces/` directory (face photo files) is not touched by migration — remains as filesystem storage. The `label` integer field on Employee maps 1:1 to the LBPH recognizer label and must be preserved exactly.

### Concurrency
- **D-15:** SQLAlchemy connection pool handles concurrent access. `fcntl.flock` advisory locking on `save_users` and `save_timesheet_overrides` is removed. PM2 single-worker constraint documented but no longer enforced by locking code.

### Database Location
- **D-16:** `DATABASE_URL` environment variable configures the SQLite path; default: `sqlite:///data/app.db` (relative to app root). `app.db` is created automatically on first run via `db.create_all()` in app startup.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing codebase
- `app.py` — all Flask routes, JSON helpers, fcntl usage, business logic; every `load_*/save_*` call must be found and replaced
- `tests/conftest.py` — current fixture strategy (monkeypatch file paths, JSON seed helpers); must be rewritten for in-memory SQLite
- `tests/test_auth.py`, `tests/test_rbac.py`, `tests/test_org_dept.py`, `tests/test_migration.py`, `tests/test_kiosk_token.py`, `tests/test_migrate_tokens.py`, `tests/test_org_settings.py`, `tests/test_reg_token.py` — must pass without modification

### Data files (source for migration)
- `data/employees.json` — employee records including `label`, `face_count`, `org_id`, `dept_id`, `schedule`
- `data/users.json` — user accounts; roles: superadmin, org_admin, dept_admin only
- `data/orgs.json` — organizations with Phase 5 token fields (org_token, kiosk_pin, reg_token, reg_pin, reg_token_expires, kiosk_display_name)
- `data/depts.json` — departments linked to orgs
- `data/attendance.json` — nested attendance records by date and emp_id
- `data/logs.json` — event log array
- `data/timesheet_overrides.json` — manual symbol overrides keyed by emp_id+date
- `data/config.json` — legacy config (admin password hash, startup values)

### Planning artifacts
- `.planning/ROADMAP.md` — Phase 6 goal, success criteria, and requirements (DB-01 through DB-05)
- `.planning/phases/05-token-based-kiosk-registration-russian-ui/05-CONTEXT.md` — Phase 5 org data model decisions (org_token/kiosk_pin fields that must be preserved in the ORM model)
- `.planning/STATE.md` — fcntl locking decisions and PM2 single-worker constraint

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app.py` load/save helpers (lines ~38–234): Complete inventory of all JSON I/O — each function is a direct replacement target
- `app.py` fcntl usage: Two locations (`save_users` ~line 66–72, `save_timesheet_overrides` ~line 228–234) — both removed post-migration
- `tests/conftest.py` fixture pattern: `monkeypatch.setattr(_app, "USERS_FILE", ...)` × 7 path patches → replaced by single `SQLALCHEMY_DATABASE_URI` override

### Established Patterns
- JSON helpers follow `load_{entity}()` → `dict` / `save_{entity}(data)` → void pattern; all 8 helpers replaced
- Attendance state machine (check-in/check-out logic) reads attendance dict by `today` key → becomes `AttendanceRecord.query.filter_by(emp_id=..., date=today)` 
- `append_log()` function (~line 470–479): inline load-array + append + cap + save → becomes `db.session.add(LogEntry(...))` + count check

### Integration Points
- `db = SQLAlchemy(app)` initialization in `app.py` — new dependency, `flask-sqlalchemy` must be added to venv
- `app.config["SQLALCHEMY_DATABASE_URI"]` — configurable via `DATABASE_URL` env var with `sqlite:///data/app.db` default
- `db.create_all()` at startup (in `if __name__ == "__main__"` block or via `with app.app_context()`)
- conftest.py `client` fixture overrides `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"` and calls `db.create_all()` in setup, `db.drop_all()` in teardown

</code_context>

<specifics>
## Specific Ideas

- The `label` integer field on Employee is the LBPH recognizer's internal employee ID and must map to the same integer value post-migration. The migration script must preserve it exactly (not auto-generate a new PK).
- `migrate_to_sqlite.py` should print a per-table summary: "Migrated N employees, M users, K organizations..." for operator confidence.
- `app.db` path should be configurable via `DATABASE_URL` env var for test overrides (tests inject `sqlite:///:memory:`).
- Face images in `data/faces/{emp_id}/` stay on the filesystem; no DB storage of binary image data.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-sqlite-migration*
*Context gathered: 2026-06-13*
