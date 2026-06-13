# Phase 6: SQLite Migration — Research

**Researched:** 2026-06-13
**Domain:** Flask-SQLAlchemy ORM, SQLite, JSON-to-DB migration, pytest test isolation
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `attendance.json` normalizes into an `attendance_record` table: `(id, emp_id, date, check_in_time, check_out_time, event_type)`. Primary key auto-increment `id`.
- **D-02:** `schedule` sub-dict moves to a separate `employee_schedule` table: `(id, emp_id, start_time, end_time, work_days_json)`. `work_days_json` is a TEXT column — never queried by individual day in SQL.
- **D-03:** `logs.json` becomes `log_entry` table: `(id, ts, event, emp_id, name, confidence_raw, confidence_pct)`. INSERT per event; log-cap via DELETE.
- **D-04:** `timesheet_overrides.json` becomes `timesheet_override` table: `(emp_id, date, symbol, updated_by, updated_at)`. Composite PK on `(emp_id, date)`.
- **D-05:** `config.json` becomes `app_setting` table: `(key TEXT PRIMARY KEY, value TEXT)`.
- **D-06:** `employees.json`, `users.json`, `orgs.json`, `depts.json` map to flat ORM model tables with individual scalar columns. No JSON blobs for these tables.
- **D-07:** Full Flask-SQLAlchemy ORM with model classes: `Employee`, `User`, `Organization`, `Department`, `AttendanceRecord`, `EmployeeSchedule`, `LogEntry`, `TimesheetOverride`, `AppSetting`. All defined in a new `models.py` module (or at the top of `app.py` — researcher to decide: use `models.py` module).
- **D-08:** All `load_*/save_*` helper functions removed entirely. Routes call `db.session` directly. `fcntl` import removed.
- **D-09:** Flask-SQLAlchemy per-request app context: `db.session` scoped to request; commit at end of write routes; rollback on exception. `@app.teardown_appcontext` handles cleanup.
- **D-10:** "No modification to test code" means `test_*.py` files only. `conftest.py` IS updated.
- **D-11:** Tests use `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"` injected via app config in the `client` fixture. Each test gets a fresh schema via `db.create_all()` / `db.drop_all()`.
- **D-12:** Seed fixture helpers in `conftest.py` migrate from JSON file writes to `db.session.add()` calls.
- **D-13:** `migrate_to_sqlite.py` reads all 7 JSON files + config.json, creates `data/app.db` via `db.create_all()`, inserts all records. Idempotent (UPSERT or skip-if-exists). Prints per-table summary.
- **D-14:** `data/faces/` directory stays on filesystem. `label` integer on Employee maps 1:1 to LBPH recognizer label — must be preserved exactly (not auto-generated).
- **D-15:** SQLAlchemy connection pool handles concurrent access. `fcntl.flock` advisory locking on `save_users` and `save_timesheet_overrides` is removed.
- **D-16:** `DATABASE_URL` env var configures SQLite path; default: `sqlite:///data/app.db`. `app.db` created automatically on first run via `db.create_all()` in app startup.

### Claude's Discretion

None noted — all decisions locked.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DB-01 | All `load_*/save_*` functions replaced with SQLAlchemy ORM calls; no JSON file I/O remains in `app.py` | 116 call sites across 8 load/save functions identified. ORM model patterns documented. |
| DB-02 | `migrate_to_sqlite.py` reads JSON files, inserts all records with zero data loss; script is idempotent | UPSERT via `on_conflict_do_nothing()` pattern documented. All source schemas confirmed. |
| DB-03 | All existing pytest tests pass against SQLite backend without modification to test code | `conftest.py` rewrite pattern documented. In-memory SQLite test isolation confirmed. |
| DB-04 | Concurrent writes handled by SQLAlchemy transactions; `fcntl` locking code removed | Two `fcntl.flock` sites in `save_users` (line 70) and `save_timesheet_overrides` (line 232). |
| DB-05 | `app.db` created automatically on first run; `SECRET_KEY` and `DATABASE_URL` are only required env vars | `db.create_all()` in startup path pattern confirmed. |
</phase_requirements>

---

## Summary

This phase replaces all JSON file I/O in `app.py` (8 load/save functions with 116 call sites) with Flask-SQLAlchemy 3.1.1 ORM backed by SQLite. The migration has two parts: (1) rewriting `app.py` to define ORM models and replace every `load_*/save_*` call with `db.session` operations, and (2) writing a one-shot `migrate_to_sqlite.py` script that reads existing JSON files and inserts their contents into `app.db`.

The test isolation challenge is the most technically subtle piece: the current `conftest.py` monkeypatches 7 module-level path constants. The new `conftest.py` must instead override `SQLALCHEMY_DATABASE_URI` to `"sqlite:///:memory:"` and replace all `seed_*` file-write helpers with `db.session.add()` calls — all within a proper app context. The `test_*.py` files themselves are not modified.

The `require_role()` decorator currently calls `load_users()` on every protected request. Post-migration, this becomes `User.query.get(user_id)`, which is a single indexed lookup — no semantic change.

**Primary recommendation:** Define all models in a new `models.py` module (not inline in `app.py`) to keep the 1,877-line `app.py` manageable. Import `db` and model classes into `app.py` at the top.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ORM model definitions | Backend / `models.py` | — | Models are pure Python classes; no UI or routing concern |
| DB session management | Backend / `app.py` | Flask teardown context | Per-request session scoping is Flask's concern |
| Schema creation at startup | Backend / `app.py` startup | — | `db.create_all()` runs in app startup path |
| Data migration | Standalone script / `migrate_to_sqlite.py` | — | One-shot; runs outside Flask request context |
| Test isolation | `tests/conftest.py` | In-memory SQLite | Fixture layer redirects DB URI, not file paths |
| Face image storage | Filesystem (`data/faces/`) | — | Binary blobs excluded from DB — no change needed |
| Concurrent write safety | SQLAlchemy session | — | Replaces `fcntl.flock`; handled by DBAPI transaction |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| flask-sqlalchemy | 3.1.1 | ORM integration with Flask app context | Official Flask extension; per-request session scoping built-in |
| sqlalchemy | 2.0.50 | ORM models, query API, UPSERT dialect | Core ORM; Flask-SQLAlchemy 3.x requires SA 2.0 |

**Version verification:**
```bash
# Confirmed via pip index versions (run 2026-06-13)
flask-sqlalchemy: 3.1.1  (latest)
sqlalchemy:       2.0.50 (latest patch on 2.0 series)
```

[VERIFIED: pip index versions, confirmed 2026-06-13]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | already installed | Test runner | No change needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flask-SQLAlchemy | Raw SQLAlchemy + `scoped_session` | More control but requires manual session/teardown wiring; Flask-SQLAlchemy handles this automatically |
| `db.create_all()` | Alembic migrations | Alembic is correct for evolving schemas; `create_all()` is acceptable here because this is a one-time greenfield schema |

**Installation:**
```bash
/var/www/sites/face-almgp33/venv/bin/pip install flask-sqlalchemy==3.1.1
```

## Package Legitimacy Audit

> The legitimacy seam returned SUS verdicts for both packages due to missing PyPI download-count data in its metadata source — not due to actual suspicion. Both packages are canonical, decade-old projects with authoritative documentation.

| Package | Registry | Age | Downloads | Source Repo | Verdict (seam) | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| flask-sqlalchemy | PyPI | 13 yrs | N/A (seam gap) | flask-sqlalchemy.palletsprojects.com | SUS (false positive — PyPI data gap) | Approved — official Pallets project, documented at flask-sqlalchemy.palletsprojects.com [CITED: flask-sqlalchemy.palletsprojects.com/en/3.1.x/] |
| sqlalchemy | PyPI | 20 yrs | N/A (seam gap) | sqlalchemy.org | SUS (false positive — seam sees recent patch as "too-new") | Approved — canonical Python ORM, documented at docs.sqlalchemy.org [CITED: docs.sqlalchemy.org/en/20/] |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious SUS:** both flagged by seam are false positives — both are official, well-documented libraries from canonical sources. No human checkpoint required.

## Architecture Patterns

### System Architecture Diagram

```
                    Flask Request
                         |
                    require_role()
                         |
                    db.session (request-scoped)
                    /     |      \
               User.query  Employee.query  AttendanceRecord.query  ...
                    \     |      /
                    SQLAlchemy ORM
                         |
                    SQLite (data/app.db)
                         |
                    [filesystem: data/faces/{emp_id}/*.jpg]  (unchanged)

                    Test Path:
                    conftest.py client fixture
                         |
                    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
                         |
                    db.create_all() → fresh schema per test
                    db.session.add(Model(...)) → seed data
                         |
                    test_*.py assertions (files unchanged)
```

### Recommended Project Structure

```
app.py                     # routes, startup — imports from models.py
models.py                  # db, all ORM model classes (NEW)
migrate_to_sqlite.py       # one-shot JSON→SQLite migration script (NEW)
migrate.py                 # existing Phase 2/5 migrate — kept as-is, not touched
tests/
  conftest.py              # rewritten: DB URI override, db.session.add() seed helpers
  test_*.py                # NOT modified
data/
  app.db                   # created on first run (gitignored)
  faces/                   # unchanged filesystem storage
  *.json                   # kept until migration script runs; then archived
```

### Pattern 1: ORM Model Definition (models.py)

**What:** All 9 model classes in a single `models.py` module. `db` object is created here and imported into `app.py`.
**When to use:** Always — do not inline models in `app.py` given its 1,877-line size.

```python
# Source: flask-sqlalchemy.palletsprojects.com/en/3.1.x/quickstart/
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, Boolean, DateTime, Date
from typing import Optional
import json

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(db.Model):
    __tablename__ = "user"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    dept_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

class Employee(db.Model):
    __tablename__ = "employee"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="employee")
    # label MUST NOT autoincrement — preserves LBPH recognizer label (D-14)
    label: Mapped[int] = mapped_column(Integer, nullable=False, autoincrement=False)
    face_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registered_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    dept_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

class EmployeeSchedule(db.Model):
    __tablename__ = "employee_schedule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    emp_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False, default="09:00")
    end_time: Mapped[str] = mapped_column(String(5), nullable=False, default="18:00")
    work_days_json: Mapped[str] = mapped_column(Text, nullable=False, default="[1,2,3,4,5]")

class Organization(db.Model):
    __tablename__ = "organization"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    kiosk_pin: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    org_token: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, unique=True)
    reg_token: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, unique=True)
    reg_pin: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reg_token_expires: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    kiosk_display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

class Department(db.Model):
    __tablename__ = "department"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    head_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

class AttendanceRecord(db.Model):
    __tablename__ = "attendance_record"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    emp_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    check_in_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    check_out_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

class LogEntry(db.Model):
    __tablename__ = "log_entry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[str] = mapped_column(String(32), nullable=False)
    event: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    emp_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    confidence_raw: Mapped[Optional[float]] = mapped_column(nullable=True)
    confidence_pct: Mapped[Optional[float]] = mapped_column(nullable=True)

class TimesheetOverride(db.Model):
    __tablename__ = "timesheet_override"
    emp_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(4), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    updated_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

class AppSetting(db.Model):
    __tablename__ = "app_setting"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

### Pattern 2: App Initialization (app.py)

**What:** Import `db` from `models.py`, configure URI, init with factory pattern, create tables at startup.

```python
# Source: flask-sqlalchemy.palletsprojects.com/en/3.1.x/quickstart/
from models import db, Employee, User, Organization, Department
from models import AttendanceRecord, EmployeeSchedule, LogEntry, TimesheetOverride, AppSetting

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///data/app.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Create tables at startup (first run or existing DB — idempotent)
with app.app_context():
    db.create_all()
    init_users()  # now inserts via db.session instead of writing JSON
```

### Pattern 3: Replacing load_*/save_* With ORM Calls

**What:** Each `load_X()` → `X.query.all()` or `X.query.get(id)` or `X.query.filter_by()`. Each `save_X(data)` → `db.session.add(obj); db.session.commit()`.

**Common patterns:**

```python
# BEFORE: load_employees() -> dict
employees = load_employees()  # returns {emp_id: {...}}
emp = employees.get(emp_id)

# AFTER: ORM query
emp = Employee.query.get(emp_id)
# or as dict-like (to minimize route changes):
employees = {e.id: e for e in Employee.query.all()}

# BEFORE: save_employees(employees)
employees[emp_id] = {...}
save_employees(employees)

# AFTER: ORM insert/update
emp = Employee(id=emp_id, name=name, ...)
db.session.add(emp)
db.session.commit()
# or update:
emp = Employee.query.get(emp_id)
emp.name = new_name
db.session.commit()
```

**Attendance (nested dict → flat table):**

```python
# BEFORE
attendance = load_attendance()
if today not in attendance:
    attendance[today] = {}
attendance[today][emp_id] = {"check_in": now, "check_out": None}
save_attendance(attendance)

# AFTER
rec = AttendanceRecord.query.filter_by(emp_id=emp_id, date=today).first()
if rec is None:
    rec = AttendanceRecord(emp_id=emp_id, date=today, check_in_time=now)
    db.session.add(rec)
elif rec.check_out_time is None:
    rec.check_out_time = now
db.session.commit()
```

**EmployeeSchedule join pattern (replaces emp["schedule"] dict access):**

```python
# BEFORE
schedule = emp.get("schedule", {"start": "09:00", "end": "18:00", "work_days": [1,2,3,4,5]})

# AFTER
sched = EmployeeSchedule.query.filter_by(emp_id=emp_id).first()
if sched:
    schedule = {
        "start": sched.start_time,
        "end": sched.end_time,
        "work_days": json.loads(sched.work_days_json)
    }
else:
    schedule = {"start": "09:00", "end": "18:00", "work_days": [1,2,3,4,5]}
```

**append_log() replacement:**

```python
# BEFORE
def append_log(entry):
    logs = ...json load...
    logs.append(entry)
    if len(logs) > 10000:
        logs = logs[-10000:]
    ...json save...

# AFTER (D-03)
def append_log(entry):
    log = LogEntry(
        ts=entry.get("ts"), event=entry.get("event"),
        emp_id=entry.get("emp_id"), name=entry.get("name"),
        confidence_raw=entry.get("confidence_raw"),
        confidence_pct=entry.get("confidence_pct")
    )
    db.session.add(log)
    db.session.commit()
    # Cap at 10,000: delete oldest when over limit
    count = LogEntry.query.count()
    if count > 10000:
        excess = count - 10000
        oldest_ids = db.session.execute(
            db.select(LogEntry.id).order_by(LogEntry.id.asc()).limit(excess)
        ).scalars().all()
        LogEntry.query.filter(LogEntry.id.in_(oldest_ids)).delete(synchronize_session=False)
        db.session.commit()
```

**require_role() replacement:**

```python
# BEFORE: loads all users as dict
users = load_users()
user = users.get(user_id)

# AFTER: direct PK lookup
user = User.query.get(user_id)
```

### Pattern 4: conftest.py Test Isolation

**What:** Replace 7 monkeypatched file constants with a single DB URI override. Replace file-write seed helpers with `db.session.add()` calls inside `app.app_context()`.

```python
# Source: flask-sqlalchemy.palletsprojects.com/en/3.1.x/ + websearch
@pytest.fixture()
def client(monkeypatch):
    import app as _app
    from models import db

    # Override DB URI BEFORE init_app runs (or re-configure)
    _app.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    _app.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    _app.app.testing = True
    _app.app.secret_key = "test-secret-key-for-pytest"

    with _app.app.app_context():
        db.create_all()
        yield _app.app.test_client()
        db.session.remove()
        db.drop_all()


def seed_users(users_dict):
    """Seed users via db.session instead of writing users.json."""
    from models import db, User
    for uid, u in users_dict.items():
        user = User(
            id=u["id"], username=u["username"],
            password_hash=u["password_hash"], role=u["role"],
            active=u["active"], org_id=u.get("org_id"),
            dept_id=u.get("dept_id")
        )
        db.session.add(user)
    db.session.commit()
```

**Critical change:** The `tmp_data` fixture is no longer needed (no file paths to redirect). The `client` fixture absorbs its responsibility. Old seed helpers that took `tmp_data` as first arg have their signature simplified.

### Pattern 5: Idempotent Migration Script

**What:** `migrate_to_sqlite.py` reads all JSON files and inserts records using `ON CONFLICT DO NOTHING` (skip-if-exists). Safe to run multiple times.

```python
# Source: docs.sqlalchemy.org/en/20/ SQLite dialect + training knowledge
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

def migrate_employees(employees_dict):
    for emp_id, emp in employees_dict.items():
        stmt = sqlite_insert(Employee).values(
            id=emp["id"], name=emp["name"], ...
        ).on_conflict_do_nothing(index_elements=["id"])
        db.session.execute(stmt)
        # migrate schedule separately
        sched = emp.get("schedule", DEFAULT_SCHEDULE)
        sched_stmt = sqlite_insert(EmployeeSchedule).values(
            emp_id=emp["id"],
            start_time=sched.get("start", "09:00"),
            end_time=sched.get("end", "18:00"),
            work_days_json=json.dumps(sched.get("work_days", [1,2,3,4,5]))
        ).on_conflict_do_nothing(index_elements=["emp_id"])
        db.session.execute(sched_stmt)
    db.session.commit()
```

### Anti-Patterns to Avoid

- **Loading full tables into dicts for every request:** The current pattern `employees = load_employees()` (returns all ~N employees) is frequently called in routes. Post-migration, use `Employee.query.filter_by(org_id=org_id)` to scope queries rather than loading all and filtering in Python — but this is an optimization; for correctness in Phase 6, loading all and filtering is acceptable to preserve existing logic with minimal change.
- **Using `db.create_all()` inside a route:** Only call once at startup within `app.app_context()`.
- **Calling `db.session.commit()` in the middle of multi-step operations:** Commit at the end of a complete operation unit; partial commits leave data in inconsistent states.
- **Storing `db.session` objects across requests:** Each request gets its own session; do not cache ORM objects at module level.
- **Re-importing `app.py` during tests without resetting the DB:** Always use `db.drop_all(); db.create_all()` in each test fixture.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQLite concurrent write safety | `fcntl.flock` wrappers | SQLAlchemy session transactions | WAL mode + SQLite's built-in serialization handles single-writer correctly |
| Idempotent insert | `if exists: skip` logic | `INSERT OR IGNORE` / `on_conflict_do_nothing()` | SQLite dialect handles this atomically |
| Per-request session cleanup | Manual `db.session.remove()` | Flask-SQLAlchemy `@teardown_appcontext` | Built-in teardown handles session scoping automatically |
| Table creation | Manual `CREATE TABLE` SQL | `db.create_all()` | Derives schema from model class definitions |
| Test DB reset | `os.unlink(db_file)` | `db.drop_all(); db.create_all()` | Works with in-memory SQLite; file deletion would fail on `:memory:` |

**Key insight:** Flask-SQLAlchemy's session management is the core value-add over raw SQLite. Do not bypass it.

## Common Pitfalls

### Pitfall 1: `db.create_all()` Called Outside App Context
**What goes wrong:** `RuntimeError: No application found.`
**Why it happens:** SQLAlchemy needs Flask's app context to read `SQLALCHEMY_DATABASE_URI`.
**How to avoid:** Always wrap in `with app.app_context(): db.create_all()`.
**Warning signs:** Error at import time; error when running `migrate_to_sqlite.py` as standalone script.

### Pitfall 2: `init_users()` Called Before `db.create_all()`
**What goes wrong:** `OperationalError: no such table: user`
**Why it happens:** `init_users()` now inserts into the `user` table, which must exist first.
**How to avoid:** Call `db.create_all()` before `init_users()` in the startup block. In `app.py`:
```python
with app.app_context():
    db.create_all()
    init_users()
```
**Warning signs:** Server crashes on first run with a new `app.db`.

### Pitfall 3: `Employee.label` Gets Auto-Incremented
**What goes wrong:** LBPH recognizer cannot match employees after migration; face recognition returns wrong person or "unknown".
**Why it happens:** SQLAlchemy defaults Integer PKs to autoincrement; if `label` is treated as a PK or an Integer column without `autoincrement=False`, it may be overwritten.
**How to avoid:** `label` is NOT the primary key — `id` is. Set `label` as a plain `Integer` column with `autoincrement=False` explicitly. Migration script copies `label` value verbatim from JSON.
**Warning signs:** Face recognition breaks immediately after migration even for existing employees.

### Pitfall 4: Attendance JSON Nested Dict → Flat Table Query Shape Mismatch
**What goes wrong:** Code that does `attendance[today][emp_id]` fails with AttributeError or KeyError.
**Why it happens:** Old `load_attendance()` returned `{date: {emp_id: {check_in, check_out}}}`. New code returns `AttendanceRecord` objects.
**How to avoid:** Build a compatibility dict in routes that need the full attendance view:
```python
records = AttendanceRecord.query.filter_by(date=today).all()
day_attendance = {r.emp_id: {"check_in": r.check_in_time, "check_out": r.check_out_time} for r in records}
```
Or rewrite the logic directly in terms of ORM queries.
**Warning signs:** `compute_timesheet_grid` and `compute_symbol` receive wrong input shapes.

### Pitfall 5: `compute_symbol` Still Takes Dict-Shaped Attendance
**What goes wrong:** `compute_symbol(day_date, emp_id, attendance, overrides, schedule, holidays_set)` signature expects `attendance` as `{date_str: {emp_id: {check_in, check_out}}}`.
**Why it happens:** `compute_symbol` and `compute_timesheet_grid` are pure-Python functions that operate on dicts — they are NOT rewritten in this phase.
**How to avoid:** Before calling `compute_timesheet_grid()`, load attendance data from ORM and reconstruct the dict format the function expects. This is intentional — it preserves the timesheet logic untouched.
**Warning signs:** T-13 grid shows НН for all days even when attendance records exist.

### Pitfall 6: `seed_*` Helper Signature Change Breaks conftest Callers
**What goes wrong:** `seed_users(tmp_data, users_dict)` signature takes `tmp_data` first; after migration `tmp_data` does not exist.
**Why it happens:** Old helpers wrote to `tmp_data / "data" / "users.json"`; new helpers call `db.session.add()`.
**How to avoid:** Remove `tmp_data` parameter from all seed helpers. Check if any `test_*.py` calls seed helpers directly — they do (e.g., `test_auth.py` calls `seed_users(tmp_data, {...})`). Since `test_*.py` files cannot be modified (D-10), the seed helpers must be called via conftest in a way that matches the existing call signature. **This is a hard constraint:** `seed_users(tmp_data, users_dict)` in `test_auth.py` must still work. Solution: keep `tmp_data` as first positional arg to all seed helpers but ignore it internally (accept and discard it).
**Warning signs:** `TypeError: seed_users() takes 1 positional argument but 2 were given`.

### Pitfall 7: `timesheet_overrides.json` Has No Existing File
**What goes wrong:** Migration script calls `json.load()` on a file that doesn't exist.
**Why it happens:** `data/timesheet_overrides.json` was confirmed absent from `data/` directory.
**How to avoid:** Migration script uses `_load_json(path)` helper that returns `{}` if file is absent — already the pattern in existing `migrate.py`.
**Warning signs:** `FileNotFoundError` during migration run.

### Pitfall 8: `app.db` Written Relative to Flask Instance Path, Not `data/`
**What goes wrong:** Database file created at wrong location.
**Why it happens:** Flask-SQLAlchemy interprets relative `sqlite:///` URIs relative to the Flask instance path (`app.instance_path`), not the working directory. `sqlite:///data/app.db` becomes `<instance_path>/data/app.db`.
**How to avoid:** Use an absolute path in the default: `"sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "app.db")`. Or set `app.instance_path` explicitly.
**Warning signs:** `app.db` appears in the wrong directory; tests cannot find it.

### Pitfall 9: `conftest.py` Uses `tmp_data` Fixture But Seed Helpers Now Need App Context
**What goes wrong:** `db.session.add()` called outside app context raises `RuntimeError`.
**Why it happens:** `db.session` requires Flask app context; `pytest` doesn't set this up automatically.
**How to avoid:** All `db.session` calls inside seed helpers must happen within the `client` fixture's app context. Either call seed helpers from within `with app.app_context():` block, or make seed helpers use `db.session` that is already active from the `client` fixture.
**Warning signs:** `RuntimeError: No application found` or `RuntimeError: Working outside of application context`.

## Code Examples

### Startup Sequence (app.py)

```python
# Source: flask-sqlalchemy.palletsprojects.com/en/3.1.x/quickstart/
from models import db, User, Employee  # ... all models

app = Flask(__name__)
_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    raise RuntimeError("SECRET_KEY environment variable must be set")
app.secret_key = _secret_key

_db_url = os.environ.get("DATABASE_URL") or (
    "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "app.db")
)
app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    init_users()  # inserts superadmin row if user table is empty
```

### Migration Script Skeleton (migrate_to_sqlite.py)

```python
# [ASSUMED] — pattern based on training knowledge + SQLAlchemy docs
#!/usr/bin/env python3
"""migrate_to_sqlite.py — One-shot JSON → SQLite migration. Idempotent."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, Employee, User, Organization, Department
from models import AttendanceRecord, EmployeeSchedule, LogEntry, TimesheetOverride, AppSetting
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def _load(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}

def run_migration():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(DATA_DIR, "app.db")
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

        # Example: migrate employees with ON CONFLICT DO NOTHING
        employees = _load("employees.json")
        count = 0
        for emp_id, emp in employees.items():
            stmt = sqlite_insert(Employee).values(
                id=emp["id"], name=emp["name"], role=emp.get("role","employee"),
                label=int(emp["label"]), face_count=int(emp.get("face_count", 0)),
                registered_at=emp.get("registered_at"),
                org_id=emp.get("org_id"), dept_id=emp.get("dept_id"),
            ).on_conflict_do_nothing(index_elements=["id"])
            db.session.execute(stmt)
            sched = emp.get("schedule", {"start":"09:00","end":"18:00","work_days":[1,2,3,4,5]})
            sched_stmt = sqlite_insert(EmployeeSchedule).values(
                emp_id=emp["id"],
                start_time=sched.get("start","09:00"),
                end_time=sched.get("end","18:00"),
                work_days_json=json.dumps(sched.get("work_days",[1,2,3,4,5]))
            ).on_conflict_do_nothing(index_elements=["emp_id"])
            db.session.execute(sched_stmt)
            count += 1
        db.session.commit()
        print(f"Migrated {count} employees")
        # ... repeat for users, orgs, depts, attendance, logs, overrides, config

if __name__ == "__main__":
    run_migration()
```

### conftest.py Pattern After Migration

```python
# Source: websearch + flask-sqlalchemy docs — LOW confidence, verify against actual behavior
import pytest

BCRYPT_HASH_SUPERADMIN = "$2b$12$aiT81qA2zjbyxSpMPdXu0euetZyQU6/htQjDW9gcJPTir35bqv8Ry"

@pytest.fixture()
def tmp_data(tmp_path):
    """Kept as a stub so test_*.py calls like 'seed_users(tmp_data, ...)' keep working.
    No longer monkeypatches file paths — returns tmp_path for signature compatibility.
    """
    return tmp_path


@pytest.fixture()
def client(tmp_data):
    import app as _app
    from models import db

    _app.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    _app.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    _app.app.testing = True
    _app.app.secret_key = "test-secret-key-for-pytest"

    with _app.app.app_context():
        db.create_all()
        with _app.app.test_client() as test_client:
            yield test_client
        db.session.remove()
        db.drop_all()


def seed_users(tmp_data, users_dict):
    """tmp_data accepted but ignored — kept for test_*.py call-site compatibility."""
    import app as _app
    from models import db, User
    with _app.app.app_context():
        for uid, u in users_dict.items():
            existing = User.query.get(u["id"])
            if not existing:
                db.session.add(User(
                    id=u["id"], username=u["username"],
                    password_hash=u["password_hash"], role=u["role"],
                    active=u.get("active", True),
                    org_id=u.get("org_id"), dept_id=u.get("dept_id"),
                ))
        db.session.commit()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `fcntl.flock` for file write safety | SQLAlchemy transactions + WAL | Phase 6 | `fcntl` import removed |
| 7 JSON file path constants | Single `DATABASE_URL` env var | Phase 6 | Simpler environment setup |
| `monkeypatch.setattr(_app, "USERS_FILE", ...)` × 7 | Single `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"` | Phase 6 (conftest rewrite) | Dramatically simpler test setup |

**Deprecated/outdated after this phase:**
- `load_config()`, `save_config()`, `init_config()`: replaced by `AppSetting` ORM queries
- `load_users()`, `save_users()`, `init_users()`: replaced by `User.query`
- `load_employees()`, `save_employees()`: replaced by `Employee.query`
- `load_orgs()`, `save_orgs()`: replaced by `Organization.query`
- `load_depts()`, `save_depts()`: replaced by `Department.query`
- `load_attendance()`, `save_attendance()`: replaced by `AttendanceRecord.query`
- `load_timesheet_overrides()`, `save_timesheet_overrides()`: replaced by `TimesheetOverride.query`
- `append_log()`: replaced by `db.session.add(LogEntry(...))`
- `fcntl` import: removed entirely

## Scope Inventory

### Load/Save Call Site Count (from codebase grep, 2026-06-13)

| Function | Definition Lines | Call Sites | Replacement |
|----------|-----------------|------------|-------------|
| `load_employees()` / `save_employees()` | 127–135 | 32 | `Employee.query.*` |
| `load_users()` / `save_users()` | 56–78 | 20 | `User.query.*` |
| `load_orgs()` / `save_orgs()` | 149–166 | 20 | `Organization.query.*` |
| `load_depts()` / `save_depts()` | 168–185 | 17 | `Department.query.*` |
| `load_attendance()` / `save_attendance()` | 137–145 | 12 | `AttendanceRecord.query.*` |
| `load_config()` / `save_config()` | 38–46 | 5 | `AppSetting.query.*` |
| `load_timesheet_overrides()` / `save_timesheet_overrides()` | 217–240 | 7 | `TimesheetOverride.query.*` |
| `append_log()` | 468–480 | 3 | `db.session.add(LogEntry(...))` |
| **Total** | | **116** | |

### fcntl.flock Sites

| Line | Function | Action |
|------|----------|--------|
| 70 | `save_users()` | Remove with function |
| 232 | `save_timesheet_overrides()` | Remove with function |

### Existing JSON Files (migration source)

| File | Structure | Target Table |
|------|-----------|--------------|
| `data/employees.json` | `{emp_id: {id, name, role, label, face_count, registered_at, org_id, dept_id, schedule}}` | `employee` + `employee_schedule` |
| `data/users.json` | `{user_id: {id, username, password_hash, role, active, org_id, dept_id}}` | `user` |
| `data/orgs.json` | `{org_id: {id, name, description, created_at, kiosk_pin, org_token, reg_token, reg_pin, reg_token_expires, kiosk_display_name}}` | `organization` |
| `data/depts.json` | `{dept_id: {id, org_id, name, head_name, created_at}}` | `department` |
| `data/attendance.json` | `{date: {emp_id: {check_in, check_out}}}` | `attendance_record` |
| `data/logs.json` | `[{ts, event, confidence_raw, confidence_pct, ...}]` | `log_entry` |
| `data/timesheet_overrides.json` | NOT FOUND (file absent) | `timesheet_override` (migrate as empty) |
| `data/config.json` | `{username, password_hash}` | `app_setting` |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (installed in venv) |
| Config file | none detected — discovery by convention |
| Quick run command | `SECRET_KEY=test /var/www/sites/face-almgp33/venv/bin/python -m pytest tests/ -q --tb=short` |
| Full suite command | `SECRET_KEY=test /var/www/sites/face-almgp33/venv/bin/python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01 | All load/save functions replaced; no JSON I/O in app.py | Integration | `pytest tests/ -q` (all existing tests cover routes that use these functions) | Existing tests |
| DB-02 | `migrate_to_sqlite.py` is idempotent; zero data loss | Unit (new) | `pytest tests/test_sqlite_migration.py` | No — Wave 0 gap |
| DB-03 | All existing tests pass without modification | Integration | `pytest tests/test_auth.py tests/test_rbac.py tests/test_org_dept.py tests/test_timesheet.py tests/test_kiosk_token.py tests/test_migrate_tokens.py tests/test_org_settings.py tests/test_reg_token.py -v` | Yes (all existing) |
| DB-04 | fcntl removed; concurrent writes via SQLAlchemy | Static check | `grep -n "fcntl" app.py` (must return empty) | N/A — grep |
| DB-05 | app.db created on first run; only SECRET_KEY + DATABASE_URL required | Smoke | Fresh run with only those env vars set | Manual |

### Sampling Rate

- **Per task commit:** `SECRET_KEY=test /var/www/sites/face-almgp33/venv/bin/python -m pytest tests/ -q --tb=short`
- **Per wave merge:** Full suite + grep for `fcntl` and `load_employees` in `app.py`
- **Phase gate:** All 60+ tests green (currently 31 passed + 4 xfailed + 25 xpassed = 60 total)

### Wave 0 Gaps

- [ ] `tests/test_sqlite_migration.py` — covers DB-02 (migration idempotency, zero data loss, per-table record count)
- [ ] No other gaps — existing test infrastructure covers all route-level requirements

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | bcrypt password hashing unchanged; `User` model stores `password_hash` |
| V3 Session Management | yes | Flask session unchanged; `require_role()` now calls `User.query.get(user_id)` |
| V4 Access Control | yes | `require_role()` decorator unchanged in behavior |
| V5 Input Validation | yes | No new user inputs introduced; existing validation unchanged |
| V6 Cryptography | no | No new crypto; bcrypt and SECRET_KEY usage unchanged |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via ORM | Tampering | SQLAlchemy parameterized queries — never use `text()` with f-strings |
| app.db readable by OS users | Information Disclosure | Ensure `data/app.db` file permissions match `data/*.json` permissions (chmod 600) |
| Migration script run with stale data | Information Disclosure | Script is idempotent; running twice does not corrupt — safe |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `seed_users(tmp_data, users_dict)` in `test_*.py` files requires keeping `tmp_data` as first param in conftest seed helpers | Pitfall 6 + Pattern 4 | If wrong: test_*.py files would need signature update — but they cannot be modified (D-10). Planner must verify by reading test call sites. |
| A2 | `migrate_to_sqlite.py` skeleton using `on_conflict_do_nothing()` for idempotency | Pattern 5 / Code Examples | Standard SQLite UPSERT pattern — low risk |
| A3 | `db.create_all()` in `with app.app_context()` at startup is idempotent for existing tables | Pattern 2 | Confirmed in Flask-SQLAlchemy docs: "create_all does not update tables if they are already in the database" [CITED: flask-sqlalchemy.palletsprojects.com/en/3.1.x/quickstart/] |
| A4 | `SQLALCHEMY_DATABASE_URI` relative sqlite path resolves relative to Flask instance path | Pitfall 8 | Confirmed in Flask-SQLAlchemy config docs [CITED: flask-sqlalchemy.palletsprojects.com/en/3.1.x/config/] |

## Open Questions

1. **Does `require_role()` need an app context check when called from CLI tools?**
   - What we know: `require_role()` currently calls `load_users()` (file read); post-migration it calls `User.query.get()` which needs app context
   - What's unclear: `require_role()` is only invoked inside request handlers (where app context exists); CLI tools don't use it
   - Recommendation: No change needed — app context is always present during a Flask request

2. **Does `compute_timesheet_grid()` need rewriting?**
   - What we know: It takes dicts (`attendance`, `overrides`, `schedule`) as parameters, not ORM objects
   - What's unclear: Whether to rewrite the pure functions or build adapter layers
   - Recommendation: Keep pure functions unchanged; build dict adapters in the routes that call them. This is the minimum change needed to pass all tests.

3. **Where should models.py models be imported from in test fixtures?**
   - What we know: `conftest.py` imports `app as _app`; models are in a new `models.py`
   - What's unclear: Whether circular import issues arise if `app.py` imports from `models.py` and tests import both
   - Recommendation: `from models import db, User, ...` in conftest — no circular import because `models.py` does not import `app`

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14.4 | app.py | ✓ | 3.14.4 | — |
| pip | Package install | ✓ | 25.1.1 | — |
| flask-sqlalchemy | ORM | ✗ | not installed | Install: `pip install flask-sqlalchemy==3.1.1` |
| sqlalchemy | ORM core | ✗ | not installed (pulled by flask-sqlalchemy) | Install via flask-sqlalchemy |
| pytest | Test runner | ✓ | installed in venv | — |
| SQLite | Database | ✓ | built into Python 3.14.4 | — |

**Missing dependencies with no fallback:**
- `flask-sqlalchemy==3.1.1` — install as Wave 0 task before any code changes

**Missing dependencies with fallback:**
- None

## Project Constraints (from CLAUDE.md)

- **Tech stack**: Flask + Python only; no framework migration
- **Storage**: JSON files in `data/` for v1; this phase replaces them with SQLite
- **Python**: 3.14.4 on venv at `/var/www/sites/face-almgp33/venv/bin/python`
- **Deployment**: PM2 manages process; final step is `pm2 restart face-recognition`
- **Data isolation**: Must be enforced server-side
- **Naming**: snake_case for Python functions, CONSTANT_CASE for module-level constants
- **Section headers**: Use Unicode box-drawing `# ─── Section Name ───────────────────`
- **Error handling**: try/except for I/O; guard clauses; `jsonify({...}), <code>` pattern
- **Single file Python**: App currently monolithic `app.py`; `models.py` is an approved extraction for this phase (D-07)

## Sources

### Primary (MEDIUM confidence)

- [Flask-SQLAlchemy 3.1 Quickstart](https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/quickstart/) — initialization pattern, db.create_all(), session operations
- [Flask-SQLAlchemy 3.1 Configuration](https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/config/) — SQLALCHEMY_DATABASE_URI, SQLite relative path behavior
- [SQLAlchemy 2.0 Declarative Mapping](https://docs.sqlalchemy.org/en/20/orm/mapping_styles.html) — DeclarativeBase, mapped_column
- [SQLAlchemy 2.0 Type Basics](https://docs.sqlalchemy.org/en/20/core/type_basics.html) — String, Text, Integer, Boolean, DateTime
- [SQLAlchemy 2.0 Table Configuration](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html) — composite PKs, Optional[], __table_args__

### Secondary (LOW confidence)

- [SQLAlchemy UPSERT discussion](https://github.com/sqlalchemy/sqlalchemy/discussions/9675) — INSERT OR IGNORE pattern for idempotent migration
- [Flask-SQLAlchemy testing patterns (websearch)](https://alexmic.net/flask-sqlalchemy-pytest/) — conftest fixture pattern

### Tertiary (codebase — HIGH confidence for project-specific facts)

- `app.py` — verified 116 load/save call sites, 2 fcntl.flock sites, 1,877 total lines
- `tests/conftest.py` — confirmed `seed_*` helper signatures (tmp_data as first arg)
- `data/*.json` — confirmed actual field structures for all source files
- `tests/` directory listing — confirmed all 10 test files to preserve

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — flask-sqlalchemy 3.1.1 confirmed latest via `pip index versions`
- Architecture: MEDIUM — ORM patterns from official docs; conftest patterns from websearch
- Pitfalls: HIGH — Pitfall 3 (label), Pitfall 6 (seed signature), Pitfall 8 (SQLite path) verified against actual codebase

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (stable library; 30-day window)
