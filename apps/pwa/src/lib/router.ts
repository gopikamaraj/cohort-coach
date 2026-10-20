// A tiny hash router: routes work as deep links (the judge test script uses them) and need no
// server rewrite, so a static host and the offline cache both serve every screen.
import { useSyncExternalStore } from "react";

export type Route = "/judge" | "/home" | "/check" | "/cards" | "/practice" | "/programme" | "/history" | "/aimap" | "/audit" | "/later";
export const ROUTES: readonly Route[] = ["/judge", "/home", "/check", "/cards", "/practice", "/programme", "/history", "/aimap", "/audit", "/later"];

function current(): Route {
  const raw = window.location.hash.replace(/^#/, "").split("?")[0] ?? "";
  const path = raw.startsWith("/later") ? "/later" : raw;
  return (ROUTES as readonly string[]).includes(path) ? (path as Route) : "/judge";
}

function subscribe(listener: () => void): () => void {
  window.addEventListener("hashchange", listener);
  return () => window.removeEventListener("hashchange", listener);
}

export function useRoute(): Route {
  return useSyncExternalStore(subscribe, current, () => "/judge" as Route);
}

/** The ?name=value part of the hash, for deep links such as #/practice?seed=5. */
export function useQuery(): URLSearchParams {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash, () => "");
  return new URLSearchParams(hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : "");
}

export function go(route: Route): void {
  window.location.hash = route;
}

export function href(route: Route): string {
  return `#${route}`;
}
