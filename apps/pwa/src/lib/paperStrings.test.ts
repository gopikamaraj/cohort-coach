import { describe, expect, it } from "vitest";
import { allTables } from "../i18n";

// A status or reason the server can send must have a string in every language: a missing key made
// the whole Papers page fail to draw once, so each one is listed here.
const STATUSES = ["draft", "auto_approved", "queued", "approved", "rejected", "confirmed", "archived"];
const QUEUE_REASONS = ["custom", "failed_check", "unreviewed_words", "spot_check", "imported_pdf"];
const COHORT_REASONS = ["no_check", "entering", "not_approved", "not_submitted", "waiting_others", "formed_this_term", "formed_next_term", "unknown"];

describe("Papers strings", () => {
  it("has a string for every paper status and cohort reason, in every language", () => {
    for (const lang of ["en", "hi", "ta"] as const) {
      const table = allTables[lang] as Record<string, string>;
      for (const s of STATUSES) expect(table[`papers.status.${s}`], `${lang}:papers.status.${s}`).toBeTruthy();
      for (const r of QUEUE_REASONS) expect(table[`papers.reason.${r}`], `${lang}:papers.reason.${r}`).toBeTruthy();
      for (const r of COHORT_REASONS) expect(table[`papers.cohort.${r}`], `${lang}:papers.cohort.${r}`).toBeTruthy();
      for (const k of ["pre", "post", "termly"]) expect(table[`check.kind.${k}`]).toBeTruthy();
      for (const op of ["dictate", "add", "subtract", "other"]) expect(table[`ph.op_${op}`]).toBeTruthy();
    }
  });
});
