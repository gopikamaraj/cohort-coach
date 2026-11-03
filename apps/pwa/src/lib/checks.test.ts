import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { CheckRow, ProfileRow } from "./db";
import {
  canClose,
  checkId,
  findDuplicate,
  formatCheckLabel,
  legacyFields,
  nextSeq,
  seqOf,
  currentCheck,
  slotForNew,
  openCheck,
  pairChecks,
  suggestForm,
  suggestKind,
  summaryOf,
} from "./checks";

const clean = (n = 10) => Array.from({ length: n }, () => "1");
function check(over: Partial<CheckRow>): CheckRow {
  return { id: "c1:1", classId: "c1", term: 1, formKey: "A", children: [clean()], updatedAt: Date.parse("2026-10-26T10:00:00Z"), ...over };
}
function profile(over: Partial<ProfileRow>): ProfileRow {
  return { id: "c1:1", classId: "c1", term: 1, formKey: "A", childrenChecked: 18, counts: {}, eligible: [], track: null, anchorWrongCount: 0, untracked: {}, simulated: false, createdAt: 0, ...over };
}
const tr = (key: string, p?: Record<string, string | number>) =>
  ({ "check.kind.pre": "Pre-test", "check.kind.post": "Post-test", "check.kind.termly": "Termly check", "check.form_n": `Form ${p?.f}`, "check.class_n": `Class ${p?.c}` })[key] ?? key;

describe("ids", () => {
  it("keeps the old id so nothing already saved is orphaned", () => {
    expect(checkId("c1", 2)).toBe("c1:2");
    expect(seqOf("c1:2")).toBe(2);
    expect(seqOf("c1:2:3")).toBe(2);
    expect(seqOf("coach")).toBe(0);
  });
  it("takes the next free running number for a class, whatever terms its old checks carry", () => {
    expect(nextSeq([], "c1")).toBe(1);
    expect(nextSeq([check({}), check({ id: "c1:2", term: 2 })], "c1")).toBe(3);
    expect(nextSeq([check({ classId: "c2", id: "c2:5" })], "c1")).toBe(1);
  });
  it("her current check is the one being entered, else the latest saved; never hidden by a number", () => {
    const old = check({ id: "c1:1", status: "closed", updatedAt: 10 });
    const newer = check({ id: "c1:2", term: 2, status: "closed", updatedAt: 20 });
    const open = check({ id: "c1:3", status: "entering", updatedAt: 5 });
    expect(currentCheck([old, newer], "c1")?.id).toBe("c1:2");
    expect(currentCheck([old, newer, open], "c1")?.id).toBe("c1:3");
    expect(currentCheck([old], "c2")).toBeUndefined();
    expect(slotForNew([old, newer], "c1")).toBe(3);
    expect(slotForNew([old, newer, open], "c1")).toBe(3);
  });
});

describe("what to suggest", () => {
  it("suggests a pre-test, Form A, when there is no check yet", () => {
    expect(suggestKind([], [])).toBe("pre");
    expect(suggestForm("pre", [])).toBe("A");
  });
  it("suggests a post-test, Form B, once a track started after a Form A pre-test and three weeks have passed", () => {
    const pre = check({ kind: "pre", formKey: "A", status: "closed" });
    const prof = profile({ track: "SUB-SFL" });
    expect(suggestKind([pre], [prof], pre.updatedAt + 22 * 86_400_000)).toBe("post");
    expect(suggestForm("post", [pre])).toBe("B");
  });
  it("suggests a termly check when no track has finished, or a post-test already exists", () => {
    const pre = check({ kind: "pre", formKey: "A", status: "closed" });
    const later = pre.updatedAt + 22 * 86_400_000;
    expect(suggestKind([pre], [profile({ track: null })], later)).toBe("termly");
    expect(suggestKind([pre], [profile({ track: "SUB-SFL" })], pre.updatedAt + 86_400_000)).toBe("termly"); // the track is not over
    const post = check({ id: "c1:2", term: 2, kind: "post", formKey: "B", status: "closed", updatedAt: Date.parse("2026-12-01T10:00:00Z") });
    expect(suggestKind([pre, post], [profile({ track: "SUB-SFL" })], post.updatedAt + 30 * 86_400_000)).toBe("termly");
  });
  it("alternates the paper for later checks so a child does not see the same numbers twice", () => {
    expect(suggestForm("termly", [check({ formKey: "B", updatedAt: 5 })])).toBe("A");
    expect(suggestForm("termly", [check({ formKey: "A", updatedAt: 5 })])).toBe("B");
    expect(suggestForm("post", [check({ kind: "pre", formKey: "B" })])).toBe("A");
  });
});

describe("rules", () => {
  it("a check cannot be closed with no sheets", () => {
    expect(canClose(check({ children: [] })).ok).toBe(false);
    expect(canClose(check({ children: [["", "", "", "", "", "", "", "", "", ""]] })).ok).toBe(false);
    expect(canClose(check({ children: [clean()] })).ok).toBe(true);
  });
  it("is unique per class, kind, form and date", () => {
    const a = check({ kind: "pre", formKey: "A", checkDate: "2026-10-26" });
    expect(findDuplicate([a], { classId: "c1", kind: "pre", form: "A", checkDate: "2026-10-26" })?.id).toBe(a.id);
    expect(findDuplicate([a], { classId: "c1", kind: "pre", form: "B", checkDate: "2026-10-26" })).toBeUndefined();
    expect(findDuplicate([a], { classId: "c1", kind: "pre", form: "A", checkDate: "2026-10-27" })).toBeUndefined();
    expect(findDuplicate([a], { classId: "c2", kind: "pre", form: "A", checkDate: "2026-10-26" })).toBeUndefined();
  });
  it("lets only one check be open for entry per class", () => {
    const open = check({ status: "entering" });
    expect(openCheck([open, check({ id: "c1:2", status: "closed" })], "c1")?.id).toBe(open.id);
    expect(openCheck([check({ status: "closed" })], "c1")).toBeUndefined();
    expect(openCheck([open], "c2")).toBeUndefined();
  });
});

describe("labels", () => {
  it("names the kind, the form, the class and the date", () => {
    const c = check({ kind: "pre", formKey: "A", checkDate: "2026-10-29" });
    expect(formatCheckLabel(tr as never, c, "Class 3A", "en")).toBe("Pre-test · Form A · Class 3A · 29 Oct 2026");
  });
  it("summarises what exists, with papers entered", () => {
    const c = check({ kind: "pre", formKey: "A", checkDate: "2026-10-26", children: [clean(), clean(), ["", "", "", "", "", "", "", "", "", ""]] });
    expect(summaryOf(c)).toEqual({ kind: "pre", form: "A", date: "2026-10-26", papers: 2 });
  });
});

describe("migration of checks saved before there were labels", () => {
  const legacy = [
    check({ id: "c1:1", term: 1, formKey: "A", updatedAt: Date.parse("2026-10-20T10:00:00Z") }),
    check({ id: "c1:2", term: 2, formKey: "B", updatedAt: Date.parse("2026-11-20T10:00:00Z") }),
    check({ id: "c2:1", classId: "c2", term: 1, formKey: "A", updatedAt: Date.parse("2026-10-21T10:00:00Z") }),
  ];
  it("gives each class's earliest check the kind pre, a later Form B one post, and marks every one to confirm", () => {
    const out = legacy.map((c) => ({ ...c, ...legacyFields(c, legacy, new Set(["c1:1"])) }));
    expect(out.map((c) => c.kind)).toEqual(["pre", "post", "pre"]);
    expect(out.every((c) => c.confirm === true)).toBe(true);
    expect(out[0]?.checkDate).toBe("2026-10-20");
    expect(out[0]?.status).toBe("closed"); // it has a class result
    expect(out[1]?.status).toBe("entering");
    expect(out[0]?.round).toBe(1);
  });
  it("loses nothing: the sheets, form and term are untouched", () => {
    const first = legacy[0] as CheckRow;
    const out = { ...first, ...legacyFields(first, legacy, new Set()) };
    expect(out.children).toEqual(first.children);
    expect(out.formKey).toBe("A");
    expect(out.term).toBe(1);
    expect(out.id).toBe("c1:1");
  });
  it("does not overwrite a check that already has a label", () => {
    const labelled = check({ kind: "termly", checkDate: "2026-01-01", round: 2, status: "closed", confirm: false });
    expect(legacyFields(labelled, [labelled], new Set())).toEqual({});
  });
});

interface Case {
  name: string;
  pre: string[][];
  post: string[][];
  pre_absent: number[];
  post_absent: number[];
  expected: unknown;
}
const cases = JSON.parse(readFileSync(new URL("../../../../tests/fixtures/check_pairing_cases.json", import.meta.url), "utf-8")) as Case[];

describe("pairing, against the Python engine's own cases", () => {
  for (const c of cases) {
    it(c.name, () => {
      const got = pairChecks("A", c.pre, "B", c.post, new Set(c.pre_absent), new Set(c.post_absent));
      expect(got).toEqual(c.expected);
    });
  }
  it("shows counts only: no row, position or name anywhere in the result", () => {
    const got = pairChecks("A", [clean()], "B", [clean()]);
    expect(JSON.stringify(got)).not.toMatch(/name|roll|child|row|index/);
  });
});
