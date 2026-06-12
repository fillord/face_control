"""
Tests for Plan 05-03: token-based employee self-registration.

Covers requirements:
  REG-TOKEN-01: GET /register/<valid_token> -> 200
  REG-TOKEN-02: GET /register/<expired_token> -> 410 with Russian "истекла"
  REG-TOKEN-03: GET /register/<unknown_token> -> 404
  REG-TOKEN-04: POST /api/register/<token>/verify_pin -> 200 {verified:true} on correct bcrypt PIN
  REG-TOKEN-05: POST /api/register/<token>/verify_pin -> 401 on wrong PIN
  REG-TOKEN-06: POST /api/register/<token>/submit creates employee scoped to token's org
  REG-TOKEN-07: Logged-in admin GET /register still returns 200 (unchanged route)
"""
import json
import time
import pytest
import bcrypt
from datetime import datetime, timedelta

from tests.conftest import (
    BCRYPT_HASH_SUPERADMIN,
    seed_users, seed_orgs, seed_depts, seed_employees,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────

REG_TOKEN = "reg00001"
ORG_ID = "org-reg-test"
DEPT_ID = "dept-reg-test"
REG_PIN_PLAIN = "1234"
REG_PIN_HASH = bcrypt.hashpw(REG_PIN_PLAIN.encode(), bcrypt.gensalt()).decode()


def _seed_reg_org(tmp_data, reg_token_expires=None):
    """Seed a single org with a reg_token and bcrypt reg_pin."""
    seed_orgs(tmp_data, {
        ORG_ID: {
            "id": ORG_ID,
            "name": "Тестовая клиника",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
            "org_token": "orgtoken1",
            "reg_token": REG_TOKEN,
            "kiosk_pin": bcrypt.hashpw(b"0000", bcrypt.gensalt()).decode(),
            "reg_pin": REG_PIN_HASH,
            "reg_token_expires": reg_token_expires,
            "kiosk_display_name": "Тестовая клиника",
        }
    })
    seed_depts(tmp_data, {
        DEPT_ID: {
            "id": DEPT_ID,
            "org_id": ORG_ID,
            "name": "Терапия",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })


# ─── REG-TOKEN-01: valid reg_token (no expiry) -> 200 ────────────────────────

def test_valid_reg_token(client, tmp_data):
    """REG-TOKEN-01: GET /register/<valid, non-expired reg_token> returns 200."""
    _seed_reg_org(tmp_data, reg_token_expires=None)
    rv = client.get(f"/register/{REG_TOKEN}")
    assert rv.status_code == 200, (
        f"Expected 200 for valid reg_token, got {rv.status_code}"
    )
    body = rv.data.decode("utf-8")
    assert REG_TOKEN in body, "Response should contain the reg_token constant"


# ─── REG-TOKEN-02: expired reg_token -> 410 with Russian message ──────────────

def test_expired_reg_token(client, tmp_data):
    """REG-TOKEN-02: GET /register/<expired_token> returns 410; body contains 'истекла'."""
    past = (datetime.now() - timedelta(hours=1)).isoformat()
    _seed_reg_org(tmp_data, reg_token_expires=past)
    rv = client.get(f"/register/{REG_TOKEN}")
    assert rv.status_code == 410, (
        f"Expected 410 for expired reg_token, got {rv.status_code}"
    )
    body = rv.data.decode("utf-8")
    assert "истекла" in body, (
        f"Expected Russian 'истекла' in response body for expired token, got: {body[:300]}"
    )


# ─── REG-TOKEN-03: future reg_token_expires -> 200 ───────────────────────────

def test_future_reg_token(client, tmp_data):
    """Future reg_token_expires should be treated as valid (not yet expired)."""
    future = (datetime.now() + timedelta(days=7)).isoformat()
    _seed_reg_org(tmp_data, reg_token_expires=future)
    rv = client.get(f"/register/{REG_TOKEN}")
    assert rv.status_code == 200, (
        f"Expected 200 for future reg_token_expires, got {rv.status_code}"
    )


# ─── REG-TOKEN-04: unknown reg_token -> 404 ──────────────────────────────────

def test_invalid_reg_token(client, tmp_data):
    """REG-TOKEN-03: GET /register/<unknown> returns 404."""
    _seed_reg_org(tmp_data)
    rv = client.get("/register/nope")
    assert rv.status_code == 404, (
        f"Expected 404 for unknown reg_token, got {rv.status_code}"
    )


# ─── REG-TOKEN-05: verify_pin correct -> 200 {verified:true} ─────────────────

def test_reg_verify_pin_correct(client, tmp_data):
    """REG-TOKEN-04: POST /api/register/<token>/verify_pin with correct PIN -> 200 {verified:true}."""
    _seed_reg_org(tmp_data)
    rv = client.post(
        f"/api/register/{REG_TOKEN}/verify_pin",
        json={"pin": REG_PIN_PLAIN},
    )
    assert rv.status_code == 200, (
        f"Expected 200 for correct PIN, got {rv.status_code}"
    )
    data = rv.get_json()
    assert data.get("verified") is True, f"Expected verified=True, got {data}"


# ─── REG-TOKEN-06: verify_pin wrong -> 401 ───────────────────────────────────

def test_reg_verify_pin_wrong(client, tmp_data):
    """REG-TOKEN-05: POST /api/register/<token>/verify_pin with wrong PIN -> 401."""
    _seed_reg_org(tmp_data)
    rv = client.post(
        f"/api/register/{REG_TOKEN}/verify_pin",
        json={"pin": "9999"},
    )
    assert rv.status_code == 401, (
        f"Expected 401 for wrong PIN, got {rv.status_code}"
    )
    data = rv.get_json()
    assert data.get("verified") is False, f"Expected verified=False, got {data}"


# ─── REG-TOKEN-07: submit creates employee scoped to org ─────────────────────

def test_reg_submit_creates_employee(client, tmp_data):
    """REG-TOKEN-06: POST /api/register/<token>/submit creates employee with org_id == token's org."""
    _seed_reg_org(tmp_data)
    seed_employees(tmp_data, {})  # start with empty employees
    rv = client.post(
        f"/api/register/{REG_TOKEN}/submit",
        json={"name": "Иван Петров", "dept_id": DEPT_ID},
    )
    assert rv.status_code == 200, (
        f"Expected 200 from submit, got {rv.status_code}: {rv.data}"
    )
    data = rv.get_json()
    assert "id" in data, f"Expected 'id' in response, got {data}"
    assert data.get("status") == "created", f"Expected status=created, got {data}"

    # Verify employee was created with correct org_id
    import app as _app
    employees = _app.load_employees()
    emp_id = data["id"]
    assert emp_id in employees, f"Employee {emp_id} not found in employees.json"
    assert employees[emp_id]["org_id"] == ORG_ID, (
        f"Employee org_id should be {ORG_ID}, got {employees[emp_id]['org_id']}"
    )
    assert employees[emp_id]["dept_id"] == DEPT_ID, (
        f"Employee dept_id should be {DEPT_ID}, got {employees[emp_id]['dept_id']}"
    )


# ─── REG-TOKEN-08: submit with foreign dept -> 400 ───────────────────────────

def test_reg_submit_foreign_dept_rejected(client, tmp_data):
    """Submit with a dept_id not belonging to the token's org should be rejected (400)."""
    _seed_reg_org(tmp_data)
    seed_depts(tmp_data, {
        DEPT_ID: {
            "id": DEPT_ID,
            "org_id": ORG_ID,
            "name": "Терапия",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        },
        "other-dept": {
            "id": "other-dept",
            "org_id": "other-org",
            "name": "Чужой отдел",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_employees(tmp_data, {})
    rv = client.post(
        f"/api/register/{REG_TOKEN}/submit",
        json={"name": "Иван Петров", "dept_id": "other-dept"},
    )
    assert rv.status_code == 400, (
        f"Expected 400 for foreign dept, got {rv.status_code}: {rv.data}"
    )


# ─── REG-TOKEN-09: admin /register unchanged ─────────────────────────────────

def test_admin_register_still_works(client, tmp_data):
    """REG-TOKEN-07: Logged-in admin GET /register returns 200 (existing route unchanged)."""
    user_id = "test-uid-admin"
    seed_users(tmp_data, {
        user_id: {
            "id": user_id,
            "username": "superadmin",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "superadmin",
            "active": True,
            "org_id": None,
            "dept_id": None,
        }
    })
    seed_orgs(tmp_data, {})
    seed_depts(tmp_data, {})
    # Log in as superadmin
    client.post("/login", data={"username": "superadmin", "password": "superadmin123"})
    rv = client.get("/register")
    assert rv.status_code == 200, (
        f"Authenticated admin GET /register should return 200, got {rv.status_code}"
    )
