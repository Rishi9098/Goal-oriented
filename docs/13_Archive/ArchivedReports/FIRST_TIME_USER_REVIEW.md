# First-Time User Review — Northstar Onboarding & Family Step

**Date:** 2026-07-06
**Method:** Genuine UI-only walkthrough via browser automation — no code or database inspection during the exercise itself. Registered a brand-new account ("Jamie Carter," India, married with 1 child and a dependent parent) and completed the full 10-step onboarding wizard through to the dashboard, then checked Profile and Goals.
**Scope actually reachable in the product today:** registration → onboarding (all 10 steps, including the new Family step) → Dashboard → Profile → Goals. There is no "Family" section anywhere in the app yet — see Finding 1, the most significant result of this review.

---

## Journey Log

1. Landing page → clicked "Get started" (top-right). Two competing calls-to-action exist on the landing page — "Build your plan" (hero) and "Get started" (nav) — both go to the same place, so no real harm done, but a first-time user has to guess they're equivalent.
2. Registration — straightforward. Saw "10-step setup" badge before even starting, which set an expectation of a long process.
3. Personal info (1/10) — filled DOB, gender, country (India), state.
4. **Family (2/10) — the step under review.** Answered Yes/Yes(1)/Yes to spouse, children, dependent parents.
5. Employment (3/10), Income (4/10), Expenses (5/10), Cash & savings (6/10, skipped), Investments (7/10, skipped), Debts (8/10, skipped), First goal (9/10), Assumptions (10/10) — completed normally.
6. Landed on "You're all set, Jamie!" → opened dashboard.
7. Checked Profile and Goals pages.

---

## Where I Hesitated

- **The "How many?" children-count field.** On first look, it displayed "1" in a way that read like a filled-in value. I clicked Continue without touching it, assuming 1 was already selected. I got a validation error ("Please enter how many children (1-10).") and had to scroll back up, notice the number was actually a *placeholder* (lighter gray, not a real value), type it myself, and resubmit. Small friction, but a real extra step for something that felt like it should have just worked, especially since "1" is also a very plausible real answer — the placeholder and a genuine default of 1 look nearly identical.
- **Two skip-worthy CTAs on the landing page** ("Build your plan" vs. "Get started") — I paused for a second trying to figure out if there was a difference before clicking either.

## What Was Confusing

- **"HOUSEHOLD: 2 adults" on the Profile page does not match what I told onboarding.** I answered Yes to spouse, Yes to 1 child, and Yes to a dependent parent — five people counting on me, by the app's own framing ("Who's counting on you?"). The Profile page's "Household" field says only **"2 adults."** No child, no parent, nothing. This is the single most confusing thing in the whole walkthrough: two different parts of the same app appear to have two different ideas of who's in my family, and neither view told me this might happen.
- **"Plan health: 4/100"** appeared immediately after finishing setup, with no explanation anywhere on the dashboard of what it means, why it's so low, or what to do about it. A number that low, shown that prominently, that fast, reads as alarming rather than informative.
- **The Net Worth Projection card's headline number ("$0") didn't match its own chart**, which visibly showed a curve rising into the tens of millions. I couldn't tell if this was a loading-state artifact or an actual bug from where I was sitting as a user — either way, it looked broken for a moment.
- **The Retirement corpus goal shows "3.8% Monte Carlo"** with no inline explanation of what "Monte Carlo" means or what 3.8% represents (a success probability, I inferred from context, but it's never stated), and no immediate next step offered for a number that low.

## What I Expected vs. What Happened

- The Family step's own copy told me: *"You can add full details anytime from Family"* and, specifically for children, *"You'll be able to add each child's name and details afterward in Family."* **I expected a "Family" section to exist somewhere in the app after onboarding. It does not.** The sidebar has Dashboard, Goals, AI Copilot, Reports, Profile, Settings — no Family. I have no way, as a user, to go add my child's name, confirm my spouse's details, or see the parent I said depends on me. The product made a specific, concrete promise during onboarding and there's currently nowhere to redeem it.
- I expected the "Household" summary on my Profile page to reflect the spouse/child/parent I'd just entered. It shows a flat "2 adults" instead — I expected consistency between the screen that asked the question and the screen that later summarizes the answer.

## Surprises

- Selecting **India** as my country did not change the currency symbol anywhere in the rest of onboarding. Every dollar amount field — income, expenses, cash accounts, investments, debts, goal target amount — is labeled with **"$"**, not "₹." I typed real Indian salary figures (₹12,00,000/year) into a field explicitly marked "ANNUAL AMOUNT ($)." Nothing stopped me, but it felt wrong the entire time, like the app didn't actually know or care which country I'd just told it I lived in.
- The **Investments step's own subtitle reads "Brokerage accounts, 401(k), IRA, and other investment holdings."** 401(k) and IRA are U.S.-specific retirement account types. As an Indian user, neither term means anything to me — I have no idea if I'm supposed to have one, or what an Indian equivalent would even be called.
- The **Assumptions step's "Tax Rate (%)" field defaulted to 22** with zero explanation — no mention of old vs. new tax regime, no link to how this number is actually used, and no acknowledgment that India has tax slabs rather than one flat rate. I had no idea whether 22% was a reasonable number for me or a placeholder I was supposed to override.
- The **"Social Security / Pension ($/mo)" field label mixes a U.S. program name ("Social Security") with a generic one ("Pension")** — confusing for anyone outside the U.S., since there's no Indian equivalent of "Social Security" specifically.
- Example placeholder text throughout used U.S.-specific institution names — "e.g. Chase," "e.g. Wells Fargo" — for Institution fields, even after I'd selected India as my country.

## Unnecessary Clicks

- The children-count validation error (above) cost one extra round trip: submit → error → scroll up to read it → scroll back down → fix → resubmit.
- No other genuinely wasted clicks — the rest of the wizard moved in a straight line with sensible Back/Skip/Continue options throughout.

## Financial Terms That Need Explanation (or Localization)

| Term | Where | Issue |
|---|---|---|
| 401(k), IRA | Investments step subtitle | U.S.-only account types, meaningless to a non-U.S. user |
| Social Security | Assumptions step | U.S.-only program name |
| Tax Rate (%) | Assumptions step | No context on what it represents, no regime awareness, no help text |
| Monte Carlo | Goals page badge | Never explained anywhere I saw; shown as a bare percentage with a technical name |
| Plan health | Dashboard | A score with no visible explanation of its scale, inputs, or what a "good" number looks like |
| $ currency symbol | Every amount field, every step | Doesn't follow the selected country — should localize to ₹ for India |

## Accessibility Concerns

- All Yes/No questions on the Family step and elsewhere use real `<select>` dropdowns and real `<input>`/`<label>` pairs — these behaved correctly with keyboard focus and are a genuine strength of this flow.
- The children-count conditional field appears/disappears based on the "Do you have children?" answer. When it appeared, focus did not move to it — a keyboard or screen-reader user would need to know to keep tabbing forward to discover the new field exists, rather than being taken there automatically.
- The validation error banner appeared at the very top of the card while my scroll position was lower on the page (mid-form) — I only knew it appeared because the whole page shifted. A screen-reader user relying on `aria-live` announcements would need the error to be announced regardless of scroll position; I couldn't verify from the UI alone whether that's the case, but the visual experience (error appears off-screen, page jumps) is worth a deliberate check.
- Color contrast throughout felt strong (light text on dark surfaces, clear focus rings on inputs) — no issues observed there.

## Overall Impression

The onboarding wizard itself — and the new Family step specifically — is calm, well-paced, and free of pressure. The three-question design works exactly as intended: fast, low-effort, no jargon in the questions themselves. The single biggest problem is that **the product makes a specific promise ("add full details anytime from Family") that the UI cannot currently keep**, and the **Household summary on Profile visibly disagrees with what I just told onboarding** — both are the kind of inconsistency that would make a real first-time user trust the app less right at the moment it most needs to earn that trust. The U.S.-centric financial vocabulary and currency symbol are the second most pressing issue, since they run through nearly every step and directly undercut a product that (based on what it asked me — India, tax rate, dependent parents) is clearly meant for an Indian audience.

**Test data note:** this walkthrough created one real account (`jamie.carter.firstuser@example.com`) in the local dev database. Per this task's "do not inspect the database" instruction, I have not queried or cleaned it up — flagging it here in case you'd like it removed.

---

## Addendum — Family Home Screen (Milestone 2 Task 5), 2026-07-07

**Method:** Full UI-only walkthrough via browser automation. Registered a new account ("Ananya Rao"), completed onboarding answering Yes/Yes(3 children)/Yes, then opened the newly-shipped Family Home screen (`/app/family`) for the first time.

**Does the information match onboarding?** Yes, exactly. Onboarding recorded 1 spouse, 3 children, 1 dependent parent (6 people total including self); Family Home's household summary read **"6 people · You · Spouse · 3 Children · Parent"** and the member list showed exactly those 6 rows, each correctly flagged incomplete except "You." This is the first time in this product's history that the screen that asks about family and the screen that later summarizes it have agreed — directly closing the gap this same document's original walkthrough (above) flagged as its single biggest problem.

**Does anything contradict another screen?** No. Profile's Household field (read-only since PCA-2) showed the identical 6 members with identical completeness state — cross-checked side by side.

**Does the screen answer the intended questions?**
- *Who's in my household?* — the member list, immediately, no clicks needed.
- *Who depends on me?* — the household summary line answers this in one glance ("3 Children · Parent" is unambiguous).
- *What should I do next?* — every incomplete member has a clearly-labeled "+ Add details" affordance; Quick Actions offers the two remaining add paths.
- *Are there risks / what recommendations exist?* — honestly deferred. The "Coming soon" section names exactly what's missing (Insurance status, Scheme eligibility, AI recommendations) rather than showing nothing or something fabricated. As a first-time user, this read as "the app is still being built out," not "the app is broken" — the wording made the difference.

**Hesitations:** none of real consequence. I initially expected tapping a member card to open a full editable form; getting a calm "coming soon" stub instead of a dead link or an error was a pleasant, non-jarring surprise rather than a point of confusion — the copy ("your existing family details are safe in the meantime") pre-empted the obvious worry.

**One thing worth a future look, not a blocker:** the "+ Add a parent who depends on you" and "+ Add someone else" Quick Actions currently lead to the same generic stub — a first-time user clicking "Add a parent" specifically might briefly expect the stub to at least acknowledge that intent (e.g., "We'll ask about your parent here soon") rather than a fully generic message. Minor, and appropriately deferred to Task 6, which will replace the stub with the real, relationship-specific forms.

**Test data note:** the test account (`task5-firstuser@example.com`) and its household/goal rows were created and fully cleaned up (deleted) after this walkthrough.

---

## Addendum — Add Family Member Flows (Milestone 2 Task 6), 2026-07-07

**Method:** Full UI-only walkthrough. Registered a new account ("Rohan Mehta"), answered Yes/Yes(1 child)/No in onboarding, then completed the spouse and child placeholders and added a new parent, all through the real (no longer stubbed) forms.

**The exact gap the previous addendum flagged is now closed.** Tapping "Spouse" and "Child" placeholder cards opened real, relationship-specific forms — not the generic stub. "Add a parent who depends on you" opened a form that immediately acknowledged the intent (its own page title read "Add a parent who depends on you," and the form asked parent-specific questions), directly resolving last addendum's note.

**Softened copy verified live, exactly as approved:** the child form's gender question read *"This helps us find scholarships and schemes that might apply — never required,"* never naming "Sukanya Samriddhi Yojana" mechanically at that point in the flow — matching `UX_REVIEW.md`'s required revision word-for-word.

**The SSY callout is genuinely alive, not decorative:** entering a daughter's details (Ananya Mehta, DOB 2019, Girl) produced *"Ananya Mehta meets the current criteria for Sukanya Samriddhi Yojana"* — a sentence built from the real backend's live eligibility service, not a canned frontend string. This was the single most reassuring moment in the walkthrough: the reason named the actual person and the actual scheme.

**Hesitation:** the native date input again showed the same day/month transposition quirk noted in the very first review of this product (typed 03/15, field showed 03/12) — a pre-existing browser input behavior, not something this task introduced or could reasonably fix without replacing the native date picker.

**Trust check:** after completing all fields, Family Home immediately reflected every change — no manual refresh, no stale data, no contradiction with what was just entered. The household summary line updated correctly at every step (2 people → 3 → 4).

**Test data note:** the test account (`task6-firstuser@example.com`) and all household/member/audit rows were created and fully cleaned up (deleted) after this walkthrough. Also independently confirmed, via a read-only database check, that adding/editing family members wrote exactly the expected audit log rows and left the account's one existing goal completely untouched (its `updated_at` timestamp predated every family change).

---

## Addendum — Family Member Detail (Milestone 2 Task 7), 2026-07-07

**Method:** Full UI-only walkthrough. Registered a new account ("Meera Iyer"), answered Yes/Yes(2 children)/No in onboarding, completed the spouse placeholder, then opened the now-complete member's detail page for the first time — the exact screen this task replaces.

**The read-only detail view is a genuine trust improvement over Task 6's interim behavior.** Tapping a complete member no longer drops straight into an edit form (which, on reflection from the previous review, always felt slightly presumptuous — "why are you asking me to re-enter what I just told you?"). Instead it showed a calm summary: name, relationship, date of birth, then two honestly-empty sections ("No goals tagged yet," "Not yet covered under any policy") that read as *forward-looking*, not broken.

**Edit felt exactly as expected.** Clicking "Edit details" opened the same familiar form from before, pre-filled — no re-typing anything. Cancel returned to the summary instantly with nothing lost.

**Remove was the moment I paid the most attention to, as it should be for family data.** "Remove from household" didn't pop a jarring modal — it calmly expanded into "Are you sure? [Yes, remove] [Cancel]" right where I was looking, the same pattern I'd expect from deleting anything else non-catastrophic in this app. That consistency mattered more than I expected it to: a heavier, modal-with-backdrop treatment here would have implied this action is scarier than it actually is (reversible-in-spirit via re-adding, per the product's own reasoning).

**Hesitation:** none of real consequence. The one thing I'd flag for a future pass (not a blocker): the removed person's card simply vanished from Family Home with no toast/confirmation of *what* just happened — a returning user who removed someone by accident has to trust their own memory of what they just clicked, rather than the app briefly confirming it. Minor, and consistent with how the rest of this product currently handles other silent-success actions (e.g. saving Profile).

**Test data note:** the test account (`task7-firstuser@example.com`) and all household/member/audit rows were created and fully cleaned up (deleted) after this walkthrough. Independently confirmed via read-only database queries: the removed member's row still existed with `is_active=false` (never hard-deleted), exactly the expected audit log rows were written for every action including the removal, editing one child left the other child completely untouched, and no duplicate member row was ever created across any of the edits performed.

---

## Addendum — Family Goal Tagging (Milestone 2 Task 8), 2026-07-07

**Method:** Full UI-only walkthrough. Registered a new account ("Anjali Rao"), onboarded with a spouse and one goal ("Family vacation fund"), completed the spouse's placeholder, then discovered and used the new Family Goals feature for the first time — approaching it the way a real user would, from the Family Home screen rather than a bookmarked URL.

**Finding the feature felt natural, not buried.** The old "Coming soon: Upcoming family goals" card on Family Home is now a real, live link — same spot, same wording almost verbatim, now clickable. That continuity mattered: nothing about the page's layout changed to announce the new feature, it just quietly became real, which is exactly how a returning user would want an anticipated feature to arrive.

**The mandatory disclosure is the single most important thing about this feature, and it held up.** The moment I checked a family member's box, before I even clicked Save, the sentence appeared: "This goal belongs to your account. Anjali Rao and Vikram Rao can see it if you share access, but their own contributions aren't tracked separately yet." Reading it live, before committing, made the "joint ownership" question feel answered rather than glossed over — I never had to wonder "wait, does tagging my spouse mean this is now *our* goal?" The sentence itself pre-empted the question.

**Grouped-by-member is the right mental model.** After tagging the same goal to both of us, it appeared under both "Anjali Rao" and "Vikram Rao" sections — at first glance this looked like it might be two goals, but the identical target amount and probability under both made it obvious at a glance that it's one goal shown twice, not duplicated. This is a case where a plainer, more literal layout (one list, tags as pills) might have been slightly less confusing on first look — worth watching if user feedback disagrees, not changed now.

**Hesitation, caught and fixed during this same review:** the first time I untagged my spouse and then reopened the tagging editor on the *same* goal row, the checkbox still showed him as checked — stale from before the change. I flagged this immediately rather than shipping it; it's now fixed (the editor re-syncs from the current server state every time it opens) and re-verified. Worth recording because it's exactly the kind of thing a real first-time user would notice and lose trust over ("wait, didn't I just remove him?") — good that it surfaced here instead of in the field.

**One honest rough edge, not fixed:** tagging the goal with *myself* produces the same disclosure sentence — "Anjali Rao can see it if you share access" — which reads a little oddly when "Anjali Rao" is the account owner reading their own sentence. Noted, not solved; a self-specific rewrite would be over-engineering for how rarely this combination will actually occur in practice.

**Test data note:** the test account (`task8-firstuser@example.com`) and all household/member/goal/audit rows were created and fully cleaned up (deleted) after this walkthrough. Independently confirmed via read-only database queries: the goal's owner, Monte Carlo probability, and on-track status were completely untouched by every tagging operation; the audit log held exactly one `family_goal_tag_changed` row per save, no more, no fewer; and the final `goal_household_members` rows matched the last on-screen state exactly, with no duplicates left behind from the earlier re-tagging.

---

## Addendum — Family Goals & Custom Inflation (Milestone 2 Task 9), 2026-07-07

**Method:** Full UI walkthrough as a parent. Registered a new account ("Priya Nair"), added a daughter ("Ananya," age 7), created an education-category goal ("Ananya college fund," $40,000, 10-year horizon), tagged it to Ananya via Family Goals, then opened the goal for the first time as a parent genuinely trying to plan for it.

**The prompt answered "why" before I could even ask.** Before I did anything, the goal already showed a plain-language projection using the standard 3% rate — so I never felt like the number was hidden or that I had to hunt for it. Then, right below it: *"Tuition, fees, and related costs have historically climbed faster than general prices — a flat inflation number can understate what you'll actually need."* That's exactly the concern a parent budgeting for college actually has, stated in one sentence, not buried in a tooltip.

**The most important thing this screen had to get right — did.** The line directly under the projection is unambiguous: *"This changes what we project this will cost — it does not change your Monte Carlo odds of reaching your current target above."* I set a custom rate (8%) specifically to see if my goal's "100% current probability" would change — it didn't, in the UI, in a fresh Dashboard visit, and in a fresh Reports visit, all three showing the identical figure. That consistency is what actually builds trust here, more than the sentence itself: the product did what it said it would (and, just as importantly, didn't do what it said it wouldn't).

**No suggested default, and that felt honest rather than incomplete.** The rate field started empty — no "8%" pre-filled, no placeholder implying a "normal" number. Given the reviewed source material genuinely doesn't have a verified education-inflation figure yet, an empty field with a clear label ("no suggested default; enter your own estimate") was the right call — a confident-looking pre-filled number would have been worse, not better, since it would have implied precision that doesn't exist yet.

**The SSY callout landed as a pleasant, well-timed surprise, not a non-sequitur.** Because Ananya is tagged to the goal and meets Sukanya Samriddhi Yojana's actual eligibility criteria, the same reason text I'd already seen once (when I first completed her profile) reappeared here, in context, right where I was already thinking about her education costs — reinforcing the same fact rather than repeating it as unrelated noise.

**Financial jargon check:** no "Calculation Context," "nominal/real value," "Monte Carlo Calculation Context," or similar internal terms leaked into any user-facing copy. "Projected cost," "annual inflation assumption," and "current probability" were the only technical-adjacent terms shown, and all three are self-explanatory in context.

**One real, live-caught bug, found and fixed before this report was written:** while verifying the SSY callout, I discovered `GET /family/members/{id}` had never actually populated `eligible_schemes` at all (only the create/update responses did) — meaning the callout I expected to see silently wouldn't have appeared for *any* tagged child, not just an edge case. Caught via direct API inspection, fixed (mirroring the exact same guard pattern already used for other dependent-derived fields on that same response), backed by two new permanent tests, and re-verified live afterward.

**Test data note:** the test account (`task9-firstuser@example.com`) and all household/member/goal/audit rows were created and fully cleaned up (deleted) after this walkthrough. Independently confirmed via a direct database query: `custom_inflation_rate` persisted correctly (0.08), and `probability`/`on_track` were byte-identical to the values recorded at goal creation — confirming the central guarantee of this task held in practice, not just in the automated tests.

---

## Addendum — Family Insurance (Milestone 2 Task 10), 2026-07-07

**Method:** Full UI walkthrough as a user with a dependent parent — the exact persona this screen exists for. Registered a new account ("Rohan Mehta"), added a mother ("Sunita Mehta") with insurance status "No" via the existing Add Family Member flow, then visited Family Insurance for the first time.

**The recommendation read like advice, not a warning.** The card led with what I could actually gain ("can unlock a tax deduction beyond what your own floater already covers"), not a red flag about something missing. That framing matters for a topic (a parent's health coverage) that can otherwise feel like a nag.

**The uncertainty was stated plainly, not hidden or overclaimed.** Because I hadn't entered Sunita's date of birth, the card said the deduction "could be as high as ₹50,000... not yet confirmed" — I immediately understood there was a bigger number I could unlock just by adding one more piece of information, without the product pretending to already know it.

**The disclosure was genuinely optional, not required reading.** "What we used, and what we don't know yet" stayed collapsed until I clicked it — the headline recommendation stood on its own for a first pass, and the full data trail was there when I wanted to check it (as I did, both as a first-time user being thorough and, separately, as a reviewer verifying the four required fields).

**The moment that built the most trust: adding a policy made the recommendation disappear.** I recorded a family floater covering Sunita, reloaded the page, and the recommendation card was simply gone — no lingering "you should still get her insured" message contradicting what I'd just done. A product that kept nagging after I'd acted would have undermined trust in every other recommendation it might show later.

**Financial jargon check:** no "80D," "recommendation_type," "confidence_score," or "calculation-lite" leaked into user-facing copy — those are internal/reviewer-facing terms only. The screen said "tax deduction," "standalone health policy," and "family floater" — all plain, and all terms the form itself already used when I added Sunita.

**Test data note:** the test account (`task10-firstuser@example.com`) and all household/policy/coverage rows were created and fully cleaned up (deleted) after this walkthrough. Independently confirmed via direct database queries: the policy and its coverage persisted exactly as entered, and the `recommendations` table (the pre-existing, unused-until-now infrastructure this task was instructed to reuse) has zero rows across the entire database — confirming the recommendation is genuinely computed fresh on every read, never persisted, exactly as designed.

---

## Addendum — Family Recommendations (Milestone 2 Task 11), 2026-07-07

**Method:** Full UI walkthrough as a user with two different kinds of dependents — a mother with no recorded insurance and a young daughter who happens to be eligible for a government scheme. Registered a new account ("Anita Kapoor"), added both, then visited the new Family Recommendations screen for the first time.

**Two completely different kinds of suggestions sat next to each other without feeling like a mismatched list.** One card was about tax-efficient health insurance for my mother; the other was about a government savings scheme for my daughter. They read as two independent, well-reasoned pieces of advice — not a jumbled feed — because each kept its own source's visual language (the insurance card's shield icon, the scheme card's institution icon) rather than being flattened into one generic template.

**Nothing implied a conflict where there wasn't one.** Both cards concerned my household, but neither said anything like "this may conflict with..." — because it doesn't. I didn't have to figure out on my own whether these two pieces of advice fought each other; the product's silence on that point was itself informative, once I understood (as a reviewer) that a real conflict check ran and correctly found nothing to flag.

**The "why now" for the scheme felt genuinely time-sensitive, not manufactured urgency.** It explained that the benefit is tied to my daughter's age and that starting now maximizes the years it can compound — a real, verifiable fact about the scheme, not a vague "act fast" nudge.

**Financial jargon check:** no "reference_code," "FamilyRecommendation," or "aggregation" leaked into user-facing copy — those are internal/reviewer-facing terms only, confirmed by reading the actual rendered page text, not just the source.

**Test data note:** the test account (`task11-firstuser@example.com`) and all household/goal rows were created and fully cleaned up (deleted) after this walkthrough. The scheme-eligible daughter was added via a direct authenticated API call (the existing "Add someone else" UI form has no gender field — a pre-existing gap from an earlier task, not something Task 11 introduced), and her SSY eligibility was confirmed both in that response and again on the Family Recommendations screen. Independently confirmed via direct database query: the `recommendations` table remained at zero rows across the entire database after the visit, confirming nothing was persisted.

---

## Addendum — Family Dashboard (Milestone 2 Task 12), 2026-07-07

**Method:** Full UI walkthrough as a user with real financial data — this time I entered a salary (₹12L/yr), monthly expenses (₹40,000), savings (₹3,00,000), and a retirement goal during onboarding, then added a mother (no insurance) and a young daughter with a tagged education goal, so every one of the six cards had something genuine to say.

**The main dashboard told me my family exists without shouting about it.** One quiet card on the money overview — "Family — 3 people · 2 suggestions to review" — between my net-worth stats and cash flow. It didn't compete with the numbers; it invited a tap.

**Every card answered exactly its own question, with my numbers.** "Who depends on me? 1 kid · 1 parent." "Education costs ahead: Riya Shah: Riya's college, ₹25,00,000 by 2038." "Insurance coverage: 0 of 3 people covered." "Emergency readiness: 7.5 months covered" — which I could verify myself in my head (₹3,00,000 savings ÷ ₹40,000/month). Nothing composite, nothing unexplained.

**The dashboard didn't flatter me.** "Retirement readiness: 4% — needs attention" is a bleak number, and it's *my* bleak number (₹500/month toward ₹5,00,000 in 20 years). A dashboard that dressed that up would have been worthless; this one showed the same persisted probability the Goals screen shows.

**The moment that proved the whole design: one action fixed three things at once.** The Parents card showed "⚠ Kamla Shah: no own insurance." I tapped it, landed on the Insurance screen (which showed the exact same recommendation the dashboard feed had shown — no reconciliation needed), recorded a family floater covering her, and came back. On the very next load: the warning was gone ("No insurance gaps we know of"), coverage read "1 of 3 people covered," and the insurance suggestion had left the feed — only the SSY suggestion for Riya remained. Nothing nagged me about something I'd already fixed.

**Financial jargon check:** no "composition layer," "recommendations_unavailable," "plan_health_score," or "liquid_assets" leaked into user-facing copy — the cards say "months covered," "people covered," "on track," all in plain words.

**Test data note:** the test account (`task12-firstuser@example.com`) and all household/goal/policy/financial rows were created and fully cleaned up (deleted) after this walkthrough. Independently confirmed via direct database queries: the `recommendations` table remained at zero rows across the entire database after many dashboard loads, and both goals' persisted probabilities were byte-identical after the walkthrough to their values at creation (21.2 and 3.9) — the Calculation Lifecycle untouched by any number of dashboard reads.

---

## Addendum — Government Schemes Screen (Milestone 2.1-P1), 2026-07-07

**Method:** Full UI walkthrough with a household of three: an SSY-eligible daughter, a son who fails SSY's gender rule, and a mother five years from SCSS eligibility.

**The "Potentially Eligible" bucket is the moment this finding actually mattered.** Before this screen existed, a parent five years from qualifying for a savings scheme got zero signal anywhere in the product. Seeing "Sunita Verify will reach the age 60+ requirement for Senior Citizens' Savings Scheme within the next 5 years" sitting right below the "Eligible now" section, not buried, felt like being told something useful before I needed it — not after.

**Seeing my son listed under "Not Eligible" didn't feel like a rejection.** "Sukanya Samriddhi Yojana has a gender-specific eligibility requirement that Arjun Verify does not meet" is a plain fact about a specific scheme, not a verdict on him — and it's collapsed behind "Not eligible — show 11 more" by default, so I only saw it if I went looking.

**The unconfigured schemes were the most reassuring part, oddly.** Six schemes (Provident Fund, EPF, NPS, and others) all read "Eligibility criteria... are not yet configured" instead of a fabricated "not eligible." As a reviewer I know this means the product doesn't have verified rules for these yet — and it says exactly that, rather than pretending it checked and found nothing.

**Financial jargon check:** no "EligibilityBucket," "bucket," or "rule_type" leaked into user-facing copy — the section headers are "Eligible now," "Potentially eligible," "Not eligible," in plain language matching the existing SSY-callout tone from Family Member Detail.

**Test data note:** the test account (`m21-p1-verify@example.com`) and all household rows were created and fully cleaned up (deleted) after this walkthrough. Independently confirmed the `recommendations` table remained at zero rows, and the Recommendations feed showed byte-identical reason text to this screen's "Eligible now" entry for the same scheme/member — no reconciliation needed between the two surfaces.
