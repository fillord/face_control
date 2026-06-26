---
phase: 09-security-hardening-and-critical-bug-fixes
verified: 2026-06-26T00:00:00Z
status: human_needed
score: 12/12 must-haves verified at code level
overrides_applied: 0
human_verification:
  - test: "Rate-limit per-IP behavior behind nginx (CR-01)"
    expected: "A 6th POST /login from a given attacker IP is rejected with 429 while a second IP that has not exceeded 5 attempts is still served — confirming per-IP isolation, not global isolation"
    why_human: "ProxyFix middleware is absent. Without it, request.remote_addr always equals 127.0.0.1 (the nginx upstream address), collapsing all rate-limit buckets into one global bucket shared by every user. Whether the production nginx passes X-Forwarded-For and whether any other mechanism provides per-IP isolation cannot be determined by grep alone. Must be verified against the live nginx deployment."
  - test: "End-to-end CSRF rejection on /login POST without token"
    expected: "Browser POST to /login with no csrf_token field returns HTTP 400 with CSRF error; the same POST including the value from {{ csrf_token() }} succeeds past the CSRF check"
    why_human: "Test client behavioral check cannot reproduce the full Jinja2 render → form submit → csrf.protect() flow that a real browser executes. Template rendering correctness (csrf_token() generates a valid nonce; the hidden input value round-trips correctly to the server) needs a browser-level or integration test."
---

# Phase 09: Security Hardening and Critical Bug Fixes — Verification Report

**Phase Goal:** Plug the highest-risk security gaps and fix three confirmed bugs: brute-force protection on login and PIN endpoints; CSRF via Flask-WTF; session cookie security flags; configurable LBPH threshold in AppSetting; three hardcoded-"09:00:00" bugs fixed; /health endpoint; KZ_HOLIDAYS extended to 2027; DB backup button; composite index on AttendanceRecord.
**Verified:** 2026-06-26
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All 12 truths are VERIFIED at the code level. Two require live behavioral confirmation (see Human Verification Required section). Review findings CR-01 and CR-08 are known defects introduced by this phase and documented as open items.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Late-arrival flags use each employee's own schedule start (+15 min grace), not a hardcoded 09:00 | VERIFIED | `_time_threshold(start, 15)` called in `recognize()` at line 3112 and `get_stats()` at line 3330; grep for `> "09:00:00"` returns 0 |
| 2 | Department summary shows the real department name, never a raw UUID | VERIFIED | `dept_name_map = {d.id: d.name for d in Department.query...}` at line 412; `dept_name_map.get(dept_id, dept_id)` at line 425; `dept_name = dept_id` fallback is gone |
| 3 | GET /health returns 200 {status:ok,db:connected} when the DB is reachable, 503 when not | VERIFIED | Public route at line 656; no auth decorator; wraps `db.session.execute(text("SELECT 1"))` in try/except; returns 200/503 as specified |
| 4 | T-13 timesheet has Kazakhstan holiday data for 2027 | VERIFIED | `KZ_HOLIDAYS` dict contains a `2027` key at lines 257-261 with full recurring dates (Jan 1-2, Jan 7, Mar 8, Mar 21-23, May 1, May 7, May 9, Jul 6, Aug 30, Oct 25, Dec 1, Dec 16-17) |
| 5 | Session cookies carry Secure, HttpOnly, and SameSite=Lax flags | VERIFIED | Lines 42-44: `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE="Lax"` all present in Flask config block |
| 6 | AttendanceRecord is served by a single composite (emp_id, date) index | VERIFIED | `models.py` line 118: `__table_args__ = (Index("ix_attendance_emp_date", "emp_id", "date"),)`; startup migration at lines 3410-3422 drops old column indexes and creates composite idempotently |
| 7 | A 6th login attempt within 15 minutes from one IP is rejected with HTTP 429 and a Russian message | VERIFIED (code) | `@limiter.limit("5 per 15 minutes", methods=["POST"])` at line 687 decorates `login_page`; 429 handler at line 741 renders Russian "Слишком много попыток. Попробуйте через 15 минут." — see CR-01 in Known Open Items for nginx deployment caveat |
| 8 | After 10 failed PIN attempts the registration token is locked (expired) and returns 429 JSON | VERIFIED (code) | `@limiter.limit("10 per 15 minutes", methods=["POST"])` at line 832 decorates `register_token_verify_pin`; 429 handler at lines 753-764 extracts `reg_token` from URL, sets `org.reg_token_expires` to yesterday, commits, returns JSON 429 — see CR-01 for nginx caveat |
| 9 | Kiosk routes (/, /api/recognize, /api/detect) are never rate limited | VERIFIED | Only 2 `@limiter.limit` decorators exist in app.py (lines 687 and 832); `default_limits=[]` in Limiter constructor; kiosk/recognize/detect carry no limiter decorator |
| 10 | A POST to /login or /profile without a valid CSRF token is rejected (HTTP 400) | VERIFIED (code) | `WTF_CSRF_CHECK_DEFAULT=False` at line 52; `csrf = CSRFProtect(app)` at line 53; explicit `csrf.protect()` in POST branch of `login_page` at line 703 and `profile_page` at line 1203 — live browser test needed for full confirmation |
| 11 | JSON /api/* routes (Content-Type application/json) and kiosk routes are not blocked by CSRF | VERIFIED | `WTF_CSRF_CHECK_DEFAULT=False` means no automatic enforcement; `csrf.protect()` is called only in `login_page` and `profile_page` POST branches; no CSRF annotation on `/api/recognize`, `/api/detect`, or any `@app.route("/api/...")` handlers |
| 12 | The LBPH recognition threshold is read from AppSetting at request time, defaulting to 80 | VERIFIED | Bootstrapped at lines 88-89 (`AppSetting(key="lbph_threshold", value="80")`); read at request time in `recognize()` at lines 3072-3073 using `AppSetting.query.filter_by(key="lbph_threshold").first()`; `confidence > 80` literal gone — line 3076 uses dynamic `threshold` variable |

**Score:** 12/12 truths verified at code level

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app.py` | Schedule-aware late logic, /health route, KZ_HOLIDAYS[2027], cookie flags, limiter, CSRF, lbph_threshold, /api/backup/db, /api/settings/lbph_threshold, PERF-01 startup migration | VERIFIED | All expected symbols found at correct locations |
| `models.py` | AttendanceRecord composite index `ix_attendance_emp_date` | VERIFIED | Line 118: `__table_args__ = (Index("ix_attendance_emp_date", "emp_id", "date"),)` — `Index` imported at line 14 |
| `requirements.txt` | `Flask-Limiter` pin | VERIFIED | `Flask-Limiter==4.1.1` present |
| `requirements.txt` | `Flask-WTF` pin | VERIFIED | `Flask-WTF==1.3.0` present |
| `templates/login.html` | `csrf_token()` hidden input | VERIFIED | Line 47: `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` |
| `templates/profile.html` | `csrf_token()` hidden input | VERIFIED | Line 34: `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` |
| `templates/superadmin.html` | System section with threshold input + backup button | VERIFIED | `Порог распознавания (LBPH)` input with `min=50 max=120` at lines 73-81; `window.location='/api/backup/db'` button at line 93; `saveThreshold()` JS POSTing to `/api/settings/lbph_threshold` at line 180 |
| `templates/base.html` | Superadmin nav link to System section | VERIFIED | Line 169: `<a href="/superadmin/system" ...>` present in the superadmin nav block |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `recognize()` | `_time_threshold(schedule.start, 15)` | is_late computation | WIRED | Line 3112: `is_late = now > _time_threshold(start, 15)` where `start = schedule.get("start", "09:00")` |
| `get_stats()` | `employees[eid]["schedule"]` | per-employee late threshold | WIRED | Lines 3329-3330: `start = employees[eid]["schedule"].get("start", "09:00"); if check_in > _time_threshold(start, 15):` |
| `compute_dept_summary()` | `Department.query` | dept_name_map lookup | WIRED | Lines 412/425: map built from query, applied per dept_id |
| `POST /login` | limiter "5 per 15 minutes" | `@limiter.limit` decorator | WIRED | Line 687 decorates `login_page` |
| `POST verify_pin` | `reg_token_expires` set to past on breach | limiter limit + 429 handler | WIRED | Line 832 decorates route; handler at lines 753-764 performs the lock |
| HTML form POST | `CSRFProtect` validation | `csrf_token()` hidden input | WIRED | `csrf.protect()` at lines 703/1203; hidden input in both templates |
| `recognize()` | `AppSetting` key `lbph_threshold` | request-time read with default 80 | WIRED | Lines 3072-3073 query AppSetting before threshold comparison |
| superadmin.html System section | `PATCH /api/settings/lbph_threshold` + `GET /api/backup/db` | fetch + window.location | WIRED | JS at lines 180/93 of superadmin.html wires both actions |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `recognize()` late check | `threshold` | `AppSetting.query.filter_by(key="lbph_threshold").first()` + fallback 80 | Yes — DB query at request time | FLOWING |
| `recognize()` `is_late` | `schedule.start` | `emp_dict.get("schedule", {})` from `_emp_to_dict(emp)` | Yes — employee ORM object | FLOWING |
| `get_stats()` late count | `employees[eid]["schedule"]` | pre-built employees dict from DB | Yes — live query | FLOWING |
| `compute_dept_summary()` dept name | `dept_name_map` | `Department.query.filter_by(org_id=org_id).all()` | Yes — live query | FLOWING |
| `superadmin_page()` threshold display | `lbph_threshold` | `AppSetting.query.get("lbph_threshold")` at line 1092-1093, passed to template | Yes — live query | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Evidence | Status |
|----------|----------|--------|
| No `> "09:00:00"` literal remains | `grep -c '> "09:00:00"' app.py` returns 0 | PASS |
| `_time_threshold` called in 4+ places | Lines 279 (def), 331, 332, 3112, 3330 | PASS |
| `/health` route exists and is public | Line 656-668: no auth decorator, wraps `SELECT 1` | PASS |
| KZ_HOLIDAYS 2027 key present with `2027-01-01` | Lines 257-261 | PASS |
| 3 session cookie flags | `grep -c 'SESSION_COOKIE_SECURE|HTTPONLY|SAMESITE' app.py` = 3 | PASS |
| `ix_attendance_emp_date` in both models.py and app.py | `models.py:118`, `app.py:3419` | PASS |
| `Flask-Limiter==4.1.1` pinned | `requirements.txt` | PASS |
| `Flask-WTF==1.3.0` pinned | `requirements.txt` | PASS |
| 2 limiter.limit decorators only (login + verify_pin) | Lines 687, 832 | PASS |
| `@require_role("superadmin")` on both new routes | Lines 2886 (/api/settings/lbph_threshold), 2907 (/api/backup/db) | PASS |
| `/superadmin/system` tab in VALID_TABS | Line 1087: `{"orgs", "users", "system"}` | PASS |
| All SUMMARY-referenced commits exist in git | All 8 commit hashes (8922eb6, dac65a8, 27fe8e6, 9c00188, b6b9a8e, 520fbca, ca12b59, ad6aa0b, 97670b5) found in `git log` | PASS |
| No debt markers (TBD/FIXME/XXX) in modified files | `grep -n 'TBD|FIXME|XXX' app.py models.py` returns empty | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|------------|--------|----------|
| BUG-01 | 09-01 | SATISFIED | `_time_threshold(start, 15)` in `recognize()` at line 3112 |
| BUG-02 | 09-01 | SATISFIED | `_time_threshold(start, 15)` in `get_stats()` at line 3330 |
| BUG-03 | 09-01 | SATISFIED | `dept_name_map` lookup in `compute_dept_summary()` at lines 412/425 |
| REL-01 | 09-01 | SATISFIED | `GET /health` public route at line 656 returning 200/503 |
| REL-02 | 09-01 | SATISFIED | `KZ_HOLIDAYS[2027]` with full recurring dates at lines 257-261 |
| REL-03 | 09-04 | SATISFIED (with caveat) | `GET /api/backup/db` superadmin-only at line 2906; path hardcoded (CR-08) |
| SEC-01 | 09-02 | SATISFIED (code) | `@limiter.limit("5 per 15 minutes", methods=["POST"])` on `login_page`; Russian 429 message — effectiveness under nginx needs human verification (CR-01) |
| SEC-02 | 09-02 | SATISFIED (code) | `@limiter.limit("10 per 15 minutes", methods=["POST"])` on `register_token_verify_pin`; token lockout in 429 handler — same nginx caveat (CR-01) |
| SEC-03 | 09-03 | SATISFIED | `CSRFProtect(app)` + `WTF_CSRF_CHECK_DEFAULT=False` + explicit `csrf.protect()` on 2 form routes + `csrf_token()` in templates |
| SEC-04 | 09-01 | SATISFIED | `SESSION_COOKIE_SECURE/HTTPONLY/SAMESITE=Lax` at lines 42-44 |
| SEC-05 | 09-04 | SATISFIED | `lbph_threshold` AppSetting bootstrapped; read per-request in `recognize()`; PATCH route with `[50,120]` validation |
| PERF-01 | 09-01 | SATISFIED | `Index("ix_attendance_emp_date", "emp_id", "date")` in models.py; idempotent startup migration in app.py |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app.py` | 750 | `import re as _re` inside `ratelimit_handler` function | Info (IN-04) | Redundant — `re` already imported at line 2. Harmless (Python caches modules) but adds noise. |
| `templates/superadmin.html` | 251 | `const kioskUrl = \`/kiosk/${org.id}\`` | Critical (CR-07) | `org.id` is the UUID primary key; the kiosk route `/kiosk/<org_token>` looks up by `org.org_token`. Every "Открыть" (Open) link in the org table is a guaranteed 404. This bug was introduced (or left unfixed) by plan 09-04 which edited superadmin.html. |

No TBD/FIXME/XXX/HACK/PLACEHOLDER debt markers in any file modified by phase 09.

---

### Known Open Items from Code Review (09-REVIEW.md)

The code review found 8 critical issues and 5 warnings. They are documented here as open items. Per the verification instructions, the primary phase requirements are assessed separately from these review findings.

**Critical issues introduced or affecting this phase:**

**CR-01 (BLOCKING in production — SEC-01/SEC-02 effectiveness):** `Limiter` is configured with `key_func=get_remote_address`. Without `werkzeug.middleware.proxy_fix.ProxyFix`, `request.remote_addr` equals `127.0.0.1` (the nginx upstream) for every request. All rate-limit buckets collapse to one global bucket. In production, the 5th login attempt from any user exhausts the global bucket for everyone simultaneously. An attacker routing through nginx is not throttled per their source IP.
Fix: Add `app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)` before Limiter initialization.

**CR-08 (defect in REL-03):** `/api/backup/db` constructs the path as `os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "app.db")` unconditionally. If `DATABASE_URL` env var points to a different location, the backup downloads the wrong file or returns 404. The startup code at line 36-38 correctly reads `DATABASE_URL`; the backup route does not.
Fix: Derive path from `app.config["SQLALCHEMY_DATABASE_URI"]`.

**Pre-existing critical issues uncovered by review (not in phase scope):**

**CR-02:** `/api/register/<reg_token>/submit` and `/capture_face` can be reached without ever passing PIN verification — no server-side proof-of-PIN state.

**CR-03:** `list_users` returns all system users to `dept_admin` (should be scoped to their department).

**CR-04:** `update_user` PATCH missing org-scope guard that `delete_user` has — cross-org privilege change possible for `org_admin`.

**CR-05:** New employee LBPH label computed as `Employee.query.count() + 1` in `add_employee` and `register_token_submit` — label collision after any deletion. `import_employees_xlsx` correctly uses `max(Employee.label) + 1`.

**CR-06:** `register_kiosk_device` endpoint validates a 4-digit PIN with no rate limiting — brute-forceable.

**CR-07:** Kiosk "Open" link in `superadmin.html` always 404 — uses `org.id` (UUID) where `org.org_token` (8-char hex) is required.

---

### Human Verification Required

The following items require live environment testing that cannot be resolved by code inspection.

### 1. Rate Limiting Per-IP Effectiveness Under Nginx (CR-01)

**Test:** Deploy the application behind nginx (production setup). From two different client IPs (or simulate with two different nginx client connections), submit 5 POST /login requests from IP-A (invalid credentials), then submit one POST /login from IP-B. Observe whether IP-B's request is rejected or served.

**Expected:** IP-B's 1st login attempt succeeds (is not rate-limited) because IP-B's bucket is empty. Only IP-A's 6th attempt should be blocked.

**Why human:** Without `ProxyFix` middleware, `request.remote_addr` always resolves to `127.0.0.1` in the nginx deployment. All client IP buckets collapse to one shared bucket. This cannot be verified by grep — it requires a live two-client test against the actual nginx proxy chain. If this test fails (IP-B is blocked), `ProxyFix` must be added and the app restarted before the rate limiting meets the SEC-01/SEC-02 contract.

### 2. CSRF Form Rejection in Browser (SEC-03)

**Test:** Open a browser in private mode, navigate to `/login`, open DevTools Network tab, submit the login form with valid credentials. Confirm the request includes `csrf_token` in the form body and the server returns 200/302 (not 400). Then: use a tool (curl or DevTools) to POST to `/login` without the `csrf_token` field and confirm the server responds with HTTP 400.

**Expected:** Form POST with `csrf_token` rendered by `{{ csrf_token() }}` succeeds past CSRF check; POST without `csrf_token` returns 400 with CSRF error.

**Why human:** Template rendering (Jinja2 nonce generation), browser form submission, and server-side `csrf.protect()` validation form a flow that Flask test client doesn't fully simulate. End-to-end browser verification confirms the Jinja2 context injection works and the round-trip validation passes.

---

### Gaps Summary

No phase requirement truths FAILED at the code level. All 12 must-have truths have compliant implementations in the codebase.

Two issues introduced by this phase are open:
1. **CR-01** — `ProxyFix` missing makes SEC-01/SEC-02 rate limiting ineffective per-IP in the nginx production deployment. The rate limit code is present and correct in isolation, but the key function receives the wrong input in production.
2. **CR-07** — The kiosk "Open" link in `superadmin.html` is broken (uses `org.id` instead of `org.org_token`) — this was introduced or left broken during plan 09-04's edits to that template.

These are not phase-requirement failures per the requirement text, but they are real defects introduced within this phase's scope and should be tracked for remediation.

---

_Verified: 2026-06-26_
_Verifier: Claude (gsd-verifier)_
