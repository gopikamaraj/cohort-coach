// The guided tour (rebuilt 6 Nov 2026): nine steps, about five minutes, following one teacher's path and then the staff
// pages. Each step names the role, opens the real screen and says what to notice. The list lives here (it is
// navigation, not a rule). Sign in with a nickname first: 3A Math or 3B Math shows the pilot class data as Teacher;
// Block Officer shows the officer page with its real counts; the mentor and coach pages hold mocked data.
import type { RoleId } from "./roles";
import type { Route } from "./router";

export interface TourStep {
  n: number;
  role: RoleId;
  seconds: number;
  route: Route; // the real screen the step opens
  mocked: boolean; // the screen holds simulated data, and the step says so
  title: string; // string keys
  notice: string;
}

export const TOUR: readonly TourStep[] = [
  { n: 1, role: "teacher", seconds: 30, route: "/papers", mocked: false, title: "tour.s1.title", notice: "tour.s1.notice" },
  { n: 2, role: "teacher", seconds: 35, route: "/check", mocked: false, title: "tour.s2.title", notice: "tour.s2.notice" },
  { n: 3, role: "teacher", seconds: 30, route: "/cards", mocked: false, title: "tour.s3.title", notice: "tour.s3.notice" },
  { n: 4, role: "teacher", seconds: 35, route: "/cohort", mocked: false, title: "tour.s4.title", notice: "tour.s4.notice" },
  { n: 5, role: "teacher", seconds: 45, route: "/practice", mocked: false, title: "tour.s5.title", notice: "tour.s5.notice" },
  { n: 6, role: "teacher", seconds: 20, route: "/profile", mocked: false, title: "tour.s6.title", notice: "tour.s6.notice" },
  { n: 7, role: "officer", seconds: 45, route: "/officer", mocked: false, title: "tour.s7.title", notice: "tour.s7.notice" },
  { n: 8, role: "mentor", seconds: 30, route: "/mentor", mocked: true, title: "tour.s8.title", notice: "tour.s8.notice" },
  { n: 9, role: "coach", seconds: 30, route: "/coach", mocked: true, title: "tour.s9.title", notice: "tour.s9.notice" },
];

export const TOUR_SECONDS = TOUR.reduce((t, s) => t + s.seconds, 0);

/** The step a "60-second walk-through" starts at for each role. */
export const WALK_START: Record<RoleId, number> = { teacher: 1, mentor: 8, coach: 9, officer: 7 };

/** Step number from a hash such as "#/tour/3?x=1", or null when the hash is not a tour step. */
export function stepFromHash(hash: string): number | null {
  const m = /^#?\/tour\/(\d+)(?:\?.*)?$/.exec(hash);
  const n = m ? Number(m[1]) : NaN;
  return n >= 1 && n <= TOUR.length ? n : null;
}
