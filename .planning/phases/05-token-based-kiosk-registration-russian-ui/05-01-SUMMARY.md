---
phase: 05-token-based-kiosk-registration-russian-ui
plan: "01"
subsystem: data-model
tags: [migration, bcrypt, tokens, orgs, tdd]
dependency_graph:
  requires: []
  provides: [migrate_org_tokens, generate_unique_token, hash_pin, is_bcrypt_hash, org-token-fields]
  affects: [data/orgs.json, app.py, migrate.py]
tech_stack:
  added: [secrets (stdlib)]
  patterns: [bcrypt-pin-hashing, token-uniqueness-loop, tdd-red-green]
key_files:
  created:
    - tests/test_migrate_tokens.py
  modified:
    - app.py
    - migrate.py
decisions:
  - "Use secrets.token_hex(4) (8 hex chars) for token generation per RESEARCH Pattern 4"
  - "is_bcrypt_hash checks startswith('$2b$') per RESEARCH Pitfall 1 detection pattern"
  - "migrate.py keeps standalone — does not import app; replicates secrets/bcrypt logic locally"
  - "generate_unique_token uses a seen-set that spans both org_token and reg_token values to prevent cross-field collisions"
  - "pre-existing test_rbac.py::test_public_routes failure (kiosk.html TemplateNotFound) is out-of-scope — caused by worktree forking before kiosk.html was committed to main"
metrics:
  duration: "~4 minutes"
  completed: "2026-06-12"
  tasks_completed: 2
  tasks_total: 3
  files_created: 1
  files_modified: 2
---

# Phase 05 Plan 01: Org Data Model — Token/PIN Fields Summary

**One-liner:** Backfill `org_token`, `reg_token`, `kiosk_pin` (bcrypt), `reg_pin` (bcrypt), `reg_token_expires`, and `kiosk_display_name` onto all org records via idempotent migrate.py extension; new orgs auto-provision all six fields via create_org.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Add token/PIN helpers and bootstrap new-org fields in app.py | 0a0d6c4 | Done |
| 2 | Write Phase 5 migrate.py token/PIN migration + test_migrate_tokens.py (TDD) | e964862 | Done |
| 3 | Checkpoint: human verification of production migration | — | Awaiting human |

## What Was Built

### Task 1 — app.py helpers and create_org (0a0d6c4)

**app.py changes:**
- Added `secrets` to the stdlib imports line (`import os, json, base64, time, shutil, uuid, secrets`)
- Added new section `# ─── Org tokens / PIN helpers ─────────────────────────────────────────────────`
- Added `generate_unique_token(existing_tokens)` — loops `secrets.token_hex(4)` until not in seen set
- Added `hash_pin(pin)` — wraps `bcrypt.hashpw(str(pin).encode(), bcrypt.gensalt()).decode()`
- Added `is_bcrypt_hash(value)` — returns `bool(value and str(value).startswith("$2b$"))`
- Updated `create_org` to emit all six token/PIN fields on every new org: `org_token`, `reg_token`, `kiosk_pin` (bcrypt "0000"), `reg_pin` (bcrypt "1234"), `reg_token_expires=None`, `kiosk_display_name=name`

### Task 2 — migrate.py + tests (e964862, preceded by RED commit 318224b)

**TDD cycle:**
- RED commit `318224b`: 6 failing tests in `tests/test_migrate_tokens.py`
- GREEN commit `e964862`: implementation passes all 6 tests

**migrate.py changes:**
- Added `import secrets` and `import bcrypt` to imports
- Added `_is_bcrypt(value)` local helper (checks `$2b$` prefix)
- Added `_gen_token(seen)` local helper (secrets.token_hex(4) uniqueness loop)
- Added `migrate_org_tokens(orgs)` function that mutates orgs dict in-place, idempotently:
  - Generates unique `org_token` per org if missing
  - Generates unique `reg_token` per org if missing (seen-set shared with org_token)
  - Hashes `kiosk_pin`: None → bcrypt("0000"); plaintext → re-hash; bcrypt → leave unchanged
  - Hashes `reg_pin`: None → bcrypt("1234"); plaintext → re-hash; bcrypt → leave unchanged
  - Sets `reg_token_expires` to None if missing
  - Sets `kiosk_display_name` to org name if missing/empty; does not overwrite existing value
  - Prints per-org summary of added/updated fields
- Wired `migrate_org_tokens` into `run_migration` as Phase 5 step (Step 6), after Phase 2 org/dept/employee steps

**tests/test_migrate_tokens.py:**
- `test_migrate_adds_all_fields` — MIG-TOKEN-01: all six fields present with correct format after migration
- `test_migrate_rehashes_plaintext` — MIG-TOKEN-02: plaintext kiosk_pin "2386" is re-hashed and verifies with bcrypt.checkpw
- `test_migrate_hashes_null_default` — MIG-TOKEN-02b: null kiosk_pin hashed to bcrypt("0000")
- `test_migrate_idempotent` — MIG-TOKEN-03: second run preserves org_token, reg_token, kiosk_pin, reg_pin values
- `test_migrate_sets_display_name` — kiosk_display_name defaults to org.name when absent
- `test_migrate_does_not_overwrite_existing_display_name` — existing kiosk_display_name is preserved

## Checkpoint: Awaiting Human Verification

Task 3 is a `checkpoint:human-verify` with `gate="blocking-human"`. The operator must run `python migrate.py` against production `data/orgs.json` and confirm the output before Phase 5 routes are built on top of it.

**Verification steps (for the operator):**

```bash
# 1. Back up
cp data/orgs.json data/orgs.json.pre05.bak

# 2. Run migration
venv/bin/python migrate.py

# 3. Inspect result
cat data/orgs.json

# 4. Verify NurLab PIN verifies against "2386"
venv/bin/python -c "import json,bcrypt; o=json.load(open('data/orgs.json')); print([bcrypt.checkpw(b'2386', v['kiosk_pin'].encode()) for v in o.values() if v.get('name')=='NurLab'])"

# 5. Run migration again — confirm idempotent (tokens unchanged)
venv/bin/python migrate.py
```

**Resume signal:** Type "approved" once orgs.json carries all six fields and the "2386" PIN verifies.

## Test Results

```
tests/test_migrate_tokens.py — 6 passed in 4.67s
Full suite (excluding pre-existing kiosk.html failure) — 7 passed, 4 xfailed, 14 xpassed
```

## Deviations from Plan

### Pre-existing Out-of-Scope Issue

**test_rbac.py::test_public_routes** fails with `TemplateNotFound: kiosk.html`. This is a pre-existing issue in this worktree — the worktree was forked at commit `c640797` (before `kiosk.html` was added in a later wave 2 commit). My changes do not affect this test file (confirmed: `git diff c640797 HEAD -- tests/test_rbac.py` is empty). Logged to `deferred-items.md` in phase directory — not fixed per scope boundary rule.

### Auto-fixed Issues

None — plan executed with no bugs or blocking issues discovered.

## Known Stubs

None. The migration helpers produce real bcrypt hashes and real unique tokens. No placeholder values.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: token-generation | app.py | generate_unique_token uses secrets.token_hex(4) (CSPRNG) — mitigates V6 cryptography concern |
| threat_flag: bcrypt-pin | migrate.py | plaintext-to-bcrypt migration path confirmed correct per ASVS V2 |

## TDD Gate Compliance

- RED gate: commit `318224b` — `test(05-01): add failing tests for migrate_org_tokens (RED phase)`
- GREEN gate: commit `e964862` — `feat(05-01): implement migrate_org_tokens in migrate.py (GREEN phase)`
- REFACTOR: not required (implementation is clean)

## Self-Check: PASSED

| Item | Status |
|------|--------|
| app.py exists with helpers | FOUND |
| migrate.py exists with migrate_org_tokens | FOUND |
| tests/test_migrate_tokens.py exists | FOUND |
| 05-01-SUMMARY.md exists | FOUND |
| Commit 0a0d6c4 (Task 1) | FOUND |
| Commit 318224b (TDD RED) | FOUND |
| Commit e964862 (TDD GREEN) | FOUND |
