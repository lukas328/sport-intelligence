import type { QueryClient, QueryKey } from "@tanstack/react-query";

/**
 * Loads a list again after a write (a new unit, a deleted one). A plain invalidate joins a first
 * load that is still under way, and that load started before the write: the list would stay
 * without the new entry and no new request would follow (dev server, «Neue Einheit»). So the
 * running load is cancelled first, then the list is fetched fresh.
 */
export async function refreshList(qc: QueryClient, queryKey: QueryKey) {
  await qc.cancelQueries({ queryKey });
  await qc.invalidateQueries({ queryKey });
}
