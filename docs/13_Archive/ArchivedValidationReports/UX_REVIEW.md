# UX Review — Family Financial Planning Design

**Date:** 2026-07-06
**Reviewing:** `FamilyPlanningDesign.md`
**Method:** Genuine critique from each named perspective — this review is not a rubber stamp. Several real issues were found while writing the design itself; they're surfaced here rather than silently fixed, since the brief's own process (design → review → approval → implementation) makes this document the checkpoint for exactly that.

---

## Persona Reviews

### First-Time User (no financial background)

The three-question onboarding branch (spouse/children/parents, each a plain Yes/No) is genuinely light — no jargon, no forms. **But one real gap:** answering "Yes" to children creates *one* placeholder row, with no way to say "actually, I have three." A user with multiple kids either has to immediately go find the "add another child" affordance in the Family workspace (not signposted anywhere in the onboarding flow itself) or assumes the app only registered one child. **This needs a fix before approval** — either a simple "how many?" stepper on the children question, or an explicit line of onboarding copy ("you can add each child by name afterward").

The "why we ask" microcopy is present everywhere it should be — this is the strongest part of the design from this persona's perspective.

### Parent (2 kids, aging parents)

The child-adding flow's gender question, framed explicitly around a scheme ("used only to check Sukanya Samriddhi Yojana eligibility"), is honest but slightly transactional in tone for what should feel like introducing your own child to the app. It's *correct* that the reasoning is stated — better than asking silently — but a parent reviewing this might feel the app is "scanning for tax angles" at the exact moment it should feel warmest. Recommend softening the copy (e.g., leading with "this helps us find scholarships and schemes that might apply" rather than naming the scheme mechanically) without removing the transparency.

The Parents flow's "do they have their own health insurance?" with a third "Not sure" option is a genuinely good, low-pressure design choice — most existing consumer finance apps force a binary here and get bad data as a result.

### Married Couple

The "who does this affect" multi-select for goals is clear for a small household (2-4 people, the realistic common case) — no issue there. **The bigger concern, and the most important finding in this whole review:** a married couple reading "who does this affect: ☑ You ☑ Priya" will very reasonably expect this means the goal is now *jointly theirs* — trackable per-person, visible identically from either spouse's login, with each person's contribution counted separately. **The design is explicit internally that this isn't what's happening** (Finding E — single owner, a descriptive tag only) but the proposed UI copy doesn't make that limitation visible to the *user* anywhere. This is a real risk of the product overpromising relative to what it actually does, discovered by a couple only when they go looking for "how much did I contribute vs. Priya" and find nothing. **Recommend:** the goal detail screen must say, in plain language, something like *"This goal belongs to your account. Priya can see it if you share access, but her own contributions aren't tracked separately yet"* — turning a silent limitation into an honest, stated one.

### Senior Citizen

The design assumes the person filling in "Add a parent" is the adult child, which matches the most common real usage pattern (per `UserPersonasReport.md`) — reasonable as a default. **Gap:** nothing in this design addresses the second-most-common pattern from that same research — an adult child operating the *entire account* on a senior parent's behalf, or a senior citizen using the app directly and needing larger text/simpler framing. This isn't necessarily a Milestone 2 blocker (it's a cross-cutting accessibility/permissions concern, not specific to Family), but it should be named as an explicit known gap rather than silently assumed away, so it doesn't quietly become permanent.

### Financial Advisor

Every major design decision traces to a specific, previously-verified research finding rather than a designer's guess: the SSY inline callout (Phase 1/3), the parent-health-insurance question (Phase 3's separate-floater-doubles-the-deduction finding), the HUF omission (`FeatureGapAnalysisReport.md`'s own narrow-reach verdict). That traceability is a genuine strength an advisor would recognize and trust. **The one thing an advisor would push back on hardest** is the same joint-goal gap the Married Couple persona found — a professional planner thinks in exact contribution attribution for tax purposes (Section 80C/123 ceilings are per-individual, per `GovernmentPolicyReport.md`), and a goal that can't say who put in what money is a real limitation for exactly the tax-planning use case this whole product exists for. Not a reason to block this milestone, but a reason to prioritize Finding E soon rather than indefinitely.

### Accessibility Expert

The design's Part 10 correctly anticipates the standard traps (color-only signaling, decorative-only icons, motion without a reduced-motion fallback) — better than most first-draft designs. **One thing to verify explicitly during implementation, not yet confirmed by this design phase:** the family-member emoji (👤💍🧒) are paired with text labels in every wireframe shown, which is correct, but the actual `aria-label` treatment needs to hide the emoji from assistive tech entirely (`aria-hidden="true"` on the emoji glyph itself) rather than relying on adjacent text alone to override it — a common subtle bug where a screen reader ends up reading both the emoji's Unicode name *and* the label, doubling every announcement. Flagged here so it's an explicit implementation checklist item, not assumed handled by "the design mentions accessibility."

### Product Designer

The Family-as-7th-nav-item decision, and the resulting mobile bottom-nav demotion of Reports/Profile/Settings behind "More," is the single most debatable structural call in this document. It's defensible (Family genuinely deserves top-level status per the brief's own philosophy), but it was decided unilaterally in the design doc without weighing the cost to Reports' and Profile's discoverability on mobile specifically. **Recommend either:** validating this with actual usage data once Family ships (which routes get opened most from the "More" menu vs. before), or shipping the "More" grouping now but flagging it explicitly as an assumption to revisit, not a settled decision.

---

## The 9 Required Questions, Answered Directly

**1. Is anything confusing?** The joint-goal "who this affects" tag, as currently worded, risks being read as true joint ownership when it isn't. This is the single clearest confusion risk in the design.

**2. Is anything overwhelming?** No — this is the design's strongest dimension. Onboarding stayed to 3 yes/no questions; the Family workspace is one person at a time; schemes are eligibility-bucketed, not listed. The "never show a massive form" mandate was followed consistently.

**3. Is there unnecessary financial jargon?** One instance: naming "Sukanya Samriddhi Yojana" by its formal scheme name directly in the child-adding flow, mid-onboarding-adjacent-moment, before the user has asked for scheme detail. Not wrong (the scheme genuinely applies), but could be softened to "a government savings scheme for her future" with the formal name revealed on tap, deferring jargon until the user opts into it.

**4. Can any step be removed?** No step is removable without losing real function — three onboarding questions is already close to the practical minimum for correctly seeding the household. The design doesn't have padding to cut.

**5. Does every question explain why it exists?** Yes, checked field-by-field against the design doc — every input in every flow carries a "why we ask" line. This is fully satisfied.

**6. Does every recommendation build trust?** The recommendation format (person, timeline, current number, projected number, confidence, alternatives) is strong and directly grounded in the certified `recommendations` schema's actual fields — nothing in the copy promises data the backend can't produce. Trust-building is satisfied *for recommendations specifically*; the joint-goal tag is the one place elsewhere in the design where trust could be quietly undermined if shipped without the disclosure fix recommended above.

**7. Would Apple ship this?** Directionally yes — the people-first framing, the calm empty state ("it's just you right now — nothing about your plan requires more"), and the eligibility-bucketing all match Apple's own restraint-first design language. What can't be verified from an ASCII wireframe is typography rhythm, motion polish, and spacing discipline — those depend on implementation, not this document.

**8. Would Linear ship this?** Yes on information density and progressive disclosure specifically — Linear's own product philosophy (do one thing per screen, defer complexity) is closely mirrored in the Family Home screen and the person-detail page. Linear would likely push harder on making the "who this affects" tag's limitation more visible inline, not just on the goal-detail screen, consistent with Linear's habit of surfacing system state honestly rather than softening it.

**9. Is this solving a real user problem?** Yes, and unusually well-evidenced for a design document — every major decision traces to a specific prior research finding (Phase 1's SSY eligibility, Phase 3's parent-insurance economics and HUF-gating rationale, Phase 4's persona findings, Milestone 1/reconciliation's actual schema constraints) rather than to assumption. The one place this traceability reveals a real problem rather than just justifying a decision is Finding E — the research already knew joint goals were unsupported; this design is the first place that gap becomes user-visible, which is exactly why it surfaced here.

---

## Verdict

**Recommend approval contingent on two revisions**, not a full redesign:

1. **Add an explicit "you can add more/edit anytime" affordance to the onboarding children question**, or a simple count stepper, so a multi-child household isn't under-registered from the first interaction.
2. **Add explicit, honest UI copy about the joint-goal limitation** on the goal-detail screen (Married Couple / Financial Advisor finding above) — this is a disclosure fix, not a schema fix, and doesn't require touching Finding E's underlying data model to ship Milestone 2 honestly.

Everything else in `FamilyPlanningDesign.md` — the onboarding brevity, the progressive person-by-person workspace, the eligibility-bucketed schemes, the recommendation format, the empty/loading/error states, and the accessibility baseline — is sound as designed and doesn't need to change before implementation begins.
