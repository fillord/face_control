---
phase: 6
slug: sqlite-migration
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-13
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (already installed) |
| **Config file** | `tests/conftest.py` (rewritten in Plan 02 Task 2) |
| **Quick run command** | `SECRET_KEY=test /var/www/sites/face-almgp33/venv/bin/python -m pytest tests/ -x -q` |
| **Full suite command** | `SECRET_KEY=test /var/www/sites/face-almgp33/venv/bin/python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `SECRET_KEY=test /var/www/sites/face-almgp33/venv/bin/python -m pytest tests/ -x -q`
- **After every plan wave:** Run `SECRET_KEY=test /var/www/sites/face-almgp33/venv/bin/python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 0 | DB-01 | T-06-SC | package legitimacy (audited) | install | `pip show flask-sqlalchemy \| grep "Version: 3.1.1"` | ✅ | ⬜ pending |
| 06-01-02 | 01 | 0 | DB-01, DB-02 | T-06-01, T-06-02 | label non-autoincrement; event_type present (D-01) | unit | `python -c "import models; ..."` (label autoincrement False + event_type col) | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 0 | DB-02 | — | migration test scaffold collects | unit | `pytest tests/test_sqlite_migration.py -q` (skips OK) | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | DB-03, DB-05 | — | app boots with SECRET_KEY+DATABASE_URL only | integration | `SECRET_KEY=test pytest tests/ -x -q` | ✅ | ⬜ pending |
| 06-02-02 | 02 | 1 | DB-03 | — | in-memory SQLite test isolation | integration | `SECRET_KEY=test pytest tests/ -x -q` | ✅ | ⬜ pending |
| 06-03-01 | 03 | 2 | DB-01 | — | require_role/user/employee/org/dept ORM | integration | `SECRET_KEY=test pytest tests/ -x -q` | ✅ | ⬜ pending |
| 06-03-02 | 03 | 2 | DB-01 | — | append_log → LogEntry insert + 10k cap | integration | `SECRET_KEY=test pytest tests/ -x -q` | ✅ | ⬜ pending |
| 06-03-03 | 03 | 2 | DB-01, DB-04 | — | helpers/_FILE constants/fcntl removed | static + integration | `grep -c fcntl app.py` (==0) + `SECRET_KEY=test pytest tests/ -x -q` | ✅ | ⬜ pending |
| 06-04-01 | 04 | 3 | DB-01 | T-06-14 | attendance/recognition ORM + event_type (D-01) | integration | `SECRET_KEY=test pytest tests/test_timesheet.py tests/test_migration.py -q` + grep event_type literals | ✅ | ⬜ pending |
| 06-04-02 | 04 | 3 | DB-01, DB-03 | — | zero JSON store I/O in app.py | static + integration | grep (no `*_FILE`/load_/save_) + `SECRET_KEY=test pytest tests/ -q` | ✅ | ⬜ pending |
| 06-04-03 | 04 | 3 | DB-02 | T-06-11, T-06-12 | idempotent migration + label preservation | unit | `SECRET_KEY=test pytest tests/test_sqlite_migration.py -q` (now active) | ❌ W0 | ⬜ pending |
| 06-04-CK | 04 | 3 | DB-02, DB-05 | T-06-13 | real-data migration + live SQLite check-in | manual (checkpoint) | human-verify per plan 04 checkpoint steps | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*File Exists ❌ W0 = test target created during Wave 0 (Plan 01) / activated in Plan 04 — covered, not a gap.*

---

## Wave 0 Requirements

- [ ] `flask-sqlalchemy==3.1.1` — install via pip (Plan 01 Task 1; not yet in venv)
- [ ] `models.py` with all 9 ORM model classes — Plan 01 Task 2 defines schema (incl. AttendanceRecord.event_type, D-01; Employee.label non-autoincrement, D-14) before routes are touched
- [ ] `tests/test_sqlite_migration.py` scaffold — Plan 01 Task 3 (DB-02 idempotency, zero-data-loss, label preservation), activated in Plan 04 Task 3

*Existing pytest infrastructure (tests/test_auth, test_rbac, test_org_dept, test_timesheet, test_migration, test_kiosk_token, test_migrate_tokens, test_org_settings, test_reg_token) covers all route-level requirements once models are defined and conftest is rewritten (Plan 02).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `migrate_to_sqlite.py` zero-data-loss run | DB-02 | Requires production JSON files | Run `python migrate_to_sqlite.py` against real `data/` files; verify row counts match JSON entry counts (Plan 04 checkpoint steps 2–4) |
| Idempotent re-run | DB-02 | Requires production data + second invocation | Run migration twice; confirm zero new rows, no error (Plan 04 checkpoint step 3) |
| Label preservation against real data | D-14 | Requires real employee labels | Spot-check `employee.label` in app.db vs employees.json (Plan 04 checkpoint step 4) |
| event_type populated on live check-in | D-01 | Requires live face check-in | After a kiosk check-in, confirm latest `attendance_record.event_type` is 'check_in'/'check_out' (Plan 04 checkpoint step 5) |
| PM2 restart with new DB backend | DB-05 | Requires live process | Start app with only SECRET_KEY+DATABASE_URL; open kiosk, register a check-in; verify attendance recorded in `data/app.db` (Plan 04 checkpoint step 5) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or are explicitly covered by a Wave 0 dependency / human checkpoint
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (only the final 06-04-CK checkpoint is manual; every code task before it has an automated command)
- [x] Wave 0 covers flask-sqlalchemy install, models definition (incl. event_type D-01), and migration test scaffold
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] Per-task map matches actual plan task structure (Plan 01: T1/2/3; Plan 02: T1/2; Plan 03: T1/2/3; Plan 04: T1/2/3 + checkpoint)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
