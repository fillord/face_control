---
phase: 01-rbac-foundation
plan: "04"
subsystem: auth
tags: [rbac, user-management, password-change, fcntl, api]
dependency_graph:
  requires: ["01-03"]
  provides: [list_users, create_user, update_user, profile_page, fcntl-locking]
  affects: [app.py, templates/admin.html, templates/profile.html]
tech_stack:
  added: [fcntl (stdlib advisory locking)]
  patterns: [hierarchy-index-check, field-whitelisting, bcrypt-re-hash, flock-write]
key_files:
  created:
    - templates/profile.html
  modified:
    - app.py
    - templates/admin.html
decisions:
  - ROLE_DISPLAY dict added as module-level constant in app.py for template + API reuse
  - profile.html created in Task 1 (required for test_password_change to pass) and finalized in Task 2
  - ROLE_HIERARCHY.index() used for both create_user and update_user hierarchy checks (3 calls total)
metrics:
  duration: "~10 minutes"
  completed: "2026-06-11T10:11:26Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase 01 Plan 04: User Management API + Profile Password Change Summary

**One-liner:** Hierarchy-enforced account creation (AUTH-03), soft deactivate/reactivate (AUTH-07), self-service password change (AUTH-06), and fcntl-locked save_users with user management panel in admin.html.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | User management + password-change API with hierarchy enforcement and file locking | 39a4da0 | app.py, templates/profile.html |
| 2 | Build profile.html and the user-management panel in admin.html | 96fa1b7 | templates/admin.html, app.py |

## What Was Built

### app.py additions

- `import fcntl` (separate import line)
- `save_users()` updated with `fcntl.flock(LOCK_EX)` / `fcntl.LOCK_UN` around the JSON write (T-01-04-RACE)
- `ROLE_DISPLAY` dict: maps role keys to Russian display labels
- `GET /api/users` (`list_users`): returns user list with password_hash stripped (T-01-04-LEAK)
- `POST /api/users` (`create_user`): whitelisted fields (username/password/role only), unique username check, password >= 8 chars, ROLE_HIERARCHY.index() hierarchy enforcement, bcrypt hash (T-01-04-ESC, T-01-04-MASS, T-01-04-PWLEN)
- `PATCH /api/users/<user_id>` (`update_user`): 404 guard, hierarchy check on caller vs target, active flag toggle (AUTH-07)
- `GET/POST /profile` (`profile_page`): current password verification, new != confirm check, len >= 8, bcrypt re-hash on success (AUTH-06)
- `admin_page()` updated to compute and pass `creatable_roles` (list of (key, label) tuples below the session user's role)

### templates/profile.html (new)

Password change form following login.html shell pattern. Admin-style header with logo, username badge, kiosk link, logout. `.card` with h2 "Смена пароля", `.sub`, success banner (green E8F5E9/1B5E20), `.error` banner, three password fields (current_password, new_password, confirm_password), `.btn` "Сменить пароль".

### templates/admin.html additions

- `panelUsers` tab panel (Jinja2-gated: `{% if session.role in ['superadmin', 'org_admin', 'dept_admin'] %}`)
- `createUserPanel` hidden card with Логин/Пароль inputs + Роль select (options from `creatable_roles`)
- Users table with thead Логин/Роль/Статус/Действия; empty state with Russian copy
- `ROLE_NAMES` JS object for client-side role display names
- `switchTab()` updated to handle users tab + call `loadUsers()` on switch
- `loadUsers()`: fetches GET /api/users, renders rows with badge-present/badge-absent and action buttons
- `toggleCreateForm()`, `createUser()`, `deactivateUser()`, `reactivateUser()` in vanilla JS (camelCase per conventions)
- Deactivate uses `window.confirm()` with exact copy from Copywriting Contract

## Test Results

All 10 tests pass:

```
XXXXXX..XX (2 passed, 8 xpassed)
```

Previously xfail tests now XPASSED (implementation complete):
- `test_privilege_hierarchy` (AUTH-03) — XPASSED
- `test_password_change` (AUTH-06) — XPASSED
- `test_deactivated_user` (AUTH-07) — XPASSED (was already XPASSED from 01-02, confirmed still passing)

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| ROLE_DISPLAY added as module-level constant | DRY: used by both admin_page() template context and future API responses |
| profile.html created in Task 1 (not Task 2) | test_password_change requires the template to return 200; Task 2 acceptance criteria verified it was complete |
| Separate `import fcntl` line | Acceptance criteria requires `grep -c "import fcntl" app.py` == 1; combined import line would fail that check |
| `fcntl.LOCK_UN` after dump (before close) | Lock releases on close regardless; explicit unlock is defensive best practice |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] profile.html created in Task 1 to satisfy test dependency**

- **Found during:** Task 1 verification
- **Issue:** `test_password_change` calls `POST /profile` which renders `profile.html`; without the template the test raises `TemplateNotFound` (xfail due to actual exception, not assertion failure). Task 2 was planned to create the template, but Task 1's verification required it.
- **Fix:** Created `templates/profile.html` as part of Task 1 implementation. Task 2 verified the template met the full UI-SPEC.
- **Files modified:** templates/profile.html
- **Commit:** 39a4da0

## Known Stubs

None — all routes are fully implemented with real validation and data.

## Threat Flags

No new threat surface beyond what is covered in the plan's threat model. All T-01-04-* mitigations implemented:

| Mitigation | Status |
|-----------|--------|
| T-01-04-ESC (elevation of privilege) | ROLE_HIERARCHY.index() check in create_user and update_user |
| T-01-04-MASS (mass assignment) | Whitelist: only username/password/role accepted; grep gate: 0 `.update(request.json)` calls |
| T-01-04-LEAK (password hash leak) | list_users builds response dict without password_hash field |
| T-01-04-RACE (concurrent write) | fcntl.flock(LOCK_EX) in save_users |
| T-01-04-PWLEN (weak password) | min length 8 enforced in create_user and profile_page |

## Self-Check: PASSED

Files created/modified:
- app.py — modified (tasks 1+2) — FOUND
- templates/profile.html — created (task 1) — FOUND
- templates/admin.html — modified (task 2) — FOUND
- .planning/phases/01-rbac-foundation/01-04-SUMMARY.md — created — FOUND

Commits:
- 39a4da0 — Task 1 (feat: user management API, profile password change, fcntl locking)
- 96fa1b7 — Task 2 (feat: user management panel in admin.html + creatable_roles)
- e6db284 — Metadata (docs: complete user management + password change plan)
