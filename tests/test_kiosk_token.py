"""
Tests for token-based kiosk routing and bcrypt PIN verification.
Requirements: KIOSK-TOKEN-01, KIOSK-TOKEN-02, KIOSK-TOKEN-03, KIOSK-TOKEN-04

These tests verify:
  - GET /kiosk/<org_token> resolves by org_token field (not org UUID key)
  - GET /kiosk/<unknown_token> returns 404 with error page
  - POST /api/kiosk/<org_token>/verify_pin with correct PIN returns {verified:true}
  - POST /api/kiosk/<org_token>/verify_pin with wrong PIN returns 401 {verified:false}
  - POST /api/kiosk/<unknown_token>/verify_pin returns 404
  - Old /kiosk/<org_id> identity route is removed (raw UUID returns 404)
"""
import json
import bcrypt
import pytest
from tests.conftest import seed_orgs


ORG_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
ORG_TOKEN = "abc12345"
ORG_PIN_PLAIN = "4321"


def _make_org(kiosk_pin_plain=None):
    """Build a minimal org record with org_token and optional bcrypt kiosk_pin."""
    pin_hash = bcrypt.hashpw(kiosk_pin_plain.encode(), bcrypt.gensalt()).decode() if kiosk_pin_plain else None
    return {
        ORG_ID: {
            "id": ORG_ID,
            "name": "Тестовая клиника",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
            "org_token": ORG_TOKEN,
            "reg_token": "reg99999",
            "kiosk_pin": pin_hash,
            "reg_pin": None,
            "reg_token_expires": None,
            "kiosk_display_name": "Тестовая клиника",
        }
    }


# ─── KIOSK-TOKEN-01: GET /kiosk/<org_token> → 200 ────────────────────────────

def test_valid_org_token(client, tmp_data):
    """GET /kiosk/<valid org_token> returns 200 and renders the kiosk page."""
    seed_orgs(tmp_data, _make_org())
    resp = client.get(f"/kiosk/{ORG_TOKEN}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data[:300]}"
    body = resp.data.decode("utf-8")
    # The kiosk page must contain the core camera section marker
    assert "МедКонтроль" in body or "kiosk" in body.lower() or "camera" in body.lower(), \
        "Response body does not look like the kiosk page"


# ─── KIOSK-TOKEN-02: GET /kiosk/<unknown token> → 404 ────────────────────────

def test_invalid_org_token(client, tmp_data):
    """GET /kiosk/<unknown token> returns 404."""
    seed_orgs(tmp_data, _make_org())
    resp = client.get("/kiosk/doesnotexist")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# ─── KIOSK-TOKEN-03: PIN verify correct → 200 {verified:true} ────────────────

def test_verify_pin_correct(client, tmp_data):
    """POST /api/kiosk/<token>/verify_pin with correct PIN returns 200 {verified:true}."""
    seed_orgs(tmp_data, _make_org(kiosk_pin_plain=ORG_PIN_PLAIN))
    resp = client.post(
        f"/api/kiosk/{ORG_TOKEN}/verify_pin",
        data=json.dumps({"pin": ORG_PIN_PLAIN}),
        content_type="application/json",
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    body = resp.get_json()
    assert body.get("verified") is True, f"Expected verified=true, got {body}"


# ─── KIOSK-TOKEN-03: PIN verify wrong → 401 {verified:false} ─────────────────

def test_verify_pin_wrong(client, tmp_data):
    """POST /api/kiosk/<token>/verify_pin with wrong PIN returns 401 {verified:false}."""
    seed_orgs(tmp_data, _make_org(kiosk_pin_plain=ORG_PIN_PLAIN))
    resp = client.post(
        f"/api/kiosk/{ORG_TOKEN}/verify_pin",
        data=json.dumps({"pin": "0000"}),
        content_type="application/json",
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.data}"
    body = resp.get_json()
    assert body.get("verified") is False, f"Expected verified=false, got {body}"


# ─── KIOSK-TOKEN-04: PIN verify unknown token → 404 ──────────────────────────

def test_verify_pin_unknown_token(client, tmp_data):
    """POST /api/kiosk/<unknown token>/verify_pin returns 404."""
    seed_orgs(tmp_data, _make_org())
    resp = client.post(
        "/api/kiosk/nope/verify_pin",
        data=json.dumps({"pin": "0000"}),
        content_type="application/json",
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.data}"


# ─── Old identity route removed ───────────────────────────────────────────────

def test_old_org_id_route_removed(client, tmp_data):
    """GET /kiosk/<raw org UUID> returns 404 — old identity-based route is removed."""
    seed_orgs(tmp_data, _make_org())
    # ORG_ID is a real UUID key in orgs.json but should NOT be routable via /kiosk/<org_id>
    resp = client.get(f"/kiosk/{ORG_ID}")
    assert resp.status_code == 404, (
        f"Expected 404 for old org_id route, got {resp.status_code}. "
        "The old /kiosk/<org_id> route must be removed and replaced with token-based routing."
    )
