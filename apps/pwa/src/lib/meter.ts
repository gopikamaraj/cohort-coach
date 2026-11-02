// Data used: how many bytes this app has sent and received, counted on the phone, so she can see what it
// costs on her plan and clear the count. It measures our own calls (the API), not the phone's other traffic.
// The cost is code arithmetic from a price per GB she types; nothing is estimated by AI.
import { actionHeaders } from "./action";

export interface KV {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export interface Usage {
  sent: number;
  received: number;
  since: number;
}

const KEY = "cc.data";
const PRICE_KEY = "cc.data_price";
const local = (): KV | null => {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
};

export function getUsage(kv: KV | null = local()): Usage {
  try {
    const raw = kv?.getItem(KEY);
    if (raw) return JSON.parse(raw) as Usage;
  } catch {
    /* fall through */
  }
  return { sent: 0, received: 0, since: Date.now() };
}

export function record(sent: number, received: number, kv: KV | null = local()): void {
  if (!kv) return;
  const u = getUsage(kv);
  kv.setItem(KEY, JSON.stringify({ ...u, sent: u.sent + sent, received: u.received + received }));
}

export function resetUsage(kv: KV | null = local()): void {
  kv?.setItem(KEY, JSON.stringify({ sent: 0, received: 0, since: Date.now() }));
}

export function getPrice(kv: KV | null = local()): number | undefined {
  const v = Number(kv?.getItem(PRICE_KEY));
  return Number.isFinite(v) && v > 0 ? v : undefined;
}

export function setPrice(price: number | undefined, kv: KV | null = local()): void {
  if (price && price > 0) kv?.setItem(PRICE_KEY, String(price));
  else kv?.removeItem(PRICE_KEY);
}

/** Cost of the data used at `pricePerGb` (her own money unit), or null when she has not given a price. */
export function costOf(u: Usage, pricePerGb: number | undefined): number | null {
  return pricePerGb ? ((u.sent + u.received) / 1_000_000_000) * pricePerGb : null;
}

function size(body: unknown): number {
  if (typeof body === "string") return new TextEncoder().encode(body).length;
  if (body instanceof Blob) return body.size;
  if (body instanceof FormData) {
    let n = 0;
    body.forEach((v, k) => (n += k.length + (typeof v === "string" ? v.length : v.size)));
    return n;
  }
  return 0;
}

let installed = false;
/** Count the bytes of every call to our own API. Installed once at start-up. */
export function installMeter(api: string): void {
  if (installed || typeof window === "undefined") return;
  installed = true;
  const original = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const ours = url.startsWith("/api") || (api !== "" && url.startsWith(api));
    const extra = ours ? actionHeaders() : {};
    if (Object.keys(extra).length > 0) {
      const h = new Headers(init?.headers);
      for (const [k, v] of Object.entries(extra)) h.set(k, v); // the running action's id (lib/action.ts)
      init = { ...init, headers: h };
    }
    const res = await original(input, init);
    if (ours) {
      const len = Number(res.headers.get("content-length"));
      const got = Number.isFinite(len) && len > 0 ? len : (await res.clone().blob().then((b) => b.size, () => 0));
      record(size(init?.body) + url.length, got);
    }
    return res;
  };
}
