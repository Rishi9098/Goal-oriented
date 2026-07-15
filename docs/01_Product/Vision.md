# Product Vision

**Status:** Canonical · **Last verified against code:** 2026-07-06, cross-checked 2026-07-13
**Supersedes:** `ProductRoadmapReport.md`'s framing section, `PrivateProductReport.md`, `CompetitorAnalysisReport.md`, `ProjectDiscoveryReport.md` (all archived); `Document/md files/MARKET_CONTEXT.md` and `COMPETITOR_ANALYSIS.md` are preserved as historical, pre-project research appendices (they predate Northstar's own existence as a product).

---

## 1. What Northstar Is

> Plan, simulate, and reach every financial goal with an AI copilot built for serious investors.

A goal-based financial planning platform combining a real Monte Carlo simulation engine (10,000 paths per goal, genuine confidence intervals — not a single deterministic guess), an AI Copilot anchored to the user's actual data, and — the product's most differentiated pillar — **family-first, India-specific financial planning**: household modeling, real government scheme eligibility (Sukanya Samriddhi Yojana, Senior Citizens' Savings Scheme, and others), and tax-deduction-aware insurance recommendations, all grounded in versioned, effective-dated real data rather than invented figures.

## 2. Why It Exists

It replaces a spreadsheet-and-guesswork approach to "will I actually retire on time?" with a real probabilistic answer, and replaces "do I qualify for any of these nine government schemes?" with a personalized, pre-filtered, explained answer — commitments the product's own Principles (`docs/03_Engineering/CodingStandards.md`) hold as non-negotiable: every recommendation must be explainable, and the product never claims a capability the data model doesn't actually have.

## 3. Who It's For

Individuals and families building a long-term financial plan, most concretely modeled around Indian tax/scheme context (the family/insurance/schemes subsystem is explicitly India-specific), while the core goal/Monte Carlo engine is currency-agnostic. Full persona detail: `docs/01_Product/UserPersonas.md`.

## 4. Competitive Positioning

Northstar's differentiation is not "another net-worth tracker" — dozens exist. It is the combination of (a) a genuinely probabilistic, not deterministic, goal-outcome engine, and (b) India-specific, versioned-data-grounded government scheme/tax guidance that a generic global financial planner cannot offer without inventing facts. The product's own engineering discipline (never hardcode a fact that can change without a deploy, never invent a financial rule) is itself part of the competitive moat — a competitor cutting this corner ships wrong the moment a rate changes.

## 5. What Northstar Is Not (deliberately)

Not an account-aggregation platform (no bank-credential linking exists — and the Landing page's claim that it does is a known, open documentation/marketing defect, FE-001, tracked in `docs/03_Engineering/TechnicalDebt.md`). Not a licensed investment advisor — the AI Copilot narrates already-computed data, it never originates a financial recommendation the way a registered adviser would (`docs/07_AI/AIArchitecture.md` §9's regulatory positioning). Not (yet) a tax-computation engine — versioned tax *data* exists; a full tax-liability calculator does not.

---

## Related Documents
`docs/01_Product/Requirements.md` · `docs/01_Product/UserPersonas.md` · `docs/01_Product/Roadmap.md` · `docs/02_Architecture/SystemArchitecture.md` §1


## Related Tests
None specific — a product-vision document has no direct test surface; see `08_Testing/QualityMetrics.md` for how product claims are verified against delivered features.

---

*Archived originals: `docs/13_Archive/ArchivedReports/ProductRoadmapReport.md`, `PrivateProductReport.md`, `CompetitorAnalysisReport.md`, `ProjectDiscoveryReport.md`. Historical, pre-project research: `docs/13_Archive/ArchivedDesignDocs/MARKET_CONTEXT.md`, `COMPETITOR_ANALYSIS.md`.*
