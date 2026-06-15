---
phase: 06-sqlite-migration
reviewed: 2026-06-13T00:00:00Z
depth: deep
files_reviewed: 5
files_reviewed_list:
  - models.py
  - app.py
  - tests/conftest.py
  - migrate_to_sqlite.py
  - requirements.txt
findings:
  critical: 5
  warning: 7
  info: 4
  total: 16
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-06-13
**Depth:** deep
**Files Reviewed:** 5
**Status:** issues_found

## Summary

The Phase 06 SQLite migration replaces all JSON file I/O with SQLAlchemy ORM. The
structural approach is sound: `models.py` defines 9 clean ORM classes, `app.py` wires
`db.init_app(app)` correctly, and `migrate_to_sqlite.py` handles idempotency well for
most tables. However, several BLOCKER-level problems were found: a data isolation
(authorization) bypass in three read-only API endpoints that return all employees and
attendance records regardless of the caller's org/dept; a race condition in employee ID
and LBPH label generation; the migrate_to_sqlite `has_app_context()` branch silently
reconfigures the live database URI at runtime; tests cannot run without `SECRET_KEY`
being pre-set in the environment; and the `append_log` cap logic has a TOCTOU window
that can corrupt data integrity. Several warnings relate to unscoped queries that expose
cross-org data to lower-privilege roles.

---

## Critical Issues

### CR-01: Data isolation bypass — /api/attendance, /api/stats, /api/attendance/dates return all-org data

**File:** `app.py:1914-2016`
**Issue:** `get_attendance()` (line 1918) and `get_stats()` (line 1960) call
`Employee.query.all()` unconditionally, then return all employees and their attendance
records without filtering by the authenticated user's `org_id` or `dept_id`.
`get_dates()` (line 1949-1953) returns all distinct dates across all orgs.
An `org_admin` or `dept_admin` can therefore read attendance data for employees in
every other organization. The project's stated core value is "exactly the employees
they are authorized to see — no more, no less". These three endpoints violate that
invariant entirely.
**Fix:**
```python
# get_attendance — add scoped employee filter before building result
def get_attendance():
    day = request.args.get("date", date.today().isoformat())
    role = session.get("role")
    org_id = session.get("org_id")
    dept_id = session.get("dept_id")
    if role == "superadmin":
        emps = Employee.query.all()
    elif role == "org_admin" and org_id:
        emps = Employee.query.filter_by(org_id=org_id).all()
    elif role == "dept_admin" and dept_id:
        emps = Employee.query.filter_by(dept_id=dept_id).all()
    else:
        emps = []
    employees = {e.id: _emp_to_dict(e) for e in emps}
    # ... rest of function unchanged ...
```
Apply the same pattern to `get_stats()` and restrict `get_dates()` to dates that have
attendance records for scoped employees only.

---

### CR-02: Race condition in Employee ID and LBPH label generation

**File:** `app.py:675-676`, `app.py:1460-1461`
**Issue:** Employee IDs are generated as `str(int(time.time() * 1000))` (millisecond
timestamps) and LBPH labels are computed as `Employee.query.count() + 1`. Both have
race conditions under concurrent requests:
- Two simultaneous POST requests can obtain the same millisecond timestamp, producing a
  PRIMARY KEY collision (`IntegrityError`) that is silently swallowed by `except
  Exception: db.session.rollback()`, losing one of the registration attempts with no
  indication to the client beyond "Internal server error".
- `Employee.query.count()` is a snapshot; between the SELECT and the INSERT another
  thread can insert a row, creating a duplicate LBPH `label` value. The LBPH recognizer
  then maps two employees to the same integer ID, causing misidentification.
**Fix:**
```python
# Use UUID for emp_id — guaranteed unique without DB coordination
emp_id = str(uuid.uuid4())

# Use MAX(label)+1 with a database-level lock, or use autoincrement
# in a new integer surrogate PK and store the next-label in AppSetting.
# Simplest safe fix for LBPH label:
from sqlalchemy import func
max_label = db.session.execute(db.select(func.max(Employee.label))).scalar() or 0
label = max_label + 1
```
Both locations (line 675 in `register_token_submit` and line 1460 in `add_employee`)
must be fixed.

---

### CR-03: `append_log` TOCTOU — cap DELETE may leave >10,000 rows or delete wrong rows

**File:** `app.py:444-463`
**Issue:** The 10,000-row cap is implemented as a read-then-delete outside of a
transaction:
1. `db.session.add(log); db.session.commit()` — commits the new row.
2. `count = LogEntry.query.count()` — reads the count in a new query.
3. `oldest_ids = db.session.execute(...).scalars().all()` — reads IDs in yet another
   query.
4. `LogEntry.query.filter(LogEntry.id.in_(oldest_ids)).delete(...)` — deletes them.

Between steps 1 and 4, another concurrent `append_log` call can insert more rows and
read a stale count, causing both threads to independently try to delete the same or
overlapping sets of IDs. The result is either (a) more than 10,000 rows remaining, or
(b) deletion of rows that were not the oldest at the time of the second query.
Additionally, because the initial `commit()` already committed the insert before the
cap check, a subsequent exception anywhere in the DELETE block leaves the session in a
partially-clean state. A rollback at that point does not undo the already-committed
insert, so the row persists and the cap is never enforced.
**Fix:** Combine insert and cap enforcement in a single transaction:
```python
def append_log(entry):
    log = LogEntry(
        ts=entry.get("ts"),
        event=entry.get("event"),
        emp_id=entry.get("emp_id"),
        name=entry.get("name"),
        confidence_raw=entry.get("confidence_raw"),
        confidence_pct=entry.get("confidence_pct"),
    )
    db.session.add(log)
    # Single commit after both operations
    count = db.session.execute(db.select(func.count()).select_from(LogEntry)).scalar()
    if count >= 10000:
        excess = count - 10000 + 1  # +1 for the row we just added
        oldest_ids = db.session.execute(
            db.select(LogEntry.id).order_by(LogEntry.id.asc()).limit(excess)
        ).scalars().all()
        LogEntry.query.filter(LogEntry.id.in_(oldest_ids)).delete(synchronize_session=False)
    db.session.commit()
```
This keeps insert and delete in one transaction and avoids the post-commit count.

---

### CR-04: `migrate_to_sqlite` silently overwrites the live DATABASE_URI in a running app context

**File:** `migrate_to_sqlite.py:362-366`
**Issue:** When `run_migration()` is called while a Flask app context is already active
(the intended test path), and the passed `database_uri` differs from the context's
configured URI, the code does:
```python
current_app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
```
This mutates the live `SQLALCHEMY_DATABASE_URI` of the running Flask application for
the duration of the app context. In tests this is intentional — the test fixture sets
up `:memory:` and the migration target is also `:memory:`. But if production code ever
inadvertently calls `run_migration()` inside an active request context (e.g., via an
admin endpoint), the DB URI of the entire live app is silently redirected to whatever
URI was passed. There is no guard preventing this, and the change is permanent for the
lifetime of the process (Flask's config dict is not scoped to a single context push).
**Fix:** Raise an explicit error instead of silently reconfiguring the live app:
```python
if has_app_context():
    configured_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    if database_uri and configured_uri != database_uri:
        raise RuntimeError(
            f"run_migration() called inside an active app context whose "
            f"DB URI ({configured_uri!r}) differs from the requested "
            f"migration URI ({database_uri!r}). Pass database_uri=None "
            f"to reuse the active context's URI, or run outside an app context."
        )
    counts = _execute(db.session)
```

---

### CR-05: Tests will fail with `RuntimeError` when `SECRET_KEY` is not set before `import app`

**File:** `tests/conftest.py:42-55`, `app.py:13-18`
**Issue:** `app.py` lines 13–18 raise `RuntimeError("SECRET_KEY environment variable
must be set...")` at import time if `SECRET_KEY` is not present in the environment.
`conftest.py` imports `app` inside the `client` fixture body (line 42: `import app as
_app`) after the fixture has already started, but there is no code anywhere in the test
suite that sets `os.environ["SECRET_KEY"]` before the first import. The first call to
any function that imports `app` at module level (e.g., `from tests.conftest import
seed_users`) will trigger the import and immediately crash. This makes the entire test
suite non-runnable in a clean CI environment without a pre-set `SECRET_KEY`.
**Fix:** Set the environment variable before importing `app`, either in `conftest.py`
at module level or via `pytest.ini`'s `[pytest] env` plugin:
```python
# At the TOP of tests/conftest.py, before any import of app:
import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
```
Or use a `pytest-env` plugin entry in `pytest.ini`:
```ini
[pytest]
env =
    SECRET_KEY=test-secret-key-for-pytest-only
```

---

## Warnings

### WR-01: `get_employees()` falls through to `Employee.query.all()` for malformed sessions

**File:** `app.py:1431-1445`
**Issue:** The `else` branch (line 1444) returns all employees when neither `org_id`
nor `dept_id` is set in the session for an `org_admin` or `dept_admin`. An
`org_admin` whose `org_id` is `None` (e.g., a corrupted session or a bug in user
creation) will see all employees across all organizations.
**Fix:**
```python
else:
    return jsonify({"error": "forbidden"}), 403
```

---

### WR-02: `create_user` — `new_dept_id` from request body is never validated for `org_admin`

**File:** `app.py:1131`
**Issue:** When `creator_role == "org_admin"`, `new_dept_id = data.get("dept_id")` is
accepted from the request body without verifying that the referenced department belongs
to `caller_org_id`. An `org_admin` can create a user assigned to any department in any
organization by simply supplying a foreign `dept_id`.
**Fix:**
```python
if creator_role == "org_admin" and new_dept_id:
    target_dept = Department.query.get(new_dept_id)
    if not target_dept or target_dept.org_id != caller_org_id:
        return jsonify({"error": "forbidden"}), 403
```

---

### WR-03: `is_late` in `recognize()` uses hardcoded `"09:00:00"` ignoring employee schedule

**File:** `app.py:1844`
**Issue:** The kiosk response field `is_late` is computed as `now > "09:00:00"` regardless
of the employee's configured schedule start time. An employee with a schedule starting
at `14:00` checking in at `10:00` will be reported as late. The field is returned to
the kiosk display and is functionally incorrect for non-standard schedules.
**Fix:**
```python
emp_sched = EmployeeSchedule.query.filter_by(emp_id=emp_id).first()
sched_start = emp_sched.start_time if emp_sched else "09:00"
late_threshold = _time_threshold(sched_start, 15)
is_late = now > late_threshold
```

---

### WR-04: No foreign key constraints in models — orphaned rows accumulate silently

**File:** `models.py` (all models)
**Issue:** No SQLAlchemy `ForeignKey` references or `relationship` cascades are defined
between any of the 9 models. Deleting an employee leaves behind `AttendanceRecord`,
`TimesheetOverride`, and `LogEntry` rows referencing the deleted `emp_id`. These orphan
rows: (a) pollute timesheet grids with ghost employees after deletion; (b) cause
`_emp_to_dict` lookups to work only when the employee still exists; (c) allow
`att_records` to pile up unbounded for deleted employees.
The `delete_employee` route (line 1546) manually removes `EmployeeSchedule` but does
not touch `AttendanceRecord`, `TimesheetOverride`, or `LogEntry`.
**Fix:** Add `ForeignKey` columns and cascade deletes to the dependent models:
```python
from sqlalchemy import ForeignKey
class AttendanceRecord(db.Model):
    emp_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employee.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
```
Then set `PRAGMA foreign_keys = ON` for SQLite (via SQLAlchemy event listener).

---

### WR-05: `debug=True` in production `app.run()` — exposes interactive debugger

**File:** `app.py:2029`
**Issue:** `app.run(debug=True, ...)` enables the Werkzeug interactive debugger. If an
unhandled exception occurs in a production Flask process started via `python app.py`
(rather than gunicorn), the debugger is reachable from any client on port 5050. The
debugger allows arbitrary Python code execution via the browser PIN. This is a
critical security risk if the fallback `python app.py` path is ever used on the live
server.
**Fix:**
```python
if __name__ == "__main__":
    train_recognizer()
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, host="0.0.0.0", port=5050)
```

---

### WR-06: `list_users` — `dept_admin` sees all users, not just their own department

**File:** `app.py:1081-1098`
**Issue:** `list_users()` scopes results to `org_id` when `caller_role == "org_admin"`,
but falls through to `User.query.all()` for any other role including `dept_admin`. A
`dept_admin` therefore receives the list of all users in the system, including
credentials metadata (username, role, active status) for users in other organizations.
**Fix:**
```python
if caller_role == "org_admin":
    all_users = User.query.filter_by(org_id=caller_org_id).all()
elif caller_role == "dept_admin":
    caller_dept_id = session.get("dept_id")
    all_users = User.query.filter_by(dept_id=caller_dept_id).all()
else:  # superadmin
    all_users = User.query.all()
```

---

### WR-07: `append_log` called outside try/except in `recognize()` — DB error crashes unhandled

**File:** `app.py:1820`, `app.py:1871`
**Issue:** `append_log()` itself calls `db.session.commit()` internally. The two call
sites in `recognize()` (lines 1820 and 1871) are outside any try/except. If the
LogEntry commit fails (e.g., disk full, DB locked), the exception propagates up to
Flask's error handler and returns a 500 with no rollback of the attendance record
session (which was already committed on line 1865 before `append_log` is called — so
the record is safe, but the error response is confusing and the stack trace may leak
internal details to the caller).
**Fix:** Wrap `append_log` calls in a try/except that silently continues (logging is
non-critical and must not block attendance recording):
```python
try:
    append_log({...})
except Exception:
    pass  # logging failure must not block attendance recording
```

---

## Info

### IN-01: `LegacyAPIWarning` — `Query.get()` used throughout app.py

**File:** `app.py` (all `.query.get()` calls — approximately 30 occurrences)
**Issue:** SQLAlchemy 2.0 deprecates `Query.get()` in favor of `db.session.get()`.
The codebase uses the legacy form exclusively. While non-blocking now, this will become
an error in a future SQLAlchemy 3.x release and already generates console warnings
under 2.0.50.
**Fix:** Replace `Model.query.get(pk)` with `db.session.get(Model, pk)`:
```python
# Before
user = User.query.get(user_id)
# After
user = db.session.get(User, user_id)
```

---

### IN-02: `migration` prints database URI including path to stdout — leaks paths in logs

**File:** `migrate_to_sqlite.py:340-341`
**Issue:** `print(f"  Target URI: {database_uri!r}\n")` outputs the full SQLite path
(or DSN including credentials for non-SQLite URIs) to stdout. In deployments that
collect stdout into centralized logging, this leaks the database path on every
migration run.
**Fix:** Either suppress the URI output or truncate the path after the last `/`:
```python
safe_uri = database_uri.rsplit("/", 1)[-1] if "/" in database_uri else database_uri
print(f"  Target: {safe_uri!r}\n")
```

---

### IN-03: `_migrate_logs` idempotency check is O(N) per log entry

**File:** `migrate_to_sqlite.py:247-260`
**Issue:** For each of potentially 10,000 log entries, a separate SELECT is executed to
check for duplicates. On a large `logs.json` this issues 10,000 individual queries,
making migration very slow. The comment says "idempotent" but the chosen mechanism does
not scale.
**Fix:** Add a composite unique constraint to `LogEntry` on `(ts, event, emp_id)` in
`models.py` and use `on_conflict_do_nothing` in the migration, matching the pattern
used for all other tables:
```python
# In models.py
from sqlalchemy import UniqueConstraint
class LogEntry(db.Model):
    __table_args__ = (UniqueConstraint("ts", "event", "emp_id"),)
```

---

### IN-04: `requirements.txt` does not include existing runtime dependencies

**File:** `requirements.txt`
**Issue:** The file lists only the two new packages (`flask-sqlalchemy==3.1.1`,
`sqlalchemy==2.0.50`) but omits all other runtime dependencies (`flask`, `bcrypt`,
`opencv-contrib-python`, `numpy`, etc.). A fresh `pip install -r requirements.txt`
will not install enough packages to run the application, and there is no
`requirements-full.txt` or `pyproject.toml` to supplement it.
**Fix:** Either add a `requirements-full.txt` that includes all dependencies or append
the missing packages to `requirements.txt`. At minimum, document in a comment that
this file is a diff-only addendum:
```
# Phase 06 additions — append to your existing requirements
flask-sqlalchemy==3.1.1
sqlalchemy==2.0.50
```

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
