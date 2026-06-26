---
phase: 09-security-hardening-and-critical-bug-fixes
plan: "04"
subsystem: recognition-config + backup
tags: [security, configurable-threshold, backup, superadmin, lbph, sqlite]
dependency_graph:
  requires: ["09-03"]
  provides: ["lbph_threshold-setting", "superadmin-system-ui"]
  affects: ["app.py", "templates/superadmin.html", "templates/base.html"]
tech_stack:
  added: []
  patterns: ["AppSetting-bootstrap", "superadmin-PATCH-route", "send_file-attachment", "server-side-template-var"]
key_files:
  created: []
  modified:
    - app.py
    - templates/superadmin.html
    - templates/base.html
decisions:
  - "Threshold passed server-side to superadmin.html template (lbph_threshold variable) rather than via separate GET fetch — avoids extra round-trip and keeps code minimal"
  - "GET /api/backup/db uses send_file directly (no streaming) per D REL-03 since file is small"
  - "saveThreshold() JS function shows inline status message rather than toast to keep UI self-contained"
metrics:
  duration: "~12 minutes"
  completed: "2026-06-26"
  tasks_completed: 3
  files_modified: 3
---

# Phase 09 Plan 04: Configurable LBPH Threshold + DB Backup Summary

**One-liner:** Superadmin-configurable LBPH recognition threshold (50–120, default 80) read at request time from AppSetting, plus a superadmin-only dated DB backup download, both surfaced in a new "Система" tab in the superadmin panel.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1+2 | Configurable LBPH threshold (SEC-05) + DB backup route (REL-03) | ad6aa0b | app.py |
| 3 | Superadmin System UI — threshold input + backup button | 97670b5 | app.py, templates/superadmin.html, templates/base.html |

## What Was Built

### Task 1: Configurable LBPH Threshold (SEC-05)

- `init_config()` now bootstraps `AppSetting(key="lbph_threshold", value="80")` if absent, committed with a separate guard after the existing password_hash bootstrap.
- `recognize()` reads `AppSetting.filter_by(key="lbph_threshold").first()` at request time and computes `threshold = int(setting.value) if setting and str(setting.value).isdigit() else 80`. Both `conf_pct` computation and `if confidence > threshold:` use this dynamic value. No process restart required for changes to take effect.
- `PATCH /api/settings/lbph_threshold` decorated `@require_role("superadmin")`: validates `isinstance(value, int)` and `50 <= value <= 120`, upserts the AppSetting row, returns `{"status": "updated", "value": <int>}`. Invalid values return 400 with a Russian error message.

### Task 2: DB Backup Download (REL-03)

- `GET /api/backup/db` decorated `@require_role("superadmin")`: resolves db path via `os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "app.db")`, returns `send_file(...)` with `as_attachment=True` and `download_name=f"app_backup_{date.today()}.db"`. Returns 404 JSON if file missing. Unauthenticated access redirects to login (302).

### Task 3: Superadmin System UI

- `superadmin_page()` extended: `VALID_TABS` now includes `"system"`, and `lbph_threshold` integer is queried and passed as a template variable.
- `templates/base.html`: Added `<a href="/superadmin/system" ...>Система</a>` nav link in the superadmin nav block.
- `templates/superadmin.html`: New `#panelSystem` hidden tab panel with:
  - A number input (`min=50 max=120`) pre-populated with `{{ lbph_threshold|default(80) }}`
  - `saveThreshold()` async JS function that PATCHes `/api/settings/lbph_threshold` and shows inline success/error message
  - A "Скачать резервную копию БД" button using `window.location='/api/backup/db'`
  - `switchTab()` updated to toggle `#panelSystem` visibility

## Verification

- `grep -c 'lbph_threshold' app.py` → 7 (bootstrap, filter_by, route path, route decorator, query.get in PATCH, upsert, template render call)
- `grep -c 'confidence > 80' app.py` → 0 (literal threshold fully removed)
- Bootstrap verified: `lbph_threshold` value `"80"` present after `init_config()` runs
- Route guard verified: unauthenticated PATCH `/api/settings/lbph_threshold` returns 302
- Backup route guard verified: unauthenticated GET `/api/backup/db` returns 302
- `import app` exits cleanly with `SECRET_KEY` set
- `/superadmin/system` returns 302 (redirect to login for unauthenticated — correct)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All UI elements are wired to live API routes. The threshold input is pre-populated from the database value at page render time.

## Threat Flags

No new security surface beyond what is documented in the plan's threat model:

| Flag | File | Description |
|------|------|-------------|
| threat_flag: information_disclosure | app.py GET /api/backup/db | Exposes entire SQLite DB — mitigated by @require_role("superadmin") per T-09-10 |
| threat_flag: elevation_of_privilege | app.py PATCH /api/settings/lbph_threshold | Alters recognition strictness — mitigated by @require_role("superadmin") + 50–120 validation per T-09-09 |

Both threats are in-scope and mitigated per the plan's STRIDE register.

## Self-Check: PASSED

- [x] `app.py` modified and committed at ad6aa0b and 97670b5
- [x] `templates/superadmin.html` modified and committed at 97670b5
- [x] `templates/base.html` modified and committed at 97670b5
- [x] `lbph_threshold` bootstrapped and reads `"80"` at runtime
- [x] No literal `confidence > 80` remains in app.py
- [x] Route guards confirmed (302 on unauthenticated access)
- [x] `import app` exits clean
