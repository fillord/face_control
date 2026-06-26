---
status: complete
quick_id: 260626-dxy
description: fix reports tab data isolation
date: 2026-06-26
commits:
  - 735e695
---

# Quick Task 260626-dxy: Fix Reports Tab Data Isolation

## What Was Fixed

`/api/attendance` and `/api/stats` both had `Employee.query.all()` with no org filtering. An org_admin at `/org_admin/reports` was seeing employees from all organizations.

## Changes (app.py)

Both `get_attendance()` and `get_stats()` now apply the same role-based employee scoping already present in `get_employees()`:

- `superadmin` → all employees
- `org_admin` / `hr_viewer` → filtered by `session["org_id"]`
- `dept_admin` → filtered by `session["dept_id"]`

The `AttendanceRecord` queries are also scoped to the visible `emp_ids`, so daily presence counts in the Stats tab are also correctly org-scoped.

## Commit

`735e695` — fix(260626-dxy): scope /api/attendance and /api/stats to session org_id/dept_id
