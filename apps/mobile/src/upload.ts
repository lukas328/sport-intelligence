import { mayUpload, missing, planParts, progress, type Network } from "@handball/client-core";
import { File, Paths } from "expo-file-system";
import * as Network_ from "expo-network";
import type { useSession } from "./session";

type Api = ReturnType<typeof useSession>["api"];

interface State {
  videoId: string;
  size: number;
  partSize: number;
  etags: Record<string, string>;
}

/** Resume state next to the recording, so an interrupted upload continues later (5.2). */
function stateFile(uri: string): File {
  const name = uri.split("/").pop() ?? "recording";
  return new File(Paths.document, `${name}.upload.json`);
}

function load(uri: string): State | null {
  const f = stateFile(uri);
  try {
    return f.exists ? (JSON.parse(f.textSync()) as State) : null;
  } catch {
    return null;
  }
}

function save(uri: string, s: State): void {
  stateFile(uri).write(JSON.stringify(s));
}

export async function network(): Promise<Network> {
  const s = await Network_.getNetworkStateAsync();
  if (!s.isConnected) return "none";
  if (s.type === Network_.NetworkStateType.WIFI || s.type === Network_.NetworkStateType.ETHERNET) return "wifi";
  if (s.type === Network_.NetworkStateType.CELLULAR) return "cellular";
  return "unknown";
}

export type UploadResult = "done" | "waiting" | "failed";

/**
 * Uploads a recording in parts directly to storage (presigned URLs) and completes it; the API then
 * starts the analysis. Returns "waiting" when only mobile data is available and not allowed.
 */
export async function uploadRecording(
  api: Api,
  orgId: string,
  matchId: string,
  uri: string,
  allowCellular: boolean,
  onProgress: (fraction: number) => void,
): Promise<UploadResult> {
  const file = new File(uri);
  const size = file.size ?? 0;
  let state = load(uri);
  if (!state) {
    const r = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/videos", {
      params: { path: { org_id: orgId, match_id: matchId } },
      body: { filename: uri.split("/").pop() ?? "spiel.mp4", size_bytes: size, content_type: "video/mp4", role: "main" },
    });
    if (!r.data) return "failed";
    state = { videoId: r.data.video.id, size, partSize: r.data.part_size, etags: {} };
    save(uri, state);
  }
  const parts = planParts(state.size, state.partSize);
  const handle = file.open();
  try {
    for (;;) {
      const todo = missing(parts, Object.keys(state.etags).map(Number));
      onProgress(progress(parts, Object.keys(state.etags).map(Number)));
      if (todo.length === 0) break;
      const left = todo.reduce((s, p) => s + (p.end - p.start), 0);
      if (!mayUpload(await network(), left, allowCellular)) return "waiting";
      const batch = todo.slice(0, 10);
      const urls = await api.POST("/v1/orgs/{org_id}/videos/{video_id}/parts", {
        params: { path: { org_id: orgId, video_id: state.videoId } },
        body: { numbers: batch.map((p) => p.number) },
      });
      if (!urls.data) return "failed";
      for (const { number, url } of urls.data) {
        const part = batch.find((p) => p.number === number)!;
        handle.offset = part.start;
        const bytes = handle.readBytes(part.end - part.start);
        const put = await fetch(url, { method: "PUT", body: bytes });
        const etag = put.headers.get("etag");
        if (!put.ok || !etag) return "failed";
        state.etags[String(number)] = etag;
        save(uri, state);
        onProgress(progress(parts, Object.keys(state.etags).map(Number)));
      }
    }
  } finally {
    handle.close();
  }
  const done = await api.POST("/v1/orgs/{org_id}/videos/{video_id}/complete", {
    params: { path: { org_id: orgId, video_id: state.videoId } },
    body: { parts: Object.entries(state.etags).map(([n, etag]) => ({ number: Number(n), etag })) },
  });
  if (!done.data) return "failed";
  stateFile(uri).delete();
  return "done";
}
