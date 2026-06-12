# Phase 3: T-13 Timesheet Grid - Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 5 (2 new, 3 modified)
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app.py` — T-13 section (new helpers + routes) | service + controller | CRUD + request-response | `app.py` — `dept_attendance_today()` + `save_users()` (lines 1069–1137, 58–70) | exact |
| `templates/timesheet.html` | template | request-response | `templates/dept_admin.html` | exact |
| `templates/org_admin.html` — DASH-04 section | template | request-response | `templates/org_admin.html` existing sections (lines 114–128) | role-match |
| `tests/test_timesheet.py` | test | batch | `tests/conftest.py` + existing test files | role-match |
| `tests/conftest.py` — TIMESHEET_OVERRIDES_FILE guard | config | N/A | `tests/conftest.py` lines 58–62 | exact |

---

## Pattern Assignments

### `app.py` — `load_timesheet_overrides()` / `save_timesheet_overrides()`

**Analog:** `app.py` lines 48–70 (`load_users()` / `save_users()`)

**load pattern** (lines 48–56):
```python
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARNING: load_users failed ({e}), returning empty dict", file=sys.stderr, flush=True)
            return {}
    return {}
```
Copy exactly — replace `USERS_FILE` with `TIMESHEET_OVERRIDES_FILE`, function name with `load_timesheet_overrides`.

**save pattern — atomic tmp+flock+replace** (lines 58–70):
```python
def save_users(data):
    tmp_fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, prefix="users_", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, USERS_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```
Copy exactly — replace `USERS_FILE` with `TIMESHEET_OVERRIDES_FILE`, prefix with `"overrides_"`.

**Do NOT use** the simpler `save_orgs()` / `save_depts()` flock pattern (lines 147–163) — those lock a live file handle without tmp+replace and are less safe for frequent writes.

---

### `app.py` — `@require_role` decorator application

**Analog:** `app.py` lines 99–115

```python
def require_role(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                return redirect(url_for("login_page", next=request.path))
            users = load_users()
            user = users.get(user_id)
            if not user or not user.get("active"):
                session.clear()
                return redirect(url_for("login_page"))
            if allowed_roles and user.get("role") not in allowed_roles:
                return render_template("403.html"), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
```

Apply as `@require_role("dept_admin", "org_admin", "superadmin")` to both `/timesheet` and `/api/timesheet/override`.

---

### `app.py` — `/timesheet` GET route scoping

**Analog:** `app.py` lines 1069–1137 (`dept_attendance_today()`)

**Scoping pattern** (lines 1073–1089):
```python
role = session.get("role")
dept_id = session.get("dept_id")
org_id = session.get("org_id")

employees = load_employees()
attendance = load_attendance()

# Filter employees by scope
if role == "dept_admin":
    scoped = {eid: e for eid, e in employees.items() if e.get("dept_id") == dept_id}
elif role == "org_admin":
    scoped = {eid: e for eid, e in employees.items() if e.get("org_id") == org_id}
else:  # superadmin — all employees
    scoped = employees
```

**Late detection pattern** (lines 1095–1122) — exact threshold string construction to copy:
```python
schedule = emp.get("schedule", {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]})
work_days = schedule.get("work_days", [1, 2, 3, 4, 5])

schedule_start = schedule.get("start", "09:00")
sh, sm = map(int, schedule_start.split(":"))
late_m = sm + 15
if late_m < 60:
    late_threshold = f"{sh:02d}:{late_m:02d}:00"
else:
    late_threshold = f"{sh + 1:02d}:{late_m % 60:02d}:00"

if check_in:
    if check_in > late_threshold:
        status = "late"
```

Note `today_weekday = date.today().weekday() + 1` (line 1080) — this converts `weekday()` to ISO. In `compute_symbol()`, use `day_date.isoweekday()` directly instead (avoids the +1 conversion entirely).

**Response pattern** (lines 1134–1137):
```python
return jsonify({
    "employees": result,
    "stats": {"present": present, "absent": absent, "late": late},
})
```
For the `/timesheet` GET route, use `render_template("timesheet.html", ...)` instead of `jsonify`.

---

### `app.py` — file path constant declaration

**Analog:** `app.py` lines 13–21

```python
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EMPLOYEES_FILE = os.path.join(DATA_DIR, "employees.json")
ATTENDANCE_FILE = os.path.join(DATA_DIR, "attendance.json")
ORGS_FILE = os.path.join(DATA_DIR, "orgs.json")
DEPTS_FILE = os.path.join(DATA_DIR, "depts.json")
```

Add immediately after `DEPTS_FILE`:
```python
TIMESHEET_OVERRIDES_FILE = os.path.join(DATA_DIR, "timesheet_overrides.json")
```

---

### `app.py` — section header style

**Analog:** `app.py` line 28, 46, 92, 117, 139

```python
# ─── Config / Auth ────────────────────────────────────────────────────────────
# ─── Auth: Users ──────────────────────────────────────────────────────────────
# ─── Auth: RBAC ───────────────────────────────────────────────────────────────
# ─── Data helpers ─────────────────────────────────────────────────────────────
# ─── Data helpers: Orgs / Depts ───────────────────────────────────────────────
```

New section header to add:
```python
# ─── T-13 Timesheet ───────────────────────────────────────────────────────────
```

---

### `app.py` — `/api/timesheet/override` error response pattern

**Analog:** `app.py` — existing API endpoints using `jsonify({...}), 4XX`

```python
return jsonify({"error": "employee_not_found"}), 404
return jsonify({"error": "forbidden"}), 403
return jsonify({"error": "invalid_symbol"}), 422
return jsonify({"symbol": symbol, "auto": False})   # 200 on success
return jsonify({"deleted": True})                    # 200 on DELETE success
```

---

### `templates/timesheet.html` (new file)

**Analog:** `templates/dept_admin.html` (full file)

**HTML boilerplate + CSS variables** (lines 1–61):
```html
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>...</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f4f6fb; color: #1a2340; min-height: 100vh; }
header { background: #fff; border-bottom: 1px solid #e2e6f0; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.logo { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; }
.logo-icon { width: 34px; height: 34px; background: #1565C0; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
.page { max-width: 1100px; margin: 0 auto; padding: 24px 20px; }
.table-card { background: #fff; border: 1px solid #e2e6f0; border-radius: 14px; overflow: hidden; margin-bottom: 20px; }
table { width: 100%; border-collapse: collapse; }
thead { background: #f8fafd; }
th { padding: 12px 12px; text-align: left; font-size: 11px; font-weight: 600; color: #546e7a; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #e2e6f0; white-space: nowrap; }
td { padding: 12px 12px; font-size: 13px; border-bottom: 1px solid #f0f3f8; vertical-align: middle; }
tr:last-child td { border-bottom: none; }
.hidden { display: none; }
.btn-primary { padding: 8px 16px; background: #1565C0; color: #fff; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-secondary { padding: 8px 16px; background: #fff; border: 1px solid #cfd8dc; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; color: #546e7a; }
</style>
```

**Header HTML** (lines 64–70):
```html
<header>
  <div class="logo"><div class="logo-icon">🏥</div> МедКонтроль{% if dept_name %} — {{ dept_name }}{% endif %}</div>
  <div class="header-right">
    <span class="user-badge">{{ username }}</span>
    <a href="/" class="btn-logout" style="border-color:#cfd8dc;color:#546e7a;">← Киоск</a>
    <a href="/logout" class="btn-logout">Выйти</a>
  </div>
</header>
```

**Table structure pattern** (lines 97–110):
```html
<div class="table-card">
  <table>
    <thead>
      <tr>
        <th>Сотрудник</th>
        <!-- day columns -->
      </tr>
    </thead>
    <tbody>
      <tr><td colspan="..." class="empty-state">Загрузка...</td></tr>
    </tbody>
  </table>
</div>
```

**JS fetch + error handling pattern** (lines 167–184):
```javascript
async function loadAttendance() {
  try {
    var resp = await fetch('/api/dept_attendance_today');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    var data = await resp.json();
    // ... update DOM
  } catch (e) {
    // update DOM with error state
  }
}
```

For `timesheet.html`, the override fetch follows the same `try { resp = await fetch(...); if (!resp.ok) ... } catch(e) { ... }` structure. Use `alert()` (consistent with `org_admin.html`) or a 3-second banner div for 403/422 errors since the project has no toast utility function.

**escHtml utility** (lines 318–325):
```javascript
function escHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
```
Copy verbatim into `timesheet.html` `<script>` block.

**JS section header style** (line 133):
```javascript
// ─── Tab switching ─────────────────────────────────────────────────────────────
```
Use the same `// ─── Section Name ──────...` style for all JS sections in `timesheet.html`.

---

### `templates/org_admin.html` — DASH-04 section

**Analog:** `templates/org_admin.html` lines 114–128 (existing dept table section)

```html
<div class="table-card">
  <table>
    <thead>
      <tr>
        <th>Название</th>
        <th>Руководитель</th>
        <th>Сотрудников</th>
        <th>Действия</th>
      </tr>
    </thead>
    <tbody id="deptsTableBody">
      <tr><td colspan="4" style="text-align:center;color:#90a4ae;padding:28px;">Загрузка...</td></tr>
    </tbody>
  </table>
</div>
```

Copy this table-card structure for the DASH-04 summary table. Change columns to: Отдел, Сотрудников, Дней (Я), Рабочих дней, Явка (%). The month picker is a `<form method="GET" action="/org_admin">` with a `<input type="month" name="summary_month">` — consistent with D-10 (GET form, bookmarkable URL).

---

### `tests/conftest.py` — TIMESHEET_OVERRIDES_FILE guard

**Analog:** `tests/conftest.py` lines 58–62

```python
# ORGS_FILE / DEPTS_FILE do not exist in app.py until plan 02-02 — guard with hasattr
if hasattr(_app, "ORGS_FILE"):
    monkeypatch.setattr(_app, "ORGS_FILE", str(data_dir / "orgs.json"))
if hasattr(_app, "DEPTS_FILE"):
    monkeypatch.setattr(_app, "DEPTS_FILE", str(data_dir / "depts.json"))
```

Add immediately after `DEPTS_FILE` guard:
```python
# TIMESHEET_OVERRIDES_FILE does not exist in app.py until plan 03-01 — guard with hasattr
if hasattr(_app, "TIMESHEET_OVERRIDES_FILE"):
    monkeypatch.setattr(_app, "TIMESHEET_OVERRIDES_FILE", str(data_dir / "timesheet_overrides.json"))
```

---

## Shared Patterns

### Role + Session Scoping
**Source:** `app.py` lines 1073–1089 (`dept_attendance_today()`)
**Apply to:** `/timesheet` route, `/api/timesheet/override` route, DASH-04 computation in `/org_admin` route

```python
role = session.get("role")
dept_id = session.get("dept_id")
org_id = session.get("org_id")

if role == "dept_admin":
    scoped = {eid: e for eid, e in employees.items() if e.get("dept_id") == dept_id}
elif role == "org_admin":
    scoped = {eid: e for eid, e in employees.items() if e.get("org_id") == org_id}
else:
    scoped = employees
```

### 403 Rendering
**Source:** `app.py` line 112
**Apply to:** `/timesheet` dept_id mismatch check, `/api/timesheet/override` scope check

```python
return render_template("403.html"), 403   # page routes
return jsonify({"error": "forbidden"}), 403  # API routes
```

### JSON Load Helper
**Source:** `app.py` lines 119–123 (`load_employees()`)
**Apply to:** `load_timesheet_overrides()` (use `load_users()` pattern with try/except for robustness)

```python
def load_employees():
    if os.path.exists(EMPLOYEES_FILE):
        with open(EMPLOYEES_FILE) as f:
            return json.load(f)
    return {}
```

### Jinja2 render_template Call
**Source:** `app.py` lines 518–528 (`org_admin_page()`), line 540 (`dept_admin_page()`)
**Apply to:** `/timesheet` route final return

```python
return render_template(
    "timesheet.html",
    username=username,
    role=role,
    dept_name=dept_name,
    # ... grid data vars
)
```

### Schedule Default Fallback
**Source:** `app.py` line 1095
**Apply to:** `compute_symbol()` and any loop reading employee schedule

```python
schedule = emp.get("schedule", {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]})
```

### CSS Color Palette
**Source:** `templates/dept_admin.html` lines 26–29, 37–39
**Apply to:** T-13 symbol cell background/foreground colors in `timesheet.html`

```css
/* Existing badge colors — map to symbol colors */
.badge-present { background: #E8F5E9; color: #1B5E20; }   /* → Я */
.badge-late    { background: #FFF3E0; color: #BF360C; border: 1px solid #FFCC80; }  /* → О, ОУ */
.badge-absent  { background: #FAFAFA; color: #90A4AE; border: 1px solid #e0e0e0; }  /* → НН */
/* New colors needed: В (gray), Б (blue-tint), К (purple-tint), У (orange), П (red-tint) */
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/test_timesheet.py` | test | batch | No test file exists for timesheet yet — Wave 0 creates it from scratch. Structure follows existing test files in `tests/` but no direct analog for symbol engine unit tests. Use RESEARCH.md test map (section "Validation Architecture") as specification. |

---

## Metadata

**Analog search scope:** `app.py`, `templates/dept_admin.html`, `templates/org_admin.html`, `tests/conftest.py`
**Files scanned:** 4 analog files read in full or targeted sections
**Pattern extraction date:** 2026-06-13
