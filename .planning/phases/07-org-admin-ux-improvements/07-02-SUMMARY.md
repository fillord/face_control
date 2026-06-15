---
phase: 07-org-admin-ux-improvements
plan: "02"
subsystem: ui
tags: [javascript, sorting, client-side, org-admin, ux]

requires:
  - "07-01: Sequential init() race condition fix"
provides:
  - "sortEmployees(key) — client-side sort of Employees table by name, dept, or date"
  - "sortUsers(key) — client-side sort of Users table by username or role"
  - "Sortable th headers with ▲/▼ arrow indicators in Employees and Users tabs"
affects:
  - "07-org-admin-ux-improvements"

tech-stack:
  added: []
  patterns:
    - "DOM sort pattern — sort data array then re-render for Employees; sort tr DOM nodes in-place for Users"
    - "Dataset attribute pattern — data-username/data-role on tr elements enables sort without re-fetching"

key-files:
  created: []
  modified:
    - "templates/org_admin.html"

key-decisions:
  - "Employees sort mutates allEmployees array then calls renderEmployees() — consistent with existing data-driven rendering pattern"
  - "Users sort moves tr DOM nodes (tbody.appendChild) rather than re-fetching — avoids server round-trip for pure UI sort"
  - "registered_at date column added to Employees table to support date-based sorting and improve data visibility"
  - "All colspan values in Employees table updated from 4 to 5 to reflect the new date column"

patterns-established:
  - "Pattern: sort data-driven tables by mutating the array + re-rendering; sort DOM-only tables by rearranging tr nodes"

requirements-completed:
  - ORGUX-02
  - ORGUX-04

duration: ~2min
completed: 2026-06-15
---

# Phase 7 Plan 02: Sortable Columns in Employees and Users Tables Summary

**Client-side sortable column headers added to Employees and Users tabs — clicking Имя, Отдел, Дата добавл., Логин, or Роль sorts rows instantly with toggle ▲/▼ arrow indicators**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-06-15T03:17:39Z
- **Completed:** 2026-06-15T03:19:58Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `th.sortable`, `th.sortable:hover`, and `.sort-arrow` CSS classes for sortable column headers
- Added four sort state variables: `empSortKey`, `empSortAsc`, `userSortKey`, `userSortAsc`
- Implemented `sortEmployees(key)` — sorts `allEmployees` array by name/dept/date and calls `renderEmployees()`; updates arrow indicator on active column header
- Implemented `sortUsers(key)` — sorts `<tr data-username>` DOM nodes in-place by dataset attributes without re-fetching; updates arrow indicator on active column header
- Wired sortable `onclick` handlers to Employees thead: Имя, Отдел, Дата добавл. headers
- Wired sortable `onclick` handlers to Users thead: Логин, Роль headers
- Added new "Дата добавл." column to Employees table showing `registered_at.slice(0,10)` (YYYY-MM-DD)
- Added `data-username` and `data-role` attributes to Users table `<tr>` elements for DOM-based sorting
- Updated all Employees table colspan values from 4 to 5 (loading, empty, and error states)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add sort state, sortable CSS, and sortTable() helper** - `6613def` (feat)
2. **Task 2: Wire sortable headers to Employees and Users table th elements** - `179c598` (feat)

## Files Created/Modified

- `templates/org_admin.html` — Sortable Employees and Users table headers with client-side sort logic

## Decisions Made

- `sortEmployees()` mutates `allEmployees` then calls `renderEmployees()` to leverage the existing data-driven render pipeline — avoids duplicating row-building logic
- `sortUsers()` rearranges `<tr>` DOM nodes via `tbody.appendChild()` to avoid a server fetch for a purely presentational sort — the displayed data is already loaded
- `data-username` and `data-role` attributes added to each user `<tr>` at render time so `sortUsers()` can read sort keys without querying the API again
- "Дата добавл." column added alongside the sort feature since `registered_at` is the sort key — surfacing the value makes the sort behavior transparent to the user

## Deviations from Plan

**1. [Rule 1 - Bug] Fixed all Employees table colspan values (not just the empty-state td)**
- **Found during:** Task 2 implementation
- **Issue:** After adding a 5th column (Дата добавл.), the loadEmployees() error state still used colspan="4"
- **Fix:** Updated loadEmployees() catch block colspan from 4 to 5 to match the new column count
- **Files modified:** templates/org_admin.html
- **Commit:** 179c598

Otherwise: plan executed as written.

## Known Stubs

None — all sort columns read real employee/user data from existing API responses.

## Threat Flags

None — sort keys are hardcoded strings ('name', 'dept', 'date', 'username', 'role'), not user input. User data rendered through escapeHtml() as before.

## Self-Check: PASSED

- `templates/org_admin.html` modified: confirmed (git log shows 6613def, 179c598)
- `sortEmployees` present in file: confirmed
- `sortUsers` present in file: confirmed
- `empSortKey` / `userSortKey` state vars present: confirmed
- `th.sortable` CSS present: confirmed
- `emp-th-name`, `emp-th-dept`, `emp-th-date` IDs present: confirmed
- `user-th-username`, `user-th-role` IDs present: confirmed
- `data-username`, `data-role` on tr: confirmed
- `registered_at` column in renderEmployees: confirmed
- colspan="5" in Employees table: confirmed

---
*Phase: 07-org-admin-ux-improvements*
*Completed: 2026-06-15*
