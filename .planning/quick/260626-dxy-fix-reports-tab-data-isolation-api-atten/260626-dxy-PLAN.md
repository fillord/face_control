---
phase: quick-260626-dxy
plan: 01
type: execute
wave: 1
files_modified:
  - app.py
---

# Fix reports tab data isolation

## Objective

`/api/attendance` and `/api/stats` both called `Employee.query.all()` with no org filtering, so an org_admin visiting the Reports tab saw employees from all organizations.

## Root Cause

Two endpoints lacked the same role-based scoping already applied in `/api/employees` (line 2424).

## Fix Applied

Applied identical pattern to both endpoints:

```python
role = session.get("role")
org_id = session.get("org_id")
dept_id = session.get("dept_id")
if role == "superadmin":
    emps = Employee.query.all()
elif role in ("org_admin", "hr_viewer") and org_id:
    emps = Employee.query.filter_by(org_id=org_id).all()
elif role == "dept_admin" and dept_id:
    emps = Employee.query.filter_by(dept_id=dept_id).all()
else:
    emps = Employee.query.all()
employees = {e.id: _emp_to_dict(e) for e in emps}
```

Also scoped the `AttendanceRecord` query to `emp_ids.in_(emp_ids)` so the daily present counts in stats are also org-scoped.
