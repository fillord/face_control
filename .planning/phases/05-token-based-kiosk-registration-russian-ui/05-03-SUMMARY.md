---
phase: 05-token-based-kiosk-registration-russian-ui
plan: "03"
subsystem: registration-routing
tags: [registration, token-routing, bcrypt, login-allowlist, tdd]
dependency_graph:
  requires: [05-02]
  provides: [register-token-routes, bcrypt-reg-pin-verify, login-role-allowlist, register-token-page]
  affects: [app.py, templates/register_token.html, tests/test_reg_token.py, tests/test_auth.py]
tech_stack:
  added: []
  patterns: [is-reg-token-expired, bcrypt-pin-verify, login-role-allowlist, tdd-red-green]
key_files:
  created:
    - tests/test_reg_token.py
    - templates/register_token.html
    - templates/register.html (copied from main repo — was untracked)
    - templates/login.html (copied from main repo — was untracked)
  modified:
    - app.py
    - tests/test_auth.py
decisions:
  - "ALLOWED_LOGIN_ROLES = ('superadmin', 'org_admin', 'dept_admin') placed near ROLE_HIERARCHY per plan"
  - "is_reg_token_expired uses .replace(tzinfo=None) for naive comparison per Research Pitfall 6"
  - "find_org_by_token NOT redefined — already present from 05-02 (plan guard honored)"
  - "register_page admin route kept @require_role-decorated and fully unchanged per Research Pitfall 3"
  - "register.html/login.html copied to worktree from main repo working directory (untracked there)"
  - "register_token.html is standalone public page — uses /api/register/<token>/submit not /api/employees"
  - "dept_id validation in submit: rejects foreign org depts with 400"
metrics:
  duration: "~9 minutes"
  completed: "2026-06-12"
  tasks_completed: 2
  tasks_total: 3
  files_created: 3
  files_modified: 2
---

# Phase 05 Plan 03: Token Registration Routes + Login Allowlist Summary

**One-liner:** Public token-gated registration routes with server-side expiry, bcrypt reg_pin verification, org-scoped employee creation, ALLOWED_LOGIN_ROLES login enforcement, and a mobile Russian PIN-pad registration page.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 (RED) | Add failing tests for token registration routes + AUTH-ROLE-01 | 9cb860b | Done |
| 1 (GREEN) | Token registration routes + login allowlist + templates | 22f6032 | Done |
| 2 | register_token.html: mobile Russian PIN pad + face capture | 22f6032 | Done (included in GREEN commit) |
| 3 | Checkpoint: human verification of token registration on mobile | — | Awaiting human |

## What Was Built

### Task 1 — Backend Routes + Tests (RED: 9cb860b, GREEN: 22f6032)

**app.py changes:**
- Added `ALLOWED_LOGIN_ROLES = ("superadmin", "org_admin", "dept_admin")` constant near `ROLE_HIERARCHY`
- Added `is_reg_token_expired(org)`: reads `org.get("reg_token_expires")`; None/empty -> False; parses ISO datetime, strips tzinfo via `.replace(tzinfo=None)` for naive comparison; malformed -> False
- Updated `login_page` POST: after bcrypt match, checks `role not in ALLOWED_LOGIN_ROLES` -> sets error "Доступ запрещён для этой роли", does NOT set session; only allowed roles proceed to session setup and redirect
- Added `register_token` route (`/register/<reg_token>`): token lookup via `find_org_by_token`, 404 if not found, 410 if expired, else renders `register_token.html` with reg_token, org_id, org_name, has_pin, depts filtered to org
- Added `register_token_verify_pin` route (`/api/register/<reg_token>/verify_pin`): find org (404), expiry check (410), no-PIN -> verified=True, validates 4-digit PIN, bcrypt.checkpw -> 200 or 401
- Added `register_token_submit` route (`/api/register/<reg_token>/submit`): find org (404), expiry (410), validate name+dept membership (400 on foreign dept), creates employee with org_id forced to token's org, saves to employees.json, creates faces dir
- `find_org_by_token` was NOT redefined (already present from 05-02)

**tests/test_reg_token.py** (new):
- `test_valid_reg_token` — REG-TOKEN-01: valid token -> 200
- `test_expired_reg_token` — REG-TOKEN-02: expired token -> 410 with "истекла"
- `test_future_reg_token` — future expiry -> 200
- `test_invalid_reg_token` — REG-TOKEN-03: unknown token -> 404
- `test_reg_verify_pin_correct` — correct bcrypt PIN -> 200 {verified:true}
- `test_reg_verify_pin_wrong` — wrong PIN -> 401 {verified:false}
- `test_reg_submit_creates_employee` — submit creates employee with correct org_id and dept_id
- `test_reg_submit_foreign_dept_rejected` — foreign org dept -> 400
- `test_admin_register_still_works` — authenticated admin GET /register -> 200

**tests/test_auth.py extension:**
- `test_viewer_login_rejected` — AUTH-ROLE-01: viewer role + correct password -> 200 (not redirected), session has no user_id

### Task 2 — register_token.html (committed with Task 1 GREEN: 22f6032)

**templates/register_token.html** (new):
- Mobile-first, max-width 440px, responsive single-column for phones
- lang="ru", title "Регистрация — МедКонтроль", light theme matching register.html
- Phase A PIN screen: `.pin-grid` of 12 `<button>` elements (1-9, backspace, 0, OK) — NO `<input>` in PIN area; #pinDisplay dot row; #pinError Russian error
- Auto-submit on 4th digit; OK button also available
- Phase B form: "ФИО" text input, "Отдел" `<select>` populated from `depts` template context
- Flow: PIN verified -> `/api/register/${REG_TOKEN}/verify_pin` -> form revealed -> submit -> `/api/register/${REG_TOKEN}/submit` -> emp_id -> capture photos -> `/api/register_face` -> success toast "Сотрудник зарегистрирован"
- `const REG_TOKEN = "{{ reg_token }}";` Jinja2 pass-through
- All visible strings Russian; vanilla JS only (no new libraries)
- Plan verify command: `REG_TOKEN in h and 'pin-grid' in h and 'register_face' in h and '<input' not in pin_area` -> REGTOKEN_OK

## Checkpoint: Awaiting Human Verification

Task 3 is a `checkpoint:human-verify`. The operator must visually verify the registration flow in a browser.

**Verification steps:**
1. `pm2 restart face-recognition`
2. Get reg_token: `venv/bin/python -c "import json; o=json.load(open('data/orgs.json')); [print(v['name'], v['reg_token']) for v in o.values()]"`
3. `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5051/register/<reg_token>` -> 200
4. `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5051/register/bad` -> 404
5. On a phone open `/register/<reg_token>`: confirm responsive layout, keyboard-free PIN pad, enter reg_pin (default 1234) -> form appears
6. Register a test employee with a photo -> success message "Сотрудник зарегистрирован"
7. Confirm viewer-role login is rejected (trust test_viewer_login_rejected green)

**Resume signal:** "approved" if token registration works on mobile end-to-end.

## Test Results

```
tests/test_reg_token.py — 9 passed
tests/test_auth.py — 10 passed, 6 xpassed (pre-existing xfail now xpass)
Full suite: 24 passed, 3 xfailed, 15 xpassed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] register.html and login.html not in worktree**
- **Found during:** Task 1 GREEN phase — `render_template("register.html")` raised TemplateNotFound in test_admin_register_still_works
- **Issue:** This worktree branched at commit `316eba4` before `register.html` and `login.html` were added to the main repo working directory; those templates remain untracked in the main repo, not in any git commit
- **Fix:** Copied both files from `/var/www/sites/face-almgp33/templates/` to the worktree. Now tracked in this worktree branch.
- **Files created:** templates/register.html, templates/login.html
- **Commit:** 22f6032 (included in GREEN task commit)

## Known Stubs

None. All routes are fully wired. The face capture flow calls real `/api/register_face` endpoint. No placeholder data or hardcoded responses.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: public-pin-endpoint | app.py | /api/register/<reg_token>/verify_pin is unauthenticated — PIN brute-force without rate limiting (deferred per CONTEXT.md scope) |
| threat_flag: public-submit-unauthenticated | app.py | /api/register/<reg_token>/submit is fully public — valid token is the only gate; rate limiting deferred |

## TDD Gate Compliance

- RED gate: commit `9cb860b` — `test(05-03): add failing tests for token registration routes (RED phase)`
- GREEN gate: commit `22f6032` — `feat(05-03): token registration routes + login role allowlist + templates (GREEN phase)`
- REFACTOR: not required

## Self-Check: PASSED

| Item | Status |
|------|--------|
| tests/test_reg_token.py exists | FOUND |
| templates/register_token.html exists | FOUND |
| templates/register.html exists in worktree | FOUND |
| app.py has is_reg_token_expired | FOUND |
| app.py has ALLOWED_LOGIN_ROLES | FOUND |
| app.py has register_token route | FOUND |
| app.py has register_token_verify_pin route | FOUND |
| app.py has register_token_submit route | FOUND |
| login_page enforces ALLOWED_LOGIN_ROLES | FOUND |
| admin /register route unchanged with @require_role | FOUND |
| Commit 9cb860b (RED) | FOUND |
| Commit 22f6032 (GREEN) | FOUND |
| All 9 test_reg_token tests pass | CONFIRMED (9 passed) |
| test_viewer_login_rejected passes | CONFIRMED |
| Plan verify command REGTOKEN_OK | CONFIRMED |
