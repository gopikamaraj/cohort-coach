import { describe, expect, it } from "vitest";
import { secondsLeft, threaded, type ChatMessage } from "./gatedChat";

const msg = (id: string, kind: ChatMessage["kind"], replyTo: string | null = null): ChatMessage => ({
  id, kind, author: "Teacher 1", role: "teacher", text: id, hidden: false, created_at: "2026-11-02T10:00:00Z", reply_to: replyTo, qstatus: null,
  ai_due_at: null, after_seconds: null, ai_label: null, sources: [], corrected: false, corrects: null, abstained: false, demo: false, pinned: false, masked: [],
});

describe("secondsLeft", () => {
  it("counts down by the server's clock, never below zero", () => {
    const server = "2026-11-02T10:00:00Z";
    const due = "2026-11-02T10:00:05Z";
    expect(secondsLeft(due, server, 1000, 1000)).toBe(5);
    expect(secondsLeft(due, server, 1000, 3000)).toBe(3);
    expect(secondsLeft(due, server, 1000, 9000)).toBe(0);
    expect(secondsLeft(null, server, 1000, 1000)).toBeNull();
  });
});

describe("threaded", () => {
  it("puts replies, the AI answer and a correction under their question", () => {
    const rows = threaded([msg("q", "question"), msg("t", "tip"), msg("a", "ai_reply", "q"), msg("r", "reply", "q"), msg("c", "correction", "q")]);
    expect(rows.map((r) => r.message.id)).toEqual(["q", "t"]);
    expect(rows[0]!.replies.map((r) => r.id)).toEqual(["a", "r", "c"]);
  });
  it("keeps a reply whose question is not loaded", () => {
    expect(threaded([msg("r", "reply", "gone")]).map((r) => r.message.id)).toEqual(["r"]);
  });
});
