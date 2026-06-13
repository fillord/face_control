---
phase: 03-t-13-timesheet-grid
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - app.py
  - templates/admin.html
  - templates/org_admin.html
  - templates/register.html
  - templates/superadmin.html
  - templates/timesheet.html
  - tests/conftest.py
  - tests/test_timesheet.py
findings:
  critical: 6
  warning: 7
  info: 3
  total: 16
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-06-13T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

This phase implements the T-13 timesheet grid, symbol engine, per-employee schedule support, and
department-scoped inline overrides. The core symbol-computation logic is well-structured and the
RBAC scope guards on the override endpoint are correctly placed server-side. However, six
blockers were found: two authorization gaps allow any `dept_admin` or `org_admin` to delete or
reset face data for employees they do not manage; two attendance API endpoints (`/api/attendance`
and `/api/stats`) return data for all employees regardless of the caller's org/dept scope; one
date-validation bypass allows arbitrary strings to be stored as override keys; and new
organizations are created with hard-coded default PINs (0000 / 1234). Additionally there are
several warnings around data integrity, XSS in admin.html, locking semantics for JSON files,
and the superadmin UI leaking bcrypt hashes into the browser.

---

## Critical Issues

### CR-01: Missing scope check on DELETE /api/employees/<emp_id>

**File:** `app.py:1418-1430`
**Issue:** `delete_employee` is decorated with `@require_role("superadmin", "org_admin", "dept_admin")` but performs **no org/dept scope check**. Any `dept_admin` or `org_admin` can DELETE any employee from any organisation by supplying an arbitrary `emp_id` in the URL. The equivalent protection that exists in `update_employee_assignment` (line 1403-1410) and `update_employee_schedule` (line 1451-1452) is completely absent here.

**Fix:**
```python
@app.route("/api/employees/<emp_id>", methods=["DELETE"])
@require_role("superadmin", "org_admin", "dept_admin")
def delete_employee(emp_id):
    employees = load_employees()
    if emp_id not in employees:
        return jsonify({"status": "deleted"})  # idempotent — keep existing behaviour
    emp = employees[emp_id]
    caller_role = session.get("role")
    caller_org_id = session.get("org_id")
    caller_dept_id = session.get("dept_id")
    if caller_role == "dept_admin" and emp.get("dept_id") != caller_dept_id:
        return jsonify({"error": "forbidden"}), 403
    if caller_role == "org_admin" and emp.get("org_id") != caller_org_id:
        return jsonify({"error": "forbidden"}), 403
    del employees[emp_id]
    save_employees(employees)
    emp_dir = os.path.join(FACES_DIR, emp_id)
    if os.path.exists(emp_dir):
        shutil.rmtree(emp_dir)
    train_recognizer()
    return jsonify({"status": "deleted"})
```

---

### CR-02: Missing scope check on POST /api/employees/<emp_id>/reset

**File:** `app.py:1482-1495`
**Issue:** `reset_employee_face` is accessible to `dept_admin` and `org_admin` but has **no org/dept scope check**. Any authenticated `dept_admin` can wipe face photos for an employee in a completely different department, triggering retraining with missing data. The endpoint only checks that the employee exists (line 1487); it never validates the caller's scope against the employee's `dept_id` / `org_id`.

**Fix:**
```python
@app.route("/api/employees/<emp_id>/reset", methods=["POST"])
@require_role("superadmin", "org_admin", "dept_admin")
def reset_employee_face(emp_id):
    employees = load_employees()
    if emp_id not in employees:
        return jsonify({"error": "Сотрудник не найден"}), 404
    emp = employees[emp_id]
    caller_role = session.get("role")
    if caller_role == "dept_admin" and emp.get("dept_id") != session.get("dept_id"):
        return jsonify({"error": "forbidden"}), 403
    if caller_role == "org_admin" and emp.get("org_id") != session.get("org_id"):
        return jsonify({"error": "forbidden"}), 403
    # ... rest of function unchanged
```

---

### CR-03: /api/attendance returns all-org data to dept_admin and org_admin

**File:** `app.py:1733-1760`
**Issue:** `get_attendance` iterates over **all employees** and returns every record to any authenticated caller, regardless of role. An `org_admin` from org-A can query `/api/attendance?date=2026-06-13` and receive attendance records for employees in org-B. The same gap exists for `dept_admin`. The scoping that is correctly applied in `dept_attendance_today` (line 1531-1534) is completely absent here. This endpoint is called directly by `admin.html` via `fetch("/api/attendance?date=...")`.

**Fix:**
```python
def get_attendance():
    # ...existing date parsing...
    role = session.get("role")
    org_id = session.get("org_id")
    dept_id = session.get("dept_id")
    result = []
    for emp_id, emp in employees.items():
        if role == "org_admin" and emp.get("org_id") != org_id:
            continue
        if role == "dept_admin" and emp.get("dept_id") != dept_id:
            continue
        # ... rest of record building unchanged
```

---

### CR-04: /api/stats returns all-org statistics to dept_admin and org_admin

**File:** `app.py:1770-1817`
**Issue:** `get_stats` builds `emp_stats` from all employees and returns the full cross-org dataset to any authenticated caller. An `org_admin` calling `/api/stats?from=2026-01-01&to=2026-06-01` receives hours worked and late-day counts for employees from every other organisation. The late-detection logic within this function also uses a hard-coded `"09:00:00"` threshold (line 1798) instead of each employee's per-schedule start time, producing incorrect late-day counts for employees with non-default schedules — but the primary bug here is the scope leak.

**Fix:** Filter `emp_stats` initialization to the caller's scope before the date loop:
```python
def get_stats():
    role = session.get("role")
    org_id = session.get("org_id")
    dept_id = session.get("dept_id")
    # ...
    emp_stats = {
        eid: {"name": e["name"], "role": e["role"], "days": 0, "minutes": 0, "late_days": 0}
        for eid, e in employees.items()
        if role == "superadmin"
        or (role == "org_admin" and e.get("org_id") == org_id)
        or (role == "dept_admin" and e.get("dept_id") == dept_id)
    }
```

---

### CR-05: Insufficient date validation in timesheet override — arbitrary string stored as key

**File:** `app.py:1005-1008`
**Issue:** The date validation check (line 1005) only verifies that `date_str` is exactly 10 characters with hyphens at positions 4 and 7. It does not validate that the individual numeric components represent a real calendar date. A client can POST `"date": "9999-99-99"` or `"date": "2025-00-00"` and the string will be stored verbatim as a key in the overrides JSON. When `compute_symbol` later calls `day_date.isoformat()` and looks up that key, phantom overrides accumulate in the data store without ever matching a real date. Use `datetime.date.fromisoformat()` instead:

**Fix:**
```python
# Replace the current format-only check with a parse check
try:
    datetime.strptime(date_str, "%Y-%m-%d")
except (ValueError, TypeError):
    return jsonify({"error": "invalid_date"}), 422
```

---

### CR-06: New organisations are created with hard-coded default PINs (0000 / 1234)

**File:** `app.py:1130-1131`
**Issue:** Every organisation created via `POST /api/orgs` receives `kiosk_pin = hash_pin("0000")` and `reg_pin = hash_pin("1234")` at creation time (lines 1130-1131). Because `has_pin` is set to `True` (the hash is not `None`) on the kiosk page, the kiosk will ask for a PIN — and the correct answer is always "0000" unless an admin explicitly changes it. In a clinic environment where multiple orgs are created and staff do not immediately update PINs, this provides a trivial bypass for any employee registration link or kiosk session. The PIN should default to `None` (no PIN required) so there is no false sense of security.

**Fix:**
```python
orgs[org_id] = {
    # ...
    "kiosk_pin": None,   # require explicit configuration before enabling
    "reg_pin": None,
    # ...
}
```

---

## Warnings

### WR-01: XSS — employee name and role rendered without escaping in admin.html

**File:** `templates/admin.html:385, 387, 467, 468`
**Issue:** The attendance journal table and the monthly stats table interpolate `r.name`, `r.role`, `e.name`, and `e.role` directly into `innerHTML` template literals without any escaping. `admin.html` does not define an `escapeHtml` helper (unlike `org_admin.html` and `superadmin.html` which do). If an employee name or role contains `<script>alert(1)</script>`, it executes in the browser of any `dept_admin` or `org_admin` who views the report. The attendance data comes from `GET /api/attendance` which returns the raw `emp["name"]` and `emp["role"]` strings set at registration time.

**Fix:** Add an `escapeHtml` function to `admin.html` (identical to the one in `org_admin.html`) and wrap all user-supplied string interpolations: `${escapeHtml(r.name)}`, `${escapeHtml(r.role)}`, `${escapeHtml(e.name)}`, `${escapeHtml(e.role)}`.

---

### WR-02: save_orgs and save_depts truncate the file before acquiring the lock

**File:** `app.py:149-165`
**Issue:** `save_orgs` and `save_depts` open their target files with `"w"` mode (which truncates the file to zero bytes immediately), then call `fcntl.flock(..., LOCK_EX)`. The file is empty between `open()` and the moment the lock is granted. A concurrent reader calling `load_orgs()` / `load_depts()` — which has no locking — can see a zero-byte file and return `{}`, causing silent data loss. Compare with `save_users` and `save_timesheet_overrides` which correctly write to a temp file and use `os.replace()` for atomic promotion.

**Fix:** Rewrite both functions to match the safe atomic pattern:
```python
def save_orgs(data):
    tmp_fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, prefix="orgs_", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, ORGS_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```
Apply the same pattern to `save_depts`.

---

### WR-03: superadmin.html populates the PIN input with the raw bcrypt hash

**File:** `templates/superadmin.html:312`
**Issue:** In `startEdit(orgId)`, the edit form's PIN field is populated with `org.kiosk_pin || ''`. The value of `org.kiosk_pin` returned by `/api/orgs` is the full bcrypt hash string (e.g. `$2b$12$...`), not the plaintext PIN. This 60-character hash string is written into the `<input>` field. When a superadmin then saves the form without changing the PIN, `saveOrg` sends `kiosk_pin: "$2b$12$..."` to `PATCH /api/orgs/<id>/settings`. The server then calls `hash_pin("$2b$12$...")` — bcrypt-hashing a bcrypt hash — and the original PIN becomes permanently unverifiable.

**Fix:** Either (a) omit the PIN from `GET /api/orgs` response entirely (preferred), or (b) populate the edit field with a placeholder instead of the hash:
```javascript
// In startEdit():
document.getElementById('orgKioskPin').value = '';  // never populate with hash
document.getElementById('orgKioskPin').placeholder = org.kiosk_pin ? '(PIN установлен)' : 'Оставьте пустым — без PIN';
```
And in `saveOrg`, only include `kiosk_pin` in the PATCH body when the field is non-empty.

---

### WR-04: /api/users GET exposes all users to dept_admin with no scope filter

**File:** `app.py:1015-1033`
**Issue:** `list_users` applies a scope filter only for `org_admin` (lines 1022-1024). When `caller_role == "dept_admin"`, there is no filtering — the function falls through to `result.append(...)` for every user in the system. A `dept_admin` receives a list of all users including their `username`, `role`, `active` status, `org_id`, and `dept_id`. The `dept_admin` role should only see users within its own `dept_id` (or none at all).

**Fix:**
```python
for u in users.values():
    if caller_role == "org_admin" and u.get("org_id") != caller_org_id:
        continue
    if caller_role == "dept_admin":
        # dept_admin should only see users in their own dept
        caller_dept_id = session.get("dept_id")
        if u.get("dept_id") != caller_dept_id:
            continue
    result.append({ ... })
```

---

### WR-05: add_employee does not validate that org_id supplied by org_admin belongs to them

**File:** `app.py:1367-1369`
**Issue:** When `caller_role == "org_admin"`, the code sets `org_id = data.get("org_id") if caller_role != "dept_admin" else ...` (line 1368). This means an `org_admin` can pass any `org_id` in the request body and the employee will be created under that foreign org, because the only guard is `if caller_role == "dept_admin"`. The `org_admin` must be restricted to `caller_org_id` from the session.

**Fix:**
```python
if caller_role == "org_admin":
    org_id = caller_org_id  # always session value; ignore request body
elif caller_role == "dept_admin":
    org_id = data.get("org_id") or caller_org_id
else:
    org_id = data.get("org_id")
```

---

### WR-06: /timesheet — year value is not range-checked, allowing pathological calendar dates

**File:** `app.py:855-861`
**Issue:** The `timesheet` route validates `1 <= month_num <= 12` but does not constrain `year`. A caller can supply `?month=9999-12` and `calendar.monthrange(9999, 12)` will succeed, but `date(9999, 12, 1)` operations across 31 days will work fine in Python. The more dangerous case is a very large year value causing `compute_symbol` to compare `day_date > date.today()` — every day will be `None` (future), producing an empty timesheet rather than an error. The `org_admin` summary route at line 761 does correctly validate `2000 <= sum_year <= 2100`; the same guard should be applied here.

**Fix:**
```python
if not (1 <= month_num <= 12 and 2000 <= year <= 2100):
    raise ValueError("out of range")
```

---

### WR-07: update_user (PATCH) does not check org-scope for org_admin callers

**File:** `app.py:1077-1094`
**Issue:** `update_user` verifies only that the caller's role is higher in the hierarchy than the target's role. An `org_admin` from org-A can activate or deactivate a user in org-B by supplying their `user_id`. The org_admin scope restriction present in `list_users` is not enforced here.

**Fix:** Add an org-scope check after the role-hierarchy check:
```python
if caller_role == "org_admin" and target.get("org_id") != session.get("org_id"):
    return jsonify({"error": "forbidden"}), 403
```

---

## Info

### IN-01: Hard-coded late threshold "09:00:00" in /api/stats ignores per-employee schedules

**File:** `app.py:1798`
**Issue:** The stats endpoint uses the magic string `"09:00:00"` to determine whether a check-in is late, ignoring each employee's per-schedule `start` time. This is inconsistent with the `compute_symbol` logic and the `dept_attendance_today` endpoint which both compute a per-employee late threshold. Employees with a `10:00` start schedule will be counted as late when they check in at `09:30`.

**Fix:** Compute the late threshold per employee using the same helper pattern as `dept_attendance_today` lines 1554-1559.

---

### IN-02: conftest.py does not patch TIMESHEET_OVERRIDES_FILE before app module-level code runs

**File:** `tests/conftest.py:64-66`
**Issue:** `TIMESHEET_OVERRIDES_FILE` is monkeypatched inside `tmp_data` fixture, but module-level code in `app.py` runs at import time (including `init_config()` and `init_users()`). While those two functions only read/write `CONFIG_FILE` and `USERS_FILE`, the guard `if hasattr(_app, "TIMESHEET_OVERRIDES_FILE")` means patching only occurs if the attribute exists — which it does now that Phase 3 has landed. This is fine as implemented; the comment on line 64 is now stale and should be updated: `# TIMESHEET_OVERRIDES_FILE added in 03-02`.

---

### IN-03: Commented-out / dead code in admin.html — `creatable_roles` variable used in superadmin-only block

**File:** `templates/admin.html:146-149`
**Issue:** The "Пользователи" tab in `admin.html` is conditionally rendered only for `superadmin` (lines 83-85 and 127-173), and the `creatable_roles` Jinja variable is only populated when the caller is a `superadmin` (via the `admin_page` route which redirects superadmin to `superadmin_page`). In practice this block is unreachable for the roles that `admin.html` actually serves (dept_admin, org_admin after redirect), making the whole users tab in `admin.html` dead code. Consider removing this tab from `admin.html` entirely and consolidating user management in `superadmin.html` and `org_admin.html`.

---

_Reviewed: 2026-06-13T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
