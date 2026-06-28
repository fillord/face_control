# Phase 10: Superadmin Panel Extension — Research

**Researched:** 2026-06-28
**Domain:** Flask/SQLAlchemy brownfield extension — superadmin tab UI + 7 backend endpoints
**Confidence:** HIGH (all findings are from direct codebase inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: create_user() fix (line 1985): superadmin may create org_admin, dept_admin, hr_viewer; show dept selector when dept_admin selected; write_audit() required
- D-02: Employees tab — read-only, all orgs, client-side org filter, endpoint GET /api/superadmin/employees
- D-03: Devices tab — all KioskDevice records, revoke calls existing DELETE endpoint, write_audit() on revoke
- D-04: Logs tab — GET /api/superadmin/logs?org_id=&event_type=, max 500 records, source LogEntry table
- D-05: Holiday Calendar — new tab panelCalendar; new DB model (or AppSetting JSON); GET/POST/DELETE /api/holidays; compute_symbol() uses DB first, fallback to KZ_HOLIDAYS if DB empty for that year
- D-06: Analytics chart — Chart.js line chart, GET /api/superadmin/attendance_stats?days=30, % attendance per day system-wide
- D-07: Global Excel export — GET /api/superadmin/export/xlsx?month=M&year=Y, one sheet per org (31-char limit on sheet names), T-13 grid per org, openpyxl only

### Claude's Discretion
- Whether panelAnalytics is new tab or integrated into panelSystem
- Whether HolidayCalendar is new SQLAlchemy model or AppSetting JSON key (prefer dedicated model)
- Tab ordering in superadmin.html nav
- Exact Chart.js version (latest stable from CDN)
- Error handling for empty data in charts/tables

### Deferred Ideas (OUT OF SCOPE)
- PDF export
- Holiday import from ICS/iCal
- Per-org analytics breakdown
- Attendance trend over multiple months
- Edit existing holidays (DELETE + re-add is sufficient)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SADM-01 | Global T-13 Excel export, one sheet per org, filter by month/year | New endpoint; reuse _build_export_grid(); openpyxl already installed (line 14-17 app.py) |
| SADM-02 | Employees tab: all orgs, name/org/dept/face status/date, org filter, read-only | New endpoint querying Employee + Organization + Department ORM joins |
| SADM-03 | Devices tab: all orgs, revoke button calls existing DELETE endpoint | New endpoint querying KioskDevice + Organization; DELETE already allows superadmin |
| SADM-04 | Logs tab: recognition log entries, max 500, filter by org/event_type | New endpoint querying LogEntry; org filter requires JOIN through Employee |
| SADM-05 | Holiday calendar CRUD in DB; compute_symbol() consumes DB holidays first | New HolidayCalendar model; modify get_holidays_set() to query DB then fallback |
| SADM-06 | Attendance analytics Chart.js line chart, % per day, last N days system-wide | New endpoint; Chart.js 4.4.0 already on CDN in codebase |
| SADM-07 | superadmin can create dept_admin and hr_viewer accounts (currently blocked) | One-line change at app.py line 1985; update createUserPanel in superadmin.html |
</phase_requirements>

---

## Summary

Phase 10 extends a working Flask/SQLAlchemy monolith. The core pattern is already established: all routes follow `@app.route(...) @require_role("superadmin") def handler(): ...`, views consume ORM models (Employee, Organization, Department, KioskDevice, LogEntry, AppSetting), and the superadmin.html template uses `panel<Name>` divs toggled by `switchTab()`. There are no external packages to install — openpyxl (lines 14-16), Chart.js 4.4.0 (CDN, already used in admin.html), and Flask-SQLAlchemy are all present.

Seven capabilities need implementation. Priority order from CONTEXT.md is: create_user() fix (trivial), Employees tab (read-only ORM query), Devices tab (ORM query + delegate to existing DELETE), Logs tab (LogEntry ORM with org JOIN), Holiday Calendar (new DB model + get_holidays_set() modification), Analytics chart (AttendanceRecord aggregation), Global Excel export (most complex — multi-org multi-dept iteration). The most risky items are the Holiday Calendar (requires a DB schema addition without a migration script) and the Global Excel export (requires custom sheet-per-org logic not covered by the existing per-dept helper).

**Primary recommendation:** Implement in exactly the locked priority order. HolidayCalendar must be added to models.py and the DB table auto-created via `db.create_all()` (Flask's app context startup already calls this). No Alembic migration is needed because `db.create_all()` is idempotent — it only creates missing tables.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| create_user() role fix | API / Backend (app.py) | Frontend (superadmin.html JS) | Server-side role guard is the primary change; UI update is secondary |
| Employees tab data | API / Backend | Browser / Client | ORM aggregation in endpoint; client-side org filter with already-loaded data |
| Devices tab data | API / Backend | Browser / Client | ORM aggregation; revoke delegates to existing backend DELETE |
| Logs tab data | API / Backend | Browser / Client | LogEntry ORM query with Employee JOIN for org resolution |
| Holiday Calendar CRUD | Database / Storage + API | Browser / Client | Requires new ORM model; compute_symbol() is pure backend |
| Attendance analytics | API / Backend | Browser / Client (Chart.js) | Aggregation query in backend; Chart.js renders client-side |
| Global Excel export | API / Backend | — | openpyxl runs server-side; browser just downloads the file |

---

## Technical Findings

### What Exists in app.py

**create_user() restriction (SADM-07)**
- File: `app.py` lines 1984-1986
- Exact code: `if creator_role == "superadmin" and target_role != "org_admin": return jsonify({"error": "..."}), 403`
- The fix is a single line change: replace the condition to allow org_admin, dept_admin, hr_viewer
- `write_audit()` is already called at lines 2015-2016 for all user creations — no change needed there
- `org_id` is already read from `data.get("org_id")` when creator is superadmin (line 1993)
- `dept_id` is already read from `data.get("dept_id")` (line 1996) — the backend already supports it

**create_user() UI (SADM-07)**
- `createUserPanel` in superadmin.html: lines 104-131
- `newRole` select currently has only one option: `org_admin` (line 117)
- No `dept_id` field exists in the form
- `createUser()` JS function at line 471 sends `{username, password, role, org_id}` — needs `dept_id` added
- `toggleUserForm()` populates org selector from `allOrgs` — same approach needed for dept selector

**Existing superadmin routes**
- `/superadmin`, `/superadmin/<tab>` → `superadmin_page()` — `VALID_TABS = {"orgs", "users", "system"}` (line 1230)
- `/api/superadmin_stats` — already exists (line 3069)
- `/api/settings/lbph_threshold` PATCH — already exists
- `/api/settings/face_match_tolerance` PATCH — already exists
- `/api/backup/db` GET — already exists
- NO endpoints exist yet for: employees, devices, logs, attendance_stats, holidays, export/xlsx

**KioskDevice delete (SADM-03)**
- `DELETE /api/kiosk/<org_token>/devices/<device_id>` at line 2545
- `@require_role("org_admin", "superadmin")` — superadmin already allowed
- DOES NOT call `write_audit()` — the Devices tab revoke must call it (either in the endpoint or we add it here)
- Requires `org_token` in the URL — the Devices tab GET endpoint must return `org_token` alongside each device

**LogEntry model (SADM-04)**
- Model fields: `id, ts, event, emp_id, name, confidence_raw, confidence_pct`
- NO `org_id` column — to filter by org, must JOIN Employee via `LogEntry.emp_id == Employee.id`
- Cap is 10,000 rows (lines 565-571)
- Logs endpoint must return last 500, most recent first: `.order_by(LogEntry.id.desc()).limit(500)`
- `emp_id` in LogEntry may not always match a current Employee row (employee could be deleted) — LEFT JOIN or subquery needed

**get_holidays_set() (SADM-05)**
- Current implementation (lines 289-291): reads only from `KZ_HOLIDAYS` dict
- Called from: timesheet route (line 1186/1514), _resolve_export_scope (line 1632), compute_dept_summary (line 424)
- The function signature is `get_holidays_set(year)` returning `set` — signature stays the same
- Must be modified to: query HolidayCalendar WHERE year=year first; if empty, fallback to KZ_HOLIDAYS.get(year, [])

**export_timesheet_xlsx() (SADM-01)**
- Existing function (lines 1655-1714) is scoped to ONE department
- Uses `_resolve_export_scope()` → `_build_export_grid()` pipeline
- `_build_export_grid(days, scoped_employees, attendance, overrides, holidays_set)` returns list of (emp_id, name, symbols, totals)
- The global export needs custom logic: iterate all orgs, for each org iterate all depts, combine employees per org into one sheet
- Cannot reuse `_resolve_export_scope()` directly (it expects request.args and resolves single dept from session)
- CAN reuse `_build_export_grid()` and `compute_symbol()` and `compute_employee_totals()`
- Excel sheet name limit: 31 chars — truncate org.name with `org.name[:31]`
- Unique sheet names: if two orgs truncate to same 31 chars, suffix with index (`name[:28] + f"_{i}"`)

**Chart.js (SADM-06)**
- CDN already used in project: `https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js`
- Pattern from admin.html lines 390-411: destroy old chart instance, create new Chart with type/data/options
- Existing usage is bar chart — need line chart for analytics
- The `ctx` variable name collision risk if superadmin.html already has inline `const ctx` usage — use scoped variable name like `analyticsCtx`

**AttendanceRecord (SADM-06)**
- Model: `id, emp_id, date, check_in_time, check_out_time, event_type`
- Composite index on `(emp_id, date)` already exists (line 118 models.py)
- To compute % attendance per day: group by date, count distinct emp_id where check_in_time IS NOT NULL
- Total employees for denominator: `Employee.query.count()`
- Days parameter: date.today() - timedelta(days=N) to date.today()

**HolidayCalendar model (SADM-05)**
- Does NOT exist in models.py — needs to be added
- Existing models in models.py: User, Employee, EmployeeSchedule, Organization, Department, AttendanceRecord, LogEntry, TimesheetOverride, KioskDevice, AppSetting, AuditLog
- `db.create_all()` is called at app startup (via Flask-SQLAlchemy's `with app.app_context(): db.create_all()`) — adding a new model and restarting pm2 will auto-create the table
- Import in app.py: models.py line 21 uses `from models import db, Employee, User, ...` — needs `HolidayCalendar` added

**superadmin.html tab structure**
- Current panels: `panelOrgs` (default), `panelSystem`, `panelUsers`
- `switchTab()` at lines 177-181 currently handles only these 3 panel IDs
- `init()` at line 172 calls `loadOrgs()`, `loadStats()`, `loadUsers()` on page load — new tab data should NOT all load on page load; use lazy loading per tab switch
- JS state vars at lines 167-169: `allOrgs`, `allEmployees`, `allUsers`
- Initial tab from server: `{{ initial_tab|default('')|tojson }}` at line 577, routed via `/superadmin/<tab>`

**base.html sidebar for superadmin (nav links)**
- Lines 153-171: 6 nav links for superadmin role
- Existing links: Организации, Пользователи, Регистрация, Аудит, Табель Т-13, Система
- New tabs added to superadmin.html will need corresponding `<a href="/superadmin/<tab>">` links in base.html

### Models Available Without Changes
- `Employee` — id, name, role, label, face_count, registered_at, org_id, dept_id, iin
- `Organization` — id, name, org_token, description, created_at
- `Department` — id, org_id, name, head_name, created_at
- `KioskDevice` — id, org_id, device_name, created_at, last_seen_at (NOT org_token; must JOIN Organization)
- `LogEntry` — id, ts, event, emp_id, name, confidence_raw, confidence_pct (NO org_id)
- `AttendanceRecord` — id, emp_id, date, check_in_time, check_out_time, event_type
- `AppSetting` — key (PK), value

### Model to Add
- `HolidayCalendar` — new; to be added to models.py with fields: id (PK autoincrement), date (str YYYY-MM-DD, unique), name (str), year (int, indexed for GET /api/holidays?year= queries)

---

## Implementation Approach

### SADM-07: create_user() Fix (1 backend + 1 frontend)

**Backend change (app.py lines 1984-1986):**
Replace:
```python
# superadmin may only create org_admin; org_admin manages all roles below them
if creator_role == "superadmin" and target_role != "org_admin":
    return jsonify({"error": "Суперадминистратор может создавать только администраторов организаций"}), 403
```
With:
```python
# superadmin may create org_admin, dept_admin, hr_viewer (SADM-07)
_SA_ALLOWED = {"org_admin", "dept_admin", "hr_viewer"}
if creator_role == "superadmin" and target_role not in _SA_ALLOWED:
    return jsonify({"error": "Суперадминистратор может создавать org_admin, dept_admin, hr_viewer"}), 403
```

**Frontend change (superadmin.html createUserPanel):**
- Add options to `#newRole` select: org_admin, dept_admin, hr_viewer
- Add `<div id="deptSelectGroup" class="form-group hidden">` with `<select id="newDeptId">` after `#newOrgId`
- On `#newRole` change: if "dept_admin" selected, show `#deptSelectGroup` and populate it by fetching `/api/depts?org_id=<selected_org>` (filter client-side from loaded allOrgs/depts or server-fetch)
- On `#newOrgId` change: re-populate dept selector when dept_admin is selected
- Update `createUser()` JS function to include `dept_id: document.getElementById('newDeptId').value || null` in payload

**Approach for dept selector population:**
Fetch `/api/depts` (already returns all depts for superadmin) once when form opens, store in `allDepts`. Filter by org_id when org changes. Simpler than per-org API call.

### SADM-02: Employees Tab

**New backend endpoint:**
```python
@app.route("/api/superadmin/employees", methods=["GET"])
@require_role("superadmin")
def superadmin_employees():
    emps = Employee.query.all()
    orgs = {o.id: o.name for o in Organization.query.all()}
    depts = {d.id: d.name for d in Department.query.all()}
    result = []
    for e in emps:
        result.append({
            "id": e.id, "name": e.name,
            "org_id": e.org_id, "org_name": orgs.get(e.org_id, "—"),
            "dept_id": e.dept_id, "dept_name": depts.get(e.dept_id, "—"),
            "face_enrolled": e.face_count > 0,
            "registered_at": e.registered_at or "",
        })
    return jsonify(result)
```

**New frontend tab `panelEmployees`:**
- Table: Имя | Организация | Отдел | Лицо | Дата добавления
- Org filter: `<select id="empOrgFilter">` above table; JS filters `allSuperEmployees` array client-side
- No action buttons (read-only per SADM-02)

### SADM-03: Devices Tab

**New backend endpoint:**
```python
@app.route("/api/superadmin/devices", methods=["GET"])
@require_role("superadmin")
def superadmin_devices():
    devices = KioskDevice.query.order_by(KioskDevice.created_at.desc()).all()
    orgs = {o.id: o for o in Organization.query.all()}
    result = []
    for d in devices:
        org = orgs.get(d.org_id)
        result.append({
            "id": d.id, "device_name": d.device_name,
            "org_id": d.org_id,
            "org_name": org.name if org else "—",
            "org_token": org.org_token if org else None,  # needed for revoke URL
            "created_at": d.created_at, "last_seen_at": d.last_seen_at,
        })
    return jsonify(result)
```

**write_audit() on revoke:**
The existing `revoke_kiosk_device()` (line 2545) does NOT call `write_audit()`. Two options:
1. Add `write_audit()` to the existing endpoint (affects org_admin too — acceptable)
2. Add it only in the superadmin.html JS after successful DELETE response

Option 1 is cleaner. Add `write_audit("device_revoke", target_type="kiosk_device", target_id=device_id)` before the return in `revoke_kiosk_device()`.

**Frontend revoke call:**
```javascript
async function revokeDevice(orgToken, deviceId) {
  if (!confirm('Отозвать устройство?')) return;
  const resp = await fetch(`/api/kiosk/${orgToken}/devices/${deviceId}`, {method:'DELETE'});
  if (resp.ok) await loadDevices();
  else alert('Ошибка при отзыве');
}
```

### SADM-04: Logs Tab

**New backend endpoint:**
LogEntry has no org_id. Strategy: load last 500 LogEntry rows, then resolve emp_id → org_id via Employee lookup. This avoids complex SQL JOIN for a max-500-row set.

```python
@app.route("/api/superadmin/logs", methods=["GET"])
@require_role("superadmin")
def superadmin_logs():
    org_id_filter = request.args.get("org_id", "")
    event_filter = request.args.get("event_type", "")
    # Build employee→org map for org filter
    emp_org = {e.id: e.org_id for e in Employee.query.with_entities(Employee.id, Employee.org_id).all()}
    orgs = {o.id: o.name for o in Organization.query.all()}
    q = LogEntry.query.order_by(LogEntry.id.desc())
    if event_filter:
        q = q.filter(LogEntry.event == event_filter)
    logs = q.limit(500).all()
    result = []
    for l in logs:
        emp_org_id = emp_org.get(l.emp_id)
        if org_id_filter and emp_org_id != org_id_filter:
            continue
        result.append({
            "ts": l.ts, "event": l.event, "name": l.name,
            "org_name": orgs.get(emp_org_id, "—"),
            "confidence_pct": l.confidence_pct,
        })
    return jsonify(result)
```

Note: Server-side org filtering after loading 500 rows (the limit applies before org filter). Client-side filtering is an alternative if all 500 rows need to be shown with live org filter. Recommend: apply event_type server-side (reduces rows), apply org_id client-side for live filtering UX consistency with other tabs.

**Frontend tab `panelLogs`:**
- Filters: org selector + event type selector (check_in / check_out / all)
- Table: Время | Событие | Имя | Организация | Уверенность %
- Data loads when tab is activated (lazy load pattern)

### SADM-05: Holiday Calendar

**New model in models.py:**
```python
class HolidayCalendar(db.Model):
    """DB-backed KZ holiday calendar (SADM-05). Replaces hardcoded KZ_HOLIDAYS dict."""
    __tablename__ = "holiday_calendar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)  # YYYY-MM-DD
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
```

**Import in app.py (line 21):**
Add `HolidayCalendar` to the existing import from models.

**Modify get_holidays_set() (app.py line 289):**
```python
def get_holidays_set(year):
    """Return a set of ISO date strings for KZ holidays in the given year.
    DB-backed (SADM-05): queries HolidayCalendar first; falls back to hardcoded KZ_HOLIDAYS if empty.
    """
    db_rows = HolidayCalendar.query.filter_by(year=year).all()
    if db_rows:
        return {r.date for r in db_rows}
    return set(KZ_HOLIDAYS.get(year, []))
```

**New endpoints:**
```
GET  /api/holidays?year=YYYY      → list [{date, name}] for year
POST /api/holidays                → body {date: "YYYY-MM-DD", name: "..."}; write_audit()
DELETE /api/holidays/<date>       → date as YYYY-MM-DD in URL; write_audit()
```

Date uniqueness: the `unique=True` constraint on `date` column prevents duplicate dates.

**Frontend tab `panelCalendar`:**
- Year selector (current year default)
- Table: Дата | Название | Удалить
- Add form: date input (type="date") + text input for name + "Добавить" button
- On successful POST/DELETE: reload table for current year

### SADM-06: Attendance Analytics Chart

**New backend endpoint:**
```python
@app.route("/api/superadmin/attendance_stats", methods=["GET"])
@require_role("superadmin")
def superadmin_attendance_stats():
    days = min(int(request.args.get("days", 30)), 90)
    total_emps = Employee.query.count()
    result = []
    for i in range(days - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        present = AttendanceRecord.query.filter(
            AttendanceRecord.date == d,
            AttendanceRecord.check_in_time != None,
        ).count()
        pct = round(present / total_emps * 100, 1) if total_emps else 0
        result.append({"date": d, "total_employees": total_emps, "present_count": present, "percent": pct})
    return jsonify(result)
```

**Chart in superadmin.html:**
- Load Chart.js from CDN: `https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js`
- This version is already referenced in admin.html and reports_partial.html — use same tag
- Place `<canvas id="analyticsChart" height="80">` in analytics panel
- Lazy-load chart data when analytics tab is activated
- Destroy/re-create chart instance on re-load (standard pattern from admin.html lines 389-411)

**Claude's Discretion: New tab vs panelSystem integration**
Recommendation: add a new `panelAnalytics` tab. The `panelSystem` tab has threshold + backup cards (conceptually "system config"), while analytics is "observability data". Separate tab is cleaner.

### SADM-01: Global Excel Export

**New backend endpoint:**
```python
@app.route("/api/superadmin/export/xlsx", methods=["GET"])
@require_role("superadmin")
def superadmin_export_xlsx():
    # Parse month/year params
    month_str = request.args.get("month", datetime.now().strftime("%Y-%m"))
    year, month_num = map(int, month_str.split("-"))
    _, num_days = calendar.monthrange(year, month_num)
    days = [date(year, month_num, 1) + timedelta(days=i) for i in range(num_days)]

    # Load shared data once (not per org)
    start_str = f"{year:04d}-{month_num:02d}-01"
    end_str = f"{year:04d}-{month_num:02d}-{num_days:02d}"
    att_recs = AttendanceRecord.query.filter(
        AttendanceRecord.date >= start_str,
        AttendanceRecord.date <= end_str,
    ).all()
    attendance = {}
    for r in att_recs:
        attendance.setdefault(r.date, {})[r.emp_id] = {
            "check_in": r.check_in_time, "check_out": r.check_out_time
        }
    ov_recs = TimesheetOverride.query.all()
    overrides = {}
    for r in ov_recs:
        overrides.setdefault(r.emp_id, {})[r.date] = r.symbol
    holidays_set = get_holidays_set(year)

    wb = Workbook()
    wb.remove(wb.active)  # remove default empty sheet
    orgs = Organization.query.order_by(Organization.name).all()
    used_sheet_names = set()
    for org in orgs:
        # Truncate sheet name to 31 chars, ensure uniqueness
        sheet_name = org.name[:31]
        if sheet_name in used_sheet_names:
            sheet_name = org.name[:28] + f"_{list(used_sheet_names).count(org.name[:28])}"
        used_sheet_names.add(sheet_name)
        ws = wb.create_sheet(title=sheet_name)
        # Write org-level T-13: all employees across all depts
        depts = Department.query.filter_by(org_id=org.id).order_by(Department.name).all()
        row_idx = 1
        num_cols = 1 + len(days) + 5
        # Title row
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=num_cols)
        ws.cell(row=row_idx, column=1, value=f"ТАБЕЛЬ Т-13 — {org.name} — {MONTHS_RU[month_num]} {year}").font = Font(bold=True)
        row_idx += 1
        for dept in depts:
            emps = Employee.query.filter_by(dept_id=dept.id).all()
            if not emps:
                continue
            scoped_employees = {e.id: _emp_to_dict(e) for e in emps}
            # Dept subtitle row
            ws.cell(row=row_idx, column=1, value=f"Отдел: {dept.name}").font = Font(bold=True, italic=True)
            row_idx += 1
            # Header row
            headers = ["Сотрудник"] + [d.day for d in days] + ["Я", "Ч", "П/НН", "О", "Б/К"]
            for col_idx, h in enumerate(headers, 1):
                ws.cell(row=row_idx, column=col_idx, value=h).font = Font(bold=True)
            row_idx += 1
            # Employee rows
            grid_rows = _build_export_grid(days, scoped_employees, attendance, overrides, holidays_set)
            for emp_id, name, symbols, totals in grid_rows:
                ws.cell(row=row_idx, column=1, value=name)
                for col_off, sym in enumerate(symbols, 2):
                    ws.cell(row=row_idx, column=col_off, value=sym or "")
                base_col = 2 + len(days)
                ws.cell(row=row_idx, column=base_col, value=totals["days_worked"])
                ws.cell(row=row_idx, column=base_col + 1, value=totals["hours_worked"])
                ws.cell(row=row_idx, column=base_col + 2, value=totals["absences"])
                ws.cell(row=row_idx, column=base_col + 3, value=totals["late"])
                ws.cell(row=row_idx, column=base_col + 4, value=totals["vac_sick"])
                row_idx += 1
            row_idx += 1  # blank row between depts
        ws.column_dimensions["A"].width = 24

    if not wb.sheetnames:
        wb.create_sheet("Нет данных")

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, download_name=f"T13_ALL_{month_str}.xlsx", as_attachment=True)
```

**Frontend for export (panelSystem or panelReports):**
- Month/year selector (default: current month in YYYY-MM format)
- "Скачать" button: `window.location = /api/superadmin/export/xlsx?month=${picker.value}`
- Recommendation: add to `panelSystem` (avoid new tab for a single button per D-07 context)

---

## Standard Stack

No new packages needed. All dependencies are already installed.

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| openpyxl | installed (line 14-16 app.py) | Excel file generation | Already imported |
| Flask-SQLAlchemy | installed | ORM queries | Already in use |
| Chart.js | 4.4.0 (CDN) | Attendance analytics chart | Already used in admin.html |
| bcrypt | installed | Password hashing (for create_user) | Already in use |

**No new pip installs required for this phase.**

---

## Package Legitimacy Audit

> No new packages are introduced in this phase. All dependencies are already installed and verified from previous phases.

**Packages removed due to SLOP verdict:** none  
**Packages flagged as suspicious:** none

---

## Architecture Patterns

### Tab Extension Pattern (superadmin.html)

**Existing pattern for adding a new tab:**

1. Add panel div in `{% block content %}`:
```html
<div id="panelXxx" class="page hidden">
  <h1 class="page-title">Title</h1>
  <!-- table/form content -->
</div>
```

2. Extend `switchTab()` to handle the new panel ID:
```javascript
function switchTab(tab) {
  const panels = ['panelOrgs', 'panelUsers', 'panelSystem', 'panelXxx'];
  panels.forEach(p => document.getElementById(p).classList.toggle('hidden', p !== 'panel' + tab.charAt(0).toUpperCase() + tab.slice(1)));
  // OR simpler: use data attributes
}
```

3. Update `VALID_TABS` in `superadmin_page()` in app.py:
```python
VALID_TABS = {"orgs", "users", "system", "employees", "devices", "logs", "calendar", "analytics"}
```

4. Add nav link in base.html sidebar (superadmin block, lines 153-171):
```html
<a href="/superadmin/employees" class="nav-item {% if request.path == '/superadmin/employees' %}active{% endif %}">
  <span class="nav-icon">👥</span> Сотрудники
</a>
```

**Lazy-load pattern for new tabs:**
Do NOT load data for all tabs in `init()`. Instead, call load function when tab is activated:
```javascript
function switchTab(tab) {
  // ... toggle panels ...
  if (tab === 'employees' && !employeesLoaded) { loadSuperEmployees(); employeesLoaded = true; }
  if (tab === 'devices' && !devicesLoaded) { loadDevices(); devicesLoaded = true; }
  // etc.
}
```

### Recommended Tab Order (Claude's Discretion)
Based on use-frequency and conceptual grouping:
1. Организации (existing)
2. Пользователи (existing)
3. Сотрудники (new, SADM-02)
4. Устройства (new, SADM-03)
5. Логи (new, SADM-04)
6. Календарь (new, SADM-05)
7. Аналитика (new, SADM-06)
8. Система (existing — keep last as it's config/maintenance)

### Anti-Patterns to Avoid
- **Loading all tab data in init():** slows initial page load; use lazy loading per tab
- **Calling _resolve_export_scope() for global export:** that function reads request.args for a single dept; bypass it entirely for the global export endpoint
- **SQL JOIN with LogEntry for org filter:** LogEntry has no org_id; use Python dict lookup after loading 500 rows; don't over-engineer the query
- **Blocking compute_symbol() with DB I/O per call:** get_holidays_set() should be called ONCE per grid render (year-level), not once per cell
- **Duplicate Excel sheet names without uniqueness check:** openpyxl will raise ValueError if two sheets have the same name

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Excel file generation | Custom CSV/binary | openpyxl (already installed) |
| Chart rendering | SVG/Canvas manually | Chart.js 4.4.0 (already on CDN) |
| Session-based role enforcement | Manual `if session.get('role') != 'superadmin'` | `@require_role("superadmin")` decorator |
| Audit log entries | Manual log writing | `write_audit()` helper (line 576) |
| Password hashing | Custom hash | bcrypt (already in use) |

---

## Common Pitfalls

### Pitfall 1: LogEntry org filter applies after LIMIT
**What goes wrong:** Applying org_id filter in Python after `.limit(500)` means you might return fewer than 500 results even when more exist for that org.
**Why it happens:** The SQL LIMIT runs before Python filtering.
**How to avoid:** Treat the 500 limit as "last 500 system-wide recognition events", then filter those by org in Python. Document this behavior: the Logs tab shows at most 500 events across all orgs; org filter narrows within that set. Per SADM-04 spec: "Max 500 records (most recent first); no pagination required" — this is acceptable.

### Pitfall 2: Excel sheet name uniqueness
**What goes wrong:** Two organizations named "МедКонтроль Алматы" and "МедКонтроль Астана" both truncate to "МедКонтроль Алматы" at 31 chars (if name is shorter than 31 chars they differ). But if two names start with identical 31 chars, openpyxl raises ValueError.
**How to avoid:** Track `used_sheet_names` set; if collision, suffix with `_2`, `_3` etc.

### Pitfall 3: get_holidays_set() called in app context without DB
**What goes wrong:** `get_holidays_set()` will call `HolidayCalendar.query` — if called outside Flask app context (e.g., in tests), this fails.
**How to avoid:** Tests that call get_holidays_set() must use `with app.app_context()`. Existing tests for compute_symbol() pass holidays_set directly, not via get_holidays_set() — they are not affected.

### Pitfall 4: HolidayCalendar table not created
**What goes wrong:** Adding HolidayCalendar model to models.py but forgetting to import it in app.py means db.create_all() doesn't know about it.
**How to avoid:** Add `HolidayCalendar` to the import line in app.py (line 21). Also verify the import is correct by checking pm2 logs after restart.

### Pitfall 5: switchTab() scope — `ctx` variable collision
**What goes wrong:** Adding Chart.js to superadmin.html and using `const ctx = canvas.getContext('2d')` collides with other `ctx` variables in the same script block.
**How to avoid:** Use a unique variable name: `const analyticsCtx = document.getElementById('analyticsChart').getContext('2d')`. Store chart instance as `let analyticsChartInst = null`.

### Pitfall 6: Global export performance on large datasets
**What goes wrong:** For large deployments (many orgs × many employees × 31 days), loading all AttendanceRecord rows for the month into Python dicts and iterating may be slow.
**How to avoid:** Load attendance data ONCE before the org loop (already shown in the implementation approach above). Do NOT query attendance inside the employee loop.

### Pitfall 7: create_user() dept_id validation for dept_admin
**What goes wrong:** Superadmin selects dept_admin role but doesn't select a department. The user gets created with `dept_id=None`, which means they can't see any department-scoped data.
**How to avoid:** Add server-side validation in create_user(): if target_role == "dept_admin" and not new_dept_id, return 400.

### Pitfall 8: Empty workbook if no orgs exist
**What goes wrong:** `wb.remove(wb.active)` removes the default sheet. If no orgs exist, `wb.sheetnames` is empty and openpyxl raises InvalidFileException on save.
**How to avoid:** Check `if not wb.sheetnames: wb.create_sheet("Нет данных")` before saving.

---

## Runtime State Inventory

> Not a rename/refactor/migration phase. Only the HolidayCalendar table is a schema addition.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | No renames; new `holiday_calendar` table added | db.create_all() on next app start creates it automatically |
| Live service config | PM2 running `face-recognition` process | `pm2 restart face-recognition` after deploy |
| OS-registered state | None | None |
| Secrets/env vars | No new env vars needed | None |
| Build artifacts | No compiled assets | None |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| openpyxl | SADM-01 (Excel export) | Yes | imported at app.py line 14 | — |
| Chart.js 4.4.0 | SADM-06 (analytics chart) | Yes (CDN) | 4.4.0 at jsdelivr.net | — |
| Flask-SQLAlchemy | All DB endpoints | Yes | models.py line 12 | — |
| SQLite app.db | All endpoints | Yes | data/app.db | — |
| PM2 process manager | Final restart | Yes | pm2 name "face-recognition" | — |

---

## Validation Architecture

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| SADM-01 | GET /api/superadmin/export/xlsx returns .xlsx with one sheet per org | smoke | `curl -s -b "session=..." /api/superadmin/export/xlsx?month=2026-06 -o /tmp/test.xlsx && python3 -c "import openpyxl; wb=openpyxl.load_workbook('/tmp/test.xlsx'); print(wb.sheetnames)"` | Manual verify sheet names match org names |
| SADM-02 | GET /api/superadmin/employees returns all employees | smoke | `curl /api/superadmin/employees` as superadmin | Check face_enrolled field |
| SADM-03 | GET /api/superadmin/devices returns all KioskDevice rows | smoke | `curl /api/superadmin/devices` as superadmin | Check org_token present in response |
| SADM-03 | DELETE revoke call works from Devices tab | manual | Click Revoke in UI | Verify device removed from list |
| SADM-04 | GET /api/superadmin/logs returns max 500 | smoke | `curl /api/superadmin/logs | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d))"` | ≤500 |
| SADM-05 | POST /api/holidays adds record; compute_symbol uses DB | smoke | POST then check timesheet for that date | Verify В on holiday date |
| SADM-05 | DELETE /api/holidays/<date> removes record | smoke | DELETE then GET /api/holidays?year= | Date absent from list |
| SADM-06 | GET /api/superadmin/attendance_stats returns array | smoke | `curl /api/superadmin/attendance_stats?days=7` | Check percent field present |
| SADM-06 | Chart.js line chart renders without JS errors | manual | Open superadmin analytics tab in browser | No console errors |
| SADM-07 | Superadmin can create dept_admin account | smoke | POST /api/users with role=dept_admin as superadmin | Returns 200 not 403 |
| SADM-07 | Superadmin cannot create employee account via this API | smoke | POST /api/users with role=employee as superadmin | Returns 403 |

### Existing Test Infrastructure
```bash
# Run existing tests
cd /var/www/sites/face-almgp33 && python -m pytest tests/ -x -q 2>/dev/null
```
Check if tests/ directory has tests for app.py routes that would break with create_user() change.

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V4 Access Control | YES | `@require_role("superadmin")` on all new endpoints |
| V5 Input Validation | YES | Validate `date` format (YYYY-MM-DD) in holiday endpoints; validate month param in export |
| V2 Authentication | No change | Existing session/require_role unchanged |

### Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on device revoke | Elevation | Existing DELETE endpoint already checks org scope for org_admin; superadmin bypasses by design |
| Holiday date injection | Tampering | Validate date is valid ISO date before INSERT; unique constraint in DB |
| org_id spoofing in logs filter | Information Disclosure | Superadmin sees all orgs by design; other roles cannot reach `/api/superadmin/*` (403 from require_role) |
| Excel formula injection | Tampering | Employee names from DB rendered as openpyxl cell values (not formulas); no risk |
| create_user role escalation | Elevation | Server-side check in create_user(): `target_role not in _SA_ALLOWED`; hierarchy check still applies |

---

## Open Questions

1. **Global export: one sheet per org or one sheet per dept?**
   - CONTEXT.md says "one sheet per org" with "T-13 grid using existing export_timesheet_xlsx() logic"
   - A T-13 grid is normally per-dept. One org may have multiple depts.
   - Recommendation: one sheet per org, with dept-separator rows between dept groups within the sheet. This matches "one sheet per org" literally and is readable.
   - If the user wants per-dept sheets, that would produce potentially many sheets for large orgs.

2. **audit() on existing revoke_kiosk_device() endpoint**
   - CONTEXT.md says write_audit() must be called on device revoke.
   - The existing endpoint at line 2545 doesn't call write_audit().
   - Adding it there benefits org_admin too (good) but is a change outside this phase's stated scope.
   - Safest: add write_audit() to the existing revoke_kiosk_device() function — it's a one-liner improvement with no risk.

3. **Logs tab: org filter client-side or server-side?**
   - With max 500 records, client-side filtering is fast and consistent with Employees tab pattern.
   - Recommendation: load 500 rows server-side (filtered by event_type only if provided), filter by org client-side with already-loaded org data.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | db.create_all() is called at app startup and will create holiday_calendar table automatically | Implementation Approach SADM-05 | Table won't exist; all /api/holidays calls fail with SQLAlchemy OperationalError |
| A2 | openpyxl's `wb.remove(wb.active)` removes the initial empty sheet | SADM-01 code | If API changed, empty first sheet appears in download |

**All other claims are VERIFIED by direct codebase inspection.**

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)
- `app.py` lines 1966-2018 — create_user() function with exact restriction location
- `app.py` lines 289-291 — get_holidays_set() hardcoded dict lookup
- `app.py` lines 1562-1650 — _resolve_export_scope(), _build_export_grid() pipeline
- `models.py` lines 1-204 — all 11 ORM models; HolidayCalendar confirmed absent
- `templates/superadmin.html` lines 1-581 — full panel/JS structure
- `templates/base.html` lines 153-171 — superadmin sidebar nav links
- `templates/admin.html` lines 5, 390-411 — Chart.js 4.4.0 CDN pattern
- `app.py` lines 2545-2562 — existing DELETE device endpoint (superadmin already allowed)

### Tertiary (LOW confidence — not verified this session)
- A1: db.create_all() auto-creates new tables at startup [ASSUMED — based on Flask-SQLAlchemy standard behavior]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all existing
- Architecture: HIGH — all patterns directly observed in codebase
- Pitfalls: HIGH — identified from direct code analysis
- Implementation code sketches: MEDIUM — correct structure, exact syntax to be confirmed by executor

**Research date:** 2026-06-28
**Valid until:** 2026-07-28 (stable codebase, no fast-moving dependencies)
