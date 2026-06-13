---
phase: 03-t-13-timesheet-grid
verified: 2026-06-13T12:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open /timesheet in a real browser as dept_admin, click a work-day cell, pick Б — Больничный, confirm cell updates in place without page reload; then click Восстановить автоматически and confirm cell reverts to the auto-derived symbol."
    expected: "Cell DOM updates in place; no full-page reload; symbol repainted using SYM_BG/SYM_FG maps."
    why_human: "In-place DOM mutation via JS cannot be verified by grep or pytest; requires a real browser."
  - test: "Open /timesheet as dept_admin. Confirm only their department's employees appear; try appending ?dept_id=<other-dept-id> to the URL and confirm no foreign employees appear and the dept_id param is silently ignored."
    expected: "Foreign dept_id URL param is suppressed; session dept_id is always used."
    why_human: "Scope isolation behavior requires browser interaction; the pytest test (test_timesheet_scope_isolation) verifies the server-side logic but not the UI affordance."
  - test: "Open /org_admin as org_admin, pick a month in Сводка по отделам, submit, and confirm the summary table shows correct per-department attendance rates (100% when all employees attended every scheduled day)."
    expected: "Table renders with dept name, employee count, work days, and attendance rate %; color is blue (#1565C0) for >= 80% and orange (#E65100) for < 80%."
    why_human: "Attendance rate correctness requires seeded data and visual inspection; cannot be exhaustively automated."
  - test: "Request /timesheet?month=2099-01 and confirm the yellow Russian banner appears: 'Праздники за 2099 год не загружены. Выходные (В) отмечены автоматически, государственные праздники — нет.'"
    expected: "Yellow banner renders above the grid table."
    why_human: "HTML rendering of a conditional Jinja2 block requires a real browser to confirm visual appearance."
  - test: "Verify KZ_HOLIDAYS dates for 2024/2025/2026 against https://egov.kz official national holiday calendar. Plan 03-04 recorded this as a human-approved checkpoint."
    expected: "All 16 date strings per year match official KZ national holidays."
    why_human: "Per 03-04-PLAN.md gate: holiday data is LOW-confidence (RESEARCH A1); human verification is a blocking phase gate."
---

# Phase 03: T-13 Timesheet Grid Verification Report

**Phase Goal:** HR staff and dept_admins can view the statutory T-13 timesheet grid for any authorized department and month, with symbols auto-derived from face check-in data and KZ public holidays applied automatically.
**Verified:** 2026-06-13T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `/timesheet` route exists and renders T-13 grid with Cyrillic symbols (Я/О/У/В/НН) | ✓ VERIFIED | `@app.route("/timesheet")` at app.py:842; `render_template("timesheet.html", ...)` at app.py:941; `test_timesheet_renders` XPASSED |
| 2 | POST/DELETE `/api/timesheet/override` exists with symbol whitelist {Б,К,П} and scope validation | ✓ VERIFIED | `@app.route("/api/timesheet/override", methods=["POST","DELETE"])` at app.py:961; `MANUAL_SYMBOLS = {"Б","К","П"}` at app.py:194; `test_override_scope_403` and `test_override_invalid_symbol_422` both XPASSED |
| 3 | Inline editing dropdown in timesheet.html — dept_admin+ can override, read-only users cannot | ✓ VERIFIED | `{% if can_edit %}` guard at timesheet.html:230; `fetch('/api/timesheet/override'` at timesheet.html:315; `override-dropdown` div at timesheet.html:232; four buttons present at lines 233-236; `can_edit=(role in ("dept_admin","org_admin","superadmin"))` at app.py:955 |
| 4 | `compute_dept_summary()` and Сводка по отделам on `/org_admin` | ✓ VERIFIED | `def compute_dept_summary` at app.py:337; `?summary_month` handling in org_admin route at app.py:756-779; "Сводка по отделам" section in org_admin.html at line 221; `test_dash04_summary` XPASSED |
| 5 | Missing-holiday banner for years without KZ_HOLIDAYS data | ✓ VERIFIED | `{% if missing_holiday_year %}` block at timesheet.html:108; correct Russian text at timesheet.html:110; `is_holiday_year_missing(year)` at app.py:228; `test_kz_holidays` XPASSED confirming `is_holiday_year_missing(2099) == True` |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app.py` | Symbol engine + /timesheet route + KZ_HOLIDAYS + override file constant and loader | ✓ VERIFIED | `compute_symbol` (line 233), `compute_employee_totals` (297), `compute_timesheet_grid` (317), `compute_dept_summary` (337), `get_holidays_set` (223), `is_holiday_year_missing` (228), `load_timesheet_overrides` (197), `save_timesheet_overrides` (208), `TIMESHEET_OVERRIDES_FILE` (23), `KZ_HOLIDAYS` (170), `MANUAL_SYMBOLS` (194), `timesheet()` route (842), `timesheet_override()` route (961) |
| `templates/timesheet.html` | Server-rendered T-13 grid with selector bar, holiday banner, totals row | ✓ VERIFIED | `<html lang="ru">` (line 2), `<title>Табель Т-13 — МедКонтроль</title>` (6), holiday banner (108), "Итого" totals row (214), "Показать табель" button (103), two-row header with Пн..Вс weekday abbrev (174) |
| `app.py` | POST/DELETE /api/timesheet/override with scope + symbol-whitelist validation | ✓ VERIFIED | `def timesheet_override` at line 963; `@require_role("dept_admin","org_admin","superadmin")` covers both methods (line 962); 422 on invalid symbol (1001); 403 on out-of-scope employee (984/986) |
| `templates/timesheet.html` | Inline override dropdown + fetch handler | ✓ VERIFIED | `fetch('/api/timesheet/override'` (315); `data-auto` attributes (194, 201, 4 instances); `applyOverride()` function (300); `updateCell()` function (287); `openOverrideDropdown()` function (247); Escape/outside-click handlers (264, 256) |
| `app.py` | `compute_dept_summary` + `?summary_month` in /org_admin | ✓ VERIFIED | Function at line 337; route param at line 756; scoped to `session["org_id"]` (769); dept name enriched from depts dict (772-775) |
| `templates/org_admin.html` | Сводка по отделам section | ✓ VERIFIED | "Сводка по отделам" h2 (line 221); `summary_month` GET form (222); table with "Отдел", "Сотрудников", "Рабочих дней", "Явка, %" headers (231-234); color thresholds blue >= 80%, orange < 80% (244) |
| `tests/test_timesheet.py` | 11 xfail/xpassed test functions | ✓ VERIFIED | All 11 required test functions present (lines 38-614); all 11 XPASSED in live run |
| `tests/conftest.py` | TIMESHEET_OVERRIDES_FILE monkeypatch guard | ✓ VERIFIED | `hasattr(_app, "TIMESHEET_OVERRIDES_FILE")` guard at line 65 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `templates/timesheet.html` | `/timesheet route` context vars | `render_template("timesheet.html", days=days, grid_rows=grid_rows, ...)` | ✓ WIRED | app.py:941; all 9 context vars passed; template consumes days, grid_rows, holidays_set, missing_holiday_year, can_edit |
| `app.py timesheet()` | `compute_symbol / compute_timesheet_grid` | per-employee per-day loop building cells list | ✓ WIRED | app.py:932-934; `compute_symbol()` called for both `sym` (with overrides) and `auto` (empty overrides dict) |
| `templates/timesheet.html override JS` | `/api/timesheet/override` | `fetch('/api/timesheet/override', {method: POST/DELETE ...})` | ✓ WIRED | timesheet.html:315; method toggles on `symbol === 'auto'`; response used to call `updateCell()` in place |
| `app.py timesheet_override()` | `save_timesheet_overrides / load_employees` | scope check then atomic write | ✓ WIRED | load_employees at line 979; scope check at 984/986; save_timesheet_overrides at 994/1009 |
| `templates/org_admin.html summary section` | `/org_admin?summary_month route` | GET form with `summary_month` param, server renders summary rows | ✓ WIRED | org_admin.html:222 form action="/org_admin"; app.py:756 reads `request.args.get("summary_month")`; rows passed as `summary_rows` (792) |
| `app.py compute_dept_summary` | `compute_symbol / get_holidays_set` | counts Я days and work days per dept for the month | ✓ WIRED | app.py:355 calls `get_holidays_set(year)`; line 382 calls `compute_symbol(...)` and checks for "Я"; denominator is work days (380) not calendar days |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `templates/timesheet.html` | `grid_rows` | `load_attendance()` + `load_employees()` + `load_timesheet_overrides()` → `compute_symbol()` per cell | Yes — reads JSON files from disk; no static returns | ✓ FLOWING |
| `templates/org_admin.html` Сводка section | `summary_rows` | `compute_dept_summary()` → `compute_symbol()` per employee per day counting Я | Yes — computes over real attendance.json data | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Symbol engine importable and functional | `python -c "import app; app.compute_symbol(...)"` | `All symbols present and importable` | ✓ PASS |
| В for Saturday (isoweekday=6) | `compute_symbol(date(2025,6,7), 'emp1', {}, {}, schedule, set())` | `'В'` | ✓ PASS |
| Я for on-time check-in on past work day | `compute_symbol(date(2025,1,13), 'emp1', {'2025-01-13': {...09:00...}}, {}, schedule, set())` | `'Я'` | ✓ PASS |
| ОУ for late+early same day | `compute_symbol(date(2025,1,13), 'emp1', {'2025-01-13': {check_in:'09:16', check_out:'17:44'}}, {}, schedule, set())` | `'ОУ'` | ✓ PASS |
| KZ holiday 2025-01-01 → В | `compute_symbol(date(2025,1,1), 'emp1', {attended...}, {}, schedule, get_holidays_set(2025))` | `'В'` | ✓ PASS |
| is_holiday_year_missing(2099) | `app.is_holiday_year_missing(2099)` | `True` | ✓ PASS |
| compute_employee_totals aggregation | `compute_employee_totals(['Я','О','У','ОУ','НН','В','Б','К'], schedule)` | `{days_worked:4, hours_worked:36.0, absences:1, late:2, vac_sick:2}` | ✓ PASS |
| All 11 timesheet tests pass | `pytest tests/test_timesheet.py -v` | `11 xpassed in 0.24s` | ✓ PASS |
| Full suite (no regressions) | `pytest tests/ -q` | `31 passed, 4 xfailed, 25 xpassed in 21.38s` | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED (no probe scripts defined for this phase; phase uses pytest as its automated verification mechanism).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| T13-01 | 03-01, 03-02 | GET /timesheet renders T-13 grid | ✓ SATISFIED | `/timesheet` route at app.py:842; `test_timesheet_renders` XPASSED |
| T13-02 | 03-01, 03-02, 03-03 | Manual override cells (Б/К/П) | ✓ SATISFIED | `MANUAL_SYMBOLS` at app.py:194; override API at 961; `test_compute_symbol_all_cases` XPASSED |
| T13-03 | 03-01, 03-02 | Я for on-time; НН for absent work day; В for weekend | ✓ SATISFIED | `compute_symbol` at app.py:233; `test_symbol_auto_derivation` XPASSED |
| T13-04 | 03-01, 03-02 | Late > 15 min → О; boundary exclusive | ✓ SATISFIED | Threshold logic at app.py:271-285; `test_symbol_late` XPASSED |
| T13-05 | 03-01, 03-02 | Early departure > 15 min before end → У; both → ОУ | ✓ SATISFIED | app.py:277-293; `test_symbol_early_and_combined` XPASSED |
| T13-07 | 03-01, 03-02 | Monthly totals row: days/hours/absences/late/vac_sick | ✓ SATISFIED | `compute_employee_totals` at app.py:297; "Итого" totals row in timesheet.html:213; `test_totals_row` XPASSED |
| T13-08 | 03-01, 03-02 | KZ holidays 2024/2025/2026 → В; missing year banner | ✓ SATISFIED | `KZ_HOLIDAYS` dict at app.py:170; `is_holiday_year_missing` at 228; holiday banner in timesheet.html:108; `test_kz_holidays` XPASSED |
| DASH-04 | 03-01, 03-04 | Org_admin per-dept monthly summary with attendance rate % | ✓ SATISFIED | `compute_dept_summary` at app.py:337; Сводка section in org_admin.html:220; `test_dash04_summary` XPASSED |
| D-05 | 03-03 | dept_admin 403 for out-of-dept employee override | ✓ SATISFIED | Scope check at app.py:984; `test_override_scope_403` XPASSED |
| D-08 | 03-02 | dept_admin cannot access foreign dept via URL param | ✓ SATISFIED | `dept_id = session_dept_id` forced at app.py:869 (param ignored); `test_timesheet_scope_isolation` XPASSED |
| V5 | 03-03 | Symbol "Я" (not in MANUAL_SYMBOLS) → 422 | ✓ SATISFIED | `if symbol not in MANUAL_SYMBOLS: return 422` at app.py:1001; `test_override_invalid_symbol_422` XPASSED |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| No TBD/FIXME/XXX markers found in any phase-modified file | — | — | — | — |
| `org_admin.html` placeholders | 104, 108, 164, 174, 210, 271, 275 | `placeholder="..."` HTML attributes | Info | UI input hints, not code stubs — not a debt marker |
| `app.py` `return {}` | 36, 57-58, 125, 135, 147, 159, 204-205 | Empty dict returns | Info | All from `load_*()` error handlers when JSON file missing — legitimate guard pattern per project conventions |

No blocking anti-patterns found.

### Human Verification Required

Plan 03-04 included two blocking human checkpoints (Task 2: KZ holiday verification; Task 3: full-phase browser smoke). The SUMMARY states both were approved, but the browser UI behaviors cannot be verified programmatically.

#### 1. Inline Cell Override — In-Place DOM Update

**Test:** Log in as dept_admin, open /timesheet, click a past work-day cell (non-В), pick "Б — Больничный" from the dropdown. Confirm cell text changes to "Б" and background changes to #E3F2FD without a page reload. Then click the same cell, pick "Восстановить автоматически", confirm cell reverts to the auto-derived symbol.
**Expected:** Cell DOM updated in-place via `applyOverride()` → `updateCell()`; no full-page reload occurs.
**Why human:** JavaScript DOM manipulation during fetch cannot be verified by grep or pytest.

#### 2. Dept Scope Isolation in Browser

**Test:** Log in as dept_admin. Append `?dept_id=<other-dept-id>` to the /timesheet URL. Confirm only the session dept's employees appear, not the foreign dept's employees.
**Expected:** dept_id URL param silently ignored; session dept_id enforced by server (app.py:869).
**Why human:** While `test_timesheet_scope_isolation` verifies server-side logic, the UI behavior (what the user sees in the rendered page) requires visual confirmation.

#### 3. DASH-04 Summary Correctness — Visual Inspection

**Test:** As org_admin, open /org_admin, pick a month with attendance data in "Сводка по отделам", submit. Confirm table shows dept name, employee count, work days, attendance rate %. Verify rate color: blue (#1565C0) for >= 80%, orange (#E65100) for < 80%.
**Expected:** Per-dept summary table renders with correct values and color-coded rates.
**Why human:** Requires seeded attendance data and visual confirmation of rate correctness and color thresholds.

#### 4. Missing-Holiday Banner — Visual Render

**Test:** Visit `/timesheet?month=2099-01` while logged in. Confirm the yellow banner appears above the grid with the exact Russian text: "Праздники за 2099 год не загружены. Выходные (В) отмечены автоматически, государственные праздники — нет."
**Expected:** Yellow banner renders inside `.table-card` above the grid table.
**Why human:** HTML rendering of Jinja2 conditional blocks requires browser to confirm visual appearance and banner text.

#### 5. KZ Holiday Data Verification

**Test:** Deferred from Plan 03-04 Task 2 (blocking human gate). Cross-reference each date in `KZ_HOLIDAYS` in `app.py` (lines 170-192) against https://egov.kz official national holiday calendar for 2024, 2025, and 2026.
**Expected:** All 16 dates per year match official KZ national holidays. Any discrepancies should be corrected directly in `KZ_HOLIDAYS`.
**Why human:** Data accuracy cannot be verified programmatically; requires comparison against an external authoritative source. RESEARCH.md classified this as LOW-confidence source A1; STATE.md flagged it as a pre-ship blocker.

### Gaps Summary

No automated gaps. All 5 observable truths VERIFIED. All 11 test functions pass. All key links wired. Data flows from real JSON files through the symbol engine to the rendered grid. No TBD/FIXME/XXX debt markers found.

Human verification items remain from Plan 03-04 blocking human gates (Tasks 2 and 3). These are expected sign-off steps that require browser interaction and external data comparison, not implementation gaps.

---

_Verified: 2026-06-13T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
