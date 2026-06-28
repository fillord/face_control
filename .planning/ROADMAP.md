# Roadmap: Face Recognition Attendance — Role & Timesheet Extension

## Overview

A brownfield Flask monolith gains four capabilities in sequence: first a secure RBAC foundation that locks down the currently-unauthenticated API surface; then an org/dept data model and migration that preserves every existing employee record; then the T-13 timesheet grid that is the core statutory deliverable; and finally Excel/CSV export plus an employee self-service cabinet. The kiosk (/, /api/recognize, /api/detect) remains permanently public throughout all phases.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: RBAC Foundation** - Secure login, 5-role system, scope filter, and protected existing API routes (completed 2026-06-11)
- [ ] **Phase 2: Org/Dept Data Model** - Org+dept structure, migration of existing employees, dashboards, and work schedules
- [x] **Phase 3: T-13 Timesheet Grid** - Symbol engine, grid view, auto-derivation from check-in data, monthly totals (completed 2026-06-13)
- [x] **Phase 4: Export & Employee Cabinet** - Excel/CSV export and employee self-service timesheet view (completed 2026-06-14)
- [x] **Phase 7: Org Admin UX Improvements** - Fix dept employee counter bug; add sortable tables; org_admin employee editing; Reports/Timesheet rendered inline; Kiosk Settings visual redesign (completed 2026-06-15)
- [x] **Phase 8: Navigation & Design Overhaul** - Dark sidebar, teal palette, Inter font, base.html shell for all authenticated pages (completed 2026-06-26)
- [x] **Phase 9: Security Hardening & Critical Bug Fixes** - Brute-force protection, CSRF, cookie flags, configurable LBPH threshold, 3 confirmed bugs fixed, /health endpoint, KZ_HOLIDAYS 2027, DB backup, composite index (completed 2026-06-26)
- [ ] **Phase 10: Superadmin Panel Extension** - Global Excel export, Employees/Devices/Logs tabs, holiday calendar management, attendance analytics chart, and superadmin role creation for dept_admin/hr_viewer

## Phase Details

### Phase 1: RBAC Foundation

**Goal**: Every protected route requires authentication; the 5-role system is active; unauthenticated users are redirected to /login; kiosk routes remain public.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, MIG-03, DASH-03
**Success Criteria** (what must be TRUE):

  1. A user with no session is redirected to /login when accessing any non-kiosk route; GET /, POST /api/recognize, and POST /api/detect remain accessible without login.
  2. Superadmin can log in with superadmin / superadmin123 immediately after first run, using the existing bcrypt hash copied from config.json — no re-hashing required.
  3. After login, each role (superadmin, org_admin, dept_admin, viewer, employee) lands on a role-appropriate dashboard; navigation shows only links relevant to that role.
  4. A dept_admin can create a viewer account; a viewer cannot create any account; privilege escalation is blocked server-side.
  5. Admin can deactivate a user account and that user's next login attempt is rejected; user can change their own password from their profile page.

**Plans**: 5 plansPlans:
**Wave 1**

- [x] 01-01-PLAN.md — Wave 0: pytest scaffold + failing end-to-end auth tests (all AUTH/MIG/DASH requirement stubs)
- [x] 01-02-PLAN.md — Wave 1: Walking Skeleton login slice — users.json store, MIG-03 bootstrap, @require_role, login redirect, /dashboard + 403.html

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-03-PLAN.md — Wave 2: Lock down all non-kiosk routes, retire @login_required, role-gate admin nav

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-04-PLAN.md — Wave 3: User management (hierarchy-scoped create/deactivate), self password change, fcntl-locked writes

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-05-PLAN.md — Wave 4: SECRET_KEY injection + single-worker PM2 config (ecosystem.config.js) [checkpoint]

**UI hint**: yes

### Phase 2: Org/Dept Data Model

**Goal**: Organizations and departments exist as structured data; all existing employees are migrated with org/dept assignment and work schedules; superadmin and org/dept_admin CRUD is functional; dashboards show live scoped data.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: ORG-01, ORG-02, ORG-03, ORG-04, MIG-01, MIG-02, T13-06, DASH-01, DASH-02, KIOSK-01
**Success Criteria** (what must be TRUE):

  1. Migration script runs without error: every existing employee gains org_id, dept_id, and schedule fields; the label integer and all other original fields are preserved; the face recognizer still trains and recognizes after migration.
  2. Superadmin can create, edit, and delete organizations; org_admin can create, edit, and delete departments within their own org; dept_admin can add and edit employees within their own department only.
  3. Superadmin dashboard shows correct system-wide totals (organizations, total employees, today's check-ins); department dashboard shows today's present, absent, and late employees scoped to the viewer's department.
  4. Each employee has a configurable work schedule (start time, end time, work days); standard Mon–Fri 8h is the default.
  5. When a face is recognized at the kiosk, the employee's department name appears on the confirmation screen alongside their name and time.

**Plans**: 5 plans
**Wave 0** *(test scaffold)*

- [x] 02-01-PLAN.md — Failing pytest scaffold + conftest extension for all 10 Phase 2 requirements (ORG/MIG/T13/DASH/KIOSK stubs)

**Wave 1** *(blocked on Wave 0)*

- [x] 02-02-PLAN.md — Data foundation: ORGS_FILE/DEPTS_FILE + load/save helpers + standalone migrate.py (MIG-01, MIG-02)

**Wave 2** *(blocked on Wave 1)*

- [x] 02-03-PLAN.md — Org/Dept CRUD with scope gates + superadmin.html & org_admin.html pages (ORG-01..04)

**Wave 3** *(blocked on Wave 2)*

- [x] 02-04-PLAN.md — Superadmin & dept dashboards + schedule PATCH + login redirect + dept_admin.html (DASH-01, DASH-02, T13-06)

**Wave 4** *(blocked on Wave 3)*

- [ ] 02-05-PLAN.md — Kiosk dept-name slice + full-phase smoke checkpoint (KIOSK-01) [checkpoint]

**UI hint**: yes

### Phase 3: T-13 Timesheet Grid

**Goal**: HR staff and dept_admins can view the statutory T-13 timesheet grid for any authorized department and month, with symbols auto-derived from face check-in data and KZ public holidays applied automatically.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: T13-01, T13-02, T13-03, T13-04, T13-05, T13-07, T13-08, DASH-04
**Success Criteria** (what must be TRUE):

  1. The T-13 grid renders employees as rows and calendar days as columns for a selected month; symbols Я, О, У, В, П, НН, Б, К appear in the correct cells based on check-in data and schedule.
  2. Kazakhstan public holidays for 2024 and 2025 are automatically marked В; weekends are automatically marked В; a work day with no check-in record is marked НН (never П by default).
  3. Late arrival (first check-in more than 15 minutes after schedule start) shows О; early departure (last check-out more than 15 minutes before schedule end) shows У; both conditions in one day are recorded in notes.
  4. Monthly totals row shows correct counts: days worked, hours worked, absences (П+НН), late arrivals (О), vacation/sick days (Б+К).
  5. Org_admin can view a per-department summary report for a selected month showing total employees and attendance rate % (days present / total work days) per department.

**Plans**: 4 plans

Plans:

**Wave 0** *(test scaffold)*

- [x] 03-01-PLAN.md — Failing/xfail pytest scaffold (T13-01..08, DASH-04, D-05, D-08) + conftest TIMESHEET_OVERRIDES_FILE guard

**Wave 1** *(blocked on Wave 0)*

- [x] 03-02-PLAN.md — Symbol engine + KZ_HOLIDAYS + /timesheet grid render slice (auto-derive Я/О/У/В/НН/ОУ, totals row, holiday banner, dept scope)

**Wave 2** *(blocked on Wave 1)*

- [x] 03-03-PLAN.md — Inline override slice: POST/DELETE /api/timesheet/override (scope + {Б,К,П} whitelist) + in-cell dropdown JS

**Wave 3** *(blocked on Wave 2)*

- [x] 03-04-PLAN.md — DASH-04 org_admin per-dept summary + KZ holiday verification + full-phase smoke [checkpoint]

**UI hint**: yes

### Phase 4: Export & Employee Cabinet

**Goal**: Authorized users can download the T-13 grid as Excel or CSV; employees can view their own attendance records and timesheet without admin access.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: EXP-01, EXP-02, EXP-03, EMP-01, EMP-02, EMP-03
**Success Criteria** (what must be TRUE):

  1. T-13 grid exports as .xlsx with merged header cells, Cyrillic column labels, and readable column widths; the file opens correctly in Excel without encoding errors.
  2. T-13 grid exports as .csv with UTF-8 BOM prefix and semicolon delimiter; Cyrillic characters display correctly when opened in Windows Excel.
  3. Export is scoped to role: dept_admin downloads their department only; org_admin downloads their entire organization; superadmin can select any org.
  4. An employee can view their own T-13 grid for the current and previous months (read-only) and see exact arrival and departure times for each day.
  5. Employee summary view shows their late arrival count, absence count, and early departure count for the current month.

**Plans**: 3 plans

Plans:

**Wave 1** *(test scaffold)*

- [x] 04-01-PLAN.md — Failing/xfail pytest scaffold (EXP-01..03, EMP-01..03) + seed_attendance conftest helper

**Wave 2** *(blocked on Wave 1)*

- [x] 04-02-PLAN.md — Export slice: openpyxl install + /timesheet/export/xlsx & /export/csv routes (T-13 layout, UTF-8 BOM, role-scoped) + Скачать buttons [checkpoint]

**Wave 3** *(blocked on Wave 2)*

- [x] 04-03-PLAN.md — Employee cabinet slice: User.emp_id + employee login, /employee rewrite, employee.html (stats cards, month clamp, read-only grid, time tooltips)

**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. RBAC Foundation | 5/5 | Complete   | 2026-06-11 |
| 2. Org/Dept Data Model | 4/5 | In Progress (02-05 superseded by Phase 5) | - |
| 3. T-13 Timesheet Grid | 4/4 | Complete   | 2026-06-13 |
| 4. Export & Employee Cabinet | 3/3 | Complete   | 2026-06-14 |
| 5. Token Kiosk, Reg & Russian UI | 5/5 | Complete | 2026-06-13 |
| 6. SQLite Migration | 4/4 | Complete | 2026-06-13 |
| 7. Org Admin UX Improvements | 5/5 | Complete   | 2026-06-15 |

### Phase 5: Token-based Kiosk, Registration & Russian UI

**Goal:** Introduce token-based kiosk and registration URLs with bcrypt-hashed PIN auth; migrate organizations.json to carry org_token, kiosk_pin, reg_token, reg_pin, reg_token_expires, kiosk_display_name; restrict users.json to superadmin/org_admin/dept_manager (employees are NOT users); rebuild all pages in Russian with МедКонтроль branding and role-scoped navigation; provide touchscreen kiosk PIN pad and mobile-friendly registration page; ship migrate.py for existing-org upgrade; absorbs Plan 02-05 (kiosk dept display).
**Requirements**:

- organizations.json: add org_token (8-char random), kiosk_pin (bcrypt, default "0000"), reg_token (8-char random), reg_pin (bcrypt, default "1234"), reg_token_expires (ISO datetime), kiosk_display_name
- Kiosk URL: /kiosk/<org_token> — touchscreen 4-digit PIN pad
- Registration URL: /register/<reg_token> — mobile-friendly, expires via reg_token_expires
- users.json roles: superadmin | org_admin | dept_manager only (employees are in employees.json, not users.json)
- employees.json: keep all fields; ensure org_id, dept_id, name, role/position, label, face_count, schedule
- All UI pages in Russian; МедКонтроль branding; role-scoped navigation (each role sees only their items)
- Headers: superadmin→"МедКонтроль — Суперадмин", org_admin→"МедКонтроль — [Org Name]", dept_manager→"МедКонтроль — [Dept Name]"
- migrate.py: update existing orgs, generate tokens, set default PINs, preserve employees and attendance data
- Post-deploy: python migrate.py && pm2 restart face-recognition
- Verify: curl http://127.0.0.1:5051/login → 200; curl http://127.0.0.1:5051/kiosk/<org_token> → 200

**Depends on:** Phase 2
**Plans:** 3/3 plans complete

Plans:

**Wave 1**

- [x] 05-01-PLAN.md — Org data model + migrate.py: org_token/reg_token/bcrypt PINs/reg_token_expires/kiosk_display_name, plaintext re-hash, idempotent migration, create_org provisioning

**Wave 2** *(blocked on Wave 1)*

- [x] 05-02-PLAN.md — Token kiosk: /kiosk/<org_token> + bcrypt verify_pin, touchscreen PIN pad (no keyboard), dept-name display (absorbs 02-05), old org_id routes removed, error_token.html

**Wave 3** *(blocked on Wave 2)*

- [x] 05-03-PLAN.md — Token registration: public /register/<reg_token> with expiry + bcrypt reg_pin + submit, mobile register_token.html, login role allowlist (AUTH-ROLE-01)

**Wave 4** *(blocked on Wave 3)*

- [x] 05-04-PLAN.md — Russian UI + МедКонтроль branding audit, role-scoped headers (Суперадмин / org name / dept name), role-only navigation

**Wave 5** *(blocked on Wave 4)*

- [x] 05-05-PLAN.md — org_admin kiosk-settings panel: change kiosk/reg PINs (bcrypt), regenerate reg_token, set/clear expiry, edit display name, live URLs; own-org scope

### Phase 6: SQLite Migration

**Goal:** Replace all JSON file stores with SQLite + Flask-SQLAlchemy. All 7 data files (employees.json, users.json, orgs.json, depts.json, attendance.json, logs.json, timesheet_overrides.json) become tables in data/app.db. Existing data migrated via migrate_to_sqlite.py. No API shape changes, no frontend changes. App passes all existing tests after migration.
**Requirements**: DB-01, DB-02, DB-03, DB-04, DB-05
**Depends on:** Phase 3
**Success Criteria** (what must be TRUE):

  1. All load_*/save_* functions replaced with SQLAlchemy ORM calls; no JSON file I/O remains in app.py except the migration script.
  2. migrate_to_sqlite.py reads existing JSON files and inserts all records into app.db with zero data loss; script is idempotent.
  3. All existing pytest tests pass against the SQLite backend without modification to test code.
  4. Concurrent writes are handled by SQLAlchemy transactions; manual fcntl locking code is removed.
  5. app.db is created automatically on first run if it does not exist; SECRET_KEY and DATABASE_URL are the only required env vars.

**Plans:** 4/4 plans executed (completed 2026-06-13)

Plans:

**Wave 0** *(schema foundation + test scaffold)*

- [x] 06-01-PLAN.md — flask-sqlalchemy install + models.py (9 ORM models, label non-autoincrement) + test_sqlite_migration.py scaffold

**Wave 1** *(blocked on Wave 0)*

- [x] 06-02-PLAN.md — wire SQLAlchemy into app.py (config, startup create_all, ORM bootstrap) + rewrite conftest.py for in-memory SQLite

**Wave 2** *(blocked on Wave 1)*

- [x] 06-03-PLAN.md — ORM rewrite of require_role + user/employee/org/dept/config routes + append_log; remove flat-entity helpers and fcntl

**Wave 3** *(blocked on Wave 2)*

- [x] 06-04-PLAN.md — ORM rewrite of attendance/recognition/timesheet routes + migrate_to_sqlite.py + .gitignore + real-data migration smoke [checkpoint]

### Phase 7: Org Admin UX Improvements

**Goal:** Fix the department employee counter bug; add sortable columns to Employees and Users tabs; allow org_admin to edit employee profiles and work schedules inline; render Reports and Timesheet T-13 content inside the org_admin layout without page navigation; and modernize the visual design of the Kiosk Settings tab.
**Mode:** mvp
**Depends on:** Phase 6
**Requirements**: ORGUX-01, ORGUX-02, ORGUX-03, ORGUX-04, ORGUX-05, ORGUX-06
**Success Criteria** (what must be TRUE):

  1. Each department row/card in the Departments tab shows the correct count of employees assigned to that department (not 0); count is derived from a live DB query at render time.
  2. The Employees tab has sortable columns (by name, department, date added); clicking a header toggles ascending/descending and shows a sort arrow; sort is client-side with no page reload.
  3. Org_admin can open an edit form for any employee in their org to modify name, department, position, and work schedule; changes persist to the database and are reflected immediately without full-page refresh.
  4. The Users tab has sortable columns (by username, role); client-side sort with toggle arrow; no page reload.
  5. Clicking "Reports" or "Timesheet T-13" in the org_admin navigation renders the relevant content inline within the org_admin page (fetched via fetch() and injected into a content panel); the browser URL does not change to /admin or /timesheet.
  6. The Kiosk Settings tab has a modernized visual design: clear section grouping, improved spacing, modern card styling consistent with the rest of the app.

**Plans**: 5 plans

Plans:

**Wave 1**

- [x] 07-01-PLAN.md — Fix dept employee counter race condition (sequential init() in org_admin.html)

**Wave 2** *(blocked on Wave 1)*

- [x] 07-02-PLAN.md — Sortable Employees and Users table columns (client-side sort with toggle arrows)

**Wave 3** *(blocked on Wave 2)*

- [x] 07-03-PLAN.md — Inline employee edit form + PATCH /api/employees/<id> expansion (name, role, scope gate)

**Wave 4** *(blocked on Wave 3)*

- [x] 07-04-PLAN.md — Inline Reports and Timesheet panels (partial routes + fetch() injection in org_admin)

**Wave 5** *(blocked on Wave 4)*

- [x] 07-05-PLAN.md — Kiosk Settings visual redesign (icon-headed cards, modern spacing)

### Phase 8: I want to radically change the navigation of the website and the design.

**Goal:** Every authenticated page renders inside a single shared `base.html` shell: a dark fixed sidebar with role-aware navigation (replacing horizontal nav-tabs), a teal accent palette replacing the old blue, Inter font, and a responsive hamburger on small screens. The kiosk and login pages stay standalone.
**Requirements**: D-01..D-16 (design decisions from 08-CONTEXT.md)
**Depends on:** Phase 7
**Plans:** 6/6 plans complete

Plans:

**Wave 1** *(foundation)*

- [x] 08-01-PLAN.md — Create base.html: CSS token system, dark sidebar, role-aware nav (6 roles), user footer, hamburger JS, content block

**Wave 2** *(blocked on Wave 1 — parallel, no file overlap)*

- [x] 08-02-PLAN.md — Convert superadmin.html (pilot tabbed page) to extend base.html
- [x] 08-03-PLAN.md — Convert org_admin.html + dept_admin.html to extend base.html
- [x] 08-04-PLAN.md — Convert admin.html + employee.html + dashboard.html to extend base.html

**Wave 3** *(blocked on Wave 1 — parallel, no file overlap)*

- [x] 08-05-PLAN.md — Convert timesheet, profile, account, audit, 403, devices, register to extend base.html
- [x] 08-06-PLAN.md — Update reports_partial.html + timesheet_partial.html CSS tokens (no extends, partials)

### Phase 9: Security Hardening & Critical Bug Fixes

**Goal:** Plug the highest-risk security gaps and fix three confirmed bugs. All items are small-effort, high-impact, grounded in the 260626-jko analysis report: brute-force protection on login and PIN endpoints; CSRF via Flask-WTF; session cookie security flags; configurable LBPH threshold in AppSetting; three hardcoded-`"09:00:00"` bugs fixed; /health endpoint; KZ_HOLIDAYS extended to 2027; DB backup button; composite index on AttendanceRecord.
**Depends on:** Phase 8
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, BUG-01, BUG-02, BUG-03, REL-01, REL-02, REL-03, PERF-01
**Plans:** 4/4 plans complete

Plans:

**Wave 1**

- [x] 09-01-PLAN.md — Critical bug fixes + reliability: schedule-aware late detection (BUG-01/02), real dept names (BUG-03), /health (REL-01), KZ_HOLIDAYS 2027 (REL-02), cookie flags (SEC-04), composite index (PERF-01)

**Wave 2** *(blocked on Wave 1 — app.py overlap)*

- [x] 09-02-PLAN.md — Flask-Limiter brute-force protection: /login 5/15min (SEC-01), verify_pin 10-attempt token lock (SEC-02) [checkpoint]

**Wave 3** *(blocked on Wave 2 — app.py overlap)*

- [x] 09-03-PLAN.md — Flask-WTF CSRF on HTML form routes, JSON /api/* exempt (SEC-03) [checkpoint]

**Wave 4** *(blocked on Wave 3 — app.py overlap)*

- [x] 09-04-PLAN.md — Configurable LBPH threshold (SEC-05) + DB backup button (REL-03) + superadmin System UI

### Phase 10: Superadmin Panel Extension

**Goal:** Superadmin gains 7 new capabilities in /superadmin: global multi-org Excel export (T-13), read-only Employees tab, Devices tab with revoke, Logs tab with filters, holiday calendar management (DB-backed, consumed by compute_symbol()), Chart.js attendance analytics, and the ability to create dept_admin/hr_viewer accounts (not only org_admin).
**Depends on:** Phase 9
**Requirements**: SADM-01, SADM-02, SADM-03, SADM-04, SADM-05, SADM-06, SADM-07
**Success Criteria** (what must be TRUE):

  1. GET /api/superadmin/export/xlsx?month=M&year=Y downloads an Excel file with one sheet per organization, each containing the T-13 grid for that month.
  2. /superadmin shows tabs: Employees (all orgs, filterable by org, read-only), Devices (all orgs, revoke button calls existing DELETE endpoint), Logs (last 500 recognition events, filter by org/event type).
  3. Holiday calendar tab: superadmin can add/delete holidays by date+name for any year; GET /api/holidays?year=YYYY returns the list; compute_symbol() uses DB holidays instead of hardcoded KZ_HOLIDAYS list.
  4. Analytics tab/section: Chart.js line chart renders % attendance per day for the last 30 days across all orgs; data served from GET /api/superadmin/attendance_stats?days=30.
  5. create_user() allows superadmin to create org_admin, dept_admin, and hr_viewer roles; when dept_admin is selected the form shows a department selector scoped to the chosen org.
  6. All new endpoints return 403 for any role other than superadmin; existing org_admin and dept_admin routes are unaffected.
  7. pm2 restart face-recognition succeeds; no import errors or startup exceptions.

**Plans**: 6 plans

Plans:

**Wave 1**

- [x] 10-01-PLAN.md — Superadmin role creation fix (org_admin/dept_admin/hr_viewer + scoped dept selector) + read-only Employees tab (SADM-07, SADM-02)

**Wave 2** *(blocked on Wave 1 — app.py + superadmin.html overlap)*

- [x] 10-02-PLAN.md — Devices tab (revoke + audit) + Logs tab (org/event filters, max 500) (SADM-03, SADM-04)

**Wave 3** *(blocked on Wave 2)*

- [x] 10-03-PLAN.md — Holiday calendar: HolidayCalendar model + DB-backed get_holidays_set + /api/holidays CRUD + Calendar tab (SADM-05)

**Wave 4** *(blocked on Wave 3)*

- [ ] 10-04-PLAN.md — Attendance analytics: /api/superadmin/attendance_stats + Chart.js line chart Analytics tab (SADM-06)

**Wave 5** *(blocked on Wave 4)*

- [ ] 10-05-PLAN.md — Global multi-org T-13 Excel export endpoint + System-tab month picker/download (SADM-01)

**Wave 6** *(blocked on Waves 1-5)*

- [ ] 10-06-PLAN.md — Full suite + clean pm2 restart + visual smoke of all 7 features [checkpoint]
