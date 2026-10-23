# Design system: Calm Institutional Material

Material 3, tuned for a quiet, trustworthy tool used by teachers, coaches and programme staff. Import this file into Stitch as the theme before generating any screen (see README.md).

> Created on 23 Oct 2026 from the locked list in the design brief because no DESIGN.md existed. Dark-theme values below were derived by the build from the light values and need a designer's check (flagged in `docs/build/reports/STITCH-PROMPTS.md`).

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

## Components

| Name | What it is |
| --- | --- |
| TopBar, NavRail, BottomNav | The shell. BottomNav shows four tabs and a More sheet. |
| OfflinePill, LangSwitch, AccountButton | Always in the top bar. |
| SimulatedBanner | Secondary container strip: "Simulated data: this class and these children are made up for the demo." |
| PlayButton | Audio-first control on every teacher text card. |
| BadgeLine | "Checked" and "Reviewed" with check icons, in the teacher's language. |
| ScenarioCard | Primary container card: error, problem, goal. |
| ClassCard | Five ChildAvatar tiles with a StateTag beneath each. |
| ChildAvatar | Drawn from the sprite system; the expression carries the state (confused, listening, ready, shy, thinking, got it). |
| StateTag | Small chip under an avatar: Confused, Listening, Ready, Quiet. |
| SayLine | The child-says line in tertiary container, with a subtitle line. |
| BoardCard | Board with Tens and Ones counts and the slate line. |
| MaterialsTray, SpriteTile | Tool tiles (bundles of ten, loose sticks, chart) drawn as inline SVG. |
| MicPanel | Hold-to-speak button with waveform bars either side. |
| QuickMove | Full-pill suggestion chip. |
| TypedFallback | Text field plus Send, shown when voice is off. |
| FeedbackCard | Success tint for strengths, tertiary tint for the thing to try. |
| ProgressMeter | Linear meter with a label and a count. |
| PrivacyNote | Lock icon plus one plain sentence. |
| ErrorCard | Count line, example, focus tag, optional StageLines. |
| StageLine, ProbeNote | Stage group with counts and a one-minute check. |
| AnswerBox, MarkToggle | Check entry field (56px, numeric keyboard) with Blank and Can't read marks. |
| SheetPicker, AbsentToggle, ConceptTag | Check entry controls. |
| PhotoCapture, ConfirmBox | Photo button, read result with low-confidence boxes to confirm. |
| LessonCard | Title, length, PlayButton, BadgeLine, download state. |
| TapReply | Three or two choice buttons after a lesson. |
| VoiceRecorder | Record, stop, play back, send. |
| ThreadPost, ReportButton | Cohort chat items. |
| StatusChip | Status words with icon (Proposed, Awaiting coach, In use...). |
| DataTable, SuppressionNote | Tables for coach and officer; "fewer than 5 classes". |
| IntervalChart, VerdictChip | Track result chart and verdict. |
| FunnelBar | Delivered, Tried, Practised, Changed, each with a source label. |
| RoleCard, ScopeDialog | Landing page and its dialog. |
| TourProgress, WhatToNotice | Guided tour shell. |
| RoadmapCard | Locked card: "Roadmap. Not built yet." |

## Rules that outrank taste

1. Counts for teachers, never percentages. Officers may see percentages.
2. Children are counts and patterns. Simulated children have names only inside the Practice Class.
3. One primary action per teacher screen.
4. Every text card for teachers has a play button.
5. Meaning is never by colour alone.
6. A track attempt with no reply reads as "no response", never "failed".
