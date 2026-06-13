#!/usr/bin/env python3
"""migrate_to_sqlite.py — One-shot JSON → SQLite migration. Idempotent.

Reads all 7 JSON data files + config.json and inserts their records into
app.db via the ORM models. Safe to run multiple times — uses
on_conflict_do_nothing for all flat-PK tables and query-then-skip for
tables without natural unique keys (AttendanceRecord, LogEntry).

Usage:
    python migrate_to_sqlite.py

Or from tests:
    migrate_to_sqlite.run_migration(data_dir="/tmp/data", database_uri="sqlite:///:memory:")

D-13: idempotent, zero data loss, per-table summary printed.
D-14: Employee.label preserved verbatim via int(emp["label"]).
D-16: DATABASE_URL env var configures path; default is data/app.db.
"""
import json
import os
import sys

# Ensure project root is on path so "from models import ..." resolves
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import (
    db,
    Employee,
    EmployeeSchedule,
    User,
    Organization,
    Department,
    AttendanceRecord,
    LogEntry,
    TimesheetOverride,
    AppSetting,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

# ─── Default data dir ─────────────────────────────────────────────────────────

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DATA_DIR = os.path.join(_SCRIPT_DIR, "data")


# ─── JSON loader ──────────────────────────────────────────────────────────────

def _load_json(data_dir, filename):
    """Load JSON from data_dir/filename; return {} (or []) if file absent (Pitfall 7)."""
    path = os.path.join(data_dir, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_json_list(data_dir, filename):
    """Load JSON list from data_dir/filename; return [] if file absent."""
    path = os.path.join(data_dir, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    return []


# ─── Per-table migration functions ────────────────────────────────────────────

def _migrate_employees(data_dir, session):
    """Migrate employees.json → Employee + EmployeeSchedule rows.

    Uses on_conflict_do_nothing on primary key to stay idempotent.
    D-14: preserves label via int(emp["label"]) verbatim.
    D-02: migrates schedule sub-dict into EmployeeSchedule row.
    """
    employees = _load_json(data_dir, "employees.json")
    count_emp = 0
    count_sched = 0
    DEFAULT_SCHEDULE = {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}

    for emp_id, emp in employees.items():
        stmt = sqlite_insert(Employee).values(
            id=emp["id"],
            name=emp["name"],
            role=emp.get("role", "employee"),
            label=int(emp["label"]),  # D-14: preserve LBPH label verbatim
            face_count=int(emp.get("face_count", 0)),
            registered_at=emp.get("registered_at"),
            org_id=emp.get("org_id"),
            dept_id=emp.get("dept_id"),
        ).on_conflict_do_nothing(index_elements=["id"])
        result = session.execute(stmt)
        if result.rowcount:
            count_emp += 1

        # Migrate schedule sub-dict (D-02)
        sched = emp.get("schedule") or DEFAULT_SCHEDULE
        sched_stmt = sqlite_insert(EmployeeSchedule).values(
            emp_id=emp["id"],
            start_time=sched.get("start", "09:00"),
            end_time=sched.get("end", "18:00"),
            work_days_json=json.dumps(sched.get("work_days", [1, 2, 3, 4, 5])),
        ).on_conflict_do_nothing(index_elements=["emp_id"])
        sched_result = session.execute(sched_stmt)
        if sched_result.rowcount:
            count_sched += 1

    session.commit()
    print(f"  Employees:         {count_emp} / {len(employees)} inserted (schedules: {count_sched})")
    return count_emp


def _migrate_users(data_dir, session):
    """Migrate users.json → User rows (on_conflict_do_nothing on id)."""
    users = _load_json(data_dir, "users.json")
    count = 0
    for uid, u in users.items():
        stmt = sqlite_insert(User).values(
            id=u["id"],
            username=u["username"],
            password_hash=u["password_hash"],
            role=u["role"],
            active=u.get("active", True),
            org_id=u.get("org_id"),
            dept_id=u.get("dept_id"),
        ).on_conflict_do_nothing(index_elements=["id"])
        result = session.execute(stmt)
        if result.rowcount:
            count += 1
    session.commit()
    print(f"  Users:             {count} / {len(users)} inserted")
    return count


def _migrate_orgs(data_dir, session):
    """Migrate orgs.json → Organization rows (on_conflict_do_nothing on id).

    Preserves all Phase 5 token fields (org_token, kiosk_pin, reg_token, etc.).
    """
    orgs = _load_json(data_dir, "orgs.json")
    count = 0
    for oid, o in orgs.items():
        stmt = sqlite_insert(Organization).values(
            id=o["id"],
            name=o["name"],
            description=o.get("description"),
            created_at=o.get("created_at"),
            kiosk_pin=o.get("kiosk_pin"),
            org_token=o.get("org_token"),
            reg_token=o.get("reg_token"),
            reg_pin=o.get("reg_pin"),
            reg_token_expires=o.get("reg_token_expires"),
            kiosk_display_name=o.get("kiosk_display_name"),
        ).on_conflict_do_nothing(index_elements=["id"])
        result = session.execute(stmt)
        if result.rowcount:
            count += 1
    session.commit()
    print(f"  Organizations:     {count} / {len(orgs)} inserted")
    return count


def _migrate_depts(data_dir, session):
    """Migrate depts.json → Department rows (on_conflict_do_nothing on id)."""
    depts = _load_json(data_dir, "depts.json")
    count = 0
    for did, d in depts.items():
        stmt = sqlite_insert(Department).values(
            id=d["id"],
            org_id=d["org_id"],
            name=d["name"],
            head_name=d.get("head_name"),
            created_at=d.get("created_at"),
        ).on_conflict_do_nothing(index_elements=["id"])
        result = session.execute(stmt)
        if result.rowcount:
            count += 1
    session.commit()
    print(f"  Departments:       {count} / {len(depts)} inserted")
    return count


def _migrate_attendance(data_dir, session):
    """Migrate attendance.json → AttendanceRecord rows.

    Source shape: {date: {emp_id: {check_in, check_out}}}
    Auto-increment id has no natural unique conflict target, so we use
    query-then-skip to remain idempotent (skip row if emp_id+date+check_in_time
    already exists).

    D-01: event_type left NULL for legacy rows — the recognition route populates
    it going forward. If check_out is present we set event_type="check_out";
    if only check_in, event_type="check_in". NULL is acceptable for legacy rows.
    """
    attendance = _load_json(data_dir, "attendance.json")
    count = 0
    skipped = 0
    for date_str, day_data in attendance.items():
        for emp_id, rec in day_data.items():
            check_in = rec.get("check_in")
            check_out = rec.get("check_out")
            # Idempotency: skip if row with same emp_id+date+check_in_time already exists
            existing = session.execute(
                db.select(AttendanceRecord).filter_by(
                    emp_id=emp_id, date=date_str, check_in_time=check_in
                )
            ).scalar_one_or_none()
            if existing:
                skipped += 1
                continue
            # Set event_type based on what data is present (D-01 — acceptable for legacy)
            if check_out:
                event_type = "check_out"
            elif check_in:
                event_type = "check_in"
            else:
                event_type = None
            session.add(AttendanceRecord(
                emp_id=emp_id,
                date=date_str,
                check_in_time=check_in,
                check_out_time=check_out,
                event_type=event_type,
            ))
            count += 1
    session.commit()
    total = sum(len(v) for v in attendance.values())
    print(f"  Attendance records:{count} inserted, {skipped} already existed (total source: {total})")
    return count


def _migrate_logs(data_dir, session):
    """Migrate logs.json → LogEntry rows.

    Idempotency: skip if a row with identical ts+event+emp_id already exists.
    Accept append-only behavior for exact timestamp collisions on the same employee.
    """
    logs = _load_json_list(data_dir, "logs.json")
    count = 0
    skipped = 0
    for entry in logs:
        ts = entry.get("ts")
        event = entry.get("event")
        emp_id = entry.get("emp_id")
        existing = session.execute(
            db.select(LogEntry).filter_by(ts=ts, event=event, emp_id=emp_id)
        ).scalar_one_or_none()
        if existing:
            skipped += 1
            continue
        session.add(LogEntry(
            ts=ts,
            event=event,
            emp_id=emp_id,
            name=entry.get("name"),
            confidence_raw=entry.get("confidence_raw"),
            confidence_pct=entry.get("confidence_pct"),
        ))
        count += 1
    session.commit()
    print(f"  Log entries:       {count} inserted, {skipped} already existed (total source: {len(logs)})")
    return count


def _migrate_config(data_dir, session):
    """Migrate config.json → AppSetting rows (on_conflict_do_nothing on key).

    config.json shape: {key: value} — each key becomes an AppSetting row.
    """
    config = _load_json(data_dir, "config.json")
    count = 0
    for key, value in config.items():
        stmt = sqlite_insert(AppSetting).values(
            key=key,
            value=str(value) if value is not None else None,
        ).on_conflict_do_nothing(index_elements=["key"])
        result = session.execute(stmt)
        if result.rowcount:
            count += 1
    session.commit()
    print(f"  App settings:      {count} / {len(config)} inserted")
    return count


def _migrate_timesheet_overrides(data_dir, session):
    """Migrate timesheet_overrides.json → TimesheetOverride rows.

    Source shape: {emp_id: {date: symbol}} — may be absent (Pitfall 7, T-06-15).
    Composite PK (emp_id, date) → on_conflict_do_nothing.
    """
    overrides = _load_json(data_dir, "timesheet_overrides.json")
    count = 0
    total = sum(len(v) for v in overrides.values()) if isinstance(overrides, dict) else 0
    if isinstance(overrides, dict):
        for emp_id, date_map in overrides.items():
            if not isinstance(date_map, dict):
                continue
            for date_str, symbol in date_map.items():
                stmt = sqlite_insert(TimesheetOverride).values(
                    emp_id=emp_id,
                    date=date_str,
                    symbol=symbol,
                    updated_by=None,
                    updated_at=None,
                ).on_conflict_do_nothing(index_elements=["emp_id", "date"])
                result = session.execute(stmt)
                if result.rowcount:
                    count += 1
    session.commit()
    print(f"  Timesheet overrides:{count} / {total} inserted")
    return count


# ─── Main entry point ─────────────────────────────────────────────────────────

def run_migration(data_dir=None, database_uri=None):
    """Run the idempotent JSON → SQLite migration.

    Args:
        data_dir: Path to the data directory containing JSON files.
                  Defaults to <script_dir>/data or DATA_DIR env var.
        database_uri: SQLAlchemy database URI.
                      Defaults to DATABASE_URL env var or sqlite:///data/app.db.
                      NOTE: When called from tests that already have an active Flask
                      app_context, the migration reuses that context so queries made
                      after run_migration() see the inserted data (D-11).

    Returns:
        dict with per-table inserted counts.
    """
    if data_dir is None:
        data_dir = os.environ.get("DATA_DIR", _DEFAULT_DATA_DIR)
    if database_uri is None:
        database_uri = os.environ.get(
            "DATABASE_URL",
            "sqlite:///" + os.path.join(_DEFAULT_DATA_DIR, "app.db"),
        )

    print(f"\nStarting migration: data_dir={data_dir!r}")
    print(f"  Target URI: {database_uri!r}\n")

    def _execute(session):
        """Run all per-table migration steps and return counts."""
        db.create_all()  # idempotent — does not drop existing tables or data
        counts = {}
        print("Migrating tables:")
        counts["employees"] = _migrate_employees(data_dir, session)
        counts["users"] = _migrate_users(data_dir, session)
        counts["organizations"] = _migrate_orgs(data_dir, session)
        counts["departments"] = _migrate_depts(data_dir, session)
        counts["attendance"] = _migrate_attendance(data_dir, session)
        counts["logs"] = _migrate_logs(data_dir, session)
        counts["config"] = _migrate_config(data_dir, session)
        counts["timesheet_overrides"] = _migrate_timesheet_overrides(data_dir, session)
        return counts

    # If there is already an active Flask app context (e.g. called from a test
    # fixture that sets up in-memory SQLite), reuse it so that data inserted here
    # is visible to queries in the same context.  Otherwise create a new app.
    from flask import current_app, has_app_context
    if has_app_context():
        # Reuse the active app context — reconfigure DB URI if it differs
        if current_app.config.get("SQLALCHEMY_DATABASE_URI") != database_uri:
            current_app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
        counts = _execute(db.session)
    else:
        # Standalone invocation (CLI or test without active context)
        flask_app = Flask(__name__)
        flask_app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
        flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        db.init_app(flask_app)
        with flask_app.app_context():
            counts = _execute(db.session)

    print(
        f"\nMigration complete: "
        f"{counts['employees']} employees, "
        f"{counts['users']} users, "
        f"{counts['organizations']} organizations, "
        f"{counts['departments']} departments, "
        f"{counts['attendance']} attendance records, "
        f"{counts['logs']} log entries, "
        f"{counts['config']} settings, "
        f"{counts['timesheet_overrides']} timesheet overrides."
    )

    return counts


if __name__ == "__main__":
    run_migration()
