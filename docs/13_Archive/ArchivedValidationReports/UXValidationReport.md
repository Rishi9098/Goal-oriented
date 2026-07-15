# UX VALIDATION REPORT — Northstar (Milestone 1)

**Role:** Principal Product Designer / UX Architect / Senior QA Engineer
**Scope:** Complete UX audit of the live, running application — onboarding through Dashboard, Financials, Family, and Goals — from the perspective of a first-time user, evaluated against Nielsen's heuristics. This is not a code review; every finding below is backed by a live interaction captured against the running app at `localhost:8080` / `localhost:8000`, using one throwaway account created and deleted for this audit (`uxtest@example.com`), walked through the full 10-step onboarding wizard as a Married, Parent-of-2, high-income ($185k-salary-intended) professional carrying a $310,000 mortgage.

---

## OVERALL UX SCORE: 6.5 / 10

The visual design, copy voice, information architecture, and micro-interactions are consistently strong — this reads as a deliberately-designed financial product, not a template. But one systemic, high-frequency interaction defect in onboarding actively misrepresents a new user's finances on their very first Dashboard view, with zero warning. That single defect is severe enough to cap the score regardless of how polished the rest of the product is, because it strikes at the one thing a financial planning tool cannot afford to get wrong: showing the user their own numbers, correctly.

---

## FIRST IMPRESSION

The marketing landing page opens on a strong, specific headline ("The plan behind every financial goal") with a live-looking net worth chart and goal-probability preview — it does not look like a generic SaaS template. Sign-up asks for the minimum (name, email, password) and immediately sets expectations with a "10-step setup" badge before the user commits. The onboarding wizard that follows is the best-designed part of the product: every step explains *why* the question is being asked, uses sensible defaults, and visibly tracks progress. That first impression sours quickly once real financial data is entered, for reasons detailed in P0-1 below — a first-time user who fills in their salary the way the form visually invites them to will reach their Dashopard and see a "4/100" plan health score and "$0" income, despite having just told the product their actual numbers.

---

## MAJOR STRENGTHS

- **Progress transparency.** A "10-step setup" badge appears before the user even creates an account, and every subsequent step shows an explicit "N / 10" counter plus a progress bar. This is textbook "visibility of system status" and it is applied consistently for all 10 steps.
- **Trust-building, "why we ask" microcopy throughout onboarding.** Examples verified live: *"Used for income validation and occupation-specific benchmarks"* (Employment step), *"Age affects joint retirement timing and health-insurance premium calculations — nothing else"* (Family member detail page), and *"Expected returns use built-in defaults: Conservative 5% · Balanced 7% · Aggressive 9%. These can be adjusted in Settings after onboarding"* (Assumptions step). For a financial product, explaining the "nothing else" and disclosing the actual return assumptions used in projections is a genuine trust signal, not boilerplate.
- **Risk profile selection uses real information, not vague labels.** The three risk-profile cards show actual allocation splits and framing ("30/70 — stability over growth", "60/40 — moderate risk", "90/10 — growth-focused") instead of just "Conservative/Balanced/Aggressive" text. This lets a user make an informed choice without needing outside knowledge.
- **Progressive disclosure done right.** The "How many children?" field only appears after "Do you have children?" is answered "Yes", with a reassuring note that details can be added later. This keeps the form short for users who don't need every field.
- **State preservation on Back navigation.** Verified live: after answering Spouse=Yes, Children=Yes/2, Parents=No, clicking Back and then forward again preserved every value exactly — no re-entry required. This is real "user control and freedom" (Nielsen), not just a claim.
- **Family module intelligently seeds placeholder records.** Answering "Yes" to spouse/children in onboarding auto-creates "Spouse — Not yet named" and "Child — Not yet named" rows on the Family page with a clear "+ Add details" call to action, and the primary user's own row is marked "✓ Complete". This is a strong "recognition over recall" pattern — nothing needs to be recreated from memory.
- **Destructive action isolation.** On the Goal detail panel, "Delete this goal" is visually separated (a divider, muted styling, no button chrome) from "Run 10,000 paths" and "Optimize toward 80%" — reducing the chance of an accidental destructive click.
- **Keyboard focus states are strong and consistent.** Verified via direct keyboard Tab navigation on the Goals page: every focusable element (filter tabs, "New goal" button, search field) received a clearly visible, high-contrast blue focus ring.
- **Responsive layout holds up cleanly.** At a 390px-equivalent mobile width, the sidebar correctly collapses into a five-item bottom tab bar (Dashboard/Goals/Family/AI/More), and both the Dashboard's card grid and the Financials list reflow without any horizontal overflow or clipped text.
- **Error recovery on the account-creation form is solid.** A "Passwords do not match" error correctly preserves every previously-typed field value (name, email, both password fields) — nothing needs to be retyped after a failed submit at that specific step.
- **Live-updating feedback loop on Goal edits.** Changing a goal's monthly contribution and saving immediately re-ran the Monte Carlo probability (3.8% → 19.3%) and reflected it on both the detail panel and the Goals list card — a concrete, visible confirmation that the save took effect, even without a separate toast.

---

## CRITICAL UX ISSUES (P0)

### P0-1: Onboarding silently discards entered financial data with zero warning — across 5 of 10 steps

**This is the single most severe finding in this audit.**

Steps 4 (Income), 5 (Expenses), 6 (Cash & savings), 7 (Investments), and 8 (Debts & liabilities) each show an "Add [item]" mini-form (Type/Amount/Description fields + a small outlined "**+ Add**" button) directly above a large, prominent, gradient-styled primary button that reads **"Skip"** (when no item has been added yet) or **"Continue"** (once at least one item exists).

**Reproduced live, exactly as a real user plausibly would:**
1. On the Income step, typed `185000` into "Annual amount ($)" — confirmed present in the DOM.
2. Did **not** click the small "+ Add" button.
3. Clicked the large primary button (which read "Skip").
4. The wizard advanced to Step 5 with the typed `$185,000` gone — no confirmation dialog, no "you have an unsaved entry" warning, nothing.
5. Repeated identically on the Expenses step with `3200` typed and not added — same silent loss.
6. Confirmed via source inspection (`code/src/components/onboarding/list-steps.tsx`, `ListNavRow`): the "Continue/Skip" button is a fully independent `onClick` handler that only checks `items.length > 0` — it has no awareness of whatever is currently typed into the sibling add-form's local state.

**The real-world consequence, captured live on this exact account after finishing onboarding:**
- Dashboard: **Monthly Income: $0**, **Monthly Savings: $0**, **Plan health: 4 / 100**
- Financials page: **"No income sources yet."**
- Goal probability for "Retire at 60": **3.8%** — a number that would be dramatically different with the salary the user believed they had entered
- 30-year net worth projection chart: all three scenarios (Conservative/Balanced/Aggressive) trending to **-$1.18M to -$3.9M**

A user who is a well-compensated professional with a spouse, two children, and manageable debt is shown, on the very first screen after completing setup, that their household has no income and a 4-out-of-100 financial health score. There is no error state, no banner, no follow-up prompt anywhere that explains why — the only way to discover the cause is to independently notice the Financials page says "No income sources yet" and infer what happened during onboarding.

**Why this is P0, not P1:** it is 100% reproducible, it affects half of the onboarding flow (every list-based step shares the same component), the triggering action (typing an amount, then clicking the big obvious button instead of the small "Add" link) is an entirely natural mistake rather than an edge case, and the consequence is not cosmetic — it actively misrepresents the user's own financial reality on the product's core value proposition (accurate goal-probability planning) from the very first session.

---

## HIGH PRIORITY ISSUES (P1)

### P1-1: Form validation surfaces only one error at a time, with no per-field indicators
Submitting the account-creation form completely empty returns only *"Password must be at least 8 characters"* — it does not mention that Full Name and Email are also required, because the checks run sequentially and stop at the first failure (confirmed in `onboarding.tsx`: mismatch check, then length check, with no aggregation). None of the four fields receive a red border, an inline message, or an `aria-invalid` cue — only a single banner at the top of the form. A user with multiple problems must submit, fix one thing, submit again, fix the next thing, and so on.

### P1-2: The Edit Goal panel's Save/Cancel controls are not visible without scrolling
Opening "Edit" on a Goal renders an "EDIT GOAL" form (Name, Category, Target, Saved so far, Monthly, Years, Risk profile) directly above the goal's existing read-only summary (probability, Monte Carlo button, Optimization button, Delete) inside the same scrollable panel, with no visual break, sticky footer, or distinct card boundary between "the thing I'm editing" and "the thing I already saw." On first opening Edit, the Save/Cancel buttons are below the fold and require a deliberate scroll to reach — the audit's own question, "Can users understand Save?", is only answered once they scroll far enough to find it.

### P1-3: No success confirmation after saving Financials or Goal edits
Saving an edited Expense, Asset, Liability, or Goal produces no toast, snackbar, or checkmark confirmation — the only signal that the save succeeded is the number itself changing in place. This is workable when the user is staring directly at the field they just changed, but for the Goal panel in particular (where Save closes the whole edit form and returns to a summary view), a user who isn't specifically comparing before/after values has no explicit "Saved" moment to rely on.

---

## MEDIUM ISSUES (P2)

### P2-1: Category/type labels are inconsistent between onboarding and Financials
Onboarding shows humanized labels for the exact same underlying data ("Housing (rent/mortgage)", "Checking account — Chase", "Mortgage"). The Financials page, for that same data, shows the raw lowercase enum values instead ("housing", "checking", "mortgage"). A user who just finished a polished onboarding flow sees noticeably rougher formatting the moment they land on the page they'll use every day afterward.

### P2-2: Primary "move forward" button uses four different labels across ten steps
Across onboarding: **"Continue"** (Personal info, Employment), **"Skip"** (same steps, when declining), **"Skip" / "Continue"** (the five list-based steps, contextual), **"Save & continue"** (Goal step), **"Finish setup"** (Assumptions step, final). All of these do conceptually the same thing — commit this step's data and advance — but the terminology shifts four times without an obvious reason tied to the step's actual behavior.

### P2-3: The "How many children?" placeholder is visually indistinguishable from a real value
The field shows a grey "1" as placeholder text with no visual distinction (weight, color, icon) from what an actually-typed "1" would look like. Submitting it empty does correctly produce a clear, specific validation error ("Please enter how many children (1-10)."), so this does not cause data loss the way P0-1 does — but a user glancing at the field before submitting could reasonably believe "1" is already a saved default.

### P2-4: Financials' locked Category field has no visual "disabled" affordance
Once an Expense/Asset/Liability is in edit mode, its Category/Type field is functionally locked (confirmed: typing into it has no effect) and correctly carries the accessible label "Category (cannot be changed)" for screen readers. Visually, however, it renders with the exact same border, background, and text opacity as the fully-editable Amount field beside it — a sighted user gets no visual cue that this field can't be changed, only screen-reader users get the correct signal. This is the inverse of the more typical accessibility gap.

### P2-5: Landing page hero content fades in very slowly on first load
On first navigation to the marketing homepage, the hero headline and supporting content render at near-zero opacity for roughly 2–3 seconds before fully appearing — during that window the page looks close to blank apart from the top nav bar. This is a first-impression risk on slower connections or devices, though it does resolve correctly.

---

## MINOR ISSUES (P3)

- **Date-of-birth entry relies entirely on the unstyled native browser date input/picker**, with no custom affordance for quickly jumping to a birth year decades in the past. Functional and accessible, but not particularly fast to use for exactly the data type (date of birth) most likely to require jumping back 20–80 years.
- **Dashboard vs. Reports savings-rate rounding inconsistency** (documented previously in `FinancialsE2EValidationReport.md`, still present): Dashboard shows one decimal place ("78.5% of income"), Reports rounds the identical underlying number to zero decimals ("79% savings rate"). Cosmetic, not a data error.

---

## ACCESSIBILITY FINDINGS

- **Positive:** Yes/No family questions use real native `<select>` elements with correctly associated labels and option text (confirmed via the accessibility tree, not just visual inspection) — screen readers will announce these correctly.
- **Positive:** Keyboard focus is consistently visible with strong contrast across every element tested (filter tabs, primary buttons, search input) on the Goals page.
- **Positive:** The disabled Category field in Financials carries a correct, descriptive `aria-label` ("Category (cannot be changed)") even though its visual styling doesn't communicate the same thing (see P2-4) — screen reader users are, in this one instance, better served than sighted users.
- **Gap:** No field-level `aria-invalid` or inline error association was observed on the account-creation form; all validation feedback is a single top-of-form banner (see P1-1), which is workable for screen readers (since it's announced) but weaker for sighted low-vision users scanning for which specific field is wrong.
- **Not assessed:** full screen-reader-driven navigation (e.g., VoiceOver/NVDA) was not run end-to-end in this session; findings above are inferred from accessible names/roles/labels visible in the accessibility tree, not from an actual assistive-technology pass.

---

## TRUST FINDINGS

- **Undermined by P0-1:** the single biggest trust risk in the product today is that a new user's own numbers can be silently wrong through no fault of their own, with the product presenting a confident-looking "4/100 Plan health" score as if it were an accurate verdict. Trust in a financial planning tool depends entirely on the numbers being right, or on the product being honest when it doesn't have enough information — this does neither.
- **Strong, where it isn't undermined:** the Assumptions step's explicit disclosure of expected-return percentages, the Family member step's "affects joint retirement timing... nothing else" framing, and the Goal panel's transparent "3.8% current probability" / "0% funded" labeling (rather than hiding a bad number) all actively build trust by being specific and honest about what's known versus assumed.
- **Recommendations are explained, not just asserted:** the AI Copilot card on the Dashboard states its reasoning plainly ("Increasing monthly contributions could raise success probability above 70%"), and the (separately, previously validated) Family Recommendations feature discloses "what we used, and what we don't know yet" per recommendation — this pattern of showing the reasoning, not just a verdict, is a genuine trust asset once the underlying data is actually correct.

---

## NAVIGATION FINDINGS

- Left sidebar (Dashboard, Goals, Family, AI Copilot, Financials, Reports, Profile, Settings) is consistent across every app page tested, with a clear active-state highlight.
- "Plan health" score is persistently visible in the bottom-left of the sidebar on every page — a constant, ambient reminder of overall status (good "visibility of system status"), though its accuracy is only as good as the underlying data (see P0-1).
- Mobile breakpoint correctly collapses to a 5-item bottom tab bar (Dashboard/Goals/Family/AI/More) with no navigation items silently dropped — Financials, Reports, Profile, and Settings are reachable via "More".
- Breadcrumb-style "← Back to Family" link on the Family member detail page and "← Back to Family" on Family Recommendations both correctly return to their parent list — no dead ends encountered anywhere in this audit.

---

## MICROCOPY FINDINGS

| Location | Copy | Assessment |
|---|---|---|
| Sign-up | "Start building your financial plan — free forever." | Clear, friendly, sets a no-cost expectation upfront. |
| Employment step | "Used for income validation and occupation-specific benchmarks." | Professional, explains purpose without jargon. |
| Family step | "This helps us tailor a few recommendations later — you don't need to add every detail right now." | Reduces perceived commitment; genuinely reassuring. |
| Family member detail | "Age affects joint retirement timing and health-insurance premium calculations — nothing else." | Excellent — the explicit "nothing else" directly answers an unasked privacy concern. |
| Assumptions step | "These defaults power every projection. You can refine them any time in Settings." | Transparent, sets correct expectations about where projections come from. |
| Children count validation | "Please enter how many children (1-10)." | Clear, specific, actionable — a strong example of good validation copy. |
| List-step primary button | "Skip" (shown even while an amount sits typed but unadded) | **Actively misleading** — see P0-1. The word "Skip" tells the user nothing is happening, when in fact something they typed is about to be discarded. |
| Completion screen | "You're all set, [Name]! Your financial profile is ready." | Warm, personalized (first name extracted from full name), confidence-building close. |

---

## CONSISTENCY FINDINGS

- **Typography and spacing** are consistent across onboarding, Dashboard, Financials, Family, and Goals — consistent card padding, consistent label casing (uppercase, tracked-out field labels), consistent use of the cyan/blue gradient for primary actions.
- **Icons** are used consistently for their concept across pages (shield for goals/protection, wallet-style icon for cash/financial-health recommendations, trash icon for delete across Income/Expense/Asset/Liability rows and Family members).
- **Terminology drift** exists in two concrete places: category label casing (P2-1) and the primary-button label across onboarding steps (P2-2).
- **Empty states** are calm and on-brand where present ("No income sources yet." on Financials; "It's just you right now. Add family members anytime — nothing about your plan requires it." on Family) — appropriately low-pressure, not alarmist.
- **Loading states**: the account-creation and goal-save actions both show inline spinner icons on their respective buttons while in flight; no bare unstyled "Loading..." text was observed anywhere in this audit.

---

## HEURISTIC REVIEW (Nielsen)

| Heuristic | Assessment |
|---|---|
| Visibility of system status | Strong in onboarding (step counters, progress bar); weak at the moment it matters most — no signal when typed financial data is about to be discarded (P0-1), and no save-confirmation toast (P1-3). |
| Match between system and the real world | Strong — "10-step setup," plain-language field labels, real allocation percentages on risk profiles instead of jargon. |
| User control and freedom | Strong — Back navigation preserves state; Cancel is always present alongside Save; destructive Delete is visually isolated. Undermined once by P0-1, where the user has no way to recover data that was never actually captured. |
| Consistency and standards | Mostly strong; two concrete terminology drifts noted (P2-1, P2-2). |
| Error prevention | This is where the product is weakest — the one form interaction most likely to cause real harm (typing a dollar amount and clicking the wrong button) has zero prevention: no confirmation, no disabled state, no inline reminder. |
| Recognition rather than recall | Strong — auto-seeded Family placeholder rows, pre-filled sensible defaults throughout Goal/Assumptions steps. |
| Flexibility and efficiency of use | Adequate for a first-time flow; no shortcuts or power-user paths assessed, none appear necessary at this stage of the product. |
| Aesthetic and minimalist design | Strong — no visual clutter, consistent restraint in color use (semantic red/amber/green reserved for actual status signals). |
| Help users recognize, diagnose, and recover from errors | The one validation error message tested (children count) was excellent — specific and actionable. The account-creation form's single-error-at-a-time behavior (P1-1) is a real but lesser gap. P0-1 fails this heuristic outright: there is no error to recognize, because the system never tells the user anything went wrong. |
| Help and documentation | Onboarding's "why we ask" copy functions as effective inline documentation throughout; no separate help center or tooltip system was needed or missed. |

---

## QUICK WINS

1. **Disable, or visually de-emphasize, the primary "Continue/Skip" button on any list-based onboarding step whenever the add-form has unsaved, non-empty input** — or, at minimum, show a one-line inline warning ("You have an unsaved income source — add it or it will be discarded") before allowing the user to proceed. This single change resolves P0-1.
2. **Add a lightweight save-confirmation toast** for Financials and Goal edits (P1-3) — a small, low-effort addition given the underlying save calls already succeed correctly.
3. **Reformat Financials category/type labels** to reuse the exact same humanized label maps already defined in `list-steps.tsx` (P2-1) — the mapping data already exists, it's just not applied on the Financials page.
4. **Standardize the primary onboarding button label** to a single consistent verb across all ten steps (P2-2).
5. **Add a visual disabled treatment** (reduced opacity, lock icon, or grey background) to the Financials "cannot be changed" Category field to match its accessible state (P2-4).

## LONG-TERM IMPROVEMENTS

1. Aggregate all form-level validation errors into a single, itemized list (or per-field inline errors) rather than surfacing one message at a time (P1-1).
2. Redesign the Goal edit panel so the edit form and the read-only summary are clearly separated (e.g., the summary collapses or is visually de-emphasized while editing, with Save/Cancel pinned in view) (P1-2).
3. Investigate the landing page's hero fade-in animation timing/threshold so the page doesn't read as blank for multiple seconds on load (P2-5).
4. Consider a lightweight custom date-of-birth input (e.g., separate month/day/year selects, or a "years old" alternative entry mode) to make entering birth dates decades in the past faster than the native calendar widget (P3).

---

## RELEASE READINESS

The product's design language, information architecture, copywriting, and core interaction patterns (goal editing, family member management, risk-profile selection, progressive disclosure) are strong and release-quality. However, this audit found a systemic, 100%-reproducible defect spanning five of the ten onboarding steps that silently discards real financial data the user believes they have entered, with no warning of any kind, and produces a directly observable, materially false financial picture (Monthly Income $0, Plan Health 4/100) on the very first Dashboard view a new user ever sees. This is not an edge case — it is triggered by the single most natural interaction a new user will attempt (type a number, click the big blue button) — and it strikes directly at the credibility of a product whose entire value proposition is showing people accurate numbers about their own finances.

### Recommendation: **DO NOT RELEASE**

Scoped specifically to P0-1: this defect must be fixed (per Quick Win #1, a small and well-contained change) before this milestone reaches real users. Every other finding in this report — including all P1s — is real but does not rise to a release blocker on its own, and could reasonably ship with a committed follow-up plan. Once P0-1 is resolved and re-verified with the same live onboarding walkthrough used in this audit, this product is very close to release-ready; the P1/P2 items above are recommended pre-release polish, not hard blockers.
