/** What the stage of the tab Video shows: the video or «Feld von oben» (the tactics camera). */
export type StageMode = "video" | "taktik";

export const STAGE_MODE_KEY = "hb.stage-mode";

/**
 * The coach's last choice on this device; the video when there is none, or the storage cannot be
 * read (private mode, blocked site data). App review UX-01: the video is the default.
 */
export function readStageMode(storage?: Pick<Storage, "getItem"> | null): StageMode {
  try {
    const store = storage === undefined ? (typeof window === "undefined" ? null : window.localStorage) : storage;
    return store?.getItem(STAGE_MODE_KEY) === "taktik" ? "taktik" : "video";
  } catch {
    return "video";
  }
}
