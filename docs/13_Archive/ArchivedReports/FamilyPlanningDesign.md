# Family Financial Planning — Design Document

**Date:** 2026-07-06
**Status:** Design phase only. No code written. Grounded in the certified Foundation schema (`households`, `household_members`, `dependents`, `huf_entities`, `nominees`, `health_policies` — see `DatabaseDesignReport.md`, `FoundationReconciliationReport.md`). Where the design wants something the schema can't yet do, that gap is named explicitly, not silently designed around.

---

## Design Philosophy

Users don't think in database tables. Nobody has ever said "let me update my dependents integer." They say *"I have a wife, two kids, and my mother depends on me."* Every screen in this design is built around **people**, not fields. The `household_members`/`dependents` schema was built specifically so the product could finally speak this language — this design is what makes that schema pay off.

---

## Part 1: User Journey

The planner should evolve with the user's life, not ask them to describe their whole life on day one.

```
Single professional          Married               Child born             Buying a house         Parents aging          Retirement
──────────────────────  →  ─────────────────  →  ──────────────────  →  ──────────────────  →  ──────────────────  →  ──────────────
Just "You" in household     Add spouse            Add child             Home-purchase goal      Add dependent parent    Shift from
Emergency fund goal         Joint vs. separate     SSY surfaces          appears, tied to         Health-policy split     accumulation to
Retirement goal (self)      goals become a         automatically if      "You + Spouse"           recommendation          decumulation
                            real question            a daughter <10       not the whole            (Phase 3 finding)       framing
                                                                          household
```

Each life event is **user-initiated** (the person tells the app what changed), never inferred or assumed. The app's job is to make each addition fast and then immediately show what changed as a result — the "why" always follows the "what."

---

## Part 2: Where Family Lives — Information Architecture

**Decision: Family is a first-class nav item, not buried in Profile or Settings.** The existing nav is `Dashboard · Goals · AI Copilot · Reports · Profile · Settings` (confirmed from `app-shell.tsx`). Family goes second, right after Dashboard's overview and before Goals — because *who* the plan is for should be established before diving into *what* the plan targets.

```
Dashboard · Goals · Family · AI Copilot · Reports · Profile · Settings
```

**Mobile bottom nav constraint (real, checked against the existing code):** the current mobile nav shows exactly 4 items (`Dashboard, Goals, AI Copilot, Reports`) plus `Settings`. Adding Family as a 7th top-level item means the mobile bottom nav must be redesigned to `Dashboard · Goals · Family · Copilot · More`, with Reports/Profile/Settings moved behind "More." This is a real, non-trivial frontend change flagged here for the implementation phase, not glossed over.

### Screen Hierarchy

```
/app/family                          Family home — the household workspace
/app/family/members/:id              A person's detail page (you, spouse, a child, a parent)
/app/family/add                      Add-a-person flow (spouse | child | parent | other)
/app/family/goals                    Family goals — who each goal is for, side by side
/app/family/insurance                Health policies — floater vs. standalone, coverage map
/app/family/schemes                  Personalized government scheme eligibility
/app/dashboard (existing, extended)  New "Family" summary card, links into /app/family
```

---

## Part 3: Onboarding — Keep It Fast, Defer the Depth

**Key design decision, stated explicitly because it deviates from a literal reading of the brief:** the existing 10-step onboarding wizard (`onboarding.tsx`) already has a "Family" step that today asks for marital status + a dependents count — the exact fields the Foundation Reconciliation just marked deprecated. Rebuilding that step into a *full* progressive family-workspace-building experience (add spouse with full details, add each child one at a time with DOB, add parents...) **inside onboarding** would make an already-long 10-step wizard longer, directly contradicting "never overwhelm users" and this project's own `FeatureGapAnalysisReport.md` finding that onboarding friction is a real, measured risk.

**Resolution:** onboarding keeps a **single, lightweight** family step — three yes/no branches, nothing more:

```
┌─────────────────────────────────────────┐
│  Who's counting on you?                  │
│  This helps us tailor a few              │
│  recommendations later — you can add     │
│  full details anytime from Family.       │
│                                           │
│  Do you have a spouse or partner?        │
│  ○ Yes   ○ No                            │
│                                           │
│  Do you have children?                   │
│  ○ Yes   ○ No                            │
│                                           │
│  Do your parents depend on you           │
│  financially?                            │
│  ○ Yes   ○ No                            │
│                                           │
│              [ Continue → ]              │
└─────────────────────────────────────────┘
```

These three answers create **placeholder household member rows** (relationship_type set, details empty) so the app immediately knows to prompt for them later — but onboarding itself never asks for a spouse's income or a child's birthday. **The rich, progressive, one-person-at-a-time experience described in the brief lives in the Family workspace, reached post-onboarding, on the user's own schedule.** This is the single most important UX decision in this document, and it's the one most likely to get second-guessed — see `UX_REVIEW.md` for the explicit challenge to this call.

---

## Part 4: The Family Workspace

### 4.1 Family Home (`/app/family`)

The "building your family's financial profile" screen the brief asks for — a vertical list of people, not a form.

```
┌───────────────────────────────────────────────────┐
│  Family                                             │
│                                                      │
│  ┌─────────────────────────────────────────────┐  │
│  │  👤 You                          Complete ✓   │  │
│  └─────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────┐  │
│  │  💍 Spouse — Priya                Complete ✓  │  │
│  └─────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────┐  │
│  │  🧒 Child — not yet named      + Add details  │  │
│  └─────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────┐  │
│  │  + Add a parent who depends on you            │  │
│  └─────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────┐  │
│  │  + Add someone else                           │  │
│  └─────────────────────────────────────────────┘  │
│                                                      │
└───────────────────────────────────────────────────┘
```

Each incomplete placeholder card (from an onboarding "Yes") is visually distinct (dashed border, "+ Add details" CTA) from a fully-detailed member (solid card, name, a completeness checkmark) — the user always knows exactly what's left to do, and nothing is hidden behind a settings menu.

### 4.2 Add a Person — One Flow, Branches by Relationship

```
Tell us about your spouse
──────────────────────────
Full name          [___________]
Date of birth       [___________]
Why we ask: age affects joint retirement
timing and health-insurance premium
calculations — nothing else.

              [ Save & continue ]
```

```
Tell us about your child
──────────────────────────
Name                [___________]
Date of birth        [___________]
                                        (girl / boy — used only to check
                                        Sukanya Samriddhi Yojana eligibility,
                                        which is girl-child-specific by law)

If a daughter under 10 is entered → immediate inline callout:
┌─────────────────────────────────────────────┐
│ ✨ Your daughter is eligible for Sukanya      │
│ Samriddhi Yojana — a tax-free government     │
│ savings scheme for her future. We'll add     │
│ this to your recommendations.                │
└─────────────────────────────────────────────┘
```

```
Tell us about a parent who depends on you
──────────────────────────────────────────
Name                 [___________]
Relationship          Mother / Father
Do they have their    ○ Yes  ○ No  ○ Not sure
own health insurance?
Why we ask: if not, we'll show you whether a
separate policy for them saves you money on
premiums and taxes (it usually does).
```

Every field in every branch carries a one-line "why we ask," per the brief's explicit requirement — never a bare label with no context.

### 4.3 Person Detail (`/app/family/members/:id`)

A single person's page — their own mini financial picture, editable in place, no modal-within-modal nesting.

```
┌───────────────────────────────────────────┐
│  ← Family        Priya (Spouse)             │
│                                              │
│  Date of birth      12 Mar 1991             │
│  Relationship        Spouse                  │
│                                              │
│  Goals involving Priya          (2)          │
│    · House down payment                      │
│    · Priya's retirement                      │
│                                              │
│  Health coverage                             │
│    · Covered under Family Floater            │
│                                              │
│  [ Edit details ]        [ Remove from       │
│                            household ]        │
└───────────────────────────────────────────┘
```

---

## Part 5: Family Goals — Honest About What the Schema Can Do Today

**Named constraint (from `FutureCompatibilityAuditReport.md` Finding E, still open):** `goals` remains single-`user_id`-owned. There is **no** true multi-person joint goal in the certified schema today. The design must not promise one.

**Resolution:** every goal has exactly one **primary owner** (unchanged from today) plus a lightweight, purely presentational **"who this affects"** tag chosen from the household's members — stored as descriptive text/category on the existing goal, not a new ownership relationship. The UI language is "this is your goal, and it affects Priya and your daughter too" rather than "you and Priya jointly own this goal." This is an honest UX approximation of joint planning within the actual data model, not a UI lie about ownership the backend doesn't enforce.

```
┌───────────────────────────────────────────┐
│  New family goal                            │
│                                              │
│  What's this for?                           │
│  [ Priya's daughter's college ]              │
│                                              │
│  Who does this affect?     (multi-select)    │
│  ☑ You   ☑ Priya   ☑ Ananya                  │
│                                              │
│  Target amount    Target date                │
│  [________]        [________]                │
└───────────────────────────────────────────┘
```

`/app/family/goals` then lists every goal grouped by which household members it affects — a household-level *view*, computed by joining through `household_members`, exactly as `DatabaseDesignReport.md` designed it to work, not a new ownership model.

---

## Part 6: Family Dashboard

New dashboard section, reached from `/app/family` and surfaced as a card on the main `/app` dashboard.

```
┌─────────────────────────────────────────────────────┐
│  Family                                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │
│  │ Who depends  │ │ Education    │ │ Insurance    │     │
│  │ on me?       │ │ costs ahead  │ │ coverage      │     │
│  │              │ │              │ │              │     │
│  │ Priya · 2    │ │ Ananya:      │ │ 2 of 4       │     │
│  │ kids ·       │ │ college in   │ │ people        │     │
│  │ 1 parent     │ │ 11 years     │ │ covered       │     │
│  └─────────────┘ └─────────────┘ └─────────────┘     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │
│  │ Parents       │ │ Retirement   │ │ Emergency    │     │
│  │              │ │ readiness    │ │ readiness    │     │
│  │ Mother:       │ │              │ │              │     │
│  │ no own        │ │ 74% on       │ │ 4.2 months   │     │
│  │ insurance ⚠   │ │ track        │ │ covered       │     │
│  └─────────────┘ └─────────────┘ └─────────────┘     │
│                                                         │
│  Recommendations                                        │
│  ┌───────────────────────────────────────────────┐   │
│  │ Your daughter starts college in 11 years.       │   │
│  │ Current probability: 61%. Adding ₹2,500/mo      │   │
│  │ raises it to 82%.            [ See how → ]       │   │
│  └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Rule enforced across every card, per the brief:** one question, one answer, no vanity metrics. "Insurance coverage: 2 of 4 people covered" is immediately actionable (who's the other 2?) in a way a raw premium total never would be.

---

## Part 7: Government Schemes — Personalized, Never a List

`/app/family/schemes` reads `scheme_eligibility_rules` (certified Foundation data) against each household member's recorded age/relationship/tax status and buckets every scheme into exactly one of three states — never a flat catalog of nine schemes for the user to parse themselves.

```
┌───────────────────────────────────────────────┐
│  For your family                                │
│                                                  │
│  ✅ Eligible now                                 │
│    Sukanya Samriddhi Yojana — for Ananya         │
│    "She's 7. This scheme is only available       │
│     for girls under 10."         [ Learn more ]  │
│                                                  │
│  🟡 Potentially eligible                          │
│    Senior Citizens' Savings Scheme — for Mother   │
│    "She turns 60 next year and would qualify."    │
│                                                  │
│  ⚪ Not eligible                                  │
│    (collapsed by default — "Show 6 more" )        │
└───────────────────────────────────────────────┘
```

Not-eligible schemes are present (for transparency and future re-evaluation) but collapsed behind a disclosure, never shown expanded by default — directly satisfying "do not overwhelm users."

---

## Part 8: Family-Aware Recommendations

Every recommendation follows the exact shape the brief specifies, and maps directly onto the certified `recommendations` table's fields (`reasoning`, `confidence_score`, `alternatives_considered`, `assumptions_used`):

```
┌───────────────────────────────────────────────┐
│  Your daughter Ananya starts college in         │
│  11 years.                                       │
│                                                  │
│  Current probability: 61%                        │
│  ████████████░░░░░░░░  61%                       │
│                                                  │
│  Increasing your monthly investment by ₹2,500     │
│  raises this to 82%.                             │
│  ████████████████░░░  82%                        │
│                                                  │
│  Confidence: High — based on your recorded        │
│  income and current education-cost inflation       │
│  assumptions.                                     │
│                                                  │
│  Alternatives:                                    │
│  · Shift to a more aggressive allocation → 74%     │
│  · Do nothing → 61% (not recommended)              │
│                                                  │
│  [ Increase contribution ]   [ See full detail ]   │
└───────────────────────────────────────────────┘
```

No recommendation ever reads "Increase SIP" alone — every one names the person, the timeline, the current number, the projected number, and at least one alternative, per this document's own product philosophy and the brief's explicit example.

---

## Part 9: Empty, Loading, and Error States

**Empty — no household yet (new user, skipped onboarding's family step or answered all "No"):**
```
┌───────────────────────────────────────────┐
│         It's just you right now.            │
│   Add family members anytime — nothing      │
│      about your plan requires it.           │
│                                              │
│         [ Add a family member ]              │
└───────────────────────────────────────────┘
```
Never a blank page or an error — being single with no dependents is a normal, complete state, not a gap to apologize for.

**Loading:** skeleton person-cards (matching the existing dashboard's `StatSkeleton` pattern already in the codebase) — never a spinner-only screen, so the layout doesn't jump once data arrives.

**Error (e.g., failed to save a family member):**
```
┌───────────────────────────────────────────┐
│  We couldn't save Priya's details.           │
│  Your other family information is safe.      │
│              [ Try again ]                   │
└───────────────────────────────────────────┘
```
Errors are scoped to exactly what failed and explicitly reassure that everything else is untouched — a household is emotionally loaded data; a vague "something went wrong" is worse here than almost anywhere else in the app.

---

## Part 10: Accessibility

- Every family-member card is a semantic list item with a real heading (`<h3>{name}</h3>`), not a styled `<div>` — a screen reader user gets "Priya, Spouse, heading level 3" for free.
- The Sukanya-Samriddhi-eligibility callout and every "why we ask" microcopy is programmatically associated with its field via `aria-describedby`, not just visually adjacent.
- Color is never the only signal — the eligibility traffic-light (✅/🟡/⚪) always pairs an icon + text label ("Eligible now," not just green), satisfying this project's own `rules/ecc/web/coding-style.md` semantic-HTML-first standard and WCAG color-independence.
- The "who this affects" multi-select on a goal is a real `<fieldset>`/checkbox group, keyboard-navigable and announced as a group, not a custom div-based chip picker with no keyboard support.
- Reduced-motion: the recommendation probability bar's fill animation (`61% → 82%`) respects `prefers-reduced-motion` and jumps directly to the end state rather than animating, per this project's own existing motion conventions.

---

## Explicit Constraints Carried Forward From the Certified Foundation

1. **No true joint goal ownership** (Finding E) — approximated via a "who this affects" tag, not a real multi-owner entity. Flagged loudly here so implementation doesn't quietly try to invent a joint-ownership column mid-build.
2. **HUF is deliberately absent from this design.** Per `FeatureGapAnalysisReport.md`'s own verdict ("narrow reach, build later") and this document's "never overwhelm" principle, HUF has no onboarding presence and no Family-workspace card. It remains schema-ready (`huf_entities`, the `huf_entity_id` ownership columns) for a future, separately-designed, business-owner-targeted surface — not part of Milestone 2's UX.
3. **Nominees are per-asset, not per-person** — a family member can be *named* as a nominee on an asset (via the existing `nominees.name`/`relationship_type` fields), but there's no single "nominee summary" view per person in this design; that would require a new query pattern, not a new table, and is a reasonable Milestone 2 implementation detail rather than a Foundation gap.
