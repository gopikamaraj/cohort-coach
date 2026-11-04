// Build-time feature flags. Assignment (a coach or officer sending a paper to a teacher, "Assigned to you")
// is switched off: every paper is shared with every user. Set VITE_ASSIGNMENT_ENABLED=1 to bring it back.
export const ASSIGNMENT_ENABLED =
  (import.meta.env as Record<string, string | undefined>)["VITE_ASSIGNMENT_ENABLED"] === "1";
