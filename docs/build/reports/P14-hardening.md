# P14: real-scenario hardening (reduced)

Status: 🟡.

## Done
- Data per teacher per track computed by `scripts/data_budget.py` into `docs/evidence/data_budget.json` (tested in `tests/test_data_budget.py`). Result: inside the 10 MB target with text practice; over it if every practice session is voice. Both are reported.
- PWA bundle size regenerated (`docs/evidence/bundle_size.json`).
- Offline behaviour as already tested for the upload queue and lesson downloads (`docs/offline.md`).

## Not done
- Slow 3G run and a real low-end phone (Gate 2). These need Gopi's phone; nothing is claimed about them.
- Offline replay of lessons in the web app was cut in P10.

## For humans
- Gopi: run the storyboard screens on an Android Go-class phone, write `docs/evidence/device_test.md` with the model and versions.
