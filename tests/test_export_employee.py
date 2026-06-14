"""
Phase 4 Export & Employee Cabinet — Failing / xfail test scaffold.

Covered requirements:
    EXP-01  GET /timesheet/export/xlsx returns 200 with xlsx ZIP magic and T13_ Content-Disposition
    EXP-02  GET /timesheet/export/csv returns 200 with UTF-8 BOM prefix and semicolon delimiter
    EXP-03  Export scope enforcement: dept_admin cannot export outside their own department
    EMP-01  GET /employee renders 200 with "Мой табель" heading
    EMP-02  Employee cabinet shows arrival/departure times as tooltip ("Приход" + "09:05")
    EMP-03  Employee cabinet contains all three stat labels: "Опоздания", "Отсутствия", "Ранний уход"

All tests are @pytest.mark.xfail(strict=False) — they will pass once the implementing
plans land:
    Export routes (EXP-01..03): plan 04-02
    Employee cabinet (EMP-01..03): plan 04-03
"""
import pytest

from tests.conftest import (
    seed_users,
    seed_employees,
    seed_depts,
    seed_orgs,
    seed_attendance,
    BCRYPT_HASH_SUPERADMIN,
)


# ─── EXP-01: Export XLSX — dept admin happy path ─────────────────────────────

def test_export_xlsx_dept_admin(client, tmp_data):
    """EXP-01: dept_admin exports their department's T-13 grid as xlsx.

    Asserts:
    - status 200
    - response bytes start with b"PK" (xlsx ZIP magic)
    - Content-Disposition contains "attachment" and "T13_"
    """
    seed_orgs(tmp_data, {
        "org-A": {
            "id": "org-A",
            "name": "Главная Организация",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        "dept-A": {
            "id": "dept-A",
            "org_id": "org-A",
            "name": "ВОП-1",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_users(tmp_data, {
        "uid-exp01": {
            "id": "uid-exp01",
            "username": "dept_admin_exp01",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "dept_admin",
            "active": True,
            "org_id": "org-A",
            "dept_id": "dept-A",
        }
    })

    client.post("/login", data={"username": "dept_admin_exp01", "password": "superadmin123"}, follow_redirects=True)

    resp = client.get("/timesheet/export/xlsx?dept_id=dept-A&month=2026-06")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert resp.data[:2] == b"PK", "xlsx response must start with PK (ZIP magic)"
    content_disp = resp.headers.get("Content-Disposition", "")
    assert "attachment" in content_disp, f"Content-Disposition must contain 'attachment', got {content_disp!r}"
    assert "T13_" in content_disp, f"Content-Disposition must contain 'T13_', got {content_disp!r}"


# ─── EXP-02: Export CSV — UTF-8 BOM and semicolon delimiter ──────────────────

def test_export_csv_bom_encoding(client, tmp_data):
    """EXP-02: dept_admin exports their department's T-13 grid as CSV with UTF-8 BOM.

    Asserts:
    - status 200
    - response data starts with UTF-8 BOM (b"\\xef\\xbb\\xbf")
    - semicolon delimiter present in response data
    """
    seed_orgs(tmp_data, {
        "org-A": {
            "id": "org-A",
            "name": "Главная Организация",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        "dept-A": {
            "id": "dept-A",
            "org_id": "org-A",
            "name": "ВОП-1",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_users(tmp_data, {
        "uid-exp02": {
            "id": "uid-exp02",
            "username": "dept_admin_exp02",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "dept_admin",
            "active": True,
            "org_id": "org-A",
            "dept_id": "dept-A",
        }
    })

    client.post("/login", data={"username": "dept_admin_exp02", "password": "superadmin123"}, follow_redirects=True)

    resp = client.get("/timesheet/export/csv?dept_id=dept-A&month=2026-06")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert resp.data.startswith(b"\xef\xbb\xbf"), "CSV response must start with UTF-8 BOM (\\xef\\xbb\\xbf)"
    assert b";" in resp.data, "CSV response must contain semicolon delimiter"


# ─── EXP-03: Export scope enforcement ────────────────────────────────────────

def test_export_scope_enforcement(client, tmp_data):
    """EXP-03: dept_admin from dept-A cannot export dept-B employee data.

    Accepts either outcome:
    - 200 with dept-B employee name absent from response data (forced to own dept)
    - 403 (direct rejection)
    """
    seed_orgs(tmp_data, {
        "org-A": {
            "id": "org-A",
            "name": "Главная Организация",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        "dept-A": {
            "id": "dept-A",
            "org_id": "org-A",
            "name": "ВОП-1",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        },
        "dept-B": {
            "id": "dept-B",
            "org_id": "org-A",
            "name": "ВОП-2",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        },
    })
    seed_employees(tmp_data, {
        "emp-b-scope": {
            "id": "emp-b-scope",
            "name": "Сотрудник Б Скоуп",
            "role": "employee",
            "label": 1,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": "org-A",
            "dept_id": "dept-B",
        }
    })
    seed_users(tmp_data, {
        "uid-exp03": {
            "id": "uid-exp03",
            "username": "dept_admin_exp03",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "dept_admin",
            "active": True,
            "org_id": "org-A",
            "dept_id": "dept-A",
        }
    })

    client.post("/login", data={"username": "dept_admin_exp03", "password": "superadmin123"}, follow_redirects=True)

    resp = client.get("/timesheet/export/xlsx?dept_id=dept-B&month=2026-06")
    assert resp.status_code in (200, 403), (
        f"dept_admin requesting cross-dept export must get 200 (own scope) or 403, got {resp.status_code}"
    )
    if resp.status_code == 200:
        assert "Сотрудник Б Скоуп".encode() not in resp.data, (
            "dept-B employee name must NOT appear in dept-A admin's xlsx export"
        )


# ─── EMP-01: Employee cabinet renders ────────────────────────────────────────

@pytest.mark.xfail(reason="implemented in 04-02/04-03", strict=False)
def test_employee_cabinet_renders(client, tmp_data):
    """EMP-01: Employee user can view their own T-13 cabinet at /employee.

    Asserts status 200 and "Мой табель" heading present in response.
    """
    seed_orgs(tmp_data, {
        "org-A": {
            "id": "org-A",
            "name": "Главная Организация",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        "dept-A": {
            "id": "dept-A",
            "org_id": "org-A",
            "name": "ВОП-1",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_employees(tmp_data, {
        "emp-1": {
            "id": "emp-1",
            "name": "Тестовый Сотрудник",
            "role": "employee",
            "label": 1,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": "org-A",
            "dept_id": "dept-A",
        }
    })
    seed_users(tmp_data, {
        "uid-emp01": {
            "id": "uid-emp01",
            "username": "employee_emp01",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "employee",
            "active": True,
            "org_id": "org-A",
            "dept_id": "dept-A",
            "emp_id": "emp-1",
        }
    })

    client.post("/login", data={"username": "employee_emp01", "password": "superadmin123"}, follow_redirects=True)

    resp = client.get("/employee?month=2026-06")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "Мой табель".encode("utf-8") in resp.data, (
        "Response must contain 'Мой табель' heading"
    )


# ─── EMP-02: Employee cabinet shows arrival/departure tooltips ────────────────

@pytest.mark.xfail(reason="implemented in 04-02/04-03", strict=False)
def test_employee_tooltip_times(client, tmp_data):
    """EMP-02: Employee cabinet shows check-in/check-out times as tooltip text.

    Seeds one AttendanceRecord for emp-1 on 2026-06-02 with check_in 09:05:00.
    Asserts "Приход" and "09:05" appear in response data (tooltip title text).
    """
    seed_orgs(tmp_data, {
        "org-A": {
            "id": "org-A",
            "name": "Главная Организация",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        "dept-A": {
            "id": "dept-A",
            "org_id": "org-A",
            "name": "ВОП-1",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_employees(tmp_data, {
        "emp-1": {
            "id": "emp-1",
            "name": "Тестовый Сотрудник",
            "role": "employee",
            "label": 1,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": "org-A",
            "dept_id": "dept-A",
        }
    })
    seed_users(tmp_data, {
        "uid-emp02": {
            "id": "uid-emp02",
            "username": "employee_emp02",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "employee",
            "active": True,
            "org_id": "org-A",
            "dept_id": "dept-A",
            "emp_id": "emp-1",
        }
    })
    seed_attendance(tmp_data, [
        {
            "id": 1,
            "emp_id": "emp-1",
            "date": "2026-06-02",
            "check_in_time": "09:05:00",
            "check_out_time": "18:00:00",
        }
    ])

    client.post("/login", data={"username": "employee_emp02", "password": "superadmin123"}, follow_redirects=True)

    resp = client.get("/employee?month=2026-06")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "Приход".encode("utf-8") in resp.data, (
        "Response must contain 'Приход' (arrival tooltip label)"
    )
    assert b"09:05" in resp.data, (
        "Response must contain '09:05' (check-in time from AttendanceRecord)"
    )


# ─── EMP-03: Employee cabinet stat labels ────────────────────────────────────

@pytest.mark.xfail(reason="implemented in 04-02/04-03", strict=False)
def test_employee_stats_counts(client, tmp_data):
    """EMP-03: Employee cabinet renders all three stat card labels.

    Asserts "Опоздания", "Отсутствия", and "Ранний уход" appear in response data.
    """
    seed_orgs(tmp_data, {
        "org-A": {
            "id": "org-A",
            "name": "Главная Организация",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        "dept-A": {
            "id": "dept-A",
            "org_id": "org-A",
            "name": "ВОП-1",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_employees(tmp_data, {
        "emp-1": {
            "id": "emp-1",
            "name": "Тестовый Сотрудник",
            "role": "employee",
            "label": 1,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": "org-A",
            "dept_id": "dept-A",
        }
    })
    seed_users(tmp_data, {
        "uid-emp03": {
            "id": "uid-emp03",
            "username": "employee_emp03",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "employee",
            "active": True,
            "org_id": "org-A",
            "dept_id": "dept-A",
            "emp_id": "emp-1",
        }
    })

    client.post("/login", data={"username": "employee_emp03", "password": "superadmin123"}, follow_redirects=True)

    resp = client.get("/employee?month=2026-06")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "Опоздания".encode("utf-8") in resp.data, (
        "Response must contain 'Опоздания' stat label"
    )
    assert "Отсутствия".encode("utf-8") in resp.data, (
        "Response must contain 'Отсутствия' stat label"
    )
    assert "Ранний уход".encode("utf-8") in resp.data, (
        "Response must contain 'Ранний уход' stat label"
    )
