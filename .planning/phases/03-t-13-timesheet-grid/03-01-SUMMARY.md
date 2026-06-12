---
phase: 03-t-13-timesheet-grid
plan: "01"
subsystem: test-scaffold
tags: [tdd, scaffold, xfail, timesheet, t13]
dependency_graph:
  requires: []
  provides:
    - tests/test_timesheet.py — 11 xfail T-13 tests covering T13-01..T13-08, DASH-04, D-05, D-08, V5
    - tests/conftest.py — TIMESHEET_OVERRIDES_FILE monkeypatch guard
  affects:
    - tests/conftest.py
tech_stack:
  added: []
  patterns:
    - xfail test scaffold following existing test_org_dept.py pattern
    - hasattr guard in conftest.py following ORGS_FILE/DEPTS_FILE precedent
key_files:
  created:
    - tests/test_timesheet.py
  modified:
    - tests/conftest.py
decisions:
  - strict=False on all xfail decorators so tests report xfail (not error) until implementation lands
  - Unit tests import compute_symbol/compute_employee_totals/get_holidays_set/is_holiday_year_missing directly; guarded by hasattr assertions
  - Integration tests use client + session_transaction fixture pattern from test_org_dept.py
  - No stub/placeholder assertions — all tests assert real T-13 behavior contracts
metrics:
  duration: "4m 6s"
  completed: "2026-06-12"
  tasks_completed: 2
  files_changed: 2
---

# Phase 03 Plan 01: T-13 Test Scaffold Summary

Wave 0 xfail test scaffold for the entire T-13 timesheet phase, plus the conftest monkeypatch guard for the new override file. Every subsequent wave has a concrete `pytest` command to flip from xfail to pass.

## What Was Built

**conftest.py guard (Task 1):** Added `TIMESHEET_OVERRIDES_FILE` hasattr monkeypatch guard in the `tmp_data` fixture, immediately after the existing `DEPTS_FILE` guard. Uses the identical pattern. The constant does not exist in `app.py` until plan 03-02; the `hasattr()` guard prevents collection errors in the meantime.

**test_timesheet.py (Task 2):** Created 11 xfail test functions covering every T-13 requirement from the validation map. Each test asserts real behavior using computed values — no `assert True` or placeholder stubs.

| Test | Requirement | Tests |
|------|-------------|-------|
| test_compute_symbol_all_cases | T13-02 | Я/О/У/ОУ/В/НН/Б/К + override wins |
| test_symbol_auto_derivation | T13-03 | Я for on-time; НН for absent work day; В for Saturday |
| test_symbol_late | T13-04 | 09:16→О; 09:15→Я (boundary exclusive) |
| test_symbol_early_and_combined | T13-05 | 17:44→У; late+early→ОУ |
| test_totals_row | T13-07 | days_worked/hours/absences/late/vac_sick aggregation |
| test_kz_holidays | T13-08 | 2025-01-01 in set; year 2099 missing; В on holiday work day |
| test_timesheet_renders | T13-01 | GET /timesheet returns 200, employee name, "Итого" |
| test_override_scope_403 | D-05 | dept_admin 403 for dept-B employee override |
| test_timesheet_scope_isolation | D-08 | dept_admin cannot view dept-B via URL param |
| test_dash04_summary | DASH-04 | /org_admin?summary_month shows "Сводка по отделам" + % |
| test_override_invalid_symbol_422 | V5 | Symbol "Я" returns 422 (not in MANUAL_SYMBOLS) |

## Verification Results

```
$ python -m pytest tests/test_timesheet.py -q
xxxxxxxxxxx                                                              [100%]
11 xfailed in 0.58s

$ python -m pytest tests/ -q
31 passed, 14 xfailed, 15 xpassed in 21.43s
```

Full suite shows no regressions from the conftest.py change.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| a57f888 | chore | Add TIMESHEET_OVERRIDES_FILE monkeypatch guard to conftest |
| 4214392 | test | Add failing/xfail test scaffold for T-13 timesheet (11 tests) |

## Deviations from Plan

None — plan executed exactly as written. Both tasks completed in sequence with no blocking issues, deviation rules not triggered.

## Known Stubs

None — all 11 tests assert real behavior. No test uses `assert True` or placeholder values.

## Threat Flags

No new security-relevant surface introduced. This plan creates test-only files; no production code, routes, or data schemas modified.

## Self-Check: PASSED

- FOUND: tests/test_timesheet.py
- FOUND: TIMESHEET_OVERRIDES_FILE in conftest.py
- FOUND: commit a57f888 (chore - conftest guard)
- FOUND: commit 4214392 (test scaffold)
