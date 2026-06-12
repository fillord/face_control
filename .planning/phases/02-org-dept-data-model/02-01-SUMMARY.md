---
phase: 02-org-dept-data-model
plan: 01
subsystem: tests
tags: [test-scaffold, xfail, conftest, migration, org-dept, wave-0]
dependency_graph:
  requires: []
  provides:
    - tests/conftest.py:seed_orgs
    - tests/conftest.py:seed_depts
    - tests/conftest.py:seed_employees
    - tests/conftest.py:ORGS_FILE/DEPTS_FILE monkeypatches
    - tests/test_org_dept.py:test_org_crud
    - tests/test_org_dept.py:test_dept_crud_scope
    - tests/test_org_dept.py:test_employee_dept_scope
    - tests/test_org_dept.py:test_employee_reassign
    - tests/test_org_dept.py:test_schedule_update
    - tests/test_org_dept.py:test_superadmin_stats
    - tests/test_org_dept.py:test_dept_attendance_scope
    - tests/test_org_dept.py:test_recognize_dept_name
    - tests/test_migration.py:test_migration_additive
    - tests/test_migration.py:test_label_integrity_warn
  affects: []
tech_stack:
  added: []
  patterns:
    - xfail with ImportError guard for pre-existence safety
    - hasattr guard for monkeypatching future app.py symbols
    - session_transaction() injection for authenticated Flask test clients
key_files:
  created:
    - tests/test_org_dept.py
    - tests/test_migration.py
  modified:
    - tests/conftest.py
decisions:
  - "test_public_routes pre-existing failure in worktree: kiosk.html is untracked in main repo; not in worktree git history; documented as pre-existing, out of scope"
  - "test_recognize_dept_name uses direct load_depts() call instead of full recognize() flow: face decoding requires real LBPH model not available in unit tests; asserting schema contract via helper lookup is the correct approach per RESEARCH"
  - "test_label_integrity_warn checks both stdout WARN and return value: migrate.py may implement warnings either way per D-06"
metrics:
  duration: "5m"
  completed_date: "2026-06-12"
  tasks_completed: 3
  files_modified: 3
---

# Phase 02 Plan 01: Wave 0 Test Scaffold Summary

**One-liner:** xfail test scaffold for all 10 Phase 2 requirements with ORGS_FILE/DEPTS_FILE isolated conftest extension, migration try/except guards, and session_transaction injection pattern.

## What Was Built

Extended `tests/conftest.py` with org/dept fixture isolation and three new seed helpers. Created `tests/test_org_dept.py` with 8 named failing tests covering ORG-01 through ORG-04, T13-06, DASH-01, DASH-02, and KIOSK-01. Created `tests/test_migration.py` with 2 named failing tests covering MIG-01 and MIG-02. All 10 tests are `@pytest.mark.xfail(strict=False)` and serve as the GREEN target for plans 02-02 through 02-05.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend conftest.py with org/dept isolation and seed helpers | dbcfde9 | tests/conftest.py |
| 2 | Write failing requirement tests for org/dept CRUD, schedule, dashboards, kiosk | 1e028ed | tests/test_org_dept.py |
| 3 | Write failing migration tests (MIG-01, MIG-02) | 9e1103c | tests/test_migration.py |

## Verification Results

- `pytest tests/ --collect-only -q` -> 20 tests collected, 0 collection errors
- `pytest tests/test_org_dept.py -q` -> 8 xfailed
- `pytest tests/test_migration.py -q` -> 2 xfailed
- Phase 1 baseline: 1 passed + 6 xpassed (unchanged); pre-existing `test_public_routes` failure documented below

## Deviations from Plan

### Pre-existing Issues (out of scope)

**1. [Pre-existing] test_public_routes fails in worktree**
- **Found during:** Task 3 overall verification
- **Issue:** `kiosk.html`, `login.html`, and `register.html` are untracked files in the main repo not committed to git history. The worktree's `templates/` directory does not contain these files. `test_public_routes` calls `GET /` which triggers `render_template("kiosk.html")` and raises `TemplateNotFound`.
- **Disposition:** Pre-existing. This test was failing before any of this plan's changes. Confirmed by running Phase 1 tests against the base commit. Out of scope per deviation rule scope boundary.
- **Deferred:** Untracked template files should be committed in a future plan or the test made template-agnostic.

### Auto-selected Implementation Approaches

**1. test_recognize_dept_name uses load_depts() lookup instead of full recognize() HTTP flow**
- **Reason:** Full face recognition requires a trained LBPH model and real JPEG face images, impractical in a unit test. The RESEARCH.md explicitly acknowledges this and recommends direct helper assertion.
- **Approach:** Test asserts `hasattr(_app, "load_depts")`, calls it, and verifies the dept name lookup path. Also asserts `/api/recognize` does not return 302 (kiosk stays public).

## Known Stubs

None. All test assertions reference real endpoint contracts from RESEARCH.md Code Examples. No placeholder values or TODO assertions that block the plan's goal.

## Threat Flags

None. This plan creates only test files. No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. Threat mitigation T-02-T1 implemented: all test path constants redirected to tmp_path via monkeypatch.

## Self-Check

- [x] tests/conftest.py contains `hasattr(_app, "ORGS_FILE")` and `hasattr(_app, "DEPTS_FILE")`
- [x] tests/conftest.py contains `def seed_orgs(`, `def seed_depts(`, `def seed_employees(`
- [x] tests/test_org_dept.py defines all 8 named functions
- [x] tests/test_migration.py defines test_migration_additive and test_label_integrity_warn
- [x] All 10 tests carry `@pytest.mark.xfail`
- [x] 20 tests collected with zero collection errors
- [x] Commits dbcfde9, 1e028ed, 9e1103c verified in git log
