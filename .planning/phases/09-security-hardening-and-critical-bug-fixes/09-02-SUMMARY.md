---
phase: 09-security-hardening-and-critical-bug-fixes
plan: "02"
subsystem: auth
tags: [flask-limiter, rate-limiting, brute-force-protection, sec-01, sec-02]

# Dependency graph
requires:
  - phase: 09-security-hardening-and-critical-bug-fixes
    plan: "01"
    provides: "Phase foundation (SQLAlchemy models, sec cookie hardening)"
provides:
  - "Flask-Limiter brute-force protection on POST /login — 5 per 15 min per IP (SEC-01)"
  - "PIN verify rate-limit 10 per 15 min + registration token locked on breach (SEC-02)"
affects: [app.py, requirements.txt]

# Tech tracking
tech-stack:
  added: [Flask-Limiter==4.1.1, limits==5.8.0]
  patterns:
    - "Module-level Limiter with empty default_limits (kiosk-safe — no global throttle)"
    - "429 handler branching on request.path: HTML for /login, JSON for /api/*"
    - "Token lock-on-breach: 429 handler extracts reg_token from path, sets reg_token_expires to past"

key-files:
  created: []
  modified:
    - app.py
    - requirements.txt

key-decisions:
  - "flask-limiter package legitimacy required human verification before install (blocking-human gate) — approved by user"
  - "In-memory storage (no Redis) — single PM2 worker, bounded keyspace, acceptable for v1 per T-09-06"
  - "Flask-Limiter 4.1.1 installed (latest stable, 4.x released after plan was written with >=3.0,<4.0 pin — pinned to exact installed version)"
  - "Token lock implemented in 429 handler using path regex rather than on_breach callback (simpler, no extra Flask-Limiter hooks)"

patterns-established:
  - "Rate limit only explicitly decorated routes (default_limits=[] protects kiosk)"
  - "Shared 429 handler dispatches by path prefix to serve both HTML and JSON clients"

requirements-completed: [SEC-01, SEC-02]

# Metrics
duration: 15min
completed: 2026-06-26
---

# Phase 09 Plan 02: Brute-Force Protection (Flask-Limiter) Summary

**One-liner:** Flask-Limiter 4.1.1 wired with in-memory storage; POST /login throttled to 5/15 min with Russian 429 page; PIN verify throttled to 10/15 min with token lockout on breach.

## Performance

- **Duration:** ~15 min (Tasks 2-3 after human-approved Task 1 gate)
- **Started:** 2026-06-26T09:47:26Z (Task 1 checkpoint)
- **Resumed:** 2026-06-26 (continuation after user approved flask-limiter)
- **Completed:** 2026-06-26
- **Tasks:** 3/3 completed (Task 1 = human-verify gate, Tasks 2-3 = implementation)
- **Files modified:** 2 (app.py, requirements.txt)

## Accomplishments

- **Task 1 (human-verify gate):** User confirmed flask-limiter on PyPI is the legitimate package (maintainer "alisaifee", MIT license). Approved.
- **Task 2 (SEC-01):** Installed Flask-Limiter==4.1.1, pinned in requirements.txt. Wired `Limiter(key_func=get_remote_address, app=app, storage_uri="memory://", default_limits=[])` after `db.init_app(app)`. Decorated `login_page` with `@limiter.limit("5 per 15 minutes", methods=["POST"])`. Added `@app.errorhandler(429)` that renders `login.html` with Russian error for HTML paths and returns JSON for `/api/` paths.
- **Task 3 (SEC-02):** Decorated `register_token_verify_pin` with `@limiter.limit("10 per 15 minutes", methods=["POST"])`. The 429 handler locks the registration token by setting `org.reg_token_expires` to `(datetime.now() - timedelta(days=1)).isoformat()` — subsequent requests get HTTP 410 link_expired from `is_reg_token_expired`.

## Task Commits

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Verify flask-limiter package legitimacy | (checkpoint — no code) | none |
| 2 | Flask-Limiter wiring + /login rate limit (SEC-01) | `9c00188` | app.py, requirements.txt |
| 3 | PIN verify rate limit + token lockout (SEC-02) | `b6b9a8e` | app.py |

## Files Created/Modified

| File | Change |
|------|--------|
| `requirements.txt` | Added `Flask-Limiter==4.1.1` pin |
| `app.py` | Added imports, `limiter` instance, `@limiter.limit` on login_page and register_token_verify_pin, `@app.errorhandler(429)` with token-lock logic |

## Decisions Made

1. **Flask-Limiter 4.1.1 pinned** — Plan specified `>=3.0,<4.0` but pip resolved to 4.1.1 (latest stable). Pinned to exact installed version for reproducibility. API compatible; import OK confirmed.
2. **Token lock in 429 handler** — Implemented via path-regex in the shared 429 handler rather than a per-route `on_breach` callback. Simpler, fewer moving parts, same effect: when flask-limiter fires 429 for verify_pin, handler extracts token from URL, sets `reg_token_expires` to yesterday, commits.
3. **`default_limits=[]`** — Ensures kiosk routes (`/`, `/api/recognize`, `/api/detect`) are never throttled. Rate limits apply only to explicitly decorated routes.

## Deviations from Plan

### Auto-handled differences

**1. [Rule 1 - Deviation] Flask-Limiter 4.1.1 installed instead of 3.x**
- **Found during:** Task 2 install
- **Issue:** Plan specified `>=3.0,<4.0` but pip resolved to 4.1.1 (no 3.x in range available at install time; Flask-Limiter 4.x is now the stable release)
- **Fix:** Verified API compatibility (`from flask_limiter import Limiter; from flask_limiter.util import get_remote_address` — OK). Pinned `Flask-Limiter==4.1.1` (exact) rather than the range from the plan. Import test and behavioral test both pass.
- **Files modified:** requirements.txt

## Verification Results

All plan acceptance criteria passed:

- `pip show flask-limiter` returns Name: Flask-Limiter, Version: 4.1.1
- `grep -ci 'flask-limiter' requirements.txt` = 1
- `grep -c 'limiter.limit("5 per 15 minutes"' app.py` = 1 (decorates login_page)
- `grep -c 'errorhandler(429)' app.py` = 1
- `grep -c 'limiter.limit("10 per 15 minutes"' app.py` = 1 (decorates register_token_verify_pin)
- `reg_token_expires` token-lock present in 429 handler
- Kiosk routes have no limiter decorator
- Behavioral: 6th POST /login returns HTTP 429 with Russian message (confirmed via test_client)
- `venv/bin/python -c "import app"` exits 0

## Known Stubs

None — all implemented functionality is fully wired.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes beyond those in the plan's threat model.

## Self-Check: PASSED

- `app.py` exists and imports cleanly
- `requirements.txt` updated with Flask-Limiter pin
- Commits `9c00188` and `b6b9a8e` exist in git log
- All plan acceptance criteria verified

---
*Phase: 09-security-hardening-and-critical-bug-fixes*
*Completed: 2026-06-26*
