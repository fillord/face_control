---
phase: 07-org-admin-ux-improvements
reviewed: 2026-06-15T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - app.py
  - templates/org_admin.html
  - templates/reports_partial.html
  - templates/timesheet_partial.html
findings:
  critical: 4
  warning: 6
  info: 3
  total: 13
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-06-15
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 7 introduces inline partial rendering for Reports and Timesheet tabs inside `org_admin.html`, a new `PATCH /api/employees/<emp_id>` endpoint with name/role/dept editing, inline employee editing via `saveEmployeeEdit()`, sortable tables, and a `loadInlinePanel()` fetch-and-inject mechanism.

The most serious issues are: (1) the `PATCH /api/employees/<emp_id>` endpoint allows `org_admin` to freely set the `role` field on any employee to an arbitrary string with no whitelist — a privilege escalation path; (2) `loadInlinePanel()` injects server-rendered HTML directly into `innerHTML` with no sanitization, and the partial responses include Jinja2-rendered user-controlled data (employee names) that is HTML-escaped by Jinja2's autoescaping but then re-injected verbatim through `innerHTML`, creating a layered XSS risk if autoescaping is disabled or a context is missed; (3) `tsSubmitForm()` in `timesheet_partial.html` does not reset the `_inlinePanelLoaded` cache, so the "Показать табель" submit button silently does nothing after the first panel load; (4) the `reports_partial.html` fetch calls for `/api/attendance`, `/api/stats`, and `/api/attendance/dates` have no error handling.

---

## Critical Issues

### CR-01: PATCH /api/employees/<emp_id> — `role` field accepts arbitrary string; no whitelist

**File:** `app.py:2155-2176`
**Issue:** The `update_employee_assignment` endpoint whitelists the key `role` for both `superadmin` and `org_admin` callers, but does not validate the *value*. An `org_admin` can PATCH any employee in their org with `{"role": "org_admin"}` or any other arbitrary role string, writing it directly to `emp.role`. There is no enum check against `ROLE_HIERARCHY` or any other list. While `Employee.role` is labelled as a display-level "position" field rather than the auth `User.role`, the field is returned verbatim in API responses and rendered in the attendance journal, creating a stored XSS vector if the value is injected into the DOM without escaping (see CR-02). Even absent XSS, free-text in a field called `role` is confusing and against the principle of minimal trust.

```python
# Current (app.py:2155-2176) — no value validation on "role":
if "role" in update_data:
    emp.role = update_data["role"]   # any string accepted

# Fix: add a whitelist of allowed employee position strings
ALLOWED_EMP_ROLES = {"employee", "manager", "doctor", "nurse", "staff"}  # expand as needed
if "role" in update_data:
    if update_data["role"] not in ALLOWED_EMP_ROLES:
        return jsonify({"error": "Недопустимая должность"}), 422
    emp.role = update_data["role"]
```

---

### CR-02: XSS — `reports_partial.html` renders `r.role` (employee position) without escaping

**File:** `templates/reports_partial.html:380,459`
**Issue:** `rRenderTable()` renders `r.role` using `rEscapeHtml(r.role)` in the journal table (line 380) — that one is safe. However `rLoadStats()` at line 459 renders `e.role` inside `rEscapeHtml(e.role)` — also safe. **But** the inline `checkInHtml`/`checkOutHtml` strings (lines 372-373) interpolate `r.check_in` and `r.check_out` directly into the returned HTML fragment without escaping:

```js
const checkInHtml  = r.check_in  ? `<span ...>${r.check_in}</span>`  : ...
const checkOutHtml = r.check_out ? `<span ...>${r.check_out}</span>` : ...
```

`r.check_in` and `r.check_out` come from the API response for `/api/attendance`, which reads `check_in_time` / `check_out_time` directly from `AttendanceRecord` ORM rows. These values are set by the `recognize()` endpoint at `now.strftime("%H:%M:%S")` — safe today. However: (a) `TimesheetOverride` symbols set by `PATCH /api/timesheet/override` are whitelisted, but `check_in_time` values are not sanitized on write in `recognize()`, and (b) the broader pattern of unescaped API data inside template literals is fragile. If `check_in_time` can ever come from a user-controlled source (e.g., a future import endpoint), this becomes a stored XSS.

Hardening fix:
```js
// reports_partial.html lines 372-373 — add escaping:
const checkInHtml  = r.check_in  ? `<span style="...;">${rEscapeHtml(r.check_in)}</span>`  : '<span style="color:#bdbdbd">—</span>';
const checkOutHtml = r.check_out ? `<span style="...;">${rEscapeHtml(r.check_out)}</span>` : '<span style="color:#bdbdbd">—</span>';
```

---

### CR-03: `loadInlinePanel()` uses `innerHTML` for server-rendered partial with script execution — stored XSS amplification

**File:** `templates/org_admin.html:1012-1030`
**Issue:** `loadInlinePanel()` fetches `/org_admin/partial/reports` or `/org_admin/partial/timesheet`, assigns the full response text to `contentEl.innerHTML`, then re-executes all `<script>` tags by appending them to `document.body`. The partial endpoints are auth-gated (`@require_role("org_admin", "superadmin")`), but the partials themselves render employee/department names via Jinja2 autoescaping inside the `<style>` block (safe). The dangerous pattern is `document.body.appendChild(newScript)` — executing injected scripts without sanitization. If any partial template is ever modified to include user-controlled data in a `<script>` context (currently `timesheet_partial.html` interpolates Jinja2 variables: `month_str`, `dept_id`, `role`, `dept_options`), a payload in a department name could escape into the script block.

Additionally, `_inlinePanelLoaded[tab] = true` is only set on success but **the flag is never cleared when `tsSubmitForm()` reloads the content** (see WR-01), meaning the cache-guard on line 1003 (`if (_inlinePanelLoaded[tab]) return;`) will prevent re-loading after the first load — a functional bug that is also a security miscalculation (old content is never refreshed).

```js
// Minimum fix: use textContent assignment for script bodies; avoid innerHTML for untrusted HTML
// Better: use a dedicated rendering layer or server-side templates instead of injecting full HTML
```

---

### CR-04: `update_employee_assignment` — `dept_admin` is not in the allowed roles for `PATCH /api/employees/<emp_id>` but `saveEmployeeEdit()` calls this endpoint unconditionally

**File:** `app.py:2138-2139`, `templates/org_admin.html:694`
**Issue:** `PATCH /api/employees/<emp_id>` is decorated with `@require_role("superadmin", "org_admin")` — `dept_admin` is excluded. However `saveEmployeeEdit()` in `org_admin.html` calls this endpoint for any logged-in user who has access to the Employees tab. The `org_admin.html` page is only shown to `org_admin` users (`@require_role("org_admin")` on the `/org_admin` route), so this is not currently an exploitable auth bypass for `dept_admin`. **However,** `update_employee_schedule` at line 2220 accepts `dept_admin` via `@require_role("superadmin", "org_admin", "dept_admin")`, while the companion `PATCH` for profile data does not. The two-step save in `saveEmployeeEdit()` (profile PATCH first, schedule PATCH second) means that if the profile PATCH fails with 403 for a `dept_admin` (if org_admin panel were ever accessible to dept_admin in the future), the user would receive a 403 silently after the schedule was already saved, leaving a partial update. The inconsistency in allowed roles between the two companion endpoints is a latent bug.

```python
# Fix: align the decorator to include dept_admin with appropriate scope gating, or
# add an explicit comment explaining why dept_admin is excluded from the profile PATCH.
@app.route("/api/employees/<emp_id>", methods=["PATCH"])
@require_role("superadmin", "org_admin", "dept_admin")  # dept_admin: scope-gated below
def update_employee_assignment(emp_id):
    ...
    if caller_role == "dept_admin" and emp.dept_id != session.get("dept_id"):
        return jsonify({"error": "forbidden"}), 403
```

---

## Warnings

### WR-01: `tsSubmitForm()` never resets `_inlinePanelLoaded['timesheet']` — "Показать табель" silently does nothing after first load

**File:** `templates/timesheet_partial.html:221-250`
**Issue:** When the user changes the month or department selector and clicks "Показать табель", `tsSubmitForm()` fires and fetches the new partial. However `_inlinePanelLoaded` (defined in `org_admin.html`) is only set to `true` in `loadInlinePanel()` on first success (line 1026). The `tsSubmitForm()` function writes directly to `contentEl.innerHTML` and re-executes scripts — but does not reset `_inlinePanelLoaded['timesheet']`. After the first submit, switching away from the Timesheet tab and back calls `switchTab('timesheet')` → `loadInlinePanel('timesheet')`, which sees `_inlinePanelLoaded['timesheet'] === true` and **returns immediately without re-fetching**, displaying whatever was last injected rather than the updated content. Subsequent tab switches are silently stale.

```js
// Fix in tsSubmitForm() (timesheet_partial.html): reset the cache flag before reloading
function tsSubmitForm(e) {
  e.preventDefault();
  // Reset so switchTab() re-fetches after returning to this tab
  if (typeof _inlinePanelLoaded !== 'undefined') {
    _inlinePanelLoaded['timesheet'] = false;
  }
  ...
```

---

### WR-02: `rLoadData()` and `rLoadStats()` in `reports_partial.html` have no error handling — unhandled promise rejections and silent failures

**File:** `templates/reports_partial.html:325-342, 413-463`
**Issue:** `rLoadData()` at line 325 calls `await fetch(...)` and `await resp.json()` with no try/catch. A network error, 401 session expiry, or non-JSON response will throw an uncaught promise rejection and leave the table in a stale "Загрузка..." state with no user feedback. Similarly `rLoadStats()` at line 413 has no error handling. `rLoadDates()` at line 304 calls `await fetch("/api/attendance/dates")` with no error check — if this fails, the date picker dropdown remains empty and `rLoadData(rToday)` at line 467 is called on an empty date.

```js
// Fix: add try/catch to each async function
async function rLoadData(dateStr) {
  try {
    const resp = await fetch("/api/attendance?date=" + dateStr);
    if (!resp.ok) {
      document.getElementById("rTableBody").innerHTML =
        '<tr><td colspan="7" style="text-align:center;color:#c62828;padding:28px;">Ошибка загрузки данных.</td></tr>';
      return;
    }
    const rows = await resp.json();
    // ...
  } catch (e) {
    document.getElementById("rTableBody").innerHTML =
      '<tr><td colspan="7" style="text-align:center;color:#c62828;padding:28px;">Ошибка соединения.</td></tr>';
  }
}
```

---

### WR-03: `toggleUser()` in `org_admin.html` swallows errors — PATCH result is never checked

**File:** `templates/org_admin.html:919-922`
**Issue:** `toggleUser()` calls `await fetch(...)` but neither checks `resp.ok` nor catches network errors. A failed PATCH (e.g., 403 because org_admin tries to deactivate a superadmin) silently reloads the users table without notifying the user. The table reload hides whether the toggle succeeded or failed.

```js
// Fix:
async function toggleUser(userId, active) {
  try {
    const resp = await fetch(`/api/users/${userId}`, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({active})
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      alert(data.error || 'Ошибка при изменении статуса.');
      return;
    }
    await loadOrgUsers();
  } catch (e) {
    alert('Ошибка соединения.');
  }
}
```

---

### WR-04: `sortEmployees()` uses `db` as a local variable name, shadowing the `db` constant from SQLAlchemy in the outer scope — silent sort bug

**File:** `templates/org_admin.html:937-939`
**Issue:** Inside the `sort` comparator for the `dept` key, the code uses `const db = allDepts.find(...)` — this shadows nothing in the JS context (it's a local block), but the variable is named `db` which is also the name of the comparator's parameter `b` reversed and is confusing. More importantly, `const db` in the closure at line 937 is fine syntactically, but the pattern uses `db` for dept-of-b and `da` for dept-of-a:

```js
const da = allDepts.find(d => d.id === a.dept_id);
const db = allDepts.find(d => d.id === b.dept_id);
```

The variable name `db` shadows any outer `db` in scope, which in this file is harmless (no Python `db` here). However it is confusing and a lint violation. The actual bug is that employees with `dept_id === null` or `dept_id` not found in `allDepts` will have `av = ''` and `bv = ''`, causing them to sort identically and remain in their original order rather than grouping unassigned employees consistently. This is a minor correctness issue but is technically incorrect for the sort specification.

```js
// Fix: rename to avoid confusion and handle missing dept
const deptA = allDepts.find(d => d.id === a.dept_id);
const deptB = allDepts.find(d => d.id === b.dept_id);
av = deptA ? deptA.name.toLowerCase() : '￿'; // sort unassigned last
bv = deptB ? deptB.name.toLowerCase() : '￿';
```

---

### WR-05: `get_attendance()` (`/api/attendance`) has no scope filter — returns all employees regardless of caller role

**File:** `app.py:2576-2607`
**Issue:** `/api/attendance` is called by `rLoadData()` in `reports_partial.html`. The endpoint is decorated with `@require_role("superadmin", "org_admin", "dept_admin")`, but the query at line 2580 does `Employee.query.all()` unconditionally — it does not filter by `session["org_id"]` for `org_admin` or by `session["dept_id"]` for `dept_admin`. An `org_admin` of Org A can see attendance records for employees of Org B. This is a data-isolation violation consistent with the CLAUDE.md requirement "Data isolation must be enforced server-side, not just hidden in UI."

```python
# Fix: add role-based employee scoping (mirrors get_employees() at line 2071)
@app.route("/api/attendance", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def get_attendance():
    role = session.get("role")
    org_id = session.get("org_id")
    dept_id = session.get("dept_id")
    day = request.args.get("date", date.today().isoformat())
    if role == "org_admin" and org_id:
        emps = Employee.query.filter_by(org_id=org_id).all()
    elif role == "dept_admin" and dept_id:
        emps = Employee.query.filter_by(dept_id=dept_id).all()
    else:
        emps = Employee.query.all()
    employees = {e.id: _emp_to_dict(e) for e in emps}
    ...
```

---

### WR-06: `get_stats()` (`/api/stats`) has no scope filter — same data isolation gap as `/api/attendance`

**File:** `app.py:2617-2678`
**Issue:** `/api/stats` is called by `rLoadStats()`. It calls `Employee.query.all()` at line 2622 with no org/dept scope check. All employee stats are returned to any authenticated caller including `dept_admin`. Same fix pattern as WR-05 applies.

---

## Info

### IN-01: `loadInlinePanel()` sets `_inlinePanelLoaded[tab]` before the script execution completes — race condition on re-entry

**File:** `templates/org_admin.html:1026`
**Issue:** `_inlinePanelLoaded[tab] = true` is set synchronously at line 1026, immediately after `contentEl.innerHTML = html`, before the `querySelectorAll('script').forEach(...)` loop finishes appending and executing scripts. If any injected script throws synchronously, the flag is already set and a subsequent `loadInlinePanel()` call will be a no-op, leaving the panel in a broken state with no recovery path. Setting the flag after script execution completes (end of the try block) would be safer.

---

### IN-02: `sortUsers()` sorts DOM rows by `data-*` attributes set at render time — stale after `toggleUser()` reload

**File:** `templates/org_admin.html:962-994`
**Issue:** `sortUsers()` sorts `<tr>` elements by `data-username` and `data-role` attributes. These attributes are set in `loadOrgUsers()`. After `toggleUser()` calls `loadOrgUsers()`, the table is re-rendered and the sort is reset to API order. The sort state variables `userSortKey` / `userSortAsc` are not re-applied after reload. The user clicks sort, toggles a user, and the sort disappears — a UX inconsistency. No code crash, but worth noting for a fix.

---

### IN-03: `creatable_roles` is not passed to `reports_partial.html` from `org_admin_partial_reports()`

**File:** `app.py:1572-1578`, `templates/reports_partial.html:124`
**Issue:** `reports_partial.html` uses `{{ creatable_roles }}` in the Jinja2 template (line 124: `{% for role_key, role_label in creatable_roles %}`). This block is inside `{% if session.role == 'superadmin' %}`, so it only renders for superadmin. The `org_admin_partial_reports()` route at line 1572 renders `reports_partial.html` but does **not** pass `creatable_roles` to the template. If a superadmin accesses the `/org_admin/partial/reports` endpoint (the route allows `"org_admin", "superadmin"`), Jinja2 will raise an `UndefinedError` on `creatable_roles` because it is not in the template context. This crashes the partial with a 500 error for superadmin users.

```python
# Fix in org_admin_partial_reports():
from app import ROLE_HIERARCHY, ROLE_DISPLAY
user = User.query.get(session.get("user_id"))
creator_role = user.role if user else ""
creatable_roles = []
if creator_role in ROLE_HIERARCHY:
    creator_idx = ROLE_HIERARCHY.index(creator_role)
    for role_key in ROLE_HIERARCHY[creator_idx + 1:]:
        creatable_roles.append((role_key, ROLE_DISPLAY.get(role_key, role_key)))
return render_template("reports_partial.html", username=username, creatable_roles=creatable_roles)
```

---

_Reviewed: 2026-06-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
