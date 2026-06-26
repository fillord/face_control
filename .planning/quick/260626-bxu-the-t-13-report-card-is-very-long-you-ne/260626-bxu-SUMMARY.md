---
quick_id: 260626-bxu
description: T-13 report card compact layout to fit on screen
date: 2026-06-26
commit: 2598e42
status: complete
---

# Summary: T-13 Compact Layout

## What Was Built

Reduced T-13 timesheet table column widths so a 31-day month fits on 1366px screens without horizontal scrolling.

**Changes in `templates/timesheet.html` and `templates/timesheet_partial.html`:**

| Property | Before | After |
|----------|--------|-------|
| emp-col width | 180px | 140px |
| day-col width | 32px | 22px |
| total-col width | 60px | 44px |
| tbody td padding | 4px | 2px |
| emp-name padding | 8px 12px | 6px 8px |
| sym-cell font-size | 13px | 11px |
| total-col inline font-size | 13px | 11px |

**New table width for 31-day month:** 1042px (was 1472px)
**Available on 1366px screen:** ~1054px — table now fits with ~12px to spare.
