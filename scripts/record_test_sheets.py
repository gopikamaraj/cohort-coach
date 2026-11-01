"""Record the sheet reader's answers for the made-up test sheets in demo/test-sheets/.

    python scripts/record_test_sheets.py        # prints the sheets and an estimate, sends nothing
    python scripts/record_test_sheets.py --yes  # reads each sheet with the live model, saves them

Recorded mode (the hosted test deployment, tests) then replays one answer per file: the key is the
SHA-256 of the original file, which the phone sends with the picture, so the same sheet always gets
the same read. This is a real read of a made-up sheet (no child, no real handwriting), saved under
ai/fixtures/recorded/c08_answer_reading/ and labelled "Recorded AI answer" wherever it is shown. It
spends a few cents of the Claude budget, so it needs --yes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.calls.c08_answer_reading import read_sheet  # noqa: E402
from ai.client import CallContext  # noqa: E402
from ai.config import load_env  # noqa: E402
from engine.forms import FORM_A  # noqa: E402

FOLDER = ROOT / "demo" / "test-sheets"
APPROX_COST_EACH = (
    0.004  # a small vision read on the reader's model, USD (an estimate, not a price)
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument(
        "--yes", action="store_true", help="make the live calls and save the recordings"
    )
    ap.add_argument("--folder", default=str(FOLDER))
    args = ap.parse_args()
    files = sorted(Path(args.folder).glob("*.jpg"))
    print(
        f"{len(files)} sheets in {args.folder}; "
        f"about USD {len(files) * APPROX_COST_EACH:.2f} to record (estimate)."
    )
    if not args.yes:
        print("Nothing was sent. Run again with --yes to record.")
        return 0
    load_env()  # the key is read from .env and never printed
    done = 0
    for path in files:
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        out = read_sheet(
            base64.b64encode(data).decode(),
            "image/jpeg",
            FORM_A,
            context=CallContext(mode="record"),
            file_sha256=sha,
        )
        ok = out is not None
        done += ok
        print(f"{path.name}  {sha[:12]}  {'recorded' if ok else 'NOT READ'}")
    print(f"{done} of {len(files)} recorded.")
    return 0 if done == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
