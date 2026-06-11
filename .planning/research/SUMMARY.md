# Project Research Summary

**Project:** Face Recognition Attendance System — Role & Timesheet Extension
**Domain:** Brownfield Flask monolith — RBAC + organizational hierarchy + T-13 timesheet
**Researched:** 2026-06-11
**Confidence:** HIGH

## Executive Summary

This is a brownfield extension of a working Flask + OpenCV face recognition kiosk. The extension adds a 5-level RBAC system (superadmin, org_admin, dept_admin, viewer, employee), organizational data isolation, a statutory T-13 timesheet grid, and Excel/CSV export — without touching the kiosk or replacing the JSON file storage pattern. The recommended approach is module extraction (auth.py, data_helpers.py, timesheet.py, export.py) from the existing 423-line app.py, adding two pip dependencies (flask-login, openpyxl), and enforcing data scope at a single data-helper function rather than at each route.

The most important architectural decision is: data isolation belongs entirely in `get_employees_for_user(user)` inside data_helpers.py. No route may call `load_employees()` directly in any protected context. This single function is the security boundary — every other component flows from it. The T-13 timesheet must be built as a pure function (no Flask dependency) so the same grid powers both the web view and the xlsx/csv export. The kiosk routes (`GET /`, `POST /api/recognize`, `POST /api/detect`) must remain permanently public and are the only explicit exceptions to RBAC.

The primary risks are: (1) forgetting to retrofit RBAC onto existing API endpoints during Phase 1 — these are currently unauthenticated; (2) corrupting the face recognizer's integer label field during the data migration; (3) T-13 symbol resolution being silently wrong for weekends, Kazakh public holidays, and partial months. All three are preventable with an upfront route audit and an additive-only migration strategy. JSON file storage is sufficient for clinic scale (< 50 employees) with `fcntl.flock` file locking added to all write paths.

---

## Key Findings

### Recommended Stack

The existing venv already provides Flask 3.1.3, bcrypt 5.0.0, Werkzeug 3.1.8, and gunicorn 26.0.0. Only two new packages are needed:

- **`flask-login` 0.6.3** — adds `current_user` proxy and `login_user()`/`logout_user()` helpers; Flask 3.x compatible
- **`openpyxl` 3.1.x** — T-13 xlsx generation with merged cells, cell styles, column widths; the only pure-Python xlsx library that supports merged cells (xlsxwriter is write-only)
- **`bcrypt` 5.0.0** (already installed) — do NOT reinstall; Rust backend works on Python 3.14
- **`functools.wraps`** (stdlib) — RBAC `require_role(*roles)` decorators follow the pattern already in app.py
- **`stdlib csv` + UTF-8 BOM** — `codecs.BOM_UTF8` prefix for correct Cyrillic in Windows Excel; semicolon delimiter for RU/KZ locale
- **`io.BytesIO`** (stdlib) — in-memory xlsx for `send_file()`, avoids temp files

**Do not use:** flask-principal (abandoned 2013), flask-security-too (SQLAlchemy-only), xlsxwriter (write-only), pandas (30MB overhead).

### Expected Features

The T-13 form is a statutory document under RK/RU labour law. HR cannot submit payroll without it.

**Table stakes (v1):**
- RBAC 5-role system with bcrypt and server-side data isolation
- Org + dept data model with migration of existing flat employees.json
- T-13 grid view (employees × days) with full symbol set: Я, О, В, П, Б, К, У, НН
- Auto-derive Я/absent from existing face check-in data
- Employee work schedule (standard 8h/5-day + custom)
- Monthly totals: days worked, hours, absences, vacation days, late arrivals
- Export T-13 to Excel (.xlsx) with Cyrillic layout and merged cells
- Export to CSV with UTF-8 BOM (semicolon delimiter for RU/KZ locale)
- Employee self-service cabinet (own T-13, read-only, reuses grid component)
- Viewer role: read-only dept attendance view

**Defer (v2+):** Shift/rotating schedules, PDF export, OAuth/SSO, payroll calculation (hand off to 1C via xlsx).

**Critical rule:** Never default unknown absences to П (disciplinary). Use НН (reason unknown) and let HR resolve.

### Architecture Approach

Four modules extracted from app.py without blueprints:

1. `auth.py` — RBAC decorators, session helpers, bcrypt verify, privilege escalation guard
2. `data_helpers.py` — scope filter (`get_employees_for_user`), all load/save with `fcntl.flock`, date-range attendance query
3. `timesheet.py` — pure function `build_timesheet()` returning symbol grid + totals; `resolve_symbol()` as single source of truth
4. `export.py` — `export_xlsx()` via openpyxl BytesIO, `export_csv()` via stdlib csv with UTF-8 BOM
5. `migrations/001_add_org_dept.py` — one-time additive migration; preserves all existing fields including `label`

Three new JSON files: `users.json`, `orgs.json`, `depts.json`. `employees.json` extended with `org_id`, `dept_id`, `schedule`. All kiosk globals remain in app.py and are never moved. Kiosk routes remain permanently RBAC-exempt.

### Critical Pitfalls

1. **Unprotected existing API endpoints** — `GET /api/employees`, `GET /api/attendance`, `/api/stats` etc. have zero auth today. Audit and protect every route in Phase 1 before writing any new feature code.

2. **Data isolation enforced only in UI** — All protected queries must go through `get_employees_for_user(user)`. Never trust URL query parameters (`?org=foo`) to scope data.

3. **bcrypt migration locks out existing admin** — Copy the existing bcrypt hash from `config.json` verbatim into `users.json` (do NOT re-hash). Test superadmin login immediately after migration.

4. **Employee `label` integer corrupted during migration** — Migration must be strictly additive: add fields, never remove or rename `label`, `id`, `face_count`, `name`. Post-migration: verify recognizer still trains and recognizes.

5. **T-13 symbol logic wrong for edge cases** — Implement `resolve_symbol()` as single source of truth with priority: public holiday → В (weekend) → Я (worked) → НН (unknown absence). Write unit tests for every symbol branch before building the export.

6. **JSON race conditions with multiple writers** — `fcntl.flock` advisory locking on all write paths; PM2 must run a single Flask worker (document this constraint).

---

## Implications for Roadmap

### Phase 1: RBAC Foundation and Auth Migration
**Rationale:** Existing API routes are unauthenticated — add features before securing them creates permanent vulnerabilities.  
**Delivers:** Secure 5-role login, protected existing API routes, `get_employees_for_user` scope filter, `fcntl` file locking, open redirect fix.

### Phase 2: Data Model and Migration
**Rationale:** T-13 grid requires org/dept on every employee; migration must preserve `label` integers or the kiosk breaks.  
**Delivers:** users.json, orgs.json, depts.json; employees.json extended; superadmin/org_admin/dept_admin CRUD; employee work schedules.

### Phase 3: T-13 Timesheet Grid and Symbol Engine
**Rationale:** Core product value. All data prerequisites in place. Pure-function design allows independent testing.  
**Delivers:** `build_timesheet()` + `resolve_symbol()`; T-13 grid view; auto-derivation of Я/НН from face check-in data; monthly totals.

### Phase 4: Export and Employee Self-Service
**Rationale:** Export depends on stable grid. Employee cabinet reuses grid component at minimal additional cost.  
**Delivers:** xlsx export (Cyrillic, merged cells), CSV export (UTF-8 BOM, semicolon), employee self-service cabinet.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions confirmed from installed venv dist-info |
| Features | HIGH (core) / MEDIUM (KZ-specific) | T-13 symbols are regulatory (HIGH); KZ holiday calendar needs official source verify |
| Architecture | HIGH | Based on direct codebase analysis of app.py and data file schemas |
| Pitfalls | HIGH | Derived from direct route audit confirming unauthenticated endpoints |

### Gaps to Address

- **Kazakh public holidays 2025–2026:** Verify against `egov.kz` before Phase 3; add startup warning if year has no holiday list.
- **`fcntl` single-worker constraint:** PM2 must run one Flask worker. Document in deployment config.
- **SECRET_KEY in production:** Existing hardcoded fallback must be replaced with env var before Phase 1 deployment.
- **1C:ZiK xlsx compatibility:** v2 concern — v1 export is human-readable, not machine-import optimized.

---
*Research completed: 2026-06-11*
*Ready for roadmap: yes*
