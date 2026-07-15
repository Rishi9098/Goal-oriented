# Northstar Financial Planning Platform — Product Design Authority Review

**Reviewers:** Principal Product Designer · Senior UX Researcher · Behavioral Economist · CFP · Human-Centered Design Expert · Product Manager · Design System Architect · Information Architecture Specialist · Accessibility Expert · Cognitive Psychology Expert

**Method:** Live click-through of every screen (Dashboard, Goals, Family, Financials, Reports, Life Events, AI Copilot, Settings, Profile, Onboarding) plus direct reading of the actual rendered copy, form fields, and data shapes shown to users. This is a product review, not a code review. Every finding below is anchored to something a real user would actually see.

---

## 1. Executive Summary

Northstar has an unusually deep and technically ambitious back-end for a financial planning product — a Life Event Engine covering 17–18 real-world events, an Undo Engine, a Preview Engine, and multiple recommendation surfaces. That depth is rare and valuable. **But right now, the product is engineered like a ledger and designed like an afterthought.** A person going through marriage, a layoff, an inheritance, or a medical emergency does not experience "life events" in this product as a story about their life — they experience it as a form with a dropdown labeled `income_source_id` and a confirmation that says "1 record affected."

The single biggest problem is not any individual screen. It's that **the most powerful, most human-centric feature in the entire product (Life Events) is invisible everywhere else.** The Dashboard doesn't mention it. Reports doesn't mention it. Recommendations don't reference it. AI Copilot has never heard of it. A first-time user has no reason to ever discover the one part of this app that could make it feel alive and personal.

The second biggest problem is **anxiety by default.** A brand-new user, thirty seconds after finishing a ten-step onboarding interview, is shown "Plan health: 5/100" in the sidebar — on every single screen, forever, with zero explanation. That's not a financial planning tool building confidence; that's a product actively telling a new user they're failing, with no idea why.

The third biggest problem is **accounting language wearing a consumer costume.** "Net proceeds," "annual amount," "monthly payment," "record affected," "income_sources" (a raw table name, visible in the product) — this is the language of a general ledger, not a financial companion. A CFP would never open a client meeting by asking for a "net proceeds" figure; they'd ask "how much did you walk away with after the sale?"

None of this requires new architecture. The engine underneath is sound. What's missing is a design layer that translates what the system already knows into what a human being actually needs to hear, in the order a real advisor would say it.

---

## 2. Overall Product Score: **6.2 / 10**

| Dimension | Score | Notes |
|---|---|---|
| Functional completeness | 9/10 | Genuinely rare depth — most fintech MVPs don't have an Undo Engine or Preview Engine at all. |
| Information architecture | 5/10 | Modules exist in silos; the best feature (Life Events) is orphaned from the rest of the product. |
| Human-centered design | 4/10 | Forms are structurally correct but emotionally tone-deaf; no story, no celebration, no reassurance. |
| Behavioral psychology | 4/10 | Plan Health score creates anxiety without context; no progress narrative; no positive reinforcement loop. |
| Microcopy / language | 4/10 | Frequent leakage of backend/accounting vocabulary into consumer-facing text. |
| Consistency | 5/10 | Money formatting, date formatting, and terminology all diverge between Dashboard/Goals/Reports/Life Events. |
| Accessibility | 5/10 | Reasonable semantic base (labels, focus rings) but native `<select>`-heavy forms and color-only status signaling need work. |
| Competitive readiness (vs. Monarch/Copilot/YNAB/Origin) | 4/10 | Not yet close on polish, storytelling, or automation — but ahead on raw planning depth. |

---

## 3. Release Recommendation

### **GO WITH CHANGES**

The underlying capability is strong enough to ship, and none of the top problems require re-architecture — they require a design and copy pass. But shipping **as-is** to real users going through emotionally significant events (divorce, medical emergency, inheritance, death of a spouse) without addressing the P0 list in Section 4 risks real reputational and trust damage. Do not launch marketing around "AI Copilot" or "Life Events" until Sections 4, 5, and 7 are addressed — those are the two features most likely to be screenshotted and criticized.

---

## 4. Top 20 UX Problems (Ranked)

**P0 — Must fix before real users touch this**

1. **Plan Health score (e.g. "5/100") is shown with zero context, on every screen, permanently, starting the moment onboarding ends.** No tooltip, no breakdown, no "why," no path to improve. This is the single most anxiety-inducing element in the product.
2. **Life Events is completely disconnected from the rest of the product.** No mention on Dashboard, Reports, Recommendations, or AI Copilot. The best feature in the app is undiscoverable.
3. **Preview effects text leaks raw backend vocabulary**: "This will affect 1 record across income_sources." A real person does not think in "records" or "income_sources." This is the literal database table name shown to a consumer.
4. **History list uses database language, not human language**: "Applied," "Undone," "1 record affected." These are audit-log words, not financial-life words.
5. **Onboarding's assumptions step tells users adjustable settings live in "Settings"** — they do not. They live in Financials. This is a broken promise on a first-run screen, exactly when trust is most fragile.
6. **AI Copilot exposes an internal model badge ("GPT-Planner · 4o") to end users** and has zero awareness of Life Events, Goals changes, or Recommendations — it's a generic chatbot bolted onto a much smarter product.
7. **Consumers are asked to supply "Inflation Rate," "Tax Rate," and "Expected Return" percentages directly during onboarding.** Almost no consumer knows these numbers. This is an advisor's assumption, not a client's fact, and it's being asked backwards.
8. **No event ever explains consequences before commitment in plain language.** Preview says record counts, not "your monthly cash flow will go up by $1,500" or "your mortgage will be marked paid off."

**P1 — Fix before broad marketing / before this becomes the primary workflow**

9. **Money formatting is inconsistent across the product**: Dashboard/Goals/Life Events show full figures ("$115,000"); Reports abbreviates ("$45k", "$2.00M"). Same number, two different products.
10. **Date formatting is inconsistent**: Life Events shows "12 Jul 2026," Reports shows "July 12, 2026," onboarding uses a raw native date picker. Three formats, one company.
11. **Entity pickers are raw native `<select>` dropdowns even when there's only one option** — e.g., a user with exactly one income source still has to open a dropdown and pick the only item in it.
12. **No celebration anywhere.** Recording a new house, a marriage, a child, a payoff, an inheritance — all render identically to editing a phone number. There is no moment in this product that feels good.
13. **"Undone" status has no visual distinction from a routine incomplete state** — a gray pill identical in weight to "not started," when it actually represents "I changed my mind and reversed a real financial decision."
14. **Divorce, Death of a spouse (missing entirely — see Section 15), and Major Medical Event are treated with the exact same visual and emotional register as a Bonus.** No product this emotionally aware of life events should treat "you got a bonus" and "you're getting divorced" identically.
15. **No annual review, no timeline, no "this year in your financial life" — despite having every ingredient (Life Events + Reports) already built to construct one.**

**P2 — Important but not launch-blocking**

16. **"Export PDF" literally just calls `window.print()`.** It's not dishonest, but it over-promises relative to what a modern competitor (Monarch, Copilot) delivers as an actual generated report.
17. **Optional field groups in Life Event forms show every possible sub-field even when nothing has been entered**, rather than starting collapsed with a single "+ Add a down payment" affordance.
18. **Family, Recommendations (Dashboard "AI Copilot" card), and Family Recommendations are three separate surfaces with overlapping purposes** and no visible relationship to each other.
19. **No empty-state guidance connects modules** — e.g., Goals' empty state says "Add your first goal" but never mentions that a Life Event (Education Planning, Retirement) is a faster, more natural way to create one.
20. **Settings has two "Coming soon" cards (Notifications, Linked accounts) sitting at 60% opacity** — visually correct restraint, but it also means the product currently has no reminders, no digest, and no bank connections at all, which is a major gap for a 2025-era competitor set.

---

## 5. Life Event UX Review (All 17 + 1 Bonus Event)

General note before the per-event review: every event shares the same two structural weaknesses — **(a) the system asks for facts it should already know or should infer**, and **(b) the confirmation/preview language is generic and technical instead of specific and human.** These are called out per-event only where there's something *additional* to say.

### Financial

**1. Salary Raise**
- Name: ✅ Plain, understandable.
- Wording: "Income source" and "New annual amount ($)" are fine but sterile. A person doesn't think "income source," they think "my job" or "my paycheck."
- Unnecessary friction: the user must select which income source got the raise from a dropdown — even when they have exactly one. **Auto-select and skip the dropdown entirely if there's only one active income source**, showing it as a confirmation line instead ("Updating your Salary income").
- Missing inference: the system already knows the *current* annual amount. It should show "$95,000 → ___" inline, and even suggest common raise sizes (+3%, +5%, +10%) as tap targets instead of a blank number field.
- Preview: currently says "This will affect 1 record across income_sources." Should say: **"Your salary will increase from $95,000/yr to $115,000/yr — about $1,666/mo more take-home."**
- Consequence understanding: zero mention of what this does to goal probability, tax bracket, or savings rate — the exact numbers a real advisor would lead with.

**2. Job Change**
- Name: ✅ Clear.
- Four required fields (old income source, new employer, new occupation, new annual amount) is the right amount of *information*, but it's presented as a flat form, not a story. This is the single best candidate in the whole catalog for a **conversational three-line flow**: "Which job is ending?" → "What's the new one?" → "What will you make?"
- Missing inference: "new occupation" should default to the old occupation if the title didn't change (most job changes are the same title, new employer) — currently the field is empty and mandatory-feeling.
- Should ask, but doesn't: nothing about a gap in pay (severance, notice period, new job start date vs. old job end date) — a real advisor would ask this immediately because it affects near-term cash flow.

**3. Bonus**
- Name: ✅ Perfect — this is the one event name a normal 24-year-old would say out loud exactly as written.
- This is the best-designed event in the catalog: one required field, sensible optional defaults ("savings," "Bonus"). Model the rest of the catalog on this one's simplicity.
- Missing: no prompt to allocate it ("Save it, spend it, or split it?") — a huge behavioral opportunity (see Automation #14) that YNAB/Copilot-style products build entire features around.

**4. New Loan**
- Name: technically correct but "New Loan" reads like a bank statement line item, not something a person says. Most people would say "I financed a car" or "I took out a personal loan."
- Asking for **liability_type as free text** ("e.g. auto_loan, personal_loan, mortgage") is a real regression in humanity — this should be a small set of tap-to-choose chips (Car, Personal, Student, Other), not a text box asking the user to type a snake_case-flavored example.
- The linked-asset section ("What this loan funded") is smart and should be the default expectation, not a buried optional fieldset.

**5. House Purchase**
- Name: ✅ Clear and natural.
- This is one of the highest-emotion, highest-stakes moments in a person's financial life, and it's presented with the exact same visual weight as adding a $50 expense. There should be a distinct, celebratory confirmation state ("🎉 You're a homeowner").
- Down payment and mortgage terms in one flat form is a lot at once for what is, for most people, the single biggest transaction of their life. This should be **two short steps**, not one dense fieldset.
- Missing inference: if the user has exactly one large liquid asset (a savings account), it should be pre-selected as the down-payment source with an easy "change" affordance, not a blank dropdown.

**6. Home Sale**
- Name: ✅ Clear.
- "Net proceeds" is real-estate/accounting jargon. A normal person says "how much I walked away with" or "what I got after paying off the mortgage and fees." This field should be **computed, not asked**: sale price → minus remaining mortgage (already known) → minus an estimated agent fee (default 6%, editable) → proposed net proceeds, shown as a calculation the user confirms rather than a number they have to produce themselves.
- "Pay off this mortgage with the sale" checkbox defaulting to true is a genuinely good, quiet default — more of the catalog should work like this.

### Family

**7. Marriage**
- Name: ✅ Perfect.
- Asking for a spouse's exact date of birth as *required* the same day you're recording a marriage is oddly cold — a person just got married, and the form's first move is a demographic data requirement. Consider making this optional at record time with a gentle "add later" affordance, since the backend already tolerates it being missing in some paths.
- No mention anywhere in the flow of the *actual* planning implications (tax filing status change, combined household goals, insurance) — a real advisor's very next question after "congratulations" would be about combining or keeping finances separate. This event ends the moment the record is saved; a CFP would never end the conversation there.

**8. Birth of Child**
- Name: ✅ Perfect, warm, human.
- The optional college-fund creation is exactly the kind of "the system should think for you" feature this product needs more of — but it's opt-in and buried in a fieldset labeled "(optional)" with no default numbers. This should be the opposite: **shown by default with a sensible pre-filled target** ("$120,000 by 2044, based on average tuition inflation — adjust or skip"), because most parents have never priced college and won't know what to type.
- This is a joyful event and is rendered with the same gray fieldset UI as everything else. This is the #1 candidate in the entire catalog for a genuinely celebratory confirmation moment.

**9. Adoption**
- Name: ✅ Correct, respectful, distinct from Birth of Child in labeling even though mechanically identical — good restraint, this matters emotionally even if the backend doesn't care.
- Same college-fund and celebration notes as Birth of Child apply.

**10. Divorce**
- Name: ✅ Clear, unavoidable, correctly blunt.
- This is the single most emotionally loaded event in the catalog and it currently has the *least* amount of care put into its presentation — one dropdown ("Spouse") and a submit button. There is no acknowledgment, no gentleness, no "we know this is hard" framing anywhere.
- No mention anywhere of the two real financial consequences a CFP would flag immediately: (a) beneficiary/insurance review, and (b) re-running every shared goal's assumptions. The backend's own notification system already generates these prompts elsewhere in the codebase — they need to surface **in this flow**, not as a disconnected notification days later.
- The word "Spouse" in the dropdown, immediately after selecting "Divorce," reads as cold. Even something as small as "Who is this affecting?" softens it.

**11. Dependent Parent**
- Name: reasonable but a normal person would say "my parent needs help" or "caring for a parent," not "Dependent Parent" — that's Census-form language.
- Asking "Has their own health insurance?" with options Yes/No/Not sure is good, appropriately real-world.
- No connection made to the Family module's own insurance recommendation engine at the moment of creation — a parent with no insurance should immediately see the insurance recommendation the backend is already capable of generating, right there, not on a separate page the user has to think to visit.

### Planning

**12. Retirement**
- Name: ✅ Clear.
- This is the single most overloaded form in the entire catalog: multi-select income sources, pension creation, two assumption fields, and a repeatable goal-contribution list, all in one screen. **This must be a short wizard, not a form.** Retirement is not a single moment; forcing it into one screen is the clearest violation of "match the form to the emotional weight of the event" in the whole product.
- Multi-select for "which income sources are ending" is a good, real-world-accurate mechanism — the execution (checkboxes) is fine, but it should default to *pre-selecting* any income source of type "salary," since that's almost always the answer.
- The repeatable "goal contributions" rows are the most advisor-like part of the whole product (a real CFP absolutely would ask "which goals need their contribution updated now that income is changing") — but zero guidance is given on *why* you'd want to do this or what a sensible new number looks like.

**13. Education Planning**
- Name: ✅ Clear, though it's really "start a college fund" or "start a savings goal for school" in normal language.
- This event and Goals (the main nav item) do the same thing (create a goal) through two completely different UIs with different field sets and no cross-navigation. A user who has already found "Goals" has no reason to ever discover this exists as a Life Event, and vice versa. **This is a duplicate front door to the same room.**

### Advanced

**14. Inheritance**
- Name: ✅ Perfect, exactly what a person would say.
- Genuinely well-designed: one required field, sensible optional income step. This is a strong template.
- Missing the single most obvious behavioral opportunity in the entire catalog: **an inheritance is the #1 moment to recommend paying off high-interest debt or topping up an emergency fund**, and the backend's own recommendation engine already reads assets live — this should be surfaced immediately in the same flow, not discovered later by accident on the Dashboard.

**15. Major Medical Event**
- Name: reasonable, though "Medical Emergency" or "Unexpected medical expense" is what a person in the moment would actually type into a search bar.
- This event is dense (new/existing expense, lump sum funding, financing loan) presented with zero acknowledgment that this is often the most stressful and financially disorienting event in the whole catalog. There is no reassurance copy anywhere ("we'll help you figure out how to cover this" / "you're not alone in this").
- This is also the clearest case in the entire product of **the system asking the user to do math it should do for them**: the user is expected to decide the lump-sum-vs-financing split themselves. Given known liquid assets and the expense amount, the system should propose a split ("Cover $3,000 from savings, finance the remaining $7,000") rather than presenting three blank optional groups.

**16. Business Start**
- Name: ✅ Clear.
- No required fields at all is philosophically correct (a business can start with zero capital), but the resulting form is oddly empty-feeling with three big optional fieldsets and nothing filled in — it needs framing copy ("Tell us as much or as little as you know right now") so it doesn't look broken.
- "Liability type: other" for a business loan (an acknowledged backend placeholder) surfaces to the user as a generic, unhelpful label wherever this liability appears later (Financials, Reports) — this will read as a bug to a real user even though it's a documented limitation.

**17. Business Sale**
- Name: ✅ Clear.
- Mirrors Home Sale's proceeds-destination pattern well (good consistency). Same "net proceeds" jargon critique applies.
- "New employment status" dropdown appearing as a generic afterthought undersells what is often the single biggest identity and cash-flow transition in someone's life (from business owner back to employee, or into retirement). This deserves its own beat in the flow, not a fourth optional fieldset.

### Bonus / Uncatalogued: **Loan Payoff**

- This event exists in the product but wasn't in scope from the brief — worth flagging on its own. Its name is fine, but it's functionally indistinguishable from what a user might expect "New Loan" or "Financials" to already handle, and it raises the IA question directly: **why is paying off a loan a "Life Event" but adding one to Financials directly is not treated the same way?** The line between "this is a life event" and "this is just editing my numbers" is not consistent across the catalog (see Section 8).

---

## 6. Financial Planning Review (CFP Perspective)

**Would a real advisor collect information this way?** No. A CFP conducts discovery in a specific, well-established order: goals and values first, then cash flow, then assets/liabilities, then risk tolerance, then planning assumptions last (and even then, assumptions are the advisor's professional judgment, offered to the client for reaction — not a blank field the client is expected to fill in). Northstar's onboarding does the opposite: personal info → family → employment → income → expenses → cash → investments → debts → *first goal* → assumptions. Goals arrive ninth, assumptions arrive tenth. **A real advisor leads with "what are you trying to achieve," this product ends with it.**

**What would an advisor ask that this product doesn't?**
- Time horizon and flexibility on each goal ("is this date firm, or could it move?")
- Existing insurance coverage as a first-class topic, not something only visible inside the Family module
- Liquidity needs / emergency fund adequacy as an explicit, named concept (it exists implicitly in the Family dashboard's "emergency" card, but is never surfaced as a *goal* a user can see progress against)
- Debt payoff strategy and prioritization (avalanche vs. snowball) — the Life Event catalog has "Loan Payoff" as an action, but nothing helps a user decide *which* loan to pay off first
- Beneficiary and estate basics — completely absent, despite Divorce, Marriage, Birth of Child, and Inheritance all being moments where a real advisor would raise this

**What feels unrealistic?**
- Asking a consumer for their own inflation rate and expected investment return assumptions. No real advisory relationship works this way; the advisor proposes defaults and the client can override them, not the reverse.
- Treating every life event as a single-sitting form. Real financial conversations happen in stages, over multiple sessions, often with the advisor doing follow-up. Nothing in this product supports "come back and finish this later" for anything beyond the top-level onboarding wizard.

**What's missing entirely that a CFP relationship always includes?**
- An annual review ritual
- A "here's what changed and why it matters" narrative after any major event
- Explicit tradeoff framing ("if you do this, X goal probability goes up but Y goes down")

---

## 7. Behavioral Psychology Review

- **Trust:** Undermined early by the assumptions-step's incorrect pointer to "Settings," and by "Plan Health: 5/100" appearing with no explanation. First impressions in financial products are disproportionately important — users are already anxious about money; a tool that appears to not know its own settings location, or that opens with a failing grade, reads as untrustworthy before any real usage has happened.
- **Confidence:** The product never tells a user they did something right. There is no positive reinforcement anywhere in the Life Events flow — recording a raise, a home purchase, or an inheritance all produce the same flat, neutral acknowledgment.
- **Motivation:** Goals show probability percentages, which is good, quantified feedback — but nothing connects "I just recorded a raise" to "and here's how that improved your retirement goal's odds," even though the data to say exactly that already exists one click away. This is the single highest-leverage behavioral fix available (see Automation #1).
- **Anxiety:** The Plan Health score, shown everywhere with no context, is the primary anxiety driver in the product. A secondary driver is the amount of financial vocabulary (net proceeds, annual amount, monthly payment) that assumes fluency most users don't have — every unfamiliar word is a small tax on confidence.
- **Decision fatigue:** Long flat forms (Retirement, House Purchase, Major Medical Event) present five to eight decisions at once with no sequencing or prioritization, when three to four of those decisions are "optional, only if this applies to you." Fatigue compounds with every additional visible-but-irrelevant field.
- **Progress visibility:** Onboarding shows step count (e.g. "4/10"), which is good. Nothing else in the product shows progress toward anything except individual goal probability. There's no sense of "your plan is more complete than it was a month ago."
- **Celebrating achievements:** Absent entirely. Paying off a loan, buying a first home, a goal crossing 100% funded — none of these produce any distinct celebratory state.
- **Reducing fear:** Divorce and Major Medical Event — the two most fear-adjacent events in the catalog — receive zero reassurance copy, zero softening, zero acknowledgment that these are hard moments. This is a missed opportunity to differentiate on empathy, which is exactly where a human CFP outperforms a spreadsheet.

---

## 8. Information Architecture Review

**Should Financials and Life Events both exist?** Not in their current form, side by side, with equal navigational weight and overlapping capability. Right now a user can add a new asset either through Financials (a raw create form) or through several Life Events (Bonus, Inheritance, House Purchase). There is no rule communicated to the user for *when* to use which. This will produce duplicate or missed data depending on which door the user happens to walk through.

**Recommendation:** Reframe **Financials as "Your Numbers"** — a read-mostly ledger view for reviewing and lightly correcting current state (typos, small updates) — and make **Life Events the primary way real changes get made.** Financials shouldn't disappear, but it should visually and functionally read as the "under the hood" view, not a parallel data-entry path competing with Life Events for the same job.

**Should Life Events become the primary workflow?** Yes, unambiguously. It's the only part of the product organized around what actually happens to a person, rather than around account types. It should likely be the **second nav item**, right after Dashboard, not buried between Financials and Reports.

**Should Dashboard highlight recent Life Events?** Yes — this is the single most obvious, lowest-effort IA fix available. The Dashboard currently has a Family summary card, a Goals card, and an AI Copilot card, but nothing surfaces "You recorded a Salary Raise 3 days ago." This is a trivial addition with an outsized trust/engagement payoff.

**Should Recommendations reference Life Events?** Yes. Right now recommendations (Dashboard's copilot card, Family's recommendation page) appear to materialize from nowhere. The backend already recomputes recommendations live off the same data Life Events change — the *only* missing piece is attribution copy: "Since your Home Sale, this recommendation no longer applies" or "Because of your recent Bonus, consider this." This turns a black box into a story.

**Should Reports include Life Event history?** Yes. Reports currently only shows goals and cash flow snapshots. A "This Year in Review" section built from Life Event history is one of the most natural, high-value additions imaginable, and nearly all the data already exists.

**Additional IA finding:** Family, Recommendations (via Dashboard's AI Copilot card), and Family Recommendations (a dedicated Family sub-page) currently look like three unrelated features to a first-time user, even though they likely share a common recommendation engine underneath. These need either a single unified "Recommendations" surface, or extremely clear differentiation copy — right now there is neither.

---

## 9. Navigation Review

- Current order: Dashboard, Goals, Family, AI Copilot, Financials, Life Events, Reports, Profile, Settings.
- **Life Events sits between Financials and Reports** — both lower-engagement, more utilitarian sections — burying the most emotionally resonant feature in the product in the "boring" half of the sidebar.
- **AI Copilot ranks above Financials and Life Events**, which is backwards given it currently has zero awareness of either. Nav position implies importance; right now the least-integrated feature has the most prominent placement.
- Mobile nav (5-slot bottom bar) currently prioritizes Dashboard, Goals, Family, Copilot, with Life Events relegated to the "More" overflow menu alongside Reports/Profile/Settings/Financials. **On mobile — arguably the primary device for "something just happened to me, let me log it" moments — Life Events is the hardest thing to reach.** This is backwards for the feature's actual use case (in-the-moment logging of real events).
- Suggested order: **Dashboard → Life Events → Goals → Family → Financials → Reports → AI Copilot → Profile → Settings**, with Life Events promoted into the primary mobile nav slots (replacing Family or Copilot as a primary slot, or expanding to accommodate it).

---

## 10. Automation Opportunities (50+)

Grouped by the type of thinking the system should be doing instead of asking.

**A. Auto-select when there's only one real choice**
1. Skip the income-source dropdown entirely (Salary Raise, Job Change) when the user has exactly one active income source.
2. Skip the liability dropdown (Loan Payoff, Home Sale mortgage payoff) when there's exactly one active liability of the relevant type.
3. Skip the asset dropdown (down payment source, funding source) when there's exactly one liquid asset.
4. Skip the household member dropdown (Divorce) when there's exactly one spouse-type member.
5. Auto-select the retirement goal in "goal contributions" when the user has exactly one retirement-category goal.

**B. Prefill from what the system already knows**
6. Show the current salary inline next to the "new annual amount" field ("$95,000 → ___"), not as a separate lookup.
7. Prefill "new occupation" (Job Change) with the current occupation, since most job changes keep the same title.
8. Prefill mortgage institution/description fields from the linked home asset's own institution, when available.
9. Prefill notes with an auto-generated human sentence the user can edit or accept ("Got a raise from $95,000 to $115,000"), instead of a blank optional field.
10. Prefill "asset description" fields for common purchases (vehicle, home) instead of leaving them blank.

**C. Compute instead of asking**
11. Compute Home/Business Sale "net proceeds" from sale price minus known mortgage balance minus an editable default agent-fee percentage, rather than asking the user to produce the final number themselves.
12. Propose a lump-sum/financing split for Major Medical Event based on current liquid assets vs. expense size, instead of three blank optional fields.
13. Auto-calculate a suggested down payment amount as a percentage of property value (e.g., 20%) as a starting point the user adjusts.
14. Offer an allocation suggestion for Bonus/Inheritance ("Save it / Spend it / Split it") with the split pre-computed based on emergency fund adequacy.
15. Auto-suggest a raise-based goal contribution bump (e.g., "put half your raise toward retirement") instead of a blank "new monthly contribution" field.
16. Default new loan "monthly payment" from balance + a reasonable term/rate assumption if the user doesn't know it offhand, rather than requiring an exact figure.

**D. Infer instead of interrogate**
17. Infer country/locale defaults from browser locale during onboarding instead of a manual dropdown.
18. Infer a starter risk profile from age/retirement horizon instead of asking a cold "Conservative/Balanced/Aggressive" choice with no guidance.
19. Infer effective tax rate from income + filing status + state instead of asking the user to type a percentage they don't know.
20. Infer a reasonable inflation/return assumption set entirely by default, and only expose it as an advanced, optional override — never as a first-class onboarding question.
21. Infer employer continuity across Job Change (if "new employer" matches a recent income source description, flag possible duplicate).
22. Infer whether a mortgage exists on the home being sold and pre-check "pay off this mortgage" without requiring the user to also manually pick the liability (already partially done — extend to full auto-detection).

**E. Hide what doesn't apply yet**
23. Collapse every optional fieldset to a single "+ Add [X]" affordance by default instead of showing empty labeled sub-forms for sections the user hasn't touched.
24. Hide the "goal contribution" section entirely (Salary Raise, House Purchase, Retirement) when the user has zero goals, rather than showing an empty, unusable dropdown.
25. Hide multi-entity selectors entirely when the relevant entity list is empty, replacing with a short explanatory line instead of "Nothing available."
26. Hide the "institution" and "description" micro-fields behind a single "add more detail" toggle across every event that has them (nearly all of them).

**F. Recommend proactively at the moment of relevance**
27. Immediately after Inheritance or Bonus, surface a "pay off high-interest debt" recommendation inline, using the same logic already computed by the recommendation engine elsewhere.
28. Immediately after Dependent Parent, surface the insurance recommendation the Family module can already generate, inline in the same flow.
29. Immediately after any event that changes monthly cash flow, show updated goal probabilities inline in the confirmation, not just "1 record affected."
30. After Major Medical Event, proactively suggest reviewing/increasing the emergency fund goal.
31. After Home Sale/Business Sale, proactively suggest a "what to do with this windfall" step, mirroring Bonus/Inheritance.
32. After recording a raise, suggest increasing the retirement goal's contribution by a computed amount, with one tap to accept.

**G. Reduce redundant entry across the product**
33. Auto-detect duplicate-looking entities across Financials and Life Events (e.g., two "salary" income sources within days of each other) and prompt to merge/replace rather than silently allowing duplicates.
34. Let a user log a life event directly from the Dashboard's suggestion feed ("Looks like your mortgage balance dropped — did you make an extra payment or pay it off?") instead of requiring them to navigate to Life Events cold.
35. Cross-link Goals' "Education" category directly to the Education Planning life event (and vice versa) so the same underlying action isn't discoverable through two disconnected UIs.

**H. Smarter defaults for dates and time**
36. Default "date it happened" to today (already done) but also offer one-tap "last week / last month" chips for common lag between event and entry.
37. For Retirement specifically, offer a "phased retirement" date range instead of forcing a single point-in-time event, since real retirements are rarely a single day.

**I. Smarter presentation of choices that must remain**
38. Replace free-text "liability type" (New Loan) with a small set of tappable categories (Car, Personal, Student, Other) instead of a text input with an example string as a placeholder.
39. Replace native `<select>` entity pickers with a searchable, avatar/icon-bearing list once a user has more than ~5 items in any list (assets, liabilities, goals, family members).
40. Turn the two-step "pick event → fill form" flow into a single conversational input for the simplest events (Bonus, Inheritance, Loan Payoff) — "I got a $5,000 bonus" parsed directly, form fields shown only for confirmation.

**J. System-computed summaries instead of user-produced ones**
41. Auto-generate the Preview line as a specific, human sentence per event type (see Section 11) instead of one generic template across all 18 events.
42. Auto-generate History row subtitles as human sentences ("Salary went from $95,000 to $115,000") instead of "1 record affected."
43. Auto-generate a one-line "what this means for your plan" sentence on every confirmation, computed from the actual before/after goal probability delta.

**K. Reduce onboarding friction specifically**
44. Make the 10-step onboarding resumable and skippable-and-returnable at a granular level (already skippable per-step, but there's no way to jump back into "finish this later" from the Dashboard once abandoned).
45. Move "Assumptions" to be system-generated with sensible defaults shown once, up front, framed as "here's what we're assuming — change it if you want" rather than a required data-entry step.
46. Reorder onboarding to ask "what are you trying to achieve" (goals) before asking for exhaustive account-by-account financial detail, matching real advisor discovery order.
47. Let users import at least starter numbers ("roughly $X in savings") instead of requiring precise figures at first pass; precision can come later.

**L. Cross-module intelligence**
48. Feed Life Event history into the Reports "Goal Breakdown" as annotations ("probability jumped after your raise on 7/12").
49. Feed Life Event history into AI Copilot's context so it can answer "what's changed recently in my plan?" using real history instead of generic canned replies.
50. Feed Family module completeness gaps (e.g., a spouse added via Marriage with no birthdate) back into a single, prioritized "finish setting up your plan" checklist surfaced on the Dashboard.
51. Use Plan Health score deltas, not just the raw number, to drive Dashboard messaging ("+8 this month" is motivating; "5/100" alone is demoralizing).
52. Recommend the *next* likely life event based on catalog gaps and existing data (e.g., a user with a mortgage and no life insurance step ever recorded gets a gentle nudge).

---

## 11. Microcopy Review

| Location | Current copy | Problem | Suggested |
|---|---|---|---|
| Life Events preview | "This will affect 1 record across income_sources." | Raw table name, plural, technical | "Your Salary income will go from $95,000/yr to $115,000/yr." |
| Life Events history | "Applied" / "1 record affected" | Audit-log language | "Recorded" / "Updated your salary" |
| Life Events history status | "Undone" | Flat, no acknowledgment of the action taken | "Reversed" with a short reason shown |
| Salary Raise field | "New annual amount ($)" | Cold, accounting-flavored | "What's your new salary?" |
| Home/Business Sale field | "Net proceeds ($)" | Real-estate/accounting jargon | "How much did you walk away with?" (or compute it — see Automation #11) |
| New Loan field | "Liability type" + placeholder "e.g. auto_loan, personal_loan, mortgage" | Shows snake_case internal values as an example | Tappable categories: Car, Personal, Student, Home, Other |
| Onboarding assumptions | "These can be adjusted in Settings after onboarding." | Factually wrong — lives in Financials | Fix the pointer, or better, remove the need to ask at all |
| AI Copilot header | "GPT-Planner · 4o" | Internal model name leaked to consumers | Remove entirely, or replace with a plain "Powered by AI" |
| Reports | "Export PDF" | Overpromises vs. actual `window.print()` behavior | "Print / Save as PDF" (honest) or actually generate a PDF |
| Dependent Parent event name | "Dependent Parent" | Census-form language | "Caring for a Parent" |
| Major Medical Event name | "Major Medical Event" | Clinical, distant | "Medical Emergency" or "Unexpected Medical Expense" |
| Sidebar | "Plan health / 5 /100" | No context, no explanation, appears everywhere | Add a tooltip/breakdown minimum; ideally reframe entirely (see P0 #1) |
| Undo conflict copy | "Undo anyway, discarding those later changes too" | Actually well written — a rare example of clear, honest, human copy | Keep as the house style to replicate elsewhere |
| Family Dashboard card | "Family — just you right now" | Genuinely good, warm, human copy | Keep as the house style to replicate elsewhere |

---

## 12. Consistency Review

| Aspect | Dashboard | Goals | Financials | Life Events | Reports |
|---|---|---|---|---|---|
| Money format | Full ("$115,000") | Full | Full | Full | **Abbreviated ("$45k", "$2.00M")** ❌ |
| Date format | — | Year only (target date) | — | "12 Jul 2026" (short month) | "July 12, 2026" (long month) ❌ |
| Status pill colors | success/warning semantic tokens | success/warning semantic tokens | — | success (Applied) / neutral (Undone) | emerald-400/amber-400/red-400 **raw Tailwind colors, not the shared semantic tokens** ❌ |
| Terminology for "how likely" | "% likely" | "% likely" | — | — | "success rate" ❌ (same concept, different word) |
| Empty-state tone | Warm ("No goals yet.") | Warm | — | Neutral ("No life events recorded yet.") | Neutral | 
| Icon system | lucide-react, consistent | consistent | consistent | consistent | consistent |

The Reports module is the clearest outlier across nearly every axis — it appears to have been built with a slightly different visual and copy vocabulary than the rest of the app (raw Tailwind color classes instead of the shared semantic design tokens, abbreviated currency, long-form date, and "success rate" instead of "% likely"). This is the single fastest consistency win available: **bring Reports' formatting functions in line with the rest of the app.**

---

## 13. Accessibility Review

- Native `<select>` elements are used extensively for entity pickers across every Life Event form. This is accessible by default (keyboard + screen reader support), which is good — but as lists grow (many assets, many goals), native selects become a poor experience for all users, sighted or not, and should evolve into a proper combobox pattern with visible labels, not just an accessibility checkbox.
- Status is frequently communicated by color alone (success/warning pill colors, red/amber/emerald percentage text in Reports) without a redundant text or icon cue in every instance — this is a real risk for color-blind users and should be audited screen-by-screen.
- Required fields are marked with a red asterisk in Life Events forms — good — but the asterisk alone is a weak signal for screen reader users unless paired with `aria-required`/`required` attributes consistently (spot-checked as present in the field renderer, which is good; verify it holds for every field kind, not just text/number).
- The Delete Account "type DELETE to confirm" pattern is a strong, deliberate friction point for a genuinely destructive action — good, appropriate use of friction exactly where it belongs.
- Focus rings are visible and consistent (`focus-visible:ring-2`) across primary interactive elements — a real strength, keep this standard as new components are added.
- No skip-to-content link was observed for keyboard users navigating the persistent sidebar before reaching page content — worth adding given the sidebar is long and present on every route.

---

## 14. Quick Wins (Under 1 Hour Each)

1. Fix the onboarding assumptions step's incorrect pointer from "Settings" to "Financials."
2. Remove the "GPT-Planner · 4o" model badge from the AI Copilot header.
3. Change Life Events preview copy from "affect N records across X" to a generic-but-better "This will update N of your records." (a full per-event human sentence is a medium effort item, but this alone removes the raw table name).
4. Change History row language from "Applied"/"record affected" to "Recorded"/"update made."
5. Align Reports' currency formatting with the rest of the app (stop abbreviating to "k"/"M").
6. Align Reports' date formatting with Life Events' date formatting (pick one format, use everywhere).
7. Replace Reports' raw Tailwind color classes (`text-emerald-400` etc.) with the shared semantic tokens used elsewhere (`text-success`, `text-warning`).
8. Rename "Dependent Parent" event label to "Caring for a Parent" in the picker (data value can stay the same).
9. Rename "Major Medical Event" event label to "Medical Emergency" in the picker.
10. Replace New Loan's free-text "liability type" placeholder text with a shorter, less snake_case-flavored example, or convert to a small preset list.
11. Add a one-line tooltip to the Plan Health score explaining what it measures, even before a fuller redesign.
12. Add "Life Events" as a Dashboard link/card, mirroring the existing Family card pattern (data plumbing likely already exists via the same list endpoint).
13. Fix "Export PDF" label to "Print / Save as PDF" to match actual behavior honestly.
14. Change "success rate" in Reports to "% likely," matching Goals/Dashboard wording for the identical concept.

---

## 15. Medium Improvements

- Rebuild the Life Events Preview and History copy generation as per-event human sentence templates (Section 11), not one generic message shared across all 18 events.
- Collapse every optional fieldset in every Life Event form to a collapsed "+ Add" affordance by default.
- Add a "Recent Life Events" module to the Dashboard, and a "This Year" section to Reports, both sourced from existing Life Event history data.
- Auto-select single-option entity pickers across the whole Life Event catalog (Automation items 1–5).
- Add attribution copy connecting Recommendations to the Life Event that produced or removed them.
- Add a genuinely celebratory confirmation state for House Purchase, Birth of Child/Adoption, Marriage, and any goal reaching 100% funded.
- Add reassurance copy specifically to Divorce and Major Medical Event flows.
- Convert Retirement from a single dense form into a short multi-step flow matching the emotional and decision weight of the event.
- Unify Family, Dashboard Recommendations, and Family Recommendations into one coherent recommendations concept with a single shared visual language, or clearly differentiate their purposes with copy.

---

## 16. Major Product Improvements

- **Make Life Events the organizing principle of the entire product**, not a nav item among many. The Dashboard, Reports, Recommendations, and AI Copilot should all be able to say, in plain language, "this changed because of that event."
- **Redesign the Plan Health score entirely** — from a bare, unexplained number into a transparent, encouraging, trend-aware metric with a visible breakdown of what's driving it and a clear next action to improve it.
- **Build a true Annual Review** — a once-a-year, guided, advisor-style walkthrough of everything that changed, everything upcoming, and everything worth reconsidering, built almost entirely from data the product already has.
- **Give AI Copilot real context** — recent Life Events, goal changes, recommendation history — so it can answer "what happened to my plan this year?" instead of only handling generic, stateless financial questions.
- **Replace assumption-gathering with assumption-proposing** across onboarding and Financials — the system should state its defaults confidently and invite correction, not interrogate the user for numbers they don't know.
- **Build a real timeline/story view of a person's financial life** — every Life Event, every goal milestone, every major recommendation acted on, on one scrollable narrative, which is the single most differentiated thing this product could build given what already exists underneath.

---

## 17. Future Vision

If Northstar became the best personal financial planning platform in the world, it would stop feeling like software you *operate* and start feeling like a financial life you *narrate* — where the product already knows most of what's true about you, asks only what it genuinely can't infer, and responds to every real event in your life the way a trusted advisor would: with a plain-language explanation of what changed, why it matters, and what — if anything — you should do next.

It would have a living timeline of a person's entire financial story — the raise, the marriage, the house, the child, the layoff, the inheritance, the parent who needed care, the business that started and the one that sold — each rendered as a real chapter, not a database row. Recommendations wouldn't feel like they came from nowhere; they'd visibly trace back to the moment in your life that triggered them. Undo wouldn't feel like a database rollback; it would feel like the product's way of saying "we've got your back, even when you change your mind." Plan Health wouldn't be a demoralizing number on day one; it would be a confidence score that visibly climbs as you tell the product more of your real story, framed the way a good coach frames progress — always forward, never a grade.

It would know, without being told twice, that you have exactly one mortgage, exactly one spouse, exactly one retirement goal — and it would stop asking you to confirm things it already knows, reserving your attention for the handful of decisions that actually require a human judgment call: how much of this bonus to save, whether this house is worth stretching for, how to split an inheritance between debt and dreams.

And it would never forget that behind every one of those seventeen life events is a real person — sometimes celebrating, sometimes grieving, sometimes terrified — and that the difference between a tool people tolerate and a tool people trust with the story of their life is not a bigger feature set. It's whether the product remembers, at every single screen, that it's talking to a human being.
