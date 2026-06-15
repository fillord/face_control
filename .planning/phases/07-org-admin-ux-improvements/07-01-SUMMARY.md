---
phase: 07-org-admin-ux-improvements
plan: "01"
subsystem: ui
tags: [javascript, async, race-condition, org-admin]

requires: []
provides:
  - "Sequential init() in org_admin.html — allEmployees populated before renderDepts() runs"
  - "reassignEmployee() reloads both datasets after successful PATCH"
affects:
  - "07-org-admin-ux-improvements"

tech-stack:
  added: []
  patterns:
    - "Sequential await pattern — await A(); await B(); ensures B can read A's side-effects"

key-files:
  created: []
  modified:
    - "templates/org_admin.html"

key-decisions:
  - "Sequential awaits (await loadEmployees(); await loadDepts()) replace Promise.all to guarantee allEmployees is populated before renderDepts() reads it"
  - "reassignEmployee() success path reloads both datasets via fetch instead of mutating allEmployees in-place to keep counts accurate after reassignment"

patterns-established:
  - "Pattern: when B depends on A's side-effects, await A() then await B() — do not use Promise.all"

requirements-completed:
  - ORGUX-01

duration: 5min
completed: 2026-06-15
---

# Phase 7 Plan 01: Fix Department Employee Counter Race Condition Summary

**Sequential init() ensures allEmployees is populated before renderDepts() counts them, eliminating the zero-count race on page load**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-15T03:10:00Z
- **Completed:** 2026-06-15T03:15:22Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Fixed race condition where dept employee count always showed 0 on initial page load
- Changed `Promise.all([loadDepts(), loadEmployees()])` to sequential `await loadEmployees(); await loadDepts()` so `allEmployees` is guaranteed populated before `renderDepts()` uses it
- Fixed `reassignEmployee()` success path to reload both datasets via fetch instead of mutating `allEmployees` in-place, keeping dept counts accurate after reassignment

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix init() race condition and reassignEmployee() counter staleness** - `77b3a87` (fix)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `templates/org_admin.html` - Sequential init() and refreshed reassignEmployee() success path

## Decisions Made
- Sequential awaits chosen over Promise.all because `loadDepts()` calls `renderDepts()` internally as a side effect, and `renderDepts()` reads `allEmployees` — parallel execution meant `allEmployees` could still be `[]` when `renderDepts()` ran
- `reassignEmployee()` now reloads from server rather than mutating local state, ensuring the single source of truth is the server response

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Department counter race condition is resolved; Departments tab will show correct counts on page load
- Plan 02 and subsequent org admin UX improvements can proceed independently

---
*Phase: 07-org-admin-ux-improvements*
*Completed: 2026-06-15*
