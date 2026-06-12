"""
Phase 3 T-13 Timesheet Grid — Failing / xfail test scaffold.

Covered requirements:
    T13-01  /timesheet route renders 200 with grid data
    T13-02  Full symbol set: Я, О, У, В, П, НН, Б, К (+ ОУ composite)
    T13-03  Auto-derived symbols from attendance; В on weekends/KZ holidays
    T13-04  Late arrival (first check-in > 15 min after schedule start) → О
    T13-05  Early departure (last check-out > 15 min before schedule end) → У; both → ОУ
    T13-07  Monthly totals row: days_worked, hours_worked, absences, late, vac_sick
    T13-08  KZ public holidays 2024/2025/2026 hard-coded; is_holiday_year_missing()
    DASH-04 org_admin per-dept monthly summary with attendance rate %
    D-05    dept_admin 403 on override for employee outside their dept
    D-08    dept_admin scope isolation on /timesheet (param ignored; forced to session)
    V5      Override API symbol validation — 422 for non-MANUAL_SYMBOLS value

All tests are @pytest.mark.xfail(strict=False) — they will pass once the implementing
plans land:
    Unit tests (T13-02 to T13-08): plan 03-02
    Integration tests (T13-01, D-05, D-08, DASH-04, V5): plan 03-03 / 03-04
"""
import json
import pytest
from datetime import date

from tests.conftest import (
    seed_users,
    seed_employees,
    seed_depts,
    seed_orgs,
    BCRYPT_HASH_SUPERADMIN,
)


# ─── T13-02: Symbol engine — full symbol set ──────────────────────────────────

@pytest.mark.xfail(reason="implemented in 03-02: compute_symbol not yet in app.py", strict=False)
def test_compute_symbol_all_cases():
    """T13-02: compute_symbol returns correct symbol for every case in the full symbol set.

    Tests: Я (on-time), О (late), У (early), ОУ (both), В (weekend/holiday),
           НН (absent work day), manual override wins, Б and К pass through from overrides.
    """
    import app as _app
    assert hasattr(_app, "compute_symbol"), "compute_symbol must be importable from app"
    compute_symbol = _app.compute_symbol

    # Common schedule: Mon–Fri 09:00–18:00
    schedule = {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}
    # A known Monday (work day, no holiday)
    monday = date(2025, 6, 2)  # 2025-06-02 is a Monday
    holidays_set = set()

    # Я: on-time check-in, no check-out (or on-time check-out)
    attendance_ya = {"2025-06-02": {"emp-1": {"check_in": "09:00:00", "check_out": "18:00:00"}}}
    sym = compute_symbol(monday, "emp-1", attendance_ya, {}, schedule, holidays_set)
    assert sym == "Я", f"On-time check-in must return Я, got {sym!r}"

    # НН: work day, no record at all
    attendance_empty = {}
    sym_nn = compute_symbol(monday, "emp-1", attendance_empty, {}, schedule, holidays_set)
    assert sym_nn == "НН", f"Missing record on work day must return НН, got {sym_nn!r}"

    # В: Saturday (isoweekday 6)
    saturday = date(2025, 6, 7)  # 2025-06-07 is a Saturday
    sym_v = compute_symbol(saturday, "emp-1", attendance_empty, {}, schedule, holidays_set)
    assert sym_v == "В", f"Saturday must return В, got {sym_v!r}"

    # О: late check-in (> 15 min after 09:00 → after 09:15:00)
    attendance_late = {"2025-06-02": {"emp-1": {"check_in": "09:16:00", "check_out": "18:00:00"}}}
    sym_o = compute_symbol(monday, "emp-1", attendance_late, {}, schedule, holidays_set)
    assert sym_o == "О", f"Late check-in 09:16 must return О, got {sym_o!r}"

    # У: early check-out (> 15 min before 18:00 → before 17:45:00)
    attendance_early = {"2025-06-02": {"emp-1": {"check_in": "09:00:00", "check_out": "17:44:00"}}}
    sym_u = compute_symbol(monday, "emp-1", attendance_early, {}, schedule, holidays_set)
    assert sym_u == "У", f"Early checkout 17:44 must return У, got {sym_u!r}"

    # ОУ: both late and early
    attendance_ou = {"2025-06-02": {"emp-1": {"check_in": "09:16:00", "check_out": "17:44:00"}}}
    sym_ou = compute_symbol(monday, "emp-1", attendance_ou, {}, schedule, holidays_set)
    assert sym_ou == "ОУ", f"Late + early must return ОУ, got {sym_ou!r}"

    # Override wins over auto-derivation: even though attendance says Я, override is Б
    overrides_b = {"emp-1": {"2025-06-02": "Б"}}
    sym_override = compute_symbol(monday, "emp-1", attendance_ya, overrides_b, schedule, holidays_set)
    assert sym_override == "Б", f"Override Б must win over auto Я, got {sym_override!r}"

    # Override К
    overrides_k = {"emp-1": {"2025-06-02": "К"}}
    sym_k = compute_symbol(monday, "emp-1", attendance_ya, overrides_k, schedule, holidays_set)
    assert sym_k == "К", f"Override К must win over auto Я, got {sym_k!r}"


# ─── T13-03: Auto-derived symbols from attendance ────────────────────────────

@pytest.mark.xfail(reason="implemented in 03-02: compute_symbol not yet in app.py", strict=False)
def test_symbol_auto_derivation():
    """T13-03: Я for on-time check-in; НН for absent work day; В for Saturday.

    Verifies the three most common auto-derivation paths without edge cases.
    """
    import app as _app
    assert hasattr(_app, "compute_symbol"), "compute_symbol must be importable from app"
    compute_symbol = _app.compute_symbol

    schedule = {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}
    holidays_set = set()

    # Я: on-time Monday
    monday = date(2025, 6, 2)
    attendance = {"2025-06-02": {"emp-x": {"check_in": "08:55:00", "check_out": "18:10:00"}}}
    sym = compute_symbol(monday, "emp-x", attendance, {}, schedule, holidays_set)
    assert sym == "Я", f"On-time check-in must produce Я, got {sym!r}"

    # НН: past work day Monday with no record
    attendance_empty = {}
    sym_nn = compute_symbol(monday, "emp-x", attendance_empty, {}, schedule, holidays_set)
    assert sym_nn == "НН", f"Missing record on work day must produce НН, got {sym_nn!r}"

    # В: Saturday (isoweekday 6), work_days = [1..5]
    saturday = date(2025, 6, 7)
    sym_v = compute_symbol(saturday, "emp-x", attendance_empty, {}, schedule, holidays_set)
    assert sym_v == "В", f"Saturday with work_days [1..5] must produce В, got {sym_v!r}"


# ─── T13-04: Late arrival boundary ───────────────────────────────────────────

@pytest.mark.xfail(reason="implemented in 03-02: compute_symbol not yet in app.py", strict=False)
def test_symbol_late():
    """T13-04: First check-in strictly > 15 min after schedule start → О.
    Exactly at +15 min is still Я (boundary is exclusive: > not >=).

    Schedule start 09:00 → late threshold 09:15:00 (exclusive).
    09:16:00 → О
    09:15:00 → Я (NOT late — must be strictly after 09:15:00)
    """
    import app as _app
    assert hasattr(_app, "compute_symbol"), "compute_symbol must be importable from app"
    compute_symbol = _app.compute_symbol

    schedule = {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}
    holidays_set = set()
    monday = date(2025, 6, 2)

    # 09:16:00 — strictly after threshold → О
    attendance_late = {"2025-06-02": {"emp-late": {"check_in": "09:16:00", "check_out": "18:00:00"}}}
    sym_late = compute_symbol(monday, "emp-late", attendance_late, {}, schedule, holidays_set)
    assert sym_late == "О", f"09:16:00 check-in must return О, got {sym_late!r}"

    # 09:15:00 — exactly at threshold boundary → Я (boundary is exclusive)
    attendance_boundary = {"2025-06-02": {"emp-late": {"check_in": "09:15:00", "check_out": "18:00:00"}}}
    sym_boundary = compute_symbol(monday, "emp-late", attendance_boundary, {}, schedule, holidays_set)
    assert sym_boundary == "Я", (
        f"09:15:00 check-in must return Я (boundary exclusive: strictly >15 min), got {sym_boundary!r}"
    )


# ─── T13-05: Early departure + composite ОУ ──────────────────────────────────

@pytest.mark.xfail(reason="implemented in 03-02: compute_symbol not yet in app.py", strict=False)
def test_symbol_early_and_combined():
    """T13-05: Early departure → У; late + early → ОУ.

    Schedule end 18:00 → early threshold 17:45:00 (exclusive; check_out < 17:45:00).
    17:44:00 → У
    Late check-in (09:16:00) + early check-out (17:44:00) → ОУ
    """
    import app as _app
    assert hasattr(_app, "compute_symbol"), "compute_symbol must be importable from app"
    compute_symbol = _app.compute_symbol

    schedule = {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}
    holidays_set = set()
    monday = date(2025, 6, 2)

    # 17:44:00 check-out — strictly before 17:45:00 threshold → У
    attendance_early = {"2025-06-02": {"emp-e": {"check_in": "09:00:00", "check_out": "17:44:00"}}}
    sym_u = compute_symbol(monday, "emp-e", attendance_early, {}, schedule, holidays_set)
    assert sym_u == "У", f"17:44:00 check-out must return У, got {sym_u!r}"

    # Late check-in + early check-out → ОУ
    attendance_ou = {"2025-06-02": {"emp-e": {"check_in": "09:16:00", "check_out": "17:44:00"}}}
    sym_ou = compute_symbol(monday, "emp-e", attendance_ou, {}, schedule, holidays_set)
    assert sym_ou == "ОУ", f"Late + early must return ОУ, got {sym_ou!r}"


# ─── T13-07: Totals row computation ──────────────────────────────────────────

@pytest.mark.xfail(reason="implemented in 03-02: compute_employee_totals not yet in app.py", strict=False)
def test_totals_row():
    """T13-07: compute_employee_totals aggregates symbol list into the 5 totals columns.

    Days worked = Я + О + У + ОУ
    Late = О + ОУ
    Absences = П + НН
    Vac/sick = Б + К
    Hours worked = days_worked × daily_hours (schedule 09:00–18:00 = 9h)
    """
    import app as _app
    assert hasattr(_app, "compute_employee_totals"), (
        "compute_employee_totals must be importable from app"
    )
    compute_employee_totals = _app.compute_employee_totals

    schedule = {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}
    # 9h workday: 18*60 - 9*60 = 9h

    symbols = ["Я", "Я", "О", "У", "ОУ", "НН", "П", "Б", "К", "В", "В"]
    totals = compute_employee_totals(symbols, schedule)

    # Days worked: Я×2 + О×1 + У×1 + ОУ×1 = 5
    assert totals["days_worked"] == 5, (
        f"days_worked must be 5 (Я×2+О+У+ОУ), got {totals['days_worked']}"
    )

    # Hours worked: 5 × 9 = 45.0
    assert totals["hours_worked"] == 45.0, (
        f"hours_worked must be 45.0 (5 days × 9h), got {totals['hours_worked']}"
    )

    # Absences: НН×1 + П×1 = 2
    assert totals["absences"] == 2, (
        f"absences must be 2 (НН+П), got {totals['absences']}"
    )

    # Late: О×1 + ОУ×1 = 2
    assert totals["late"] == 2, (
        f"late must be 2 (О+ОУ), got {totals['late']}"
    )

    # Vac/sick: Б×1 + К×1 = 2
    assert totals["vac_sick"] == 2, (
        f"vac_sick must be 2 (Б+К), got {totals['vac_sick']}"
    )


# ─── T13-08: KZ public holidays ──────────────────────────────────────────────

@pytest.mark.xfail(reason="implemented in 03-02: KZ_HOLIDAYS/get_holidays_set not yet in app.py", strict=False)
def test_kz_holidays():
    """T13-08: KZ public holidays 2024/2025/2026 are hard-coded; missing year detected.

    2025-01-01 (New Year) must be in the 2025 holidays set.
    is_holiday_year_missing(2099) must return True.
    compute_symbol returns В for a holiday date on a weekday (work day).
    """
    import app as _app
    assert hasattr(_app, "get_holidays_set"), "get_holidays_set must be importable from app"
    assert hasattr(_app, "is_holiday_year_missing"), "is_holiday_year_missing must be importable from app"
    assert hasattr(_app, "compute_symbol"), "compute_symbol must be importable from app"

    get_holidays_set = _app.get_holidays_set
    is_holiday_year_missing = _app.is_holiday_year_missing
    compute_symbol = _app.compute_symbol

    # 2025-01-01 must be in 2025 holiday set
    holidays_2025 = get_holidays_set(2025)
    assert "2025-01-01" in holidays_2025, (
        "2025-01-01 (KZ New Year) must be in get_holidays_set(2025)"
    )

    # Unknown year must be flagged as missing
    assert is_holiday_year_missing(2099) is True, (
        "is_holiday_year_missing(2099) must return True (no holiday data for 2099)"
    )

    # compute_symbol returns В for a KZ holiday date on a workday
    # 2025-01-01 is a Wednesday (isoweekday 3) — a normal work day if not a holiday
    schedule = {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]}
    holiday_wednesday = date(2025, 1, 1)
    # Provide attendance record to show the holiday overrides auto-derivation
    attendance = {"2025-01-01": {"emp-h": {"check_in": "09:00:00", "check_out": "18:00:00"}}}
    sym = compute_symbol(holiday_wednesday, "emp-h", attendance, {}, schedule, holidays_2025)
    assert sym == "В", (
        f"compute_symbol must return В for KZ holiday 2025-01-01 even with check-in record, got {sym!r}"
    )


# ─── T13-01: /timesheet route renders ────────────────────────────────────────

@pytest.mark.xfail(reason="implemented in 03-03: /timesheet route not yet built", strict=False)
def test_timesheet_renders(client, tmp_data):
    """T13-01: GET /timesheet returns 200 and contains employee name + 'Итого'.

    Seeds superadmin user, one dept, one employee (with schedule + dept_id),
    injects session, then verifies the route renders the grid.
    """
    superadmin_id = "uid-sa-timesheet-render"
    emp_id = "emp-ts-render"

    seed_orgs(tmp_data, {
        "org-ts": {
            "id": "org-ts",
            "name": "Тестовая Организация",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        "dept-ts": {
            "id": "dept-ts",
            "org_id": "org-ts",
            "name": "Тестовый Отдел",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_employees(tmp_data, {
        emp_id: {
            "id": emp_id,
            "name": "Иванов Иван",
            "role": "employee",
            "label": 1,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": "org-ts",
            "dept_id": "dept-ts",
            "schedule": {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]},
        }
    })
    seed_users(tmp_data, {
        superadmin_id: {
            "id": superadmin_id,
            "username": "superadmin",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "superadmin",
            "active": True,
            "org_id": None,
            "dept_id": None,
        }
    })

    with client.session_transaction() as sess:
        sess["user_id"] = superadmin_id
        sess["role"] = "superadmin"
        sess["org_id"] = None
        sess["dept_id"] = None

    rv = client.get("/timesheet?dept_id=dept-ts&month=2025-06")
    assert rv.status_code == 200, (
        f"GET /timesheet must return 200, got {rv.status_code}"
    )
    body = rv.get_data(as_text=True)
    assert "Иванов Иван" in body, "Response must contain employee name 'Иванов Иван'"
    assert "Итого" in body, "Response must contain 'Итого' (totals row)"


# ─── D-05: dept_admin 403 on override for out-of-scope employee ──────────────

@pytest.mark.xfail(reason="implemented in 03-03: /api/timesheet/override not yet built", strict=False)
def test_override_scope_403(client, tmp_data):
    """D-05: dept_admin from dept-A gets 403 when POSTing override for employee in dept-B.

    Horizontal privilege escalation threat: dept_admin must not be able to override
    cells for employees outside their own department.
    """
    dept_admin_id = "uid-da-scope-403"
    emp_b_id = "emp-dept-b-override"

    seed_orgs(tmp_data, {
        "org-scope": {
            "id": "org-scope",
            "name": "Организация Скоуп",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        "dept-A": {
            "id": "dept-A",
            "org_id": "org-scope",
            "name": "Отдел А",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        },
        "dept-B": {
            "id": "dept-B",
            "org_id": "org-scope",
            "name": "Отдел Б",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        },
    })
    seed_employees(tmp_data, {
        emp_b_id: {
            "id": emp_b_id,
            "name": "Сотрудник Б",
            "role": "employee",
            "label": 1,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": "org-scope",
            "dept_id": "dept-B",
            "schedule": {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]},
        }
    })
    seed_users(tmp_data, {
        dept_admin_id: {
            "id": dept_admin_id,
            "username": "dept_admin_a",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "dept_admin",
            "active": True,
            "org_id": "org-scope",
            "dept_id": "dept-A",
        }
    })

    # Login as dept_admin for dept-A
    with client.session_transaction() as sess:
        sess["user_id"] = dept_admin_id
        sess["role"] = "dept_admin"
        sess["org_id"] = "org-scope"
        sess["dept_id"] = "dept-A"

    # Try to override an employee in dept-B → must be 403
    rv = client.post(
        "/api/timesheet/override",
        json={"emp_id": emp_b_id, "date": "2025-06-02", "symbol": "Б"},
        content_type="application/json",
    )
    assert rv.status_code == 403, (
        f"dept_admin from dept-A overriding dept-B employee must return 403, got {rv.status_code}"
    )


# ─── D-08: dept_admin scope isolation on /timesheet ──────────────────────────

@pytest.mark.xfail(reason="implemented in 03-03: /timesheet scope enforcement not yet built", strict=False)
def test_timesheet_scope_isolation(client, tmp_data):
    """D-08: dept_admin's dept_id param is ignored — grid always uses session dept_id.

    When a dept_admin requests ?dept_id=dept-B but their session dept_id is dept-A,
    the server must enforce session scope: either render dept-A data (ignoring param)
    or return 403. dept-B data must NOT appear in the response.
    """
    dept_admin_id = "uid-da-isolation"
    emp_a_id = "emp-dept-a-isolation"
    emp_b_id = "emp-dept-b-isolation"

    seed_orgs(tmp_data, {
        "org-iso": {
            "id": "org-iso",
            "name": "Организация ИСО",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        "dept-A": {
            "id": "dept-A",
            "org_id": "org-iso",
            "name": "Отдел А",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        },
        "dept-B": {
            "id": "dept-B",
            "org_id": "org-iso",
            "name": "Отдел Б",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        },
    })
    seed_employees(tmp_data, {
        emp_a_id: {
            "id": emp_a_id,
            "name": "Сотрудник А Изоляция",
            "role": "employee",
            "label": 1,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": "org-iso",
            "dept_id": "dept-A",
            "schedule": {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]},
        },
        emp_b_id: {
            "id": emp_b_id,
            "name": "Сотрудник Б Изоляция",
            "role": "employee",
            "label": 2,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": "org-iso",
            "dept_id": "dept-B",
            "schedule": {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]},
        },
    })
    seed_users(tmp_data, {
        dept_admin_id: {
            "id": dept_admin_id,
            "username": "dept_admin_a_iso",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "dept_admin",
            "active": True,
            "org_id": "org-iso",
            "dept_id": "dept-A",
        }
    })

    # Session belongs to dept-A; request asks for dept-B
    with client.session_transaction() as sess:
        sess["user_id"] = dept_admin_id
        sess["role"] = "dept_admin"
        sess["org_id"] = "org-iso"
        sess["dept_id"] = "dept-A"

    rv = client.get("/timesheet?dept_id=dept-B&month=2025-06")

    # Server must either render dept-A scope (200 without dept-B data) or return 403
    assert rv.status_code in (200, 403), (
        f"dept_admin requesting cross-dept must get 200 (own scope) or 403, got {rv.status_code}"
    )

    if rv.status_code == 200:
        body = rv.get_data(as_text=True)
        assert "Сотрудник Б Изоляция" not in body, (
            "dept-B employee name must NOT appear in dept-A admin's timesheet response"
        )


# ─── DASH-04: Org_admin per-dept monthly summary ─────────────────────────────

@pytest.mark.xfail(reason="implemented in 03-04: DASH-04 section not yet in org_admin route", strict=False)
def test_dash04_summary(client, tmp_data):
    """DASH-04: GET /org_admin?summary_month=2025-06 returns 200 with 'Сводка по отделам'.

    Seeds org_admin + 2 depts + employees with attendance; verifies summary section
    renders with attendance-rate value (days-with-Я / work-days × 100).
    """
    org_admin_id = "uid-oa-dash04"
    emp_id = "emp-dash04"

    seed_orgs(tmp_data, {
        "org-dash04": {
            "id": "org-dash04",
            "name": "Организация DASH04",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        "dept-dash-1": {
            "id": "dept-dash-1",
            "org_id": "org-dash04",
            "name": "Отдел Один",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        },
        "dept-dash-2": {
            "id": "dept-dash-2",
            "org_id": "org-dash04",
            "name": "Отдел Два",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        },
    })
    seed_employees(tmp_data, {
        emp_id: {
            "id": emp_id,
            "name": "Сотрудник DASH04",
            "role": "employee",
            "label": 1,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": "org-dash04",
            "dept_id": "dept-dash-1",
            "schedule": {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]},
        }
    })
    # Seed attendance: check-in on 2025-06-02 (Monday)
    attendance_path = tmp_data / "data" / "attendance.json"
    attendance_path.write_text(
        json.dumps({
            "2025-06-02": {emp_id: {"check_in": "09:00:00", "check_out": "18:00:00"}}
        }, ensure_ascii=False),
        encoding="utf-8"
    )
    seed_users(tmp_data, {
        org_admin_id: {
            "id": org_admin_id,
            "username": "org_admin_dash04",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "org_admin",
            "active": True,
            "org_id": "org-dash04",
            "dept_id": None,
        }
    })

    with client.session_transaction() as sess:
        sess["user_id"] = org_admin_id
        sess["role"] = "org_admin"
        sess["org_id"] = "org-dash04"
        sess["dept_id"] = None

    rv = client.get("/org_admin?summary_month=2025-06")
    assert rv.status_code == 200, (
        f"GET /org_admin?summary_month=2025-06 must return 200, got {rv.status_code}"
    )
    body = rv.get_data(as_text=True)
    assert "Сводка по отделам" in body, (
        "Response must contain 'Сводка по отделам' section header (DASH-04)"
    )
    # Attendance rate value must appear in the response (any percentage value)
    # The exact value depends on the month's work day count; we just verify a % appears
    assert "%" in body, "Response must contain an attendance rate value with '%' (DASH-04)"


# ─── V5: Override API symbol validation (422 for non-MANUAL_SYMBOLS) ─────────

@pytest.mark.xfail(reason="implemented in 03-03: /api/timesheet/override validation not yet built", strict=False)
def test_override_invalid_symbol_422(client, tmp_data):
    """V5 input validation: POST /api/timesheet/override with symbol='Я' (not in MANUAL_SYMBOLS)
    must return 422.

    MANUAL_SYMBOLS = {'Б', 'К', 'П'} — auto-derived symbols must not be settable as overrides.
    Sending 'Я' (valid auto symbol but not a manual symbol) tests the whitelist guard.
    """
    dept_admin_id = "uid-da-sym-422"
    emp_id = "emp-sym-422"

    seed_orgs(tmp_data, {
        "org-sym": {
            "id": "org-sym",
            "name": "Организация СИМ",
            "description": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_depts(tmp_data, {
        "dept-sym": {
            "id": "dept-sym",
            "org_id": "org-sym",
            "name": "Отдел СИМ",
            "head_name": "",
            "created_at": "2026-01-01T00:00:00",
        }
    })
    seed_employees(tmp_data, {
        emp_id: {
            "id": emp_id,
            "name": "Сотрудник СИМ",
            "role": "employee",
            "label": 1,
            "face_count": 5,
            "registered_at": "2026-01-01T00:00:00",
            "org_id": "org-sym",
            "dept_id": "dept-sym",
            "schedule": {"start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5]},
        }
    })
    seed_users(tmp_data, {
        dept_admin_id: {
            "id": dept_admin_id,
            "username": "dept_admin_sym",
            "password_hash": BCRYPT_HASH_SUPERADMIN,
            "role": "dept_admin",
            "active": True,
            "org_id": "org-sym",
            "dept_id": "dept-sym",
        }
    })

    with client.session_transaction() as sess:
        sess["user_id"] = dept_admin_id
        sess["role"] = "dept_admin"
        sess["org_id"] = "org-sym"
        sess["dept_id"] = "dept-sym"

    # Symbol "Я" is auto-derived, NOT in MANUAL_SYMBOLS → must return 422
    rv = client.post(
        "/api/timesheet/override",
        json={"emp_id": emp_id, "date": "2025-06-02", "symbol": "Я"},
        content_type="application/json",
    )
    assert rv.status_code == 422, (
        f"Override with symbol 'Я' (not in MANUAL_SYMBOLS) must return 422, got {rv.status_code}"
    )
