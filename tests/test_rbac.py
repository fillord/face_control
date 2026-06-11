"""
RBAC requirement tests for Phase 1 RBAC Foundation.

Covers requirements: AUTH-03, AUTH-05, DASH-03

Most tests are @pytest.mark.xfail because the underlying code (require_role decorator,
updated login handler, /dashboard route) is created in plans 01-02/01-03/01-04.

The END-TO-END happy-path test test_post_login_redirect is NOT marked skip; it is
marked xfail so the suite stays green-on-expected-failure while the implementation
is built in later plans.

test_public_routes MUST PASS immediately — the kiosk routes are already public in
the existing app.py.
"""
import pytest

from tests.conftest import BCRYPT_HASH_SUPERADMIN, seed_users


# ─── AUTH-05 (part 1): Unauthenticated /admin redirects to /login ─────────────

def test_unauthenticated_redirect(client):
    """AUTH-05: GET /admin without an active session must redirect to /login.
    This already works in the existing app.py (login_required decorator)."""
    rv = client.get("/admin", follow_redirects=False)
    assert rv.status_code == 302, f"Expected 302 redirect for /admin, got {rv.status_code}"
    location = rv.headers.get("Location", "")
    assert "login" in location, f"Redirect must point to /login, got Location: {location}"


# ─── AUTH-05 (part 2): Public kiosk routes remain accessible without auth ──────

def test_public_routes(client):
    """AUTH-05: GET / must return 200 (kiosk page).
    POST /api/recognize and POST /api/detect must NOT redirect to /login;
    they may return 400 on missing image but never 302."""
    # Kiosk page
    rv_kiosk = client.get("/")
    assert rv_kiosk.status_code == 200, f"GET / must return 200, got {rv_kiosk.status_code}"

    # API recognition — may fail with 400 on missing image but must never redirect to login
    rv_recognize = client.post(
        "/api/recognize",
        json={},
        content_type="application/json",
        follow_redirects=False,
    )
    assert rv_recognize.status_code != 302, (
        f"POST /api/recognize must not redirect to login (got {rv_recognize.status_code})"
    )

    # API detection — same contract
    rv_detect = client.post(
        "/api/detect",
        json={},
        content_type="application/json",
        follow_redirects=False,
    )
    assert rv_detect.status_code != 302, (
        f"POST /api/detect must not redirect to login (got {rv_detect.status_code})"
    )


# ─── AUTH-03: Privilege hierarchy for account creation ────────────────────────

@pytest.mark.xfail(reason="implemented in 01-03: POST /api/users and require_role not yet built")
def test_privilege_hierarchy(client, tmp_data):
    """AUTH-03: A dept_admin can create a viewer account (POST /api/users returns 200 or 201).
    A viewer attempting to create any account is rejected with 403."""
    import app as _app

    dept_admin_id = "test-uid-dept-admin"
    viewer_id = "test-uid-viewer"

    seed_users(tmp_data, {
        dept_admin_id: {
            "id": dept_admin_id,
            "username": "dept_admin_user",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "dept_admin",
            "active": True,
            "org_id": None,
            "dept_id": None,
        },
        viewer_id: {
            "id": viewer_id,
            "username": "viewer_user",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "viewer",
            "active": True,
            "org_id": None,
            "dept_id": None,
        },
    })

    # Log in as dept_admin and create a viewer
    client.post("/login", data={"username": "dept_admin_user", "password": "superadmin123"})
    rv_create = client.post(
        "/api/users",
        json={
            "username": "new_viewer",
            "password": "password123",
            "role": "viewer",
        },
        content_type="application/json",
    )
    assert rv_create.status_code in (200, 201), (
        f"dept_admin must be able to create viewer (expected 200/201, got {rv_create.status_code})"
    )

    # Log out and log in as viewer; viewer must NOT be able to create any account
    client.get("/logout")
    client.post("/login", data={"username": "viewer_user", "password": "superadmin123"})
    rv_forbidden = client.post(
        "/api/users",
        json={
            "username": "new_employee",
            "password": "password123",
            "role": "employee",
        },
        content_type="application/json",
    )
    assert rv_forbidden.status_code == 403, (
        f"viewer must NOT be able to create accounts (expected 403, got {rv_forbidden.status_code})"
    )


# ─── DASH-03: Post-login redirect by role (MVP end-to-end happy-path test) ─────

@pytest.mark.xfail(reason="implemented in 01-02/01-03: login handler and /dashboard not yet built")
def test_post_login_redirect(client, tmp_data):
    """DASH-03 / MVP end-to-end: After login, superadmin must redirect to /admin
    and viewer/employee must redirect to /dashboard.

    This is the defining RED test for Phase 1 — it will turn GREEN once:
    - Plan 01-02 upgrades the login handler to use users.json and sets session keys
    - Plan 01-03 adds the /dashboard route
    """
    superadmin_id = "test-uid-superadmin"
    viewer_id = "test-uid-viewer"

    seed_users(tmp_data, {
        superadmin_id: {
            "id": superadmin_id,
            "username": "superadmin",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "superadmin",
            "active": True,
            "org_id": None,
            "dept_id": None,
        },
        viewer_id: {
            "id": viewer_id,
            "username": "viewer_user",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "viewer",
            "active": True,
            "org_id": None,
            "dept_id": None,
        },
    })

    # superadmin must be redirected to /admin
    rv_admin = client.post(
        "/login",
        data={"username": "superadmin", "password": "superadmin123"},
        follow_redirects=False,
    )
    assert rv_admin.status_code == 302, (
        f"superadmin login must return 302 redirect (got {rv_admin.status_code})"
    )
    location = rv_admin.headers.get("Location", "")
    assert location.endswith("/admin"), (
        f"superadmin must redirect to /admin (got Location: {location})"
    )

    # Log out
    client.get("/logout")

    # viewer must be redirected to /dashboard
    rv_dashboard = client.post(
        "/login",
        data={"username": "viewer_user", "password": "superadmin123"},
        follow_redirects=False,
    )
    assert rv_dashboard.status_code == 302, (
        f"viewer login must return 302 redirect (got {rv_dashboard.status_code})"
    )
    location_dash = rv_dashboard.headers.get("Location", "")
    assert location_dash.endswith("/dashboard"), (
        f"viewer must redirect to /dashboard (got Location: {location_dash})"
    )
