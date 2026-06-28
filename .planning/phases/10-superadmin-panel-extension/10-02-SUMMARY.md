---
phase: 10-superadmin-panel-extension
plan: "02"
subsystem: superadmin-panel
tags: [rbac, superadmin, devices, logs, audit, frontend, backend, api]
dependency_graph:
  requires:
    - superadmin_employees (GET /api/superadmin/employees) — from plan 10-01
    - KioskDevice ORM model
    - LogEntry ORM model
    - write_audit() helper
    - escapeHtml JS helper in superadmin.html
    - switchTab / lazy-load tab pattern — from plan 10-01
  provides:
    - superadmin_devices (GET /api/superadmin/devices)
    - superadmin_logs (GET /api/superadmin/logs)
    - write_audit("device_revoke") in revoke_kiosk_device()
    - panelDevices tab with loadDevices / renderDevices / revokeDevice JS
    - panelLogs tab with loadSuperLogs / renderSuperLogs / filterLogs JS
    - logsOrgFilter / logsEventFilter client-side filters
    - Устройства and Логи nav links in base.html superadmin sidebar
  affects:
    - app.py (new endpoints, revoke audit)
    - templates/superadmin.html (two new tabs, JS functions, state vars)
    - templates/base.html (two new nav links)
tech_stack:
  added: []
  patterns:
    - ORM query + org dict-map + jsonify for superadmin_devices
    - SQL event_type filter + Python org_id filter + 500-row LIMIT for superadmin_logs
    - Lazy-load tab pattern (devicesLoaded/logsLoaded flags + switchTab gate)
    - DELETE action pattern (confirm → fetch DELETE → reload) for revokeDevice
    - Client-side dual-filter (org + event) with re-render for filterLogs
key_files:
  created:
    - tests/test_sadm03_04.py
  modified:
    - app.py
    - templates/superadmin.html
    - templates/base.html
decisions:
  - logsOrgFilter populated from distinct org_name strings (not org_id), since LogEntry has no org_id and org resolution goes through emp_id → emp_org_map → org_name_map
  - Python org_id filter applied after SQL LIMIT 500 (Pitfall 1 per RESEARCH.md — documented in endpoint comment)
  - write_audit placed after db.session.commit() succeeds (device already deleted) rather than before, so audit only records confirmed revocations
metrics:
  duration: "~15 minutes"
  completed: "2026-06-29"
  tasks_completed: 2
  files_changed: 3
---

# Phase 10 Plan 02: SADM-03 / SADM-04 — Devices Tab and Logs Tab Summary

Delivered SADM-03 (Devices tab with cross-org kiosk device listing and Revoke action) and SADM-04 (Logs tab showing up to 500 most-recent recognition events filterable by org and event type), with server-side 403 enforcement on both new endpoints and audit trail on device revocation.

## What Was Built

### Task 1: Backend (app.py + tests/test_sadm03_04.py)

**GET /api/superadmin/devices (SADM-03 / D-03):** New endpoint under `# ─── API: Superadmin Extensions ───` section. Queries all KioskDevice rows ordered by created_at descending, builds an org_id-to-Organization object map, and returns JSON with: id, device_name, org_id, org_name (fallback "—"), org_token (org.org_token or null — required for revoke URL), created_at, last_seen_at. Protected by `@require_role("superadmin")`.

**GET /api/superadmin/logs (SADM-04 / D-04):** New endpoint. Builds emp_id-to-org_id map from Employee and org_id-to-name map from Organization. Queries LogEntry ordered by id descending; applies event_type SQL filter when provided; takes LIMIT 500. Python-side org_id filter skips rows whose resolved org differs from the query param. Returns: ts, event, name, org_name (fallback "—"), confidence_pct. Comment documents Pitfall 1 (LIMIT-before-filter). Protected by `@require_role("superadmin")`.

**write_audit in revoke_kiosk_device() (SADM-03 audit / T-10-06):** After successful db.session.commit(), captures device_name and org_id before deletion and calls write_audit("device_revoke", target_type="kiosk_device", target_id=device_id, old_value={"device_name": device_name, "org_id": device_org_id}). Benefits org_admin revokes too — acceptable per plan.

**tests/test_sadm03_04.py:** 5 tests all passing:
- (a) GET /api/superadmin/devices returns 200 with org_token
- (b) GET /api/superadmin/devices as org_admin returns 403
- (c) GET /api/superadmin/logs returns 200, at most 500 items, correct shape
- (d) GET /api/superadmin/logs?event_type=check_in returns only check_in events
- (e) GET /api/superadmin/logs as org_admin returns 403

### Task 2: Frontend (templates/superadmin.html, templates/base.html)

**panelDevices tab:** Table-card with columns Организация, Устройство, Зарегистрировано, Последняя активность, Действие. tbody id=devicesTableBody. `loadDevices()` fetches /api/superadmin/devices and calls `renderDevices`. `renderDevices(list)` renders rows with `escapeHtml` on all text (T-10-08); action cell has Отозвать button calling `revokeDevice(orgToken, deviceId)`. `revokeDevice()` confirms "Отозвать устройство?", calls DELETE /api/kiosk/{org_token}/devices/{deviceId}, reloads via `loadDevices` on success.

**panelLogs tab:** Toolbar with logsOrgFilter select (populated from distinct org_names) and logsEventFilter select (all/check_in/check_out). Table-card with columns Время, Событие, Имя, Организация, Уверенность %. `loadSuperLogs()` fetches /api/superadmin/logs, populates logsOrgFilter, calls `renderSuperLogs`. `renderSuperLogs(list)` renders rows with `escapeHtml`; confidence_pct formatted as rounded integer + "%". `filterLogs()` client-side filters allSuperLogs by org_name and event type, re-renders.

**JS state vars added:** allDevices, devicesLoaded, allSuperLogs, logsLoaded.

**switchTab extended:** Now toggles all 6 panels (orgs/users/system/employees/devices/logs) with lazy-load guards for devices and logs.

**templates/base.html:** Added Устройства (href=/superadmin/devices, icon 🖥) and Логи (href=/superadmin/logs, icon 📄) nav links after Сотрудники in the superadmin sidebar block, using existing active-class pattern.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat | Mitigation | Location |
|--------|------------|----------|
| T-10-05 Info Disclosure (devices/logs) | `@require_role("superadmin")` returns 403 for all other roles; verified by tests (b) and (e) | app.py superadmin_devices(), superadmin_logs() |
| T-10-06 Repudiation (device revoke) | `write_audit("device_revoke")` records actor, device_name, org_id after commit | app.py revoke_kiosk_device() |
| T-10-08 Tampering (text rendering) | `escapeHtml()` applied to all DB-sourced strings in renderDevices and renderSuperLogs | templates/superadmin.html |
| T-10-09 DoS (logs query size) | LogEntry query capped at LIMIT 500 in SQL before Python iteration | app.py superadmin_logs() |

## Known Stubs

None. loadDevices and loadSuperLogs both fetch live data from the new backend endpoints.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 — Backend endpoints + audit + tests | 8895735 | app.py, tests/test_sadm03_04.py |
| 2 — Frontend tabs + nav links | a0918bf | templates/superadmin.html, templates/base.html |

## Self-Check: PASSED
