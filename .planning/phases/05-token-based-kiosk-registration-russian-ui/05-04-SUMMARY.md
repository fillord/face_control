---
phase: 05-token-based-kiosk-registration-russian-ui
plan: "04"
subsystem: ui-branding
tags:
  - russian-ui
  - branding
  - role-scoped-nav
  - headers
dependency_graph:
  requires:
    - 05-03
  provides:
    - role-scoped-headers
    - russian-ui-chrome
    - scoped-navigation
  affects:
    - templates/superadmin.html
    - templates/org_admin.html
    - templates/dept_admin.html
    - templates/admin.html
    - app.py
tech_stack:
  added: []
  patterns:
    - Flask context injection for role-scoped header names
    - Jinja2 conditional nav rendering by session.role
key_files:
  created: []
  modified:
    - app.py
    - templates/org_admin.html
    - templates/dept_admin.html
    - templates/admin.html
decisions:
  - org_name and dept_name resolved server-side from session.org_id and session.dept_id
  - dept_admin nav: replaced Отчёты with Регистрация (reports not in dept scope per CONTEXT)
  - org_admin nav: kept Отчёты, added Регистрация (both in org scope per CONTEXT)
  - admin.html Пользователи tab gated to superadmin and org_admin; dept_admin excluded
metrics:
  duration: "~15 minutes"
  completed: "2026-06-12T17:05:16Z"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 4
---

# Phase 05 Plan 04: Russian UI Branding and Role-Scoped Navigation Summary

**One-liner:** Role-scoped headers (org name / dept name from Flask) and role-only navigation with full Russian UI chrome across all admin/auth templates.

## What Was Built

- `app.py`: `org_admin_page` now resolves the caller's org via `load_orgs().get(session.org_id)` and passes `org_name` to the template; `dept_admin_page` resolves `load_depts().get(session.dept_id)` and passes `dept_name`.
- `templates/org_admin.html`: Header reads `МедКонтроль — {{ org_name }}` (falls back to `МедКонтроль` when org_name is empty). Title updated to match. Nav updated: added Регистрация tab.
- `templates/dept_admin.html`: Header reads `МедКонтроль — {{ dept_name }}` (fallback `МедКонтроль`). Title updated. Nav updated: replaced cross-role Отчёты link with Регистрация tab.
- `templates/admin.html`: Пользователи tab in nav is now gated to `superadmin` and `org_admin` only; dept_admin no longer sees user management in the reports view.
- `templates/superadmin.html`: Already had `МедКонтроль — Суперадмин` header — no changes needed.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 2ec2047 | feat(05-04): pass org_name/dept_name from Flask and set role-scoped headers |
| 2 | 91c6bf4 | feat(05-04): enforce role-scoped navigation across dashboards |

## Verification Results

- Automated brand check: BRAND_OK (`Суперадмин` in superadmin.html, `org_name` in org_admin.html, `dept_name` in dept_admin.html, `org_name=` and `dept_name=` in app.py)
- Automated nav-scope check: NAV_SCOPED_OK (no `/superadmin` or `/org_admin` links in dept_admin.html)
- Pytest: 24 passed, 3 xfailed, 15 xpassed — no regressions

## Deviations from Plan

### Auto-adjustments (within plan scope)

**1. [Rule 2 - Missing functionality] Scoped nav additions beyond minimum**
- **Found during:** Task 2
- **Issue:** Plan specifies org_admin nav should include "registration" and dept_admin nav should include "registration" — these were absent.
- **Fix:** Added `<a class="tab" href="/register">Регистрация</a>` to org_admin.html and dept_admin.html navs.
- **Files modified:** templates/org_admin.html, templates/dept_admin.html

**2. [Rule 2 - Cross-role visibility] admin.html Пользователи tab visible to dept_admin**
- **Found during:** Task 2 audit
- **Issue:** admin.html nav showed Пользователи tab to all three admin roles including dept_admin, which should not manage system users.
- **Fix:** Gated Пользователи tab in admin.html to `session.role in ['superadmin', 'org_admin']` only.
- **Files modified:** templates/admin.html

## Checkpoint Required

Task 3 is a `checkpoint:human-verify` gate. Execution has paused for human visual verification.

**What to verify:**
1. `pm2 restart face-recognition`
2. Log in as superadmin → header reads "МедКонтроль — Суперадмин"; nav shows only superadmin tabs
3. Log in as org_admin → header reads "МедКонтроль — [org name]"; nav shows Отделы, Сотрудники, Отчёты, Регистрация — no superadmin links
4. Log in as dept_admin → header reads "МедКонтроль — [dept name]"; nav shows Посещаемость, Сотрудники, Регистрация — no org/superadmin links
5. All pages: confirm no English text in buttons, tables, placeholders, toasts, empty states

## Known Stubs

None. All templates render live data from the server.

## Threat Flags

None. No new network endpoints or auth paths introduced. Only template rendering and Flask context injection.

## Self-Check: PASSED

- app.py modified: found in git commit 2ec2047
- templates/org_admin.html modified: found in git commit 2ec2047 and 91c6bf4
- templates/dept_admin.html modified: found in git commit 2ec2047 and 91c6bf4
- templates/admin.html modified: found in git commit 91c6bf4
- Brand verification: BRAND_OK
- Nav scope verification: NAV_SCOPED_OK
- Test suite: all passing
