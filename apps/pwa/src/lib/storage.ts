// Persistent storage: ask the browser not to clear this phone's data (checks, rehearsals) when space is
// short. A browser may refuse; the app says so, and the backup file is the safety net.
interface StorageNav {
  storage?: {
    persist?: () => Promise<boolean>;
    persisted?: () => Promise<boolean>;
    estimate?: () => Promise<{ usage?: number; quota?: number }>;
  };
}

export interface PersistenceStatus {
  supported: boolean;
  persisted: boolean;
  usage: number;
  quota: number;
}

const nav = (): StorageNav => (typeof navigator === "undefined" ? {} : (navigator as unknown as StorageNav));

export async function requestPersistence(n: StorageNav = nav()): Promise<boolean> {
  try {
    if (!n.storage?.persist) return false;
    return await n.storage.persist();
  } catch {
    return false;
  }
}

export async function persistenceStatus(n: StorageNav = nav()): Promise<PersistenceStatus> {
  const s = n.storage;
  if (!s?.persisted) return { supported: false, persisted: false, usage: 0, quota: 0 };
  try {
    const est = (await s.estimate?.()) ?? {};
    return { supported: true, persisted: await s.persisted(), usage: est.usage ?? 0, quota: est.quota ?? 0 };
  } catch {
    return { supported: true, persisted: false, usage: 0, quota: 0 };
  }
}
