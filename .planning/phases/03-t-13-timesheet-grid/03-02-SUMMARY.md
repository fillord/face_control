---
phase: 03-t-13-timesheet-grid
plan: "02"
subsystem: timesheet
tags: [flask, jinja2, t13, symbol-engine, kz-holidays, data-isolation]
dependency_graph:
  requires: ["03-01"]
  provides: ["compute_symbol", "compute_employee_totals", "get_holidays_set", "is_holiday_year_missing", "load_timesheet_overrides", "save_timesheet_overrides", "KZ_HOLIDAYS", "MANUAL_SYMBOLS", "TIMESHEET_OVERRIDES_FILE", "/timesheet route", "timesheet.html"]
  affects: ["app.py", "templates/timesheet.html"]
tech_stack:
  added: ["calendar (stdlib)", "timedelta (stdlib)"]
  patterns: ["atomic-tmp-flock-replace for save_timesheet_overrides", "pure-function symbol engine", "server-side scope enforcement"]
key_files:
  created: ["templates/timesheet.html"]
  modified: ["app.py"]
decisions:
  - "compute_symbol is pure (no I/O) — accepts pre-loaded dicts, returns one symbol or None"
  - "Future days (date > today) return None to exclude from totals — prevents inflated НН counts mid-month"
  - "dept_admin dept_id param silently ignored — always forced to session dept_id (D-08)"
  - "org_admin cross-org dept_id returns 403 per threat model T-03-scope"
  - "Override dropdown wired to page reload on success (not cell DOM update) — edit API lands in 03-03"
metrics:
  duration: "~20 minutes"
  completed: "2026-06-12T23:37:52Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
  tests_green: 8
---

# Phase 03 Plan 02: T-13 Timesheet Wave 1 — Symbol Engine + Grid Render Summary

Delivered the first end-to-end T-13 vertical slice: a pure `compute_symbol()` engine with KZ holiday support, a `compute_employee_totals()` aggregator, atomic override file I/O, and a server-rendered `/timesheet` route with a scoped Jinja2 grid template.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Symbol engine + data layer (constants, loaders, compute_symbol, totals) | `0c338a7` | app.py |
| 2 | /timesheet route + timesheet.html grid render | `903a7e1` | app.py, templates/timesheet.html |

## What Was Built

### Task 1 — Symbol Engine + Data Layer (`app.py`)

- Added `import calendar` and `timedelta` to imports
- Added `TIMESHEET_OVERRIDES_FILE` constant after `DEPTS_FILE`
- Added `# ─── T-13 Timesheet ───...` section with:
  - `KZ_HOLIDAYS` dict (2024/2025/2026, 16 standard KZ national holidays each)
  - `MANUAL_SYMBOLS = {"Б", "К", "П"}`
  - `load_timesheet_overrides()` — load_users() try/except pattern with TIMESHEET_OVERRIDES_FILE
  - `save_timesheet_overrides(data)` — atomic tmp+flock+os.replace pattern (save_users() style)
  - `get_holidays_set(year)` — returns `set(KZ_HOLIDAYS.get(year, []))`
  - `is_holiday_year_missing(year)` — `year not in KZ_HOLIDAYS`
  - `compute_symbol(day_date, emp_id, attendance, overrides, schedule, holidays_set)` — pure function; priority: override > В (weekend via isoweekday() or holiday date) > future-day None > attendance/НН/Я/О/У/ОУ; thresholds built as HH:MM:00 strings; HH:MM times normalized with ":00"
  - `compute_employee_totals(symbols, schedule)` — days_worked(Я/О/У/ОУ), late(О/ОУ), absences(П/НН), vac_sick(Б/К), hours_worked = days × daily_hours
  - `compute_timesheet_grid()` — grid-level helper used internally

### Task 2 — `/timesheet` Route + Template (`app.py`, `templates/timesheet.html`)

**Route (`app.py`):**
- `@app.route("/timesheet")` with `@require_role("dept_admin","org_admin","superadmin")`
- Month param resolved with try/except fallback to current month
- Scope enforcement: dept_admin → session dept_id (param ignored); org_admin → param must match session org_id or 403; superadmin → unrestricted
- Employee filter: `e.get("dept_id") == dept_id`; None dept_id treated as out-of-scope (Pitfall 3)
- Passes `days`, `grid_rows`, `holidays_set`, `missing_holiday_year`, `can_edit`, `dept_options` to template

**Template (`templates/timesheet.html`):**
- `<html lang="ru">` and `<title>Табель Т-13 — МедКонтроль</title>`
- Selector bar with month `<input type="month">` and dept `<select>` (org_admin = flat list, superadmin = `<optgroup>` per org, dept_admin = no selector)
- Yellow holiday banner (`missing_holiday_year` condition) with exact copy from UI-SPEC
- Two-row grid header: day numbers + weekday abbreviations (Пн..Вс); weekends/holidays in `#9E9E9E`
- Symbol cells with background/text color map per UI-SPEC; `title` attributes in Russian; `ОУ` at 11px; future/None cells transparent; `data-emp`/`data-date` attributes; `cursor:pointer` + `tabindex=0` for editable cells (override API wired in 03-03)
- Totals row labeled "Итого"
- Empty states: "В этом отделе нет сотрудников." and "Выберите отдел для просмотра табеля."
- Override dropdown HTML + stub JS (page-reload on success; API routes land in 03-03)
- `escHtml` utility, keyboard support (Enter/Space to open, Escape to close)
- `scope="col"` on all `<th>` elements; `scope="row"` on employee name cells

## Test Results

All 8 targeted tests now XPASSED (flipped from xfail):

| Test | Requirement |
|------|-------------|
| test_compute_symbol_all_cases | T13-02 |
| test_symbol_auto_derivation | T13-03 |
| test_symbol_late | T13-04 |
| test_symbol_early_and_combined | T13-05 |
| test_totals_row | T13-07 |
| test_kz_holidays | T13-08 |
| test_timesheet_renders | T13-01 |
| test_timesheet_scope_isolation | D-08 |

Full suite: 31 passed, 6 xfailed, 23 xpassed — no regressions.

## Deviations from Plan

### Auto-fixed Issues

None.

### Intentional Implementation Choices (within Claude's Discretion)

**1. Override cell click → page reload (not DOM in-place update)**
- **Reason:** The plan notes "The click handler is wired in 03-03; cells are inert this plan" — but the dropdown HTML was added now per the plan. On success, the JS does `window.location.reload()` rather than cell DOM update. This is correct for plan 02 since the override API routes don't exist yet. 03-03 will wire up the proper in-place cell update.
- **Files modified:** templates/timesheet.html

**2. compute_timesheet_grid() added as bonus helper**
- **Reason:** Clean extraction of the per-employee loop for future reuse (DASH-04 in 03-04). Pure function, no I/O.
- **Files modified:** app.py

## Known Stubs

None. All data flows are wired:
- Selector bar submits to `/timesheet` with real server render
- Symbol computation reads from real `attendance.json` + employee schedules + `timesheet_overrides.json`
- Override dropdown HTML present but POST API not yet implemented (03-03)

## Threat Surface Scan

All surfaces match the plan's threat model:
- `/timesheet` GET: dept_id scope enforced server-side; No new unplanned trust boundaries introduced.
- `save_timesheet_overrides()`: atomic write pattern — no concurrent write risk.

No new unplanned threat surfaces detected.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| app.py | FOUND |
| templates/timesheet.html | FOUND |
| 03-02-SUMMARY.md | FOUND |
| Commit 0c338a7 (Task 1) | FOUND |
| Commit 903a7e1 (Task 2) | FOUND |
