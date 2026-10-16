# Evidence registry

Every number in the README, docs, reports and deck comes from a file generated here (or `evals/results.md`) by a script, never typed by hand.

- Each generated file records: the number, its **source script and input path**, the **date**, and the **sample size**.
- Small samples carry a confidence note ("from 3 classes, read as directional").
- Simulated data is labelled "simulated" wherever it appears.
- Regenerate with `python tasks.py evidence` (available after P02). Eval results come from `python tasks.py eval all`.
