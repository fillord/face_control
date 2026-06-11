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

# Verbatim bcrypt hash from data/config.json — used by MIG-03 tests to assert
# that init_users() copies the hash without re-hashing.
BCRYPT_HASH_SUPERADMIN = "$2b$12$F0kPJqHfW3hWU9QJm7kCyee3xD/eYhdcBwwmWgBvXuC9wqwKyPMym"

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
