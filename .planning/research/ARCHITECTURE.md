# Architecture Research

**Domain:** Flask monolith brownfield extension — RBAC + org hierarchy + T-13 timesheet
**Researched:** 2026-06-11
**Confidence:** HIGH (based on direct codebase analysis of app.py and data structures)

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Presentation Layer (Jinja2 templates)                        │
│  kiosk.html [PUBLIC]  login.html  admin.html  register.html  │
│  + new: dashboard.html  timesheet.html  employee-cabinet.html │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP / fetch()
┌──────────────────────▼───────────────────────────────────────┐
│  Route Layer  (app.py, extended)                              │
│                                                               │
│  [PUBLIC]           [AUTH-GATED — RBAC decorator]            │
│  GET /              /admin  /register                         │
│  POST /api/recognize /api/employees  /api/timesheet          │
│  POST /api/detect   /api/attendance  /api/export             │
│                     /api/orgs  /api/depts                     │
└──────────────────────┬───────────────────────────────────────┘
                       │ direct function calls
┌──────────────────────▼───────────────────────────────────────┐
│  Auth / RBAC Layer  (auth.py — new module)                    │
│  login_required()   role_required(*roles)                     │
│  get_current_user() session["user_id","role","org_id","dept"] │
│  bcrypt verify      scope_filter(query, user)                 │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│  Data Access Layer  (data_helpers.py — new module)            │
│  load/save for each store with isolation enforcement          │
│  get_employees_for_user(user)  ← scope filter lives HERE     │
│  get_attendance_for_user(user, date_range)                    │
│  build_timesheet(employees, attendance, month)                │
│  export_xlsx(timesheet)  export_csv(timesheet)                │
└──────────────────────┬───────────────────────────────────────┘
                       │ load_*/save_* helpers (unchanged API)
┌──────────────────────▼───────────────────────────────────────┐
│  JSON Storage Layer                                           │
│  data/users.json        ← NEW  (user accounts, all roles)    │
│  data/orgs.json         ← NEW  (org records)                 │
│  data/depts.json        ← NEW  (dept records, org-linked)    │
│  data/employees.json    ← EXTENDED (add org_id, dept_id)     │
│  data/attendance.json   ← UNCHANGED (date→emp_id→in/out)     │
│  data/config.json       ← UNCHANGED then phased out          │
│  data/logs.json         ← UNCHANGED                          │
│  data/faces/{id}/       ← UNCHANGED                          │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With | Location |
|-----------|---------------|-------------------|----------|
| **RBAC decorators** | Enforce role + scope on every protected route | Route layer (wraps handlers) | `auth.py` |
| **Session manager** | Store user_id, role, org_id, dept_id in Flask session | Login route, all protected routes | `auth.py` |
| **Scope filter** | Translate user role into employee ID whitelist | Data access layer only — never route layer | `data_helpers.py` |
| **User store** | Persist user accounts with bcrypt hashes | Auth layer, admin routes | `data/users.json` |
| **Org store** | Persist organization records | Superadmin routes, scope filter | `data/orgs.json` |
| **Dept store** | Persist department records (org-linked) | Org admin routes, scope filter | `data/depts.json` |
| **Employee store** | Persist employee records (dept-linked) | All roles, face recognition engine | `data/employees.json` |
| **Attendance store** | Persist daily check-in/out | Kiosk (write), all roles (read via scope) | `data/attendance.json` |
| **Timesheet engine** | Build T-13 grid from attendance + schedules | Dept admin, viewer, employee cabinet | `timesheet.py` |
| **Export engine** | Render T-13 to Excel/CSV | Timesheet routes | `export.py` |
| **Face/CV engine** | Recognition + training (unchanged) | Kiosk route only | `app.py` globals |

**Hard rule:** The scope filter is the only place that converts a user's role/org/dept into a list of employee IDs it can see. No route may build its own filter — all employee/attendance queries go through `get_employees_for_user(user)`.

---

## Recommended Project Structure

```
/var/www/sites/face-almgp33/
├── app.py                    # Routes only — no inline business logic
├── auth.py                   # NEW: RBAC decorators, session helpers, bcrypt
├── data_helpers.py           # NEW: all load/save + scope-filtered queries
├── timesheet.py              # NEW: T-13 grid builder + schedule logic
├── export.py                 # NEW: openpyxl Excel + CSV UTF-8 BOM writer
├── migrations/
│   └── 001_add_org_dept.py   # NEW: migrate flat employees → default org+dept
├── templates/
│   ├── kiosk.html            # UNCHANGED
│   ├── login.html            # MINOR CHANGE: extends base
│   ├── register.html         # UNCHANGED (admin-only, RBAC wraps route)
│   ├── admin.html            # EXTENDED: org/dept/user management tabs
│   ├── dashboard.html        # NEW: role-aware landing after login
│   ├── timesheet.html        # NEW: T-13 grid view + export buttons
│   └── employee_cabinet.html # NEW: self-service view for employee role
└── data/
    ├── users.json            # NEW
    ├── orgs.json             # NEW
    ├── depts.json            # NEW
    ├── employees.json        # EXTENDED (org_id, dept_id, schedule fields)
    ├── attendance.json       # UNCHANGED
    ├── config.json           # LEGACY (kept for bcrypt; superadmin migrates from it)
    ├── logs.json             # UNCHANGED
    └── faces/                # UNCHANGED
```

### Structure Rationale

- **auth.py extracted:** The existing `login_required` decorator lives in `app.py`. Moving auth to a separate module lets the migration proceed without touching CV code. `app.py` imports from `auth.py`.
- **data_helpers.py extracted:** Current `load_employees()` / `save_employees()` are thin. The scope filter must wrap these — extracting to a module keeps the concern isolated.
- **timesheet.py / export.py separate:** These are pure functions (no Flask dependency). Keeping them outside `app.py` makes them testable and prevents the monolith from growing further.
- **No blueprints:** At this scale (one server, one app), Flask blueprints add indirection without benefit. Module extraction achieves the same boundary without restructuring URL layout.

---

## Architectural Patterns

### Pattern 1: Role-Scope Decorator Stack

**What:** Two decorators compose: `@login_required` ensures a session exists; `@role_required("dept_admin", "org_admin")` checks session role. All protected routes use both.

**When to use:** Every route except `GET /`, `POST /api/recognize`, `POST /api/detect`, and `GET|POST /login`.

**Trade-offs:** Simple and explicit. Downside: role list must be correct on each route — easy to miss. Mitigate by defaulting to most-restrictive role when unsure.

**Example:**
```python
# auth.py
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user or user["role"] not in roles:
                return jsonify({"error": "forbidden"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

# app.py
@app.route("/api/timesheet")
@login_required
@role_required("superadmin", "org_admin", "dept_admin", "viewer", "employee")
def get_timesheet():
    user = get_current_user()
    employees = get_employees_for_user(user)
    ...
```

### Pattern 2: Scope Filter at Data Layer

**What:** `get_employees_for_user(user)` returns only the employee IDs the user is authorized to see. Every downstream query (attendance, timesheet, stats) accepts this filtered list, never the full dataset.

**When to use:** Every read operation on employees or attendance.

**Trade-offs:** Single enforcement point — bug here affects everything. But this is the correct trade-off: one place to audit, one place to fix.

**Example:**
```python
# data_helpers.py
def get_employees_for_user(user):
    all_emps = load_employees()
    role = user["role"]
    if role == "superadmin":
        return all_emps                              # sees all
    if role == "org_admin":
        return {k: v for k, v in all_emps.items()
                if v.get("org_id") == user["org_id"]}
    if role in ("dept_admin", "viewer"):
        return {k: v for k, v in all_emps.items()
                if v.get("dept_id") == user["dept_id"]}
    if role == "employee":
        emp_id = user.get("emp_id")
        return {emp_id: all_emps[emp_id]} if emp_id in all_emps else {}
    return {}
```

### Pattern 3: T-13 Timesheet as Pure Function

**What:** `build_timesheet(employees, attendance, year, month, schedules)` returns a plain dict/list structure. It has no Flask dependency and no file I/O. Routes call it, pass result to template or exporter.

**When to use:** Every timesheet view and every export request.

**Trade-offs:** Decouples calendar logic from HTTP concerns. Export and view share the same grid calculation. Slightly more plumbing in routes (two calls: build then render/export).

**T-13 symbol mapping:**
```python
# timesheet.py
SYMBOLS = {
    "present":   "Я",   # явка (present, standard day)
    "overtime":  "С",   # сверхурочно (overtime)
    "weekend":   "В",   # выходной (weekend/day off)
    "vacation":  "О",   # отпуск (annual leave)
    "sick":      "Б",   # болезнь (sick leave, self-cert)
    "sick_doc":  "Т",   # нетрудоспособность с документом
    "absent":    "П",   # прогул (unexcused absence)
    "training":  "У",   # учёба (training/study leave)
}

def build_timesheet(employees, attendance, year, month, schedules):
    """Return {emp_id: {day: symbol, ...}, totals: {...}}"""
    ...
```

---

## Data Flow

### RBAC Request Flow

```
Browser request
    │
    ▼
Flask route handler
    │
    ├─ @login_required → check session["user_id"] → 401 if missing
    │
    ├─ @role_required(*roles) → check session["role"] in roles → 403 if not
    │
    ▼
get_current_user()  →  reads session → returns {user_id, role, org_id, dept_id, emp_id}
    │
    ▼
get_employees_for_user(user)  →  scope filter → filtered {emp_id: emp} dict
    │
    ▼
Business logic (timesheet / attendance query) operates ONLY on filtered employees
    │
    ▼
JSON response / template render
```

### Role Creation Flow (Hierarchical)

```
superadmin  →  can create: org_admin, dept_admin, viewer, employee
org_admin   →  can create: dept_admin, viewer, employee (own org only)
dept_admin  →  can create: viewer, employee (own dept only)
viewer      →  cannot create users
employee    →  cannot create users
```

Enforcement: `role_required` on user-creation route + validation that `new_role_level < current_user_level`.

### Kiosk Flow (Unchanged)

```
GET / → kiosk.html (no auth check, unchanged)
    ↓
POST /api/recognize (no auth check, unchanged)
    ↓
train_recognizer() / recognizer.predict()
    ↓
load_employees() — returns ALL employees (kiosk is org-agnostic)
    ↓
save_attendance() — writes to data/attendance.json (unchanged schema)
```

The kiosk deliberately bypasses RBAC. It reads the full employee set because face recognition requires all trained labels. This is correct: the kiosk is a physical device, not a human user.

### T-13 Export Flow

```
GET /api/timesheet/export?format=xlsx&month=2026-06
    │
    ├─ @login_required + @role_required(all except public)
    │
    ▼
get_current_user() → scope-filtered employees
    │
    ▼
load_attendance() filtered by date range (month) and emp_id whitelist
    │
    ▼
build_timesheet(employees, attendance, year, month, schedules)
    →  returns grid: {emp_id: {1: "Я", 2: "В", ...}, totals: {...}}
    │
    ├─ format=xlsx → export_xlsx(grid) → BytesIO → send_file(mimetype=openpyxl)
    └─ format=csv  → export_csv(grid) → BytesIO UTF-8 BOM → send_file
```

---

## Migration Strategy

### Phase 0: Data Schema Migration

Before any RBAC code runs, existing data must be upgraded. A one-time migration script (`migrations/001_add_org_dept.py`) performs:

1. Create `data/users.json` with superadmin entry (bcrypt hash of `superadmin123`)
2. Create `data/orgs.json` with one default org (`org_id: "org_default"`)
3. Create `data/depts.json` with one default dept (`dept_id: "dept_default"`, linked to `org_default`)
4. Rewrite `data/employees.json`: add `org_id: "org_default"`, `dept_id: "dept_default"` to every existing record, add `schedule: {type: "standard", hours: 8, days: [1,2,3,4,5]}`
5. Leave `data/config.json` intact — old admin credentials remain valid until superadmin logs in and migrates

**Run once, idempotent**: if `users.json` already exists and has entries, migration is a no-op.

### Build Order

The dependency graph forces this sequence:

```
1. auth.py module         ← RBAC decorators, no data dependency
        ↓
2. data schema migration  ← extends employees.json, creates users/orgs/depts
        ↓
3. data_helpers.py        ← scope filter depends on new schema fields
        ↓
4. User/org/dept CRUD routes  ← depend on data_helpers + RBAC
        ↓
5. timesheet.py           ← depends on extended employee + attendance data
        ↓
6. export.py              ← depends on timesheet.py output
        ↓
7. UI templates           ← depend on all routes being present
```

**Do not skip steps.** Specifically: do not add timesheet routes before the scope filter is in place — an unguarded `/api/timesheet` would expose all employee data.

---

## Splitting app.py Safely

The existing `app.py` is 423 lines. The split must not break the kiosk.

**Safe split strategy:**

1. Create `auth.py`. Move `login_required` decorator and `init_config()` logic there. In `app.py`, replace with `from auth import login_required, get_current_user`. Run kiosk test — it should be unaffected (kiosk route has no auth import).

2. Create `data_helpers.py`. Copy (do not move yet) `load_employees`, `save_employees`, `load_attendance`, `save_attendance`, `append_log` there. Add new scope-filtered variants. In `app.py`, import both old and new. Remove duplicates after all routes updated.

3. Create `timesheet.py` and `export.py` as pure new files — no risk to existing routes.

4. New routes are additive: append to `app.py` without touching existing route functions.

**Kiosk safety invariant:** `GET /` calls `load_employees()` directly, not the scoped variant. This must remain. The kiosk route should never import `get_employees_for_user`.

---

## Anti-Patterns

### Anti-Pattern 1: RBAC in Templates (UI-Only Isolation)

**What people do:** Hide admin buttons in Jinja2 with `{% if session.role == 'admin' %}`. Don't add backend checks.

**Why it's wrong:** Any authenticated user can `curl /api/attendance` and get all data. Template guards are presentation, not security.

**Do this instead:** Enforce scope filter in `data_helpers.py`. Templates may additionally hide UI elements, but that is cosmetic only.

### Anti-Pattern 2: Scope Filter Scattered Across Routes

**What people do:** Each route independently checks `if user.org_id == emp.org_id`. Copy-paste across 10 routes.

**Why it's wrong:** One missed check = data leak. Inconsistent logic across roles. Hard to audit.

**Do this instead:** Single `get_employees_for_user(user)` function. All routes use it. Audit = read one function.

### Anti-Pattern 3: Modifying the Kiosk Route for RBAC

**What people do:** Add `@login_required` to `GET /` or `POST /api/recognize` during auth refactor.

**Why it's wrong:** The kiosk is a physical device on a wall. It has no browser session. Auth breaks the primary use case of the entire system.

**Do this instead:** Keep `GET /`, `POST /api/recognize`, `POST /api/detect` explicitly exempted. Document this exemption in code comments. Never add decorators to these three routes.

### Anti-Pattern 4: Storing Role in employees.json "role" Field

**What people do:** Reuse the existing `"role": "IT-специалист"` field (job title) as the RBAC role.

**Why it's wrong:** The existing `role` field is a free-text job title ("ВОП-1", "IT-специалист"). It has nothing to do with system access level. Conflating them creates confusion and bugs.

**Do this instead:** System roles (superadmin/org_admin/etc.) live in `users.json`. The `role` field in `employees.json` remains the job title. A user account in `users.json` may have an `emp_id` foreign key linking to the corresponding employee record (for the employee-cabinet role).

### Anti-Pattern 5: Rebuilding the Full Attendance JSON on Every Timesheet Request

**What people do:** Load all of `attendance.json` (potentially months of data), iterate every date, then filter by employee and date range in Python.

**Why it's wrong:** `attendance.json` is already the full O(dates × employees) structure. For a clinic with 50 employees and 2 years of history, this is ~36,000 records per request.

**Do this instead:** Filter by date range keys first (`{d: v for d, v in attendance.items() if from_date <= d <= to_date}`), then filter employee IDs from the scoped whitelist. Two O(n) passes, not one nested loop.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1–50 employees, 1 clinic | Current monolith + JSON files is sufficient. No changes needed beyond this design. |
| 50–200 employees, 2–5 orgs | JSON write contention under concurrent check-ins becomes real. Add file locking (`fcntl.flock`) around all `save_*` calls. |
| 200+ employees | Migrate `attendance.json` to SQLite (drop-in with no route changes if data helpers are properly abstracted). `employees.json`, `users.json`, `orgs.json` remain small enough for JSON. |
| Multi-server | JSON files on shared NFS with locking, or migrate to SQLite/PostgreSQL. Face recognition model state (`recognizer` global) must be re-examined — use a model file on disk rather than in-memory global. |

**First bottleneck for this system:** The `train_recognizer()` call on every face registration. It retrains on all employees. With 50+ employees this takes 2–5 seconds and blocks the request. Fix: run training in a background thread, return immediately with `{"status": "queued"}`.

---

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `app.py` routes ↔ `auth.py` | Direct import: `from auth import login_required, role_required, get_current_user` | No HTTP boundary — same process |
| `app.py` routes ↔ `data_helpers.py` | Direct import: `from data_helpers import get_employees_for_user, get_attendance_for_user` | Replaces inline `load_employees()` in protected routes |
| Protected routes ↔ `timesheet.py` | Direct import: `from timesheet import build_timesheet` | Pure function, no side effects |
| `timesheet.py` ↔ `export.py` | `build_timesheet` result passed to `export_xlsx` or `export_csv` | Decoupled by data contract (dict structure) |
| Kiosk routes ↔ CV globals | `recognizer`, `face_cascade` module-level globals in `app.py` | UNCHANGED — do not move these |
| Kiosk routes ↔ `data_helpers.py` | Kiosk calls `load_employees()` directly (unscoped) | Intentional exception to scope rule — documented |

---

## Sources

- Direct analysis of `/var/www/sites/face-almgp33/app.py` (423 lines, 2026-06-11)
- Direct analysis of `data/employees.json` schema (3 sample records)
- `.planning/codebase/ARCHITECTURE.md` (system layers map)
- `.planning/codebase/STRUCTURE.md` (file layout and naming conventions)
- `.planning/PROJECT.md` (requirements and constraints)
- Flask documentation knowledge: decorator composition, session handling, `functools.wraps`
- T-13 timesheet standard (Russian/Kazakh labour law form КО-13): standard symbol set for attendance states

---

*Architecture research for: Flask RBAC + T-13 timesheet extension (brownfield)*
*Researched: 2026-06-11*
