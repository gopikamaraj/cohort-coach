// The role config for the landing page and its dialog. It comes from the server (the same file the
// server enforces); the app holds no second copy of what each role can and cannot do.
import { useEffect, useState } from "react";
import { API_BASE } from "./api";

export type RoleId = "teacher" | "mentor" | "coach" | "officer";
export const ROLE_IDS: readonly RoleId[] = ["teacher", "mentor", "coach", "officer"];

export interface RoleLine {
  id: string;
  key: string;
  planned: string | null;
}
export interface RoleConfig {
  id: RoleId;
  card: string;
  holders: string;
  data: string;
  also_on: string[];
  weekly_minutes: number | null;
  can: RoleLine[];
  cannot: RoleLine[];
}
export interface RolesResponse {
  judge: boolean;
  roles: RoleConfig[];
}

export async function loadRoles(fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<RolesResponse> {
  const res = await fetchFn(`${API_BASE}/api/roles`);
  if (!res.ok) throw new Error(`roles ${res.status}`);
  return (await res.json()) as RolesResponse;
}

const SEEN = "cc.roleSeen.";

/** The dialog shows the first time a role is entered in this browser. No server state. */
export function dialogSeen(role: string, kv: Pick<Storage, "getItem"> | null = safe()): boolean {
  try {
    return kv?.getItem(SEEN + role) === "1";
  } catch {
    return false;
  }
}

export function markDialogSeen(role: string, kv: Pick<Storage, "setItem"> | null = safe()): void {
  try {
    kv?.setItem(SEEN + role, "1");
  } catch {
    /* private mode: the dialog just shows again */
  }
}

function safe(): Storage | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

let judgeCache: Promise<boolean> | null = null;

/** Whether this deployment is the judge-mode demo. The server decides; the app only asks. */
export function judgeDeployment(): Promise<boolean> {
  judgeCache ??= loadRoles().then(
    (r) => r.judge,
    () => {
      judgeCache = null; // offline or down: ask again next time, show no judge extras meanwhile
      return false;
    },
  );
  return judgeCache;
}

export function useJudge(): boolean {
  const [judge, setJudge] = useState(false);
  useEffect(() => {
    let live = true;
    void judgeDeployment().then((j) => live && setJudge(j));
    return () => {
      live = false;
    };
  }, []);
  return judge;
}
