// The guided tour: seven steps, about five minutes, switching roles as it goes. The list lives here
// (it is navigation, not a rule); each step shows a real screen and names the judging criterion.
import type { RoleId } from "./roles";

export type TourScreen = "check" | "cohort" | "content" | "practice" | "term2" | "hood" | "testing";

export interface TourStep {
  n: number;
  role: RoleId;
  seconds: number;
  screen: TourScreen;
  title: string; // string keys
  notice: string;
}

export const TOUR: readonly TourStep[] = [
  { n: 1, role: "teacher", seconds: 45, screen: "check", title: "tour.s1.title", notice: "tour.s1.notice" },
  { n: 2, role: "officer", seconds: 20, screen: "cohort", title: "tour.s2.title", notice: "tour.s2.notice" },
  { n: 3, role: "coach", seconds: 30, screen: "content", title: "tour.s3.title", notice: "tour.s3.notice" },
  { n: 4, role: "teacher", seconds: 120, screen: "practice", title: "tour.s4.title", notice: "tour.s4.notice" },
  { n: 5, role: "officer", seconds: 45, screen: "term2", title: "tour.s5.title", notice: "tour.s5.notice" },
  { n: 6, role: "teacher", seconds: 30, screen: "hood", title: "tour.s6.title", notice: "tour.s6.notice" },
  { n: 7, role: "officer", seconds: 10, screen: "testing", title: "tour.s7.title", notice: "tour.s7.notice" },
];

export const TOUR_SECONDS = TOUR.reduce((t, s) => t + s.seconds, 0);

/** The step a "60-second walk-through" starts at for each role. */
export const WALK_START: Record<RoleId, number> = { teacher: 1, mentor: 3, coach: 3, officer: 2 };

/** Step number from a hash such as "#/tour/3?x=1", or null when the hash is not a tour step. */
export function stepFromHash(hash: string): number | null {
  const m = /^#?\/tour\/(\d+)(?:\?.*)?$/.exec(hash);
  const n = m ? Number(m[1]) : NaN;
  return n >= 1 && n <= TOUR.length ? n : null;
}

/** The role banner shows only when the role changes from the step before. */
export function roleChanged(n: number): boolean {
  const here = TOUR[n - 1];
  const before = TOUR[n - 2];
  return Boolean(here && (!before || before.role !== here.role));
}
