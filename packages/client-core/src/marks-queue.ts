/**
 * Offline queue for courtside marks (addendum 01, 5.3). Each mark keeps the phone's clock time and a
 * client id; the API stores a mark once per client id, so retries after a lost response are safe.
 */
export interface QueuedMark {
  client_id: string;
  device_time: string;
  key: string;
  note?: string;
}

type Store = Pick<Storage, "getItem" | "setItem">;
type Post = (marks: QueuedMark[]) => Promise<{ ok: boolean; stored?: string[] }>;

const storeKey = (matchId: string) => `hb.marks.${matchId}`;

export function pending(store: Store, matchId: string): QueuedMark[] {
  try {
    const raw = store.getItem(storeKey(matchId));
    return raw ? (JSON.parse(raw) as QueuedMark[]) : [];
  } catch {
    return [];
  }
}

function save(store: Store, matchId: string, items: QueuedMark[]): void {
  try {
    store.setItem(storeKey(matchId), JSON.stringify(items));
  } catch {
    /* storage blocked: marks still go out while the page is open */
  }
}

export function mark(store: Store, matchId: string, key: string, now: Date = new Date(), id: string = crypto.randomUUID()): QueuedMark {
  const item = { client_id: id, device_time: now.toISOString(), key };
  save(store, matchId, [...pending(store, matchId), item]);
  return item;
}

/** Sends everything pending in one request; removes what the API confirmed. Returns the rest. */
export async function flush(store: Store, matchId: string, post: Post): Promise<number> {
  const items = pending(store, matchId);
  if (items.length === 0) return 0;
  try {
    const r = await post(items);
    if (!r.ok) return items.length;
    const done = new Set(r.stored ?? items.map((i) => i.client_id));
    const rest = pending(store, matchId).filter((i) => !done.has(i.client_id));
    save(store, matchId, rest);
    return rest.length;
  } catch {
    return items.length;
  }
}

/** Takes a mark out of the queue before it went out («Zurücknehmen»); true when it was queued. */
export function forget(store: Store, matchId: string, clientId: string): boolean {
  const items = pending(store, matchId);
  const rest = items.filter((i) => i.client_id !== clientId);
  save(store, matchId, rest);
  return rest.length !== items.length;
}
