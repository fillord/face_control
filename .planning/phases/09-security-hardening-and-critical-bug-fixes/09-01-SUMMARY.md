---
phase: 09-security-hardening-and-critical-bug-fixes
plan: "01"
subsystem: app-core
tags: [bug-fix, security, reliability, performance, late-detection, holidays, health-check, index]
dependency_graph:
  requires: []
  provides:
    - schedule-aware-late-detection
    - kz-holidays-2027
    - session-cookie-security-flags
    - dept-name-lookup
    - health-endpoint
    - attendance-composite-index
  affects:
    - app.py
    - models.py
tech_stack:
  added: []
  patterns:
    - "_time_threshold() reused for per-employee late threshold (recognize + get_stats)"
    - "dept_name_map cached once before loop to avoid N+1 Department queries"
    - "idempotent DDL migration pattern (DROP INDEX IF EXISTS / CREATE INDEX IF NOT EXISTS)"
key_files:
  created: []
  modified:
    - app.py
    - models.py
decisions:
  - "BUG-01/02: _time_threshold(schedule.start, 15) used in both recognize() and get_stats(); default 09:00 yields 09:15:00 grace when no schedule is set"
  - "BUG-03: dept_name_map built once via Department.query.filter_by(org_id=org_id).all() before the dept loop"
  - "REL-02: KZ_HOLIDAYS[2027] mirrors 2026 recurring dates exactly"
  - "SEC-04: SESSION_COOKIE_SECURE/HTTPONLY/SAMESITE=Lax added to Flask config block; nginx terminates SSL"
  - "REL-01: /health is public (no @require_role), wraps SELECT 1 in try/except, returns 200/503"
  - "PERF-01: composite index ix_attendance_emp_date replaces two column-level indexes; startup migration uses DROP INDEX IF EXISTS + CREATE INDEX IF NOT EXISTS for existing DBs"
metrics:
  duration_minutes: 25
  completed_date: "2026-06-26"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 2
---

# Phase 09 Plan 01: Security Hardening and Critical Bug Fixes — Summary

**One-liner:** Schedule-aware late detection via _time_threshold, KZ 2027 holidays, department name lookup, /health endpoint, session cookie hardening, and AttendanceRecord composite index.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Schedule-aware late detection (BUG-01, BUG-02) | 8922eb6 | app.py |
| 2 | Real dept names, KZ 2027, cookie flags (BUG-03, REL-02, SEC-04) | dac65a8 | app.py |
| 3 | /health endpoint + composite index (REL-01, PERF-01) | 27fe8e6 | app.py, models.py |

## What Was Built

### Task 1 — Schedule-aware late detection (BUG-01, BUG-02)

In `recognize()` (app.py ~2980): replaced `is_late = now > "09:00:00"` with:
```python
schedule = emp_dict.get("schedule", {})
start = schedule.get("start", "09:00")
is_late = now > _time_threshold(start, 15)
```

In `get_stats()` (app.py ~3197): replaced `if check_in > "09:00:00":` with:
```python
start = employees[eid]["schedule"].get("start", "09:00")
if check_in > _time_threshold(start, 15):
```

Both sites now derive the late threshold from the employee's own schedule start + 15-minute grace period. The existing `_time_threshold()` helper (line 244) is reused — no reimplementation.

### Task 2 — Real dept names, KZ 2027, cookie flags (BUG-03, REL-02, SEC-04)

**BUG-03:** `compute_dept_summary()` now builds `dept_name_map = {d.id: d.name for d in Department.query.filter_by(org_id=org_id).all()}` before the dept loop and replaces `dept_name = dept_id` with `dept_name = dept_name_map.get(dept_id, dept_id)`.

**REL-02:** Added `KZ_HOLIDAYS[2027]` with the full recurring Kazakhstan holiday list (Jan 1-2, Jan 7, Mar 8, Mar 21-23, May 1, May 7, May 9, Jul 6, Aug 30, Oct 25, Dec 1, Dec 16-17).

**SEC-04:** Three session cookie security flags added to Flask config block:
```python
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
```

### Task 3 — /health endpoint + AttendanceRecord composite index (REL-01, PERF-01)

**REL-01:** Public `GET /health` route added (no auth). Wraps `db.session.execute(text("SELECT 1"))` in try/except; returns `{"status": "ok", "db": "connected"}` (200) on success, `{"status": "error", "db": "unavailable"}` (503) on failure.

**PERF-01 (models.py):** Added `Index` to imports; removed `index=True` from `emp_id` and `date` columns; added `__table_args__ = (Index("ix_attendance_emp_date", "emp_id", "date"),)` to `AttendanceRecord`.

**PERF-01 (app.py startup):** Idempotent migration block added after `db.create_all()`:
```python
DROP INDEX IF EXISTS ix_attendance_record_emp_id
DROP INDEX IF EXISTS ix_attendance_record_date
CREATE INDEX IF NOT EXISTS ix_attendance_emp_date ON attendance_record (emp_id, date)
```

## Verification Results

All plan acceptance criteria verified:
- `grep -c '> "09:00:00"' app.py` → 0 (both literals removed)
- `_time_threshold` appears 5 times (definition + tests + recognize + get_stats + compute_symbol)
- `is_holiday_year_missing(2027)` → False; `'2027-01-01' in get_holidays_set(2027)` → True
- `grep -c 'SESSION_COOKIE_SECURE\|SESSION_COOKIE_HTTPONLY\|SESSION_COOKIE_SAMESITE' app.py` → 3
- `/health` test_client returns 200 `{"status": "ok", "db": "connected"}`
- `grep -c 'ix_attendance_emp_date' models.py` → 1, `app.py` → 1
- `grep -c 'Index' models.py` → 2 (import + usage)
- `import app` and `import models` both succeed without error

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — all changes are inline edits to existing files; no new network endpoints beyond /health which was planned and its threat (T-09-02) accepted in the plan's threat model.

## Self-Check: PASSED

Files exist:
- /var/www/sites/face-almgp33/.claude/worktrees/agent-ab165157282ac0953/app.py — FOUND
- /var/www/sites/face-almgp33/.claude/worktrees/agent-ab165157282ac0953/models.py — FOUND
- /var/www/sites/face-almgp33/.claude/worktrees/agent-ab165157282ac0953/.planning/phases/09-security-hardening-and-critical-bug-fixes/09-01-SUMMARY.md — FOUND

Commits exist:
- 8922eb6 — fix(09-01): schedule-aware late detection (BUG-01, BUG-02)
- dac65a8 — fix(09-01): real dept names, KZ 2027 holidays, cookie security flags (BUG-03, REL-02, SEC-04)
- 27fe8e6 — feat(09-01): /health endpoint and AttendanceRecord composite index (REL-01, PERF-01)
