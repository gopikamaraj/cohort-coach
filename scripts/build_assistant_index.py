"""Build the assistant's indexes (the deploy step), or check that the bundled ones are current.

    python scripts/build_assistant_index.py            build and write services/assistant/index/
    python scripts/build_assistant_index.py --check    exit 1 if the bundled index is out of date

Run it after the deck and the video are final, so the slide numbers and timestamps it indexes are
the real ones. A secret, phone number, email or roll number in any source fails the build.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.assistant import curate, index  # noqa: E402


def main(argv: list[str]) -> int:
    try:
        if "--check" in argv:
            ok = index.is_current()
            print(
                "assistant index is current"
                if ok
                else "assistant index is OUT OF DATE: run this script"
            )
            return 0 if ok else 1
        built = index.build()
    except index.IndexBuildError as e:
        print(e)
        return 1
    index.write(built, sha=index.git_sha())
    pre = curate.build_all()  # the suggested answers, written from the files just built
    total = sum(len(c) for c in built.chunks.values())
    print(
        f"wrote {total} chunks: "
        + ", ".join(f"{ns} {len(c)}" for ns, c in sorted(built.chunks.items()))
    )
    print("pre-written answers: " + ", ".join(f"{r} {len(v)}" for r, v in pre.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
