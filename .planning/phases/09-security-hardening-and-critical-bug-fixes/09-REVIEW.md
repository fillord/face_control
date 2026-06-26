---
phase: 09-security-hardening-and-critical-bug-fixes
reviewed: 2026-06-26T00:00:00Z
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
  critical: 8
  warning: 5
  info: 5
  total: 18
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-06-26
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

This phase is meant to harden security and fix critical bugs, yet the submitted implementation contains several new critical defects. The most severe are: (1) the rate limiter key function returns the wrong address when the app sits behind nginx, nullifying all brute-force protections; (2) the self-registration PIN can be bypassed entirely because server-side state is never checked on submit; (3) `list_users` leaks all system users to any `dept_admin`; (4) `update_user` is missing the org-scope check present in `delete_user`, allowing cross-org privilege changes; (5) LBPH employee labels can collide after any deletion because `count()` is used instead of `max(label)`; (6) the kiosk "Open" link in superadmin.html is broken (always 404) because `org.id` is used where `org.org_token` is required. Secondary issues include the kiosk device cookie's missing `secure` flag despite the session cookie being flagged secure, a buggy manual late-threshold computation in `dept_attendance_today`, and an unsafe fallback DB backup path that ignores `DATABASE_URL`.

---

## Critical Issues

### CR-01: Rate limiter key function returns proxy IP — all brute-force protections bypassed

**File:** `app.py:58-63`
**Issue:** `Limiter` is configured with `key_func=get_remote_address`. The project's own deployment guide says nginx is the recommended reverse proxy. Without `ProxyFix` middleware, `request.remote_addr` (and therefore `get_remote_address()`) always equals `127.0.0.1` — the nginx upstream address. All rate-limit buckets collapse to one global bucket shared by every user in the system. Both SEC-01 (login, 5 per 15 min) and SEC-02 (registration PIN, 10 per 15 min) are effectively switched off: the single shared bucket fills on the 5th or 10th request from any user, locking out everyone, or an attacker can trivially rotate through a second client connection while honest users absorb the tokens.

**Fix:**
```python
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Add before any other middleware or limiter setup:
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Then the limiter's get_remote_address will read X-Forwarded-For correctly.
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://",
    default_limits=[],
)
```

---

### CR-02: Self-registration PIN verification is client-enforced only — server-side bypass exists

**File:** `app.py:852-907` and `app.py:926-957`
**Issue:** The PIN check at `/api/register/<reg_token>/verify_pin` is rate-limited (10/15 min). However, neither `/api/register/<reg_token>/submit` nor `/api/register/<reg_token>/capture_face` verifies that the PIN was ever validated. An attacker who knows the registration URL (or guesses/captures the `reg_token`) can POST directly to `/submit` with a name and immediately create employee records, then upload face photos via `/capture_face`, completely bypassing the PIN and its rate limit. The server stores no server-side proof-of-PIN state.

**Fix:** Issue a short-lived signed token on successful `verify_pin` and require it on `submit` and `capture_face`:
```python
# In verify_pin, on success:
from itsdangerous import URLSafeTimedSerializer
_pin_serializer = URLSafeTimedSerializer(app.secret_key, salt="reg-pin-verified")

# Return signed token good for 30 minutes:
proof = _pin_serializer.dumps({"reg_token": reg_token})
return jsonify({"verified": True, "proof": proof})

# In register_token_submit and register_token_capture_face, add at top:
if org.reg_pin:  # Only enforce when PIN is configured
    proof = (request.json or {}).get("proof", "")
    try:
        _pin_serializer.loads(proof, max_age=1800)
    except Exception:
        return jsonify({"error": "pin_proof_required"}), 403
```

---

### CR-03: `list_users` returns all system users to any `dept_admin`

**File:** `app.py:1771-1791`
**Issue:** The `else` branch in `list_users` runs for both `superadmin` and `dept_admin`:
```python
if caller_role == "org_admin":
    all_users = User.query.filter_by(org_id=caller_org_id).all()
else:
    all_users = User.query.all()  # dept_admin hits this
```
A `dept_admin` receives every user in every organization in the system, including superadmin usernames. The correct scope for `dept_admin` is users within their own org/dept.

**Fix:**
```python
if caller_role == "superadmin":
    all_users = User.query.all()
elif caller_role == "org_admin":
    all_users = User.query.filter_by(org_id=caller_org_id).all()
elif caller_role == "dept_admin":
    caller_dept_id = session.get("dept_id")
    all_users = User.query.filter_by(
        org_id=caller_org_id, dept_id=caller_dept_id
    ).all()
else:
    all_users = []
```

---

### CR-04: `update_user` PATCH missing org-scope guard for `org_admin`

**File:** `app.py:1848-1884`
**Issue:** `delete_user` correctly checks `if caller_role == "org_admin" and target.org_id != session.get("org_id"): return 403`. `update_user` (PATCH) performs no such check. An `org_admin` can toggle `active`, reset `password`, or change `dept_id` for any user in any organization as long as their role is lower in the hierarchy. This is a cross-org privilege escalation.

**Fix:** Add the same guard present in `delete_user`:
```python
# After the hierarchy check in update_user:
if caller_role == "org_admin" and target.org_id != session.get("org_id"):
    return jsonify({"error": "forbidden"}), 403
```

---

### CR-05: Employee LBPH label collision after any deletion

**File:** `app.py:2547` and `app.py:875`
**Issue:** Both `add_employee` and `register_token_submit` compute the new LBPH label as:
```python
label = Employee.query.count() + 1
```
If any employee has ever been deleted, `count()` is lower than `max(label)`. Example: labels {1, 2, 3} exist; delete label 2 → count = 2 → next label = 3, which collides with the existing employee carrying label 3. LBPH will now confuse two employees, causing misidentification at the kiosk. `import_employees_xlsx` (line 2776) correctly uses `max(Employee.label) + 1`, but the other two creation paths do not.

**Fix:**
```python
# Replace in add_employee (line 2547) and register_token_submit (line 875):
max_label = db.session.execute(
    db.select(db.func.max(Employee.label))
).scalar()
label = (max_label or 0) + 1
```

---

### CR-06: `register_kiosk_device` has no rate limiting — kiosk PIN brute-forceable

**File:** `app.py:2286-2331`
**Issue:** The `/api/kiosk/<org_token>/register_device` endpoint validates a 4-digit PIN (10,000 possible values) with no rate limiting decorator. An attacker can exhaust the full PIN space in seconds. The login and registration PIN routes have explicit `@limiter.limit(...)` guards; this endpoint does not.

**Fix:**
```python
@app.route("/api/kiosk/<org_token>/register_device", methods=["POST"])
@limiter.limit("5 per 15 minutes")
def register_kiosk_device(org_token):
    ...
```

---

### CR-07: Kiosk "Open" link in superadmin.html uses org.id instead of org.org_token — always 404

**File:** `templates/superadmin.html:251`
**Issue:** `renderOrgs()` builds the kiosk URL as:
```javascript
const kioskUrl = `/kiosk/${org.id}`;
```
`org.id` is the UUID primary key. The kiosk route at `/kiosk/<org_token>` looks up by `Organization.org_token` (an 8-char hex value), not by `id`. No UUID will ever match an `org_token`, so every "Открыть" link in the superadmin org table returns a 404. The kiosk itself works when accessed by direct URL; only the admin UI link is broken.

**Fix:**
```javascript
const kioskUrl = `/kiosk/${org.org_token}`;
```

---

### CR-08: DB backup path hardcoded — ignores DATABASE_URL, sends wrong file if env var is set

**File:** `app.py:2910`
**Issue:** The backup route always constructs the path as:
```python
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "app.db")
```
If `DATABASE_URL` is set to a custom path, the actual database lives elsewhere and this path either does not exist (404) or is a stale/unrelated file. The startup code correctly reads `DATABASE_URL`; the backup route should too.

**Fix:**
```python
@app.route("/api/backup/db", methods=["GET"])
@require_role("superadmin")
def backup_db():
    # Parse the actual path from the configured SQLALCHEMY_DATABASE_URI
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite:///"):
        db_path = db_uri[len("sqlite:///"):]
    else:
        return jsonify({"error": "Резервное копирование поддерживается только для SQLite"}), 400
    if not os.path.isfile(db_path):
        return jsonify({"error": "Файл базы данных не найден"}), 404
    return send_file(
        db_path,
        as_attachment=True,
        download_name=f"app_backup_{date.today()}.db",
        mimetype="application/octet-stream",
    )
```

---

## Warnings

### WR-01: Kiosk device cookie set with `secure=False` despite session cookie being `secure=True`

**File:** `app.py:2327-2329`
**Issue:** The session cookie is hardened with `SESSION_COOKIE_SECURE = True` (line 42). The kiosk device cookie is set with `secure=False`:
```python
resp.set_cookie(
    _device_cookie_name(org_token),
    raw_token,
    ...
    secure=False,   # set True when enforcing HTTPS at Flask level
)
```
The comment misunderstands the setup: nginx terminates TLS, but Flask must still emit `Secure` in the `Set-Cookie` header so the browser enforces HTTPS-only transmission. The session cookie does this correctly. The device cookie does not, meaning the browser will also send it over cleartext HTTP if any such connection occurs.

**Fix:**
```python
resp.set_cookie(
    _device_cookie_name(org_token),
    raw_token,
    max_age=365 * 24 * 3600,
    httponly=True,
    samesite="Lax",
    secure=True,  # nginx terminates TLS; browser still enforces Secure flag
)
```

---

### WR-02: `dept_attendance_today` manual late-threshold arithmetic is incorrect for edge-case schedules

**File:** `app.py:2966-2971`
**Issue:** The endpoint computes the late threshold manually instead of calling `_time_threshold()`:
```python
late_m = sm + 15
if late_m < 60:
    late_threshold = f"{sh:02d}:{late_m:02d}:00"
else:
    late_threshold = f"{sh + 1:02d}:{late_m % 60:02d}:00"
```
For a schedule starting at "23:50", `sh = 23`, `sm = 50`, `late_m = 65 >= 60`, so `sh + 1 = 24` → produces `"24:05:00"`, an invalid time string. String comparison with a valid `check_in` like `"09:00:00"` against `"24:05:00"` yields unpredictable results. The `_time_threshold()` helper at line 279 was written specifically to handle this case with proper clamping; it is not used here. This produces different late-status results from `compute_symbol()` for the same employee on the same day.

**Fix:**
```python
# Replace lines 2966–2971 with:
late_threshold = _time_threshold(schedule_start, 15)
```

---

### WR-03: `employee_page` month parameter not guarded — unhandled ValueError on malformed input

**File:** `app.py:1008-1011`
**Issue:**
```python
month_str = request.args.get("month", current_month)
if month_str < prev_month or month_str > current_month:
    month_str = current_month
year, month_num = map(int, month_str.split("-"))
```
The string comparison on line 1009 may allow a malformed `month_str` to pass if it happens to sort between `prev_month` and `current_month`. The subsequent `map(int, month_str.split("-"))` raises `ValueError` or produces too many/few values to unpack for any input that is not exactly `"YYYY-MM"`. The `/timesheet` route (line 1277–1283) wraps the same pattern in `try/except`; `/employee` does not, resulting in an unhandled 500 for any URL like `/employee?month=abc`.

**Fix:**
```python
month_str = request.args.get("month", current_month)
try:
    year, month_num = map(int, month_str.split("-"))
    if not (1 <= month_num <= 12 and 2000 <= year <= 2099):
        raise ValueError("out of range")
    if month_str < prev_month or month_str > current_month:
        month_str = current_month
        year, month_num = map(int, month_str.split("-"))
except (ValueError, AttributeError):
    month_str = current_month
    year, month_num = map(int, current_month.split("-"))
```

---

### WR-04: Default PINs "0000" (kiosk) and "1234" (registration) set on every new org

**File:** `app.py:2157-2159`
**Issue:**
```python
kiosk_pin=hash_pin("0000"),
reg_pin=hash_pin("1234"),
```
Every organization is created with trivially guessable PINs. An attacker with the `reg_token` link (obtainable by intercepting invite URLs or social engineering) can register employees with PIN "1234" without any brute-force attempts. An attacker with the org_token can register kiosk devices with "0000". Neither PIN has a mandatory-change flow.

**Fix:** Create orgs without default PINs (require explicit configuration):
```python
kiosk_pin=None,
reg_pin=None,
```
And add UI messaging in `renderOrgs()` to warn when a PIN is not set.

---

### WR-05: `Limiter` storage is in-memory — rate limits lost on every PM2 restart, not shared across workers

**File:** `app.py:61`
**Issue:** `storage_uri="memory://"` means rate-limit state lives in the process heap. A `pm2 restart face-recognition` (routine after deployments) resets all rate-limit counters. An attacker who triggers the restart (e.g., via a deliberately crashing request) or who acts immediately after a deployment can make unlimited login or PIN attempts. If PM2 ever runs multiple workers (`instances > 1`), each worker maintains independent counters, dividing the effective limit by the worker count.

**Fix:** Use Redis or the filesystem for persistent storage:
```python
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    default_limits=[],
)
```
And set `RATELIMIT_STORAGE_URI=redis://localhost:6379/0` in the environment.

---

## Info

### IN-01: `viewer` role is dead code — cannot log in, cannot be created, but appears in routing

**File:** `app.py:119, 1178`, `templates/base.html:199`
**Issue:** `viewer` is in `ROLE_HIERARCHY` and in `require_role("dept_admin", "viewer")` for `dept_admin_page`, and conditionally rendered in `base.html`. However, `ALLOWED_LOGIN_ROLES` excludes `viewer` (line 122), and `create_user` rejects it with a 400 (line 1807-1808). No viewer can ever exist or log in; the routing surface is unreachable. The sidebar shows a "Регистрация" link for `viewer` users (base.html line 209) which leads to a route that returns 403 for that role.

**Fix:** Remove `viewer` from `require_role()` calls and from base.html nav conditionals, or document it as an intentionally reserved placeholder.

---

### IN-02: Session never stores `username` — sidebar always shows empty name

**File:** `templates/base.html:229`
**Issue:**
```html
<div class="sidebar-user-name">{{ session.get('username', '') }}</div>
```
The login handler stores `user_id`, `role`, `org_id`, and `dept_id` in the session (lines 718-721), but never `username`. This sidebar element is always blank for every user.

**Fix:** Either store the username in the session at login:
```python
session["username"] = user.username
```
Or retrieve it from the ORM in the template context (add `username` to each page route's `render_template` call, which most routes already do).

---

### IN-03: `hr_viewer` role missing from `roleLabels` lookup in superadmin.html

**File:** `templates/superadmin.html:417`
**Issue:**
```javascript
const roleLabels = {superadmin:'Суперадмин', org_admin:'Адм. орг.', dept_admin:'Адм. отдела', viewer:'Наблюдатель', employee:'Сотрудник'};
```
`hr_viewer` is absent. Any user with `role='hr_viewer'` displays as `undefined` in the users table. The `hr_viewer` role can be created by `org_admin` via `create_user`.

**Fix:**
```javascript
const roleLabels = {
  superadmin: 'Суперадмин',
  org_admin: 'Адм. орг.',
  dept_admin: 'Адм. отдела',
  hr_viewer: 'HR-наблюдатель',
  viewer: 'Наблюдатель',
  employee: 'Сотрудник',
};
```

---

### IN-04: `import re as _re` inside `ratelimit_handler` — `re` already imported at module level

**File:** `app.py:750`
**Issue:**
```python
@app.errorhandler(429)
def ratelimit_handler(e):
    import re as _re
```
`re` is imported at line 2 (`import re, csv, io`). The redundant inline import is harmless (Python caches modules) but adds noise and implies the module-level import was not noticed.

**Fix:** Remove the inline import; use the module-level `re` directly:
```python
pin_match = re.match(r"^/api/register/([^/]+)/verify_pin$", path)
```

---

### IN-05: `org.id` used unescaped in onclick attributes in renderOrgs

**File:** `templates/superadmin.html:261-263`
**Issue:**
```javascript
<button onclick="startEdit('${org.id}')">Изменить</button>
<button onclick="setPIN('${org.id}', '${escapeHtml(org.name)}')">PIN</button>
<button onclick="deleteOrg('${org.id}', '${escapeHtml(org.name)}')">Удалить</button>
```
`org.id` (a UUID) is interpolated directly into event-handler attribute strings without `escapeHtml()`. While UUIDs produced by `uuid.uuid4()` contain only hex and hyphens and pose no practical XSS risk today, any future schema change that allows non-UUID IDs or a DB poisoning scenario would produce an exploitable onclick attribute. `org.name` is correctly escaped; `org.id` should be too.

**Fix:**
```javascript
<button onclick="startEdit('${escapeHtml(org.id)}')">Изменить</button>
<button onclick="setPIN('${escapeHtml(org.id)}', '${escapeHtml(org.name)}')">PIN</button>
<button onclick="deleteOrg('${escapeHtml(org.id)}', '${escapeHtml(org.name)}')">Удалить</button>
```

---

_Reviewed: 2026-06-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
