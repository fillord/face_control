---
phase: 08-i-want-to-radically-change-the-navigation-of-the-website-and
plan: "05"
subsystem: templates
tags: [jinja2, base-html, migration, teal-rebrand, timesheet, registration]
dependency_graph:
  requires: [08-01]
  provides: [complete-template-migration]
  affects: [templates/timesheet.html, templates/audit.html, templates/devices.html, templates/profile.html, templates/account.html, templates/403.html, templates/register.html]
tech_stack:
  added: []
  patterns: [jinja2-template-inheritance, css-custom-properties, block-head-override]
key_files:
  created:
    - templates/devices.html
  modified:
    - templates/timesheet.html
    - templates/audit.html
    - templates/profile.html
    - templates/account.html
    - templates/403.html
    - templates/register.html
decisions:
  - "devices.html did not exist in worktree (was untracked in main repo) — created from scratch using main repo source as reference"
  - "sym_fg['Б'] in timesheet JS changed from #1565C0 to #0d9488 (hex equivalent of var(--accent)) since CSS variables cannot be used in JS objects"
  - "COLORS[0] in register.html JS changed from #1565C0 to #0d9488 to maintain teal theme in avatar palette"
  - "403.html uses h2 not h1.page-title per plan spec (error page exception to D-05)"
  - "T-13 grid has no .page wrapper — overflow-x:auto applied directly on .table-card override in block head"
metrics:
  duration: "~6 minutes"
  completed: "2026-06-25"
  tasks_completed: 2
  files_changed: 7
---

# Phase 08 Plan 05: Remaining Template Migration Summary

Converted the remaining seven authenticated full-page templates to extend `base.html`, completing the full sidebar-shell migration for phase 08.

## What Was Built

All seven templates (`timesheet.html`, `audit.html`, `devices.html`, `profile.html`, `account.html`, `403.html`, `register.html`) were stripped of standalone document shells, old blue headers, nav-tabs, and shared CSS — then re-expressed as Jinja2 child templates of `base.html` using `{% extends %}`, `{% block title %}`, `{% block head %}`, and `{% block content %}`.

**Key specifics:**
- `timesheet.html`: T-13 grid rendered full-width with `overflow-x:auto` via `.table-card` override in `{% block head %}`; no `.page` max-width clamp applied to the grid
- `audit.html`: nav-tabs linking `/admin` → `/register` removed (sidebar replaces them); content wrapped in `.page`
- `devices.html`: dark `header { background:#0d1429 }` deleted; blue rename/save buttons replaced with teal `var(--accent)` tokens
- `profile.html`: header removed (sidebar reads `session.get('username','')` — no unpassed `username` variable)
- `account.html`: teal focus rings and button colors
- `403.html`: role-based return link preserved (`dashboard_page` for viewer/employee, `admin_page` for others); uses `btn-primary` class
- `register.html`: all camera/capture/face-detection JavaScript preserved unchanged; only color tokens updated

## Verification Results

All acceptance criteria passed:
- `{% extends 'base.html' %}` is line 1 in all 7 files
- Zero `<!DOCTYPE`, zero `<header` in all 7 files
- `{% block content %}` present in all 7 files
- `grep -c "#1565C0\|#0d47a1"` → 0 across all 7 files
- `grep -c "#0d1429"` → 0 in devices.html
- `overflow-x:auto` present in timesheet.html; no `class="page"` wrapper on grid
- Jinja2 template parse chain OK for all 7 templates
- Flask app imports cleanly

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes on devices.html

`devices.html` was not present in the worktree (untracked file in main repo, not yet committed at worktree base commit `5a8e916`). The file was created fresh in the worktree using the main-repo source as the reference, converting it directly to a `base.html` child.

## Known Stubs

None — all placeholder text found is HTML input `placeholder=""` attribute text (normal form UI patterns, not code stubs).

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary changes introduced. This plan only modifies HTML/CSS template structure.

## Self-Check: PASSED

All 7 template files confirmed on disk. Task commits verified:
- `90c47c1` — feat(08-05): convert timesheet, audit, devices to extend base.html
- `edf6b77` — feat(08-05): convert profile, account, 403, register to extend base.html
