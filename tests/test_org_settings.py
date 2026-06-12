"""
Phase 5 Plan 05 — ORG-SETTINGS-01, ORG-SETTINGS-02
Tests for PATCH /api/orgs/<org_id>/settings:
  - bcrypt PIN storage for kiosk_pin and reg_pin
  - 4-digit PIN validation
  - reg_token regeneration (regen_reg_token)
  - reg_token_expires set and clear
  - kiosk_display_name editable
  - org_admin scope: foreign org -> 403
"""
import bcrypt
import pytest

from tests.conftest import seed_users, seed_orgs, BCRYPT_HASH_SUPERADMIN


# ─── Shared fixtures ──────────────────────────────────────────────────────────

ORG_A_ID = "org-settings-a"
ORG_B_ID = "org-settings-b"
USER_ID = "uid-org-admin-settings"


def _seed(tmp_data, client):
    """Seed two orgs + one org_admin (scoped to org A) and inject session."""
    seed_orgs(tmp_data, {
        ORG_A_ID: {
            "id": ORG_A_ID,
            "name": "Org Alpha",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
            "org_token": "aabbccdd",
            "reg_token": "11223344",
            "kiosk_pin": bcrypt.hashpw(b"0000", bcrypt.gensalt()).decode(),
            "reg_pin": bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode(),
            "reg_token_expires": None,
            "kiosk_display_name": "Alpha Kiosk",
        },
        ORG_B_ID: {
            "id": ORG_B_ID,
            "name": "Org Beta",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
            "org_token": "eeff0011",
            "reg_token": "55667788",
            "kiosk_pin": bcrypt.hashpw(b"0000", bcrypt.gensalt()).decode(),
            "reg_pin": bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode(),
            "reg_token_expires": None,
            "kiosk_display_name": "Beta Kiosk",
        },
    })
    seed_users(tmp_data, {
        USER_ID: {
            "id": USER_ID,
            "username": "orgadmin_settings",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "org_admin",
            "active": True,
            "org_id": ORG_A_ID,
            "dept_id": None,
        }
    })
    with client.session_transaction() as sess:
        sess["user_id"] = USER_ID
        sess["role"] = "org_admin"
        sess["org_id"] = ORG_A_ID
        sess["dept_id"] = None


# ─── ORG-SETTINGS-01: bcrypt PIN storage ──────────────────────────────────────

def test_kiosk_pin_stored_as_bcrypt(client, tmp_data):
    """PATCH {kiosk_pin:'5678'} -> 200; stored kiosk_pin is a bcrypt hash that verifies '5678'."""
    _seed(tmp_data, client)

    rv = client.patch(
        f"/api/orgs/{ORG_A_ID}/settings",
        json={"kiosk_pin": "5678"},
        content_type="application/json",
    )
    assert rv.status_code == 200, f"Expected 200, got {rv.status_code}: {rv.get_json()}"

    import app as _app
    orgs = _app.load_orgs()
    stored = orgs[ORG_A_ID]["kiosk_pin"]
    assert stored.startswith("$2b$"), f"kiosk_pin must be bcrypt hash, got: {stored!r}"
    assert bcrypt.checkpw(b"5678", stored.encode()), "bcrypt.checkpw('5678') must be True"


def test_reg_pin_stored_as_bcrypt(client, tmp_data):
    """PATCH {reg_pin:'4321'} -> 200; stored reg_pin is a bcrypt hash that verifies '4321'."""
    _seed(tmp_data, client)

    rv = client.patch(
        f"/api/orgs/{ORG_A_ID}/settings",
        json={"reg_pin": "4321"},
        content_type="application/json",
    )
    assert rv.status_code == 200, f"Expected 200, got {rv.status_code}: {rv.get_json()}"

    import app as _app
    orgs = _app.load_orgs()
    stored = orgs[ORG_A_ID]["reg_pin"]
    assert stored.startswith("$2b$"), f"reg_pin must be bcrypt hash, got: {stored!r}"
    assert bcrypt.checkpw(b"4321", stored.encode()), "bcrypt.checkpw('4321') must be True"


# ─── ORG-SETTINGS-01: PIN validation ──────────────────────────────────────────

def test_invalid_pin_rejected(client, tmp_data):
    """PATCH {kiosk_pin:'12'} -> 400 (must be 4 digits)."""
    _seed(tmp_data, client)

    rv = client.patch(
        f"/api/orgs/{ORG_A_ID}/settings",
        json={"kiosk_pin": "12"},
        content_type="application/json",
    )
    assert rv.status_code == 400, f"Expected 400 for 2-digit PIN, got {rv.status_code}"
    data = rv.get_json()
    assert "error" in data, "Response must contain 'error' key"


# ─── ORG-SETTINGS-01: reg_token regen ────────────────────────────────────────

def test_regen_reg_token(client, tmp_data):
    """PATCH {regen_reg_token:true} -> reg_token changes to a new 8-hex value."""
    _seed(tmp_data, client)

    old_token = "11223344"  # seeded above

    rv = client.patch(
        f"/api/orgs/{ORG_A_ID}/settings",
        json={"regen_reg_token": True},
        content_type="application/json",
    )
    assert rv.status_code == 200, f"Expected 200, got {rv.status_code}: {rv.get_json()}"

    import app as _app
    orgs = _app.load_orgs()
    new_token = orgs[ORG_A_ID]["reg_token"]
    assert new_token != old_token, "reg_token must change after regen"
    assert len(new_token) == 8, f"reg_token must be 8 hex chars, got: {new_token!r}"


# ─── ORG-SETTINGS-01: reg_token_expires set and clear ────────────────────────

def test_set_reg_token_expires(client, tmp_data):
    """PATCH {reg_token_expires:'2026-12-31T00:00:00'} -> stored verbatim.
    PATCH {reg_token_expires:null} -> cleared to None.
    """
    _seed(tmp_data, client)

    # Set expiry
    rv = client.patch(
        f"/api/orgs/{ORG_A_ID}/settings",
        json={"reg_token_expires": "2026-12-31T00:00:00"},
        content_type="application/json",
    )
    assert rv.status_code == 200, f"Expected 200, got {rv.status_code}: {rv.get_json()}"

    import app as _app
    orgs = _app.load_orgs()
    assert orgs[ORG_A_ID]["reg_token_expires"] == "2026-12-31T00:00:00", (
        "reg_token_expires must be stored verbatim"
    )

    # Clear expiry
    rv2 = client.patch(
        f"/api/orgs/{ORG_A_ID}/settings",
        json={"reg_token_expires": None},
        content_type="application/json",
    )
    assert rv2.status_code == 200, f"Expected 200 on clear, got {rv2.status_code}: {rv2.get_json()}"

    orgs2 = _app.load_orgs()
    assert orgs2[ORG_A_ID]["reg_token_expires"] is None, (
        "reg_token_expires must be cleared to None"
    )


# ─── ORG-SETTINGS-02: kiosk_display_name ─────────────────────────────────────

def test_set_display_name(client, tmp_data):
    """PATCH {kiosk_display_name:'Поликлиника №33'} -> stored."""
    _seed(tmp_data, client)

    rv = client.patch(
        f"/api/orgs/{ORG_A_ID}/settings",
        json={"kiosk_display_name": "Поликлиника №33"},
        content_type="application/json",
    )
    assert rv.status_code == 200, f"Expected 200, got {rv.status_code}: {rv.get_json()}"

    import app as _app
    orgs = _app.load_orgs()
    assert orgs[ORG_A_ID]["kiosk_display_name"] == "Поликлиника №33", (
        "kiosk_display_name must be stored as provided"
    )


# ─── ORG-SETTINGS-02: scope gate — foreign org -> 403 ────────────────────────

def test_org_admin_foreign_org_forbidden(client, tmp_data):
    """org_admin scoped to org A PATCH-ing org B -> 403."""
    _seed(tmp_data, client)

    rv = client.patch(
        f"/api/orgs/{ORG_B_ID}/settings",
        json={"kiosk_display_name": "Hijacked"},
        content_type="application/json",
    )
    assert rv.status_code == 403, f"Expected 403 for foreign org PATCH, got {rv.status_code}"
