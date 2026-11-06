// App state: the language and role (kept in localStorage, they are tiny), and what the phone
// holds for the active class and her current check (kept in IndexedDB and reloaded after every change).
import { reconcileWithServer } from "./lib/serverTruth";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { isLang, t as translate, type Key, type Lang } from "./i18n";
import { clearCloud, forgetQueue, hydrate, watchTables } from "./lib/cloudStore";
import { activeClass, clearPhone, db, getSetting, type CheckRow, type ClassRow, type ProfileRow } from "./lib/db";
import { currentCheck, nextSeq, seqOf } from "./lib/checks";
import { demoPair } from "./lib/demo";
import { fetchPaperKey } from "./lib/paperKeys";
import { samplePaper } from "./lib/papers";
import { keys } from "./lib/diagnosis";
import { backfillAnyCounts, fetchMissingPaperKeys, finishCheck } from "./lib/check";
import { pendingCount } from "./lib/sync";
import { flushAllowed } from "./lib/sendnow";
import { requestPersistence } from "./lib/storage";
import { track } from "./lib/tester";
import { isOnline, setForcedOffline, useForcedOffline, useOnline } from "./lib/net";

export type Role = "teacher" | "coach" | "mentor" | "officer" | "admin" | "judge";
export const ROLES: readonly Role[] = ["judge", "teacher", "mentor", "coach", "officer", "admin"];

interface AppState {
  lang: Lang;
  setLang: (lang: Lang) => void;
  role: Role;
  setRole: (role: Role) => void;
  /** The running number of the check she is on (or about to start): it only keeps check ids apart. */
  slot: number;
  /** How many checks the active class has, so a screen can tell whether it has a later one. */
  checkCount: number;
  online: boolean;
  forcedOffline: boolean;
  setOffline: (on: boolean) => void;
  klass: ClassRow | null;
  profile: ProfileRow | null;
  check: CheckRow | null;
  pending: number;
  reload: () => Promise<void>;
  loadDemo: () => Promise<void>;
  /** Start another check for the class: earlier ones stay as they are. */
  startAnother: () => Promise<void>;
  /** Judge mode and the tour: add the simulated later check (the post-test) to the demo class. */
  addLaterDemo: () => Promise<void>;
  reset: (alsoServer?: boolean) => Promise<void>; // alsoServer false: clear this phone only, the account on the server stays
  tr: (key: Key, params?: Record<string, string | number>) => string;
}

const Ctx = createContext<AppState | null>(null);

function stored<T>(key: string, ok: (v: unknown) => v is T, fallback: T): T {
  try {
    const v = localStorage.getItem(key);
    return v !== null && ok(v) ? v : fallback;
  } catch {
    return fallback;
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => stored("cc.lang", isLang, "en"));
  const [role, setRoleState] = useState<Role>(() =>
    stored("cc.role", (v): v is Role => (ROLES as readonly string[]).includes(v as string), "teacher"),
  );
  const [slot, setSlot] = useState(1);
  const [checkCount, setCheckCount] = useState(0);
  const fresh = useRef<number | null>(null); // the number of a check she asked to start; in memory only
  const [klass, setKlass] = useState<ClassRow | null>(null);
  const [profile, setProfile] = useState<ProfileRow | null>(null);
  const [check, setCheck] = useState<CheckRow | null>(null);
  const [pending, setPending] = useState(0);
  const online = useOnline();
  const forcedOffline = useForcedOffline();

  const reload = useCallback(async () => {
    const id = await getSetting<string | null>("activeClass", null);
    const row = id ? ((await db.classes.get(id)) ?? null) : null;
    const all = row ? await db.checks.where("classId").equals(row.id).toArray() : [];
    if (fresh.current !== null && all.some((c) => seqOf(c.id) === fresh.current)) fresh.current = null; // the new check now exists
    // Her current check is the one still being entered, else the most recent: no term decides it.
    const cur = row && fresh.current === null ? currentCheck(all, row.id) : undefined;
    setSlot(fresh.current ?? (cur ? seqOf(cur.id) : row ? nextSeq(all, row.id) : 1));
    setCheckCount(all.length);
    setKlass(row);
    setProfile(cur ? ((await db.profiles.get(cur.id)) ?? null) : null);
    setCheck(cur ?? null);
    setPending(await pendingCount());
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  // Load on open, and send what is waiting whenever a signal is there.
  useEffect(() => {
    if (online) void reconcileWithServer(); // the server is the truth: drop pointers to records it no longer has
    void requestPersistence(); // ask the browser to keep this phone's data; harmless if it declines
    watchTables(); // every change to the classes, checks and results is written to the cloud copy
    void reload().then(() => hydrate()).then(async (got) => { const filled = await backfillAnyCounts().catch(() => 0); const keyed = await fetchMissingPaperKeys().catch(() => 0); if (got !== "same" || filled || keyed) await reload(); }).then(async () => { // the cloud copy is the record: read it back first
      await flushAllowed(isOnline());
      setPending(await pendingCount());
    });
  }, [reload, online]);

  // A new nickname is a different teacher: read her documents from the cloud (her data moves up if she has none yet).
  useEffect(() => {
    const again = () => {
      forgetQueue();
      void hydrate().then(async (got) => {
        const keyed = await fetchMissingPaperKeys().catch(() => 0); // her checks' papers: the answer keys this device lacks
        if (got !== "same" || keyed) await reload();
      });
    };
    window.addEventListener("cc:identity", again);
    return () => window.removeEventListener("cc:identity", again);
  }, [reload]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      localStorage.setItem("cc.lang", next);
    } catch {
      /* not saved in private mode */
    }
  }, []);

  const setRole = useCallback((next: Role) => {
    setRoleState(next);
    try {
      localStorage.setItem("cc.role", next);
    } catch {
      /* not saved in private mode */
    }
  }, []);

  const putDemo = useCallback(async (kind: "pre" | "post"): Promise<void> => {
    const row = await activeClass(true);
    // A pre-test and, later, its post-test with the same children in the same order, so the before-and-after
    // view has something to show. All of it is made up. Each check is on a real paper (the sample paper and its
    // twin, stored on the server and keyed like any paper); with no connection the same numbers are used from
    // the phone's built-in copy.
    const { pre, post } = demoPair();
    const day = 86_400_000;
    const existing = await db.checks.where("classId").equals(row.id).toArray();
    const seq = nextSeq(existing, row.id);
    const id = `${row.id}:${seq}`;
    let form = kind === "post" ? "B" : "A";
    let code: string | null = null;
    try {
      const p = await samplePaper(id, kind, "Demo", seq, lang);
      await fetchPaperKey(p.id, { role: "teacher", classId: row.id });
      form = p.id;
      code = p.check_code;
    } catch {
      /* the built-in copy is used */
    }
    const rows = kind === "post" ? post : pre;
    const at = kind === "post" ? Date.now() : Date.now() - 21 * day;
    await db.checks.put({
      id, classId: row.id, term: seq, formKey: form, children: rows, updatedAt: at,
      kind, round: 1, checkDate: new Date(at).toISOString().slice(0, 10), paperVersion: keys.content_hash,
      trackId: null, expectedChildren: rows.length, status: "closed", paperId: form.startsWith("P-") ? form : null, paperCode: code,
    });
    const result = await finishCheck(row.id, seq, form, rows, true);
    if (kind === "post") {
      const first = existing.find((c) => c.kind === "pre") ?? existing[0];
      const prof = first ? await db.profiles.get(first.id) : undefined;
      await db.checks.update(id, { trackId: prof?.track ?? null });
    } else if (result.track) await db.checks.update(id, { trackId: result.track });
  }, [lang]);

  const loadDemo = useCallback(async () => {
    track("sample_input_run", { value: { sample: "demo_class" } });
    const row = await activeClass(true);
    if ((await db.checks.where("classId").equals(row.id).count()) === 0) await putDemo("pre");
    await reload();
    await flushAllowed(isOnline());
    setPending(await pendingCount());
  }, [reload, putDemo]);

  const addLaterDemo = useCallback(async () => {
    const row = await activeClass(true);
    const have = await db.checks.where("classId").equals(row.id).toArray();
    if (have.length === 0) await putDemo("pre");
    if (!have.some((c) => c.kind === "post")) await putDemo("post");
    await reload();
    await flushAllowed(isOnline());
    setPending(await pendingCount());
  }, [reload, putDemo]);

  const startAnother = useCallback(async () => {
    const row = klass;
    const all = row ? await db.checks.where("classId").equals(row.id).toArray() : [];
    fresh.current = row ? nextSeq(all, row.id) : 1;
    await reload();
  }, [reload, klass]);

  const reset = useCallback(async (alsoServer = true) => {
    await clearCloud(undefined, alsoServer);
    await clearPhone();
    await reload();
  }, [reload]);

  const value = useMemo<AppState>(
    () => ({
      lang,
      setLang,
      role,
      setRole,
      slot,
      checkCount,
      online,
      forcedOffline,
      setOffline: (on: boolean) => {
        setForcedOffline(on);
        if (!on) void flushAllowed(isOnline()).then(reload);
      },
      klass,
      profile,
      check,
      pending,
      reload,
      loadDemo,
      startAnother,
      addLaterDemo,
      reset,
      tr: (key, params) => translate(lang, key, params),
    }),
    [lang, setLang, role, setRole, slot, checkCount, online, forcedOffline, klass, profile, check, pending, reload, loadDemo, startAnother, addLaterDemo, reset],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const value = useContext(Ctx);
  if (!value) throw new Error("useApp needs an AppProvider");
  return value;
}
