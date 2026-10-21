// App state: the language and role (kept in localStorage, they are tiny), and what the phone
// holds for the active class and term (kept in IndexedDB and reloaded after every change).
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { isLang, t as translate, type Key, type Lang } from "./i18n";
import { activeClass, clearPhone, db, getSetting, setSetting, type CheckRow, type ClassRow, type ProfileRow } from "./lib/db";
import { demoChildren, DEMO_FORM } from "./lib/demo";
import { finishCheck } from "./lib/check";
import { pendingCount } from "./lib/sync";
import { flushAllowed } from "./lib/sendnow";
import { requestPersistence } from "./lib/storage";
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
    const row = await activeClass(true);
    const termNow = await getSetting("term", 1);
    const rows = demoChildren(termNow);
    await db.checks.put({ id: `${row.id}:${termNow}`, classId: row.id, term: termNow, formKey: DEMO_FORM, children: rows, updatedAt: Date.now() });
    await finishCheck(row.id, termNow, DEMO_FORM, rows, true);
    await reload();
    await flushAllowed(isOnline());
    setPending(await pendingCount());
  }, [reload]);

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
