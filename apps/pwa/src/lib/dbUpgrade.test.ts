import "fake-indexeddb/auto";
import Dexie from "dexie";
import { describe, expect, it } from "vitest";
import { CohortDb } from "./db";

// A phone that opened the app before checks had labels: a version 1 database with two checks.
async function oldPhone(name: string) {
  const v1 = new Dexie(name);
  v1.version(1).stores({ classes: "id", checks: "id, classId", profiles: "id, classId", syncQueue: "++id, kind, classId", transcripts: "++id, classId", outbox: "++id, classId", settings: "key" });
  await v1.table("checks").bulkPut([
    { id: "c-1:1", classId: "c-1", term: 1, formKey: "A", children: [["3", "4"]], updatedAt: Date.parse("2026-10-20T10:00:00Z"), viaPhoto: [0] },
    { id: "c-1:2", classId: "c-1", term: 2, formKey: "B", children: [["5", "6"]], updatedAt: Date.parse("2026-11-20T10:00:00Z") },
  ]);
  await v1.table("profiles").put({ id: "c-1:1", classId: "c-1", term: 1, formKey: "A", childrenChecked: 1, counts: {}, eligible: [], track: null, anchorWrongCount: 0, untracked: {}, simulated: false, createdAt: 1 });
  v1.close();
}

describe("the version 2 upgrade", () => {
  it("labels the old checks, marks them to confirm, and loses no sheet", async () => {
    await oldPhone("upgrade-a");
    const db = new CohortDb("upgrade-a");
    const rows = await db.checks.orderBy("id").toArray();
    expect(rows.map((r) => [r.id, r.kind, r.status, r.confirm, r.checkDate])).toEqual([
      ["c-1:1", "pre", "closed", true, "2026-10-20"],
      ["c-1:2", "post", "entering", true, "2026-11-20"],
    ]);
    expect(rows[0]?.children).toEqual([["3", "4"]]);
    expect(rows[0]?.viaPhoto).toEqual([0]);
    expect(rows[1]?.formKey).toBe("B");
    expect(await db.profiles.count()).toBe(1);
    db.close();
  });

  it("is a no-op for a phone that has never had a check, and the date index works", async () => {
    const db = new CohortDb("upgrade-b");
    expect(await db.checks.count()).toBe(0);
    await db.checks.put({ id: "x:1", classId: "x", term: 1, formKey: "A", children: [], updatedAt: 1, checkDate: "2026-10-26" });
    expect((await db.checks.where("checkDate").equals("2026-10-26").toArray()).length).toBe(1);
    db.close();
  });
});
