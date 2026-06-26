---
phase: 09-security-hardening-and-critical-bug-fixes
plan: "03"
subsystem: auth
tags: [csrf, flask-wtf, security, forms]

# Dependency graph
requires:
  - phase: 09-security-hardening-and-critical-bug-fixes
    provides: Flask-Limiter rate limiting from 09-02; SECRET_KEY already enforced
provides:
  - CSRFProtect initialized on the Flask app (WTF_CSRF_CHECK_DEFAULT=False pattern)
  - csrf_token() hidden input in login.html and profile.html
  - Flask-WTF==1.3.0 pinned in requirements.txt
affects:
  - Any future plans adding new browser-form POST routes (must add csrf_token() input)
  - Any future plans adding new JSON /api/* routes (already exempt by default)

# Tech tracking
tech-stack:
  added:
    - Flask-WTF==1.3.0
    - WTForms==3.2.2 (transitive dependency of Flask-WTF)
  patterns:
    - "WTF_CSRF_CHECK_DEFAULT=False: opt-in per-view CSRF enforcement via csrf.protect()"
    - "csrf.protect() called at top of POST branch in HTML-form views only"
    - "csrf_token() Jinja2 hidden input as first child of <form method=POST>"

key-files:
  created: []
  modified:
    - app.py
    - requirements.txt
    - templates/login.html
    - templates/profile.html

key-decisions:
  - "Used WTF_CSRF_CHECK_DEFAULT=False + explicit csrf.protect() instead of decorators to avoid decorating all ~40 /api/* routes"
  - "csrf.protect() called inside the POST branch of login_page and profile_page, not as a decorator, because the rate-limiter decorator is already on login_page"
  - "Flask-WTF 1.3.0 chosen (latest stable, compatible with Flask 3.1)"

patterns-established:
  - "Pattern: New HTML-form POST routes must call csrf.protect() in their POST branch AND add {{ csrf_token() }} to the template"
  - "Pattern: JSON /api/* routes require no CSRF annotation because WTF_CSRF_CHECK_DEFAULT=False"

requirements-completed: [SEC-03]

# Metrics
duration: 15min
completed: 2026-06-26
---

# Phase 09 Plan 03: CSRF Protection Summary

**Flask-WTF CSRFProtect wired with WTF_CSRF_CHECK_DEFAULT=False; /login and /profile form POSTs require a valid csrf_token() while all 40+ JSON /api/* and kiosk routes remain fully exempt**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-26T09:54:00Z
- **Completed:** 2026-06-26T10:09:15Z
- **Tasks:** 3 (Task 1 was human-verify checkpoint, Tasks 2-3 executed)
- **Files modified:** 4

## Accomplishments
- Installed Flask-WTF 1.3.0 and pinned it in requirements.txt
- Wired `CSRFProtect(app)` with `WTF_CSRF_CHECK_DEFAULT=False` so JSON routes are never checked
- Added explicit `csrf.protect()` in the POST branch of `login_page` and `profile_page`
- Added `{{ csrf_token() }}` hidden input to login.html and profile.html forms
- Verified: POST /login without token returns 400 with "CSRF token is missing"; POST /api/recognize returns 400 with "image required" (own validation, not CSRF)

## Task Commits

Each task was committed atomically:

1. **Task 1: Verify flask-wtf package legitimacy** - Human-verified checkpoint (no code commit)
2. **Task 2: Install Flask-WTF, init CSRFProtect, exempt JSON API** - `520fbca` (feat)
3. **Task 3: Add csrf_token() to HTML forms** - `ca12b59` (feat)

**Plan metadata:** `(docs commit — see below)`

## Files Created/Modified
- `app.py` - Added CSRFProtect import, WTF_CSRF_CHECK_DEFAULT=False config, csrf = CSRFProtect(app), csrf.protect() in login and profile POST branches
- `requirements.txt` - Added Flask-WTF==1.3.0 pin
- `templates/login.html` - Added hidden csrf_token input as first child of <form method="POST">
- `templates/profile.html` - Added hidden csrf_token input as first child of <form method="POST">

## Decisions Made
- **WTF_CSRF_CHECK_DEFAULT=False over per-route @csrf.exempt:** With ~40 JSON /api/* routes and only 2 HTML form routes, opt-in enforcement is safer and cleaner than decorating every JSON route with @csrf.exempt.
- **csrf.protect() in POST branch (not as decorator):** The /login route already has @limiter.limit() as a decorator; calling csrf.protect() inside the function avoids decorator ordering complexity and keeps the check explicit.
- **Flask-WTF 1.3.0:** Latest stable release, fully compatible with Flask 3.1.3.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Test verification with `import app` and `DATABASE_URL=sqlite:///data/app.db` failed when using a relative path. Fixed by using the actual absolute path `/var/www/sites/face-almgp33/data/app.db` (no DB modification needed; tests ran against production DB read-only).

## Known Stubs

None.

## Threat Flags

No new threat surface introduced. This plan exclusively adds defensive controls at existing trust boundaries.

## User Setup Required

None - no external service configuration required. Run `pm2 restart face-recognition` to deploy.

## Next Phase Readiness
- CSRF protection active on the two browser-form routes; all JSON/kiosk routes unaffected
- Any new HTML form that does a non-JSON browser POST to a new route must: (1) call `csrf.protect()` in the POST branch, and (2) include `{{ csrf_token() }}` in the template
- Ready for plan 09-04

---
*Phase: 09-security-hardening-and-critical-bug-fixes*
*Completed: 2026-06-26*
