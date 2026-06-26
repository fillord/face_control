---
quick_id: 260626-bxu
slug: the-t-13-report-card-is-very-long-you-ne
description: The T-13 report card is very long, you need it to fit on the screen
date: 2026-06-26
---

# Quick Plan: T-13 Compact Layout

## Goal
Reduce the T-13 timesheet table so it fits on 1366px-wide screens without horizontal scrolling.

**Current:** emp-col=180px, day-col=32px, total-col=60px → 1472px for 31-day month
**Target:**  emp-col=140px, day-col=22px, total-col=44px → 1042px for 31-day month (fits in ~1054px available at 1366px)

## Tasks

### Task 1 — Update timesheet.html CSS
- File: `templates/timesheet.html`
- Reduce `emp-col` width from 180px to 140px
- Reduce `day-col` width from 32px to 22px
- Reduce `total-col` width from 60px to 44px
- Reduce `tbody td` padding from 4px to 2px
- Reduce `emp-name` padding to 6px 8px, max-width to 140px
- Reduce `sym-cell` font-size from 13px to 11px
- Update inline `font-size:13px` on total-col body cells → 11px

### Task 2 — Update timesheet_partial.html CSS
- File: `templates/timesheet_partial.html`
- Same column width and font-size changes as Task 1
