// "Use sample sheets" (judge mode): recorded reads of made-up Form A rows from the server, so a
// judge can run a check without a photo. Nothing here is a real class; the label says so.
import { API_BASE } from "./api";

export interface SampleSheets {
  form: string;
  label: string;
  children: string[][];
  unsure: Record<string, number[]>;
  note: string;
}

export async function fetchSample(fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<SampleSheets> {
  const res = await fetchFn(`${API_BASE}/api/judge/sample-sheets`);
  if (!res.ok) throw new Error(`sample ${res.status}`);
  return (await res.json()) as SampleSheets;
}
