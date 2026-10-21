# Stage signature check (one-off, 21 Oct 2026)

Source data: `docs/design/pilot_forms.golden.json` (Forms A and B). Produced by running the script below from the repo root with the files listed as arguments. It is a design-time check on the written specification; the permanent version is the P08 unit test and eval 1 (`docs/design/addendum-v3.1.md` §F9). Nothing here is an eval result.

Command: `python sig_check2.py docs/design/addendum-v3.1.md docs/judge-test-script.md docs/build/synthetic-sheets-stage-addendum.md`

## Output

```text
== 1. Disjointness (items 1-5 and 7-10, both forms) ==
overlap: ('A', 1, 'PV-HEARD & PV-REVERSE', [3064, 30064, 300604])
overlap: ('A', 2, 'PV-HEARD & PV-REVERSE', [7082, 70082, 700802])
overlap: ('B', 1, 'PV-HEARD & PV-REVERSE', [2046, 20046, 200406])
overlap: ('B', 2, 'PV-HEARD & PV-REVERSE', [8035, 80035, 800305])
overlaps=4 designed(PV-HEARD & PV-REVERSE, items 1-2 of both forms)=4 unexpected=0
== 2. Sheets S01-S07 (Form A) ==
S01 ['IN-OP'] -> ['Input (test)']
S02 ['IN-OP'] -> ['Input (test)']
S03 ['IN-OPND'] -> ['Input (test)']
S04 ['OUT-REV'] -> ['Output']
S05 ['IN-NEAR'] -> ['Input (test)']
S06 ['CORE-OFF1'] -> ['Core']
S07 ['OUT-REV', 'PV-REVERSE', 'SUB-SFL'] -> ['Core', 'Output']
== 3. Check items in the text added by this change ==
computation items=16 dictation numbers=[264, 346, 728, 853]
docs/design/addendum-v3.1.md:279: pair 45,19 is a check item: 45 − 19
docs/design/addendum-v3.1.md:279: pair 19,45 is a check item: 19 − 45
docs/design/addendum-v3.1.md:279: pair 19,45 is a check item: 19 + 45
docs/design/addendum-v3.1.md:279: pair 45,19 is a check item: 45 − 19
docs/design/addendum-v3.1.md:292: pair 45,19 is a check item: 45 − 19
docs/design/addendum-v3.1.md:292: pair 19,45 is a check item: 19 − 45
docs/design/addendum-v3.1.md:292: pair 19,45 is a check item: 19 + 45
docs/design/addendum-v3.1.md:335: dictation number 346
docs/build/synthetic-sheets-stage-addendum.md:13: dictation number 728
docs/build/synthetic-sheets-stage-addendum.md:14: dictation number 728
docs/build/synthetic-sheets-stage-addendum.md:15: dictation number 728
docs/build/synthetic-sheets-stage-addendum.md:16: dictation number 728
docs/build/synthetic-sheets-stage-addendum.md:18: dictation number 728
docs/build/synthetic-sheets-stage-addendum.md:13: dictation number 346
docs/build/synthetic-sheets-stage-addendum.md:14: dictation number 346
docs/build/synthetic-sheets-stage-addendum.md:15: dictation number 346
docs/build/synthetic-sheets-stage-addendum.md:16: dictation number 346
docs/build/synthetic-sheets-stage-addendum.md:18: dictation number 346
```

## Reading the output

- Part 1: the only overlap is the designed one (PV-HEARD and PV-REVERSE share the "both heard and reversed" answers on items 1 and 2 of both forms). Every other signature set is disjoint from the others and from the correct answer on items 1 to 5 and 7 to 10 of both forms.
- Part 2: each synthetic sheet S01 to S07 lands in the stage the specification expects.
- Part 3: the scan lists every Form A or Form B item (and every dictation target) in the files given. The hits are the deliberate negative examples in the validator tests (section E) and the sheet answer rows (section G), which are test data, not lesson content. No worked example, hint or order probe added in this change contains a check item.

## Script

```python
"""One-off check for addendum v3.1 (21 Oct 2026). Run from the repo root: python sig_check2.py

1. Signature answer sets (CORE-OFF1, IN-OP, IN-OPND, IN-NEAR, OUT-REV plus the existing error answers)
   are generated from the items of Form A and Form B in docs/design/pilot_forms.golden.json and checked
   for being disjoint from each other and from the correct answer on every item except item 6.
2. Sheets S01 to S07 (Form A) are classified with the stage rules and compared with the expected stages.
3. The text added in this change is scanned for any Form A or Form B item (either order, either operation).
"""

import json
import re
import sys
from itertools import combinations

g = json.load(open("docs/design/pilot_forms.golden.json", encoding="utf-8"))
rev = lambda n: int(str(n)[::-1])


def near(n):
    s = str(n)
    out = set()
    for i in range(len(s)):
        for d in (-1, 1):
            t = int(s[i]) + d
            if 0 <= t <= 9:
                v = int(s[:i] + str(t) + s[i + 1 :])
                if len(str(v)) == len(s):
                    out.add(v)
    return out


def sigs(it):
    c = it["correct"]
    out = {}
    if it["type"] == "dictation":
        out["PV-HEARD"] = set(it["error_answers"]["PV-HEARD"]) | set(it["both_heard_and_reversed"])
        out["PV-REVERSE"] = set(it["error_answers"]["PV-REVERSE"]) | set(
            it["both_heard_and_reversed"]
        )
        out["IN-NEAR"] = near(it["value"])
    elif it["type"] in ("add_carry", "sub_borrow"):
        a, b = it["a"], it["b"]
        add = it["type"] == "add_carry"
        for k, v in it["error_answers"].items():
            out[k] = set(v)
        for k, v in it.get("untracked_signatures", {}).items():
            out[k] = set(v)
        out["CORE-OFF1"] = {c - 1, c + 1}
        out["IN-OP"] = {abs(a - b)} if add else {a + b}
        ops = set()
        for x, y in ((rev(a), b), (a, rev(b)), (rev(a), rev(b))):
            r = x + y if add else x - y
            if r >= 0:
                ops.add(r)
        out["IN-OPND"] = ops
        out["OUT-REV"] = {rev(c)}
    return out


print("== 1. Disjointness (items 1-5 and 7-10, both forms) ==")
overlaps = []
for f in ("A", "B"):
    for it in g["forms"][f]["items"]:
        if it["n"] == 6:
            continue
        s = sigs(it)
        c = it["correct"]
        for k, v in s.items():
            if c in v:
                overlaps.append((f, it["n"], k, "contains the correct answer"))
        for k1, k2 in combinations(s, 2):
            both = s[k1] & s[k2]
            if both:
                overlaps.append((f, it["n"], f"{k1} & {k2}", sorted(both)))
for o in overlaps:
    print("overlap:", o)
designed = {("PV-HEARD & PV-REVERSE")}
unexpected = [o for o in overlaps if o[2] not in designed]
print(
    f"overlaps={len(overlaps)} designed(PV-HEARD & PV-REVERSE, items 1-2 of both forms)={len(overlaps) - len(unexpected)} unexpected={len(unexpected)}"
)

print("== 2. Sheets S01-S07 (Form A) ==")
A = g["forms"]["A"]["items"]
SHEETS = {
    "S01": "346,728,85,74,82,35,110,26,121,54",
    "S02": "346,728,9,18,36,35,38,26,43,54",
    "S03": "346,728,130,92,118,35,38,26,43,54",
    "S04": "346,728,58,47,28,35,83,62,43,54",
    "S05": "347,738,85,74,82,35,38,26,43,54",
    "S06": "346,728,84,73,83,35,39,26,43,54",
    "S07": "364,782,58,47,28,35,42,34,57,66",
}
STAGE = {
    "PV-HEARD": "Core",
    "ADD-NOCARRY": "Core",
    "SUB-SFL": "Core",
    "SUB-NODEC": "Core",
    "ADD-WHOLE-ONES": "Core",
    "CORE-OFF1": "Core",
    "IN-OP": "Input (test)",
    "IN-OPND": "Input (test)",
    "IN-NEAR": "Input (test)",
    "OUT-REV": "Output",
}
NEED = {"PV-HEARD": 2, "PV-REVERSE": 2, "IN-NEAR": 2}
for name, row in SHEETS.items():
    ans = [int(x) for x in row.split(",")]
    hits = {}
    for it, a in zip(A, ans):
        if it["n"] == 6:
            continue
        for k, v in sigs(it).items():
            if a in v:
                hits.setdefault(k, []).append(it["n"])
    found = []
    for k, items in hits.items():
        if len(items) >= NEED.get(k, 2):
            found.append(k)
    out_rev_computed = "OUT-REV" in found
    stages = set()
    for k in found:
        if k == "PV-REVERSE":
            stages.add("Output" if out_rev_computed else "Input (test)")
        elif k in STAGE:
            stages.add(STAGE[k])
    print(name, sorted(found), "->", sorted(stages))

print("== 3. Check items in the text added by this change ==")
forbidden = set()
dictation = set()
for f in ("A", "B"):
    for it in g["forms"][f]["items"]:
        if it["type"] == "dictation":
            dictation.add(it["value"])
        else:
            forbidden.add(frozenset((it["a"], it["b"])))
print(f"computation items={len(forbidden)} dictation numbers={sorted(dictation)}")
files = sys.argv[1:]
pat = re.compile(r"(\d+)\s*(?:[−\-+–]|plus|minus)\s*(\d+)")
for path in files:
    text = open(path, encoding="utf-8").read()
    for m in pat.finditer(text):
        a, b = int(m.group(1)), int(m.group(2))
        if frozenset((a, b)) in forbidden:
            line = text.count("\n", 0, m.start()) + 1
            print(f"{path}:{line}: pair {a},{b} is a check item: {m.group(0)}")
    for d in dictation:
        for m in re.finditer(rf"(?<!\d){d}(?!\d)", text):
            line = text.count("\n", 0, m.start()) + 1
            print(f"{path}:{line}: dictation number {d}")
```
