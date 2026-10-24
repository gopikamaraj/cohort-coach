// The pilot app's router. Two pages exist; every other address, including every route of the full
// app, is sent to Upload sheets. (The server also answers 404 for every non-pilot API route.)
import { useSyncExternalStore } from "react";

export type PilotRoute = "/upload" | "/audio";
export const PILOT_ROUTES: readonly PilotRoute[] = ["/upload", "/audio"];

/** The pilot route a location hash means; anything else means Upload sheets. */
export function resolveRoute(hash: string): PilotRoute {
  const path = hash.replace(/^#/, "").split("?")[0] ?? "";
  return (PILOT_ROUTES as readonly string[]).includes(path) ? (path as PilotRoute) : "/upload";
}

/** True when the hash is not a pilot route and should be replaced. */
export function needsRedirect(hash: string): boolean {
  return hash.replace(/^#/, "").split("?")[0] !== resolveRoute(hash);
}

function subscribe(listener: () => void): () => void {
  window.addEventListener("hashchange", listener);
  return () => window.removeEventListener("hashchange", listener);
}

export function usePilotRoute(): PilotRoute {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash, () => "");
  return resolveRoute(hash);
}

/** Replace any address that is not a pilot page; called on load and on every hash change. */
export function enforceRoute(): void {
  if (needsRedirect(window.location.hash)) window.location.replace("#/upload");
}

export function goPilot(route: PilotRoute): void {
  window.location.hash = route;
}

export function href(route: PilotRoute): string {
  return `#${route}`;
}
