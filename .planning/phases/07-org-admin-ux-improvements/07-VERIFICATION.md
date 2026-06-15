---
phase: 07-org-admin-ux-improvements
verified: 2026-06-15T06:00:00Z
status: human_needed
score: 12/13 must-haves verified
overrides_applied: 0
gaps: []
human_verification:
  - test: "Open /org_admin as org_admin user — click Настройки киоска tab and confirm three visually distinct cards render: Ссылки и регистрация (🔗), PIN-коды (🔑), Название на экране киоска (🏥)"
    expected: "Three cards with icon badges, bottom-border header separators, rounded corners, and proper box-shadow"
    why_human: "Visual layout quality and CSS rendering cannot be verified by grep"
  - test: "Click Имя header in Сотрудники tab — rows sort A→Z; click again → Z→A; ▲/▼ indicator appears on active column"
    expected: "Client-side sort toggles ascending/descending with no page reload; arrow indicator updates"
    why_human: "Runtime JS sort behavior and indicator toggling are not verifiable statically"
  - test: "Click Изменить on any employee row — edit panel opens with pre-filled ФИО, Должность, Отдел, schedule; edit name and click Сохранить — row updates immediately"
    expected: "Panel shows current values; save triggers PATCH /api/employees/<id> then /api/employees/<id>/schedule; list reloads"
    why_human: "End-to-end inline edit requires a live session and DB"
  - test: "Click Отчёты in nav — reports content loads inline, URL stays at /org_admin; click Табель Т-13 — timesheet grid loads inline with org-scoped dept selector"
    expected: "No navigation to /admin or /timesheet; both panels render actual content from partial routes"
    why_human: "fetch() injection into innerHTML requires a browser with live session to verify"
  - test: "As org_admin, switch away from Табель Т-13 then switch back — confirm panel does NOT reload (cached); then change dept/month selector and click Показать табель — confirm updated grid appears (WR-01)"
    expected: "Second tab switch reuses cached content; form submit updates the injected content (WR-01 cache bug may block this)"
    why_human: "Cache-invalidation behavior on tsSubmitForm() requires runtime interaction"
---

# Phase 7: Org Admin UX Improvements — Verification Report

**Phase Goal:** Fix the department employee counter bug; add sortable columns to Employees and Users tabs; allow org_admin to edit employee profiles and work schedules inline; render Reports and Timesheet T-13 content inside the org_admin layout without page navigation; and modernize the visual design of the Kiosk Settings tab.

**Verified:** 2026-06-15T06:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Each department row shows the correct employee count (not 0); derived from live data at render time | VERIFIED | `renderDepts()` at line 464 computes `allEmployees.filter(e => e.dept_id === dept.id).length`; `init()` at lines 418–419 awaits `loadEmployees()` before `loadDepts()` — `allEmployees` is guaranteed populated before `renderDepts()` reads it; `Promise.all` is absent from `init()` |
| SC-2 | Employees tab has sortable columns (name, department, date added); clicking header toggles asc/desc with sort arrow; client-side only | VERIFIED | `sortEmployees(key)` function at line 925; `empSortKey`/`empSortAsc` state vars at lines 411–412; sortable `<th>` with `id="emp-th-name"`, `id="emp-th-dept"`, `id="emp-th-date"` and `onclick` handlers at lines 391–394; `.sort-arrow` span elements with ▲/▼ toggle at lines 957–958 |
| SC-3 | Org_admin can open edit form for any employee, modify name/dept/position/schedule; changes persist to DB; reflects immediately without full-page refresh | VERIFIED | `editEmpPanel` div at line 344; `startEditEmp()`/`cancelEmployeeEdit()`/`saveEmployeeEdit()` functions at lines 640–720; PATCH `/api/employees/<emp_id>` accepts `name` and `role` (lines 2155, 2174, 2176 in app.py); org scope gate at line 2149; dual-PATCH save (profile then schedule) in `saveEmployeeEdit()` |
| SC-4 | Users tab has sortable columns (username, role); client-side sort with toggle arrow; no page reload | VERIFIED | `sortUsers(key)` function at line 962; `userSortKey`/`userSortAsc` state vars at lines 413–414; sortable `<th>` with `id="user-th-username"`, `id="user-th-role"` at lines 317–318; `data-username` and `data-role` attributes on user `<tr>` elements at line 867 |
| SC-5 | Clicking Reports or Timesheet T-13 in org_admin nav loads content inline; browser URL stays at /org_admin | VERIFIED | Nav items converted to `<span onclick="switchTab('reports')">` and `<span onclick="switchTab('timesheet')">` at lines 88–89; `switchTab()` extended with `'reports'` and `'timesheet'` at line 424; `loadInlinePanel()` function at line 999; `panelReports`/`panelTimesheet` divs at lines 331–339; partial routes `/org_admin/partial/reports` and `/org_admin/partial/timesheet` at lines 1572–1582 in app.py |
| SC-6 | Kiosk Settings tab has modernized visual design with clear section grouping, improved spacing, modern card styling | UNCERTAIN | Code verified: 3 `.settings-card` blocks present (lines 153, 196, 221); `.settings-card`, `.settings-card-header`, `.settings-card-icon` CSS classes at lines 56–59; all 11 required element IDs present; all 7 JS function references intact — visual quality requires human review |

**Score: 12/13 truths verified** (SC-6 is UNCERTAIN pending human visual check)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `templates/org_admin.html` | Sequential `init()` — `await loadEmployees()` before `await loadDepts()` | VERIFIED | Lines 417–419: `async function init() { await loadEmployees(); await loadDepts(); }` — `Promise.all` absent from init body |
| `templates/org_admin.html` | `sortEmployees()` + `sortUsers()` + sortable `th` headers with ▲/▼ | VERIFIED | Both functions present; all 5 sortable header IDs present; `.sort-arrow` CSS and spans wired |
| `templates/org_admin.html` | `saveEmployeeEdit()` + `editEmpPanel` with form fields | VERIFIED | All form elements present: `editEmpName`, `editEmpDept`, `editEmpStart`, `editEmpEnd`, `editEmpDays`, `editEmpError`; all 3 JS functions present |
| `app.py` | PATCH `/api/employees/<emp_id>` accepts `name`, `role`; org scope gate | VERIFIED | `allowed_keys` whitelist at line 2155 includes `"name"` and `"role"`; scope gate at line 2149 returns 403 if `emp.org_id != caller_org_id` |
| `templates/reports_partial.html` | HTML fragment with Chart.js CDN, `panelJournal`, no DOCTYPE/html/body | VERIFIED | File exists; no DOCTYPE/html/body tags; Chart.js CDN at line 1; `panelJournal` div at line 67 |
| `templates/timesheet_partial.html` | HTML fragment with `tabelle-t13`, `.selector-bar`, no DOCTYPE/html/body | VERIFIED | File exists; no DOCTYPE/html/body tags; `tabelle-t13` table at line 133; `.selector-bar` at line 49 |
| `app.py` | `GET /org_admin/partial/reports` and `GET /org_admin/partial/timesheet` routes | VERIFIED | Both routes at lines 1572–1581 and 1582+; both decorated `@require_role("org_admin", "superadmin")` |
| `templates/org_admin.html` | `panelReports`/`panelTimesheet` divs + `loadInlinePanel()` + updated nav | VERIFIED | `loadInlinePanel()` at line 999; `_inlinePanelLoaded` cache at line 997; both panel divs at lines 331–339; nav spans at lines 88–89 |
| `templates/org_admin.html` | `panelSettings` redesigned with 3 `.settings-card` blocks, "Ссылки и регистрация" section | VERIFIED | 3 cards present (lines 153, 196, 221); "Ссылки и регистрация" heading at line 156; all required IDs preserved |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `init()` | `renderDepts()` reads populated `allEmployees` | `await loadEmployees()` before `await loadDepts()` | WIRED | Lines 418–419: sequential awaits guarantee ordering |
| `reassignEmployee()` success | both datasets reloaded | `await loadEmployees(); await loadDepts()` | WIRED | Lines 736–739: reloads both on success path |
| Employees `th` headers | `sortEmployees(key)` | `onclick="sortEmployees('name')"` etc. | WIRED | Lines 391–394: all 3 sortable headers wired |
| Users `th` headers | `sortUsers(key)` | `onclick="sortUsers('username')"` etc. | WIRED | Lines 317–318: both sortable headers wired |
| `sortUsers()` | DOM row sort | `data-username`/`data-role` attributes on `<tr>` | WIRED | Line 867: `<tr data-username="..." data-role="...">` |
| `startEditEmp()` | `editEmpPanel` visibility | `.hidden` class remove on `editEmpPanel` | WIRED | Line 660 |
| `saveEmployeeEdit()` | `PATCH /api/employees/<id>` | `fetch()` with `method: 'PATCH'` | WIRED | Line 694: `fetch(\`/api/employees/${empId}\`, {method: 'PATCH'})` |
| `saveEmployeeEdit()` | `PATCH /api/employees/<id>/schedule` | second `fetch()` call | WIRED | Line 706: `fetch(\`/api/employees/${empId}/schedule\`, {method: 'PATCH'})` |
| Отчёты nav span | `loadInlinePanel('reports')` | `switchTab('reports')` → `loadInlinePanel(tab)` | WIRED | Lines 88, 424, 432 |
| `loadInlinePanel()` | `reports_partial.html` | `fetch('/org_admin/partial/reports')` → `innerHTML` | WIRED | Lines 1004, 1011 |
| `panelSettings` buttons | JS handlers | `onclick="saveExpiry()"` etc. | WIRED | All 7 JS function onclick references confirmed present |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `renderDepts()` dept counter | `allEmployees` array | `await fetch('/api/employees')` in `loadEmployees()` → SQLAlchemy `Employee.query.all()` | Yes — real DB query | FLOWING |
| `saveEmployeeEdit()` → `PATCH /api/employees/<id>` | `emp.name`, `emp.role`, `emp.dept_id` | `request.json`, validated, persisted via `db.session.commit()` at app.py line ~2178 | Yes — real DB write | FLOWING |
| `sortEmployees()` | `allEmployees` | Same as above — already in memory from `loadEmployees()` | Yes | FLOWING |
| `loadInlinePanel('reports')` → `reports_partial.html` | Attendance data loaded by `rLoadData()` via `/api/attendance` | `/api/attendance` queries `AttendanceRecord` ORM | Yes — real DB query | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `init()` is sequential (no `Promise.all`) | `python3 -c "content=open('templates/org_admin.html').read(); lines=content.split('\n'); i=next(j for j,l in enumerate(lines) if 'async function init()' in l); e=next(j for j,l in enumerate(lines) if j>i and l.strip()=='}'); body='\n'.join(lines[i:e]); assert 'Promise.all' not in body; print('PASS')"` | PASS | PASS |
| `sortEmployees` and `sortUsers` present | `grep -c 'sortEmployees\|sortUsers' templates/org_admin.html` | 16 matches | PASS |
| Partial templates exist with correct content markers | `python3 -c "..." (see Step 4 checks)` | `reports_partial.html`: panelJournal FOUND, Chart.js FOUND; `timesheet_partial.html`: tabelle-t13 FOUND | PASS |
| All 11 settings IDs present | Python assert loop | All 11 IDs FOUND | PASS |
| Partial routes in app.py | `grep 'org_admin_partial' app.py` | Both routes found at lines 1574, 1583 | PASS |

---

### Probe Execution

Step 7c: SKIPPED — no probe-*.sh files defined for Phase 7; phase is UI/API enhancement, not a migration with probes.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ORGUX-01 | 07-01 | Fix dept employee counter race condition | SATISFIED | Sequential `init()` at lines 418–419; `allEmployees` populated before `renderDepts()` runs |
| ORGUX-02 | 07-02 | Sortable Employees table columns | SATISFIED | `sortEmployees()` function + sortable `th` headers + ▲/▼ arrows |
| ORGUX-03 | 07-03 | Org_admin inline employee edit (name, dept, position, schedule) | SATISFIED | `editEmpPanel`, `saveEmployeeEdit()`, PATCH route expansion with scope gate |
| ORGUX-04 | 07-02 | Sortable Users table columns | SATISFIED | `sortUsers()` function + sortable `th` headers + `data-*` attrs on `<tr>` |
| ORGUX-05 | 07-04 | Reports and Timesheet inline in org_admin layout | SATISFIED | Partial routes + `loadInlinePanel()` + panel divs + nav spans |
| ORGUX-06 | 07-05 | Kiosk Settings visual redesign | PARTIALLY SATISFIED | Code verified (3 cards, CSS classes, all IDs preserved); visual rendering requires human check |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app.py` | 2176 | `emp.role = update_data["role"]` — no whitelist validation on value | WARNING | Arbitrary string (including misleading values) accepted as employee position; also creates stored XSS risk if `emp.role` is ever rendered unescaped (currently escaped via `rEscapeHtml` in reports_partial, but no server-side guard) — flagged as CR-01 in 07-REVIEW.md |
| `app.py` | 1574–1578 | `org_admin_partial_reports()` does not pass `creatable_roles` to template | WARNING | `reports_partial.html` uses `{% for role_key, role_label in creatable_roles %}` inside `{% if session.role == 'superadmin' %}`; Jinja2 default Undefined iterates as empty (no 500), but the "Create User" panel renders with an empty role dropdown for superadmin — nonfunctional UX |
| `templates/timesheet_partial.html` | ~221 | `tsSubmitForm()` does not reset `_inlinePanelLoaded['timesheet']` | WARNING | After first timesheet load, switching away and back calls `loadInlinePanel()` which sees `_inlinePanelLoaded['timesheet'] === true` and returns immediately — showing stale content instead of re-fetching; flagged as WR-01 in 07-REVIEW.md |
| `templates/org_admin.html` | 587 | `loadEmployees()` catch block uses `colspan="5"` while table has 6 columns | INFO | Minor visual glitch in error state only — empty row occupies one fewer column than table |
| `templates/reports_partial.html` | ~325, ~413 | `rLoadData()` and `rLoadStats()` have no try/catch | WARNING | Network errors produce unhandled promise rejections and leave table in "Загрузка..." state with no user feedback — flagged as WR-02 in 07-REVIEW.md |

No `TBD`, `FIXME`, or `XXX` debt markers found in modified files.

---

### Human Verification Required

#### 1. Kiosk Settings Visual Design (SC-6)

**Test:** Open /org_admin as org_admin user and click "Настройки киоска" tab
**Expected:** Three distinct cards visible: "Ссылки и регистрация" (🔗), "PIN-коды" (🔑), "Название на экране киоска" (🏥); each card has icon badge, bottom-border header separator, 14px border-radius, subtle box-shadow; layout is consistent with rest of org_admin page
**Why human:** CSS rendering and visual design quality cannot be verified by grep

#### 2. Client-Side Sort Behavior — Employees and Users Tables

**Test:** Click "Имя" header in Сотрудники tab → rows sort A→Z, ▲ appears; click again → Z→A, ▼ appears; click "Отдел" header → grouping by dept name; click "Дата добавл." → sort by date; switch to Пользователи tab and repeat for Логин and Роль
**Expected:** Instant client-side sort with no page reload; arrow indicator moves to active column; toggle works correctly
**Why human:** Runtime JS execution and DOM manipulation require browser interaction

#### 3. Inline Employee Edit — End-to-End

**Test:** As org_admin, click "Изменить" on an employee row; confirm pre-filled form (name, position, dept, schedule); change name; click "Сохранить"; verify row updates without page reload; check DB: `sqlite3 data/app.db "SELECT name FROM employee WHERE id='<id>'"` shows new value
**Expected:** Form opens with current values; save triggers two PATCH calls; table reloads with updated data
**Why human:** Requires live session, DB, and browser interaction

#### 4. Inline Reports and Timesheet — Functional Test

**Test:** Click "Отчёты" nav tab → content loads inline (attendance journal table renders, URL stays at /org_admin); click "Табель Т-13" → T-13 grid loads with org-scoped department selector; click another tab → panel hides; click "Отчёты" again → served from cache (no network request)
**Expected:** URL does not change; panels render actual content; cache prevents double-fetch
**Why human:** fetch()-injected HTML and script re-execution require browser runtime

#### 5. Timesheet Cache Invalidation After Form Submit (WR-01 Regression)

**Test:** Load Timesheet tab → grid appears; change month selector → click "Показать табель"; switch to another tab; switch back to Timesheet
**Expected (concern):** Switching back after a form submit should show the last submitted month's data — WR-01 notes that `_inlinePanelLoaded['timesheet']` is never cleared by `tsSubmitForm()`, so switching away and back may show the originally-loaded month's grid, not the form-submitted one
**Why human:** Cache state across tab switches requires interactive session to reproduce

---

### Open Issues From Code Review (07-REVIEW.md)

The following issues from the existing code review are not blockers for the phase goal but should be tracked:

- **CR-01** (WARNING): `PATCH /api/employees/<emp_id>` — `role` field has no value whitelist; any string accepted as employee position. Fix: add `ALLOWED_EMP_POSITIONS` set.
- **WR-01** (WARNING): `tsSubmitForm()` in `timesheet_partial.html` does not reset `_inlinePanelLoaded['timesheet']`; switching away from Timesheet tab after a form re-submit and back shows stale content.
- **WR-02** (WARNING): `rLoadData()` and `rLoadStats()` in `reports_partial.html` have no error handling; network errors leave UI in "Загрузка..." state.
- **WR-05** (WARNING — pre-existing): `/api/attendance` returns all employees regardless of caller role; org isolation gap not introduced by Phase 7 but surfaced by it.
- **IN-03** (INFO): `org_admin_partial_reports()` does not pass `creatable_roles` to template; superadmin sees empty role dropdown in the injected Create User panel.

---

### Gaps Summary

No code-level blockers found. All artifacts exist, are substantive, and are wired correctly. The only UNCERTAIN item (SC-6 — visual design) requires human confirmation of CSS rendering quality. The WR-01 cache bug is a functional issue for the Timesheet filter form but does not prevent the core goal of loading content inline.

---

_Verified: 2026-06-15T06:00:00Z_
_Verifier: Claude (gsd-verifier)_
