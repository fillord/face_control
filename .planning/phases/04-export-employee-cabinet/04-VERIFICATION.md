---
phase: 04-export-employee-cabinet
verified: 2026-06-14T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open /timesheet as dept_admin, select a dept and month, click Скачать XLSX, open the downloaded file in Excel or LibreOffice Calc"
    expected: "File opens without errors; Row 1 shows merged title 'ТАБЕЛЬ УЧЁТА РАБОЧЕГО ВРЕМЕНИ (Форма Т-13)' bold-centered; Row 2 shows org/dept/month; Row 3 shows column headers with Cyrillic labels; employee rows fill correctly"
    why_human: "Binary XLSX structural rendering (merged cells, fonts, column widths) cannot be validated via grep or test assertions; test only verifies b'PK' magic bytes"
  - test: "Open /timesheet as dept_admin, click Скачать CSV, open the downloaded file in Windows Excel (or Excel via import with semicolon delimiter)"
    expected: "Cyrillic characters display without garbling; columns are correctly separated; no encoding artifacts"
    why_human: "UTF-8 BOM rendering in Windows Excel cannot be asserted programmatically — only b'\\xef\\xbb\\xbf' presence is tested; actual display requires a Windows Excel environment"
  - test: "Log in as an employee-role user linked to an employee record (emp_id set), navigate to /employee, change the month selector to the previous month and back"
    expected: "Page renders the single-row T-13 grid for the employee; month selector clamps to current/previous; grid is read-only (no edit controls on cells)"
    why_human: "Read-only constraint and month selector UI behavior cannot be asserted by HTTP response inspection alone; requires visual/interactive verification"
  - test: "Hover over a day cell on /employee that has attendance data"
    expected: "Tooltip shows 'Приход: HH:MM / Уход: HH:MM' with actual times from the employee's check-in records"
    why_human: "title attribute tooltip rendering and time slicing display is a browser UI behavior not verifiable via response byte inspection in tests"
---

# Phase 04: Export & Employee Cabinet Verification Report

**Phase Goal:** Authorized users can download the T-13 grid as Excel or CSV; employees can view their own attendance records and timesheet without admin access.
**Verified:** 2026-06-14
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | T-13 grid exports as .xlsx with merged header cells, Cyrillic labels, readable column widths | VERIFIED | `export_timesheet_xlsx()` at app.py:1198 builds openpyxl Workbook with `merge_cells` (rows 1-2), bold Cyrillic headers row 3, col A width=24, day cols width=4. `buf.seek(0)` before `send_file`. test_export_xlsx_dept_admin PASSED (b"PK" magic + T13_ Content-Disposition) |
| SC-2 | T-13 grid exports as .csv with UTF-8 BOM prefix and semicolon delimiter; Cyrillic displays correctly in Windows Excel | VERIFIED | `export_timesheet_csv()` at app.py:1262 uses `csv.writer(delimiter=";")` and `encode("utf-8-sig")` codec. test_export_csv_bom_encoding PASSED (BOM prefix b"\xef\xbb\xbf" + b";" present) |
| SC-3 | Export is scoped to role: dept_admin downloads their dept only; org_admin their org; superadmin any | VERIFIED | `_resolve_export_scope()` at app.py:1105 implements exact 3-branch logic: dept_admin → session["dept_id"] (param ignored); org_admin → validates dept.org_id == session_org_id else 403; superadmin → any dept_id param. test_export_scope_enforcement PASSED |
| SC-4 | Employee can view own T-13 grid for current and previous months (read-only) with arrival/departure times | VERIFIED | `employee_page()` at app.py:746 reads emp_id only from `user.emp_id` (session-derived); server-side month clamp `[prev_month, current_month]`; builds single-row grid with `times_by_date`; passes to `employee.html`. Template has no onclick/tabindex on grid cells. test_employee_cabinet_renders PASSED + test_employee_tooltip_times PASSED |
| SC-5 | Employee summary shows late arrival count, absence count, early departure count for current month | VERIFIED | `employee_page()` computes `early_count = sum(1 for s in symbols if s in ("У", "ОУ"))` (Gap 3 workaround) and `stats = {late, absences, early}`. `employee.html` renders Опоздания, Отсутствия, Ранний уход stat cards. test_employee_stats_counts PASSED |

**Score:** 5/5 truths verified

### Requirements Coverage

| Requirement | Phase | Description | Status | Evidence |
|-------------|-------|-------------|--------|----------|
| EXP-01 | Phase 4 | .xlsx export with merged headers and Cyrillic labels | SATISFIED | `export_timesheet_xlsx()` + openpyxl 3.1.5 installed; test passes |
| EXP-02 | Phase 4 | .csv export with UTF-8 BOM and semicolon delimiter | SATISFIED | `export_timesheet_csv()` + utf-8-sig codec; test passes |
| EXP-03 | Phase 4 | Export scoped to role; no cross-dept data leak | SATISFIED | `_resolve_export_scope()` 3-branch dept_admin lock; test_export_scope_enforcement passes |
| EMP-01 | Phase 4 | Employee views own T-13 grid for current/previous months (read-only) | SATISFIED | `employee_page()` + `employee.html` with read-only grid; test passes |
| EMP-02 | Phase 4 | Employee sees exact arrival/departure times per day | SATISFIED | `times_by_date` dict built in `employee_page()`; template renders Приход/Уход tooltip; test_employee_tooltip_times passes |
| EMP-03 | Phase 4 | Employee sees late, absence, early-departure summary | SATISFIED | `stats` dict with late/absences/early passed to template; 3 stat cards rendered; test passes |

All 6 Phase 4 requirements satisfied. No orphaned requirements detected (all EXP/EMP IDs mapped to plans and verified).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_export_employee.py` | 6 passing tests (EXP-01..03, EMP-01..03) | VERIFIED | 6 functions present; 0 xfail decorators active; all 6 pass |
| `tests/conftest.py` | `seed_attendance()` ORM helper | VERIFIED | `def seed_attendance` at line 245; imports `AttendanceRecord` lazily inside app_context; calls `db.session.add` + `db.session.commit` |
| `app.py` | `export_timesheet_xlsx()` and `export_timesheet_csv()` routes | VERIFIED | Both routes at lines 1198 and 1262; decorated `@require_role("dept_admin","org_admin","superadmin")`; `send_file` with `download_name=`; `buf.seek(0)` before send; utf-8-sig encoding |
| `app.py` | `employee_page()` rewrite | VERIFIED | Line 746; `@require_role("employee")`; emp_id from session only; month clamp; AttendanceRecord ORM load; times_by_date; stats; renders employee.html |
| `app.py` | ALLOWED_LOGIN_ROLES includes "employee" | VERIFIED | Line 93: `("superadmin", "org_admin", "dept_admin", "employee")` |
| `app.py` | Login dispatch redirects employee to employee_page | VERIFIED | Line 581-582: `elif role == "employee": return redirect(url_for("employee_page"))` |
| `app.py` | Idempotent ALTER TABLE startup migration | VERIFIED | After `db.create_all()`, `ALTER TABLE user ADD COLUMN emp_id TEXT` wrapped in `try/except sa_exc.OperationalError: pass` |
| `app.py` | `create_user()` persists emp_id for employee role only | VERIFIED | Line 1437: `new_emp_id = (data.get("emp_id") or None) if target_role == "employee" else None`; passed to `User(...)` at line 1448 |
| `models.py` | `User.emp_id` FK column | VERIFIED | Line 40: `emp_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)` |
| `templates/employee.html` | Employee cabinet with stats, month selector, read-only grid | VERIFIED | File exists (lang="ru"); contains "Мой табель", Опоздания, Отсутствия, Ранний уход, Приход tooltip logic; no onclick/tabindex on cells |
| `templates/timesheet.html` | Скачать XLSX / Скачать CSV buttons | VERIFIED | Lines 107-108: both anchor hrefs inside `{% if dept_id %}`; `.btn-secondary` CSS at line 27-28 |
| `templates/admin.html` | emp_id input in create-user form | VERIFIED | Lines 145, 151-153: `#newEmpId` input inside `#empIdGroup` (hidden by default); `onchange="toggleEmpIdField()"` on `#newRole`; `toggleEmpIdField()` JS at line 241; `createUser()` includes `emp_id: empId` in POST body at line 293 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `templates/timesheet.html` | `/timesheet/export/xlsx` | anchor href with dept_id + month params | WIRED | `grep "timesheet/export/xlsx" templates/timesheet.html` → line 107 confirmed |
| `templates/timesheet.html` | `/timesheet/export/csv` | anchor href with dept_id + month params | WIRED | line 108 confirmed |
| `app.py export routes` | `_resolve_export_scope() → compute_symbol / compute_employee_totals` | `_build_export_grid()` helper at line 1185 | WIRED | Both routes call `_build_export_grid(days, scoped_employees, ...)` which calls `compute_symbol` and `compute_employee_totals` per employee |
| `app.py employee_page` | `User.emp_id → Employee` | `user.emp_id` then `Employee.query.get(emp_id)` | WIRED | Lines 752, 760 in employee_page() |
| `templates/employee.html` | `times_by_date` | `title` attribute on day td cells | WIRED | Line 156: `title="{% if time_data %}Приход: {{ time_data.check_in[:5]...` |
| `app.py login dispatch` | `employee_page` | `elif role == "employee": redirect(url_for("employee_page"))` | WIRED | Line 581-582 confirmed |
| `templates/admin.html create-user form` | `app.py create_user` | `emp_id: empId` in POST body to /api/users | WIRED | admin.html line 293 + app.py line 1437/1448 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `templates/employee.html` | `stats.late`, `stats.absences`, `stats.early` | `employee_page()` computes from ORM `AttendanceRecord` + `compute_employee_totals()` | Yes — ORM query at app.py:780-784 | FLOWING |
| `templates/employee.html` | `times_by_date` | `employee_page()` builds from ORM `AttendanceRecord` rows in same loop | Yes — check_in_time/check_out_time from DB rows | FLOWING |
| `templates/employee.html` | `grid_row` (cells, totals) | `compute_symbol()` + `compute_employee_totals()` from ORM attendance + overrides | Yes — ORM data drives symbol computation | FLOWING |
| `templates/timesheet.html` export hrefs | `dept_id`, `month_str` | Rendered from template context passed by `/timesheet` route | Yes — dept_id from scope resolution in /timesheet route | FLOWING |
| Export routes | `grid_rows` | `_resolve_export_scope()` + `_build_export_grid()` from ORM Employee + AttendanceRecord + TimesheetOverride | Yes — ORM queries at lines 1158-1175 | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 6 Phase 4 tests pass | `SECRET_KEY=test venv/bin/python -m pytest tests/test_export_employee.py -v` | 6 passed, 0 errors | PASS |
| Full test suite has no regressions | `SECRET_KEY=test venv/bin/python -m pytest tests/ -q` | 40 passed, 9 xfailed, 20 xpassed, 0 failures | PASS |
| openpyxl 3.1.5 installed | `venv/bin/python -c "import openpyxl; print(openpyxl.__version__)"` | 3.1.5 | PASS |
| `User.emp_id` column exists on model | `python -c "from models import User; assert hasattr(User, 'emp_id')"` | attribute present (line 40 in models.py) | PASS |
| employee login role admitted | `python -c "import app; assert 'employee' in app.ALLOWED_LOGIN_ROLES"` | line 93 confirmed | PASS |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app.py` | 386 | `dept_name = dept_id  # fallback if dept name not available here` (in dashboard route, not Phase 4 code) | Info | Pre-existing code, not modified by Phase 4 |

No `TBD`, `FIXME`, or `XXX` debt markers found in any Phase 4 modified files. No stub patterns (empty returns, placeholder components) found in Phase 4 artifacts.

The SQLAlchemy `LegacyAPIWarning` (`Query.get()` deprecated in 2.0) appears in 62 test warnings but is pre-existing across the codebase and not introduced by Phase 4.

### Human Verification Required

All automated checks pass. The following items require human browser verification:

### 1. XLSX File Opens Correctly in Excel

**Test:** As dept_admin, select a dept and month on /timesheet, click "Скачать XLSX", open the downloaded file in Excel or LibreOffice Calc.
**Expected:** Row 1 shows merged bold-centered title "ТАБЕЛЬ УЧЁТА РАБОЧЕГО ВРЕМЕНИ (Форма Т-13)"; Row 2 shows org/dept/month subtitle; Row 3 has Cyrillic column headers; employee rows populate with symbol codes and totals; column A is wide enough for employee names.
**Why human:** Binary XLSX layout (merged cell rendering, font display, column widths) cannot be verified via grep or HTTP response assertions — the test only checks the ZIP magic bytes `b"PK"` and Content-Disposition header.

### 2. CSV Cyrillic Display in Windows Excel

**Test:** As dept_admin, click "Скачать CSV", open in Windows Excel (or import with semicolon delimiter detection).
**Expected:** Cyrillic text (employee names, header labels) displays correctly without garbling; columns split on semicolons; no BOM artifact visible in the first cell.
**Why human:** UTF-8 BOM correct rendering in Windows Excel requires an actual Windows Excel session; the test verifies b"\xef\xbb\xbf" byte presence only.

### 3. Employee Cabinet Read-Only Grid and Month Selector Clamping

**Test:** Log in as an employee-role user with a linked emp_id, go to /employee, try changing the month to a month older than "previous month" via the URL (?month=2024-01).
**Expected:** Page reloads showing the current month's data (server-side clamp rejects out-of-range month); no edit controls (dropdowns, pencil icons) appear on grid cells.
**Why human:** Server-side month clamp is code-verified, but the visual absence of edit controls and the UX of the selector clamping require interactive inspection.

### 4. Tooltip Hover Times Display

**Test:** On /employee, hover the cursor over a day cell that has attendance data (check_in_time populated from a face recognition check-in event).
**Expected:** Browser tooltip shows "Приход: HH:MM / Уход: HH:MM" with the employee's actual times sliced to 5 characters; empty check_out shows "—".
**Why human:** Browser tooltip rendering from `title=""` HTML attributes requires a visual browser check; the test asserts that the bytes "Приход" and "09:05" appear in the response body but cannot confirm the tooltip renders correctly on hover in an actual browser.

### Gaps Summary

No automated gaps. All 5 roadmap success criteria verified. All 6 requirement IDs (EXP-01, EXP-02, EXP-03, EMP-01, EMP-02, EMP-03) satisfied by substantive, wired, data-flowing implementations. Status is `human_needed` because 4 UI/browser behaviors cannot be confirmed programmatically.

---

_Verified: 2026-06-14_
_Verifier: Claude (gsd-verifier)_
