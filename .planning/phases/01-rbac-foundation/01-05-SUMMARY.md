---
phase: 01-rbac-foundation
plan: "05"
subsystem: infra
tags: [pm2, gunicorn, secret-key, process-management, deployment]

# Dependency graph
requires:
  - phase: 01-rbac-foundation plan 04
    provides: fcntl.flock locking for JSON writes; single-worker requirement established

provides:
  - ecosystem.config.js PM2 config injecting SECRET_KEY and pinning gunicorn to -w 1
  - Operator checkpoint guidance for applying secret and restarting the process

affects:
  - all future phases (deployment config is phase-wide infrastructure)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PM2 ecosystem.config.js for process-manager env injection (no hardcoded secrets)"
    - "interpreter: none with exec_mode: fork for direct gunicorn launch under PM2"

key-files:
  created:
    - ecosystem.config.js
  modified: []

key-decisions:
  - "SECRET_KEY injected via PM2 env (not hardcoded in source) per ASVS V3"
  - "Single gunicorn worker (-w 1) combined with fcntl.flock prevents concurrent JSON-write race"
  - "interpreter: none + exec_mode: fork launches gunicorn directly without Node wrapper"

patterns-established:
  - "Deployment secrets always in PM2 env block, never in source"

requirements-completed: [AUTH-04]

# Metrics
duration: 1min
completed: 2026-06-11
---

# Phase 01 Plan 05: Runtime Hardening Summary

**PM2 ecosystem.config.js created with SECRET_KEY placeholder env injection and single gunicorn worker (-w 1) to eliminate hardcoded session key and multi-worker JSON write race**

## Performance

- **Duration:** 1 min
- **Started:** 2026-06-11T10:13:51Z
- **Completed:** 2026-06-11T10:14:35Z
- **Tasks:** 1 of 2 (Task 2 is a human-action checkpoint, pending operator)
- **Files modified:** 1

## Accomplishments

- `ecosystem.config.js` authored at repo root: PM2 config for `face-recognition` process with `SECRET_KEY` env placeholder, single gunicorn worker (`-w 1`), and bind `127.0.0.1:5051`
- All automated acceptance criteria pass: file loads without error, contains `SECRET_KEY`, `face-recognition`, `-w 1`, `127.0.0.1:5051`; hardcoded fallback `medkontrol-secret-2026-xK9mP3qR7v` absent; placeholder `REPLACE_WITH_GENERATED_SECRET` present
- Operator checkpoint (Task 2) documents exact steps to generate secret, apply config, confirm single worker, and re-login

## Task Commits

Each task was committed atomically:

1. **Task 1: Author ecosystem.config.js** - `e7d5621` (chore)
2. **Task 2: Apply SECRET_KEY + single worker via PM2** - PENDING — awaiting operator action

**Plan metadata:** pending final docs commit (after operator checkpoint completes)

## Files Created/Modified

- `/var/www/sites/face-almgp33/ecosystem.config.js` — PM2 app config: `face-recognition` process, gunicorn `-w 1 -b 127.0.0.1:5051 app:app`, `SECRET_KEY` env placeholder with generation instructions

## Decisions Made

- Used `interpreter: "none"` with `exec_mode: "fork"` to launch gunicorn directly (not via Node wrapper) — cleaner process tree, PID tracking accurate in PM2
- Placeholder token is `REPLACE_WITH_GENERATED_SECRET` (two occurrences: once in the comment, once in the env block) — `grep -c` returns 2, which satisfies `>= 1` criterion
- Did NOT reuse or reference `medkontrol-secret-2026-xK9mP3qR7v` (the hardcoded fallback) anywhere in the file

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**Operator action required before plan is fully live.** Task 2 checkpoint steps:

1. Generate a strong secret:
   ```
   /var/www/sites/face-almgp33/venv/bin/python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. Replace `REPLACE_WITH_GENERATED_SECRET` in `ecosystem.config.js` with the output.
3. Apply:
   ```
   pm2 start /var/www/sites/face-almgp33/ecosystem.config.js
   # or if face-recognition already exists:
   pm2 restart face-recognition --update-env
   ```
4. Verify: `pm2 status` shows `face-recognition` online.
5. Verify env: `pm2 env $(pm2 id face-recognition | tr -d "[] ")` shows `SECRET_KEY` set to new value (not hardcoded fallback).
6. Verify single worker: `pm2 describe face-recognition` or `ps aux | grep gunicorn` — one worker process besides the master.
7. Re-login: `superadmin / superadmin123` must succeed (existing sessions invalidated by key change, expected).

## Threat Flags

None — all threat mitigations in the plan's threat model are addressed by the ecosystem.config.js artifact (T-01-05-KEY, T-01-05-RACE, T-01-05-WEAK).

## Known Stubs

None — this plan produces only an infrastructure config file, no UI or data flow stubs.

## Next Phase Readiness

- After operator applies the PM2 config (Task 2 checkpoint), Phase 1 deployment posture is complete
- Phase 2 can begin once operator confirms login works post-key-rotation
- The `ecosystem.config.js` is the canonical deployment config going forward — future phases should update `args` if port or worker count changes

---
*Phase: 01-rbac-foundation*
*Completed: 2026-06-11 (Task 2 pending operator action)*
