# Product Principles

**Purpose:** What Northstar builds, and why — the durable filter every future feature proposal should pass through before it's designed, not just before it's built. Pairs with `UX_PRINCIPLES.md` (how it should feel) and `docs/ENGINEERING_CONSTITUTION.md` (how it's built).

---

## 1. Every feature must solve a real user problem — not a competitor-parity checkbox.

`FeatureGapAnalysisReport.md` established this concretely: account aggregation, HUF-as-a-built-feature, and Kubera's "Dead Man's Switch" were each evaluated on their own merits and either deferred or deliberately scaled down, specifically because "a competitor has it" is not, by itself, a reason to build something. Every feature proposal should be able to name the specific persona and specific problem it solves, the way `UserPersonasReport.md` did for all eleven personas.

## 2. Every recommendation must be explainable.

No recommendation ships as a bare instruction ("increase your SIP"). Every one carries a reason, the calculation behind it, the policy or scheme it cites, its confidence, and at least one alternative — this is not a UX nicety, it's a structural requirement enforced by the `recommendations` table's own schema (`reasoning`, `confidence_score`, `alternatives_considered`, `assumptions_used`). A feature that can't populate all of these honestly isn't ready to ship a recommendation yet.

## 3. Simplicity is preferred over feature count.

The Family Planning design deliberately kept onboarding to three yes/no questions rather than building a full family-profile form up front, and deliberately left HUF out of the primary experience despite HUF having a full research chapter behind it. Depth of research does not imply priority of feature — a feature earns its place in the primary flow only when it serves the common case, not the interesting case.

## 4. The application educates users; it does not overwhelm them.

Government schemes are bucketed into Eligible / Potentially Eligible / Not Eligible, never presented as a flat catalog. Difficult concepts (why a separate parent health policy saves money, why SSY is girl-child-specific by law) are explained inline, in plain language, at the moment they become relevant — not deferred to a help article the user has to go find.

## 5. Family-first financial planning is a core differentiator, not an add-on.

`CompetitorAnalysisReport.md` found no researched competitor combining real Monte Carlo rigor, India-specific tax/scheme depth, and a genuine family view in one product. Family is a first-class navigation item, not a settings sub-page, precisely because it's a defensible product position, not a feature to bolt on later.

## 6. Government schemes and tax rules are personalized, never presented as long lists.

A user should never have to read nine scheme descriptions to figure out which two apply to them. The product's job is to do that filtering — using the household's actual recorded ages, relationships, and tax-relevant facts against the versioned `scheme_eligibility_rules` data — and present only the two, with a plain-language reason each one applies.

## 7. Never claim capability the data model doesn't actually have.

The Family Planning design's "who this affects" goal tag is explicitly not presented as true joint ownership, because the schema doesn't support per-person contribution tracking yet (`FutureCompatibilityAuditReport.md` Finding E). Where a product limitation exists, the UI states it honestly rather than implying a capability that isn't real — an overpromising UI is a trust liability, not a growth lever.

## 8. Every unverified fact stays visibly unverified.

Confidence tiers (verified / convention / unverified_flag on `best_practice_rules`; the "provisional" flag on the NPS withdrawal-tax finding) exist so a recommendation grounded in solid research is never presented with the same authority as one grounded in an untested heuristic. A user should always be able to tell the difference, even if the product never says so out loud on every screen.

## 9. Build for the persona in front of you, not a hypothetical future one.

HNI/NRI-specific schema exists (Foundation's `asset_source_detail` design) but has no UI yet, correctly, because those personas weren't prioritized for Milestone 2. A feature that serves 2% of users well is not automatically worth building before a feature that serves 60% of users adequately — prioritize using the same "users benefited" reasoning `FeatureGapAnalysisReport.md` applied to every candidate feature.
