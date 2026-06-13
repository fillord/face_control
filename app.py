import os, json, base64, time, shutil, uuid, tempfile, sys, secrets
import fcntl
import calendar
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import numpy as np
import cv2
import bcrypt

app = Flask(__name__)
_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable must be set to a long random string. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
app.secret_key = _secret_key

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FACES_DIR = os.path.join(DATA_DIR, "faces")
EMPLOYEES_FILE = os.path.join(DATA_DIR, "employees.json")
ATTENDANCE_FILE = os.path.join(DATA_DIR, "attendance.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
LOGS_FILE = os.path.join(DATA_DIR, "logs.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ORGS_FILE = os.path.join(DATA_DIR, "orgs.json")
DEPTS_FILE = os.path.join(DATA_DIR, "depts.json")
TIMESHEET_OVERRIDES_FILE = os.path.join(DATA_DIR, "timesheet_overrides.json")
os.makedirs(FACES_DIR, exist_ok=True)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer_trained = False

# ─── Config / Auth ────────────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_config():
    cfg = load_config()
    if "password_hash" not in cfg:
        pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        save_config({"username": "admin", "password_hash": pw_hash})

# ─── Auth: Users ──────────────────────────────────────────────────────────────

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARNING: load_users failed ({e}), returning empty dict", file=sys.stderr, flush=True)
            return {}
    return {}

def save_users(data):
    tmp_fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, prefix="users_", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, USERS_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

def init_users():
    if os.path.exists(USERS_FILE):
        return
    cfg = load_config()
    existing_hash = cfg.get("password_hash")
    if not existing_hash:
        existing_hash = bcrypt.hashpw(b"superadmin123", bcrypt.gensalt()).decode()
    user_id = str(uuid.uuid4())
    save_users({
        user_id: {
            "id": user_id,
            "username": "superadmin",
            "password_hash": existing_hash,
            "role": "superadmin",
            "active": True,
            "org_id": None,
            "dept_id": None,
        }
    })

# ─── Auth: RBAC ───────────────────────────────────────────────────────────────

ROLE_HIERARCHY = ['superadmin', 'org_admin', 'dept_admin', 'viewer', 'employee']

# Roles that are permitted to log in via the admin login page (AUTH-ROLE-01)
ALLOWED_LOGIN_ROLES = ("superadmin", "org_admin", "dept_admin")

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

# ─── Data helpers ─────────────────────────────────────────────────────────────

def load_employees():
    if os.path.exists(EMPLOYEES_FILE):
        with open(EMPLOYEES_FILE) as f:
            return json.load(f)
    return {}

def save_employees(data):
    with open(EMPLOYEES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_attendance():
    if os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE) as f:
            return json.load(f)
    return {}

def save_attendance(data):
    with open(ATTENDANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── Data helpers: Orgs / Depts ───────────────────────────────────────────────

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

def load_depts():
    if os.path.exists(DEPTS_FILE):
        with open(DEPTS_FILE) as f:
            return json.load(f)
    return {}

def save_depts(data):
    with open(DEPTS_FILE, "w", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fcntl.flock(fh, fcntl.LOCK_UN)

# ─── T-13 Timesheet ───────────────────────────────────────────────────────────

# Add next year's dates before January 1 of that year
KZ_HOLIDAYS = {
    2024: [
        "2024-01-01", "2024-01-02", "2024-01-07", "2024-03-08",
        "2024-03-21", "2024-03-22", "2024-03-23",
        "2024-05-01", "2024-05-07", "2024-05-09",
        "2024-07-06", "2024-08-30",
        "2024-10-25", "2024-12-01", "2024-12-16", "2024-12-17",
    ],
    2025: [
        "2025-01-01", "2025-01-02", "2025-01-07", "2025-03-08",
        "2025-03-21", "2025-03-22", "2025-03-23",
        "2025-05-01", "2025-05-07", "2025-05-09",
        "2025-07-06", "2025-08-30",
        "2025-10-25", "2025-12-01", "2025-12-16", "2025-12-17",
    ],
    2026: [
        "2026-01-01", "2026-01-02", "2026-01-07", "2026-03-08",
        "2026-03-21", "2026-03-22", "2026-03-23",
        "2026-05-01", "2026-05-07", "2026-05-09",
        "2026-07-06", "2026-08-30",
        "2026-10-25", "2026-12-01", "2026-12-16", "2026-12-17",
    ],
}

MANUAL_SYMBOLS = {"Б", "К", "П"}


def load_timesheet_overrides():
    if os.path.exists(TIMESHEET_OVERRIDES_FILE):
        try:
            with open(TIMESHEET_OVERRIDES_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARNING: load_timesheet_overrides failed ({e}), returning empty dict", file=sys.stderr, flush=True)
            return {}
    return {}


def save_timesheet_overrides(data):
    tmp_fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, prefix="overrides_", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, TIMESHEET_OVERRIDES_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def get_holidays_set(year):
    """Return a set of ISO date strings for KZ holidays in the given year."""
    return set(KZ_HOLIDAYS.get(year, []))


def is_holiday_year_missing(year):
    """Return True if no KZ holiday data is available for the given year."""
    return year not in KZ_HOLIDAYS


def compute_symbol(day_date, emp_id, attendance, overrides, schedule, holidays_set):
    """Return the T-13 symbol for one employee on one calendar day.

    Priority: override > В (weekend/holiday) > future-day None > attendance-derived > НН
    """
    date_str = day_date.isoformat()

    # 1. Manual override takes highest priority
    emp_overrides = overrides.get(emp_id, {})
    if date_str in emp_overrides:
        return emp_overrides[date_str]

    # 2. Weekend or public holiday → В
    work_days = schedule.get("work_days", [1, 2, 3, 4, 5])
    if day_date.isoweekday() not in work_days or date_str in holidays_set:
        return "В"

    # 3. Future work day → None (no data yet; exclude from totals)
    if day_date > date.today():
        return None

    # 4. Work day — check attendance
    day_records = attendance.get(date_str, {})
    rec = day_records.get(emp_id)
    if not rec or not rec.get("check_in"):
        return "НН"

    check_in = rec["check_in"]
    # Normalize HH:MM to HH:MM:SS for consistent string comparison (Pitfall 1)
    if len(check_in) == 5:
        check_in += ":00"

    check_out = rec.get("check_out")
    if check_out and len(check_out) == 5:
        check_out += ":00"

    # Late threshold: schedule start + 15 min (as HH:MM:00 string, Pitfall 1)
    sh, sm = map(int, schedule.get("start", "09:00").split(":"))
    late_m = sm + 15
    if late_m >= 60:
        late_threshold = f"{sh + 1:02d}:{late_m % 60:02d}:00"
    else:
        late_threshold = f"{sh:02d}:{late_m:02d}:00"

    # Early departure threshold: schedule end - 15 min (as HH:MM:00 string)
    eh, em = map(int, schedule.get("end", "18:00").split(":"))
    early_m = em - 15
    if early_m < 0:
        early_threshold = f"{eh - 1:02d}:{60 + early_m:02d}:00"
    else:
        early_threshold = f"{eh:02d}:{early_m:02d}:00"

    is_late = check_in > late_threshold
    is_early = bool(check_out) and check_out < early_threshold

    if is_late and is_early:
        return "ОУ"
    elif is_late:
        return "О"
    elif is_early:
        return "У"
    return "Я"


def compute_employee_totals(symbols, schedule):
    """Compute T13-07 totals from an employee's list of symbols for one month.

    Excludes None symbols (future days) from all counts.
    days_worked counts Я/О/У/ОУ; late counts О/ОУ; absences counts П/НН;
    vac_sick counts Б/К; hours_worked = days_worked × daily_hours.
    """
    days_worked = sum(1 for s in symbols if s in ("Я", "О", "У", "ОУ"))
    sh, sm = map(int, schedule.get("start", "09:00").split(":"))
    eh, em = map(int, schedule.get("end", "18:00").split(":"))
    daily_hours = (eh * 60 + em - (sh * 60 + sm)) / 60
    return {
        "days_worked": days_worked,
        "hours_worked": round(days_worked * daily_hours, 1),
        "absences": sum(1 for s in symbols if s in ("П", "НН")),
        "late": sum(1 for s in symbols if s in ("О", "ОУ")),
        "vac_sick": sum(1 for s in symbols if s in ("Б", "К")),
    }


def compute_timesheet_grid(year, month_num, scoped_employees, attendance, overrides, holidays_set):
    """Build the grid rows and totals for the T-13 timesheet.

    Returns (days, grid_rows) where:
      days: list of date objects for the month
      grid_rows: list of (emp_id, name, symbols, totals) tuples
    """
    _, num_days = calendar.monthrange(year, month_num)
    days = [date(year, month_num, 1) + timedelta(days=i) for i in range(num_days)]

    grid_rows = []
    for emp_id, emp in scoped_employees.items():
        schedule = emp.get("schedule", {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]})
        symbols = [compute_symbol(d, emp_id, attendance, overrides, schedule, holidays_set) for d in days]
        totals = compute_employee_totals(symbols, schedule)
        grid_rows.append((emp_id, emp.get("name", emp_id), symbols, totals))

    return days, grid_rows


def compute_dept_summary(year, month_num, org_id, employees, attendance, overrides):
    """DASH-04: Per-department attendance summary for a given month within an org.

    For each dept in the org:
      - employee_count: number of employees in the dept
      - work_days: total scheduled work days across all employees in the dept
        (per-employee: count days where isoweekday() in work_days AND not holiday)
      - days_with_ya: count across the dept's employees of days with symbol Я
      - attendance_rate: round(days_with_ya / work_days * 100, 1), or 0.0 if work_days == 0

    Returns a list of dicts sorted by dept_name:
      {dept_id, dept_name, employee_count, work_days, days_with_ya, attendance_rate}

    Scope: org_id is always from session — never from client input (T-03-summary-scope).
    Denominator is work days (Pitfall 5), not calendar days.
    """
    _, num_days = calendar.monthrange(year, month_num)
    days = [date(year, month_num, 1) + timedelta(days=i) for i in range(num_days)]
    holidays_set = get_holidays_set(year)

    # Collect all depts referenced by employees in this org
    dept_ids_in_org = set()
    for emp in employees.values():
        if emp.get("org_id") == org_id and emp.get("dept_id"):
            dept_ids_in_org.add(emp["dept_id"])

    summary_rows = []
    for dept_id in sorted(dept_ids_in_org):
        dept_employees = {
            eid: e for eid, e in employees.items()
            if e.get("org_id") == org_id and e.get("dept_id") == dept_id
        }
        if not dept_employees:
            continue

        total_work_days = 0
        total_ya = 0
        dept_name = dept_id  # fallback if dept name not available here

        for emp_id, emp in dept_employees.items():
            schedule = emp.get("schedule", {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]})
            work_days_list = schedule.get("work_days", [1, 2, 3, 4, 5])
            for d in days:
                if d.isoweekday() in work_days_list and d.isoformat() not in holidays_set:
                    total_work_days += 1
                    sym = compute_symbol(d, emp_id, attendance, overrides, schedule, holidays_set)
                    if sym == "Я":
                        total_ya += 1

        attendance_rate = round(total_ya / total_work_days * 100, 1) if total_work_days > 0 else 0.0

        summary_rows.append({
            "dept_id": dept_id,
            "dept_name": dept_name,
            "employee_count": len(dept_employees),
            "work_days": total_work_days,
            "days_with_ya": total_ya,
            "attendance_rate": attendance_rate,
        })

    return summary_rows


# ─── Org tokens / PIN helpers ─────────────────────────────────────────────────

def find_org_by_token(orgs, field, value):
    """Return (org_id, org) for the first org whose org.get(field) == value, else (None, None)."""
    for org_id, org in orgs.items():
        if org.get(field) == value:
            return org_id, org
    return None, None


def generate_unique_token(existing_tokens):
    """Generate an 8-char hex token (secrets.token_hex(4)) not already in existing_tokens."""
    while True:
        token = secrets.token_hex(4)
        if token not in existing_tokens:
            return token


def hash_pin(pin):
    """Return a bcrypt hash of the given PIN string."""
    return bcrypt.hashpw(str(pin).encode(), bcrypt.gensalt()).decode()


def is_bcrypt_hash(value):
    """Return True if value looks like a bcrypt hash (starts with '$2b$')."""
    return bool(value and str(value).startswith("$2b$"))


def is_reg_token_expired(org):
    """Return True if org.reg_token_expires is set and in the past.

    None/empty -> False (no expiry set).
    Malformed datetime string -> False (safe default — do not block on bad data).
    Timezone-aware ISO strings are compared naively by stripping tzinfo (Pitfall 6).
    """
    expires_str = org.get("reg_token_expires")
    if not expires_str:
        return False
    try:
        expires = datetime.fromisoformat(expires_str).replace(tzinfo=None)
        return datetime.now() > expires
    except (ValueError, TypeError):
        return False


def append_log(entry):
    logs = []
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE) as f:
            try:
                logs = json.load(f)
            except Exception:
                logs = []
    logs.append(entry)
    if len(logs) > 10000:
        logs = logs[-10000:]
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# ─── CV helpers ───────────────────────────────────────────────────────────────

def decode_image(b64_string):
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_bytes = base64.b64decode(b64_string)
    arr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

def extract_face(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None, None
    x, y, w, h = max(faces, key=lambda f: f[2]*f[3])
    face_roi = gray[y:y+h, x:x+w]
    face_roi = cv2.resize(face_roi, (200, 200))
    return face_roi, (int(x), int(y), int(w), int(h))

def train_recognizer():
    global recognizer_trained
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
        recognizer_trained = True
        return True
    recognizer_trained = False
    return False

# ─── Page routes ──────────────────────────────────────────────────────────────

@app.route("/")
def kiosk():
    employees = load_employees()
    return render_template("kiosk.html", has_employees=bool(employees),
                           org_id=None, org_name=None, has_pin=False)

@app.route("/kiosk/<org_token>")
def kiosk_token(org_token):
    orgs = load_orgs()
    org_id, org = find_org_by_token(orgs, "org_token", org_token)
    if not org:
        return render_template("error_token.html", message="Организация не найдена"), 404
    employees = load_employees()
    org_employees = {k: v for k, v in employees.items() if v.get("org_id") == org_id}
    has_pin = bool(org.get("kiosk_pin"))
    org_name = org.get("kiosk_display_name") or org.get("name")
    return render_template("kiosk.html", has_employees=bool(org_employees),
                           org_token=org_token, org_id=org_id,
                           org_name=org_name, has_pin=has_pin)

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET" and session.get("user_id"):
        role_now = session.get("role")
        if role_now == "superadmin":
            return redirect(url_for("superadmin_page"))
        elif role_now == "org_admin":
            return redirect(url_for("org_admin_page"))
        elif role_now in ("dept_admin", "viewer"):
            return redirect(url_for("dept_admin_page"))
        else:
            return redirect(url_for("dashboard_page"))
    error = None
    if request.method == "POST":
        users = load_users()
        username = request.form.get("username", "")
        password = request.form.get("password", "").encode()
        user = next((u for u in users.values() if u["username"] == username), None)
        if user and not user.get("active"):
            error = "Ваш аккаунт деактивирован. Обратитесь к администратору."
            print(f"LOGIN_FAIL: username={username!r} reason=deactivated", flush=True)
        elif user and bcrypt.checkpw(password, user["password_hash"].encode()):
            role = user["role"]
            # AUTH-ROLE-01: only allowed roles may log in
            if role not in ALLOWED_LOGIN_ROLES:
                print(f"LOGIN_FAIL: username={username!r} role={role!r} reason=role_not_allowed", flush=True)
                error = "Доступ запрещён для этой роли"
            else:
                session.clear()
                session["user_id"] = user["id"]
                session["role"] = role
                session["org_id"] = user.get("org_id")
                session["dept_id"] = user.get("dept_id")
                print(f"LOGIN_OK: username={username!r} role={role!r}", flush=True)
                if role == "superadmin":
                    return redirect(url_for("superadmin_page"))
                elif role == "org_admin":
                    return redirect(url_for("org_admin_page"))
                elif role == "dept_admin":
                    return redirect(url_for("dept_admin_page"))
                else:
                    return redirect(url_for("dashboard_page"))
        else:
            print(f"LOGIN_FAIL: username={username!r} user_found={user is not None} hash_match=False", flush=True)
            error = "Неверный логин или пароль"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/register")
@require_role("superadmin", "org_admin", "dept_admin")
def register_page():
    users = load_users()
    user = users.get(session.get("user_id"), {})
    caller_role = user.get("role", session.get("role"))
    caller_org_id = user.get("org_id", session.get("org_id"))
    caller_dept_id = user.get("dept_id", session.get("dept_id"))
    orgs = load_orgs()
    depts = load_depts()
    if caller_role == "superadmin":
        visible_orgs = list(orgs.values())
        visible_depts = list(depts.values())
    elif caller_role == "org_admin":
        visible_orgs = [orgs[caller_org_id]] if caller_org_id in orgs else []
        visible_depts = [d for d in depts.values() if d.get("org_id") == caller_org_id]
    else:
        visible_orgs = [orgs[caller_org_id]] if caller_org_id in orgs else []
        visible_depts = [depts[caller_dept_id]] if caller_dept_id in depts else []
    return render_template("register.html",
        caller_role=caller_role,
        caller_org_id=caller_org_id or "",
        caller_dept_id=caller_dept_id or "",
        visible_orgs=visible_orgs,
        visible_depts=visible_depts
    )

# ─── Page routes: Public token registration ────────────────────────────────────

@app.route("/register/<reg_token>")
def register_token(reg_token):
    """Public, token-gated mobile employee self-registration page (REG-TOKEN-01..02..03)."""
    orgs = load_orgs()
    org_id, org = find_org_by_token(orgs, "reg_token", reg_token)
    if not org:
        return render_template("error_token.html", message="Ссылка недействительна"), 404
    if is_reg_token_expired(org):
        return render_template("error_token.html",
                               message="Ссылка истекла. Обратитесь к администратору."), 410
    depts = load_depts()
    org_depts = [d for d in depts.values() if d.get("org_id") == org_id]
    return render_template(
        "register_token.html",
        reg_token=reg_token,
        org_id=org_id,
        org_name=org.get("name", ""),
        has_pin=bool(org.get("reg_pin")),
        depts=org_depts,
    )


# ─── API: Public token registration ───────────────────────────────────────────

@app.route("/api/register/<reg_token>/verify_pin", methods=["POST"])
def register_token_verify_pin(reg_token):
    """Verify reg_pin for a registration token link (REG-TOKEN-04..05)."""
    orgs = load_orgs()
    org_id, org = find_org_by_token(orgs, "reg_token", reg_token)
    if not org:
        return jsonify({"error": "not_found"}), 404
    if is_reg_token_expired(org):
        return jsonify({"error": "link_expired"}), 410
    stored = org.get("reg_pin")
    if not stored:
        # No PIN configured — open registration
        return jsonify({"verified": True})
    entered = str((request.json or {}).get("pin", ""))
    if len(entered) != 4 or not entered.isdigit():
        return jsonify({"error": "invalid_pin"}), 400
    if bcrypt.checkpw(entered.encode(), stored.encode()):
        return jsonify({"verified": True})
    return jsonify({"error": "wrong_pin", "verified": False}), 401


@app.route("/api/register/<reg_token>/submit", methods=["POST"])
def register_token_submit(reg_token):
    """Create a new employee scoped to the registration token's org (REG-TOKEN-06)."""
    orgs = load_orgs()
    org_id, org = find_org_by_token(orgs, "reg_token", reg_token)
    if not org:
        return jsonify({"error": "not_found"}), 404
    if is_reg_token_expired(org):
        return jsonify({"error": "link_expired"}), 410

    data = request.json or {}
    name = data.get("name", "").strip()
    dept_id = data.get("dept_id", "")

    if not name:
        return jsonify({"error": "ФИО обязательно"}), 400

    # Validate dept_id belongs to the token's org
    if dept_id:
        depts = load_depts()
        dept = depts.get(dept_id)
        if not dept or dept.get("org_id") != org_id:
            return jsonify({"error": "Недопустимый отдел для этой ссылки"}), 400

    employees = load_employees()
    emp_id = str(int(time.time() * 1000))
    label = len(employees) + 1

    employees[emp_id] = {
        "id": emp_id,
        "name": name,
        "role": "employee",
        "label": label,
        "registered_at": datetime.now().isoformat(),
        "face_count": 0,
        "org_id": org_id,
        "dept_id": dept_id or None,
        "schedule": {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]},
    }
    save_employees(employees)
    os.makedirs(os.path.join(FACES_DIR, emp_id), exist_ok=True)
    print(f"REGISTER_TOKEN: emp_id={emp_id!r} name={name!r} org_id={org_id!r} dept_id={dept_id!r}", flush=True)
    return jsonify({"id": emp_id, "status": "created"})


ROLE_DISPLAY = {
    "superadmin": "Суперадмин",
    "org_admin": "Администратор организации",
    "dept_admin": "Администратор отдела",
    "viewer": "Наблюдатель",
    "employee": "Сотрудник",
}

@app.route("/admin")
@require_role("superadmin", "org_admin", "dept_admin")
def admin_page():
    if session.get("role") == "superadmin":
        return redirect(url_for("superadmin_page"))
    users = load_users()
    user = users.get(session.get("user_id"), {})
    username = user.get("username", "")
    creator_role = user.get("role", "")
    creatable_roles = []
    if creator_role in ROLE_HIERARCHY:
        creator_idx = ROLE_HIERARCHY.index(creator_role)
        for role_key in ROLE_HIERARCHY[creator_idx + 1:]:
            creatable_roles.append((role_key, ROLE_DISPLAY.get(role_key, role_key)))
    return render_template("admin.html", username=username, creatable_roles=creatable_roles)

@app.route("/employee")
@require_role("employee")
def employee_page():
    users = load_users()
    user = users.get(session.get("user_id"), {})
    username = user.get("username", "")
    return render_template("dashboard.html", username=username)

# ─── Page routes: Role Dashboards ─────────────────────────────────────────────

@app.route("/superadmin")
@require_role("superadmin")
def superadmin_page():
    users = load_users()
    user = users.get(session.get("user_id"), {})
    username = user.get("username", "")
    role = user.get("role", "")
    return render_template("superadmin.html", username=username, role=role)


@app.route("/org_admin")
@require_role("org_admin")
def org_admin_page():
    users = load_users()
    user = users.get(session.get("user_id"), {})
    username = user.get("username", "")
    role = user.get("role", "")
    caller_org_id = session.get("org_id")
    org = load_orgs().get(caller_org_id)
    org_name = org.get("name") if org else ""
    org_token = org.get("org_token", "") if org else ""
    reg_token = org.get("reg_token", "") if org else ""
    reg_token_expires = org.get("reg_token_expires") if org else None
    kiosk_display_name = org.get("kiosk_display_name", "") if org else ""

    # DASH-04: optional ?summary_month=YYYY-MM — compute per-dept summary when present
    # Scope is always session["org_id"] — never from client (T-03-summary-scope)
    summary_month = request.args.get("summary_month", "")
    summary_rows = []
    if summary_month:
        try:
            sum_year, sum_month_num = map(int, summary_month.split("-"))
            if not (1 <= sum_month_num <= 12 and 2000 <= sum_year <= 2100):
                raise ValueError("out of range")
            # Load data for summary computation
            employees = load_employees()
            attendance = load_attendance()
            overrides = load_timesheet_overrides()
            depts = load_depts()
            rows = compute_dept_summary(
                sum_year, sum_month_num, caller_org_id, employees, attendance, overrides
            )
            # Enrich dept_name from depts dict
            for row in rows:
                dept = depts.get(row["dept_id"])
                if dept:
                    row["dept_name"] = dept.get("name", row["dept_id"])
            summary_rows = rows
        except (ValueError, AttributeError, TypeError):
            summary_month = ""
            summary_rows = []

    return render_template(
        "org_admin.html",
        username=username,
        role=role,
        org_name=org_name,
        org_id=caller_org_id or "",
        org_token=org_token,
        reg_token=reg_token,
        reg_token_expires=reg_token_expires or "",
        kiosk_display_name=kiosk_display_name,
        summary_month=summary_month,
        summary_rows=summary_rows,
    )


@app.route("/dept_admin")
@require_role("dept_admin", "viewer")
def dept_admin_page():
    users = load_users()
    user = users.get(session.get("user_id"), {})
    username = user.get("username", "")
    role = user.get("role", "")
    dept = load_depts().get(session.get("dept_id"))
    dept_name = dept.get("name") if dept else ""
    return render_template("dept_admin.html", username=username, role=role, dept_name=dept_name)


@app.route("/dashboard")
@require_role()
def dashboard_page():
    users = load_users()
    user = users.get(session.get("user_id"), {})
    username = user.get("username", "")
    return render_template("dashboard.html", username=username)

@app.route("/profile", methods=["GET", "POST"])
@require_role()
def profile_page():
    error = None
    success = None
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        users = load_users()
        user_id = session.get("user_id")
        user = users.get(user_id)
        if not user or not bcrypt.checkpw(current_password.encode(), user["password_hash"].encode()):
            error = "Текущий пароль введён неверно"
        elif new_password != confirm_password:
            error = "Новые пароли не совпадают"
        elif len(new_password) < 8:
            error = "Пароль должен содержать не менее 8 символов"
        else:
            users[user_id]["password_hash"] = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            save_users(users)
            success = "Пароль успешно изменён"
    return render_template("profile.html", error=error, success=success)

# ─── Page routes: T-13 Timesheet ──────────────────────────────────────────────

@app.route("/timesheet")
@require_role("dept_admin", "org_admin", "superadmin")
def timesheet():
    """T13-01: Render the T-13 attendance timesheet grid for a dept/month."""
    users = load_users()
    user = users.get(session.get("user_id"), {})
    username = user.get("username", "")
    role = session.get("role")
    session_dept_id = session.get("dept_id")
    session_org_id = session.get("org_id")

    # (a) Resolve month param
    month_str = request.args.get("month", datetime.now().strftime("%Y-%m"))
    try:
        year, month_num = map(int, month_str.split("-"))
        if not (1 <= month_num <= 12):
            raise ValueError("invalid month")
    except (ValueError, AttributeError):
        year, month_num = datetime.now().year, datetime.now().month
        month_str = f"{year:04d}-{month_num:02d}"

    # (b) Resolve dept scope (D-08: dept_admin param is ignored — always forced to session dept)
    dept_id_param = request.args.get("dept_id", "")
    depts = load_depts()
    dept_options = []

    if role == "dept_admin":
        dept_id = session_dept_id  # always fixed from session; param ignored
    elif role == "org_admin":
        if dept_id_param and dept_id_param in depts:
            dept = depts[dept_id_param]
            if dept.get("org_id") != session_org_id:
                return render_template("403.html"), 403
            dept_id = dept_id_param
        else:
            # Default to first dept in org
            org_depts = [did for did, d in depts.items() if d.get("org_id") == session_org_id]
            dept_id = org_depts[0] if org_depts else None
        # Build dept_options for selector
        dept_options = [
            {"id": did, "name": d.get("name", did)}
            for did, d in depts.items()
            if d.get("org_id") == session_org_id
        ]
    else:  # superadmin
        dept_id = dept_id_param or None
        # Build dept_options grouped by org for superadmin
        orgs = load_orgs()
        dept_options = []
        for org_id_key, org in orgs.items():
            org_depts = [
                {"id": did, "name": d.get("name", did), "org_name": org.get("name", org_id_key)}
                for did, d in depts.items()
                if d.get("org_id") == org_id_key
            ]
            if org_depts:
                dept_options.append({"org_id": org_id_key, "org_name": org.get("name", org_id_key), "depts": org_depts})

    # Resolve dept name for display
    if dept_id and dept_id in depts:
        dept_name = depts[dept_id].get("name", "")
    else:
        dept_name = ""

    # (c) Build days list
    _, num_days = calendar.monthrange(year, month_num)
    days = [date(year, month_num, 1) + timedelta(days=i) for i in range(num_days)]

    # (d) Load data
    attendance = load_attendance()
    employees = load_employees()
    overrides = load_timesheet_overrides()
    holidays_set = get_holidays_set(year)
    missing_holiday_year = is_holiday_year_missing(year)

    # Filter employees to dept scope (Pitfall 3: None dept_id is out-of-scope)
    if dept_id:
        scoped_employees = {eid: e for eid, e in employees.items() if e.get("dept_id") == dept_id}
    else:
        scoped_employees = {}

    # (e) Build grid rows and totals
    # Each cell is a dict: {sym: displayed_symbol, auto: auto_symbol, date: iso_date_str}
    # auto is the symbol computed without overrides — used by "Восстановить автоматически"
    # to repaint the cell client-side without a page reload.
    grid_rows = []
    for emp_id, emp in scoped_employees.items():
        schedule = emp.get("schedule", {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]})
        cells = []
        for d in days:
            sym = compute_symbol(d, emp_id, attendance, overrides, schedule, holidays_set)
            auto = compute_symbol(d, emp_id, attendance, {}, schedule, holidays_set)
            cells.append({"sym": sym, "auto": auto, "date": d.isoformat()})
        # symbols list for totals computation: use displayed symbols (overrides included)
        symbols = [c["sym"] for c in cells]
        totals = compute_employee_totals(symbols, schedule)
        grid_rows.append((emp_id, emp.get("name", emp_id), cells, totals))

    # (f) Render template
    return render_template(
        "timesheet.html",
        username=username,
        role=role,
        dept_name=dept_name,
        dept_id=dept_id,
        dept_options=dept_options,
        month_str=month_str,
        year=year,
        month_num=month_num,
        days=days,
        grid_rows=grid_rows,
        holidays_set=holidays_set,
        missing_holiday_year=missing_holiday_year,
        can_edit=(role in ("dept_admin", "org_admin", "superadmin")),
    )


# ─── API: T-13 Timesheet Override ────────────────────────────────────────────

@app.route("/api/timesheet/override", methods=["POST", "DELETE"])
@require_role("dept_admin", "org_admin", "superadmin")
def timesheet_override():
    """D-05: Inline manual override for timesheet cells.

    POST: set a manual symbol (Б/К/П) for emp_id on date.
    DELETE: remove override and restore auto-derived symbol.
    Scope-checked server-side from employees.json (never trust client dept/org).
    """
    role = session.get("role")
    session_dept_id = session.get("dept_id")
    session_org_id = session.get("org_id")

    data = request.get_json(silent=True) or {}
    emp_id = data.get("emp_id", "")
    date_str = data.get("date", "")

    # Validate emp exists
    emp = load_employees().get(emp_id)
    if not emp:
        return jsonify({"error": "employee_not_found"}), 404

    # Scope check: read dept/org from employee record (T-03-privesc mitigation)
    if role == "dept_admin" and emp.get("dept_id") != session_dept_id:
        return jsonify({"error": "forbidden"}), 403
    if role == "org_admin" and emp.get("org_id") != session_org_id:
        return jsonify({"error": "forbidden"}), 403
    # superadmin: unrestricted

    overrides = load_timesheet_overrides()

    if request.method == "DELETE":
        overrides.get(emp_id, {}).pop(date_str, None)
        save_timesheet_overrides(overrides)
        return jsonify({"deleted": True})

    # POST branch
    symbol = data.get("symbol", "")

    # Validate symbol is in the manual whitelist (T-03-inject mitigation)
    if symbol not in MANUAL_SYMBOLS:
        return jsonify({"error": "invalid_symbol"}), 422

    # Validate date_str is a non-empty YYYY-MM-DD string
    if not date_str or len(date_str) != 10 or date_str[4] != "-" or date_str[7] != "-":
        return jsonify({"error": "invalid_date"}), 422

    overrides.setdefault(emp_id, {})[date_str] = symbol
    save_timesheet_overrides(overrides)
    return jsonify({"symbol": symbol, "auto": False})


# ─── API: Users ───────────────────────────────────────────────────────────────

@app.route("/api/users", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def list_users():
    users = load_users()
    caller_role = session.get("role")
    caller_org_id = session.get("org_id")
    result = []
    for u in users.values():
        if caller_role == "org_admin" and u.get("org_id") != caller_org_id:
            continue
        result.append({
            "id": u["id"],
            "username": u["username"],
            "role": u["role"],
            "active": u["active"],
            "org_id": u.get("org_id"),
            "dept_id": u.get("dept_id"),
        })
    return jsonify(result)

@app.route("/api/users", methods=["POST"])
@require_role("superadmin", "org_admin", "dept_admin")
def create_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    target_role = data.get("role", "")
    creator_role = session.get("role")
    if not username:
        return jsonify({"error": "Логин не может быть пустым"}), 400
    if len(password) < 8:
        return jsonify({"error": "Пароль должен содержать не менее 8 символов"}), 400
    if target_role not in ROLE_HIERARCHY:
        return jsonify({"error": "Недопустимая роль"}), 400
    if (creator_role not in ROLE_HIERARCHY or
            ROLE_HIERARCHY.index(creator_role) >= ROLE_HIERARCHY.index(target_role)):
        return jsonify({"error": "forbidden"}), 403
    # superadmin may only create org_admin; org_admin manages all roles below them
    if creator_role == "superadmin" and target_role != "org_admin":
        return jsonify({"error": "Суперадминистратор может создавать только администраторов организаций"}), 403
    users = load_users()
    if any(u["username"] == username for u in users.values()):
        return jsonify({"error": "Пользователь с таким логином уже существует"}), 400
    # Determine org scope: org_admin and dept_admin are always forced to their own org
    caller_org_id = session.get("org_id")
    caller_dept_id = session.get("dept_id")
    if creator_role == "superadmin":
        new_org_id = data.get("org_id")
    else:
        new_org_id = caller_org_id  # org_admin/dept_admin may never cross org boundary
    new_dept_id = data.get("dept_id") or (caller_dept_id if creator_role == "dept_admin" else None)
    user_id = str(uuid.uuid4())
    users[user_id] = {
        "id": user_id,
        "username": username,
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "role": target_role,
        "active": True,
        "org_id": new_org_id,
        "dept_id": new_dept_id,
    }
    save_users(users)
    print(f"USER_CREATED: username={username!r} role={target_role!r} org_id={new_org_id!r} dept_id={new_dept_id!r}", flush=True)
    return jsonify({"id": user_id, "status": "created"})

@app.route("/api/users/<user_id>", methods=["PATCH"])
@require_role("superadmin", "org_admin", "dept_admin")
def update_user(user_id):
    users = load_users()
    if user_id not in users:
        return jsonify({"error": "Пользователь не найден"}), 404
    target = users[user_id]
    caller_role = session.get("role")
    target_role = target.get("role")
    if (caller_role not in ROLE_HIERARCHY or
            target_role not in ROLE_HIERARCHY or
            ROLE_HIERARCHY.index(caller_role) >= ROLE_HIERARCHY.index(target_role)):
        return jsonify({"error": "forbidden"}), 403
    data = request.get_json(silent=True) or {}
    if "active" in data:
        users[user_id]["active"] = bool(data["active"])
    save_users(users)
    return jsonify({"status": "updated", "active": users[user_id]["active"]})

# ─── API: Orgs ────────────────────────────────────────────────────────────────

@app.route("/api/orgs", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def list_orgs():
    return jsonify(list(load_orgs().values()))


@app.route("/api/orgs", methods=["POST"])
@require_role("superadmin")
def create_org():
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Название организации не может быть пустым"}), 400
    org_id = str(uuid.uuid4())
    orgs = load_orgs()
    # Build a seen-set of all existing tokens to guarantee uniqueness
    seen_tokens = set()
    for org in orgs.values():
        if org.get("org_token"):
            seen_tokens.add(org["org_token"])
        if org.get("reg_token"):
            seen_tokens.add(org["reg_token"])
    org_token = generate_unique_token(seen_tokens)
    seen_tokens.add(org_token)
    reg_token = generate_unique_token(seen_tokens)
    orgs[org_id] = {
        "id": org_id,
        "name": name,
        "description": data.get("description", ""),
        "created_at": datetime.now().isoformat(),
        "org_token": org_token,
        "reg_token": reg_token,
        "kiosk_pin": hash_pin("0000"),
        "reg_pin": hash_pin("1234"),
        "reg_token_expires": None,
        "kiosk_display_name": name,
    }
    save_orgs(orgs)
    return jsonify({"id": org_id, "status": "created"})


@app.route("/api/orgs/<org_id>", methods=["PUT"])
@require_role("superadmin")
def update_org(org_id):
    orgs = load_orgs()
    if org_id not in orgs:
        return jsonify({"error": "Организация не найдена"}), 404
    data = request.json or {}
    if "name" in data:
        name = data["name"].strip()
        if not name:
            return jsonify({"error": "Название организации не может быть пустым"}), 400
        orgs[org_id]["name"] = name
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
    employees = load_employees()
    if any(e.get("org_id") == org_id for e in employees.values()):
        return jsonify({"error": "Организация содержит сотрудников"}), 409
    del orgs[org_id]
    save_orgs(orgs)
    return jsonify({"status": "deleted"})


@app.route("/api/orgs/<org_id>/settings", methods=["PATCH"])
@require_role("superadmin", "org_admin")
def update_org_settings(org_id):
    orgs = load_orgs()
    if org_id not in orgs:
        return jsonify({"error": "Организация не найдена"}), 404
    caller_role = session.get("role")
    if caller_role == "org_admin" and session.get("org_id") != org_id:
        return jsonify({"error": "forbidden"}), 403
    data = request.json or {}

    # kiosk_pin — validate 4 digits; store as bcrypt hash
    if "kiosk_pin" in data:
        pin = data["kiosk_pin"]
        if pin:
            if len(str(pin)) != 4 or not str(pin).isdigit():
                return jsonify({"error": "PIN должен быть 4-значным числом"}), 400
            orgs[org_id]["kiosk_pin"] = hash_pin(pin)
        else:
            orgs[org_id]["kiosk_pin"] = None

    # reg_pin — same validation and bcrypt storage
    if "reg_pin" in data:
        pin = data["reg_pin"]
        if pin:
            if len(str(pin)) != 4 or not str(pin).isdigit():
                return jsonify({"error": "PIN должен быть 4-значным числом"}), 400
            orgs[org_id]["reg_pin"] = hash_pin(pin)
        else:
            orgs[org_id]["reg_pin"] = None

    # regen_reg_token — generate a new unique 8-hex reg_token
    if data.get("regen_reg_token"):
        seen = set()
        for org in orgs.values():
            if org.get("org_token"):
                seen.add(org["org_token"])
            if org.get("reg_token"):
                seen.add(org["reg_token"])
        orgs[org_id]["reg_token"] = generate_unique_token(seen)

    # reg_token_expires — store ISO string or clear to None
    if "reg_token_expires" in data:
        expires = data["reg_token_expires"]
        if expires:
            try:
                datetime.fromisoformat(expires)
            except (ValueError, TypeError):
                return jsonify({"error": "Неверный формат даты (ожидается ISO 8601)"}), 400
            orgs[org_id]["reg_token_expires"] = expires
        else:
            orgs[org_id]["reg_token_expires"] = None

    # kiosk_display_name — store trimmed string (allow empty)
    if "kiosk_display_name" in data:
        orgs[org_id]["kiosk_display_name"] = str(data["kiosk_display_name"]).strip()

    save_orgs(orgs)
    return jsonify({"status": "updated", "reg_token": orgs[org_id].get("reg_token")})


@app.route("/api/kiosk/<org_token>/verify_pin", methods=["POST"])
def verify_kiosk_pin_token(org_token):
    orgs = load_orgs()
    org_id, org = find_org_by_token(orgs, "org_token", org_token)
    if not org:
        return jsonify({"error": "not_found"}), 404
    stored = org.get("kiosk_pin")
    if not stored:
        return jsonify({"verified": True})
    entered = str((request.json or {}).get("pin", ""))
    if len(entered) != 4 or not entered.isdigit():
        return jsonify({"error": "invalid_pin"}), 400
    if bcrypt.checkpw(entered.encode(), stored.encode()):
        return jsonify({"verified": True})
    return jsonify({"error": "wrong_pin", "verified": False}), 401


# ─── API: Depts ───────────────────────────────────────────────────────────────

@app.route("/api/depts", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def list_depts():
    caller_role = session.get("role")
    caller_org_id = session.get("org_id")
    depts = load_depts()
    if caller_role in ("org_admin", "dept_admin"):
        result = [d for d in depts.values() if d.get("org_id") == caller_org_id]
    else:
        result = list(depts.values())
    return jsonify(result)


@app.route("/api/depts", methods=["POST"])
@require_role("superadmin", "org_admin")
def create_dept():
    caller_role = session.get("role")
    caller_org_id = session.get("org_id")
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Название отдела не может быть пустым"}), 400
    # org_admin always creates within their own org regardless of request body
    if caller_role == "org_admin":
        target_org_id = caller_org_id
    else:
        target_org_id = data.get("org_id")
    dept_id = str(uuid.uuid4())
    depts = load_depts()
    depts[dept_id] = {
        "id": dept_id,
        "org_id": target_org_id,
        "name": name,
        "head_name": data.get("head_name", ""),
        "created_at": datetime.now().isoformat(),
    }
    save_depts(depts)
    return jsonify({"id": dept_id, "status": "created"})


@app.route("/api/depts/<dept_id>", methods=["PUT"])
@require_role("superadmin", "org_admin")
def update_dept(dept_id):
    caller_role = session.get("role")
    caller_org_id = session.get("org_id")
    depts = load_depts()
    if dept_id not in depts:
        return jsonify({"error": "Отдел не найден"}), 404
    dept = depts[dept_id]
    if caller_role == "org_admin" and dept.get("org_id") != caller_org_id:
        return jsonify({"error": "forbidden"}), 403
    data = request.json or {}
    if "name" in data:
        name = data["name"].strip()
        if not name:
            return jsonify({"error": "Название отдела не может быть пустым"}), 400
        depts[dept_id]["name"] = name
    if "head_name" in data:
        depts[dept_id]["head_name"] = data["head_name"]
    save_depts(depts)
    return jsonify({"status": "updated"})


@app.route("/api/depts/<dept_id>", methods=["DELETE"])
@require_role("superadmin", "org_admin")
def delete_dept(dept_id):
    caller_role = session.get("role")
    caller_org_id = session.get("org_id")
    depts = load_depts()
    if dept_id not in depts:
        return jsonify({"error": "Отдел не найден"}), 404
    dept = depts[dept_id]
    if caller_role == "org_admin" and dept.get("org_id") != caller_org_id:
        return jsonify({"error": "forbidden"}), 403
    employees = load_employees()
    if any(e.get("dept_id") == dept_id for e in employees.values()):
        return jsonify({"error": "Отдел содержит сотрудников"}), 409
    del depts[dept_id]
    save_depts(depts)
    return jsonify({"status": "deleted"})


# ─── API: Employees ───────────────────────────────────────────────────────────

@app.route("/api/employees", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def get_employees():
    employees = load_employees()
    role = session.get("role")
    org_id = session.get("org_id")
    dept_id = session.get("dept_id")
    if role == "superadmin":
        return jsonify(employees)
    elif role == "org_admin" and org_id:
        return jsonify({k: v for k, v in employees.items() if v.get("org_id") == org_id})
    elif role == "dept_admin" and dept_id:
        return jsonify({k: v for k, v in employees.items() if v.get("dept_id") == dept_id})
    return jsonify(employees)

@app.route("/api/employees", methods=["POST"])
@require_role("superadmin", "org_admin", "dept_admin")
def add_employee():
    caller_role = session.get("role")
    caller_dept_id = session.get("dept_id")
    caller_org_id = session.get("org_id")
    data = request.json or {}

    # Scope gate: dept_admin may only create in their own dept
    target_dept_id = data.get("dept_id")
    if caller_role == "dept_admin" and target_dept_id != caller_dept_id:
        return jsonify({"error": "forbidden"}), 403

    employees = load_employees()
    emp_id = str(int(time.time() * 1000))
    label = len(employees) + 1

    # Determine org_id/dept_id: dept_admin defaults to session values when omitted
    org_id = data.get("org_id") if caller_role != "dept_admin" else (data.get("org_id") or caller_org_id)
    dept_id = target_dept_id if caller_role != "dept_admin" else caller_dept_id

    employees[emp_id] = {
        "id": emp_id,
        "name": data["name"],
        "role": data.get("role", "employee"),
        "label": label,
        "registered_at": datetime.now().isoformat(),
        "face_count": 0,
        "org_id": org_id,
        "dept_id": dept_id,
        "schedule": data.get("schedule", {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}),
    }
    save_employees(employees)
    os.makedirs(os.path.join(FACES_DIR, emp_id), exist_ok=True)
    return jsonify({"id": emp_id, "status": "created"})


@app.route("/api/employees/<emp_id>", methods=["PATCH"])
@require_role("superadmin", "org_admin")
def update_employee_assignment(emp_id):
    """ORG-04: reassign employee to another dept; org_admin restricted to own org scope."""
    caller_role = session.get("role")
    caller_org_id = session.get("org_id")
    employees = load_employees()
    if emp_id not in employees:
        return jsonify({"error": "Сотрудник не найден"}), 404

    data = request.json or {}

    # Whitelist: only dept_id (and org_id for superadmin); never touch label/face_count/name
    allowed_keys = {"dept_id", "org_id"} if caller_role == "superadmin" else {"dept_id"}
    update_data = {k: v for k, v in data.items() if k in allowed_keys}

    if "dept_id" in update_data:
        target_dept_id = update_data["dept_id"]
        if caller_role == "org_admin":
            # Verify target dept belongs to caller's org
            depts = load_depts()
            target_dept = depts.get(target_dept_id)
            if not target_dept or target_dept.get("org_id") != caller_org_id:
                return jsonify({"error": "forbidden"}), 403

    for k, v in update_data.items():
        employees[emp_id][k] = v

    save_employees(employees)
    return jsonify({"status": "updated"})

@app.route("/api/employees/<emp_id>", methods=["DELETE"])
@require_role("superadmin", "org_admin", "dept_admin")
def delete_employee(emp_id):
    employees = load_employees()
    if emp_id not in employees:
        return jsonify({"status": "deleted"})
    emp = employees[emp_id]
    role = session.get("role")
    if role == "dept_admin" and emp.get("dept_id") != session.get("dept_id"):
        return jsonify({"error": "forbidden"}), 403
    if role == "org_admin" and emp.get("org_id") != session.get("org_id"):
        return jsonify({"error": "forbidden"}), 403
    del employees[emp_id]
    save_employees(employees)
    emp_dir = os.path.join(FACES_DIR, emp_id)
    if os.path.exists(emp_dir):
        shutil.rmtree(emp_dir)
    train_recognizer()
    return jsonify({"status": "deleted"})

@app.route("/api/employees/<emp_id>", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def get_employee(emp_id):
    employees = load_employees()
    if emp_id not in employees:
        return jsonify({"error": "Сотрудник не найден"}), 404
    return jsonify(employees[emp_id])

@app.route("/api/employees/<emp_id>/schedule", methods=["PATCH"])
@require_role("superadmin", "org_admin", "dept_admin")
def update_employee_schedule(emp_id):
    """T13-06: Update per-employee work schedule with HH:MM validation."""
    caller_role = session.get("role")
    caller_dept_id = session.get("dept_id")
    employees = load_employees()
    if emp_id not in employees:
        return jsonify({"error": "Сотрудник не найден"}), 404

    # Scope gate: dept_admin may only edit employees in their own dept
    emp = employees[emp_id]
    if caller_role == "dept_admin" and emp.get("dept_id") != caller_dept_id:
        return jsonify({"error": "forbidden"}), 403

    data = request.json or {}
    start = data.get("start", "")
    end = data.get("end", "")
    work_days = data.get("work_days")

    # Validate HH:MM format with range check
    def valid_time(t):
        import re
        if not re.match(r'^\d{2}:\d{2}$', str(t)):
            return False
        h, m = map(int, t.split(":"))
        return 0 <= h <= 23 and 0 <= m <= 59

    if not valid_time(start) or not valid_time(end):
        return jsonify({"error": "Неверный формат времени"}), 400

    # Validate work_days is a list of ints in 1..7
    if not isinstance(work_days, list) or not work_days:
        return jsonify({"error": "Неверный формат рабочих дней"}), 400
    for d in work_days:
        if not isinstance(d, int) or d < 1 or d > 7:
            return jsonify({"error": "Неверный формат рабочих дней"}), 400

    # Whitelist: only update schedule sub-fields
    employees[emp_id]["schedule"] = {"start": start, "end": end, "work_days": work_days}
    save_employees(employees)
    return jsonify({"status": "updated"})

@app.route("/api/employees/<emp_id>/reset", methods=["POST"])
@require_role("superadmin", "org_admin", "dept_admin")
def reset_employee_face(emp_id):
    employees = load_employees()
    if emp_id not in employees:
        return jsonify({"error": "Сотрудник не найден"}), 404
    emp = employees[emp_id]
    role = session.get("role")
    if role == "dept_admin" and emp.get("dept_id") != session.get("dept_id"):
        return jsonify({"error": "forbidden"}), 403
    if role == "org_admin" and emp.get("org_id") != session.get("org_id"):
        return jsonify({"error": "forbidden"}), 403
    emp_dir = os.path.join(FACES_DIR, emp_id)
    if os.path.exists(emp_dir):
        shutil.rmtree(emp_dir)
    os.makedirs(emp_dir, exist_ok=True)
    employees[emp_id]["face_count"] = 0
    save_employees(employees)
    train_recognizer()
    return jsonify({"status": "reset", "face_count": 0})

# ─── API: Dashboards ──────────────────────────────────────────────────────────

@app.route("/api/superadmin_stats", methods=["GET"])
@require_role("superadmin")
def superadmin_stats():
    """DASH-01: System-wide stats for superadmin dashboard."""
    attendance = load_attendance()
    today = date.today().isoformat()
    today_records = attendance.get(today, {})
    checkins_today = sum(
        1 for rec in today_records.values() if rec.get("check_in")
    )
    return jsonify({
        "orgs": len(load_orgs()),
        "employees": len(load_employees()),
        "checkins_today": checkins_today,
    })


@app.route("/api/dept_attendance_today", methods=["GET"])
@require_role("dept_admin", "org_admin", "superadmin")
def dept_attendance_today():
    """DASH-02: Today's attendance scoped by caller role (dept_admin→dept, org_admin→org, superadmin→all)."""
    role = session.get("role")
    dept_id = session.get("dept_id")
    org_id = session.get("org_id")

    employees = load_employees()
    attendance = load_attendance()
    today = date.today().isoformat()
    today_weekday = date.today().weekday() + 1  # ISO 1=Mon, 7=Sun
    today_records = attendance.get(today, {})

    # Filter employees by scope
    if role == "dept_admin":
        scoped = {eid: e for eid, e in employees.items() if e.get("dept_id") == dept_id}
    elif role == "org_admin":
        scoped = {eid: e for eid, e in employees.items() if e.get("org_id") == org_id}
    else:  # superadmin — all employees
        scoped = employees

    result = []
    present = absent = late = 0

    for eid, emp in scoped.items():
        schedule = emp.get("schedule", {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]})
        work_days = schedule.get("work_days", [1, 2, 3, 4, 5])

        if today_weekday not in work_days:
            continue  # Day off — do not count as absent (A3)

        rec = today_records.get(eid)
        check_in = rec.get("check_in") if rec else None
        check_out = rec.get("check_out") if rec else None

        # Late detection: check_in > schedule.start + 15 min grace (A1)
        schedule_start = schedule.get("start", "09:00")
        sh, sm = map(int, schedule_start.split(":"))
        late_m = sm + 15
        if late_m < 60:
            late_threshold = f"{sh:02d}:{late_m:02d}:00"
        else:
            late_threshold = f"{sh + 1:02d}:{late_m % 60:02d}:00"

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

# ─── API: Face Registration ───────────────────────────────────────────────────

@app.route("/api/register_face", methods=["POST"])
@require_role("superadmin", "org_admin", "dept_admin")
def register_face():
    data = request.get_json(silent=True) or {}
    if not data.get("emp_id") or not data.get("image"):
        return jsonify({"error": "emp_id and image required"}), 400
    emp_id = data["emp_id"]
    employees = load_employees()
    if emp_id not in employees:
        return jsonify({"error": "Сотрудник не найден"}), 404

    img = decode_image(data["image"])
    face_roi, bbox = extract_face(img)
    if face_roi is None:
        return jsonify({"error": "Лицо не обнаружено. Убедитесь, что лицо хорошо видно в кадре."}), 400

    emp_dir = os.path.join(FACES_DIR, emp_id)
    os.makedirs(emp_dir, exist_ok=True)
    count = employees[emp_id].get("face_count", 0) + 1
    cv2.imwrite(os.path.join(emp_dir, f"face_{count}.jpg"), face_roi)
    employees[emp_id]["face_count"] = count
    save_employees(employees)
    train_recognizer()
    return jsonify({"status": "saved", "count": count, "bbox": bbox})

@app.route("/api/detect", methods=["POST"])
def detect_face_only():
    """Detect face bbox without saving — used for live preview overlay."""
    try:
        data = request.json
        img = decode_image(data["image"])
        if img is None:
            return jsonify({"face": False})
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) == 0:
            return jsonify({"face": False})
        x, y, w, h = max(faces, key=lambda f: f[2]*f[3])
        faces_strict = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=9, minSize=(80, 80))
        quality = "good" if len(faces_strict) > 0 else "ok"
        return jsonify({"face": True, "bbox": [int(x), int(y), int(w), int(h)], "quality": quality})
    except Exception:
        return jsonify({"face": False})

# ─── API: Recognition ─────────────────────────────────────────────────────────

@app.route("/api/recognize", methods=["POST"])
def recognize():
    global recognizer_trained
    employees = load_employees()
    if not employees:
        return jsonify({"error": "no_employees"}), 400

    if not recognizer_trained:
        ok = train_recognizer()
        if not ok:
            return jsonify({"error": "not_trained"}), 400

    data = request.get_json(silent=True) or {}
    if "image" not in data:
        return jsonify({"error": "image required"}), 400
    img = decode_image(data["image"])
    face_roi, bbox = extract_face(img)
    if face_roi is None:
        return jsonify({"error": "no_face"}), 400

    label, confidence = recognizer.predict(face_roi)
    # LBPH: lower confidence = better. Threshold ~80. Convert to % (0–100 good to bad).
    conf_pct = max(0, min(100, round(100 - (confidence / 80 * 100))))

    if confidence > 80:
        append_log({"ts": datetime.now().isoformat(), "event": "unknown",
                    "confidence_raw": float(confidence), "confidence_pct": conf_pct})
        return jsonify({"error": "unknown", "confidence": float(confidence)}), 400

    emp = next((e for e in employees.values() if e.get("label") == label), None)
    if not emp:
        return jsonify({"error": "unknown"}), 400

    # Org filter: if request specifies org_id, reject matches from other orgs
    req_org_id = data.get("org_id")
    if req_org_id and emp.get("org_id") != req_org_id:
        return jsonify({"error": "unknown"}), 400

    dept_name = None
    if emp.get("dept_id"):
        dept = load_depts().get(emp["dept_id"])
        if dept:
            dept_name = dept.get("name")

    today = date.today().isoformat()
    attendance = load_attendance()
    if today not in attendance:
        attendance[today] = {}

    emp_id = emp["id"]
    now_dt = datetime.now()
    now = now_dt.strftime("%H:%M:%S")
    is_late = now > "09:00:00"

    if emp_id not in attendance[today]:
        attendance[today][emp_id] = {"check_in": now, "check_out": None}
        event = "check_in"
    elif attendance[today][emp_id]["check_out"] is None:
        attendance[today][emp_id]["check_out"] = now
        event = "check_out"
    else:
        event = "already_done"

    save_attendance(attendance)
    append_log({"ts": now_dt.isoformat(), "emp_id": emp_id, "name": emp["name"],
                "event": event, "confidence_raw": float(confidence), "confidence_pct": conf_pct})

    return jsonify({
        "status": "ok",
        "employee": emp,
        "event": event,
        "record": attendance[today].get(emp_id),
        "confidence": float(confidence),
        "confidence_pct": conf_pct,
        "is_late": is_late and event == "check_in",
        "bbox": bbox,
        "dept_name": dept_name,
    })

# ─── API: Kiosk public log ────────────────────────────────────────────────────

@app.route("/api/kiosk_log")
def kiosk_log():
    """Public endpoint for kiosk attendance log — no auth, today only, optional org filter."""
    org_id = request.args.get("org_id")
    attendance = load_attendance()
    employees = load_employees()
    today = date.today().isoformat()
    day_data = attendance.get(today, {})
    result = []
    for emp_id, emp in employees.items():
        if org_id and emp.get("org_id") != org_id:
            continue
        rec = day_data.get(emp_id, {})
        if rec.get("check_in"):
            result.append({"name": emp["name"], "role": emp["role"],
                           "check_in": rec.get("check_in"), "check_out": rec.get("check_out")})
    return jsonify(result)

# ─── API: Attendance ──────────────────────────────────────────────────────────

@app.route("/api/attendance", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def get_attendance():
    day = request.args.get("date", date.today().isoformat())
    attendance = load_attendance()
    employees = load_employees()
    day_data = attendance.get(day, {})
    result = []
    for emp_id, emp in employees.items():
        rec = day_data.get(emp_id, {})
        check_in = rec.get("check_in")
        check_out = rec.get("check_out")
        duration = None
        duration_minutes = None
        if check_in and check_out:
            fmt = "%H:%M:%S"
            delta = datetime.strptime(check_out, fmt) - datetime.strptime(check_in, fmt)
            total = int(delta.total_seconds())
            duration_minutes = total // 60
            duration = f"{total//3600}ч {(total%3600)//60}мин"
        result.append({
            "emp_id": emp_id,
            "name": emp["name"],
            "role": emp["role"],
            "check_in": check_in,
            "check_out": check_out,
            "duration": duration,
            "duration_minutes": duration_minutes
        })
    return jsonify(result)

@app.route("/api/attendance/dates", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def get_dates():
    attendance = load_attendance()
    return jsonify(sorted(attendance.keys(), reverse=True))

@app.route("/api/stats", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def get_stats():
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    attendance = load_attendance()
    employees = load_employees()

    dates = sorted(attendance.keys())
    if from_date:
        dates = [d for d in dates if d >= from_date]
    if to_date:
        dates = [d for d in dates if d <= to_date]

    emp_stats = {
        eid: {"name": e["name"], "role": e["role"], "days": 0, "minutes": 0, "late_days": 0}
        for eid, e in employees.items()
    }
    daily_counts = []
    for d in dates:
        day_data = attendance[d]
        present = 0
        for eid, rec in day_data.items():
            check_in = rec.get("check_in")
            check_out = rec.get("check_out")
            if not check_in:
                continue
            present += 1
            if eid in emp_stats:
                emp_stats[eid]["days"] += 1
                if check_in > "09:00:00":
                    emp_stats[eid]["late_days"] += 1
                if check_out:
                    ci = datetime.strptime(check_in, "%H:%M:%S")
                    co = datetime.strptime(check_out, "%H:%M:%S")
                    emp_stats[eid]["minutes"] += int((co - ci).total_seconds()) // 60
        daily_counts.append({"date": d, "count": present})

    for es in emp_stats.values():
        h = es["minutes"] // 60
        m = es["minutes"] % 60
        es["hours_str"] = f"{h}ч {m}мин"
        es["hours"] = round(es["minutes"] / 60, 1)

    return jsonify({
        "dates": dates,
        "daily_counts": daily_counts,
        "employee_stats": list(emp_stats.values()),
        "total_days": len(dates)
    })

# ─── Startup ──────────────────────────────────────────────────────────────────

init_config()
init_users()

if __name__ == "__main__":
    train_recognizer()
    app.run(debug=True, host="0.0.0.0", port=5050)
