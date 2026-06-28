---
phase: 10-superadmin-panel-extension
plan: "04"
subsystem: superadmin-panel
tags: [analytics, chart-js, attendance-stats, superadmin, frontend, backend, api]
dependency_graph:
  requires:
    - AttendanceRecord ORM model (emp_id, date, check_in_time)
    - Employee ORM model (for Employee.query.count())
    - require_role("superadmin") decorator — from prior plans
    - switchTab / lazy-load tab pattern — from plan 10-01
    - escapeHtml JS helper — from prior plans
    - panelCalendar tab — from plan 10-03
  provides:
    - superadmin_attendance_stats (GET /api/superadmin/attendance_stats)
    - panelAnalytics tab with loadAnalytics / analyticsChartInst / analyticsCtx JS
    - analyticsLoaded lazy-load state flag
    - Chart.js 4.4.0 CDN script tag in superadmin.html head block
    - Аналитика nav link in base.html superadmin sidebar
    - tests/test_sadm06.py — 4 tests
  affects:
    - app.py (new endpoint)
    - templates/superadmin.html (new tab, Chart.js CDN, JS functions, state vars, extended switchTab)
    - templates/base.html (new nav link)
tech_stack:
  added:
    - Chart.js 4.4.0 (CDN, already in admin.html — now also in superadmin.html)
  patterns:
    - Date-range aggregation loop (last N days, oldest-first) for attendance_stats
    - days param clamp to [1, 90] for DoS protection (T-10-16)
    - Destroy-then-create Chart.js pattern (analyticsChartInst.destroy() on re-render)
    - Lazy-load tab pattern (analyticsLoaded flag + switchTab gate)
    - Unique variable names (analyticsCtx, analyticsChartInst) to avoid ctx collision (Pitfall 5)
key_files:
  created:
    - tests/test_sadm06.py
  modified:
    - app.py
    - templates/superadmin.html
    - templates/base.html
decisions:
  - Used unique variable names analyticsCtx and analyticsChartInst (not ctx/chartInst) to avoid collision with any other script scope in superadmin.html (Pitfall 5 per RESEARCH.md)
  - Empty-data guard added to loadAnalytics — if data is empty or fetch fails, returns early without attempting Chart.js instantiation
  - y-axis scale fixed min 0 max 100 (percent) so chart is always meaningful even with sparse data
  - Chart.js CDN placed in the head block of superadmin.html (currently was empty), matching admin.html line 5 pattern
metrics:
  duration: "~10 minutes"
  completed: "2026-06-29"
  tasks_completed: 2
  files_changed: 3
---

# Phase 10 Plan 04: SADM-06 — Attendance Analytics Chart Summary

Delivered SADM-06 (D-06): a system-wide attendance analytics chart. GET /api/superadmin/attendance_stats returns per-day percent attendance across all orgs for the last N days (days clamped 1–90), and a new Analytics tab renders a Chart.js line chart with destroy-then-create re-render safety and 403 enforcement.

## What Was Built

### Task 1: Backend — attendance_stats aggregation endpoint + tests (app.py, tests/test_sadm06.py)

**GET /api/superadmin/attendance_stats (SADM-06 / D-06):** New endpoint under `# ─── API: Superadmin Extensions ───` section. Reads `days` query param (default 30), clamps to `max(1, min(days, 90))`. Computes `total_employees = Employee.query.count()`. For each of the last N days (oldest-first, range from `days-1` down to 0), computes present_count as `AttendanceRecord.query.filter(date == d, check_in_time != None).count()` and `percent = round(present_count / total_employees * 100, 1)` (0 when no employees). Returns JSON list of `{date, total_employees, present_count, percent}`. Protected by `@require_role("superadmin")`.

**tests/test_sadm06.py:** 4 tests all passing:
- (a) GET ?days=7 returns 200 and list of length 7 with correct keys
- (b) Present employee with check_in_time causes percent > 0 for that day
- (c) days=1000 returns exactly 90 entries (clamped)
- (d) GET as org_admin returns 403

### Task 2: Frontend — Analytics tab, Chart.js line chart, nav link (templates/superadmin.html, templates/base.html)

**Chart.js 4.4.0 CDN:** `<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js">` added to `{% block head %}` (was empty). Matches admin.html line 5 pattern.

**panelAnalytics div:** Added `<div id="panelAnalytics" class="page hidden">` with page-title "Аналитика" and a card containing `<canvas id="analyticsChart" height="80">`.

**JS state variables added:** `analyticsLoaded = false`, `analyticsChartInst = null`.

**loadAnalytics():** Fetches `/api/superadmin/attendance_stats?days=30`. Empty-data guard returns early if no data. Maps response to `labels` (date) and `values` (percent). Destroys `analyticsChartInst` if it exists (re-render safety). Creates new `Chart` of type `line` using `analyticsCtx = document.getElementById('analyticsChart').getContext('2d')`. Single dataset labeled `% присутствия`, tension 0.3, fill false, y-axis min 0 max 100. Uses `analyticsCtx` and `analyticsChartInst` names throughout (Pitfall 5).

**switchTab extended:** `'analytics'` added to the tab list; lazy-load guard `if (tab === 'analytics' && !analyticsLoaded) { loadAnalytics(); analyticsLoaded = true; }` added.

**templates/base.html:** Added Аналитика nav link (`href=/superadmin/analytics`, icon 📈) after Календарь link in the superadmin sidebar block.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat | Mitigation | Location |
|--------|------------|----------|
| T-10-15 Info Disclosure / Elevation | `@require_role("superadmin")` returns 403 for all other roles; verified by test (d) | app.py superadmin_attendance_stats() |
| T-10-16 DoS (days param) | `max(1, min(days, 90))` clamps the day range; verified by test (c) | app.py superadmin_attendance_stats() |
| T-10-17 CDN tampering | Pinned to chart.umd.min.js@4.4.0 already trusted in admin.html; same-origin policy applies | templates/superadmin.html |

## Known Stubs

None. loadAnalytics fetches live data from GET /api/superadmin/attendance_stats which queries the production AttendanceRecord table.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 — Backend endpoint + tests | 19601c9 | app.py, tests/test_sadm06.py |
| 2 — Frontend Analytics tab + nav link | b1d70ed | templates/superadmin.html, templates/base.html |

## Self-Check: PASSED
