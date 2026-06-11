# Phase 01: RBAC Foundation - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 8 (1 modified Python file, 5 modified/new templates, 2 new test files)
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app.py` (Auth: Users section) | utility/service | CRUD | `app.py` `load_config()` / `save_config()` / `init_config()` lines 26-40 | exact |
| `app.py` (Auth: RBAC section) | middleware | request-response | `app.py` `login_required` decorator lines 42-48 | exact |
| `app.py` (login_page upgrade) | controller | request-response | `app.py` `login_page()` lines 136-152 | exact |
| `app.py` (API routes with @require_role) | controller | request-response | `app.py` `register_page()` / `admin_page()` lines 159-167 | exact |
| `app.py` (POST /api/users + PATCH /api/users) | controller | CRUD | `app.py` `add_employee()` / `delete_employee()` lines 175-203 | role-match |
| `templates/403.html` | template | request-response | `templates/login.html` lines 1-62 | role-match |
| `templates/dashboard.html` | template | request-response | `templates/login.html` lines 1-62 | role-match |
| `templates/profile.html` | template | request-response | `templates/login.html` lines 38-60 (form pattern) | role-match |
| `templates/admin.html` (nav upgrade) | template | request-response | `templates/admin.html` lines 66-79 (header + nav-tabs) | exact |
| `tests/conftest.py` | test | — | none | no analog |
| `tests/test_auth.py` | test | — | none | no analog |
| `tests/test_rbac.py` | test | — | none | no analog |

---

## Pattern Assignments

### `app.py` — Auth: Users section (new section after line 48)

**Analog:** `app.py` lines 26-40 (`load_config` / `save_config` / `init_config`)

**File constant pattern** (lines 12-17):
```python
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EMPLOYEES_FILE = os.path.join(DATA_DIR, "employees.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
```
New constant follows same form:
```python
USERS_FILE = os.path.join(DATA_DIR, "users.json")
```

**load/save helper pattern** (lines 26-34):
```python
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```
New helpers follow identical structure with `USERS_FILE` and `{}` default.

**init bootstrap pattern** (lines 36-40):
```python
def init_config():
    cfg = load_config()
    if "password_hash" not in cfg:
        pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        save_config({"username": "admin", "password_hash": pw_hash})
```
`init_users()` follows this pattern: check existence first, read `config.json` via `load_config()`, copy `password_hash` verbatim (do NOT re-hash), fall back to `bcrypt.hashpw(b"superadmin123", bcrypt.gensalt()).decode()` only when `cfg.get("password_hash")` is falsy. Use `uuid.uuid4()` for `id` field.

**Section header convention** (line 24):
```python
# ─── Config / Auth ────────────────────────────────────────────────────────────
```
New sections:
```python
# ─── Auth: Users ──────────────────────────────────────────────────────────────
# ─── Auth: RBAC ───────────────────────────────────────────────────────────────
```

---

### `app.py` — `@require_role` decorator (replaces `@login_required`, lines 42-48)

**Analog:** `app.py` `login_required` lines 42-48

**Existing decorator to replace:**
```python
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login_page", next=request.path))
        return f(*args, **kwargs)
    return decorated
```

**New decorator — wraps the same `@wraps(f)` inner structure, adds outer factory layer and two extra checks:**
```python
def require_role(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                return redirect(url_for("login_page", next=request.path))
            users = load_users()
            user = users.get(user_id)
            if not user or not user.get("active"):
                session.clear()
                return redirect(url_for("login_page"))
            if allowed_roles and user.get("role") not in allowed_roles:
                return render_template("403.html"), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
```
`from functools import wraps` is already imported at line 3 — no new import needed.

---

### `app.py` — `login_page()` POST handler upgrade (lines 136-152)

**Analog:** existing `login_page()` lines 136-152

**Existing handler to upgrade:**
```python
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if session.get("logged_in"):
        return redirect(url_for("admin_page"))
    error = None
    if request.method == "POST":
        cfg = load_config()
        username = request.form.get("username", "")
        password = request.form.get("password", "").encode()
        stored_hash = cfg.get("password_hash", "").encode()
        if username == cfg.get("username") and stored_hash and bcrypt.checkpw(password, stored_hash):
            session["logged_in"] = True
            session["username"] = username
            next_url = request.args.get("next", url_for("admin_page"))
            return redirect(next_url)
        error = "Неверный логин или пароль"
    return render_template("login.html", error=error)
```

**Upgrade points:**
- Replace `session.get("logged_in")` guard with `session.get("user_id")`
- Replace `load_config()` lookup with `load_users()` + username search
- Replace `session["logged_in"] = True` with `session["user_id"]`, `session["role"]`, `session["org_id"]`, `session["dept_id"]`
- Replace single redirect with role-based redirect table: `superadmin`/`org_admin`/`dept_admin` → `url_for("admin_page")`; `viewer`/`employee` → `url_for("dashboard_page")`
- Keep `bcrypt.checkpw(password, user["password_hash"].encode())` pattern — `.encode()` on both sides (existing line 146 already does `.encode()` on password)

**Error string to keep:** `"Неверный логин или пароль"` (line 151, Russian UI)

---

### `app.py` — existing `@login_required` routes upgraded to `@require_role`

**Analog:** `app.py` lines 159-167

**Existing decoration pattern:**
```python
@app.route("/register")
@login_required
def register_page():
    return render_template("register.html")

@app.route("/admin")
@login_required
def admin_page():
    return render_template("admin.html")
```

Replace `@login_required` with `@require_role(...)` passing appropriate role tuple:
- `/register` → `@require_role("superadmin", "org_admin", "dept_admin")`
- `/admin` → `@require_role("superadmin", "org_admin", "dept_admin")`
- All 8 API routes (employees, attendance, stats, register_face) → `@require_role("superadmin", "org_admin", "dept_admin")`

Kiosk routes (`GET /` line 131, `POST /api/recognize` line 264, `POST /api/detect` line 243) receive NO decorator.

---

### `app.py` — `POST /api/users` and `PATCH /api/users/<id>` (new routes)

**Analog:** `app.py` `add_employee()` lines 175-191 and `delete_employee()` lines 193-203

**CRUD POST pattern** (lines 175-191):
```python
@app.route("/api/employees", methods=["POST"])
def add_employee():
    data = request.json
    employees = load_employees()
    emp_id = str(int(time.time() * 1000))
    ...
    employees[emp_id] = { ... }
    save_employees(employees)
    return jsonify({"id": emp_id, "status": "created"})
```

New `POST /api/users` follows the same structure: `data = request.json`, `users = load_users()`, hierarchy check before write, `user_id = str(uuid.uuid4())`, `users[user_id] = {...}`, `save_users(users)`, return `jsonify({"id": user_id, "status": "created"})`.

**404 guard pattern** (lines 207-209):
```python
if emp_id not in employees:
    return jsonify({"error": "Сотрудник не найден"}), 404
```
New `PATCH /api/users/<id>` uses same guard: `if user_id not in users: return jsonify({"error": "Пользователь не найден"}), 404`.

**Hierarchy check for account creation** — new logic, no existing analog:
```python
creator_role = session.get("role")
target_role = request.json.get("role")
if (creator_role not in ROLE_HIERARCHY or
        target_role not in ROLE_HIERARCHY or
        ROLE_HIERARCHY.index(creator_role) >= ROLE_HIERARCHY.index(target_role)):
    return jsonify({"error": "forbidden"}), 403
```

---

### `templates/403.html` (new file)

**Analog:** `templates/login.html` lines 1-62

**Full page structure to copy from login.html:**
- DOCTYPE, `<html lang="ru">`, charset meta (lines 1-5)
- Inline `<style>` block: copy `.login-wrap`, `.card`, `.btn`, `body` rules (lines 7-26)
- `<div class="login-wrap">` outer wrapper (line 30)
- `.card` inner container (line 38)
- Logo block with `.logo-icon` and МедКонтроль branding (lines 31-36)

**Specific additions for 403:**
- `<h2>403 — Доступ запрещён</h2>`
- `<p class="sub">У вас нет прав для просмотра этой страницы.</p>`
- Back link using Jinja2: `{% if session.role in ['viewer','employee'] %}{{ url_for('dashboard_page') }}{% else %}{{ url_for('admin_page') }}{% endif %}`
- Link styled with `.btn` class

**CSS classes available from login.html (lines 7-26):** `.login-wrap`, `.card`, `.btn`, `.btn:hover`, `.error`, `.hint`, `h2`, `.sub`

---

### `templates/dashboard.html` (new file)

**Analog:** `templates/login.html` lines 1-62 (page shell); `templates/admin.html` lines 66-79 (header with logout)

**Page shell from login.html:** Same `body`, `.login-wrap`, `.card` CSS. Same DOCTYPE and head structure.

**Header from admin.html** (lines 66-73):
```html
<header>
  <div class="logo"><div class="logo-icon">🏥</div> МедКонтроль — Отчёты</div>
  <div class="header-right">
    <span class="user-badge">Администратор</span>
    <a href="/" class="btn-logout" style="border-color:#cfd8dc;color:#546e7a;">← Киоск</a>
    <a href="/logout" class="btn-logout">Выйти</a>
  </div>
</header>
```
Replace static "Администратор" with `{{ session.username }}` (or pass `username` from route handler). Replace "МедКонтроль — Отчёты" with "МедКонтроль — Личный кабинет".

**Content for dashboard:** Card with user name, role badge, message "Ваш личный кабинет будет доступен в следующем обновлении." (per D-09). Role displayed using `{{ session.role }}`.

---

### `templates/profile.html` (new file — password change)

**Analog:** `templates/login.html` form block lines 38-60

**Form pattern from login.html** (lines 46-55):
```html
<form method="POST">
  <div class="form-group">
    <label>Логин</label>
    <input type="text" name="username" placeholder="admin" autocomplete="username" autofocus required>
  </div>
  <div class="form-group">
    <label>Пароль</label>
    <input type="password" name="password" placeholder="••••••••" autocomplete="current-password" required>
  </div>
  <button type="submit" class="btn">Войти</button>
</form>
```
Profile form replaces username field with "Текущий пароль" (`name="current_password"`) and adds two password fields: "Новый пароль" (`name="new_password"`) and "Подтвердите пароль" (`name="confirm_password"`). Same `.form-group` / `label` / `input` / `.btn` structure.

**Error display pattern from login.html** (lines 42-44):
```html
{% if error %}
<div class="error">⚠ {{ error }}</div>
{% endif %}
```
Same pattern for profile — also add `{% if success %}<div class="success">{{ success }}</div>{% endif %}` with a green `.success` style class.

---

### `templates/admin.html` — header and nav upgrade

**Analog:** `templates/admin.html` lines 66-79 (existing header + nav-tabs)

**Existing header to extend** (lines 66-74):
```html
<header>
  <div class="logo"><div class="logo-icon">🏥</div> МедКонтроль — Отчёты</div>
  <div class="header-right">
    <span class="user-badge">Администратор</span>
    <a href="/" class="btn-logout" style="border-color:#cfd8dc;color:#546e7a;">← Киоск</a>
    <a href="/logout" class="btn-logout">Выйти</a>
  </div>
</header>
```
Replace `Администратор` static text with `{{ session.get('username', 'Администратор') }}`.

**Existing nav-tabs to extend** (lines 76-79):
```html
<div class="nav-tabs">
  <span class="tab active" id="tabJournal" onclick="switchTab('journal')">Журнал посещаемости</span>
  <span class="tab" id="tabStats" onclick="switchTab('stats')">Статистика за месяц</span>
</div>
```
Add user management tab conditionally:
```html
{% if session.role in ['superadmin', 'org_admin', 'dept_admin'] %}
  <span class="tab" id="tabUsers" onclick="switchTab('users')">Пользователи</span>
{% endif %}
```
Tab CSS classes already defined at line 19-21: `.tab`, `.tab.active`, `.tab:hover:not(.active)` — no new CSS needed.

---

## Shared Patterns

### JSON File Load/Save Helper
**Source:** `app.py` lines 26-34 (`load_config` / `save_config`)
**Apply to:** `load_users()` / `save_users()` in new Auth: Users section
```python
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

### bcrypt Password Verification
**Source:** `app.py` lines 144-146 (`login_page` POST handler)
**Apply to:** `login_page()` upgrade and `POST /profile` password change handler
```python
password = request.form.get("password", "").encode()
stored_hash = cfg.get("password_hash", "").encode()
bcrypt.checkpw(password, stored_hash)
```
Both arguments must be `bytes` — always call `.encode()` on strings from JSON and from form input.

### API Error Response Format
**Source:** `app.py` lines 207-209 (`reset_employee_face`)
**Apply to:** All new API routes (`/api/users`, `/api/users/<id>`)
```python
return jsonify({"error": "Сотрудник не найден"}), 404
```
Pattern: `jsonify({"error": "..."})` with appropriate 4XX status.

### Guard Clause / Early Return
**Source:** `app.py` lines 207-209, 225-227
**Apply to:** All new route handlers
```python
if emp_id not in employees:
    return jsonify({"error": "Сотрудник не найден"}), 404
```
Validate inputs at the top of handlers and return early rather than nesting logic.

### Jinja2 Session Variable Access
**Source:** Flask docs / existing `login.html` `{% if error %}` pattern (line 42)
**Apply to:** `admin.html` nav, `403.html` back-link, `dashboard.html` username display
```html
{% if session.role in ['superadmin', 'org_admin', 'dept_admin'] %}
  <!-- admin-only nav item -->
{% endif %}
```
Flask auto-injects `session` into Jinja2 template context — no `render_template(..., session=session)` needed.

### Section Header Convention
**Source:** `app.py` lines 24, 50, 86, 129, 169, 219, 262, 329, 416
**Apply to:** All new sections in `app.py`
```python
# ─── Auth: Users ──────────────────────────────────────────────────────────────
# ─── Auth: RBAC ───────────────────────────────────────────────────────────────
```

---

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/conftest.py` | test config | — | No test infrastructure exists; use pytest Flask test client pattern from RESEARCH.md |
| `tests/test_auth.py` | test | — | No tests exist; use RESEARCH.md validation architecture section |
| `tests/test_rbac.py` | test | — | No tests exist; use RESEARCH.md validation architecture section |

---

## Metadata

**Analog search scope:** `app.py` (423 lines, fully read), `templates/login.html` (62 lines, fully read), `templates/admin.html` (first 120 lines read for header/nav/CSS patterns)
**Files scanned:** 4 source files
**Pattern extraction date:** 2026-06-11
