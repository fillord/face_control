---
phase: 04-export-employee-cabinet
plan: "01"
subsystem: test-infrastructure
tags: [testing, xfail-scaffold, conftest, attendance, export, employee-cabinet]
dependency_graph:
  requires: []
  provides:
    - tests/test_export_employee.py (6 xfail tests for EXP-01..03, EMP-01..03)
    - tests/conftest.py seed_attendance() helper
  affects:
    - 04-02-PLAN.md (export routes must make EXP-01..03 green)
    - 04-03-PLAN.md (employee cabinet must make EMP-01..03 green)
tech_stack:
  added: []
  patterns:
    - seed_* ORM helper pattern (lazy import + app_context + db.session.add)
    - xfail scaffold with strict=False for requirement-to-test mapping
key_files:
  created:
    - tests/test_export_employee.py
  modified:
    - tests/conftest.py
decisions:
  - seed_attendance deduplicates by explicit id when provided; auto-increments when id absent
  - emp_id on User dict in seed_users calls is silently ignored (User.emp_id column added in 04-03)
  - EXP-03 accepts both 200 (forced to own dept) and 403 (direct rejection) outcomes
metrics:
  duration: "~3 minutes"
  completed: "2026-06-14"
  tasks_completed: 2
  files_changed: 2
---

# Phase 04 Plan 01: Test Scaffold (Export & Employee Cabinet) Summary

**One-liner:** xfail test scaffold for 6 Phase 4 requirements (EXP-01..03, EMP-01..03) plus seed_attendance() ORM helper for AttendanceRecord fixtures.

## What Was Built

### Task 1: seed_attendance() helper (tests/conftest.py)

Added `seed_attendance(tmp_data, records_list)` function following the existing `seed_employees` pattern:

- Accepts `tmp_data` (ignored) and a list of record dicts
- Imports `db, AttendanceRecord` lazily inside `with _app.app.app_context()`
- Deduplicates: when `id` key is provided, calls `AttendanceRecord.query.get(rec["id"])` and skips if found
- When no `id` provided, lets the autoincrement PK assign automatically
- Maps `emp_id`, `date`, `check_in_time`, `check_out_time`, `event_type` fields
- Calls `db.session.commit()` after all inserts
- No existing helpers modified

### Task 2: xfail test scaffold (tests/test_export_employee.py)

Created 6 test functions, all decorated `@pytest.mark.xfail(reason="implemented in 04-02/04-03", strict=False)`:

| Test | Requirement | Contract |
|------|-------------|---------|
| test_export_xlsx_dept_admin | EXP-01 | GET /timesheet/export/xlsx returns 200, b"PK" magic, T13_ in Content-Disposition |
| test_export_csv_bom_encoding | EXP-02 | GET /timesheet/export/csv returns 200, UTF-8 BOM prefix, semicolon in body |
| test_export_scope_enforcement | EXP-03 | dept_admin cross-dept export returns 200 (forced) or 403; dept-B names absent if 200 |
| test_employee_cabinet_renders | EMP-01 | GET /employee returns 200, "Мой табель" in body |
| test_employee_tooltip_times | EMP-02 | GET /employee contains "Приход" and "09:05" from AttendanceRecord |
| test_employee_stats_counts | EMP-03 | GET /employee contains "Опоздания", "Отсутствия", "Ранний уход" stat labels |

## Verification Results

```
tests/test_export_employee.py: 6 xfailed, 0 errors
tests/ (full suite): 34 passed, 15 xfailed, 20 xpassed, 0 collection errors
```

## Deviations from Plan

None — plan executed exactly as written.

The only notable design decision: `seed_users` calls in the test file include `"emp_id": "emp-1"` in the dict, but the current `User` model does not yet have an `emp_id` column (that schema change is in plan 04-03). The existing `seed_users` helper maps only the known User fields (`id`, `username`, `password_hash`, `role`, `active`, `org_id`, `dept_id`) and silently ignores `emp_id`. This is consistent with how previous plans have seeded data — the field will be consumed correctly once 04-03 adds `User.emp_id`.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: seed_attendance() | 19d7369 | tests/conftest.py |
| Task 2: xfail test scaffold | e53f7d7 | tests/test_export_employee.py |

## Self-Check: PASSED

- FOUND: tests/test_export_employee.py
- FOUND: tests/conftest.py (with seed_attendance)
- FOUND: .planning/phases/04-export-employee-cabinet/04-01-SUMMARY.md
- FOUND commit 19d7369 (seed_attendance helper)
- FOUND commit e53f7d7 (xfail test scaffold)
- Test run: 6 xfailed, 0 errors
