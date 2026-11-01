// Approved answer sheets kept for the teacher for 60 days (a private bucket, behind the API). Only if she
// agreed ("keep_sheets"). The picture is the shrunk JPEG the phone already made; the sheet carries a roll
// number only. Everything here is best effort: when it fails the picture is still on the phone and she is told.
import { API_BASE } from "./api";
import { deviceId } from "./consent";

export interface Kept {
  roll: number;
  approved_at: string;
  delete_after: string;
}

function headers(role: string, classId: string): Record<string, string> {
  return { "X-Role": role === "mentor" ? "mentor" : "teacher", "X-Class-Id": classId, "X-Device-Id": deviceId() };
}

const base = (checkId: string) => `${API_BASE}/api/sheet-keep/${encodeURIComponent(checkId)}`;

export async function keepStatus(role: string, classId: string, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<{ enabled: boolean; retention_days: number }> {
  try {
    const res = await fetchFn(`${API_BASE}/api/sheet-keep/status`, { headers: headers(role, classId) });
    return res.ok ? ((await res.json()) as { enabled: boolean; retention_days: number }) : { enabled: false, retention_days: 60 };
  } catch {
    return { enabled: false, retention_days: 60 };
  }
}

export async function listKept(role: string, classId: string, checkId: string, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<Kept[]> {
  try {
    const res = await fetchFn(base(checkId), { headers: headers(role, classId) });
    return res.ok ? ((await res.json()) as Kept[]) : [];
  } catch {
    return [];
  }
}

/** Keep (or replace) the picture of one roll number. Throws when it could not be kept. */
export async function keepSheet(role: string, classId: string, checkId: string, roll: number, picture: Blob, sha256: string, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<Kept> {
  const body = new FormData();
  body.append("image", picture, "sheet.jpg");
  body.append("consent", "1");
  if (sha256) body.append("sha256", sha256);
  const res = await fetchFn(`${base(checkId)}/${roll}`, { method: "PUT", headers: headers(role, classId), body });
  if (!res.ok) throw new Error(String(res.status));
  return (await res.json()) as Kept;
}

export async function fetchKept(role: string, classId: string, checkId: string, roll: number, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<Blob> {
  const res = await fetchFn(`${base(checkId)}/${roll}/image`, { headers: headers(role, classId) });
  if (!res.ok) throw new Error(String(res.status));
  return res.blob();
}

export async function deleteKept(role: string, classId: string, checkId: string, roll: number, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<void> {
  const res = await fetchFn(`${base(checkId)}/${roll}`, { method: "DELETE", headers: headers(role, classId) });
  if (!res.ok && res.status !== 404) throw new Error(String(res.status));
}
