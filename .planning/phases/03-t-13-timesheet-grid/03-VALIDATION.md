---
phase: 3
slug: t-13-timesheet-grid
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pytest.ini` (exists — `testpaths = tests`) |
| **Quick run command** | `python -m pytest tests/test_timesheet.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_timesheet.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01 | 01 | 0 | T13-01..T13-08, DASH-04 | — | N/A | unit/integration | `pytest tests/test_timesheet.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02 | 01 | 1 | T13-02 | — | N/A | unit | `pytest tests/test_timesheet.py::test_compute_symbol_all_cases -x` | ❌ W0 | ⬜ pending |
| 03-03 | 01 | 1 | T13-03 | — | N/A | unit | `pytest tests/test_timesheet.py::test_symbol_auto_derivation -x` | ❌ W0 | ⬜ pending |
| 03-04 | 01 | 1 | T13-04 | — | N/A | unit | `pytest tests/test_timesheet.py::test_symbol_late -x` | ❌ W0 | ⬜ pending |
| 03-05 | 01 | 1 | T13-05 | — | N/A | unit | `pytest tests/test_timesheet.py::test_symbol_early_and_combined -x` | ❌ W0 | ⬜ pending |
| 03-06 | 01 | 1 | T13-07 | — | N/A | unit | `pytest tests/test_timesheet.py::test_totals_row -x` | ❌ W0 | ⬜ pending |
| 03-07 | 01 | 1 | T13-08 | — | N/A | unit | `pytest tests/test_timesheet.py::test_kz_holidays -x` | ❌ W0 | ⬜ pending |
| 03-08 | 02 | 2 | T13-01 | — | N/A | integration | `pytest tests/test_timesheet.py::test_timesheet_renders -x` | ❌ W0 | ⬜ pending |
| 03-09 | 02 | 2 | D-05 | T-03-privesc | dept_admin 403 on override for out-of-scope emp | integration | `pytest tests/test_timesheet.py::test_override_scope_403 -x` | ❌ W0 | ⬜ pending |
| 03-10 | 02 | 2 | D-08 | T-03-scope | dept_admin 403 when dept_id param != session | integration | `pytest tests/test_timesheet.py::test_timesheet_scope_isolation -x` | ❌ W0 | ⬜ pending |
| 03-11 | 03 | 3 | DASH-04 | — | N/A | integration | `pytest tests/test_timesheet.py::test_dash04_summary -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_timesheet.py` — stubs for T13-01..T13-08, DASH-04, D-05, D-08 (all tests listed above)
- [ ] `tests/conftest.py` — add `TIMESHEET_OVERRIDES_FILE` monkeypatch using existing `hasattr()` guard pattern (alongside ORGS_FILE/DEPTS_FILE guards)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| T-13 grid visually correct with real browser (column widths, Cyrillic symbols readable, cell highlight on hover) | T13-01 | UI render quality not verifiable via pytest | Load /timesheet in browser, check grid renders with correct layout |
| KZ public holiday dates visually correct for 2024/2025/2026 | T13-08 | Dates require human verification against egov.kz (LOW confidence source) | Cross-check hard-coded KZ_HOLIDAYS dict against https://egov.kz |
| Inline override dropdown shows and saves correctly | D-03 | JS interaction requires browser | Click a work-day cell as dept_admin, pick Б, verify cell updates without page reload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
