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
        return redirect(url_for("admin_page"))
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
            if user["role"] in ("superadmin", "org_admin", "dept_admin"):
                return redirect(url_for("admin_page"))
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

@app.route("/admin")
@require_role("superadmin", "org_admin", "dept_admin")
def admin_page():
    users = load_users()
    user = users.get(session.get("user_id"), {})
    username = user.get("username", "")
    return render_template("admin.html", username=username)

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

# ─── API: Employees ───────────────────────────────────────────────────────────

@app.route("/api/employees", methods=["GET"])
@require_role("superadmin", "org_admin", "dept_admin")
def get_employees():
    return jsonify(load_employees())

@app.route("/api/employees", methods=["POST"])
@require_role("superadmin", "org_admin", "dept_admin")
def add_employee():
    data = request.json
    employees = load_employees()
    emp_id = str(int(time.time() * 1000))
    label = len(employees) + 1
    employees[emp_id] = {
        "id": emp_id,
        "name": data["name"],
        "role": data["role"],
        "label": label,
        "registered_at": datetime.now().isoformat(),
        "face_count": 0
    }
    save_employees(employees)
    os.makedirs(os.path.join(FACES_DIR, emp_id), exist_ok=True)
    return jsonify({"id": emp_id, "status": "created"})

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
