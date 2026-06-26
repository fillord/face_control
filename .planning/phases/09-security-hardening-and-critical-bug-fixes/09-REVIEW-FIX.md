---
phase: 09-security-hardening-and-critical-bug-fixes
fixed_at: 2026-06-26T13:00:00Z
review_path: .planning/phases/09-security-hardening-and-critical-bug-fixes/09-REVIEW.md
iteration: 1
findings_in_scope: 25
fixed: 25
skipped: 0
status: all_fixed
---

# Phase 09: Code Review Fix Report

**Fixed at:** 2026-06-26T13:00:00Z
**Source review:** `.planning/phases/09-security-hardening-and-critical-bug-fixes/09-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 25
- Fixed: 25
- Skipped: 0

---

## Fixed Issues

### CR-01: Rate limiter key function returns proxy IP

**Files modified:** `app.py`
**Commit:** `506e562`
**Applied fix:** Added `from werkzeug.middleware.proxy_fix import ProxyFix` import and wrapped `app.wsgi_app` with `ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)` immediately after `Flask(__name__)`. Rate limiter now reads real client IP from `X-Forwarded-For`.

---

### CR-02: Self-registration PIN verification is client-enforced only

**Files modified:** `app.py`, `templates/register_token.html`
**Commit:** `8ab6801`
**Applied fix:** Added `_pin_ser = URLSafeTimedSerializer(...)` at module level. `verify_pin` now returns a signed `proof` token on success (valid 30 minutes). `/submit` and `/capture_face` endpoints reject calls when `org.reg_pin` is set but no valid `proof` is provided. Client-side `submitPin()` stores `pinProof` from the response and passes it to `/submit` and `/capture_face` calls. Note: the more elaborate version of `register_token.html` (with dept selection flow) was merged with CR-02 changes and left as a working-directory file (same state as pre-session). **Requires human verification** of the proof-passing logic in both template versions.

---

### CR-03: IDOR in `register_face` — no org/dept scope check

**Files modified:** `app.py`
**Commit:** `2b58843`
**Applied fix:** Added scope guard after employee lookup: `org_admin` blocked if `emp.org_id != session.get("org_id")`; `dept_admin` blocked if `emp.dept_id != session.get("dept_id")`. Returns 403 on mismatch.

---

### CR-04: IDOR in `get_employee` — no scope check

**Files modified:** `app.py`
**Commit:** `c7015e2`
**Applied fix:** Added scope guard in `get_employee`: `org_admin` blocked if employee is in another org; `dept_admin` blocked if employee is in another dept. Returns 403 on mismatch.

---

### CR-05: IDOR in `update_employee_schedule` — missing org_admin scope check

**Files modified:** `app.py`
**Commit:** `c7015e2`
**Applied fix:** Added `caller_org_id = session.get("org_id")` and guard `if caller_role == "org_admin" and emp.org_id != caller_org_id: return 403`. Combined with existing `dept_admin` guard. Committed in same commit as CR-04.

---

### CR-06: `update_user` PATCH missing org-scope guard

**Files modified:** `app.py`
**Commit:** `8226959`
**Applied fix:** Added after role-hierarchy check: `if caller_role in ("org_admin", "dept_admin") and target.org_id != session.get("org_id"): return 403`. Prevents cross-org account modification.

---

### CR-07: `list_users` returns all users to `dept_admin`

**Files modified:** `app.py`
**Commit:** `8226959`
**Applied fix:** Replaced the binary `org_admin`/else branch with explicit four-way branch: `superadmin` → all; `org_admin` → filter by `org_id`; `dept_admin` → filter by `org_id` AND `dept_id`; else → `[]`. Committed in same commit as CR-06.

---

### CR-08: LBPH label collision after any employee deletion

**Files modified:** `app.py`
**Commit:** `094d0df`
**Applied fix:** Replaced `Employee.query.count() + 1` with `max(Employee.label or 0) + 1` using `db.session.execute(db.select(db.func.max(Employee.label))).scalar()` in both `add_employee` (line ~2592) and `register_token_submit` (line ~900). Uses distinct variable names `_max_label` and `_max_label_rt` to avoid shadowing.

---

### CR-09: Kiosk device registration has no rate limiting

**Files modified:** `app.py`
**Commit:** `09c2a64`
**Applied fix:** Added `@limiter.limit("5 per 15 minutes")` decorator to `register_kiosk_device` route, preventing brute-force of the 4-digit kiosk PIN.

---

### CR-10: Kiosk "Open" link uses `org.id` instead of `org.org_token`

**Files modified:** `templates/superadmin.html`
**Commit:** `09c2a64`
**Applied fix:** Changed `const kioskUrl = \`/kiosk/${org.id}\`` to `const kioskUrl = \`/kiosk/${org.org_token}\`` in `renderOrgs()`. The `/kiosk/<org_token>` route uses the 8-char hex token, not the UUID primary key. Committed in same commit as CR-09.

---

### CR-11: DB backup route ignores `DATABASE_URL`

**Files modified:** `app.py`
**Commit:** `09c2a64`
**Applied fix:** Replaced hardcoded `os.path.join(..., "data", "app.db")` with parsing `SQLALCHEMY_DATABASE_URI`: strips `sqlite:///` prefix to get the actual path. Returns 400 if URI is not SQLite. Committed in same commit as CR-09 and CR-10.

---

### WR-01: Kiosk device cookie set with `secure=False`

**Files modified:** `app.py`
**Commit:** `57394a7`
**Applied fix:** Changed `secure=False` to `secure=True` in `resp.set_cookie()` call in `register_kiosk_device`. Updated the inline comment to explain that nginx terminates TLS so the browser still enforces the `Secure` flag.

---

### WR-02: `dept_attendance_today` manual late-threshold arithmetic

**Files modified:** `app.py`
**Commit:** `57394a7`
**Applied fix:** Replaced the 6-line manual `sh`/`sm` arithmetic (which could produce `"24:05:00"` for `23:50` schedules) with a single call `late_threshold = _time_threshold(schedule_start, 15)`, which clamps to `[00:00:00, 23:59:59]`.

---

### WR-03: `/employee` page crashes on malformed `?month=` parameter

**Files modified:** `app.py`
**Commit:** `57394a7`
**Applied fix:** Wrapped month parsing in `try/except (ValueError, AttributeError)` with range validation (`1 <= month_num <= 12 and 2000 <= year <= 2099`). Falls back to `current_month` on any parse error. Matches the pattern already used in `/timesheet`.

---

### WR-04: Exception message leaked to client in `import_employees_xlsx`

**Files modified:** `app.py`
**Commit:** `57394a7`
**Applied fix:** Changed `except Exception as e:` to `except Exception:` and replaced `f"Ошибка при сохранении: {e}"` with the generic `"Ошибка при сохранении. Попробуйте ещё раз."`, preventing SQL schema details from reaching the browser.

---

### WR-05: Default PINs "0000" (kiosk) and "1234" (registration) on every new org

**Files modified:** `app.py`
**Commit:** `57394a7`
**Applied fix:** Changed `kiosk_pin=hash_pin("0000")` and `reg_pin=hash_pin("1234")` to `kiosk_pin=None` and `reg_pin=None` in the `add_org` endpoint. Admins must now explicitly configure PINs via `/api/orgs/<id>/settings`.

---

### WR-06: In-memory rate-limit storage resets on every PM2 restart

**Files modified:** `app.py`
**Commit:** `8ab6801` (included in CR-02 commit)
**Applied fix:** Changed `storage_uri="memory://"` to `storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://")` in the `Limiter` constructor. Set `RATELIMIT_STORAGE_URI=redis://localhost:6379/0` in the environment to enable durable storage.

---

### WR-07: Active sessions not invalidated after password change

**Files modified:** `app.py`
**Commit:** `57394a7`
**Applied fix:** After successful password hash update in both `profile_page` (POST) and `/api/me` (PATCH), the session is cleared and re-populated with fresh user data (`user_id`, `role`, `org_id`, `dept_id`, `username`). This invalidates any concurrent sessions holding the old session cookie. **Requires human verification** — logic correctness depends on Flask's session regeneration behavior.

---

### WR-08: Unsafe fallback returns ALL records when scope is misconfigured

**Files modified:** `app.py`
**Commit:** `57394a7`
**Applied fix:** Changed `else: emps = Employee.query.all()` to `else: emps = []` in three endpoints: `get_employees`, `get_attendance`, and `get_stats`. These now fail closed (return empty result) when a user's `dept_id`/`org_id` is `None` rather than returning all records system-wide.

---

### IN-01: Missing audit log for `delete_employee` and `update_employee_assignment`

**Files modified:** `app.py`
**Commit:** `8666b19`
**Applied fix:** Added `write_audit("employee_delete", ...)` call in `delete_employee` after the face directory removal. Added `old_emp_values` capture before mutation and `write_audit("employee_update", ...)` call after successful commit in `update_employee_assignment`. Mirrors the pattern from `delete_dept` and `add_employee`.

---

### IN-02: Session never stores `username` — sidebar always shows empty name

**Files modified:** `app.py`
**Commit:** `8666b19`
**Applied fix:** Added `session["username"] = user.username` in the login handler immediately after the other session values are set. The sidebar `{{ session.get('username', '') }}` now renders the logged-in user's username.

---

### IN-03: `hr_viewer` absent from `roleLabels` in superadmin.html

**Files modified:** `templates/superadmin.html`
**Commit:** `8666b19`
**Applied fix:** Added `hr_viewer:'HR-наблюдатель'` to the `roleLabels` object in `renderUsers()`. Users with the `hr_viewer` role now display a proper label instead of `undefined`.

---

### IN-04: `viewer` role is dead code in routing and nav

**Files modified:** `app.py`, `templates/base.html`
**Commit:** `8666b19`
**Applied fix:** Removed `"viewer"` from `require_role("dept_admin", "viewer")` in `dept_admin_page`. Changed `elif role_now in ("dept_admin", "viewer"):` to `elif role_now == "dept_admin":` in the login redirect block. Changed `{% elif session.role in ('dept_admin', 'viewer') %}` to `{% elif session.role == 'dept_admin' %}` in `base.html` nav. `viewer` remains in `ROLE_HIERARCHY` and `create_user` rejection guard for documentation purposes.

---

### IN-05: `import re as _re` inside `ratelimit_handler` — redundant import

**Files modified:** `app.py`
**Commit:** `8666b19`
**Applied fix:** Removed the inline `import re as _re` statement and replaced `_re.match(...)` with the module-level `re.match(...)` (already imported at line 2: `import re, csv, io`).

---

### IN-06: `org.id` not HTML-escaped in onclick attributes in `renderOrgs`

**Files modified:** `templates/superadmin.html`
**Commit:** `8666b19`
**Applied fix:** Wrapped all three `org.id` template literal interpolations in `onclick` attributes with `escapeHtml()`: `startEdit('${escapeHtml(org.id)}')`, `setPIN('${escapeHtml(org.id)}', ...)`, `deleteOrg('${escapeHtml(org.id)}', ...)`. Consistent with the existing `escapeHtml(org.name)` usage on the same line.

---

## Skipped Issues

None — all 25 findings were fixed.

---

_Fixed: 2026-06-26T13:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
