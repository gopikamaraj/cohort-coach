// Where the API lives. Empty in dev and in tests (the dev and preview servers proxy /api);
// set VITE_API_BASE to the API's https address when the PWA is hosted separately (staging).
export const API_BASE: string = (import.meta.env["VITE_API_BASE"] as string | undefined) ?? "";
