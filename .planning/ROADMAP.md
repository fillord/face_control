# Roadmap: Face Recognition Attendance — Role & Timesheet Extension

## Overview

A brownfield Flask monolith gains four capabilities in sequence: first a secure RBAC foundation that locks down the currently-unauthenticated API surface; then an org/dept data model and migration that preserves every existing employee record; then the T-13 timesheet grid that is the core statutory deliverable; and finally Excel/CSV export plus an employee self-service cabinet. The kiosk (/, /api/recognize, /api/detect) remains permanently public throughout all phases.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: RBAC Foundation** - Secure login, 5-role system, scope filter, and protected existing API routes
- [ ] **Phase 2: Org/Dept Data Model** - Org+dept structure, migration of existing employees, dashboards, and work schedules
- [ ] **Phase 3: T-13 Timesheet Grid** - Symbol engine, grid view, auto-derivation from check-in data, monthly totals
- [ ] **Phase 4: Export & Employee Cabinet** - Excel/CSV export and employee self-service timesheet view

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

- [ ] 01-04-PLAN.md — Wave 3: User management (hierarchy-scoped create/deactivate), self password change, fcntl-locked writes

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 01-05-PLAN.md — Wave 4: SECRET_KEY injection + single-worker PM2 config (ecosystem.config.js) [checkpoint]

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

**Plans**: TBD
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

**Plans**: TBD
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

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. RBAC Foundation | 3/5 | In Progress|  |
| 2. Org/Dept Data Model | 0/TBD | Not started | - |
| 3. T-13 Timesheet Grid | 0/TBD | Not started | - |
| 4. Export & Employee Cabinet | 0/TBD | Not started | - |
