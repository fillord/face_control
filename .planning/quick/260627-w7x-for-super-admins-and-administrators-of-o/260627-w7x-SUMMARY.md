---
phase: quick-260627-w7x
plan: "01"
subsystem: frontend
tags: [users, superadmin, crud, password-reset, delete]
dependency_graph:
  requires: []
  provides: [superadmin-user-password-reset, superadmin-user-delete]
  affects: [templates/superadmin.html]
tech_stack:
  added: []
  patterns: [fetch PATCH, fetch DELETE, inline panel, guard clause validation]
key_files:
  created: []
  modified:
    - templates/superadmin.html
decisions:
  - Frontend-only change: backend PATCH /api/users/<id> and DELETE /api/users/<id> already enforced role hierarchy and self-delete guard; no app.py edit needed
metrics:
  duration: "~3 min"
  completed: "2026-06-27"
---

# Phase quick-260627-w7x Plan 01: Superadmin Users Tab Full CRUD Summary

## One-liner

Added password-reset panel and delete button to the superadmin Users tab, wiring existing PATCH/DELETE backend routes for full CRUD parity with org-admin.

## What Was Built

The superadmin Users tab previously exposed only "create user" and "toggle active". This plan adds:

1. **`#editUserPanel`** — A collapsible card (hidden by default) with a password field and inline error display, scoped to password-only reset. Inserted directly after `#createUserPanel`.
2. **`openEditUserPanel(userId)`** — Finds the user in `allUsers`, populates the panel heading and resets the field, then un-hides the panel.
3. **`closeEditUserPanel()`** — Re-hides the panel.
4. **`saveUserPassword()`** — Validates min-8-char constraint client-side, then `PATCH /api/users/<id>` with `{password}`. Shows inline error on failure; closes panel and refreshes list on success.
5. **`deleteUser(userId, username)`** — `confirm()` dialog, then `DELETE /api/users/<id>`. Shows `alert(data.error)` on server rejection (handles self-delete guard); refreshes list on success.
6. **Row buttons** — "Изменить пароль" (`btn-edit` class) and "Удалить" (red danger style, `border:#ef9a9a; color:#c62828`) added alongside the existing toggle button in every user row.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Add password-reset panel, reset handler, and delete button | 3b5274d | templates/superadmin.html |

## Checkpoint Pending

Task 2 is a `checkpoint:human-verify` requiring manual testing of the live UI. The automated verification (`grep` for 4 function definitions, `editUserPanel` element, and `method: 'DELETE'`) passed.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. No new network endpoints or auth paths introduced; changes are frontend-only, calling existing backend routes that already enforce role-hierarchy and self-delete guards.

## Self-Check: PASSED

- `templates/superadmin.html` — FOUND (modified, committed at 3b5274d)
- Commit 3b5274d — FOUND in git log
- All 4 JS functions present: `openEditUserPanel`, `closeEditUserPanel`, `saveUserPassword`, `deleteUser`
- `editUserPanel` element present in HTML
- `method: 'DELETE'` present in JS
