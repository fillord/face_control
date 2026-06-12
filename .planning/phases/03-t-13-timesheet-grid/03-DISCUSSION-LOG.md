# Phase 3: T-13 Timesheet Grid - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 3-T-13 Timesheet Grid
**Areas discussed:** Manual symbol entry, Grid placement & routing, Month/dept selector UI, 2026 holidays & startup warning

---

## Manual symbol entry

**Q1: How should Б, К, П be handled?**

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 3: inline cell editing | HR clicks a cell to override; saves to timesheet_overrides.json | ✓ |
| Phase 3: НН only (no manual entry) | All non-auto symbols render as НН until Phase 4 | |
| Phase 3: read-only with placeholder markers | НН with pencil icon indicating future override | |

**User's choice:** Phase 3: inline cell editing

---

**Q2: Where should manual overrides be stored?**

| Option | Description | Selected |
|--------|-------------|----------|
| data/timesheet_overrides.json | Separate file, clean separation from auto-derived data | |
| Inline in attendance.json | Add 'override' field to attendance records | |
| You decide | Claude picks the storage approach | ✓ |

**User's choice:** You decide (Claude: separate `data/timesheet_overrides.json`)

---

**Q3: Who can edit cell overrides?**

| Option | Description | Selected |
|--------|-------------|----------|
| dept_admin and above (recommended) | dept_admin→own dept; org_admin→their org; superadmin→all | ✓ |
| org_admin and above only | dept_admin sees grid but cannot override | |
| You decide | Claude uses ROLE_HIERARCHY | |

**User's choice:** dept_admin and above

---

**Q4: О+У notation in a single cell?**

| Option | Description | Selected |
|--------|-------------|----------|
| ОУ combined in cell (recommended) | Two chars in cell; totals count independently | ✓ |
| Tooltip on hover | Cell shows О; hover reveals early departure detail | |
| You decide | Claude picks notation that fits grid layout | |

**User's choice:** ОУ combined in cell

---

## Grid placement & routing

**Q1: Where does the T-13 grid live?**

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated /timesheet route (recommended) | New page + template; URL params for dept/month | ✓ |
| Tab inside dept_admin.html | T-13 tab in existing dashboard | |
| Tab inside org_admin.html only | Restricts access to org_admin+ | |

**User's choice:** Dedicated /timesheet route

---

**Q2: Which roles can access /timesheet?**

| Option | Description | Selected |
|--------|-------------|----------|
| dept_admin, org_admin, superadmin (recommended) | Scoped by role at query layer; viewer read-only | ✓ |
| org_admin and superadmin only | dept_admin excluded from full grid | |
| You decide | Claude uses ROLE_HIERARCHY | |

**User's choice:** dept_admin, org_admin, superadmin

---

**Q3: Where does DASH-04 (per-dept monthly summary) live?**

| Option | Description | Selected |
|--------|-------------|----------|
| Section on org_admin.html dashboard (recommended) | Month picker + dept table; no new route | ✓ |
| Separate /org-report route | Dedicated org report page | |
| You decide | Claude picks placement | |

**User's choice:** Section on org_admin.html dashboard

---

## Month/dept selector UI

**Q1: How does the user pick month and department?**

| Option | Description | Selected |
|--------|-------------|----------|
| URL params + server render (recommended) | Form GET; page reload; bookmarkable | ✓ |
| JS-driven dynamic update | fetch() + DOM update; no page reload | |
| You decide | Claude picks based on codebase style | |

**User's choice:** URL params + server render

---

**Q2: Default month when /timesheet first opened?**

| Option | Description | Selected |
|--------|-------------|----------|
| Current month (recommended) | datetime.now() formatted as YYYY-MM | ✓ |
| Previous month | Last month — useful for post-period review | |
| You decide | Claude picks for clinic HR workflow | |

**User's choice:** Current month

---

**Q3: Dept selector for org_admin/superadmin?**

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown of authorized depts (recommended) | org_admin→their org's depts; superadmin→all grouped by org | ✓ |
| Two-step: pick org then dept | Avoids long list for superadmin | |
| You decide | Claude picks based on expected org count | |

**User's choice:** Single dropdown of authorized depts

---

## 2026 holidays & startup warning

**Q1: Extend hard-coded holiday list to 2026?**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — hard-code 2024, 2025, 2026 (recommended) | Covers current operational year; TODO comment for 2027 | ✓ |
| Hard-code 2024 + 2025 only (as written) | Strict REQUIREMENTS.md compliance; startup warning fires | |
| You decide | Claude decides based on 2026 operational reality | |

**User's choice:** Yes — hard-code 2024, 2025, 2026

---

**Q2: What happens when a year has no holiday data?**

| Option | Description | Selected |
|--------|-------------|----------|
| Yellow banner in the grid (recommended) | Russian-language warning at top of timesheet; weekends still show В | ✓ |
| Startup log warning only | Flask logs WARNING at startup; grid renders silently | |

**User's choice:** Yellow banner in the grid

---

## Claude's Discretion

- Override storage schema: `data/timesheet_overrides.json` keyed `{emp_id: {date: symbol}}`
- Inline edit UI widget (dropdown or button group in grid cell)
- CSS/visual styling for ОУ cells and the holiday warning banner
- KZ 2026 public holiday exact dates (Claude uses egov.kz official list)
- Exact HTML layout of the timesheet.html template

## Deferred Ideas

None — discussion stayed within phase scope.
