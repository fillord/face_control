---
phase: 10-superadmin-panel-extension
plan: "05"
subsystem: superadmin-panel
tags: [export, xlsx, openpyxl, t13, superadmin, multi-org, backend, frontend]
dependency_graph:
  requires:
    - Organization ORM model (name, id) — from Phase 10 plan 01
    - Department ORM model (id, org_id, name) — from Phase 10 plan 01
    - Employee ORM model (id, name, org_id, dept_id) — from Phase 10 plan 01
    - AttendanceRecord ORM model (emp_id, date, check_in_time, check_out_time) — from prior plans
    - TimesheetOverride ORM model (emp_id, date, symbol) — from prior plans
    - _build_export_grid() helper — existing in app.py
    - _emp_to_dict() helper — existing in app.py
    - get_holidays_set(year) — DB-backed from plan 10-03
    - MONTHS_RU constant — existing in app.py
    - require_role("superadmin") decorator — from Phase 1
    - panelSystem tab — existing in superadmin.html
  provides:
    - superadmin_export_xlsx (GET /api/superadmin/export/xlsx) — app.py
    - exportAllXlsx JS function — templates/superadmin.html
    - exportMonth input (id=exportMonth, type=month) — templates/superadmin.html
    - tests/test_sadm01.py — 3 pytest tests
  affects:
    - app.py (new endpoint)
    - templates/superadmin.html (new export card in panelSystem, new JS function)
tech_stack:
  added: []
  patterns:
    - Load shared data once before org loop (Pitfall 6 — no per-employee DB queries)
    - Sheet name truncation to 31 chars + numeric suffix deduplication (Pitfall 2)
    - Empty-workbook guard via placeholder sheet 'Нет данных' (Pitfall 8)
    - _build_export_grid() reuse for per-dept grid building
    - window.location navigation for file download (no new tab)
    - Init-time month picker default via init() in template JS
key_files:
  created:
    - tests/test_sadm01.py
  modified:
    - app.py
    - templates/superadmin.html
decisions:
  - Shared attendance/overrides/holidays loaded once before the org loop for performance (Pitfall 6)
  - Sheet names use while-loop dedup with numeric suffix (cleaner than RESEARCH count-based approach)
  - exportMonth default set in init() rather than HTML attribute for DRY maintenance
  - exportAllXlsx uses window.location (not fetch) so browser triggers native file download
metrics:
  duration: "~8 minutes"
  completed: "2026-06-29"
  tasks_completed: 2
  files_changed: 3
---

# Phase 10 Plan 05: SADM-01 — Global Multi-Org T-13 Excel Export Summary

Delivered SADM-01 (D-07): GET /api/superadmin/export/xlsx builds one worksheet per organization (department-grouped T-13 grid) for a selected month, with shared data loaded once, sheet-name deduplication, and empty-workbook guard; the System tab exposes a month picker and Скачать button.

## What Was Built

### Task 1: Backend — multi-org T-13 export endpoint + tests (app.py, tests/test_sadm01.py)

**GET /api/superadmin/export/xlsx (SADM-01 / D-07):** New endpoint added after the existing holiday endpoints in the `# ─── API: Superadmin Extensions ───` section. Protected by `@require_role("superadmin")`.

**Month param handling:** Parses `month` query param as YYYY-MM (default `datetime.now().strftime("%Y-%m")`). Validates range (1 ≤ month_num ≤ 12, 2000 ≤ year ≤ 2099); falls back to current month on invalid input.

**Shared data load (Pitfall 6):** AttendanceRecord rows for the month, all TimesheetOverride rows, and `get_holidays_set(year)` loaded once before the org loop. `attendance` dict keyed by `date → emp_id → {check_in, check_out}`; `overrides` keyed by `emp_id → date → symbol`.

**Workbook construction:** `Workbook()` created; default sheet removed via `wb.remove(wb.active)`. Organizations queried ordered by name. For each org:
- Sheet name computed from `org.name[:31]`; deduplicated via while-loop with `_N` numeric suffix (Pitfall 2)
- Bold merged title row: `ТАБЕЛЬ Т-13 — <org name> — <MONTHS_RU month> <year>`
- For each Department in the org ordered by name, with at least one employee: bold italic dept subtitle row; bold header row (Сотрудник, day numbers 1–N, Я, Ч, П/НН, О, Б/К); employee rows from `_build_export_grid(days, scoped_employees, attendance, overrides, holidays_set)`; blank spacer row between departments
- Column A width = 24

**Empty-workbook guard (Pitfall 8):** If `wb.sheetnames` is empty after the org loop, creates `"Нет данных"` placeholder sheet.

**Response:** `BytesIO` buffer, `wb.save(buf)`, `buf.seek(0)`, `send_file` as attachment `T13_ALL_<month>.xlsx`.

**tests/test_sadm01.py:** 3 tests, all passing:
- (a) `test_export_xlsx_one_sheet_per_org` — 2 seeded orgs → 200 response, xlsx content-type, 2 sheets with correct titles
- (b) `test_export_xlsx_no_orgs_returns_placeholder` — no orgs seeded → 1 sheet named 'Нет данных'
- (c) `test_export_xlsx_403_for_org_admin` — org_admin session → 403

### Task 2: Frontend — month picker + download button in System tab (templates/superadmin.html)

**Export card in panelSystem:** Added card titled "Экспорт Т-13 — все организации" with a `<input type="month" id="exportMonth">` and "Скачать" button calling `exportAllXlsx()`. Placed after the existing backup card.

**exportAllXlsx():** Reads `document.getElementById('exportMonth').value` (falls back to `new Date().toISOString().slice(0, 7)`); navigates the browser via `window.location = '/api/superadmin/export/xlsx?month=' + encodeURIComponent(month)`. File download is handled by browser's native file-download trigger.

**Initialization:** `init()` sets `exportMonth.value = new Date().toISOString().slice(0, 7)` on page load so the picker defaults to the current month.

## Deviations from Plan

None — plan executed exactly as written. The sheet-name dedup logic uses a while-loop with numeric suffix counter (cleaner than the RESEARCH.md sketch's `list.count()` approach but semantically identical).

## Threat Mitigations Applied

| Threat | Mitigation | Location |
|--------|------------|----------|
| T-10-18 Information Disclosure / Elevation | `@require_role("superadmin")` returns 403 for all other roles; verified by test (c) | app.py superadmin_export_xlsx() |
| T-10-19 Formula injection via names | Employee names written as plain openpyxl cell values (data), not as formulas | app.py superadmin_export_xlsx() |
| T-10-20 DoS large dataset | Attendance/overrides loaded once before org loop; no per-employee DB queries inside grid loop | app.py superadmin_export_xlsx() |
| T-10-21 Empty workbook on no orgs | 'Нет данных' placeholder sheet prevents openpyxl save failure; verified by test (b) | app.py superadmin_export_xlsx() |
| T-10-22 Duplicate sheet names | while-loop dedup with numeric suffix within 31-char limit | app.py superadmin_export_xlsx() |

## Known Stubs

None. The endpoint queries live ORM models (Organization, Department, Employee, AttendanceRecord, TimesheetOverride, HolidayCalendar). The frontend navigates to the real endpoint URL.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 — Backend endpoint + tests | b17da3a | app.py, tests/test_sadm01.py |
| 2 — Frontend month picker + download button | ecce5d8 | templates/superadmin.html |

## Self-Check: PASSED
