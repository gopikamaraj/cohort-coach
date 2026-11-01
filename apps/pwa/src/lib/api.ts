// Where the API lives. Empty in dev and in tests (the dev and preview servers proxy /api);
// set VITE_API_BASE to the API's https address when the PWA is hosted separately (staging).
// There is one back end: the app, the papers, the demo and the pilot staff's pages all call it.
const env = import.meta.env as Record<string, string | undefined>;

export const API_BASE: string = env["VITE_API_BASE"] ?? "";
