---
phase: 03-t-13-timesheet-grid
fixed_at: 2026-06-13T00:00:00Z
iteration: 1
fix_scope: critical_warning
findings_in_scope: 11
fixed: 11
skipped: 0
status: all_fixed
---

# Phase 03 Code Review Fix Report

All 11 findings (5 Critical, 6 Warning) from `03-REVIEW.md` were applied and committed atomically.

## Fixes Applied

### Critical

| ID | File | Fix |
|----|------|-----|
| CR-01 | `app.py` | `delete_employee` and `reset_employee_face` now check that `dept_admin` targets employees in their own dept and `org_admin` targets employees in their own org; returns 403 otherwise. |
| CR-02 | `app.py` | `create_user` forces `org_admin` and `dept_admin` to `session.org_id`, ignoring any `org_id` in the request body. Only `superadmin` may supply an arbitrary `org_id`. |
| CR-03 | `templates/admin.html`, `templates/register.html` | Added `escapeHtml()` utility to both templates and applied it to all six `innerHTML` insertion points that used raw server-supplied strings (`u.username`, `r.name`, `r.role`, `e.name`, `e.role`). |
| CR-04 | `app.py` | Replaced bare `request.json` with `request.get_json(silent=True) or {}` in `create_user`, `update_user`, `register_face`, and `recognize`. Added explicit field-presence checks in `register_face` and `recognize`. |
| CR-05 | `app.py` | Removed `"medkontrol-secret-2026-xK9mP3qR7v"` hardcoded fallback. App now raises `RuntimeError` at startup if `SECRET_KEY` env var is absent. |

### Warning

| ID | File | Fix |
|----|------|-----|
| WR-01 | `app.py` | `save_orgs` and `save_depts` rewritten to use `tempfile.mkstemp + os.replace` atomic pattern (same as `save_timesheet_overrides`), eliminating the truncate-before-lock race. |
| WR-02 | `app.py` | Added `_time_threshold(base_hhmm, delta_minutes)` helper using `datetime + timedelta` with same-day clamping; replaced the manual string arithmetic in `compute_symbol`. |
| WR-03 | `app.py` | Year range `2000 <= year <= 2099` added to the `/timesheet` month parameter validation. |
| WR-04 | `app.py` | `add_employee` now uses `data.get("name", "").strip()` with a 400 guard instead of bare `data["name"]`. |
| WR-05 | `app.py` | Override API date validation replaced with `datetime.strptime(date_str, "%Y-%m-%d")`, rejecting out-of-range values like `"2025-13-01"`. |
| WR-06 | `app.py`, `templates/org_admin.html` | `create_user` now returns 400 for `target_role == "viewer"`. The "Наблюдатель" option removed from the org_admin UI dropdown. |

## Commits

```
6249d59 fix(03): WR-06 block viewer role creation in API and remove from org_admin UI dropdown
51f39fa fix(03): WR-05 use datetime.strptime for override date validation
c9608d9 fix(03): WR-04 add guard clause for missing name field in add_employee
594a52c fix(03): WR-03 add year range validation 2000-2099 to timesheet route
7220d59 fix(03): WR-02 use datetime arithmetic in compute_symbol
181092d fix(03): WR-01 save_orgs and save_depts use atomic tempfile+os.replace pattern
9aa435f fix(03): CR-05 remove hardcoded SECRET_KEY fallback
df80eee fix(03): CR-04 replace bare request.json with request.get_json(silent=True)
da55d69 fix(03): CR-03 add escapeHtml and apply to all innerHTML user-data insertions
baf7375 fix(03): CR-02 force org_admin create_user to session org_id
d337704 fix(03): CR-01 add scope check to delete_employee and reset_employee_face
```

## Test Results

All tests pass: 31 passed, 4 xfailed, 25 xpassed.
