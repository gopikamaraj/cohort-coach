// When the page opens online, the server is the truth. A phone remembers only a pointer to a server record
// (the demo session, the two-class run); if the server no longer has that record (an admin deleted it),
// the pointer and anything cached from it are dropped, so there are never two copies that disagree.
// Only a clear "not found" answer removes anything: a failed or offline read changes nothing.
import { API_BASE } from "./api";

async function gone(path: string, fetchFn: typeof fetch): Promise<boolean> {
  try {
    const r = await fetchFn(`${API_BASE}${path}`);
    return r.status === 404;
  } catch {
    return false;
  }
}

export async function reconcileWithServer(fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<void> {
  let s: Storage;
  try {
    s = window.localStorage;
  } catch {
    return;
  }
  const demo = s.getItem("cc.demo.session");
  if (demo && /^demo-[0-9a-f]+$/.test(demo) && (await gone(`/api/demo/session/${demo}`, fetchFn))) {
    for (const k of ["cc.demo.session", "cc.demo.step", "cc.demo.reads", "cc.demo.paper", "cc.demo.paper.code", "cc.demo.entry"]) s.removeItem(k);
    window.dispatchEvent(new Event("cc-demo"));
  }
  const run = s.getItem("cc.run.id");
  if (run && /^run-[0-9a-f]{16}$/.test(run) && (await gone(`/api/cohort-run/runs/${run}`, fetchFn))) s.removeItem("cc.run.id");
}
