# Behavioral Design Audit — Phase 7

**Date:** 2026-07-13
**Lens:** Certified Financial Planner + Behavioral Economist + Product Designer, reviewing the one screen with the most emotional range in the product — Life Events, where an objectively joyful moment (a new home, a marriage, a child) and an objectively hard one (a divorce, a medical emergency) currently produce the exact same, flat confirmation.

**Ground rule, taken directly from the mission:** *never manipulate users.* Everything below is either (a) an honest acknowledgment of something real and positive the user just told the system, or (b) an honest, non-alarmist acknowledgment that a moment is hard — never invented praise, never urgency, never guilt, never a dark pattern.

---

## 1. What's actually there today (verified in code)

- `RecordLifeEventDialog`'s success path calls `onRecorded(result.life_event)` immediately — the dialog closes, the new row appears in history. No distinction exists anywhere in the code between recording a Bonus and recording a House Purchase, a Marriage, or a Divorce. All eighteen event types share one confirmation experience.
- Nothing in the picker, the form, or the confirmation ever acknowledges that some of these moments are hard. Divorce's own form is a single dropdown ("Spouse") and a submit button — the same shape as any routine edit.
- Plan Health's anxiety problem was already addressed in Phase 3. This phase is about the *moment of action*, not the ambient score.

## 2. Findings and decisions

### 2.1 No celebration for genuinely joyful milestones

**Finding:** A first home, a marriage, a new child, a loan finally paid off, a retirement — recording any of these produces identical, silent confirmation to editing a phone number.

**Decision:** Six event types get an honest, specific celebratory confirmation *after* a successful record: House Purchase, Marriage, Birth of Child, Adoption, Loan Payoff, Retirement. Each message names the specific thing that just happened ("Your mortgage and home are now part of your plan") rather than generic praise — this is what keeps it honest rather than manipulative: the system is telling the user what changed, warmly, not flattering them for no reason.

**Explicitly excluded from celebration:** Bonus, Inheritance, Business Sale, Home Sale, Job Change, Salary Raise, New Loan, Dependent Parent, Divorce, Major Medical Event, Business Start, Education Planning. Several of these are *plausibly* positive (a bonus, an inheritance, a business sale) but are not *unambiguously* so for every person in every circumstance — a business sale can be a forced exit, an inheritance can follow a loss, a "raise" from a demotion-adjacent role change is not guaranteed cause for celebration. Where real ambiguity exists, this phase adds nothing rather than risk guessing wrong at an emotionally loaded moment.

### 2.2 No acknowledgment that some moments are hard

**Finding:** Divorce and Major Medical Event ("Medical Emergency") receive zero softening anywhere — the form for the single most emotionally loaded event in the entire catalog (Divorce) is the sparsest form in the product.

**Decision:** Both event types get one short, honest, non-alarmist sentence shown at the top of the form once selected — acknowledging the moment is hard and stating plainly what the form itself will and won't do ("this only updates your financial records"). No advice, no forced next step, no guilt about delay — just acknowledgment and a factual boundary on what the product is doing.

### 2.3 What is *not* done, and why

- **No manufactured urgency or streaks** ("You're on a 3-event streak!", "Complete your profile now!") — classic engagement dark patterns, explicitly excluded by "never manipulate users."
- **No celebration is invented for ambiguous events** (§2.1) — silence is the honest choice when the system cannot know whether a moment is good news.
- **No change to the Preview/Undo/History mechanics** — those already work correctly (validated in earlier phases); this phase only adds a warmer moment *after* a successful, unambiguous-good record, and a gentler *entry* into two specific hard forms.
- **No backend change** — every celebratory/supportive message is static, per-event-type copy shipped in the frontend's own config, not computed from anything new.

## 3. Implementation shape

1. Extend `LifeEventTypeConfig` (frontend-only type) with two new optional fields: `celebration?: { title: string; body: string }` and `supportiveNote?: string`.
2. Populate `celebration` for the six milestone events, `supportiveNote` for Divorce and Major Medical Event.
3. `RecordLifeEventDialog`: render `supportiveNote` as a small, calm banner immediately under the event's own description, before any fields. On successful record, if the event type has a `celebration`, show it as a replacement view inside the same dialog with a single "Done" button (manual dismiss only — no forced timer, so nothing about how long a user takes to read it is dictated for them); events without a `celebration` keep today's exact behavior (immediate close).
