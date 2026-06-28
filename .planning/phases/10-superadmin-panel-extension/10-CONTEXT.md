# Phase 10: Superadmin Panel Extension — Context

**Gathered:** 2026-06-28
**Status:** Ready for planning
**Source:** PRD Express Path (user invocation spec)

<domain>
## Phase Boundary

Extends the existing `/superadmin` panel (superadmin.html) with 7 new capabilities. The kiosk, org_admin, dept_admin, and employee flows are NOT touched. All new endpoints are protected by `@require_role("superadmin")`. Data isolation is intentional: superadmin deliberately sees all orgs.

**What already exists (DO NOT touch):**
- Tabs: Организации (CRUD), Пользователи (only org_admin creation), Система (recognition threshold, DB backup)
- Page: `/audit` — audit log with filters
- API: `/api/orgs`, `/api/users`, `/api/audit`, `/api/backup/db`, `/api/settings/*`
- DELETE `/api/kiosk/<org_token>/devices/<device_id>` endpoint already exists

</domain>

<decisions>
## Implementation Decisions

### D-01: Feature 7 — Superadmin Role Creation (Priority 1)
- Fix `create_user()` in app.py (~line 1985): superadmin can create `org_admin`, `dept_admin`, `hr_viewer` (currently blocked to only `org_admin`)
- When `dept_admin` is selected: show department select filtered by chosen org (fetch via existing org/dept APIs)
- Update `createUserPanel` in superadmin.html: add role options and conditional dept field
- `write_audit()` must be called for each user creation

### D-02: Feature 2 — Employees Tab (Priority 2)
- New tab `panelEmployees` in superadmin.html
- Endpoint: `GET /api/superadmin/employees` — all employees across all orgs
- Returns: name, org name, dept name, face_enrolled (bool), created_at date
- Filter: org selector dropdown (client-side filter on already-loaded data)
- Read-only: no edit/delete buttons — those stay with org_admin/dept_admin

### D-03: Feature 3 — Devices Tab (Priority 3)
- New tab `panelDevices` in superadmin.html
- Endpoint: `GET /api/superadmin/devices` — all KioskDevice records across all orgs
- Returns: org name, device_name, registered_at, last_seen
- Revoke button: calls existing `DELETE /api/kiosk/<org_token>/devices/<device_id>` — superadmin gets access to it
- `write_audit()` must be called on revoke

### D-04: Feature 4 — Logs Tab (Priority 4)
- New tab `panelLogs` in superadmin.html
- Endpoint: `GET /api/superadmin/logs?org_id=&event_type=` — recognition log entries
- Source: LogEntry table (SQLAlchemy ORM) or logs.json if LogEntry not yet modeled
- Returns: timestamp, event (check_in/check_out), employee name, org name, confidence_pct
- Max 500 records (most recent first); no pagination required
- Client-side filters: org selector + event type selector

### D-05: Feature 5 — Holiday Calendar (Priority 5)
- New tab `panelCalendar` in superadmin.html
- New DB model `HolidayCalendar` (or use existing `AppSetting` with JSON key `holidays_<year>`): date (string YYYY-MM-DD), name (string)
- Endpoints:
  - `GET /api/holidays?year=YYYY` — list holidays for year
  - `POST /api/holidays` — add `{date, name}`; `write_audit()` required
  - `DELETE /api/holidays/<date>` — remove; `write_audit()` required
- UI: table of holidays for selected year + add form (date input + name input + Add button)
- `compute_symbol()` must use DB holidays instead of hardcoded `KZ_HOLIDAYS` dict; fallback to hardcoded if DB empty for that year

### D-06: Feature 6 — Attendance Analytics Chart (Priority 6)
- Add to `panelSystem` tab OR new `panelAnalytics` tab in superadmin.html
- Chart.js via CDN (same pattern as other CDN scripts in project)
- Endpoint: `GET /api/superadmin/attendance_stats?days=30`
- Returns: `[{date, total_employees, present_count, percent}]`
- Line chart: x-axis = dates, y-axis = % attendance; system-wide aggregation (no org filter)

### D-07: Feature 1 — Global Excel Export (Priority 7 — most complex)
- New button in `panelSystem` tab or new `panelReports` tab
- Endpoint: `GET /api/superadmin/export/xlsx?month=M&year=Y`
- One Excel sheet per organization; sheet name = org name (truncated to 31 chars Excel limit)
- Each sheet: T-13 grid using existing `export_timesheet_xlsx()` logic extended to accept org/dept params
- Before download: month/year selector (current month default)
- Uses `openpyxl` (already installed); no new dependencies

### Claude's Discretion
- Whether `panelAnalytics` is a new tab or integrated into `panelSystem` — choose what fits the UI best
- Whether `HolidayCalendar` is a new SQLAlchemy model or stored as `AppSetting` JSON — prefer a dedicated model for query efficiency
- Tab ordering in superadmin.html nav
- Exact Chart.js version (latest stable from CDN)
- Error handling for empty data in charts/tables

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Application
- `app.py` — Flask app, all routes, SQLAlchemy models, `require_role`, `write_audit`, `compute_symbol`, `export_timesheet_xlsx`, `create_user`
- `templates/superadmin.html` — target template to extend with new tabs

### Patterns to Follow
- `templates/base.html` — base template shell (all authenticated pages extend this)
- `templates/org_admin.html` — example of tabbed panel layout in same design system
- `.planning/phases/09-security-hardening-and-critical-bug-fixes/09-04-PLAN.md` — most recent plan touching superadmin.html

### Data Models
- Look for `KioskDevice`, `LogEntry`, `Employee`, `Organization`, `Department`, `AppSetting` models in app.py

</canonical_refs>

<specifics>
## Specific Ideas

- `create_user()` fix is at ~line 1985 in app.py: change `if creator_role == "superadmin" and target_role != "org_admin": return 403` to allow `org_admin`, `dept_admin`, `hr_viewer`
- The existing `DELETE /api/kiosk/<org_token>/devices/<device_id>` endpoint needs superadmin access added to its role check
- `compute_symbol()` hardcoded holidays are in `KZ_HOLIDAYS` dict — replace lookup with DB query per date
- All new endpoints follow pattern: `@app.route('/api/superadmin/...') @require_role('superadmin')`
- Section dividers: `# ─── Section Name ───────────────────` (box-drawing chars, consistent with existing style)

</specifics>

<deferred>
## Deferred Ideas

- PDF export (out of scope per v2 requirements EXP2-01)
- Holiday import from ICS/iCal file
- Per-org analytics breakdown (only system-wide chart required)
- Attendance trend over multiple months
- Edit existing holidays (DELETE + re-add is sufficient)

</deferred>

---

*Phase: 10-superadmin-panel-extension*
*Context gathered: 2026-06-28 via PRD Express Path (user invocation)*
