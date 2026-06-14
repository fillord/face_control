---
status: testing
phase: 04-export-employee-cabinet
source: [04-VERIFICATION.md]
started: 2026-06-14T00:00:00Z
updated: 2026-06-14T00:00:00Z
---

## Current Test

number: 1
name: XLSX renders correctly in Excel
expected: |
  Merged cells in rows 1-2 with Cyrillic T-13 title, bold column headers in row 3,
  column widths (A=24, day cols=4), and per-employee data rows visible without errors
awaiting: user response

## Tests

### 1. XLSX renders correctly in Excel
expected: Merged cells in rows 1-2 with Cyrillic T-13 title, bold column headers in row 3, column widths set, and per-employee data rows visible without errors
result: [pending]

### 2. CSV Cyrillic displays correctly in Windows Excel
expected: UTF-8 BOM causes Windows Excel to open the file without a character encoding prompt; Cyrillic column headers display correctly (not as mojibake)
result: [pending]

### 3. Employee cabinet is read-only with month clamping
expected: No edit controls visible on the cabinet page; month selector is bounded to current and previous month only; navigating outside that range is blocked
result: [pending]

### 4. Tooltip times display on hover in browser
expected: Hovering over a T-13 grid cell shows a native tooltip with "Приход: HH:MM / Уход: HH:MM" formatted times
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
