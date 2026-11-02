// The roll numbers of one check, as the Enter check page shows them: each has a data state (not entered,
// entered, absent) and an approval state. Pure functions only, so the rules are tested without a browser.
//   - Marking a roll absent approves it. Only the teacher marks absent.
//   - Any change to an approved roll's answers, marks or tags sets it back to not approved.
//   - Finish is allowed only when every roll is approved or absent, and at least one is entered and approved.
import { isEmptyRow } from "./check";

export type DataState = "not_entered" | "entered" | "absent";

export interface RollSet {
  rows: string[][];
  absent: ReadonlySet<number>;
  approved: ReadonlySet<number>;
}

export function dataState(rs: RollSet, i: number): DataState {
  if (rs.absent.has(i)) return "absent";
  return isEmptyRow(rs.rows[i] ?? []) ? "not_entered" : "entered";
}

/** Absent rolls are approved automatically; a roll that is not entered has no approval to speak of. */
export function isApproved(rs: RollSet, i: number): boolean {
  const s = dataState(rs, i);
  return s === "absent" || (s === "entered" && rs.approved.has(i));
}

export type OptionKey = "check.opt_not_entered" | "check.opt_entered_not_approved" | "check.opt_awaiting_check" | "check.opt_entered_approved" | "check.opt_absent";

/** `awaiting`: the AI read this roll from a photo and flagged boxes for her to check. */
export function optionKey(rs: RollSet, i: number, awaiting = false): OptionKey {
  const s = dataState(rs, i);
  if (s === "absent") return "check.opt_absent";
  if (s === "not_entered") return "check.opt_not_entered";
  if (rs.approved.has(i)) return "check.opt_entered_approved";
  return awaiting ? "check.opt_awaiting_check" : "check.opt_entered_not_approved";
}

/** Roll numbers 0..size-1: every roll up to the class size, or as many as have been opened. */
export function rollCount(rs: RollSet, classSize: number | null): number {
  return Math.max(rs.rows.length, classSize ?? 0);
}

export interface Counts {
  entered: number;
  approved: number;
  absent: number;
  notEntered: number;
  toApprove: number;
  total: number;
}

export function countRolls(rs: RollSet, classSize: number | null): Counts {
  const total = rollCount(rs, classSize);
  const c: Counts = { entered: 0, approved: 0, absent: 0, notEntered: 0, toApprove: 0, total };
  for (let i = 0; i < total; i++) {
    const s = dataState(rs, i);
    if (s === "absent") c.absent += 1;
    else if (s === "not_entered") c.notEntered += 1;
    else {
      c.entered += 1;
      if (rs.approved.has(i)) c.approved += 1;
      else c.toApprove += 1;
    }
  }
  return c;
}

/** The next roll to approve after `from` (entered, not approved), wrapping round; null when none. */
export function nextToApprove(rs: RollSet, from: number, classSize: number | null): number | null {
  const n = rollCount(rs, classSize);
  for (let d = 1; d <= n; d++) {
    const i = (from + d) % n;
    if (dataState(rs, i) === "entered" && !rs.approved.has(i)) return i;
  }
  return null;
}

export function nextNotEntered(rs: RollSet, from: number, classSize: number | null): number | null {
  const n = rollCount(rs, classSize);
  for (let d = 1; d <= n; d++) {
    const i = (from + d) % n;
    if (dataState(rs, i) === "not_entered") return i;
  }
  return null;
}

/** After Approve: the next roll to approve, else the next not entered, else stay. */
export function afterApprove(rs: RollSet, from: number, classSize: number | null): number {
  return nextToApprove(rs, from, classSize) ?? nextNotEntered(rs, from, classSize) ?? from;
}

export const NOTE_CAP = 8;

export type FinishNote =
  | { kind: "none_entered" }
  | { kind: "not_entered"; rolls: number[]; more: number }
  | { kind: "not_approved"; rolls: number[]; more: number }
  | { kind: "ready"; total: number };

export interface FinishGate {
  enabled: boolean;
  notes: FinishNote[];
  entered: number;
  absent: number;
}

function capped(list: number[]): { rolls: number[]; more: number } {
  return { rolls: list.slice(0, NOTE_CAP), more: Math.max(0, list.length - NOTE_CAP) };
}

/** Roll numbers (1-based) shown to the teacher. */
export function finishGate(rs: RollSet, classSize: number | null): FinishGate {
  const total = rollCount(rs, classSize);
  const notEntered: number[] = [];
  const notApproved: number[] = [];
  let approvedEntered = 0;
  let absent = 0;
  for (let i = 0; i < total; i++) {
    const s = dataState(rs, i);
    if (s === "absent") absent += 1;
    else if (s === "not_entered") notEntered.push(i + 1);
    else if (rs.approved.has(i)) approvedEntered += 1;
    else notApproved.push(i + 1);
  }
  const notes: FinishNote[] = [];
  const entered = approvedEntered + notApproved.length;
  if (entered === 0) notes.push({ kind: "none_entered" });
  if (notEntered.length > 0 && entered > 0) notes.push({ kind: "not_entered", ...capped(notEntered) });
  if (notApproved.length > 0) notes.push({ kind: "not_approved", ...capped(notApproved) });
  const enabled = notEntered.length === 0 && notApproved.length === 0 && approvedEntered >= 1;
  if (enabled) notes.length = 0;
  if (enabled) notes.push({ kind: "ready", total });
  return { enabled, notes, entered: approvedEntered, absent };
}

/** "4, 9 and 12" / "1, 2, 3, 4, 5, 6, 7, 8 and 3 more", with `and` supplied by the language. */
export function listRolls(rolls: number[], more: number, and: string, moreText: (n: number) => string): string {
  const parts = rolls.map(String);
  if (more > 0) return `${parts.join(", ")} ${and} ${moreText(more)}`;
  if (parts.length <= 1) return parts.join("");
  return `${parts.slice(0, -1).join(", ")} ${and} ${parts[parts.length - 1]}`;
}

/** Any edit to an approved roll (answers, marks, tags) sets it back to not approved. */
export function withoutApproval(approved: ReadonlySet<number>, i: number): Set<number> {
  const next = new Set(approved);
  next.delete(i);
  return next;
}

/** Approving needs something entered. */
export function canApprove(rs: RollSet, i: number): boolean {
  return dataState(rs, i) === "entered" && !rs.approved.has(i);
}

// ---- Missed-the-teaching checkboxes: question numbers come from the chosen paper's own items ----

export type ConceptName = "addition" | "place_value" | "subtraction";
const ORDER: ConceptName[] = ["addition", "place_value", "subtraction"];

/** Which concept an item rests on, from the errors it probes (PV-*, ADD-*, SUB-*). */
export function conceptOfProbes(probes: string[]): ConceptName | null {
  if (probes.some((p) => p.startsWith("PV-"))) return "place_value";
  if (probes.some((p) => p.startsWith("ADD-"))) return "addition";
  if (probes.some((p) => p.startsWith("SUB-"))) return "subtraction";
  return null;
}

/** [3,4,5,11] -> "3–5 and 11"; [7,8,9,10,14,15] -> "7–10 and 14–15". */
export function formatQuestions(numbers: number[], and: string): string {
  const sorted = [...new Set(numbers)].sort((a, b) => a - b);
  const ranges: string[] = [];
  let start = 0;
  for (let i = 1; i <= sorted.length; i++) {
    if (i === sorted.length || sorted[i] !== (sorted[i - 1] as number) + 1) {
      const lo = sorted[start] as number;
      const hi = sorted[i - 1] as number;
      ranges.push(lo === hi ? String(lo) : `${lo}–${hi}`);
      start = i;
    }
  }
  return ranges.length <= 1 ? (ranges[0] ?? "") : `${ranges.slice(0, -1).join(", ")} ${and} ${ranges[ranges.length - 1]}`;
}

/** The checkboxes in the order addition, place value, subtraction; a concept with no item is left out. */
export function conceptQuestions(items: { n: number; probes: string[] }[]): { concept: ConceptName; questions: number[] }[] {
  const by = new Map<ConceptName, number[]>();
  for (const it of items) {
    const c = conceptOfProbes(it.probes);
    if (c) by.set(c, [...(by.get(c) ?? []), it.n]);
  }
  return ORDER.filter((c) => by.has(c)).map((c) => ({ concept: c, questions: by.get(c) as number[] }));
}
