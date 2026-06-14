# Phase 4: Export & Employee Cabinet - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Two capabilities delivered together:
1. **T-13 Export** — "Export XLSX" and "Export CSV" buttons on the `/timesheet` page that download the currently displayed dept+month grid. Role-scoped: dept_admin exports their dept, org_admin exports their org, superadmin exports whatever is on screen.
2. **Employee Cabinet** — a dedicated `/employee` page (`employee.html`) where employees view their own T-13 grid for the current and previous months, see exact check-in/check-out times as tooltips on grid cells, and see summary stats (late count, absences, early departures) in cards above the grid. Read-only — no editing.

</domain>

<decisions>
## Implementation Decisions

### Export — Entry Point & Scope (EXP-01, EXP-02, EXP-03)

- **D-01:** Export buttons ("Скачать XLSX" and "Скачать CSV") live on the **existing `/timesheet` page**, added to the selector bar. No separate export page or wizard.
- **D-02:** Export is always **scoped to the currently visible grid** — whatever dept+month is selected in the timesheet selector. No additional org/dept selector on the export UI. Superadmin selects the org/dept via the existing dept selector, then clicks Export.
- **D-03:** The `.xlsx` file follows the **official T-13 form layout**: merged header cells (month name spans day columns), Cyrillic column labels (Я, О, В, etc.), employee rows, and a totals row at the bottom. Not a flat one-row-header table.
- **D-04:** Downloaded filename pattern: **`T13_[dept-name]_[YYYY-MM].xlsx`** and **`T13_[dept-name]_[YYYY-MM].csv`** (e.g., `T13_ВОП-1_2026-06.xlsx`). dept-name taken from the department's `name` field.
- **D-05:** The `.csv` file uses **UTF-8 BOM prefix** (`﻿`) and **semicolon delimiter** (`;`) for correct Cyrillic display when opened in Windows Excel.
- **D-06:** Export routes are new Flask GET routes (e.g., `/timesheet/export/xlsx` and `/timesheet/export/csv`) accepting the same `?dept_id=X&month=YYYY-MM` query params as the timesheet route. They reuse `compute_timesheet_grid()` to generate the data, then stream the file.

### Employee Cabinet — Layout & Navigation (EMP-01, EMP-02, EMP-03)

- **D-07:** The `/employee` route is **repurposed** to render a new `employee.html` template (the full employee cabinet). It no longer redirects to `dashboard.html`. An employee logs in and lands directly on their T-13 cabinet.
- **D-08:** The `employee.html` page has three sections (top to bottom):
  1. **Summary stats cards** — 3 cards: "Опоздания" (late arrivals count), "Отсутствия" (П+НН count), "Ранний уход" (early departure count) for the current month.
  2. **Month selector** — a `<form method="GET">` with a `<input type="month">` restricted to current and previous month only (no arbitrary historical access). Default: current month.
  3. **T-13 grid** — read-only; same symbol display as the timesheet page but no edit controls, no dept selector (employee sees only their own row rendered as a full grid — or the grid with just their row).
- **D-09:** The T-13 grid in the employee cabinet shows **one employee's row** for the selected month, with all 31 day columns and the totals row at the bottom. Same symbol set and visual style as the admin timesheet.
- **D-10:** The employee cabinet is scoped server-side: the route reads `session['user_id']` → looks up the linked `Employee` record via `User.emp_id` (or equivalent FK) → renders only that employee's data. Any URL manipulation to see another employee returns 403.

### Arrival/Departure Time Display (EMP-02)

- **D-11:** Exact check-in and check-out times appear as a **tooltip on hover** over each day cell in the employee cabinet's T-13 grid. Tooltip text: `"Приход: HH:MM / Уход: HH:MM"` (or `"Приход: HH:MM / Уход: —"` if no check-out recorded). No separate table for times.
### Claude's Discretion

- Exact `openpyxl` cell styling (column widths, font sizes, header row heights, cell borders) — Claude follows standard T-13 form proportions and uses openpyxl's `MergedCell`, `Alignment`, and `Font` APIs.
- CSV column order — Claude matches the xlsx column order (employee name, then day 1…31, then totals).
- Flask `send_file` vs `make_response` for streaming the export file — Claude picks the pattern that works cleanly with Flask 3.x and BytesIO.
- Whether to link `User` to `Employee` via a FK column `emp_id` on `User` (may already exist from Phase 1/2) or via username match — Claude reads `models.py` and uses the existing relationship.
- Tooltip implementation: `title` attribute on `<td>` vs CSS tooltip (`:hover::after`) — Claude picks the approach that fits existing CSS patterns in `timesheet.html`. [informational]

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements

- `.planning/REQUIREMENTS.md` — EXP-01, EXP-02, EXP-03, EMP-01, EMP-02, EMP-03 (Phase 4 scope); read full text for each
- `.planning/ROADMAP.md` — Phase 4 goal, success criteria, and phase boundary

### Prior Phase Decisions

- `.planning/phases/03-t-13-timesheet-grid/03-CONTEXT.md` — D-01 through D-13 (symbol engine, grid routing, totals row, data isolation pattern); the export reuses `compute_timesheet_grid()` and `compute_employee_totals()` defined here
- `.planning/phases/01-rbac-foundation/01-CONTEXT.md` — `@require_role` decorator, session fields (`user_id`, `role`, `org_id`, `dept_id`), 403 handling
- `.planning/phases/06-sqlite-migration/06-CONTEXT.md` — ORM model classes (`Employee`, `User`, `Organization`, `Department`, `AttendanceRecord`, `TimesheetOverride`), `db.session` usage patterns, no more `load_*/save_*` helpers

### Existing Codebase

- `app.py` — `compute_timesheet_grid()` (line 316) and `compute_employee_totals()` (line 296): reuse these functions for both export and employee cabinet. `@require_role` decorator. `/timesheet` route (line 868) as the model for the export routes.
- `templates/timesheet.html` — visual reference for grid styling, CSS variables, selector bar layout; `employee.html` should match the same design language
- `data/app.db` — SQLite DB (post Phase 6); queries via `AttendanceRecord.query`, `Employee.query`, `TimesheetOverride.query`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `compute_timesheet_grid(year, month_num, scoped_employees, attendance, overrides, holidays_set)` — builds the full grid rows and totals; pass a single-employee list to get the employee cabinet grid
- `compute_employee_totals(symbols, schedule)` — computes days worked, hours, absences, late, early departure counts; drives the stats cards in the employee cabinet
- `@require_role("employee")` decorator — already on the `/employee` route; keeps the server-side isolation gate in place
- `timesheet.html` CSS: `.selector-bar`, `.table-card`, `.sym-cell`, `.btn-primary` — reuse these classes in `employee.html` for visual consistency

### Established Patterns

- Export as Flask GET route with query params → `send_file()` / `make_response()` with `Content-Disposition: attachment`
- `<form method="GET">` for selector submission (server-render pattern; no AJAX for grid)
- `session['role']`, `session['dept_id']`, `session['org_id']` for server-side scoping
- `openpyxl` is available in the venv (listed in REQUIREMENTS.md as available via pip)

### Integration Points

- `/timesheet` page: add "Скачать XLSX" and "Скачать CSV" buttons to the existing `.selector-bar`; buttons submit GET to new export routes with same params
- New routes: `GET /timesheet/export/xlsx` and `GET /timesheet/export/csv` — accept `?dept_id=X&month=YYYY-MM`, enforce role-scoped access, return file download
- `/employee` route (line 729): replace `render_template("dashboard.html", ...)` with `render_template("employee.html", ...)` and pass the employee's grid data, stats, and selected month
- New template: `templates/employee.html` — follows the same header/layout pattern as `timesheet.html`

</code_context>

<specifics>
## Specific Ideas

- The "Скачать XLSX" and "Скачать CSV" buttons should be visually distinct from the "Показать" (apply filter) button — perhaps outlined/secondary style vs. the primary blue, so the download action is recognizable.
- The T-13 xlsx header should span: Row 1 = "ТАБЕЛЬ УЧЁТА РАБОЧЕГО ВРЕМЕНИ (Форма Т-13)", Row 2 = org name + dept name + month/year, then the employee rows. Standard statutory form structure.
- Employee cabinet month selector: the `<input type="month">` should have `min` and `max` attributes set server-side to restrict to current and previous month only.
- Stats cards use the same `#1565C0` blue accent; display integer counts (no decimals).
- Filename sanitization: replace spaces and special chars in dept name with underscores for the download filename (e.g., `ВОП_1` not `ВОП-1` if dashes cause issues — Claude picks what works cleanly across OS).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 4-Export & Employee Cabinet*
*Context gathered: 2026-06-13*
