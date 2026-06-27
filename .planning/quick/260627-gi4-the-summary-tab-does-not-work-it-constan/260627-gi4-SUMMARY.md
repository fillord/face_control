---
phase: quick-260627-gi4
plan: "01"
subsystem: org_admin
tags: [bugfix, navigation, summary-tab]
dependency_graph:
  requires: []
  provides: [summary-tab-navigation-fix]
  affects: [templates/org_admin.html]
tech_stack:
  added: []
  patterns: [GET form routing via Flask tab path]
key_files:
  created: []
  modified:
    - templates/org_admin.html
decisions:
  - "Changed form action from /org_admin to /org_admin/summary so Flask resolves tab='summary' and switchTab stays on Summary"
metrics:
  duration: "<2 min"
  completed_date: "2026-06-27"
  tasks_completed: 1
  tasks_total: 2
---

# Quick 260627-gi4: Summary Tab Fix

## One-liner

Fixed Summary tab bouncing to Departments by pointing the month-picker form to `/org_admin/summary` instead of `/org_admin`.

## What Was Done

**Task 1 (commit 2a32ebf):** Changed line 172 of `templates/org_admin.html` — the Summary panel's month-picker form action from `action="/org_admin"` to `action="/org_admin/summary"`.

Root cause: The bare `/org_admin` route defaults `tab="depts"`, so `initial_tab="depts"` was passed to the template, causing the bottom-of-page IIFE to call `switchTab("depts")` immediately — hiding the just-computed summary rows and showing the Departments panel instead.

With the fix, the GET submit resolves to the `/org_admin/<tab>` route with `tab="summary"`, so Flask correctly sets `initial_tab="summary"` and `switchTab("summary")` is called, keeping the user on the Summary tab with the `summary_rows` table visible.

**Task 2 (checkpoint:human-verify):** Per plan constraints, not blocking — noted below for manual verification.

## Deviations from Plan

None — plan executed exactly as written.

## Human Verification Required

After running `pm2 restart face-recognition` from `/var/www/sites/face-almgp33`, verify:

1. Log in as org_admin and open the org admin panel.
2. Click "Сводка" (Summary) in the left nav — confirm the Summary panel appears.
3. Pick a month and click "Показать табель".
4. Confirm the page STAYS on the Summary tab showing the per-department table (or "Нет данных за выбранный месяц." if no data).
5. Confirm "Сводка" in the left nav remains highlighted as active.

## Known Stubs

None.

## Threat Flags

None — this change affects only a form action attribute; no new network endpoints or auth paths introduced.

## Self-Check

- [x] `templates/org_admin.html` modified: `action="/org_admin/summary"` present exactly once at line 172
- [x] No bare `action="/org_admin"` remains in the file
- [x] Commit 2a32ebf exists in git log
