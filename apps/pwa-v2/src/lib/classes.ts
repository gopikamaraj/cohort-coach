// A teacher can have several classes (sections). Each has its own checks, results and rehearsals; one is
// active at a time. Deleting a class removes its data from this phone and asks the server to erase its counts.
import { API_BASE } from "./api";
import { db, getSetting, newClassId, setSetting, type ClassRow, type CohortDb } from "./db";

export interface ClassItem extends ClassRow {
  active: boolean;
}

export async function listClasses(store: CohortDb = db): Promise<ClassItem[]> {
  const [rows, active] = await Promise.all([store.classes.toArray(), getSetting<string | null>("activeClass", null, store)]);
  rows.sort((a, b) => a.createdAt - b.createdAt);
  const current = rows.find((r) => r.id === active)?.id ?? rows[0]?.id;
  return rows.map((r) => ({ ...r, active: r.id === current }));
}

const clean = (name: string) => name.trim().slice(0, 40);

export async function addClass(name: string, simulated: boolean, store: CohortDb = db): Promise<ClassRow> {
  const cleaned = clean(name);
  if (!cleaned) throw new Error("A class needs a name.");
  const row: ClassRow = { id: newClassId(simulated), name: cleaned, simulated, createdAt: Date.now() };
  await store.classes.put(row);
  if ((await getSetting<string | null>("activeClass", null, store)) === null) await setSetting("activeClass", row.id, store);
  return row;
}

export async function setActive(id: string, store: CohortDb = db): Promise<void> {
  if (await store.classes.get(id)) await setSetting("activeClass", id, store);
}

export async function renameClass(id: string, name: string, store: CohortDb = db): Promise<void> {
  const cleaned = clean(name);
  if (cleaned) await store.classes.update(id, { name: cleaned });
}

async function eraseOnServer(id: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/classes/${id}`, { method: "DELETE" });
    return res.ok;
  } catch {
    return false;
  }
}

/** Remove a class and everything kept for it on this phone; the server's counts are erased too when online. */
export async function deleteClass(id: string, store: CohortDb = db, erase: (id: string) => Promise<boolean> = eraseOnServer): Promise<boolean> {
  await store.transaction("rw", [store.classes, store.checks, store.profiles, store.syncQueue, store.transcripts, store.outbox], async () => {
    await store.classes.delete(id);
    await store.checks.where("classId").equals(id).delete();
    await store.profiles.where("classId").equals(id).delete();
    await store.syncQueue.where("classId").equals(id).delete();
    await store.transcripts.where("classId").equals(id).delete();
    await store.outbox.where("classId").equals(id).delete();
  });
  const remaining = await listClasses(store);
  const active = await getSetting<string | null>("activeClass", null, store);
  if (active === id) await setSetting("activeClass", remaining[0]?.id ?? null, store);
  return erase(id);
}
