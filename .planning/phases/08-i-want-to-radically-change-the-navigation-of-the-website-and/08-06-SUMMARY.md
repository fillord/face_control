---
phase: 08-i-want-to-radically-change-the-navigation-of-the-website-and
plan: "06"
subsystem: templates
tags: [css-tokens, teal-palette, partials, error-page, inter-font]
dependency_graph:
  requires: ["08-01"]
  provides: ["reports_partial teal tokens", "timesheet_partial teal tokens", "error_token Inter+teal standalone"]
  affects: ["templates/reports_partial.html", "templates/timesheet_partial.html", "templates/error_token.html"]
tech_stack:
  added: []
  patterns: ["CSS custom property tokens (var(--accent))", "Inter font via Google Fonts CDN"]
key_files:
  created: []
  modified:
    - templates/reports_partial.html
    - templates/timesheet_partial.html
    - templates/error_token.html
decisions:
  - "Used var(--accent)/var(--accent-hover) in CSS rules; used #0d9488/#0f766e hex literals in JS inline style strings for compatibility"
  - "Kept timesheet .page with max-width:1400px override (wider than base.html 1200px — required for T-13 wide table)"
  - "Kept timesheet .table-card override (overflow-x:auto) since base.html sets overflow:hidden"
  - "register_token.html intentionally excluded per D-12 (public, session-less, not in D-14 scope)"
metrics:
  duration: "~5 minutes"
  completed: "2026-06-25T16:52:29Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase 08 Plan 06: CSS Token + Font Updates for Partials and error_token Summary

Teal palette applied to the two included partials (reports_partial.html, timesheet_partial.html) and the public token-error page (error_token.html). All old blue (#1565C0, #0d47a1) removed; Inter font added to the public page. Neither partial gained an extends or document shell.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update reports_partial.html and timesheet_partial.html CSS tokens | da11110 | templates/reports_partial.html, templates/timesheet_partial.html |
| 2 | Restyle public error_token.html to Inter + teal (standalone, D-14) | 5b06c3e | templates/error_token.html |

## What Was Built

**Task 1 — Partials teal token update:**
- `reports_partial.html`: Removed leftover `<div class="nav-tabs" id="reportsNavTabs">` block (7 lines) — sidebar navigation replaces it (D-09). Stripped ~35 CSS rules now provided by base.html (logo, nav-tabs, stat-card, stat-label, stat-val, table-card, table/thead/th/td, badges, hidden, toolbar, page). Applied teal tokens: `.btn-export` background → `var(--accent)`, hover → `var(--accent-hover)`. Updated chart bar colors to `rgba(13,148,136,0.7)` / `#0d9488`. Changed `stat-val.blue` HTML class to `stat-val.teal`. Updated RCOLORS[0] and stats-body inline color to `#0d9488`.
- `timesheet_partial.html`: Removed duplicated base.html rules (thead bg, btn-primary/btn-primary:hover/btn-secondary, hidden, tr:last-child td, `*` box-sizing). Kept timesheet-specific overrides: `.page max-width:1400px`, `.table-card overflow-x:auto`, full `thead th` / `tbody td` table layout CSS, sym-cell/totals-row/holiday styles. Applied teal tokens: form focus → `var(--accent)`, `.totals-row td` → `var(--accent)`, sym-cell editable hover → `var(--accent)`, inline `color:var(--accent)` on total columns, `TS_SYM_FG['Б']` sick-leave color → `#0d9488`.

**Task 2 — error_token.html Inter + teal restyle:**
- Added three Inter font `<link>` tags (preconnect × 2 + stylesheet) before `<style>` (D-08).
- Updated `body` font-family to `'Inter', 'Segoe UI', system-ui, sans-serif`.
- Refreshed body background `#f4f6fb` → `#f8fafc`, text color `#1a2340` → `#0f172a`.
- Changed `.logo-icon` background `#1565C0` → `#0d9488` (teal accent, D-07).
- Changed `.card` box-shadow `rgba(21,101,192,0.07)` → `rgba(13,148,136,0.07)`.
- Kept `<!DOCTYPE html>` standalone shell, `{{ message }}` markup, no `{% extends %}`, no `session` reference (D-12).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing null-check] rSwitchTab null-safe tab element access**
- **Found during:** Task 1
- **Issue:** After removing nav-tabs HTML, `document.getElementById("rTabJournal")` / `"rTabStats"` returned null, causing a runtime TypeError on `.classList.toggle()`.
- **Fix:** Added `const tabJournal = document.getElementById("rTabJournal"); if (tabJournal) tabJournal.classList.toggle(...)` pattern for both non-null-checked tab elements.
- **Files modified:** templates/reports_partial.html
- **Commit:** da11110

**2. [Rule 2 - Missing override] Kept .table-card override in timesheet_partial.html**
- **Found during:** Task 1
- **Issue:** base.html sets `.table-card { overflow: hidden; }` but the timesheet requires `overflow-x: auto` for the horizontally-scrollable T-13 table.
- **Fix:** Retained `.table-card { overflow-x: auto; }` override in the partial instead of removing it entirely.
- **Files modified:** templates/timesheet_partial.html
- **Commit:** da11110

**3. [Rule 2 - Missing override] Kept .page max-width in timesheet_partial.html**
- **Found during:** Task 1
- **Issue:** base.html sets `.page { max-width: 1200px; }` but the T-13 table needs `max-width: 1400px` for wide-screen display.
- **Fix:** Retained the `.page { max-width: 1400px; ... }` definition in the partial.
- **Files modified:** templates/timesheet_partial.html
- **Commit:** da11110

## Scope Exclusion (documented, not a gap)

`templates/register_token.html` is intentionally NOT modified. It is a PUBLIC, session-less mobile registration page rendered by `GET /register/<reg_token>` — not named in D-14's redesign scope. Per D-12 (public token-flow pages stay standalone), this exclusion is deliberate.

## Known Stubs

None — no stub patterns found.

## Threat Flags

None — this plan is a CSS/font update only; no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

All files exist. Both task commits verified in git history.
