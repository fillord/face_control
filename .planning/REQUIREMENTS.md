# Requirements: Face Recognition Attendance — Role & Timesheet Extension

**Defined:** 2026-06-11
**Core Value:** Department heads and HR staff can view, manage, and export attendance data for exactly the employees they are authorized to see — no more, no less.

## v1 Requirements

### Authentication

- [x] **AUTH-01**: User can log in with username and password (bcrypt verified)
- [x] **AUTH-02**: Default superadmin account (superadmin / superadmin123) created automatically on first run if users.json is absent
- [x] **AUTH-03**: Each role can create user accounts for roles one level below itself (e.g. dept_admin can create viewer and employee accounts)
- [x] **AUTH-04**: User session persists across browser refresh
- [x] **AUTH-05**: Unauthenticated requests to protected routes redirect to /login; kiosk routes (/, /api/recognize, /api/detect) remain permanently public
- [x] **AUTH-06**: User can change their own password from their profile page
- [x] **AUTH-07**: Admin can deactivate a user account without deleting it; deactivated user cannot log in

### Organizations & Departments

- [ ] **ORG-01**: Superadmin can create, edit, and delete organizations
- [ ] **ORG-02**: Org_admin can create, edit, and delete departments within their own organization
- [ ] **ORG-03**: Dept_admin can add and edit employees within their own department only
- [ ] **ORG-04**: Org_admin and superadmin can assign or reassign employees between departments

### T-13 Timesheet

- [ ] **T13-01**: T-13 grid view shows employees as rows and calendar days as columns for a selected month
- [ ] **T13-02**: Full symbol set supported: Я (present), О (late), У (left early), В (day off/weekend), П (absent no reason), НН (absent reason unknown), Б (sick leave), К (business trip)
- [ ] **T13-03**: Symbols auto-derived from face check-in data: Я if check-in exists within schedule window; НН if absent on a work day; В on weekends and Kazakhstan public holidays
- [ ] **T13-04**: Late arrival detection: if first check-in is more than 15 minutes after schedule start time, symbol is О instead of Я
- [ ] **T13-05**: Early departure detection: if last check-out is more than 15 minutes before schedule end time, symbol is У (if arrived on time) or О+У together recorded in notes
- [ ] **T13-06**: Each employee has a configurable work schedule: start time, end time, and which days of week are work days (standard 8h Mon–Fri or custom)
- [ ] **T13-07**: Monthly totals row: days worked, hours worked, absences (П+НН), late arrivals (О), vacation/sick days (Б+К)
- [ ] **T13-08**: Kazakhstan public holidays for 2024 and 2025 hard-coded; holiday dates auto-marked as В in T-13

### Export

- [ ] **EXP-01**: T-13 grid can be exported as .xlsx (openpyxl) with merged header cells, Cyrillic column labels, and proper cell widths
- [ ] **EXP-02**: T-13 grid can be exported as .csv with UTF-8 BOM prefix and semicolon delimiter for correct Cyrillic display in Windows Excel
- [ ] **EXP-03**: Export is scoped to the user's role: dept_admin exports their department only; org_admin exports their entire organization; superadmin can export any org

### Dashboards & Navigation

- [ ] **DASH-01**: Superadmin dashboard shows system-wide stats: total organizations, total employees across all orgs, total check-ins today across all orgs
- [ ] **DASH-02**: Department dashboard (visible to dept_admin and org_admin) shows today's attendance in real time: list of present employees, absent employees, and late arrivals for the department
- [x] **DASH-03**: After login, each role is redirected to their own role-appropriate dashboard; navigation menu shows only links relevant to that role
- [ ] **DASH-04**: Org_admin can view a summary report per department for a selected month: total employees, attendance rate % (days present / total work days)

### Employee Cabinet

- [ ] **EMP-01**: Employee can view their own T-13 timesheet grid for the current and previous months (read-only)
- [ ] **EMP-02**: Employee can view exact arrival and departure times for each day as logged by face recognition
- [ ] **EMP-03**: Employee can view a summary of their late arrivals, absences, and early departures for the current month

### Kiosk Enhancement

- [ ] **KIOSK-01**: When a face is recognized at the kiosk, the display shows the employee's department name alongside their name and current time

### Data Migration

- [ ] **MIG-01**: Migration script adds org_id, dept_id, and schedule fields to all existing employees and assigns them to a default organization and department; all existing fields (including label) are preserved unchanged
- [ ] **MIG-02**: Migration script verifies face recognizer label integrity post-run: every employee's label value can still be found in the trained model
- [x] **MIG-03**: Existing admin password hash is copied verbatim from config.json into users.json without re-hashing; superadmin login works immediately after migration

---

## v2 Requirements

### Timesheet Enhancements

- **T2-01**: Shift/rotating work schedules (2/2, 1/3 patterns)
- **T2-02**: Timesheet status workflow (open → submitted → locked by HR)
- **T2-03**: Audit log of manual symbol changes (who changed what, when, old value, new value)
- **T2-04**: Kazakhstan public holidays for 2026+ via configurable calendar (not hard-coded)

### Export Enhancements

- **EXP2-01**: PDF export of T-13 form
- **EXP2-02**: 1C:ZiK compatible xlsx format for payroll software import

### Reporting

- **RPT2-01**: Org_admin can export department summary report to xlsx
- **RPT2-02**: Historical trend view: attendance rate per department over multiple months

### Advanced Auth

- **AUTH2-01**: OAuth/SSO integration (Active Directory or Google Workspace)
- **AUTH2-02**: Login attempt rate limiting and lockout

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Payroll calculation | T-13 is input to 1C payroll software; this system produces the export and stops there |
| Mobile app | Web-first; mobile deferred |
| Real-time push notifications | No WebSocket infrastructure; not needed for clinic scale |
| Face re-registration from employee cabinet | Admin-only operation to prevent abuse |
| Self-service org registration | Orgs created by superadmin only; not a SaaS product |
| Video attendance | Out of scope for all versions |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| AUTH-04 | Phase 1 | Complete |
| AUTH-05 | Phase 1 | Complete |
| AUTH-06 | Phase 1 | Complete |
| AUTH-07 | Phase 1 | Complete |
| MIG-01 | Phase 2 | Pending |
| MIG-02 | Phase 2 | Pending |
| MIG-03 | Phase 1 | Complete |
| ORG-01 | Phase 2 | Pending |
| ORG-02 | Phase 2 | Pending |
| ORG-03 | Phase 2 | Pending |
| ORG-04 | Phase 2 | Pending |
| T13-01 | Phase 3 | Pending |
| T13-02 | Phase 3 | Pending |
| T13-03 | Phase 3 | Pending |
| T13-04 | Phase 3 | Pending |
| T13-05 | Phase 3 | Pending |
| T13-06 | Phase 2 | Pending |
| T13-07 | Phase 3 | Pending |
| T13-08 | Phase 3 | Pending |
| DASH-01 | Phase 2 | Pending |
| DASH-02 | Phase 2 | Pending |
| DASH-03 | Phase 1 | Complete |
| DASH-04 | Phase 3 | Pending |
| EXP-01 | Phase 4 | Pending |
| EXP-02 | Phase 4 | Pending |
| EXP-03 | Phase 4 | Pending |
| EMP-01 | Phase 4 | Pending |
| EMP-02 | Phase 4 | Pending |
| EMP-03 | Phase 4 | Pending |
| KIOSK-01 | Phase 2 | Pending |

**Coverage:**

- v1 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-11*
*Last updated: 2026-06-11 after roadmap creation — all 33 requirements mapped to phases 1–4*
