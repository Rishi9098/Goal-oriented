# Open Source Readiness Review

**Date:** 2026-07-14
**Method:** direct inspection of the repository as it stands today — not an aspiration, not a template checklist filled in by assumption. Every finding below was verified by checking for the specific file or content it claims is present or absent.

---

## Summary

**Not ready for public release as-is.** The engineering documentation is now genuinely excellent (31 canonical documents, fully cross-linked, historically traceable). The *legal and community-process* scaffolding a public open-source repository needs is largely absent, and — most seriously — **the repository claims a license it does not actually have**, which is a real legal-clarity problem, not a nice-to-have gap.

## Findings

### 1. README — Good, with one serious defect

**Present and good:** a clear one-line pitch, an architecture diagram, a features list. **Serious defect:** README.md links to a `LICENSE` file (`[![License: MIT]... ](LICENSE)`) and states "MIT © 2025 Northstar Planning" in its own License section — **but no `LICENSE` file exists anywhere in this repository.** This is not a missing nicety; it is a repository making a specific legal claim about how it may be used, reused, and redistributed, with nothing on disk to back that claim up. Anyone relying on the README's stated license today has no actual license grant to point to.

**Fix:** add a real `LICENSE` file (MIT, matching the README's own claim, unless a different license is actually intended) before any public release consideration. This is the single highest-priority open-source-readiness item in this entire review.

### 2. Setup Instructions — Good

`CONTRIBUTING.md` and `03_Engineering/DeveloperGuide.md` both give clear, working setup commands for backend (`venv` + `pip install` + `.env` + `uvicorn`) and frontend (`bun install` + `bun run dev`), including the important note that the frontend works standalone via mock data with no backend running. This is genuinely good onboarding UX for a new contributor.

### 3. Examples — Thin

No dedicated "examples" or "quickstart" walkthrough beyond the setup commands themselves — a new contributor gets the app running but has no guided first-contribution example task. Not a blocker, but worth adding (e.g., "add a new government scheme" from `03_Engineering/EngineeringHandbook.md` §2.A is already exactly this kind of guided example internally — it just isn't surfaced as an onboarding "try this first" exercise).

### 4. API Docs — Excellent

`04_API/RESTAPI.md`, `ServiceInteractions.md`, and `APIReference.md` are thorough, accurate (post-correction), and cross-linked. This is above the bar for most open-source projects at this stage.

### 5. Contribution Guide — Good, but incomplete for a public project

`CONTRIBUTING.md` covers dev setup, coding standards, test requirements, git workflow, and a PR checklist — genuinely solid. **Missing:** any mention of how external (non-team) contributions are triaged, reviewed, or credited; no `CODEOWNERS` file exists to indicate who reviews what.

### 6. Architecture Diagrams — Excellent

`02_Architecture/SystemArchitecture.md` alone has multiple Mermaid diagrams (high-level architecture, request lifecycles); every other architecture document has domain-specific diagrams. This is a genuine strength — better than most projects at any stage, open source or not.

### 7. License — **Missing (the critical finding, restated)**

See §1. No `LICENSE` file exists. No `license` field exists in `code/package.json` or `backend/pyproject.toml` either — the MIT claim exists only as prose in the README, nowhere else.

### 8. Code of Conduct — Missing

No `CODE_OF_CONDUCT.md` exists. Standard practice for a public repository expecting external contributions; currently absent entirely.

### 9. Security Policy — Missing

No `SECURITY.md` exists — no documented process for how a security researcher should responsibly disclose a vulnerability. Given this codebase handles financial data and (per `09_Security/SecurityArchitecture.md`) has a real, documented history of security findings and fixes, a public `SECURITY.md` describing a disclosure process is a meaningful gap, not a formality.

### 10. Issue Templates — Missing

No `.github/ISSUE_TEMPLATE/` directory exists. A public repository without issue templates tends to accumulate low-quality, hard-to-triage issues.

### 11. PR Templates — Missing

No `.github/PULL_REQUEST_TEMPLATE.md` exists. `CONTRIBUTING.md`'s own PR checklist (§"PR checklist") is exactly the content a PR template should surface automatically to every contributor — it currently only reaches someone who reads `CONTRIBUTING.md` in full first.

### 12. CI — Present and Genuinely Good (a finding this review corrects from every prior pass)

`.github/workflows/ci.yml` exists, runs backend lint+typecheck+test, frontend lint+typecheck, and a Docker build-check, on every push/PR to `main`/`develop`. This is a real, working, reasonably comprehensive CI setup — better than many public open-source projects have. **Every prior version of this project's documentation incorrectly claimed this didn't exist; this review is the first to verify it directly against `.github/`.**

---

## Priority Fix List (before any public release)

1. **Add a `LICENSE` file** matching the README's MIT claim (or correct the README if a different license is actually intended) — the one item that's actively misleading today, not just incomplete.
2. Add `SECURITY.md` with a real disclosure process, given this is a financial-data application.
3. Add `CODE_OF_CONDUCT.md` (a standard template, e.g. Contributor Covenant, is sufficient).
4. Add `.github/ISSUE_TEMPLATE/` (bug report + feature request at minimum) and `.github/PULL_REQUEST_TEMPLATE.md` (mirroring `CONTRIBUTING.md`'s existing PR checklist).
5. Add a `license` field to `code/package.json` and confirm `backend/pyproject.toml`'s own metadata matches.
6. Consider a `CODEOWNERS` file once there's a stable team structure to encode.

**Not on the critical path, but worth doing well:** a guided "first contribution" example task, referencing the already-excellent internal playbooks in `03_Engineering/EngineeringHandbook.md` §2.

---

## What NOT to Change

This review found the actual engineering documentation, architecture diagrams, API reference, and contribution setup instructions to already be at or above typical open-source-project quality — the gaps found are entirely in legal/community scaffolding (license, code of conduct, security policy, templates), not in engineering content. Don't rewrite what's already working to "look more open source" — add what's genuinely missing.

---

## Related Documents
`14_KnowledgeBase/NorthstarEngineeringKnowledgeBaseV2.md` · `03_Engineering/DeveloperGuide.md` · `09_Security/SecurityArchitecture.md`
