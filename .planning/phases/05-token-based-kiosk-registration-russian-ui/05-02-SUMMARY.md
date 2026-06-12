---
phase: 05-token-based-kiosk-registration-russian-ui
plan: "02"
subsystem: kiosk-routing
tags: [kiosk, token-routing, bcrypt, touchscreen-pin, tdd]
dependency_graph:
  requires: [05-01]
  provides: [kiosk-token-routes, bcrypt-pin-verify, touchscreen-pin-pad, error-token-page]
  affects: [app.py, templates/kiosk.html, templates/error_token.html, tests/test_kiosk_token.py]
tech_stack:
  added: []
  patterns: [token-lookup, bcrypt-pin-verify, touchscreen-button-pad, tdd-red-green]
key_files:
  created:
    - tests/test_kiosk_token.py
    - templates/error_token.html
    - templates/kiosk.html
  modified:
    - app.py
decisions:
  - "find_org_by_token(orgs, field, value) returns (org_id, org) tuple — reusable for org_token and reg_token lookups"
  - "Old kiosk_org (/kiosk/<org_id>) and verify_kiosk_pin (/api/kiosk/<org_id>/verify_pin) routes fully removed — no redirects"
  - "verify_kiosk_pin_token validates PIN length/digits before bcrypt.checkpw to prevent timing attacks on malformed input"
  - "PIN unlock stored in localStorage keyed by ORG_TOKEN (not ORG_ID) — survives token-based URLs"
  - "Auto-submit on 4th digit pressed for fast touchscreen UX; OK button also available for 4-digit entry"
  - "loadLog() switched from /api/attendance (auth-required) to /api/kiosk_log (public, org-scoped)"
  - "kiosk.html added to worktree from Phase 02-05 version (already has empDept display)"
  - "HTML comment text removed '<input>' string to avoid false positive in plan verification command"
metrics:
  duration: "~21 minutes"
  completed: "2026-06-12"
  tasks_completed: 2
  tasks_total: 3
  files_created: 3
  files_modified: 1
---

# Phase 05 Plan 02: Token-Based Kiosk Routing Summary

**One-liner:** Token-based /kiosk/<org_token> routes with bcrypt PIN verification, touchscreen-only button pad (no keyboard), and Russian error page — old UUID-identity routes removed.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 (RED) | Add failing tests for token-based kiosk routing | a005c68 | Done |
| 1 (GREEN) | Token kiosk routes + bcrypt PIN verify + error_token.html | 99b00d3 | Done |
| 2 | Rebuild kiosk.html PIN entry as touchscreen button pad | a9c85d9 | Done |
| 3 | Checkpoint: human verification of kiosk in browser | — | Awaiting human |

## What Was Built

### Task 1 — Token Routes + Tests (RED: a005c68, GREEN: 99b00d3)

**app.py changes:**
- Added `find_org_by_token(orgs, field, value)` — generic O(n) lookup returning `(org_id, org)` tuple; returns `(None, None)` on miss
- Removed `kiosk_org` route (`/kiosk/<org_id>`) — identity-based UUID routing eliminated
- Added `kiosk_token` route (`/kiosk/<org_token>`):
  - Calls `find_org_by_token(orgs, "org_token", org_token)`
  - Returns `error_token.html` with 404 if not found
  - Passes `org_token`, `org_id`, `org_name` (kiosk_display_name or name), `has_pin` to template
- Removed `verify_kiosk_pin` route (`/api/kiosk/<org_id>/verify_pin`) — plaintext comparison eliminated
- Added `verify_kiosk_pin_token` route (`/api/kiosk/<org_token>/verify_pin`):
  - Resolves org by token (404 if not found)
  - No-PIN orgs return `{verified:true}` immediately
  - Validates PIN: must be exactly 4 digits else 400
  - Uses `bcrypt.checkpw(entered.encode(), stored.encode())` for comparison
  - Returns `{verified:True}` (200) or `{error:"wrong_pin", verified:False}` (401)

**templates/error_token.html** (new):
- Russian error page: МедКонтроль header, light theme (#f4f6fb), `{{ message }}` variable
- Reusable by Plan 05-03 for expired registration tokens

**tests/test_kiosk_token.py** (new):
- `test_valid_org_token` — KIOSK-TOKEN-01: GET /kiosk/abc12345 → 200
- `test_invalid_org_token` — KIOSK-TOKEN-02: GET /kiosk/doesnotexist → 404
- `test_verify_pin_correct` — KIOSK-TOKEN-03: POST verify_pin "4321" → 200 {verified:true}
- `test_verify_pin_wrong` — KIOSK-TOKEN-03: POST verify_pin "0000" → 401 {verified:false}
- `test_verify_pin_unknown_token` — KIOSK-TOKEN-04: POST /api/kiosk/nope/verify_pin → 404
- `test_old_org_id_route_removed` — GET /kiosk/<UUID> → 404 (old route confirmed gone)

### Task 2 — Touchscreen PIN Pad (a9c85d9)

**templates/kiosk.html changes:**
- Added touchscreen PIN screen overlay (`#pinScreen`):
  - `#pinDisplay`: 4 dot spans (#pinDot0-3) filled/empty via CSS class toggle
  - `.pin-grid` CSS Grid (3 columns): `<button>` for 1-9, ⌫ (back), 0, OK — no `<input>` elements
  - 72px tap targets, 26px font — optimized for touchscreen
  - `#pinError` Russian error div: "Неверный PIN-код. Попробуйте снова."
- Added `ORG_TOKEN` JS constant from Jinja2; retained `ORG_ID` constant for /api/recognize
- PIN unlock localStorage key: `kiosk_pin_unlocked_${ORG_TOKEN || 'root'}`
- `pinPress(val)`: digit push (max 4), back pop, ok → submitPin if len===4, auto-submit on 4th digit
- `updatePinDisplay()`: updates dot fill state
- `submitPin()`: POSTs `{pin}` to `/api/kiosk/${ORG_TOKEN}/verify_pin`; on verified → unlockPin(); on fail → show error, clear digits
- `isPinUnlocked()` / `unlockPin()`: localStorage read/write keyed by ORG_TOKEN
- `loadLog()` updated: calls `/api/kiosk_log?org_id=ORG_ID` (public endpoint) instead of `/api/attendance`
- `recognize()` fetch: passes `org_id: ORG_ID` in body (unchanged from Pitfall 7 requirement)
- Dept name: `empDept` element renders `data.dept_name` below employee name on recognition
- Register link: `/login?next=/register` retained; reg_token wiring deferred to plan 05-05 (comment added)

## Checkpoint: Awaiting Human Verification

Task 3 is a `checkpoint:human-verify` — the operator must visually confirm the kiosk works in a browser.

**Verification steps:**
1. `pm2 restart face-recognition` (or run dev server)
2. Get org token: `venv/bin/python -c "import json; o=json.load(open('data/orgs.json')); [print(v['name'], v['org_token']) for v in o.values()]"`
3. `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5051/kiosk/<that_token>` → 200
4. `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5051/kiosk/badtoken` → 404
5. Open `/kiosk/<token>` in browser — confirm PIN pad is on-screen buttons (tapping does NOT raise mobile keyboard)
6. Enter org PIN (default "0000") → camera unlocks
7. Recognize a registered face → confirm department name appears under the name

**Resume signal:** "approved" if kiosk loads by token, PIN pad is keyboard-free, unlocks on correct PIN, and dept name shows.

## Test Results

```
tests/test_kiosk_token.py — 6 passed in 1.26s
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] HTML comment triggered `<input>` false positive in plan's verification script**
- **Found during:** Task 2 verification
- **Issue:** The HTML comment `<!-- PIN screen — touchscreen button pad, no <input> elements -->` contained the literal text `<input>` causing the plan's Python verification check to fail even though no actual `<input>` element existed in the PIN screen
- **Fix:** Changed comment text to `<!-- PIN screen — touchscreen button pad only, keyboard-free -->` removing the `<input>` literal from the comment
- **Files modified:** templates/kiosk.html
- **Commit:** a9c85d9 (included in task commit)

**2. [Rule 2 - Missing] kiosk.html not tracked in worktree**
- **Found during:** Task 1 GREEN phase — `render_template("kiosk.html")` raised TemplateNotFound
- **Issue:** This worktree branched at commit c640797 before kiosk.html was added in Phase 02-05; the template was absent from the worktree's templates/ directory
- **Fix:** Copied kiosk.html from git commit cf263f1 (Phase 02-05 version with empDept display already present). Task 2 then rebuilt the PIN screen on top of it.
- **Files modified:** templates/kiosk.html (created then rebuilt)
- **Commit:** 99b00d3 (GREEN), a9c85d9 (Task 2)

**3. [Rule 2 - Missing] loadLog() called auth-required /api/attendance endpoint**
- **Found during:** Task 2 code review
- **Issue:** The kiosk is public (no auth); calling /api/attendance would fail when session is absent
- **Fix:** Switched loadLog() to call `/api/kiosk_log?org_id=ORG_ID` — the existing public endpoint that accepts an org_id query parameter for org-scoped filtering
- **Files modified:** templates/kiosk.html
- **Commit:** a9c85d9

## Known Stubs

None. All routes are fully wired. The register link at `/login?next=/register` is intentionally kept pointing at the admin flow — Plan 05-05 will wire it to the token-based self-registration flow.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: public-pin-endpoint | app.py | /api/kiosk/<org_token>/verify_pin is unauthenticated — PIN brute-force possible without rate limiting |

Note: Rate limiting on the PIN endpoint is not in scope for this plan. If required, add Flask-Limiter in a future plan.

## TDD Gate Compliance

- RED gate: commit `a005c68` — `test(05-02): add failing tests for token-based kiosk routing (RED phase)`
- GREEN gate: commit `99b00d3` — `feat(05-02): token-based kiosk routes + bcrypt PIN verify + error_token.html (GREEN phase)`
- REFACTOR: not required

## Self-Check: PASSED

| Item | Status |
|------|--------|
| tests/test_kiosk_token.py exists | FOUND |
| templates/error_token.html exists | FOUND |
| templates/kiosk.html exists | FOUND |
| app.py updated | FOUND |
| kiosk_token route present | FOUND (1 occurrence) |
| verify_kiosk_pin_token route present | FOUND (1 occurrence) |
| find_org_by_token helper present | FOUND (1 occurrence) |
| error_token.html contains МедКонтроль | FOUND (2 occurrences) |
| Commit a005c68 (RED) | FOUND |
| Commit 99b00d3 (GREEN Task 1) | FOUND |
| Commit a9c85d9 (Task 2) | FOUND |
| All 6 tests pass | CONFIRMED (6 passed in 1.26s) |
