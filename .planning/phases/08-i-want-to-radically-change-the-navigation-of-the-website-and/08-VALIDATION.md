---
phase: 8
slug: i-want-to-radically-change-the-navigation-of-the-website-and
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-25
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) + browser smoke test (manual) |
| **Config file** | `conftest.py` (existing) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v` + browser smoke test
- **Before `/gsd-verify-work`:** Full suite must be green + visual check of all role pages
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | base.html created | — | N/A | manual | check file exists | ✅ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | Role sidebar correct | — | sidebar shows only role-appropriate items | manual | visual per role | ✅ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | superadmin extends base | — | N/A | unit | `pytest -k superadmin` | ✅ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | org_admin extends base | — | N/A | unit | `pytest -k org_admin` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing `tests/` directory covers Flask route responses
- No new test files needed for Wave 0 — visual/manual verification is primary for UI changes

*Existing infrastructure covers all automated phase requirements. UI correctness is manual-only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sidebar shows correct items per role | D-02 | CSS/HTML rendering | Log in as each role, verify sidebar nav items |
| Dark sidebar + teal accent renders | D-06, D-07 | Visual design | Open each authenticated page, confirm colors |
| Inter font loads | D-08 | Font CDN | Dev tools → Network → check Inter loaded |
| Hamburger collapses at ≤768px | D-15 | Responsive CSS | Resize browser to 768px, confirm hamburger appears |
| No top header bar | D-16 | Layout | Verify absence of old white header |
| User info at sidebar bottom | D-04 | Layout | Verify username/role/logout at sidebar bottom |
| All 13 templates functional | D-14 | Route coverage | Click through every authenticated page |
| Partials render inside base layout | D-10 | Jinja2 | Load timesheet and reports pages |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
