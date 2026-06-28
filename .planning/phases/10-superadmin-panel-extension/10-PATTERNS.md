# Phase 10: Superadmin Panel Extension — Pattern Map

**Mapped:** 2026-06-28
**Files analyzed:** 3 (app.py, models.py, templates/superadmin.html) + 1 supporting (templates/base.html)
**Analogs found:** all from direct codebase inspection

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app.py` — new superadmin API endpoints | controller | request-response (CRUD) | `app.py` existing `/api/orgs`, `/api/users` endpoints | exact |
| `app.py` — `create_user()` line 1985 fix | controller | request-response | same function, lines 1965-2018 | exact (one-line change) |
| `app.py` — `get_holidays_set()` modification | utility | transform | same function, lines 289-291 | exact (drop-in replacement) |
| `app.py` — `superadmin_export_xlsx()` new endpoint | controller | file-I/O | `export_timesheet_xlsx()`, lines 1653-1714 | role-match |
| `models.py` — `HolidayCalendar` new model | model | CRUD | `AppSetting` (lines 177-184) and `AuditLog` (lines 189-204) | role-match |
| `templates/superadmin.html` — new tabs + JS | component | request-response | existing `panelUsers` / `panelSystem` blocks + JS functions | exact |
| `templates/base.html` — new nav links (superadmin block) | config | — | lines 153-171 existing nav links | exact |

---

## Pattern Assignments

### `app.py` — New superadmin API endpoints (SADM-02, 03, 04, 06)

**Analog:** `app.py` existing `GET /api/users` and `GET /api/orgs` endpoints

**Route + decorator pattern** (app.py lines 1226-1228, 1965-1966):
```python
@app.route("/superadmin/<tab>")
@app.route("/superadmin")
@require_role("superadmin")
def superadmin_page(tab="orgs"):
```
```python
@app.route("/api/users", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def list_users():
```
All new endpoints follow: `@app.route("/api/superadmin/<name>") @require_role("superadmin") def handler_name():`

**ORM query + dict-map + jsonify pattern** (app.py lines 1950-1963):
```python
all_users = User.query.filter(User.role != "superadmin").all()
result = [
    {
        "id": u.id,
        "username": u.username,
        "role": u.role,
        "org_id": u.org_id,
        "active": u.active,
    }
    for u in all_users
]
return jsonify(result)
```
Use this exact pattern for `superadmin_employees()`, `superadmin_devices()`, `superadmin_logs()`, `superadmin_attendance_stats()`.

**Error handling pattern** (app.py lines 2000-2014):
```python
try:
    db.session.add(...)
    db.session.commit()
except Exception:
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500
```

**write_audit() call pattern** (app.py lines 2015-2016):
```python
write_audit("user_create", target_type="user", target_id=user_id,
            new_value={"username": username, "role": target_role, "org_id": new_org_id})
```
Call `write_audit()` immediately after `db.session.commit()` succeeds, before the return.

**Section divider style** (app.py line 574):
```python
# ─── Audit helpers ────────────────────────────────────────────────────────────
```
Use same Unicode box-drawing style for new section: `# ─── API: Superadmin Extensions ─────────────────────────────────────────────`

---

### `app.py` — `create_user()` fix at line 1985 (SADM-07)

**Analog:** same function, lines 1984-1986

**Exact lines to replace:**
```python
# superadmin may only create org_admin; org_admin manages all roles below them
if creator_role == "superadmin" and target_role != "org_admin":
    return jsonify({"error": "Суперадминистратор может создавать только администраторов организаций"}), 403
```

**Replace with:**
```python
# superadmin may create org_admin, dept_admin, hr_viewer (SADM-07)
_SA_ALLOWED = {"org_admin", "dept_admin", "hr_viewer"}
if creator_role == "superadmin" and target_role not in _SA_ALLOWED:
    return jsonify({"error": "Суперадминистратор может создавать org_admin, dept_admin, hr_viewer"}), 403
```

Also add server-side guard (no analog exists — new logic):
```python
if target_role == "dept_admin" and not new_dept_id:
    return jsonify({"error": "Для роли dept_admin необходимо указать отдел"}), 400
```
Insert this guard after `new_dept_id` is resolved (after line 1996).

---

### `app.py` — `get_holidays_set()` modification (SADM-05)

**Analog:** same function, lines 289-291

**Current implementation:**
```python
def get_holidays_set(year):
    """Return a set of ISO date strings for KZ holidays in the given year."""
    return set(KZ_HOLIDAYS.get(year, []))
```

**Replace body with (signature unchanged — callers unaffected):**
```python
def get_holidays_set(year):
    """Return a set of ISO date strings for KZ holidays in the given year.
    DB-backed (SADM-05): queries HolidayCalendar first; falls back to KZ_HOLIDAYS if DB empty for that year.
    """
    db_rows = HolidayCalendar.query.filter_by(year=year).all()
    if db_rows:
        return {r.date for r in db_rows}
    return set(KZ_HOLIDAYS.get(year, []))
```

`HolidayCalendar` must be imported before this function (add to models import at line 21).

---

### `app.py` — `superadmin_export_xlsx()` new endpoint (SADM-01)

**Analog:** `export_timesheet_xlsx()`, lines 1653-1714

**Imports already present** (app.py lines 14-17):
```python
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
```

**BytesIO + send_file pattern** (app.py lines 1705-1714):
```python
buf = BytesIO()
wb.save(buf)
buf.seek(0)  # must seek before send_file

return send_file(
    buf,
    download_name=f"T13_{safe_name}_{month_str}.xlsx",
    as_attachment=True,
)
```

**`_build_export_grid()` reuse** — this function (lines 1562-1650) is the per-dept row builder. Call it per-dept within the org loop. The global export must NOT call `_resolve_export_scope()` (that function reads request session for a single dept scope — bypass entirely for the global export).

**Column header row pattern** (app.py lines 1681-1685):
```python
headers = ["Сотрудник"] + [d.day for d in days] + ["Я", "Ч", "П/НН", "О", "Б/К"]
for col_idx, header in enumerate(headers, start=1):
    cell = ws.cell(row=3, column=col_idx, value=header)
    cell.font = Font(bold=True)
    cell.alignment = Alignment(horizontal="center")
```

**totals columns write pattern** (app.py lines 1693-1698):
```python
base_col = 2 + len(days)
ws.cell(row=row_idx, column=base_col, value=totals["days_worked"])
ws.cell(row=row_idx, column=base_col + 1, value=totals["hours_worked"])
ws.cell(row=row_idx, column=base_col + 2, value=totals["absences"])
ws.cell(row=row_idx, column=base_col + 3, value=totals["late"])
ws.cell(row=row_idx, column=base_col + 4, value=totals["vac_sick"])
```

**Empty workbook guard** (new — no analog; needed per RESEARCH.md Pitfall 8):
```python
if not wb.sheetnames:
    wb.create_sheet("Нет данных")
```

**Sheet name uniqueness** (new — no analog):
```python
used_sheet_names = set()
sheet_name = org.name[:31]
if sheet_name in used_sheet_names:
    sheet_name = org.name[:28] + f"_{len(used_sheet_names)}"
used_sheet_names.add(sheet_name)
ws = wb.create_sheet(title=sheet_name)
```

---

### `models.py` — `HolidayCalendar` new model (SADM-05)

**Analog:** `AppSetting` (lines 177-184) for simple key-value, `AuditLog` (lines 189-204) for autoincrement int PK with index

**Section header pattern** (models.py line 1 style):
```python
# ─── HolidayCalendar ──────────────────────────────────────────────────────────
```

**Model definition pattern** (models.py lines 189-204 — AuditLog as closest match):
```python
class AuditLog(db.Model):
    """Audit log for sensitive actions..."""
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
```

**New HolidayCalendar to copy from:**
```python
class HolidayCalendar(db.Model):
    """DB-backed KZ holiday calendar (SADM-05). Replaces hardcoded KZ_HOLIDAYS dict lookup."""
    __tablename__ = "holiday_calendar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)  # YYYY-MM-DD
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
```

**Import line in models.py** (line 13-15 — existing imports to copy column types from):
```python
from sqlalchemy import Integer, String, Text, Boolean, Float, Index
```
`Integer` and `String` are already imported — no new imports needed.

**Import in app.py** (line 21 — add `HolidayCalendar` to existing from-import):
```python
from models import db, Employee, User, Organization, Department
from models import AttendanceRecord, EmployeeSchedule, LogEntry, TimesheetOverride, AppSetting, KioskDevice, AuditLog
```
Add `HolidayCalendar` to the second import line.

---

### `templates/superadmin.html` — New panel divs (SADM-02, 03, 04, 05, 06)

**Analog:** `panelUsers` block, lines 97-163; `panelSystem` block, lines 68-95

**Panel div pattern** (lines 68-69, 97-99):
```html
<!-- ═══ TAB: <NAME> ═══ -->
<div id="panel<Name>" class="page hidden">
<h1 class="page-title"><Title></h1>
  <!-- content -->
</div>
```
New panels: `panelEmployees`, `panelDevices`, `panelLogs`, `panelCalendar`, `panelAnalytics`

**Table-card pattern** (lines 50-65):
```html
<div class="table-card">
  <table>
    <thead>
      <tr>
        <th>Col1</th><th>Col2</th>
      </tr>
    </thead>
    <tbody id="<name>TableBody">
      <tr><td colspan="N" style="text-align:center;color:#90a4ae;padding:28px;">Загрузка...</td></tr>
    </tbody>
  </table>
</div>
```

**Toolbar + filter row pattern** (lines 24-26 and class `toolbar`):
```html
<div class="toolbar">
  <select id="empOrgFilter" onchange="filterEmployees()">
    <option value="">Все организации</option>
  </select>
</div>
```

**Form card pattern** (lines 104-131 createUserPanel):
```html
<div id="<name>Panel" class="card hidden" style="max-width:480px;margin-bottom:20px;">
  <h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">Title</h3>
  <div class="form-group">
    <label>Label</label>
    <input type="text" id="fieldId" placeholder="...">
  </div>
  <div id="<name>FormError" class="error-msg hidden"></div>
  <div class="form-actions">
    <button class="btn-primary" onclick="action()">Submit</button>
    <button class="btn-secondary" onclick="cancel()">Отмена</button>
  </div>
</div>
```

---

### `templates/superadmin.html` — JS state, init, switchTab extensions (all new tabs)

**State variables pattern** (lines 167-169):
```javascript
let allOrgs = [];
let allEmployees = [];
let allUsers = [];
```
Add new state vars in the same `// ─── State ──` block:
```javascript
let allSuperEmployees = [];
let allDevices = [];
let allSuperLogs = [];
let allHolidays = [];
let employeesLoaded = false;
let devicesLoaded = false;
let logsLoaded = false;
let calendarLoaded = false;
let analyticsLoaded = false;
let analyticsChartInst = null;  // Chart.js instance; use unique name to avoid ctx collision
```

**switchTab() pattern** (lines 177-181):
```javascript
function switchTab(tab) {
  document.getElementById('panelOrgs').classList.toggle('hidden', tab !== 'orgs');
  document.getElementById('panelUsers').classList.toggle('hidden', tab !== 'users');
  document.getElementById('panelSystem').classList.toggle('hidden', tab !== 'system');
}
```
Extend to all 8 panels. Add lazy-load calls:
```javascript
function switchTab(tab) {
  ['orgs','users','system','employees','devices','logs','calendar','analytics'].forEach(t => {
    document.getElementById('panel' + t.charAt(0).toUpperCase() + t.slice(1))
      .classList.toggle('hidden', t !== tab);
  });
  if (tab === 'employees' && !employeesLoaded) { loadSuperEmployees(); employeesLoaded = true; }
  if (tab === 'devices'   && !devicesLoaded)   { loadDevices();        devicesLoaded   = true; }
  if (tab === 'logs'      && !logsLoaded)       { loadSuperLogs();     logsLoaded      = true; }
  if (tab === 'calendar'  && !calendarLoaded)   { loadHolidays();      calendarLoaded  = true; }
  if (tab === 'analytics' && !analyticsLoaded)  { loadAnalytics();     analyticsLoaded = true; }
}
```

**Fetch + render pattern** (lines 417-422, loadUsers):
```javascript
async function loadUsers() {
  try {
    const resp = await fetch('/api/users');
    allUsers = resp.ok ? await resp.json() : [];
    renderUsers();
  } catch(e) {}
}
```
Copy this exact structure for `loadSuperEmployees()`, `loadDevices()`, `loadSuperLogs()`.

**DELETE action pattern** (lines 399-413, deleteOrg):
```javascript
async function deleteOrg(orgId, orgName) {
  if (!window.confirm(`Удалить организацию «${orgName}»? Это действие нельзя отменить.`)) return;
  try {
    const resp = await fetch(`/api/orgs/${orgId}`, {method: 'DELETE'});
    if (resp.ok) {
      await loadOrgs();
      await loadStats();
    } else if (resp.status === 409) {
      alert('Не удалось удалить. Возможно, запись используется.');
    } else {
      alert('Ошибка при сохранении. Попробуйте ещё раз.');
    }
  } catch (e) {
    alert('Ошибка при сохранении. Попробуйте ещё раз.');
  }
}
```
Use for `revokeDevice(orgToken, deviceId)` and `deleteHoliday(date)`.

**POST action pattern** (lines 471-498, createUser):
```javascript
async function createUser() {
  const errEl = document.getElementById('userFormError');
  errEl.classList.add('hidden');
  try {
    const resp = await fetch('/api/users', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, password, role, org_id}),
    });
    const data = await resp.json();
    if (resp.ok) {
      toggleUserForm();
      await loadUsers();
    } else {
      errEl.textContent = data.error || 'Ошибка при создании';
      errEl.classList.remove('hidden');
    }
  } catch(e) {
    errEl.textContent = 'Ошибка соединения';
    errEl.classList.remove('hidden');
  }
}
```
Use for `addHoliday()`.

**escapeHtml() helper** (lines 564-571) — already present in superadmin.html; reuse in all new render functions:
```javascript
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
```

**initial_tab restore pattern** (lines 576-579):
```javascript
(function() {
  var h = {{ initial_tab|default('')|tojson }} || window.location.hash.slice(1);
  if (h) { switchTab(h); history.replaceState(null, '', window.location.pathname); }
})();
```
No change needed — `switchTab()` already handles all tab IDs once extended.

---

### `templates/superadmin.html` — Chart.js analytics panel (SADM-06)

**Analog:** `templates/admin.html` lines 5 (CDN) and lines 390-411 (chart init)

**CDN script tag pattern** (admin.html line 5 — from RESEARCH.md):
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```
Place in `{% block head %}` of superadmin.html (currently empty at line 4).

**Chart.js destroy-then-create pattern** (admin.html lines 389-411 — adapted):
```javascript
async function loadAnalytics() {
  const resp = await fetch('/api/superadmin/attendance_stats?days=30');
  if (!resp.ok) return;
  const data = await resp.json();
  const labels = data.map(r => r.date);
  const values = data.map(r => r.percent);
  if (analyticsChartInst) { analyticsChartInst.destroy(); }
  const analyticsCtx = document.getElementById('analyticsChart').getContext('2d');
  analyticsChartInst = new Chart(analyticsCtx, {
    type: 'line',
    data: {
      labels,
      datasets: [{label: '% присутствия', data: values, tension: 0.3, fill: false}]
    },
    options: {responsive: true, scales: {y: {min: 0, max: 100}}}
  });
}
```
Use `analyticsCtx` and `analyticsChartInst` (not `ctx`) to avoid variable collision with any other script scope.

**Canvas element:**
```html
<canvas id="analyticsChart" height="80"></canvas>
```

---

### `templates/superadmin.html` — create_user form extension (SADM-07)

**Analog:** existing `createUserPanel`, lines 104-131; `toggleUserForm()`, lines 452-468

**Role select to extend** (lines 116-118):
```html
<select id="newRole">
  <option value="org_admin">Администратор организации</option>
</select>
```
Add options:
```html
<select id="newRole" onchange="onRoleChange()">
  <option value="org_admin">Администратор организации</option>
  <option value="dept_admin">Администратор отдела</option>
  <option value="hr_viewer">HR-наблюдатель</option>
</select>
```

**New dept selector group** (insert after `#newOrgId` form-group, after line 124):
```html
<div class="form-group" id="deptSelectGroup" style="display:none;">
  <label>Отдел</label>
  <select id="newDeptId">
    <option value="">— выберите отдел —</option>
  </select>
</div>
```

**Dept selector population JS** (copy structure from `toggleUserForm()` org populate, lines 457-462):
```javascript
let allDepts = [];  // add to state block

function onRoleChange() {
  const role = document.getElementById('newRole').value;
  const grp = document.getElementById('deptSelectGroup');
  grp.style.display = role === 'dept_admin' ? '' : 'none';
  if (role === 'dept_admin') populateDeptSelector();
}

async function populateDeptSelector() {
  if (!allDepts.length) {
    const resp = await fetch('/api/depts');
    allDepts = resp.ok ? await resp.json() : [];
  }
  const orgId = document.getElementById('newOrgId').value;
  const sel = document.getElementById('newDeptId');
  sel.innerHTML = '<option value="">— выберите отдел —</option>';
  allDepts.filter(d => d.org_id === orgId).forEach(d => {
    const opt = document.createElement('option');
    opt.value = d.id; opt.textContent = d.name;
    sel.appendChild(opt);
  });
}
```

**createUser() `dept_id` addition** (lines 471-483 — add `dept_id` to payload):
```javascript
body: JSON.stringify({username, password, role, org_id,
  dept_id: document.getElementById('newDeptId').value || null}),
```

---

### `templates/base.html` — superadmin nav links (all new tabs)

**Analog:** lines 153-171, existing superadmin nav block

**Existing nav link pattern** (lines 157, 169):
```html
<a href="/superadmin/users" class="nav-item {% if request.path == '/superadmin/users' %}active{% endif %}">
  <span class="nav-icon">👥</span> Пользователи
</a>
```

**New links to insert** (after line 158, before `/register` link; maintain tab order from RESEARCH.md recommendation):
```html
<a href="/superadmin/employees" class="nav-item {% if request.path == '/superadmin/employees' %}active{% endif %}">
  <span class="nav-icon">👤</span> Сотрудники
</a>
<a href="/superadmin/devices" class="nav-item {% if request.path == '/superadmin/devices' %}active{% endif %}">
  <span class="nav-icon">🖥</span> Устройства
</a>
<a href="/superadmin/logs" class="nav-item {% if request.path == '/superadmin/logs' %}active{% endif %}">
  <span class="nav-icon">📄</span> Логи
</a>
<a href="/superadmin/calendar" class="nav-item {% if request.path == '/superadmin/calendar' %}active{% endif %}">
  <span class="nav-icon">📅</span> Календарь
</a>
<a href="/superadmin/analytics" class="nav-item {% if request.path == '/superadmin/analytics' %}active{% endif %}">
  <span class="nav-icon">📈</span> Аналитика
</a>
```

---

### `app.py` — `superadmin_page()` VALID_TABS extension (all new tabs)

**Analog:** lines 1229-1231

**Current:**
```python
VALID_TABS = {"orgs", "users", "system"}
initial_tab = tab if tab in VALID_TABS else "orgs"
```

**Replace with:**
```python
VALID_TABS = {"orgs", "users", "system", "employees", "devices", "logs", "calendar", "analytics"}
initial_tab = tab if tab in VALID_TABS else "orgs"
```

---

### `app.py` — `revoke_kiosk_device()` audit addition (SADM-03)

**Analog:** `create_user()` write_audit call, lines 2015-2016

**Add before `return jsonify({"status": "revoked"})` at line 2562:**
```python
write_audit("device_revoke", target_type="kiosk_device", target_id=device_id,
            old_value={"device_name": device.device_name, "org_id": device.org_id})
```

---

## Shared Patterns

### Role Guard
**Source:** `app.py` lines 144-159 (`require_role` decorator)
**Apply to:** All new endpoints
```python
@app.route("/api/superadmin/<name>", methods=["GET"])
@require_role("superadmin")
def handler():
    ...
```

### Audit Logging
**Source:** `app.py` lines 576-624 (`write_audit()`)
**Apply to:** `POST /api/holidays`, `DELETE /api/holidays/<date>`, `revoke_kiosk_device()` addition
```python
write_audit("holiday_add", target_type="holiday", target_id=date_str,
            new_value={"name": name, "date": date_str})
```

### DB Session commit/rollback
**Source:** `app.py` lines 2000-2014
**Apply to:** All endpoints that write to DB
```python
try:
    db.session.add(...)
    db.session.commit()
except Exception:
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500
```

### JS error element show/hide
**Source:** `templates/superadmin.html` lines 476-497
**Apply to:** All new form submit functions (`addHoliday()`, `createUser()` extension)
```javascript
const errEl = document.getElementById('<name>FormError');
errEl.classList.add('hidden');
// ... on error:
errEl.textContent = data.error || 'Ошибка';
errEl.classList.remove('hidden');
```

### Table empty-state placeholder
**Source:** `templates/superadmin.html` lines 62, 158-159
**Apply to:** All new `render<Name>()` functions
```javascript
if (!data.length) {
  tbody.innerHTML = '<tr><td colspan="N" style="text-align:center;color:#90a4ae;padding:28px;">Нет данных</td></tr>';
  return;
}
```

---

## No Analog Found

| File/Change | Role | Data Flow | Reason |
|-------------|------|-----------|--------|
| `GET /api/superadmin/attendance_stats` aggregation query | service | batch | No existing date-range aggregation endpoint in codebase; pattern from RESEARCH.md code sketch applies |
| Holiday date format validation | utility | transform | No existing date-input validation in app.py; add `datetime.strptime(date_str, "%Y-%m-%d")` inside try/except ValueError to validate before INSERT |

---

## Metadata

**Analog search scope:** `app.py` (full, 2700+ lines), `models.py` (204 lines), `templates/superadmin.html` (581 lines), `templates/base.html` (lines 148-175)
**Files scanned:** 4
**Pattern extraction date:** 2026-06-28
