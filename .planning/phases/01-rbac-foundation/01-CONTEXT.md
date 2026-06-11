# Phase 1: RBAC Foundation - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Secure every non-kiosk route behind authentication and a 5-role system. Add a `users.json` store, upgrade the login handler to bcrypt + users.json, define `@require_role` enforcement, and give each role a post-login destination. Kiosk routes (`GET /`, `POST /api/recognize`, `POST /api/detect`) remain permanently public. No org/dept data model yet — that's Phase 2.

</domain>

<decisions>
## Implementation Decisions

### User Store (users.json)

- **D-01:** `users.json` schema includes these fields per user: `id`, `username`, `password_hash`, `role`, `active`, `org_id` (null), `dept_id` (null). `org_id` and `dept_id` are null in Phase 1 but present so Phase 2 can populate them without a schema migration.
- **D-02:** Role hierarchy encoded as a module-level constant in `app.py`: `ROLE_HIERARCHY = ['superadmin', 'org_admin', 'dept_admin', 'viewer', 'employee']`. Hierarchy is enforced by index position — a role can only create accounts for roles with a higher index. No `parent_role` field in the user record.
- **D-03:** `users.json` bootstrap is automatic on startup. If `data/users.json` is absent: read `data/config.json`, copy the existing `password` hash verbatim into a superadmin entry (MIG-03). If `config.json` has no hash, create a default `superadmin / superadmin123` bcrypt entry. No manual migration script needed.

### Role Enforcement

- **D-04:** Access control uses a parameterized decorator `@require_role(*allowed_roles)` on each route. This extends the existing `@login_required` pattern. All existing protected routes (`/admin`, `/register`, employee APIs) are upgraded to `@require_role` in Phase 1 — `@login_required` is retired.
- **D-05:** The `@require_role` decorator performs three checks in order: (1) user is logged in, (2) account is `active: true`, (3) role is in `allowed_roles`. A failed check at step 1 redirects to `/login`. Failed checks at steps 2 or 3 render a `403 Forbidden` page. Deactivated users are sent to login, not shown 403.
- **D-06:** Unauthorized access (wrong role) renders a `403.html` template — a simple page with the error message and a "Back to dashboard" link. HTTP status code 403 is set on the response.

### Flask Session Contents

- **D-07:** After login, the session stores: `user_id`, `role`, `org_id`, `dept_id`. `org_id` and `dept_id` are null for Phase 1 users but already in session so Phase 2 scoping can read `session['org_id']` without touching the login handler.

### Post-Login Routing (DASH-03)

- **D-08:** After login, role-based redirect:
  - `superadmin` → `/admin` (existing attendance admin panel; Phase 2 replaces this)
  - `org_admin` → `/admin` (same existing panel; Phase 2 adds scoping)
  - `dept_admin` → `/admin` (same; Phase 2 adds dept scoping)
  - `viewer` → `/dashboard` (minimal placeholder page)
  - `employee` → `/dashboard` (same minimal placeholder page)
- **D-09:** `/dashboard` is a single new minimal page showing the user's name, role, and a message: "Your attendance cabinet will be available in a future update." Covers both viewer and employee in Phase 1.

### Code Structure

- **D-10:** Stay monolithic in `app.py`. Use the existing section-header convention (`# ─── Section ───────────────────`). New sections to add: `# ─── Auth: Users ──────────────────`, `# ─── Auth: RBAC ──────────────────`. No Flask blueprints, no module split.

### Claude's Discretion

- Navigation menu visibility per role (which links to show/hide in HTML templates) — Claude picks the cleanest Jinja2 approach (e.g., `{% if session.role in ['superadmin', 'org_admin'] %}`).
- User management UI for Phase 1 (creating accounts one level below) — Claude designs the form layout following existing admin UI patterns.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — Full v1 requirement list; AUTH-01 through AUTH-07, MIG-03, DASH-03 are Phase 1 scope
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, and dependency map

### Existing Codebase
- `app.py` — Single-file Flask app; existing login handler (~lines 200–250), `@login_required` decorator, `data/config.json` password check to be replaced
- `data/config.json` — Contains existing admin bcrypt hash under `password` key — must be read during `users.json` bootstrap (MIG-03)
- `templates/login.html` — Existing login form template to extend/keep
- `templates/admin.html` — Existing admin panel; becomes the Phase 1 landing for superadmin/org_admin/dept_admin

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `@login_required` decorator in `app.py` — direct model for the new `@require_role` parameterized decorator; same wrapper structure, extended with role + active checks
- `data/config.json` password hash — must be copied verbatim to users.json on first run; do not re-hash
- `templates/login.html` — reuse as-is or minimal changes for the updated login flow
- `templates/admin.html` — reuse as Phase 1 landing for admin roles; navigation items will be conditionally shown by role

### Established Patterns
- Flask `session` dict for auth state — already in use; extend with `user_id`, `role`, `org_id`, `dept_id`
- JSON load/save helpers (`load_*()` / `save_*()`) — follow same pattern for `load_users()` / `save_users()`
- Section headers `# ─── Name ───────────────────` — use for new RBAC and user management sections
- `jsonify({...}), 4XX` for API error responses — use for any new API endpoints

### Integration Points
- `/login` POST handler — replace `config.json` check with `users.json` + bcrypt lookup; store `user_id`, `role`, `org_id`, `dept_id` in session
- `/logout` — already exists; no changes needed
- All routes currently decorated with `@login_required` — upgrade to `@require_role` with appropriate role list
- Kiosk routes `GET /`, `POST /api/recognize`, `POST /api/detect` — must remain completely undecorated (public)

</code_context>

<specifics>
## Specific Ideas

- Default superadmin credentials: `superadmin / superadmin123` (per REQUIREMENTS.md AUTH-02)
- bcrypt package already installed (v5.0.0) — use it directly, no new dependency
- Kazakhstan domain context: user-facing strings can be in Russian where the UI has Russian labels (existing admin UI is Russian-language)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-RBAC Foundation*
*Context gathered: 2026-06-11*
