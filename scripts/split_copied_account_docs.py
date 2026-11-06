"""Move what the nickname '3b math' holds of '3a math' out of her account, to an `unclaimed:` owner (nothing is deleted).
Dry run by default; --apply commits. Prints ids and counts only."""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.getcwd())
from sqlalchemy import text

from services.api.db import make_engine

APPLY = "--apply" in sys.argv
WHO = "3b math"
PARK = "unclaimed:3b-copy-of-3a"  # 23 characters: fits the 32-character owner column
COPIED_CLASSES = ["c-9d43d6c63e", "c-e0ea0c2d27"]  # 3A's class ids, copied into 3B's account by the old shared key
COPIED_TRANSCRIPTS = ["43a0f0a92561", "a6f09bc78cc8"]  # 3A's two Practice Class sessions, the same ids in both accounts
COHORT = "cc-9b5eaa634841"  # "3A Class: Borrows a ten..." shown to 3B

engine = make_engine()
log: list[dict] = []


class DryRun(Exception):
    pass


try:
  with engine.begin() as c:
      print("kept sheets held by", WHO, "by class:", list(c.execute(text("select class_id, count(*) from kept_sheet where owner=:o group by 1"), {"o": WHO})))
      docs = [("classes", i) for i in COPIED_CLASSES] + [("transcripts", i) for i in COPIED_TRANSCRIPTS]
      for coll, doc in docs:
          for table in ("user_docs", "doc_versions"):
              n = c.execute(text(f"update {table} set owner=:p where owner=:o and collection=:c and doc_id=:d"), {"p": PARK, "o": WHO, "c": coll, "d": doc}).rowcount
              if n:
                  log.append({"table": table, "owner_from": WHO, "owner_to": PARK, "collection": coll, "doc_id": doc})
              print(f"{table} {coll}/{doc}: {n}")
      n = c.execute(text("update class_cohorts set teacher_id=:p where id=:i and teacher_id=:o"), {"p": PARK, "i": COHORT, "o": WHO}).rowcount
      print("class_cohorts", COHORT, n)
      if n:
          log.append({"table": "class_cohorts", "id": COHORT, "teacher_from": WHO, "teacher_to": PARK})
      m = c.execute(text("update tracks set teacher_id=:p where class_cohort_id=:i and teacher_id=:o"), {"p": PARK, "i": COHORT, "o": WHO}).rowcount
      print("tracks of that cohort", m)
      if m:
          log.append({"table": "tracks", "class_cohort_id": COHORT, "teacher_from": WHO, "teacher_to": PARK})
      left = list(c.execute(text("select id, name from class_cohorts where teacher_id=:o order by id"), {"o": WHO}))
      print("cohorts left for", WHO, [(i, n[:40]) for i, n in left])
      print("classes left for", WHO, [r[0] for r in c.execute(text("select doc_id from user_docs where owner=:o and collection='classes' order by 1"), {"o": WHO})])
      if not APPLY:
          print("DRY RUN: nothing changed")
          raise DryRun()
      os.makedirs("backups", exist_ok=True)
      path = "backups/split-3b-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"
      json.dump(log, open(path, "w", encoding="utf-8"), indent=1)
      print("APPLIED; revert log:", path)
except DryRun:
  pass
