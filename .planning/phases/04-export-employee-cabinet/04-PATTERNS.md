# Phase 4: Export & Employee Cabinet - Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 5 (app.py, models.py, templates/timesheet.html, templates/employee.html [new], tests/test_export_employee.py [new])
**Analogs found:** 4 / 5 (employee.html is new with no analog — closest is timesheet.html)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app.py` — export routes (new) | route / controller | request-response, file-I/O | `app.py` `/timesheet` route (lines 868-997) | exact |
| `app.py` — `employee_page()` rewrite | route / controller | request-response | `app.py` `/timesheet` route (lines 868-997) | role-match (single-employee scope) |
| `app.py` — ALLOWED_LOGIN_ROLES + login redirect | config / auth | — | `app.py` lines 80, 550-569 | exact (targeted 2-line edit) |
| `models.py` — `User.emp_id` column | model | — | `models.py` `User` class (lines 29-41); `EmployeeSchedule.emp_id` (line 70) | exact |
| `templates/employee.html` (new) | template | request-response | `templates/timesheet.html` | role-match (same design language, subset of features) |
| `tests/test_export_employee.py` (new) | test | — | `tests/test_timesheet.py` | exact |

---

## Pattern Assignments

### `app.py` — `export_timesheet_xlsx()` and `export_timesheet_csv()` routes (new)

**Analog:** `app.py` `/timesheet` route, lines 868-997

**Imports pattern** — all already present in `app.py` except `re` and `BytesIO`/`csv`/`openpyxl`. Add at top of file alongside existing imports:
```python
# These need to be added to the existing imports block in app.py
import re
import csv
import io
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
from flask import send_file  # already imported via: from flask import Flask, request, ...
```

**Route decorator + role guard pattern** (analog: `app.py` lines 868-870):
```python
@app.route("/timesheet/export/xlsx")
@require_role("dept_admin", "org_admin", "superadmin")
def export_timesheet_xlsx():
```

**Dept-scope resolution pattern** — copy verbatim from `app.py` lines 892-919:
```python
    if role == "dept_admin":
        dept_id = session_dept_id  # always fixed from session; param ignored
    elif role == "org_admin":
        if dept_id_param:
            dept_obj = Department.query.get(dept_id_param)
            if not dept_obj or dept_obj.org_id != session_org_id:
                return render_template("403.html"), 403
            dept_id = dept_id_param
        else:
            first_dept = Department.query.filter_by(org_id=session_org_id).first()
            dept_id = first_dept.id if first_dept else None
    else:  # superadmin
        dept_id = dept_id_param or None
```

**ORM data loading pattern** — copy from `app.py` lines 932-953:
```python
    employees = {e.id: _emp_to_dict(e) for e in Employee.query.all()}
    start_str = f"{year:04d}-{month_num:02d}-01"
    _, _num_days_ts = calendar.monthrange(year, month_num)
    end_str = f"{year:04d}-{month_num:02d}-{_num_days_ts:02d}"
    _att_recs = AttendanceRecord.query.filter(
        AttendanceRecord.date >= start_str,
        AttendanceRecord.date <= end_str,
    ).all()
    attendance = {}
    for r in _att_recs:
        attendance.setdefault(r.date, {})[r.emp_id] = {
            "check_in": r.check_in_time,
            "check_out": r.check_out_time,
        }
    _ov_recs = TimesheetOverride.query.all()
    overrides = {}
    for r in _ov_recs:
        overrides.setdefault(r.emp_id, {})[r.date] = r.symbol
    holidays_set = get_holidays_set(year)
    scoped_employees = {eid: e for eid, e in employees.items() if e.get("dept_id") == dept_id}
```

**Grid computation pattern** — use the inline cell-building loop from `app.py` lines 966-977 (NOT `compute_timesheet_grid()` directly, since export needs symbol strings, not cell dicts):
```python
    grid_rows = []
    for emp_id, emp in scoped_employees.items():
        schedule = emp.get("schedule", {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]})
        symbols = [
            compute_symbol(d, emp_id, attendance, overrides, schedule, holidays_set)
            for d in days
        ]
        totals = compute_employee_totals(symbols, schedule)
        grid_rows.append((emp_id, emp.get("name", emp_id), symbols, totals))
```

**XLSX send_file pattern** (new — no existing analog; use RESEARCH.md Pattern 1):
```python
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)  # CRITICAL: must seek(0) before send_file or 0-byte download
    safe_dept = re.sub(r"[^A-Za-zА-Яа-яЁё0-9]", "_", dept_name)
    return send_file(
        buf,
        download_name=f"T13_{safe_dept}_{month_str}.xlsx",
        as_attachment=True,
        # mimetype auto-detected from .xlsx in Flask 3.1.3; add explicit if needed:
        # mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
```

**CSV send_file pattern** (new — no existing analog; use RESEARCH.md Pattern 2):
```python
    str_buf = io.StringIO()
    writer = csv.writer(str_buf, delimiter=";")
    content = str_buf.getvalue().encode("utf-8-sig")  # BOM auto-inserted by utf-8-sig codec
    byte_buf = io.BytesIO(content)
    safe_dept = re.sub(r"[^A-Za-zА-Яа-яЁё0-9]", "_", dept_name)
    return send_file(byte_buf, download_name=f"T13_{safe_dept}_{month_str}.csv",
                     as_attachment=True, mimetype="text/csv")
```

---

### `app.py` — `employee_page()` rewrite (lines 729-734)

**Analog:** `app.py` `/timesheet` route (lines 868-997) — same structure, single-employee scope

**Current stub** (lines 729-734) to be replaced:
```python
@app.route("/employee")
@require_role("employee")
def employee_page():
    user = User.query.get(session.get("user_id"))
    username = user.username if user else ""
    return render_template("dashboard.html", username=username)
```

**User + emp_id resolution pattern** (see RESEARCH.md Pattern 3; `User.emp_id` added in models.py):
```python
    user = User.query.get(session.get("user_id"))
    username = user.username if user else ""
    emp_id = user.emp_id if user else None
    if not emp_id:
        return render_template("employee.html", username=username, emp=None,
                               error="Ваш аккаунт не привязан к записи сотрудника.")
    emp_obj = Employee.query.get(emp_id)
    if not emp_obj:
        return render_template("403.html"), 403
```

**Month clamp pattern** (new for employee cabinet; guards against historical access beyond prev month):
```python
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    prev_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    month_str = request.args.get("month", current_month)
    if month_str < prev_month or month_str > current_month:
        month_str = current_month
    year, month_num = map(int, month_str.split("-"))
```

**ORM data loading pattern** (single-employee variant — filter by emp_id):
```python
    _att_recs = AttendanceRecord.query.filter(
        AttendanceRecord.emp_id == emp_id,
        AttendanceRecord.date >= start_str,
        AttendanceRecord.date <= end_str,
    ).all()
    attendance = {}
    times_by_date = {}
    for r in _att_recs:
        attendance.setdefault(r.date, {})[r.emp_id] = {
            "check_in": r.check_in_time, "check_out": r.check_out_time
        }
        times_by_date[r.date] = {"check_in": r.check_in_time, "check_out": r.check_out_time}
    _ov_recs = TimesheetOverride.query.filter_by(emp_id=emp_id).all()
    overrides = {emp_id: {r.date: r.symbol for r in _ov_recs}}
```

**Stats computation pattern** (EMP-03 — add `early` count not returned by `compute_employee_totals()`):
```python
    symbols = [c["sym"] for c in cells]
    totals = compute_employee_totals(symbols, schedule)
    early_count = sum(1 for s in symbols if s in ("У", "ОУ"))
    stats = {
        "late": totals["late"],
        "absences": totals["absences"],
        "early": early_count,
    }
```

**render_template call pattern** (analog: `app.py` lines 980-997):
```python
    return render_template(
        "employee.html",
        username=username,
        emp_name=emp_obj.name,
        grid_row=grid_rows[0],      # (emp_id, name, cells, totals)
        stats=stats,
        times_by_date=times_by_date,
        days=days,
        month_str=month_str,
        current_month=current_month,
        prev_month=prev_month,
        holidays_set=holidays_set,
    )
```

---

### `app.py` — ALLOWED_LOGIN_ROLES and login redirect (targeted edits)

**Analog:** `app.py` lines 80 and 562-568

**Line 80 — current:**
```python
ALLOWED_LOGIN_ROLES = ("superadmin", "org_admin", "dept_admin")
```
**Change to:**
```python
ALLOWED_LOGIN_ROLES = ("superadmin", "org_admin", "dept_admin", "employee")
```

**Lines 562-569 — current login role dispatch:**
```python
                if role == "superadmin":
                    return redirect(url_for("superadmin_page"))
                elif role == "org_admin":
                    return redirect(url_for("org_admin_page"))
                elif role == "dept_admin":
                    return redirect(url_for("dept_admin_page"))
                else:
                    return redirect(url_for("dashboard_page"))
```
**Add before the `else` branch:**
```python
                elif role == "employee":
                    return redirect(url_for("employee_page"))
```

---

### `models.py` — `User.emp_id` column addition

**Analog:** `models.py` `User` class lines 29-41; `EmployeeSchedule.emp_id` column at line 70

**Current `User` model** (lines 29-41) — add `emp_id` after `dept_id`:
```python
class User(db.Model):
    __tablename__ = "user"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    dept_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    emp_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # ADD THIS
```

**`app.py` startup migration guard** (add after `db.create_all()` call in startup block):
```python
    from sqlalchemy import text, exc as sa_exc
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE user ADD COLUMN emp_id TEXT"))
            conn.commit()
    except sa_exc.OperationalError:
        pass  # Column already exists — idempotent
```

---

### `templates/employee.html` (new template)

**Analog:** `templates/timesheet.html` — copy page skeleton, CSS classes, sym-cell styling, and symbol color maps verbatim

**Page skeleton pattern** (from `timesheet.html` lines 1-20 and structural layout):
```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Кабинет сотрудника</title>
  <style>
    /* Copy CSS from timesheet.html lines 1-74 verbatim:
       body, h1, .page-header, .username-badge, .selector-bar, .form-group,
       input[type="month"], .btn-primary, .table-card, table, th, td,
       .sym-cell, .sym-ou, sym color variables */
  </style>
</head>
```

**Stats cards pattern** (new — no existing analog; follow `.table-card` style with flex layout):
```html
  <div class="stats-row" style="display:flex; gap:16px; margin-bottom:20px;">
    <div class="stat-card" style="background:#fff; border:1px solid #e2e6f0; border-radius:12px; padding:20px 28px; flex:1; text-align:center;">
      <div style="font-size:28px; font-weight:700; color:#1565C0;">{{ stats.late }}</div>
      <div style="font-size:13px; color:#555; margin-top:4px;">Опоздания</div>
    </div>
    <div class="stat-card" ...>
      <div style="font-size:28px; font-weight:700; color:#1565C0;">{{ stats.absences }}</div>
      <div ...>Отсутствия</div>
    </div>
    <div class="stat-card" ...>
      <div style="font-size:28px; font-weight:700; color:#1565C0;">{{ stats.early }}</div>
      <div ...>Ранний уход</div>
    </div>
  </div>
```

**Month selector pattern** (analog: `timesheet.html` lines 77-104 — simpler, no dept select):
```html
  <form method="GET" action="/employee" class="selector-bar">
    <div class="form-group">
      <label for="month-input">Месяц</label>
      <input type="month" id="month-input" name="month" value="{{ month_str }}"
             min="{{ prev_month }}" max="{{ current_month }}">
    </div>
    <button type="submit" class="btn-primary">Показать</button>
  </form>
```

**T-13 grid (single-row) pattern** (analog: `timesheet.html` lines 107-230 — copy sym_titles, sym_bg, header row; render only `grid_row` instead of `grid_rows`):
```html
  <div class="table-card">
    {% set sym_titles = { "Я": "Я — явка", "О": "О — опоздание", ... } %}
    {% set sym_bg = { ... } %}  {# copy from timesheet.html lines 134-145 #}
    <table>
      <thead>
        <tr>
          <th>Сотрудник</th>
          {% for d in days %}
          <th style="...">{{ d.day }}<br><small>{{ wd_abbrev[d.isoweekday()] }}</small></th>
          {% endfor %}
          <th>Я</th><th>Ч</th><th>П/НН</th><th>О</th><th>Б/К</th>
        </tr>
      </thead>
      <tbody>
        {% set emp_id, emp_name, cells, totals = grid_row %}
        <tr>
          <td>{{ emp_name }}</td>
          {% for cell in cells %}
          {% set tip = times_by_date.get(cell.date) %}
          <td class="sym-cell{% if cell.sym == 'ОУ' %} sym-ou{% endif %}"
              style="background:{{ sym_bg.get(cell.sym, '#fff') }};"
              title="{% if tip %}Приход: {{ tip.check_in[:5] if tip.check_in else '—' }} / Уход: {{ tip.check_out[:5] if tip.check_out else '—' }}{% else %}{{ sym_titles.get(cell.sym, cell.sym) }}{% endif %}">
            {{ cell.sym or '' }}
          </td>
          {% endfor %}
          <td>{{ totals.days_worked }}</td>
          <td>{{ totals.hours_worked }}</td>
          <td>{{ totals.absences }}</td>
          <td>{{ totals.late }}</td>
          <td>{{ totals.vac_sick }}</td>
        </tr>
        {# Totals row #}
        <tr style="font-weight:600; background:#f5f7fb;">
          <td>Итого</td>
          {% for _ in days %}<td></td>{% endfor %}
          <td>{{ totals.days_worked }}</td>
          <td>{{ totals.hours_worked }}</td>
          <td>{{ totals.absences }}</td>
          <td>{{ totals.late }}</td>
          <td>{{ totals.vac_sick }}</td>
        </tr>
      </tbody>
    </table>
  </div>
```

**Tooltip implementation decision:** Use `title` attribute on `<td>` (D-12 Claude's choice). The `timesheet.html` already uses `title` on sym-cells (line 192: `title="Нет данных (будущий день)"`). Consistent; zero JS required.

---

### `templates/timesheet.html` — export button addition

**Analog:** `timesheet.html` lines 103-104 (existing "Показать табель" button in `.selector-bar`)

**Add after button on line 103:**
```html
    <button type="submit" class="btn-primary">Показать табель</button>
    {% if dept_id %}
    <a href="/timesheet/export/xlsx?dept_id={{ dept_id }}&amp;month={{ month_str }}"
       class="btn-secondary">Скачать XLSX</a>
    <a href="/timesheet/export/csv?dept_id={{ dept_id }}&amp;month={{ month_str }}"
       class="btn-secondary">Скачать CSV</a>
    {% endif %}
```

**`.btn-secondary` CSS** (add alongside `.btn-primary` in `timesheet.html` `<style>` block at line 25-26):
```css
.btn-secondary { padding: 8px 16px; background: #fff; color: #1565C0; border: 1.5px solid #1565C0; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; height: 36px; text-decoration: none; display: inline-flex; align-items: center; }
.btn-secondary:hover { background: #e3f0ff; }
```

---

### `tests/test_export_employee.py` (new test file)

**Analog:** `tests/test_timesheet.py` — copy file header, import pattern, fixture usage, `@pytest.mark.xfail` scaffold

**File header and import pattern** (from `tests/test_timesheet.py` lines 1-32):
```python
"""
Phase 4 Export & Employee Cabinet — Failing / xfail test scaffold.

Covered requirements:
    EXP-01  /timesheet/export/xlsx returns .xlsx with merged headers and Cyrillic labels
    EXP-02  /timesheet/export/csv returns UTF-8 BOM, semicolon-delimited file
    EXP-03  Export scoped to role: dept_admin only exports their dept (403 on other dept)
    EMP-01  /employee renders T-13 grid for current and previous month only
    EMP-02  Tooltip times (Приход/Уход) appear as title attribute on td cells
    EMP-03  Stats cards show late, absences, early departure counts
"""
import json
import pytest
from tests.conftest import (
    seed_users,
    seed_employees,
    seed_depts,
    seed_orgs,
    BCRYPT_HASH_SUPERADMIN,
)
```

**`seed_attendance` helper pattern** (does not exist yet in conftest.py — add to conftest.py; follow `seed_employees` pattern from lines 193-240):
```python
def seed_attendance(tmp_data, records_list):
    """Insert AttendanceRecord rows via ORM into the active app context.

    records_list is a list of dicts: {id, emp_id, date, check_in_time, check_out_time, org_id}.
    """
    import app as _app
    from models import db, AttendanceRecord
    with _app.app.app_context():
        for rec in records_list:
            if not AttendanceRecord.query.get(rec["id"]):
                db.session.add(AttendanceRecord(
                    id=rec["id"],
                    emp_id=rec["emp_id"],
                    date=rec["date"],
                    check_in_time=rec.get("check_in_time"),
                    check_out_time=rec.get("check_out_time"),
                    org_id=rec.get("org_id"),
                ))
        db.session.commit()
```

**xfail integration test pattern** (from `test_timesheet.py` lines 37-45 and the login-then-GET pattern used across the test suite):
```python
@pytest.mark.xfail(reason="implemented in 04-01: export routes not yet added", strict=False)
def test_export_xlsx_dept_admin(client, tmp_data):
    """EXP-01: dept_admin GET /timesheet/export/xlsx returns .xlsx file download."""
    seed_orgs(tmp_data, {"org-A": {"id": "org-A", "name": "Org", "description": ""}})
    seed_depts(tmp_data, {"dept-A": {"id": "dept-A", "org_id": "org-A", "name": "ВОП-1"}})
    seed_users(tmp_data, {"uid-1": {"id": "uid-1", "username": "da", "password_hash": BCRYPT_HASH_SUPERADMIN,
                                    "role": "dept_admin", "active": True, "org_id": "org-A", "dept_id": "dept-A"}})
    client.post("/login", data={"username": "da", "password": "superadmin123"}, follow_redirects=True)
    resp = client.get("/timesheet/export/xlsx?dept_id=dept-A&month=2026-06")
    assert resp.status_code == 200
    assert b"PK" in resp.data  # xlsx is a ZIP file starting with PK magic bytes
    cd = resp.headers.get("Content-Disposition", "")
    assert "attachment" in cd
    assert "T13_" in cd
```

---

## Shared Patterns

### Authentication / role guard
**Source:** `app.py` lines 82-97 (`require_role` decorator)
**Apply to:** All new routes (`export_timesheet_xlsx`, `export_timesheet_csv`)
```python
@require_role("dept_admin", "org_admin", "superadmin")
def export_timesheet_xlsx():
    ...
```
The decorator reads `session['user_id']`, fetches `User`, checks `user.role in allowed_roles`, returns `render_template("403.html"), 403` on failure.

### 403 response pattern
**Source:** `app.py` lines 93-94
**Apply to:** All scope-enforcement checks in export routes and `employee_page`
```python
return render_template("403.html"), 403
```

### Session-derived scope (never trust URL params for role enforcement)
**Source:** `app.py` lines 892-894
**Apply to:** Both export routes
```python
if role == "dept_admin":
    dept_id = session_dept_id  # always fixed from session; param ignored
```

### Russian month names dict (for XLSX Row 2 label)
**Source:** No existing analog — hard-code per RESEARCH.md Open Question 2 (locale unreliable)
**Apply to:** `export_timesheet_xlsx()`
```python
MONTHS_RU = {1:"Январь",2:"Февраль",3:"Март",4:"Апрель",5:"Май",6:"Июнь",
             7:"Июль",8:"Август",9:"Сентябрь",10:"Октябрь",11:"Ноябрь",12:"Декабрь"}
```

### ORM dict adapter
**Source:** `app.py` lines 101-115 (`_emp_to_dict`)
**Apply to:** All routes that need employee + schedule data
```python
emp_dict = _emp_to_dict(emp_obj)
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `templates/employee.html` | template | request-response | New page type (employee self-service cabinet); closest structural analog is `timesheet.html` but layout differs (stats cards above grid, no dept selector, read-only) |
| `export_timesheet_xlsx()` XLSX generation body | utility / file-I/O | file-I/O | No existing openpyxl usage in codebase; use RESEARCH.md Pattern 1 verbatim |
| `export_timesheet_csv()` CSV generation body | utility / file-I/O | file-I/O | No existing CSV export in codebase; use RESEARCH.md Pattern 2 verbatim |

---

## Metadata

**Analog search scope:** `app.py`, `models.py`, `templates/timesheet.html`, `tests/conftest.py`, `tests/test_timesheet.py`
**Files scanned:** 5
**Pattern extraction date:** 2026-06-13
**Key anti-patterns documented in RESEARCH.md:** BytesIO seek(0), `download_name` not `attachment_filename`, scope bypass via dept_id URL param, `db.create_all()` not adding columns
