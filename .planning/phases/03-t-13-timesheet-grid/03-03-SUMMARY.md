---
phase: 03-t-13-timesheet-grid
plan: "03"
subsystem: timesheet-override-api
tags: [flask, override-api, rbac, inline-editing, scope-validation, symbol-whitelist]
dependency_graph:
  requires: ["03-02"]
  provides: ["override-api", "inline-cell-editing", "data-auto-attribute"]
  affects: ["app.py", "templates/timesheet.html"]
tech_stack:
  added: []
  patterns:
    - "scope-validated JSON API (dept_id/org_id from employees.json, not client)"
    - "symbol whitelist validation (MANUAL_SYMBOLS = {Б,К,П})"
    - "atomic JSON write with fcntl.flock + os.replace (reuse of save_timesheet_overrides)"
    - "in-place DOM cell update via JS color/title maps (SYM_BG, SYM_FG, SYM_TITLES)"
    - "data-auto HTML attribute for client-side auto-symbol restore"
key_files:
  modified:
    - app.py
    - templates/timesheet.html
decisions:
  - "Single @require_role decorator covers both POST and DELETE methods (closes T-03-delete-auth threat)"
  - "Scope read from employees.json server-side — never trust client-supplied dept_id/org_id"
  - "timesheet() route computes auto symbol in a separate compute_symbol() call (empty overrides) alongside displayed symbol so template can emit data-auto without extra route"
  - "applyOverride() updates cell DOM in-place (no page reload); restore reads data-auto attribute"
  - "Override dropdown HTML wrapped in {% if can_edit %} — read-only users receive no editing affordance in DOM"
metrics:
  duration: "268 seconds"
  completed: "2026-06-13"
  tasks_completed: 2
  files_changed: 2
---

# Phase 03 Plan 03: T-13 Override API + Inline Cell Editing Summary

**One-liner:** POST/DELETE /api/timesheet/override with server-side scope + {Б,К,П} whitelist validation; in-cell dropdown updates symbol in place via `data-auto` restore without page reload.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | POST/DELETE /api/timesheet/override with scope + symbol validation | 5050073 | app.py |
| 2 | Inline override dropdown + fetch handler + data-auto attribute | ad66a37 | app.py, templates/timesheet.html |

## What Was Built

### Task 1: `/api/timesheet/override` route (app.py)

Added `timesheet_override()` route decorated with `@require_role("dept_admin", "org_admin", "superadmin")` and `@app.route("/api/timesheet/override", methods=["POST", "DELETE"])`. One decorator covers both HTTP methods (closes T-03-delete-auth threat).

**Scope validation (T-03-privesc mitigation):**
- Reads `emp.dept_id` and `emp.org_id` from `employees.json` — never trusts client-supplied values
- dept_admin: 403 if `emp.dept_id != session["dept_id"]`
- org_admin: 403 if `emp.org_id != session["org_id"]`
- superadmin: unrestricted

**Symbol whitelist (T-03-inject mitigation):**
- POST only accepts symbols in `MANUAL_SYMBOLS = {"Б", "К", "П"}` — returns 422 otherwise
- Auto-derived symbols (Я, О, У, В, НН, ОУ) are never accepted as overrides

**DELETE branch:** removes override entry and returns `{"deleted": True}`. Uses `save_timesheet_overrides` which is already atomic (fcntl.flock + os.replace) — closes T-03-race.

### Task 2: Inline dropdown + data-auto (app.py + templates/timesheet.html)

**app.py changes:**
- `timesheet()` route now computes two symbols per cell: `sym` (with overrides applied) and `auto` (computed without overrides via second `compute_symbol()` call with empty overrides dict)
- `grid_rows` now contains `(emp_id, name, cells, totals)` where `cells` is a list of `{"sym": ..., "auto": ..., "date": ...}` dicts
- Totals computation unchanged (uses `[c["sym"] for c in cells]`)

**templates/timesheet.html changes:**
- Template iterates `cells` instead of `symbols`, reads `cell.sym`, `cell.auto`, `cell.date`
- Each cell `<td>` emits `data-auto="{{ auto if auto is not none else '' }}"` attribute
- Override dropdown HTML wrapped in `{% if can_edit %}` — read-only users receive no editing affordance
- Added `SYM_BG`, `SYM_FG`, `SYM_TITLES` JS objects mirroring server-side Jinja2 maps
- Added `updateCell(cell, sym)` function that sets textContent + background + color + title in-place
- `applyOverride()` now calls `updateCell()` instead of `window.location.reload()`
- On DELETE (restore auto): reads `cell.dataset.auto` to repaint the cell without a server round-trip

## Verification Results

```
/var/www/sites/face-almgp33/venv/bin/python -m pytest tests/test_timesheet.py -q
1 xfailed, 10 xpassed in 0.28s

/var/www/sites/face-almgp33/venv/bin/python -m pytest tests/ -q
31 passed, 4 xfailed, 25 xpassed in 21.36s
```

- `test_override_scope_403` — XPASSED (dept_admin out-of-dept → 403)
- `test_override_invalid_symbol_422` — XPASSED (symbol "Я" → 422)
- `test_timesheet_renders` — XPASSED (route renders with employee name + Итого)
- `test_timesheet_scope_isolation` — XPASSED (dept_admin param ignored, session scope enforced)
- Only `test_dash04_summary` remains xfailed — deferred to plan 03-04
- No regressions in any other test module

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| `@app.route("/api/timesheet/override"` with `methods=["POST", "DELETE"]` | PASS |
| `def timesheet_override(` present in app.py | PASS |
| `grep -c MANUAL_SYMBOLS app.py` >= 2 (defined + used) | PASS (2) |
| test_override_scope_403 passes | PASS |
| test_override_invalid_symbol_422 passes | PASS |
| `fetch('/api/timesheet/override'` in timesheet.html | PASS |
| element with id `override-dropdown` in timesheet.html | PASS |
| Four dropdown labels present | PASS |
| `grep -c "data-auto" templates/timesheet.html` >= 1 | PASS (4) |
| Override interaction wrapped in `{% if can_edit %}` | PASS |
| All previously-green tests remain green | PASS |

## Deviations from Plan

None — plan executed exactly as written.

The only implementation nuance: the plan said "use `{% if can_edit %}`" and the override dropdown was already rendered unconditionally in 03-02 (accessible only through editable cells). This plan wrapped the entire dropdown div in `{% if can_edit %}` for strict compliance.

## Known Stubs

None. All cells are wired to real data; no placeholder or mock values.

## Threat Flags

No new threat surface introduced beyond the plan's threat register. The new `/api/timesheet/override` endpoint is accounted for in the threat model (T-03-privesc, T-03-inject, T-03-delete-auth, T-03-race all mitigated).

## Self-Check: PASSED

- FOUND: .planning/phases/03-t-13-timesheet-grid/03-03-SUMMARY.md
- FOUND: commit 5050073 (feat(03-03): POST/DELETE /api/timesheet/override)
- FOUND: commit ad66a37 (feat(03-03): data-auto attribute + in-place DOM update)
