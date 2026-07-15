# Northstar Engineering Knowledge Base

**Purpose of this document:** not a technical reference (that's everything else under `docs/`) — this is the meta-document describing *how this documentation system itself works*: its philosophy, its structure, who owns what, how it's maintained, and how it should grow. Read this once, then use `DocumentationIndex.md` as your daily-driver homepage.

---

## 1. Documentation Philosophy

Three principles, inherited directly from this project's own engineering culture and applied here to documentation itself:

**Verify against the actual codebase, never assume documentation is correct.** Every canonical document in this system states the code it was last verified against and corrects stale claims explicitly rather than silently repeating them — the same discipline this project already applies to government scheme rates, tax sections, and every other fact that can drift out of sync with reality. A documentation system that doesn't hold itself to its own stated standard has no credibility applying that standard to anything else.

**Prefer merging over deleting, but never lose information.** This restructuring took 254 original documents down to 31 canonical ones — a 12% file count, not a 12% information count. Every original is preserved, in full, under `docs/13_Archive/`. When two things overlapped, they were merged into one better document; when something was purely historical, it was archived, not discarded.

**Minimal diff, no premature abstraction — applied to documentation structure itself.** The taxonomy below has exactly the sections this project's actual domains need, not a generic template borrowed from elsewhere. `LifeEventEngine.md` exists as its own document because it's a large, distinct engine with its own release history — it wasn't folded into `SystemArchitecture.md` just to reduce file count, and it wasn't split into 18 separate per-event-type canonical documents just because 18 event types exist.

---

## 2. Folder Structure & Rationale

```
docs/
├── DocumentationIndex.md              ← the homepage — start here
├── NorthstarEngineeringKnowledgeBase.md  ← this document
├── 01-product/       — what & why: vision, requirements, personas, journeys, roadmap
├── 02-architecture/  — how the system is built: one document per major engine/subsystem
├── 03-engineering/   — how to work in this codebase day to day
├── 04-api/           — the contract between frontend and backend
├── 05-data/          — the schema, independent of the services that read it
├── 06-testing/       — how correctness is verified, and the historical record of every verification
├── 07-security/      — implementation-level controls (Security Architecture) vs. broader risk (Threat Model)
├── 08-release/       — how software leaves this repository and reaches users
├── 09-history/       — every original document, organized by kind, never deleted
├── ENGINEERING_CONSTITUTION.md, PRODUCT_PRINCIPLES.md, UX_PRINCIPLES.md  — the project's own durable rules, referenced by exact path throughout
```

**Why architecture (02) and engineering (03) are separate:** architecture documents describe what a subsystem *is* and *why it's shaped that way* — they change rarely, only when the system itself changes. Engineering documents describe *how to safely change it* — playbooks, debugging guides, coding standards — and are written for someone about to make an edit right now. Conflating the two produces documents that are either too abstract to act on or too procedural to explain the reasoning.

**Why API (04) and data (05) are separate from architecture (02):** the REST contract and the database schema are each independently useful references someone might need without reading the full architectural narrative around them — a frontend engineer implementing a new API call needs `RESTAPI.md`, not a re-read of `RecommendationEngine.md`'s full business-rule catalog.

**Why testing (06) covers both strategy and history:** `TestingStrategy.md` (the ongoing approach) and `ValidationStrategy.md` (the chronological record of every checkpoint this project ever ran) are deliberately different documents — one tells you what to do next, the other tells you what's already been proven and when.

---

## 3. Naming Conventions

- **Canonical documents:** `PascalCase.md`, one clear noun phrase (`SystemArchitecture.md`, not `SystemArchitectureBible.md` or `SystemArchitectureBibleV2.md`) — the taxonomy folder already provides the context a longer name would try to add.
- **Archived originals:** kept under their **original filename**, unchanged, inside the appropriate `docs/13_Archive/Archived*/` subfolder — never renamed on archive, so a reference to the original name (in a commit message, an old PR, another archived document) still resolves.
- **No version suffixes in canonical documents.** A canonical document has exactly one current version — its own git history *is* its version history. (Archived originals that were themselves part of a version chain — `Milestone1ImplementationSpecification_FINAL.md` vs. `_v2.md` — keep their original suffixes for exactly this reason: those suffixes are load-bearing historical facts, not clutter.)

---

## 4. Ownership

This documentation system does not assign named human owners (this is a technical, not organizational, artifact) — but it does assign **domain ownership by convention**: whoever owns a service in `docs/03_Engineering/ArchitectureDecisionRecords.md`'s "Related Services" sense owns keeping that service's architecture document current. Concretely:

| Document | Owned in practice by whoever touches |
|---|---|
| `CalculationEngine.md` | `planning_service.py`, `monte_carlo.py`, `optimizer.py` |
| `RecommendationEngine.md` | Any `family_*_service.py` |
| `LifeEventEngine.md` | `life_event_service.py`, any handler |
| `FrontendArchitecture.md` | Any `routes/` or `components/` change |
| `DatabaseArchitecture.md` / `DatabaseSchema.md` | Any new migration |
| `ArchitectureDecisionRecords.md` | Anyone making a decision non-obvious enough to need one (Coding Standards Rule 8) |

**The rule, simply stated:** if your change would make a canonical document's own claims stale, update that document in the same change — not a follow-up ticket someone else picks up later. This is the same discipline Rule 11 (Deprecation Completion) already demands for code; it applies identically to the documentation describing that code.

---

## 5. Maintenance Process

**On every meaningful code change:** check whether it makes any canonical document's claims stale (a new endpoint not yet in `RESTAPI.md`, a new table not yet in `DatabaseSchema.md`, a newly-fixed finding still listed as open) — update in the same change.

**On every new ADR-worthy decision:** add an entry to `ArchitectureDecisionRecords.md` — never just a commit message or a scratch file. If the decision resolves or supersedes an existing one, note that explicitly rather than leaving two contradictory entries.

**Quarterly:** follow `08-release/OperationsRunbook.md`'s quarterly checklist, which includes re-reading `CodingStandards.md` in full to confirm the last quarter's changes didn't drift from any rule without a documented, deliberate decision — the same discipline extends to confirming the documentation itself hasn't drifted from the code.

**When a document is found stale:** correct it in place, citing what changed and when — the way every canonical document in this v2 system already models (see any "Last verified against code" line, and the several explicit corrections each one makes against its own source material).

---

## 6. How Future Documents Should Be Written

1. **State what code it was last verified against**, in the document's own header — a canonical document without this is a claim with no evidence.
2. **Prefer extending an existing canonical document over creating a new one** unless the new content is genuinely a distinct domain (a new major engine, a new taxonomy category) — the same "no premature abstraction" discipline that governs code governs documents.
3. **Include a "Related Documents" section** (and, where relevant, Related ADRs/APIs/Database Tables/Services/Frontend Components) — every canonical document in this system does this; it's what makes the system navigable without a search tool.
4. **Distinguish clearly between what exists and what's proposed** — `AIArchitecture.md`'s split between "Current" (§1–5) and "Future — PLANNED, NOT IMPLEMENTED" (§6–10) is the template: never let a proposal read as if it were shipped.
5. **Preserve findings and decisions verbatim when merging** — never reword a finding's severity or a decision's reasoning to make prose flow better. If it needs paraphrasing for length, the paraphrase must preserve every fact, not just the gist.

## 7. How Obsolete Documents Are Archived

1. Determine whether the content is **superseded** (a newer version exists and fully replaces it) or **historical** (no newer version, but the content is no longer current — a point-in-time snapshot, a completed milestone's own spec).
2. Move the file, **unchanged, under its original name**, into the matching `docs/13_Archive/Archived*/` subfolder (`ArchivedReports` for general reports, `ArchivedAudits` for audit/review documents, `ArchivedImplementationReports` for implementation reports, `ArchivedValidationReports` for validation/dependency/root-cause documents, `ArchivedDesignDocs` for pre-implementation design documents, `ArchivedPRReports` for PR reports).
3. **Never delete.** If a document is truly redundant (an exact duplicate), it still moves to history rather than being removed — disk space is not the scarce resource here, traceability is.
4. Update the superseding canonical document's own footer ("Archived originals: ...") to name every file the merge drew from, so a reader can always trace a canonical claim back to its original source.

---

## Related Documents
`DocumentationIndex.md` (the homepage this document explains) · `09-history/DocumentationInventory.md` (the full catalog this system was built from) · `09-history/DocumentationMigrationReport.md` (the record of this specific restructuring) · `03-engineering/CodingStandards.md` (the code-level discipline this document's own rules mirror)
