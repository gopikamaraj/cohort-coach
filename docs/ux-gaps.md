# Teacher questions the app should answer (gap list, 2026-10-20)

Each row is a "where do I find / how do I know" question, in the style of the five Gopi raised on 20 Oct. Status says what is true now. Rows marked **built** were done in this pass; the rest are listed, not built, and each names the phase that owns it in `docs/build/BUILD_PROMPTS.md`.

| # | Question a teacher (or mentor, officer) will ask | Status now | Owner |
| --- | --- | --- | --- |
| 1 | Does the app fit my phone, a tablet, a laptop? | **Built**: fluid layout from 320 px to a centred 1000 px column, scrolling menu, tested at four sizes | P05/P14 |
| 2 | Where is everything I entered, and did it reach the server? | **Built**: "What I entered" (checks, children, how many from a photo, counts sent or waiting, answers on request). The server never holds answers or photos | P08 for the two-channel version |
| 3 | How do I tell you the simulated children were not like mine? | **Built**: "After you try it in class" in the Review tab (choices only, no name or class). Server keeps it for tuning; a summary hides figures under 5 reports | P13 uses it in the realism eval |
| 4 | Where are my lessons, audio and script from the coach or mentor? | **Built as a status screen**: "My programme" says none are published yet and where they will appear. The lessons themselves wait for the content pipeline | P09, P10 |
| 5 | How do I know I was placed in a cohort, or invited as a mentor? | **Built for cohort** (placement, waiting list, cohort size, "a mentor is planned"); a mentor invitation is decided after the next check, so the screen says so. Messages for both wait for the Telegram channel (roadmap) | P10, P11 |
| 6 | Can I hear the card instead of reading it? (rule: audio on every text card) | **Icon built**: a speaker icon on each card answers with a toast; the audio itself is not built | P07 follow-up / P09 |
| 7 | I tapped "this is wrong". Who saw it? | **Built**: flags go to the admin page (anonymous, with the card code) when she has allowed feedback | P09 (review queue) |
| 8 | I changed phone or cleared the browser. Is my work gone? | **Built**: persistent storage is requested, and My profile exports and restores a backup file (optionally sealed with a passphrase) | P05 (teacher id) |
| 9 | Can I delete my data, or withdraw consent to share? | **Built**: erase everything (phone and the server's class counts), delete a class, withdraw all consents; feedback is anonymous so it cannot be traced back | P05 (V3-T15) |
| 10 | I typed the wrong child's answers or the wrong form. Can I fix or remove a child? | Not built: no delete or reorder of a child row, and history is read-only | P08 |
| 11 | I teach two sections. Can I keep two classes? | **Built**: add, rename, switch and delete classes in My profile | P05 |
| 12 | When is the next check due, and who reminds me? | Not built | P10 (T6 and reminders) |
| 13 | What does the data cost me (MB used) on my plan? | **Built**: Data used in My profile (sent, received, total, a cost from her price per GB, a Clear button) | P14 |
| 14 | How do I know what happens to my reflections, who reads them, and for how long? | **Notice built** (in-app, three languages, and `docs/privacy.md`); reflections themselves arrive in P10 | P05, P08 |
| 15 | Which of my feedback changed the product? ("You said, we changed") | Doc only (`docs/feedback-log.md`); not shown in the app | P16 |
| 16 | As a mentor: what do I record, by when, and what did my card change? | Screen says "later" | P11 |
| 17 | As a reviewer or officer: what is waiting for me, and how old is it? | Screen says "later" | P09, P12 |
| 18 | The rehearsal session expired after two hours. Did I lose it? | Transcript stays on the phone; the server session is gone and she is told to start again | P06 follow-up |
| 19 | Is the app available when my signal is weak, and what still works? | Documented in `docs/offline.md`; the Practice Class is the only live feature | P14 |
| 20 | Text size, read-aloud and low-literacy support | Not built beyond system fonts and 48 px targets | P14 |

Counts of these are from this list only; none is a measured finding. Rows 6 to 20 are the next candidates; confirm the order with Gopi and Seema.

## Added after the 20 Oct pass

| # | Question | Status | Owner |
| --- | --- | --- | --- |
| 21 | Who is the admin, how do they sign in, and who else could open the admin page? | Shared `ADMIN_KEY`; open if unset. Named accounts are not built | P05 (identity) |
| 22 | How long do you keep my feedback and counts? | "While the programme runs"; a number of days is not agreed | Gopi, legal |
| 23 | Who do I write to with a complaint? | Placeholder in the notice | Seema, Gopi |
| 24 | If a coach or admin changes role, what do they see? | The role switcher is a demo control; real roles need sign-in | P05 |
| 25 | Can I move a class to another teacher (a transfer) or share one with a colleague? | Not built | later |
