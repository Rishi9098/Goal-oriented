# Feature Completeness Matrix — Northstar

**Date:** 2026-07-08
**Columns:** Frontend handler exists · API client function exists (`api.ts`) · Backend endpoint/service exists · Status · Classification

**Status key:** ✓ Complete · ⚠ Partial · ❌ Missing/Dead · 🔒 Intentionally disabled (honest placeholder)

---

| Feature | Frontend | API client | Backend | Status | Classification |
|---|:---:|:---:|:---:|:---:|---|
| Sign up / Sign in / Sign out | ✓ | ✓ | ✓ | ✓ | Complete |
| Forgot / Reset password | ✓ | ✓ | ✓ | ✓ | Complete |
| Change password | ✓ | ✓ | ✓ | ✓ | Complete |
| Delete account | ✓ | ✓ | ✓ | ✓ | Complete |
| Update full name | ✓ | ✓ | ✓ | ✓ | Complete |
| **Update email** | ✓ (UI only) | ⚠ (param never sent) | ❌ (no schema field) | ❌ | Partially implemented, abandoned mid-way — see Broken Interaction Report #1 |
| Onboarding wizard (12 steps) | ✓ | ✓ | ✓ | ✓ | Complete |
| Goals — create / edit / delete | ✓ | ✓ | ✓ | ✓ | Complete |
| Goals — Monte Carlo simulation | ✓ | ✓ | ✓ | ✓ | Complete |
| Goals — optimizer suggestions | ✓ | ✓ | ✓ | ✓ | Complete |
| Goals — custom education inflation rate | ✓ | ✓ | ✓ | ✓ | Complete |
| Dashboard (net worth, cash flow, projections) | ✓ | ✓ | ✓ | ✓ | Complete |
| **Dashboard goal-card click-through** | ❌ | n/a | n/a | ❌ | Never implemented — see Dead Click Report #4 |
| Family — member CRUD | ✓ | ✓ | ✓ | ✓ | Complete |
| Family — goal tagging | ✓ | ✓ | ✓ | ✓ | Complete |
| Family — insurance tracking + recommendation | ✓ | ✓ | ✓ | ✓ | Complete |
| Family — government schemes eligibility | ✓ | ✓ | ✓ | ✓ | Complete |
| Family — recommendations feed | ✓ | ✓ | ✓ | ✓ | Complete |
| Family — dashboard aggregation | ✓ | ✓ | ✓ | ✓ | Complete |
| Family — audit logging (insurance writes) | n/a | n/a | ✓ | ✓ | Complete (verified in Milestone 2.1-P2) |
| Reports — summary + goal breakdown | ✓ | ✓ | ✓ | ✓ | Complete |
| **Reports — PDF export** | ⚠ (uses `window.print()`) | n/a | n/a | ⚠ | Partially implemented — see Broken Interaction Report #7 |
| AI Copilot — chat | ✓ | ✓ | ✓ | ✓ | Complete (real path + tested rule-based fallback) |
| **AI Copilot — mode disclosure** (AI vs. fallback) | ❌ | ❌ | ❌ | ❌ | Never implemented — see Broken Interaction Report #8 |
| **Global search** | ❌ | ❌ | ❌ | ❌ | Never implemented — see Dead Click Report #1 |
| **Notification center** | ❌ | ❌ | ❌ | ❌ | Never implemented — see Dead Click Report #2. Settings' "Notifications" card correctly labels this 🔒 Coming soon, but the header bell icon does **not** carry the same honest labeling — it presents as already-functional |
| **Profile avatar menu** | ❌ | n/a | n/a | ❌ | Never implemented — see Dead Click Report #3 |
| Settings — linked accounts (Plaid) | 🔒 | ❌ | ❌ | 🔒 | Intentionally disabled, honestly labeled "Coming soon" — correct pattern |
| Settings — notifications preferences | 🔒 | ❌ | ❌ | 🔒 | Intentionally disabled, honestly labeled "Coming soon" — correct pattern |
| **Landing page — account linking claim** | n/a (marketing copy) | ❌ | ❌ | ❌ | Claimed as live in marketing copy; contradicts Settings' own "Coming soon" label — see Broken Interaction Report #5 |
| **Landing page — live demo** | ⚠ (redirects to sign-in) | n/a | n/a | ⚠ | No demo-mode exists — see Broken Interaction Report #2 |
| **Landing page — legal pages** (Privacy/Terms/Disclosures) | ❌ | n/a | n/a | ❌ | Never implemented — see Dead Click Report #6 |
| shadcn/ui component library (`components/ui/*`) | n/a | n/a | n/a | ❌ (unused) | ~50 files of dialog/dropdown/tabs/select/table/pagination/context-menu/accordion primitives exist in the repo but are imported by **zero** app screens — dead scaffold code, not a defect but a completeness/hygiene finding |
| Personal tax calculation | ❌ | ❌ | ❌ | ❌ | Never started — versioned tax *data* exists (`tax_sections`), no computation engine (documented in this session's separate AI-assistant research, `06_Tool_Calling.md` §4, as a known, correctly-deferred gap) |

---

## Rollup by category

| Category | Complete | Partial | Missing/Dead | Intentionally disabled |
|---|---|---|---|---|
| Auth & account | 5 | 1 | 0 | 0 |
| Goals | 4 | 0 | 1 | 0 |
| Family module | 7 | 0 | 0 | 0 |
| Reports | 1 | 1 | 0 | 0 |
| AI Copilot | 1 | 0 | 1 | 0 |
| Global chrome (search/notifications/avatar) | 0 | 0 | 3 | 0 |
| Settings | 0 | 0 | 0 | 2 |
| Landing/marketing | 0 | 1 | 2 | 0 |
| Infrastructure/scaffold | 0 | 0 | 1 | 0 |

## Reading this matrix

The certified, tested product surface (Auth, Goals, Family module, Reports data, AI Copilot's actual chat function) is **essentially complete** — every real defect found in this audit is either (a) global shell chrome that was scaffolded but never wired (Search/Notifications/Avatar — all three share one root cause and one fix path), (b) the unauthenticated marketing site (which was out of scope for the Milestone 2 certification and should be treated as its own follow-up), or (c) one genuine, narrow data-integrity bug (Profile email field) that should be prioritized ahead of everything else in this report. The Settings page is the one screen in the entire audit that demonstrates the *correct* way to handle an unbuilt feature (clearly labeled "Coming soon," de-emphasized, non-interactive) — that pattern should be the template applied to the landing page's account-linking claim and to the notification bell's honest-disclosure state.
