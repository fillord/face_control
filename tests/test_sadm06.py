"""
Tests for SADM-06: system-wide attendance analytics endpoint.

Coverage:
  (a) GET /api/superadmin/attendance_stats?days=7 returns 200 and a list of length 7
      with items containing date, total_employees, present_count, percent
  (b) On a day where a seeded employee has check_in_time, percent is > 0
  (c) days param is clamped — GET with days=1000 returns at most 90 entries
  (d) GET as org_admin returns 403
"""
import pytest
from datetime import date, timedelta
from tests.conftest import (
    BCRYPT_HASH_SUPERADMIN,
    seed_users,
    seed_employees,
    seed_attendance,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

SA_ID = "uid-sa-sadm06"
OA_ID = "uid-oa-sadm06"
ORG_ID = "org-sadm06"
EMP_ID = "emp-sadm06-1"

TODAY = date.today().isoformat()


def _seed_base(tmp_data, client):
    """Seed a superadmin and org_admin for SADM-06 tests."""
    seed_users(tmp_data, {
        SA_ID: {
            "id": SA_ID,
            "username": "sa_sadm06",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "superadmin",
            "active": True,
            "org_id": None,
            "dept_id": None,
        },
        OA_ID: {
            "id": OA_ID,
            "username": "oa_sadm06",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "org_admin",
            "active": True,
            "org_id": ORG_ID,
            "dept_id": None,
        },
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


# ─── Test (a): days=7 returns list of length 7 with correct shape ─────────────

def test_attendance_stats_seven_days(client, tmp_data):
    """GET /api/superadmin/attendance_stats?days=7 returns 200 and 7 items with correct keys."""
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    rv = client.get("/api/superadmin/attendance_stats?days=7")
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list)
    assert len(data) == 7
    for item in data:
        assert "date" in item
        assert "total_employees" in item
        assert "present_count" in item
        assert "percent" in item


# ─── Test (b): percent > 0 when employee has check_in_time ────────────────────

def test_attendance_stats_percent_nonzero_when_checked_in(client, tmp_data):
    """On a day where a seeded employee has check_in_time, percent is > 0."""
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    # Seed one employee
    seed_employees(tmp_data, {
        EMP_ID: {
            "id": EMP_ID,
            "name": "Test Employee SADM06",
            "role": "employee",
            "label": 1,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": ORG_ID,
            "dept_id": None,
        }
    })
    # Seed attendance record for today with check_in_time set
    seed_attendance(tmp_data, [
        {
            "emp_id": EMP_ID,
            "date": TODAY,
            "check_in_time": "09:00:00",
            "check_out_time": None,
            "event_type": "check_in",
        }
    ])

    rv = client.get("/api/superadmin/attendance_stats?days=7")
    assert rv.status_code == 200
    data = rv.get_json()
    # Find today's entry
    today_entry = next((item for item in data if item["date"] == TODAY), None)
    assert today_entry is not None
    assert today_entry["percent"] > 0
    assert today_entry["present_count"] >= 1


# ─── Test (c): days=1000 is clamped to at most 90 entries ─────────────────────

def test_attendance_stats_days_clamped(client, tmp_data):
    """GET with days=1000 returns at most 90 entries (days clamped to 90)."""
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    rv = client.get("/api/superadmin/attendance_stats?days=1000")
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list)
    assert len(data) <= 90
    assert len(data) == 90


# ─── Test (d): GET as org_admin returns 403 ───────────────────────────────────

def test_attendance_stats_403_for_org_admin(client, tmp_data):
    """GET /api/superadmin/attendance_stats as org_admin returns 403."""
    _seed_base(tmp_data, client)
    _inject_org_admin(client)

    rv = client.get("/api/superadmin/attendance_stats?days=7")
    assert rv.status_code == 403
