---
phase: 02
slug: org-dept-data-model
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-12
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pytest.ini` (exists at project root) |
| **Quick run command** | `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -x -q` |
| **Full suite command** | `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -x -q`
- **After every plan wave:** Run `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | ORG-01 | T-V4-01 | superadmin only on org write routes | unit | `pytest tests/test_org_dept.py::test_org_crud -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | ORG-02 | T-V4-02 | org_admin blocked from other org's depts | unit | `pytest tests/test_org_dept.py::test_dept_crud_scope -x -q` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | ORG-03 | T-V4-03 | dept_admin blocked from other dept employees | unit | `pytest tests/test_org_dept.py::test_employee_dept_scope -x -q` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | ORG-04 | T-V4-02 | org_admin reassign within own org only | unit | `pytest tests/test_org_dept.py::test_employee_reassign -x -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | MIG-01 | — | label field preserved verbatim after migration | unit | `pytest tests/test_migration.py::test_migration_additive -x -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | MIG-02 | — | warn-only on label mismatch, no abort | unit | `pytest tests/test_migration.py::test_label_integrity_warn -x -q` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | T13-06 | T-V5-01 | schedule validated HH:MM format, work_days 1-7 | unit | `pytest tests/test_org_dept.py::test_schedule_update -x -q` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | DASH-01 | — | superadmin stats endpoint returns correct counts | unit | `pytest tests/test_org_dept.py::test_superadmin_stats -x -q` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 2 | DASH-02 | T-V4-04 | dept_admin cannot see other dept attendance | unit | `pytest tests/test_org_dept.py::test_dept_attendance_scope -x -q` | ❌ W0 | ⬜ pending |
| 02-05-01 | 05 | 3 | KIOSK-01 | — | recognize returns dept_name; null when dept missing | unit | `pytest tests/test_org_dept.py::test_recognize_dept_name -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_org_dept.py` — stubs for ORG-01 through ORG-04, T13-06, DASH-01, DASH-02, KIOSK-01
- [ ] `tests/test_migration.py` — stubs for MIG-01, MIG-02
- [ ] `tests/conftest.py` extension — add `ORGS_FILE` and `DEPTS_FILE` to `tmp_data` fixture monkeypatches

*Existing infrastructure (2 passed + 8 xpassed) must remain green after Wave 0 additions.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Kiosk shows dept name on confirmation screen | KIOSK-01 | UI rendering requires browser + live face recognition | 1. Run migrate.py; 2. Start app; 3. Use kiosk with registered face; 4. Confirm dept name appears below employee name |
| migrate.py backup file created before patching | MIG-01 | File system side-effect, not Flask API | Run migrate.py; verify `data/employees_backup_*.json` exists before and `data/employees.json` has org_id/dept_id/schedule |
| Login redirect routes each role correctly | D-11 | Browser session behavior | Login as superadmin → confirm lands on /superadmin; as org_admin → /org_admin; as dept_admin → /dept_admin |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
