# Phase 2: Org/Dept Data Model - Pattern Map

**Mapped:** 2026-06-12
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app.py` (new constants + helpers + routes) | service + controller | CRUD, request-response | `app.py` load_users/save_users + /api/employees routes | exact |
| `migrate.py` | utility (migration) | batch, file-I/O | `app.py` train_recognizer() + save_users() | role-match |
| `templates/superadmin.html` | component (template) | request-response | `templates/admin.html` | exact visual |
| `templates/org_admin.html` | component (template) | request-response | `templates/admin.html` | exact visual |
| `templates/dept_admin.html` | component (template) | request-response | `templates/admin.html` | exact visual |
| `templates/kiosk.html` (minor patch) | component (template) | event-driven | `templates/kiosk.html` showResult() lines 312-370 | exact |
| `data/orgs.json` | config/storage | file-I/O | `data/users.json` (UUID-keyed dict) | exact |
| `data/depts.json` | config/storage | file-I/O | `data/users.json` (UUID-keyed dict) | exact |
| `tests/conftest.py` (extension) | test | — | `tests/conftest.py` tmp_data fixture lines 30-65 | exact |
| `tests/test_org_dept.py` | test | request-response | `tests/conftest.py` client + seed_users pattern | role-match |
| `tests/test_migration.py` | test | batch | `tests/conftest.py` tmp_data fixture | role-match |

---

## Pattern Assignments

### `app.py` — New file constants (add after line 19, USERS_FILE)

**Analog:** `app.py` lines 13-19

**Imports already present** (lines 1-8): `os, json, uuid, fcntl, datetime` — all needed, no new imports required.

**File constants pattern** (lines 13-19 — copy and extend):
```python
# ─── Data helpers ─────────────────────────────────────────────────────────────
# Existing constants (lines 13-19):
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EMPLOYEES_FILE = os.path.join(DATA_DIR, "employees.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

# ADD immediately after USERS_FILE (same pattern):
ORGS_FILE = os.path.join(DATA_DIR, "orgs.json")
DEPTS_FILE = os.path.join(DATA_DIR, "depts.json")
```

---

### `app.py` — load_orgs / save_orgs / load_depts / save_depts (add in `# ─── Data helpers` section)

**Analog:** `app.py` lines 46-56 (load_users / save_users — USE THIS, NOT save_employees which lacks flock)

**load pattern** (analog: lines 46-50):
```python
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}
```

**save pattern with flock** (analog: lines 52-56 — MANDATORY for new saves):
```python
def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fcntl.flock(fh, fcntl.LOCK_UN)
```

**DO NOT copy** `save_employees` (lines 108-110) — it lacks flock. New save helpers must use the `save_users` pattern above.

---

### `app.py` — `/api/orgs` and `/api/depts` CRUD routes

**Analog:** `app.py` lines 346-398 (employee CRUD — GET list, POST create, item-level DELETE)

**Route + decorator pattern** (lines 348-351):
```python
@app.route("/api/employees", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def get_employees():
    return jsonify(load_employees())
```

**POST create pattern with UUID** (lines 353-370 — note: org/dept use uuid4, not timestamp id):
```python
@app.route("/api/employees", methods=["POST"])
@require_role("superadmin", "org_admin", "dept_admin")
def add_employee():
    data = request.json
    employees = load_employees()
    emp_id = str(int(time.time() * 1000))   # ← org/dept use str(uuid.uuid4()) instead
    employees[emp_id] = {
        "id": emp_id,
        "name": data["name"],
        ...
        "registered_at": datetime.now().isoformat(),
    }
    save_employees(employees)
    return jsonify({"id": emp_id, "status": "created"})
```

**404 guard pattern** (lines 372-383):
```python
@app.route("/api/employees/<emp_id>", methods=["DELETE"])
@require_role("superadmin", "org_admin", "dept_admin")
def delete_employee(emp_id):
    employees = load_employees()
    if emp_id in employees:
        del employees[emp_id]
        save_employees(employees)
    return jsonify({"status": "deleted"})
```

**Scope gate pattern** (from RESEARCH.md Pattern 2 — no direct analog in app.py yet, add inline):
```python
caller_role = session.get("role")
caller_org_id = session.get("org_id")
data = request.json
target_org_id = data.get("org_id")
if caller_role == "org_admin" and target_org_id != caller_org_id:
    return jsonify({"error": "forbidden"}), 403
```

**Section header** (apply before new route blocks, following app.py convention):
```python
# ─── API: Orgs ────────────────────────────────────────────────────────────────
```

---

### `app.py` — `/api/superadmin_stats` and `/api/dept_attendance_today` endpoints

**Analog:** `app.py` lines 511-542 (get_attendance — reads attendance.json, filters by date)

**Stats aggregation pattern** (lines 513-520):
```python
@app.route("/api/attendance", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def get_attendance():
    day = request.args.get("date", date.today().isoformat())
    attendance = load_attendance()
    employees = load_employees()
    # ... iterate over employees, look up attendance[day].get(emp_id)
```

**Error response pattern** (lines 385-398, guard clause + 404):
```python
if emp_id not in employees:
    return jsonify({"error": "Сотрудник не найден"}), 404
```

---

### `app.py` — Login redirect update (lines 204-205)

**Analog:** `app.py` lines 186-210 (login_page function)

**Current single-branch redirect** (lines 204-205 — REPLACE this):
```python
if user["role"] in ("superadmin", "org_admin", "dept_admin"):
    return redirect(url_for("admin_page"))
```

**Replace with role-specific branches:**
```python
role = user["role"]
if role == "superadmin":
    return redirect(url_for("superadmin_page"))
elif role == "org_admin":
    return redirect(url_for("org_admin_page"))
elif role in ("dept_admin", "viewer"):
    return redirect(url_for("dept_admin_page"))
else:
    return redirect(url_for("dashboard_page"))
```

---

### `app.py` — `recognize()` dept_name enrichment (lines 473-509)

**Analog:** `app.py` lines 473-509 (recognize function body — modify in-place)

**Insertion point** — after line 475 (`if not emp: return ...`):
```python
# After emp is confirmed found — add dept lookup:
dept_name = None
if emp.get("dept_id"):
    depts = load_depts()
    dept = depts.get(emp["dept_id"])
    if dept:
        dept_name = dept.get("name")
```

**Return payload extension** (lines 500-509 — add `dept_name` key):
```python
return jsonify({
    "status": "ok",
    "employee": emp,
    "event": event,
    "record": attendance[today].get(emp_id),
    "confidence": float(confidence),
    "confidence_pct": conf_pct,
    "is_late": is_late and event == "check_in",
    "bbox": bbox,
    "dept_name": dept_name,          # ← NEW field
})
```

---

### `templates/superadmin.html`, `org_admin.html`, `dept_admin.html`

**Analog:** `templates/admin.html` lines 1-64 (CSS variables, stat cards, table layout)

**HTML/CSS boilerplate to copy** (admin.html lines 1-64):
- `body`, `header`, `.logo`, `.logo-icon`, `.header-right`, `.user-badge`, `.btn-logout` — identical
- `.nav-tabs`, `.tab`, `.tab.active` — identical navigation pattern
- `.page`, `.stats-grid`, `.stat-card`, `.stat-label`, `.stat-val` — copy stat card pattern
- `.table-card`, `table`, `thead`, `th`, `td`, `.badge` classes — copy table pattern
- Color modifier classes: `.stat-val.blue`, `.stat-val.green`, `.stat-val.orange`

**Stat card HTML template** (admin.html lines 30-35):
```html
<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-label">МЕТКА</div>
    <div class="stat-val blue" id="statSomeValue">—</div>
  </div>
  ...
</div>
```

**Table HTML template** (admin.html lines 36-49):
```html
<div class="table-card">
  <table>
    <thead>
      <tr>
        <th>СТОЛБЕЦ</th>
      </tr>
    </thead>
    <tbody id="tableBody"></tbody>
  </table>
</div>
```

**JS fetch pattern** (inline script convention — no imports, no modules):
```javascript
// All JS inline in <script> block; fetch API for data; camelCase functions
async function loadOrgs() {
  const resp = await fetch("/api/orgs");
  const data = await resp.json();
  // populate table
}
```

**Navigation tab pattern** (admin.html lines 76-80):
```html
<div class="nav-tabs">
  {% if session.role in ['superadmin'] %}
  <span class="tab active" id="tabOrgs" onclick="switchTab('orgs')">Организации</span>
  {% endif %}
</div>
```

---

### `templates/kiosk.html` — dept_name display patch

**Analog:** `templates/kiosk.html` lines 156-179 (employee-card div) + lines 312-370 (showResult function)

**HTML insertion point** (after line 161, `.emp-role` div):
```html
<div class="emp-name" id="empName"></div>
<div class="emp-role" id="empRole"></div>
<!-- ADD after emp-role: -->
<div class="emp-dept" id="empDept" style="display:none; font-size:13px; color:#7986cb; margin-top:4px;"></div>
```

**JS display pattern** (after line 328 in showResult, mirroring the empRole pattern):
```javascript
// Existing pattern (line 328):
document.getElementById("empRole").textContent = emp.role;

// ADD after it:
const deptEl = document.getElementById("empDept");
if (deptEl) {
  if (data.dept_name) {
    deptEl.textContent = data.dept_name;
    deptEl.style.display = "";
  } else {
    deptEl.style.display = "none";
  }
}
```

---

### `migrate.py` — standalone migration script

**Analog:** `app.py` lines 155-177 (train_recognizer — LBPH training from face images)

**Train from files pattern** (lines 155-177):
```python
def train_recognizer():
    employees = load_employees()
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
                img = cv2.resize(img, (200, 200))
                faces.append(img)
                labels.append(label)
    if len(faces) >= 2:
        recognizer.train(faces, np.array(labels))
```

**File backup pattern** (analog: `app.py` line 381 shutil.rmtree — use shutil.copy2 for backup):
```python
import shutil
from datetime import datetime
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = os.path.join(DATA_DIR, f"employees_backup_{ts}.json")
shutil.copy2(EMPLOYEES_FILE, backup_path)
```

**Safe in-place employee patch** (from RESEARCH.md Pitfall 5 — NEVER reassign the whole record):
```python
# CORRECT — mutate only new keys:
employees[emp_id]["org_id"] = default_org_id
employees[emp_id]["dept_id"] = default_dept_id
employees[emp_id]["schedule"] = DEFAULT_SCHEDULE
# WRONG — would overwrite label, face_count etc.:
# employees[emp_id] = { ...new_record }
```

**Idempotency guard** (from RESEARCH.md anti-patterns):
```python
# Skip employees already migrated:
if emp.get("org_id"):
    continue
```

**getLabels() correct usage** (from RESEARCH.md Pitfall 2):
```python
# Returns shape (N, 1) numpy array — must flatten and cast:
trained_labels = set(int(x) for x in recognizer.getLabels().flatten())
```

---

### `tests/conftest.py` — extension (ORGS_FILE / DEPTS_FILE monkeypatches)

**Analog:** `tests/conftest.py` lines 54-56 (hasattr guard for USERS_FILE, lines 43-57)

**Pattern to copy** (lines 54-56):
```python
# USERS_FILE does not exist in app.py until plan 01-02 — guard with hasattr
if hasattr(_app, "USERS_FILE"):
    monkeypatch.setattr(_app, "USERS_FILE", str(data_dir / "users.json"))
```

**New additions follow same pattern:**
```python
if hasattr(_app, "ORGS_FILE"):
    monkeypatch.setattr(_app, "ORGS_FILE", str(data_dir / "orgs.json"))
if hasattr(_app, "DEPTS_FILE"):
    monkeypatch.setattr(_app, "DEPTS_FILE", str(data_dir / "depts.json"))
```

**Seeding helper pattern** (lines 87-109 — copy for org/dept seeds):
```python
def seed_users(tmp_data, users_dict):
    users_path = tmp_data / "data" / "users.json"
    users_path.write_text(json.dumps(users_dict, ensure_ascii=False, indent=2), encoding="utf-8")
```

---

### `tests/test_org_dept.py` and `tests/test_migration.py`

**Analog:** `tests/conftest.py` `client` fixture (lines 68-82) — all tests use `client` + `tmp_data`

**Authenticated client session pattern** (lines 68-82):
```python
@pytest.fixture()
def client(tmp_data, monkeypatch):
    import app as _app
    _app.app.testing = True
    _app.app.secret_key = "test-secret-key-for-pytest"
    with _app.app.test_client() as test_client:
        yield test_client
```

**Seeding + session injection pattern** (from seed_users, lines 87-109):
```python
# Seed data file directly, then inject session via test client:
seed_users(tmp_data, {"uid-1": {..., "role": "superadmin", "org_id": None, "dept_id": None}})
with client.session_transaction() as sess:
    sess["user_id"] = "uid-1"
    sess["role"] = "superadmin"
    sess["org_id"] = None
    sess["dept_id"] = None
```

---

## Shared Patterns

### Authentication / Role Guard
**Source:** `app.py` lines 82-98 (`require_role` decorator)
**Apply to:** All new page routes (`/superadmin`, `/org_admin`, `/dept_admin`) and all new API routes (`/api/orgs`, `/api/depts`, `/api/superadmin_stats`, `/api/dept_attendance_today`)
```python
@app.route("/superadmin")
@require_role("superadmin")
def superadmin_page():
    ...
```

### Session Scope Extraction
**Source:** `app.py` line 202-203 (login_page sets session org_id/dept_id)
**Apply to:** All scoped API write routes
```python
caller_role = session.get("role")
caller_org_id = session.get("org_id")
caller_dept_id = session.get("dept_id")
```

### JSON Error Response Format
**Source:** `app.py` lines 474-475, 389-390
**Apply to:** All new API endpoints
```python
return jsonify({"error": "Организация не найдена"}), 404
return jsonify({"error": "forbidden"}), 403
return jsonify({"error": "Конфликт: организация содержит отделы"}), 409
```

### File-backed JSON dict (load + flock save)
**Source:** `app.py` lines 46-56 (load_users / save_users)
**Apply to:** `load_orgs` / `save_orgs` / `load_depts` / `save_depts`
```python
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

### UUID4 ID generation
**Source:** `app.py` line 65 (`user_id = str(uuid.uuid4())`)
**Apply to:** `create_org`, `create_dept` handlers (NOT to `add_employee` which uses timestamp)
```python
org_id = str(uuid.uuid4())
```

### Section header dividers
**Source:** `app.py` lines 26, 44, 78, 100, 346, 400, 444, 511
**Apply to:** Every new section added to app.py
```python
# ─── API: Orgs ────────────────────────────────────────────────────────────────
# ─── API: Depts ───────────────────────────────────────────────────────────────
# ─── Page routes: Role Dashboards ─────────────────────────────────────────────
```

---

## No Analog Found

All files have close analogs. No entries needed.

---

## Metadata

**Analog search scope:** `/var/www/sites/face-almgp33/app.py`, `templates/admin.html`, `templates/kiosk.html`, `tests/conftest.py`
**Files scanned:** 4
**Pattern extraction date:** 2026-06-12
