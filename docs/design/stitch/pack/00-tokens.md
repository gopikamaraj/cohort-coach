# Design tokens to attach once

From `docs/design/stitch/DESIGN.md` (Calm Institutional Material; Material 3). The app has a light theme only; the dark column in DESIGN.md is derived and not shipped.

## Colour tokens
| Role | Light | Dark (derived) |
| --- | --- | --- |
| primary | #0B6B6B | #6CD3D3 |
| on primary | #FFFFFF | #003737 |
| primary container | #BDEEEE | #004F4F |
| on primary container | #00201F | #BDEEEE |
| secondary container | #CCE8E7 | #1F4B4A |
| tertiary | #A04A00 | #FFB784 |
| tertiary container | #FFDCC4 | #7A3500 |
| success | #1B6D2F | #8FD99A |
| success container | #B4F2BC | #00531B |
| background | #F7FAFA | #0E1414 |
| surface | #FFFFFF | #151B1B |
| outline | #BEC9C8 | #5B6665 |
| text | #191C1C | #E0E3E3 |
| text secondary | #3F4948 | #BEC9C8 |
| error (system) | #B3261E | #F2B8B5 |

Meaning by colour, never by colour alone: success container for what went well, tertiary container for what to watch, primary container for the scenario or the focus, secondary container for neutral chips. Every tinted card also carries an icon and a word.

## Shape and spacing
- Cards: 16px radius, 1px outline (#BEC9C8), no shadow.
- Buttons, chips, inputs: 8px radius. Quick moves: full pill.
- Touch targets at least 44px; primary buttons 48px; text inputs 56px.
- Spacing scale 4, 8, 12, 16, 24, 32. Phone gutter 16. Desktop content capped at 1280px.

## Type
Inter, with Noto Sans Devanagari and Noto Sans Tamil as fallbacks in that order. Scale: title large 22/28 semibold; title medium 16/24 semibold; body 16/24 (never smaller for teacher text); label 14/20 medium (never below 14); numbers use tabular figures. No gradients, no blurs, no emojis. Icons are line icons (24px grid, 2px stroke), always beside a text label.

Font loading note for engineers: Stitch's export packs three fonts into one malformed Google Fonts URL, so Inter never loads, and it loads Tailwind from a CDN. Never copy either into our code. We self-host subsetted font files and use our own CSS.

## Layout
- Desktop: 88px left navigation rail (icon over label), top bar with title, subtitle, "Works offline" pill, EN / हिं / தமி switch and an account button; content capped at 1280px.
- Phone: bottom navigation bar (four items and More), header wraps to two rows (title and pill; language switch and account).
- Teacher screens are phone first. Mentor, coach, officer and judge screens are desktop first and collapse to one column on a phone.
