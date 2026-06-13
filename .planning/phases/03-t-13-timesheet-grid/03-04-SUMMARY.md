---
phase: 03-t-13-timesheet-grid
plan: "04"
subsystem: ui
tags: [flask, jinja2, org_admin, dashboard, attendance, summary, rbac]

requires:
  - phase: 03-02
    provides: compute_symbol, get_holidays_set, KZ_HOLIDAYS, timesheet route
  - phase: 03-03
    provides: save_timesheet_overrides, inline override API

provides:
  - "compute_dept_summary() — attendance rate per dept for a given month"
  - "?summary_month GET param on /org_admin — server-rendered summary table"
  - "Сводка по отделам section in org_admin.html with month picker"
  - "KZ_HOLIDAYS 2024/2025/2026 human-verified (approved as-is, acknowledged as potentially needing future updates)"

affects: ["04-excel-export", "05-token-based-kiosk-registration-russian-ui"]

tech-stack:
  added: []
  patterns:
    - "GET ?summary_month on existing /org_admin route — no new route (D-09/D-10)"
    - "compute_dept_summary is pure function consuming compute_symbol + get_holidays_set"

key-files:
  created: []
  modified:
    - app.py
    - templates/org_admin.html
    - templates/admin.html
    - templates/timesheet.html
    - templates/register.html
    - templates/superadmin.html

key-decisions:
  - "KZ_HOLIDAYS approved as-is by human reviewer; acknowledged as potentially needing future year updates"
  - "Summary rendered server-side via Jinja2 (GET form with ?summary_month) — no JS fetch needed"
  - "Smoke test revealed 5 bugs fixed in-session: dept creation 403, list_users unfiltered, superadmin role scope, missing back nav, Users tab misplacement"
  - "superadmin creates only org_admin (API + UI both restricted)"
  - "org_admin Users tab moved to org_admin dashboard; removed from Reports page"
  - "dept_admin user creation now includes dept selector in org_admin.html"
  - "list_users() filters by org_id when caller is org_admin"

patterns-established:
  - "Dept creation: org_admin always gets org_id from session, never from request body"
  - "User scope: list_users filters by org for org_admin"
  - "Role restriction: superadmin → org_admin only; org_admin → dept_admin/viewer/employee"
  - "Back navigation: role-conditional ← Управление / ← Панель / ← Киоск links in header"

requirements-completed: [DASH-04, T13-08]

duration: ~90min
completed: 2026-06-13
---

# Plan 03-04: Dept Summary + Phase Sign-Off Summary

**`compute_dept_summary` + Сводка по отделам on org_admin dashboard; KZ holidays human-verified; 5 RBAC/UX bugs fixed during smoke test**

## Performance

- **Duration:** ~90 min (including smoke test + bug fixes)
- **Completed:** 2026-06-13
- **Tasks:** 3 (1 implementation + 2 human checkpoints)
- **Files modified:** 6

## Accomplishments

- `compute_dept_summary(org_id, year, month)` — attendance rate per dept (Я days / work days × 100)
- `?summary_month` GET param on `/org_admin` renders Сводка по отделам table with month picker
- KZ_HOLIDAYS 2024/2025/2026 human-approved (16 dates/year, default "0000" kiosk PIN)
- Full-phase smoke test surfaced and fixed 5 bugs: dept creation 403, user list unscoped, superadmin role scope, missing back nav, Users tab on wrong page

## Task Commits

1. **Task 1: compute_dept_summary + summary table** - `327cb11` (feat(03-04))
2. **Task 2: KZ holidays verification** — human gate, approved as-is
3. **Task 3: Browser smoke test + bug fixes** - `6869ed4`, `5f359b4` (fix(03-smoke))

## Files Created/Modified

- `app.py` — `compute_dept_summary()`, `?summary_month` on `/org_admin`, `list_users()` org filter, `create_dept()` org_id fix, `create_user()` superadmin scope
- `templates/org_admin.html` — Сводка tab, Пользователи tab with dept selector, `← Управление` back link
- `templates/admin.html` — Пользователи tab restricted to superadmin only, `← Управление` for org_admin
- `templates/timesheet.html` — role-conditional back nav (`← Управление` / `← Панель`)
- `templates/register.html` — role-conditional back nav
- `templates/superadmin.html` — role dropdown restricted to org_admin only

## Decisions Made

- KZ_HOLIDAYS approved by human reviewer as-is; reviewer acknowledged dates may drift year-to-year
- Summary section uses server-side Jinja2 render (GET form) rather than fetch — no new route needed
- superadmin can only create org_admin (API + UI both enforced)
- Пользователи tab moved from Reports (admin.html) to org_admin main dashboard
- Dept selector shown in org_admin user creation form only when role = dept_admin

## Deviations from Plan

### Auto-fixed Issues

**1. Dept creation 403 for org_admin**
- **Found during:** Task 3 smoke test
- **Issue:** JS sends `org_id: null`; server rejected because `None != session.org_id`
- **Fix:** Server now forces `target_org_id = caller_org_id` for org_admin regardless of request body
- **Files modified:** app.py `create_dept()`
- **Committed in:** 6869ed4

**2. list_users() returned all users unfiltered**
- **Found during:** Task 3 smoke test
- **Issue:** org_admin could see users from other orgs
- **Fix:** Added `if caller_role == "org_admin" and u.get("org_id") != caller_org_id: continue`
- **Files modified:** app.py `list_users()`
- **Committed in:** 6869ed4

**3. superadmin could create any role**
- **Found during:** Task 3 smoke test
- **Issue:** superadmin could create dept_admin/viewer/employee (should only create org_admin)
- **Fix:** API check + superadmin.html dropdown restricted to org_admin only
- **Files modified:** app.py `create_user()`, templates/superadmin.html
- **Committed in:** 6869ed4

**4. No back navigation for org_admin**
- **Found during:** Task 3 smoke test
- **Issue:** Reports, T-13, and Registration pages showed only `← Киоск` for all roles
- **Fix:** Added role-conditional back links in 3 templates
- **Files modified:** templates/admin.html, timesheet.html, register.html
- **Committed in:** 6869ed4

**5. Пользователи tab in wrong page**
- **Found during:** Task 3 smoke test
- **Issue:** User management was on Reports page; user wanted it on main org_admin dashboard
- **Fix:** Moved Пользователи tab to org_admin.html with full user list + dept-aware creation form; removed from admin.html for org_admin
- **Files modified:** templates/org_admin.html, templates/admin.html
- **Committed in:** 5f359b4

---

**Total deviations:** 5 auto-fixed (RBAC scope, data isolation, UX navigation)
**Impact on plan:** All fixes necessary for correctness and data isolation. No scope creep — all bugs were regressions from prior phases surfaced by the smoke test.

## Issues Encountered

- Kiosk PIN reported as "not working" — investigated and confirmed PIN API works correctly. Root kiosk `/` has no PIN (expected); org-specific kiosk `/kiosk/<org_token>` has PIN set to "0000" by default. NurLab's PIN was changed via org settings. This is Phase 5 scope and works as designed.

## Next Phase Readiness

- Phase 03 complete: T-13 grid renders, inline overrides work, dept summary on org_admin dashboard
- RBAC data isolation now correctly enforced at API layer (org_admin scoped to own org)
- Ready for Phase 04 (Excel/CSV export) or Phase 05 (token-based kiosk + registration)
- Kiosk PIN documentation may be needed to inform users of `/kiosk/<org_token>` URL vs root `/`

---
*Phase: 03-t-13-timesheet-grid*
*Completed: 2026-06-13*
