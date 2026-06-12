# Phase 2: Org/Dept Data Model - Research

**Researched:** 2026-06-12
**Domain:** Flask JSON file CRUD, data migration, RBAC-scoped dashboards, Python datetime schedule logic
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Two separate files: `data/orgs.json` (keyed by org_id) and `data/depts.json` (keyed by dept_id). Depts carry an `org_id` foreign key. Follows the same load_*/save_* pattern as `employees.json` and `users.json`.
- **D-02:** Org record schema: `{ id, name, description, created_at }`. Dept record schema: `{ id, org_id, name, created_at }`. Claude decides on the dept head field: keep it as a simple `head_name` string (not a user FK) to avoid join complexity in a JSON file system. Both IDs are UUID4 strings.
- **D-03:** Add `load_orgs()` / `save_orgs()` and `load_depts()` / `save_depts()` helpers in `app.py` following the exact pattern of `load_employees()` / `save_employees()`. Use `fcntl.flock(LOCK_EX)` on writes, same as `save_users()`.
- **D-04:** Standalone `migrate.py` script in project root. Run once manually: `python migrate.py`. No auto-run on startup, no Flask route.
- **D-05:** Migration creates a single default org ("Главная организация") and a single default dept ("Основной отдел"), then assigns `org_id` and `dept_id` to every existing employee record. All existing fields preserved verbatim.
- **D-06:** After patching `employees.json`, migration performs MIG-02 label integrity check: loads the LBPH model from face images (trains in-memory), reads every label value, and warns for any employee whose `label` integer is not found in the trained model. Prints a summary; warn-only, does NOT abort on mismatch.
- **D-07:** Migration writes a backup of the original `employees.json` to `data/employees_backup_{timestamp}.json` before patching.
- **D-08:** Schedule stored inline in each employee record under key `schedule`. Schema: `{ "start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5] }`. ISO weekday integers (1=Mon … 7=Sun). No default — required field when creating a new employee. Migration assigns standard `{ "start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5] }` to all existing employees.
- **D-09:** Total daily hours for T-13 is calculated at render time from `end - start` (not stored).
- **D-10:** Three new dedicated templates: `superadmin.html`, `org_admin.html`, `dept_admin.html`. Existing `admin.html` remains as-is for the attendance report (secondary page for all admin-tier roles).
- **D-11:** Routing: `/superadmin` → superadmin.html (@require_role("superadmin")); `/org_admin` → org_admin.html (@require_role("org_admin")); `/dept_admin` → dept_admin.html (@require_role("dept_admin", "viewer")). Login redirect updated: superadmin → `/superadmin`, org_admin → `/org_admin`, dept_admin → `/dept_admin`.
- **D-12:** Superadmin dashboard (DASH-01): three stat cards (total orgs, total employees system-wide, today's check-ins across all orgs) + org table + inline "Add org" form.
- **D-13:** Dept dashboard (DASH-02) on `dept_admin.html`: three stat cards (present today, absent today, late today) scoped to viewer's dept + employee table + Edit schedule action. Present/absent/late computed from `attendance.json` for today and each employee's `schedule`.
- **D-14:** Org_admin dashboard: dept list for their org + employee list for the entire org + "Add dept" form.
- **D-15:** When `recognize()` returns a successful match, look up `dept_id` in `employees.json`, load `depts.json` to get `dept.name`. Return `dept_name` in JSON response. `kiosk.html` displays it below employee name. If `dept_id` is null or dept not found, display nothing (graceful degradation).

### Claude's Discretion

- Exact HTML/CSS layout of the new pages — follow existing admin.html visual patterns (CSS variables, section headers, table style).
- Dept head field in dept record — use a simple `head_name` string (decided in D-02).
- ID generation — use `str(uuid.uuid4())` for new org/dept IDs, consistent with user ID pattern in users.json.
- API endpoint naming for org/dept CRUD — follow the existing `/api/employees` REST pattern (GET list, POST create, PUT update, DELETE).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ORG-01 | Superadmin can create, edit, and delete organizations | D-10, D-11, D-12 + REST CRUD pattern on `/api/orgs` |
| ORG-02 | Org_admin can create, edit, and delete departments within their own organization | D-11, D-14 + scope gate: check `session['org_id']` on write |
| ORG-03 | Dept_admin can add and edit employees within their own department only | D-11, D-13 + scope gate: check `session['dept_id']` on POST/PATCH |
| ORG-04 | Org_admin and superadmin can assign or reassign employees between departments | PATCH `/api/employees/<id>` with `dept_id` field; scope gate: org_admin may only reassign within their org |
| MIG-01 | Migration script adds org_id, dept_id, and schedule fields; all existing fields preserved | D-04 to D-07 + verified: existing employee fields confirmed via `data/employees.json` |
| MIG-02 | Migration script verifies face recognizer label integrity post-run | D-06 + verified: `recognizer.getLabels()` returns numpy array of trained label integers |
| T13-06 | Each employee has configurable work schedule (start, end, work days) | D-08, D-09 + schedule edit form in dept_admin.html |
| DASH-01 | Superadmin dashboard shows system-wide stats | D-12 + `/api/superadmin_stats` endpoint returning orgs count, total employees, today check-ins |
| DASH-02 | Department dashboard shows today's attendance in real time: present, absent, late | D-13 + `/api/dept_attendance_today` endpoint scoped to session dept_id |
| KIOSK-01 | When face recognized at kiosk, display shows employee's department name | D-15 + verified: `recognize()` returns JSON, kiosk.html reads `data.employee`; add `dept_name` field |
</phase_requirements>

---

## Summary

Phase 2 extends the existing Flask + JSON monolith with organizational hierarchy data. All decisions are locked from the CONTEXT.md discussion. The technical challenge is purely integration: wiring new JSON files, helper functions, CRUD routes, three new templates, a migration script, and dashboard scoping into an existing working system without breaking the kiosk or face recognizer.

The codebase is a single `app.py` (~610 lines) with a clear pattern: module-level file path constants, `load_*()` / `save_*()` pairs for each JSON store, `@require_role` decorator for access control, and Flask JSON API endpoints. Phase 2 adds two more data files (orgs.json, depts.json), three new page routes with templates, six new API endpoint groups, a standalone migration script, and a kiosk response enhancement. All additions are strictly additive — no existing code paths are removed.

Key integration points: (1) the login redirect logic in `login_page()` must be updated from the Phase 1 stub (all admin roles → `/admin`) to the role-specific destinations; (2) `recognize()` must enrich its JSON response with `dept_name`; (3) `kiosk.html` must render `dept_name` conditionally; (4) `save_orgs()` and `save_depts()` must include `fcntl.flock(LOCK_EX)` matching `save_users()`. The migration script is standalone and trains the face recognizer in-memory from face image files — the LBPH model is not persisted to disk in this codebase.

**Primary recommendation:** Build in dependency order: (1) file constants + load/save helpers + new file constants, (2) migrate.py, (3) CRUD API routes with scope gates, (4) three new templates wired to new API endpoints, (5) login redirect update, (6) kiosk enhancement. Test after each wave.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Org/dept CRUD (create, edit, delete) | API / Backend (app.py routes) | Browser/Client (fetch calls in templates) | Business logic, scope enforcement, and JSON writes must be server-side per CLAUDE.md security constraint |
| Data isolation (scope gates) | API / Backend (app.py) | — | Server-side only — not just hidden in UI (explicit CLAUDE.md constraint) |
| Dashboard stat computation | API / Backend (app.py endpoint) | Browser/Client (renders result) | Attendance aggregation over `attendance.json` belongs in Python, not JS |
| Migration script | Standalone Python script | — | One-time operator script; no web tier involvement |
| Work schedule storage | Database / Storage (employees.json) | API (reads at compute time) | Stored inline in employee record per D-08 |
| Kiosk dept name display | Browser/Client (kiosk.html JS) | API (returns dept_name in recognize response) | recognize() already returns JSON; JS renders the new field |
| Login redirect routing | API / Backend (login_page() handler) | — | Redirect logic lives in the Flask route; templates just follow |
| New templates (superadmin/org_admin/dept_admin) | Frontend Server (Jinja2 render) | Browser/Client (fetch for table data) | Page shells server-rendered; table data fetched via JS to avoid full page reloads |

---

## Standard Stack

This phase introduces no new external packages. All required capabilities exist in the current venv.

### Core (all already installed)

| Library | Verified Version | Purpose | Why Standard |
|---------|-----------------|---------|--------------|
| Flask | 3.1.3 | HTTP routing, session, Jinja2 render | Already in use; no change |
| Python stdlib `uuid` | 3.14.4 | UUID4 generation for org/dept IDs | Already used in app.py (`str(uuid.uuid4())`) |
| Python stdlib `fcntl` | 3.14.4 | Advisory write lock on JSON saves | Already used in `save_users()` |
| Python stdlib `datetime` | 3.14.4 | Timestamp for backup filename; schedule time parsing | Already used throughout app.py |
| Python stdlib `json` | 3.14.4 | JSON read/write | Already used throughout |
| Python stdlib `shutil` | 3.14.4 | Backup file copy in migrate.py | Already imported in app.py |
| opencv-contrib-python | 4.13.0.92 | LBPH recognizer training for label integrity check in migrate.py | Already in use; `cv2.face.LBPHFaceRecognizer_create()` + `getLabels()` |

[VERIFIED: codebase grep] — all packages confirmed present via `/var/www/sites/face-almgp33/venv/bin/python` import checks.

### No New Packages Required

No `pip install` step needed for this phase. All capabilities are covered by the existing venv.

**Installation:** none needed.

---

## Package Legitimacy Audit

No new packages are installed in this phase. This section is not applicable.

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious (SUS):** none

---

## Architecture Patterns

### System Architecture Diagram

```
[Browser]
    |
    |-- GET /superadmin /org_admin /dept_admin  --> [Flask: page route]
    |       |                                           |
    |       |                                     Jinja2 render
    |       |                                     (superadmin.html / org_admin.html / dept_admin.html)
    |       |                                           |
    |       |<------------------------------------------+
    |
    |-- fetch /api/orgs (GET/POST/PUT/DELETE)    --> [Flask: /api/orgs]
    |       |                                           |
    |       |                                     scope gate: @require_role("superadmin")
    |       |                                     load/save orgs.json
    |       |<------------------------------------------+
    |
    |-- fetch /api/depts (GET/POST/PUT/DELETE)   --> [Flask: /api/depts]
    |       |                                           |
    |       |                                     scope gate: org_admin → filter by session org_id
    |       |                                     load/save depts.json
    |       |<------------------------------------------+
    |
    |-- fetch /api/employees (POST/PATCH)        --> [Flask: /api/employees]
    |       |                                           |
    |       |                                     scope gate: dept_admin → enforce session dept_id
    |       |                                     load/save employees.json
    |       |<------------------------------------------+
    |
    |-- fetch /api/superadmin_stats              --> [Flask: stats endpoint]
    |       |                                           |
    |       |                                     read orgs.json + employees.json + attendance.json
    |       |<------------------------------------------+
    |
    |-- fetch /api/dept_attendance_today         --> [Flask: dept attendance endpoint]
    |       |                                           |
    |       |                                     filter attendance.json by session dept_id
    |       |                                     compute present/absent/late vs employee schedule
    |       |<------------------------------------------+
    |
    |-- POST /api/recognize (kiosk)              --> [Flask: recognize()]
            |                                           |
            |                                     existing LBPH match
            |                                     NEW: lookup emp.dept_id → depts.json → dept.name
            |                                     return existing fields + dept_name
            |<------------------------------------------+

[migrate.py] (standalone, operator runs once)
    |
    +-- read data/employees.json (backup first)
    +-- create default org in data/orgs.json
    +-- create default dept in data/depts.json
    +-- patch every employee with org_id, dept_id, schedule
    +-- train LBPH in-memory from data/faces/
    +-- check every employee label vs getLabels() → warn on mismatch
    +-- print color-coded summary to stdout
```

### Recommended Project Structure

```
/var/www/sites/face-almgp33/
├── app.py                    # Extended with new sections and routes
├── migrate.py                # NEW standalone migration script
├── data/
│   ├── orgs.json             # NEW { uuid: { id, name, description, created_at } }
│   ├── depts.json            # NEW { uuid: { id, org_id, name, head_name, created_at } }
│   ├── employees.json        # PATCHED: adds org_id, dept_id, schedule per employee
│   └── employees_backup_{ts}.json  # NEW backup created by migrate.py
├── templates/
│   ├── superadmin.html       # NEW
│   ├── org_admin.html        # NEW
│   ├── dept_admin.html       # NEW
│   ├── admin.html            # UNCHANGED (attendance report, secondary page)
│   └── kiosk.html            # MINOR CHANGE: render dept_name below emp name
└── tests/
    ├── conftest.py           # EXTENDED: add ORGS_FILE / DEPTS_FILE monkeypatches
    └── test_org_dept.py      # NEW: covers ORG-01 through ORG-04, DASH-01, DASH-02, KIOSK-01
```

### Pattern 1: load/save Helper Pair (established, apply to orgs and depts)

**What:** File-backed JSON dict store with a read helper and a write helper.
**When to use:** Every time a new JSON data file is introduced.

```python
# Source: app.py lines 102-120 (load_employees/save_employees + load_users/save_users)
# The load variant — read file if exists, return empty dict if absent
ORGS_FILE = os.path.join(DATA_DIR, "orgs.json")
DEPTS_FILE = os.path.join(DATA_DIR, "depts.json")

def load_orgs():
    if os.path.exists(ORGS_FILE):
        with open(ORGS_FILE) as f:
            return json.load(f)
    return {}

def save_orgs(data):
    with open(ORGS_FILE, "w", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fcntl.flock(fh, fcntl.LOCK_UN)
```

Critical: `save_orgs` and `save_depts` MUST use `fcntl.flock(LOCK_EX)` wrapping (matching `save_users`, not `save_employees`). The existing `save_employees` does NOT use flock — that is a pre-existing gap in the codebase. New save helpers must use flock.

[VERIFIED: codebase grep] — save_users pattern at app.py lines 52-56 confirmed.

### Pattern 2: Scope Gate in API Routes

**What:** After `@require_role`, enforce data-level isolation by checking `session['org_id']` or `session['dept_id']`.
**When to use:** Any route that writes to or reads from org/dept-scoped data.

```python
# Source: app.py ROLE_HIERARCHY + session pattern (D-07 Phase 1)
@app.route("/api/depts", methods=["POST"])
@require_role("superadmin", "org_admin")
def create_dept():
    caller_role = session.get("role")
    caller_org_id = session.get("org_id")
    data = request.json
    target_org_id = data.get("org_id")
    # org_admin can only create depts within their own org
    if caller_role == "org_admin" and target_org_id != caller_org_id:
        return jsonify({"error": "forbidden"}), 403
    # ... create dept
```

[VERIFIED: codebase grep] — `session.get("org_id")` already populated by login handler (app.py line 202).

### Pattern 3: REST CRUD Endpoint Pair

**What:** GET (list) + POST (create) at collection URL; PUT (update) + DELETE (remove) at item URL.
**When to use:** All new org/dept entity management.

```python
# Source: app.py lines 348-383 (/api/employees pattern)
@app.route("/api/orgs", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def list_orgs():
    return jsonify(list(load_orgs().values()))

@app.route("/api/orgs", methods=["POST"])
@require_role("superadmin")
def create_org():
    data = request.json
    org_id = str(uuid.uuid4())
    orgs = load_orgs()
    orgs[org_id] = {
        "id": org_id,
        "name": data["name"],
        "description": data.get("description", ""),
        "created_at": datetime.now().isoformat(),
    }
    save_orgs(orgs)
    return jsonify({"id": org_id, "status": "created"})

@app.route("/api/orgs/<org_id>", methods=["PUT"])
@require_role("superadmin")
def update_org(org_id):
    orgs = load_orgs()
    if org_id not in orgs:
        return jsonify({"error": "Организация не найдена"}), 404
    data = request.json
    if "name" in data:
        orgs[org_id]["name"] = data["name"]
    if "description" in data:
        orgs[org_id]["description"] = data["description"]
    save_orgs(orgs)
    return jsonify({"status": "updated"})

@app.route("/api/orgs/<org_id>", methods=["DELETE"])
@require_role("superadmin")
def delete_org(org_id):
    orgs = load_orgs()
    if org_id not in orgs:
        return jsonify({"error": "Организация не найдена"}), 404
    del orgs[org_id]
    save_orgs(orgs)
    return jsonify({"status": "deleted"})
```

[VERIFIED: codebase grep] — `/api/employees` REST pattern confirmed at app.py lines 348-383.

### Pattern 4: Present/Absent/Late Computation (DASH-02)

**What:** For each employee in a dept, classify today's attendance status using their schedule.
**When to use:** `dept_attendance_today` API endpoint; also relevant to T-13 in Phase 3.

```python
# Source: [ASSUMED] — derived from existing get_stats() logic at app.py lines 550-598
from datetime import datetime, date, timedelta

def classify_attendance(emp, today_record):
    """
    Returns 'present', 'late', or 'absent' based on today's attendance record
    and employee schedule.
    
    emp: employee dict with 'schedule' = { 'start': 'HH:MM', 'end': 'HH:MM', 'work_days': [1..7] }
    today_record: attendance dict { 'check_in': 'HH:MM:SS' or None, 'check_out': ... }
    """
    today = date.today()
    weekday = today.weekday() + 1  # ISO: 1=Mon, 7=Sun
    schedule = emp.get("schedule", {})
    work_days = schedule.get("work_days", [1, 2, 3, 4, 5])
    
    if weekday not in work_days:
        return "day_off"  # Weekend/non-work day — not counted as absent
    
    check_in = today_record.get("check_in") if today_record else None
    if not check_in:
        return "absent"
    
    schedule_start = schedule.get("start", "09:00")
    # Add 15-minute grace period for late detection (T13-04, relevant for DASH-02)
    start_h, start_m = map(int, schedule_start.split(":"))
    threshold = f"{start_h:02d}:{start_m + 15:02d}:00" if start_m <= 44 else f"{start_h+1:02d}:{(start_m+15)%60:02d}:00"
    
    if check_in > threshold:
        return "late"
    return "present"
```

Note: The existing `recognize()` endpoint uses a hardcoded `"09:00:00"` late threshold (app.py line 485). Phase 2 introduces `schedule`-based computation for the dashboard. The kiosk `is_late` field is NOT updated in this phase — that schedule-aware kiosk late detection belongs in Phase 3 (T13-04). Phase 2 scope for DASH-02 only requires present/absent/late counts.

[VERIFIED: codebase grep] — existing `is_late = now > "09:00:00"` at app.py line 485 confirmed.

### Pattern 5: Migration Script (standalone, no Flask)

**What:** Standalone Python script that patches data files and runs its own LBPH training.
**When to use:** One-time migration per D-04.

```python
# Source: [ASSUMED] — derived from train_recognizer() pattern at app.py lines 155-177
#!/usr/bin/env python3
"""
migrate.py — Phase 2 data migration
Run once: python migrate.py
"""
import json, os, shutil, uuid
from datetime import datetime
import cv2
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FACES_DIR = os.path.join(DATA_DIR, "faces")
EMPLOYEES_FILE = os.path.join(DATA_DIR, "employees.json")
ORGS_FILE = os.path.join(DATA_DIR, "orgs.json")
DEPTS_FILE = os.path.join(DATA_DIR, "depts.json")

def check_label_integrity(employees):
    """Train LBPH in-memory from face image files; return set of trained label ints."""
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces, labels = [], []
    for emp_id, emp in employees.items():
        emp_dir = os.path.join(FACES_DIR, emp_id)
        if not os.path.exists(emp_dir):
            continue
        label = int(emp.get("label", 0))
        for fname in os.listdir(emp_dir):
            if not fname.endswith(".jpg"):
                continue
            img = cv2.imread(os.path.join(emp_dir, fname), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                faces.append(cv2.resize(img, (200, 200)))
                labels.append(label)
    if len(faces) < 2:
        return set()
    recognizer.train(faces, np.array(labels))
    trained_labels = set(int(x) for x in recognizer.getLabels().flatten())
    return trained_labels

# ... rest of migration: backup, create org/dept, patch employees, check labels
```

Key: `recognizer.getLabels()` returns a numpy 2D array of shape (N, 1); use `.flatten()` and `int()` cast.

[VERIFIED: codebase grep + live Python test] — `cv2.face.LBPHFaceRecognizer_create()` and `getLabels()` confirmed working on Python 3.14.4 / opencv-contrib-python 4.13.0.92.

### Anti-Patterns to Avoid

- **Using `save_employees()` pattern (no flock) for new save helpers:** `save_employees()` does not use `fcntl.flock`. All new `save_orgs()` / `save_depts()` must use the `save_users()` flock pattern. Inconsistency exists in the codebase — new code must use flock.
- **Cascade delete without warning:** Deleting an org that still has depts/employees. Phase 2 scope uses `window.confirm()` dialogs only. Backend should check for orphan references and return a 409 if employees exist under a dept being deleted, or return a warning payload — don't silently orphan data.
- **Trusting session org_id/dept_id for write authorization without re-checking:** The session is set at login time. If an org_admin's org is deleted after login, their session still has the old org_id. All write routes must verify the referenced org/dept still exists in the JSON store.
- **Running migrate.py twice without checking:** The script must be idempotent or detect already-migrated employees (check if `org_id` key already exists) and skip them, to avoid overwriting manually set org assignments.
- **Inline `<script>` in templates importing from modules:** This project uses inline JS in each HTML file. Do not attempt to `import` or `require` other scripts.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID generation for org/dept IDs | Custom ID scheme | `str(uuid.uuid4())` | Already used in users.json; zero collision risk |
| File locking | Custom lock file | `fcntl.flock(LOCK_EX)` | Already proven pattern in save_users(); advisory lock is sufficient for single-worker PM2 deployment |
| Time string comparison for late detection | Parse datetime objects | String comparison `"HH:MM:SS" > "HH:MM:SS"` | Already established pattern in app.py line 485 and 580; ISO time strings sort correctly lexicographically |
| Employee count per org/dept | Separate counter field | Count on read: `sum(1 for e in employees.values() if e.get("org_id") == org_id)` | JSON store is small (clinic scale); counter fields go stale |
| Today's date | Reinvent | `date.today().isoformat()` | Already used throughout attendance logic |

**Key insight:** This codebase is intentionally simple. The "don't hand-roll" insight is to not over-engineer JSON querying — no ORM, no query builder, no caching. Iterate over the dict values directly; at clinic scale (dozens to low hundreds of employees) this is fast.

---

## Runtime State Inventory

This is a migration phase (MIG-01, MIG-02 add fields to employees.json).

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `data/employees.json` — 1 live employee (`1781173156953`) with fields `id, name, role, label, registered_at, face_count` — missing `org_id, dept_id, schedule` | Data migration: migrate.py adds these 3 fields + creates orgs.json + depts.json |
| Stored data | `data/attendance.json` — 2 dates present (2026-06-11, 2026-06-12), records keyed by emp_id with `check_in, check_out` | No change — attendance format unchanged by Phase 2 |
| Stored data | `data/users.json` — 1 superadmin with `org_id: null, dept_id: null` | After migrate.py runs, superadmin remains org_id null (correct — superadmin is not tied to any org) |
| Live service config | PM2 process `face-recognition` running on port 5051 | `pm2 restart face-recognition` at phase end — no config change needed |
| OS-registered state | None beyond PM2 process name | None |
| Secrets/env vars | SECRET_KEY env var (or hardcoded fallback in app.py) | No change |
| Build artifacts | venv at `/var/www/sites/face-almgp33/venv` | No change — no new packages |
| LBPH model | In-memory only — no .xml file on disk | migrate.py trains from face image files directly (faces dir has 10 jpg images for emp `1781173156953`) |

**Critical migration note:** `data/employees.json` has a real employee with face data (10 photos in `data/faces/1781173156953/`). The migration backup (`data/employees_backup_{ts}.json`) must be written before any patching. The LBPH label for this employee is `1`.

---

## Common Pitfalls

### Pitfall 1: Missing fcntl import / wrong lock pattern
**What goes wrong:** New `save_orgs()` or `save_depts()` helper written without `fcntl.flock`. Under concurrent requests (even with single-worker PM2, a gunicorn multi-worker restart could cause overlap), two simultaneous saves corrupt the JSON.
**Why it happens:** The codebase has inconsistent patterns — `save_employees()` (no flock) and `save_users()` (with flock) exist side by side. Developers copy the wrong template.
**How to avoid:** Always use `save_users()` (lines 52-56) as the template for new save helpers, not `save_employees()` (lines 108-111).
**Warning signs:** JSON decode error on next load; Python `json.JSONDecodeError`.

### Pitfall 2: migrate.py getLabels() returns numpy 2D array, not a flat list
**What goes wrong:** Checking `emp_label in trained_labels` where `trained_labels = set(recognizer.getLabels())` — this set contains numpy row arrays, not integers. Membership check always fails.
**Why it happens:** `getLabels()` returns shape `(N, 1)` numpy array, not a 1D list.
**How to avoid:** Use `set(int(x) for x in recognizer.getLabels().flatten())`.
**Warning signs:** Migration reports WARN for every employee even when label files exist.

### Pitfall 3: Dept scoping leak — org_admin seeing other orgs' depts
**What goes wrong:** `GET /api/depts` returns all depts in depts.json without filtering by org_id for org_admin callers. org_admin sees depts from other orgs.
**Why it happens:** The existing `GET /api/employees` (app.py line 349) returns all employees without scoping — that pattern is pre-Phase-2 and needs to be fixed for new scoped endpoints.
**How to avoid:** In all GET routes for depts/employees, check `session['role']` and apply filter: if `role == "org_admin"`, filter by `session['org_id']`; if `role == "dept_admin"`, filter by `session['dept_id']`.
**Warning signs:** org_admin template shows more depts than expected.

### Pitfall 4: Hardcoded "09:00" late threshold not updated in kiosk is_late
**What goes wrong:** After Phase 2, employees have individual schedules. The kiosk `recognize()` still uses `now > "09:00:00"` for `is_late`. An employee with `start: "08:00"` shows as on-time but is actually late.
**Why it happens:** Phase 2 scope intentionally does not fix this (T13-04 is Phase 3 scope). But a developer might try to fix it here.
**How to avoid:** Leave app.py line 485 (`is_late = now > "09:00:00"`) unchanged in Phase 2. Document that schedule-aware late detection is Phase 3 scope. DASH-02 uses the schedule-aware computation independently.
**Warning signs:** Test failures in Phase 3 if the logic is inconsistently changed here.

### Pitfall 5: Migration script breaks face recognizer by touching label field
**What goes wrong:** migrate.py accidentally overwrites the `label` integer field when patching employee records.
**Why it happens:** Using dict.update() or reassigning the whole record object instead of adding only the new keys.
**How to avoid:** Patch only the three new keys explicitly:
```python
employees[emp_id]["org_id"] = default_org_id
employees[emp_id]["dept_id"] = default_dept_id
employees[emp_id]["schedule"] = DEFAULT_SCHEDULE
```
Never do `employees[emp_id] = { ...new_record }` — always mutate in-place.
**Warning signs:** Face recognition stops working after migration; `train_recognizer()` finds no labels.

### Pitfall 6: Login redirect only partially updated
**What goes wrong:** Login handler updated for `superadmin` redirect but `org_admin` and `dept_admin` cases left pointing to `/admin`. org_admin users land on the attendance report page instead of their dashboard.
**Why it happens:** The Phase 1 login redirect was: `if user["role"] in ("superadmin", "org_admin", "dept_admin"): return redirect(url_for("admin_page"))` — a single branch for all three roles.
**How to avoid:** Replace the single redirect with role-specific branches:
```python
role = user["role"]
if role == "superadmin":
    return redirect(url_for("superadmin_page"))
elif role == "org_admin":
    return redirect(url_for("org_admin_page"))
elif role == "dept_admin":
    return redirect(url_for("dept_admin_page"))
else:
    return redirect(url_for("dashboard_page"))
```
**Warning signs:** org_admin or dept_admin login lands on `/admin` instead of their role page.

### Pitfall 7: Dept employee count computed at API response time — expensive iteration
**What goes wrong:** For every org in the org table, the API iterates all employees to count per org/dept. At clinic scale this is fine, but the pattern tempts storing a count field.
**Why it happens:** Cached count fields in JSON go stale when employees are reassigned.
**How to avoid:** Always count on read. At clinic scale (< 1000 employees), iterating the employees dict is < 1ms.
**Warning signs:** employee_count field in orgs.json that doesn't match actual employees.json.

---

## Code Examples

### Example 1: DASH-02 — Dept attendance today endpoint

```python
# Source: [ASSUMED] — derived from get_attendance() at app.py lines 512-542 + schedule logic
@app.route("/api/dept_attendance_today", methods=["GET"])
@require_role("dept_admin", "org_admin", "superadmin")
def dept_attendance_today():
    role = session.get("role")
    dept_id = session.get("dept_id")
    
    employees = load_employees()
    attendance = load_attendance()
    today = date.today().isoformat()
    today_weekday = date.today().weekday() + 1  # ISO 1=Mon
    today_records = attendance.get(today, {})
    
    # Filter employees by scope
    if role == "dept_admin":
        scoped = {eid: e for eid, e in employees.items() if e.get("dept_id") == dept_id}
    elif role == "org_admin":
        org_id = session.get("org_id")
        scoped = {eid: e for eid, e in employees.items() if e.get("org_id") == org_id}
    else:  # superadmin
        scoped = employees
    
    result = []
    present = absent = late = 0
    
    for eid, emp in scoped.items():
        schedule = emp.get("schedule", {"start": "09:00", "end": "18:00", "work_days": [1,2,3,4,5]})
        work_days = schedule.get("work_days", [1,2,3,4,5])
        
        if today_weekday not in work_days:
            continue  # Day off — exclude from present/absent counts
        
        rec = today_records.get(eid)
        check_in = rec.get("check_in") if rec else None
        check_out = rec.get("check_out") if rec else None
        
        # Late detection: check_in > schedule.start + 15 min
        schedule_start = schedule.get("start", "09:00")
        sh, sm = map(int, schedule_start.split(":"))
        late_threshold_m = sm + 15
        late_threshold = f"{sh:02d}:{late_threshold_m % 60:02d}:00" if late_threshold_m < 60 else f"{sh+1:02d}:{late_threshold_m % 60:02d}:00"
        
        if check_in:
            if check_in > late_threshold:
                status = "late"
                late += 1
            else:
                status = "present"
                present += 1
        else:
            status = "absent"
            absent += 1
        
        result.append({
            "emp_id": eid,
            "name": emp["name"],
            "check_in": check_in,
            "check_out": check_out,
            "status": status,
            "schedule": f"{schedule.get('start')} – {schedule.get('end')}",
        })
    
    return jsonify({
        "employees": result,
        "stats": {"present": present, "absent": absent, "late": late},
    })
```

### Example 2: KIOSK-01 — dept_name enrichment in recognize()

```python
# Source: [ASSUMED] — insert after line 473 (emp found) in app.py recognize()
# After: emp = next((e for e in employees.values() if e.get("label") == label), None)
# Add dept name lookup:
dept_name = None
if emp.get("dept_id"):
    depts = load_depts()
    dept = depts.get(emp["dept_id"])
    if dept:
        dept_name = dept.get("name")

# In the final return jsonify(...), add:
# "dept_name": dept_name,
```

```javascript
// Source: [ASSUMED] — kiosk.html showResult() function around line 312
// After: document.getElementById("empRole").textContent = emp.role;
// Add:
const deptEl = document.getElementById("empDept");
if (deptEl) {
    if (data.dept_name) {
        deptEl.textContent = data.dept_name;
        deptEl.style.display = "";
    } else {
        deptEl.style.display = "none";
    }
}
// HTML addition to employee-card div (after .emp-role):
// <div class="emp-dept" id="empDept" style="display:none; font-size:13px; color:#7986cb; margin-top:4px;"></div>
```

### Example 3: New file constants block in app.py

```python
# Source: app.py lines 13-19 (existing constants pattern)
# Add immediately after USERS_FILE line:
ORGS_FILE = os.path.join(DATA_DIR, "orgs.json")
DEPTS_FILE = os.path.join(DATA_DIR, "depts.json")
```

---

## State of the Art

| Old Approach | Current Approach | Impact for This Phase |
|--------------|-----------------|----------------------|
| Single admin page for all roles | Role-specific dashboards | Phase 2 implements this split via D-10/D-11 |
| Hardcoded 09:00 late threshold | Per-employee schedule (T13-06) | Phase 2 stores schedule; kiosk still uses hardcoded until Phase 3 |
| Employees with no org/dept | All employees assigned to default org/dept | One-time migration (D-04 to D-07) |
| No dept name on kiosk | dept_name returned by recognize() | KIOSK-01 implemented in Phase 2 |

**Note:** The `save_employees()` function (app.py line 108) does not have flock. This is a pre-existing pattern gap. New save helpers must use flock even though save_employees doesn't. This is not changed in Phase 2 — save_employees stays as-is to minimize blast radius.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Late detection threshold for DASH-02 adds 15 minutes to schedule start | Code Examples (DASH-02), Pattern 4 | T13-04 spec (Phase 3) may define different threshold; the 15-min grace period is sourced from T13-04 requirement text. If wrong, DASH-02 stat counts will differ from Phase 3 T-13 symbols. |
| A2 | LBPH model is in-memory only; migrate.py must retrain from face image files | Pattern 5 (Migration) | Confirmed by grep: no `.xml` model save/load in app.py. Risk: if model file exists in future, migrate.py label check would be stale. |
| A3 | dept_attendance_today should skip employees on their day off (not count as absent) | Code Examples (DASH-02) | If weekends should show as absent, stat counts will differ. The distinction matters for accurate DASH-02 absent count. |
| A4 | `schedule.work_days` uses ISO weekday where `date.today().weekday() + 1` conversion is correct | Pattern 4 | Python's weekday() returns 0-6 (Mon=0); ISO is 1-7 (Mon=1). The +1 conversion is standard. If wrong, day-off detection misaligns by 1 day. |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.
_(Table is not empty — A1 and A3 should be confirmed with user before Phase 3 T-13 work, but are low risk for Phase 2 DASH-02 implementation.)_

---

## Open Questions

1. **Should deleting an org cascade-delete its depts and set emp org_id to null, or should it be blocked if employees exist?**
   - What we know: D-12 only mentions delete action in UI; no cascade behavior specified.
   - What's unclear: Whether a backend guard (return 409 if employees exist under org) is required.
   - Recommendation: Block delete if any employee has `org_id` matching the deleted org. Return `{"error": "Организация содержит сотрудников"}`, 409. This is the safe default. Apply same logic for dept delete.

2. **Is the login redirect update (D-11) a replacement of the existing redirect or an extension?**
   - What we know: Phase 1 CONTEXT D-08 says all admin roles go to `/admin`; Phase 2 CONTEXT D-11 says update to role-specific routes.
   - What's unclear: The existing `login_page()` in app.py line 204 uses a single `if user["role"] in ("superadmin", "org_admin", "dept_admin"): return redirect(url_for("admin_page"))`.
   - Recommendation: Replace the single branch with role-specific redirects per D-11. This is a clean in-place replacement, not an extension.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv | All code | Yes | 3.14.4 | — |
| Flask | All routes | Yes | 3.1.3 | — |
| opencv-contrib-python | migrate.py label check | Yes | 4.13.0.92 | — |
| numpy | migrate.py LBPH training | Yes | 2.4.6 | — |
| fcntl | save_orgs/save_depts | Yes | stdlib | — |
| uuid | org/dept ID generation | Yes | stdlib | — |
| pytest | test suite | Yes | 9.0.3 | — |
| PM2 | process restart | Yes | running | — |

[VERIFIED: codebase grep + live import check] — all packages confirmed present.

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pytest.ini` (exists at project root) |
| Quick run command | `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -x -q` |
| Full suite command | `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -v` |

### Baseline (from Phase 1)

Current state: 2 passed + 8 xpassed in 3.89s. All xpassed tests will remain passing (Phase 1 code is implemented). Phase 2 must not regress this baseline.

The existing `conftest.py` monkeypatches `EMPLOYEES_FILE`, `USERS_FILE`, etc. Phase 2 tests must also monkeypatch `ORGS_FILE` and `DEPTS_FILE`. The `tmp_data` fixture in conftest.py must be extended to add these two new path constants.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ORG-01 | superadmin can create/edit/delete org via API | unit | `pytest tests/test_org_dept.py::test_org_crud -x -q` | Wave 0 |
| ORG-02 | org_admin can create/edit/delete dept in own org; blocked from other org | unit | `pytest tests/test_org_dept.py::test_dept_crud_scope -x -q` | Wave 0 |
| ORG-03 | dept_admin can add/edit employee in own dept; blocked from other dept | unit | `pytest tests/test_org_dept.py::test_employee_dept_scope -x -q` | Wave 0 |
| ORG-04 | org_admin can reassign employee between depts within own org | unit | `pytest tests/test_org_dept.py::test_employee_reassign -x -q` | Wave 0 |
| MIG-01 | migrate.py adds org_id, dept_id, schedule; preserves label | unit | `pytest tests/test_migration.py::test_migration_additive -x -q` | Wave 0 |
| MIG-02 | migrate.py warns on label mismatch; does not abort | unit | `pytest tests/test_migration.py::test_label_integrity_warn -x -q` | Wave 0 |
| T13-06 | PATCH /api/employees/<id>/schedule updates schedule; invalid format rejected | unit | `pytest tests/test_org_dept.py::test_schedule_update -x -q` | Wave 0 |
| DASH-01 | /api/superadmin_stats returns org count, employee count, today check-ins | unit | `pytest tests/test_org_dept.py::test_superadmin_stats -x -q` | Wave 0 |
| DASH-02 | /api/dept_attendance_today returns scoped stats; dept_admin cannot see other depts | unit | `pytest tests/test_org_dept.py::test_dept_attendance_scope -x -q` | Wave 0 |
| KIOSK-01 | /api/recognize returns dept_name; absent when dept_id null | unit | `pytest tests/test_org_dept.py::test_recognize_dept_name -x -q` | Wave 0 |

### Sampling Rate
- **Per task commit:** `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -x -q`
- **Per wave merge:** `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_org_dept.py` — covers ORG-01 through ORG-04, T13-06, DASH-01, DASH-02, KIOSK-01
- [ ] `tests/test_migration.py` — covers MIG-01, MIG-02
- [ ] `tests/conftest.py` extension — add ORGS_FILE and DEPTS_FILE to `tmp_data` fixture monkeypatches

---

## Security Domain

`security_enforcement: true` in `.planning/config.json`.

### Applicable ASVS Categories (ASVS Level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No new auth added | (Phase 1 covers this) |
| V3 Session Management | Yes — session org_id/dept_id used for data scoping | `session.get("org_id")` / `session.get("dept_id")` read-only; never set from request data |
| V4 Access Control | Yes — primary threat in this phase | `@require_role` + inline scope gate checks in every write route |
| V5 Input Validation | Yes | Validate org/dept name is non-empty string; validate schedule fields (HH:MM format, work_days is list of 1-7 ints) |
| V6 Cryptography | No new crypto | — |

### Known Threat Patterns for Flask JSON CRUD

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Horizontal privilege escalation: org_admin POSTs dept with org_id of another org | Spoofing / Tampering | Server checks `target_org_id == session['org_id']` in every write handler |
| Vertical privilege escalation: dept_admin calls `/api/orgs` DELETE | Elevation | `@require_role("superadmin")` on all org write routes |
| Session fixation after role change | Spoofing | `session.clear()` before setting new session keys on login (already done in app.py line 199) |
| JSON injection via org/dept name containing control characters | Tampering | `ensure_ascii=False` + `json.dump` handles encoding; strip leading/trailing whitespace; validate non-empty |
| Mass assignment: PATCH employee with attacker-supplied `label` field | Tampering | Whitelist accepted fields in PATCH handlers; never pass `request.json` directly to employee record |

---

## Sources

### Primary (HIGH confidence)
- `app.py` (lines 1-609) — verified live codebase: load/save patterns, fcntl usage, session structure, recognize() response format, ROLE_HIERARCHY, existing route structure
- `data/employees.json` — verified live file: current employee schema (id, name, role, label, registered_at, face_count)
- `data/users.json` — verified live file: UUID4 id pattern, org_id/dept_id null placeholders
- `tests/conftest.py` — verified live file: monkeypatch pattern for EMPLOYEES_FILE, tmp_data fixture structure
- Python 3.14.4 REPL — verified `cv2.face.LBPHFaceRecognizer_create()`, `getLabels()` returns numpy shape (N,1), `str(uuid.uuid4())` available

### Secondary (MEDIUM confidence)
- CONTEXT.md D-01 through D-15 — locked user decisions
- UI-SPEC.md — confirmed CSS variable names, component patterns, copywriting contract

### Tertiary (LOW confidence)
- T13-04 15-minute late grace period in DASH-02 — derived from requirements; actual threshold for DASH-02 inferred from T13-04 text

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages confirmed via live import
- Architecture: HIGH — all patterns verified against live app.py
- Migration: HIGH — getLabels() behavior confirmed via live Python test
- Pitfalls: HIGH — all confirmed from direct code inspection
- Validation: HIGH — existing test infrastructure inspected directly
- DASH-02 late threshold: MEDIUM — inferred from T13-04; not explicitly confirmed for Phase 2

**Research date:** 2026-06-12
**Valid until:** 2026-07-12 (stable — no external dependencies added)
