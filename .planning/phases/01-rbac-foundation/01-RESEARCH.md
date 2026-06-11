# Phase 01: RBAC Foundation - Research

**Researched:** 2026-06-11
**Domain:** Flask RBAC, JSON user store, bcrypt auth, Jinja2 role-scoped navigation
**Confidence:** HIGH (all findings verified from live codebase and installed packages)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `users.json` schema: `id`, `username`, `password_hash`, `role`, `active`, `org_id` (null), `dept_id` (null).
- **D-02:** `ROLE_HIERARCHY = ['superadmin', 'org_admin', 'dept_admin', 'viewer', 'employee']`. Hierarchy enforced by index position — a role can only create accounts for roles with a higher index. No `parent_role` field.
- **D-03:** Bootstrap automatic on startup. If `data/users.json` absent: read `data/config.json`, copy existing `password_hash` verbatim into a superadmin entry (MIG-03). If no hash in config.json, create `superadmin / superadmin123` default. No manual script.
- **D-04:** `@require_role(*allowed_roles)` parameterized decorator on each route. All existing `@login_required` routes upgraded; `@login_required` retired.
- **D-05:** Three-step check order: (1) logged in → fail: redirect `/login`; (2) `active: true` → fail: redirect `/login` (not 403); (3) role in `allowed_roles` → fail: render `403.html` with HTTP 403.
- **D-06:** Unauthorized role: render `403.html` template with "Back to dashboard" link, HTTP 403.
- **D-07:** Session stores: `user_id`, `role`, `org_id`, `dept_id` (null for Phase 1).
- **D-08:** Post-login redirects: `superadmin`/`org_admin`/`dept_admin` → `/admin`; `viewer`/`employee` → `/dashboard`.
- **D-09:** `/dashboard` — single minimal page: user name, role, message "Ваш личный кабинет будет доступен в следующем обновлении."
- **D-10:** Stay monolithic in `app.py`. New sections: `# ─── Auth: Users ──────────────────` and `# ─── Auth: RBAC ──────────────────`. No blueprints.

### Claude's Discretion

- Navigation menu visibility per role (which links to show/hide in HTML templates).
- User management UI for Phase 1 (creating accounts one level below) — follow existing admin UI patterns.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | User can log in with username and password (bcrypt verified) | Login handler rewrite: `users.json` lookup + `bcrypt.checkpw()`. Existing pattern confirmed in `app.py` lines 136-152. |
| AUTH-02 | Default superadmin account created automatically on first run if `users.json` absent | Bootstrap in `init_users()` function; replace existing `init_config()` startup pattern. |
| AUTH-03 | Each role can create user accounts for roles one level below itself | `ROLE_HIERARCHY` index check in POST `/api/users` handler; `session['role']` index must be strictly less than target role index. |
| AUTH-04 | User session persists across browser refresh | Flask signed cookie sessions (via `itsdangerous`) persist across refresh by default; `session.permanent` optional. |
| AUTH-05 | Unauthenticated requests to protected routes redirect to `/login`; kiosk routes remain public | `@require_role` decorator step 1; kiosk routes (`GET /`, `POST /api/recognize`, `POST /api/detect`) remain undecorated. |
| AUTH-06 | User can change their own password from their profile page | New `GET/POST /profile` route + `PATCH /api/users/<id>/password`; bcrypt re-hash on change. |
| AUTH-07 | Admin can deactivate a user account without deleting it; deactivated user cannot log in | `active` field in `users.json`; `@require_role` step 2 checks `active`; deactivation via `PATCH /api/users/<id>`. |
| MIG-03 | Existing admin password hash copied verbatim from `config.json` to `users.json` without re-hashing | Confirmed: `config.json` uses key `password_hash`, value is `$2b$12$...` bcrypt hash — copy directly. |
| DASH-03 | After login, each role redirected to role-appropriate dashboard; nav shows only relevant links | Post-login redirect table in `login_page()` handler; Jinja2 `{% if session.role in [...] %}` for nav visibility. |
</phase_requirements>

---

## Summary

This phase is a brownfield extension of a working Flask app. The existing codebase already has `bcrypt` (v5.0.0), Flask sessions, and a `@login_required` decorator — all the infrastructure needed for RBAC exists and must be upgraded, not replaced from scratch.

The core work is: (1) add `users.json` as the user store with bootstrap migration from `config.json`; (2) replace `@login_required` with a parameterized `@require_role(*roles)` decorator; (3) upgrade the login handler to use `users.json`; (4) protect the 8 currently unprotected API routes; (5) add `/dashboard`, `/profile`, and `403.html` as new pages; and (6) add a user management UI so privileged roles can create accounts one level below.

No new Python packages are needed — all dependencies are already installed. The only new infrastructure is `pytest` (not installed) for Nyquist validation.

**Primary recommendation:** Follow the established `load_*/save_*` JSON helper pattern for `load_users()/save_users()`, follow the `@login_required` decorator structure for `@require_role`, and use `{% if session.role in [...] %}` for Jinja2 nav gating.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Authentication (login/logout) | API / Backend | — | Session state set server-side; cookie is signed by Flask secret key |
| Role enforcement | API / Backend | — | `@require_role` decorator runs before any handler; client cannot bypass |
| User management (create/deactivate) | API / Backend | Browser / Client | API validates hierarchy; UI collects input |
| Post-login routing | API / Backend | — | Redirect determined by `session['role']` server-side |
| Nav link visibility | Browser / Client (Jinja2 SSR) | — | HTML rendered server-side with `{% if session.role %}` |
| Password change | API / Backend | Browser / Client | Hash computed server-side; form collects current+new password |
| User store (users.json) | Database / Storage | — | JSON file on filesystem; read/write via Python helpers |
| 403 / dashboard pages | Frontend Server (SSR) | — | Jinja2 templates rendered on Flask server |

---

## Standard Stack

### Core (all already installed — no new packages)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1.3 | Routing, sessions, request handling | Project constraint; already in use |
| bcrypt | 5.0.0 | Password hashing and verification | Already installed; used in existing login handler |
| Jinja2 | 3.1.6 | HTML templating with session variables | Flask dependency; already in use |
| functools (stdlib) | Python 3.14 | `@wraps` for decorator metadata preservation | stdlib; already imported in `app.py` |

[VERIFIED: pip index versions] — all packages confirmed installed at listed versions.

### Supporting (new, for testing only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.3 | Test runner for Nyquist validation | Wave 0 setup; not installed yet |

[VERIFIED: pip index versions] — pytest 9.0.3 confirmed latest on PyPI.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled `@require_role` | Flask-Login | Flask-Login is overkill for single-file monolith; hand-rolled matches existing `@login_required` pattern exactly |
| Hand-rolled `@require_role` | Flask-Principal | Over-engineered for 5 static roles |
| JSON file users store | SQLite | Contradicts project constraint (JSON files in `data/`; no DB migration for v1) |

**Installation (testing only):**
```bash
/var/www/sites/face-almgp33/venv/bin/pip install pytest==9.0.3
```

---

## Package Legitimacy Audit

> No new runtime packages are introduced in this phase. All runtime dependencies are already installed in the venv. The legitimacy seam returned `SUS` for `bcrypt`, `flask`, and `jinja2` due to missing PyPI download count data — these are well-known, established packages confirmed via PyPI official registry.

| Package | Registry | Installed | Source Repo | Verdict | Disposition |
|---------|----------|-----------|-------------|---------|-------------|
| bcrypt | PyPI | 5.0.0 | github.com/pyca/bcrypt | SUS (download data unavailable via seam) | Approved — well-known package, already in venv, confirmed via `pip index versions` [VERIFIED: PyPI] |
| flask | PyPI | 3.1.3 | github.com/pallets/flask | SUS (download data unavailable via seam) | Approved — well-known package, already in venv, confirmed via `pip index versions` [VERIFIED: PyPI] |
| jinja2 | PyPI | 3.1.6 | github.com/pallets/jinja | SUS (download data unavailable via seam) | Approved — well-known package, already in venv, confirmed via `pip index versions` [VERIFIED: PyPI] |
| pytest | PyPI | not installed | github.com/pytest-dev/pytest | not checked | Test-only; install in Wave 0 |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious SUS:** bcrypt, flask, jinja2 — seam flagged due to missing download count data from PyPI API, not due to actual suspicion. All three are canonical Pallets/PyCA packages with decade-long histories. Already installed in project venv.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser
  │
  ├── GET /login  ──────────────────────────────────────────► login_page()
  │     └─ POST /login (username, password)                      │
  │           │                                                   │
  │           ▼                                              load_users()
  │       bcrypt.checkpw()                                        │
  │           │ pass                                         users.json
  │           ├── set session{user_id, role, org_id, dept_id}
  │           └── redirect based on role → /admin or /dashboard
  │
  ├── Any protected route ─────────────────────────────────► @require_role
  │           │                                                   │
  │           ├── step 1: session['user_id']? ──── no ──────► redirect /login
  │           ├── step 2: user['active']? ──────── no ──────► redirect /login
  │           └── step 3: role in allowed_roles? ── no ─────► render 403.html (HTTP 403)
  │                       │ yes
  │                       └──────────────────────────────────► route handler()
  │
  ├── GET/POST /profile ─────────────────────────────────────► profile_page()
  │     └─ own password change                                 bcrypt.hashpw()
  │                                                            save_users()
  │
  ├── POST /api/users ──────────────────────────────────────► create_user()
  │     └─ role hierarchy check                               ROLE_HIERARCHY index
  │        creator_idx < target_idx?                         load_users() / save_users()
  │
  └── Kiosk routes (GET /, POST /api/recognize, /api/detect)
        └── NO decorator — permanently public
```

### Recommended Project Structure

No structural changes — stay monolithic in `app.py`. New sections in order:

```
app.py sections (new additions):
  # ─── Auth: Users ──────────────────  (after existing # ─── Config / Auth ───)
  #   USERS_FILE constant
  #   load_users() / save_users()
  #   init_users() — bootstrap on startup
  #
  # ─── Auth: RBAC ──────────────────
  #   ROLE_HIERARCHY constant
  #   @require_role(*allowed_roles) decorator
  #
  (existing sections continue, @login_required retired)

New templates:
  templates/403.html          — simple forbidden page
  templates/dashboard.html    — viewer/employee landing (minimal)
  templates/profile.html      — password change page

No new directories needed.
```

### Pattern 1: @require_role Decorator

**What:** Parameterized decorator that enforces login + active + role checks.
**When to use:** On every route except kiosk routes (`GET /`, `POST /api/recognize`, `POST /api/detect`) and the login/logout routes.

```python
# Source: app.py existing @login_required pattern, extended
from functools import wraps

ROLE_HIERARCHY = ['superadmin', 'org_admin', 'dept_admin', 'viewer', 'employee']

def require_role(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return redirect(url_for('login_page', next=request.path))
            users = load_users()
            user = users.get(user_id)
            if not user or not user.get('active'):
                session.clear()
                return redirect(url_for('login_page'))
            if allowed_roles and user.get('role') not in allowed_roles:
                return render_template('403.html'), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
```

### Pattern 2: users.json Bootstrap

**What:** On startup, if `data/users.json` absent, create it by reading `data/config.json`.
**When to use:** Called from module-level startup (replacing `init_config()` call).

```python
# Source: app.py init_config() pattern, extended for MIG-03
import uuid

USERS_FILE = os.path.join(DATA_DIR, 'users.json')

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_users():
    if os.path.exists(USERS_FILE):
        return
    cfg = load_config()
    existing_hash = cfg.get('password_hash')
    if not existing_hash:
        existing_hash = bcrypt.hashpw(b'superadmin123', bcrypt.gensalt()).decode()
    user_id = str(uuid.uuid4())
    save_users({
        user_id: {
            'id': user_id,
            'username': 'superadmin',
            'password_hash': existing_hash,
            'role': 'superadmin',
            'active': True,
            'org_id': None,
            'dept_id': None
        }
    })
```

### Pattern 3: Login Handler Upgrade

**What:** Replace `config.json` lookup with `users.json` lookup; set new session fields.
**When to use:** In `login_page()` POST handler.

```python
# Source: app.py login_page() pattern, upgraded
if request.method == 'POST':
    username = request.form.get('username', '')
    password = request.form.get('password', '').encode()
    users = load_users()
    user = next((u for u in users.values()
                 if u['username'] == username), None)
    if user and user.get('active') and bcrypt.checkpw(
            password, user['password_hash'].encode()):
        session['user_id'] = user['id']
        session['role'] = user['role']
        session['org_id'] = user.get('org_id')
        session['dept_id'] = user.get('dept_id')
        # Role-based redirect (D-08)
        if user['role'] in ('superadmin', 'org_admin', 'dept_admin'):
            return redirect(url_for('admin_page'))
        return redirect(url_for('dashboard_page'))
    error = 'Неверный логин или пароль'
```

### Pattern 4: Privilege Hierarchy Check for Account Creation

**What:** Creator can only create accounts for roles strictly below their own.
**When to use:** In `POST /api/users` handler.

```python
# Source: D-02 / D-03 locked decisions
creator_role = session.get('role')
target_role = request.json.get('role')
if (creator_role not in ROLE_HIERARCHY or
        target_role not in ROLE_HIERARCHY or
        ROLE_HIERARCHY.index(creator_role) >= ROLE_HIERARCHY.index(target_role)):
    return jsonify({'error': 'forbidden'}), 403
```

### Pattern 5: Jinja2 Role-Scoped Navigation

**What:** Show/hide nav links based on `session.role`.
**When to use:** In `admin.html` header nav; add to all templates with navigation.

```html
{# Source: Jinja2 docs — session dict auto-injected into template context by Flask #}
{% if session.role in ['superadmin', 'org_admin'] %}
  <a href="/admin/orgs" class="tab">Организации</a>
{% endif %}
{% if session.role in ['superadmin', 'org_admin', 'dept_admin'] %}
  <a href="/admin/employees" class="tab">Сотрудники</a>
{% endif %}
```

### Anti-Patterns to Avoid

- **Client-side role gating only:** Never hide routes only in templates without server-side `@require_role`. The existing API routes (`/api/employees`, `/api/attendance`, etc.) have NO auth check — any unauthenticated user can call them directly via curl. This must be fixed in Phase 1.
- **Re-hashing the existing password:** The `$2b$12$F0kPJqHfW3hWU9QJm7kCyee3xD/...` hash from `config.json` must be copied verbatim to `users.json`. Do not pass it through `bcrypt.hashpw()` again — that would produce a hash of the hash, breaking login.
- **Checking `session['logged_in']`:** The old session key `logged_in` will not exist after the upgrade. All checks must use `session.get('user_id')`, not `session.get('logged_in')`.
- **Using `@login_required` after Phase 1:** The old decorator is retired. Remove it entirely so no route accidentally remains on the old check.
- **Deactivated user shown 403:** Per D-05, deactivated users must see a redirect to `/login`, not a 403. Only wrong-role gets 403.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom hash function | `bcrypt.hashpw() / checkpw()` | Already installed; bcrypt is the correct choice for passwords; custom hashes have timing attacks and weak entropy |
| Session signing | Manual cookie crypto | Flask's built-in signed cookies (itsdangerous) | Already in use; itsdangerous is tamper-evident; never roll cookie crypto |
| Privilege hierarchy math | Custom tree/graph | Index comparison on `ROLE_HIERARCHY` list | Simple list index diff is exact and fast for 5 static roles |
| UUID generation | Timestamp-based IDs | `uuid.uuid4()` (stdlib) | Timestamps collide under load; UUID4 is collision-resistant and stdlib |

**Key insight:** All the hard parts (hashing, session signing, HTML templating) are already solved by installed packages. This phase is pure plumbing — wiring the existing tools together correctly.

---

## Common Pitfalls

### Pitfall 1: Unprotected API Routes

**What goes wrong:** Eight API routes currently have no authentication: `GET /api/employees`, `POST /api/employees`, `DELETE /api/employees/<id>`, `POST /api/employees/<id>/reset`, `POST /api/register_face`, `GET /api/attendance`, `GET /api/attendance/dates`, `GET /api/stats`. The admin HTML calls these from JS, but any external caller can hit them without login.

**Why it happens:** The existing app had a single admin user with basic protection only on page routes. API routes were assumed to be called only from the admin UI.

**How to avoid:** Every API route that mutates data or reads sensitive data must get `@require_role`. Use `'superadmin', 'org_admin', 'dept_admin'` for employee/attendance management routes.

**Warning signs:** `curl http://localhost:5051/api/employees` returning data without any auth header.

### Pitfall 2: Bytes/String Type Confusion in bcrypt

**What goes wrong:** `bcrypt.checkpw(password, stored_hash)` requires both arguments to be `bytes`. If `stored_hash` is loaded from JSON as a `str`, calling `checkpw` without `.encode()` raises `TypeError`.

**Why it happens:** JSON stores strings; bcrypt needs bytes. Easy to miss.

**How to avoid:** Always call `user['password_hash'].encode()` and `password.encode()` before passing to bcrypt. The existing login handler already does `request.form.get("password", "").encode()` — follow this pattern.

**Warning signs:** `TypeError: Unicode-objects must be encoded before hashing` in logs.

### Pitfall 3: Gunicorn 2-Worker Race on JSON Writes

**What goes wrong:** The PM2 config currently runs `gunicorn -w 2`, meaning two worker processes share the same `data/` filesystem. Concurrent writes to `users.json` (e.g., two simultaneous account creations) can corrupt the file.

**Why it happens:** The existing JSON helpers write the whole file on every save with no locking. Single-worker was the assumption, but the current PM2 config uses `-w 2`.

**How to avoid:** For Phase 1, the simplest safe approach is to wrap `save_users()` with `fcntl.flock()` advisory locking (same as the STATE.md note recommends). Alternatively, reduce to `-w 1` in PM2 config. Document the constraint.

**Warning signs:** Truncated or empty `users.json` after concurrent requests.

[ASSUMED] — The PM2 config `-w 2` was observed live but whether this is intentional or should be `-w 1` per the STATE.md constraint ("PM2 must run single Flask worker") is unclear. The planner should add a task to confirm and align.

### Pitfall 4: Session Key Mismatch After Upgrade

**What goes wrong:** After upgrading the login handler to set `session['user_id']` instead of `session['logged_in']`, any user who was logged in before the restart will have a stale session without `user_id`. Their next request will hit `@require_role`, fail step 1, and redirect to login. This is correct behavior — but it means all current sessions are invalidated on deploy.

**Why it happens:** Session schema change without session invalidation.

**How to avoid:** This is acceptable behavior — just document that all users must re-login after Phase 1 deploys. No mitigation needed; it's a one-time inconvenience.

**Warning signs:** None — this is expected and correct.

### Pitfall 5: Bootstrap Runs on Every Gunicorn Worker Startup

**What goes wrong:** `init_users()` is called at module load time (like `init_config()` is now). With 2 gunicorn workers, both workers call `init_users()` on startup. If `users.json` doesn't exist yet, both workers may try to create it simultaneously — file race.

**Why it happens:** Module-level initialization runs in each worker process.

**How to avoid:** Use an existence check with `fcntl.flock()` inside `init_users()`, or use Python's `os.O_CREAT | os.O_EXCL` flag to atomically create the file. Simplest: check existence first; if it exists, return; the race only happens once on first-ever startup.

**Warning signs:** `users.json` missing or corrupt after first deploy.

---

## Code Examples

### users.json Schema

```json
{
  "a1b2c3d4-e5f6-...": {
    "id": "a1b2c3d4-e5f6-...",
    "username": "superadmin",
    "password_hash": "$2b$12$F0kPJqHfW3hWU9QJm7kCyee3xD/eYhdcBwwmWgBvXuC9wqwKyPMym",
    "role": "superadmin",
    "active": true,
    "org_id": null,
    "dept_id": null
  }
}
```

### 403.html Minimal Template (follows existing UI style)

```html
{# Source: existing login.html / admin.html style patterns #}
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Доступ запрещён — МедКонтроль</title>
<!-- same CSS as login.html base -->
</head>
<body>
<div class="login-wrap">
  <div class="card">
    <h2>403 — Доступ запрещён</h2>
    <p class="sub">У вас нет прав для просмотра этой страницы.</p>
    <a href="{{ url_for('dashboard_page') if session.role in ['viewer','employee'] else url_for('admin_page') }}"
       class="btn" style="margin-top:16px;display:block;text-align:center;">
      ← Вернуться к панели
    </a>
  </div>
</div>
</body>
</html>
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Single admin via `config.json` + `@login_required` | Multi-user `users.json` + `@require_role` | Enables 5-role hierarchy; old decorator retired |
| `session['logged_in']` boolean | `session['user_id', 'role', 'org_id', 'dept_id']` | Richer session for Phase 2 scoping |
| `init_config()` on startup | `init_users()` on startup | Bootstrap migrates existing hash (MIG-03); no re-hash |

**Deprecated/outdated after Phase 1:**
- `@login_required` decorator: removed and replaced by `@require_role`
- `config.json` as auth store: superseded by `users.json`; `config.json` kept for app settings but no longer checked on login
- `session['logged_in']`: key removed from all session writes/reads

---

## Runtime State Inventory

> This phase renames the auth mechanism (config.json → users.json) and changes session keys — potential runtime state migration needed.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `data/config.json` — contains `password_hash` and `username: "admin"` fields used for current login auth | Code migration only: `init_users()` reads hash verbatim on first run; no data deletion needed |
| Stored data | `data/users.json` — does NOT exist yet | Bootstrap creates it on first startup via `init_users()` |
| Live service config | PM2 `face-recognition` process: `gunicorn -w 2 -b 127.0.0.1:5051 app:app` — 2 workers active | STATE.md says single worker required; verify and align (possibly reduce to `-w 1`) |
| OS-registered state | PM2 process saved state: process name "face-recognition" is unchanged | No action — PM2 restart uses same name; `pm2 restart face-recognition` works as-is |
| Secrets/env vars | `SECRET_KEY` env var: not injected via PM2; app falls back to hardcoded `"medkontrol-secret-2026-xK9mP3qR7v"` | STATE.md flagged this as a concern; planner should add task to inject SECRET_KEY via PM2 env or `.env` file |
| Build artifacts | venv at `/var/www/sites/face-almgp33/venv/` — no rename involved | No action needed |

**Active user sessions:** All existing sessions use `session['logged_in']`. After Phase 1 deploy, these sessions are invalidated (no `user_id` key). Users must re-login. This is correct behavior.

---

## Open Questions

1. **Gunicorn worker count vs. single-worker constraint**
   - What we know: STATE.md says "PM2 must run single Flask worker"; PM2 config actually runs `gunicorn -w 2`
   - What's unclear: Was `-w 2` intentional or an oversight? Is the fcntl locking already in place somewhere?
   - Recommendation: Add a task to align PM2 config to `-w 1` OR add `fcntl.flock()` to all `save_*()` helpers. The planner should decide and include one of these tasks.

2. **SECRET_KEY injection**
   - What we know: Secret key is currently a hardcoded fallback. STATE.md flagged this as a pre-Phase-1 concern.
   - What's unclear: Is there a `.env` file or PM2 env injection already configured that isn't visible in the process listing?
   - Recommendation: Add a task to set `SECRET_KEY` as a PM2 environment variable (`pm2 set ...` or ecosystem.config.js). Hardcoded key is technically functional but a security concern under ASVS V3.

3. **User management UI scope**
   - What we know: CONTEXT.md leaves user management UI to Claude's discretion. The existing admin.html has a tabbed layout pattern.
   - What's unclear: Should user management be a new tab in `admin.html` or a separate page?
   - Recommendation: Add as a new tab in `admin.html` following the existing tab pattern (cleaner; single-page admin experience). Claude's call per CONTEXT.md.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | All code | Yes | 3.14.4 | — |
| Flask | Core framework | Yes | 3.1.3 | — |
| bcrypt | Password hashing | Yes | 5.0.0 | — |
| Jinja2 | Templates | Yes | 3.1.6 | — |
| functools (stdlib) | `@wraps` | Yes | stdlib | — |
| uuid (stdlib) | User ID generation | Yes | stdlib | — |
| fcntl (stdlib) | File locking | Yes | stdlib | — |
| pytest | Test runner | No | 9.0.3 available | Install in Wave 0: `pip install pytest==9.0.3` |
| PM2 | Process restart | Yes | running | — |

**Missing dependencies with no fallback:** none

**Missing dependencies with fallback:**
- `pytest` — not installed; install in Wave 0 before writing tests

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (not yet installed) |
| Config file | `pytest.ini` — none; Wave 0 creates `tests/conftest.py` |
| Quick run command | `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -x -q` |
| Full suite command | `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Login with valid bcrypt credentials succeeds; invalid fails | unit | `pytest tests/test_auth.py::test_login_valid -x` | Wave 0 |
| AUTH-02 | `init_users()` creates superadmin when `users.json` absent | unit | `pytest tests/test_auth.py::test_init_users_bootstrap -x` | Wave 0 |
| AUTH-02 | MIG-03: hash from `config.json` copied verbatim | unit | `pytest tests/test_auth.py::test_init_users_migrates_hash -x` | Wave 0 |
| AUTH-03 | `dept_admin` can create `viewer`; `viewer` cannot create any | unit | `pytest tests/test_rbac.py::test_privilege_hierarchy -x` | Wave 0 |
| AUTH-04 | Session persists `user_id`, `role`, `org_id`, `dept_id` | unit | `pytest tests/test_auth.py::test_session_contents -x` | Wave 0 |
| AUTH-05 | Unauthenticated request to `/admin` redirects to `/login` | unit | `pytest tests/test_rbac.py::test_unauthenticated_redirect -x` | Wave 0 |
| AUTH-05 | `GET /`, `/api/recognize`, `/api/detect` accessible without auth | unit | `pytest tests/test_rbac.py::test_public_routes -x` | Wave 0 |
| AUTH-06 | Password change with correct current password succeeds | unit | `pytest tests/test_auth.py::test_password_change -x` | Wave 0 |
| AUTH-07 | Deactivated user login attempt is rejected | unit | `pytest tests/test_auth.py::test_deactivated_user -x` | Wave 0 |
| DASH-03 | `superadmin` login redirects to `/admin`; `viewer` to `/dashboard` | unit | `pytest tests/test_rbac.py::test_post_login_redirect -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -x -q`
- **Per wave merge:** `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/conftest.py` — Flask test client fixture with `app.testing = True`, temp `data/` directory
- [ ] `tests/test_auth.py` — covers AUTH-01, AUTH-02, MIG-03, AUTH-04, AUTH-06, AUTH-07
- [ ] `tests/test_rbac.py` — covers AUTH-03, AUTH-05, DASH-03
- [ ] Framework install: `/var/www/sites/face-almgp33/venv/bin/pip install pytest==9.0.3`

---

## Security Domain

### Applicable ASVS Categories (Level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | bcrypt `checkpw()` — already installed; no plain-text passwords |
| V3 Session Management | Yes | Flask signed cookies via itsdangerous; `SECRET_KEY` must be env var (not hardcoded) |
| V4 Access Control | Yes | `@require_role` server-side check; client-side nav hiding is supplemental only |
| V5 Input Validation | Yes | Validate username/password lengths; validate `role` field against `ROLE_HIERARCHY` whitelist on user creation |
| V6 Cryptography | No | No custom crypto; bcrypt handles password hashing |

### Known Threat Patterns for Flask + JSON auth

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Session fixation | Spoofing | `session.clear()` before setting new session on login (Flask does this with `session.regenerate()` in newer versions; manually clear then repopulate) |
| Privilege escalation via API | Elevation of Privilege | Server-side `ROLE_HIERARCHY` index check in `POST /api/users`; never trust client-supplied role |
| Hardcoded SECRET_KEY | Information Disclosure | Replace `"medkontrol-secret-2026-xK9mP3qR7v"` with env var injection; hardcoded key means any code reader can forge sessions |
| Mass assignment on user create | Tampering | Whitelist fields accepted from request JSON; never `user.update(request.json)` |
| Unauthenticated API access | Spoofing | Apply `@require_role` to all 8 currently unprotected API routes |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PM2 gunicorn `-w 2` is current config and not a display artifact | Runtime State Inventory | If actually running `-w 1`, the file locking concern is moot — but `fcntl.flock()` is harmless either way |
| A2 | `users.json` does not exist (confirmed by `ls` check) | Bootstrap pattern | If somehow users.json already exists, bootstrap is skipped — correct behavior |
| A3 | SECRET_KEY is not injected via any mechanism not visible in `pm2 env 5` output | Security Domain | If SECRET_KEY IS set somewhere, the hardcoded fallback never runs — concern is moot |

---

## Project Constraints (from CLAUDE.md)

The following directives are extracted from `CLAUDE.md` and must be honored by the planner:

1. **Tech stack:** Flask + Python only — no framework migration, extend in place
2. **Storage:** JSON files in `data/` — no DB migration for v1
3. **Python:** 3.14.4 on venv at `/var/www/sites/face-almgp33/venv/bin/python`
4. **Deployment:** `pm2 restart face-recognition` is the final deploy step
5. **Isolation:** Data isolation must be enforced server-side, not just hidden in UI
6. **Code style:** snake_case functions, CONSTANT_CASE module-level constants, section headers `# ─── Name ───────────────────`
7. **Module design:** Single monolithic `app.py` — no blueprints, no module splits
8. **No type hints:** No type annotations in `app.py` (project convention)
9. **Import organization:** No frontend modules; all JS inline in `<script>` blocks
10. **Section headers:** Use Unicode box-drawing: `# ─── Section Name ───────────────────`
11. **Error handling:** API errors via `jsonify({...}), 4XX`; UI errors via template rendering
12. **GSD workflow:** All file changes via GSD workflow (`/gsd-execute-phase`)

---

## Sources

### Primary (codebase — highest confidence)
- `/var/www/sites/face-almgp33/app.py` — existing `@login_required`, login handler, session usage, route list [VERIFIED: direct read]
- `/var/www/sites/face-almgp33/data/config.json` — `password_hash` key confirmed, `$2b$12$` hash prefix verified [VERIFIED: direct read]
- `/var/www/sites/face-almgp33/templates/login.html`, `admin.html`, `register.html` — UI patterns confirmed [VERIFIED: direct read]

### Secondary (package registry)
- PyPI: `bcrypt 5.0.0`, `flask 3.1.3`, `jinja2 3.1.6`, `pytest 9.0.3` confirmed via `pip index versions` [VERIFIED: PyPI registry]
- venv: All runtime packages confirmed installed via `pip show` and `python -c "import ..."` [VERIFIED: venv import test]

### Tertiary (training knowledge, ASSUMED)
- Flask signed cookie session behavior (itsdangerous) [ASSUMED] — well-established, but not verified via Context7 this session
- `fcntl.flock()` advisory locking pattern for Linux file safety [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed in live venv
- Architecture: HIGH — all patterns derived from existing `app.py` code
- Route audit: HIGH — grepped live `app.py`; 8 unprotected routes confirmed
- Bootstrap/MIG-03: HIGH — `config.json` key names and hash format confirmed by direct read
- File locking concern: MEDIUM — gunicorn `-w 2` confirmed; locking recommendation is ASSUMED best practice
- Security (ASVS): MEDIUM — ASVS categories applied from training knowledge; no external verification

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (stable stack; Flask/bcrypt APIs are stable)
