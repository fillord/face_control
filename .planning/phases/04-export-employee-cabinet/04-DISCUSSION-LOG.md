# Phase 4: Export & Employee Cabinet - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 4-Export & Employee Cabinet
**Areas discussed:** Export trigger & scope, Employee cabinet layout, Arrival/departure time display

---

## Export trigger & scope

| Option | Description | Selected |
|--------|-------------|----------|
| On the timesheet page | Add Export buttons to existing /timesheet selector bar | ✓ |
| Separate export page | Dedicated /export page with its own dept/month picker | |

**User's choice:** On the timesheet page

---

| Option | Description | Selected |
|--------|-------------|----------|
| Official T-13 form layout | Merged header cells, Cyrillic labels, statutory form shape | ✓ |
| Clean tabular layout | Simple one-row header, easier to build | |

**User's choice:** Official T-13 form layout

---

| Option | Description | Selected |
|--------|-------------|----------|
| Always export what's currently visible | Reuse current dept+month selection | ✓ |
| Export with separate org selector | Extra org selector for superadmin | |

**User's choice:** Always export what's currently visible

---

| Option | Description | Selected |
|--------|-------------|----------|
| T13_[dept-name]_[YYYY-MM].xlsx | Includes dept and month | ✓ |
| tabely_[YYYY-MM].xlsx | Generic name, month only | |
| You decide | Claude picks filename pattern | |

**User's choice:** T13_[dept-name]_[YYYY-MM].xlsx

---

## Employee cabinet layout

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated new page | New employee.html with stats cards + grid | ✓ |
| Reuse timesheet.html in read-only mode | Add read-only mode to existing page | |

**User's choice:** Dedicated new page

---

| Option | Description | Selected |
|--------|-------------|----------|
| /employee IS the cabinet | Route renders full cabinet directly | ✓ |
| Dashboard + cabinet as sub-page | /employee dashboard + /employee/cabinet | |

**User's choice:** /employee IS the cabinet

---

| Option | Description | Selected |
|--------|-------------|----------|
| Stats card above the T-13 grid | 3 cards at top: Late / Absences / Early departures | ✓ |
| Below the grid in a totals section | Stats appear after grid as a summary table | |
| You decide | Claude picks layout | |

**User's choice:** Stats card above the T-13 grid

---

## Arrival/departure time display

| Option | Description | Selected |
|--------|-------------|----------|
| Tooltip on hover over T-13 cell | Symbol in cell, times on hover | ✓ |
| Separate table below the grid | Second table: Date / Check-in / Check-out / Symbol | |
| Click-to-expand row in the grid | Click reveals detail row with times | |

**User's choice:** Tooltip on hover over T-13 cell

---

## Claude's Discretion

- openpyxl cell styling (column widths, font sizes, header row heights, cell borders)
- CSV column order
- Flask `send_file` vs `make_response` for streaming exports
- User-to-Employee relationship lookup (FK or username match — read models.py)
- CSS tooltip implementation (title attribute vs CSS pseudo-element)
- Filename sanitization for special characters in dept names

## Deferred Ideas

None — discussion stayed within phase scope.
