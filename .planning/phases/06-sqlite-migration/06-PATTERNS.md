# Phase 6: SQLite Migration — Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 3 new/modified files
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `models.py` | model | CRUD | `app.py` load/save helpers (lines 38–240) | role-match (models extracted from app) |
| `app.py` (modify) | controller + service | CRUD, request-response | `app.py` itself — existing route/helper pattern | self-analog (in-place rewrite) |
| `migrate_to_sqlite.py` | utility / migration script | batch, transform | `migrate.py` (existing Phase 2/5 script) | exact (same standalone migration pattern) |
| `tests/conftest.py` (modify) | test fixture | request-response | `tests/conftest.py` itself — existing fixture pattern | self-analog (in-place rewrite) |

## Pattern Assignments

---

### `models.py` (model, CRUD)

**Analog:** `app.py` lines 38–240 (load/save helpers — each function's dict schema maps 1:1 to a model class)

**Imports pattern** (no analog in codebase — use RESEARCH.md Pattern 1):
```python
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, Boolean
from typing import Optional
import json

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
```

**Core model pattern** — copy column names from the JSON dict keys used in the load/save helpers:

`load_users()` dict keys → `User` model (`app.py` lines 56–98):
```python
# JSON keys: id, username, password_hash, role, active, org_id, dept_id
class User(db.Model):
    __tablename__ = "user"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    dept_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
```

`load_employees()` dict keys → `Employee` + `EmployeeSchedule` (`app.py` lines 127–135, `migrate.py` line 35):
```python
# JSON keys: id, name, role, label, face_count, registered_at, org_id, dept_id, schedule
# CRITICAL: label MUST NOT be autoincrement — it's the LBPH recognizer label (D-14)
class Employee(db.Model):
    __tablename__ = "employee"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="employee")
    label: Mapped[int] = mapped_column(Integer, nullable=False, autoincrement=False)
    face_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registered_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    dept_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

# schedule sub-dict moves to separate table (D-02)
# DEFAULT_SCHEDULE from migrate.py line 35: {"start": "09:00", "end": "18:00", "work_days": [1,2,3,4,5]}
class EmployeeSchedule(db.Model):
    __tablename__ = "employee_schedule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    emp_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False, default="09:00")
    end_time: Mapped[str] = mapped_column(String(5), nullable=False, default="18:00")
    work_days_json: Mapped[str] = mapped_column(Text, nullable=False, default="[1,2,3,4,5]")
```

`load_orgs()` / `load_depts()` dict keys → `Organization` / `Department` (`app.py` lines 149–185, Phase 5 token fields from `migrate.py` lines 102–172):
```python
# orgs.json keys: id, name, description, created_at + Phase 5: kiosk_pin, org_token,
#                 reg_token, reg_pin, reg_token_expires, kiosk_display_name
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

# depts.json keys: id, org_id, name, head_name, created_at
class Department(db.Model):
    __tablename__ = "department"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    head_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
```

`load_attendance()` nested dict → `AttendanceRecord` (`app.py` lines 137–145):
```python
# attendance.json structure: {date: {emp_id: {check_in, check_out}}}
class AttendanceRecord(db.Model):
    __tablename__ = "attendance_record"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    emp_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    check_in_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    check_out_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
```

`append_log()` → `LogEntry` (`app.py` lines 468–480):
```python
# logs.json array entry keys: ts, event, emp_id, name, confidence_raw, confidence_pct
class LogEntry(db.Model):
    __tablename__ = "log_entry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[str] = mapped_column(String(32), nullable=False)
    event: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    emp_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    confidence_raw: Mapped[Optional[float]] = mapped_column(nullable=True)
    confidence_pct: Mapped[Optional[float]] = mapped_column(nullable=True)
```

`load_timesheet_overrides()` dict → `TimesheetOverride` (`app.py` lines 217–240):
```python
# timesheet_overrides.json: {emp_id: {date_str: symbol}}
# Composite PK on (emp_id, date) (D-04)
class TimesheetOverride(db.Model):
    __tablename__ = "timesheet_override"
    emp_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(4), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    updated_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
```

`load_config()` dict → `AppSetting` (`app.py` lines 38–52):
```python
# config.json keys: username, password_hash (arbitrary key-value store)
class AppSetting(db.Model):
    __tablename__ = "app_setting"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

---

### `app.py` — modifications (controller + service, CRUD/request-response)

**Analog:** `app.py` itself — the existing structure is preserved; only the top section and all load/save calls are replaced.

**Imports pattern** — replace file-constant block and add ORM imports (current `app.py` lines 1–30):
```python
# REMOVE: import fcntl
# REMOVE: DATA_DIR, FACES_DIR, EMPLOYEES_FILE, ... TIMESHEET_OVERRIDES_FILE constants
# REMOVE: all load_*/save_* function definitions
# ADD after existing imports:
from models import db, Employee, User, Organization, Department
from models import AttendanceRecord, EmployeeSchedule, LogEntry, TimesheetOverride, AppSetting
```

**App initialization pattern** — extends current `app.py` lines 11–18:
```python
app = Flask(__name__)
_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable must be set to a long random string. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
app.secret_key = _secret_key

# NEW: SQLAlchemy config (D-16 + Pitfall 8 — use abspath to avoid instance-path trap)
_db_url = os.environ.get("DATABASE_URL") or (
    "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "app.db")
)
app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
```

**Startup block pattern** — extends current app startup (after all route definitions):
```python
# Current (lines ~last section of app.py):
if __name__ == "__main__":
    init_config()
    init_users()
    ...

# AFTER migration — startup block:
with app.app_context():
    db.create_all()      # idempotent — does not modify existing tables
    init_users()         # now inserts via db.session instead of writing JSON
```

**require_role() replacement** — current `app.py` lines 107–123:
```python
# BEFORE (line 114–115):
users = load_users()
user = users.get(user_id)

# AFTER:
user = User.query.get(user_id)
# Rest of function unchanged: check user.active, user.role
```

**load_employees / save_employees replacement** — current `app.py` lines 127–135:
```python
# BEFORE (read):
employees = load_employees()
emp = employees.get(emp_id)

# AFTER (single lookup):
emp = Employee.query.get(emp_id)

# AFTER (all employees as dict — for routes that iterate):
employees = {e.id: e for e in Employee.query.all()}

# BEFORE (write):
employees[emp_id] = {...}
save_employees(employees)

# AFTER (insert):
emp = Employee(id=emp_id, name=name, label=label, ...)
db.session.add(emp)
db.session.commit()

# AFTER (update):
emp = Employee.query.get(emp_id)
emp.name = new_name
db.session.commit()
```

**Attendance replacement** — current `app.py` lines 137–145 and recognition route:
```python
# BEFORE (check-in):
attendance = load_attendance()
if today not in attendance:
    attendance[today] = {}
attendance[today][emp_id] = {"check_in": now, "check_out": None}
save_attendance(attendance)

# AFTER:
rec = AttendanceRecord.query.filter_by(emp_id=emp_id, date=today).first()
if rec is None:
    rec = AttendanceRecord(emp_id=emp_id, date=today, check_in_time=now)
    db.session.add(rec)
elif rec.check_out_time is None:
    rec.check_out_time = now
db.session.commit()

# AFTER (build compat dict for compute_symbol/compute_timesheet_grid — Pitfall 4 & 5):
records = AttendanceRecord.query.filter_by(date=date_str).all()
attendance_dict = {r.emp_id: {"check_in": r.check_in_time, "check_out": r.check_out_time}
                   for r in records}
```

**append_log() replacement** — current `app.py` lines 468–480:
```python
# BEFORE:
def append_log(entry):
    logs = []
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE) as f:
            try:
                logs = json.load(f)
            except Exception:
                logs = []
    logs.append(entry)
    if len(logs) > 10000:
        logs = logs[-10000:]
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# AFTER:
def append_log(entry):
    log = LogEntry(
        ts=entry.get("ts"), event=entry.get("event"),
        emp_id=entry.get("emp_id"), name=entry.get("name"),
        confidence_raw=entry.get("confidence_raw"),
        confidence_pct=entry.get("confidence_pct")
    )
    db.session.add(log)
    db.session.commit()
    count = LogEntry.query.count()
    if count > 10000:
        excess = count - 10000
        oldest_ids = db.session.execute(
            db.select(LogEntry.id).order_by(LogEntry.id.asc()).limit(excess)
        ).scalars().all()
        LogEntry.query.filter(LogEntry.id.in_(oldest_ids)).delete(synchronize_session=False)
        db.session.commit()
```

**Error handling pattern** — section headers and try/except style from current `app.py` (copy as-is):
```python
# ─── Section Name ─────────────────────────────────────────────────────────────

try:
    ...
    db.session.commit()
except Exception:
    db.session.rollback()
    raise
```

---

### `migrate_to_sqlite.py` (utility, batch/transform)

**Analog:** `migrate.py` (lines 1–283) — exact structural match: standalone script, `_load_json()` helper, `run_migration()` function, idempotent per-entity functions, `if __name__ == "__main__"` entry point.

**Script header and imports** — copy from `migrate.py` lines 1–35:
```python
#!/usr/bin/env python3
"""migrate_to_sqlite.py — One-shot JSON → SQLite migration. Idempotent."""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, Employee, User, Organization, Department
from models import AttendanceRecord, EmployeeSchedule, LogEntry, TimesheetOverride, AppSetting
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
```

**_load_json() helper** — copy verbatim from `migrate.py` lines 38–43:
```python
def _load_json(filename):
    """Load JSON dict/list from data/filename; return {} if file absent."""
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}
```

**Idempotent insert pattern** — copy `on_conflict_do_nothing()` approach from RESEARCH.md Pattern 5:
```python
# Use sqlite_insert + on_conflict_do_nothing for all tables
stmt = sqlite_insert(Employee).values(
    id=emp["id"], name=emp["name"], role=emp.get("role", "employee"),
    label=int(emp["label"]),   # CRITICAL: preserve verbatim (D-14)
    face_count=int(emp.get("face_count", 0)),
    registered_at=emp.get("registered_at"),
    org_id=emp.get("org_id"), dept_id=emp.get("dept_id"),
).on_conflict_do_nothing(index_elements=["id"])
db.session.execute(stmt)
```

**Summary print pattern** — copy from `migrate.py` lines 170–172, 276–278:
```python
print(f"  OK  {entity_name}: migrated")
# ...
print(f"\nМиграция завершена: {count_employees} сотрудников, {count_users} пользователей, ...")
```

**App context pattern for standalone script** — copy from `migrate.py` lines 175–282, adapted for SQLAlchemy:
```python
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
        # ... per-table migration blocks
        db.session.commit()

if __name__ == "__main__":
    run_migration()
```

---

### `tests/conftest.py` — modifications (test fixture, request-response)

**Analog:** `tests/conftest.py` itself — the structure is preserved; `tmp_data` becomes a stub and `client` absorbs the DB setup.

**tmp_data stub pattern** — replaces current `conftest.py` lines 29–75:
```python
@pytest.fixture()
def tmp_data(tmp_path):
    """Stub: kept so test_*.py calls like seed_users(tmp_data, ...) keep working.
    No longer monkeypatches file paths — the DB is overridden in client fixture.
    Returns tmp_path for signature compatibility.
    """
    return tmp_path
```

**client fixture pattern** — replaces current `conftest.py` lines 78–92:
```python
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
```

**seed helper pattern** — replaces current `conftest.py` lines 97–198 (keep `tmp_data` as first positional arg to preserve `test_*.py` call-site compatibility — Pitfall 6):
```python
def seed_users(tmp_data, users_dict):
    """tmp_data accepted but ignored — kept for test_*.py call-site compatibility (Pitfall 6)."""
    import app as _app
    from models import db, User
    with _app.app.app_context():
        for uid, u in users_dict.items():
            if not User.query.get(u["id"]):
                db.session.add(User(
                    id=u["id"], username=u["username"],
                    password_hash=u["password_hash"], role=u["role"],
                    active=u.get("active", True),
                    org_id=u.get("org_id"), dept_id=u.get("dept_id"),
                ))
        db.session.commit()

# Repeat same pattern for seed_config, seed_orgs, seed_depts, seed_employees
# Each: (tmp_data, data_dict) → db.session.add(ModelClass(...)) per item
```

---

## Shared Patterns

### Section Headers (apply to all new/modified Python files)
**Source:** `app.py` throughout
```python
# ─── Section Name ─────────────────────────────────────────────────────────────
```

### Error Handling (apply to all db.session write operations in app.py routes)
**Source:** `app.py` error handling pattern throughout routes
```python
try:
    db.session.add(obj)
    db.session.commit()
    return jsonify({...}), 200
except Exception:
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500
```

### Guard Clauses (apply to all routes — unchanged from current pattern)
**Source:** `app.py` throughout route handlers
```python
emp = Employee.query.get(emp_id)
if not emp:
    return jsonify({"error": "Employee not found"}), 404
```

### fcntl Removal Checklist
**Source:** `app.py` lines 1 (import), 70 (save_users), 232 (save_timesheet_overrides); `migrate.py` lines 15, 49
```python
# REMOVE from app.py: import fcntl
# REMOVE from app.py: save_users() entire function body (tempfile + flock pattern)
# REMOVE from app.py: save_timesheet_overrides() entire function body (tempfile + flock pattern)
# REMOVE from migrate_to_sqlite.py: do NOT copy fcntl from migrate.py
```

### Attendance Dict Adapter (apply wherever compute_symbol / compute_timesheet_grid is called)
**Source:** `app.py` `compute_symbol()` signature at line 267 expects `attendance` as `{date_str: {emp_id: {check_in, check_out}}}`
```python
# Build compat dict before calling compute_symbol or compute_timesheet_grid:
records = AttendanceRecord.query.filter(
    AttendanceRecord.emp_id == emp_id,
    AttendanceRecord.date >= start_date_str,
    AttendanceRecord.date <= end_date_str,
).all()
attendance = {}
for r in records:
    attendance.setdefault(r.date, {})[r.emp_id] = {
        "check_in": r.check_in_time,
        "check_out": r.check_out_time,
    }
```

### EmployeeSchedule Access Adapter (apply wherever emp["schedule"] was accessed)
**Source:** `app.py` `compute_symbol()` line 280 accesses `schedule.get("work_days", ...)`, `migrate.py` line 35 `DEFAULT_SCHEDULE`
```python
sched = EmployeeSchedule.query.filter_by(emp_id=emp_id).first()
schedule = {
    "start": sched.start_time if sched else "09:00",
    "end": sched.end_time if sched else "18:00",
    "work_days": json.loads(sched.work_days_json) if sched else [1, 2, 3, 4, 5],
}
```

## No Analog Found

All files have analogs. No entries here.

## Metadata

**Analog search scope:** `/var/www/sites/face-almgp33/` (app.py, migrate.py, tests/conftest.py)
**Files scanned:** 3 source files fully read
**Pattern extraction date:** 2026-06-13
