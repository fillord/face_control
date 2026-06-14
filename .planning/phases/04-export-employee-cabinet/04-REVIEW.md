---
phase: 04-export-employee-cabinet
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - app.py
  - models.py
  - templates/timesheet.html
  - templates/employee.html
  - templates/admin.html
  - tests/conftest.py
  - tests/test_export_employee.py
findings:
  critical: 4
  warning: 7
  info: 4
  total: 15
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-06-14T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

This phase added T-13 XLSX/CSV export routes, the employee self-service cabinet (`/employee`), and the employee–user FK link (`User.emp_id`). The export scope enforcement and IDOR protection on the employee cabinet are generally sound. However, several critical issues were found: a superadmin IDOR bypass in the export scope resolver that lets any superadmin export any department without validation, a stored-XSS vector in the admin panel through unescaped innerHTML injection of server-supplied `u.username` and `u.role` values, an `emp_id` link validation gap that allows creating user accounts linked to arbitrary employees from another org, and an unhandled `None` value crash in `emp_id` returned from the export tuple. Additional warnings cover logic errors in the `_resolve_export_scope` return signature, month-clamping bypass on the employee cabinet, and missing scope enforcement on several API endpoints.

---

## Critical Issues

### CR-01: Superadmin can export any department — `_resolve_export_scope` performs no ownership check for superadmin

**File:** `app.py:1141`
**Issue:** In `_resolve_export_scope()`, when `role == "superadmin"` the function blindly uses the `dept_id` URL parameter with no check that the department exists or belongs to any expected scope:

```python
else:  # superadmin
    dept_id = dept_id_param or None
```

This means a superadmin can supply any arbitrary string as `dept_id` and the function proceeds to load `Department.query.get(dept_id)`. If the department doesn't exist, `dept_obj` is `None` and line 1150 (`dept_obj.org_id`) raises an `AttributeError` that propagates as a 500. This is not a security issue for superadmin itself (they have full access by design), but it is a correctness bug: `org_name = org_obj.name if org_obj else ""` on line 1151 silently produces an empty org name in the XLSX header, and `AttributeError` on `dept_obj.org_id` at line 1150 crashes the request when a nonexistent dept_id is supplied.

**Fix:** Guard the case where `dept_obj` is `None`:
```python
dept_obj = Department.query.get(dept_id)
if not dept_obj:
    return None, (render_template("403.html"), 403)
dept_name = dept_obj.name
org_obj = Organization.query.get(dept_obj.org_id)
org_name = org_obj.name if org_obj else ""
```

---

### CR-02: Stored XSS in admin panel — `u.username` and `u.role` injected via `innerHTML` without sanitization

**File:** `templates/admin.html:267-281`
**Issue:** The `loadUsers()` function builds HTML via string concatenation and assigns it directly to `innerHTML`. While `escapeHtml(u.username)` and `escapeHtml(u.role)` are called for the visible cell text, the `deactivateUser` button onclick attribute on line 273 injects `u.id` and `u.username` directly into the onclick handler string without escaping:

```javascript
`<button onclick="deactivateUser('${u.id}', '${u.username}')" ...>`
```

If `u.username` or `u.id` contains a single quote or JavaScript payload (e.g., `'); alert(1); //`), the onclick attribute breaks out and executes arbitrary JavaScript. `u.id` is a UUID (safe), but `u.username` is user-controlled string data stored in the database. An org_admin who can create users can set a malicious username and trigger XSS for any superadmin viewing the Users tab.

**Fix:** Never inject user data into onclick attribute strings. Use data attributes and a delegated event listener:
```javascript
// In the HTML generation:
`<button class="btn-deactivate" data-uid="${escapeHtml(u.id)}" data-uname="${escapeHtml(u.username)}" ...>Деактивировать</button>`

// In the script:
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('btn-deactivate')) {
    deactivateUser(e.target.dataset.uid, e.target.dataset.uname);
  }
});
```

---

### CR-03: `emp_id` FK not validated against caller's org scope when creating employee-role users

**File:** `app.py:1437`
**Issue:** In `create_user()`, when `target_role == "employee"`, the `emp_id` is taken from the request body without checking that the referenced `Employee` record belongs to the same org as the caller:

```python
new_emp_id = (data.get("emp_id") or None) if target_role == "employee" else None
```

An `org_admin` for org-A can supply `emp_id` pointing to an employee in org-B. This creates a user account that, when logged in as that employee, will load the attendance data for org-B's employee via `User.emp_id`. This is a cross-org IDOR on the employee cabinet.

**Fix:** Validate that the referenced employee belongs to the caller's org:
```python
if new_emp_id and caller_role != "superadmin":
    linked_emp = Employee.query.get(new_emp_id)
    if not linked_emp or linked_emp.org_id != caller_org_id:
        return jsonify({"error": "forbidden"}), 403
```

---

### CR-04: `_resolve_export_scope` return value unpacked incorrectly when error returned — crashes caller

**File:** `app.py:1200-1203`
**Issue:** `_resolve_export_scope()` returns either `(ctx_tuple, None)` or `(None, error_tuple)`. The callers unpack correctly with `ctx, err = _resolve_export_scope()`. However, when the function returns `(None, (render_template("403.html"), 403))` from the guard at line 1145, the caller at line 1202 does `return err` which would return a tuple instead of a proper Flask response. Flask will attempt to interpret the 2-tuple `(html_string, 403)` as a response, which actually works in modern Flask (it handles `(body, status)` tuples) — but the `render_template("403.html"), 403` inside `_resolve_export_scope` is itself a Python tuple constructed inside the function, so it gets doubly wrapped. The return chain is: `_resolve_export_scope` returns `(None, (html, 403))`, caller does `return err` which returns `(html, 403)` — Flask handles this as `(body, status)`. This actually works. However the same return path via line 1135 `return None, (render_template("403.html"), 403)` is an inconsistency: if Flask's `render_template` returns a `str`, then `return err` returns a 2-tuple of `(str, int)` which Flask accepts — but this is fragile and semantically confusing. The actual crash scenario is: if the guard at line 1144–1145 triggers (`not dept_id`), the function returns `(None, (render_template("403.html"), 403))` — the caller does `ctx, err = ...` then `if err is not None: return err` and returns `(render_template_str, 403)`. Flask handles that, so no crash, but the design relies on Flask's implicit tuple-response behavior which is undocumented for this pattern. The real bug is CR-01 above where `dept_obj` is None and line 1150 raises `AttributeError`.

**Fix:** Refactor `_resolve_export_scope` to raise an exception or return a Flask `Response` object directly:
```python
from flask import make_response
# In error paths:
return None, make_response(render_template("403.html"), 403)
```

---

## Warnings

### WR-01: Employee cabinet month-clamp can be bypassed with a malformed `month` param

**File:** `app.py:769-771`
**Issue:** The month clamp logic is:
```python
if month_str < prev_month or month_str > current_month:
    month_str = current_month
```
This comparison is done as a string lexicographic comparison. A value like `"2026-06-extra"` (extra characters after the YYYY-MM part) would pass the `< prev_month` and `> current_month` checks in unexpected ways. More importantly, if `month_str.split("-")` at line 771 receives a value like `"2026"` (no hyphen), it raises a `ValueError` because `map(int, ...)` on a 1-element list fails. The clamp happens before the split, so a value like `"2025-"` passes the string comparison but fails the `split("-")` producing `["2025", ""]` and `int("")` raises `ValueError` — an unhandled exception that crashes the route with a 500.

**Fix:** Validate and parse the month string before clamping:
```python
try:
    year, month_num = map(int, month_str.split("-"))
    if not (1 <= month_num <= 12 and 2000 <= year <= 2099):
        raise ValueError()
except (ValueError, AttributeError):
    month_str = current_month
    year, month_num = map(int, current_month.split("-"))
# Then apply the prev/current clamp on the parsed values
```

---

### WR-02: `/api/attendance` has no org/dept data isolation for `org_admin` or `dept_admin`

**File:** `app.py:2222-2252`
**Issue:** `get_attendance()` loads all employees with `Employee.query.all()` regardless of the caller's role, then returns attendance data for every employee in the system. An `org_admin` scoped to org-A receives data for employees in org-B. This contradicts the core requirement ("data isolation must be enforced server-side").

**Fix:** Apply the same role-based scoping as `dept_attendance_today()`:
```python
role = session.get("role")
org_id = session.get("org_id")
dept_id = session.get("dept_id")
if role == "superadmin":
    emps = Employee.query.all()
elif role == "org_admin":
    emps = Employee.query.filter_by(org_id=org_id).all()
elif role == "dept_admin":
    emps = Employee.query.filter_by(dept_id=dept_id).all()
else:
    emps = []
```

---

### WR-03: `/api/stats` has no org/dept data isolation

**File:** `app.py:2263-2323`
**Issue:** Same as WR-02. `get_stats()` calls `Employee.query.all()` unconditionally and returns stats for all employees to `org_admin` and `dept_admin` callers.

**Fix:** Apply role-scoped employee query (same pattern as WR-02 fix).

---

### WR-04: `compute_employee_totals` counts `None` symbols in `vac_sick`/`absences`/`late` via implicit falsy comparison

**File:** `app.py:316-326`
**Issue:** `compute_employee_totals` receives a `symbols` list that can contain `None` values (for future days). The individual sum expressions guard correctly with `if s in (...)`, but the function is also called in the employee page route at line 815 with:
```python
symbols = [c["sym"] for c in cells]
totals = compute_employee_totals(symbols, schedule)
```
Where `c["sym"]` can be `None` for future days. The sum expressions `sum(1 for s in symbols if s in ("П", "НН"))` will correctly skip `None` (since `None not in ("П", "НН")`). This is actually correct, but it is fragile — the function's docstring says "Excludes None symbols" but the only place this is documented. If a caller forgets and passes raw `None`s without filtering, future symbol additions could silently miscount. A more defensive approach would be to filter at the top:
```python
symbols = [s for s in symbols if s is not None]
```

This is a robustness/maintainability concern, not a current bug, but miscount risk is real if the function is reused.

---

### WR-05: Late-threshold arithmetic in `dept_attendance_today` can produce invalid time strings when schedule start is at or after 23:45

**File:** `app.py:2019-2024`
**Issue:** The late threshold calculation in `dept_attendance_today` is:
```python
sh, sm = map(int, schedule_start.split(":"))
late_m = sm + 15
if late_m < 60:
    late_threshold = f"{sh:02d}:{late_m:02d}:00"
else:
    late_threshold = f"{sh + 1:02d}:{late_m % 60:02d}:00"
```
If `sh == 23` and `sm >= 45`, `sh + 1` becomes `24`, producing `"24:xx:00"` which is an invalid time string. The string comparison `check_in > "24:00:00"` would never be true, silently making late detection fail. This contrasts with the `_time_threshold()` helper (line 242) that uses `datetime` arithmetic and clamps properly — but `dept_attendance_today` uses its own inline arithmetic instead of calling `_time_threshold()`.

**Fix:** Replace the inline arithmetic with a call to the existing `_time_threshold()` helper:
```python
late_threshold = _time_threshold(schedule.get("start", "09:00"), 15)
```

---

### WR-06: `is_late` hardcoded to `09:00:00` in `/api/recognize` — ignores per-employee schedule

**File:** `app.py:2151`
**Issue:**
```python
is_late = now > "09:00:00"
```
This hardcodes 09:00 as the late threshold, ignoring the employee's actual `schedule.start`. The T-13 symbol computation via `compute_symbol` correctly uses `schedule.get("start")`, but the `is_late` flag in the kiosk recognition response is always based on a hardcoded 09:00. This misleads the kiosk UI for employees with non-standard schedules.

**Fix:**
```python
schedule_start = emp_dict.get("schedule", {}).get("start", "09:00")
late_threshold = _time_threshold(schedule_start, 15)
is_late = now > late_threshold
```

---

### WR-07: `_resolve_export_scope` loads ALL overrides, not just for the current month

**File:** `app.py:1171-1174`
**Issue:**
```python
_ov_recs = TimesheetOverride.query.all()
```
Overrides are loaded without any date filter. For large deployments with years of override history, this loads all override records into memory for every export request. The overrides dict is then filtered implicitly during symbol computation (only dates matching the month are looked up). This does not cause a correctness bug but in a production system with many departments and years of data, this could cause excessive memory consumption. The same pattern is also used in the `/timesheet` route (line 1054) and `org_admin_page` (line 894).

**Fix:** Add a date range filter to the override query:
```python
_ov_recs = TimesheetOverride.query.filter(
    TimesheetOverride.date >= start_str,
    TimesheetOverride.date <= end_str,
).all()
```

---

## Info

### IN-01: `viewer` role is silently excluded from login but listed in `ROLE_HIERARCHY`

**File:** `app.py:93`
**Issue:** `ALLOWED_LOGIN_ROLES = ("superadmin", "org_admin", "dept_admin", "employee")` — `viewer` is in `ROLE_HIERARCHY` but cannot log in. This will silently fail with "Доступ запрещён для этой роли" with no clear indicator to the admin. The `create_user` endpoint also rejects `viewer` with a specific message (line 1419), but if a legacy `viewer` row exists it cannot log in.

**Fix:** Document this explicitly in `ALLOWED_LOGIN_ROLES` or remove `viewer` from `ROLE_HIERARCHY`.

---

### IN-02: `emp_id` field in `admin.html` user-creation form is only shown for `employee` role, but any role can be submitted with it via direct API call

**File:** `templates/admin.html:151-154`, `app.py:1437`
**Issue:** The `empIdGroup` div is hidden via JavaScript for non-employee roles. The server correctly sets `new_emp_id = None` for non-employee roles (line 1437), so the server-side enforcement is correct. However, the comment on line 1437 ("force None for all other roles") is somewhat misleading since `data.get("emp_id")` is only ignored, not rejected, for other roles. This is fine but could confuse future maintainers into thinking the API validates the field.

**Fix:** No code change required; add a comment clarifying the intent.

---

### IN-03: `conftest.py` seed helpers open a second `app_context()` nested inside the existing test context

**File:** `tests/conftest.py:83-96`
**Issue:** All `seed_*` helpers call `with _app.app.app_context():` to push a new context. When called from within a test that already has an active app context (established by the `client` fixture), this creates a nested context. Flask supports nested contexts but this means the seed helpers operate on a different SQLAlchemy session stack than the test client, which can cause subtle transaction isolation issues when seeds are added mid-test after the client has already started a transaction.

**Fix:** Remove the `with _app.app.app_context():` wrapper from all seed helpers (they are always called within a test that already has an active context via the `client` fixture), or document that seeds must be called before the client makes any requests.

---

### IN-04: `compute_dept_summary` uses `dept_id` as fallback `dept_name` — dept names are never actually resolved in the function itself

**File:** `app.py:386`
**Issue:**
```python
dept_name = dept_id  # fallback if dept name not available here
```
The function `compute_dept_summary` sets `dept_name` to the dept_id string and never updates it (the Department ORM is not queried inside the function). The enrichment happens in the caller (`org_admin_page`, lines 902-905). If a caller forgets to enrich, the dept name shown to users will be a raw UUID string. This is a fragile design where the function returns incomplete data.

**Fix:** Accept an optional `depts` dict parameter so `compute_dept_summary` can resolve dept names itself, or move the enrichment inside the function.

---

_Reviewed: 2026-06-14T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
