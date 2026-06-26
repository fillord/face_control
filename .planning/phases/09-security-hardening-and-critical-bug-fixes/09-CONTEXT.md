# Phase 9: Security Hardening & Critical Bug Fixes - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning
**Source:** User-provided requirements (260626-jko analysis report)

<domain>
## Phase Boundary

Plug the highest-risk security gaps and fix three confirmed bugs before any new feature work. Every item is small-effort, high-impact, and grounded in the 260626-jko project analysis. No new frameworks except Flask-Limiter and Flask-WTF (both pip-installable). No API shape changes visible to the kiosk.

</domain>

<decisions>
## Implementation Decisions

### SEC-01: Brute-Force Protection on /login
- `Flask-Limiter` (pip install flask-limiter)
- Limit: 5 attempts per 15 minutes per IP on `POST /login`
- On limit exceeded: return HTTP 429 with flash message "Слишком много попыток. Попробуйте через 15 минут."
- Use in-memory storage (default) — PM2 single worker, no Redis needed

### SEC-02: Brute-Force Protection on PIN Verification
- Same `Flask-Limiter` instance
- `POST /api/register/<reg_token>/verify_pin` — 10 attempts, then lock the token (set `reg_token_expires` to past datetime so it's effectively expired)
- Return 429 with JSON `{"error": "Слишком много попыток"}`

### SEC-03: CSRF Protection
- `Flask-WTF` with `CSRFProtect(app)` (pip install flask-wtf)
- Apply to all HTML form POST routes (non-JSON endpoints): `/login`, `/api/me` (password change), user management forms in superadmin
- JSON API routes (`Content-Type: application/json`) are exempt — Flask-WTF exempts them automatically via `WTF_CSRF_CHECK_DEFAULT = False` + `@csrf.exempt` where needed
- Add `{{ csrf_token() }}` hidden input to every HTML `<form>` in templates
- Affected templates: `login.html`, `profile.html`, `account.html` and any form in `superadmin.html`, `org_admin.html`, `dept_admin.html`

### SEC-04: Session Cookie Security Flags
- Add to `app.py` Flask config block:
  - `SESSION_COOKIE_SECURE = True` (HTTPS only — nginx terminates SSL)
  - `SESSION_COOKIE_HTTPONLY = True`
  - `SESSION_COOKIE_SAMESITE = "Lax"`
- These are config-only changes, no logic changes

### SEC-05: Configurable LBPH Threshold
- Move hardcoded `80` (confidence threshold in `recognize()`) to `AppSetting` table
- Key: `lbph_threshold`, default value: `"80"`, type: integer
- Read at request time via `AppSetting.query.filter_by(key='lbph_threshold').first()`
- Add UI control in superadmin settings tab: number input 50–120, label "Порог распознавания (LBPH)"
- PATCH `/api/settings/lbph_threshold` (reuse existing settings PATCH pattern)

### BUG-01: Hardcoded 09:00 in recognize() — app.py:2980
- `is_late` in the `/api/recognize` response currently compares `now_time > "09:00:00"` regardless of the employee's schedule
- Fix: after fetching `emp_dict`, load `EmployeeSchedule.query.filter_by(emp_id=emp_id).first()` and compute `is_late = now_time > _time_threshold(schedule.start_time, minutes=15)`
- `_time_threshold(t, minutes)` already exists in `app.py` — reuse it
- If no schedule found: fall back to `"09:15:00"` (09:00 + 15 min grace)

### BUG-02: Hardcoded 09:00 in get_stats() — app.py:3197
- `get_stats()` computes late-arrival count by comparing `check_in_time > "09:00:00"` for all employees
- Fix: join `EmployeeSchedule` per employee and use each employee's `start_time + 15 min` as the threshold
- Performance note: `get_stats()` already queries employees; add a dict lookup `schedule_map = {s.emp_id: s for s in EmployeeSchedule.query.filter_by(org_id=org_id).all()}` and use `schedule_map.get(emp_id)`

### BUG-03: dept_id UUID instead of dept_name in compute_dept_summary() — app.py:388
- `compute_dept_summary()` falls back to `dept_id` (UUID) as the department name when the name lookup fails
- Fix: replace the fallback with `Department.query.get(dept_id).name if Department.query.get(dept_id) else dept_id`
- Or cache: `dept_name_map = {d.id: d.name for d in Department.query.filter_by(org_id=org_id).all()}` and use `dept_name_map.get(dept_id, dept_id)`

### REL-01: /health Endpoint
- `GET /health` — no auth required (public)
- Response: `{"status": "ok", "db": "connected"}` with HTTP 200
- If DB check fails: `{"status": "error", "db": "unavailable"}` with HTTP 503
- DB check: `db.session.execute(text("SELECT 1"))` wrapped in try/except

### REL-02: KZ_HOLIDAYS 2027
- The `KZ_HOLIDAYS` dict in `app.py` (lines 207–229) ends at 2026
- Add 2027 entries following the same format: `date(2027, M, D)` keys with `"Holiday Name"` values
- Kazakhstan public holidays 2027 (same dates as prior years for recurring holidays):
  - Jan 1–2: Новый год
  - Jan 7: Рождество Христово
  - Mar 8: Международный женский день
  - Mar 21–23: Наурыз мейрамы
  - May 1: Праздник единства народа Казахстана
  - May 7: День защитника Отечества
  - May 9: День Победы
  - Jul 6: День Столицы
  - Aug 30: День Конституции Республики Казахстан
  - Dec 1: День Первого Президента (note: verify if still official)
  - Dec 16–17: День Независимости Республики Казахстан

### REL-03: DB Backup Button in Superadmin Panel
- New route: `GET /api/backup/db` — requires `superadmin` role
- Implementation: `send_file('data/app.db', as_attachment=True, download_name=f'app_backup_{date.today()}.db', mimetype='application/octet-stream')`
- Add button in `superadmin.html` settings/system section: "Скачать резервную копию БД"
- Button triggers `window.location = '/api/backup/db'`

### PERF-01: Composite Index on AttendanceRecord
- Currently `AttendanceRecord` has two separate indexes: `Index('ix_attendance_emp_id', 'emp_id')` and `Index('ix_attendance_date', 'date')` in `models.py`
- Replace with a single composite index: `Index('ix_attendance_emp_date', 'emp_id', 'date')`
- Requires a DB migration: add the new index, remove the old separate ones
- Use raw SQLAlchemy DDL (`op.create_index` / `op.drop_index`) — project does NOT use Flask-Migrate, so write an inline migration function called once at startup (same pattern as existing inline `ALTER TABLE` in `app.py`)

### Claude's Discretion
- Order of operations within waves (parallel where no file overlap)
- Exact startup migration guard pattern for PERF-01 (use try/except like existing inline migrations)
- Whether to put the backup button in the existing "Настройки" tab or a new "Система" section

</decisions>

<specifics>
## Specific Ideas

- BUG-01 line reference: `app.py` line ~2980 — `is_late = now_time > "09:00:00"` inside `recognize()`
- BUG-02 line reference: `app.py` line ~3197 — `if check_in_time > "09:00:00":` inside `get_stats()`
- BUG-03 line reference: `app.py` line ~388 — fallback `dept_id` in `compute_dept_summary()`
- `_time_threshold()` already exists in app.py — reuse for BUG-01 and BUG-02
- Flask-Limiter storage: in-memory (MemoryStorage) — single PM2 worker, no Redis
- CSRF exempt pattern: `@csrf.exempt` on all `/api/*` routes that receive `application/json`
- Backup route must not stream — `data/app.db` is small (<50MB), use `send_file` directly

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project foundations
- `app.py` — main Flask app (3283 lines); all routes, ORM calls, CV code, helpers
- `models.py` — 10 SQLAlchemy models including `AppSetting`, `AttendanceRecord`, `EmployeeSchedule`, `Department`
- `CLAUDE.md` — project conventions and constraints (Flask + Python only, PM2 single worker)
- `.planning/STATE.md` — project state and completed phases

### Key areas in app.py
- Lines ~207–229: `KZ_HOLIDAYS` dict (extend to 2027)
- Lines ~388: `compute_dept_summary()` (BUG-03)
- Lines ~2946: confidence threshold hardcode `80` (SEC-05 configurable threshold)
- Lines ~2980: `is_late` hardcode in `recognize()` (BUG-01)
- Lines ~3197: `is_late` hardcode in `get_stats()` (BUG-02)

### Analysis report
- `.planning/quick/260626-jko-project-analysis-improvements/260626-jko-ANALYSIS.md` — source of all findings

</canonical_refs>

<deferred>
## Deferred Ideas

- Flask-Migrate (Alembic) — deferred to a future refactor phase; inline migration sufficient for PERF-01
- Anti-spoofing for face recognition — deferred (requires ML model, large scope)
- Background LBPH training thread — deferred
- Geo/IP kiosk restriction — deferred
- Breaking app.py into Blueprints — deferred

</deferred>

---

*Phase: 09-security-hardening-and-critical-bug-fixes*
*Context gathered: 2026-06-26 from user requirements*
