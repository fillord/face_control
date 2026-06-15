---
phase: 07-org-admin-ux-improvements
plan: "04"
subsystem: org-admin-ui
tags: [inline-panels, partial-routes, reports, timesheet, org_admin]
dependency_graph:
  requires: [07-03]
  provides: [inline-reports-panel, inline-timesheet-panel]
  affects: [org_admin.html, app.py]
tech_stack:
  added: []
  patterns: [fetch-inject-html, partial-template, re-execute-script-tags]
key_files:
  created:
    - templates/reports_partial.html
    - templates/timesheet_partial.html
  modified:
    - app.py
    - templates/org_admin.html
decisions:
  - "Use ID-namespaced JS function prefixes (rXxx for reports, tsXxx for timesheet) to prevent global name collisions when partial HTML is injected into org_admin page"
  - "Timesheet partial form submits via tsSubmitForm() which re-fetches the partial with updated params, allowing dept/month selection without full page reload"
  - "Override dropdown in timesheet_partial.html uses ts-override-dropdown ID (not override-dropdown) to avoid conflicting with any existing element in org_admin.html"
  - "Plan specified derive_symbol — actual codebase uses compute_symbol with a different signature; implemented using compute_symbol to match existing timesheet route logic exactly"
metrics:
  duration: ~8min
  completed: "2026-06-15"
  tasks: 2
  files: 4
---

# Phase 07 Plan 04: Inline Reports and Timesheet Panels Summary

Reports and timesheet T-13 content now loads inline inside the org_admin layout via fetch-injected HTML partials, so org_admin users never leave /org_admin when accessing either panel.

## What Was Built

### Task 1: Partial Flask routes and templates (c82b0f5)

**Two new routes in app.py** (`GET /org_admin/partial/reports` and `GET /org_admin/partial/timesheet`), both gated with `@require_role("org_admin", "superadmin")`.

The timesheet partial route fully mirrors the main `/timesheet` view's dept-scope logic:
- For `org_admin`: validates that the requested `dept_id` belongs to `session.org_id` before rendering (T-07-04-A mitigation)
- Defaults to the first dept in the org if no `dept_id` param is supplied
- For `superadmin`: accepts any `dept_id` param, builds grouped dept_options by org

**`templates/reports_partial.html`**: Contains Chart.js CDN script tag, all styles (scoped to not conflict with org_admin.html's existing rules), the `panelJournal` / `panelStats` / `panelUsers` content divs, and a full `<script>` block. All JS functions are prefixed `r` (e.g. `rLoadData`, `rSwitchTab`) to avoid collision with org_admin.html globals.

**`templates/timesheet_partial.html`**: Contains styles, the selector bar form (with `onsubmit="tsSubmitForm(event)"` for AJAX re-load), the T-13 grid table (id `tabelle-t13`), the `ts-override-dropdown`, and a `<script>` block. All JS functions/variables are prefixed `ts` or `TS_`.

Neither partial contains `<!DOCTYPE>`, `<html>`, `<head>`, `<body>`, or `<header>` tags.

### Task 2: org_admin.html nav and inline panel divs (8601ab7)

- Replaced `<a class="tab" href="/admin">` and `<a class="tab" href="/timesheet">` with `<span class="tab" id="tabReports" onclick="switchTab('reports')">` and `<span class="tab" id="tabTimesheet" onclick="switchTab('timesheet')">`.
- Extended `switchTab()` tabs array from 5 to 7 entries, adding `'reports'` and `'timesheet'`. After showing the panel, calls `loadInlinePanel(tab)`.
- Added `#panelReports` and `#panelTimesheet` divs with loading placeholder text, placed after `#panelUsers` in the DOM.
- Added `loadInlinePanel(tab)` async function that fetches `/org_admin/partial/{tab}`, sets innerHTML of the inner content div, re-executes injected `<script>` tags by appending cloned elements to `<body>`, and caches the result in `_inlinePanelLoaded` to prevent redundant fetches.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan used derive_symbol (non-existent function)**
- **Found during:** Task 1 implementation
- **Issue:** The plan's code template for `org_admin_partial_timesheet` called `derive_symbol(emp_id_key, iso, attendance, overrides, holidays_set, work_days, start_t, end_t)` — but this function does not exist in app.py. The actual function is `compute_symbol(day_date, emp_id, attendance, overrides, schedule, holidays_set)` with a different signature.
- **Fix:** Implemented the route using `compute_symbol` and `compute_employee_totals` (identical to the main `timesheet()` view), building proper `schedule` dicts and `cells` lists with `{sym, auto, date}` dicts as the Jinja2 template expects.
- **Files modified:** app.py
- **Commit:** c82b0f5

**2. [Rule 2 - Critical] Timesheet partial form needs AJAX re-load, not full navigation**
- **Found during:** Task 1 design review
- **Issue:** The plan specified reusing the timesheet.html selector form which uses `<form method="GET" action="/timesheet">`. If the same form were used in the partial, submitting it would navigate to `/timesheet` (breaking the inline layout). The plan did not explicitly address this.
- **Fix:** Changed the form action to `onsubmit="tsSubmitForm(event)"` which intercepts the submit, builds the URL `/org_admin/partial/timesheet?month=...&dept_id=...`, fetches the partial, and re-injects into `#inlineTimesheetContent`. This also required invalidating the `_inlinePanelLoaded['timesheet']` cache implicitly (the re-load replaces the content directly without using the cache).
- **Files modified:** templates/timesheet_partial.html
- **Commit:** c82b0f5

**3. [Rule 1 - Bug] ID conflicts: override-dropdown and error-toast**
- **Found during:** Task 1 implementation
- **Issue:** timesheet.html uses `id="override-dropdown"` and `id="error-toast"`. If these were used as-is in the partial, injecting into org_admin.html would create duplicate IDs in the DOM, breaking JS lookups.
- **Fix:** Renamed to `id="ts-override-dropdown"` and `id="ts-error-toast"` in the partial, with all JS references updated accordingly.
- **Files modified:** templates/timesheet_partial.html
- **Commit:** c82b0f5

## Success Criteria Verification

- Clicking "Отчёты" in org_admin nav calls `switchTab('reports')` → shows `#panelReports` → calls `loadInlinePanel('reports')` → fetches `/org_admin/partial/reports` → injects HTML with full journal/stats functionality
- Clicking "Табель Т-13" in org_admin nav calls `switchTab('timesheet')` → shows `#panelTimesheet` → calls `loadInlinePanel('timesheet')` → fetches `/org_admin/partial/timesheet` → injects HTML with T-13 grid for org's departments
- Browser URL stays at /org_admin throughout (no navigation events)
- `/org_admin/partial/reports` and `/org_admin/partial/timesheet` return 200 for org_admin role
- Unauthenticated requests to partial routes return 302 (redirect to login) via `@require_role`
- dept_id validation in timesheet partial enforces org isolation (T-07-04-A)
- Panels are fetched only once per session (cached via `_inlinePanelLoaded`)

## Self-Check: PASSED

| Item | Status |
|------|--------|
| templates/reports_partial.html | FOUND |
| templates/timesheet_partial.html | FOUND |
| 07-04-SUMMARY.md | FOUND |
| commit c82b0f5 (Task 1) | FOUND |
| commit 8601ab7 (Task 2) | FOUND |
