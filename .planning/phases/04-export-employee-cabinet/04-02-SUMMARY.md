---
phase: 04-export-employee-cabinet
plan: "02"
subsystem: export
tags: [export, xlsx, csv, openpyxl, timesheet, rbac, scope-enforcement]
dependency_graph:
  requires:
    - 04-01 (xfail test scaffold for EXP-01..03)
  provides:
    - GET /timesheet/export/xlsx (EXP-01)
    - GET /timesheet/export/csv (EXP-02, EXP-03)
    - Скачать XLSX / Скачать CSV buttons in timesheet.html
  affects:
    - 04-03-PLAN.md (employee cabinet — EMP-01..03 still xfail)
tech_stack:
  added:
    - openpyxl 3.1.5 (Excel generation via Workbook/Font/Alignment/get_column_letter)
  patterns:
    - _resolve_export_scope() shared helper mirrors /timesheet 3-branch scope resolution
    - BytesIO + buf.seek(0) before send_file (Flask 3 streaming pattern)
    - utf-8-sig encoding codec for BOM (no hand-written b'\xef\xbb\xbf')
    - re.sub() for safe filename construction (T13_<dept>_<YYYY-MM>)
key_files:
  created: []
  modified:
    - app.py (export routes + imports + MONTHS_RU constant)
    - templates/timesheet.html (Скачать XLSX / Скачать CSV buttons + .btn-secondary CSS)
    - tests/test_export_employee.py (xfail markers removed from 3 EXP-* tests)
decisions:
  - MONTHS_RU hardcoded as module constant — no locale dependency (RESEARCH Open Question 2)
  - Shared _resolve_export_scope() helper to avoid duplication between xlsx/csv routes
  - dept_admin scope always forced from session["dept_id"]; param silently ignored (T-04-IDOR)
  - Export buttons gated with {% if dept_id %} — hidden when no dept selected (D-02)
  - send_file() uses download_name= (Flask 3 API; not legacy attachment_filename=)
metrics:
  duration: "~4 minutes"
  completed: "2026-06-14"
  tasks_completed: 2
  files_changed: 3
---

# Phase 04 Plan 02: Export Vertical Slice Summary

**One-liner:** T-13 XLSX (openpyxl merged headers) and UTF-8 BOM semicolon CSV export routes with role-scoped dept isolation and download buttons in the timesheet selector bar.

## What Was Built

### Task 1: openpyxl install + export routes (app.py + tests)

Installed openpyxl==3.1.5 into the project venv (legitimacy approved in checkpoint).

Added to `app.py` imports:
- `import re, csv, io` and `from io import BytesIO`
- `send_file` added to the `from flask import ...` line
- `from openpyxl import Workbook`, `from openpyxl.styles import Font, Alignment`, `from openpyxl.utils import get_column_letter`

Added `MONTHS_RU` module-level constant (Russian month names 1-12) near other module constants.

Added two helper functions:
- `_resolve_export_scope()` — shared scope/data resolution that mirrors the /timesheet route's 3-branch logic verbatim: dept_admin forced to session dept; org_admin validates dept.org_id == session_org_id (403 otherwise); superadmin uses any dept_id param. Also loads Employee, AttendanceRecord, TimesheetOverride data via ORM and returns the full context tuple. Returns `(None, response_tuple)` on error so callers can propagate immediately.
- `_build_export_grid()` — builds `(emp_id, name, symbols, totals)` rows from scoped employees using `compute_symbol` and `compute_employee_totals` (export needs raw symbol strings, not cell dicts).

Added two GET routes:
- `GET /timesheet/export/xlsx` (`@require_role("dept_admin", "org_admin", "superadmin")`) — builds an openpyxl Workbook with merged Row 1 title (bold center), merged Row 2 subtitle, Row 3 bold headers, employee rows with day symbols and 5 totals columns (Я/Ч/П-НН/О/Б-К). Column A width 24, day columns width 4. Saves to BytesIO, seeks to 0, returns via `send_file(..., download_name=f"T13_{safe_dept}_{month_str}.xlsx", as_attachment=True)`.
- `GET /timesheet/export/csv` (`@require_role(...)`) — writes title row + header row + employee rows to `io.StringIO` with `csv.writer(delimiter=";")`, encodes with `"utf-8-sig"` codec (BOM automatic), returns via `send_file(..., mimetype="text/csv")`.

Removed `@pytest.mark.xfail(reason="implemented in 04-02/04-03", strict=False)` decorators from exactly three tests: `test_export_xlsx_dept_admin`, `test_export_csv_bom_encoding`, `test_export_scope_enforcement`. The three EMP-* tests retain their xfail markers.

### Task 2: Download buttons in timesheet.html

Added `.btn-secondary` CSS rule to the `<style>` block (after `.btn-primary:hover`):
- White background, `border: 1px solid #cfd8dc`, `border-radius: 8px`, `padding: 8px 16px`, `color: #546e7a`, `font-size: 13px`, `font-weight: 600`, `text-decoration: none`, `display: inline-flex`, `align-items: center`, `height: 36px`; hover: `background: #f4f6fb`

Added two anchor buttons immediately after the "Показать табель" `.btn-primary` submit button in the `.selector-bar` form, wrapped in `{% if dept_id %}...{% endif %}`:
- `<a href="/timesheet/export/xlsx?dept_id={{ dept_id }}&amp;month={{ month_str }}" class="btn-secondary">Скачать XLSX</a>`
- `<a href="/timesheet/export/csv?dept_id={{ dept_id }}&amp;month={{ month_str }}" class="btn-secondary">Скачать CSV</a>`

## Verification Results

```
tests/test_export_employee.py: 3 passed, 3 xfailed, 0 errors
- test_export_xlsx_dept_admin: PASSED (EXP-01)
- test_export_csv_bom_encoding: PASSED (EXP-02)
- test_export_scope_enforcement: PASSED (EXP-03)
- test_employee_cabinet_renders: xfailed (EMP-01, awaiting 04-03)
- test_employee_tooltip_times: xfailed (EMP-02, awaiting 04-03)
- test_employee_stats_counts: xfailed (EMP-03, awaiting 04-03)
```

Manual acceptance criteria verified:
- `venv/bin/python -c "import openpyxl; print(openpyxl.__version__)"` → 3.1.5
- `import re` and `send_file` present in app.py imports
- `from openpyxl import Workbook` present
- `def export_timesheet_xlsx` and `def export_timesheet_csv` both decorated `@require_role(...)`
- `buf.seek(0)` called before `send_file` in xlsx route
- csv route uses `delimiter=";"` and `encode("utf-8-sig")`
- dept_admin scope forced from `session["dept_id"]` (param ignored)
- timesheet.html contains both export hrefs with `dept_id={{ dept_id }}` and `month={{ month_str }}`
- Both anchors inside `{% if dept_id %}` guard
- `.btn-secondary` rule present in `<style>` block
- Grid `<table>` markup and existing `.btn-primary` button unchanged

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Export routes are fully wired: scope resolution, ORM data loading, xlsx/csv generation, and file download are all live code paths that function end-to-end.

## Threat Flags

No new threat surface beyond what the plan's `<threat_model>` already covers:
- T-04-IDOR mitigated: dept_admin scope forced from session in both routes
- T-04-VAL mitigated: month param range-checked with try/except (1-12, 2000-2099)
- T-04-SC mitigated: openpyxl install was blocked behind legitimacy checkpoint, pinned to ==3.1.5

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: openpyxl install + export routes | f0b2fcb | app.py, tests/test_export_employee.py |
| Task 2: Download buttons | 6b366d5 | templates/timesheet.html |

## Self-Check: PASSED

- FOUND: app.py (contains def export_timesheet_xlsx, def export_timesheet_csv)
- FOUND: templates/timesheet.html (contains timesheet/export/xlsx, timesheet/export/csv, btn-secondary)
- FOUND: tests/test_export_employee.py (3 EXP-* xfail removed, 3 EMP-* xfail retained)
- FOUND commit f0b2fcb (export routes)
- FOUND commit 6b366d5 (download buttons)
- Test run: 3 passed, 3 xfailed, 0 errors
