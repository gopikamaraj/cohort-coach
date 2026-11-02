# Style guide: the v2 front-end (`apps/pwa-v2/`)

Calm Institutional Material (`docs/design/stitch/DESIGN.md`), rebuilt as tokens, a small component set and an app shell. Behaviour is frozen: this is presentation only. The original front-end in `apps/pwa/` is untouched; `apps/pwa-v2/` is a copy with the new look. A living page shows every component: open `#/dev/styleguide` (also linked from judge mode).

## Tokens (`src/styles/tokens.css`)

| Group | Names | Rule |
| --- | --- | --- |
| Colour | `--paper --surface --chalk --tonal --pen --pen-container --ink --muted --outline --line --good* --warn* --margin*` | Material 3 roles. Light and dark values; dark follows the phone (`prefers-color-scheme`) unless `data-mode="light"` or `"dark"` is set on `<html>`. Meaning is always carried by an icon and a word as well as colour. |
| Type | `--text-sm 16 · --text-md 18 · --text-lg 20 · --text-xl 24 · --text-2xl 32` | Five sizes, in `rem`, so text scales to 200%. Nothing below 16 px. |
| Space | `--s1 … --s6` (4, 8, 12, 16, 24, 32 px) | No ad-hoc margins. |
| Shape | `--r-card 16 · --r-btn 8 · --r-field 8 · --r-chip 12 · --r-pill · --r-sheet 28` | Cards: radius, 1 px border, no stacked shadows. |
| Elevation | `--elev-0 none · --elev-1 · --elev-2` | Only floating things (toast, dialog, sheet) lift. |
| Motion | `--dur-fast .1s · --dur .15s · --dur-slow .2s` | 200 ms or less; `prefers-reduced-motion` turns it off. |
| Layout | `--rail-w · --content-max 72rem · --touch 44px · --touch-primary 48px` | |

Colours exist only in `tokens.css`. `styles.css`, `base.css`, `components.css` and the screens read them.

## Shell

A bottom bar with four tabs and a More sheet on phones (labels wrap to two lines instead of being cut). From 900 px a side rail lists every tab. The page content sits in a column up to 72 rem. Language and role are chosen on the landing page; the signal pill and offline note stay in the top strip.

## Components (`src/ui/index.tsx`)

Button (filled, tonal, outlined, text, danger; loading, disabled) · Card · Chip · StatusPill (good, warn, bad, with icon) · TextField · SelectField · Toggle · Segmented · ListRow and List · BigNumber · ProgressMeter · Callout (info, warning, success, error) · EmptyState · Skeleton · Dialog and BottomSheet (native `<dialog>`) · Avatar (the code-drawn child sprites) · AudioPlayer (script always as text) · BarChart (values written beside the bars) · StepFlow · Table (stacks into cards on a phone) · TopBar. The existing Toast is reused. Raw `input`, `select`, `textarea` and unclassed `button` elements get the same look from `base.css`.

## Do

- One filled button per screen: the main action.
- Take every word from `strings/{en,hi,ta}.json`. No fixed-width buttons.
- Show a count with a label ("11 of 28 children"). Teachers never see a percentage.
- Put "Simulated" wherever simulated data shows.
- Give every field a visible label; give help and errors as text.

## Don't

- No colour, size or radius literal in a screen or component stylesheet.
- No new one-off component in a page: add it to `src/ui` and to the style guide.
- No CDN, no web-font link, no icon without a text label.
- No shadow stacks; no motion longer than 200 ms.
