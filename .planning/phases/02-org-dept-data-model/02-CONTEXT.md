# Phase 2: Org/Dept Data Model - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Add organizations and departments as structured JSON data; migrate all existing employees with org/dept assignment and work schedules (strictly additive — no existing fields touched); build CRUD management UI on dedicated pages per role; wire superadmin and dept dashboards to show scoped live data; display department name on kiosk recognition.

</domain>

<decisions>
## Implementation Decisions

### Data File Structure

- **D-01:** Two separate files: `data/orgs.json` (keyed by org_id) and `data/depts.json` (keyed by dept_id). Depts carry an `org_id` foreign key. Follows the same load_*/save_* pattern as `employees.json` and `users.json` — consistent with existing codebase conventions.
- **D-02:** Org record schema: `{ id, name, description, created_at }`. Dept record schema: `{ id, org_id, name, created_at }`. Claude decides on the dept head field: keep it as a simple `head_name` string (not a user FK) to avoid join complexity in a JSON file system — display only, no permissions logic tied to it. Both IDs are UUID4 strings (matching the `id` pattern in `users.json`).
- **D-03:** Add `load_orgs()` / `save_orgs()` and `load_depts()` / `save_depts()` helpers in `app.py` following the exact pattern of `load_employees()` / `save_employees()`. Use `fcntl.flock(LOCK_EX)` on writes, same as `save_users()`.

### Migration Delivery (MIG-01, MIG-02)

- **D-04:** Standalone `migrate.py` script in project root. Run once manually: `python migrate.py`. No auto-run on startup, no Flask route. Gives operator explicit control; easy to re-run safely if needed.
- **D-05:** Migration creates a single default org ("Главная организация") and a single default dept ("Основной отдел"), then assigns `org_id` and `dept_id` to every existing employee record. All existing fields (`id`, `name`, `role`, `label`, `face_count`, `registered_at`) are preserved verbatim — never overwritten.
- **D-06:** After patching `employees.json`, migration performs MIG-02 label integrity check: loads the LBPH model from `data/face_model.xml` (or equivalent), reads every label value from the model, and warns for any employee whose `label` integer is not found. Prints a summary; does NOT abort on mismatch — warn-only. Script prints a success/warning summary to stdout before exiting.
- **D-07:** Migration writes a backup of the original `employees.json` to `data/employees_backup_{timestamp}.json` before patching, so the operator can roll back manually if needed.

### Work Schedule Schema (T13-06)

- **D-08:** Schedule stored inline inside each employee record in `employees.json` under the key `schedule`. Schema: `{ "start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5] }`. Work days are ISO weekday integers (1=Mon … 7=Sun). No default — schedule is a required field when creating a new employee via the CRUD form. Migration assigns `{ "start": "09:00", "end": "18:00", "work_days": [1, 2, 3, 4, 5] }` to all existing employees (standard clinic workday).
- **D-09:** Total daily hours for T-13 is calculated at render time from `end - start` (not stored). Avoids stale cached values.

### CRUD UI Location

- **D-10:** Three new dedicated templates, each purpose-built for its role:
  - `templates/superadmin.html` — superadmin dashboard + org CRUD (replaces the `/admin` redirect for superadmin after login)
  - `templates/org_admin.html` — org_admin dashboard + dept CRUD for their own org + employee list
  - `templates/dept_admin.html` — dept dashboard (DASH-02) + employee management within their dept
  - Existing `templates/admin.html` remains as-is for the attendance report (used by all admin-tier roles as a secondary page)
- **D-11:** Routing: `/superadmin` → superadmin.html (@require_role("superadmin")); `/org_admin` → org_admin.html (@require_role("org_admin")); `/dept_admin` → dept_admin.html (@require_role("dept_admin", "viewer")). The Phase 1 login redirect (D-08 from Phase 1 CONTEXT) is updated: superadmin → `/superadmin`, org_admin → `/org_admin`, dept_admin → `/dept_admin`.
- **D-12:** Superadmin dashboard (DASH-01) shows: three stat cards (total orgs, total employees system-wide, today's check-ins across all orgs) + org table (org name, employee count, description, Edit/Delete actions) + inline "Add org" form at the bottom.
- **D-13:** Dept dashboard (DASH-02) on `dept_admin.html` shows: three stat cards (present today, absent today, late today) scoped to the viewer's dept + employee table (name, today's check-in time, status badge, schedule start/end) + Edit schedule action per employee. Present/absent/late computed from `attendance.json` for today and each employee's `schedule`.
- **D-14:** Org_admin dashboard shows: dept list for their org (dept name, employee count, Edit/Delete actions) + employee list for the entire org + "Add dept" form. DASH-04 (per-dept summary report for a month) is Phase 3 scope — not here.

### Kiosk Enhancement (KIOSK-01)

- **D-15:** When `recognize()` returns a successful match, look up the employee's `dept_id` in `employees.json`, then load `depts.json` to get `dept.name`. Return `dept_name` in the JSON response alongside `name` and `time`. `kiosk.html` displays it below the employee name. If `dept_id` is null or dept not found, display nothing (graceful degradation).

### Claude's Discretion

- Exact HTML/CSS layout of the new pages — Claude follows existing admin.html visual patterns (CSS variables, section headers, table style).
- Dept head field in dept record — Claude uses a simple `head_name` string (decided above in D-02).
- ID generation — Claude uses `str(uuid.uuid4())` for new org/dept IDs, consistent with user ID pattern in users.json.
- API endpoint naming for org/dept CRUD — Claude follows the existing `/api/employees` REST pattern (GET list, POST create, PUT update, DELETE).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — ORG-01 through ORG-04, MIG-01, MIG-02, T13-06, DASH-01, DASH-02, KIOSK-01 are Phase 2 scope; MIG-03 is Phase 1 complete (read for migration context)
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria, and phase boundary

### Prior Phase Decisions
- `.planning/phases/01-rbac-foundation/01-CONTEXT.md` — D-01 (users.json schema with org_id/dept_id null placeholders), D-07 (session stores org_id/dept_id), D-08 (login redirect targets — Phase 2 updates these)

### Existing Codebase
- `app.py` — load_employees/save_employees pattern (lines ~102–115) is the model for new load_orgs/save_depts helpers; save_users fcntl pattern (lines ~52–65) must be applied to all new save_* functions; ROLE_HIERARCHY constant (line 80)
- `data/employees.json` — current flat schema (id, name, role, label, face_count, registered_at) — migration adds org_id, dept_id, schedule
- `data/users.json` — UUID4 id pattern, org_id/dept_id null fields to be populated
- `templates/admin.html` — visual reference for new page styling (CSS patterns, table layout, section headers)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `load_employees()` / `save_employees()` in `app.py` — direct template for `load_orgs()`, `save_orgs()`, `load_depts()`, `save_depts()`. Same file-open pattern, same fcntl lock on write.
- `@require_role(*allowed_roles)` decorator — apply to all new CRUD routes; no changes to the decorator itself.
- `session['org_id']` / `session['dept_id']` — already populated after login (Phase 1 D-07); use directly in org/dept-scoped queries.
- `ROLE_HIERARCHY` constant — use for permission checks in CRUD (e.g., only org_admin can edit their own depts).
- CSS and HTML structure in `templates/admin.html` — new pages should inherit the same visual language (stat cards, tables, action buttons).

### Established Patterns
- JSON keyed dicts (`{id: record}`) — use for orgs.json and depts.json, matching employees.json and users.json.
- `jsonify({...}), 4XX` for API error responses.
- Section headers `# ─── Section Name ───────────────────` in app.py.
- `fcntl.flock(f, fcntl.LOCK_EX)` wrapping all JSON writes (save_users precedent).

### Integration Points
- `/login` POST handler — update post-login redirect for superadmin → `/superadmin`, org_admin → `/org_admin`, dept_admin → `/dept_admin` (extends Phase 1 D-08).
- `POST /api/recognize` → `recognize()` function — add dept_name lookup and include in JSON response (KIOSK-01).
- `kiosk.html` recognition result display — render `dept_name` below employee name if present.
- `data/employees.json` — migration patches this file; Phase 2 CRUD also updates it (add employee to dept).

</code_context>

<specifics>
## Specific Ideas

- Migration prints to stdout with color-coded OK/WARN lines per employee — gives operator confidence the migration ran correctly.
- Default names for migration default org/dept are Russian-language to match the clinic context: "Главная организация" / "Основной отдел".
- Schedule `work_days` uses ISO weekday integers so Phase 3 can call `datetime.weekday() + 1` directly without conversion.
- The `id` field for new org/dept records uses `str(uuid.uuid4())`, consistent with the user `id` pattern in `users.json`.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-Org/Dept Data Model*
*Context gathered: 2026-06-12*
