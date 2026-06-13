"""
DB-02 migration test scaffold: idempotency, zero data loss, and label preservation.

These tests require migrate_to_sqlite.py (created in plan 06-04). Until that file
exists the whole module skips cleanly so the test runner stays green during Wave 0.

Coordinate with migrate_to_sqlite.py: the migration entry point must accept
  run_migration(data_dir=..., database_uri=...)
so tests can inject a temporary directory and an in-memory SQLite URI.

Do NOT import or monkeypatch any *_FILE path constant from app.py (D-10).
"""
import json
import os
import pytest

# ─── Migration availability guard ────────────────────────────────────────────

try:
    import migrate_to_sqlite  # noqa: F401
    MIGRATION_AVAILABLE = True
except ImportError:
    MIGRATION_AVAILABLE = False

SKIP_REASON = "migrate_to_sqlite.py created in plan 06-04"

# ─── Fixture: in-memory SQLite app context ────────────────────────────────────

@pytest.fixture()
def _db_context(tmp_path):
    """Spin up an in-memory Flask app + SQLAlchemy for migration testing.

    Yields a tuple (app_instance, tmp_data_dir) so each test gets:
    - A fresh in-memory SQLite schema (db.create_all / db.drop_all)
    - A tmp_path/data directory for fixture JSON files
    """
    from flask import Flask
    from models import db

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app, data_dir
        db.session.remove()
        db.drop_all()


# ─── Helper: write fixture JSON files ─────────────────────────────────────────

def _write_fixture_employees(data_dir, employees_dict):
    """Write employees.json fixture into data_dir."""
    path = data_dir / "employees.json"
    path.write_text(json.dumps(employees_dict, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_fixture_users(data_dir, users_dict):
    """Write users.json fixture into data_dir."""
    path = data_dir / "users.json"
    path.write_text(json.dumps(users_dict, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_fixture_orgs(data_dir, orgs_dict):
    """Write orgs.json fixture into data_dir."""
    path = data_dir / "orgs.json"
    path.write_text(json.dumps(orgs_dict, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_fixture_depts(data_dir, depts_dict):
    """Write depts.json fixture into data_dir."""
    path = data_dir / "depts.json"
    path.write_text(json.dumps(depts_dict, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── Fixture data ─────────────────────────────────────────────────────────────

FIXTURE_EMPLOYEES = {
    "emp-001": {
        "id": "emp-001",
        "name": "Alice Smith",
        "role": "employee",
        "label": 7,
        "face_count": 10,
        "registered_at": "2026-01-01T09:00:00",
        "org_id": "org-001",
        "dept_id": "dept-001",
        "schedule": {
            "start": "09:00",
            "end": "18:00",
            "work_days": [1, 2, 3, 4, 5],
        },
    },
    "emp-002": {
        "id": "emp-002",
        "name": "Bob Jones",
        "role": "employee",
        "label": 42,
        "face_count": 5,
        "registered_at": "2026-02-01T08:30:00",
        "org_id": "org-001",
        "dept_id": "dept-001",
        "schedule": {
            "start": "08:30",
            "end": "17:30",
            "work_days": [1, 2, 3, 4, 5],
        },
    },
}

FIXTURE_USERS = {
    "user-001": {
        "id": "user-001",
        "username": "superadmin",
        "password_hash": "$2b$12$aiT81qA2zjbyxSpMPdXu0euetZyQU6/htQjDW9gcJPTir35bqv8Ry",
        "role": "superadmin",
        "active": True,
        "org_id": None,
        "dept_id": None,
    },
}

FIXTURE_ORGS = {
    "org-001": {
        "id": "org-001",
        "name": "Test Org",
        "description": "Test organization",
        "created_at": "2026-01-01T00:00:00",
        "kiosk_pin": None,
        "org_token": None,
        "reg_token": None,
        "reg_pin": None,
        "reg_token_expires": None,
        "kiosk_display_name": None,
    },
}

FIXTURE_DEPTS = {
    "dept-001": {
        "id": "dept-001",
        "org_id": "org-001",
        "name": "Engineering",
        "head_name": "Alice Smith",
        "created_at": "2026-01-01T00:00:00",
    },
}


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not MIGRATION_AVAILABLE, reason=SKIP_REASON)
def test_migration_idempotency(_db_context):
    """Running the migration twice produces the same row counts — no duplicates, no error.

    DB-02: migrate_to_sqlite.py must be idempotent (D-13).
    """
    import migrate_to_sqlite
    from models import db, Employee, User

    app, data_dir = _db_context
    _write_fixture_employees(data_dir, FIXTURE_EMPLOYEES)
    _write_fixture_users(data_dir, FIXTURE_USERS)
    _write_fixture_orgs(data_dir, FIXTURE_ORGS)
    _write_fixture_depts(data_dir, FIXTURE_DEPTS)

    db_uri = "sqlite:///:memory:"

    # First run
    migrate_to_sqlite.run_migration(data_dir=str(data_dir), database_uri=db_uri)
    count_after_first = {
        "employees": Employee.query.count(),
        "users": User.query.count(),
    }

    # Second run — must produce identical counts with no error
    migrate_to_sqlite.run_migration(data_dir=str(data_dir), database_uri=db_uri)
    count_after_second = {
        "employees": Employee.query.count(),
        "users": User.query.count(),
    }

    assert count_after_second == count_after_first, (
        f"Idempotency failure: first run {count_after_first}, second run {count_after_second}"
    )


@pytest.mark.skipif(not MIGRATION_AVAILABLE, reason=SKIP_REASON)
def test_migration_zero_data_loss(_db_context):
    """After migrating a known fixture set, row counts equal source record counts.

    DB-02: number of rows in each table must equal the number of source records (D-13).
    """
    import migrate_to_sqlite
    from models import db, Employee, User, Organization, Department, EmployeeSchedule

    app, data_dir = _db_context
    _write_fixture_employees(data_dir, FIXTURE_EMPLOYEES)
    _write_fixture_users(data_dir, FIXTURE_USERS)
    _write_fixture_orgs(data_dir, FIXTURE_ORGS)
    _write_fixture_depts(data_dir, FIXTURE_DEPTS)

    migrate_to_sqlite.run_migration(
        data_dir=str(data_dir),
        database_uri="sqlite:///:memory:",
    )

    # Row counts must equal source record counts
    assert Employee.query.count() == len(FIXTURE_EMPLOYEES), (
        f"Employee count mismatch: expected {len(FIXTURE_EMPLOYEES)}, "
        f"got {Employee.query.count()}"
    )
    assert User.query.count() == len(FIXTURE_USERS), (
        f"User count mismatch: expected {len(FIXTURE_USERS)}, "
        f"got {User.query.count()}"
    )
    assert Organization.query.count() == len(FIXTURE_ORGS), (
        f"Organization count mismatch: expected {len(FIXTURE_ORGS)}, "
        f"got {Organization.query.count()}"
    )
    assert Department.query.count() == len(FIXTURE_DEPTS), (
        f"Department count mismatch: expected {len(FIXTURE_DEPTS)}, "
        f"got {Department.query.count()}"
    )
    # Every employee must have a corresponding schedule row (D-02)
    assert EmployeeSchedule.query.count() == len(FIXTURE_EMPLOYEES), (
        f"EmployeeSchedule count mismatch: expected {len(FIXTURE_EMPLOYEES)}, "
        f"got {EmployeeSchedule.query.count()}"
    )


@pytest.mark.skipif(not MIGRATION_AVAILABLE, reason=SKIP_REASON)
def test_migration_label_preservation(_db_context):
    """An employee with JSON label=7 has exactly label=7 after migration.

    D-14: the LBPH recognizer integer label must be preserved exactly — not auto-generated.
    """
    import migrate_to_sqlite
    from models import db, Employee

    app, data_dir = _db_context
    _write_fixture_employees(data_dir, FIXTURE_EMPLOYEES)
    _write_fixture_users(data_dir, FIXTURE_USERS)
    _write_fixture_orgs(data_dir, FIXTURE_ORGS)
    _write_fixture_depts(data_dir, FIXTURE_DEPTS)

    migrate_to_sqlite.run_migration(
        data_dir=str(data_dir),
        database_uri="sqlite:///:memory:",
    )

    # emp-001 has label=7 in the fixture — must be preserved exactly
    alice = Employee.query.get("emp-001")
    assert alice is not None, "emp-001 not found after migration"
    assert alice.label == 7, (
        f"Label preservation failure (D-14): expected label=7, got label={alice.label}"
    )

    # emp-002 has label=42 — must also be preserved
    bob = Employee.query.get("emp-002")
    assert bob is not None, "emp-002 not found after migration"
    assert bob.label == 42, (
        f"Label preservation failure (D-14): expected label=42, got label={bob.label}"
    )
