"""
Test fixtures and shared helpers for the Face Recognition Attendance System test suite.

Rewritten for Phase 6 SQLite migration (plan 06-02):
- tmp_data is now a stub (no monkeypatching) — kept so seed_*(tmp_data, ...) call sites work
- client fixture drives in-memory SQLite via SQLALCHEMY_DATABASE_URI override (D-10/D-11)
- seed helpers insert via db.session.add() instead of writing JSON files (D-12)
- All monkeypatch.setattr(_app, "*_FILE", ...) calls removed (D-12)

Threat mitigation T-06-04: db.drop_all() in teardown ensures no cross-test data leakage.
"""
import json
import pytest

# ─── Fixture constants ────────────────────────────────────────────────────────

# Bcrypt hash of "superadmin123" — used by auth/RBAC tests that POST with password="superadmin123".
# Also used by MIG-03 tests: seed_config seeds AppSetting with this hash so init_users() copies it
# verbatim, and the test asserts user["password_hash"] == BCRYPT_HASH_SUPERADMIN.
BCRYPT_HASH_SUPERADMIN = "$2b$12$aiT81qA2zjbyxSpMPdXu0euetZyQU6/htQjDW9gcJPTir35bqv8Ry"

# ─── Core fixture ─────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_data(tmp_path):
    """Stub: kept so test_*.py calls like seed_users(tmp_data, ...) keep working.

    No longer monkeypatches file paths — the DB is overridden in client fixture.
    Returns tmp_path for signature compatibility (Pitfall 6).
    """
    return tmp_path


@pytest.fixture()
def client(tmp_data):
    """Yield an isolated Flask test client backed by an in-memory SQLite database.

    - Overrides SQLALCHEMY_DATABASE_URI to sqlite:///:memory: for test isolation (D-10/D-11)
    - Creates a fresh schema per test via db.create_all() (T-06-04)
    - Drops all tables in teardown via db.drop_all() to prevent cross-test leakage
    """
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


# ─── Seeding helpers ──────────────────────────────────────────────────────────

def seed_users(tmp_data, users_dict):
    """Insert User rows via ORM into the active app context.

    tmp_data accepted but ignored — kept for test_*.py call-site compatibility (Pitfall 6).
    The keys of users_dict are user_id strings; values follow the D-06 schema:
    id, username, password_hash, role, active, org_id, dept_id.

    Example::

        seed_users(tmp_data, {
            "uid-1": {
                "id": "uid-1",
                "username": "superadmin",
                "password_hash": BCRYPT_HASH_SUPERADMIN,
                "role": "superadmin",
                "active": True,
                "org_id": None,
                "dept_id": None,
            }
        })
    """
    import app as _app
    from models import db, User
    with _app.app.app_context():
        for uid, u in users_dict.items():
            if not User.query.get(u["id"]):
                db.session.add(User(
                    id=u["id"],
                    username=u["username"],
                    password_hash=u["password_hash"],
                    role=u["role"],
                    active=u.get("active", True),
                    org_id=u.get("org_id"),
                    dept_id=u.get("dept_id"),
                ))
        db.session.commit()


def seed_config(tmp_data, config_dict):
    """Insert AppSetting rows via ORM into the active app context.

    tmp_data accepted but ignored — kept for test_*.py call-site compatibility (Pitfall 6).
    Used by MIG-03 tests to control what hash init_users() finds in AppSetting.
    Each key/value pair in config_dict becomes an AppSetting row.

    Example::

        seed_config(tmp_data, {
            "username": "admin",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
        })
    """
    import app as _app
    from models import db, AppSetting
    with _app.app.app_context():
        for key, value in config_dict.items():
            if not AppSetting.query.get(key):
                db.session.add(AppSetting(key=key, value=str(value) if value is not None else None))
        db.session.commit()


def seed_orgs(tmp_data, orgs_dict):
    """Insert Organization rows via ORM into the active app context.

    tmp_data accepted but ignored — kept for test_*.py call-site compatibility (Pitfall 6).
    Keys are org_id strings; values follow the D-06 schema: id, name, description,
    created_at, plus Phase 5 token fields (kiosk_pin, org_token, reg_token, etc.).

    Example::

        seed_orgs(tmp_data, {
            "org-A": {
                "id": "org-A",
                "name": "Главная организация",
                "description": "",
                "created_at": "2026-01-01T00:00:00",
            }
        })
    """
    import app as _app
    from models import db, Organization
    with _app.app.app_context():
        for oid, o in orgs_dict.items():
            if not Organization.query.get(o["id"]):
                db.session.add(Organization(
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
                ))
        db.session.commit()


def seed_depts(tmp_data, depts_dict):
    """Insert Department rows via ORM into the active app context.

    tmp_data accepted but ignored — kept for test_*.py call-site compatibility (Pitfall 6).
    Keys are dept_id strings; values follow the D-06 schema: id, org_id, name,
    head_name, created_at.

    Example::

        seed_depts(tmp_data, {
            "dept-A": {
                "id": "dept-A",
                "org_id": "org-A",
                "name": "Основной отдел",
                "head_name": "",
                "created_at": "2026-01-01T00:00:00",
            }
        })
    """
    import app as _app
    from models import db, Department
    with _app.app.app_context():
        for did, d in depts_dict.items():
            if not Department.query.get(d["id"]):
                db.session.add(Department(
                    id=d["id"],
                    org_id=d["org_id"],
                    name=d["name"],
                    head_name=d.get("head_name"),
                    created_at=d.get("created_at"),
                ))
        db.session.commit()


def seed_employees(tmp_data, employees_dict):
    """Insert Employee + EmployeeSchedule rows via ORM into the active app context.

    tmp_data accepted but ignored — kept for test_*.py call-site compatibility (Pitfall 6).
    Keys are employee_id strings; values include id, name, role, label, face_count,
    registered_at, and optionally org_id, dept_id, schedule sub-dict.
    An EmployeeSchedule row is always inserted alongside each Employee (D-02).

    Example::

        seed_employees(tmp_data, {
            "emp-1": {
                "id": "emp-1",
                "name": "Test Employee",
                "role": "employee",
                "label": 1,
                "face_count": 10,
                "registered_at": "2026-01-01T00:00:00",
                "org_id": "org-A",
                "dept_id": "dept-A",
                "schedule": {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]},
            }
        })
    """
    import app as _app
    from models import db, Employee, EmployeeSchedule
    DEFAULT_SCHEDULE = {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}
    with _app.app.app_context():
        for eid, e in employees_dict.items():
            if not Employee.query.get(e["id"]):
                db.session.add(Employee(
                    id=e["id"],
                    name=e["name"],
                    role=e.get("role", "employee"),
                    label=int(e["label"]),
                    face_count=int(e.get("face_count", 0)),
                    registered_at=e.get("registered_at"),
                    org_id=e.get("org_id"),
                    dept_id=e.get("dept_id"),
                ))
                sched = e.get("schedule") or DEFAULT_SCHEDULE
                if not EmployeeSchedule.query.filter_by(emp_id=e["id"]).first():
                    db.session.add(EmployeeSchedule(
                        emp_id=e["id"],
                        start_time=sched.get("start", "09:00"),
                        end_time=sched.get("end", "18:00"),
                        work_days_json=json.dumps(sched.get("work_days", [1, 2, 3, 4, 5])),
                    ))
        db.session.commit()
