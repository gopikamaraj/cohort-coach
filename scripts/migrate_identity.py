# ruff: noqa: E501
"""Move every record from device ids and nickname hashes to the user id (the normalised nickname).

    python scripts/migrate_identity.py                    DRY RUN (default): does everything inside one transaction,
                                                          prints the counts per table, then rolls back. Nothing changes.
    python scripts/migrate_identity.py --apply            the same, committed. Run only after a backup (the script
                                                          refuses an SQLite file without --backup-done).
    python scripts/migrate_identity.py --apply --backup-done
    python scripts/migrate_identity.py --list-unclaimed   rows kept under an `unclaimed:` owner
    python scripts/migrate_identity.py --revert backups/identity-migration-YYYYMMDD-HHMMSS.json

DATABASE_URL names the database (a local SQLite file by default). It never touches a cloud database unless
DATABASE_URL points at one, and then it prints the host and asks for --i-mean-the-hosted-database.

How a record finds its user (the mapping the old data already holds):
  * a store key (the 16-hex hash of the nickname) -> the `nickname` settings document stored under that key;
  * a class code (`c-...`) -> the store key that holds that class document -> its nickname;
  * a teacher (`t-...`) -> the class her phone made (teachers.class_id, or the class in her cohorts' check ids);
  * a device id (consents, channel links) -> its teacher.
Anything that cannot be mapped is NOT deleted: it moves to an `unclaimed:<old id>` owner, is listed, and
`scripts/claim_unclaimed.py` hands it to a real user later.

Nothing in this file prints an answer, a child, or a token: ids, nicknames' normalised form and counts only."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.api.db import User, make_engine  # noqa: E402
from services.api.devicestore import UserDoc  # noqa: E402
from services.api.identity import normalise  # noqa: E402

UNCLAIMED = "unclaimed:"
BACKUPS = Path(__file__).resolve().parents[1] / "backups"

# (table, column) holding a teacher id
TEACHER_COLS = [
    ("channel_links", "teacher_id"),
    ("link_codes", "teacher_id"),
    ("flow_state", "teacher_id"),
    ("lesson_taps", "teacher_id"),
    ("class_cohorts", "teacher_id"),
    ("audio_download_use", "teacher_id"),
    ("cohort_members", "teacher_id"),
    ("thread_posts", "author_teacher_id"),
    ("chat_threads", "teacher_id"),
    ("tracks", "teacher_id"),
]


class Plan:
    """What the migration does, counted. Filled by `run`."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.unclaimed: list[tuple[str, str]] = []  # (table, old id)
        self.log: list[dict[str, str]] = []  # (table, column, old, new) for --revert

    def moved(self, table: str, col: str, old: str, new: str, n: int) -> None:
        if n:
            self.counts[f"{table}.{col}"] += n
            self.log.append({"table": table, "column": col, "old": old, "new": new})
            if new.startswith(UNCLAIMED):
                self.unclaimed.append((table, old))


def has(conn: Connection, table: str) -> bool:
    return inspect(conn).has_table(table)


def cols(conn: Connection, table: str) -> set[str]:
    return {c["name"] for c in inspect(conn).get_columns(table)} if has(conn, table) else set()


def uid_for_nickname(nick: str) -> str | None:
    uid = normalise(nick)
    return uid if uid and len(uid) <= 32 else None


def build_maps(conn: Connection) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    """storekey -> uid, class code -> uid, teacher id -> uid, device id -> teacher id."""
    key_uid: dict[str, str] = {}
    class_owner: dict[str, str] = {}
    if has(conn, "device_docs"):
        for dev, doc_id, data in conn.execute(text("SELECT device, doc_id, data FROM device_docs WHERE collection='settings'")):
            if doc_id == "nickname":
                value = (json.loads(data) if isinstance(data, str) else data or {}).get("value")
                uid = uid_for_nickname(str(value or ""))
                if uid:
                    key_uid[dev] = uid
        for dev, doc_id in conn.execute(text("SELECT device, doc_id FROM device_docs WHERE collection='classes'")):
            if dev in key_uid:
                class_owner.setdefault(doc_id, key_uid[dev])
    teacher_uid: dict[str, str] = {}
    device_teacher: dict[str, str] = {}
    if has(conn, "channel_links"):
        for ch, ext, tid in conn.execute(text("SELECT channel, external_id, teacher_id FROM channel_links")):
            if ch == "pwa" and re.fullmatch(r"[0-9a-f]{16}", ext):  # a device id, not an already-migrated user id
                device_teacher[ext] = tid
    if has(conn, "teachers"):
        for tid, class_id in conn.execute(text("SELECT teacher_id, class_id FROM teachers")):
            if class_id and class_id in class_owner:
                teacher_uid[tid] = class_owner[class_id]
    if has(conn, "class_cohorts"):
        for tid, check_id in conn.execute(text("SELECT teacher_id, check_id FROM class_cohorts")):
            cls = str(check_id).split(":")[0]
            if tid not in teacher_uid and cls in class_owner and tid != "coach-cohorts":
                teacher_uid[tid] = class_owner[cls]
    return key_uid, class_owner, teacher_uid, device_teacher


def rekey(conn: Connection, plan: Plan, table: str, col: str, old: str, new: str) -> None:
    if not has(conn, table) or col not in cols(conn, table):
        return
    n = conn.execute(text(f'UPDATE "{table}" SET "{col}" = :new WHERE "{col}" = :old'), {"new": new, "old": old}).rowcount or 0
    plan.moved(table, col, old, new, n)


def run(conn: Connection, plan: Plan) -> None:
    key_uid, class_owner, teacher_uid, device_teacher = build_maps(conn)
    pg = conn.dialect.name == "postgresql"

    # 1. new tables, widened ids, renamed columns
    from services.modules.models import CohortPlan, CohortPlanModule

    for t in (CohortPlan.__table__, CohortPlanModule.__table__):
        t.create(conn, checkfirst=True)  # type: ignore[attr-defined]
    if has(conn, "tracks") and "plan_id" not in cols(conn, "tracks"):
        conn.execute(text("ALTER TABLE tracks ADD COLUMN plan_id VARCHAR(24)"))
    if has(conn, "class_cohorts") and "group_id" not in cols(conn, "class_cohorts"):
        conn.execute(text("ALTER TABLE class_cohorts ADD COLUMN group_id VARCHAR(40)"))
    for t in (User.__table__, UserDoc.__table__):
        t.create(conn, checkfirst=True)  # type: ignore[attr-defined]
    if pg:
        for table, col in TEACHER_COLS + [("teachers", "teacher_id")]:
            if has(conn, table):
                conn.execute(text(f'ALTER TABLE "{table}" ALTER COLUMN "{col}" TYPE VARCHAR(32)'))
    if has(conn, "kept_sheet") and "device" in cols(conn, "kept_sheet"):
        conn.execute(text('ALTER TABLE kept_sheet RENAME COLUMN device TO owner'))
        if pg:
            conn.execute(text("ALTER TABLE kept_sheet ALTER COLUMN owner TYPE VARCHAR(32)"))
    if has(conn, "profile_sync") and "owner" not in cols(conn, "profile_sync"):
        conn.execute(text("ALTER TABLE profile_sync ADD COLUMN owner VARCHAR(32) NOT NULL DEFAULT 'unclaimed'"))
    for t in ("tester_device", "tester_event", "tester_feedback"):
        if has(conn, t) and "device_hash" in cols(conn, t):
            conn.execute(text(f'ALTER TABLE {t} RENAME COLUMN device_hash TO user_id'))
            if pg:
                conn.execute(text(f"ALTER TABLE {t} ALTER COLUMN user_id TYPE VARCHAR(64)"))  # widened later, hashes are 64

    # 2. users: every nickname we know, once
    nick_display: dict[str, str] = {}
    if has(conn, "device_docs"):
        for dev, data in conn.execute(text("SELECT device, data FROM device_docs WHERE collection='settings' AND doc_id='nickname'")):
            value = (json.loads(data) if isinstance(data, str) else data or {}).get("value")
            if dev in key_uid:
                nick_display.setdefault(key_uid[dev], str(value)[:30])
    tester_nick: dict[str, str] = {}  # old device hash -> uid (the tester table also records a nickname)
    if has(conn, "tester_device"):
        for h, nick in conn.execute(text("SELECT user_id, nickname FROM tester_device")):
            uid = uid_for_nickname(str(nick))
            if uid and h != uid and len(h) == 64:
                tester_nick[h] = uid
                nick_display.setdefault(uid, str(nick)[:30])
    existing = {r[0] for r in conn.execute(text("SELECT id FROM users"))}
    for uid, disp in sorted(nick_display.items()):
        if uid not in existing:
            conn.execute(text("INSERT INTO users (id, nickname, created_at, last_seen_at) VALUES (:i, :n, :t, :t)"), {"i": uid, "n": disp, "t": datetime.now(UTC)})
            plan.counts["users.created"] += 1

    # 3. the store: device_docs -> user_docs (a copy; the old table is kept as legacy_device_docs)
    if has(conn, "device_docs"):
        for dev, coll, doc_id, data, upd in conn.execute(text("SELECT device, collection, doc_id, data, updated_at FROM device_docs")).fetchall():
            owner = key_uid.get(dev, UNCLAIMED + dev)
            if owner.startswith(UNCLAIMED):
                plan.unclaimed.append(("device_docs", dev))
            if conn.execute(text("SELECT 1 FROM user_docs WHERE owner=:o AND collection=:c AND doc_id=:d"), {"o": owner, "c": coll, "d": doc_id}).first():
                continue
            conn.execute(text("INSERT INTO user_docs (owner, collection, doc_id, data, updated_at) VALUES (:o,:c,:d,:data,:u)"), {"o": owner, "c": coll, "d": doc_id, "data": json.dumps(data) if not isinstance(data, str) else data, "u": upd})
            plan.counts["user_docs.rows"] += 1
        conn.execute(text("ALTER TABLE device_docs RENAME TO legacy_device_docs"))

    # 4. teachers: t-... -> user id, or unclaimed:<t-...>
    all_teachers = [r[0] for r in conn.execute(text("SELECT teacher_id FROM teachers"))] if has(conn, "teachers") else []
    for tid in all_teachers:
        if not re.fullmatch(r"t-[0-9a-f]{16}", tid):  # already a user id, an unclaimed owner, or the system owner
            continue
        new = teacher_uid.get(tid, UNCLAIMED + tid)
        if new == tid:
            continue
        if conn.execute(text("SELECT 1 FROM teachers WHERE teacher_id=:n"), {"n": new}).first():  # a user with two phones: keep one teacher row
            conn.execute(text("DELETE FROM teachers WHERE teacher_id=:o"), {"o": tid})
            plan.counts["teachers.merged"] += 1
            for table, col in TEACHER_COLS:
                rekey(conn, plan, table, col, tid, new)
            continue
        # Postgres enforces the foreign keys: add the new teacher row first, repoint the children, then drop the old one.
        conn.execute(text("INSERT INTO teachers (teacher_id, lang, consent, judge, class_id, created_at) SELECT :n, lang, consent, judge, class_id, created_at FROM teachers WHERE teacher_id=:o"), {"n": new, "o": tid})
        for table, col in TEACHER_COLS:
            rekey(conn, plan, table, col, tid, new)
        conn.execute(text("DELETE FROM teachers WHERE teacher_id=:o"), {"o": tid})
        plan.counts["teachers.rekeyed"] += 1
        if new.startswith(UNCLAIMED):
            plan.unclaimed.append(("teachers", tid))
    # web links: external id becomes the user id
    if has(conn, "channel_links"):
        for dev, tid in device_teacher.items():
            new = teacher_uid.get(tid, UNCLAIMED + tid)
            rekey(conn, plan, "channel_links", "external_id", dev, new)
        # a second device of one user leaves two identical links: keep one
        conn.execute(text("DELETE FROM channel_links WHERE channel='pwa' AND rowid NOT IN (SELECT MIN(rowid) FROM channel_links WHERE channel='pwa' GROUP BY external_id)" if not pg else "DELETE FROM channel_links a USING channel_links b WHERE a.channel='pwa' AND b.channel='pwa' AND a.external_id=b.external_id AND a.ctid > b.ctid"))

    # 5. consents (subject = the device id) follow their teacher's user
    if has(conn, "consents"):
        for dev, tid in device_teacher.items():
            rekey(conn, plan, "consents", "subject_id", dev, teacher_uid.get(tid, UNCLAIMED + tid))
        left = conn.execute(text("SELECT DISTINCT subject_id FROM consents WHERE subject_id NOT LIKE 'unclaimed:%'")).fetchall()
        known = set(teacher_uid.values()) | existing | set(nick_display)
        for (sid,) in left:
            if sid not in known and re.fullmatch(r"[0-9a-f]{16}", sid):
                rekey(conn, plan, "consents", "subject_id", sid, UNCLAIMED + sid)

    # 6. class results and kept sheets follow the class's owner
    if has(conn, "profile_sync"):
        for (cid,) in conn.execute(text("SELECT DISTINCT class_id FROM profile_sync")).fetchall():
            n = conn.execute(text("UPDATE profile_sync SET owner=:o WHERE class_id=:c AND owner IN ('unclaimed', :o2)"), {"o": class_owner.get(cid, UNCLAIMED + cid), "c": cid, "o2": ""}).rowcount or 0
            plan.moved("profile_sync", "owner", cid, class_owner.get(cid, UNCLAIMED + cid), n)
    if has(conn, "kept_sheet"):
        for (dev, cid) in conn.execute(text("SELECT DISTINCT owner, class_id FROM kept_sheet")).fetchall():
            new = class_owner.get(cid) or teacher_uid.get(device_teacher.get(dev, ""), UNCLAIMED + dev)
            rekey(conn, plan, "kept_sheet", "owner", dev, new) if dev != new else None

    # 7. group cohorts: members keyed by store key -> user id
    if has(conn, "class_cohorts"):
        for cid, counts in conn.execute(text("SELECT id, counts FROM class_cohorts WHERE teacher_id='coach-cohorts'")).fetchall():
            data = json.loads(counts) if isinstance(counts, str) else dict(counts or {})
            members = data.get("_members") or {}
            if members and any(k in key_uid for k in members):
                data["_members"] = {key_uid.get(k, k): v for k, v in members.items()}
                conn.execute(text("UPDATE class_cohorts SET counts=:c WHERE id=:i"), {"c": json.dumps(data), "i": cid})
                plan.counts["class_cohorts.members_rekeyed"] += 1

    # 8. tester analytics: the device hash becomes the user id; one user's several devices merge into one row
    if has(conn, "tester_device"):
        for h, uid in tester_nick.items():
            for t in ("tester_event", "tester_feedback"):
                rekey(conn, plan, t, "user_id", h, uid)
            first = conn.execute(text("SELECT user_id FROM tester_device WHERE user_id=:u"), {"u": uid}).first()
            if first and h != uid:
                conn.execute(text("DELETE FROM tester_device WHERE user_id=:h"), {"h": h})  # events already moved; a duplicate device row
                plan.counts["tester_device.merged"] += 1
            else:
                rekey(conn, plan, "tester_device", "user_id", h, uid)
        for (h,) in conn.execute(text("SELECT user_id FROM tester_device WHERE length(user_id) = 64")).fetchall():
            rekey(conn, plan, "tester_device", "user_id", h, UNCLAIMED + h[:16])
            for t in ("tester_event", "tester_feedback"):
                rekey(conn, plan, t, "user_id", h, UNCLAIMED + h[:16])


    # 9. improvement plans: one per cohort and error; each teacher's track keeps her own progress, feedback and branch
    if has(conn, "tracks"):
        from sqlalchemy.orm import Session as OrmSession

        from services.modules.plans import merge_teacher_plans

        with OrmSession(bind=conn) as orm:
            for k, v in merge_teacher_plans(orm).items():
                plan.counts[f"plans.{k}"] += v
            orm.flush()


def print_report(plan: Plan, applied: bool) -> None:
    print(("APPLIED" if applied else "DRY RUN (nothing was changed)") + ": rows re-keyed per table.column")
    for k, v in sorted(plan.counts.items()):
        print(f"  {k:36s} {v}")
    by_table = Counter(t for t, _ in plan.unclaimed)
    print(f"unclaimed (kept, not deleted, listed by --list-unclaimed): {sum(by_table.values())}")
    for t, n in sorted(by_table.items()):
        print(f"  {t:36s} {n}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backup-done", action="store_true", help="I have a copy of the database file / a cloud backup")
    ap.add_argument("--i-mean-the-hosted-database", action="store_true")
    ap.add_argument("--list-unclaimed", action="store_true")
    ap.add_argument("--revert", metavar="LOGFILE")
    args = ap.parse_args(argv)
    engine = make_engine()
    url = engine.url
    hosted = url.get_backend_name() != "sqlite"
    print(f"database: {url.get_backend_name()} {url.host or url.database}")
    if hosted and args.apply and not args.i_mean_the_hosted_database:
        print("This is a hosted database. Re-run with --i-mean-the-hosted-database after taking a Cloud SQL backup.")
        return 2
    if args.list_unclaimed:
        with engine.connect() as conn:
            for t, c in [("user_docs", "owner"), ("teachers", "teacher_id"), ("consents", "subject_id"), ("profile_sync", "owner"), ("kept_sheet", "owner"), ("class_cohorts", "teacher_id")]:
                if has(conn, t):
                    n = conn.execute(text(f"SELECT {c}, count(*) FROM {t} WHERE {c} LIKE 'unclaimed:%' GROUP BY {c}")).fetchall()
                    for owner, k in n:
                        print(f"{t:14s} {owner:34s} {k}")
        return 0
    if args.revert:
        log = json.loads(Path(args.revert).read_text(encoding="utf-8"))
        with engine.begin() as conn:
            for e in reversed(log["moves"]):
                if has(conn, e["table"]):
                    conn.execute(text(f'UPDATE "{e["table"]}" SET "{e["column"]}" = :old WHERE "{e["column"]}" = :new'), {"old": e["old"], "new": e["new"]})
            if has(conn, "legacy_device_docs"):
                conn.execute(text("DROP TABLE IF EXISTS device_docs"))
                conn.execute(text("ALTER TABLE legacy_device_docs RENAME TO device_docs"))
            conn.execute(text("DROP TABLE IF EXISTS user_docs"))
        print("Reverted the value moves and restored device_docs. Teacher rows re-keyed or merged are restored from the backup copy of the database: see the log's note.")
        return 0
    if args.apply and not hosted and not args.backup_done:
        print("Back up the database file first, then run again with --backup-done.")
        return 2
    plan = Plan()
    if not args.apply and url.get_backend_name() == "sqlite" and url.database:
        # pysqlite does not roll DDL back, so a dry run works on a throwaway copy of the file
        import shutil
        import tempfile

        copy = Path(tempfile.mkdtemp()) / "dry-run.sqlite"
        shutil.copy(url.database, copy)
        engine = make_engine(f"sqlite:///{copy}")
        print(f"dry run on a copy of the file: {copy}")
    conn = engine.connect()
    trans = conn.begin()
    try:
        run(conn, plan)
        if args.apply:
            trans.commit()
            BACKUPS.mkdir(exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            log = BACKUPS / f"identity-migration-{stamp}.json"
            log.write_text(json.dumps({"moves": plan.log, "unclaimed": plan.unclaimed, "note": "merged teacher rows and merged tester devices are not reversible by value; restore the database backup for those"}, indent=1), encoding="utf-8")
            print(f"revert log: {log}")
        else:
            trans.rollback()
    except Exception:
        trans.rollback()
        raise
    finally:
        conn.close()
    print_report(plan, args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
