"""
Auth requirement tests for Phase 1 RBAC Foundation.

Covers requirements: AUTH-01, AUTH-02, AUTH-04, AUTH-06, AUTH-07, MIG-03

Most tests are @pytest.mark.xfail because the underlying code (load_users, init_users,
require_role, updated login handler) is created in plans 01-02/01-03/01-04.
The test stubs are real — they have genuine assertions and will turn GREEN once each
plan implements the corresponding feature.
"""
import json
import pytest

from tests.conftest import BCRYPT_HASH_SUPERADMIN, seed_users, seed_config


# ─── AUTH-01: Valid bcrypt login succeeds; invalid login fails ─────────────────

@pytest.mark.xfail(reason="implemented in 01-02: login handler not yet upgraded to users.json")
def test_login_valid(client, tmp_data):
    """AUTH-01: A valid username+password pair in users.json results in a 302 redirect;
    invalid credentials return the login page with an error."""
    import app as _app

    user_id = "test-uid-superadmin"
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

    # Valid login should redirect
    rv = client.post("/login", data={"username": "superadmin", "password": "superadmin123"},
                     follow_redirects=False)
    assert rv.status_code == 302, f"Expected redirect on valid login, got {rv.status_code}"

    # Invalid password should return 200 (login page) not redirect
    client2 = _app.app.test_client()
    with _app.app.test_request_context():
        pass
    rv_bad = client.post("/login", data={"username": "superadmin", "password": "wrongpass"},
                          follow_redirects=False)
    assert rv_bad.status_code == 200, f"Expected login page on bad credentials, got {rv_bad.status_code}"


# ─── AUTH-02: init_users() bootstraps superadmin when users.json absent ────────

@pytest.mark.xfail(reason="implemented in 01-02: init_users() not yet in app.py")
def test_init_users_bootstrap(client, tmp_data):
    """AUTH-02: When data/users.json does not exist and config.json has no hash,
    init_users() creates a superadmin account with username='superadmin'."""
    import app as _app

    # Ensure users.json does not exist
    users_path = tmp_data / "data" / "users.json"
    assert not users_path.exists(), "Precondition: users.json must not exist before bootstrap"

    # Seed config.json with no password_hash so init_users() creates a fresh one
    seed_config(tmp_data, {"username": "admin"})

    _app.init_users()

    assert users_path.exists(), "init_users() must create users.json"
    users = json.loads(users_path.read_text(encoding="utf-8"))
    assert len(users) == 1, "Bootstrap must create exactly one account"
    user = next(iter(users.values()))
    assert user["username"] == "superadmin", "Bootstrap account username must be 'superadmin'"
    assert user["role"] == "superadmin", "Bootstrap account role must be 'superadmin'"
    assert user["active"] is True, "Bootstrap account must be active"
    assert user.get("password_hash"), "Bootstrap account must have a password_hash"


# ─── MIG-03: Hash from config.json copied verbatim (not re-hashed) ─────────────

@pytest.mark.xfail(reason="implemented in 01-02: init_users() not yet in app.py")
def test_init_users_migrates_hash(client, tmp_data):
    """MIG-03: When data/users.json does not exist and config.json contains an existing
    bcrypt hash, init_users() copies that hash verbatim without re-hashing it."""
    import app as _app

    # Ensure users.json does not exist
    users_path = tmp_data / "data" / "users.json"
    assert not users_path.exists(), "Precondition: users.json must not exist"

    # config.json already has BCRYPT_HASH_SUPERADMIN (seeded by tmp_data fixture)
    _app.init_users()

    assert users_path.exists(), "init_users() must create users.json"
    users = json.loads(users_path.read_text(encoding="utf-8"))
    user = next(iter(users.values()))

    # The hash must be copied byte-for-byte — no re-hash
    assert user["password_hash"] == BCRYPT_HASH_SUPERADMIN, (
        f"MIG-03: password_hash must be copied verbatim.\n"
        f"  Expected: {BCRYPT_HASH_SUPERADMIN}\n"
        f"  Got:      {user['password_hash']}"
    )


# ─── AUTH-04: Session stores user_id, role, org_id, dept_id after login ────────

@pytest.mark.xfail(reason="implemented in 01-02: login handler not yet upgraded to set new session keys")
def test_session_contents(client, tmp_data):
    """AUTH-04: After a successful login, the Flask session must contain
    user_id, role, org_id, and dept_id (org_id/dept_id are None in Phase 1)."""
    import app as _app

    user_id = "test-uid-session"
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

    with client.session_transaction() as pre_session:
        pre_session.clear()

    rv = client.post("/login", data={"username": "superadmin", "password": "superadmin123"},
                     follow_redirects=False)
    assert rv.status_code == 302, "Successful login should redirect"

    with client.session_transaction() as sess:
        assert "user_id" in sess, "Session must contain 'user_id' after login"
        assert "role" in sess, "Session must contain 'role' after login"
        assert "org_id" in sess, "Session must contain 'org_id' after login (None for Phase 1)"
        assert "dept_id" in sess, "Session must contain 'dept_id' after login (None for Phase 1)"
        assert sess["user_id"] == user_id
        assert sess["role"] == "superadmin"
        assert sess["org_id"] is None
        assert sess["dept_id"] is None


# ─── AUTH-06: Password change with correct current password succeeds ────────────

@pytest.mark.xfail(reason="implemented in 01-04: /profile route and password change not yet built")
def test_password_change(client, tmp_data):
    """AUTH-06: A logged-in user can change their password by providing the correct
    current password. Wrong current password is rejected."""
    import app as _app
    import bcrypt

    user_id = "test-uid-pwchange"
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

    # Log in first
    client.post("/login", data={"username": "superadmin", "password": "superadmin123"})

    # Change password with correct current password
    rv = client.post(
        "/profile",
        data={
            "current_password": "superadmin123",
            "new_password": "newpassword456",
            "confirm_password": "newpassword456",
        }
    )
    assert rv.status_code in (200, 302), f"Password change should return 200 or redirect, got {rv.status_code}"

    # Verify new password works — load updated users.json
    if hasattr(_app, "load_users"):
        users = _app.load_users()
        updated_hash = users[user_id]["password_hash"].encode()
        assert bcrypt.checkpw(b"newpassword456", updated_hash), "New password hash must verify correctly"

    # Wrong current password must be rejected
    rv_bad = client.post(
        "/profile",
        data={
            "current_password": "wrongcurrent",
            "new_password": "newpassword456",
            "confirm_password": "newpassword456",
        }
    )
    assert rv_bad.status_code in (200, 400), "Wrong current password should not return redirect"


# ─── AUTH-07: Deactivated user login attempt is rejected ────────────────────────

@pytest.mark.xfail(reason="implemented in 01-02: login handler not yet upgraded to check active flag")
def test_deactivated_user(client, tmp_data):
    """AUTH-07: A user with active=False must not be able to log in, even with a
    correct username and password combination."""
    import app as _app

    user_id = "test-uid-deactivated"
    seed_users(tmp_data, {
        user_id: {
            "id": user_id,
            "username": "deactivated_user",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "viewer",
            "active": False,
            "org_id": None,
            "dept_id": None,
        }
    })

    rv = client.post(
        "/login",
        data={"username": "deactivated_user", "password": "superadmin123"},
        follow_redirects=False,
    )
    # Deactivated user must NOT get a redirect to admin or dashboard
    assert rv.status_code == 200, (
        f"Deactivated user login must return login page (200), got {rv.status_code}"
    )
    # The response body should contain the login page (not a redirect)
    assert rv.status_code == 200 or b"login" in rv.data.lower()
