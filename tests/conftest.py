"""
Test fixtures and shared helpers for the Face Recognition Attendance System test suite.

NOTE: The following symbols do not exist in app.py yet — they are created in plan 01-02:
  - app.USERS_FILE
  - app.load_users
  - app.init_users
  - app.require_role
  - app.ROLE_HIERARCHY
Tests that depend on these symbols use @pytest.mark.xfail(reason="implemented in 01-02/01-03/01-04")
or guard with hasattr() to avoid collection errors.

Threat mitigation T-01-T1: All fixtures monkeypatch module-level path constants so no test
writes to the real /var/www/sites/face-almgp33/data/ directory.
"""
import json
import os
import pytest

# ─── Fixture constants ────────────────────────────────────────────────────────

# Bcrypt hash of "superadmin123" — used by auth/RBAC tests that POST with password="superadmin123".
# Also used by MIG-03 tests: tmp_data seeds config.json with this hash so init_users() copies it
# verbatim, and the test asserts user["password_hash"] == BCRYPT_HASH_SUPERADMIN.
BCRYPT_HASH_SUPERADMIN = "$2b$12$aiT81qA2zjbyxSpMPdXu0euetZyQU6/htQjDW9gcJPTir35bqv8Ry"

# ─── Core fixture ─────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_data(tmp_path, monkeypatch):
    """Create an isolated temp data directory and monkeypatch all app path constants.

    The fixture redirects every module-level path constant in app.py to subdirectories
    inside pytest's tmp_path so tests never touch the production data/ directory.

    Returns the tmp_path Path object so tests can seed files directly if needed.
    """
    import app as _app

    # Build the same subdirectory layout that the real data/ uses
    data_dir = tmp_path / "data"
    faces_dir = data_dir / "faces"
    data_dir.mkdir(parents=True, exist_ok=True)
    faces_dir.mkdir(parents=True, exist_ok=True)

    # Monkeypatch all module-level path constants
    monkeypatch.setattr(_app, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(_app, "FACES_DIR", str(faces_dir))
    monkeypatch.setattr(_app, "EMPLOYEES_FILE", str(data_dir / "employees.json"))
    monkeypatch.setattr(_app, "ATTENDANCE_FILE", str(data_dir / "attendance.json"))
    monkeypatch.setattr(_app, "LOGS_FILE", str(data_dir / "logs.json"))
    monkeypatch.setattr(_app, "CONFIG_FILE", str(data_dir / "config.json"))

    # USERS_FILE does not exist in app.py until plan 01-02 — guard with hasattr
    if hasattr(_app, "USERS_FILE"):
        monkeypatch.setattr(_app, "USERS_FILE", str(data_dir / "users.json"))

    # ORGS_FILE / DEPTS_FILE do not exist in app.py until plan 02-02 — guard with hasattr
    if hasattr(_app, "ORGS_FILE"):
        monkeypatch.setattr(_app, "ORGS_FILE", str(data_dir / "orgs.json"))
    if hasattr(_app, "DEPTS_FILE"):
        monkeypatch.setattr(_app, "DEPTS_FILE", str(data_dir / "depts.json"))

    # Seed a minimal config.json so init_config() does not blow up on first import
    config_path = data_dir / "config.json"
    config_path.write_text(
        json.dumps({"username": "admin", "password_hash": BCRYPT_HASH_SUPERADMIN}),
        encoding="utf-8"
    )

    return tmp_path


@pytest.fixture()
def client(tmp_data, monkeypatch):
    """Yield an isolated Flask test client.

    - Sets app.testing = True and a fixed secret_key.
    - Data directory is redirected to tmp_data so no real data/ writes occur.
    - The test client follows Flask's with-statement protocol (no extra setup needed).
    """
    import app as _app

    _app.app.testing = True
    _app.app.secret_key = "test-secret-key-for-pytest"

    with _app.app.test_client() as test_client:
        yield test_client


# ─── Seeding helpers ──────────────────────────────────────────────────────────

def seed_users(tmp_data, users_dict):
    """Write a users dict directly to the isolated users.json.

    Used by RBAC and auth tests to stage accounts without going through the
    bootstrap path. The keys of users_dict are user_id strings; values follow
    the D-01 schema: id, username, password_hash, role, active, org_id, dept_id.

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
    users_path = tmp_data / "data" / "users.json"
    users_path.write_text(json.dumps(users_dict, ensure_ascii=False, indent=2), encoding="utf-8")


def seed_config(tmp_data, config_dict):
    """Write a config dict directly to the isolated config.json.

    Used by MIG-03 tests to control what hash init_users() finds in config.json.
    """
    config_path = tmp_data / "data" / "config.json"
    config_path.write_text(json.dumps(config_dict, ensure_ascii=False, indent=2), encoding="utf-8")


def seed_orgs(tmp_data, orgs_dict):
    """Write an orgs dict directly to the isolated orgs.json.

    Keys are org_id strings; values follow the D-02 schema: id, name, description, created_at.
    Used by Phase 2 org/dept tests to stage organization data without going through the API.

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
    orgs_path = tmp_data / "data" / "orgs.json"
    orgs_path.write_text(json.dumps(orgs_dict, ensure_ascii=False, indent=2), encoding="utf-8")


def seed_depts(tmp_data, depts_dict):
    """Write a depts dict directly to the isolated depts.json.

    Keys are dept_id strings; values follow the D-02 schema: id, org_id, name, head_name, created_at.
    Used by Phase 2 org/dept tests to stage department data without going through the API.

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
    depts_path = tmp_data / "data" / "depts.json"
    depts_path.write_text(json.dumps(depts_dict, ensure_ascii=False, indent=2), encoding="utf-8")


def seed_employees(tmp_data, employees_dict):
    """Write an employees dict directly to the isolated employees.json.

    Keys are employee_id strings; values include id, name, role, label, face_count, registered_at,
    and optionally org_id, dept_id, schedule fields added by migration.
    Used by Phase 2 tests to stage employees with org/dept/schedule for dashboard and migration tests.

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
    employees_path = tmp_data / "data" / "employees.json"
    employees_path.write_text(json.dumps(employees_dict, ensure_ascii=False, indent=2), encoding="utf-8")
