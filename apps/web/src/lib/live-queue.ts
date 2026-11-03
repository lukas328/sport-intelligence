/**
 * Offline queue for live tagging (courtside, unreliable Wi-Fi). Events are kept in localStorage per
 * match with a client id; `flush` posts them in order and removes each one the API confirmed. The API
 * is idempotent on the client id, so a retry after a lost response never creates a duplicate.
 */
export interface QueuedEvent {
  client_id: string;
  body: Record<string, unknown>;
  queued_at: number;
}

type Store = Pick<Storage, "getItem" | "setItem">;
type Post = (body: Record<string, unknown>) => Promise<{ ok: boolean; status: number; id?: string }>;

const key = (matchId: string) => `hb.live.${matchId}`;

export function load(store: Store, matchId: string): QueuedEvent[] {
  try {
    const raw = store.getItem(key(matchId));
    return raw ? (JSON.parse(raw) as QueuedEvent[]) : [];
  } catch {
    return [];
  }
}

function save(store: Store, matchId: string, items: QueuedEvent[]): void {
  try {
    store.setItem(key(matchId), JSON.stringify(items));
  } catch {
    /* storage full or blocked: the in-memory list still syncs while the page is open */
  }
}

export function enqueue(store: Store, matchId: string, body: Record<string, unknown>, id = crypto.randomUUID()): QueuedEvent {
  const item = { client_id: id, body: { ...body, client_id: id }, queued_at: Date.now() };
  save(store, matchId, [...load(store, matchId), item]);
  return item;
}

export function remove(store: Store, matchId: string, clientId: string): void {
  save(
    store,
    matchId,
    load(store, matchId).filter((e) => e.client_id !== clientId),
  );
}

/**
 * Sends queued events in order. Stops at the first network failure (still offline) and keeps the rest.
 * Events the API rejects as invalid (4xx except 408/429) are dropped so they cannot block the queue;
 * they are returned so the UI can tell the user.
 */
export async function flush(
  store: Store,
  matchId: string,
  post: Post,
): Promise<{ sent: { client_id: string; id?: string }[]; rejected: QueuedEvent[]; pending: number }> {
  const sent: { client_id: string; id?: string }[] = [];
  const rejected: QueuedEvent[] = [];
  for (const item of load(store, matchId)) {
    let res: Awaited<ReturnType<Post>>;
    try {
      res = await post(item.body);
    } catch {
      break; // offline
    }
    if (res.ok) {
      sent.push({ client_id: item.client_id, id: res.id });
      remove(store, matchId, item.client_id);
    } else if (res.status >= 400 && res.status < 500 && res.status !== 408 && res.status !== 429) {
      rejected.push(item);
      remove(store, matchId, item.client_id);
    } else {
      break; // server busy or down: retry later
    }
  }
  return { sent, rejected, pending: load(store, matchId).length };
}

/** Match clock: running time survives reloads (stored per match). */
export interface Clock {
  period: number;
  base_s: number; // seconds accumulated before the current run
  started_at: number | null; // epoch ms when running, else null
}

export function clockSeconds(c: Clock, now = Date.now()): number {
  return c.base_s + (c.started_at !== null ? (now - c.started_at) / 1000 : 0);
}

export function toggle(c: Clock, now = Date.now()): Clock {
  return c.started_at !== null ? { ...c, base_s: clockSeconds(c, now), started_at: null } : { ...c, started_at: now };
}

export function adjust(c: Clock, delta: number, now = Date.now()): Clock {
  const s = Math.max(0, clockSeconds(c, now) + delta);
  return { ...c, base_s: s, started_at: c.started_at !== null ? now : null };
}
