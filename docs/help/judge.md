# Judge guide: a ten-minute test path

## What you are testing

Cohort Coach is a tool for primary teachers in India that groups them for training by the specific mistake their pupils make, and helps them rehearse the fix before using it on children. Everything in the demo is simulated or labelled as simulated. The judge guide answers from the repository, the rubric map, the deck and the video script, and gives an honest status for each claim: Built, Partly built, Simulated, Mock or Roadmap.

## Sign-in

Judge mode needs no sign-in and holds no real user's data. The staff pilot has its own sign-in, with accounts held by the team; judges do not need it. Use View as in the assistant panel to see another role's assistant on demo data. The About this product tab always answers as the judge guide.

## The path

1. Open the web app. The landing page shows four role cards and a five-minute guided tour. Ask the guide: who is the user?
2. Open the guided tour at step 1. It runs the check on sample sheets and shows the error card with where learning most likely broke down.
3. On the Judge page, choose Load a simulated class, then open My class. Each card shows a count of children, never a percentage.
4. Open Practice, choose Start, and type: Priya, what is 52 minus 29? Then type: Tell me how you got that. Open the Judge tab and choose Show AI layers to see the five layers of one turn.
5. Open the AI map and then the audit trail. Open Try to break it to see which check stops each prepared bad line.
6. Choose the Coach role on the landing page and open the review screen. Choose Officer and open the results to see one working track, one not working and one hidden under five classes.
7. On the Judge page choose Simulate offline, then open Enter check. The result waits and is sent when you go back online.
8. Switch the language in the top bar of the landing page and open My profile to see the same screens in Hindi or Tamil.
9. In the assistant, open About this product and ask: what is real and what is simulated?

## What is real and what is simulated

The error counts, the cohorts, the verdicts and the children in the Practice Class are simulated. The model calls are real: Claude reads sheet photos, labels the teacher's moves, speaks as the simulated children and drafts lessons. The pilot server is real and holds no real class data yet.

## Where to look

The rubric map, docs/RUBRIC_MAP.md, lists every claim with its status, code path, test, demo steps, slide and video time. The README table Where AI is used is generated from ai/registry.py.
