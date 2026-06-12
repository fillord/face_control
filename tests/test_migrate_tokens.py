"""
test_migrate_tokens.py — Phase 5 migration unit tests for token/PIN fields.

Tests MIG-TOKEN-01, MIG-TOKEN-02, MIG-TOKEN-03 requirements.
Tests call migrate_org_tokens directly on a dict (unit-level) for fast, isolated testing.
"""
import json
import os
import sys

import bcrypt
import pytest

# Import migrate module directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import migrate


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_org(org_id, name, kiosk_pin=None, reg_pin=None, **extra):
    """Build a minimal org dict matching the D-02 schema."""
    org = {
        "id": org_id,
        "name": name,
        "description": "",
        "created_at": "2026-01-01T00:00:00",
    }
    if kiosk_pin is not None:
        org["kiosk_pin"] = kiosk_pin
    if reg_pin is not None:
        org["reg_pin"] = reg_pin
    org.update(extra)
    return org


# ─── MIG-TOKEN-01: All fields added ───────────────────────────────────────────

def test_migrate_adds_all_fields():
    """MIG-TOKEN-01: After migration every org has all six new token/PIN fields."""
    orgs = {
        "org-A": make_org("org-A", "Главная организация"),
        "org-B": make_org("org-B", "NurLab"),
    }
    migrate.migrate_org_tokens(orgs)

    for org_id, org in orgs.items():
        # org_token: 8 hex chars
        assert "org_token" in org, f"{org_id} missing org_token"
        assert len(org["org_token"]) == 8, f"{org_id} org_token not 8 chars"
        assert all(c in "0123456789abcdef" for c in org["org_token"]), f"{org_id} org_token not hex"

        # reg_token: 8 hex chars
        assert "reg_token" in org, f"{org_id} missing reg_token"
        assert len(org["reg_token"]) == 8, f"{org_id} reg_token not 8 chars"
        assert all(c in "0123456789abcdef" for c in org["reg_token"]), f"{org_id} reg_token not hex"

        # org_token and reg_token must differ within same org
        assert org["org_token"] != org["reg_token"], f"{org_id} org_token == reg_token"

        # kiosk_pin: bcrypt hash
        assert "kiosk_pin" in org, f"{org_id} missing kiosk_pin"
        assert org["kiosk_pin"].startswith("$2b$"), f"{org_id} kiosk_pin not bcrypt"

        # reg_pin: bcrypt hash
        assert "reg_pin" in org, f"{org_id} missing reg_pin"
        assert org["reg_pin"].startswith("$2b$"), f"{org_id} reg_pin not bcrypt"

        # reg_token_expires: None (default)
        assert "reg_token_expires" in org, f"{org_id} missing reg_token_expires"

        # kiosk_display_name: set
        assert "kiosk_display_name" in org, f"{org_id} missing kiosk_display_name"


# ─── MIG-TOKEN-02: Re-hash plaintext PIN ──────────────────────────────────────

def test_migrate_rehashes_plaintext():
    """MIG-TOKEN-02: An org with plaintext kiosk_pin is re-hashed and verifies correctly."""
    orgs = {
        "org-nurlab": make_org("org-nurlab", "NurLab", kiosk_pin="2386"),
    }
    migrate.migrate_org_tokens(orgs)

    org = orgs["org-nurlab"]
    stored = org["kiosk_pin"]
    assert stored.startswith("$2b$"), "plaintext PIN was not re-hashed"
    assert bcrypt.checkpw(b"2386", stored.encode()), "re-hashed PIN does not verify against '2386'"


def test_migrate_hashes_null_default():
    """MIG-TOKEN-02b: An org with kiosk_pin=None gets a bcrypt hash of the default '0000'."""
    orgs = {
        "org-main": make_org("org-main", "Главная организация", kiosk_pin=None),
    }
    migrate.migrate_org_tokens(orgs)

    org = orgs["org-main"]
    stored = org["kiosk_pin"]
    assert stored.startswith("$2b$"), "null PIN was not hashed"
    assert bcrypt.checkpw(b"0000", stored.encode()), "null PIN hash does not verify against '0000'"


# ─── MIG-TOKEN-03: Idempotent ─────────────────────────────────────────────────

def test_migrate_idempotent():
    """MIG-TOKEN-03: Running migration twice does not change already-set token/PIN fields."""
    orgs = {
        "org-A": make_org("org-A", "Главная организация"),
        "org-B": make_org("org-B", "NurLab", kiosk_pin="2386"),
    }
    # First run
    migrate.migrate_org_tokens(orgs)

    # Capture values after first run
    first_run = {
        org_id: {
            "org_token": org["org_token"],
            "reg_token": org["reg_token"],
            "kiosk_pin": org["kiosk_pin"],
            "reg_pin": org["reg_pin"],
        }
        for org_id, org in orgs.items()
    }

    # Second run
    migrate.migrate_org_tokens(orgs)

    # Assert values unchanged
    for org_id, captured in first_run.items():
        org = orgs[org_id]
        assert org["org_token"] == captured["org_token"], f"{org_id} org_token changed on second run"
        assert org["reg_token"] == captured["reg_token"], f"{org_id} reg_token changed on second run"
        assert org["kiosk_pin"] == captured["kiosk_pin"], f"{org_id} kiosk_pin changed on second run"
        assert org["reg_pin"] == captured["reg_pin"], f"{org_id} reg_pin changed on second run"


# ─── kiosk_display_name ───────────────────────────────────────────────────────

def test_migrate_sets_display_name():
    """MIG-TOKEN-01b: kiosk_display_name defaults to org name when absent."""
    orgs = {
        "org-A": make_org("org-A", "Поликлиника №33"),
    }
    migrate.migrate_org_tokens(orgs)

    assert orgs["org-A"]["kiosk_display_name"] == "Поликлиника №33"


def test_migrate_does_not_overwrite_existing_display_name():
    """kiosk_display_name is not overwritten if already set."""
    orgs = {
        "org-A": make_org("org-A", "НурЛаб", kiosk_display_name="Поликлиника №33"),
    }
    migrate.migrate_org_tokens(orgs)

    # Should keep the custom display name, not revert to org name
    assert orgs["org-A"]["kiosk_display_name"] == "Поликлиника №33"
