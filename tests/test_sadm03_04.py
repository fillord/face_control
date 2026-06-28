"""
Tests for SADM-03 (GET /api/superadmin/devices, revoke audit) and
SADM-04 (GET /api/superadmin/logs with filtering).

Coverage:
  (a) GET /api/superadmin/devices returns 200 and items include org_token
  (b) GET /api/superadmin/devices as org_admin returns 403
  (c) GET /api/superadmin/logs returns 200 and at most 500 items
  (d) GET /api/superadmin/logs?event_type=check_in returns only check_in events
  (e) GET /api/superadmin/logs as org_admin returns 403
"""
import pytest
from tests.conftest import (
    BCRYPT_HASH_SUPERADMIN,
    seed_users,
    seed_orgs,
    seed_employees,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

SA_ID = "uid-sa-sadm0304"
OA_ID = "uid-oa-sadm0304"
ORG_ID = "org-sadm0304"
ORG_TOKEN = "tok0304x"


def _seed_base(tmp_data, client):
    """Seed a superadmin, org_admin, and one org shared by all tests."""
    seed_users(tmp_data, {
        SA_ID: {
            "id": SA_ID,
            "username": "sa_sadm0304",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "superadmin",
            "active": True,
            "org_id": None,
            "dept_id": None,
        },
        OA_ID: {
            "id": OA_ID,
            "username": "oa_sadm0304",
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
            "name": "SADM0304 Org",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
            "org_token": ORG_TOKEN,
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


def _seed_device(app, org_id):
    """Insert a KioskDevice row directly via ORM inside an app context."""
    import uuid
    import hashlib
    from datetime import datetime
    from models import db, KioskDevice
    device_id = str(uuid.uuid4())
    raw_token = str(uuid.uuid4())
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with app.app_context():
        db.session.add(KioskDevice(
            id=device_id,
            org_id=org_id,
            device_token_hash=token_hash,
            device_name="Test Kiosk",
            created_at=datetime.now().isoformat(),
            last_seen_at=None,
        ))
        db.session.commit()
    return device_id


def _seed_log_entries(app, emp_id, count, event="check_in"):
    """Insert LogEntry rows directly via ORM inside an app context."""
    from datetime import datetime, timedelta
    from models import db, LogEntry
    with app.app_context():
        for i in range(count):
            db.session.add(LogEntry(
                ts=(datetime.now() - timedelta(seconds=i)).isoformat(),
                event=event,
                emp_id=emp_id,
                name="Test Employee",
                confidence_raw=0.5,
                confidence_pct=50.0,
            ))
        db.session.commit()


# ─── Test (a): GET /api/superadmin/devices returns 200 with org_token ─────────

def test_superadmin_devices_returns_list_with_org_token(client, tmp_data):
    """GET /api/superadmin/devices returns 200 and each item includes org_token."""
    import app as _app
    _seed_base(tmp_data, client)
    _seed_device(_app.app, ORG_ID)
    _inject_superadmin(client)

    rv = client.get("/api/superadmin/devices")
    assert rv.status_code == 200, (
        f"GET /api/superadmin/devices must return 200 for superadmin, got {rv.status_code}"
    )
    data = rv.get_json()
    assert isinstance(data, list), f"Response must be a list, got: {type(data)}"
    assert len(data) >= 1, "Devices list must contain the seeded device"

    item = data[0]
    for key in ("id", "device_name", "org_id", "org_name", "org_token", "created_at"):
        assert key in item, f"Device item must contain '{key}', got keys: {list(item.keys())}"
    assert item["org_token"] == ORG_TOKEN, (
        f"org_token must be '{ORG_TOKEN}', got: {item['org_token']}"
    )
    assert item["org_name"] == "SADM0304 Org", (
        f"org_name must be 'SADM0304 Org', got: {item['org_name']}"
    )


# ─── Test (b): GET /api/superadmin/devices as org_admin returns 403 ───────────

def test_superadmin_devices_rejects_org_admin(client, tmp_data):
    """GET /api/superadmin/devices must return 403 for org_admin (T-10-05)."""
    _seed_base(tmp_data, client)
    _inject_org_admin(client)

    rv = client.get("/api/superadmin/devices")
    assert rv.status_code == 403, (
        f"GET /api/superadmin/devices must return 403 for org_admin, got {rv.status_code}"
    )


# ─── Test (c): GET /api/superadmin/logs returns 200 with at most 500 items ────

def test_superadmin_logs_returns_at_most_500(client, tmp_data):
    """GET /api/superadmin/logs returns 200 and a list of at most 500 items."""
    import app as _app
    _seed_base(tmp_data, client)
    seed_employees(tmp_data, {
        "emp-sadm04-1": {
            "id": "emp-sadm04-1",
            "name": "Log Test Employee",
            "role": "employee",
            "label": 10,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": ORG_ID,
            "dept_id": None,
        }
    })
    # Seed 10 log entries (well under 500, keeps test fast)
    _seed_log_entries(_app.app, "emp-sadm04-1", 10)
    _inject_superadmin(client)

    rv = client.get("/api/superadmin/logs")
    assert rv.status_code == 200, (
        f"GET /api/superadmin/logs must return 200 for superadmin, got {rv.status_code}"
    )
    data = rv.get_json()
    assert isinstance(data, list), f"Response must be a list, got: {type(data)}"
    assert len(data) <= 500, f"Response must contain at most 500 items, got: {len(data)}"
    assert len(data) >= 1, "Response must contain at least the seeded log entries"

    item = data[0]
    for key in ("ts", "event", "name", "org_name", "confidence_pct"):
        assert key in item, f"Log item must contain '{key}', got keys: {list(item.keys())}"


# ─── Test (d): event_type filter returns only matching events ─────────────────

def test_superadmin_logs_event_type_filter(client, tmp_data):
    """GET /api/superadmin/logs?event_type=check_in returns only check_in events."""
    import app as _app
    _seed_base(tmp_data, client)
    seed_employees(tmp_data, {
        "emp-sadm04-2": {
            "id": "emp-sadm04-2",
            "name": "Filter Test Employee",
            "role": "employee",
            "label": 11,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": ORG_ID,
            "dept_id": None,
        }
    })
    _seed_log_entries(_app.app, "emp-sadm04-2", 3, event="check_in")
    _seed_log_entries(_app.app, "emp-sadm04-2", 3, event="check_out")
    _inject_superadmin(client)

    rv = client.get("/api/superadmin/logs?event_type=check_in")
    assert rv.status_code == 200, (
        f"GET /api/superadmin/logs?event_type=check_in must return 200, got {rv.status_code}"
    )
    data = rv.get_json()
    assert isinstance(data, list), f"Response must be a list, got: {type(data)}"
    assert len(data) >= 1, "Filtered result must contain at least one check_in entry"
    non_check_in = [item for item in data if item.get("event") != "check_in"]
    assert not non_check_in, (
        f"All events must be 'check_in', found non-matching: {non_check_in[:3]}"
    )


# ─── Test (e): GET /api/superadmin/logs as org_admin returns 403 ─────────────

def test_superadmin_logs_rejects_org_admin(client, tmp_data):
    """GET /api/superadmin/logs must return 403 for org_admin (T-10-05)."""
    _seed_base(tmp_data, client)
    _inject_org_admin(client)

    rv = client.get("/api/superadmin/logs")
    assert rv.status_code == 403, (
        f"GET /api/superadmin/logs must return 403 for org_admin, got {rv.status_code}"
    )
