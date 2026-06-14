---
phase: 4
slug: export-employee-cabinet
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-13
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — `tests/` directory) |
| **Config file** | `pytest.ini` (existing) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | EXP-01..03, EMP-01..03 | — | N/A (conftest helper) | unit | `SECRET_KEY=test venv/bin/python -c "import tests.conftest as c; assert hasattr(c,'seed_attendance')"` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | EXP-01..03, EMP-01..03 | — | N/A (xfail scaffold) | unit | `pytest tests/test_export_employee.py -q` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 2 | EXP-01, EXP-02, EXP-03 | T-04-IDOR | role-scoped export enforced server-side; CSV BOM + semicolon; cross-dept blocked | unit | `pytest tests/test_export_employee.py::test_export_xlsx_dept_admin tests/test_export_employee.py::test_export_csv_bom_encoding tests/test_export_employee.py::test_export_scope_enforcement -q` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 2 | EXP-01 | — | export buttons gated by dept selection | static | `grep -q "timesheet/export/xlsx" templates/timesheet.html` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 3 | EMP-01 | T-04-EMP-AUTH | employee login admitted + emp_id column | unit | `SECRET_KEY=test venv/bin/python -c "import app; from models import User; assert hasattr(User,'emp_id'); assert 'employee' in app.ALLOWED_LOGIN_ROLES"` | ❌ W0 | ⬜ pending |
| 4-03-02 | 03 | 3 | EMP-01, EMP-02, EMP-03 | T-04-EMP-IDOR, T-04-EMP-MONTH | employee sees only own data; arrival/departure times; stats counts | unit | `pytest tests/test_export_employee.py::test_employee_cabinet_renders tests/test_export_employee.py::test_employee_tooltip_times tests/test_export_employee.py::test_employee_stats_counts -q` | ❌ W0 | ⬜ pending |
| 4-03-03 | 03 | 3 | EMP-01, EMP-02, EMP-03 | T-04-EMP-IDOR | read-only cabinet template; full file green | unit | `pytest tests/test_export_employee.py -q` | ❌ W0 | ⬜ pending |
| 4-03-04 | 03 | 3 | EMP-01 | T-04-EMP-IDOR | admin can link employee account to Employee via emp_id (RESEARCH Open Q3) | static | `grep -q "emp_id" app.py && grep -q "emp_id" templates/admin.html` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Note: the single Phase 4 test file is `tests/test_export_employee.py`, defining exactly these 6 functions (per 04-01 Task 2): `test_export_xlsx_dept_admin`, `test_export_csv_bom_encoding`, `test_export_scope_enforcement`, `test_employee_cabinet_renders`, `test_employee_tooltip_times`, `test_employee_stats_counts`. There are no `tests/test_export.py` or `tests/test_employee_cabinet.py` files.*

---

## Wave 0 Requirements

- [ ] `tests/test_export_employee.py` — 6 xfail tests covering EXP-01, EXP-02, EXP-03, EMP-01, EMP-02, EMP-03 (xlsx ZIP magic + filename, csv BOM + semicolon, dept-scope enforcement, employee cabinet render, arrival/departure tooltip times, stats counts) — created by 04-01 Task 2
- [ ] `tests/conftest.py` — add `seed_attendance()` helper that inserts `AttendanceRecord` rows via ORM — created by 04-01 Task 1
- [ ] `pip install openpyxl==3.1.5` — required before xlsx tests can pass; gated by a blocking legitimacy checkpoint and performed in 04-02 Task 1

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| XLSX opens in Excel without encoding errors | EXP-01 | Binary file inspection — Cyrillic rendering requires human review in Excel | Download .xlsx, open in LibreOffice Calc or Excel, verify Cyrillic headers display correctly |
| CSV opens correctly in Windows Excel | EXP-02 | Locale/encoding behavior differs per OS | Open .csv in Excel on Windows, verify semicolon delimiting and Cyrillic chars render |
| Tooltip shows arrival/departure on hover | EMP-02 | Browser interaction required | Log in as employee, hover over a day cell with check-in data, verify tooltip text format |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
