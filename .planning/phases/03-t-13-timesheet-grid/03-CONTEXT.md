# Phase 3: T-13 Timesheet Grid - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the statutory T-13 timesheet grid: a dedicated `/timesheet` page where dept_admins, org_admins, and superadmins view a monthly grid of employees × calendar days with symbols auto-derived from face check-in data and KZ public holidays. Includes inline cell editing for manual symbols (Б/К/П), a monthly totals row, and the DASH-04 per-department summary report on the org_admin dashboard. Export (Phase 4) is out of scope here.

</domain>

<decisions>
## Implementation Decisions

### Symbol Engine (T13-02 through T13-05, T13-08)

- **D-01:** Auto-derived symbols: **Я** (present, within schedule), **О** (late — first check-in > 15 min after schedule start), **У** (early departure — last check-out > 15 min before schedule end), **В** (weekend or KZ public holiday), **НН** (work day with no check-in record). НН is the default for absent work days — never П by default.
- **D-02:** Both О and У in the same day: display as **"ОУ"** in the cell (two-character notation). Totals row counts each condition separately (late count and early departure count are independent columns).
- **D-03:** Manual symbol override: Phase 3 includes **inline cell editing** for Б (sick leave), К (business trip), and П (absent with reason). An HR user clicks a cell to get a dropdown/button group; the chosen symbol overrides the auto-derived value for that day.
- **D-04:** Override storage: **`data/timesheet_overrides.json`** — a separate file keyed by `emp_id → date (YYYY-MM-DD) → symbol`. Follows the `load_*/save_*` pattern with `fcntl.flock(LOCK_EX)` on writes. Auto-derived values are never stored — they are computed at render time from `attendance.json` + schedule.
- **D-05:** Override edit permissions: **dept_admin and above**. dept_admin can override cells for employees in their own dept; org_admin can override any employee in their org; superadmin can override all. Viewer gets read-only grid.
- **D-06:** KZ public holidays hard-coded for **2024, 2025, and 2026** in a module-level constant in `app.py` (a dict of `year → [date strings]`). When the grid renders a month whose year has no holiday data, a **yellow banner** appears in the timesheet: "Праздники за [year] год не загружены. Выходные (В) отмечены автоматически, государственные праздники нет." Weekends still auto-mark В; only national holidays are missing.

### Grid Placement & Routing (T13-01, DASH-04)

- **D-07:** The T-13 lives at a **dedicated `/timesheet` route** with a new `templates/timesheet.html` template. Month and department are passed as URL query params: `?dept_id=X&month=YYYY-MM`. Route is decorated with `@require_role('dept_admin', 'org_admin', 'superadmin')`.
- **D-08:** Data isolation enforced server-side: dept_admin's `dept_id` is read from `session['dept_id']` — any `dept_id` param that doesn't match is rejected with 403. org_admin can only view depts belonging to their `session['org_id']`. Superadmin has no restriction.
- **D-09:** DASH-04 (per-dept summary report) is implemented as a **section on `org_admin.html`** — a month picker + table showing: dept name, employee count, days present total, and attendance rate % (days present / total work days × 100). No new route needed.

### Month/Dept Selector UI

- **D-10:** Selector interaction: **URL params + server render**. Dropdowns submit a `<form method="GET">` — the page reloads with the new grid. No JS fetch for the grid itself. Consistent with existing server-render pattern and makes links bookmarkable.
- **D-11:** Default month: **current calendar month** (`datetime.now().strftime('%Y-%m')`). If `?month=` is absent from the URL, the route defaults to the current month.
- **D-12:** Dept selector for org_admin/superadmin: a **single `<select>` dropdown** of authorized departments. org_admin sees depts in their org; superadmin sees all depts grouped by org (`<optgroup label="Org Name">`). dept_admin has no dept selector — their dept is fixed from session.

### Monthly Totals Row (T13-07)

- **D-13:** The totals row at the bottom of the grid shows: **days worked** (Я count), **hours worked** (days worked × daily_hours, where daily_hours = schedule.end − schedule.start), **absences** (П + НН count), **late arrivals** (О count, including ОУ cells), **vacation/sick days** (Б + К count).

### Claude's Discretion

- Storage schema details for `timesheet_overrides.json` — Claude uses `{emp_id: {date: symbol}}` nested dict, consistent with `attendance.json` keying style.
- Inline edit UI — Claude picks a compact dropdown or button group that fits in a grid cell without breaking the table layout.
- Exact CSS for the timesheet grid — Claude follows `admin.html` / `dept_admin.html` visual patterns (CSS variables, table style, section headers).
- KZ public holiday dates for 2026 — Claude hard-codes the official list from egov.kz (standard KZ holidays: New Year, Orthodox Christmas, International Women's Day, Nauryz x3, Kazakhstan People's Unity Day, Defender's Day, Victory Day, Capital Day, Constitution Day, First President Day, Independence Day x2).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements

- `.planning/REQUIREMENTS.md` — T13-01 through T13-08, DASH-04 are Phase 3 scope; read full requirement text for each
- `.planning/ROADMAP.md` — Phase 3 goal, success criteria, and phase boundary; also read Phase 2 success criteria for schedule schema context

### Prior Phase Decisions

- `.planning/phases/01-rbac-foundation/01-CONTEXT.md` — D-04 (`@require_role` decorator pattern), D-05 (403 handling), D-07 (session fields: `user_id`, `role`, `org_id`, `dept_id`)
- `.planning/phases/02-org-dept-data-model/02-CONTEXT.md` — D-08 (employee schedule schema: `{start, end, work_days}` in employees.json), D-09 (daily hours computed at render time), D-03 (fcntl.flock pattern for all JSON writes), D-10/D-11 (role dashboard routes), D-14 (org_admin.html layout reference)

### Existing Codebase

- `app.py` — `load_attendance()` / `save_attendance()` (lines ~129–145): attendance data structure `{date: {emp_id: {check_in, check_out}}}` that the symbol engine reads; `save_users()` fcntl pattern to replicate for `save_timesheet_overrides()`; `ROLE_HIERARCHY` constant; `@require_role` decorator
- `data/attendance.json` — live attendance data keyed by YYYY-MM-DD → emp_id → `{check_in: "HH:MM", check_out: "HH:MM" or null}`
- `data/employees.json` — employee records with `schedule: {start, end, work_days}` (added by Phase 2 migration)
- `templates/dept_admin.html` — visual reference for grid styling; same CSS variables and table patterns apply to `timesheet.html`
- `templates/org_admin.html` — DASH-04 section goes here; read current layout before adding the monthly summary section

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `load_attendance()` in `app.py` — reads `attendance.json` into `{date: {emp_id: {check_in, check_out}}}`. The symbol engine iterates this structure per employee per day.
- `@require_role(*allowed_roles)` decorator — apply to `/timesheet` and `/api/timesheet/override`. No changes to the decorator needed.
- `session['dept_id']`, `session['org_id']`, `session['role']` — already populated after login; used directly for data isolation in the timesheet route.
- `fcntl.flock(LOCK_EX)` write pattern (from `save_users()`) — replicate exactly for `save_timesheet_overrides()`.
- `dept_attendance_today()` at `/api/dept_attendance_today` (line ~1069) — shows the pattern for role-scoped attendance queries; adapt for monthly aggregation.

### Established Patterns

- `load_*/save_*` JSON helpers — add `load_timesheet_overrides()` / `save_timesheet_overrides()` following the exact same file-open + flock pattern.
- Section headers `# ─── Section Name ───────────────────` — add `# ─── T-13 Timesheet ──────────────────` in `app.py`.
- `jsonify({...}), 4XX` — for the override save API endpoint.
- Server-render with Jinja2 — the timesheet grid is a `<table>` rendered server-side; no client-side grid library needed.

### Integration Points

- `/timesheet` GET route (new) — server-renders the grid with dept+month params; calls the symbol engine function.
- `POST /api/timesheet/override` (new) — accepts `{emp_id, date, symbol}`, validates role+scope, saves to `timesheet_overrides.json`.
- `org_admin.html` — add DASH-04 monthly summary section with a month picker form and dept summary table.
- `data/employees.json` — read `schedule` field per employee for late/early detection; read `dept_id` for scoping.

</code_context>

<specifics>
## Specific Ideas

- KZ public holidays for 2026 should be hard-coded alongside 2024 and 2025 in a single `KZ_HOLIDAYS` dict in `app.py`, with a comment: `# Add next year's dates before January 1 of that year`.
- The "no holiday data" banner should be in Russian and appear at the top of the timesheet table, not as a flash message — it's a permanent state for that year, not a one-time alert.
- ОУ notation (both late and early departure) should be visually distinct in the cell — Claude picks a styling approach (e.g., slightly smaller font or different color) so HR can spot it at a glance.
- The monthly summary on org_admin.html (DASH-04) should compute attendance rate as: `(days with Я) / (total_work_days in month per schedule) × 100`, rounded to one decimal.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 3-T-13 Timesheet Grid*
*Context gathered: 2026-06-13*
