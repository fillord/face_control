"""
Tests for SADM-07 (create_user role allowlist) and SADM-02 (GET /api/superadmin/employees).

Coverage:
  (a) POST /api/users role=dept_admin with valid org_id and dept_id returns non-403 success
  (b) POST /api/users role=dept_admin without dept_id returns 400
  (c) POST /api/users role=employee returns 403
  (d) POST /api/users role=hr_viewer with org_id returns success
  (e) GET /api/superadmin/employees as superadmin returns 200 with name, org_name, dept_name, face_enrolled
  (f) GET /api/superadmin/employees with org_admin session returns 403
"""
import pytest
from tests.conftest import (
    BCRYPT_HASH_SUPERADMIN,
    seed_users,
    seed_orgs,
    seed_depts,
    seed_employees,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

SA_ID = "uid-sa-sadm07"
OA_ID = "uid-oa-sadm07"
ORG_ID = "org-sadm07"
DEPT_ID = "dept-sadm07"


def _seed_base(tmp_data, client):
    """Seed a superadmin, org_admin, one org and one dept shared by all tests."""
    seed_users(tmp_data, {
        SA_ID: {
            "id": SA_ID,
            "username": "sa_sadm07",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "superadmin",
            "active": True,
            "org_id": None,
            "dept_id": None,
        },
        OA_ID: {
            "id": OA_ID,
            "username": "oa_sadm07",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "org_admin",
            "active": True,
            "org_id": ORG_ID,
            "dept_id": None,
        },
    })
    seed_orgs(tmp_data, {
        ORG_ID: {
            "id": ORG_ID,
            "name": "SADM07 Org",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        DEPT_ID: {
            "id": DEPT_ID,
            "org_id": ORG_ID,
            "name": "SADM07 Dept",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })


def _inject_superadmin(client):
    with client.session_transaction() as sess:
        sess["user_id"] = SA_ID
        sess["role"] = "superadmin"
        sess["org_id"] = None
        sess["dept_id"] = None


def _inject_org_admin(client):
    with client.session_transaction() as sess:
        sess["user_id"] = OA_ID
        sess["role"] = "org_admin"
        sess["org_id"] = ORG_ID
        sess["dept_id"] = None


# ─── Test (a): dept_admin with org_id and dept_id returns success ──────────────

def test_create_dept_admin_with_dept_returns_success(client, tmp_data):
    """Superadmin can create a dept_admin when dept_id is provided."""
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    rv = client.post(
        "/api/users",
        json={
            "username": "new_da_sadm07",
            "password": "password123",
            "role": "dept_admin",
            "org_id": ORG_ID,
            "dept_id": DEPT_ID,
        },
        content_type="application/json",
    )
    assert rv.status_code != 403, (
        f"Superadmin creating dept_admin must not return 403, got {rv.status_code}: {rv.get_json()}"
    )
    assert rv.status_code in (200, 201), (
        f"Expected success status, got {rv.status_code}: {rv.get_json()}"
    )
    data = rv.get_json()
    assert "id" in data, f"Response must contain 'id', got: {data}"


# ─── Test (b): dept_admin without dept_id returns 400 ─────────────────────────

def test_create_dept_admin_without_dept_returns_400(client, tmp_data):
    """Creating a dept_admin without dept_id must return 400 (T-10-02 server-side guard)."""
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    rv = client.post(
        "/api/users",
        json={
            "username": "bad_da_sadm07",
            "password": "password123",
            "role": "dept_admin",
            "org_id": ORG_ID,
            # dept_id intentionally omitted
        },
        content_type="application/json",
    )
    assert rv.status_code == 400, (
        f"dept_admin without dept_id must return 400, got {rv.status_code}: {rv.get_json()}"
    )
    data = rv.get_json()
    assert "error" in data, f"Response must contain 'error' key, got: {data}"


# ─── Test (c): role=employee returns 403 ─────────────────────────────────────

def test_create_employee_role_returns_403(client, tmp_data):
    """Superadmin may NOT create an employee-role account via /api/users (T-10-01)."""
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    rv = client.post(
        "/api/users",
        json={
            "username": "bad_emp_sadm07",
            "password": "password123",
            "role": "employee",
            "org_id": ORG_ID,
        },
        content_type="application/json",
    )
    assert rv.status_code == 403, (
        f"Superadmin creating employee role must return 403, got {rv.status_code}: {rv.get_json()}"
    )


# ─── Test (d): hr_viewer with org_id returns success ─────────────────────────

def test_create_hr_viewer_returns_success(client, tmp_data):
    """Superadmin can create an hr_viewer account (SADM-07)."""
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    rv = client.post(
        "/api/users",
        json={
            "username": "new_hrv_sadm07",
            "password": "password123",
            "role": "hr_viewer",
            "org_id": ORG_ID,
        },
        content_type="application/json",
    )
    assert rv.status_code != 403, (
        f"Superadmin creating hr_viewer must not return 403, got {rv.status_code}: {rv.get_json()}"
    )
    assert rv.status_code in (200, 201), (
        f"Expected success status, got {rv.status_code}: {rv.get_json()}"
    )
    data = rv.get_json()
    assert "id" in data, f"Response must contain 'id', got: {data}"


# ─── Test (e): GET /api/superadmin/employees returns roster to superadmin ─────

def test_superadmin_employees_returns_roster(client, tmp_data):
    """GET /api/superadmin/employees returns 200 and items with name, org_name, dept_name, face_enrolled."""
    _seed_base(tmp_data, client)
    seed_employees(tmp_data, {
        "emp-sadm02-1": {
            "id": "emp-sadm02-1",
            "name": "Иванов Иван",
            "role": "employee",
            "label": 1,
            "face_count": 5,
            "registered_at": "2026-01-10T10:00:00",
            "org_id": ORG_ID,
            "dept_id": DEPT_ID,
        }
    })
    _inject_superadmin(client)

    rv = client.get("/api/superadmin/employees")
    assert rv.status_code == 200, (
        f"GET /api/superadmin/employees must return 200 for superadmin, got {rv.status_code}"
    )
    data = rv.get_json()
    assert isinstance(data, list), f"Response must be a list, got: {type(data)}"
    assert len(data) >= 1, "Roster must contain at least the seeded employee"

    item = data[0]
    for key in ("name", "org_name", "dept_name", "face_enrolled"):
        assert key in item, f"Each roster item must contain key '{key}', got keys: {list(item.keys())}"

    emp = next((e for e in data if e["name"] == "Иванов Иван"), None)
    assert emp is not None, "Seeded employee 'Иванов Иван' must appear in the roster"
    assert emp["org_name"] == "SADM07 Org", f"org_name mismatch: {emp['org_name']}"
    assert emp["dept_name"] == "SADM07 Dept", f"dept_name mismatch: {emp['dept_name']}"
    assert emp["face_enrolled"] is True, f"face_enrolled must be True for face_count=5, got: {emp['face_enrolled']}"


# ─── Test (f): org_admin gets 403 from /api/superadmin/employees ─────────────

def test_superadmin_employees_rejects_org_admin(client, tmp_data):
    """GET /api/superadmin/employees must return 403 for org_admin (T-10-03)."""
    _seed_base(tmp_data, client)
    _inject_org_admin(client)

    rv = client.get("/api/superadmin/employees")
    assert rv.status_code == 403, (
        f"GET /api/superadmin/employees must return 403 for org_admin, got {rv.status_code}"
    )
