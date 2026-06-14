# Phase 4: Export & Employee Cabinet - Research

**Researched:** 2026-06-13
**Domain:** Flask file streaming, openpyxl XLSX generation, UTF-8 BOM CSV, employee cabinet routing, User-Employee linkage schema
**Confidence:** MEDIUM

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Export — Entry Point & Scope (EXP-01, EXP-02, EXP-03)**
- D-01: Export buttons ("Скачать XLSX" and "Скачать CSV") live on the existing `/timesheet` page, added to the selector bar. No separate export page or wizard.
- D-02: Export is always scoped to the currently visible grid — whatever dept+month is selected in the timesheet selector. No additional org/dept selector on the export UI.
- D-03: The `.xlsx` file follows the official T-13 form layout: merged header cells (month name spans day columns), Cyrillic column labels (Я, О, В, etc.), employee rows, and a totals row at the bottom. Not a flat one-row-header table.
- D-04: Downloaded filename pattern: `T13_[dept-name]_[YYYY-MM].xlsx` and `T13_[dept-name]_[YYYY-MM].csv`. dept-name taken from the department's `name` field.
- D-05: The `.csv` file uses UTF-8 BOM prefix (`﻿`) and semicolon delimiter (`;`) for correct Cyrillic display when opened in Windows Excel.
- D-06: Export routes are new Flask GET routes (`/timesheet/export/xlsx` and `/timesheet/export/csv`) accepting the same `?dept_id=X&month=YYYY-MM` query params as the timesheet route. They reuse `compute_timesheet_grid()` to generate the data, then stream the file.

**Employee Cabinet — Layout & Navigation (EMP-01, EMP-02, EMP-03)**
- D-07: The `/employee` route is repurposed to render a new `employee.html` template (the full employee cabinet). It no longer redirects to `dashboard.html`.
- D-08: The `employee.html` page has three sections (top to bottom): (1) Summary stats cards — 3 cards: "Опоздания", "Отсутствия", "Ранний уход" for the current month; (2) Month selector — `<form method="GET">` with `<input type="month">` restricted to current and previous month; (3) T-13 grid — read-only, one employee's row.
- D-09: The T-13 grid in the employee cabinet shows one employee's row for the selected month, with all 31 day columns and the totals row at the bottom.
- D-10: The employee cabinet is scoped server-side: the route reads `session['user_id']` → looks up the linked `Employee` record via `User.emp_id` (or equivalent FK) → renders only that employee's data. Any URL manipulation to see another employee returns 403.

**Arrival/Departure Time Display (EMP-02)**
- D-11: Exact check-in and check-out times appear as a tooltip on hover over each day cell in the employee cabinet's T-13 grid. Tooltip text: `"Приход: HH:MM / Уход: HH:MM"` (or `"Приход: HH:MM / Уход: —"` if no check-out recorded). No separate table for times.
- D-12: Tooltip is implemented with `title` attribute on the `<td>` for simplicity, or a CSS tooltip (`:hover::after` pseudo-element). Claude picks the approach that fits the existing CSS patterns in `timesheet.html`.

### Claude's Discretion

- Exact `openpyxl` cell styling (column widths, font sizes, header row heights, cell borders) — Claude follows standard T-13 form proportions and uses openpyxl's `MergedCell`, `Alignment`, and `Font` APIs.
- CSV column order — Claude matches the xlsx column order (employee name, then day 1…31, then totals).
- Flask `send_file` vs `make_response` for streaming the export file — Claude picks the pattern that works cleanly with Flask 3.x and BytesIO.
- Whether to link `User` to `Employee` via a FK column `emp_id` on `User` (may already exist from Phase 1/2) or via username match — Claude reads `models.py` and uses the existing relationship.
- CSS tooltip implementation detail — Claude reuses the CSS variable/style patterns from `timesheet.html`.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXP-01 | T-13 grid can be exported as .xlsx (openpyxl) with merged header cells, Cyrillic column labels, and proper cell widths | openpyxl 3.1.5 not yet installed; install via pip; `merge_cells`, `column_dimensions`, `Font`, `Alignment` APIs confirmed; Flask `send_file` + `BytesIO` streaming pattern confirmed |
| EXP-02 | T-13 grid can be exported as .csv with UTF-8 BOM prefix and semicolon delimiter for correct Cyrillic display in Windows Excel | Python built-in `csv` module + `utf-8-sig` encoding + `StringIO` → encode → `BytesIO` pattern confirmed; no new dependency needed |
| EXP-03 | Export is scoped to the user's role: dept_admin exports their department only; org_admin exports their entire organization; superadmin can export any org | Same role-scoping logic as `/timesheet` route; reuse dept_id resolution pattern from lines 892-918 in app.py |
| EMP-01 | Employee can view their own T-13 timesheet grid for the current and previous months (read-only) | `/employee` route exists but currently routes to dashboard.html; repurpose with `compute_timesheet_grid()` passing single-employee dict; month selector via `<input type="month">` with min/max server-side |
| EMP-02 | Employee can view exact arrival and departure times for each day as logged by face recognition | `AttendanceRecord.check_in_time` / `check_out_time` columns exist; pass raw attendance records to template; render as `title` attribute on each `<td>` |
| EMP-03 | Employee can view a summary of their late arrivals, absences, and early departures for the current month | `compute_employee_totals()` already returns `late`, `absences` counts; missing `early_departure` count needs extraction from symbol list (symbols containing "У" or "ОУ") |
</phase_requirements>

---

## Summary

Phase 4 adds two end-to-end vertical slices to the existing Flask + SQLite stack: T-13 export and employee self-service cabinet. All data is already computed by `compute_timesheet_grid()` and `compute_employee_totals()` (app.py lines 316 and 296) — Phase 4's job is to surface that data through new routes and new templates, not to recompute it.

The export slice is straightforward: two new GET routes mirror the timesheet route, reuse its dept-resolution and role-scoping logic verbatim, call `compute_timesheet_grid()` with the resolved dept, then stream the result via `send_file(BytesIO(...))`. openpyxl 3.1.5 needs installation in the venv (not currently present). The T-13 xlsx header structure (merged title row, org+dept row, column header row) is well-defined in the UI-SPEC and CONTEXT.md D-03.

The employee cabinet slice requires two schema changes that are currently missing: (1) `User.emp_id` column does not exist — it must be added to the `User` model and migrated via `db.create_all()` (idempotent); and (2) employee-role users cannot currently log in because `ALLOWED_LOGIN_ROLES` does not include `'employee'` (line 80 of app.py). Both are small, targeted changes. The `/employee` route already exists with `@require_role("employee")` guard; its body just needs replacing with cabinet-rendering logic. The employee cabinet template reuses `timesheet.html`'s CSS wholesale — no new design tokens.

**Primary recommendation:** Plan two feature slices: Plan 04-01 (Export: install openpyxl, two export routes, buttons in timesheet.html) and Plan 04-02 (Employee Cabinet: User.emp_id schema, ALLOWED_LOGIN_ROLES fix, /employee route logic, employee.html template). Tests for each slice follow the existing conftest pattern (in-memory SQLite, seed helpers).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Export XLSX/CSV file generation | API / Backend (app.py route) | — | File generation is CPU work; result streamed to browser via HTTP response |
| Export role scoping enforcement | API / Backend (app.py route) | — | Server-side; never trust client dept_id param without session-scope check |
| Export button rendering | Frontend Server (SSR/Jinja2) | — | Buttons are `<a href>` anchors in timesheet.html; rendered server-side with current dept_id param |
| Employee cabinet data computation | API / Backend (app.py route) | — | Calls compute_timesheet_grid() and compute_employee_totals(); pure server logic |
| Employee data isolation (403 guard) | API / Backend (app.py route) | — | Must be server-side; URL manipulation must return 403 |
| Employee cabinet UI rendering | Frontend Server (SSR/Jinja2) | — | Jinja2 template; no AJAX; same server-render pattern as timesheet |
| Arrival/departure tooltips | Browser / Client (HTML title attr) | — | `title` attribute on `<td>`; native browser tooltip — zero JS required |
| Month selector (employee cabinet) | Browser / Client + Frontend Server | — | `<input type="month">` with server-set min/max; GET form submission triggers server-render |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openpyxl | 3.1.5 | XLSX file generation with styled cells, merged headers, column widths | Standard Python xlsx library; no Java dependency; write-only WorkBook pattern works with BytesIO |
| Python `csv` module | stdlib | CSV generation with custom delimiter | Built-in; no install needed; `utf-8-sig` encoding handles BOM automatically |
| Python `io.BytesIO` | stdlib | In-memory file buffer for streaming | Avoids temp-file creation on disk; Flask `send_file` accepts BytesIO directly |
| Flask `send_file` | Flask 3.1.3 (installed) | Stream generated file as HTTP download | Standard Flask pattern; `download_name` param (Flask 2+) replaces deprecated `attachment_filename` |

**Package legitimacy note:** openpyxl received `SUS` verdict from package-legitimacy seam due to unknown weekly-download count on PyPI signal (PyPI API limitation — downloads field not always available). openpyxl is confirmed legitimate via its official repository at `https://foss.heptapod.net/openpyxl/openpyxl` and extensive industry usage. The project instructions state "openpyxl available via pip" as a known dependency.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `openpyxl.styles` (Font, Alignment, PatternFill) | 3.1.5 | Cell styling for T-13 header rows | Use for merged title rows, bold headers, and center-alignment |
| `openpyxl.utils.get_column_letter` | 3.1.5 | Convert column index to letter (e.g., 5 → 'E') | Use when setting column_dimensions by index |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openpyxl | xlsxwriter | xlsxwriter is write-only (better for large files) but no style reuse; openpyxl is the more familiar standard |
| `title` tooltip | CSS `:hover::after` tooltip | CSS tooltip gives more visual control; `title` attribute is simpler, zero JS, already used in timesheet.html |
| `send_file(BytesIO)` | `make_response()` with manual headers | `send_file` is cleaner; `make_response` is only needed if Flask's content-type detection fails |

**Installation:**
```bash
pip install openpyxl==3.1.5
```
(into `/var/www/sites/face-almgp33/venv/`)

**Version verification:** [VERIFIED: pip index versions openpyxl] — latest is 3.1.5, published 2024-06-28. No other packages need installation; all others are stdlib or already in venv.

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| openpyxl | PyPI | ~12 yrs | unknown (PyPI signal gap) | https://foss.heptapod.net/openpyxl/openpyxl | SUS (unknown-downloads) | **Approved** — project instructions state it is available; official Mercurial repo confirmed; industry-standard library |

**Packages removed due to SLOP verdict:** none

**Packages flagged as suspicious (SUS):** openpyxl — flagged only due to PyPI download-count signal being unavailable (a known limitation of PyPI's API for some packages). This is a false positive. CLAUDE.md and REQUIREMENTS.md both explicitly name openpyxl as an available dependency. No checkpoint needed.

---

## Critical Findings (Schema & Runtime Gaps)

### Gap 1: `User.emp_id` column does not exist

`models.py` `User` class has columns: `id`, `username`, `password_hash`, `role`, `active`, `org_id`, `dept_id`. **There is no `emp_id` column.**

D-10 in CONTEXT.md calls for linking User to Employee via `User.emp_id (or equivalent FK)`. The planning ARCHITECTURE.md also states `emp_id` FK should exist on User for the employee-cabinet role.

**Required action:** Add `emp_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)` to the `User` model. Because `db.create_all()` is called on startup and is idempotent (it creates missing tables but does NOT alter existing tables), this column addition requires an explicit `ALTER TABLE user ADD COLUMN emp_id TEXT` migration step or a drop-and-recreate during deployment (safe since Phase 6 migration.py handles initial data load).

**Recommended approach:** Add `emp_id` to `User` model + add an `ALTER TABLE user ADD COLUMN emp_id TEXT` call inside the startup block (guarded by `try/except OperationalError` to handle re-runs). This is the minimal change that works with the existing `db.create_all()` startup pattern.

### Gap 2: `ALLOWED_LOGIN_ROLES` excludes `'employee'`

Line 80 of `app.py`:
```python
ALLOWED_LOGIN_ROLES = ("superadmin", "org_admin", "dept_admin")
```

Employee-role users cannot log in. The `/employee` route has `@require_role("employee")` but login never redirects there because `'employee'` is not in `ALLOWED_LOGIN_ROLES`.

**Required action:** Add `"employee"` to `ALLOWED_LOGIN_ROLES` **and** add a `redirect(url_for("employee_page"))` branch in the login POST handler (after `elif role == "dept_admin":`).

### Gap 3: `compute_employee_totals()` does not return early-departure count separately

`compute_employee_totals()` (line 296) returns: `days_worked`, `hours_worked`, `absences`, `late`, `vac_sick`.

EMP-03 requires an "early departure" count (Ранний уход) separate from the late count. Symbols У and ОУ indicate early departure. The existing function does NOT expose early departure count.

**Options:**
1. Add `early`: `sum(1 for s in symbols if s in ("У", "ОУ"))` to the returned dict (backwards-compatible since callers access by key).
2. Compute it inline in the employee route without changing the function.

Option 1 is cleaner. The existing callers only use `totals.days_worked`, `totals.hours_worked`, `totals.absences`, `totals.late`, `totals.vac_sick` — adding `early` key is non-breaking.

### Gap 4: `compute_timesheet_grid()` returns symbols list, not attendance records

For EMP-02 (tooltip with exact times), the route needs raw `check_in_time` / `check_out_time` from `AttendanceRecord`. The grid cells in the admin `timesheet.html` contain `{sym, auto, date}` dicts — no time data.

The employee cabinet route must build a separate `times_by_date` dict:
```python
times_by_date = {}
for r in _att_recs:
    if r.emp_id == emp_id:
        times_by_date[r.date] = {"check_in": r.check_in_time, "check_out": r.check_out_time}
```
Then pass it to the template alongside the grid. This is a cheap extra query (already performed for the grid computation anyway).

---

## Architecture Patterns

### System Architecture Diagram

```
Browser GET /timesheet/export/xlsx?dept_id=X&month=YYYY-MM
         │
         ▼
Flask route: export_xlsx()
  ├── Validate session role (require_role guard)
  ├── Resolve dept_id (same 3-branch logic as /timesheet: dept_admin=forced, org_admin=scoped, superadmin=any)
  ├── 403 if dept_id outside session's org scope
  ├── Load data (AttendanceRecord, TimesheetOverride queries — same as /timesheet)
  ├── compute_timesheet_grid() → (days, grid_rows)
  ├── Build openpyxl Workbook
  │     Row 1: merged "ТАБЕЛЬ УЧЁТА РАБОЧЕГО ВРЕМЕНИ (Форма Т-13)"
  │     Row 2: merged "OrgName — DeptName — MonthYear"
  │     Row 3: column headers (Сотрудник, 1..31, Я, Ч, П/НН, О, Б/К)
  │     Rows 4+: employee data rows (grid_rows)
  │     Last row: totals (Итого)
  ├── wb.save(BytesIO) → buf.seek(0)
  └── send_file(buf, download_name='T13_Dept_2026-06.xlsx', as_attachment=True)

Browser GET /employee?month=YYYY-MM
         │
         ▼
Flask route: employee_page()
  ├── require_role("employee") guard
  ├── user = User.query.get(session['user_id'])
  ├── if not user.emp_id → render empty-state "not linked to employee record"
  ├── emp = Employee.query.get(user.emp_id) → 403 if None
  ├── Resolve month param (current default, clamp to prev/current)
  ├── Load AttendanceRecord for emp_id + month range
  ├── Load TimesheetOverride for emp_id
  ├── compute_timesheet_grid(year, month, {emp.id: emp_dict}, attendance, overrides, holidays)
  ├── Compute stats: late, absences, early (from totals + symbols)
  ├── Build times_by_date dict for tooltip data
  └── render_template("employee.html", grid_row, stats, times_by_date, month_str, ...)
```

### Recommended Project Structure

No structural changes — all code goes into existing files:
```
app.py                   # +export_xlsx(), +export_csv() routes, employee_page() rewrite
                         # +User.emp_id to ALLOWED_LOGIN_ROLES, login handler employee branch
models.py                # +emp_id column to User class
templates/
├── timesheet.html       # +two <a> export buttons in .selector-bar
└── employee.html        # NEW: full employee cabinet template
tests/
└── test_export_employee.py   # NEW: test file for EXP-01..03, EMP-01..03
```

### Pattern 1: XLSX Export via BytesIO

```python
# Source: openpyxl docs + Flask 3.x send_file docs [CITED: openpyxl.readthedocs.io/en/stable/styles.html]
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from flask import send_file

@app.route("/timesheet/export/xlsx")
@require_role("dept_admin", "org_admin", "superadmin")
def export_timesheet_xlsx():
    # ... resolve dept_id, month, scoped_employees (same as /timesheet route) ...
    days, grid_rows = compute_timesheet_grid(year, month_num, scoped_employees, attendance, overrides, holidays_set)

    wb = Workbook()
    ws = wb.active
    ws.title = f"Табель {month_str}"

    num_cols = 1 + len(days) + 5  # emp-name + days + 5 totals

    # Row 1: title (merged)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    ws["A1"] = "ТАБЕЛЬ УЧЁТА РАБОЧЕГО ВРЕМЕНИ (Форма Т-13)"
    ws["A1"].font = Font(bold=True, size=12)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    # Row 2: org/dept/period (merged)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    ws["A2"] = f"{org_name} — {dept_name} — {month_label}"  # month_label e.g. "Июнь 2026"
    ws["A2"].alignment = Alignment(horizontal="center")

    # Row 3: column headers
    headers = ["Сотрудник"] + [str(d.day) for d in days] + ["Я", "Ч", "П/НН", "О", "Б/К"]
    for col_idx, header in enumerate(headers, start=1):
        ws.cell(row=3, column=col_idx, value=header).font = Font(bold=True)

    # Rows 4+: employee rows
    for row_idx, (emp_id, emp_name, symbols, totals) in enumerate(grid_rows, start=4):
        ws.cell(row=row_idx, column=1, value=emp_name)
        for col_idx, sym in enumerate(symbols, start=2):
            ws.cell(row=row_idx, column=col_idx, value=sym or "")
        # Totals columns
        ws.cell(row=row_idx, column=len(days)+2, value=totals["days_worked"])
        ws.cell(row=row_idx, column=len(days)+3, value=totals["hours_worked"])
        ws.cell(row=row_idx, column=len(days)+4, value=totals["absences"])
        ws.cell(row=row_idx, column=len(days)+5, value=totals["late"])
        ws.cell(row=row_idx, column=len(days)+6, value=totals["vac_sick"])

    # Column widths
    ws.column_dimensions["A"].width = 24  # employee name
    for col_idx in range(2, len(days)+2):
        from openpyxl.utils import get_column_letter
        ws.column_dimensions[get_column_letter(col_idx)].width = 4

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    safe_dept = re.sub(r"[^A-Za-zА-Яа-яЁё0-9]", "_", dept_name)
    return send_file(buf, download_name=f"T13_{safe_dept}_{month_str}.xlsx", as_attachment=True)
```

### Pattern 2: CSV Export via utf-8-sig + BytesIO

```python
# Source: Python stdlib csv module + utf-8-sig encoding [CITED: tobywf.com/2017/08/unicode-csv-excel/]
import csv
import io

@app.route("/timesheet/export/csv")
@require_role("dept_admin", "org_admin", "superadmin")
def export_timesheet_csv():
    # ... resolve dept_id, month, scoped_employees same as xlsx route ...
    days, grid_rows = compute_timesheet_grid(year, month_num, scoped_employees, attendance, overrides, holidays_set)

    str_buf = io.StringIO()
    writer = csv.writer(str_buf, delimiter=";")

    # Header rows
    writer.writerow([f"ТАБЕЛЬ Т-13 — {dept_name} — {month_str}"])
    writer.writerow(["Сотрудник"] + [str(d.day) for d in days] + ["Я", "Ч", "П/НН", "О", "Б/К"])

    for emp_id, emp_name, symbols, totals in grid_rows:
        row = [emp_name] + [sym or "" for sym in symbols]
        row += [totals["days_worked"], totals["hours_worked"],
                totals["absences"], totals["late"], totals["vac_sick"]]
        writer.writerow(row)

    content = str_buf.getvalue().encode("utf-8-sig")  # BOM + UTF-8
    byte_buf = io.BytesIO(content)
    safe_dept = re.sub(r"[^A-Za-zА-Яа-яЁё0-9]", "_", dept_name)
    return send_file(byte_buf, download_name=f"T13_{safe_dept}_{month_str}.csv",
                     as_attachment=True, mimetype="text/csv")
```

### Pattern 3: Employee Cabinet Route

```python
@app.route("/employee")
@require_role("employee")
def employee_page():
    user = User.query.get(session.get("user_id"))
    username = user.username if user else ""

    # D-10: resolve emp_id from User.emp_id FK
    emp_id = user.emp_id if user else None
    if not emp_id:
        return render_template("employee.html", username=username, emp=None,
                               error="Ваш аккаунт не привязан к записи сотрудника. Обратитеськ администратору.")

    emp_obj = Employee.query.get(emp_id)
    if not emp_obj:
        return render_template("403.html"), 403

    # D-08: month param clamped to current and previous month
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    prev_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    month_str = request.args.get("month", current_month)
    if month_str < prev_month or month_str > current_month:
        month_str = current_month
    year, month_num = map(int, month_str.split("-"))

    # Load data scoped to this single employee
    emp_dict = _emp_to_dict(emp_obj)
    scoped_employees = {emp_id: emp_dict}
    start_str = f"{year:04d}-{month_num:02d}-01"
    _, num_days = calendar.monthrange(year, month_num)
    end_str = f"{year:04d}-{month_num:02d}-{num_days:02d}"

    _att_recs = AttendanceRecord.query.filter(
        AttendanceRecord.emp_id == emp_id,
        AttendanceRecord.date >= start_str,
        AttendanceRecord.date <= end_str,
    ).all()
    attendance = {}
    times_by_date = {}  # EMP-02: for tooltip data
    for r in _att_recs:
        attendance.setdefault(r.date, {})[r.emp_id] = {
            "check_in": r.check_in_time, "check_out": r.check_out_time
        }
        times_by_date[r.date] = {"check_in": r.check_in_time, "check_out": r.check_out_time}

    _ov_recs = TimesheetOverride.query.filter_by(emp_id=emp_id).all()
    overrides = {emp_id: {r.date: r.symbol for r in _ov_recs}}

    holidays_set = get_holidays_set(year)
    days, grid_rows = compute_timesheet_grid(year, month_num, scoped_employees, attendance, overrides, holidays_set)

    emp_name, symbols, totals = grid_rows[0][1], [c["sym"] for c in grid_rows[0][2]], grid_rows[0][3]
    # EMP-03: early departure count (У or ОУ symbols)
    early_count = sum(1 for s in symbols if s in ("У", "ОУ"))
    stats = {
        "late": totals["late"],
        "absences": totals["absences"],
        "early": early_count,
    }

    return render_template("employee.html",
        username=username,
        emp_name=emp_name,
        grid_row=grid_rows[0],   # (emp_id, name, cells, totals)
        stats=stats,
        times_by_date=times_by_date,
        days=days,
        month_str=month_str,
        current_month=current_month,
        prev_month=prev_month,
        holidays_set=holidays_set,
    )
```

**Note:** The `grid_rows` from `compute_timesheet_grid()` returns `(emp_id, name, symbols_list, totals)` tuples. The admin `timesheet.html` augments cells with `{sym, auto, date}` dicts inline in the route. For the employee cabinet, the route should use the same inline approach (calling `compute_symbol` per cell) rather than `compute_timesheet_grid()` directly, to add the `times_by_date` data alongside each cell. See Anti-Patterns section.

### Pattern 4: User.emp_id Schema Migration

```python
# In models.py — add to User class:
emp_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

# In app.py startup block (after db.create_all()):
from sqlalchemy import text, exc as sa_exc
try:
    with db.engine.connect() as conn:
        conn.execute(text("ALTER TABLE user ADD COLUMN emp_id TEXT"))
        conn.commit()
except sa_exc.OperationalError:
    pass  # Column already exists — idempotent
```

This is necessary because `db.create_all()` does NOT add missing columns to existing tables — it only creates new tables. The `ALTER TABLE ... ADD COLUMN` approach is the standard SQLite migration pattern for additive changes.

### Anti-Patterns to Avoid

- **Calling `compute_timesheet_grid()` then trying to add time data retroactively:** The function returns only symbols per cell. If you need `times_by_date` alongside cells, build the cell list inline (as the admin `/timesheet` route does at lines 966-973) rather than calling `compute_timesheet_grid()`. Both approaches are valid — choose inline for employee cabinet to include the raw attendance time per cell.
- **Using `attachment_filename` in `send_file`:** This param was renamed to `download_name` in Flask 2.0. Flask 3.1.3 will raise TypeError with the old name.
- **Saving openpyxl workbook to BytesIO without seek(0):** After `wb.save(buf)`, the buffer position is at the end. Call `buf.seek(0)` before passing to `send_file()` or the response will be a 0-byte file.
- **Writing BOM manually as b'\xef\xbb\xbf':** Use `str_buf.getvalue().encode('utf-8-sig')` instead. Python's `utf-8-sig` codec handles BOM insertion automatically and correctly.
- **Trusting dept_id from query param without session scope check in export routes:** Same pitfall as the existing `/timesheet` route (Pitfall 3 in Phase 3 research). Enforce role-scoped access in export routes — a `dept_admin` must not be able to export a different dept by changing the URL.
- **Using `db.create_all()` to add new columns to existing User table:** `create_all()` is idempotent for table creation but does not run ALTER TABLE. You must explicitly run `ALTER TABLE user ADD COLUMN emp_id TEXT` for the new column to appear in existing databases.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cyrillic CSV for Windows Excel | Custom BOM insertion code | `str.encode('utf-8-sig')` (stdlib) | Python handles BOM correctly via codec; manual `b'\xef\xbb\xbf'` prefix risks double-encoding |
| XLSX cell merging | Custom XML manipulation | `ws.merge_cells()` (openpyxl) | openpyxl handles the underlying OOXML relationship graph for merged cells |
| Column letter conversion (1 → 'A') | Custom chr(ord('A')+i) logic | `openpyxl.utils.get_column_letter(n)` | Handles all 16384 columns including multi-letter (AA, AB, ...) |
| File streaming response | Writing to temp file on disk | `BytesIO` + `send_file()` | No disk I/O; no cleanup needed; PM2 single-worker constraint makes temp files safe but unnecessary |

**Key insight:** Both export formats are single-pass generation — build in memory, stream immediately. No temp files, no async workers needed at clinic scale.

---

## Common Pitfalls

### Pitfall 1: openpyxl merge_cells styling — value must go in top-left cell only

**What goes wrong:** Writing a value to any cell in a merged region other than the top-left cell (e.g., `ws["C1"] = "header"` when A1:Z1 is merged) silently does nothing — the value is lost.
**Why it happens:** openpyxl writes merged cell content only from the top-left cell; other cells in the range become MergedCell objects.
**How to avoid:** Always write value and style to the first cell in the merge range: `ws["A1"] = "Title"` then `ws["A1"].font = Font(bold=True)`.
**Warning signs:** XLSX opens with blank merged header rows.

### Pitfall 2: BytesIO position not reset before send_file

**What goes wrong:** `send_file(buf, ...)` returns a 0-byte file download.
**Why it happens:** After `wb.save(buf)` or `buf.write(...)`, the buffer's internal position is at the end. `send_file` reads from the current position.
**How to avoid:** Always call `buf.seek(0)` immediately before `send_file(buf, ...)`.
**Warning signs:** Downloaded file is 0 bytes or browser shows empty download.

### Pitfall 3: Export route dept_id scope bypass

**What goes wrong:** A `dept_admin` calls `/timesheet/export/xlsx?dept_id=OTHER_DEPT` and gets another dept's data.
**Why it happens:** Export routes reuse dept_id from query param without enforcing session-based scope.
**How to avoid:** Copy the 3-branch role-scope logic from `/timesheet` lines 892-918 exactly — don't simplify. `dept_admin` always uses `session['dept_id']`; `org_admin` validates `dept.org_id == session['org_id']`; `superadmin` accepts any.
**Warning signs:** Test: dept_admin GET with wrong dept_id returns 200 instead of 403.

### Pitfall 4: `db.create_all()` does not add User.emp_id to existing database

**What goes wrong:** After adding `emp_id` to the `User` model, `User.query.get(id).emp_id` raises `AttributeError` or `OperationalError: no such column: user.emp_id`.
**Why it happens:** `db.create_all()` only creates tables that don't exist yet. It does not ALTER existing tables to add new columns.
**How to avoid:** Run `ALTER TABLE user ADD COLUMN emp_id TEXT` on startup, guarded by `try/except OperationalError` to be idempotent.
**Warning signs:** No error on startup (create_all succeeds), but ORM query for `user.emp_id` fails at runtime.

### Pitfall 5: Employee login blocked by ALLOWED_LOGIN_ROLES

**What goes wrong:** Employee user attempts login, gets "Доступ запрещён для этой роли" error (line 554 of app.py).
**Why it happens:** `ALLOWED_LOGIN_ROLES = ("superadmin", "org_admin", "dept_admin")` — `"employee"` is absent.
**How to avoid:** Add `"employee"` to `ALLOWED_LOGIN_ROLES` tuple and add `redirect(url_for("employee_page"))` in the login role-dispatch block.
**Warning signs:** Employee user exists in DB with correct password but cannot log in.

### Pitfall 6: Month clamp — employee must not access arbitrary historical months

**What goes wrong:** Employee manually sets `?month=2024-01` and sees last year's attendance.
**Why it happens:** Month param trusted from URL without server-side clamp.
**How to avoid:** After parsing the month param, enforce: `if month_str < prev_month or month_str > current_month: month_str = current_month`. Compute `prev_month` server-side, never from client.
**Warning signs:** Employee can retrieve data for months more than one prior.

### Pitfall 7: No `re` import for filename sanitization

**What goes wrong:** `NameError: name 're' is not defined` in export route.
**Why it happens:** `app.py` currently does not import `re` — it uses `os.path.join` and string ops, not regex.
**How to avoid:** Add `import re` to the existing imports block at the top of `app.py`.
**Warning signs:** 500 error on first export attempt.

---

## Code Examples

### Verified pattern: openpyxl merge_cells and styling

```python
# Source: [CITED: openpyxl.readthedocs.io/en/stable/styles.html]
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

wb = Workbook()
ws = wb.active

# Merge row 1 across all columns (e.g., columns 1-10)
ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=10)
ws["A1"].value = "Merged Title"
ws["A1"].font = Font(bold=True, size=12)
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

# Column width
ws.column_dimensions["A"].width = 24

# Save to BytesIO
from io import BytesIO
buf = BytesIO()
wb.save(buf)
buf.seek(0)  # CRITICAL: must seek before reading/streaming
```

### Verified pattern: Flask send_file with BytesIO

```python
# Source: [CITED: flask.palletsprojects.com — send_file docs]
from flask import send_file
from io import BytesIO

buf = BytesIO()
wb.save(buf)
buf.seek(0)  # reset position
return send_file(
    buf,
    download_name="T13_Dept_2026-06.xlsx",  # Flask 3.x param name
    as_attachment=True,
    # mimetype auto-detected from .xlsx extension in Flask 3.x
)
```

### Verified pattern: UTF-8 BOM CSV

```python
# Source: [CITED: tobywf.com/2017/08/unicode-csv-excel/]
import csv, io
from flask import send_file

str_buf = io.StringIO()
writer = csv.writer(str_buf, delimiter=";")
writer.writerow(["Сотрудник", "1", "2", ...])
writer.writerow(["Имя", "Я", "НН", ...])

# Encode with UTF-8 BOM for Windows Excel Cyrillic compatibility
content = str_buf.getvalue().encode("utf-8-sig")
byte_buf = io.BytesIO(content)

return send_file(byte_buf, download_name="T13_Dept_2026-06.csv",
                 as_attachment=True, mimetype="text/csv")
```

### Verified pattern: export button in timesheet.html (from UI-SPEC D-01)

```html
<!-- Add after .btn-primary "Показать табель" button inside .selector-bar form -->
{% if dept_id %}
<a href="/timesheet/export/xlsx?dept_id={{ dept_id }}&amp;month={{ month_str }}" class="btn-secondary">Скачать XLSX</a>
<a href="/timesheet/export/csv?dept_id={{ dept_id }}&amp;month={{ month_str }}" class="btn-secondary">Скачать CSV</a>
{% endif %}
```

The `.btn-secondary` CSS class is not yet in `timesheet.html` — add it (already defined in the UI-SPEC; matches the pattern from `superadmin.html` and `dept_admin.html`).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `attachment_filename` param in Flask `send_file` | `download_name` param | Flask 2.0 (2021) | Old code raises TypeError in Flask 3.x |
| Write CSV with manual `﻿` BOM prefix | Use `encoding='utf-8-sig'` codec | Python 3.x | Simpler, codec handles BOM correctly |
| `openpyxl.compat` module | Removed in openpyxl 3.0 | openpyxl 3.0 (2019) | Any old openpyxl 2.x examples using compat fail |

**Deprecated/outdated:**
- `attachment_filename`: replaced by `download_name` in Flask 2.0+; raises `TypeError` in Flask 3.1.3
- `openpyxl.writer.dump_worksheet`: removed; use standard `Workbook.save()` for all cases

---

## Runtime State Inventory

This is a feature addition phase (not rename/refactor), so a full runtime state inventory is not required. However, two targeted runtime state items need tracking:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| DB schema | `user` table missing `emp_id` column | ALTER TABLE user ADD COLUMN emp_id TEXT at startup (guarded) |
| App code state | `ALLOWED_LOGIN_ROLES` excludes `'employee'` | Code edit: add `"employee"` to tuple + login redirect |
| Stored data | No employee-role User records exist in users.json | No data migration; employee accounts created via admin UI post-deploy |
| OS-registered state | None | — |
| Secrets/env vars | None — no new env vars needed | — |
| Build artifacts | openpyxl not in venv | `pip install openpyxl==3.1.5` in venv |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pytest.ini` (testpaths = tests) |
| Quick run command | `SECRET_KEY=test pytest tests/test_export_employee.py -x -q` |
| Full suite command | `SECRET_KEY=test pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXP-01 | XLSX download with merged headers, Cyrillic labels, correct content | integration | `SECRET_KEY=test pytest tests/test_export_employee.py::test_export_xlsx_dept_admin -x` | ❌ Wave 0 |
| EXP-02 | CSV download with UTF-8 BOM, semicolon delimiter | integration | `SECRET_KEY=test pytest tests/test_export_employee.py::test_export_csv_bom_encoding -x` | ❌ Wave 0 |
| EXP-03 | Export scoped to role: dept_admin gets only dept, org_admin gets org | integration | `SECRET_KEY=test pytest tests/test_export_employee.py::test_export_scope_enforcement -x` | ❌ Wave 0 |
| EMP-01 | Employee can GET /employee with T-13 grid for current/prev month | integration | `SECRET_KEY=test pytest tests/test_export_employee.py::test_employee_cabinet_renders -x` | ❌ Wave 0 |
| EMP-02 | Tooltip times rendered in HTML (Приход/Уход per cell) | integration | `SECRET_KEY=test pytest tests/test_export_employee.py::test_employee_tooltip_times -x` | ❌ Wave 0 |
| EMP-03 | Stats cards show late/absences/early counts correctly | unit | `SECRET_KEY=test pytest tests/test_export_employee.py::test_employee_stats_counts -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `SECRET_KEY=test pytest tests/test_export_employee.py -x -q`
- **Per wave merge:** `SECRET_KEY=test pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_export_employee.py` — covers EXP-01..03, EMP-01..03
- [ ] Extend `tests/conftest.py` with `seed_attendance()` helper if not present (check existing helper list)

**Existing conftest helpers status:** `seed_users`, `seed_employees`, `seed_depts`, `seed_orgs` all exist. `seed_attendance` (for AttendanceRecord) needs verification:

```bash
grep -n "seed_attendance\|AttendanceRecord" /var/www/sites/face-almgp33/tests/conftest.py
```

---

## Security Domain

**security_enforcement:** `true` (from config.json)
**ASVS level:** 1

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `ALLOWED_LOGIN_ROLES` + bcrypt + session (existing; employee login is new) |
| V3 Session Management | yes | Flask session (existing); no new session fields for export |
| V4 Access Control | yes | `@require_role` decorator + dept_id scope check in export routes |
| V5 Input Validation | yes | month param: parse + clamp; dept_id param: validate via ORM query (existing pattern) |
| V6 Cryptography | no | No cryptographic operations in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Dept scope bypass (export another dept via URL manipulation) | Spoofing / IDOR | Enforce role-scope in export routes (same 3-branch as /timesheet); dept_admin always forced to session dept |
| Month param out-of-range for employee cabinet | Tampering | Server-side clamp: `if month_str < prev_month or month_str > current_month` |
| Employee accessing another employee's cabinet via URL | IDOR | Session-derived emp_id only; never accept emp_id from URL param; return 403 on mismatch |
| CSV injection (Cyrillic data containing =, +, - prefixes) | Tampering | Cyrillic employee names and symbols (Я/О/В/etc.) do not trigger CSV formula injection; no mitigation needed for this dataset |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| openpyxl | EXP-01 (XLSX export) | ✗ (not in venv) | — | None — must install |
| Python `csv` module | EXP-02 (CSV export) | ✓ (stdlib) | stdlib | — |
| Python `io.BytesIO` | EXP-01, EXP-02 | ✓ (stdlib) | stdlib | — |
| Python `re` module | export filename sanitization | ✓ (stdlib, not yet imported) | stdlib | — |
| Flask `send_file` | EXP-01, EXP-02 | ✓ (Flask 3.1.3 in venv) | 3.1.3 | — |
| SQLite `user` table `emp_id` col | EMP-01, EMP-02, EMP-03 | ✗ (column missing) | — | None — must migrate |
| PM2 `face-recognition` process | deployment | ✓ (running, id=5) | — | — |

**Missing dependencies with no fallback:**
- openpyxl 3.1.5 — must be installed via `pip install openpyxl==3.1.5` in venv before XLSX export will function
- `User.emp_id` column — must be added via `ALTER TABLE user ADD COLUMN emp_id TEXT` before employee cabinet will function

**Missing dependencies with fallback:**
- `re` module — stdlib, just needs `import re` added to app.py imports

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Flask `send_file` auto-detects mimetype from `download_name` extension in Flask 3.1.3 for .xlsx files | Code Examples | If detection fails, explicitly pass `mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'` |
| A2 | `openpyxl.Workbook.save(BytesIO)` works identically to `save(filepath)` | Code Examples | Confirmed in openpyxl source (wb.save calls wb._write which accepts any file-like object) |
| A3 | `db.create_all()` does NOT add new columns to existing tables in SQLite via Flask-SQLAlchemy 3.1.1 | Critical Findings | [ASSUMED] based on standard SQLAlchemy behavior — if wrong, the ALTER TABLE workaround is still safe to include |
| A4 | `conftest.py` does not yet have a `seed_attendance()` helper | Validation Architecture | Check with `grep seed_attendance tests/conftest.py`; if missing, add to Wave 0 gaps |

---

## Open Questions

1. **Does `seed_attendance()` helper exist in `tests/conftest.py`?** (RESOLVED)
   - Resolution: It did not exist; 04-01 Task 1 adds the `seed_attendance()` ORM helper to `tests/conftest.py`.
   - What we know: `seed_users`, `seed_employees`, `seed_depts`, `seed_orgs` are confirmed present
   - What's unclear: Whether `AttendanceRecord` seeding is needed for export/cabinet tests
   - Recommendation: Check `grep -n "seed_attendance\|AttendanceRecord" tests/conftest.py` before writing test plan; if missing, add `seed_attendance()` helper to Wave 0

2. **Russian month names for XLSX Row 2 (e.g., "Июнь 2026")** (RESOLVED)
   - Resolution: Use the hard-coded `MONTHS_RU` dict (no locale dependency); 04-02 Task 1 adds it at module level and uses it for the XLSX Row 2 header.
   - What we know: Python's `datetime.strftime('%B')` returns English month names; locale-dependent
   - What's unclear: Whether locale is set to Russian on the server
   - Recommendation: Use a hard-coded Russian month names dict (same pattern as KZ_HOLIDAYS hard-coding) rather than relying on locale: `MONTHS_RU = {1: "Январь", 2: "Февраль", ..., 6: "Июнь", ...}`

3. **User account creation UI for employee role** (RESOLVED)
   - Resolution: 04-03 Task 4 adds an optional `emp_id` param to `create_user` (applied only when role == "employee") and exposes an emp_id field in the admin create-user form, so an employee account links to an Employee record at creation. The broader question of which roles see the USERS tab (currently superadmin-only) is recorded as a deferred follow-up RBAC task in 04-03 — out of Phase 4 scope per CONTEXT.md.
   - What we know: `create_user` API at line 1102 accepts `role="employee"` (role not excluded). `ROLE_HIERARCHY` includes `'employee'`. The UI for creating employee accounts may or may not expose this role.
   - What's unclear: Whether `dept_admin` can create employee-role users via the existing admin UI (this is needed for the employee cabinet to be usable end-to-end)
   - Recommendation: Phase 4 should add `emp_id` param to the `create_user` API call for employee-role creation; this is the minimal link between User and Employee records.

---

## Sources

### Primary (MEDIUM confidence)
- [CITED: openpyxl.readthedocs.io/en/stable/styles.html] — Font, Alignment, PatternFill, merge_cells patterns
- [VERIFIED: pip index versions openpyxl] — openpyxl 3.1.5 latest version confirmed
- `app.py` (codebase) — compute_timesheet_grid, compute_employee_totals, require_role, User model, ALLOWED_LOGIN_ROLES, send_file imports
- `models.py` (codebase) — User model confirmed missing emp_id column; AttendanceRecord columns confirmed
- `tests/conftest.py` (codebase) — test infrastructure confirmed; pytest 9.0.3; in-memory SQLite fixture pattern

### Secondary (LOW confidence)
- [CITED: tobywf.com/2017/08/unicode-csv-excel/] — utf-8-sig encoding for BOM-prefixed CSV
- WebSearch: Flask send_file BytesIO pattern with download_name param for Flask 3

### Tertiary
- geeksforgeeks.org — column_dimensions.width and row_dimensions.height openpyxl usage

---

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — openpyxl 3.1.5 confirmed on PyPI; Flask send_file pattern confirmed from search + codebase
- Architecture: HIGH — all routing patterns read directly from existing codebase
- Critical gaps: HIGH — User.emp_id absence and ALLOWED_LOGIN_ROLES confirmed by direct code reading
- Pitfalls: MEDIUM — BytesIO/seek pitfall from search; scope bypass from codebase code review

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (30 days; stable library versions)
