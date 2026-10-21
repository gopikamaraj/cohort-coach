import { describe, expect, it } from "vitest";
import { nextPlayback, type Playback } from "./watch";

const start: Playback = { index: 0, playing: true, speed: 1 };

describe("Watch playback", () => {
  it("ticks forward one turn at a time and stops at the end", () => {
    let p = start;
    for (let i = 0; i < 3; i++) p = nextPlayback(p, 3, "tick");
    expect(p).toEqual({ index: 3, playing: false, speed: 1 });
    expect(nextPlayback(p, 3, "tick")).toEqual(p);
  });
  it("pause stops ticks, step shows exactly one more turn, 2x flips the speed", () => {
    const paused = nextPlayback(start, 5, "pause");
    expect(nextPlayback(paused, 5, "tick").index).toBe(0);
    expect(nextPlayback(paused, 5, "step")).toEqual({ index: 1, playing: false, speed: 1 });
    expect(nextPlayback(start, 5, "fast").speed).toBe(2);
    expect(nextPlayback(nextPlayback(start, 5, "fast"), 5, "fast").speed).toBe(1);
  });
  it("skip jumps to the feedback and play does not restart a finished run", () => {
    const done = nextPlayback(start, 4, "skip");
    expect(done.index).toBe(4);
    expect(nextPlayback(done, 4, "play").playing).toBe(false);
  });
});
