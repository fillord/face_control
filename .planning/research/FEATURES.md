# Feature Research

**Domain:** HR Attendance / T-13 Timesheet System with RBAC
**Researched:** 2026-06-11
**Confidence:** MEDIUM — T-13 symbols and rules are well-established regulatory standards (HIGH confidence); RBAC patterns for HR are well-established (HIGH); Kazakhstan-specific export nuances are from training data (MEDIUM, should be verified against current RK labor code if strict compliance is required)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that HR and clinic staff assume exist. Missing these = the system feels unfinished or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| T-13 grid view (employees × days) | The T-13 form is the statutory document in RK/RU for recording daily attendance; HR cannot submit payroll without it | HIGH | Grid must show day columns 1–31 (or month-length), employee rows, symbol per cell. Two sub-rows per employee (first half / second half of month per standard form) |
| T-13 symbols: Я, О, В, П, У, Б, К and variants | These letter codes are defined by Rosstat/Goskomstat and expected by any accountant or payroll clerk in post-Soviet context | LOW | Core codes: Я=worked (явка), О=vacation (отпуск), В=day off (выходной), П=absence without reason (прогул), У=study leave, Б=sick leave, К=business trip. Numeric sub-row for hours | 
| Monthly totals per employee | Payroll depends on days/hours worked, absences, vacation days; accountants cross-check totals against salary | MEDIUM | Totals: days worked (code I/1), hours worked (code II/2), calendar days absent, vacation days, sick days |
| Role-based access (5 roles) | Without it every user sees everything — unacceptable in a clinic with patient-adjacent data | HIGH | superadmin, org_admin, dept_admin, viewer, employee. Each role's scope must be enforced server-side |
| Data isolation by org and department | HR at ВОП-1 must not see ВОП-2 records; this is a trust and compliance requirement | HIGH | Isolation at query layer, not just UI hiding |
| Employee list with org/dept assignment | You cannot build a timesheet without knowing who belongs to which unit | LOW | Name, position, department; existing employees.json needs migration |
| Month/year navigation | Timesheets are monthly documents; users need to navigate backward to prior months | LOW | Must not allow editing of a "closed" (submitted) period without explicit unlock |
| Password hashing (bcrypt) | Basic security hygiene; plain-text or weak-hash passwords are unacceptable in any 2026 system | LOW | Existing app already imports bcrypt; upgrade is straightforward |
| Export T-13 to Excel (.xlsx) | Accountants and payroll systems in KZ/RU universally expect Excel; PDF is secondary | MEDIUM | openpyxl; must replicate T-13 column layout with Cyrillic headers, merged cells for month totals |
| Export to CSV UTF-8 BOM | Windows Excel opens UTF-8 BOM CSVs correctly with Cyrillic; without BOM, mojibake guaranteed | LOW | Add BOM (`﻿`) at stream start; comma or semicolon delimiter (semicolon preferred for RU/KZ Excel locale) |
| Employee self-service cabinet | Employees must be able to view their own record; they cannot accept their timesheet data on faith | MEDIUM | Own T-13 view, exact arrival/departure timestamps, late arrival and absence flags. Read-only. |
| Work schedule per employee | Hours calculation requires knowing expected hours (8h/day standard, custom for part-time) | MEDIUM | Standard 5-day/8h default; custom days + hours for exceptions |
| Late arrival detection | Clinics operate on fixed shifts; late arrivals affect performance review | LOW | Compare face-check-in time against schedule start; flag if > N minutes late |
| Absence marking | Days with no check-in must be automatically pre-filled П (absence) pending HR review | MEDIUM | Auto-mark is pre-fill only; HR confirms or changes symbol. Never auto-submit to payroll. |
| Viewer role (read-only) | Auditors, directors, and observers need visibility without edit rights | LOW | Viewer sees dept timesheet, cannot change symbols or export configuration |

### Differentiators (Competitive Advantage)

Features that go beyond basic T-13 compliance and add real operational value for a clinic.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Face recognition auto-populates Я | The existing kiosk already captures check-in/out; automatically deriving Я (worked) vs absence from biometric data eliminates manual daily entry — this is the core integration value | MEDIUM | Map: first scan of day = arrival, last scan = departure. If both present and within schedule: Я. If only arrival: partial (HR reviews). |
| Configurable late threshold per department | ВОП departments may have different shift starts; per-dept threshold is more accurate than a global value | LOW | Config: shift_start time + grace_minutes. Already partially implied by per-employee schedule |
| Timesheet status workflow (open → submitted → locked) | Prevents accidental edits after HR submits to payroll; creates audit trail | MEDIUM | Status per timesheet per month: open, submitted, locked. Only superadmin/org_admin can unlock. |
| Audit log of symbol changes | Regulators and managers ask "who changed this cell?"; the log answers it | MEDIUM | Append-only log: who, when, old symbol, new symbol, reason field |
| Organizational hierarchy dashboard | superadmin needs a bird's-eye view of all orgs and their completion status | MEDIUM | Summary: orgs × months × percent complete |
| Employee position/rate in export | Full T-13 form includes position title and rate category; payroll systems need it | LOW | Add position field to employee record; include in xlsx header rows |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Shift/rotating schedule support (2/2, 1/3) | Some clinic support staff work rotating shifts | Rotating schedule logic is an order-of-magnitude more complex than standard; it requires shift calendar, night hours, inter-day span handling, and different T-13 coding (НН, НВ etc.) | Defer to v2; document the constraint clearly; for v1 mark rotating-schedule employees with a manual note |
| Real-time notifications (email/SMS when late) | Managers want instant alerts | Push infrastructure (SMTP, SMS gateway) adds operational complexity and failure modes well outside the project scope | Use daily summary in the timesheet view instead; managers check at end of day |
| Self-service org registration | Convenience for multi-tenant SaaS | This is a single-clinic deployment; uncontrolled org creation is a security hole | superadmin creates orgs manually — already decided in PROJECT.md |
| OAuth / SSO (Google, LDAP) | IT staff asks for it | Overkill for a 5-org clinic system with <100 users; adds dependency on external identity provider | bcrypt local auth is sufficient; SSO is a v2 consideration if the system expands to a hospital network |
| Mobile app | Staff want to check timesheets on phone | A responsive web design covers 90% of mobile use cases without a separate codebase | Make web UI responsive (Bootstrap or similar); no native app |
| Face re-registration from employee cabinet | Employees want to update their own photo | Biometric data must be controlled by admin to prevent spoofing; employee self-service re-registration is a security risk | Admin-only face re-registration; employee can request it via the cabinet (message/flag, not self-service) |
| Bulk symbol override | "Mark everyone as worked today" | Bulk operations on payroll data create audit risk and are prone to misuse | Cell-by-cell edit with audit log; multi-select with confirmation if absolutely needed |
| Payroll calculation | HR asks "can it also calculate salary?" | Payroll involves tax tables, deduction rules, RK-specific labor law edge cases — it is a separate domain | The T-13 is an input to payroll software (1C, etc.); export xlsx for import there |

---

## Feature Dependencies

```
[RBAC / 5-role system]
    └──requires──> [bcrypt auth upgrade]
    └──requires──> [org + dept data model]

[T-13 grid view]
    └──requires──> [org + dept data model]
    └──requires──> [employee work schedule]
    └──requires──> [attendance data (existing)]

[Absence auto-fill (П)]
    └──requires──> [T-13 grid view]
    └──requires──> [employee work schedule]

[Late arrival detection]
    └──requires──> [employee work schedule]
    └──requires──> [attendance data (existing)]

[Monthly totals]
    └──requires──> [T-13 grid view]
    └──requires──> [T-13 symbols per cell]

[Export Excel / CSV]
    └──requires──> [T-13 grid view]
    └──requires──> [monthly totals]
    └──requires──> [employee position field]

[Employee self-service cabinet]
    └──requires──> [RBAC / 5-role system]  (employee role must exist)
    └──requires──> [T-13 grid view]  (read-only view reuses grid)
    └──requires──> [late arrival detection]

[Timesheet status workflow]
    └──requires──> [T-13 grid view]
    └──enhances──> [export Excel / CSV]  (only export locked/submitted timesheets)

[Audit log of symbol changes]
    └──requires──> [T-13 grid view]  (changes happen in the grid)
    └──enhances──> [timesheet status workflow]

[Face recognition auto-populates Я]
    └──requires──> [attendance data (existing)]  (already collected)
    └──requires──> [T-13 symbols per cell]
    └──enhances──> [absence auto-fill]

[Org hierarchy dashboard]
    └──requires──> [RBAC / 5-role system]
    └──requires──> [T-13 grid view]  (reads completion status)
```

### Dependency Notes

- **T-13 grid requires org+dept model:** You cannot build the employee-rows dimension of the grid without knowing org/dept assignment. RBAC and org model must come first.
- **Export requires monthly totals:** The xlsx T-13 form has a totals section; generating the file without totals would produce an invalid statutory document.
- **Employee cabinet reuses grid:** The cabinet is not a separate UI component — it is the same grid filtered to one employee with edit controls removed. Build the grid first.
- **Face auto-populate enhances absence fill:** When face data exists for a day, pre-fill Я. When it does not, pre-fill П. These two rules combine into one "derive symbol from attendance" pass.

---

## MVP Definition

### Launch With (v1)

Minimum set to replace manual T-13 paper sheets at the clinic.

- [ ] RBAC 5-role system with bcrypt, data isolation at query layer — without this nothing else is trustworthy
- [ ] Org + dept data model with migration of existing employees — prerequisite for everything else
- [ ] T-13 grid view for dept_admin / org_admin with full symbol set (Я, О, В, П, У, Б, К) — the core document
- [ ] Auto-derive Я/absent from existing face check-in data — eliminates the primary manual work
- [ ] Employee work schedule (standard 8h/5-day + custom) — required for totals and late detection
- [ ] Monthly totals (days worked, hours, absences, vacation days) — required for payroll handoff
- [ ] Export T-13 to Excel (.xlsx) with correct Cyrillic layout — the statutory deliverable
- [ ] Export to CSV UTF-8 BOM — secondary export for systems that do not accept xlsx
- [ ] Employee self-service cabinet (own T-13, arrival/departure times, late/absence summary) — reduces HR support load
- [ ] Viewer role: read-only dept attendance view — needed for directors and auditors from day one

### Add After Validation (v1.x)

Features to add once v1 is running and HR staff have used it for a month.

- [ ] Timesheet status workflow (open → submitted → locked) — add once HR confirms the edit/review cycle; premature locking creates friction
- [ ] Audit log of symbol changes — add when HR or management requests accountability; implementation is low-risk but adds storage
- [ ] Configurable late threshold per department — add when clinics with different shift times onboard
- [ ] Org hierarchy dashboard for superadmin — add once more than one org is active

### Future Consideration (v2+)

- [ ] Rotating/shift schedules (2/2, 1/3) — deferred; requires separate schedule model
- [ ] PDF export of T-13 — secondary format; xlsx satisfies the immediate need
- [ ] OAuth / SSO — only relevant if system expands to hospital network
- [ ] Payroll calculation — separate domain; hand off to 1C via xlsx export

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| RBAC 5-role system | HIGH | HIGH | P1 |
| Org + dept data model + migration | HIGH | MEDIUM | P1 |
| T-13 grid view | HIGH | HIGH | P1 |
| Auto-derive symbol from face data | HIGH | MEDIUM | P1 |
| Employee work schedule | HIGH | MEDIUM | P1 |
| Monthly totals | HIGH | MEDIUM | P1 |
| Export to Excel (.xlsx) | HIGH | MEDIUM | P1 |
| Export to CSV UTF-8 BOM | MEDIUM | LOW | P1 |
| Employee self-service cabinet | HIGH | LOW | P1 (reuses grid) |
| Viewer role | MEDIUM | LOW | P1 |
| Timesheet status workflow | MEDIUM | MEDIUM | P2 |
| Audit log | MEDIUM | MEDIUM | P2 |
| Late threshold per dept | LOW | LOW | P2 |
| Org hierarchy dashboard | MEDIUM | MEDIUM | P2 |
| Rotating schedules | HIGH | HIGH | P3 |
| Payroll calculation | HIGH | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## T-13 Symbol Reference

This table documents the standard Goskomstat/Rosstat T-13 attendance codes. These are regulatory definitions — not configurable per-customer.

| Symbol | Russian Name | Meaning | Hours sub-row? |
|--------|-------------|---------|----------------|
| Я | Явка | Day worked (present) | Yes — actual hours |
| О | Отпуск | Annual paid vacation | No (or days) |
| ОЗ | Отпуск без сохранения з/п | Unpaid leave | No |
| Б | Болезнь | Sick leave (with certificate) | No |
| К | Командировка | Business trip | Yes |
| У | Учебный отпуск | Study leave | No |
| В | Выходной/праздник | Weekend or public holiday | No |
| П | Прогул | Absence without reason | No |
| НН | Невыясненная причина | Reason not established yet | No |
| Р | Отпуск по беременности | Maternity leave | No |
| ОВ | Дополнительный выходной | Additional day off (donated blood etc.) | No |

**Implementation note:** For a clinic MVP, the minimum viable symbol set is Я, О, В, П, Б, К, У, НН. The НН code is important: mark unknown absences НН first, resolve to П or Б later. Never default to П without confirmation — it implies disciplinary action.

---

## Kazakhstan-Specific Notes

**Confidence: MEDIUM** — based on training data; verify against current RK Labor Code (Трудовой кодекс РК) if strict statutory compliance is required.

- Kazakhstan uses T-13 form as-is from post-Soviet standard; the RK Labor Code references attendance sheets but does not prescribe a proprietary form
- Excel export headers should support both Russian and Kazakh (Latin or Cyrillic) column titles; for v1 Russian is sufficient
- CSV semicolon delimiter is preferred over comma for compatibility with Windows Excel in RU/KZ locale settings (Excel uses the system list separator, which is `;` in Russian locale)
- UTF-8 BOM (`﻿`) is mandatory for correct Cyrillic rendering when opening CSV in Windows Excel
- RK public holidays differ from Russian Federation holidays; the В (day off) auto-fill for weekends is correct, but public holiday calendar is separate and either hard-coded per year or left to HR manual entry for v1
- 1C:Зарплата и Кадры (1C:ZiK) is the dominant payroll system in KZ; T-13 xlsx export should be compatible with 1C import format if possible — but 1C import is a v2 concern

---

## Sources

- T-13 symbol codes: Goskomstat Resolution No. 1 (2004) "On approval of unified forms of primary accounting documentation for labor and its payment" — regulatory source, HIGH confidence
- RBAC patterns: training data synthesis from Flask/web application security literature — HIGH confidence for patterns, applied to this domain
- Kazakhstan Excel/CSV locale: training data on Windows CJK/Eastern European locale behavior — MEDIUM confidence; verify with a test file on target Windows version if CSV format is user-critical
- 1C compatibility note: training data on 1C:ZiK import formats — LOW confidence; treat as hypothesis, verify in v2

---

*Feature research for: Flask RBAC + T-13 Timesheet Attendance System (Kazakh clinic)*
*Researched: 2026-06-11*
