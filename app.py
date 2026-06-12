import os, json, base64, time, shutil, uuid
import fcntl
from datetime import datetime, date
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import numpy as np
import cv2
import bcrypt

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "medkontrol-secret-2026-xK9mP3qR7v")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FACES_DIR = os.path.join(DATA_DIR, "faces")
EMPLOYEES_FILE = os.path.join(DATA_DIR, "employees.json")
ATTENDANCE_FILE = os.path.join(DATA_DIR, "attendance.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
LOGS_FILE = os.path.join(DATA_DIR, "logs.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ORGS_FILE = os.path.join(DATA_DIR, "orgs.json")
DEPTS_FILE = os.path.join(DATA_DIR, "depts.json")
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
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fcntl.flock(fh, fcntl.LOCK_UN)

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
    return render_template("kiosk.html", has_employees=bool(employees))

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
        elif user and bcrypt.checkpw(password, user["password_hash"].encode()):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["org_id"] = user.get("org_id")
            session["dept_id"] = user.get("dept_id")
            role = user["role"]
            if role == "superadmin":
                return redirect(url_for("superadmin_page"))
            elif role == "org_admin":
                return redirect(url_for("org_admin_page"))
            elif role in ("dept_admin", "viewer"):
                return redirect(url_for("dept_admin_page"))
            else:
                return redirect(url_for("dashboard_page"))
        else:
            error = "Неверный логин или пароль"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/register")
@require_role("superadmin", "org_admin", "dept_admin")
def register_page():
    return render_template("register.html")

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
    return render_template("org_admin.html", username=username, role=role)


@app.route("/dept_admin")
@require_role("dept_admin", "viewer")
def dept_admin_page():
    users = load_users()
    user = users.get(session.get("user_id"), {})
    username = user.get("username", "")
    role = user.get("role", "")
    return render_template("dept_admin.html", username=username, role=role)


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

# ─── API: Users ───────────────────────────────────────────────────────────────

@app.route("/api/users", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def list_users():
    users = load_users()
    result = []
    for u in users.values():
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
    data = request.json
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
    users = load_users()
    if any(u["username"] == username for u in users.values()):
        return jsonify({"error": "Пользователь с таким логином уже существует"}), 400
    user_id = str(uuid.uuid4())
    users[user_id] = {
        "id": user_id,
        "username": username,
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "role": target_role,
        "active": True,
        "org_id": None,
        "dept_id": None,
    }
    save_users(users)
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
    data = request.json
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
    orgs[org_id] = {
        "id": org_id,
        "name": name,
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
    target_org_id = data.get("org_id")
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Название отдела не может быть пустым"}), 400
    if caller_role == "org_admin" and target_org_id != caller_org_id:
        return jsonify({"error": "forbidden"}), 403
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
    return jsonify(load_employees())

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
    if emp_id in employees:
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
    data = request.json
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

    data = request.json
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
        "bbox": bbox
    })

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
