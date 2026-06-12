"""
Migration requirement tests for Phase 2 (MIG-01, MIG-02).

Covers requirements:
  MIG-01 — Migration adds org_id, dept_id, schedule fields; all existing fields preserved verbatim.
  MIG-02 — Migration warns on label mismatch; does not abort.

All tests are @pytest.mark.xfail because migrate.py is created in plan 02-02.

The tests import migrate.py inside the test body (guarded by try/except ImportError) so that
collection never fails before migrate.py exists — the ImportError is swallowed under xfail.

Threat mitigation T-02-T1: All migrate.py path constants are monkeypatched to tmp_path via the
tmp_data fixture. No test touches the real data/ directory.
"""
import glob
import io
import json
import os
import pytest

from tests.conftest import seed_employees


# ─── MIG-01: Additive migration preserves existing fields, adds new ones ──────

@pytest.mark.xfail(reason="implemented in 02-02: migrate.py not yet built", strict=False)
def test_migration_additive(tmp_data):
    """MIG-01: migrate.py adds org_id, dept_id, and schedule fields to all employees;
    preserves all original fields verbatim (id, name, role, label, face_count, registered_at).
    Creates a default org 'Главная организация' and dept 'Основной отдел'.
    Writes a backup file employees_backup_*.json before patching.

    Steps:
    1. Seed one employee with original fields — no org_id, dept_id, or schedule.
    2. Run migration against tmp_data.
    3. Assert employee still has original label value (1) and name verbatim.
    4. Assert employee now has org_id, dept_id, and schedule == standard workday.
    5. Assert orgs.json has exactly one org named 'Главная организация'.
    6. Assert depts.json has exactly one dept named 'Основной отдел'.
    7. Assert an employees_backup_*.json file was created in data/.
    """
    try:
        import migrate
    except ImportError:
        pytest.xfail("migrate.py not yet created — MIG-01 will be green after plan 02-02")

    original_emp_id = "1781173156953"
    original_name = "Тест Сотрудник"
    original_label = 1
    original_face_count = 10
    original_registered_at = "2026-06-11T10:00:00"

    seed_employees(tmp_data, {
        original_emp_id: {
            "id": original_emp_id,
            "name": original_name,
            "role": "employee",
            "label": original_label,
            "face_count": original_face_count,
            "registered_at": original_registered_at,
            # Intentionally NO org_id, dept_id, or schedule — pre-migration state
        }
    })

    # Monkeypatch migrate.py's module-level path constants to tmp_data
    data_dir = tmp_data / "data"
    faces_dir = data_dir / "faces"

    for attr, val in [
        ("DATA_DIR", str(data_dir)),
        ("FACES_DIR", str(faces_dir)),
        ("EMPLOYEES_FILE", str(data_dir / "employees.json")),
        ("ORGS_FILE", str(data_dir / "orgs.json")),
        ("DEPTS_FILE", str(data_dir / "depts.json")),
    ]:
        if hasattr(migrate, attr):
            setattr(migrate, attr, val)

    # Run migration
    migrate.run_migration()

    # Reload employees from the tmp_data location
    employees_path = data_dir / "employees.json"
    assert employees_path.exists(), "employees.json must exist after migration"
    with open(str(employees_path), encoding="utf-8") as f:
        employees = json.load(f)

    assert original_emp_id in employees, (
        f"Employee {original_emp_id} must still exist after migration"
    )
    emp = employees[original_emp_id]

    # Original fields must be preserved verbatim
    assert emp["label"] == original_label, (
        f"label must be preserved as {original_label}, got {emp.get('label')}"
    )
    assert emp["name"] == original_name, (
        f"name must be preserved as '{original_name}', got {emp.get('name')}"
    )
    assert emp.get("face_count") == original_face_count, (
        f"face_count must be preserved as {original_face_count}, got {emp.get('face_count')}"
    )
    assert emp.get("registered_at") == original_registered_at, (
        f"registered_at must be preserved verbatim, got {emp.get('registered_at')}"
    )

    # New fields must be added by migration
    assert "org_id" in emp, "Migration must add org_id field to employee"
    assert "dept_id" in emp, "Migration must add dept_id field to employee"
    assert "schedule" in emp, "Migration must add schedule field to employee"

    # Schedule must match standard workday (D-08)
    expected_schedule = {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}
    schedule = emp["schedule"]
    assert schedule.get("start") == expected_schedule["start"], (
        f"schedule.start must be '09:00', got {schedule.get('start')}"
    )
    assert schedule.get("end") == expected_schedule["end"], (
        f"schedule.end must be '18:00', got {schedule.get('end')}"
    )
    assert schedule.get("work_days") == expected_schedule["work_days"], (
        f"schedule.work_days must be [1,2,3,4,5], got {schedule.get('work_days')}"
    )

    # orgs.json must have exactly one org named 'Главная организация' (D-05)
    orgs_path = data_dir / "orgs.json"
    assert orgs_path.exists(), "migration must create orgs.json"
    with open(str(orgs_path), encoding="utf-8") as f:
        orgs = json.load(f)
    assert len(orgs) == 1, f"orgs.json must have exactly 1 org after migration, got {len(orgs)}"
    default_org = list(orgs.values())[0]
    assert default_org.get("name") == "Главная организация", (
        f"Default org name must be 'Главная организация', got {default_org.get('name')}"
    )

    # depts.json must have exactly one dept named 'Основной отдел' (D-05)
    depts_path = data_dir / "depts.json"
    assert depts_path.exists(), "migration must create depts.json"
    with open(str(depts_path), encoding="utf-8") as f:
        depts = json.load(f)
    assert len(depts) == 1, f"depts.json must have exactly 1 dept after migration, got {len(depts)}"
    default_dept = list(depts.values())[0]
    assert default_dept.get("name") == "Основной отдел", (
        f"Default dept name must be 'Основной отдел', got {default_dept.get('name')}"
    )

    # A backup file must have been created before patching (D-07)
    backup_pattern = str(data_dir / "employees_backup_*.json")
    backup_files = glob.glob(backup_pattern)
    assert len(backup_files) >= 1, (
        f"Migration must create a employees_backup_*.json backup file; "
        f"none found matching {backup_pattern}"
    )


# ─── MIG-02: Label integrity warn-only — migration does not abort on mismatch ─

@pytest.mark.xfail(reason="implemented in 02-02: migrate.py not yet built", strict=False)
def test_label_integrity_warn(tmp_data, capsys):
    """MIG-02: When an employee's label integer has no matching face images, migration
    completes successfully (does not raise / does not abort) and surfaces a warning
    (captured stdout contains 'WARN' or a returned warnings list is non-empty).

    This test seeds an employee with label=99 but no face images on disk.
    Per D-06: warn-only, never abort.

    Steps:
    1. Seed one employee with label=99 and no faces directory.
    2. Run migration.
    3. Assert migration completes without raising an exception.
    4. Assert stdout contains 'WARN' OR migration function returns a non-empty warnings list.
    """
    try:
        import migrate
    except ImportError:
        pytest.xfail("migrate.py not yet created — MIG-02 will be green after plan 02-02")

    mismatched_emp_id = "emp-label-mismatch-99"
    seed_employees(tmp_data, {
        mismatched_emp_id: {
            "id": mismatched_emp_id,
            "name": "Сотрудник Без Фото",
            "role": "employee",
            "label": 99,  # No matching face images — triggers label integrity warning
            "face_count": 0,
            "registered_at": "2026-01-01T00:00:00",
            # No org_id, dept_id, schedule — pre-migration state
        }
    })

    data_dir = tmp_data / "data"
    faces_dir = data_dir / "faces"
    # Do NOT create any face images — label 99 has no matching images

    for attr, val in [
        ("DATA_DIR", str(data_dir)),
        ("FACES_DIR", str(faces_dir)),
        ("EMPLOYEES_FILE", str(data_dir / "employees.json")),
        ("ORGS_FILE", str(data_dir / "orgs.json")),
        ("DEPTS_FILE", str(data_dir / "depts.json")),
    ]:
        if hasattr(migrate, attr):
            setattr(migrate, attr, val)

    # Migration must not raise — it is warn-only per D-06
    result = None
    try:
        result = migrate.run_migration()
    except Exception as exc:
        pytest.fail(
            f"migrate.run_migration() must not raise on label mismatch (D-06 warn-only), "
            f"but raised: {type(exc).__name__}: {exc}"
        )

    # Warning must be surfaced — either via stdout or returned warnings list
    captured = capsys.readouterr()
    stdout_has_warn = "WARN" in captured.out.upper()
    result_has_warn = isinstance(result, (list, dict)) and bool(result)

    assert stdout_has_warn or result_has_warn, (
        "Migration must surface a warning for employees with no matching face images. "
        f"Stdout: {captured.out!r}. Return value: {result!r}. "
        "Expected either 'WARN' in stdout or a non-empty warnings list returned."
    )
