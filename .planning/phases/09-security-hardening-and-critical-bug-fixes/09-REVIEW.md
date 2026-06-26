---
phase: 09-security-hardening-and-critical-bug-fixes
reviewed: 2026-06-26T12:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - app.py
  - models.py
  - requirements.txt
  - templates/base.html
  - templates/login.html
  - templates/profile.html
  - templates/superadmin.html
findings:
  critical: 11
  warning: 8
  info: 6
  total: 25
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-06-26T12:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 09 was supposed to harden security. The delivered code introduces or retains 11 critical (BLOCKER) defects, 8 warnings, and 6 info items. The most serious are a set of insecure direct object reference (IDOR) vulnerabilities — `register_face`, `get_employee`, and `update_employee_schedule` perform zero scope-checking for `org_admin` callers, allowing cross-organization data modification. Self-registration PIN gating is entirely client-enforced: the server never verifies PIN authorization before accepting employee creation or face capture via `/submit` and `/capture_face`. The rate limiter almost certainly does not work in production because `get_remote_address` returns the nginx proxy IP (`127.0.0.1`) for every request without a `ProxyFix` middleware. The `update_user` PATCH endpoint is missing the org-scope guard that `delete_user` has, enabling cross-org privilege changes. Additional critical issues include LBPH label collision after any deletion, the kiosk "Open" link being broken in the UI, and the database backup route ignoring `DATABASE_URL`. Secondary defects include an incorrect manual late-threshold formula, unhandled `ValueError` in the employee page, leaked exception details on import failure, predictable default PINs on org creation, and in-memory rate-limit state that resets on restart.

---

## Structural Findings (fallow)

No structural pre-pass was provided for this review.

---

## Narrative Findings (AI reviewer)

---

## Critical Issues

### CR-01: Rate limiter key function returns proxy IP — all brute-force protections bypassed

**File:** `app.py:58-63`
**Issue:** `Limiter` uses `key_func=get_remote_address`. The project deploys behind nginx. Without `ProxyFix` middleware, Flask's `request.remote_addr` equals `127.0.0.1` (the nginx loopback) for every request. All rate-limit buckets collapse to a single shared bucket. The SEC-01 (login, 5/15 min) and SEC-02 (registration PIN, 10/15 min) protections are effectively disabled: a single attacker can burn through credentials without personal throttling, and in the worst case, legitimate users are locked out when the shared bucket fills.

**Fix:**
```python
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

limiter = Limiter(
    key_func=get_remote_address,   # now reads X-Forwarded-For correctly
    app=app,
    storage_uri="memory://",
    default_limits=[],
)
```

---

### CR-02: Self-registration PIN verification is client-enforced only — server-side bypass exists

**File:** `app.py:852-907` (`register_token_submit`), `app.py:926-957` (`register_token_capture_face`)
**Issue:** The PIN check lives only in `/api/register/<reg_token>/verify_pin` (rate-limited, 10/15 min). Neither `/submit` nor `/capture_face` checks whether the PIN was ever validated. An attacker with the registration URL can POST directly to `/submit` (creating an employee record) and then POST to `/capture_face` (uploading a face photo), bypassing the PIN and its rate limit entirely. The server holds no server-side proof-of-PIN state.

**Fix:** Issue a short-lived signed token on `verify_pin` success and require it on subsequent endpoints:
```python
# verify_pin — on success return a signed proof token:
from itsdangerous import URLSafeTimedSerializer
_pin_ser = URLSafeTimedSerializer(app.secret_key, salt="reg-pin-ok")
proof = _pin_ser.dumps({"reg_token": reg_token})
return jsonify({"verified": True, "proof": proof})

# register_token_submit / register_token_capture_face — add near top:
if org.reg_pin:
    proof = (request.json or {}).get("proof", "")
    try:
        _pin_ser.loads(proof, max_age=1800)  # 30-minute window
    except Exception:
        return jsonify({"error": "pin_proof_required"}), 403
```

---

### CR-03: IDOR — `register_face` performs no org or dept scope check

**File:** `app.py:3001-3028`
**Issue:** `register_face` accepts any `emp_id` from the request body, looks up the employee, and overwrites their face data — with no verification that the caller's org or dept matches the employee:
```python
emp_id = data["emp_id"]
emp = Employee.query.get(emp_id)
if not emp:
    return jsonify({"error": "Сотрудник не найден"}), 404
# No scope check — org_admin of Org A can overwrite faces for Org B employees
```
An `org_admin` from one organization can silently replace any employee's biometric face data in any other organization, causing misidentification at kiosks.

**Fix:**
```python
role = session.get("role")
if role == "org_admin" and emp.org_id != session.get("org_id"):
    return jsonify({"error": "forbidden"}), 403
if role == "dept_admin" and emp.dept_id != session.get("dept_id"):
    return jsonify({"error": "forbidden"}), 403
```

---

### CR-04: IDOR — `get_employee` has no scope check

**File:** `app.py:2661-2667`
**Issue:**
```python
@require_role("superadmin", "org_admin", "dept_admin")
def get_employee(emp_id):
    emp = Employee.query.get(emp_id)
    if not emp:
        return jsonify({"error": "Сотрудник не найден"}), 404
    return jsonify(_emp_to_dict(emp))
```
Any authenticated admin can retrieve any employee's full details — name, IIN, org_id, dept_id, face_count, schedule — regardless of their own org or department scope. Every other write endpoint (`reset_employee_face`, `delete_employee`, `update_employee_assignment`) has scope guards; this read endpoint does not.

**Fix:**
```python
role = session.get("role")
if role == "org_admin" and emp.org_id != session.get("org_id"):
    return jsonify({"error": "forbidden"}), 403
if role == "dept_admin" and emp.dept_id != session.get("dept_id"):
    return jsonify({"error": "forbidden"}), 403
```

---

### CR-05: IDOR — `update_employee_schedule` missing org_admin scope check

**File:** `app.py:2669-2724`
**Issue:** The scope gate only checks `dept_admin`; `org_admin` is unconstrained:
```python
if caller_role == "dept_admin" and emp.dept_id != caller_dept_id:
    return jsonify({"error": "forbidden"}), 403
# org_admin check is ABSENT — can edit schedules for any org's employees
```
An `org_admin` can alter the work schedule (start time, end time, work days) of employees belonging to other organizations, changing which days count as absences in their T-13 timesheets.

**Fix:**
```python
caller_org_id = session.get("org_id")
if caller_role == "org_admin" and emp.org_id != caller_org_id:
    return jsonify({"error": "forbidden"}), 403
if caller_role == "dept_admin" and emp.dept_id != caller_dept_id:
    return jsonify({"error": "forbidden"}), 403
```

---

### CR-06: `update_user` PATCH missing org-scope guard — cross-org privilege escalation

**File:** `app.py:1848-1884`
**Issue:** `delete_user` (line 1901) correctly checks `if caller_role == "org_admin" and target.org_id != session.get("org_id"): return 403`. `update_user` PATCH performs only the role-hierarchy check, with no org-scope guard. An `org_admin` can toggle `active` (locking out accounts), reset `password`, or change `dept_id` for any user in any organization, as long as that user's role is lower in the hierarchy.

**Fix:**
```python
# Add after the hierarchy check in update_user:
if caller_role == "org_admin" and target.org_id != session.get("org_id"):
    return jsonify({"error": "forbidden"}), 403
if caller_role == "dept_admin" and target.org_id != session.get("org_id"):
    return jsonify({"error": "forbidden"}), 403
```

---

### CR-07: `list_users` returns all system users to any `dept_admin`

**File:** `app.py:1776-1779`
**Issue:**
```python
if caller_role == "org_admin":
    all_users = User.query.filter_by(org_id=caller_org_id).all()
else:
    all_users = User.query.all()   # dept_admin hits this branch
```
A `dept_admin` receives every user record across every organization, including usernames and role labels for the superadmin account.

**Fix:**
```python
if caller_role == "superadmin":
    all_users = User.query.all()
elif caller_role == "org_admin":
    all_users = User.query.filter_by(org_id=caller_org_id).all()
elif caller_role == "dept_admin":
    all_users = User.query.filter_by(org_id=caller_org_id,
                                      dept_id=session.get("dept_id")).all()
else:
    all_users = []
```

---

### CR-08: LBPH label collision after any employee deletion

**File:** `app.py:2547` and `app.py:875`
**Issue:** Both `add_employee` and `register_token_submit` compute the next LBPH label as:
```python
label = Employee.query.count() + 1
```
After any deletion, `count()` falls below `max(existing label)`. Example: labels {1, 2, 3} exist; delete label 2 → count = 2 → next label = 3, colliding with the employee already carrying label 3. The LBPH recognizer will then map two employees to the same label, causing misidentification at the kiosk. `import_employees_xlsx` (line 2776) already uses the correct `max(Employee.label) + 1` pattern.

**Fix:** Replace in both `add_employee` (line 2547) and `register_token_submit` (line 875):
```python
max_label = db.session.execute(
    db.select(db.func.max(Employee.label))
).scalar()
label = (max_label or 0) + 1
```

---

### CR-09: Kiosk device registration has no rate limiting — kiosk PIN brute-forceable

**File:** `app.py:2286-2331`
**Issue:** `/api/kiosk/<org_token>/register_device` validates a 4-digit PIN (10 000 combinations) with no `@limiter.limit()` decorator. Every other sensitive PIN endpoint is rate-limited; this one is not, and the only protection is the default PINs ("0000") which are weak.

**Fix:**
```python
@app.route("/api/kiosk/<org_token>/register_device", methods=["POST"])
@limiter.limit("5 per 15 minutes")
def register_kiosk_device(org_token):
    ...
```

---

### CR-10: Kiosk "Open" link in superadmin.html uses `org.id` (UUID) — always 404

**File:** `templates/superadmin.html:251`
**Issue:**
```javascript
const kioskUrl = `/kiosk/${org.id}`;
```
The kiosk route `/kiosk/<org_token>` looks up by `Organization.org_token` (8-char hex string), not by primary key `id` (UUID). Every "Открыть" link in the org table returns 404.

**Fix:**
```javascript
const kioskUrl = `/kiosk/${org.org_token}`;
```

---

### CR-11: DB backup route hardcodes path — ignores `DATABASE_URL`

**File:** `app.py:2910`
**Issue:**
```python
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "app.db")
```
If `DATABASE_URL` points elsewhere, this path either does not exist (404) or is a stale file. The startup code (line 36-38) correctly reads `DATABASE_URL`; the backup route does not.

**Fix:**
```python
db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
if not db_uri.startswith("sqlite:///"):
    return jsonify({"error": "Backup only supported for SQLite"}), 400
db_path = db_uri[len("sqlite:///"):]
if not os.path.isfile(db_path):
    return jsonify({"error": "Файл базы данных не найден"}), 404
```

---

## Warnings

### WR-01: Kiosk device cookie set with `secure=False` while session cookie uses `secure=True`

**File:** `app.py:2327-2328`
**Issue:** `SESSION_COOKIE_SECURE = True` (line 42) correctly marks the session cookie as HTTPS-only. The kiosk device cookie is emitted with `secure=False`. The comment explaining this ("set True when enforcing HTTPS at Flask level") misunderstands the setup: nginx already terminates TLS, but the browser still requires the `Secure` flag in the `Set-Cookie` header to honor HTTPS-only transmission. The session cookie demonstrates this is achievable; the device cookie should match.

**Fix:**
```python
resp.set_cookie(
    _device_cookie_name(org_token), raw_token,
    max_age=365 * 24 * 3600,
    httponly=True,
    samesite="Lax",
    secure=True,   # nginx terminates TLS; browser still enforces Secure flag
)
```

---

### WR-02: `dept_attendance_today` manual late-threshold arithmetic produces invalid time strings

**File:** `app.py:2966-2971`
**Issue:**
```python
late_m = sm + 15
if late_m < 60:
    late_threshold = f"{sh:02d}:{late_m:02d}:00"
else:
    late_threshold = f"{sh + 1:02d}:{late_m % 60:02d}:00"
```
For a schedule starting at `"23:50"`, `sh = 23`, `late_m = 65`, so `sh + 1 = 24` → `"24:05:00"`. String comparison of a real time like `"09:00:00"` against `"24:05:00"` yields unpredictable results. `_time_threshold()` (line 279) was written exactly for this case and clamps to `[00:00:00, 23:59:59]`; it is unused here, producing inconsistent late-status results vs. `compute_symbol()` for the same employee on the same day.

**Fix:**
```python
# Replace lines 2966-2971 with:
late_threshold = _time_threshold(schedule_start, 15)
```

---

### WR-03: `/employee` page crashes on malformed `?month=` parameter — unhandled ValueError

**File:** `app.py:1008-1011`
**Issue:**
```python
month_str = request.args.get("month", current_month)
if month_str < prev_month or month_str > current_month:
    month_str = current_month
year, month_num = map(int, month_str.split("-"))  # raises ValueError on "abc", "2025-13", etc.
```
The string-comparison guard on line 1009 may pass malformed input (e.g., `"2025-99"` sorts between the clamp bounds). The subsequent `split`/`map` raises unhandled `ValueError`, resulting in a 500 error page. `/timesheet` wraps identical logic in `try/except (ValueError, AttributeError)`; `/employee` does not.

**Fix:**
```python
month_str = request.args.get("month", current_month)
try:
    year, month_num = map(int, month_str.split("-"))
    if not (1 <= month_num <= 12 and 2000 <= year <= 2099):
        raise ValueError
    if month_str < prev_month or month_str > current_month:
        month_str = current_month
        year, month_num = map(int, month_str.split("-"))
except (ValueError, AttributeError):
    month_str = current_month
    year, month_num = map(int, current_month.split("-"))
```

---

### WR-04: Exception message from DB commit leaked to client in `import_employees_xlsx`

**File:** `app.py:2861-2862`
**Issue:**
```python
except Exception as e:
    db.session.rollback()
    return jsonify({"error": f"Ошибка при сохранении: {e}"}), 500
```
The raw exception string (which can contain SQL column names, constraint names, file paths, or stack fragments) is returned directly to the browser. Every other 500 handler in `app.py` returns the generic string `"Internal server error"`.

**Fix:**
```python
except Exception:
    db.session.rollback()
    return jsonify({"error": "Ошибка при сохранении. Попробуйте ещё раз."}), 500
```

---

### WR-05: Default PINs "0000" (kiosk) and "1234" (registration) on every new org

**File:** `app.py:2157-2159`
**Issue:**
```python
kiosk_pin=hash_pin("0000"),
reg_pin=hash_pin("1234"),
```
Every org is created with trivially guessable PINs. An attacker with the registration URL (distributed to employees) can immediately register without any brute-force attempt using PIN "1234". There is no forced-change flow for these defaults.

**Fix:** Create orgs without default PINs; require explicit admin configuration:
```python
kiosk_pin=None,
reg_pin=None,
```

---

### WR-06: In-memory rate-limit storage resets on every PM2 restart

**File:** `app.py:61`
**Issue:** `storage_uri="memory://"` keeps all rate-limit counters in the process heap. A `pm2 restart` (routine after deployments) resets every counter, giving attackers a clean slate. If PM2 runs multiple worker instances, each holds independent counters, dividing the effective limit by the worker count.

**Fix:**
```python
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    default_limits=[],
)
```
Set `RATELIMIT_STORAGE_URI=redis://localhost:6379/0` in the environment.

---

### WR-07: Active sessions not invalidated after password change

**File:** `app.py:1215-1219` and `app.py:1253-1254`
**Issue:** Both `profile_page` (POST branch) and `/api/me` (PATCH) update `user.password_hash` without invalidating the user's existing session or other concurrent sessions. If an account is compromised and the legitimate owner resets the password, the attacker's active session remains valid indefinitely (until the session cookie expires).

**Fix:** After a successful password update, regenerate the session to invalidate any pre-change sessions:
```python
user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
db.session.commit()
session.clear()
session["user_id"] = user.id
session["role"] = user.role
session["org_id"] = user.org_id
session["dept_id"] = user.dept_id
```

---

### WR-08: Unsafe fallback in scoped endpoints returns ALL employees/records when role is misconfigured

**File:** `app.py:2528-2530`, `app.py:3228-3230`, `app.py:3290-3292`
**Issue:** In `get_employees`, `get_attendance`, and `get_stats`:
```python
else:
    emps = Employee.query.all()
```
If a user has a recognized role (`dept_admin`) but their `dept_id` is `None` in the session (e.g., due to a misconfigured account or session tampering), the `elif role == "dept_admin" and dept_id:` condition fails and the else branch runs, returning all employees system-wide. The fix is to fail closed.

**Fix:**
```python
else:
    emps = []   # fail closed; return empty result rather than all records
```

---

## Info

### IN-01: Missing audit log entries for employee delete and employee assignment update

**File:** `app.py:2634-2659` (`delete_employee`), `app.py:2585-2632` (`update_employee_assignment`)
**Issue:** `delete_employee` removes the employee record and their face directory with no `write_audit()` call. `update_employee_assignment` (PATCH) updates name, dept, org, role, and IIN with no audit call. Every other sensitive write operation (org/dept CRUD, user CRUD, manual attendance edit, employee create) writes an audit row; these two do not, leaving gaps in the audit trail.

**Fix:** Add `write_audit()` calls after successful commits in both functions, mirroring the pattern used in `delete_dept` and `add_employee`.

---

### IN-02: Session never stores `username` — sidebar always shows empty name

**File:** `app.py:717-721`, `templates/base.html:229`
**Issue:** The login handler stores `user_id`, `role`, `org_id`, `dept_id` but never `session["username"]`. The sidebar template reads `{{ session.get('username', '') }}`, which is always empty.

**Fix:** Add to login handler after `session.clear()`:
```python
session["username"] = user.username
```

---

### IN-03: `hr_viewer` absent from `roleLabels` in superadmin.html — displays as `undefined`

**File:** `templates/superadmin.html:417`
**Issue:**
```javascript
const roleLabels = {superadmin:'Суперадмин', org_admin:'Адм. орг.', dept_admin:'Адм. отдела', viewer:'Наблюдатель', employee:'Сотрудник'};
```
`hr_viewer` is missing. Any user with this role shows `undefined` in the users table. `hr_viewer` accounts can be created by `org_admin` via `create_user`.

**Fix:** Add `hr_viewer: 'HR-наблюдатель'` to the map.

---

### IN-04: `viewer` role is dead code — unreachable but appears in routing and nav

**File:** `app.py:119, 1178`, `templates/base.html:199`
**Issue:** `viewer` is in `ROLE_HIERARCHY`, the `dept_admin_page` `require_role`, and the `base.html` nav block. However, `ALLOWED_LOGIN_ROLES` excludes `viewer` and `create_user` rejects it. No viewer account can ever exist or log in. The dead routing surface and nav block add maintenance risk.

**Fix:** Remove `viewer` from `require_role("dept_admin", "viewer")` and from the `base.html` nav conditional, or document clearly that it is a reserved future role.

---

### IN-05: `import re as _re` inside `ratelimit_handler` — redundant, `re` is already imported

**File:** `app.py:750`
**Issue:** `re` is imported at module level (line 2: `import re, csv, io`). The inline import `import re as _re` inside `ratelimit_handler` (line 750) is redundant. Python caches module imports so this is harmless at runtime, but it signals the module-level import was overlooked.

**Fix:** Remove the inline import and use the module-level `re` directly.

---

### IN-06: `org.id` not HTML-escaped in onclick attributes in `renderOrgs`

**File:** `templates/superadmin.html:261-263`
**Issue:**
```javascript
<button onclick="startEdit('${org.id}')">
<button onclick="setPIN('${org.id}', '${escapeHtml(org.name)}')">
<button onclick="deleteOrg('${org.id}', '${escapeHtml(org.name)}')">
```
`org.name` is escaped; `org.id` (a UUID today) is not. UUIDs are safe, but the inconsistency means any future change to ID format that allows quotes or angle brackets would produce XSS. `escapeHtml` is already defined and used on the same line for `org.name`.

**Fix:** Apply `escapeHtml(org.id)` consistently.

---

_Reviewed: 2026-06-26T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
