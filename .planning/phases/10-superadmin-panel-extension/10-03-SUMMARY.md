---
phase: 10-superadmin-panel-extension
plan: "03"
subsystem: superadmin-panel
tags: [holiday-calendar, db-backed, crud, superadmin, frontend, backend, api, audit]
dependency_graph:
  requires:
    - HolidayCalendar ORM model (new — this plan)
    - write_audit() helper — from prior plans
    - require_role("superadmin") decorator — from prior plans
    - switchTab / lazy-load tab pattern — from plan 10-01
    - escapeHtml JS helper — from prior plans
    - panelLogs, panelDevices tabs — from plan 10-02
  provides:
    - HolidayCalendar ORM model (models.py)
    - holiday_calendar SQLite table (auto-created by db.create_all())
    - list_holidays (GET /api/holidays)
    - add_holiday (POST /api/holidays)
    - delete_holiday (DELETE /api/holidays/<date>)
    - get_holidays_set DB-backed with KZ_HOLIDAYS fallback
    - panelCalendar tab with loadHolidays / renderHolidays / addHoliday / deleteHoliday / onHolidayYearChange JS
    - Календарь nav link in base.html superadmin sidebar
    - tests/test_sadm05.py — 7 tests
  affects:
    - models.py (new HolidayCalendar model)
    - app.py (new import, modified get_holidays_set, three new endpoints)
    - templates/superadmin.html (new tab, JS functions, state vars, extended switchTab)
    - templates/base.html (new nav link)
tech_stack:
  added: []
  patterns:
    - DB-backed get_holidays_set with hardcoded KZ_HOLIDAYS fallback
    - sa_exc.IntegrityError catch for 409 duplicate-date response
    - datetime.strptime YYYY-MM-DD validation for date input
    - Lazy-load tab pattern (calendarLoaded flag + switchTab gate)
    - POST action pattern (read inputs, fetch POST, show errEl on failure, reload on success)
    - DELETE action pattern (confirm, fetch DELETE, reload on success)
key_files:
  created:
    - tests/test_sadm05.py
  modified:
    - models.py
    - app.py
    - templates/superadmin.html
    - templates/base.html
decisions:
  - HolidayCalendar.date column is String(10) with unique=True — the unique constraint drives 409 detection via sa_exc.IntegrityError catch (no separate lookup needed)
  - year derived from parsed datetime, not from a separate request field — avoids year/date mismatch bugs
  - get_holidays_set falls back to KZ_HOLIDAYS when DB has no rows for that year — preserves correct behavior for years with no DB entries
  - calendarLoaded guard added to switchTab — same lazy-load pattern as employeesLoaded/devicesLoaded/logsLoaded from prior plans
metrics:
  duration: "~30 minutes"
  completed: "2026-06-28"
  tasks_completed: 3
  files_changed: 4
---

# Phase 10 Plan 03: SADM-05 — DB-Backed Holiday Calendar Summary

DB-backed KZ working holiday calendar using HolidayCalendar ORM model, three /api/holidays endpoints with audit trails, DB-backed get_holidays_set with KZ_HOLIDAYS fallback, and a superadmin Calendar tab with year filter, add form, and per-row delete.

## What Was Built

### Task 1: HolidayCalendar model + get_holidays_set DB-backed + import

**HolidayCalendar model (models.py):** New ORM model under `# ─── HolidayCalendar ─────` section divider. Fields: `id` Integer PK autoincrement, `date` String(10) unique not null (YYYY-MM-DD), `name` String(128) not null, `year` Integer not null indexed. No new imports — Integer and String already present.

**app.py import (line 21):** Added `HolidayCalendar` to the second models import line.

**get_holidays_set(year) body replaced (SADM-05 / D-05):** Now queries `HolidayCalendar.query.filter_by(year=year).all()`; if DB rows exist returns `{r.date for r in db_rows}`; otherwise falls back to `set(KZ_HOLIDAYS.get(year, []))`. Signature unchanged — all existing callers unaffected.

**holiday_calendar table:** Created automatically by the existing `db.create_all()` at startup once HolidayCalendar is imported (Pitfall 4 — the import is what registers the model with SQLAlchemy metadata).

### Task 2: Holiday CRUD endpoints + tests

**GET /api/holidays (list_holidays):** Reads `year` query param (defaults to current year). Queries `HolidayCalendar.query.filter_by(year=year).order_by(date)`. Returns JSON list of `{date, name}` objects. Protected by `@require_role("superadmin")`.

**POST /api/holidays (add_holiday):** Parses JSON `date` and `name`. Validates date format via `datetime.strptime(date_str, "%Y-%m-%d")` inside try/except ValueError → 400 "Неверный формат даты". Derives year from parsed date. Catches `sa_exc.IntegrityError` for duplicate date → 409 "Дата уже существует". Generic exception → rollback + 500. On success: calls `write_audit("holiday_add", target_type="holiday", target_id=date_str, new_value={"name": name, "date": date_str})`, returns created record with 201.

**DELETE /api/holidays/<date_str> (delete_holiday):** Queries by date; 404 if not found. Deletes with rollback-on-error. On success: calls `write_audit("holiday_delete", target_type="holiday", target_id=date_str, old_value={"name": deleted_name, "date": date_str})`, returns `{status: "deleted", date: date_str}`.

**tests/test_sadm05.py:** 7 tests all passing:
- (a) POST valid → 201; GET retrieves row for that year
- (b) POST invalid date format → 400 with error key
- (c) POST duplicate date → 409 with error key
- (d) DELETE removes row; subsequent GET omits it
- (e) After POST, get_holidays_set(year) contains that date
- (f) compute_symbol returns "В" for a Monday holiday date in holidays_set
- (g) GET /api/holidays as org_admin → 403

### Task 3: Calendar tab UI + nav link

**panelCalendar tab (templates/superadmin.html):** Page div with:
- Toolbar containing `<label>Год:</label>` and `<select id="holidayYear" onchange="onHolidayYearChange()">` (populated dynamically with current year ±1/+2 range)
- Add form card with `type="date"` input `id="holidayDate"`, text input `id="holidayName"`, error element `id="holidayFormError"`, "Добавить" button calling `addHoliday()`
- Table-card with headers Дата, Название, Действие; tbody `id="holidaysTableBody"`

**JS state added:** `allHolidays = []`, `calendarLoaded = false`

**loadHolidays():** Calls `_initHolidayYearSelect()` to populate year select, then fetches `/api/holidays?year=<selectedYear>` into `allHolidays`, calls `renderHolidays`.

**renderHolidays(list):** Renders rows with `escapeHtml` on date/name (T-10-12); per-row Удалить button calling `deleteHoliday(date)`. Empty-state "Нет данных" row.

**addHoliday():** Reads `holidayDate` and `holidayName`; client-side required-field check; POST /api/holidays; shows `holidayFormError` on failure; reloads on success (POST action pattern).

**deleteHoliday(date):** Confirms, calls DELETE /api/holidays/<date>, reloads on success (DELETE action pattern).

**onHolidayYearChange():** Fetches /api/holidays for selected year, re-renders holidays table.

**switchTab extended:** Now includes `'calendar'` in the panel list; lazy-load guard `if (tab === 'calendar' && !calendarLoaded) { loadHolidays(); calendarLoaded = true; }` added.

**templates/base.html:** Added Календарь nav link (`href=/superadmin/calendar`, icon 📅) after the Логи link in the superadmin sidebar block.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat | Mitigation | Location |
|--------|------------|----------|
| T-10-10 Tampering (POST date param) | `datetime.strptime` validates YYYY-MM-DD before insert; unique constraint + IntegrityError catch returns 409 on duplicate | app.py add_holiday() |
| T-10-11 Info Disclosure / Elevation | `@require_role("superadmin")` on all three endpoints returns 403 for other roles; verified by test (g) | app.py list_holidays(), add_holiday(), delete_holiday() |
| T-10-12 Tampering (name rendering) | `escapeHtml()` applied to date and name in renderHolidays | templates/superadmin.html |
| T-10-13 DoS (get_holidays_set per render) | get_holidays_set called once per grid render at year level, not inside compute_symbol per-cell loop | app.py architecture unchanged |
| T-10-14 Schema addition without migration | db.create_all() is idempotent; only creates the missing holiday_calendar table | app.py startup |

## Known Stubs

None. loadHolidays fetches live data from GET /api/holidays which queries the production holiday_calendar table.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 — HolidayCalendar model + get_holidays_set | a2e6e9c | models.py, app.py |
| 2 — Holiday CRUD endpoints + tests | 7da3bcf | app.py, tests/test_sadm05.py |
| 3 — Calendar tab UI + nav link | d06401e | templates/superadmin.html, templates/base.html |

## Self-Check: PASSED

All files exist: models.py, tests/test_sadm05.py, SUMMARY.md
All commits found: a2e6e9c (Task 1), 7da3bcf (Task 2), d06401e (Task 3)
