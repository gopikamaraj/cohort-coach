# Claude Code prompt: re-skin the front-end (design system, screenshot loop, no change in behaviour)

Paste everything below the line into Claude Code at the repo root. Put the reference files named in Step 0 in the repo first.

---

**Task.** Rebuild the look and feel of the front-end with a proper design system, without changing what the product does. The requirements are mature, so this is a presentation rewrite: tokens, a small component set, page templates, and every screen migrated onto them, checked by screenshots you look at yourself.

**Rules.**

- **Behaviour is frozen.** Do not change APIs, state logic, data models, permissions, or AI calls. Change markup structure and styles only.
- **Tests stay green** at every commit. Add visual snapshot tests as you go.
- **Follow DESIGN.md** (Calm Institutional Material) and the reference files. Do not invent a new look.
- **No heavy new dependency.** Keep the current framework. No CDN. Self-host fonts, or load each Google font family with its own request and a fallback. Icons are inline SVG with text labels.
- **Offline and low-cost phones matter.** Keep the service worker caching. The main CSS and JS bundle must not grow by more than 15 percent. Report the numbers.
- **Accessibility:** 44px touch targets, contrast of at least 4.5 to 1, a visible focus ring, reduced motion respected, text that scales to 200 percent, labels for screen readers.
- **Languages:** English, Hindi and Tamil must fit. No fixed-width buttons. Test with strings 30 percent longer and with the Devanagari and Tamil fonts loaded.

**Step 0. Read first.** Read CLAUDE.md, DECISIONS.md, PROGRESS.md, docs/design/stitch/DESIGN.md, docs/design/stitch/INVENTORY.md, and the front-end code: the framework, routing, how styles are written today, and the list of screens. Read the visual references in `docs/design/reference/`: `practice-class-v3.html` (the approved Practice Class design) and any Stitch exports. Treat them as the target for spacing, hierarchy, colour and tone.

## Step 1. Audit the current UI

1. Write a Playwright script that renders every screen at 360 by 800 and 1280 by 800, in English, and in Hindi and Tamil for the main screens. Save the images to `docs/design/audit/before/`.
2. Write `docs/design/audit/AUDIT.md`. For each screen, list defects against this **visual rubric**, with a severity:
   - one clear primary action per screen, and a clear hierarchy
   - a spacing scale on a 4 or 8 pixel base, with no ad-hoc margins
   - one alignment grid
   - a type scale of five sizes or fewer
   - colours from tokens only, with meaning carried by text and icon as well as colour
   - consistent cards (radius, border, no stacked shadows)
   - a sensible amount on screen (about seven items per group)
   - empty, loading, offline and error states present
   - consistent line icons, always with text
   - short, plain copy
   - touch targets, motion, and Hindi and Tamil fit

## Step 2. Tokens

Create `styles/tokens.css` (or the equivalent) from DESIGN.md as CSS variables: colours with light and dark values, the type scale, spacing, radii, elevation levels and motion durations. Respect `prefers-color-scheme`. Remove every hard-coded colour and size from component and page styles.

## Step 3. Components and a living style guide

Build each with states (default, hover, focus, pressed, disabled, loading) and accessible markup: AppShell (side rail on desktop, bottom bar on phones), TopBar (title, language switch, offline pill, account), Card, Button (filled, tonal, outlined, text), Chip, StatusPill, TextField, Select, Toggle, Segmented control, ListRow, BigNumber, ProgressMeter, Callout (info, warning, success), EmptyState, Skeleton, Toast, BottomSheet and Dialog, Avatar (use the child sprites), AudioPlayer (with the script as text), BarChart (inline SVG with a text alternative), StepFlow (icons joined by arrows), and a responsive Table. Add a `/dev/styleguide` page that shows them all, and make it reachable from judge mode.

## Step 4. Migrate the screens, in the judge's ten-minute order

Use the components only. A page may add layout rules but no new colours, sizes or one-off components.

1. Sign-in and role picker, with the judge's "view as" switch
2. Teacher home (the Next step card, the progress mirror, a welcome-back state)
3. Photograph sheets and review the reads
4. Class card and diagnosis
5. Cohort and mentor view
6. Voice lesson player with the script, and the one-tap reply
7. Practice Class (match `practice-class-v3.html`)
8. Cohort chat
9. Mentor method card (record and confirm)
10. Coach inbox and the knowledge base
11. Officer dashboard
12. Judge guide panel
13. Settings and accessibility

Protect the work with a flag, `UI_V2`, per route group, so old and new can coexist during migration. Remove the flag only when every screen on this list is migrated.

## Step 5. The screenshot loop (the most important step)

After each screen: render it at 360 by 800 and 1280 by 800 in English and Hindi. **Look at the images yourself.** Compare with the reference, or with the rubric if there is none. Write three specific defects, fix them, and render again. Repeat up to three times. Save the final images to `docs/design/audit/after/` and record any defect you could not fix.

## Step 6. Polish

Subtle transitions of 200 ms or less. Skeletons while loading. Clear success and error feedback. Minimal inline SVG illustrations for empty states. The child avatars from the sprite system. App icon, splash screen and manifest theme colours. Keep the copy short and in plain words.

## Step 7. Quality gates

- Axe accessibility checks pass on every screen.
- Lighthouse (mobile, throttled): record performance, accessibility and PWA scores before and after.
- Visual snapshot tests for the main screens at both sizes in English, and Hindi overflow checks.
- Keyboard-only paths work. Reduced motion is respected. The app loads and the main screens render with the network off.
- Bundle size before and after.

## Step 8. Docs and kit updates

- `docs/design/STYLEGUIDE.md`: tokens, components, do and don't.
- DECISIONS.md: an entry dated 2026-10-30, a re-skin with behaviour frozen.
- PROGRESS.md and docs/design/stitch/INVENTORY.md updated.
- Report: `docs/build/reports/UI-RESKIN.md`, with a before and after table of screenshots, the Lighthouse and bundle numbers, and the defects still open.

**Order:** Steps 1 to 3, then Step 4 in the listed order with Step 5 after each screen, then 6 to 8. Re-record the demo video and refresh the deck screenshots only after the UI is frozen.

**Done when** the tests and accessibility checks pass, every screen on the list is on the new components, the before and after screenshots exist, and the flag is removed.
