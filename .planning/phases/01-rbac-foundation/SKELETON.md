# Walking Skeleton — Face Recognition Attendance (Role & Timesheet Extension)

**Phase:** 1
**Generated:** 2026-06-11

## Capability Proven End-to-End

A user signs in with username + password (bcrypt-verified against `data/users.json`) and is routed to a role-appropriate landing page — admin roles to the existing `/admin` panel, viewer/employee to a new `/dashboard` — proving the full stack: JSON storage → bootstrap migration → bcrypt auth → Flask session → role-based routed page, served by the existing PM2-managed Flask process.

> This is a brownfield extension. The "skeleton" is not a new app scaffold — it is the thinnest end-to-end RBAC slice layered onto the existing Flask monolith without altering the public kiosk.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | Flask 3.1.3 monolith in `app.py` (no blueprints, no module split) | Project constraint (CLAUDE.md); extend in place, no framework migration (D-10) |
| Data layer | JSON files in `data/` — new `users.json` joins employees/attendance/config/logs | Project constraint: no DB migration for v1; mirror existing `load_*/save_*` helper pattern |
| User store schema | `id, username, password_hash, role, active, org_id(null), dept_id(null)` keyed by uuid4 | D-01: org_id/dept_id present-but-null now so Phase 2 populates without a schema migration |
| Auth | bcrypt 5.0.0 `checkpw`/`hashpw` (already installed) + Flask signed-cookie sessions (itsdangerous) | Project already uses bcrypt; never hand-roll hashing/cookie crypto |
| Access control | `@require_role(*allowed_roles)` decorator factory replacing `@login_required` | D-04/D-05: parameterized, three-step check (login → active → role), server-side authoritative |
| Role model | `ROLE_HIERARCHY = ['superadmin','org_admin','dept_admin','viewer','employee']`; creation rights by list index | D-02: a role creates only roles with a strictly higher index; no `parent_role` field |
| Session contents | `user_id, role, org_id, dept_id` (org_id/dept_id null in Phase 1) | D-07: Phase 2 scoping reads `session['org_id']` without touching the login handler |
| Bootstrap | `init_users()` on startup; if `users.json` absent, copy `config.json` `password_hash` verbatim into a superadmin record | D-03 / MIG-03: no re-hash, no manual migration script |
| Post-login routing | superadmin/org_admin/dept_admin → `/admin`; viewer/employee → `/dashboard` | D-08 / DASH-03 |
| Deployment target | Existing PM2 process `face-recognition`, gunicorn at `127.0.0.1:5051`, single worker `-w 1` | STATE.md single-worker constraint; `ecosystem.config.js` injects `SECRET_KEY` (ASVS V3) |
| Concurrency safety | `fcntl.flock(LOCK_EX)` around `save_users` writes | Multi-worker JSON-write race defense (RESEARCH Pitfall 3) |
| UI | Vanilla CSS/HTML in Jinja2 templates; no design system, Russian copy | UI-SPEC: Flask + Jinja2 project; reuse login.html/admin.html patterns |
| Directory layout | `app.py` (all logic), `templates/*.html`, `data/*.json`, `tests/*.py` (new) | No structural change; tests are the only new directory |

## Stack Touched in Phase 1

- [x] Project scaffold — none needed (existing Flask app); pytest test runner added (`tests/`, `pytest.ini`)
- [x] Routing — new `/dashboard`, `/profile`, `/api/users` (GET/POST), `/api/users/<id>` (PATCH); all existing non-kiosk routes re-decorated
- [x] Database — real read AND write of `data/users.json` (bootstrap write on first run; login read; create/deactivate/password-change writes)
- [x] UI — interactive user-management tab (create/deactivate via fetch to `/api/users`) and a password-change form wired to `/profile`
- [x] Deployment — `ecosystem.config.js` for PM2 with `SECRET_KEY` env + single worker; final deploy `pm2 restart face-recognition`

## Out of Scope (Deferred to Later Slices)

Explicit — these are NOT in the Phase 1 skeleton and later phases must not assume them:

- Organizations and departments as structured data (Phase 2 — ORG-01..04, MIG-01/02)
- Employee migration to org/dept + work schedules (Phase 2 — MIG-01, T13-06)
- Real dashboard data; `/dashboard` is a static placeholder in Phase 1 (Phase 2 — DASH-01/02)
- Kiosk department-name display (Phase 2 — KIOSK-01)
- T-13 timesheet grid, symbol engine, holidays (Phase 3)
- Excel/CSV export and employee self-service cabinet content (Phase 4)
- Password reset, email verification, OAuth/SSO, rate limiting/lockout (v2 — AUTH2-01/02)
- Audit log of changes, timesheet status workflow (v2)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions (JSON store, monolithic `app.py`, `@require_role`, session-carried scope):

- Phase 2: Org/Dept data model + migration; populate `session['org_id']`/`session['dept_id']`; superadmin/org/dept CRUD; live scoped dashboards; kiosk department name.
- Phase 3: T-13 timesheet grid with symbols auto-derived from check-in data + KZ holidays; monthly totals; per-department summary report.
- Phase 4: Excel/CSV export of the T-13 grid scoped to role; employee self-service cabinet (own timesheet + summary).
