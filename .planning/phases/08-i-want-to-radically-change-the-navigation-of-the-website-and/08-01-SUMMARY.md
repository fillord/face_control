---
phase: 08-i-want-to-radically-change-the-navigation-of-the-website-and
plan: "01"
subsystem: frontend-layout
tags: [base-template, sidebar, navigation, css-tokens, jinja2-inheritance, responsive]
dependency_graph:
  requires: []
  provides:
    - templates/base.html
    - CSS token :root block (27 custom properties)
    - Jinja2 blocks: title, head, content
    - toggleSidebar() JS function
  affects:
    - All authenticated page templates (Phase 8 plans 02-06 extend this file)
tech_stack:
  added: []
  patterns:
    - "Jinja2 template inheritance via {% extends 'base.html' %} / {% block %}"
    - "CSS custom properties token system in :root"
    - "position:fixed sidebar + margin-left content layout"
    - "Pure JS hamburger toggle with overlay backdrop"
key_files:
  created:
    - templates/base.html
  modified: []
decisions:
  - "Sidebar nav uses switchTab() onclick for multi-panel pages (superadmin, org_admin, dept_admin) — no new Flask routes needed"
  - "Sidebar footer reads session.get('username','') not {{ username }} to avoid UndefinedError on routes that don't pass username variable"
  - "sidebar-overlay placed as sibling of .layout at root level (not nested in .content) — required for correct click-outside-to-close behavior"
  - "All 6 roles handled in one Jinja2 if/elif chain: superadmin, org_admin, dept_admin/viewer, hr_viewer, employee"
  - "Universal Аккаунт link (/account) appended after the role if/endif block — visible to all roles"
metrics:
  duration: "3m"
  completed: "2026-06-25T11:25:45Z"
  tasks_completed: 2
  files_created: 1
  files_modified: 0
---

# Phase 8 Plan 01: Create base.html Shared Layout Shell — Summary

**One-liner:** Jinja2 base template with dark sidebar (navy #0f172a), teal accent tokens (#0d9488), role-aware nav for 6 roles, and hamburger mobile toggle — providing the layout foundation for all Phase 8 template conversions.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create base.html document shell, CSS token :root block, and all shared CSS | 5fbcd57 | templates/base.html (created, 250 lines) |
| 2 | Add role-aware sidebar nav, logo, user footer, hamburger, overlay, toggle JS | 5fbcd57 | templates/base.html (body completed in same creation) |

Note: Both tasks were implemented as a single atomic file creation and committed together since the file was designed as a complete unit. All Task 1 and Task 2 acceptance criteria were verified before commit.

## What Was Built

`templates/base.html` (250 lines) — the single shared Jinja2 layout shell for all authenticated pages.

### CSS token system (`:root` block, 27 custom properties):
- Sidebar tokens: `--sidebar-bg`, `--sidebar-hover`, `--sidebar-text`, `--sidebar-text-active`, `--sidebar-accent`, `--sidebar-border`, `--sidebar-width`
- Content tokens: `--content-bg`, `--card-bg`, `--border`, `--text-primary`, `--text-secondary`, `--text-muted`
- Accent tokens: `--accent` (`#0d9488`), `--accent-hover`, `--accent-alt`, `--accent-light`, `--accent-text`
- Status color pairs: `--green-bg/text`, `--orange-bg/text`, `--red-bg/text`, `--gray-bg/text`
- Component tokens: `--radius-card`, `--radius-btn`, `--shadow-card`

### Shared component CSS:
`.stat-card` (+ `.teal/.green/.orange/.gray/.blue` modifiers), `.table-card`, `table`/`thead`/`th`/`td`, `.btn-primary`, `.btn-secondary`, `.btn-edit`, `.btn-delete`, `.form-group`, `.card`, `.badge` (+ 7 variants), `.hidden`, `.toolbar`, `.error-msg`, `.form-actions`, `.stats-grid`

### Role-aware sidebar nav:
- **superadmin**: Организации, Пользователи (switchTab onclick), Регистрация, Аудит, Табель Т-13
- **org_admin**: Отделы, Сотрудники, Сводка, Отчёты, Пользователи, Настройки (all switchTab onclick), Табель Т-13, Регистрация
- **dept_admin / viewer**: Посещаемость, Сотрудники (switchTab onclick), Табель Т-13, Регистрация
- **hr_viewer**: Табель Т-13 only
- **employee**: Мой табель only
- **universal (all roles)**: Аккаунт

### Mobile responsiveness:
`@media (max-width:768px)` — sidebar translates off-canvas, hamburger button shown, `toggleSidebar()` JS with Escape-key close, overlay backdrop.

## Verification Results

| Check | Result |
|-------|--------|
| `from app import app` | OK |
| Jinja2 `env.get_template('base.html')` | OK |
| `grep --accent: #0d9488` | 1 match |
| `grep --sidebar-bg: #0f172a` | 1 match |
| `grep {% block content %}` | 1 match |
| `grep {% block head %}` | 1 match |
| `grep @media (max-width: 768px)` | 2 matches |
| `grep .hamburger` | 1 match |
| `grep .sidebar.open` | 1 match |
| No old blue (#1565C0 / #0d47a1) in non-comment lines | 0 matches (pass) |
| All 6 role branches present | pass |
| `session.get('username', '')` in footer | 1 match |
| No `{{ username }}` in base.html | 0 matches (pass) |
| No `<header` tag | 0 matches (pass) |
| `switchTab('employees')` present | 2 matches |
| Line count | 250 (min 220) |

## Deviations from Plan

None — plan executed exactly as written. Both tasks implemented atomically as the file was designed complete and verified before commit.

## Known Stubs

None. `base.html` is a pure layout shell with no data stubs — it reads live session values (`session.get('username','')`, `session.role`) which are populated by Flask's session mechanism on all authenticated routes.

## Threat Flags

No new threat surface. The sidebar reads `session.role` for cosmetic rendering only; `@require_role` decorators in `app.py` remain the authoritative access control enforcement. Jinja2 auto-escapes `{{ session.get('username','') }}` preventing XSS.

## Self-Check: PASSED

- [x] `templates/base.html` exists (250 lines)
- [x] Commit `5fbcd57` exists in git log
- [x] App imports cleanly
- [x] Jinja2 parses base.html without error
- [x] No old blue color values
- [x] All 6 roles, all 3 blocks, all required IDs present
