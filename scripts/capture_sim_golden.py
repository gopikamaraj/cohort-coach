"""Save the legacy simulator's golden runs to tests/fixtures/sim_legacy_golden.json.

    python scripts/capture_sim_golden.py

Run once, before the Bayesian child model was added, with SIMULATOR_MODEL unset. Do not re-run it to
make the golden test pass: the file is the record of what legacy did.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.engine.sim_golden import capture  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "sim_legacy_golden.json"


def main() -> int:
    if os.environ.get("SIMULATOR_MODEL", "legacy") != "legacy":
        print("SIMULATOR_MODEL must be unset or legacy to capture the legacy runs")
        return 1
    data = capture()
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        for k, (name, runs) in enumerate(data.items()):
            f.write(f'  "{name}": [\n')
            for i, run in enumerate(runs):
                sep = "," if i < len(runs) - 1 else ""
                f.write("    " + json.dumps(run, separators=(",", ":")) + sep + "\n")
            f.write("  ]" + ("," if k < len(data) - 1 else "") + "\n")
        f.write("}\n")
    n = sum(len(r["turns"]) for runs in data.values() for r in runs)
    print(
        f"wrote {OUT.relative_to(ROOT)}: {sum(len(v) for v in data.values())} sessions, {n} turns"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
