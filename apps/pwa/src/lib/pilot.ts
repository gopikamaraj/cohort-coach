// Pilot class data: the classes entered from the pilot papers, signed in as "3A Math" or "3B Math". The app has no
// per-class pilot flag, so the pilot is known by these nicknames (normalised, as the server keeps them). A pilot class is
// real data: it is labelled "Pilot class data", never "Simulated".
import { getUser } from "./identity";

export const PILOT_USERS: readonly string[] = ["3a math", "3b math"];

export function isPilotUser(): boolean {
  const id = getUser()?.id;
  return id !== undefined && PILOT_USERS.includes(id);
}
