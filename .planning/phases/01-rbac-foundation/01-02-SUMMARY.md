---
phase: 01-rbac-foundation
plan: "02"
subsystem: auth
tags: [auth, rbac, users, session, bootstrap, migration]
dependency_graph:
  requires: ["01-01"]
  provides: [USERS_FILE, load_users, save_users, init_users, ROLE_HIERARCHY, require_role, dashboard_page]
  affects: [app.py, templates/dashboard.html, templates/403.html, tests/conftest.py]
tech_stack:
  added: [uuid (stdlib)]
  patterns: [require_role decorator factory, verbatim hash migration, role-based redirect, session-fixation mitigation]
key_files:
  created:
    - templates/dashboard.html
    - templates/403.html
  modified:
    - app.py
    - tests/conftest.py
decisions:
  - "Login page GET-only redirect guard: session.get('user_id') guard now applies only to GET requests so that a client can POST invalid credentials after a valid session without being redirected (test_login_valid requirement)"
  - "conftest BCRYPT_HASH_SUPERADMIN corrected to superadmin123 hash; prior value was the admin123 hash from config.json — test intent was always superadmin123"
metrics:
  duration: "4 minutes"
  completed: "2026-06-11"
  tasks_completed: 2
  files_modified: 4
---

# Phase 01 Plan 02: Walking Skeleton Auth Summary

JWT-free bcrypt auth with users.json bootstrap, 5-role hierarchy, @require_role decorator factory, role-based post-login routing, and minimal /dashboard + 403.html templates.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add users.json store, bootstrap migration, @require_role | 079d9c8 | app.py |
| 2 | Upgrade login handler; add /dashboard, 403.html, dashboard.html | 31a14a1 | app.py, templates/dashboard.html, templates/403.html, tests/conftest.py |

## What Was Built

### Task 1: Auth infrastructure

- `USERS_FILE` constant added to the file-constants block
- `import uuid` added to the imports line
- `load_users()` / `save_users()` following the load_config/save_config pattern
- `init_users()` with MIG-03 verbatim hash copy: reads `config.json` → copies `password_hash` without calling `bcrypt.hashpw` again; falls back to fresh superadmin123 hash only when config has no hash
- `ROLE_HIERARCHY = ['superadmin', 'org_admin', 'dept_admin', 'viewer', 'employee']`
- `require_role(*allowed_roles)` decorator factory with D-05 three-check order: (1) session.user_id present → redirect /login, (2) user active → session.clear + redirect /login, (3) role in allowed_roles → 403.html with 403 status
- `init_users()` called at startup after `init_config()`

### Task 2: Login handler + UI pages

- `login_page()` upgraded: uses `load_users()` + bcrypt.checkpw against users.json; sets 4 session keys (user_id, role, org_id, dept_id) after session.clear() (T-01-02-SF); role-based redirect (admin/org_admin/dept_admin → /admin, viewer/employee → /dashboard); deactivated user gets separate Russian error string
- `/dashboard` route added: `@require_role()` (any authenticated active user); passes username to template
- `templates/dashboard.html`: admin.html-style header + login.html-style card; Jinja2 `{% if %}` chain for Russian role display names
- `templates/403.html`: login.html shell + role-aware back link via Jinja2

## Test Results

All plan-targeted tests pass (xpassed):

```
tests/test_auth.py::test_login_valid          XPASS
tests/test_auth.py::test_init_users_bootstrap XPASS
tests/test_auth.py::test_init_users_migrates_hash XPASS
tests/test_auth.py::test_session_contents     XPASS
tests/test_auth.py::test_deactivated_user     XPASS
tests/test_rbac.py::test_post_login_redirect  XPASS
```

Remaining xfail tests (future plans): `test_password_change` (01-04), `test_privilege_hierarchy` (01-03).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed conftest BCRYPT_HASH_SUPERADMIN constant**
- **Found during:** Task 2 verification
- **Issue:** `BCRYPT_HASH_SUPERADMIN` in tests/conftest.py was set to the admin123 hash from data/config.json (`$2b$12$F0kP...`). Auth tests POST with `password="superadmin123"` against this hash, causing bcrypt.checkpw to return False and test_login_valid to fail.
- **Fix:** Changed `BCRYPT_HASH_SUPERADMIN` to a freshly generated bcrypt hash of "superadmin123" (`$2b$12$aiT8...`). The MIG-03 test still passes because tmp_data seeds config.json with this constant and init_users() copies it verbatim.
- **Files modified:** tests/conftest.py
- **Commit:** 31a14a1

**2. [Rule 1 - Bug] Login page GET-only redirect guard**
- **Found during:** Task 2 verification — test_login_valid sends two consecutive POSTs; second (wrong-password) POST on an already-authenticated session triggered the early redirect guard
- **Issue:** Original plan described `if session.get("user_id"): return redirect(...)` without method gating; after first successful login the guard fired on the second POST
- **Fix:** Changed guard to `if request.method == "GET" and session.get("user_id")`. GET navigating to /login when already logged in still redirects; POST always processes credentials
- **Files modified:** app.py
- **Commit:** 31a14a1

## Threat Model Compliance

| Threat ID | Status |
|-----------|--------|
| T-01-02-SF | Mitigated: session.clear() before writing new session keys in login_page() |
| T-01-02-PW | Mitigated: bcrypt.checkpw(password, user["password_hash"].encode()) |
| T-01-02-RH | Mitigated: init_users() copies hash verbatim; hashpw only in fallback branch |
| T-01-02-AC | Mitigated: inactive user → session.clear() + redirect to /login (not 403) |
| T-01-02-SK | Accepted (deferred to 01-04) |

## Known Stubs

The `/dashboard` placeholder message "Ваш личный кабинет будет доступен в следующем обновлении." is intentional per plan D-09. It is not a bug — it fulfills the DASH-03 requirement that viewer/employee have a post-login landing page. Full dashboard functionality is out of Phase 1 scope.

## Self-Check: PASSED

- app.py: exists, contains USERS_FILE, ROLE_HIERARCHY, require_role, init_users, dashboard_page
- templates/403.html: exists, contains "403"
- templates/dashboard.html: exists, contains placeholder message
- Commits 079d9c8 and 31a14a1 exist in git log
