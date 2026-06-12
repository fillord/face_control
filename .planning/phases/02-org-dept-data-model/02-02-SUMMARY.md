---
phase: 02-org-dept-data-model
plan: "02"
subsystem: data-foundation
tags: [migration, data-helpers, fcntl, lbph, json-store]
dependency_graph:
  requires: [02-01]
  provides: [ORGS_FILE, DEPTS_FILE, load_orgs, save_orgs, load_depts, save_depts, migrate.py]
  affects: [app.py, data/employees.json, data/orgs.json, data/depts.json]
tech_stack:
  added: []
  patterns: [fcntl.flock LOCK_EX on JSON writes, standalone migration script, LBPH in-memory training]
key_files:
  created:
    - migrate.py
  modified:
    - app.py
decisions:
  - "Model save_orgs/save_depts on save_users (with fcntl.flock), not save_employees (no flock)"
  - "In-place key mutation only in migration (never record reassignment) to preserve label integrity"
  - "check_label_integrity returns empty set when < 2 face images — treats all labels as unverifiable warnings"
  - "Idempotent migration: skip employees that already have org_id set"
metrics:
  duration: "~8 minutes"
  completed: "2026-06-12T05:21:24Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 02 Plan 02: Data Foundation and One-Time Migration Summary

**One-liner:** JSON org/dept load/save helpers with fcntl locking and idempotent additive migration script with LBPH label integrity check.

## What Was Built

### Task 1 — ORGS_FILE/DEPTS_FILE constants and load/save helpers (app.py)

Added to `app.py` immediately after the `USERS_FILE` constant:

- `ORGS_FILE = os.path.join(DATA_DIR, "orgs.json")`
- `DEPTS_FILE = os.path.join(DATA_DIR, "depts.json")`

Added a new section `# ─── Data helpers: Orgs / Depts ───` with four helpers:

- `load_orgs()` — returns `{}` when orgs.json absent, else the parsed dict
- `save_orgs(data)` — writes orgs.json with `fcntl.flock(LOCK_EX)` + `ensure_ascii=False`, `indent=2`
- `load_depts()` — returns `{}` when depts.json absent, else the parsed dict
- `save_depts(data)` — writes depts.json with same flock pattern

All save helpers follow the `save_users()` template (lines 52-56 of original app.py), NOT `save_employees()` which lacks flock (pre-existing gap, D-03 requirement).

### Task 2 — migrate.py standalone migration script

Created `migrate.py` at project root (no Flask import). Key behaviors:

- Module-level constants `DATA_DIR`, `FACES_DIR`, `EMPLOYEES_FILE`, `ORGS_FILE`, `DEPTS_FILE` for test monkeypatching
- `DEFAULT_SCHEDULE = {"start":"09:00","end":"18:00","work_days":[1,2,3,4,5]}`
- `check_label_integrity(employees)`: trains `cv2.face.LBPHFaceRecognizer_create()` in-memory from grayscale 200x200 JPEGs under `FACES_DIR/<emp_id>/*.jpg`; uses `getLabels().flatten()` + `int()` cast; returns empty set if < 2 images
- `run_migration()`: backs up employees.json via `shutil.copy2`, creates default org "Главная организация" and dept "Основной отдел" (idempotent — skips if files already populated), patches each employee in-place (`employees[emp_id]["org_id"] = ...`), warns on label mismatches, saves all files with fcntl, prints summary line

## Verification Results

```
tests/test_migration.py::test_migration_additive   XPASS (MIG-01 GREEN)
tests/test_migration.py::test_label_integrity_warn XPASS (MIG-02 GREEN)
```

Full suite: 1 failed (pre-existing `test_public_routes` — kiosk.html absent in worktree; unrelated to this plan), 1 passed, 9 xfailed, 9 xpassed.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | d4839a5 | feat(02-02): add ORGS_FILE/DEPTS_FILE constants and load/save helpers to app.py |
| Task 2 | 68f5df7 | feat(02-02): create migrate.py — backup, default org/dept, additive patch, label integrity |

## Deviations from Plan

None — plan executed exactly as written. The one failing test (`test_public_routes`) is a pre-existing worktree gap (kiosk.html not present in worktree templates/) that predates this plan's changes, confirmed by reproducing the failure on the base commit.

## Known Stubs

None — `migrate.py` contains no hardcoded empty values that flow to UI rendering. The default org/dept names are intentional data, not stubs.

## Threat Surface Scan

No new network endpoints or auth paths introduced. `migrate.py` is a standalone operator script with no web exposure. Threat mitigations from plan's threat register:

| Threat ID | Mitigation Applied |
|-----------|--------------------|
| T-02-T3 | In-place key mutation only; shutil.copy2 backup before patching |
| T-02-D1 | fcntl.flock(LOCK_EX) on all JSON writes in migrate.py and save_orgs/save_depts |

## Self-Check: PASSED

- `/var/www/sites/face-almgp33/.claude/worktrees/agent-a58d5fd79b8b29b9c/app.py` — FOUND, contains ORGS_FILE, DEPTS_FILE, load_orgs, save_orgs, load_depts, save_depts
- `/var/www/sites/face-almgp33/.claude/worktrees/agent-a58d5fd79b8b29b9c/migrate.py` — FOUND, contains run_migration, check_label_integrity, DEFAULT_SCHEDULE
- Commit d4839a5 — FOUND (feat: Task 1)
- Commit 68f5df7 — FOUND (feat: Task 2)
- MIG-01 and MIG-02 tests: 2 xpassed
