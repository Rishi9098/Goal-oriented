# Screen Inventory — Milestone 2 (Family Financial Planning)

**Date:** 2026-07-06. Condensed cross-reference; full detail for each screen lives in `Milestone2ImplementationContract.md`.

| # | Screen | Route | Inputs | Outputs | Depends On | Navigates To |
|---|---|---|---|---|---|---|
| 1 | Onboarding — Family Step | (in-wizard, no dedicated route) | 3 yes/no + children count | `households`, `household_members` rows | Existing onboarding wizard | Next onboarding step (unchanged) |
| 2 | Family Home | `/app/family` | none (read) | Member list w/ completeness | Screen 1's seeded rows | Screens 3-7 |
| 3 | Add Family Member — Spouse | `/app/family/add?type=spouse` | name, DOB | `household_members` row | Screen 2 | Screen 2 |
| 4 | Add Family Member — Child | `/app/family/add?type=child` | name, DOB, gender? | `household_members` + `dependents` row, SSY check | Screen 2; §11's scheme data | Screen 2 |
| 5 | Add Family Member — Parent | `/app/family/add?type=parent` | name, relationship, insurance-status | `household_members` + `dependents` row | Screen 2 | Screen 2; feeds Screen 10's recommendation |
| 6 | Add Family Member — Other | `/app/family/add?type=other` | name, relationship, DOB? | `household_members` + `dependents` row | Screen 2 | Screen 2 |
| 7 | Family Member Detail | `/app/family/members/:id` | none (read); Remove action | Member summary, tagged goals, coverage | Screens 3-6, 8, 10 | Edit (→3-6), Remove (→2) |
| 8 | Family Goals | `/app/family/goals` | tag selection (household_member_ids) | `goal_household_members` rows | Existing `goals`; Screen 2's members | Screen 9 (education goals), existing goal detail |
| 9 | Education Planning | (goal-detail extension, no new route) | custom_inflation_rate | `goals.custom_inflation_rate` | Screen 8's tagged goal; §11's SSY data | Back to Screen 8 |
| 10 | Family Insurance | `/app/family/insurance` | policy fields, covered members | `health_policies` + `health_policy_coverage` | Screen 5's parent insurance-status; Screen 2's members | Screen 12's dashboard card |
| 11 | Family Government Schemes | `/app/family/schemes` | none (read) | Eligible/Potentially/Not-eligible buckets | Screen 2's members; certified `schemes`/`scheme_eligibility_rules` | Screen 4 (SSY reused), Screen 12 |
| 12 | Family Dashboard | `/app/family` (summary) + `/app` card | none (read) | 6 cards + recommendation feed | Screens 2, 8, 10, 11; existing `planning_service` | All above |

## Navigation Graph

```
Onboarding (1) ──seeds──▶ Family Home (2) ─┬─▶ Add Spouse (3) ──▶ back to (2)
                                              ├─▶ Add Child (4)  ──▶ back to (2)
                                              ├─▶ Add Parent (5) ──▶ back to (2), feeds (10)
                                              ├─▶ Add Other (6)  ──▶ back to (2)
                                              └─▶ Member Detail (7) ──▶ Edit (3-6) / Remove

Family Goals (8) ──education-category goal──▶ Education Planning (9) ──▶ back to (8)

Family Insurance (10) ◀──reads insurance-status from (5)

Family Schemes (11) ◀──reads members from (2); SSY check reused by (4) and (9)

Family Dashboard (12) ◀──aggregates (2), (8), (10), (11); embedded card on existing /app dashboard
```

## Screens Explicitly Not Built This Milestone (named so they aren't assumed)

- **HUF workspace** — schema-ready (`huf_entities`, `huf_entity_id` ownership columns), deliberately no UI per `FamilyPlanningDesign.md`'s explicit constraint and `docs/PRODUCT_PRINCIPLES.md` #9.
- **Nominee-per-person summary view** — nominees remain per-asset (existing `Asset`/`nominees` screens, out of Milestone 2 scope); a cross-cutting "nominee summary" view is a reasonable future Milestone 2 extension, not a Foundation gap, and not built now.
- **Shared household login/multi-adult access** — every household has exactly one authenticated creator this milestone (§Family Home's ownership-check note); a spouse's own login accessing the same household is out of scope.
- **"Review Summary" / "Confirm Profile" as separate onboarding screens** — considered (they appeared as illustrative examples in the request), not adopted: `FamilyPlanningDesign.md`'s approved design doesn't include them, and the existing onboarding wizard's own summary/assumptions steps already serve that purpose. Not inventing a new screen the approved UX didn't call for.
