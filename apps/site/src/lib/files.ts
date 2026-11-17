/** The sentences that depend on a switch, filled into the texts as {pause}, {pauseShort}, {upload}, {fileNeed}, {fileNot}. */
import type { Messages } from "@/messages/de";
import { MULTI_FILE } from "@/lib/site";

export function fileVars(m: Messages): Record<string, string> {
  return {
    pause: MULTI_FILE ? m.filming.pauseMulti : m.filming.pause,
    pauseShort: MULTI_FILE ? m.filming.pauseShortMulti : m.filming.pauseShort,
    upload: MULTI_FILE ? m.filming.uploadMulti : m.filming.upload,
    fileNeed: MULTI_FILE ? m.facts.fileNeedMulti : m.facts.fileNeed,
    fileNot: MULTI_FILE ? "" : m.facts.fileNot,
  };
}

/** «Das machst du»; while MULTI_FILE is false it also names that only the first file is analysed. */
export function notList(m: Messages): string[] {
  return MULTI_FILE ? m.honest.not : [...m.honest.not, m.honest.notFiles];
}
