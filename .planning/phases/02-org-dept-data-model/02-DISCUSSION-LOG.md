# Phase 2: Org/Dept Data Model - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 2-Org/Dept Data Model
**Areas discussed:** Data file structure, Migration delivery, Work schedule schema, CRUD UI location

---

## Data File Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Separate files (Recommended) | orgs.json + depts.json with org_id FK; mirrors existing load/save pattern | ✓ |
| Single nested file | orgs.json with depts array inside each org | |
| Inline in employees.json | Embed org/dept name directly into employee records | |

**User's choice:** Separate files (orgs.json + depts.json)
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal | Org: {id, name, created_at}. Dept: {id, org_id, name, created_at} | |
| With metadata | Add description and contact/head fields | ✓ |

**User's choice:** With metadata
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| Org: name + description. Dept: name + head_name. | Simple string head, no FK | |
| Org: name + description. Dept: name + head_user_id. | Dept head as user FK | |
| You decide | Claude picks schema for clinic context | ✓ |

**User's choice:** You decide — Claude chose `head_name` string (no FK) to avoid join complexity with JSON files.

---

## Migration Delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone script (Recommended) | migrate.py run once manually | ✓ |
| Auto on startup | app.py detects missing org_id and auto-migrates | |
| Flask route /migrate | POST /migrate triggers migration via HTTP | |

**User's choice:** Standalone migrate.py
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| Single default org + dept (Recommended) | Creates "Главная организация" + "Основной отдел", assigns all employees | ✓ |
| Prompt for names | Interactive shell prompts for org/dept name | |
| Config-driven | Edit name constants at top of migrate.py | |

**User's choice:** Single default org + dept with hardcoded Russian-language names
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| Verify + warn (Recommended) | Check label integrity, print warnings, don't abort | ✓ |
| Verify + abort on mismatch | Revert employees.json if any label missing | |
| Skip integrity check | No MIG-02 verification | |

**User's choice:** Verify + warn
**Notes:** —

---

## Work Schedule Schema

| Option | Description | Selected |
|--------|-------------|----------|
| Time strings + day list (Recommended) | { start: '09:00', end: '18:00', work_days: [1,2,3,4,5] } | ✓ |
| Shift object with total hours | Includes hours field explicitly | |
| You decide | Claude designs schema | |

**User's choice:** Time strings + day list
**Notes:** work_days uses ISO weekday integers for direct datetime.weekday()+1 comparison in Phase 3

| Option | Description | Selected |
|--------|-------------|----------|
| 09:00–18:00, Mon–Fri (Recommended) | Standard clinic workday as default | |
| Configurable system default | Global default in config.json | |
| No default — required on creation | Schedule must be explicitly set | ✓ |

**User's choice:** No default — required on creation (schedule is a required form field)
**Notes:** Migration assigns standard 09:00–18:00 Mon–Fri to all existing employees

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in employees.json (Recommended) | schedule: {...} inside each employee record | ✓ |
| Separate schedules.json | Keyed by emp_id, separate file | |

**User's choice:** Inline in employees.json

---

## CRUD UI Location

| Option | Description | Selected |
|--------|-------------|----------|
| New dedicated pages (Recommended) | superadmin.html, org_admin.html, dept_admin.html | ✓ |
| Extend admin.html with tabs | Add new tabs to existing admin.html | |
| Hybrid: new superadmin.html + extend admin.html | Mixed approach | |

**User's choice:** New dedicated pages

| Option | Description | Selected |
|--------|-------------|----------|
| System stats + org list (Recommended) | Stat cards + org table + inline Add org form | ✓ |
| Stats only, no org table | Summary stats only, /orgs separate | |
| You decide | Claude designs superadmin dashboard | |

**User's choice:** System stats + org list

| Option | Description | Selected |
|--------|-------------|----------|
| Present/absent/late for today + employee table (Recommended) | Three counters + employee table with check-in status | ✓ |
| Check-in list only | List of today's check-in events | |
| You decide | Claude designs dept dashboard | |

**User's choice:** Present/absent/late for today + employee table

---

## Claude's Discretion

- Exact HTML/CSS layout of new pages (follow admin.html patterns)
- Dept head field schema (chose `head_name` string, no FK)
- ID generation strategy (uuid4)
- API endpoint naming for org/dept CRUD

## Deferred Ideas

None — discussion stayed within phase scope.
