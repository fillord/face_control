---
quick_id: 260615-q01
slug: employee-iin-import-user-crud
status: complete
date: 2026-06-15
commit: 93c9e1f
---

# Quick Task 260615-q01: Employee IIN, Excel Import, User CRUD

## What was done

### 1. Employee IIN field
- Added `iin: Mapped[Optional[str]]` column to `Employee` model (`models.py`)
- Ran `ALTER TABLE employee ADD COLUMN iin TEXT` migration
- Added `iin` to `_emp_to_dict()` output so all API responses include it
- PATCH `/api/employees/<id>` now accepts `iin` in its whitelist

### 2. Excel import endpoint
- `POST /api/employees/import_xlsx` — `org_admin`/`superadmin` only
- Auto-detects header row by scanning for "ИИН" in any cell
- Columns mapped: Фамилия(4)+Имя(5)+Отчество(6)→name, ИИН(7)→iin, Отделение(9)→dept
- Matches existing employees by IIN (update), creates new if not found
- Returns `{created, updated, skipped}`

### 3. org_admin Employees tab UI
- "Импорт из Excel" button triggers hidden file input, calls import endpoint, shows result inline
- IIN column added to employees table (between Имя and Отдел)
- Edit employee panel now has IIN field (populated and saved)
- colspan fixed from 6→7 throughout

### 4. User CRUD in Users tab
- `DELETE /api/users/<id>` — cannot delete self, role hierarchy enforced
- `PATCH /api/users/<id>` extended: accepts `password` (change) and `dept_id` (reassign)
- Edit user panel added in HTML: shows username, allows password change + dept reassign
- Delete button added to each user row
- Edit button opens inline panel, closes after save
