# Phase 1: RBAC Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 1-RBAC Foundation
**Areas discussed:** User store schema, Role enforcement pattern, Phase 1 dashboards, app.py code structure

---

## User store schema

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add now (null/empty) | users.json includes org_id and dept_id fields from the start, null for Phase 1. Phase 2 populates them. Avoids a schema migration between phases. | ✓ |
| No — defer to Phase 2 | users.json has only id, username, password_hash, role, active. Phase 2 adds org_id/dept_id. Cleaner phase boundary but requires schema migration. | |

**User's choice:** Yes — add now (null/empty)
**Notes:** Avoids touching the login handler in Phase 2.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Ordered list constant in code | ROLE_HIERARCHY = ['superadmin', 'org_admin', 'dept_admin', 'viewer', 'employee'] in app.py. No schema field. | ✓ |
| parent_role field per user | Each user stores which role created them. More flexible but adds complexity. | |
| You decide | Let the planner pick. | |

**User's choice:** Ordered list constant in code
**Notes:** Simple, explicit, no extra data to maintain.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Auto on startup (if users.json missing) | On Flask startup, if users.json absent: read config.json, copy hash, create default entry. | ✓ |
| Separate migration script | Standalone Python script run manually once. | |

**User's choice:** Auto on startup
**Notes:** Zero friction for the live server — no manual step required.

---

## Role enforcement pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Parameterized decorator | @require_role('superadmin', 'org_admin') on each route. Extends existing @login_required. | ✓ |
| before_request hook | Single function checks role against ROUTE_PERMISSIONS dict. Centralized but brittle. | |
| You decide | Let the planner choose. | |

**User's choice:** Parameterized decorator
**Notes:** Explicit per-route, easy to audit. Consistent with existing @login_required convention.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Redirect to their dashboard (403-silent) | User silently sent back to their dashboard. Friendlier UX. | |
| Show a 403 error page | Render a 403 Forbidden page. Explicit, matches HTTP semantics. | ✓ |
| Redirect to /login | Treat unauthorized same as unauthenticated. | |

**User's choice:** Show a 403 error page
**Notes:** Clear feedback to the user that they're blocked, not just redirected away silently.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Combined — same decorator handles both | @require_role checks login + active + role in one pass. | ✓ |
| Separate checks | Active-status checked independently. More granular but more boilerplate. | |

**User's choice:** Combined
**Notes:** Deactivated users treated same as unauthenticated — sent to /login.

---

## Phase 1 dashboards

| Option | Description | Selected |
|--------|-------------|----------|
| Redirect to existing /admin page | Superadmin lands on existing attendance admin panel. Phase 2 replaces it. | ✓ |
| New superadmin stub dashboard | A new /dashboard/superadmin page with placeholder content. | |

**User's choice:** Redirect to existing /admin page
**Notes:** No new UI work for superadmin in Phase 1.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Same /admin page as superadmin (scoped later) | All admin-level roles see existing panel. Phase 2 adds scoping. | ✓ |
| A 'coming soon' stub page per role | Dedicated pages with placeholder content. 2 extra pages to build. | |

**User's choice:** Same /admin page for all admin roles
**Notes:** Minimal Phase 1 UI work. Scoping deferred to Phase 2 when data model exists.

---

| Option | Description | Selected |
|--------|-------------|----------|
| A minimal placeholder page | Single /dashboard page: 'Your attendance cabinet is coming in Phase 4.' Shows username and role. | ✓ |
| Redirect viewer to /admin read-only, employee to kiosk | Mixes concerns — viewer shouldn't see admin data they can't act on. | |
| Viewer and employee see 403 until Phase 4 | Can log in and change password but no dashboard. | |

**User's choice:** A minimal placeholder page
**Notes:** One simple page covers both viewer and employee in Phase 1.

---

## app.py code structure

| Option | Description | Selected |
|--------|-------------|----------|
| Stay monolithic in app.py | Everything in one file using section-header convention. Consistent. | ✓ |
| Split into modules now | Extract auth.py, models.py, blueprints etc. Cleaner at scale. | |

**User's choice:** Stay monolithic in app.py
**Notes:** Consistent with existing convention; no module-import boilerplate.

---

| Option | Description | Selected |
|--------|-------------|----------|
| user_id + role + org_id + dept_id | All four in session now. org_id/dept_id null in Phase 1 but ready for Phase 2. | ✓ |
| user_id + role only | Minimal session. Phase 2 needs to update login handler. | |
| Full user dict in session | Convenient but session bloat and stale data risk. | |

**User's choice:** user_id + role + org_id + dept_id
**Notes:** Phase 2 scoping reads session['org_id'] without touching login code.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Replace with @require_role on all existing routes | All @login_required upgraded. One consistent pattern. | ✓ |
| Keep @login_required for old routes, add @require_role for new ones | Two enforcement patterns in the codebase. | |

**User's choice:** Replace all @login_required with @require_role
**Notes:** Clean slate — retire @login_required in Phase 1.

---

## Claude's Discretion

- Navigation menu visibility per role — Jinja2 conditional approach left to planner
- User management UI design for creating accounts one level below — follow existing admin UI patterns

## Deferred Ideas

None — discussion stayed within phase scope.
