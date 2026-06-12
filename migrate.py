#!/usr/bin/env python3
"""
migrate.py — Phase 2 data migration
Run once: python migrate.py

Adds org_id, dept_id, and schedule fields to every existing employee record.
Creates default org "Главная организация" and dept "Основной отдел" in orgs.json and depts.json.
Backs up employees.json before patching.
Warns (never aborts) on face recognizer label integrity issues.
"""
import fcntl
import glob
import json
import os
import shutil
import uuid
from datetime import datetime

import cv2
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
FACES_DIR = os.path.join(DATA_DIR, "faces")
EMPLOYEES_FILE = os.path.join(DATA_DIR, "employees.json")
ORGS_FILE = os.path.join(DATA_DIR, "orgs.json")
DEPTS_FILE = os.path.join(DATA_DIR, "depts.json")

DEFAULT_SCHEDULE = {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}


def _load_json(path):
    """Load JSON dict from path; return {} if file absent."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_json(path, data):
    """Save data to path with fcntl.flock(LOCK_EX) for safe concurrent writes."""
    with open(path, "w", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fcntl.flock(fh, fcntl.LOCK_UN)


def check_label_integrity(employees):
    """Train LBPH in-memory from face image files under FACES_DIR/<emp_id>/*.jpg.

    Returns set of trained label integers found in the model.
    If fewer than 2 face images are found total, returns an empty set —
    the model cannot be trained, and all labels are treated as unverifiable warnings.
    """
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces = []
    labels = []

    for emp_id, emp in employees.items():
        emp_dir = os.path.join(FACES_DIR, emp_id)
        if not os.path.exists(emp_dir):
            continue
        label = int(emp.get("label", 0))
        for fname in os.listdir(emp_dir):
            if not fname.lower().endswith(".jpg"):
                continue
            img_path = os.path.join(emp_dir, fname)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                faces.append(cv2.resize(img, (200, 200)))
                labels.append(label)

    if len(faces) < 2:
        return set()

    recognizer.train(faces, np.array(labels))
    trained_labels = set(int(x) for x in recognizer.getLabels().flatten())
    return trained_labels


def run_migration():
    """Execute the Phase 2 data migration.

    Steps:
    1. Back up employees.json to data/employees_backup_{ts}.json.
    2. Load or create orgs.json with default org "Главная организация".
    3. Load or create depts.json with default dept "Основной отдел".
    4. For each employee missing org_id: add org_id, dept_id, schedule (in-place).
    5. Run label integrity check; print WARN for any mismatched label.
    6. Save orgs, depts, employees; print summary.

    Returns a list of warning strings (may be empty).
    """
    warnings = []

    # ── Step 1: Backup employees.json ─────────────────────────────────────────
    if os.path.exists(EMPLOYEES_FILE):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(DATA_DIR, f"employees_backup_{ts}.json")
        shutil.copy2(EMPLOYEES_FILE, backup_path)
        print(f"  Резервная копия: {backup_path}")

    # ── Step 2: Load or create default org ────────────────────────────────────
    orgs = _load_json(ORGS_FILE)
    if not orgs:
        default_org_id = str(uuid.uuid4())
        orgs[default_org_id] = {
            "id": default_org_id,
            "name": "Главная организация",
            "description": "",
            "created_at": datetime.now().isoformat(),
        }
        print("  OK  Создана организация по умолчанию: Главная организация")
    else:
        default_org_id = list(orgs.keys())[0]
        print(f"  OK  Организация уже существует: {orgs[default_org_id].get('name')}")

    # ── Step 3: Load or create default dept ───────────────────────────────────
    depts = _load_json(DEPTS_FILE)
    if not depts:
        default_dept_id = str(uuid.uuid4())
        depts[default_dept_id] = {
            "id": default_dept_id,
            "org_id": default_org_id,
            "name": "Основной отдел",
            "head_name": "",
            "created_at": datetime.now().isoformat(),
        }
        print("  OK  Создан отдел по умолчанию: Основной отдел")
    else:
        default_dept_id = list(depts.keys())[0]
        print(f"  OK  Отдел уже существует: {depts[default_dept_id].get('name')}")

    # ── Step 4: Patch employees additively ────────────────────────────────────
    employees = _load_json(EMPLOYEES_FILE)
    updated_count = 0

    for emp_id, emp in employees.items():
        if emp.get("org_id"):
            # Already migrated — skip (idempotent)
            continue
        # Mutate in-place: only add the three new keys; never reassign the record
        employees[emp_id]["org_id"] = default_org_id
        employees[emp_id]["dept_id"] = default_dept_id
        employees[emp_id]["schedule"] = DEFAULT_SCHEDULE.copy()
        updated_count += 1
        print(f"  OK  {emp.get('name', emp_id)}: org_id и dept_id назначены")

    # ── Step 5: Label integrity check ─────────────────────────────────────────
    trained_labels = check_label_integrity(employees)
    warn_count = 0

    for emp_id, emp in employees.items():
        label = emp.get("label")
        if label is None:
            continue
        label_int = int(label)
        if not trained_labels or label_int not in trained_labels:
            warn_msg = (
                f"WARN: {emp.get('name', emp_id)} (label={label_int}) "
                f"не найден в обученной модели распознавания"
            )
            print(f"  {warn_msg}")
            warnings.append(warn_msg)
            warn_count += 1

    # ── Step 6: Save all data files ───────────────────────────────────────────
    _save_json(ORGS_FILE, orgs)
    _save_json(DEPTS_FILE, depts)
    if employees:
        _save_json(EMPLOYEES_FILE, employees)

    # ── Summary line ──────────────────────────────────────────────────────────
    print(
        f"Миграция завершена: {updated_count} сотрудников обновлено, "
        f"{warn_count} предупреждений."
    )

    return warnings


if __name__ == "__main__":
    run_migration()
