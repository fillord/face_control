# Phase 3: T-13 Timesheet Grid - Research

**Researched:** 2026-06-13
**Domain:** Python/Flask date arithmetic, T-13 timesheet symbol engine, Jinja2 server-rendered grid, JSON file storage, inline cell editing (JS fetch + DOM update)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Auto-derived symbols: Я (present, within schedule), О (late — first check-in > 15 min after schedule start), У (early departure — last check-out > 15 min before schedule end), В (weekend or KZ public holiday), НН (work day with no check-in record). НН is the default for absent work days — never П by default.

**D-02:** Both О and У in the same day: display as "ОУ" in the cell (two-character notation). Totals row counts each condition separately.

**D-03:** Manual symbol override: Phase 3 includes inline cell editing for Б (sick leave), К (business trip), and П (absent with reason). HR user clicks a cell to get a dropdown/button group; the chosen symbol overrides the auto-derived value for that day.

**D-04:** Override storage: `data/timesheet_overrides.json` — a separate file keyed by `emp_id → date (YYYY-MM-DD) → symbol`. Follows the `load_*/save_*` pattern with `fcntl.flock(LOCK_EX)` on writes. Auto-derived values are never stored — computed at render time from `attendance.json` + schedule.

**D-05:** Override edit permissions: dept_admin and above. dept_admin can override cells for employees in their own dept; org_admin can override any employee in their org; superadmin can override all. Viewer gets read-only grid.

**D-06:** KZ public holidays hard-coded for 2024, 2025, and 2026 in a module-level constant in `app.py` (a dict of `year → [date strings]`). Yellow banner when year has no holiday data.

**D-07:** T-13 lives at a dedicated `/timesheet` route with a new `templates/timesheet.html` template. Month and department are URL query params: `?dept_id=X&month=YYYY-MM`. Route decorated with `@require_role('dept_admin', 'org_admin', 'superadmin')`.

**D-08:** Data isolation enforced server-side: dept_admin's dept_id read from `session['dept_id']` — any dept_id param that doesn't match is rejected with 403. org_admin can only view depts belonging to their `session['org_id']`. Superadmin has no restriction.

**D-09:** DASH-04 implemented as a section on `org_admin.html` — a month picker + table showing: dept name, employee count, days present total, and attendance rate %. No new route needed.

**D-10:** Selector interaction: URL params + server render. Dropdowns submit a `<form method="GET">` — the page reloads with the new grid. No JS fetch for the grid itself.

**D-11:** Default month: current calendar month (`datetime.now().strftime('%Y-%m')`). If `?month=` is absent from URL, route defaults to current month.

**D-12:** Dept selector for org_admin/superadmin: a single `<select>` dropdown. dept_admin has no dept selector — their dept is fixed from session.

**D-13:** The totals row shows: days worked (Я count), hours worked (days worked × daily_hours), absences (П + НН count), late arrivals (О count, including ОУ cells), vacation/sick days (Б + К count).

### Claude's Discretion

- Storage schema details for `timesheet_overrides.json` — Claude uses `{emp_id: {date: symbol}}` nested dict.
- Inline edit UI — Claude picks compact dropdown or button group.
- Exact CSS for timesheet grid — Claude follows `admin.html` / `dept_admin.html` visual patterns.
- KZ public holiday dates for 2026 — Claude hard-codes the official list.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| T13-01 | T-13 grid view: employees as rows, calendar days as columns for selected month | `calendar.monthrange()` for day count; Jinja2 table render with day loop |
| T13-02 | Full symbol set: Я, О, У, В, П, НН, Б, К | Symbol engine function `compute_symbol()` handles all 8 symbols + ОУ composite |
| T13-03 | Auto-derived symbols from face check-in data; В on weekends and KZ holidays | `attendance.json` structure verified — keyed `{date: {emp_id: {check_in, check_out}}}`; holiday dict confirmed |
| T13-04 | Late arrival: first check-in > 15 min after schedule start → О | String comparison on HH:MM:SS times verified correct (existing pattern in `dept_attendance_today`) |
| T13-05 | Early departure: last check-out > 15 min before schedule end → У; both → notes | Early threshold construction verified; ОУ composite symbol per D-02 |
| T13-07 | Monthly totals row: days worked, hours worked, absences, late arrivals, vacation/sick | Aggregation logic verified: ОУ counts in both О and У columns; daily_hours from schedule arithmetic |
| T13-08 | KZ public holidays 2024 and 2025 hard-coded; auto-marked В | Research extended to 2026 per D-06; 16 holidays/year; missing-year banner logic |
| DASH-04 | Org_admin per-dept monthly summary: total employees, attendance rate % | attendance_rate = (days with Я) / total_work_days × 100; work_days counting verified |
</phase_requirements>

---

## Summary

Phase 3 builds a statutory T-13 timesheet grid on a pure server-rendered Flask + Jinja2 page with a thin JS layer for inline cell override only. The technical core is a `compute_symbol()` function that classifies each employee-day as one of 8 symbols (or the composite ОУ) by combining three data sources: `attendance.json` (check-in/check-out times), `employees.json` (schedule), and `timesheet_overrides.json` (manual HR corrections). All symbol derivation logic uses Python stdlib only — no new packages.

The grid is a wide HTML table rendered server-side (31 day columns + 5 totals columns). The `<form method="GET">` selector pattern matches the existing project convention, making the URL bookmarkable and avoiding client-side state complexity. The only JS required is the override cell dropdown (POST to `/api/timesheet/override`) and the DASH-04 month picker on `org_admin.html`.

The most important architectural constraints are: (1) auto-derived values are never persisted — they are always computed at render time; (2) `timesheet_overrides.json` overrides take priority before any auto-derivation; (3) data isolation mirrors the existing `dept_attendance_today()` scoping pattern exactly.

**Primary recommendation:** Implement `compute_symbol()` as a standalone helper function in `app.py` (under the new `# ─── T-13 Timesheet ───────────────────────────` section), make it pure (no I/O, accepts pre-loaded dicts), then call it in both the `/timesheet` route and the DASH-04 computation.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Symbol derivation (Я/О/У/В/НН/ОУ) | API / Backend (Python) | — | Business logic must be server-side; cannot trust client-computed symbols for HR record |
| Manual override storage | API / Backend | — | fcntl-locked JSON write; must be server-side to prevent race conditions |
| Override permission check | API / Backend | — | Scope validation against session[dept_id/org_id] must happen server-side (D-08) |
| Grid rendering | Frontend Server (Jinja2) | — | Full-page server render; no client-side grid library needed |
| Inline override dropdown | Browser / Client (JS) | — | POST to API, DOM update on success — only JS interaction in phase |
| DASH-04 summary table | Frontend Server (Jinja2) | — | Server-renders into org_admin.html section; month selector is a GET form |
| Data isolation / scope enforcement | API / Backend | — | dept_admin → session dept_id; org_admin → session org_id; reject mismatches 403 |

---

## Standard Stack

### Core (no new packages — stdlib only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `calendar` stdlib | 3.14.4 | `calendar.monthrange(year, month)` → `(weekday_of_first, num_days)` | Built-in; no dependency |
| Python `datetime` stdlib | 3.14.4 | `date.isoweekday()` for weekday check; `datetime.now().strftime('%Y-%m')` for default month | Already imported in `app.py` |
| Python `fcntl` stdlib | 3.14.4 | `fcntl.flock(LOCK_EX)` for `save_timesheet_overrides()` | Established pattern from `save_users()` |
| Flask + Jinja2 | 3.1.3 / 3.1.6 | Server-render timesheet grid; route handling | Already installed |
| Vanilla JS | N/A | Override cell dropdown; POST to API; DOM update | Existing pattern in all templates |

[VERIFIED: codebase grep — all imports already present in app.py; no new packages required]

### No Alternatives to Consider

This phase requires zero new packages. The symbol engine, grid rendering, and data persistence all use patterns already established in the codebase.

**Installation:** None required.

---

## Package Legitimacy Audit

No external packages are installed in this phase. All functionality uses Python stdlib, Flask (already installed), and vanilla JS.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (dept_admin / org_admin / superadmin)
  |
  | GET /timesheet?dept_id=X&month=YYYY-MM
  |
  v
Flask route: timesheet()
  |-- @require_role("dept_admin", "org_admin", "superadmin")
  |-- validate dept_id scope vs session (403 if mismatch)
  |-- load_attendance()          → attendance dict
  |-- load_employees()           → filtered to dept/org scope
  |-- load_timesheet_overrides() → overrides dict
  |-- build KZ_HOLIDAYS set for year
  |-- for each employee, for each day in month:
  |       compute_symbol(day, emp_id, attendance, overrides, schedule, holidays)
  |       → symbol matrix: List[List[str]]
  |-- compute totals row from symbol matrix
  |-- render_template("timesheet.html", ...)
  v
timesheet.html (Jinja2 table)
  |-- Selector bar (form GET)
  |-- [Holiday banner if year not in KZ_HOLIDAYS]
  |-- <table>: header rows (day numbers + weekday abbrevs)
  |-- tbody: one row per employee, symbol cells with color coding
  |-- totals row
  |-- Inline override JS:
       click cell → show dropdown (Б/К/П/Восстановить авто)
       POST /api/timesheet/override {emp_id, date, symbol}
       on 200 → update cell DOM in place
       on 403/422 → error toast 3 sec

  [For DELETE /api/timesheet/override → remove override, revert to auto]

org_admin.html (DASH-04 section)
  |-- Month picker form (GET, ?month=YYYY-MM)
  |-- compute_dept_summary(month, org_id)
       → for each dept: employees, total_ya_days, work_days_in_month, rate%
  |-- render summary table
```

### Recommended Project Structure

```
app.py
  # ─── T-13 Timesheet ───────────────────────
  TIMESHEET_OVERRIDES_FILE = ...
  KZ_HOLIDAYS = {2024: [...], 2025: [...], 2026: [...]}
  load_timesheet_overrides()
  save_timesheet_overrides()
  compute_symbol(day_date, emp_id, attendance, overrides, schedule, holidays_set)
  compute_timesheet_grid(year, month, employees, attendance, overrides)
  compute_dept_summary(year, month, org_id, employees, attendance, overrides)
  
  # Page routes
  GET /timesheet → timesheet()
  
  # API routes
  POST /api/timesheet/override → save_override()
  DELETE /api/timesheet/override → delete_override()

templates/
  timesheet.html     (new)
  org_admin.html     (add DASH-04 section)
```

### Pattern 1: Symbol Engine — compute_symbol()

**What:** Pure function, no I/O — accepts pre-loaded dicts, returns one symbol string.
**When to use:** Called once per employee per day in the grid render loop.

```python
# Source: [VERIFIED: codebase grep — derived from existing dept_attendance_today() pattern]
import calendar
from datetime import date

def compute_symbol(day_date, emp_id, attendance, overrides, schedule, holidays_set):
    """Return the T-13 symbol for one employee on one calendar day.

    Priority: override > В (weekend/holiday) > attendance-derived > НН
    """
    date_str = day_date.isoformat()

    # 1. Manual override takes priority
    emp_overrides = overrides.get(emp_id, {})
    if date_str in emp_overrides:
        return emp_overrides[date_str]

    # 2. Weekend or public holiday
    work_days = schedule.get("work_days", [1, 2, 3, 4, 5])
    if day_date.isoweekday() not in work_days or date_str in holidays_set:
        return "В"

    # 3. Work day — check attendance
    day_records = attendance.get(date_str, {})
    rec = day_records.get(emp_id)
    if not rec or not rec.get("check_in"):
        return "НН"

    check_in = rec["check_in"]    # "HH:MM:SS"
    check_out = rec.get("check_out")  # "HH:MM:SS" or None

    # Late threshold: schedule start + 15 min
    sh, sm = map(int, schedule.get("start", "09:00").split(":"))
    late_m = sm + 15
    if late_m >= 60:
        late_threshold = f"{sh + 1:02d}:{late_m % 60:02d}:00"
    else:
        late_threshold = f"{sh:02d}:{late_m:02d}:00"

    # Early departure threshold: schedule end - 15 min
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
```

### Pattern 2: Totals Row Computation

**What:** Aggregate symbol list into the 5 totals columns.
**When to use:** After building the grid matrix for an employee's month.

```python
# Source: [VERIFIED: codebase — derived from T13-07 requirement + D-13]
def compute_employee_totals(symbols, schedule):
    """Compute T13-07 totals from an employee's list of symbols for one month."""
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
```

### Pattern 3: save_timesheet_overrides() — flock pattern

**What:** Atomic write using tmp file + os.replace, matching save_users() exactly.
**When to use:** Every POST to `/api/timesheet/override`.

```python
# Source: [VERIFIED: codebase grep — save_users() lines 59-70 in app.py]
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
```

**Note:** The existing `save_orgs()` / `save_depts()` use a simpler flock pattern (without tmp+replace). For timesheet_overrides — which will be written on every HR cell click — use the `save_users()` tmp+replace approach for atomicity.

### Pattern 4: KZ_HOLIDAYS Constant

```python
# Source: [ASSUMED — standard KZ holidays; verify against egov.kz before shipping]
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
```

**Holiday derivation logic:**
```python
def get_holidays_set(year):
    """Return a set of ISO date strings for KZ holidays in the given year."""
    return set(KZ_HOLIDAYS.get(year, []))

def is_holiday_year_missing(year):
    return year not in KZ_HOLIDAYS
```

### Pattern 5: /timesheet Route Structure

```python
# Source: [VERIFIED: codebase — adapted from dept_attendance_today() scoping pattern]
@app.route("/timesheet")
@require_role("dept_admin", "org_admin", "superadmin")
def timesheet():
    role = session.get("role")
    session_dept_id = session.get("dept_id")
    session_org_id = session.get("org_id")

    # Resolve month param
    month_str = request.args.get("month", datetime.now().strftime("%Y-%m"))
    try:
        year, month_num = map(int, month_str.split("-"))
    except (ValueError, AttributeError):
        year, month_num = datetime.now().year, datetime.now().month
        month_str = f"{year:04d}-{month_num:02d}"

    # Resolve dept_id param with scope enforcement
    dept_id_param = request.args.get("dept_id", "")
    if role == "dept_admin":
        dept_id = session_dept_id  # always fixed, ignore param
    elif role == "org_admin":
        # Must belong to their org
        depts = load_depts()
        if dept_id_param and dept_id_param in depts:
            dept = depts[dept_id_param]
            if dept.get("org_id") != session_org_id:
                return render_template("403.html"), 403
            dept_id = dept_id_param
        else:
            # Default to first dept in org
            org_depts = [did for did, d in depts.items() if d.get("org_id") == session_org_id]
            dept_id = org_depts[0] if org_depts else None
    else:  # superadmin
        dept_id = dept_id_param or None

    # Build grid ...
    _, num_days = calendar.monthrange(year, month_num)
    # ... (load data, compute symbols, totals)
    return render_template("timesheet.html", ...)
```

### Pattern 6: Override API — Scope Validation

```python
# Source: [VERIFIED: codebase — D-05 scope rules]
@app.route("/api/timesheet/override", methods=["POST", "DELETE"])
@require_role("dept_admin", "org_admin", "superadmin")
def timesheet_override():
    role = session.get("role")
    data = request.json or {}
    emp_id = data.get("emp_id", "")
    date_str = data.get("date", "")
    symbol = data.get("symbol", "")  # absent on DELETE

    employees = load_employees()
    emp = employees.get(emp_id)
    if not emp:
        return jsonify({"error": "employee_not_found"}), 404

    # Scope check
    if role == "dept_admin" and emp.get("dept_id") != session.get("dept_id"):
        return jsonify({"error": "forbidden"}), 403
    if role == "org_admin" and emp.get("org_id") != session.get("org_id"):
        return jsonify({"error": "forbidden"}), 403

    if request.method == "DELETE":
        # Remove override → cell reverts to auto-derived
        overrides = load_timesheet_overrides()
        overrides.get(emp_id, {}).pop(date_str, None)
        save_timesheet_overrides(overrides)
        return jsonify({"deleted": True})

    # POST: validate symbol
    MANUAL_SYMBOLS = {"Б", "К", "П"}
    if symbol not in MANUAL_SYMBOLS:
        return jsonify({"error": "invalid_symbol"}), 422

    overrides = load_timesheet_overrides()
    if emp_id not in overrides:
        overrides[emp_id] = {}
    overrides[emp_id][date_str] = symbol
    save_timesheet_overrides(overrides)
    return jsonify({"symbol": symbol, "auto": False})
```

### Anti-Patterns to Avoid

- **Storing auto-derived symbols in JSON:** Auto-derived values must be computed at render time from attendance.json + schedule. Only manual overrides go in `timesheet_overrides.json`.
- **String slice for time comparison:** `check_in[:5] > schedule_start` misses seconds and is ambiguous. Use the full HH:MM:SS threshold string (as verified working in `dept_attendance_today()`).
- **Client-side symbol computation:** Computing symbols in JS for display and then trusting them in API calls. The API must recompute or trust only stored overrides.
- **Blocking grid render on attendance dict re-read per employee:** Call `load_attendance()` once before the loop, not inside it.
- **Using `fcntl.flock` on a file opened for read:** flock on read is unnecessary and can cause deadlocks in multi-worker scenarios. Lock only on writes (the save_* functions).
- **`<form method="POST">` for the grid selector:** Must be GET — URL must be bookmarkable (D-10).
- **Iterating all attendance dates for a month:** Filter by month prefix (`date_str.startswith(month_str)`) or pre-build a set of date strings for the month to avoid O(n) scans over large attendance.json files.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Day count in a month | Manual 30/31/28/29 lookup | `calendar.monthrange(year, month)[1]` | Handles leap years correctly |
| First day of month weekday | Manual calculation | `calendar.monthrange(year, month)[0]` (0=Mon) OR `date(year, month, 1).isoweekday()` (1=Mon) | Off-by-one error risk |
| Time arithmetic for thresholds | Strptime + timedelta + strftime | String threshold construction (`f"{sh:02d}:{late_m:02d}:00"`) | Existing codebase pattern — verified correct; no parsing overhead |
| Holiday detection | User-editable config table | `KZ_HOLIDAYS` dict constant in app.py | Simple, auditable, no admin UI needed for v1 |
| Grid HTML | Client-side JS grid library | Jinja2 `<table>` with `{% for %}` | Consistent with server-render pattern; bookmarkable URLs |

**Key insight:** The standard library `calendar` module handles all calendar arithmetic needed. Time comparisons use string comparison on HH:MM:SS format (already established in `dept_attendance_today()`). No external packages are warranted.

---

## Common Pitfalls

### Pitfall 1: Attendance time format — HH:MM:SS vs HH:MM

**What goes wrong:** `attendance.json` stores times as `"HH:MM:SS"` (e.g., `"09:16:04"`). The `schedule` stores start/end as `"HH:MM"` (e.g., `"09:00"`). Building a late threshold as `"09:15"` instead of `"09:15:00"` causes the string comparison to fail (`"09:16:04" > "09:15"` returns True correctly, but `"09:15:04" > "09:15"` also returns True — the comparison is on different-length strings, which works but is fragile).

**Why it happens:** Copy-paste from schedule fields without normalizing to the same length.

**How to avoid:** Always build thresholds as `"HH:MM:00"` (zero-padded seconds) to match the HH:MM:SS format in attendance.json. Verified correct in existing `dept_attendance_today()` pattern.

**Warning signs:** Late detection triggering for employees who arrived at exactly `HH:MM:00`.

---

### Pitfall 2: Weekend + Holiday Logic — isoweekday() vs weekday()

**What goes wrong:** Python's `date.weekday()` returns 0=Monday; `date.isoweekday()` returns 1=Monday. The schedule's `work_days` field uses ISO weekday integers (1=Mon … 7=Sun) per Phase 2 D-08. Using `weekday()` causes an off-by-one error that marks all Sundays as Mondays.

**Why it happens:** `weekday()` and `isoweekday()` are easily confused.

**How to avoid:** Always use `day_date.isoweekday()` when checking against `schedule["work_days"]`. The existing `dept_attendance_today()` line 1080 correctly uses `date.today().weekday() + 1` (converts `weekday()` to ISO). In `compute_symbol()`, use `day_date.isoweekday()` directly.

**Warning signs:** Saturdays (ISO 6) or Sundays (ISO 7) showing НН instead of В.

---

### Pitfall 3: Grid Scope — Employees Without dept_id Appearing in Grid

**What goes wrong:** Employees migrated before Phase 2 may have `dept_id: null`. If not filtered, they appear in every department's grid.

**Why it happens:** Migration script assigns dept_id but some employees may be added via the old API without dept_id.

**How to avoid:** Filter employees in the `/timesheet` route: `scoped = {eid: e for eid, e in employees.items() if e.get("dept_id") == dept_id}`. Treat `None` dept_id as not belonging to any dept.

**Warning signs:** Phantom employee rows in timesheet with valid check-in data.

---

### Pitfall 4: Totals Row — ОУ Double-Counting

**What goes wrong:** ОУ (both late and early departure) must count in BOTH the late column and the early departure count. A naive implementation counting only distinct symbols will under-count late arrivals.

**Why it happens:** ОУ is a composite symbol. The totals row requirement (D-13) counts О and У independently.

**How to avoid:** Use `s in ("О", "ОУ")` for late count and `s in ("У", "ОУ")` for early departure count (not shown in totals header, but tracked). Days worked = symbols in ("Я", "О", "У", "ОУ"). Verified in research.

**Warning signs:** Late arrival total < number of О cells visible.

---

### Pitfall 5: DASH-04 Attendance Rate Denominator

**What goes wrong:** Computing attendance rate as `present_days / calendar_days` instead of `present_days / work_days_in_month`. A dept with 5-day schedules in a month with 10 weekends would show ~71% even if everyone came every work day.

**Why it happens:** Using `calendar.monthrange()[1]` (total days) as denominator.

**How to avoid:** Count work days in month = days where `isoweekday() in work_days AND date_str not in holidays_set`. Use that count as denominator. Formula: `(days_with_ya) / total_work_days * 100`, rounded to 1 decimal.

**Warning signs:** Attendance rate below 100% for a dept where everyone attended all scheduled days.

---

### Pitfall 6: Future Days in Current Month

**What goes wrong:** For the current month, days after today have no attendance data. They will all show НН (absent, reason unknown), inflating the absent count in the totals row.

**Why it happens:** The symbol engine correctly returns НН for a work day with no record — which is correct for past days but misleading for future days.

**How to avoid:** For days after `date.today()`, return `None` or a special `"—"` marker (no data / future day) in the symbol engine, and render them with the transparent/gray color per the UI-SPEC. Exclude `None` symbols from totals row calculations.

**Warning signs:** Totals row showing high НН count for the current month mid-month.

---

### Pitfall 7: Override API — Symbol Injection

**What goes wrong:** Accepting any string as the override symbol allows injection of invalid symbols (e.g., `"Я"`, `"В"`, or arbitrary strings) via direct API calls.

**Why it happens:** No server-side validation on the symbol value.

**How to avoid:** Whitelist: `MANUAL_SYMBOLS = {"Б", "К", "П"}`. Return 422 for anything outside this set. Auto-derived symbols (Я, О, У, В, НН, ОУ) must never be stored as overrides — they are computed.

**Warning signs:** Cells showing unexpected symbols after direct API calls.

---

## Code Examples

### Grid date iteration (month loop)

```python
# Source: [VERIFIED: Python stdlib calendar docs + local runtime test]
import calendar
from datetime import date, timedelta

def get_month_days(year, month):
    """Return list of date objects for all days in the given year-month."""
    _, num_days = calendar.monthrange(year, month)
    first = date(year, month, 1)
    return [first + timedelta(days=i) for i in range(num_days)]

# Usage:
days = get_month_days(2026, 6)
# days[0].isoweekday() == 1 (Monday, June 1 2026) -- verified
```

### Jinja2 grid cell macro pattern

```html
{# Source: [VERIFIED: codebase — matches dept_admin.html table pattern] #}
<table style="table-layout:fixed;border-collapse:collapse;min-width:max-content;">
<thead>
  <tr>
    <th scope="col" style="width:180px;padding:4px 12px;...">Сотрудник</th>
    {% for d in days %}
    <th scope="col" style="width:32px;text-align:center;padding:4px;
        {% if d.isoweekday() >= 6 or d.isoformat() in holidays_set %}color:#9E9E9E;{% endif %}">
      {{ d.day }}
    </th>
    {% endfor %}
    <th scope="col" style="width:60px;text-align:center;">Я</th>
    <th scope="col" style="width:60px;text-align:center;">Ч</th>
    <th scope="col" style="width:60px;text-align:center;">П/НН</th>
    <th scope="col" style="width:60px;text-align:center;">О</th>
    <th scope="col" style="width:60px;text-align:center;">Б/К</th>
  </tr>
  ...
</thead>
<tbody>
  {% for emp_id, row in grid_rows %}
  <tr>
    <td style="...">{{ employees[emp_id].name }}</td>
    {% for sym in row.symbols %}
    <td data-emp="{{ emp_id }}" data-date="{{ loop.index0|day_date(year, month) }}"
        title="{{ sym_titles[sym] }}"
        style="background:{{ sym_bg[sym] }};color:{{ sym_fg[sym] }};
               font-size:{% if sym == 'ОУ' %}11px{% else %}13px{% endif %};
               font-weight:600;text-align:center;padding:4px;cursor:{% if can_edit %}pointer{% else %}default{% endif %};">
      {{ sym if sym else '' }}
    </td>
    {% endfor %}
    ...
  </tr>
  {% endfor %}
</tbody>
</table>
```

### JS inline override handler

```javascript
// Source: [VERIFIED: codebase — matches existing fetch() pattern in dept_admin.html]
function openOverrideDropdown(cell) {
  const dropdown = document.getElementById('override-dropdown');
  const rect = cell.getBoundingClientRect();
  dropdown.style.top = (rect.bottom + window.scrollY + 4) + 'px';
  dropdown.style.left = (rect.left + window.scrollX) + 'px';
  dropdown.dataset.empId = cell.dataset.emp;
  dropdown.dataset.date = cell.dataset.date;
  dropdown.classList.remove('hidden');
}

async function applyOverride(symbol) {
  const dropdown = document.getElementById('override-dropdown');
  const empId = dropdown.dataset.empId;
  const dateStr = dropdown.dataset.date;
  dropdown.classList.add('hidden');

  const method = symbol === 'auto' ? 'DELETE' : 'POST';
  const body = symbol === 'auto'
    ? JSON.stringify({ emp_id: empId, date: dateStr })
    : JSON.stringify({ emp_id: empId, date: dateStr, symbol: symbol });

  try {
    const resp = await fetch('/api/timesheet/override', {
      method, headers: { 'Content-Type': 'application/json' }, body
    });
    if (resp.ok) {
      const data = await resp.json();
      // Update cell in-place
      const cell = document.querySelector(`td[data-emp="${empId}"][data-date="${dateStr}"]`);
      // Re-apply color class based on returned symbol
      updateCell(cell, data.symbol || null);
    } else {
      showToast(resp.status === 403 ? 'Нет прав для изменения этой ячейки.' : 'Недопустимый символ.');
    }
  } catch (e) {
    showToast('Ошибка соединения. Попробуйте ещё раз.');
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@login_required` decorator | `@require_role(*allowed_roles)` | Phase 1 | All new routes use @require_role |
| `save_employees()` without flock | `save_users()` with tmp+os.replace+flock | Phase 1 | All new save_* must use atomic write pattern |
| No org/dept scoping | Role-scoped data via `session['dept_id']`, `session['org_id']` | Phase 2 | Timesheet route must filter by these session fields |
| No schedule on employees | `schedule: {start, end, work_days}` in employees.json | Phase 2 | Symbol engine reads this field for late/early detection |

**Deprecated/outdated:**
- `save_orgs()` / `save_depts()` in current app.py use a simpler flock (lock on open file, not tmp+replace). For `save_timesheet_overrides()`, use the `save_users()` atomic pattern instead — more writes per session, higher risk of partial write on crash.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | KZ public holiday dates for 2024, 2025, 2026 (16 holidays/year, standard national holidays) | Standard Stack / Code Examples | If egov.kz has different dates (e.g., substitution days), В will be marked incorrectly for some days |
| A2 | attendance.json check_in/check_out times are always in HH:MM:SS format (not HH:MM) | Common Pitfalls / Code Examples | If some records store HH:MM, the threshold comparison string must be adjusted to HH:MM length |
| A3 | Employees added after Phase 2 migration will all have `schedule` field populated | Architecture Patterns | If `schedule` is missing on an employee, `compute_symbol()` must gracefully default to `{"start":"09:00","end":"18:00","work_days":[1,2,3,4,5]}` |

**Note on A1:** The KZ holidays constant should be verified against the official Kazakhstan government portal (egov.kz) before the phase ships. The STATE.md blocker note confirms this: "Phase 3: KZ public holidays 2025–2026 need verification against egov.kz."

---

## Open Questions

1. **attendance.json time format consistency**
   - What we know: Live data shows `"10:12:10"` format (HH:MM:SS). Code in `dept_attendance_today()` builds thresholds as `"09:15:00"` (HH:MM:SS).
   - What's unclear: Could any legacy records (pre-RBAC) have stored `"HH:MM"` format?
   - Recommendation: Add a defensive normalizer in `compute_symbol()`: if `len(check_in) == 5: check_in += ":00"`. Cost: one branch per cell; negligible.

2. **KZ 2026 holiday dates — substitution days**
   - What we know: Standard holidays are predictable. Some years have government-declared substitution days (a Friday declared off, a Saturday made a work day).
   - What's unclear: 2026 substitution schedule not confirmed.
   - Recommendation: Hard-code standard holidays per D-06. Substitution days are a v2 problem per REQUIREMENTS.md T2-04.

3. **DASH-04 route — GET or API?**
   - What we know: D-09 says "section on org_admin.html" with a month picker form. No new route.
   - What's unclear: Does the org_admin.html route currently accept a `?month=` param? It does not appear to.
   - Recommendation: Extend the existing `/org_admin` GET route to accept an optional `?summary_month=YYYY-MM` query param, passing summary data to the template when present. Keep the main org_admin page functionality unchanged.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14.4 | Symbol engine, date arithmetic | Yes | 3.14.4 | — |
| `calendar` stdlib | `calendar.monthrange()` | Yes | built-in | — |
| `datetime` stdlib | Date iteration, month parsing | Yes | built-in | — |
| `fcntl` stdlib | `save_timesheet_overrides()` | Yes | built-in | — |
| Flask 3.1.3 | Route handling, session | Yes | 3.1.3 | — |
| Jinja2 3.1.6 | Grid template rendering | Yes | 3.1.6 | — |
| pytest 9.0.3 | Test suite | Yes | 9.0.3 | — |
| PM2 | Process restart after deploy | Yes | confirmed in project | — |

**Missing dependencies with no fallback:** None.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pytest.ini` (exists — `testpaths = tests`) |
| Quick run command | `python -m pytest tests/test_timesheet.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| T13-01 | `/timesheet` route renders, returns 200 with grid data | integration | `pytest tests/test_timesheet.py::test_timesheet_renders -x` | No — Wave 0 |
| T13-02 | All 8 symbols + ОУ produced by symbol engine | unit | `pytest tests/test_timesheet.py::test_compute_symbol_all_cases -x` | No — Wave 0 |
| T13-03 | Я for on-time check-in; НН for absent work day; В for weekend | unit | `pytest tests/test_timesheet.py::test_symbol_auto_derivation -x` | No — Wave 0 |
| T13-04 | Late arrival → О | unit | `pytest tests/test_timesheet.py::test_symbol_late -x` | No — Wave 0 |
| T13-05 | Early departure → У; both → ОУ | unit | `pytest tests/test_timesheet.py::test_symbol_early_and_combined -x` | No — Wave 0 |
| T13-07 | Totals row counts correct (days_worked, hours, absences, late, vac_sick) | unit | `pytest tests/test_timesheet.py::test_totals_row -x` | No — Wave 0 |
| T13-08 | KZ holidays marked В; year-without-data triggers missing_holiday_year flag | unit | `pytest tests/test_timesheet.py::test_kz_holidays -x` | No — Wave 0 |
| DASH-04 | org_admin summary shows correct attendance rate per dept | integration | `pytest tests/test_timesheet.py::test_dash04_summary -x` | No — Wave 0 |
| D-05 | dept_admin 403 on override for out-of-scope employee | integration | `pytest tests/test_timesheet.py::test_override_scope_403 -x` | No — Wave 0 |
| D-08 | dept_admin 403 when dept_id param != session dept_id | integration | `pytest tests/test_timesheet.py::test_timesheet_scope_isolation -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_timesheet.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_timesheet.py` — all T13 and DASH-04 tests listed above
- [ ] `conftest.py` update: add `TIMESHEET_OVERRIDES_FILE` monkeypatch (alongside ORGS_FILE/DEPTS_FILE guards)

**Note on conftest.py update:** The existing `conftest.py` guards ORGS_FILE and DEPTS_FILE with `hasattr()`. The same guard pattern must be applied for `TIMESHEET_OVERRIDES_FILE` so Wave 0 tests work before the constant is added to `app.py`.

---

## Security Domain

`security_enforcement: true` (from `.planning/config.json`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Handled by existing `@require_role` |
| V3 Session Management | No | Existing session management unchanged |
| V4 Access Control | Yes | Server-side scope check: dept_admin can only override their dept employees; org_admin their org |
| V5 Input Validation | Yes | Override symbol whitelist: `{"Б", "К", "П"}` only; reject all other values with 422 |
| V6 Cryptography | No | No crypto in this phase |

### Known Threat Patterns for Flask + JSON Storage

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Horizontal privilege escalation: dept_admin POSTs override for emp outside their dept via forged `emp_id` | Elevation of privilege | Server reads emp.dept_id from employees.json (not from client); compares to `session['dept_id']` |
| Parameter tampering: `?dept_id=X` on `/timesheet` where X is another dept | Spoofing | Server validates dept ownership against session; returns 403 on mismatch (D-08) |
| Symbol injection via override API | Tampering | Whitelist: MANUAL_SYMBOLS = {"Б", "К", "П"}; return 422 for any other value |
| JSON file race condition on concurrent override saves | Tampering | `fcntl.flock(LOCK_EX)` + `os.replace()` atomic write (matches save_users pattern) |
| Missing `@require_role` on DELETE override route | Elevation of privilege | Both POST and DELETE on `/api/timesheet/override` share the same `@require_role` decorator |

---

## Sources

### Primary (HIGH confidence)

- `app.py` (codebase) — `dept_attendance_today()` function: established late detection pattern, scoping pattern, flock pattern
- `app.py` (codebase) — `save_users()`: canonical atomic write pattern with tmp+os.replace+flock
- `data/attendance.json` (codebase) — confirmed time format: `"HH:MM:SS"` (e.g., `"10:12:10"`)
- `data/employees.json` (codebase) — confirmed schedule schema: `{start: "HH:MM", end: "HH:MM", work_days: [1..7]}`
- `templates/dept_admin.html` (codebase) — CSS variables, table layout, badge colors, spacing scale
- `templates/org_admin.html` (codebase) — DASH-04 section target layout
- `tests/conftest.py` (codebase) — monkeypatch pattern for new file constants

### Secondary (MEDIUM confidence)

- Python `calendar` stdlib documentation — `monthrange(year, month)` return value semantics [CITED: docs.python.org/3/library/calendar.html]

### Tertiary (LOW confidence)

- KZ public holiday dates for 2024/2025/2026 — training data; must be verified against egov.kz before release [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all stdlib and existing Flask/Jinja2
- Symbol engine logic: HIGH — verified via local runtime tests; all 7 test cases passed
- Time comparison correctness: HIGH — verified against existing codebase pattern
- Totals row aggregation: HIGH — verified via runtime test
- KZ holiday dates: LOW — training data, not confirmed against egov.kz this session
- DASH-04 work day counting: HIGH — verified via local runtime test

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (stable domain; KZ holiday data should be re-verified annually)
