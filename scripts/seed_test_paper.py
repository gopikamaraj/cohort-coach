"""Make the standard test paper for a class, so Enter check has a paper to choose.

    python scripts/seed_test_paper.py --class-id <id> [--api URL] [--kind pre|post]

Enter check chooses a paper that already exists; it never makes one. The standard test paper has
the published pilot-test numbers, the same numbers the sheets in demo/test-sheets/ were made on
(Form A for a pre-test, Form B for the post-test twin). A class is created on each phone, so run
this once for the class id of that device (the `activeClass` setting in the browser's IndexedDB).
No child data: a paper is questions and an answer key.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--class-id", required=True)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--kind", choices=("pre", "post"), default="pre")
    ap.add_argument("--term", type=int, default=1)
    ap.add_argument("--language", choices=("en", "hi", "ta"), default="en")
    ap.add_argument("--label", default="3A", help="class label printed in the check code")
    args = ap.parse_args()
    body = {
        "check": {
            "id": f"{args.class_id}:{args.term}",
            "kind": args.kind,
            "form": "B" if args.kind == "post" else "A",
            "class_label": args.label,
            "term": args.term,
        },
        "language": args.language,
        "sample": True,
    }
    req = urllib.request.Request(
        f"{args.api.rstrip('/')}/api/papers/generate",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Role": "teacher"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:  # noqa: S310 - the team's own API
            paper = json.load(res)["paper"]
    except urllib.error.HTTPError as err:
        print(f"the API refused: {err.code} {err.read().decode()[:300]}", file=sys.stderr)
        return 1
    print(f"paper {paper['id']} ({paper.get('check_code', '')}) made for class {args.class_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
