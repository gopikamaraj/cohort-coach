# UI guidelines: fewer words, clearer screens (2026-10-20)

Teachers using a low-end phone, often in a second language, should be able to use the app without reading paragraphs. These rules came from reviewing every screen on 20 Oct. They sit on top of `docs/design-system.md` (tokens, contrast, tap targets), which still governs.

## 1. What changed in this pass

| Before | Now | Why |
| --- | --- | --- |
| Text-only buttons ("Listen", "This is wrong") and a paragraph under them | Icon buttons (speaker, flag) with an accessible name; the "arrives later" or "thank you" message is a toast that goes by itself | Less text on the card; the message is still announced to screen readers |
| Bottom menu of words | Icon above a short label, scrolls sideways when it does not fit | Faster to find; works from 320 px |
| Home with four stacked buttons | One primary action plus a grid of tiles (icon and label) | One obvious next step, the rest one tap away |
| Settings spread across screens | One **My profile**: classes, storage and backup, data used, privacy, feedback, each a titled panel | One place to look |
| Raw `<button>` styles per screen | `IconButton`, panels, tiles, chips, switches, stars from one set | Consistent look |

## 2. Rules

1. **Icon plus label by default; icon alone only for a familiar action** (listen, flag, rename, delete, use). Icon-only controls always carry `aria-label` and `title`. Never an icon as the only carrier of a status: add a word or a shape.
2. **One icon set** (`apps/pwa/src/components/icons.tsx`): inline SVG, 24 px grid, 2 px stroke, `currentColor`. No icon fonts, no images, no extra requests (budget in `CLAUDE.md` section 9).
3. **A sentence on the page only if it is needed to act.** Reassurance, "not yet" and "done" messages go to a toast (`useToast`): short, 4.5 s, tap to close, never the only place a decision is explained.
4. **One primary action per screen**, filled; everything else secondary (outlined). Destructive actions use the danger style and always confirm.
5. **Panels group related controls** (rounded, 1 px line, a title with an icon). At most three levels: screen title, panel title, label.
6. **Counts, never percentages, for teachers** (rule 5); simulated data keeps its banner (rule 6).
7. **Tap targets at least 48 px, text at least 16 px** (tested in `tests/test_design_tokens.py`); icon buttons are 56 px wide.
8. **Language first.** Every string has `en`, `hi`, `ta`. A test scans the home, check, practice, programme and history screens in Hindi and Tamil for stray English words.
9. **Responsive.** Fluid from 320 px; a centred column up to 1000 px; no horizontal scrolling except tables and the menu (tested at 320, 360, 768 and 1280 px).
10. **Colour carries meaning only with a second cue**: green (done), amber (check), red (danger), blue (action); always with an icon or word.

## 3. How to check a new screen

- Open it at 320 px and at 1280 px. Is there any sideways scroll? Is the primary action visible without scrolling on 360 x 640?
- Count the sentences above the first action. More than two: move the rest to a toast, a panel behind a tap, or delete it.
- Tab through it with a keyboard: every icon control has a name and a visible focus ring.
- Switch to Hindi and Tamil: no English, no clipped text.

## 4. Still to do (listed, not built)

- Replace the remaining text-only buttons on the Check keypad and the Practice Class with icons where the meaning is universal.
- Audio on every text card (the speaker icon currently answers "arrives in a later step").
- Skeleton loading states, and a first-run walkthrough of three screens.
- A dark theme and a larger-text setting.
- Review with real teachers (round 3) before tuning further: these rules are the team's judgement, not a test result.
