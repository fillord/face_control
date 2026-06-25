---
phase: 08-i-want-to-radically-change-the-navigation-of-the-website-and
plan: "03"
subsystem: frontend-templates
tags: [navigation, sidebar, base-html, org-admin, dept-admin, template-conversion]
dependency_graph:
  requires: ["08-01"]
  provides: ["org_admin.html base.html child", "dept_admin.html base.html child"]
  affects: ["templates/org_admin.html", "templates/dept_admin.html"]
tech_stack:
  added: []
  patterns: ["Jinja2 template inheritance via {% extends %}", "{% block head %} for page-specific CSS", "{% block content %} for page markup"]
key_files:
  modified:
    - templates/org_admin.html
    - templates/dept_admin.html
decisions:
  - "Kept .page { max-width: 1100px } override in block head to preserve original narrower layout vs base.html 1200px default"
  - "Kept .stats-grid { grid-template-columns: repeat(3, 1fr) } override since both pages use fixed 3-column stat grids"
  - "Kept .card { max-width: 480px } in org_admin block head since addDeptPanel uses class=card without inline max-width"
  - "Adapted switchTab() by removing dead btn.classList.toggle('active') lines referencing removed .tab elements; kept only panel .hidden toggles"
  - "panelTimesheet in org_admin.html retained (sidebar links to /timesheet page instead, but AJAX inline panel preserved for completeness)"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-25"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 08 Plan 03: Org Admin and Dept Admin base.html Migration Summary

Migrated `templates/org_admin.html` and `templates/dept_admin.html` to extend `base.html` using the same conversion recipe proven in the superadmin pilot (plan 02). Both pages now render inside the sidebar shell, removing the old header and horizontal nav-tabs bars.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Convert org_admin.html to extend base.html | 623162a | templates/org_admin.html |
| 2 | Convert dept_admin.html to extend base.html | 95189cb | templates/dept_admin.html |

## What Was Built

**org_admin.html** — Multi-panel tabbed page (Отделы, Сотрудники, Настройки, Сводка, Пользователи, Отчёты, Табель) converted to base.html child. Removed 105 lines of duplicate shell/CSS, kept 7 page-specific CSS rules (sort-arrow, settings-card family, stats-grid override). `switchTab()` stripped of dead `.tab` active-class logic; panel `.hidden` toggling preserved. All `#1565C0`/`#0d47a1` replaced with CSS vars in HTML and JS template literals.

**dept_admin.html** — Three-panel page (Посещаемость, Сотрудники, Табель) converted to base.html child. Removed 80 lines of duplicate shell/CSS. Page-specific CSS kept: schedule-str, empty-state, weekdays, stats-grid override. All blue colors were in the removed CSS only — no inline replacements needed.

## Deviations from Plan

None — plan executed exactly as written. Both files follow the conversion recipe from plan 02.

## Verification Results

All acceptance criteria passed:

**org_admin.html:**
- `head -1` → `{% extends 'base.html' %}`
- No DOCTYPE, no `<header`, no `class="nav-tabs"`
- `{% block content %}` count = 1, `page-title` count = 1
- `grep #1565C0\|#0d47a1` → 0
- `function switchTab` present
- `{% include %}` count = 0 (unchanged)
- App imports cleanly; Jinja2 parse OK

**dept_admin.html:**
- `head -1` → `{% extends 'base.html' %}`
- No DOCTYPE, no `<header`, no `class="nav-tabs"`
- `{% block content %}` count = 1, `page-title` count = 1
- `grep #1565C0\|#0d47a1` → 0
- App imports cleanly; Jinja2 parse OK

## Known Stubs

None — all panels wire to real API endpoints (existing AJAX calls unchanged).

## Threat Flags

None — templates only; no new routes or auth paths introduced.

## Self-Check: PASSED

Files exist:
- templates/org_admin.html — FOUND (first line: `{% extends 'base.html' %}`)
- templates/dept_admin.html — FOUND (first line: `{% extends 'base.html' %}`)

Commits exist:
- 623162a — feat(08-03): convert org_admin.html to extend base.html
- 95189cb — feat(08-03): convert dept_admin.html to extend base.html
