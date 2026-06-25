---
phase: 08-i-want-to-radically-change-the-navigation-of-the-website-and
plan: "02"
subsystem: frontend-templates
tags: [navigation, base-template, superadmin, jinja2, pilot-conversion]
dependency_graph:
  requires: ["08-01"]
  provides: ["templates/superadmin.html extends base.html"]
  affects: ["templates/superadmin.html"]
tech_stack:
  added: []
  patterns: ["Jinja2 template inheritance via {% extends %}", "{% block content %} / {% block head %} pattern"]
key_files:
  modified:
    - templates/superadmin.html
decisions:
  - "Empty {% block head %} retained (all shared CSS now lives in base.html)"
  - "switchTab() reduced to panel-only toggle; dead tabOrgs/tabUsers DOM refs removed"
  - "Inline color references in renderOrgs() JS replaced with var(--accent) per D-07"
metrics:
  duration: "~10 minutes"
  completed: "2026-06-25"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
---

# Phase 08 Plan 02: Convert superadmin.html to extend base.html Summary

Converted `templates/superadmin.html` from a standalone document into a `base.html` child template. Removed the full HTML shell, old header, horizontal nav-tabs, and all shared CSS now provided by `base.html`. Wrapped org/users panel content in `{% block content %}` with an `h1.page-title` first element, and adapted `switchTab()` to drop dead `.tab` element references.

## Tasks

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Convert superadmin.html to extend base.html | 2de0388 | templates/superadmin.html |

## Acceptance Criteria Verification

All acceptance criteria passed:

- `head -1 templates/superadmin.html` → `{% extends 'base.html' %}` ✓
- `grep -c "{% block content %}"` → 1 ✓
- `grep -c "<!DOCTYPE"` → 0 ✓
- `grep -c "<header"` → 0 ✓
- `grep -c 'class="nav-tabs"'` → 0 ✓
- `grep -c "page-title"` → 1 ✓
- Old blue color check (`#1565C0`, `#0d47a1`) → 0 ✓
- `grep -c "getElementById('tabOrgs')"` → 0 ✓
- `grep -c "function switchTab"` → 1 ✓
- Jinja2 template parse → `template parse OK` ✓
- `SECRET_KEY=testkey python -c "from app import app"` → `app OK` ✓

## What Changed

### Removals
- Entire `<!DOCTYPE html>` ... `</html>` document shell
- `<header>` block (logo, user badge, logout links) — sidebar in base.html replaces this
- `<div class="nav-tabs">` horizontal tab bar — sidebar nav calls `switchTab()` instead
- All shared CSS rules now provided by base.html: `*`, `body`, `.stat-card`, `.stat-label`, `.stat-val.*`, `.table-card`, `table`/`thead`/`th`/`td`, `.badge`, `.btn-primary`, `.btn-secondary`, `.btn-edit`, `.btn-delete`, `.card`, `.form-group*`, `.form-actions`, `.hidden`, `.toolbar`, `.error-msg`, `.stats-grid`, media query for `.stats-grid`
- Header-specific CSS: `.logo`, `.logo-icon`, `.header-right`, `.user-badge`, `.btn-logout`
- Tab-specific CSS: `.nav-tabs`, `.tab`

### Added
- `{% extends 'base.html' %}` as first line
- `{% block title %}Суперадмин — МедКонтроль{% endblock %}`
- `{% block head %}{% endblock %}` (empty — no page-specific CSS needed)
- `{% block content %} ... {% endblock %}` wrapping all page content
- `<h1 class="page-title">Организации</h1>` as first element in content block (D-05)

### Modified
- `switchTab()` reduced from 4 lines to 2 lines (panel toggles only; dead `tabOrgs`/`tabUsers` classList calls removed)
- `#1565C0` → `var(--accent)` in inline styles inside `renderOrgs()` JS template literals
- `.stat-val.blue` → `.stat-val.teal` on stat cards in markup

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The panels contain real CRUD functionality backed by API calls; no placeholder data.

## Threat Flags

None. This change is purely a template refactor — no new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

- templates/superadmin.html: FOUND
- Commit 2de0388: FOUND
- 08-02-SUMMARY.md: FOUND
