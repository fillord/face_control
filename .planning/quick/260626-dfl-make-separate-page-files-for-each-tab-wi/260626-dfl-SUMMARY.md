---
status: complete
quick_id: 260626-dfl
slug: make-separate-page-files-for-each-tab-wi
description: make separate page files for each tab with direct URLs like /register and /account
date: 2026-06-26
commits:
  - 4adf6f5
  - 030581f
  - 11109e6
---

# Quick Task 260626-dfl: Per-Tab Direct URLs

## What Was Built

Every hub tab now has a direct, bookmarkable URL — matching how `/register` and `/account` already work.

### New Routes (app.py)

| Hub | Route | Tabs |
|-----|-------|------|
| `/org_admin/<tab>` | org_admin | depts, employees, summary, reports, users, settings, timesheet |
| `/superadmin/<tab>` | superadmin | orgs, users |
| `/dept_admin/<tab>` | dept_admin | attendance, employees, timesheet |

Invalid `<tab>` values silently fall back to the default tab (no 404).

### Template Changes

`org_admin.html`, `superadmin.html`, `dept_admin.html` — each hub template's tab-restore IIFE now reads the server-injected `initial_tab` first, then falls back to `window.location.hash`. This means visiting `/org_admin/reports` opens Reports on fresh load and after F5 refresh.

### Sidebar Rewire (base.html)

- All `onclick navSwitchTab(...)` attributes removed from sidebar nav anchor elements
- Each nav item now has a direct `href="/hub/tab"` URL
- `active` CSS class keyed off `request.path` (path-based, not JS-based)

## Commits

| # | Commit | Description |
|---|--------|-------------|
| 1 | `4adf6f5` | feat(260626-dfl): add per-tab routes injecting initial_tab to hub pages |
| 2 | `030581f` | feat(260626-dfl): source initial_tab in hub templates before hash fallback |
| 3 | `11109e6` | feat(260626-dfl): rewire sidebar nav to direct per-tab URLs with path-based active highlight |

## Verification Needed

1. Log in as org_admin → click "Отчёты" → URL should be `/org_admin/reports`, tab highlighted
2. Refresh (F5) → should stay on Reports tab
3. Paste `/org_admin/employees` directly → Employees tab opens
4. As superadmin: `/superadmin/users` → Users tab opens
5. As dept_admin: `/dept_admin/employees` → Employees tab opens
6. `/register`, `/account`, `/timesheet` still load normally
