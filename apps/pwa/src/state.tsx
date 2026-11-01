// App state: the language and role (kept in localStorage, they are tiny), and what the phone
// holds for the active class and term (kept in IndexedDB and reloaded after every change).
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { isLang, t as translate, type Key, type Lang } from "./i18n";
import { activeClass, clearPhone, db, getSetting, setSetting, type CheckRow, type ClassRow, type ProfileRow } from "./lib/db";
import { demoPair } from "./lib/demo";
import { fetchPaperKey } from "./lib/paperKeys";
import { samplePaper } from "./lib/papers";
import { keys } from "./lib/diagnosis";
import { finishCheck } from "./lib/check";
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
  term: number;
  online: boolean;
  forcedOffline: boolean;
  setOffline: (on: boolean) => void;
  klass: ClassRow | null;
  profile: ProfileRow | null;
  check: CheckRow | null;
  pending: number;
  reload: () => Promise<void>;
  loadDemo: () => Promise<void>;
  advanceTerm: () => Promise<void>;
  reset: () => Promise<void>;
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
  const [term, setTerm] = useState(1);
  const [klass, setKlass] = useState<ClassRow | null>(null);
  const [profile, setProfile] = useState<ProfileRow | null>(null);
  const [check, setCheck] = useState<CheckRow | null>(null);
  const [pending, setPending] = useState(0);
  const online = useOnline();
  const forcedOffline = useForcedOffline();

  const reload = useCallback(async () => {
    const termNow = await getSetting("term", 1);
    const id = await getSetting<string | null>("activeClass", null);
    const row = id ? ((await db.classes.get(id)) ?? null) : null;
    setTerm(termNow);
    setKlass(row);
    setProfile(row ? ((await db.profiles.get(`${row.id}:${termNow}`)) ?? null) : null);
    setCheck(row ? ((await db.checks.get(`${row.id}:${termNow}`)) ?? null) : null);
    setPending(await pendingCount());
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  // Load on open, and send what is waiting whenever a signal is there.
  useEffect(() => {
    void requestPersistence(); // ask the browser to keep this phone's data; harmless if it declines
    void reload().then(async () => {
      await flushAllowed(isOnline());
      setPending(await pendingCount());
    });
  }, [reload, online]);

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

  const loadDemo = useCallback(async () => {
    track("sample_input_run", { value: { sample: "demo_class" } });
    const row = await activeClass(true);
    const termNow = await getSetting("term", 1);
    // A pre-test and, from term 2, its post-test with the same children in the same order, so the
    // before-and-after view has something to show. All of it is made up. Each check is on a real paper
    // (the sample paper and its twin, stored on the server and keyed like any paper); with no
    // connection the same numbers are used from the phone's built-in copy.
    const { pre, post } = demoPair();
    const day = 86_400_000;
    const paperFor = async (kind: "pre" | "post", term: number): Promise<{ id: string; code: string | null }> => {
      try {
        const p = await samplePaper(`${row.id}:${term}`, kind, "Demo", term, lang);
        await fetchPaperKey(p.id, { role: "teacher", classId: row.id });
        return { id: p.id, code: p.check_code };
      } catch {
        return { id: kind === "post" ? "B" : "A", code: null };
      }
    };
    const put = async (term: number, kind: "pre" | "post", rows: string[][], at: number) => {
      const paper = await paperFor(kind, term);
      const form = paper.id;
      await db.checks.put({
        id: `${row.id}:${term}`, classId: row.id, term, formKey: form, children: rows, updatedAt: at,
        kind, round: 1, checkDate: new Date(at).toISOString().slice(0, 10), paperVersion: keys.content_hash,
        trackId: null, expectedChildren: rows.length, status: "closed", paperId: form.startsWith("P-") ? form : null, paperCode: paper.code,
      });
      const result = await finishCheck(row.id, term, form, rows, true);
      if (result.track) await db.checks.update(`${row.id}:${term}`, { trackId: result.track });
    };
    if (termNow >= 2) {
      if (!(await db.checks.get(`${row.id}:1`))) await put(1, "pre", pre, Date.now() - 21 * day);
      await put(termNow, "post", post, Date.now());
      const first = await db.profiles.get(`${row.id}:1`);
      await db.checks.update(`${row.id}:${termNow}`, { trackId: first?.track ?? null });
    } else await put(termNow, "pre", pre, Date.now());
    await reload();
    await flushAllowed(isOnline());
    setPending(await pendingCount());
  }, [reload, lang]);

  const advanceTerm = useCallback(async () => {
    await setSetting("term", 2);
    await reload();
  }, [reload]);

  const reset = useCallback(async () => {
    await clearPhone();
    await reload();
  }, [reload]);

  const value = useMemo<AppState>(
    () => ({
      lang,
      setLang,
      role,
      setRole,
      term,
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
      advanceTerm,
      reset,
      tr: (key, params) => translate(lang, key, params),
    }),
    [lang, setLang, role, setRole, term, online, forcedOffline, klass, profile, check, pending, reload, loadDemo, advanceTerm, reset],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const value = useContext(Ctx);
  if (!value) throw new Error("useApp needs an AppProvider");
  return value;
}
