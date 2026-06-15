---
quick_id: 260615-jh4
slug: add-account-settings-page-for-all-users
status: complete
date: 2026-06-15
commits:
  - 99b57ca
  - 08ca110
  - 7c6f4a1
---

# Quick Task 260615-jh4: Add Account Settings Page for All Users

## What was done

### 1. User.display_name column (models.py)
- Added `display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)` to User model
- Idempotent `ALTER TABLE user ADD COLUMN display_name TEXT` migration added to startup block in app.py

### 2. Backend routes (app.py)
- `GET /account` — requires any authenticated role (`@require_role()`), renders `account.html` with current user's `username` and `display_name`
- `PATCH /api/me` — resolves user exclusively from `session["user_id"]` (D-03 security boundary, never from request body)
  - Accepts `display_name` (max 128 chars) and/or `new_password` (8-char min, current password verified via bcrypt)
  - Full Russian error messages
  - Returns `{status: "updated", display_name: ...}` on success

### 3. account.html template
- Standalone page styled after profile.html (Russian UI, МедКонтроль branding)
- Card 1: "Имя профиля" — text input pre-filled with display_name, save button
- Card 2: "Смена пароля" — current/new/confirm inputs, client-side match validation
- `#msg` feedback region with `.success`/`.error` styling
- Both forms use `fetch PATCH /api/me` with no user id in body

### 4. Nav links in admin templates
- `<a href="/account" class="btn-logout">Аккаунт</a>` added to header-right block in:
  - `templates/dept_admin.html`
  - `templates/org_admin.html`
  - `templates/superadmin.html`
