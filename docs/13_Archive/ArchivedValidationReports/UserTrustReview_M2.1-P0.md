# User Trust Review — Milestone 2.1-P0 (Risk Profile Persistence Bug)

**Date:** 2026-07-07

## Before this fix

A user visits Profile, sees "Risk Profile" presented identically to "Full Name" and "Email" — an ordinary, saveable account field. They change it, see "✓ Saved" (the exact same success indicator real saves use), and reasonably conclude their preference is now stored. It silently isn't. The failure is invisible at the moment it happens and only surfaces later — the worst kind of trust failure, because the user has no reason to ever re-check.

## After this fix

The field is gone. A user who wants to set a risk profile is not told anything false — they simply don't see a field here that doesn't work. The real, working equivalent (per-goal risk profile on `/app/goals`) is unaffected and remains exactly where a user would naturally look when creating or editing a specific goal.

## Does removing a visible field itself feel like a regression to a user who previously saw it?

No user has ever successfully used this field for its apparent purpose — every prior "successful save" was a false positive. Removing a control that never worked is not a capability loss; a capability that silently didn't work was never actually available. This is consistent with `UX_PRINCIPLES.md` #7 ("a limitation stated clearly builds more trust than a capability implied and later found missing") — here taken to its natural conclusion: the clearest statement of "this isn't a real setting" is not showing it as one.

## Verification this doesn't create a new honesty gap

Checked: nothing elsewhere in the product (dashboard cards, goal creation defaults, onboarding copy) references or depends on Profile's risk-profile field or its value. Its removal closes a gap without opening a new one.
