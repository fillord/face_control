"""
Tests for SADM-05: DB-backed working holiday calendar.

Coverage:
  (a) POST /api/holidays with a valid date/name returns success; GET returns the row
  (b) POST with an invalid date string returns 400
  (c) POST a duplicate date returns 409
  (d) DELETE /api/holidays/<date> removes it; subsequent GET omits it
  (e) After inserting a holiday for a year, get_holidays_set(year) returns a set containing that date
  (f) compute_symbol returns В for that holiday date given a work-day schedule + holidays_set
  (g) GET /api/holidays as org_admin returns 403
"""
import pytest
from datetime import date
from tests.conftest import (
    BCRYPT_HASH_SUPERADMIN,
    seed_users,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

SA_ID = "uid-sa-sadm05"
OA_ID = "uid-oa-sadm05"
ORG_ID = "org-sadm05"

HOLIDAY_DATE = "2026-06-15"
HOLIDAY_YEAR = 2026
HOLIDAY_NAME = "Тестовый праздник"


def _seed_base(tmp_data, client):
    """Seed a superadmin and org_admin for SADM-05 tests."""
    seed_users(tmp_data, {
        SA_ID: {
            "id": SA_ID,
            "username": "sa_sadm05",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "superadmin",
            "active": True,
            "org_id": None,
            "dept_id": None,
        },
        OA_ID: {
            "id": OA_ID,
            "username": "oa_sadm05",
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


# ─── Test (a): POST valid holiday; GET returns it ─────────────────────────────

def test_add_holiday_success_and_get(client, tmp_data):
    """POST /api/holidays with valid date/name returns 201; GET retrieves it for that year."""
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    rv = client.post(
        "/api/holidays",
        json={"date": HOLIDAY_DATE, "name": HOLIDAY_NAME},
    )
    assert rv.status_code == 201, (
        f"POST /api/holidays must return 201 for valid input, got {rv.status_code}: {rv.data}"
    )
    created = rv.get_json()
    assert created["date"] == HOLIDAY_DATE, f"Response date must be {HOLIDAY_DATE}"
    assert created["name"] == HOLIDAY_NAME, f"Response name must be {HOLIDAY_NAME}"

    # GET the holiday back
    rv_get = client.get(f"/api/holidays?year={HOLIDAY_YEAR}")
    assert rv_get.status_code == 200, (
        f"GET /api/holidays must return 200, got {rv_get.status_code}"
    )
    data = rv_get.get_json()
    assert isinstance(data, list), "GET /api/holidays must return a list"
    dates = [item["date"] for item in data]
    assert HOLIDAY_DATE in dates, (
        f"GET /api/holidays?year={HOLIDAY_YEAR} must include {HOLIDAY_DATE}, got: {dates}"
    )


# ─── Test (b): POST with invalid date returns 400 ────────────────────────────

def test_add_holiday_invalid_date_returns_400(client, tmp_data):
    """POST /api/holidays with invalid date format returns 400."""
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    rv = client.post(
        "/api/holidays",
        json={"date": "15-06-2026", "name": "Bad Date Format"},
    )
    assert rv.status_code == 400, (
        f"POST with invalid date must return 400, got {rv.status_code}: {rv.data}"
    )
    data = rv.get_json()
    assert "error" in data, "400 response must contain 'error' key"


# ─── Test (c): POST duplicate date returns 409 ───────────────────────────────

def test_add_holiday_duplicate_date_returns_409(client, tmp_data):
    """POST /api/holidays with a duplicate date returns 409."""
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    # First insert
    rv1 = client.post(
        "/api/holidays",
        json={"date": HOLIDAY_DATE, "name": HOLIDAY_NAME},
    )
    assert rv1.status_code == 201, f"First POST must return 201, got {rv1.status_code}"

    # Duplicate insert
    rv2 = client.post(
        "/api/holidays",
        json={"date": HOLIDAY_DATE, "name": "Другое название"},
    )
    assert rv2.status_code == 409, (
        f"Duplicate POST must return 409, got {rv2.status_code}: {rv2.data}"
    )
    data = rv2.get_json()
    assert "error" in data, "409 response must contain 'error' key"


# ─── Test (d): DELETE removes holiday; GET omits it ──────────────────────────

def test_delete_holiday_removes_from_list(client, tmp_data):
    """DELETE /api/holidays/<date> removes it; subsequent GET omits it."""
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    # Insert first
    rv_post = client.post(
        "/api/holidays",
        json={"date": HOLIDAY_DATE, "name": HOLIDAY_NAME},
    )
    assert rv_post.status_code == 201, f"POST must succeed, got {rv_post.status_code}"

    # Delete it
    rv_del = client.delete(f"/api/holidays/{HOLIDAY_DATE}")
    assert rv_del.status_code == 200, (
        f"DELETE /api/holidays/{HOLIDAY_DATE} must return 200, got {rv_del.status_code}: {rv_del.data}"
    )

    # Confirm it's gone
    rv_get = client.get(f"/api/holidays?year={HOLIDAY_YEAR}")
    assert rv_get.status_code == 200
    data = rv_get.get_json()
    dates = [item["date"] for item in data]
    assert HOLIDAY_DATE not in dates, (
        f"After DELETE, {HOLIDAY_DATE} must not appear in GET /api/holidays, got: {dates}"
    )


# ─── Test (e): get_holidays_set returns DB holiday date ───────────────────────

def test_get_holidays_set_returns_db_holiday(client, tmp_data):
    """After inserting a holiday, get_holidays_set(year) returns a set containing that date."""
    import app as _app
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    # Insert via POST endpoint
    rv = client.post(
        "/api/holidays",
        json={"date": HOLIDAY_DATE, "name": HOLIDAY_NAME},
    )
    assert rv.status_code == 201, f"POST must succeed, got {rv.status_code}"

    # get_holidays_set is DB-backed; call it inside app context (already active via client fixture)
    holidays_set = _app.get_holidays_set(HOLIDAY_YEAR)
    assert isinstance(holidays_set, set), "get_holidays_set must return a set"
    assert HOLIDAY_DATE in holidays_set, (
        f"get_holidays_set({HOLIDAY_YEAR}) must contain {HOLIDAY_DATE}, got: {holidays_set}"
    )


# ─── Test (f): compute_symbol returns В for DB holiday date ───────────────────

def test_compute_symbol_returns_v_for_db_holiday(client, tmp_data):
    """compute_symbol returns В for a holiday date when holidays_set contains that date."""
    import app as _app
    _seed_base(tmp_data, client)
    _inject_superadmin(client)

    # HOLIDAY_DATE = "2026-06-15" — a Monday (work day by default schedule)
    holiday_date = date(2026, 6, 15)
    assert holiday_date.isoweekday() == 1, "2026-06-15 must be a Monday (isoweekday=1)"

    # Insert holiday via POST
    rv = client.post(
        "/api/holidays",
        json={"date": HOLIDAY_DATE, "name": HOLIDAY_NAME},
    )
    assert rv.status_code == 201, f"POST must succeed, got {rv.status_code}"

    # Get holidays_set from DB
    holidays_set = _app.get_holidays_set(HOLIDAY_YEAR)
    assert HOLIDAY_DATE in holidays_set, (
        f"holidays_set must contain {HOLIDAY_DATE} before compute_symbol call"
    )

    # Mon–Fri schedule — 2026-06-15 is a Monday, so it would normally be a work day
    schedule = {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}
    # No attendance on that day
    attendance = {}
    overrides = {}

    sym = _app.compute_symbol(holiday_date, "emp-test", attendance, overrides, schedule, holidays_set)
    assert sym == "В", (
        f"compute_symbol must return 'В' for a holiday date, got: {sym!r}"
    )


# ─── Test (g): GET /api/holidays as org_admin returns 403 ────────────────────

def test_list_holidays_rejects_org_admin(client, tmp_data):
    """GET /api/holidays must return 403 for org_admin (T-10-11)."""
    _seed_base(tmp_data, client)
    _inject_org_admin(client)

    rv = client.get(f"/api/holidays?year={HOLIDAY_YEAR}")
    assert rv.status_code == 403, (
        f"GET /api/holidays must return 403 for org_admin, got {rv.status_code}"
    )
