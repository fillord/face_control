---
phase: 08-i-want-to-radically-change-the-navigation-of-the-website-and
plan: 04
subsystem: ui
tags: [jinja2, flask, base-template, navigation, css-tokens, teal]

# Dependency graph
requires:
  - phase: 08-i-want-to-radically-change-the-navigation-of-the-website-and
    plan: 01
    provides: "templates/base.html shared layout shell with sidebar, CSS tokens, hamburger JS"
provides:
  - "templates/admin.html as base.html child (hr_viewer journal + superadmin Пользователи panel)"
  - "templates/employee.html as base.html child (T-13 self-service cabinet)"
  - "templates/dashboard.html as base.html child (placeholder landing page)"
affects:
  - "any plan referencing admin.html, employee.html, or dashboard.html routes"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "tabbed-page recipe: extends base.html, switchTab() keeps only panel .hidden toggles (no dead .tab classList lines)"
    - "single-page recipe: extends base.html, {% block content %} with h1.page-title, no switchTab"
    - "wide-table recipe: .table-card CSS scoped to override base.html generic table styles; overflow-x:auto on wrapper div"

key-files:
  created: []
  modified:
    - templates/admin.html
    - templates/employee.html
    - templates/dashboard.html

key-decisions:
  - "T-13 table styles scoped to .table-card selector to override base.html's generic table/th/td at higher specificity"
  - "overflow-x:auto added via both .table-card CSS override and explicit wrapper div to satisfy acceptance criterion"
  - "switchTab() in admin.html retains only panel .hidden toggles — dead tabX.classList.toggle lines removed (tabs replaced by sidebar)"
  - "#1565C0/#0d47a1 replaced throughout including JS inline styles and Chart.js dataset colors"

patterns-established:
  - "tabbed admin pages: remove nav-tabs div, keep panel-toggle switchTab() with null-guarded panelUsers"
  - "employee grid: use .table-card with overflow-x override + outer overflow-x:auto wrapper for T-13 width"

requirements-completed: [D-09, D-10, D-11, D-14]

# Metrics
duration: 5min
completed: 2026-06-25
---

# Phase 08 Plan 04: Migrate admin.html, employee.html, dashboard.html to base.html Summary

**admin.html, employee.html, and dashboard.html converted to Jinja2 children of base.html using tabbed-page and single-page recipes, with full old-blue color replacement**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-25T10:47:27Z
- **Completed:** 2026-06-25T10:51:52Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- admin.html extends base.html; switchTab() preserves panel-only visibility control; superadmin-guarded Пользователи panel intact; chart colors migrated to teal
- employee.html extends base.html; T-13 table CSS scoped to avoid conflicts with base.html generic table rules; horizontal scroll on wide grid
- dashboard.html extends base.html; minimal placeholder card with page-title; zero CSS duplication from base.html

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert admin.html (hr_viewer journal) to extend base.html** - `fdc5837` (feat)
2. **Task 2: Convert employee.html and dashboard.html (single-page) to extend base.html** - `ad03e24` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `templates/admin.html` - Extends base.html; admin-specific CSS (btn-export, chart cards, row-late); switchTab() adapted; superadmin panel guarded; teal color palette
- `templates/employee.html` - Extends base.html; T-13 table CSS scoped to .table-card; overflow-x:auto on wrapper and .table-card override; selector-bar styles
- `templates/dashboard.html` - Extends base.html; minimal: card + h2 + role sub-label; page wrapper; teal card shadow

## Decisions Made
- T-13 table styles scoped via `.table-card` compound selectors (higher specificity 0,1,X) to prevent base.html's generic `th`/`td` rules from clobbering the T-13 column-width layout with `table-layout: fixed`.
- `overflow-x: auto` added in two places for employee.html: `.table-card { overflow-x: auto; }` in CSS (overrides base.html's `overflow: hidden`) and `<div style="overflow-x:auto;">` wrapper in HTML — both satisfy the acceptance criterion unambiguously.
- `switchTab()` in admin.html had dead `tabJournal`/`tabStats` `classList.toggle` calls referencing elements that no longer exist after header/nav-tabs removal. These were removed; only panel `.hidden` toggles remain. The `panelUsers` null-guard is preserved.
- COLORS array in admin.html JS replaced `#1565C0` with `#0d9488` (accent teal) so colorFor() remains functional without any blue reference.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- admin.html, employee.html, and dashboard.html are now base.html children; sidebar navigation renders on all three pages
- All old-blue (#1565C0, #0d47a1) eliminated from the three files
- Ready for phase 08 remaining plans (register.html, account.html, reports_partial.html, etc.)

---
*Phase: 08-i-want-to-radically-change-the-navigation-of-the-website-and*
*Completed: 2026-06-25*
