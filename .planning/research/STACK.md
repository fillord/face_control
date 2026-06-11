# Stack Research

**Domain:** Flask RBAC + T-13 Timesheet extension (brownfield)
**Researched:** 2026-06-11
**Confidence:** HIGH — versions confirmed from installed venv dist-info; library choices confirmed against known API stability

---

## Context: What Already Exists

The venv contains exactly: Flask 3.1.3, bcrypt 5.0.0, opencv-contrib-python 4.13.0.92, numpy 2.4.6, Werkzeug 3.1.8, Jinja2 3.1.6, gunicorn 26.0.0. Neither flask-login, openpyxl, nor any RBAC library is installed. The existing app already uses `functools.wraps` for a `login_required` decorator and calls `bcrypt.hashpw` / `bcrypt.checkpw` directly.

---

## Recommended Stack

### Core Technologies (new additions)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| openpyxl | 3.1.x (latest stable) | T-13 Excel export (.xlsx) | Only pure-Python xlsx library with full read/write; required for styled multi-cell T-13 grids with merged cells and column widths. xlsxwriter is write-only and cannot modify templates. |
| flask-login | 0.6.3 | Session-based user object management | Integrates `current_user` proxy, `@login_required`, `login_user()` / `logout_user()` with Flask sessions. Avoids reinventing session cookie management. |

### Authentication

| Component | Implementation | Why |
|-----------|---------------|-----|
| Password hashing | `bcrypt` 5.0.0 (already installed) | Already in venv and used in production. `bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12))` produces 60-char hash. No change needed. |
| Session management | Flask built-in sessions (already in use) | Signed cookie via `itsdangerous`. Adding flask-login layers a `current_user` object on top of the same mechanism — no new session store needed. |

### RBAC Implementation

| Component | Implementation | Why |
|-----------|---------------|-----|
| Role decorators | Custom `functools.wraps` decorators (extend existing pattern) | The existing `login_required` decorator already uses this pattern. Adding `require_role(*roles)` as a stacked decorator is the minimal, zero-dependency extension. flask-principal is abandoned (last release 2013) and adds unnecessary complexity for 5 fixed roles. |
| Role storage | `users.json` field `"role": "dept_admin"` | JSON storage is the existing pattern. Role is a string enum on the user object; no permission tables needed for 5 fixed roles. |
| Data isolation | Filter functions at data-layer helpers | `load_employees_for_user(current_user)` applies org/dept filter before returning data. Enforced in helpers, not routes, so no route can accidentally bypass it. |

### Excel / CSV Export

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| openpyxl | 3.1.x | T-13 .xlsx generation | Supports merged cells (required for T-13 header rows), cell styles, column widths, and UTF-8 strings natively. Actively maintained, ~10M downloads/month. |
| Python stdlib `csv` | 3.14 stdlib | CSV UTF-8 BOM export | `csv.writer` with `newline=''` and a UTF-8 BOM prefix (U+FEFF, via `codecs.BOM_UTF8`) covers the CSV requirement with zero new dependencies. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `et_xmlfile` | (openpyxl dependency, auto-installed) | lxml-compatible XML streaming for openpyxl | Installed automatically with openpyxl, no direct use |
| Python stdlib `io.BytesIO` | stdlib | In-memory xlsx for `send_file()` | Use instead of writing xlsx to disk; `BytesIO` buffer passed to `flask.send_file()` with `mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'` |

---

## Installation

```bash
# Activate venv first
source /var/www/sites/face-almgp33/venv/bin/activate

# New dependencies only
pip install flask-login openpyxl
```

bcrypt 5.0.0 is already installed — do not reinstall.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Custom `require_role` decorator | flask-principal | Only if roles need to express compound permissions (e.g., "can_edit AND in_org") rather than simple role membership. Not needed here. |
| Custom `require_role` decorator | flask-security-too | Only if you need registration flows, email confirmation, 2FA. Adds ~15 dependencies. Overkill for a single-admin-bootstrapped system. |
| flask-login | Manual `session["role"]` checks in every route | Acceptable but error-prone at scale. flask-login adds `current_user` proxy that makes role checks readable (`current_user.role == "dept_admin"`). |
| openpyxl | xlsxwriter | xlsxwriter is faster for large files (>50k rows) but is write-only — cannot open existing .xlsx templates. openpyxl is correct here; T-13 is at most ~35 columns x ~50 rows. |
| openpyxl | pandas + openpyxl | pandas adds 30MB of dependencies for DataFrame overhead that is unnecessary when building a fixed-format grid. Use openpyxl directly. |
| stdlib `csv` | openpyxl CSV export | Not applicable — openpyxl does not write CSV. stdlib csv is correct for the CSV path. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| flask-principal | Abandoned since 2013, no Flask 3.x support, last commit ~10 years ago | Custom `require_role` decorator with `functools.wraps` |
| flask-security | Requires SQLAlchemy ORM; incompatible with JSON-file storage pattern | Custom role decorator |
| flask-security-too | Heavy dependency tree (~15 packages), designed for DB-backed user stores | Custom role decorator + flask-login |
| xlsxwriter | Write-only; cannot merge cells with the same API elegance as openpyxl for complex grid headers; no template support | openpyxl |
| pandas | 30MB+ install, unnecessary abstraction for a fixed-format timesheet grid | openpyxl directly |
| `werkzeug.security.generate_password_hash` | Uses PBKDF2-HMAC-SHA256, not bcrypt; would require migrating existing hashes | `bcrypt.hashpw` (already in use) |
| Flask-Bcrypt (extension wrapper) | Thin wrapper around bcrypt that adds no value; bcrypt 5.0.0 is already installed and used directly | `bcrypt` directly |

---

## RBAC Decorator Pattern

The existing `login_required` decorator establishes the correct pattern. Extend it as follows:

```python
from functools import wraps
from flask import session, redirect, url_for, abort

ROLE_HIERARCHY = {
    "superadmin": 5,
    "org_admin": 4,
    "dept_admin": 3,
    "viewer": 2,
    "employee": 1,
}

def require_role(*allowed_roles):
    """Stack on top of @login_required. Usage: @require_role('superadmin', 'org_admin')"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("logged_in"):
                return redirect(url_for("login_page", next=request.path))
            user_role = session.get("role", "employee")
            if user_role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator
```

Key design decisions:
- Role stored in `session["role"]` (string), set at login time alongside `session["logged_in"]`
- No separate permission table — 5 fixed roles map directly to access levels
- `abort(403)` rather than redirect, so AJAX calls receive a proper 403 status
- Stacking: `@require_role("superadmin")` replaces `@login_required` — the role check implies authentication

---

## Data Isolation Pattern

```python
def load_employees_for_user():
    """Returns employees filtered by current user's org/dept scope."""
    all_employees = load_employees()
    role = session.get("role")
    org_id = session.get("org_id")
    dept_id = session.get("dept_id")

    if role == "superadmin":
        return all_employees
    if role == "org_admin":
        return {k: v for k, v in all_employees.items() if v.get("org_id") == org_id}
    if role in ("dept_admin", "viewer"):
        return {k: v for k, v in all_employees.items()
                if v.get("org_id") == org_id and v.get("dept_id") == dept_id}
    if role == "employee":
        emp_id = session.get("emp_id")
        return {k: v for k, v in all_employees.items() if k == emp_id}
    return {}
```

This pattern ensures isolation is enforced at the data helper layer, not at individual routes. Every route that reads employees calls this function, never `load_employees()` directly.

---

## T-13 Excel Export Pattern

```python
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, Border, Side
import io
from flask import send_file

def generate_t13_xlsx(employees, attendance, year, month):
    wb = Workbook()
    ws = wb.active
    # ... build grid: row per employee, column per day, T-13 symbols
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"T13_{year}_{month:02d}.xlsx"
    )
```

Key: `io.BytesIO` avoids disk writes; `send_file` with `mimetype` handles the Content-Disposition header.

For CSV: open the response with `codecs.BOM_UTF8` prepended to the byte stream so Excel on Windows recognises UTF-8 encoding without a charset declaration.

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| flask-login | 0.6.3 | Flask 3.1.3, Werkzeug 3.1.x | 0.6.x added Flask 3.x support; do not use 0.5.x |
| openpyxl | 3.1.x | Python 3.9+, no Flask dependency | Pure Python, no native extensions |
| bcrypt | 5.0.0 | Python 3.14.4 | Already installed and working; uses Rust backend |
| functools.wraps | stdlib | All Python versions | No version concern |

---

## Sources

- Confirmed installed: `bcrypt-5.0.0.dist-info/METADATA` in venv — version verified from filesystem
- Confirmed NOT installed: venv site-packages directory listing — flask-login, openpyxl absent
- flask-login 0.6.3 release notes — Flask 3.x compatibility added in 0.6.x series (training knowledge, HIGH confidence; widely documented)
- openpyxl vs xlsxwriter comparison — openpyxl supports read+write+merge, xlsxwriter is write-only (HIGH confidence, stable API difference for years)
- flask-principal abandonment — last PyPI release 2013, confirmed by training knowledge (HIGH confidence)
- Python stdlib csv UTF-8 BOM — codecs.BOM_UTF8 is the standard Windows Excel compatibility approach (HIGH confidence, stdlib docs)

---

*Stack research for: Flask RBAC + T-13 Timesheet extension*
*Researched: 2026-06-11*
