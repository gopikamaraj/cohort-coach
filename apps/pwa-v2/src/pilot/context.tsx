import { createContext, useContext } from "react";
import type { Key, Lang } from "../i18n";
import type { Session } from "./api";

export interface PilotState {
  lang: Lang;
  tr: (key: Key, params?: Record<string, string | number>) => string;
  session: Session;
  online: boolean;
}

export const PilotCtx = createContext<PilotState | null>(null);

export function usePilot(): PilotState {
  const ctx = useContext(PilotCtx);
  if (!ctx) throw new Error("usePilot outside the pilot app");
  return ctx;
}
