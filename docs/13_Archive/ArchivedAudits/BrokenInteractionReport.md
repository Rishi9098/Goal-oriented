# Broken Interaction Report — Northstar

**Date:** 2026-07-08
**Scope:** Every element from `InteractiveProductAudit.md` marked ⚠ or ❌, with root cause, severity, impact, fix, and effort. Prioritized P0 (fix before anything else touches this surface) → P3 (cosmetic/consistency).

---

## P0 — Trust and data-integrity issues

### 1. Profile page: email field silently discards changes
- **Screen:** Profile (`app.profile.tsx`)
- **Component:** Email address input, "Save changes" button
- **Expected behavior:** Editing the email and saving updates the account's email address.
- **Actual behavior:** The field is editable and enables the Save button, but `handleSubmit` calls `auth.updateMe({ full_name: form.fullName })` — email is never sent. The backend's `UserUpdate` schema (`app/schemas/user.py`) and `PUT /me` handler (`app/routers/auth.py`) have **no email field at all**. The UI then shows "✓ Saved" and updates its own local state, masking the fact that nothing was persisted; a page refresh reverts the field.
- **Root cause:** Frontend form was built with an editable email field before backend email-change support existed (or after it was descoped) and never had the field disabled/removed to match.
- **Frontend handler exists:** Yes (but incomplete — omits email) · **API exists:** Partially (function signature never accepted email) · **Backend exists:** No · **Classification:** Partially implemented, abandoned mid-way without UI cleanup.
- **Severity:** P0 — silent data loss combined with a false success confirmation is exactly the trust failure this product's own Milestone 2.1 "no silent data loss / no misleading UI" bar exists to catch.
- **User impact:** A user who changes their email (e.g., after a personal email change) believes it saved. It didn't. They may lose access recovery capability (e.g., password reset going to the old, still-active email) without realizing why.
- **Recommended fix:** Either (a) make the email field read-only with a note ("Email can't be changed here yet"), matching the Household field's existing honest-disabled pattern on this same page, or (b) implement real email-change support (verification flow, `UserUpdate.email`, backend handler) if the product wants this capability. Option (a) is the minimal, immediately-safe fix.
- **Estimated effort:** Option (a): trivial (< 1 hour). Option (b): medium (new verification flow, several hours to a day).

---

## P1 — Misleading affordances and broken navigation

### 2. Landing page "View live demo" doesn't show a demo
- **Screen:** Landing (`index.tsx`)
- **Component:** "View live demo" button
- **Expected:** Show prospective users the product without requiring signup.
- **Actual:** Links to `/app`, which has a hard client-side auth guard (`app.tsx`'s `beforeLoad`) — an unauthenticated visitor is immediately redirected to `/auth/sign-in`, functionally identical to clicking "Sign in."
- **Root cause:** No demo-mode/sandboxed account exists; the button was likely written aspirationally or copy-pasted before demo infrastructure was built.
- **Frontend handler exists:** Yes · **API/backend:** N/A (no demo-mode backend exists) · **Classification:** Feature abandoned or never started; label not updated to match.
- **Severity:** P1 — first-impression trust issue for prospective customers on the highest-traffic page.
- **User impact:** A curious visitor clicks expecting to explore, instead hits a sign-up/sign-in wall with no explanation — a bait-and-switch impression, however unintentional.
- **Recommended fix:** Either build a real read-only demo account/mode, or relabel the button to match reality ("Sign in" duplicate, or remove it).
- **Estimated effort:** Relabel/remove: trivial. Real demo mode: large (new seeded read-only account, route guard exception).

### 3. Landing page nav "Security" link points to a non-existent anchor
- **Screen:** Landing (`index.tsx`)
- **Component:** Top nav "Security" link (`href="#trust"`)
- **Expected:** Scroll to a security/trust section.
- **Actual:** No element with `id="trust"` exists anywhere on the page (sections have `id="product"`, `id="how"`, `id="pricing"` only). Clicking does nothing visible.
- **Root cause:** A "Security"/trust section was likely planned or removed, and the nav link was never updated or removed to match.
- **Classification:** Feature abandoned (the section), link left orphaned.
- **Severity:** P1 — visible on every page load, in primary navigation.
- **User impact:** Confusing dead click on the marketing site's main nav.
- **Recommended fix:** Either add the missing `id="trust"` section (the Features grid already contains a "Bank-grade security" card — an anchor could target that section) or remove the nav item.
- **Estimated effort:** Trivial (add an `id` attribute, or delete one line).

### 4. Landing page footer legal links are placeholders
- **Screen:** Landing (`index.tsx`)
- **Component:** Footer — Privacy, Terms, Disclosures
- **Expected:** Open the corresponding legal document.
- **Actual:** All three are `href="#"` — no pages exist.
- **Root cause:** Legal pages never built; classic placeholder left in from initial scaffold.
- **Classification:** Feature not started.
- **Severity:** P1 — for a financial product, missing Privacy/Terms is a real compliance-adjacent gap, not just a UX nit.
- **User impact:** Users (and any compliance reviewer) cannot find the product's actual privacy or terms commitments.
- **Recommended fix:** Write and link real Privacy Policy / Terms of Service pages before any public launch; Disclosures may be lower urgency depending on jurisdiction.
- **Estimated effort:** Medium-to-large — this is a content/legal task, not just an engineering one.

### 5. Landing page claims a feature ("account linking") that doesn't exist
- **Screen:** Landing (`index.tsx`) vs. Settings (`app.settings.tsx`)
- **Component:** Features grid — "Bank-grade security... OAuth read-only account linking"; How-it-works step "01 — Link your accounts"
- **Expected:** These claims should reflect a real, working capability.
- **Actual:** Settings' own "Linked accounts" card explicitly states "Institution connections via Plaid — coming in a future release." The landing page presents this as an already-working feature ("Link your accounts" is literally step one of the onboarding narrative).
- **Root cause:** Marketing copy written ahead of, or never reconciled with, actual build status.
- **Classification:** Feature not started (in-product); marketing describes it as shipped.
- **Severity:** P1 — a prospective user reading the landing page and then finding "Coming soon" in Settings is a direct, discoverable contradiction.
- **User impact:** Erodes trust once discovered; is the kind of claim a fintech regulator or diligence reviewer would flag.
- **Recommended fix:** Either caveat the landing-page copy ("coming soon") to match Settings, or reorder the roadmap so account linking ships before this copy goes live.
- **Estimated effort:** Trivial for the copy fix; the underlying feature itself is a separate, large body of work already correctly deferred.

### 6. Dashboard goal preview cards look clickable but aren't
- **Screen:** Dashboard (`app.index.tsx`)
- **Component:** Goal mini-cards in the "Goals" panel (up to 4 shown)
- **Expected:** Given the hover-state styling (`hover:border-border-strong`) and that the *same data* is fully clickable on the Goals page itself, a user reasonably expects clicking here to open the goal.
- **Actual:** No `onClick`, no `<Link>` — purely decorative hover.
- **Root cause:** The card was copied from a display-only pattern without adding the click-through behavior the Goals page equivalent has.
- **Classification:** Partially implemented — display logic present, interaction logic missing.
- **Severity:** P1 — inconsistent behavior between two near-identical UI elements on two different screens is a specific, confusing pattern break.
- **User impact:** User tries to click a goal from the dashboard (the app's home screen), nothing happens, has to navigate to Goals separately.
- **Recommended fix:** Wrap each card in a `<Link to="/app/goals">` (simplest) or open `GoalSimPanel` directly from the dashboard (matches Goals-page behavior more closely).
- **Estimated effort:** Small (under an hour).

---

## P2 — Functional but mislabeled or incomplete

### 7. Reports "Export PDF" doesn't export a PDF
- **Screen:** Reports (`app.reports.tsx`)
- **Component:** "Export PDF" button
- **Actual behavior:** Calls `window.print()` — opens the OS/browser print dialog. Produces a PDF only if the user manually selects "Save as PDF" as their print destination.
- **Root cause:** Simplest-possible implementation of "export," never upgraded to a real generated-file download.
- **Classification:** Partially implemented.
- **Severity:** P2 — functional path to a PDF exists, just not a one-click one, and print-to-PDF is a widely understood browser pattern.
- **User impact:** Minor friction and mild expectation mismatch (label says "Export," behavior is "Print").
- **Recommended fix:** Either relabel to "Print / Save as PDF," or implement a real server-side PDF generation endpoint.
- **Estimated effort:** Relabel: trivial. Real PDF generation: medium (new backend endpoint + template).

### 8. AI Copilot header always claims "GPT-Planner · 4o"
- **Screen:** AI Copilot (`app.copilot.tsx`)
- **Component:** Header label
- **Actual behavior:** Hardcoded string, shown regardless of whether `OPENAI_API_KEY` is configured. When it isn't, `copilot.py` silently serves a rule-based canned response — same UI, no disclosure.
- **Root cause:** Label written assuming the AI path is always active; the backend's intentional, tested fallback path was never surfaced to the frontend.
- **Classification:** Partially implemented (fallback exists and works; UI doesn't reflect which mode is active).
- **Severity:** P2 — not data-unsafe, but a misleading-capability issue similar in kind (smaller in stakes) to the email-save bug.
- **User impact:** User may attribute a generic rule-based reply to "GPT-4o," misjudging the assistant's actual capability.
- **Recommended fix:** Have `ChatResponse` include a `mode: "ai" | "fallback"` field and render the header conditionally.
- **Estimated effort:** Small-medium (one backend field + one frontend conditional).

### 9. `app.family.add.tsx` missed by the accessibility fix
- **Screen:** Add Family Member
- **Component:** "Back to Family" link (×2)
- **Actual behavior:** No `focus-visible` styling — keyboard users get no visible focus indicator here, unlike every other Family-module screen.
- **Root cause:** The Milestone 2.1 Accessibility Polish finding scoped its fix to "6 files, 24 elements" but this 7th file/2 elements were not included in that inventory.
- **Classification:** Regression/gap in a previously-"complete" fix.
- **Severity:** P2.
- **Recommended fix:** Add the same `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background` utility already used everywhere else.
- **Estimated effort:** Trivial (two `className` edits).

### 10. Goals page and its panel have zero keyboard-focus indicators
- **Screen:** Goals (`app.goals.tsx`), `GoalSimPanel.tsx`, `EducationPlanningSection.tsx`
- **Actual behavior:** None of this screen's ~15 interactive elements (search, filters, New Goal, goal cards, modal buttons, risk selector, Edit/Save/Run/Optimize/Delete) have `focus-visible` styling.
- **Root cause:** This screen predates, and was never included in, the Milestone 2.1 Accessibility Polish finding, which was explicitly scoped to the Family module only.
- **Classification:** Known gap, correctly out of that finding's stated scope, but a real, undocumented gap on the app's second-most-visited screen.
- **Severity:** P2.
- **Recommended fix:** Apply the same established utility class across this screen's interactive elements as a follow-up accessibility pass.
- **Estimated effort:** Medium (similar shape to the Family-module fix — ~15 elements across 3 files).

### 11. Onboarding "Sign in" link causes a full page reload
- **Screen:** Onboarding, Step 0
- **Component:** "Already have an account? Sign in"
- **Actual behavior:** Plain `<a href="/auth/sign-in">` instead of the router's `<Link>` — works, but reloads the whole page instead of client-side navigating.
- **Classification:** Working but inconsistent.
- **Severity:** P2.
- **Recommended fix:** Swap for `<Link to="/auth/sign-in">`.
- **Estimated effort:** Trivial.

---

## P3 — Cosmetic / low-risk observations

### 12. Root document metadata still says "Lovable App"
- **Screen:** All pages (root-level `<head>` defaults in `__root.tsx`)
- **Actual behavior:** `og:title`/`og:description`/`twitter:site` are hardcoded to "Lovable App" / "Lovable Generated Project" / "@Lovable" — leftover scaffold metadata, never rebranded. Per-route `<title>` is overridden correctly, but social-share previews are not.
- **Severity:** P3 — invisible in normal use, visible the moment any page is shared on social media or via a link-preview-generating tool (Slack, iMessage, etc.).
- **Recommended fix:** Update root meta to Northstar branding.
- **Estimated effort:** Trivial.

### 13. Forgot-password "dev mode" reset-token block
- **Screen:** Forgot password
- **Actual behavior:** Conditionally renders the raw reset token in the UI when the backend returns one (non-production behavior, correctly gated server-side).
- **Severity:** P3 — not a code defect; a configuration-hygiene item to double-check before any production deploy (confirm the backend never returns `reset_token` outside dev/test).
- **Recommended fix:** No code change; add to pre-launch checklist.
- **Estimated effort:** N/A (verification task).
