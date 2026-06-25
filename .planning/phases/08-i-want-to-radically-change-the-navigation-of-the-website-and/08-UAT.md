---
status: testing
phase: 08-i-want-to-radically-change-the-navigation-of-the-website-and
source: [08-VERIFICATION.md]
started: 2026-06-25T00:00:00Z
updated: 2026-06-25T00:00:00Z
---

## Current Test

number: 1
name: Visual sidebar rendering
expected: |
  Dark navy sidebar visible on left, teal accents on active items, Inter font throughout, no top horizontal header bar on any authenticated page
awaiting: user response

## Tests

### 1. Visual sidebar rendering
expected: Dark navy sidebar (#1a2340 background) visible on the left, teal (#0d9488) accents on active nav items, Inter font applied throughout, no top horizontal header bar visible on any authenticated page
result: [pending]

### 2. Mobile hamburger toggle
expected: At viewport ≤768px, sidebar collapses; hamburger button (☰) appears in top-left; tapping it opens the sidebar with a dark overlay; tapping overlay or ✕ closes it
result: [pending]

### 3. Role-based nav items
expected: Each of the 6 roles (superadmin, org_admin, dept_admin, hr_viewer, viewer, employee) sees only its authorized nav items in the sidebar — no cross-role leakage visible in UI
result: [pending]

### 4. Content layout
expected: Sidebar and main content render side-by-side without overlap; `h1.page-title` is visible at the top of each page's content area; no horizontal scrollbar on standard desktop viewport
result: [pending]

### 5. Standalone error_token.html
expected: Navigating to an invalid/expired token URL (e.g. `/register/BADTOKEN`) shows a centered card page with Inter font and teal accent, NO sidebar, no session required — renders correctly for unauthenticated users
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
