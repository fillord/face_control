---
phase: 05-token-based-kiosk-registration-russian-ui
plan: "05"
subsystem: org-settings
tags: [bcrypt, pin, reg-token, tdd, org-admin, russian-ui]
dependency_graph:
  requires: [05-01, 05-03, 05-04]
  provides: [update_org_settings-bcrypt, org-admin-settings-panel]
  affects: [app.py, templates/org_admin.html, tests/test_org_settings.py]
tech_stack:
  added: []
  patterns: [bcrypt-pin-hashing, token-uniqueness-loop, tdd-red-green, jinja2-template-context]
key_files:
  created:
    - tests/test_org_settings.py
  modified:
    - app.py
    - templates/org_admin.html
decisions:
  - "update_org_settings stores kiosk_pin and reg_pin as bcrypt hashes via hash_pin() from 05-01; plaintext storage removed"
  - "regen_reg_token builds a seen-set of all org_token+reg_token values before calling generate_unique_token() to prevent cross-field collisions"
  - "reg_token_expires validated via datetime.fromisoformat() before storage; returns 400 on malformed ISO string"
  - "org_admin_page now passes org_id, org_token, reg_token, reg_token_expires, kiosk_display_name to template so settings panel renders live URLs on load"
  - "settings panel uses ORG_ID const from Jinja2 context so all fetch calls target the caller's own org — no arbitrary id from URL"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-12"
  tasks_completed: 2
  tasks_total: 3
  files_created: 1
  files_modified: 2
---

# Phase 05 Plan 05: Org Settings — bcrypt PINs, Token Regen, Expiry, Display Name Summary

**One-liner:** Upgraded PATCH /api/orgs/<org_id>/settings to store kiosk/reg PINs as bcrypt hashes, regenerate reg_token, set/clear expiry, and edit kiosk display name — with an org_admin dashboard settings panel showing live kiosk and registration URLs.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 (RED) | Failing tests for update_org_settings upgrade | e8fd2db | Done |
| 1 (GREEN) | Upgrade update_org_settings + org_admin_page context | e457807 | Done |
| 2 | org_admin Настройки киоска panel | ce9fc04 | Done |
| 3 | Checkpoint: human verification | — | Awaiting human |

## What Was Built

### Task 1 — update_org_settings upgrade (TDD)

**TDD cycle:**
- RED commit `e8fd2db`: 7 failing tests in `tests/test_org_settings.py`
- GREEN commit `e457807`: implementation passes all 7 tests

**app.py changes:**

`update_org_settings` (PATCH /api/orgs/<org_id>/settings) now handles:
- `kiosk_pin`: 4-digit validation; stores `hash_pin(pin)` (bcrypt) when non-empty, else `None`. Replaces previous plaintext storage.
- `reg_pin`: same validation and bcrypt storage as kiosk_pin.
- `regen_reg_token`: when truthy, builds seen-set of all existing org_token+reg_token values, calls `generate_unique_token()`, stores new reg_token on the org record.
- `reg_token_expires`: validates via `datetime.fromisoformat()` (returns 400 on failure); stores the ISO string or `None` when cleared.
- `kiosk_display_name`: stores trimmed string (allows empty — falls back to name at render time).
- Response: `{"status": "updated", "reg_token": "<current_token>"}` so the UI can refresh the displayed link after regen.

`org_admin_page` now passes to the template: `org_id`, `org_token`, `reg_token`, `reg_token_expires`, `kiosk_display_name` in addition to the existing `org_name`.

**tests/test_org_settings.py — 7 tests:**
- `test_kiosk_pin_stored_as_bcrypt` — PATCH {kiosk_pin:"5678"} -> bcrypt hash verifying "5678"
- `test_reg_pin_stored_as_bcrypt` — PATCH {reg_pin:"4321"} -> bcrypt hash verifying "4321"
- `test_invalid_pin_rejected` — PATCH {kiosk_pin:"12"} -> 400
- `test_regen_reg_token` — PATCH {regen_reg_token:true} -> new 8-hex token distinct from old
- `test_set_reg_token_expires` — set ISO string stored; null clears to None
- `test_set_display_name` — PATCH {kiosk_display_name:"Поликлиника №33"} -> stored
- `test_org_admin_foreign_org_forbidden` — org A admin PATCHing org B -> 403

### Task 2 — org_admin.html Настройки киоска panel (ce9fc04)

Added a third tab "Настройки киоска" to `org_admin.html` with:
- **Live URL display**: read-only inputs showing `/kiosk/<org_token>` and `/register/<reg_token>` with copy buttons. Values rendered server-side from Jinja2 context on page load.
- **PIN change controls**: kiosk_pin and reg_pin fields (4-digit, Russian labels) with save buttons. Client-side 4-digit validation before PATCH.
- **Token regen button**: "Сгенерировать новую ссылку регистрации" — confirms before PATCH; on success updates the `regUrl` input field with the returned `reg_token`.
- **Expiry control**: `datetime-local` input with "Сохранить срок" and "Без срока" (clear) buttons.
- **Display name field**: text input pre-populated from Jinja2 `kiosk_display_name` with save button.

All labels and messages in Russian. The `ORG_ID` JavaScript constant is rendered from the Jinja2 `{{ org_id }}` template variable (the caller's own org_id from session), so all fetch calls are scoped to the caller's own org.

`switchTab()` updated to handle the new `settings` tab/panel.

## Test Results

```
tests/test_org_settings.py — 7 passed in 8.38s
```

## Checkpoint Pending: Human Verification

Task 3 is a `checkpoint:human-verify`. The operator must:
1. `pm2 restart face-recognition`
2. Log in as org_admin -> open "Настройки киоска" tab; confirm kiosk and registration URLs are visible.
3. Change kiosk PIN to 5678, save. Verify 5678 unlocks /kiosk/<token>.
4. Click "Сгенерировать новую ссылку регистрации" -> URL changes; old link 404s.
5. Set past expiry -> /register/<token> shows "Ссылка истекла". Clear -> works.
6. (Backend scope enforcement covered by `test_org_admin_foreign_org_forbidden`.)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All controls call the real API and all live URL fields are populated from actual org token data passed from Flask.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: bcrypt-pin-update | app.py | update_org_settings now enforces bcrypt storage for PIN changes — closes V2 plaintext-storage gap |
| threat_flag: scope-gate | app.py | org_admin can only modify their own org (403 on foreign org) — enforced server-side |

## TDD Gate Compliance

- RED gate: commit `e8fd2db` — `test(05-05): add failing tests for update_org_settings bcrypt/regen/expiry/scope (RED phase)`
- GREEN gate: commit `e457807` — `feat(05-05): upgrade update_org_settings to bcrypt PINs, reg_token regen, expiry, display name; update org_admin_page render context`
- REFACTOR: not required (implementation is clean)

## Self-Check: PASSED

| Item | Status |
|------|--------|
| tests/test_org_settings.py exists | FOUND |
| app.py updated (update_org_settings + org_admin_page) | FOUND |
| templates/org_admin.html has settings panel | FOUND |
| RED commit e8fd2db | FOUND |
| GREEN commit e457807 | FOUND |
| Task 2 commit ce9fc04 | FOUND |
| All 7 tests green | PASSED |
