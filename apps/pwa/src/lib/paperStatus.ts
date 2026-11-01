// Whether cohorts exist for the checks that used a paper, and if not, why and what to do next.
// Counts only: nothing here reads a child's answers beyond how many rows are filled in. The logic
// reads the check records on this phone and the placement the programme API already gives; it adds
// no second source of truth.
import type { CheckRow } from "./db";

export type Placement = "waiting" | "this_term" | "next_term" | null;

export type CohortReason =
  | "no_check" // no check has used this paper
  | "entering" // a check is open and not every sheet is entered
  | "not_approved" // every sheet entered, not approved yet
  | "not_submitted" // approved, not closed and submitted
  | "waiting_others" // submitted; cohorts need other classes with the same error
  | "formed_this_term"
  | "formed_next_term"
  | "unknown"; // the programme answer is not available (offline)

export type NextAction = "enter_check" | "continue_check" | "none";

export interface CohortStatus {
  reason: CohortReason;
  formed: boolean;
  entered?: number;
  expected?: number;
  cohortSize?: number;
  action: NextAction;
}

const filled = (row: string[]): boolean => row.some((c) => c.trim() !== "");

/** Rows entered so far in a check: children with at least one box filled, plus those skipped as absent. */
export function enteredCount(check: CheckRow): number {
  const absent = new Set(check.absent ?? []);
  return check.children.filter((row, i) => filled(row) || absent.has(i)).length;
}

export function cohortStatus(paperId: string, checks: readonly CheckRow[], placement: Placement, cohortSize?: number): CohortStatus {
  const used = checks.filter((c) => c.paperId === paperId);
  if (used.length === 0) return { reason: "no_check", formed: false, action: "enter_check" };
  const open = used.find((c) => c.status !== "closed");
  if (open) {
    const expected = open.expectedChildren ?? open.children.length;
    const entered = enteredCount(open);
    if (open.status === "approved") return { reason: "not_submitted", formed: false, entered, expected, action: "continue_check" };
    if (entered >= expected && expected > 0) return { reason: "not_approved", formed: false, entered, expected, action: "continue_check" };
    return { reason: "entering", formed: false, entered, expected, action: "continue_check" };
  }
  if (placement === "this_term") return { reason: "formed_this_term", formed: true, cohortSize, action: "none" };
  if (placement === "next_term") return { reason: "formed_next_term", formed: true, cohortSize, action: "none" };
  if (placement === "waiting") return { reason: "waiting_others", formed: false, action: "none" };
  return { reason: "unknown", formed: false, action: "none" };
}
